from rest_framework.views import APIView
from django.http import JsonResponse
from rest_framework import serializers, fields

from external_services.caching.cache_impl import CacheImpl
from utility.json_utilities import JsonUtilities
from togther.models import *
from django.contrib.auth.models import User
from collections import OrderedDict
import json
import time

from utility.celery_tasks import get_conversation_poll, update_event_instructors_in_cache, \
    update_event_highlights_in_cache, update_event_member_testimonials_in_cache, update_event_faq_in_cache, \
    update_event_attendees, update_event_attendees_for_micro_event
from .conversation.reactions import fetch_chatroom_or_conversation_reactions
from .serializers import (get_answer_files, get_preview_for_url, get_category_of_chatroom,
                          get_members_profile, get_share_url_text, CollabcardPollsSerializer,
                          get_removed_member_custom_text, get_collabcard_files, get_user_profile,
                          get_answer_text_for_poll)
from utility.states import (card_types, question_states, member_states, poll_types,
                            deleted_members, manager_rights, member_rights, conversation_states,
                            conversation_poll_types)
from utility.utils import (get_time_text, generate_private_link, eligibility_count,
                           get_members_count_in_community)
from django.conf import settings
from .user_moderation_rights import check_admin_approve_right
from utility.cache_keys import CONVERSATION_REACTIONS_CACHE_KEY, EVENT_INSTRUCTORS_CHATROOM, EVENT_HIGHLIGHTS_CHATROOM, \
    EVENT_MEMBERTESTIMONIALS_CHATROOM, EVENT_FAQ_CHATROOM, EVENT_ATTENDEES_CHATROOM, EVENT_ATTENDEES_CONVERSATION
from .static_files import *
from django.db.models import F, When, Q

url = settings.URL


def get_error_context(success, error_message):
    '''function to get error context for apis'''

    context = {
        'success': success,
        'error_message': error_message
    }
    return context


class reportsView(APIView):

    def get(self, request, *args, **kwargs):
        query_set = Report.objects.all().order_by("-id")[:2]
        serialized_obj = reportSerializer(query_set, many=True)
        return JsonResponse(serialized_obj.data, safe=False)


class YourCommunitySerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    purpose = serializers.CharField(write_only=True)
    about = serializers.CharField(write_only=True)
    image_url = serializers.CharField(write_only=True)
    type = serializers.IntegerField(write_only=True)
    sub_type = serializers.IntegerField(write_only=True)

    members_count = serializers.IntegerField(write_only=True)
    member_right_states = serializers.ListField(write_only=True)
    actions = serializers.ListField(write_only=True)
    open_reports_count = serializers.IntegerField(write_only=True)
    pending_chatroom_count = serializers.IntegerField(write_only=True)
    pending_members_count = serializers.IntegerField(write_only=True)
    collabcard_unseen = serializers.IntegerField(write_only=True)

    class Meta:
        model = Member_Engage
        fields = ('id', 'open_reports_count', 'member_state',
                  'click_state', 'collabcard_unseen', 'actions', 'name', 'purpose', 'about',
                  'member_right_states', 'pending_chatroom_count', 'image_url', 'members_count',
                  'type', 'sub_type', 'pending_members_count', 'order_time')

    def __init__(self, *args, **kwargs):
        super(YourCommunitySerializer, self).__init__(*args, **kwargs)
        self.current_user_id = self.context.get('current_user_id', None)  # optional
        self.promoter_id = self.context.get('promoter_id', None)
        self.is_owner = self.context.get('is_owner', False)
        self.current_user_instance = self.context.get('current_user_instance', None)
        self.user = User.objects.get(id=self.current_user_id)

    def get_name(self, community_engage):
        return community_engage.community_id.name

    def get_home_screen_community_actions(self, community_instance):

        actions = []

        community_details = {
            'title': "View community details",
            'route': """route://community?community_id=%s""" % (str(community_instance.id))
        }

        actions.append(community_details)

        member_directory = {
            'title': "View member directory",
            'route': """route://members_directory?community_id=%s&community_name=%s""" % (
                str(community_instance.id), community_instance.name)
        }

        actions.append(member_directory)

        invite_members = {
            'title': "Invite members to this community",
            'route': """route://community?community_id=%s&share=true""" % (
                str(community_instance.id))
        }

        actions.append(invite_members)

        return actions

    def to_representation(self, community_engage):
        data = super(YourCommunitySerializer, self).to_representation(community_engage)
        fields = self._readable_fields

        if community_engage.member_state == member_states.ADMIN:
            has_approve_right = check_admin_approve_right(self.user, community_engage.community_id)

            if has_approve_right:
                data['pending_members_count'] = community_engage.pending_members
            else:
                data['pending_members_count'] = 0

            data['pending_chatroom_count'] = community_engage.pending_chatrooms
            data['open_reports_count'] = community_engage.open_reports

        else:
            if 'pending_members_count' in data:
                del data['pending_members_count']
            if 'pending_chatroom_count' in data:
                del data['pending_chatroom_count']
            if 'open_reports_count' in data:
                del data['open_reports_count']

        community_data = CommunitySerializerV1(community_engage.community_id).data
        data.update(**community_data)

        data['member_right_states'] = json.loads(community_engage.rights_list) if community_engage.rights_list else []

        actions = self.get_home_screen_community_actions(community_engage.community_id)

        if community_engage.member_state == member_states.ADMIN:
            management_tools = {
                'title': """Management tools""",
                'route': """route://management_tools?community_id=%s&community_name=%s""" % (
                    str(data['id']), data['name'])
            }
            actions.append(management_tools)

        if community_engage.member_state in [member_states.ADMIN, member_states.MEMBER,
                                             member_states.PROFILE_UNAVAILABLE]:
            data['collabcard_unseen'] = community_engage.last_unseen_count
        else:
            data['collabcard_unseen'] = 0

        data['click_state'] = community_engage.click_state

        data['actions'] = actions

        for field in fields:
            if data[field.field_name] is None:
                del data[field.field_name]

        return data


