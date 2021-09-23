import json

from django.db.models import Q
from django.contrib.auth.models import User

from collabmates_api.chatroom_member.chatroom_member_manager import ChatroomMemberManager
from utility.cache_keys import EVENT_INSTRUCTORS_CHATROOM, EVENT_HIGHLIGHTS_CHATROOM, EVENT_FAQ_CHATROOM, \
    EVENT_MEMBERTESTIMONIALS_CHATROOM, EVENT_ATTENDEES_CHATROOM
from utility.celery_tasks import update_chatroom_conversation_count_in_cache, \
    update_chatroom_conversation_creators_in_cache, update_event_instructors_in_cache, update_event_highlights_in_cache, \
    update_event_faq_in_cache, update_event_member_testimonials_in_cache, update_event_attendees
from collabmates_api.chatroom_member.constants import ACTIVE_USER_LIMIT
from collabmates_api.conversation.reactions import fetch_chatroom_or_conversation_reactions
from collabmates_api.member_community import member_community_impl
from collabmates_api.raw_queries import get_chatroom_count_based_on_community_list, \
    get_count_of_community_members_based_on_community_list, fetch_chatroom_polls, fetch_member_poll_votes
from collabmates_api.serializers import conversationSerializer, get_collabcard_files, get_preview_for_url, \
    get_members_profile
from utility.constants import CONVERSATIONS_COUNT_CACHE_KEY, CONVERSATIONS_DISTINCT_CREATORS_KEY
from external_services.caching.cache_impl import CacheImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.number_utilities import NumberUtilities
from utility.states import card_types, poll_types, conversation_states
from utility.time_utilities import TimeUtilities
from utility.utils import get_time_text_for_my_chatrooms
from togther.models import collabcardState, Members, ModelUtilities, MemberPollVotes, card_answers, EventInstructor, \
    EventHighlights, EventMemberTestimonials, EventFAQ, conversationEngage

error_logger = LoggingWrapper.get_instance()


class ChatroomMemberImpl(ChatroomMemberManager):
    member_id = None
    chatroom_id = None
    device_id = None

    member_community_instance = None

    def __init__(self, member_id: str, chatroom_id: str = None,
                 device_id: str = None):
        self.member_id = member_id
        self.chatroom_id = chatroom_id
        self.device_id = device_id

    def get_member_id(self) -> str:
        return self.member_id

    def set_member_id(self, member_id: str) -> None:
        self.member_id = member_id

    def get_chatroom_id(self) -> str:
        return self.member_id

    def set_chatroom_id(self, chatroom_id: str) -> None:
        self.member_id = chatroom_id

    def get_device_id(self):
        return self.device_id

    def set_device_id(self, device_id):
        self.device_id = device_id

    def get_member_community_impl_instance(self, community_instance):

        if self.member_community_instance is None:
            member_community_impl_instance = member_community_impl.MemberCommunityImpl(
                member_id=self.get_member_id(), community_id=community_instance.id)
            self.member_community_instance = member_community_impl_instance

        return self.member_community_instance

    @staticmethod
    def fetch_poll_id_list(chatroom_list):
        poll_list = []

        for data in chatroom_list:
            card_instance = data.card

            if card_instance.type == card_types.CARD_POLL:
                poll_list.append(card_instance.id)

        return poll_list

    @staticmethod
    def process_poll_list(poll_list):

        poll_data = {}
        poll_votes = {}

        if poll_list:
            poll_data = fetch_chatroom_polls(poll_list)
            poll_votes = fetch_member_poll_votes(poll_list)

        return poll_data, poll_votes

    @staticmethod
    def process_poll(poll_data, chatroom_id, poll_votes, is_multi, member_id):

        chatroom_poll_data = poll_data.get(chatroom_id)
        chatroom_votes = poll_votes.get(chatroom_id)

        if not chatroom_poll_data:
            chatroom_poll_data = []

        if not chatroom_votes:
            chatroom_votes = []

        total_votes = len(chatroom_votes)
        polls = []

        for data in chatroom_poll_data:

            poll_id = data['id']
            member_set = set()
            count = 0
            total_member_set = set()
            temp = {}
            temp['id'] = poll_id
            temp['text'] = data['text']
            temp['is_selected'] = False
            temp['member'] = data['member']
            if total_votes == 0:
                temp['no_votes'] = 0
                temp['percentage'] = 0
                polls.append(temp)
                continue
            for member in chatroom_votes:

                if member['user_id'] not in total_member_set:
                    total_member_set.add(member['user_id'])

                if member['poll_id'] == poll_id:
                    count = count + 1
                    if member['user_id'] not in member_set:
                        if member['user_id'] == int(member_id):
                            temp['is_selected'] = True
                        member_set.add(member['user_id'])

            if is_multi:
                count = len(member_set)
                total_votes = len(total_member_set)

            temp['no_votes'] = count

            temp['percentage'] = int((count / total_votes) * 100)

            polls.append(temp)

        return polls

    def compute_co_host_of_chatroom_events(self, co_host_list, community_instance) -> []:

        co_hosts = []
        member_dict = self.get_member_community_impl_instance(community_instance).fetch_members_based_on_user_list(
            co_host_list,
            community_instance, send_expired_info=False)

        for data in co_host_list:
            user_id = NumberUtilities.get_integer_from_string(data)

            if user_id in member_dict:
                co_hosts.append(member_dict[user_id])
            else:
                user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

                if not user_instance:
                    continue

                removed_context = self.get_member_community_impl_instance(
                    community_instance).compute_removed_user_context(user_instance,
                                                                     community_instance)
                co_hosts.append(removed_context)

        return co_hosts

    def compute_event_attendees_of_chatroom(self, card_instance, community_instance):

        event_attendees_dict = CacheImpl.get_cache(EVENT_ATTENDEES_CHATROOM % str(card_instance.id))

        if event_attendees_dict:
            event_attendees_list = event_attendees_dict.get('event_attendees_list')
            attendees_list = self.process_event_attendees_list(event_attendees_list, community_instance)

            return attendees_list

        event_attendees_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                                           {'card': card_instance,
                                                                            'attending_status': True}
                                                                           ).values_list('user', flat=True).
                                           order_by('created_at', 'id'))

        attendees_list = self.process_event_attendees_list(event_attendees_list, community_instance)
        update_event_attendees.delay({'chatroom_id': card_instance.id,
                                'event_attendees_list': event_attendees_list})
        return attendees_list

    def process_event_attendees_list(self, event_attendees_list, community_instance):

        attendees_list = []
        member_dict = self.get_member_community_impl_instance(community_instance).fetch_members_based_on_user_list(
            event_attendees_list,
            community_instance, send_expired_info=False)

        for data in event_attendees_list:
            user_id = NumberUtilities.get_integer_from_string(data)

            if user_id in member_dict:
                attendees_list.append(member_dict[user_id])
            else:
                user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

                if not user_instance:
                    continue

                removed_context = self.get_member_community_impl_instance(
                    community_instance).compute_removed_user_context(user_instance,
                                                                     community_instance)
                attendees_list.append(removed_context)

        return attendees_list

    def create_chatroom_preview(self, card_instance):

        preview = {}

        if card_instance.internal_link:
            try:
                preview = get_preview_for_url(self.get_member_id(), card_instance.internal_link,
                                              community_instance=card_instance.preview_community,
                                              chatroom_instance=card_instance.preview_chatroom,
                                              send_preview_text=False)
                if preview is None:
                    return {}

            except Exception as e:
                error_logger.error(e.args)

        return preview

    @staticmethod
    def compute_total_response_count(card_instance):

        key = CONVERSATIONS_COUNT_CACHE_KEY % str(card_instance.id)

        conversation_count = CacheImpl.get_cache(key)

        if conversation_count:
            return conversation_count['total_responses_count']
        else:
            conversations_count = card_answers.objects.filter(card=card_instance.id,
                                                              state=conversation_states.ANSWER).filter(
                Q(attachment_count=0)
                | Q(
                    attachments_uploaded=True)).count()
            update_chatroom_conversation_count_in_cache({'chatroom_id': card_instance.id,
                                                         'total_responses_count': conversations_count})

            return conversations_count

    @staticmethod
    def compute_user_id_list_of_chatroom_creators(chatroom_list) -> []:

        user_list = []
        user_set = set()

        for data in chatroom_list:
            user_id = data.card.user_id

            if user_id not in user_set:
                user_list.append(user_id)
                user_set.add(user_id)

        return user_list

    @staticmethod
    def compute_user_id_list_of_conversation_creators(card_instance) -> []:

        conversation_creator_list = []

        key = CONVERSATIONS_DISTINCT_CREATORS_KEY % str(card_instance.id)
        conversation_creator_dict = CacheImpl.get_cache(key)

        if conversation_creator_dict:
            conversation_creator_list = conversation_creator_dict['conversation_creator_list']

        else:

            conversation_filter = card_answers.objects \
                                      .filter(card=card_instance, state=conversation_states.ANSWER) \
                                      .filter(Q(attachment_count=0) |
                                              Q(attachments_uploaded=True)) \
                                      .distinct('user') \
                                      .order_by('user', '-id')[:5]

            for data in conversation_filter:
                user_id = data.user_id
                conversation_creator_list.append(user_id)

            update_chatroom_conversation_creators_in_cache({'chatroom_id': card_instance.id,
                                                            'conversation_creator_list': conversation_creator_list})

        return conversation_creator_list

    def create_last_response_members_images(self, card_instance, community_instance):

        conversation_members = []

        user_list = self.compute_user_id_list_of_conversation_creators(card_instance)
        member_dict = self.get_member_community_impl_instance(community_instance).fetch_members_based_on_user_list(
            user_list, community_instance, send_expired_info=False)

        for user_id in user_list:

            member_data = {}

            member = member_dict.get(user_id)

            if member:
                member_data = member
                member_data['chatroom_id'] = card_instance.id

            else:
                user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

                if not user_instance:
                    continue

                userinfo_instance = user_instance.userinfo

                if user_instance:
                    member_dict = {
                        'id': user_instance.id,
                        'name': userinfo_instance.name,
                        'image_url': userinfo_instance.image_link
                    }

            if not member_data:
                continue

            conversation_members.append(member_data)

        return conversation_members

    def fill_event_context_for_response(self, chatroom_context, card_instance, community_instance):

        co_host_list = chatroom_context.get('co_hosts') if chatroom_context.get('co_hosts') else []
        co_hosts = self.compute_co_host_of_chatroom_events(co_host_list, community_instance)

        if co_hosts:
            chatroom_context['co_hosts'] = co_hosts

        chatroom_context['instructors'] = ChatroomMemberHelper.fetch_event_instructors(card_instance)
        chatroom_context['highlights'] = ChatroomMemberHelper.fetch_event_highlights(card_instance)
        chatroom_context['testimonials'] = ChatroomMemberHelper.fetch_member_testimonials(card_instance)
        chatroom_context['faq'] = ChatroomMemberHelper.fetch_event_FAQ(card_instance)

        event_attendees = self.compute_event_attendees_of_chatroom(card_instance, community_instance)

        if event_attendees:
            chatroom_context['attendees'] = event_attendees

    def process_chatroom(self, card_instance, state_instance, community_instance, poll_data,
                         poll_votes) -> {}:

        chatroom_context = ChatroomMemberHelper.serialize_chatroom(card_instance, return_topic=True)

        if card_instance.has_reactions:
            reactions = fetch_chatroom_or_conversation_reactions(chatroom_id=chatroom_context['id'])
        else:
            reactions = []

        chatroom_context['reactions'] = reactions

        chatroom_context['community_name'] = community_instance.name

        if NumberUtilities.get_integer_from_string(self.get_member_id()) == card_instance.user_id:
            chatroom_context['has_been_named'] = card_instance.has_been_named
            chatroom_context['member_id'] = card_instance.user_id

        state_context = ChatroomMemberHelper.serialize_chatroom_user_actions(state_instance)

        if card_instance.attachment_count > 0:
            chatroom_files = ChatroomMemberHelper.fetch_chatroom_files(card_instance)
            chatroom_context.update(chatroom_files)

        if card_instance.type == card_types.CARD_POLL:
            poll_serializer = ChatroomMemberHelper.serialize_poll_chatroom(card_instance, self.get_member_id())
            polls = self.process_poll(poll_data, card_instance.id, poll_votes,
                                      poll_serializer.get('multiple_select_no'),
                                      self.get_member_id())

            if polls:
                poll_serializer['polls'] = polls

            chatroom_context.update(poll_serializer)

        if card_instance.type == card_types.CARD_EVENT or card_instance.type == card_types.CARD_PUBLIC_EVENT:
            self.fill_event_context_for_response(chatroom_context, card_instance, community_instance)

        chatroom_context.update(state_context)

        preview = self.create_chatroom_preview(card_instance)

        if preview:
            chatroom_context['preview'] = preview

        chatroom_context['total_response_count'] = self.compute_total_response_count(card_instance)

        if chatroom_context['total_response_count']:
            chatroom_context['last_response_members'] = self.create_last_response_members_images(card_instance,
                                                                                                 community_instance)

        return chatroom_context

    def process_chatroom_list(self, chatroom_list, community_instance) -> []:

        chatroom_context_list = []
        user_list = self.compute_user_id_list_of_chatroom_creators(chatroom_list)
        member_dict = self.get_member_community_impl_instance(community_instance).fetch_members_based_on_user_list(
            user_list, community_instance)
        poll_list = self.fetch_poll_id_list(chatroom_list)
        poll_data, poll_votes = self.process_poll_list(poll_list)

        removed_member_dict = {}

        for data in chatroom_list:
            card_instance = data.card
            state_instance = data
            card_creator_id = card_instance.user_id

            current_user_id = NumberUtilities.get_integer_from_string(self.get_member_id())

            if ChatroomMemberHelper.has_attachments_uploaded(card_instance, current_user_id, device_id=self.device_id):
                continue

            chatroom_context = self.process_chatroom(card_instance, state_instance, community_instance
                                                     , poll_data, poll_votes)

            if member_dict.get(card_creator_id):
                chatroom_context['member'] = member_dict[card_creator_id]

            else:

                if card_creator_id in removed_member_dict:
                    chatroom_context['member'] = removed_member_dict.get(card_creator_id)
                else:
                    chatroom_context['member'] = self.get_member_community_impl_instance(
                        community_instance).compute_removed_user_context(card_instance.user,
                                                                         community_instance)
                    removed_member_dict[card_creator_id] = chatroom_context['member']

            chatroom_context_list.append(chatroom_context)

        return chatroom_context_list

    def process_event_chatroom_list(self, chatroom_list):

        """function to process event chatroom list for event module"""

        chatroom_context_list = []

        for data in chatroom_list:
            card_instance = data.card
            state_instance = data
            card_creator_id = card_instance.user_id
            community_instance = data.community

            current_user_id = NumberUtilities.get_integer_from_string(self.get_member_id())

            if ChatroomMemberHelper.has_attachments_uploaded(card_instance, current_user_id, device_id=self.device_id):
                continue

            chatroom_context = self.process_chatroom(card_instance, state_instance, community_instance
                                                     , {}, {})
            member_dict = self.get_member_community_impl_instance(community_instance).fetch_members_based_on_user_list(
                [card_creator_id], community_instance)

            # Get Last conversation
            conversation_engage_filter = ModelUtilities.get_model_filter(conversationEngage,
                                                                         {"card": card_instance})

            if conversation_engage_filter:
                conversation_engage_instance = conversation_engage_filter[0]

                if conversation_engage_instance.last_conversation:
                    chatroom_context['last_conversation'] = conversationSerializer(
                        conversation_engage_instance.last_conversation)

                    chatroom_context['last_conversation_time'] = get_time_text_for_my_chatrooms(
                        conversation_engage_instance.updated_at)

            if member_dict.get(card_creator_id):
                chatroom_context['member'] = member_dict[card_creator_id]

            else:
                chatroom_context['member'] = self.get_member_community_impl_instance(
                    community_instance).compute_removed_user_context(card_instance.user,
                                                                     community_instance)

            chatroom_context_list.append(chatroom_context)

        return chatroom_context_list