class CommunitySerializerV1(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = ('id', 'name', 'purpose', 'about', 'image_url', 'members_count',
                  'type', 'sub_type', 'is_paid', 'auto_approval', 'grace_period',
                  'is_discoverable', 'website_url', "community_category", "referral_enabled",
                  "dashboard_link")

    def __init__(self, *args, **kwargs):
        super(CommunitySerializerV1, self).__init__(*args, **kwargs)
        self.current_user_id = self.context.get('current_user_id', None)  # optional
        self.promoter_id = self.context.get('promoter_id', None)
        self.is_owner = self.context.get('is_owner', False)
        self.current_user_instance = self.context.get('current_user_instance', None)
        self.restrict_members_count = self.context.get('restrict_members_count', False)

    def get_members_count(self, instance):

        if self.restrict_members_count:
            return None

        return get_members_count_in_community(instance)

    def to_representation(self, community):
        data = super(CommunitySerializerV1, self).to_representation(community)

        fields = self._readable_fields

        for field in fields:

            if field.field_name == "image_url":
                if community.image_link:
                    data['image_url'] = community.image_link
                elif community.image_url:
                    data['image_url'] = community.image_url.url
                else:
                    data['image_url'] = '/media/media/community/default.jpeg'

                if data['image_url'] == "/media/https%3A/upload.wikimedia.org/wikipedia/en/0/09/Community_title.jpg":
                    data[
                        'image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
                elif not community.image_link:
                    data['image_url'] = url + data['image_url']

            elif data[field.field_name] is None:
                del data[field.field_name]

        return data


class GetChatroomInstanceSerializer(serializers.ModelSerializer):
    """ alternative for get_chatroom_instance function, for only collabcard have to write a new DRF serializer """

    date = serializers.SerializerMethodField()
    card_creation_time = serializers.SerializerMethodField()
    poll_type_text = serializers.SerializerMethodField()
    submit_type_text = serializers.SerializerMethodField()
    chatroom_category = serializers.SerializerMethodField()
    is_anonymous = serializers.SerializerMethodField()
    member_id = serializers.SerializerMethodField()
    expiry_time = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    community_name = serializers.ReadOnlyField(source='community.name')
    deleted_by = serializers.SerializerMethodField()

    images = serializers.SerializerMethodField()
    pdf = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()
    audios = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    preview = serializers.DictField(write_only=True)
    polls = serializers.SerializerMethodField()
    share_url = serializers.CharField(write_only=True)
    creator_share_url = serializers.CharField(write_only=True)
    link_created_at = serializers.CharField(write_only=True)
    state = serializers.IntegerField(write_only=True)
    mute_status = serializers.BooleanField(write_only=True)
    follow_status = serializers.BooleanField(write_only=True)
    is_guest = serializers.BooleanField(write_only=True)
    is_tagged = serializers.BooleanField(write_only=True)
    chatroom_expiry_time = serializers.CharField(write_only=True)
    last_seen_conversation = serializers.IntegerField(write_only=True)
    attendees_ids = serializers.SerializerMethodField()
    instructors = serializers.SerializerMethodField()
    highlights = serializers.SerializerMethodField()
    testimonials = serializers.SerializerMethodField()
    faq = serializers.SerializerMethodField()

    class Meta:
        model = Collabcard
        fields = ('id', 'title', 'community_id', 'answer_text',
                  'image_count', 'pdf_count', 'video_count', 'audio_count', 'attachment_count',
                  'attachments_uploaded', 'type', 'date_time', 'is_pending', 'attending_count',
                  'polls_count', 'card_creation_time', 'community_name', 'has_been_named', 'date_epoch',
                  'user', 'is_poll_anonymous', 'allow_add_option', 'multiple_select_state',
                  'multiple_select_no', 'polls', 'location', 'location_lat', 'location_long',
                  'start_date', 'end_date', 'about', 'co_hosts', 'updated_member',
                  'community', 'og_tags', 'created_at', 'is_anonymous',
                  'expiry_time', 'poll_type_text', 'submit_type_text', 'date',
                  'chatroom_category', 'deleted_by', 'member_id', 'created_at',
                  'internal_link', 'images', 'pdf', 'audios', 'videos', 'attachments',
                  'preview', 'deleted_by', 'header',
                  'share_url', 'creator_share_url', 'link_created_at',
                  'state', 'mute_status', 'follow_status', 'is_guest', 'is_tagged', 'chatroom_expiry_time',
                  'poll_type', 'last_seen_conversation', 'is_secret', 'secret_chatroom_participants',
                  'topic_id', 'auto_follow_done', 'is_edited', 'attendees_ids', 'instructors', 'highlights',
                  'testimonials', 'faq', 'online_link_enable_before', 'is_paid', 'access',
                  'online_link', 'online_link_id', 'online_link_password', 'event_payment_link', 'event_web_page',
                  'webflow_item_id', 'is_private', 'chatroom_with_user_id', 'member_can_message', 'cohort_ids',
                  'has_event_recording', 'about_recording', 'recording_url_og_tags'
                  )

    def __init__(self, *args, **kwargs):
        super(GetChatroomInstanceSerializer, self).__init__(*args, **kwargs)
        self.member_id = self.context.get('member_id', None)  # required
        self.user = self.context.get('user', None)  # required
        self.state_instance = self.context.get('state_instance', None)  # optional
        self.current_user_id = self.context.get('current_user_id', None)  # optional
        if not self.current_user_id:
            self.current_user_id = self.member_id

    def get_created_at(self, card):

        return TimeUtilities.convert_epoch_time_in_hh_mm(card.date_epoch)

    def get_date(self, card):
        return TimeUtilities.convert_epoch_time_in_date(card.date_epoch)

    def get_card_creation_time(self, card):
        return TimeUtilities.convert_epoch_time_in_hh_mm_am_pm(card.date_epoch)

    def get_expiry_time(self, card):
        if card.type == card_types.CARD_POLL:
            return card.end_date
        return None

    def get_is_anonymous(self, card):
        if card.type == card_types.CARD_POLL:
            return card.is_poll_anonymous
        return None

    def get_poll_type_text(self, card):
        return "Instant poll" if card.poll_type == poll_types.POLL_TYPE_INSTANT else "Deferred poll"

    def get_submit_type_text(self, card):
        return "Secret voting" if card.is_poll_anonymous else "Public voting"

    def get_chatroom_category(self, card):
        return get_category_of_chatroom(card.type)

    def get_polls(self, card):

        polls = []
        if card.type == card_types.CARD_POLL:
            card_polls = CollabcardPolls.objects.filter(card=card).order_by('id')
            for poll in card_polls:
                poll_serializer = CollabcardPollsSerializer(poll, self.current_user_id, card)
                polls.append(poll_serializer)

        return polls

    def get_member_id(self, card):
        return card.user.id

    def get_deleted_by(self, card):
        deleted_by = None
        if card.deleted_by_user:
            deleted_by = card.deleted_by_user.id
        return deleted_by

    def get_co_hosts(self, co_hosts):

        co_host_list = []
        for member in co_hosts:
            temp = {}
            temp['id'] = member
            co_host_list.append(temp)

        return co_host_list

    def get_related_cohorts(self, cohort_ids):
        filter_dict = {
            'id__in': cohort_ids
        }
        cohort_list = ModelUtilities.get_model_filter(Cohort, filter_dict)
        cohorts = []

        for cohort in cohort_list:
            cohort_context = {
                'id': cohort.id,
                'name': cohort.name,
                'community': cohort.community_id
            }
            cohorts.append(cohort_context)

        return cohorts

    def get_images(self, card):

        images = []

        if card.has_files or \
                card.attachment_count > 0:
            files = Card_Attachment.objects.filter(collabcard=card, type="image")

            for file in files:
                img = {'image_url': file.file_url, 'index': file.index}

                if file.dimensions:
                    img['dimensions'] = json.loads(file.dimensions)

                if file.height:
                    img['height'] = file.height

                if file.width:
                    img['width'] = file.width

                if file.thumbnail_url:
                    img['thumbnail_url'] = file.thumbnail_url

                images.append(img)

        return images

    def get_pdf(self, card):

        pdf = []

        if card.has_files or \
                card.attachment_count > 0 or \
                card.pdf_count > 0:
            files = Card_Attachment.objects.filter(collabcard=card, type="pdf")

            for file in files:
                temp = {'pdf_file': file.file_url, 'index': file.index}
                pdf.append(temp)

        return pdf

    def get_audios(self, card):

        audios = []

        if card.has_files or \
                card.attachment_count > 0:
            files = Card_Attachment.objects.filter(collabcard=card, type="audio")

            for file in files:
                audio_file = {'audio_url': file.file_url, 'index': file.index}
                audios.append(audio_file)

        return audios

    def get_videos(self, card):

        videos = []

        if card.has_files or \
                card.attachment_count > 0:
            files = Card_Attachment.objects.filter(collabcard=card, type="video")
            for file in files:
                video_file = {'video_url': file.file_url, 'index': file.index}

                if file.height:
                    video_file['height'] = file.height

                if file.width:
                    video_file['width'] = file.width

                if file.thumbnail_url:
                    video_file['thumbnail_url'] = file.thumbnail_url

                videos.append(video_file)

        return videos

    def get_attachments(self, card):
        attachments = []

        if card.has_files or \
                card.attachment_count > 0 or \
                card.pdf_count > 0:
            files = Card_Attachment.objects.filter(collabcard=card)

            for file in files:
                attachment_file = {'url': file.file_url, 'index': file.index, 'type': file.type}

                if file.height:
                    attachment_file['height'] = file.height

                if file.width:
                    attachment_file['width'] = file.width

                if file.thumbnail_url:
                    attachment_file['thumbnail_url'] = file.thumbnail_url

                attachments.append(attachment_file)

        return attachments

    def get_attendees_ids(self, card):

        if card.type == card_types.CARD_EVENT or card.type == card_types.CARD_PUBLIC_EVENT:
            event_attendees_dict = CacheImpl.get_cache(EVENT_ATTENDEES_CHATROOM % str(card.id))

            if event_attendees_dict:
                event_attendees_list = event_attendees_dict.get('event_attendees_list')

                return event_attendees_list

            event_attendees_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                                        {'card': card,
                                                                         'attending_status': True}
                                                                        ).values_list('user', flat=True).
                                        order_by('created_at', 'id'))

            update_event_attendees.delay({'chatroom_id': card.id,
                                    'event_attendees_list': event_attendees_list})

            return event_attendees_list

    def get_instructors(self, card):

        if card.type == card_types.CARD_EVENT or card.type == card_types.CARD_PUBLIC_EVENT:

            instructors_dict = CacheImpl.get_cache(EVENT_INSTRUCTORS_CHATROOM % str(card.id))

            if instructors_dict:

                instructors_list = instructors_dict.get('instructors_list', [])

            else:

                instructor_filter = ModelUtilities.get_model_filter(EventInstructor,
                                                                    {'card': card}).order_by('id')
                instructors_list = []

                for data in instructor_filter:
                    instructors_list.append(ModelUtilities.serialize_instance(data))

                update_event_instructors_in_cache.delay({'chatroom_id': card.id,
                                                         'instructors_list': instructors_list})

            return instructors_list

    def get_highlights(self, card):

        if card.type == card_types.CARD_EVENT or card.type == card_types.CARD_PUBLIC_EVENT:

            highlights_dict = CacheImpl.get_cache(EVENT_HIGHLIGHTS_CHATROOM % str(card.id))

            if highlights_dict:
                highlights_list = highlights_dict.get('highlights_list', [])

            else:

                highlights_filter = ModelUtilities.get_model_filter(EventHighlights,
                                                                    {'card': card}).order_by('id')
                highlights_list = []

                for data in highlights_filter:
                    highlights_list.append(ModelUtilities.serialize_instance(data))

                update_event_highlights_in_cache.delay({'chatroom_id': card.id,
                                                        'highlights_list': highlights_list})

            return highlights_list

    def get_testimonials(self, card):

        if card.type == card_types.CARD_EVENT or card.type == card_types.CARD_PUBLIC_EVENT:
            testimonial_dict = CacheImpl.get_cache(EVENT_MEMBERTESTIMONIALS_CHATROOM % str(card.id))

            if testimonial_dict:
                testimonials_list = testimonial_dict.get('testimonials_list', [])

            else:
                testimonial_filter = ModelUtilities.get_model_filter(EventMemberTestimonials,
                                                                     {'card': card}).order_by('id')
                testimonials_list = []

                for data in testimonial_filter:
                    testimonials_list.append(ModelUtilities.serialize_instance(data))

                update_event_member_testimonials_in_cache.delay({'chatroom_id': card.id,
                                                                 'testimonials_list': testimonials_list})

            return testimonials_list

    def get_faq(self, card):

        if card.type == card_types.CARD_EVENT or card.type == card_types.CARD_PUBLIC_EVENT:
            faq_dict = CacheImpl.get_cache(EVENT_FAQ_CHATROOM % str(card.id))

            if faq_dict:
                faqs_list = faq_dict.get('faqs_list', [])

            else:

                faq_filter = ModelUtilities.get_model_filter(EventFAQ,
                                                             {'card': card}).order_by('id')
                faqs_list = []

                for data in faq_filter:
                    faqs_list.append(ModelUtilities.serialize_instance(data))

                update_event_faq_in_cache.delay({'chatroom_id': card.id, 'faqs_list': faqs_list})

            return faqs_list

    def get_online_link(self, card):

        if card.online_link and not card.is_paid:

            return card.online_link

    def get_online_link_id(self, card):

        if card.online_link_id and not card.is_paid:
            return card.online_link_id

    def get_online_link_password(self, card):

        if card.online_link_password and not card.is_paid:
            return card.online_link_password

    def to_representation(self, card):
        data = super(GetChatroomInstanceSerializer, self).to_representation(card)

        fields = self._readable_fields

        for field in fields:

            if field.field_name == 'header':
                if not data['header']:
                    if len(data['title']) <= 30:
                        data['header'] = data['title'][:30]
                    else:
                        data['header'] = data['title'][:27] + "..."

            if field.field_name == "community" and data['community'] is not None:
                data['community_id'] = data['community']
                del data["community"]

            elif field.field_name == "card" and data['card'] is not None:
                data['chatroom_id'] = data['card']
                del data["card"]

            elif field.field_name == "og_tags" and data['og_tags'] is not None:
                if not card.og_tags == '':
                    data['og_tags'] = json.loads(data['og_tags'])
                else:
                    del data['og_tags']

            elif field.field_name == "end_date" and data["end_date"] <= 0:
                del data['end_date']

            elif field.field_name == "has_been_named":
                if int(self.member_id) == data['user']:
                    data['has_been_named'] = data['has_been_named']
                else:
                    del data['has_been_named']

            elif field.field_name == "internal_link" and data['internal_link'] is not None:

                try:
                    preview = get_preview_for_url(member_id=self.current_user_id,
                                                  preview_url=data['internal_link'])

                    if preview:
                        data['preview'] = preview

                except:
                    del data['preview']

                del data['internal_link']

            elif field.field_name == "multiple_select":
                if data['type'] != card_types.CARD_POLL:
                    del data["multiple_select"]

            elif field.field_name == "multiple_select_no" and data['multiple_select_no'] is not None:
                if data['type'] != card_types.CARD_POLL:
                    del data["multiple_select_no"]

            elif field.field_name == "multiple_select_state" and data['multiple_select_state'] is not None:
                if data['type'] != card_types.CARD_POLL:
                    del data["multiple_select_state"]

            elif field.field_name == "allow_add_option":
                if data['type'] != card_types.CARD_POLL:
                    del data["allow_add_option"]

            elif field.field_name == "poll_type" and data['poll_type'] is not None:
                if data['type'] != card_types.CARD_POLL:
                    del data["poll_type"]

            elif field.field_name == "expiry_time":
                if data['type'] == card_types.CARD_POLL:
                    data["expiry_time"] = card.end_date
                else:
                    del data['expiry_time']

            elif field.field_name == "polls":
                if data['type'] != card_types.CARD_POLL:
                    del data['polls']

            elif field.field_name == "poll_type_text":
                if data['type'] != card_types.CARD_POLL:
                    del data["poll_type_text"]

            elif field.field_name == "submit_type_text":
                if data['type'] != card_types.CARD_POLL:
                    del data["submit_type_text"]

            elif field.field_name == "location" and data['location'] is not None:
                if data['type'] not in [card_types.CARD_POLL, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
                    del data["location"]

            elif field.field_name == "location_lat" and data['location_lat'] is not None:
                if data['type'] not in [card_types.CARD_POLL, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
                    del data["location_lat"]

            elif field.field_name == "location_long" and data['location_long'] is not None:
                if data['type'] not in [card_types.CARD_POLL, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
                    del data["location_long"]

            elif field.field_name == "start_date" and data['start_date'] is not None:
                if data['type'] not in [card_types.CARD_POLL, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
                    del data["start_date"]

            elif field.field_name == "about" and data['about'] is not None:
                if data['type'] not in [card_types.CARD_POLL, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
                    del data["about"]

            elif field.field_name == "online_link" and data['online_link'] is not None:
                if data['type'] not in [card_types.CARD_POLL, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
                    del data["online_link"]

            elif field.field_name == 'co_hosts' and data['co_hosts'] is not None:
                if data['type'] not in [card_types.CARD_POLL, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
                    del data["co_hosts"]
                else:
                    co_host_list = json.loads(data['co_hosts'])
                    data['co_hosts_id'] = self.get_co_hosts(co_host_list)
                    del data['co_hosts']

            elif field.field_name == 'cohort_ids' and data['cohort_ids'] is not None:
                cohort_ids = json.loads(data['cohort_ids'])
                data['cohorts'] = self.get_related_cohorts(cohort_ids)
                del data['cohort_ids']

            elif field.field_name == "answer_text":
                if data['type'] == card_types.CARD_POLL:
                    data['answer_text'] = get_answer_text_for_poll(card, self.current_user_id)
                else:
                    del data['answer_text']

            elif field.field_name == "secret_chatroom_participants" and data[
                'secret_chatroom_participants'] is not None:
                data['secret_chatroom_participants'] = json.loads(data['secret_chatroom_participants'])

            elif data[field.field_name] is None:
                del data[field.field_name]

        del data['user']

        if self.state_instance is None:
            collabcard_state = collabcardState.objects.filter(card=card, user=self.member_id)

            if collabcard_state:
                self.state_instance = collabcard_state[0]

        if self.state_instance is not None:
            status_dict = CardStateSerializer(self.state_instance).data
            expiry_time = status_dict['expiry_time']
            status_dict['chatroom_expiry_time'] = expiry_time
            status_dict['active'] = False
            if not expiry_time or expiry_time >= int(time.time()):
                status_dict['active'] = True

            data['state'] = status_dict['state']
            data['mute_status'] = status_dict['mute_status']
            data['follow_status'] = status_dict['follow_status']
            data['is_guest'] = status_dict['is_guest']
            data['is_tagged'] = status_dict['is_tagged']
            data['chatroom_expiry_time'] = status_dict['chatroom_expiry_time']
            data['attended'] = status_dict.get('attended', False)

            if status_dict['last_seen_conversation']:
                data['last_seen_conversation'] = status_dict['last_seen_conversation']

            self.state_instance = None  # making None for the next object

        return data


class CardStateSerializer(serializers.ModelSerializer):
    chatroom_expiry_time = serializers.SerializerMethodField()

    class Meta:
        model = collabcardState
        fields = ('state', 'mute_status', 'follow_status', 'is_guest', 'attending_status',
                  'remove', 'expiry_time', 'is_tagged', 'chatroom_expiry_time', 'last_seen_conversation', 'attended')

    def get_chatroom_expiry_time(self, obj):
        return obj.expiry_time


class membersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Members
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(membersSerializer, self).__init__(*args, **kwargs)
        self.member_instance = kwargs.get('member_instance')
        self.community_id = kwargs.get('community_id')
        self.current_user_id = kwargs.get('current_user_id', None)
        self.send_profile = kwargs.get('send_profile', None)
        self.is_promoter = kwargs.get('is_promoter', None)
        self.is_owner = kwargs.get('is_owner', None)
        self.all_members_api = kwargs.get('all_members_api', None)
        self.profile_detail_api = kwargs.get('profile_detail_api', None)
        self.user_admin_rights = kwargs.get('user_admin_rights', None)
        self.parents_list = json.loads(
            self.member_instance.parent_cm_list) if self.member_instance.parent_cm_list else []

    def to_representation(self, obj):
        data = super(membersSerializer, self).to_representation(obj)

        fields = self._readable_fields

        for field in fields:
            if field.field_name == "community" and data['community'] is not None:
                data['community_id'] = data['community']["id"]
                data['community_name'] = data['community']["name"]
                del data["community"]
            elif data[field.field_name] is None:
                del data[field.field_name]

        # data = OrderedDict([(key, data[key]) for key in data if data[key] is not None])
        return data

    def get_menu_for_members(self, current_user_id, item_member_id, community_id, current_user_is_promoter,
                             item_member_state,
                             current_user_is_owner=False, item_member_is_owner=False, current_user_admin_rights=None,
                             parents_list=None, profile_detail_api=False):
        """ function to get the menu for all members for all members api and profile detail api """
        #  x is current member , y is member whose profile is currently in iteration sequence
        # current_user_state, item_member_state,

        edit_title = {"title": "Edit title",
                      "route": f"route://edit_custom_title?community_id={community_id}&member_id={item_member_id}"}
        edit_permissions = {"title": "Edit permissions",
                            "route": f"route://edit_member_rights?community_id={community_id}&member_id={item_member_id}"}
        give_CM_rights = {"title": "Give community management rights",
                          "route": f"route://give_manager_rights?community_id={community_id}&member_id={item_member_id}"}
        edit_CM_rights = {"title": "Edit management rights",
                          "route": f"route://edit_manager_rights?community_id={community_id}&member_id={item_member_id}"}
        report_member = {"title": "Report member",
                         "route": f"route://report_member?community_id={community_id}&member_id={item_member_id}"}
        remove_from_community = {"title": "Remove from community",
                                 "route": f"route://remove_from_community?community_id={community_id}&member_id={item_member_id}"}
        block_member = {"title": "Block member",
                        "route": f"route://block_member?community_id={community_id}&member_id={item_member_id}"}

        if parents_list is None:
            parents_list = []

        if current_user_is_owner and int(current_user_id) == int(item_member_id):
            return [edit_title]
        if current_user_id and int(current_user_id) == int(item_member_id):
            return []
        elif not current_user_id:
            return []

        menu = []

        if current_user_is_owner and item_member_is_owner:
            menu = [edit_title]
        elif current_user_is_owner and item_member_state == member_states.ADMIN:
            menu = [edit_CM_rights, remove_from_community]

        elif current_user_is_owner and item_member_state == member_states.MEMBER:
            menu = [edit_permissions, give_CM_rights, remove_from_community]

        elif current_user_is_promoter and item_member_state == member_states.ADMIN:

            is_child = current_user_id in parents_list

            if current_user_admin_rights:
                if current_user_admin_rights["approve"] and is_child:
                    menu.append(remove_from_community)

                if current_user_admin_rights["add_manager"] and is_child:
                    menu.append(edit_CM_rights)

            if profile_detail_api:
                menu.append(report_member)
                # if not item_member_is_owner:
                menu.append(block_member)

        elif current_user_is_promoter and item_member_state == member_states.MEMBER:
            if current_user_admin_rights:
                if current_user_admin_rights["approve"]:
                    menu.append(remove_from_community)

                if current_user_admin_rights["delete_room"] or current_user_admin_rights["approve"]:
                    menu.append(edit_permissions)

                if current_user_admin_rights["add_manager"]:
                    menu.append(give_CM_rights)

                if not current_user_admin_rights["approve"] and profile_detail_api:
                    menu.append(report_member)

                if profile_detail_api:
                    menu.append(block_member)

        else:
            if profile_detail_api:
                menu.append(report_member)
                # if not item_member_is_owner:
                menu.append(block_member)

        return menu


class formSerializer(serializers.ModelSerializer):
    class Meta:
        model = Members
        fields = '__all__'


class reportSerializer(serializers.ModelSerializer):
    # community = communitySerializer()
    # collabcard = chatroomSerializer()

    class Meta:
        model = Report
        fields = '__all__'
        depth = 1

    def to_representation(self, obj):
        data = super(reportSerializer, self).to_representation(obj)

        fields = self._readable_fields

        for field in fields:
            if field.field_name == "community" and data['community'] is not None:
                data['community_id'] = data['community']["id"]
                data['community_name'] = data['community']["name"]
                del data["community"]
            elif data[field.field_name] is None:
                del data[field.field_name]

        # data = OrderedDict([(key, data[key]) for key in data if data[key] is not None])
        return data


class memberCommunityProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Members
        fields = '__all__'
        depth = 1

    def __init__(self, *args, **kwargs):
        super(memberCommunityProfileSerializer, self).__init__(*args, **kwargs)
        self.member_ids = kwargs.get('member_ids')
        self.community_id = kwargs.get('community_id')
        self.current_user_id = kwargs.get('current_user_id', None)
        self.send_profile = kwargs.get('send_profile', None)
        self.remove = kwargs.get('remove', None)
        self.is_promoter = kwargs.get('is_promoter', None)
        self.is_owner = kwargs.get('is_owner', None)
        self.all_members_api = kwargs.get('all_members_api', None)
        self.profile_detail_api = kwargs.get('profile_detail_api', None)
        self.user_admin_rights = kwargs.get('user_admin_rights', None)


class CardAnswersDBSyncSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    deleted_by = serializers.SerializerMethodField()
    images = serializers.ListField(write_only=True)
    pdf = serializers.ListField(write_only=True)
    videos = serializers.ListField(write_only=True)
    audios = serializers.ListField(write_only=True)
    location = serializers.ListField(write_only=True)
    reply_conversation = serializers.IntegerField(write_only=True)
    preview = serializers.DictField(write_only=True)
    member_id = serializers.CharField(write_only=True)
    created_epoch = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    polls = serializers.SerializerMethodField()
    poll_type_text = serializers.SerializerMethodField()
    submit_type_text = serializers.SerializerMethodField()
    co_hosts_ids = serializers.SerializerMethodField()
    attendees_ids = serializers.SerializerMethodField()

    class Meta:
        model = card_answers
        fields = ("id", 'answer', 'card', 'user', 'created_at', 'community', 'state',
                  'og_tags', 'deleted_by', 'is_edited', 'reply', 'internal_link',
                  'has_files', 'date', 'images', 'pdf', 'audios', 'videos',
                  'attachment_count', 'attachments_uploaded', 'location', 'reply_conversation',
                  'preview', 'member_id', 'created_epoch', 'temporary_id', 'is_anonymous',
                  'allow_add_option', 'poll_type', 'expiry_time', 'multiple_select_state',
                  'multiple_select_no', 'polls', 'reactions', 'poll_type_text', 'submit_type_text',
                  'poll_answer_text', 'reply_chatroom_id', 'header', 'location',
                  'location_lat', 'location_long', 'start_time', 'end_time', 'co_hosts_ids',
                  'attendees_ids', 'has_event_recording', 'about_recording', 'recording_url_og_tags')

    def __init__(self, *args, **kwargs):
        super(CardAnswersDBSyncSerializer, self).__init__(*args, **kwargs)
        self.fetch_reply = self.context.get('fetch_reply', True)
        self.current_user_id = self.context.get('current_user_id', None)

    def get_reactions(self, obj):

        if obj.has_reactions:
            reactions = fetch_chatroom_or_conversation_reactions(conversation_id=obj.id)
        else:
            reactions = []

        return reactions

    def get_date(self, obj):
        return TimeUtilities.convert_epoch_time_in_date(obj.created_at)

    def get_deleted_by(self, obj):
        if obj.deleted_by_user is not None:
            return obj.deleted_by_user.id
        return None

    def get_created_epoch(self, obj):
        return int(obj.created_at)

    def get_poll_type_text(self, obj):

        if obj.state == conversation_states.CONVERSATION_POLL:
            return "Instant poll" if obj.poll_type == conversation_poll_types.INSTANT else "Deferred poll"

    def get_submit_type_text(self, obj):

        if obj.state == conversation_states.CONVERSATION_POLL:
            return "Secret voting" if obj.is_anonymous else "Public voting"

    def get_polls(self, obj):

        if obj.state == conversation_states.CONVERSATION_POLL:
            polls = []
            polls = get_conversation_poll({'conversation_instance': obj,
                                           'conversation_id': obj.id,
                                           'poll_type': obj.poll_type,
                                           'multiple_select_no': obj.multiple_select_no,
                                           'expiry_time': obj.expiry_time,
                                           'member_id': self.current_user_id})

            return polls

        return None

    def get_co_hosts_ids(self, obj):

        if obj.state == conversation_states.CONVERSATION_EVENT:
            co_hosts_ids = JsonUtilities.load_json_data(obj.co_hosts)

            if co_hosts_ids:
                return co_hosts_ids

    def get_attendees_ids(self, obj):

        if obj.state == conversation_states.CONVERSATION_EVENT:
            event_attendees_dict = CacheImpl.get_cache(EVENT_ATTENDEES_CONVERSATION % str(obj.id))

            if event_attendees_dict:
                event_attendees_list = event_attendees_dict.get('event_attendees_list')

                return event_attendees_list

            event_attendees_list = list(ModelUtilities.get_model_filter(conversationEventMembers,
                                                                        {'conversation': obj,
                                                                         'attending_status': True}
                                                                        ).values_list('user', flat=True).
                                        order_by('created_at')[:10])

            update_event_attendees_for_micro_event.delay({'conversation_id': obj.id,
                                                          'event_attendees_list': event_attendees_list})

            return event_attendees_list

    def to_representation(self, obj):
        data = super(CardAnswersDBSyncSerializer, self).to_representation(obj)

        fields = self._readable_fields

        for field in fields:

            if field.field_name == "community" and data['community'] is not None:
                data['community_id'] = data['community']
                del data["community"]

            elif field.field_name == "card" and data['card'] is not None:
                data['chatroom_id'] = data['card']
                del data["card"]

            elif field.field_name == "user" and data['user'] is not None:
                data['member_id'] = data['user']
                del data["user"]

            elif field.field_name == "created_at" and data['created_at'] is not None:
                data['created_at'] = TimeUtilities.convert_epoch_time_in_hh_mm(data['created_at'])

            elif field.field_name == "og_tags":
                if data['og_tags'] is not None:
                    data['og_tags'] = json.loads(data['og_tags'])
                else:
                    del data['og_tags']

            elif (field.field_name == "attachment_count" and
                     data['attachment_count'] > 0):
                answer_files = get_answer_files(data['id'])
                data['images'] = answer_files['image']
                data['pdf'] = answer_files['pdf']
                data['videos'] = answer_files['videos']
                data['audios'] = answer_files['audios']
                data['attachments'] = answer_files['attachments']
                if 'location' in answer_files:
                    data['location'] = answer_files['location']

            elif field.field_name == "reply" and data['reply'] is not None and self.fetch_reply:
                data['reply_conversation'] = data['reply']
                del data['reply']

            elif field.field_name == "internal_link" and data['internal_link'] is not None:
                try:
                    preview = get_preview_for_url(member_id=self.current_user_id,
                                                  preview_url=data['internal_link'],
                                                  )
                    if preview:
                        data['preview'] = preview
                except:
                    data['preview'] = None
                del data['internal_link']

            elif data[field.field_name] is None:
                del data[field.field_name]

        return data


class UserinfoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Userinfo
        fields = ('id', 'name', 'image_url')

    def get_image_url(self, userinfo):
        return userinfo.image_link

    def to_representation(self, userinfo):
        data = super(UserinfoSerializer, self).to_representation(userinfo)

        fields = self._readable_fields

        for field in fields:
            if field.field_name == 'id':
                data['id'] = userinfo.user_id.id

        return data


class MessageReactionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReactions
        fields = "__all__"


class ChatroomAttachmentsSerializer(serializers.ModelSerializer):
    url = serializers.ReadOnlyField(source='file_url')

    class Meta:
        model = Card_Attachment
        fields = ('url', 'thumbnail_url', 'type', 'index', 'height', 'width')

    def to_representation(self, obj):
        data = super(ChatroomAttachmentsSerializer, self).to_representation(obj)

        fields = self._readable_fields

        for field in fields:
            if data[field.field_name] is None:
                del data[field.field_name]

        return data


class ConversationAttachmentsSerializer(serializers.ModelSerializer):
    url = serializers.ReadOnlyField(source='file_url')

    class Meta:
        model = Card_Attachment
        fields = ('url', 'thumbnail_url', 'type', 'index', 'height', 'width')

    def to_representation(self, obj):
        data = super(ConversationAttachmentsSerializer, self).to_representation(obj)

        fields = self._readable_fields

        for field in fields:
            if data[field.field_name] is None:
                del data[field.field_name]

        return data


class EventRecordingsAttachmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRecordingsAttachments
        fields = '__all__'