class ChatroomMemberHelper:

    @staticmethod
    def get_card_header(card_instance) -> str:

        if card_instance.header:
            header = card_instance.header
        else:

            if len(card_instance.title) <= 30:
                header = card_instance.title[:30]
            else:
                header = card_instance.title[:27] + "..."

        return header

    @staticmethod
    def compute_card_poll_answer_text(card_instance, current_user_id) -> str:

        current_user_vote_exists = ModelUtilities.is_model_filter_exists(MemberPollVotes, {'card': card_instance,
                                                                                           'user__id': current_user_id})

        total_users = ModelUtilities.get_model_filter(MemberPollVotes,
                                                      {'card': card_instance}).values('user').distinct().count()

        poll_text = "Be the first one to vote"

        if current_user_vote_exists:

            if total_users > 1:

                if total_users == 2:
                    poll_text = f"You and 1 other voted"

                else:
                    poll_text = f"You and {total_users - 1} others voted"

            elif total_users == 1:
                poll_text = f"You voted on this poll"

        elif total_users > 0:

            if total_users == 1:
                poll_text = "1 member voted"

            else:
                poll_text = f"{total_users} members voted"

        return poll_text

    @staticmethod
    def serialize_poll_chatroom(card_instance, current_user_id):

        poll_context = {}
        poll_context["answer_text"] = ChatroomMemberHelper.compute_card_poll_answer_text(card_instance,
                                                                                         current_user_id)

        if card_instance.multiple_select:
            poll_context['multiple_select'] = card_instance.multiple_select

        if card_instance.multiple_select_no is not None:
            poll_context['multiple_select_no'] = card_instance.multiple_select_no
        if card_instance.multiple_select_state is not None:
            poll_context['multiple_select_state'] = card_instance.multiple_select_state

        poll_context['is_anonymous'] = card_instance.is_poll_anonymous
        poll_context['allow_add_option'] = card_instance.allow_add_option
        poll_context['poll_type'] = card_instance.poll_type
        poll_context[
            'poll_type_text'] = "Instant poll" if card_instance.poll_type == poll_types.POLL_TYPE_INSTANT else "Deferred poll"
        poll_context['submit_type_text'] = "Secret voting" if card_instance.is_poll_anonymous else "Public voting"

        poll_context['expiry_time'] = card_instance.end_date

        return poll_context

    @staticmethod
    def serialize_chatroom(card_instance, return_topic=False) -> dict:

        chatroom_context = {'id': card_instance.id,
                            'title': card_instance.title,
                            'community_id': card_instance.community_id,
                            'answer_text': card_instance.answer_text,
                            'share_link': card_instance.share_link,
                            'image_count': card_instance.image_count,
                            'pdf_count': card_instance.pdf_count,
                            'video_count': card_instance.video_count,
                            'audio_count': card_instance.audio_count,
                            'attachment_count': card_instance.attachment_count,
                            'attachments_uploaded': card_instance.attachments_uploaded,
                            'type': card_instance.type,
                            'date_time': card_instance.date_time,
                            'duration': card_instance.duration,
                            'is_pending': card_instance.is_pending,
                            'is_secret': card_instance.is_secret,
                            'answers_count': card_instance.answers_count,
                            'attending_count': card_instance.attending_count,
                            'polls_count': card_instance.polls_count,
                            'date_epoch': card_instance.date_epoch,
                            'header': ChatroomMemberHelper.get_card_header(card_instance),
                            'date': TimeUtilities.convert_epoch_time_in_date(card_instance.date_epoch),
                            'created_at': TimeUtilities.convert_epoch_time_in_hh_mm(card_instance.date_epoch),
                            'card_creation_time': TimeUtilities.convert_epoch_time_in_hh_mm_am_pm(
                                card_instance.date_epoch),
                            'auto_follow_done': card_instance.auto_follow_done,
                            'is_edited': card_instance.is_edited,
                            'is_paid': card_instance.is_paid,
                            'access': card_instance.access,
                            'online_link_enable_before': card_instance.online_link_enable_before,
                            'is_private': card_instance.is_private}

        if card_instance.is_secret:
            chatroom_context['secret_chatroom_participants'] = json.loads(card_instance.secret_chatroom_participants)

        if card_instance.og_tags:
            chatroom_context['og_tags'] = json.loads(card_instance.og_tags)

        if card_instance.location:
            chatroom_context['location'] = card_instance.location

        if card_instance.location_lat:
            chatroom_context['location_lat'] = card_instance.location_lat

        if card_instance.location_long:
            chatroom_context['location_long'] = card_instance.location_long

        if card_instance.start_date:
            chatroom_context['start_date'] = card_instance.start_date

        if card_instance.end_date:
            chatroom_context['end_date'] = card_instance.end_date

        if card_instance.about:
            chatroom_context['about'] = card_instance.about

        if card_instance.co_hosts:

            try:
                co_host_list = json.loads(card_instance.co_hosts)
            except Exception as e:
                co_host_list = []

            chatroom_context['co_hosts'] = co_host_list

        if card_instance.event_payment_link:
            chatroom_context['event_payment_link'] = card_instance.event_payment_link

        if card_instance.event_web_page:
            chatroom_context['event_web_page'] = card_instance.event_web_page

        if card_instance.webflow_item_id:
            chatroom_context['webflow_item_id'] = card_instance.webflow_item_id

        if return_topic and card_instance.topic is not None:
            conversation_serializer = conversationSerializer(card_instance.topic, fetch_reply=False)
            conversation_serializer['created_at'] = TimeUtilities.convert_epoch_time_in_hh_mm(
                conversation_serializer['created_at'])

            chatroom_context['topic'] = conversation_serializer

        if card_instance.chatroom_with_user:
            chatroom_member = get_members_profile([card_instance.chatroom_with_user_id], card_instance.community_id,
                                                  send_profile=False)

            chatroom_context['chatroom_with_user'] = chatroom_member[0]

        return chatroom_context

    @staticmethod
    def serialize_chatroom_user_actions(state_instance) -> {}:

        chatroom_user_actions = {}

        chatroom_user_actions['state'] = state_instance.state
        chatroom_user_actions['mute_status'] = state_instance.mute_status
        chatroom_user_actions['follow_status'] = state_instance.follow_status
        chatroom_user_actions['attending_status'] = state_instance.attending_status
        chatroom_user_actions['is_guest'] = state_instance.is_guest
        chatroom_user_actions['active'] = False
        chatroom_user_actions['is_tagged'] = state_instance.is_tagged
        chatroom_user_actions['attended'] = state_instance.attended
        expiry_time = state_instance.expiry_time

        if not expiry_time or expiry_time >= TimeUtilities.current_time_in_sec():
            chatroom_user_actions['active'] = True

        return chatroom_user_actions

    @staticmethod
    def has_attachments_uploaded(chatroom, user_id, device_id=''):
        if chatroom.attachment_count > 0 and \
                chatroom.attachments_uploaded is False and \
                (user_id != chatroom.user_id or
                 device_id != chatroom.device_id):
            return True

        return False

    @staticmethod
    def fetch_event_instructors(card_instance):

        instructors_dict = CacheImpl.get_cache(EVENT_INSTRUCTORS_CHATROOM % str(card_instance.id))

        if instructors_dict:

            instructors_list = instructors_dict.get('instructors_list', [])

        else:

            instructor_filter = ModelUtilities.get_model_filter(EventInstructor,
                                                                {'card': card_instance}).order_by('id')
            instructors_list = []

            for data in instructor_filter:
                instructors_list.append(ModelUtilities.serialize_instance(data))

            update_event_instructors_in_cache.delay({'chatroom_id': card_instance.id,
                                                     'instructors_list': instructors_list})

        return instructors_list

    @staticmethod
    def fetch_event_highlights(card_instance):

        highlights_dict = CacheImpl.get_cache(EVENT_HIGHLIGHTS_CHATROOM % str(card_instance.id))

        if highlights_dict:
            highlights_list = highlights_dict.get('highlights_list', [])

        else:

            highlights_filter = ModelUtilities.get_model_filter(EventHighlights,
                                                                {'card': card_instance}).order_by('id')
            highlights_list = []

            for data in highlights_filter:
                highlights_list.append(ModelUtilities.serialize_instance(data))

            update_event_highlights_in_cache.delay({'chatroom_id': card_instance.id,
                                              'highlights_list': highlights_list})

        return highlights_list

    @staticmethod
    def fetch_event_FAQ(card_instance):

        faq_dict = CacheImpl.get_cache(EVENT_FAQ_CHATROOM % str(card_instance.id))

        if faq_dict:
            faqs_list = faq_dict.get('faqs_list', [])

        else:

            faq_filter = ModelUtilities.get_model_filter(EventFAQ,
                                                         {'card': card_instance}).order_by('id')
            faqs_list = []

            for data in faq_filter:
                faqs_list.append(ModelUtilities.serialize_instance(data))

            update_event_faq_in_cache.delay({'chatroom_id': card_instance.id, 'faqs_list': faqs_list})

        return faqs_list

    @staticmethod
    def fetch_member_testimonials(card_instance):

        testimonial_dict = CacheImpl.get_cache(EVENT_MEMBERTESTIMONIALS_CHATROOM % str(card_instance.id))

        if testimonial_dict:
            testimonials_list = testimonial_dict.get('testimonials_list', [])

        else:
            testimonial_filter = ModelUtilities.get_model_filter(EventMemberTestimonials,
                                                                 {'card': card_instance}).order_by('id')
            testimonials_list = []

            for data in testimonial_filter:
                testimonials_list.append(ModelUtilities.serialize_instance(data))

            update_event_member_testimonials_in_cache.delay({'chatroom_id': card_instance.id,
                                                             'testimonials_list': testimonials_list})

        return testimonials_list

    @staticmethod
    def fetch_chatroom_files(card_instance) -> {}:

        chatroom_files = {}
        collabcard_files = get_collabcard_files(card_instance.id)
        chatroom_files['images'] = collabcard_files[0]
        chatroom_files['pdf'] = collabcard_files[1]
        chatroom_files['audios'] = collabcard_files[2]
        chatroom_files['videos'] = collabcard_files[3]
        chatroom_files['attachments'] = collabcard_files[4]

        return chatroom_files
