import json

from django.db.models import QuerySet
from collections import Iterable
from typing import Union
from rest_framework import status as status_codes
from django.contrib.auth.models import User
from django.db.models import Q, Max, When, Case
from celery import shared_task
from django.template.loader import get_template

from django.conf import settings

from external_services.calender.calendar_impl import CalendarImpl
from external_services.segment.segment_impl import SegmentImpl
from external_services.caching.cache_impl import CacheImpl
from internal_services.url_tags.uri_tags_impl import UriTagsImpl
from utility.api_client import ApiClient
from utility.mail_category_constants import EmailCategories, EmailSubCategories
from .constants import CHATROOM_EXPIRE_DURATION, INTRO_PLACEHOLDER_TEXT, INTRO_PLACEHOLDER_USER_ROUTE, \
    SUBSCRIPTION_VALIDATE_EVENT_ONLINE_LINK, EVENT_CARD_MAIL_DESCRIPTION, CHATROOM_URL, MAIL_EVENT_NOTIFICATION, \
    IMAGE_LINK_FOR_NO_EVENTS_FOUND, TITLE_FOR_NO_UPCOMING_EVENTS_FOUND, TITLE_FOR_NO_PAST_EVENTS_FOUND, \
    SUB_TITLE_FOR_MEMBER_VIEW_NO_UPCOMING_EVENTS_FOUND, SUB_TITLE_FOR_CM_VIEW_NO_UPCOMING_EVENTS_FOUND, \
    SUB_TITLE_FOR_NO_PAST_EVENTS_FOUND, FIRST_EVENT_CM_MAIL_SUBJECT, FIRST_EVENT_CM_MAIL_BUTTON_TEXT, \
    FIRST_EVENT_CM_REPLY_EMAIL, DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR, CHATROOM_URL_WITH_COMMUNITY_ID, \
    DM_CHATROOM_NAME, CHATROOM_NOTIFICATION_PAUSE_EVENT, CHATROOM_NOTIFICATION_SETTING_UPDATED_EVENT , \
    CHATROOM_USER_SETTINGS_MEMBER_CAN_MESSAGE, CHATROOM_USER_SETTINGS, \
    PauseChatroomNotificationTime
from ..chatroom.chatroom_manager import ChatroomManager
from ..chatroom_member.chatroom_member_impl import ChatroomMemberImpl
from .chatroom_view_helper import ChatroomViewHelper
from ..member_community.member_community_impl import MemberCommunityImpl, MemberCommunityHelper
from ..raw_queries import get_last_seen_event_chatroom_id_for_user, get_count_of_new_event_chatrooms_created_for_user, \
    get_last_seen_non_member_access_event_chatroom_id_for_community_managers, \
    get_last_seen_non_member_access_event_for_user, \
    get_count_for_new_non_member_access_event_chatroom_community_managers, \
    get_count_for_non_member_access_event_for_user_non_community_manager, check_user_has_member_can_initiate_dm_right, \
    get_all_chatrooms_of_community, get_chatroom_participants_count,\
    get_sorted_user_data_on_basis_of_activity_in_chatroom, get_members_based_on_user_list_query, \
    get_community_members_data_on_basis_of_name_search, get_last_conversation_id_corresponding_to_chatrooms_list, \
    get_chatroom_invites_for_user, get_all_chatrooms_of_community_old
from ..rest_api import EventRecordingsAttachmentsSerializer, GetChatroomInstanceSerializer, get_error_context, \
    CardAnswersDBSyncSerializer, GetChatroomInstanceSerializer, EventRecordingsURLSerializer, EventInstructorSerializer, \
    EventHighlightsSerializer, EventMemberTestimonialsSerializer, EventFAQSerializer, \
    ScheduledChatroomFollowSerializer, ChatroomInviteSerializer, UserChannelSettingsSerializer
from ..serializers import (get_preview_for_url, CommunitySerializer,
                           UserinfoSerializer, get_chatroom_instance, CollabcardSerializer)
from ..static_text import settings_for_purpose_chatroom, member_can_message, pin_chatroom, settings_for_chatroom, \
    delete_chatroom, accessible_without_subscription, settings_for_chatroom_with_revamp, make_it_secret, \
    auto_joined_by_all_members, manage_permissions, BLOCK_MEMBER_DM_CHATROOM_MESSAGE, UNBLOCK_MEMBER_DM_CHATROOM_MESSAGE
from ..sync.model_update import update_models_for_syncing_apis
from ..upload_attachments import get_user_image_based_on_community, save_chatroom_attachments
from ..user_moderation_rights import check_admin_delete_right
from ..utility import create_chatroom_revamp_version_check
from ..views import (adding_guest_in_chatroom, get_chatroom_actions, get_expiry_time_of_chatroom,
                     create_chatroom_state_instance, get_icons_states_of_chatroom_version_1,
                     save_the_latest_conversation, collabcard_follow_internal,
                     send_chatroom_creation_notifications_and_mails, update_seen_status_for_new_user_in_chatroom,
                     create_chatroom, get_latest_conversation_members, event_access, CommunitySerializerV1,
                     send_chatroom_creation_notification, get_community_creator, update_community_get_started)

from ..tasks import update_pending_chatroom_count_for_promoters, cm_onboarding_version_check
from ..notification import (get_tagged_members_list, send_notification_to_event_co_hosts, send_sync_notification,
                            send_pin_chatroom_notification, send_notification_for_new_secret_room_participant,
                            send_notification_for_removed_secret_room_participant,
                            send_notification_for_auto_follow_chatroom_for_all_members,
                            send_notification_for_event_update, send_notification_on_dm_request_initiation)

from ..search.sync import ElasticSearchSync

from collabmates_api.sdk.models import (SdkClient)
from togther.models import (Members, Collabcard, card_answers, Community,
                            collabcardState, conversationEngage, userMemberRights,
                            CollabcardPolls, draftChatroom, draftPolls, ModelUtilities, Userinfo, EventInstructor,
                            EventHighlights, EventMemberTestimonials, EventFAQ, EventNudge, userEmails, Card_Attachment,
                            EventRecordingsAttachments, ChatroomCohort, Cohort, CohortMember, removedMembers,
                            CommunityGetStarted, EventRecordingsURL, ChatroomSecretTypeConversion,
                            ScheduledChatroomFollow, CommunitySettings, ChatroomInvite, UserChannelSettings)

from external_services.logging.logging_wrapper import LoggingWrapper
from external_services.webflow.webflow_impl import WebflowImpl
from external_services.email.email_wrapper import MailWrapper, MailHelper
from utility.states import member_states, card_types, collabcard_states, SyncNotificationTypes, \
    SyncTypes, member_rights, conversation_states, email_states, event_webflow_update_types, get_started_types, \
    event_online_link_types, block_chatroom_states, chat_request_states, api_types, noti_states, \
    community_setting_types, chatroom_invite_status_types, chatroom_setting_states

from utility.utils import check_notification_flag
from utility.internal_link_preview_utilities import PreviewUtilities
from utility.celery_tasks import set_chatroom_state_for_all_members_on_card_creation, get_chatroom_user_images_for_web, \
    schedule_chatroom_unpinning_after_event_completion, update_last_unseen_in_engage, \
    update_preview_of_chatroom_in_cache, update_event_instructors_in_cache, update_event_highlights_in_cache, \
    update_event_member_testimonials_in_cache, update_event_faq_in_cache, update_event_attendees, \
    send_analytics_on_event_attend_link_click, schedule_event_analytics_on_event_start, \
    schedule_event_analytics_daily_7AM, send_event_analytics_on_event_creation, \
    schedule_event_analytics_on_event_before_n_hour, send_analytics_on_event_registered_to_attend, \
    create_event_in_webflow_service, update_event_in_webflow_service, reset_unread_message_count_in_cache, \
    fetch_conversations_unread, create_chatroom_cohort_instances, convert_chatroom_to_secret_chatroom, \
    convert_chatroom_to_open_chatroom, send_chatroom_creation_analytics_data, \
    send_participants_added_in_chatroom_analytics_data, send_chatroom_updated_analytics_data, \
    initial_message_dm_chatroom, update_community_pin_chatrooms_list_in_cache, toggle_user_chatroom_settings, \
    add_new_participants_to_secret_chatroom
from utility.firebase import update_last_answer_id
from utility.exception_utilities import (CustomException, InvalidSecretChatroomParticipantsException)
from utility.time_utilities import TimeUtilities
from utility.number_utilities import NumberUtilities
from collabmates_api.conversation import conversation_impl
from utility.validation_utilities import ValidationUtilities
from utility.auth_utilities import AuthUtilities
from utility.string_utilities import StringUtilities

from collabmates_api.branch import create_community_feed_url_for_cm_onboarding, create_single_event_branch_url

from collabmates_api.notifications.tasks import trigger_event_comms, send_app_notification_on_event_attachment, \
    send_app_notification_for_event_type, send_calender_invite_for_event_type, \
    send_email_notification_for_event_type, \
    reschedule_event_comms_notifications_on_event_update
from collabmates_api.notifications.constants import EVENT_TYPE, CALENDAR_INVITE_TYPE

from utility.response_utilities import ResponseUtilities
from utility.cache_keys import (CHATROOM_PARTICIPANTS_CREATED_CACHE_KEY, CHATROOM_TYPE_CONVERSION)
from utility.version_utilities import VersionUtilities

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()
subscription_url = settings.SUBSCRIPTION_SERVER_URL
url = settings.URL


class ChatroomImpl(ChatroomManager):
    member_id = None
    chatroom_id = None
    source_id = None
    aj = None
    device_id = None
    request_platform = None

    def __init__(self, member_id: str, chatroom_id: str = None, source_id: str = None, aj: str = None,
                 device_id: str = None, request_platform: str = None, version_code: int = 0, api_key: str = None, sdk_source: str = None):
        self.member_id = member_id
        self.chatroom_id = chatroom_id
        self.source_id = source_id
        self.aj = aj
        self.device_id = device_id
        self.request_platform = request_platform
        self.version_code = version_code
        self.api_key = api_key
        self.sdk_source = sdk_source

    def get_member_id(self) -> Union[str, int]:
        return self.member_id

    def set_member_id(self, member_id: Union[str, int]) -> None:
        self.member_id = member_id

    def get_chatroom_id(self):
        return self.chatroom_id

    def set_chatroom_id(self, chatroom_id):
        self.chatroom_id = chatroom_id

    def get_source_id(self):
        return self.source_id

    def set_source_id(self, source_id):
        self.source_id = source_id

    def get_aj(self):
        return self.aj

    def set_aj(self, aj):
        self.aj = aj

    def get_version_code(self):
        return self.version_code

    def get_request_platform(self):
        return self.request_platform
    
    def get_sdk_source(self):
        return self.sdk_source
    
    def get_device_id(self):
        return self.device_id

    def get_api_key(self):
        return self.api_key

    def _make_user_chatroom_guest(self, card_instance):
        guest_context = adding_guest_in_chatroom({}, card_instance, self.get_aj(), self.get_source_id(),
                                                 card_instance.community.id, current_user_id=self.get_member_id(),
                                                 version_code=self.get_version_code(),
                                                 platform_code=self.get_request_platform())
        return guest_context

    def _fetch_chatroom_internal_link(self, card_instance):

        if card_instance.internal_link:
            try:
                preview = get_preview_for_url(self.get_member_id(), card_instance.internal_link,
                                              community_instance=card_instance.preview_community,
                                              chatroom_instance=card_instance.preview_chatroom,
                                              send_preview_text=False)
                return preview

            except Exception as e:
                error_logger.error(e.args)

    def _fetch_total_response_count(self, card_instance):

        total_response_count = card_answers.objects.filter(card=card_instance,
                                                           state=conversation_states.ANSWER
                                                           ).filter(Q(attachment_count=0) |
                                                                    Q(attachments_uploaded=True)
                                                                    ).count()

        return total_response_count

    def _fetch_card_status(self, chatroom_data):

        card_status = {
            'state': chatroom_data['state'],
            'mute_status': chatroom_data['mute_status'],
            'follow_status': chatroom_data['follow_status'],
            'attending_status': chatroom_data['attending_status'],
            'type': chatroom_data['type'],
            'is_tagged': chatroom_data['is_tagged'],
        }

        return card_status

    def _fetch_chatroom_actions(self, card_instance, chatroom_data, api_type=api_types.Non_SDK):

        card_status = self._fetch_card_status(chatroom_data)
        is_promoter = False
        is_child = False
        parent_list = []
        member_instance = Members.objects.filter(member_id=self.get_member_id(),
                                                 community_id=card_instance.community).filter(
            Q(state=member_states.ADMIN))

        if member_instance.exists():
            is_promoter = True
            parent_cm_list = member_instance[0].parent_cm_list
            parent_list = json.loads(parent_cm_list) if parent_cm_list else []
            is_child = str(card_instance.user.id) in parent_list

        is_card_creator = False

        if self.get_member_id() and int(self.get_member_id()) == card_instance.user.id:
            is_card_creator = True
        # sending the chatroom actions
        chatroom_actions = get_chatroom_actions(card_status, creator=is_card_creator, card_instance=card_instance,
                                                promoter=is_promoter,
                                                current_user_instance=self.get_member_id(),
                                                community_instance=card_instance.community, is_child=is_child,
                                                parent_list=parent_list, platform_code=self.get_request_platform(),
                                                version_code=self.get_version_code(), api_type=api_type)
        return chatroom_actions

    def _save_external_seen_in_chatroom_state(self, card_instance, user_instance):

        chatroom_state = collabcardState.objects.filter(card=card_instance, user=self.get_member_id())
        # if the user is seeing this chatroom from external link or notification
        if not chatroom_state.exists() and user_instance:
            expire_at = get_expiry_time_of_chatroom()
            create_chatroom_state_instance(card_instance, user_instance, state=0, external_seen=True,
                                           expire_at=expire_at,
                                           function_called="get_chatroom_internal_version_1")
        elif user_instance:
            instance = chatroom_state[0]
            if not instance.external_seen:
                instance.external_seen = True
                instance.save()

        update_last_unseen_in_engage(user=user_instance, community=card_instance.community)

    def _fetch_icon_states_for_chatroom(self, card_instance, chatroom_data):

        icons = {}
        card_status = self._fetch_card_status(chatroom_data)
        icon_states = get_icons_states_of_chatroom_version_1(card_status, card_instance, self.get_member_id())
        icons['show_follow_telescope'] = icon_states['show_follow_telescope']
        icons['show_follow_auto_tag'] = icon_states['show_follow_auto_tag']

        return icons

    def _fetch_number_of_unread_messages(self, card_instance, user_instance):

        engage_filter = conversationEngage.objects.filter(card=card_instance, user=user_instance)
        unseen_count = 0
        if engage_filter.exists():
            unseen_count = engage_filter[0].unseen_count
        return unseen_count

    def _save_latest_conversation_on_screen(self, card_instance):

        save_the_latest_conversation(card_instance, self.get_member_id())

    def _fill_chatroom_basic_info(self, card_content, title, community, user, chatroom_type, auto_follow_done=False,
                                  include_members_later=False, chatroom_image_url=None):
        card_content['title'] = title
        card_content['community'] = community
        card_content['user'] = user
        card_content['type'] = chatroom_type
        card_content['auto_follow_done'] = auto_follow_done
        card_content['include_members_later'] = include_members_later
        card_content['chatroom_image_url'] = chatroom_image_url

        card_content['device_id'] = self.device_id
        card_content['platform'] = self.request_platform

    @staticmethod
    def fill_pinned_information(card_content):

        if card_content['type'] == card_types.CARD_PURPOSE or \
                card_content['type'] == card_types.CARD_MASTER_INTRO or \
                card_content['type'] == card_types.CARD_EVENT or \
                card_content['type'] == card_types.CARD_PUBLIC_EVENT:
            card_content['is_pinned'] = True
            card_content['pinning_time'] = TimeUtilities.current_time_in_milliseconds()

    def _fill_secret_room_details(self, card_content, req_body, community):
        card_content['is_secret'] = req_body.get("is_secret", False)

        if card_content['is_secret']:
            card_content['is_secret'] = True
            
            uuids = req_body.get("uuids", [])   

            if uuids:
                secret_chatroom_participants = ModelUtilities.get_valid_user_ids_from_uuids(uuids, community.id)

            else:
                secret_chatroom_participants = ModelUtilities.get_valid_member_ids(
                    req_body.get("secret_chatroom_participants", []), community_id=community.id)

            secret_chatroom_participants = ChatroomHelper.validate_secret_chatroom_participants_or_raise_exception(
                secret_chatroom_participants
            )

            if len(secret_chatroom_participants):
                member_id = NumberUtilities.get_integer_from_string(self.get_member_id())

                if member_id not in secret_chatroom_participants:
                    secret_chatroom_participants.append(member_id)

            card_content['secret_chatroom_participants'] = json.dumps(secret_chatroom_participants)

    def _fill_chatroom_attachment_count(self, card_content, req_body):
        card_content['image_count'] = req_body.get('image_count', 0)
        card_content['pdf_count'] = req_body.get('pdf_count', 0)
        card_content['video_count'] = req_body.get('video_count', 0)
        card_content['audio_count'] = req_body.get('audio_count', 0)
        card_content['has_files'] = req_body.get('has_files', False)

        card_content['attachment_count'] = req_body.get('attachment_count', 0)
        card_content['attachments_uploaded'] = False

        if card_content['attachment_count'] == 0 and card_content['pdf_count'] > 0:
            card_content['attachment_count'] = card_content['pdf_count']

        if card_content['attachment_count'] > 0 or card_content['pdf_count'] > 0:
            card_content['has_files'] = True
            req_body['has_files'] = True

    def _fill_chatroom_epoch_time(self, card_content, req_body) -> None:
        card_content['date_time'] = req_body.get('date_time', 0)
        card_content['duration'] = req_body.get('duration', 0)
        card_content['start_date'] = req_body.get('start_date', 0)

        if card_content['type'] == card_types.CARD_POLL:
            # for saving poll expiry time
            expiry_time = req_body.get('expiry_time', 0)
            if expiry_time > 0:
                # rounding off epoch time into exact minute
                # removing any extra seconds
                expiry_time = expiry_time // 1000
                expiry_time = expiry_time - (expiry_time % 60)

            card_content['end_date'] = expiry_time * 1000
        else:
            card_content['end_date'] = req_body.get('end_date', 0)

        card_content['date_epoch'] = TimeUtilities.current_time_in_sec()

    def _fill_chatroom_event_details(self, req_body, card_content):
        card_content['location'] = req_body.get('location', None)
        card_content['location_lat'] = req_body.get('location_lat', None)
        card_content['location_long'] = req_body.get('location_long', None)

        card_content['about'] = req_body.get('about', None)
        card_content['co_hosts'] = json.dumps(req_body['co_hosts']) if \
            ('co_hosts' in req_body and
             req_body['co_hosts'] is not None and
             isinstance(req_body['co_hosts'], Iterable)) else []
        card_content['online_link'] = req_body.get('online_link', None)

    def _fill_chatroom_poll_details(self, card_content, req_body):
        card_content['poll_type'] = req_body.get('poll_type', None)
        card_content['is_poll_anonymous'] = req_body.get('is_anonymous', None)
        card_content['allow_add_option'] = req_body.get('allow_add_option', None)
        card_content['multiple_select'] = req_body.get('multiple_select', False)
        card_content['multiple_select_no'] = req_body.get('multiple_select_no', None)
        card_content['multiple_select_state'] = req_body.get('multiple_select_state', None)

    def _fill_chatroom_header(self, card_content, req_body, chatroom_type, chatroom_name, decoded_chatroom_title=""):

        card_type = chatroom_type
        has_been_named = False
        if 'header' in req_body:
            card_content['header'] = req_body['header']
            has_been_named = True
            card_content['has_been_named'] = has_been_named

        else:

            decoded_title = decoded_chatroom_title

            if len(decoded_title) <= 30:
                card_content['header'] = decoded_title[:30]
            else:
                card_content['header'] = decoded_title[:27] + "..."

            if card_type == card_types.CARD_PURPOSE:
                card_content['header'] = chatroom_name
                card_content['has_been_named'] = True
            elif card_type == card_types.CARD_INTRO:
                card_content['header'] = chatroom_name
                card_content['has_been_named'] = True
            else:
                card_content['has_been_named'] = has_been_named

    def _add_og_tags(self, req_body, card_content):
        try:
            if 'share_link' in req_body:
                card_content['share_link'] = req_body['share_link']
                og_tags = UriTagsImpl(req_body['share_link']).get_tags_from_uri()
                card_content['og_tags'] = json.dumps(og_tags)

        except Exception as e:
            error_logger.error(f"link tag parsing failed for link={req_body['share_link']}, reason={e}")

    def _check_and_set_chatroom_pending_status(self, card_content, is_intro_card, user_has_auto_approve_right):
        if not user_has_auto_approve_right and not is_intro_card:
            card_content['is_pending'] = True

    def _create_chatroom_with_contents(self, card_content):
        chatroom_instance = Collabcard(**card_content)
        self._save_chatroom_instance(chatroom_instance)

        return chatroom_instance

    def _save_chatroom_instance(self, chatroom_instance):
        chatroom_instance.save()

    def _add_preview_from_internal_link(self, chatroom_instance, req_body) -> None:
        preview_utilities = PreviewUtilities()
        preview_utilities.set_preview_object(chatroom_instance, req_body, self.get_member_id())

        self._save_chatroom_instance(chatroom_instance)

    def _create_chatroom_polls(self, user_instance, chatroom_instance, req_body) -> None:
        polls = req_body.get('polls', None)

        if polls is None:
            return

        poll_instances = [
            CollabcardPolls(
                card=chatroom_instance,
                user=user_instance,
                text=poll['text'],
                sub_text=poll['sub_text'] if ('sub_text' in poll) else None,
                image_url=poll['image_url'] if ('image_url' in poll) else None
            )
            for poll in polls
        ]
        self._bulk_create_polls(poll_instances)

    def _bulk_create_polls(self, poll_instances) -> None:
        CollabcardPolls.objects.bulk_create(poll_instances)

    def _delete_draft(self, req_body) -> None:
        if 'draft_id' in req_body:
            conversationEngage.objects.filter(draft_id=req_body['draft_id']).delete()
            draftChatroom.objects.filter(id=req_body['draft_id']).delete()
            draftPolls.objects.filter(draft=req_body['draft_id']).delete()

    def _send_follow_notifications_to_tagged_members(self, tagged_members_list):
        for user_id in tagged_members_list:
            req_dict = ChatroomHelper.get_follow_user_dict(user_id, self.get_chatroom_id(),
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

    def _send_follow_notifications_to_secret_room_participants(self, participants_list):
        for user_id in participants_list:
            req_dict = ChatroomHelper.get_follow_user_dict(user_id, self.get_chatroom_id(),
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

    def _send_follow_notifications_to_event_co_hosts(self, req_body, chatroom_title, user_name):

        if 'co_hosts' not in req_body:
            return

        co_hosts = req_body.get('co_hosts', [])
        # making the co_host auto follow the card
        for user_id in co_hosts:
            req_dict = ChatroomHelper.get_follow_user_dict(user_id, self.get_chatroom_id(),
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

        send_notification_to_event_co_hosts.delay(co_hosts, self.get_chatroom_id(),
                                                  chatroom_title, user_name)

    def _send_chatroom_creation_notifications(self, user_instance, community_id, community_name,
                                              chatroom_instance, card_content, user_has_auto_approve_right,
                                              chatroom_type, is_intro_chatroom, set_default_unread_count=False):

        if chatroom_type == card_types.CARD_POLL and user_has_auto_approve_right:
            # sending polls notification
            send_chatroom_creation_notifications_and_mails(chatroom_instance, user_instance,
                                                           set_default_unread_count=set_default_unread_count)

        if user_has_auto_approve_right or is_intro_chatroom:
            # create relevant flags for first time conversation
            notification_list = [
                'mail_card_owner_inactivity'
            ]
            check_notification_flag(self.get_member_id(), notification_list,
                                    card_id=self.get_chatroom_id(), community_id=None)

        # send notification to new chatroom posted
        if card_content['has_been_named']:
            send_chatroom_creation_notifications_and_mails(chatroom_instance, user_instance,
                                                           set_default_unread_count=set_default_unread_count)

    def _send_additional_notifications_and_tasks_after_room_creation(self, user_instance, community_instance,
                                                                     chatroom_instance, req_body,
                                                                     is_intro_chatroom, user_has_auto_approve_right,
                                                                     community_id, chatroom_participants_list=None):
        create_intro = 'create_intro' in req_body
        if create_intro:
            update_seen_status_for_new_user_in_chatroom(community_instance, user_instance)
            # intro room notification
            send_chatroom_creation_notifications_and_mails(chatroom_instance, user_instance)

        if user_has_auto_approve_right or is_intro_chatroom or create_intro:
            # following the user created chatroom

            req_dict = ChatroomHelper.get_follow_user_dict(self.get_member_id(), self.get_chatroom_id(),
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

            # creating default conversation for chatroom creation
            create_chatroom(card_instance=chatroom_instance, user_instance=user_instance,
                            state=conversation_states.CONVERSATION_HEADER, current_user_id=self.get_member_id())

            # batch update for already existing users and saving their unseen count
            if not chatroom_instance.is_secret:
                ChatroomHelper.run_async_tasks_related_to_member_for_chatroom_posting.delay(
                    chatroom_instance.id, user_instance.id, community_instance.id,
                    chatroom_participants_list=chatroom_participants_list)
            else:
                update_last_answer_id(chatroom_instance.id, "")

        else:
            update_pending_chatroom_count_for_promoters.delay(community_id)

    def _latest_conversations_user_data(self):

        conversation_users_meta = get_chatroom_user_images_for_web(self.get_chatroom_id())
        conversation_users = get_latest_conversation_members(conversation_users_meta['last_conversation_member'],
                                                             conversation_users_meta['second_last_conversation_member'],
                                                             conversation_users_meta['last_conversation_user'],
                                                             conversation_users_meta['second_last_conversation_user'])

        return conversation_users

    @staticmethod
    def compute_tagging_list_of_community_members(community_instance, member_ids=[], search_name: str=None, 
                                                  page: int=None, page_size: int=None, order_by_name: bool=None, 
                                                  sdk_client_info_flag: bool=False): 
        member_list = MemberCommunityImpl.fetch_list_of_community_members(community_instance, member_ids)
        member_data = MemberCommunityImpl.fetch_members_based_on_user_list(member_list, community_instance, 
                                                                           member_name_search_string=search_name, 
                                                                           page=page, page_size=page_size, 
                                                                           order_by_name=order_by_name,
                                                                           sdk_client_info_flag=sdk_client_info_flag)
        tagging_list = MemberCommunityHelper.extract_member_tagging_data(member_data, sdk_client_info_flag=sdk_client_info_flag)

        return tagging_list

    @staticmethod
    def compute_tagging_list_of_guest_members(chatroom_instance):

        guest_user_list = list(collabcardState.objects.filter(is_guest=True,
                                                              card=chatroom_instance).values_list('user', flat=True))
        tag_list = []

        userinfo_filter = Userinfo.objects.filter(user_id__in=guest_user_list)

        for data in userinfo_filter:
            temp = dict()
            temp['id'] = data.user_id_id
            temp['name'] = data.name
            temp['image_url'] = data.image_link if data.image_link else ""
            temp['is_guest'] = data.is_guest

            tag_list.append(temp)

        return tag_list

    @staticmethod
    def compute_tagging_list_of_chatroom_participants(chatroom_instance, search_name: str = None, user_id: int = None,
                                                      page: int = None, page_size: int = None):

        if not search_name:
            tag_list = get_sorted_user_data_on_basis_of_activity_in_chatroom(chatroom_instance.id,
                                                                             user_id=user_id,
                                                                             page=page,
                                                                             limit=page_size)

        else:
            tag_list = get_community_members_data_on_basis_of_name_search(
                chatroom_instance.community_id, chatroom_instance.id, user_id=user_id, page=page, limit=page_size,
                member_name_search=search_name, tag_only_participants=chatroom_instance.tag_only_participants)

        return tag_list

    @staticmethod
    def compute_tagging_list_of_secret_chatroom_participants(chatroom_instance, search_name: str = None,
                                                             user_id: int = None, page: int = None,
                                                             page_size: int = None):

        tag_list = []

        try:
            member_list = json.loads(chatroom_instance.secret_chatroom_participants)

        except Exception as e:
            error_logger.error(e)
            member_list = []

        if not member_list:
            return tag_list

        if not search_name:
            tag_list = get_sorted_user_data_on_basis_of_activity_in_chatroom(
                chatroom_instance.id, user_id=user_id, page=page, limit=page_size, filter_user_ids=member_list)

        else:
            tag_list = get_community_members_data_on_basis_of_name_search(
                chatroom_instance.community_id, chatroom_instance.id, user_id=user_id, page=page, limit=page_size,
                member_name_search=search_name, filter_user_ids=member_list)

        return tag_list

    @staticmethod
    def remove_guest_user_from_participants_data_list(participants_data):
        participants_list = []

        for member_data in participants_data:

            if not member_data.get('is_guest'):
                participants_list.append(member_data)

        return participants_list

    @staticmethod
    def compute_tagging_list_for_secret_participants(chatroom_instance, community_instance, page=0, page_size=0,
                                                     member_name_search_string="", order_by_name=False, 
                                                     sdk_client_info_flag: bool=False):

        try:
            member_list = json.loads(chatroom_instance.secret_chatroom_participants)

        except Exception as e:
            error_logger.error(e)
            member_list = []

        member_data = MemberCommunityImpl.fetch_members_based_on_user_list(
            member_list, community_instance, page=page, page_size=page_size,
            member_name_search_string=member_name_search_string, order_by_name=order_by_name, 
            sdk_client_info_flag=sdk_client_info_flag)
        tagging_list = MemberCommunityHelper.extract_member_tagging_data(member_data, 
                                                                         sdk_client_info_flag=sdk_client_info_flag)

        return tagging_list

    @staticmethod
    def compute_placeholder_for_intro_room(card_instance, user_instance):

        if not user_instance:
            return ""

        placeholder = ""

        if card_instance.type == card_types.CARD_INTRO \
                and card_instance.user_id != user_instance.id:
            last_seen_conversation_filter = ModelUtilities.get_model_filter(collabcardState,
                                                                            {'card': card_instance,
                                                                             'user': user_instance}
                                                                            ).only('last_seen_conversation')
            if last_seen_conversation_filter and \
                    not last_seen_conversation_filter[0].last_seen_conversation:
                card_creator_userinfo_instance = card_instance.user.userinfo
                community_instance = card_instance.community
                placeholder = ChatroomHelper.create_placeholder_for_introduction_card(community_instance,
                                                                                      card_creator_userinfo_instance)

        return placeholder

    def _create_event_meta(self, req_body, user_instance, community_instance, member_state):
        create_context = dict()
        create_context['header'] = req_body.get('header')
        create_context['title'] = req_body.get('title')
        create_context['about'] = req_body.get('about')
        create_context['community'] = community_instance
        create_context['user'] = user_instance
        create_context['online_link'] = req_body.get('online_link')
        create_context['online_link_id'] = req_body.get('online_link_id')
        create_context['online_link_password'] = req_body.get('online_link_password')
        create_context['online_link_type'] = req_body.get('online_link_type')
        create_context['location'] = req_body.get('location')
        create_context['location_lat'] = req_body.get('location_lat')
        create_context['location_long'] = req_body.get('location_long')
        create_context['date_time'] = req_body.get('date_time')
        create_context['end_date'] = req_body.get('end_date', 0)
        create_context['is_paid'] = req_body.get('is_paid', False)
        create_context['access'] = req_body.get('access')
        create_context['type'] = req_body.get('type')
        create_context['attachment_count'] = req_body.get('attachment_count', 0)
        create_context['co_hosts'] = json.dumps(req_body['co_hosts']) if req_body.get('co_hosts') else None

        create_context['online_link_enable_before'] = req_body.get('online_link_enable_before',
                                                                   TimeUtilities.get_minutes_in_milliseconds(15))
        create_context['date_epoch'] = TimeUtilities.current_time_in_sec()
        create_context['member_state'] = member_state
        create_context['event_payment_link'] = req_body.get('event_payment_link')
        create_context['event_web_page'] = req_body.get('event_web_page')

        if create_context.get('access') in [event_access.NON_COMMUNITY_USERS,
                                            event_access.NON_COMMUNITY_USERS_AND_MEMBERS]:
            create_context['access_without_subscription'] = True

        card_instance = Collabcard(**create_context)
        card_instance.save()

        self.set_chatroom_id(card_instance.id)

        if req_body.get('cohort_ids'):
            create_chatroom_cohort_instances(chatroom_id=card_instance.id, cohort_ids=req_body.get('cohort_ids'))

        return card_instance

    def update_event_meta(self, req_body, user_instance, community_instance, card_instance):
        update_context = dict()
        update_context['header'] = req_body.get('header', card_instance.header)
        update_context['title'] = req_body.get('title', card_instance.title)
        update_context['community'] = community_instance
        update_context['user'] = user_instance
        update_context['online_link'] = req_body.get('online_link', card_instance.online_link)
        update_context['about'] = req_body.get('about', card_instance.about)
        update_context['online_link_id'] = req_body.get('online_link_id', card_instance.online_link_id)
        update_context['online_link_password'] = req_body.get('online_link_password',
                                                              card_instance.online_link_password)
        update_context['online_link_type'] = req_body.get('online_link_type',
                                                          card_instance.online_link_type)
        update_context['location'] = req_body.get('location', card_instance.location)
        update_context['location_lat'] = req_body.get('location_lat', card_instance.location_lat)
        update_context['location_long'] = req_body.get('location_long', card_instance.location_long)
        update_context['date_time'] = req_body.get('date_time', card_instance.date_time)
        update_context['end_date'] = req_body.get('end_date', card_instance.end_date)
        update_context['is_paid'] = req_body.get('is_paid', card_instance.is_paid)
        update_context['access'] = req_body.get('access', card_instance.access)
        update_context['type'] = req_body.get('type', card_instance.type)
        update_context['attachment_count'] = req_body.get('attachment_count',
                                                          card_instance.attachment_count)
        if req_body.get('co_hosts'):
            update_context['co_hosts'] = json.dumps(req_body['co_hosts'])

        update_context['online_link_enable_before'] = req_body.get('online_link_enable_before',
                                                                   card_instance.online_link_enable_before)
        update_context['member_state'] = card_instance.member_state
        update_context['event_payment_link'] = req_body.get('event_payment_link',
                                                            card_instance.event_payment_link)
        update_context['event_web_page'] = req_body.get('event_web_page',
                                                        card_instance.event_web_page)
        update_context['updated_at'] = TimeUtilities.current_time_in_milliseconds()

        if req_body.get('cohort_ids'):
            create_chatroom_cohort_instances(chatroom_id=card_instance.id, cohort_ids=req_body.get('cohort_ids'))

        ModelUtilities.model_update(Collabcard, {'id': card_instance.id}, update_context)
        ModelUtilities.model_update(collabcardState, {'card': card_instance},
                                    {'updated_at': TimeUtilities.current_time_in_sec()})

        self.set_chatroom_id(card_instance.id)

        return card_instance

    @staticmethod
    def get_filter_dict_for_fetch_all_events(user_instance, attending_status=None, has_content=None, past_events=None,
                                             community_id=None):
        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        filter_dict = {
            'card__is_pending': False,
            'card__is_deleted': False,
            'user': user_instance,
            'secret_chatroom_left': False
        }

        if attending_status is not None:
            filter_dict['attending_status'] = attending_status

        if community_id is not None:
            filter_dict['community'] = community_id

        if has_content is not None:
            filter_dict['card__has_event_recording'] = has_content

        if not past_events:
            filter_dict['card__end_date__gte'] = current_time_ms

        else:
            filter_dict['card__end_date__lt'] = current_time_ms

        filter_dict['card__type__in'] = [card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]

        return filter_dict

    @staticmethod
    def fetch_events_queryset(past_events=None, event_filter_dict=None):
        filter_dict = event_filter_dict.copy()

        if filter_dict is None:
            filter_dict = {}

        filter_dict['card__access__in'] = [event_access.COMMUNITY_MEMBERS, event_access.NON_COMMUNITY_USERS_AND_MEMBERS]

        if not past_events:
            chatroom_queryset = ModelUtilities.get_model_filter(collabcardState, filter_dict). \
                select_related('card', 'card__user', 'community').order_by('card__date_time')

        else:
            chatroom_queryset = ModelUtilities.get_model_filter(collabcardState, filter_dict). \
                select_related('card', 'card__user', 'community').order_by('-card__date_time')

        return chatroom_queryset

    @staticmethod
    def fetch_events_member_cohort_access(user_instance, past_events=None, event_filter_dict=None):
        filter_dict = event_filter_dict.copy()

        if filter_dict is None:
            filter_dict = {}

        user_cohorts = ModelUtilities.get_model_filter(CohortMember, {'user_id': user_instance.id}).values_list(
            'cohort_id', flat=True)

        # Get ids of chatroom in which user related cohorts are added.
        chatroom_ids = ModelUtilities.get_model_filter(ChatroomCohort, {'cohort_id__in': user_cohorts}).values_list(
            'chatroom_id', flat=True)

        filter_dict['card_id__in'] = chatroom_ids

        if not past_events:
            chatroom_queryset = ModelUtilities.get_model_filter(collabcardState, filter_dict)\
                .filter(Q(card__access=0) | Q(card__access=None)).select_related('card', 'card__user', 'community')\
                .order_by('card__date_time')

        else:
            chatroom_queryset = ModelUtilities.get_model_filter(collabcardState, filter_dict)\
                .filter(Q(card__access=0) | Q(card__access=None)).select_related('card', 'card__user', 'community')\
                .order_by('-card__date_time')

        return chatroom_queryset

    @staticmethod
    def fetch_non_member_access_events_for_community_manager_queryset(past_events=None, event_filter_dict=None,
                                                                      user_instance=None):
        filter_dict = event_filter_dict.copy()

        if filter_dict is None:
            filter_dict = {}

        # If Community ID not given, fetch all communities in which user is CM
        if not filter_dict.get('community'):
            community_manager_filter = ModelUtilities.get_model_filter(Members, {'state': member_states.ADMIN,
                                                                                 'member_id_id': user_instance.id})
            filter_dict['community_id__in'] = community_manager_filter.values_list('community_id_id', flat=True)
        else:
            community_manager_filter = ModelUtilities.get_model_filter(Members, {'state': member_states.ADMIN,
                                                                                 'member_id_id': user_instance.id,
                                                                                 'community_id_id': filter_dict.get(
                                                                                     'community')})
            if not community_manager_filter:
                return collabcardState.objects.none()

        if not past_events:
            chatroom_queryset = ModelUtilities.get_model_filter(collabcardState, filter_dict). \
                filter(Q(card__access=0) | Q(card__access=None)).select_related('card', 'card__user', 'community'). \
                order_by('card__date_time')

        else:
            chatroom_queryset = ModelUtilities.get_model_filter(collabcardState, filter_dict). \
                filter(Q(card__access=0) | Q(card__access=None)).select_related('card', 'card__user', 'community'). \
                order_by('-card__date_time')

        return chatroom_queryset

    def _fill_online_link_for_event(self, chatroom_context, card_instance):

        if card_instance.online_link:
            chatroom_context['online_link'] = card_instance.online_link

        if card_instance.online_link_id:
            chatroom_context['online_link_id'] = card_instance.online_link_id

        if card_instance.online_link_password:
            chatroom_context['online_link_password'] = card_instance.online_link_password

    def fetch_chatroom(self, is_internal=False, excluded_conversation_states: list = None) -> dict:

        if excluded_conversation_states:
            excluded_conversation_states = StringUtilities.get_list_from_string(excluded_conversation_states,
                                                                                default=None)

        if not (excluded_conversation_states and isinstance(excluded_conversation_states, list)):
            excluded_conversation_states = [conversation_states.CONVERSATION_HEADER]

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, self.get_chatroom_id())

        if not card_instance:
            return ResponseUtilities.get_impl_error_context("invalid chatroom id",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return ResponseUtilities.get_impl_error_context("invalid user id",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = card_instance.community

        if SdkClient.is_sdk_community(community_id=community_instance.id):
            api_type = api_types.SDK

        else:
            api_type = api_types.Non_SDK

        if is_internal:
            return {'success': True, 'chatroom': CollabcardSerializer(card_instance, user_instance.id)}

        if all([card_instance.is_private, card_instance.type == card_types.CARD_DIRECT_MESSAGE,
                not (card_instance.user == user_instance or card_instance.chatroom_with_user == user_instance)]):
            return ResponseUtilities.get_impl_error_context("You cannot access DM chatroom!",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        if card_instance.access not in [event_access.COMMUNITY_MEMBERS, event_access.NON_COMMUNITY_USERS_AND_MEMBERS] \
                and card_instance.type in [card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:

            is_promoter = Members.is_member_community_promoter(community_instance, user_instance)

            if not is_promoter:
                # If only non-members have event access, he/she should be member of of any chatroom related cohort.
                from collabmates_api.cohort.cohort_impl import CohortHelper
                has_event_access = CohortHelper.check_if_user_is_member_of_chatroom_related_cohort(card_instance,
                                                                                                   user_instance)

                if not has_event_access:
                    return ResponseUtilities.get_impl_error_context("You don't have access to this event",
                                                                    status_code=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_data = ChatroomHelper.compute_chatroom_response(card_instance, user_instance,
                                                                 community_instance=community_instance,
                                                                 sdk_client_info_flag=True)

        if not chatroom_data:
            return ResponseUtilities.get_impl_error_context("User is not associated with chatroom",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        reset_unread_message_count_in_cache.delay(self.get_chatroom_id(), self.get_member_id())

        chatroom_icons = self._fetch_icon_states_for_chatroom(card_instance, chatroom_data)
        chatroom_data.update(chatroom_icons)

        chatroom_obj = dict()
        chatroom_obj['chatroom'] = chatroom_data
        chatroom_obj['chatroom_actions'] = self._fetch_chatroom_actions(card_instance, chatroom_data, api_type=api_type)
        chatroom_obj['community'] = CommunitySerializerV1(community_instance,
                                                          context={"current_user_id": user_instance.id},
                                                          many=False).data
        chatroom_obj['unread_messages'] = fetch_conversations_unread(self.get_chatroom_id(), self.get_member_id())
        chatroom_obj['participant_count'] = ChatroomHelper.chatroom_participants_count(card_instance)
        chatroom_obj['conversation_users'] = self._latest_conversations_user_data()
        self._save_external_seen_in_chatroom_state(card_instance, user_instance)

        can_access_secret_chatroom = False

        if self.get_member_id() is not None:
            member_id = NumberUtilities.get_integer_from_string(self.get_member_id())

            if card_instance.is_secret:

                try:
                    can_access_secret_chatroom = member_id in json.loads(card_instance.secret_chatroom_participants)

                    member_filter = ModelUtilities.get_model_filter(Members, {
                        'community_id_id': card_instance.community_id,
                        'member_id_id': member_id
                    })

                    # Only CM/Owner can access chatroom apart from participants
                    if member_filter and member_filter[0].state == member_states.ADMIN:
                        can_access_secret_chatroom = True

                except Exception as e:
                    error_logger.error(f"fetch_chatroom - {e.args}")

                    response = {
                        'success': False,
                        'error_message': f"{e.args}"
                    }
                    raise CustomException(response, status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)

            elif card_instance.attachment_count > 0 and \
                    card_instance.attachments_uploaded is False:
                can_access_secret_chatroom = not ChatroomHelper.has_attachments_uploaded(card_instance,
                                                                                         member_id,
                                                                                         self.device_id)

        chatroom_obj['can_access_secret_chatroom'] = can_access_secret_chatroom
        placeholder = self.compute_placeholder_for_intro_room(card_instance, user_instance)

        if placeholder:
            chatroom_obj['placeholder'] = placeholder

        from collabmates_api.cohort.cohort_impl import CohortHelper
        cohort_access = CohortHelper.fetch_cohort_access_for_chatroom(self.get_chatroom_id(), self.get_member_id())

        if cohort_access is not None:
            chatroom_obj['cohort_access'] = cohort_access

        # For Event Recordings and Attachments data
        event_recordings_data = ChatroomHelper.display_event_recordings_and_attachments(
            user_instance=user_instance,
            card_instance=card_instance
        )

        chatroom_obj.get('chatroom').update(event_recordings_data)

        last_conversation_id = None

        card_ans_map = get_last_conversation_id_corresponding_to_chatrooms_list(
            [card_instance.id], excluded_conversation_state=excluded_conversation_states)

        if card_ans_map:
            last_conversation_id = card_ans_map.get(card_instance.id)

        chatroom_obj['last_conversation_id'] = last_conversation_id

        chatroom_obj['success'] = True

        return chatroom_obj

    def fetch_all_chatroom(self, chatroom_filter_type: str, chatroom_excluded_type: str, page: int = 1) -> dict:
        validated_req = ChatroomViewHelper.validate_fetch_all_chatroom_request(self.get_member_id(),
                                                                               self.get_api_key(),
                                                                               chatroom_filter_type,
                                                                               chatroom_excluded_type)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_req.get('community_instance')
        chatroom_filter_type = validated_req.get('chatroom_filter_type')
        chatroom_excluded_type = validated_req.get('chatroom_excluded_type')

        error_logger.error(f"[process_chatroom] chatroom/fetch_all_new fetching chatrooms data from db")

        chatrooms_data = get_all_chatrooms_of_community(community_instance.id, chatroom_filter_type,
                                                        chatroom_excluded_type, page)
        
        error_logger.error(f"[process_chatroom] chatroom/fetch_all_new done fetching chatrooms data from db")

        error_logger.error(f"[process_chatroom] chatroom/fetch_all_new parsing chatrooms data")

        from collabmates_api.sync.sync_helper import SyncHelper
        chatrooms_data = SyncHelper.parse_sync_raw_query_response(chatrooms_data, 'chatrooms')

        error_logger.error(f"[process_chatroom] chatroom/fetch_all_new done parsing chatrooms data")

        filter_dict = {
            'is_deleted': False,
            'is_private': False,
            'community': community_instance.id
        }

        total_chatroom_count = ModelUtilities.get_model_filter(Collabcard, filter_dict).count()
        return {'success': True, **chatrooms_data, 'total_chatroom_count': total_chatroom_count}

    def fetch_all_chatroom_old(self, chatroom_filter_type: str, chatroom_excluded_type: str, page: int = 1) -> dict:
        validated_req = ChatroomViewHelper.validate_fetch_all_chatroom_request(self.get_member_id(),
                                                                               self.get_api_key(),
                                                                               chatroom_filter_type,
                                                                               chatroom_excluded_type)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_req.get('community_instance')
        user_instance = validated_req.get('user_instance')
        chatroom_filter_type = validated_req.get('chatroom_filter_type')
        chatroom_excluded_type = validated_req.get('chatroom_excluded_type')

        if not chatroom_excluded_type:
            chatroom_excluded_type = [card_types.CARD_INTRO]

        else:
            chatroom_excluded_type.append(card_types.CARD_INTRO)

        card_ids = get_all_chatrooms_of_community_old(community_instance.id, chatroom_filter_type,
                                                      chatroom_excluded_type)
        chatroom_list = ModelUtilities.get_model_filter(collabcardState,
                                                        {'card_id__in': card_ids,
                                                         'user': self.get_member_id(),
                                                         'secret_chatroom_left': False}).select_related('card',
                                                                                                        'card__user')
        total_chatroom_count = len(chatroom_list)
        chatroom_list = ModelUtilities.paginate_queryset(chatroom_list, page, 10)

        chatroom_context_list = []

        if chatroom_list:

            from ..chatroom_member.chatroom_member_impl import ChatroomMemberImpl

            error_logger.error(f"[process_chatroom] chatroom/fetch_all_old")

            chatroom_member_impl = ChatroomMemberImpl(member_id=self.get_member_id(), device_id=self.device_id)
            chatroom_context_list = chatroom_member_impl.process_chatroom_list(chatroom_list, community_instance)

        return {'success': True, 'chatrooms': chatroom_context_list, 'total_chatroom_count': total_chatroom_count}

    def create_chatroom(self, req_body: dict) -> dict:
        validated_req = ChatroomViewHelper.validate_create_chatroom_request(self.get_member_id(),
                                                                            self.get_api_key(),
                                                                            req_body)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        community_instance = validated_req.get('community_instance')
        community_id = community_instance.id

        member_state = ChatroomHelper.fetch_member_state_in_community(user=user_instance,
                                                                      community=community_instance)

        user_has_auto_approve_right = ChatroomHelper.check_user_auto_approve_right(user=user_instance,
                                                                                   community=community_instance)
        chatroom_name = req_body['title']

        tagged_members = get_tagged_members_list(community_id, '', chatroom_name)

        chatroom_type = int(req_body.get('type', card_types.CARD_NORMAL))
        is_intro_card = chatroom_type == card_types.CARD_INTRO
        auto_follow_done = req_body.get('auto_follow_done', False)
        include_members_later = req_body.get('include_members_later', False)
        chatroom_image_url = req_body.get('chatroom_image_url', None)

        uuids = req_body.get('uuids', None)
        is_secret = req_body.get('is_secret', False)
        
        card_content = {}

        self._fill_chatroom_basic_info(card_content, chatroom_name,
                                       community_instance, user_instance, chatroom_type,
                                       auto_follow_done=auto_follow_done, include_members_later=include_members_later,
                                       chatroom_image_url=chatroom_image_url)
        self._fill_chatroom_attachment_count(card_content, req_body)
        self._fill_chatroom_epoch_time(card_content, req_body)

        self._fill_chatroom_event_details(card_content=card_content, req_body=req_body)
        self._fill_chatroom_poll_details(card_content, req_body)
        self._fill_chatroom_header(card_content, req_body, chatroom_type, chatroom_name, tagged_members[1])

        self._add_og_tags(req_body=req_body, card_content=card_content)
        self._check_and_set_chatroom_pending_status(card_content, is_intro_card, user_has_auto_approve_right)
        self.fill_pinned_information(card_content)

        self._fill_secret_room_details(card_content, req_body, community_instance)

        card_content['member_state'] = member_state

        card_content['third_party_unique_id'] = req_body.get('third_party_unique_id')

        card_content['custom_tag'] = req_body.get('tag')

        if card_content['is_secret'] and \
                not ChatroomHelper.check_user_secret_room_creation_right(user_instance, community_instance):
            error_message = "Only CM or member with secret chatroom creation right can create secret chatroom"
            return ResponseUtilities.get_impl_error_context(error_message,
                                                            status_code=status_codes.HTTP_403_FORBIDDEN)

        chatroom_instance = self._create_chatroom_with_contents(card_content=card_content)
        self.set_chatroom_id(chatroom_instance.id)

        self._add_preview_from_internal_link(chatroom_instance, req_body)
        self._create_chatroom_polls(user_instance, chatroom_instance, req_body)
        self._delete_draft(req_body)
        ChatroomHelper.set_chatroom_participants_created_key_in_cache(self.get_chatroom_id(), False)

        send_chatroom_creation_analytics_data.delay(self.get_chatroom_id(), int(self.get_member_id()))

        sdk_communities = ModelUtilities.get_model_filter(SdkClient, {"community": community_instance,
                                                                      "is_deleted": False})

        if not sdk_communities:
            self._send_chatroom_creation_notifications(user_instance, community_id, community_instance.name,
                                                       chatroom_instance, card_content, user_has_auto_approve_right,
                                                       chatroom_type, is_intro_card, set_default_unread_count=True)

        cohort_ids = req_body['cohort_ids'] if ('cohort_ids' in req_body) else None

        if cohort_ids:
            create_chatroom_cohort_instances(self.get_chatroom_id(), cohort_ids)

        if user_has_auto_approve_right or is_intro_card:
            self._send_follow_notifications_to_tagged_members(tagged_members_list=tagged_members[0])

        if chatroom_instance.is_secret:
            participants_list = []

            if chatroom_instance.secret_chatroom_participants:
                participants_list = json.loads(chatroom_instance.secret_chatroom_participants)

            room_creator_id = NumberUtilities.get_integer_from_string(self.get_member_id())

            ChatroomHelper.make_secret_chatroom_relation_for_community_members.delay(participants_list,
                                                                                     self.get_chatroom_id(),
                                                                                     community_id,
                                                                                     room_creator_id=room_creator_id)

        if chatroom_instance.co_hosts:
            ChatroomHelper.auto_follow_event_co_hosts_and_send_notification(chatroom_instance, user_instance.userinfo)

        open_chatroom_participants = req_body.get('chatroom_participants', [])

        # If uuids are passed and chatroom is open, update open_chatroom_participants with valid member_ids
        if uuids and not is_secret:
            valid_ids = ModelUtilities.get_valid_user_ids_from_uuids(uuids, community_id)
            open_chatroom_participants = valid_ids

        self._send_additional_notifications_and_tasks_after_room_creation(user_instance, community_instance,
                                                                          chatroom_instance, req_body,
                                                                          is_intro_card, user_has_auto_approve_right,
                                                                          community_id, open_chatroom_participants)

        ChatroomHelper.update_time_for_community_members_on_card_creation(community_instance)

        send_sync_notification.delay({'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value,
                                      'community_id': community_id})

        if chatroom_instance.type == card_types.CARD_EVENT or \
                chatroom_instance.type == card_types.CARD_PUBLIC_EVENT:
            schedule_chatroom_unpinning_after_event_completion(chatroom_instance)

            ModelUtilities.model_update(collabcardState, {'card': chatroom_instance, 'user': user_instance},
                                        {'attending_status': True, 'updated_at': TimeUtilities.current_time_in_sec()})

        if req_body.get('schedule_time') and req_body.get('end_time'):
            ChatroomImpl.update_scheduled_chatroom_follow_and_delete_task_after_end_time.delay(
                self.get_member_id(),
                chatroom_instance.id,
                req_body
            )

        context = {
            'success': True,
            'chatroom': ChatroomHelper.compute_chatroom_response(chatroom_instance, user_instance, community_instance, 
                                                                 sdk_client_info_flag=True),
            'chatroom_local': ChatroomHelper.fetch_serialized_chatroom_for_local_db_sycing(self.get_member_id(),
                                                                                           chatroom_instance)
        }

        return context

    @staticmethod
    @shared_task
    def update_scheduled_chatroom_follow_and_delete_task_after_end_time(member_id, chatroom_id, req_body):

        data_dict = {
            'schedule_time': req_body.get('schedule_time'),
            'end_time': req_body.get('end_time'),
            'chatroom_id': chatroom_id
        }

        if req_body.get('schedule_time_before'):
            data_dict['schedule_time_before'] = req_body.get('schedule_time_before')

        if req_body.get('end_time_after'):
            data_dict['end_time_after'] = req_body.get('end_time_after')

        serializer = ScheduledChatroomFollowSerializer(data=data_dict)

        if serializer.is_valid():
            instance = serializer.save()

            args = [member_id, chatroom_id]

            task_begin_time = TimeUtilities.convert_epoch_to_datetime_in_IST(
                instance.end_time + instance.end_time_after
            )

            from collabmates_api.views import delete_chatroom_async

            delete_chatroom_async.apply_async(
                args,
                eta=task_begin_time
            )

    def get_chatroom_participants(self, filter_dict: dict) -> QuerySet:
        return collabcardState.get_chatroom_participants(filter_dict)

    def pin_or_unpin_chatroom(self, req_body: dict) -> dict:
        validated_req = ChatroomViewHelper.validate_pin_unpin_chatroom_request(self.get_chatroom_id(),
                                                                               self.get_member_id())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        value = req_body['value']
        notify = req_body['notify']

        chatroom_instance = validated_req.get('card_instance')
        community_instance = chatroom_instance.community
        pinned_status = chatroom_instance.is_pinned

        if pinned_status is value:
            return {'success': True}

        chatroom_instance.is_pinned = value

        if value:
            chatroom_instance.pinning_time = TimeUtilities.current_time_in_milliseconds()

        chatroom_instance.save()

        if notify is True and value is True:
            send_pin_chatroom_notification.delay(community_instance.id, self.get_member_id(), self.get_chatroom_id())

        send_chatroom_updated_analytics_data.delay(self.get_chatroom_id(), int(self.get_member_id()),
                                                   {'is_pinned': value})

        cache_update_dict = {
            'chatroom_id': self.get_chatroom_id(),
            'community_id': chatroom_instance.community_id,
            'pin_value': value
        }

        update_community_pin_chatrooms_list_in_cache.delay(cache_update_dict)

        return {'success': True}

    def leave_secret_chatroom(self, member_id: Union[int, str] = None, uuid = None) -> None:

        chatroom_instance = Collabcard.get_chatroom_with_joins_or_raise_exception(self.get_chatroom_id())

        chatroom_state = conversation_states.CONVERSATION_REMOVED_FROM_CHATROOM
        if (member_id or uuid) is None:
            member_id = self.get_member_id()
            chatroom_state = conversation_states.CONVERSATION_LEAVE_CHATROOM

        # If uuid is passed, get valid user id and update member_id
        if uuid:
            valid_id = ModelUtilities.get_valid_user_ids_from_uuids([uuid], chatroom_instance.community_id)
            
            if not valid_id:
                return ResponseUtilities.get_impl_error_context("Invalid uuid sent", status_codes.HTTP_400_BAD_REQUEST)
            
            member_id = valid_id[0]

        user_instance = ModelUtilities.get_user_instance_or_none(member_id)
        if not user_instance:
            return ResponseUtilities.get_impl_error_context("Invalid member_id sent", status_codes.HTTP_400_BAD_REQUEST)

        # removing member id from secret_chatroom_participants list
        existing_participants_list = json.loads(chatroom_instance.secret_chatroom_participants)
        member_id = user_instance.id

        if member_id in existing_participants_list:
            existing_participants_list.remove(member_id)
        else:
            response = {
                'success': False,
                'error_message': f'member with id {member_id} is not a participant of this secret chatroom'
            }
            raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

        chatroom_instance.secret_chatroom_participants = existing_participants_list
        self._save_chatroom_instance(chatroom_instance)

        member_state = Members.get_community_member_state(chatroom_instance.community_id, user_instance)
        secret_chatroom_left = True

        if member_state == member_states.ADMIN:
            secret_chatroom_left = False

        filter_dict = {
            'card': chatroom_instance,
            'user': user_instance
        }

        update_dict = {
            'secret_chatroom_left': secret_chatroom_left,
            'follow_status': False,
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        ModelUtilities.model_update(collabcardState, filter_dict, update_dict)

        # updating all secret chatroom participants
        filter_dict = {
            'card': chatroom_instance,
        }

        update_dict = {
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        ModelUtilities.model_update(collabcardState, filter_dict, update_dict)

        # deleting conversation engage for this chatroom for this user
        conversationEngage.objects.filter(card=chatroom_instance, user=user_instance).delete()

        ChatroomHelper.create_answer(chatroom_instance=chatroom_instance, user_instance=user_instance,
                                     state=chatroom_state, current_user_id=self.get_member_id())

        update_last_unseen_in_engage(user=member_id, community=chatroom_instance.community_id)

        if secret_chatroom_left:
            ElasticSearchSync.delete_chatroom_for_user.delay(chatroom_instance.id, user_instance.id)

        if chatroom_state == conversation_states.CONVERSATION_REMOVED_FROM_CHATROOM:
            send_notification_for_removed_secret_room_participant.delay(member_id, self.get_chatroom_id())

    def add_secret_chatroom_participant(self, req_body: dict, is_internal: bool = True,
                                        add_user_joined_message: bool = True) -> dict:
        validated_req_body = ChatroomViewHelper.validate_add_secret_chatroom_participants_request(self.get_member_id(),
                                                                                                  self.get_chatroom_id(),
                                                                                                  req_body)

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req_body.get('user_instance')
        chatroom_instance = validated_req_body.get('card_instance')
        secret_chatroom_participants = validated_req_body.get('secret_chatroom_participants')
        uuids = validated_req_body.get('uuids')
        is_chatroom_invite = req_body.get('is_channel_invite', True)

        if not is_internal:

            # If uuids is passed, get valid user ids
            if uuids:
                secret_chatroom_participants = ModelUtilities.get_valid_user_ids_from_uuids(uuids, chatroom_instance.community_id)

            else:
                # support for user_unique_ids in secret chatroom participants parameter
                secret_chatroom_participants = ModelUtilities.get_valid_member_ids(secret_chatroom_participants,
                                                                                   community_id=chatroom_instance.community_id)

        secret_chatroom_participants = ChatroomHelper.validate_secret_chatroom_participants_or_raise_exception(
            secret_chatroom_participants)

        if len(secret_chatroom_participants) <= 0:
            return {'success': True}

        existing_participants = json.loads(chatroom_instance.secret_chatroom_participants)

        is_setting_enabled = False

        if is_chatroom_invite:
            filter_dict = {
                'community': chatroom_instance.community,
                'enabled': True
            }

            if chatroom_instance.type == card_types.CARD_NORMAL:
                filter_dict['setting_type'] = community_setting_types.SECRET_CHATROOMS_INVITE
                chatroom_invite_setting = ModelUtilities.get_model_filter(CommunitySettings, filter_dict)

                if chatroom_invite_setting:
                    is_setting_enabled = True

            elif chatroom_instance.type == card_types.CARD_FEED_GROUP:
                filter_dict['setting_type'] = community_setting_types.SECRET_GROUP_INVITE
                post_group_invite_setting = ModelUtilities.get_model_filter(CommunitySettings, filter_dict)

                if post_group_invite_setting:
                    is_setting_enabled = True

            if is_setting_enabled:
                new_users_list = list(set(secret_chatroom_participants) - set(existing_participants))
                ChatroomHelper.create_chatroom_invite_to_users.delay(user_instance.id,
                                                                     chatroom_instance.id,
                                                                     new_users_list)

                return {'success': True}

        final_participants_list = set(secret_chatroom_participants) | set(existing_participants)

        chatroom_instance.secret_chatroom_participants = json.dumps(list(final_participants_list))

        self._save_chatroom_instance(chatroom_instance)

        new_participants_list = list(set(secret_chatroom_participants) - set(existing_participants))

        if len(new_participants_list) <= 0:
            return {'success': True}

        # updating all secret chatroom participants
        filter_dict = {
            'card': chatroom_instance,
            'user__id__in': new_participants_list
        }

        update_dict = {
            'secret_chatroom_left': False,
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       filter_dict=filter_dict,
                                       update_dict=update_dict)

        ChatroomHelper.add_new_secret_chatroom_participants.delay(new_participants_list,
                                                                  self.get_chatroom_id(),
                                                                  self.get_member_id(),
                                                                  add_user_joined_message)

        send_participants_added_in_chatroom_analytics_data.delay(self.get_chatroom_id(), int(self.get_member_id()))

        # updating all secret chatroom participants
        filter_dict = {
            'card': chatroom_instance,
        }

        update_dict = {
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       filter_dict=filter_dict,
                                       update_dict=update_dict)

        return {'success': True}

    def get_tagging_list(self, search_name: str = None, page: int = None, page_size: int = None) -> dict:

        validated_req_body = ChatroomViewHelper.validate_get_tagging_list_request(self.get_member_id(),
                                                                                  self.get_chatroom_id())

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_instance = validated_req_body.get('card_instance')
        user_instance = validated_req_body.get('user_instance')
        community_instance = chatroom_instance.community

        group_tags = []

        if page and page < 2:
            group_tags = self._add_group_tags(community_instance, chatroom_instance)

        if chatroom_instance.is_secret:
            participant_list = self.compute_tagging_list_of_secret_chatroom_participants(chatroom_instance,
                                                                                         search_name,
                                                                                         user_id=user_instance.id,
                                                                                         page=page,
                                                                                         page_size=page_size)

            return {
                'success': True,
                'chatroom_participants': participant_list,
                'community_members': [],
                'group_tags': group_tags
            }

        participant_list = self.compute_tagging_list_of_chatroom_participants(chatroom_instance,
                                                                              search_name,
                                                                              user_id=user_instance.id,
                                                                              page=page,
                                                                              page_size=page_size)

        return {
            'success': True,
            'chatroom_participants': [],
            'community_members': participant_list,
            'group_tags': group_tags
        }

    def get_tagging_list_old(self) -> dict:
        validated_req_body = ChatroomViewHelper.validate_get_tagging_list_request(self.get_member_id(),
                                                                                  self.get_chatroom_id())

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_instance = validated_req_body.get('card_instance')
        community_instance = chatroom_instance.community

        group_tags = self._add_group_tags(community_instance, chatroom_instance)

        if chatroom_instance.is_secret:
            participant_list = self.compute_tagging_list_for_secret_participants(chatroom_instance, community_instance,
                                                                                 sdk_client_info_flag=True)
            participant_list = self.remove_guest_user_from_participants_data_list(participant_list)

            return {
                'success': True,
                'participants': participant_list,
                'members': [],
                'group_tags': group_tags
            }

        members = self.compute_tagging_list_of_community_members(community_instance, sdk_client_info_flag=True)
        members = self.remove_guest_user_from_participants_data_list(members)
        participant_list = self.compute_tagging_list_of_guest_members(chatroom_instance)
        participant_list = self.remove_guest_user_from_participants_data_list(participant_list)

        return {
            'success': True,
            'members': members,
            'participants': participant_list,
            'group_tags': group_tags
        }

    def _add_group_tags(self, community_instance: Community, chatroom_instance: Collabcard) -> list:
        group_tags: list = list()

        member_state = Members.get_community_member_state(community_instance, self.get_member_id())

        if member_state == member_states.ADMIN and not chatroom_instance.is_secret:
            # group_tags.append(ChatroomHelper.get_everyone_group_tag())
            group_tags.append(ChatroomHelper.get_participants_group_tag())

        elif member_state == member_states.ADMIN and chatroom_instance.is_secret:
            group_tags.append(ChatroomHelper.get_participants_group_tag())

        # chatroom creator
        elif self.get_member_id() == chatroom_instance.user.id:
            group_tags.append(ChatroomHelper.get_participants_group_tag())

        return group_tags

    def create_introduction_card_in_community(self, community_instance, user_instance, req_body, member_state,
                                              master_intro_instance):

        card_content = {}
        chatroom_name = req_body.get('title')
        chatroom_type = card_types.CARD_INTRO

        self._fill_chatroom_basic_info(card_content, chatroom_name,
                                       community_instance, user_instance, chatroom_type)

        self._fill_chatroom_attachment_count(card_content, req_body)
        self._fill_chatroom_epoch_time(card_content, req_body)

        self._fill_chatroom_event_details(card_content=card_content, req_body=req_body)
        self._fill_chatroom_poll_details(card_content, req_body)
        self._fill_chatroom_header(card_content, req_body, chatroom_type, chatroom_name)

        self._add_og_tags(req_body=req_body, card_content=card_content)
        self._fill_secret_room_details(card_content, req_body, community_instance)

        card_content['member_state'] = member_state
        chatroom_instance = self._create_chatroom_with_contents(card_content=card_content)

        self.add_files_for_introduction_card(chatroom_instance, user_instance, community_instance)
        ChatroomHelper.update_time_for_community_members_on_card_creation(community_instance)
        ChatroomHelper.auto_follow_chatroom(chatroom_instance, user_instance,
                                            community_instance, member_state=member_state)
        create_chatroom(card_instance=chatroom_instance, user_instance=user_instance,
                        state=conversation_states.CONVERSATION_HEADER, current_user_id=self.get_member_id())

        # async task for posting introduction room
        ChatroomHelper.update_old_chatrooms_relation_and_post_introduction_conversation.delay(master_intro_instance.id,
                                                                                              user_instance.id,
                                                                                              chatroom_instance.id,
                                                                                              community_instance.id,
                                                                                              member_state)

        ChatroomHelper.run_async_tasks_related_to_member_for_chatroom_posting.delay(chatroom_instance.id,
                                                                                    user_instance.id,
                                                                                    community_instance.id,
                                                                                    is_intro_chatroom=True)

        return chatroom_instance

    def add_files_for_introduction_card(self, card_instance, user_instance, community_instance):

        image_url = get_user_image_based_on_community(user_instance.id, community_instance.id)

        if card_instance and image_url:
            save_chatroom_attachments(card_instance, body={
                'url': image_url,
                'type': "image",
                'index': 1
            })
            ModelUtilities.model_update(Collabcard, {'id': card_instance.id},
                                        {'has_files': True, 'attachment_count': 1,
                                         'attachments_uploaded': True})

    def follow_chatroom_automatically_for_all_members_of_community(self, member_id, request_body) -> dict:

        validated_req = ChatroomViewHelper.validate_chatroom_auto_follow_for_all_members_request(
            self.get_chatroom_id(), member_id)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        cache_key = CHATROOM_PARTICIPANTS_CREATED_CACHE_KEY.format(self.get_chatroom_id())
        are_chatroom_participants_created = CacheImpl.get_cache(cache_key)

        if all(['are_participants_created' in are_chatroom_participants_created,
                not are_chatroom_participants_created.get('are_participants_created')]):
            return ResponseUtilities.get_impl_error_context('Chatroom creation in progress. Try again after some time.',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        chatroom_instance = validated_req.get('card_instance')
        community_id = chatroom_instance.community_id

        user_list = []
        auto_followed = False

        auto_follow_done = request_body.get('auto_follow_done', True)
        include_members_later = request_body.get('include_members_later', True)

        if (not chatroom_instance.auto_follow_done) and auto_follow_done:
            chatroom_instance.auto_follow_done = auto_follow_done
            auto_followed = True

        chatroom_instance.include_members_later = include_members_later
        chatroom_instance.save()

        if auto_followed:
            community_members = list(Members.get_members_of_community(community_id).values_list('member_id',
                                                                                                flat=True))

            ChatroomHelper.bulk_follow_chatroom_users(chatroom_instance, community_members)

            # removing tag status for tagged users
            ModelUtilities.model_update(collabcardState,
                                        {'card': chatroom_instance,
                                         'is_tagged': True},
                                        {'is_tagged': False,
                                         'updated_at': TimeUtilities.current_time_in_sec()})

            ChatroomHelper.post_added_all_members_conversation(chatroom_instance, user_instance)

            send_participants_added_in_chatroom_analytics_data.delay(self.get_chatroom_id(), int(self.get_member_id()))

            if len(user_list) > 0:
                send_notification_for_auto_follow_chatroom_for_all_members.delay(self.get_chatroom_id(),
                                                                                 user_instance.id, user_list)

        return {'success': True}

    def edit_chatroom(self, req_body) -> dict:
        validated_req = ChatroomViewHelper.validate_edit_chatroom_request(self.get_member_id(),
                                                                          self.get_chatroom_id())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        card_instance = validated_req.get('card_instance')

        title = req_body.get('title')
        text = req_body.get('text')
        header = req_body.get('header')
        card_image_url = req_body.get('chatroom_image_url')
        custom_tag = req_body.get('tag')

        if not (title or header or text or card_image_url or custom_tag):
            return ResponseUtilities.get_impl_error_context("Send title/header/chatroom_image_url/tag to update",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        update_analytics_data = {
            'updated_title': False,
            'updated_description': False,
            'updated_card_image': False,
            'updated_custom_tag': False,
        }

        update_dict = {'is_edited': True, 'updated_at': TimeUtilities.current_time_in_milliseconds()}

        if title or text:
            update_dict['title'] = title if title else text
            update_analytics_data['updated_title'] = True

        if header:
            update_dict['header'] = header
            update_analytics_data['updated_description'] = True

        if card_image_url:
            update_dict['chatroom_image_url'] = card_image_url
            update_analytics_data['updated_card_image'] = True

        if custom_tag:
            update_dict['custom_tag'] = custom_tag
            update_analytics_data['updated_custom_tag'] = True

        ModelUtilities.model_update(Collabcard, {'id': card_instance.id}, update_dict)

        send_chatroom_updated_analytics_data.delay(card_instance.id, int(self.get_member_id()), update_analytics_data)

        ChatroomHelper.run_async_tasks_related_to_chatroom_edit.delay(card_instance.id)

        return {'success': True}

    def fetch_participants_of_secret_chatroom(self, participant_name: str = None, page: int = None,
                                              page_size: int = None):

        validated_req = ChatroomHelper.validate_fetch_secret_participants_meta_request(self.get_member_id(),
                                                                                       self.get_chatroom_id())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        card_instance = validated_req.get('card_instance')

        community_instance = card_instance.community
        can_edit_participant = False

        if card_instance.is_secret:

            if card_instance.user_id == user_instance.id:
                can_edit_participant = True
            else:
                member_filter = ModelUtilities.get_model_filter(Members,
                                                                {'community_id': community_instance,
                                                                 'member_id': user_instance})
                if member_filter:
                    member_state = member_filter[0].state

                    if member_state == member_states.ADMIN:
                        can_edit_participant = ModelUtilities.is_model_filter_exists(collabcardState, {
                            'card': card_instance,
                            'follow_status': True,
                            'remove': None,
                            'user': user_instance
                        })

            pagination_version_check = VersionUtilities.check_version(self.get_request_platform(),
                                                                      self.get_version_code(),
                                                                      VersionUtilities.participants_meta_pagination,
                                                                      self.get_sdk_source())

            non_pagination_version_check = VersionUtilities.check_version(
                self.get_request_platform(), self.get_version_code(),
                VersionUtilities.participants_meta_without_pagination, self.get_sdk_source())

            order_by_name = False

            if pagination_version_check and (not non_pagination_version_check):
                order_by_name = True

            participant_list = self.compute_tagging_list_for_secret_participants(
                card_instance, community_instance, page=page, page_size=page_size,
                member_name_search_string=participant_name, order_by_name=order_by_name, 
                sdk_client_info_flag=True)
            participant_list = self.remove_guest_user_from_participants_data_list(participant_list)

            response_dict = {
                'success': True,
                'participants': participant_list,
                'can_edit_participant': can_edit_participant
            }

            if pagination_version_check and (not non_pagination_version_check):
                participants_count = ChatroomHelper.get_participants_count_in_chatroom(card_instance)
                response_dict['total_participants_count'] = participants_count

            return response_dict

        return ResponseUtilities.get_impl_error_context("Chatroom is not secret",
                                                        status_code=status_codes.HTTP_400_BAD_REQUEST)

    def create_event(self, req_body: dict) -> dict:

        validated_req = ChatroomHelper.validate_create_event_request(self.get_member_id(),
                                                                     req_body.get('community_id'),
                                                                     self.get_api_key())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        user_instance = validated_req.get('user_instance')
        community_instance = validated_req.get('community_instance')
        member_state = validated_req.get('member_state')

        # If co_hosts_uuids are passed, get valid user ids and update co_hosts
        co_hosts_uuids = req_body.get('co_hosts_uuids')

        if co_hosts_uuids:
            valid_ids = ModelUtilities.get_valid_user_ids_from_uuids(co_hosts_uuids, community_instance.id)

            if not valid_ids:
                return ResponseUtilities.get_impl_error_context("Invalid co_hosts_uuids sent",
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            req_body['co_hosts'] = valid_ids

        if req_body.get('type') == card_types.CARD_EVENT \
                or req_body.get('type') == card_types.CARD_PUBLIC_EVENT:

            card_instance = self._create_event_meta(req_body, user_instance, community_instance, member_state)
            ChatroomHelper.auto_follow_chatroom(card_instance, user_instance, community_instance,
                                                member_state=member_state, func_dict={'attending_status': True})
            conversation_impl.ConversationHelper.create_conversation_state(card_instance, user_instance,
                                                                           conversation_states.CONVERSATION_HEADER)

            ChatroomHelper.run_async_tasks_related_to_member_for_chatroom_posting.delay(card_instance.id,
                                                                                        user_instance.id,
                                                                                        community_instance.id)
            create_event_in_webflow_service(card_instance)
            schedule_chatroom_unpinning_after_event_completion(card_instance)
            # ChatroomHelper.send_event_creation_mail.delay(card_instance.id)
            send_chatroom_creation_notification(card_instance, user_instance)
            send_event_analytics_on_event_creation.delay(card_instance.id, user_instance.id)
            ChatroomHelper.run_async_tasks_related_to_event_chatroom_analytics(card_instance)
            ChatroomHelper.create_or_update_single_event_branch_link(card_instance.id)

            if cm_onboarding_version_check(self.get_request_platform(), self.get_version_code()):
                ChatroomHelper.send_first_event_creation_email_to_promoter(card_instance)
                update_community_get_started(community_instance, get_started_types.CREATE_EVENT_TYPE, is_enabled=True)

            payload_for_whatsapp_comms = {
                'chatroom': card_instance.id,
                'community': community_instance.id,
                'user': user_instance.id
            }

            payload_for_app_and_email_notifications = {
                'chatroom': card_instance.id
            }

            info_logger.info(f"api/event/create: create_event: "
                             f"user_id = {user_instance.id}, "
                             f"user_name = {user_instance.userinfo.name}, " 
                             f"Community_id = {community_instance.id}, "
                             f"Community_name = {community_instance.name}, "
                             f"Event = {card_instance.id}, "
                             f"Event_name = {card_instance.title}")
            
            trigger_event_comms.delay(payload_for_whatsapp_comms, payload_for_app_and_email_notifications)

            chatroom_context = {
                'success': True,
                'chatroom': ChatroomHelper.compute_chatroom_response(card_instance, user_instance, community_instance, 
                                                                     sdk_client_info_flag=True),
                'chatroom_local': ChatroomHelper.fetch_serialized_chatroom_for_local_db_sycing(self.get_member_id(),
                                                                                               card_instance)
            }

            return chatroom_context

        else:

            return {'success': False, 'error_message': "send correct event type"}

    def update_event(self, req_body: dict) -> dict:

        validated_req = ChatroomHelper.validate_update_event_request(self.get_member_id(),
                                                                     self.get_chatroom_id(),
                                                                     self.get_api_key())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        card_instance = validated_req.get('chatroom_instance')
        community_instance = card_instance.community

        # If co_hosts_uuids are passed, get valid user ids and update co_hosts
        co_hosts_uuids = req_body.get('co_hosts_uuids')

        if co_hosts_uuids:
            valid_ids = ModelUtilities.get_valid_user_ids_from_uuids(co_hosts_uuids, community_instance.id)

            if not valid_ids:
                return ResponseUtilities.get_impl_error_context("Invalid co_hosts_uuids sent",
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            req_body['co_hosts'] = valid_ids

        if card_instance.type == card_types.CARD_EVENT \
                or card_instance.type == card_types.CARD_PUBLIC_EVENT:

            new_co_hosts, attending_members_list = ChatroomHelper.fetch_new_co_hosts_list(card_instance, req_body)

            meta_data_for_calendar_updation = ChatroomHelper.get_meta_data_for_calendar_updation(req_body,
                                                                                                 card_instance,
                                                                                                 new_co_hosts,
                                                                                                 attending_members_list)

            card_instance = self.update_event_meta(req_body, user_instance, community_instance, card_instance)

            if new_co_hosts:
                ChatroomHelper.auto_follow_event_co_hosts_and_send_notification(card_instance, user_instance.userinfo,
                                                                                new_co_hosts=new_co_hosts)

            chatroom_context = {
                'success': True,
                'chatroom': ChatroomHelper.compute_chatroom_response(card_instance, user_instance, community_instance, 
                                                                     sdk_client_info_flag=True),
                'chatroom_local': ChatroomHelper.fetch_serialized_chatroom_for_local_db_sycing(self.get_member_id(),
                                                                                               card_instance)
            }
            update_event_in_webflow_service.delay({'chatroom_id': card_instance.id,
                                                   'update_type': event_webflow_update_types.META})

            if not req_body.get('restrict_event_update_notification'):
                send_notification_for_event_update.delay(card_instance.id)

                payload_for_whatsapp_comms = {
                    'chatroom': card_instance.id,
                    'community': community_instance.id,
                    'user': user_instance.id
                }

                payload_for_app_and_email_notifications = {
                    'chatroom': card_instance.id
                }

                reschedule_event_comms_notifications_on_event_update.delay(payload_for_whatsapp_comms,
                                                                           payload_for_app_and_email_notifications)

                payload_for_app_and_email_notifications['calendar_meta_data'] = meta_data_for_calendar_updation

                send_calender_invite_for_event_type.delay(payload_for_app_and_email_notifications,
                                                          EVENT_TYPE.REGISTRATION,
                                                          calendar_invite_type=CALENDAR_INVITE_TYPE.UPDATE_CALENDAR)

            return chatroom_context

        else:
            return ResponseUtilities.get_impl_error_context('Send correct event type',
                                                            status_codes.HTTP_400_BAD_REQUEST)

    def add_or_update_instructor(self, req_body: dict) -> dict:

        validated_request = ChatroomHelper.validate_add_or_update_instructor_request(req_body.get('chatroom_id'),
                                                                                     self.get_api_key())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        card_instance = validated_request.get('card_instance')

        instructors = req_body.get('instructors', [])

        from collabmates_api.views import SyncChatrooms

        instructors_list = SyncChatrooms().fetch_event_instructors(card_instance.id)

        for data in instructors:
            instructor_context = {
                'card': card_instance.id,
                'about': data.get('about'),
                'url': data.get('url'),
                'name': data.get('name')

            }

            instructor_serializer = EventInstructorSerializer(data=instructor_context)

            if instructor_serializer.is_valid():
                instructor_serializer.save()
                instructors_list.append(instructor_serializer.data)

            else:
                error_logger.error(f' Instructor Serializer:{instructor_serializer.errors},'
                                   f' Instructor data:{instructor_context} | Instance not created')

        update_event_in_webflow_service.delay({'chatroom_id': card_instance.id,
                                               'instructors_list': instructors_list,
                                               'update_type': event_webflow_update_types.INSTRUCTORS})
        update_event_instructors_in_cache.delay({'chatroom_id': card_instance.id,
                                                 'instructors_list': instructors_list})

        return {'success': True}

    def add_or_update_highlights(self, req_body: dict, api_key=None) -> dict:

        validated_request = ChatroomHelper.validate_add_or_update_highlights_request(req_body.get('chatroom_id'),
                                                                                     api_key)
        
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        card_instance = validated_request.get('card_instance')

        highlights = req_body.get('highlights', [])

        from collabmates_api.views import SyncChatrooms

        highlights_list = SyncChatrooms().fetch_event_highlights(card_instance.id)

        for data in highlights:
            highlight_context = {
                'card': card_instance.id,
                'highlight': data.get('highlight'),
                'url': data.get('url')

            }

            highlight_serializer = EventHighlightsSerializer(data=highlight_context)

            if highlight_serializer.is_valid():
                highlight_serializer.save()
                highlights_list.append(highlight_serializer.data)

            else:
                error_logger.error(f' Highlight Serializer:{highlight_serializer.errors},'
                                   f' Highlight data:{highlight_context} | Instance not created')

        update_event_in_webflow_service.delay({'chatroom_id': card_instance.id,
                                               'highlights_list': highlights_list,
                                               'update_type': event_webflow_update_types.HIGHLIGHTS})
        update_event_highlights_in_cache.delay({'chatroom_id': card_instance.id, 'highlights_list': highlights_list})

        return {'success': True}

    def add_or_update_member_testimonials(self, req_body: dict) -> dict:

        validated_request = ChatroomHelper.validate_add_or_update_highlights_request(req_body.get('chatroom_id'),
                                                                                     self.get_api_key())
        
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        card_instance = validated_request.get('card_instance')

        testimonials = req_body.get('testimonials', [])

        from collabmates_api.views import SyncChatrooms

        testimonials_list = SyncChatrooms().fetch_member_testimonials(card_instance.id)

        for data in testimonials:
            testimonial_context = {
                'card': card_instance.id,
                'member_name': data.get('member_name'),
                'testimonial': data.get('testimonial'),
                'url': data.get('url')

            }

            testimonial_serializer = EventMemberTestimonialsSerializer(data=testimonial_context)

            if testimonial_serializer.is_valid():
                testimonial_serializer.save()
                testimonials_list.append(testimonial_serializer.data)

            else:
                error_logger.error(f' Testimonial Serializer:{testimonial_serializer.errors},'
                                   f' Testimonial data:{testimonial_serializer} | Instance not created')

        update_event_in_webflow_service.delay({'chatroom_id': card_instance.id,
                                               'testimonials_list': testimonials_list,
                                               'update_type': event_webflow_update_types.TESTIMONIALS})
        update_event_member_testimonials_in_cache.delay({'chatroom_id': card_instance.id,
                                                         'testimonials_list': testimonials_list})

        return {'success': True}

    def add_or_update_event_faq(self, req_body: dict) -> dict:

        validated_request = ChatroomHelper.validate_add_or_update_highlights_request(req_body.get('chatroom_id'),
                                                                                     self.get_api_key())
        
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        card_instance = validated_request.get('card_instance')

        faq = req_body.get('faq', [])

        from collabmates_api.views import SyncChatrooms

        faqs_list = SyncChatrooms().fetch_event_FAQ(card_instance.id)

        for data in faq:
            faq_context = {
                'card': card_instance.id,
                'question': data.get('question'),
                'answer': data.get('answer')

            }

            faq_serializer = EventFAQSerializer(data=faq_context)

            if faq_serializer.is_valid():
                faq_serializer.save()
                faqs_list.append(faq_serializer.data)

            else:
                error_logger.error(f' FAQ Serializer:{faq_serializer.errors},'
                                   f' FAQ data:{faq_serializer} | Instance not created')

        update_event_in_webflow_service.delay({'chatroom_id': card_instance.id,
                                               'faqs_list': faqs_list,
                                               'update_type': event_webflow_update_types.FAQ})
        update_event_faq_in_cache.delay({'chatroom_id': card_instance.id, 'faqs_list': faqs_list})

        return {'success': True}

    def update_last_seen_event(self, community_id: str) -> dict:

        validated_request = ChatroomHelper.validate_update_last_seen_event_request(self.get_member_id())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        user_instance = validated_request.get('user_instance')

        if community_id or self.get_api_key():
            return self._update_last_seen_event_in_community(user_instance, community_id, api_key=self.get_api_key())

        last_seen_event_chatroom_id = get_last_seen_event_chatroom_id_for_user(user_id=user_instance.id)
        last_seen_event_chatroom_id_for_cohort_member = get_last_seen_non_member_access_event_for_user(
            user_id=user_instance.id)
        last_seen_event_chatroom_id_for_cm = get_last_seen_non_member_access_event_chatroom_id_for_community_managers(
            user_id=user_instance.id
        )
        if not last_seen_event_chatroom_id:
            last_seen_event_chatroom_id = 0

        if not last_seen_event_chatroom_id_for_cm:
            last_seen_event_chatroom_id_for_cm = 0

        if not last_seen_event_chatroom_id_for_cohort_member:
            last_seen_event_chatroom_id_for_cohort_member = 0

        last_seen_event_chatroom_id = max(last_seen_event_chatroom_id, last_seen_event_chatroom_id_for_cm,
                                          last_seen_event_chatroom_id_for_cohort_member)

        if not last_seen_event_chatroom_id:
            return {'success': True}

        event_nudge_filter = ModelUtilities.get_model_filter(EventNudge, {'user': user_instance})

        if event_nudge_filter:
            nudge_instance = event_nudge_filter[0]

            if nudge_instance.seen_event_chatroom_id != last_seen_event_chatroom_id:
                card_instance = ModelUtilities.get_model_instance_or_none(Collabcard,
                                                                          last_seen_event_chatroom_id)
                nudge_instance.seen_event_chatroom = card_instance
                nudge_instance.save()

        else:

            card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, last_seen_event_chatroom_id)
            EventNudge.create_instance({'card_instance': card_instance,
                                        'user_instance': user_instance})

        return {'success': True}

    @staticmethod
    def _update_last_seen_event_in_community(user_instance: User, community_id: str, api_key=None) -> dict:
        community: Community = SdkClient.get_community_instance_or_none(community_id, api_key)
        
        if not community:
            return {'success': False, 'error_message': "Invalid community-id"}
        
        community_id = community.id

        last_seen_event_chatroom_id: int = get_last_seen_event_chatroom_id_for_user(
            user_id=user_instance.id,
            community_id=community_id
        )
        last_seen_event_chatroom_id_for_cohort_member: int = get_last_seen_non_member_access_event_for_user(
            user_id=user_instance.id,
            community_id=community_id
        )
        last_seen_event_chatroom_id_for_cm: int = get_last_seen_non_member_access_event_chatroom_id_for_community_managers(
            user_id=user_instance.id,
            community_id=community_id
        )

        if not last_seen_event_chatroom_id:
            last_seen_event_chatroom_id = 0
        if not last_seen_event_chatroom_id_for_cm:
            last_seen_event_chatroom_id_for_cm = 0
        if not last_seen_event_chatroom_id_for_cohort_member:
            last_seen_event_chatroom_id_for_cohort_member = 0

        last_seen_event_chatroom_id = max(last_seen_event_chatroom_id, last_seen_event_chatroom_id_for_cm,
                                          last_seen_event_chatroom_id_for_cohort_member)

        if not last_seen_event_chatroom_id:
            return {'success': True}

        event_nudge_filter: list = ModelUtilities.get_model_filter(EventNudge, {
            'user': user_instance,
            'community': community
        })

        if event_nudge_filter:
            nudge_instance: EventNudge = event_nudge_filter[0]

            if nudge_instance.seen_event_chatroom_id != last_seen_event_chatroom_id:
                card_instance: Collabcard = ModelUtilities.get_model_instance_or_none(
                    Collabcard,
                    last_seen_event_chatroom_id
                )
                nudge_instance.seen_event_chatroom = card_instance
                nudge_instance.save()

        else:

            card_instance: Collabcard = ModelUtilities.get_model_instance_or_none(Collabcard, last_seen_event_chatroom_id)
            EventNudge.create_instance({'card_instance': card_instance,
                                        'user_instance': user_instance,
                                        'community_instance': community})

        return {'success': True}

    def fetch_unseen_count_in_event(self, community_id: str) -> dict:

        validated_request = ChatroomHelper.validate_fetch_unseen_count_in_event_request(self.get_member_id())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        user_instance = validated_request.get('user_instance')
                                                                                            
        if community_id or self.get_api_key():
            return self._fetch_unseen_event_count_in_community(user_instance, community_id, self.get_api_key())

        unseen_count = 0

        nudge_filter = ModelUtilities.get_model_filter(EventNudge, {'user': user_instance})

        if nudge_filter:
            card_instance = nudge_filter[0].seen_event_chatroom

            unseen_count = get_count_of_new_event_chatrooms_created_for_user(card_id=card_instance.id,
                                                                             user_id=user_instance.id)
            unseen_count += get_count_for_new_non_member_access_event_chatroom_community_managers(
                card_id=card_instance.id,
                user_id=user_instance.id)

            unseen_count += get_count_for_non_member_access_event_for_user_non_community_manager(
                card_id=card_instance.id,
                user_id=user_instance.id)

        return {'count': unseen_count, 'success': True}

    @staticmethod
    def _fetch_unseen_event_count_in_community(user_instance: User, community_id: str, api_key=None):

        community: Community = SdkClient.get_community_instance_or_none(community_id, api_key)
        if not community:
            return {'error_message': "Invalid community-id or api key", "success": False}
        
        community_id = community.id

        unseen_count: int = 0
        nudge_filter: list = ModelUtilities.get_model_filter(EventNudge, {
            'user': user_instance,
            'community': community
        })

        if nudge_filter:
            card_instance: Collabcard = nudge_filter[0].seen_event_chatroom

            unseen_count = get_count_of_new_event_chatrooms_created_for_user(
                card_id=card_instance.id,
                user_id=user_instance.id,
                community_id=community_id)
            unseen_count += get_count_for_new_non_member_access_event_chatroom_community_managers(
                card_id=card_instance.id,
                user_id=user_instance.id,
                community_id=community_id)
            unseen_count += get_count_for_non_member_access_event_for_user_non_community_manager(
                card_id=card_instance.id,
                user_id=user_instance.id,
                community_id=community_id)

        return {'count': unseen_count, 'success': True}

    def fetch_link_for_event(self, is_edit_mode) -> dict:

        validated_request = ChatroomHelper.validate_fetch_link_for_event_request(self.get_member_id(),
                                                                                 self.get_chatroom_id(),
                                                                                 self.get_api_key())
        
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        user_instance = validated_request.get('user_instance')
        card_instance = validated_request.get('card_instance')

        member_state = Members.get_community_member_state(card_instance.community, user_instance)

        is_user_registered = ModelUtilities.is_model_filter_exists(
            collabcardState,
            {
                'user': user_instance,
                'card': card_instance,
                'attending_status': True
            }
        )

        chatroom_context = {}

        if (is_edit_mode and (user_instance == card_instance.user or member_state == member_states.ADMIN)):

            self._fill_online_link_for_event(chatroom_context, card_instance)
            return chatroom_context

        if TimeUtilities.current_time_in_milliseconds() >= card_instance.date_time:

            if not card_instance.is_paid and not is_user_registered:
                self._fill_online_link_for_event(chatroom_context, card_instance)
                return chatroom_context

        if TimeUtilities.current_time_in_milliseconds() >= \
                (card_instance.date_time - card_instance.online_link_enable_before):

            if (not card_instance.is_paid and is_user_registered) or \
                    (card_instance.is_paid and ChatroomHelper.is_online_event_link_verified_for_user(card_instance,
                                                                                                     user_instance)) \
                    or (card_instance.is_paid and (member_state == member_states.ADMIN or \
                                                   user_instance == card_instance.user)):
                self._fill_online_link_for_event(chatroom_context, card_instance)

            return chatroom_context

        return {'error_message': "Link doesn’t exists"}

    def fetch_user_all_events(self, page, attending_status, has_content, past_events=False, community_id=None) -> dict:

        validated_request = ChatroomHelper.validate_fetch_user_all_events_request(self.get_member_id(),
                                                                                  self.get_api_key())
        
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        user_instance = validated_request.get('user_instance')                        

        event_filter_dict = self.get_filter_dict_for_fetch_all_events(user_instance=user_instance,
                                                                      attending_status=attending_status,
                                                                      has_content=has_content,
                                                                      past_events=past_events,
                                                                      community_id=community_id)

        member_accessible_chatroom_queryset = self.fetch_events_queryset(past_events=past_events,
                                                                         event_filter_dict=event_filter_dict)

        cm_chatroom_queryset = self.fetch_non_member_access_events_for_community_manager_queryset(
            user_instance=user_instance,
            past_events=past_events,
            event_filter_dict=event_filter_dict
        )

        cohort_access_chatroom_queryset = self.fetch_events_member_cohort_access(user_instance=user_instance,
                                                                                 past_events=past_events,
                                                                                 event_filter_dict=event_filter_dict)

        chatroom_queryset = member_accessible_chatroom_queryset | cm_chatroom_queryset | cohort_access_chatroom_queryset

        if not past_events:
            chatroom_queryset = chatroom_queryset.order_by('card__date_time')

        else:
            chatroom_queryset = chatroom_queryset.order_by('-card__date_time')

        chatroom_list = ModelUtilities.paginate_queryset(chatroom_queryset, page, paginate_by=5)

        chatroom_member_instance = ChatroomMemberImpl(member_id=user_instance.id)
        chatroom_list = chatroom_member_instance.process_event_chatroom_list(chatroom_list)

        return {'events': chatroom_list, 'success': True}

    def fetch_user_all_events_meta(self, past_events=False, community_id=None):

        validated_request = ChatroomHelper.validate_fetch_user_all_events_meta_request(self.get_member_id(),
                                                                                       community_id,
                                                                                       self.get_api_key())
        
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        community_instance = validated_request.get('community_instance')

        is_user_cm = Members.is_member_community_promoter(community_instance, user_instance)

        event_filter_dict = self.get_filter_dict_for_fetch_all_events(user_instance=user_instance,
                                                                      past_events=past_events,
                                                                      community_id=community_id)

        member_accessible_chatroom_queryset = self.fetch_events_queryset(past_events=past_events,
                                                                         event_filter_dict=event_filter_dict)

        # If user is CM of community show all events having access 0 else filter using member group
        if is_user_cm:
            non_member_access_chatroom_queryset = self.fetch_non_member_access_events_for_community_manager_queryset(
                past_events=past_events,
                event_filter_dict=event_filter_dict,
                user_instance=user_instance
            )

        else:
            non_member_access_chatroom_queryset = self.fetch_events_member_cohort_access(
                user_instance=user_instance, past_events=past_events, event_filter_dict=event_filter_dict)

        chatroom_queryset = member_accessible_chatroom_queryset | non_member_access_chatroom_queryset

        if not past_events:
            chatroom_queryset = chatroom_queryset.order_by('card__date_time')

        else:
            chatroom_queryset = chatroom_queryset.order_by('-card__date_time')

        response_dict = ChatroomImpl.process_response_dict_for_fetch_all_event_meta(chatroom_queryset, past_events,
                                                                                    is_user_cm)

        return response_dict

    @staticmethod
    def process_response_dict_for_fetch_all_event_meta(chatroom_queryset, past_events=False, is_user_cm=False):

        response_dict = {
            'success': True
        }

        if not chatroom_queryset:

            if not past_events:
                upcoming_event_empty_view = {
                    'image': IMAGE_LINK_FOR_NO_EVENTS_FOUND,
                    'title': TITLE_FOR_NO_UPCOMING_EVENTS_FOUND,
                }

                if is_user_cm:
                    upcoming_event_empty_view['sub_title'] = SUB_TITLE_FOR_CM_VIEW_NO_UPCOMING_EVENTS_FOUND

                else:
                    upcoming_event_empty_view['sub_title'] = SUB_TITLE_FOR_MEMBER_VIEW_NO_UPCOMING_EVENTS_FOUND

                response_dict['upcoming_event_empty_view'] = upcoming_event_empty_view

            else:
                past_event_empty_view = {
                    'image': IMAGE_LINK_FOR_NO_EVENTS_FOUND,
                    'title': TITLE_FOR_NO_PAST_EVENTS_FOUND,
                    'sub_title': SUB_TITLE_FOR_NO_PAST_EVENTS_FOUND
                }

                response_dict['past_event_empty_view'] = past_event_empty_view

        else:
            registered_filter = ModelUtilities.get_model_filter(
                collabcardState,
                {
                    'id__in': [chatroom.id for chatroom in chatroom_queryset],
                    'attending_status': True
                }
            )

            response_dict['registered_filter_show'] = True if registered_filter else False

            event_attachment_filter = ModelUtilities.get_model_filter(
                Collabcard,
                {
                    'id__in': [chatroom.card.id for chatroom in chatroom_queryset],
                    'has_event_recording': True
                }
            )

            response_dict['event_attachment_filter_show'] = True if event_attachment_filter else False

        return response_dict

    def attend_event(self, req_body, api_key=None) -> dict:
            
        validated_request = ChatroomHelper.validate_attend_event_request(self.get_member_id(),
                                                                         req_body.get('chatroom_id'),
                                                                         api_key)
        
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        user_instance = validated_request.get('user_instance')
        card_instance = validated_request.get('card_instance')

        status = req_body.get('attending_status', False)

        community_instance = card_instance.community

        member_state = Members.get_community_member_state(community_instance, user_instance)

        ChatroomHelper.auto_follow_chatroom(card_instance, user_instance, community_instance,
                                            func_dict={'attending_status': status}, member_state=member_state)

        update_event_attendees.delay({
            'chatroom_id': card_instance.id,
            'user_id': user_instance.id,
            'status': status
        })

        # if member_state == member_states.GUEST:
        #     ChatroomHelper.send_event_creation_mail.delay(card_instance.id, send_to_members=False,
        #                                                   user_list=[user_instance.id])

        if status:
            payload_for_app_and_email_notification = {
                'chatroom': card_instance.id,
                'user': user_instance.id,
                'attending_status': status
            }

            send_app_notification_for_event_type.delay(payload_for_app_and_email_notification, EVENT_TYPE.REGISTRATION)
            send_email_notification_for_event_type.delay(payload_for_app_and_email_notification, EVENT_TYPE.REGISTRATION)

            payload_for_calendar_invite = {
                'chatroom': card_instance.id,
            }

            send_calender_invite_for_event_type.delay(payload_for_calendar_invite, EVENT_TYPE.REGISTRATION,
                                                      send_to_members=False, user_list=[user_instance.id],
                                                      calendar_invite_type=CALENDAR_INVITE_TYPE.APPEND_ATTENDEES)

        ChatroomHelper.run_async_task_related_to_event_chatroom_attend_analytics(card_instance,
                                                                                 user_instance, status)

        return {'success': True}

    def set_event_attended(self) -> dict:

        validated_request = ChatroomHelper.validate_set_event_attended_request(self.get_member_id(),
                                                                               self.get_chatroom_id(),
                                                                               self.get_api_key())
        
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        user_instance = validated_request.get('user_instance')
        card_instance = validated_request.get('card_instance')

        ModelUtilities.model_update(collabcardState,
                                    {'card': card_instance, 'user': user_instance},
                                    {'attended': True, 'updated_at': TimeUtilities.current_time_in_sec()})

        send_analytics_on_event_attend_link_click.delay(card_instance.id, user_instance.id)

        return {'success': True}

    def toggle_member_message_post(self, value) -> dict:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "In-valid user id"}

        card_filter = ModelUtilities.get_model_filter(Collabcard, {'id': self.get_chatroom_id()})

        if not card_filter:
            return {'success': False, 'error_message': "In-valid chatroom id"}

        card_instance = card_filter[0]

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': card_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of community"}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return {'success': False, 'error_message': "User can’t enable/disable member messaging setting option"}

        card_filter.update(member_can_message=value, updated_at=TimeUtilities.current_time_in_sec())

        # toggle user chatroom settings with setting type as member_can_message for all the members of this chatroom
        toggle_user_chatroom_settings.delay(card_instance.id, CHATROOM_USER_SETTINGS_MEMBER_CAN_MESSAGE, value)

        send_chatroom_updated_analytics_data.delay(self.get_chatroom_id(),
                                                   int(self.get_member_id()),
                                                   {'has_send_permission': True,
                                                    'members_can_send_messages': value})

        return {'success': True}

    def fetch_chatroom_settings(self) -> dict:
        validated_req = ChatroomViewHelper.validate_fetch_chatroom_settings_request(self.get_member_id(),
                                                                                    self.get_chatroom_id())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        card_instance = validated_req.get('card_instance')
        community_instance = card_instance.community

        if VersionUtilities.check_version(self.get_request_platform(), self.get_version_code(),
                                          VersionUtilities.new_chatroom_settings, self.get_sdk_source()):
            chatroom_settings = settings_for_chatroom_with_revamp.copy()
            admin_has_delete_right = check_admin_delete_right(user=user_instance,
                                                              community=community_instance)

            if admin_has_delete_right:
                chatroom_settings.append(delete_chatroom)

            if not card_instance.is_secret:
                chatroom_settings.append(auto_joined_by_all_members)
                chatroom_settings.append(manage_permissions)
                chatroom_settings.append(pin_chatroom)

            if VersionUtilities.check_version(self.get_request_platform(),
                                              self.get_version_code(),
                                              VersionUtilities.tag_only_participants):
                tag_participants_setting = {
                    'id': chatroom_setting_states.TAG_ONLY_PARTICIPANTS_ID,
                    'title': chatroom_setting_states.TAG_ONLY_PARTICIPANTS_TITLE
                }
                chatroom_settings.append(tag_participants_setting)

        else:
            chatroom_settings = settings_for_chatroom.copy()
            admin_has_delete_right = check_admin_delete_right(user=user_instance,
                                                              community=community_instance)

            if card_instance.is_secret or (card_instance.type not in [card_types.CARD_NORMAL, card_types.CARD_POLL,
                                                                      card_types.CARD_PURPOSE]):
                chatroom_settings.remove(pin_chatroom)

            if admin_has_delete_right and (card_instance.type not in [card_types.CARD_PURPOSE]):
                chatroom_settings.append(delete_chatroom)

        settings_list = ChatroomHelper.get_settings_for_chatroom(chatroom_settings, card_instance)

        return {'success': True, 'settings': settings_list}

    def add_members_to_chatroom(self, chatroom_participants, uuids = None) -> dict:
        validated_req = ChatroomViewHelper.validate_add_members_to_open_chatroom(self.get_member_id(),
                                                                                 self.get_chatroom_id(),
                                                                                 chatroom_participants,
                                                                                 uuids)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        cache_key = CHATROOM_PARTICIPANTS_CREATED_CACHE_KEY.format(self.get_chatroom_id())
        are_chatroom_participants_created = CacheImpl.get_cache(cache_key)

        if all(['are_participants_created' in are_chatroom_participants_created,
                not are_chatroom_participants_created.get('are_participants_created')]):
            return ResponseUtilities.get_impl_error_context('Chatroom creation in progress. Try again after some time.',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        card_instance = validated_req.get('card_instance')

        if uuids:
            chatroom_participants = ModelUtilities.get_valid_user_ids_from_uuids(uuids, card_instance.community_id)

        else:
            # Support for user_unique_ids in chatroom participants parameter
            chatroom_participants = ModelUtilities.get_valid_member_ids(chatroom_participants,
                                                                        community_id=card_instance.community_id)

        ChatroomHelper.bulk_follow_chatroom_users(card_instance, chatroom_participants)

        conversation_impl.ConversationHelper.create_conversation_state(card_instance, user_instance,
                                                                       conversation_states.CONVERSATION_ADD_ALL_MEMBERS,
                                                                       added_member_count=len(chatroom_participants))

        send_participants_added_in_chatroom_analytics_data.delay(self.get_chatroom_id(), int(self.get_member_id()))

        chatroom_update_analytics = {
            'added_future_members': card_instance.auto_follow_done and card_instance.include_members_later
        }

        send_chatroom_updated_analytics_data.delay(self.get_chatroom_id(), int(self.get_member_id()),
                                                   chatroom_update_analytics)

        return {'success': True}

    def update_files(self, req_body):
        validated_req = ChatroomViewHelper.validate_update_files_request(self.get_member_id(), self.get_chatroom_id())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        card_instance = validated_req.get('card_instance')
        files_list = req_body.get('attachments', [])

        ModelUtilities.delete_record_in_model(Card_Attachment,
                                              {'collabcard_id': card_instance})

        for file_data in files_list:
            save_chatroom_attachments(card_instance, file_data)

        files_count = len(files_list)
        ModelUtilities.model_update(Collabcard, {'id': card_instance.id},
                                    {'has_files': True, 'attachment_count': files_count,
                                     'attachments_uploaded': files_count != 0,
                                     'updated_at': TimeUtilities.current_time_in_milliseconds()})
        ModelUtilities.model_update(collabcardState,
                                    {'card': card_instance},
                                    {'updated_at': TimeUtilities.current_time_in_sec()})

        update_event_in_webflow_service.delay({'chatroom_id': card_instance.id,
                                               'update_type': event_webflow_update_types.FILE})

        return {'chatroom': ChatroomHelper.compute_chatroom_response(card_instance,
                                                                     user_instance, card_instance.community),
                'success': True}

    def fetch_event_link_for_dashboard(self) -> dict:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user-id"}

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, self.get_chatroom_id())

        if not card_instance:
            return {'success': False, 'error_message': "Invalid chatroom id"}

        if Members.get_community_member_state(card_instance.community, user_instance) != member_states.ADMIN:
            return {'success': False, 'error_message': "Only promoter can access this link"}

        chatroom_context = {'success': True}
        self._fill_online_link_for_event(chatroom_context, card_instance)

        return chatroom_context

    def update_access_without_subscription(self, value) -> dict:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        card_filter = ModelUtilities.get_model_filter(Collabcard, {'id': self.get_chatroom_id()})

        if not card_filter:
            return {'success': False, 'error_message': "Invalid chatroom id"}

        card_instance = card_filter[0]

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': card_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of community"}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return {'success': False,
                    'error_message': "User can’t enable/disable access without subscription option"}

        card_filter.update(access_without_subscription=value, updated_at=TimeUtilities.current_time_in_milliseconds())

        update_models_for_syncing_apis(SyncTypes.CHATROOM, {'card': card_instance}, {})

        send_chatroom_updated_analytics_data.delay(self.get_chatroom_id(),
                                                   int(self.get_member_id()),
                                                   {'accessible_without_subscription': value})

        return {'success': True}

    def remove_cohort_from_chatroom(self, request_body) -> dict:
        cohort_id = request_body.get('cohort_id')
        chatroom_id = request_body.get('chatroom_id')

        validated_req = ChatroomHelper.validate_remove_chatroom_cohort_request(self.get_member_id(),
                                                                               chatroom_id,
                                                                               cohort_id)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_instance = validated_req.get('chatroom_instance')
        self.set_chatroom_id(chatroom_instance.id)

        chatroom_cohort_filter_dict = {
            'cohort_id': cohort_id,
            'chatroom_id': self.get_chatroom_id()
        }

        chatroom_cohort_filter = ModelUtilities.get_model_filter(ChatroomCohort, chatroom_cohort_filter_dict)

        if not chatroom_cohort_filter:
            return ResponseUtilities.get_impl_error_context('Cohort is not a part of this chatroom',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        filter_dict = {
            'chatroom_id': self.get_chatroom_id(),
            'chatroom__is_secret': True
        }

        removed_member_count = 0

        related_cohort_ids = ModelUtilities.get_model_filter(ChatroomCohort, filter_dict).values_list('cohort_id',
                                                                                                      flat=True)

        other_cohort_participants = ModelUtilities.get_model_filter(CohortMember, {'cohort_id__in': related_cohort_ids}) \
            .exclude(cohort_id=cohort_id).values_list('user_id', flat=True)

        cohort_member_ids = ModelUtilities.get_model_filter(CohortMember, {'cohort_id': cohort_id}) \
            .values_list('user_id', flat=True)

        for cohort_member_id in cohort_member_ids:

            if cohort_member_id not in other_cohort_participants:

                try:
                    chatroom_manager = ChatroomImpl(self.get_member_id(), chatroom_id=self.get_chatroom_id())
                    chatroom_manager.leave_secret_chatroom(cohort_member_id)
                    removed_member_count += 1

                except Exception as e:
                    error_logger.error(e.args)

        chatroom_cohort_filter.delete()

        return {'success': True, 'removed_participant_count': removed_member_count}

    def add_cohort_to_chatroom(self, request_body) -> dict:
        cohort_ids = request_body.get('cohort_ids')
        chatroom_id = request_body.get('chatroom_id')
        add_existing_members = request_body.get('add_existing_members', False)

        validated_req = ChatroomHelper.validate_add_chatroom_cohort_request(self.get_member_id(),
                                                                            chatroom_id,
                                                                            cohort_ids)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_instance = validated_req.get('chatroom_instance')
        create_chatroom_cohort_instances(chatroom_instance.id, cohort_ids)

        if chatroom_instance.is_secret and add_existing_members:
            ChatroomHelper.add_cohort_members_to_secret_chatroom(self.get_member_id(),
                                                                 chatroom_instance.id,
                                                                 cohort_ids)

        return {'success': True}

    def fetch_access_for_chatroom(self) -> dict:

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, self.get_chatroom_id())

        if not card_instance:
            return {'success': False, 'error_message': "Invalid chatroom id"}

        community_instance = card_instance.community

        community_object = CommunitySerializerV1(community_instance).data

        created_by = get_community_creator(community_instance)
        admin_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance.id,
                                                                 'state': member_states.ADMIN})
        community_object['created_by'] = created_by
        community_object['promoters_count'] = admin_filter.count()

        chatroom_object = {'access_without_subscription': card_instance.access_without_subscription,
                           'community': community_object, 'chatroom_type': card_instance.type}

        if self.get_member_id():
            user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

            if not user_instance:
                return {'success': False, 'error_message': "Invalid User ID"}

            removed_member_filter = ModelUtilities.get_model_filter(removedMembers,
                                                                    {'community': community_instance,
                                                                     'member': user_instance})

            if removed_member_filter:
                remove_instance = removed_member_filter[0]

                chatroom_object['remove_state'] = remove_instance.removed_state

        return chatroom_object

    def fetch_chatroom_participants(self, participant_name: str = None, page: int = None, page_size: int = None):

        validated_req = ChatroomHelper.validate_fetch_participants_meta_request(self.get_member_id(),
                                                                                self.get_chatroom_id())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        card_instance = validated_req.get('card_instance')

        community_instance = card_instance.community
        can_edit_participant = False

        member_filter = ModelUtilities.get_model_filter(Members,
                                                        {'community_id': community_instance,
                                                         'member_id': user_instance})

        if member_filter:

            member_instance = member_filter[0]
            is_cm = member_instance.state == member_states.ADMIN

            if is_cm:
                can_edit_participant = True

        filter_dict = {
            'card': card_instance,
            'follow_status': True,
            'is_tagged': False,
            'remove': None,
            'user__userinfo__is_guest': False
        }

        total_participants_list = ModelUtilities.get_model_filter(collabcardState, filter_dict).values_list('user_id',
                                                                                                            flat=True)

        pagination_version_check = VersionUtilities.check_version(self.get_request_platform(),
                                                                  self.get_version_code(),
                                                                  VersionUtilities.participants_meta_pagination,
                                                                  self.get_sdk_source())

        non_pagination_version_check = VersionUtilities.check_version(
            self.get_request_platform(), self.get_version_code(), VersionUtilities.participants_meta_without_pagination,
            self.get_sdk_source())

        order_by_name = False

        if pagination_version_check and (not non_pagination_version_check):
            order_by_name = True

        member_data = MemberCommunityImpl.fetch_members_based_on_user_list(total_participants_list, community_instance,
                                                                           page=page, page_size=page_size,
                                                                           member_name_search_string=participant_name,
                                                                           order_by_name=order_by_name, 
                                                                           sdk_client_info_flag=True)
        participant_list = MemberCommunityHelper.extract_member_tagging_data(member_data, sdk_client_info_flag=True)

        response_dict = {
            'success': True,
            'participants': participant_list,
            'can_edit_participant': can_edit_participant
        }

        if pagination_version_check and (not non_pagination_version_check):
            participants_count = ChatroomHelper.get_participants_count_in_chatroom(card_instance)
            response_dict['total_participants_count'] = participants_count

        return response_dict

    @staticmethod
    def update_chatroom_or_conversation_instance_with_event_attachments_metadata(req_body, member_id, api_key=None):
            
        if req_body.get('chatroom_id'):
            
            validated_request = ChatroomHelper.validate_upload_recordings_meta_request(req_body.get('chatroom_id'),
                                                                                       api_key)
            
            if validated_request.get('error_message'):
                return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            chatroom_instance = validated_request.get('card_instance')

            recording_url_og_tags = UriTagsImpl(req_body.get('recording_url')).get_tags_from_uri() \
                if req_body.get('recording_url') \
                else {}

            if req_body.get('recording_url_title'):
                recording_url_og_tags['title'] = req_body.get('recording_url_title')

            payload_for_email_comms = {
                'chatroom': chatroom_instance.id,
                'user': int(member_id)
            }

            send_email_notification_for_event_type.delay(payload_for_email_comms, EVENT_TYPE.POST_EVENT_ATTACHMENTS)
            send_app_notification_on_event_attachment.delay(chatroom_instance.id, chatroom_instance.has_event_recording)

            create_dict = ChatroomHelper.get_create_dict_for_creating_url_instance_for_event(
                req_body,
                recording_url_og_tags
            )

            create_dict['chatroom_id'] = chatroom_instance

            event_recording_url_instance = EventRecordingsURL.create_instance(create_dict)

            event_url_serializer = EventRecordingsURLSerializer(event_recording_url_instance)

            chatroom_instance.has_event_recording = True
            chatroom_instance.save()

            update_models_for_syncing_apis(
                SyncTypes.CHATROOM,
                {'card': chatroom_instance},
                {}
            )

            member_data = {
                'member_id': member_id,
                'current_user_id': member_id,
                'state_instance': None
            }

            chatroom_serializer_local = GetChatroomInstanceSerializer(chatroom_instance, \
                                                                      context=member_data, many=False)

            chatroom_serializer = CollabcardSerializer(card=chatroom_instance, user=member_id)

            res = {
                'success': True,
                'event_url': event_url_serializer.data,
                'chatroom': chatroom_serializer,
                'chatroom_local': chatroom_serializer_local.data

            }
            return res

        elif req_body.get('conversation_id'):
            conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers,
                                                                              req_body.get('conversation_id'))

            if not conversation_instance:
                res = get_error_context(False, "Invalid conversation_id")
                return res

            recording_url_og_tags = UriTagsImpl(req_body.get('recording_url')).get_tags_from_uri() \
                if req_body.get('recording_url') \
                else {}

            if req_body.get('recording_url_title'):
                recording_url_og_tags['title'] = req_body.get('recording_url_title')

            create_dict = ChatroomHelper.get_create_dict_for_creating_url_instance_for_event(
                req_body,
                recording_url_og_tags
            )

            create_dict['conversation_id'] = conversation_instance

            event_recording_url_instance = EventRecordingsURL.create_instance(create_dict)

            event_url_serializer = EventRecordingsURLSerializer(event_recording_url_instance)

            conversation_instance.has_event_recording = True
            conversation_instance.save()

            update_models_for_syncing_apis(
                SyncTypes.CONVERSATION,
                {'id': conversation_instance.id},
                {}
            )

            conversation_context = {
                "current_user_id": member_id,
                "fetch_reply": True
            }

            conversation_serializer = CardAnswersDBSyncSerializer(conversation_instance, \
                                                                  context=conversation_context, many=False)

            res = {
                "success": True,
                'event_url': event_url_serializer.data,
                "conversation": conversation_serializer.data
            }
            return res

        res = {
            "success": False
        }
        return res

    @staticmethod
    def add_event_attachments(req_body, member_id, api_key=None):

        validated_request = ChatroomHelper.validate_add_event_attachments_request(api_key)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        serializer = EventRecordingsAttachmentsSerializer(data=req_body)

        if serializer.is_valid():
            serializer.save()

            if req_body.get('chatroom_id'):
                event_obj = ModelUtilities.get_model_instance_or_none(
                    Collabcard,
                    req_body.get('chatroom_id')
                )

                payload_for_email_comms = {
                    'chatroom': event_obj.id,
                    'user': int(member_id)
                }

                send_email_notification_for_event_type.delay(payload_for_email_comms, EVENT_TYPE.POST_EVENT_ATTACHMENTS)
                send_app_notification_on_event_attachment.delay(event_obj.id, event_obj.has_event_recording)

                event_obj.has_event_recording = True
                event_obj.save()

                update_models_for_syncing_apis(
                    SyncTypes.CHATROOM,
                    {'card': event_obj},
                    {}
                )

                member_data = {
                    'member_id': member_id,
                    'current_user_id': member_id,
                    'state_instance': None
                }

                event_serializer_local = GetChatroomInstanceSerializer(event_obj, context=member_data, many=False)

                event_serializer = CollabcardSerializer(card=event_obj, user=member_id, 
                                                        sdk_client_info_flag=True)

                res = {
                    'success': True,
                    'event_attachment': serializer.data,
                    'chatroom': event_serializer,
                    'chatroom_local': event_serializer_local.data
                }

            elif req_body.get('conversation_id'):
                event_obj = ModelUtilities.get_model_instance_or_none(
                    card_answers,
                    req_body.get('conversation_id')
                )

                event_obj.has_event_recording = True
                event_obj.save()

                update_models_for_syncing_apis(
                    SyncTypes.CONVERSATION,
                    {'id': event_obj.id},
                    {}
                )

                conversation_context = {
                    "current_user_id": member_id,
                    "fetch_reply": True
                }

                event_serializer = CardAnswersDBSyncSerializer(event_obj, context=conversation_context, many=True)

                res = {
                    "success": True,
                    'event_attachment': serializer.data,
                    "conversation": event_serializer.data
                }

            return res, True
        
        error_logger.error(serializer.errors.__str__())

        res = {
            "success": False,
            "error_message": "Invalid request body"
        }

        return res, False

    @staticmethod
    def delete_event_attachment_metadata_from_chatroom_or_conversation_instance(req_body, member_id, api_key=None):
        
        validated_request = ChatroomHelper.validate_delete_event_attachments_meta_request(req_body.get('id'),
                                                                                          api_key)
       
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        event_url_obj = validated_request.get('event_url_obj')

        if req_body.get('chatroom_id'):
            chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, req_body.get('chatroom_id'))

            if not chatroom_instance:
                res = get_error_context(False, "Invalid chatroom_id")
                return res

            if event_url_obj.chatroom_id != chatroom_instance:
                res = get_error_context(False, "Incorrect chatroom_id/id")
                return res

            event_obj = chatroom_instance
            event_attachment_count, event_url_count = ChatroomHelper.get_attachments_count_for_event_obj(
                chatroom_instance=event_obj
            )

        elif req_body.get('conversation_id'):
            conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers,
                                                                              req_body.get('conversation_id'))

            if not conversation_instance:
                res = get_error_context(False, "Invalid conversation_id")
                return res

            if event_url_obj.conversation_id != conversation_instance:
                res = get_error_context(False, "Incorrect conversation_id/id")
                return res

            event_obj = conversation_instance
            event_attachment_count, event_url_count = ChatroomHelper.get_attachments_count_for_event_obj(
                conversation_instance=event_obj
            )

        if event_attachment_count > 0 or event_url_count > 1:
            event_obj.has_event_recording = True

        else:
            event_obj.has_event_recording = False

        event_obj.save()
        event_url_obj.delete()

        res = {
            "success": True,
        }

        if req_body.get('chatroom_id'):

            update_models_for_syncing_apis(
                SyncTypes.CHATROOM,
                {'card': event_obj},
                {}
            )

            member_data = {
                'member_id': member_id,
                'current_user_id': member_id,
                'state_instance': None
            }

            event_serializer_local = GetChatroomInstanceSerializer(event_obj, \
                                                                   context=member_data, many=False)

            event_serializer = CollabcardSerializer(card=event_obj, user=member_id)

            res['chatroom'] = event_serializer
            res['chatroom_local'] = event_serializer_local.data

        elif req_body.get('conversation_id'):

            update_models_for_syncing_apis(
                SyncTypes.CONVERSATION,
                {'id': event_obj.id},
                {}
            )

            conversation_context = {
                "current_user_id": member_id,
                "fetch_reply": True
            }

            event_serializer = CardAnswersDBSyncSerializer(event_obj, \
                                                           context=conversation_context, many=False)

            res['conversation'] = event_serializer.data

        return res

    @staticmethod
    def delete_event_attachments(event_attachment_id, member_id, api_key=None): 

        validated_request = ChatroomHelper.validate_delete_event_attachments_request(event_attachment_id, api_key)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        event_attachment_obj = validated_request.get('event_attachment_obj')   

        if event_attachment_obj.chatroom_id:
            event_obj = event_attachment_obj.chatroom_id
            event_attachment_count, event_url_count = ChatroomHelper.get_attachments_count_for_event_obj(
                chatroom_instance=event_obj
            )

        elif event_attachment_obj.conversation_id:
            event_obj = event_attachment_obj.conversation_id
            event_attachment_count, event_url_count = ChatroomHelper.get_attachments_count_for_event_obj(
                conversation_instance=event_obj
            )

        if event_attachment_count > 1 or event_url_count > 0:
            event_obj.has_event_recording = True

        else:
            event_obj.has_event_recording = False

        event_obj.save()
        event_attachment_obj.delete()

        res = {
            'success': True
        }

        if event_attachment_obj.chatroom_id:

            update_models_for_syncing_apis(
                SyncTypes.CHATROOM,
                {'card': event_obj},
                {}
            )

            member_data = {
                'member_id': member_id,
                'current_user_id': member_id,
                'state_instance': None
            }

            event_serializer_local = GetChatroomInstanceSerializer(event_obj, \
                                                                   context=member_data, many=False)

            event_serializer = CollabcardSerializer(card=event_obj, user=member_id)

            res['chatroom'] = event_serializer
            res['chatroom_local'] = event_serializer_local.data

        elif event_attachment_obj.conversation_id:

            update_models_for_syncing_apis(
                SyncTypes.CONVERSATION,
                {'id': event_obj.id},
                {}
            )

            conversation_context = {
                "current_user_id": member_id,
                "fetch_reply": True
            }

            event_serializer = CardAnswersDBSyncSerializer(event_obj, \
                                                           context=conversation_context, many=False)

            res['conversation'] = event_serializer.data

        return res

    def publish_event_webflow(self, req_body) -> dict:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': 'Invalid member_id'}

        validated_req_body = ChatroomHelper.validate_publish_event_webflow_req_body(req_body)

        if not validated_req_body.get('success'):
            return validated_req_body

        validated_req_body = validated_req_body.get('req_body')

        event_meta_data = {
            'domains': validated_req_body.get('domains')
        }

        webflow_response = WebflowImpl.publish_event_in_webflow(event_meta_data, validated_req_body.get('site_id'))

        return {'success': True, 'data': webflow_response}

    @staticmethod
    def fetch_link_for_events_list(is_edit_mode, member_id, chatroom_ids, api_key=None):

        final_response = {}

        validated_request = ChatroomHelper.validate_fetch_link_for_events_list_request(member_id, chatroom_ids, api_key)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        chatrooms_link_objects = []

        for chatroom_id in chatroom_ids:
            chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=chatroom_id)
            response_context = chatroom_manager.fetch_link_for_event(is_edit_mode)

            if response_context.get('error_message'):
                chatrooms_link_objects.append({
                    'chatroom_id': chatroom_id,
                    'error_message': response_context['error_message']
                })

            else:
                response_context['chatroom_id'] = chatroom_id
                chatrooms_link_objects.append(response_context)

        return {'success': True, 'chatroom_links': chatrooms_link_objects}

    def change_chatroom_type(self, req_body) -> dict:

        validated_req = ChatroomViewHelper.validate_change_chatroom_type_request(self.get_member_id(),
                                                                                 req_body)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        card_instance = validated_req.get('card_instance')

        self.set_chatroom_id(req_body.get('chatroom_id'))

        is_secret = req_body.get('is_secret')

        if is_secret == card_instance.is_secret:
            return {'success': True}

        if (card_instance.created_at + TimeUtilities.MILLI_SEC_IN_AN_HOUR) > TimeUtilities.current_time_in_milliseconds():
            return ResponseUtilities.get_impl_error_context('Action not allowed, try again after 1 hour',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        conversion_filter = ModelUtilities.get_model_filter(ChatroomSecretTypeConversion, {'chatroom': card_instance})

        if conversion_filter:
            last_conversion_time = conversion_filter[0].converted_at

            if last_conversion_time + TimeUtilities.MILLI_SEC_IN_A_DAY > TimeUtilities.current_time_in_milliseconds():
                return ResponseUtilities.get_impl_error_context('Action not allowed, try again after a few hours.',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)

        ChatroomHelper.set_chatroom_conversion_type_status_key_in_cache(self.get_chatroom_id(), True)

        if is_secret:
            convert_chatroom_to_secret_chatroom.delay(self.get_chatroom_id())

        else:
            convert_chatroom_to_open_chatroom.delay(self.get_chatroom_id())

        return {'success': True}

    def get_change_chatroom_type_status(self) -> dict:
        validated_req = ChatroomViewHelper.validate_change_chatroom_type_status_request(self.get_member_id(),
                                                                                        self.get_chatroom_id())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        change_chatroom_status = ChatroomHelper.get_chatroom_conversion_type_status_of_chatroom_from_cache(
            self.get_chatroom_id())

        if change_chatroom_status:
            return {
                'success': True,
                'is_converting': change_chatroom_status,
                'success_message': 'Chatroom conversion in progress!'
            }

        return {'success': True, 'is_converting': change_chatroom_status}

    def create_dm_chatroom(self, req_body) -> dict:
        validated_request = ChatroomViewHelper.validate_create_dm_chatroom_request(self.get_member_id(), req_body,
                                                                                   self.get_api_key())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        community_instance = validated_request.get('community_instance')
        member_instance = validated_request.get('member_instance')
        custom_tag = validated_request.get('custom_tag')

        filter_dict = {
            'is_private': True,
            'type': card_types.CARD_DIRECT_MESSAGE,
            'community': community_instance,
            'user__in': [user_instance, member_instance],
            'chatroom_with_user__in': [user_instance, member_instance]
        }

        card_filter = ModelUtilities.get_model_filter(Collabcard, filter_dict)

        if card_filter:
            chatroom_instance = card_filter[0]

        else:
            user_member_state = ChatroomHelper.fetch_member_state_in_community(user=user_instance,
                                                                               community=community_instance)
            member_state = ChatroomHelper.fetch_member_state_in_community(user=member_instance,
                                                                          community=community_instance)

            card_content = {}
            chatroom_name = DM_CHATROOM_NAME
            chatroom_type = card_types.CARD_DIRECT_MESSAGE

            if member_state == member_states.ADMIN:
                self._fill_chatroom_basic_info(card_content, chatroom_name,
                                               community_instance, member_instance, chatroom_type)

                card_content['chatroom_with_user'] = user_instance
                card_content['member_state'] = member_state

            else:
                self._fill_chatroom_basic_info(card_content, chatroom_name,
                                               community_instance, user_instance, chatroom_type)

                card_content['chatroom_with_user'] = member_instance
                card_content['member_state'] = user_member_state

            card_content['date_epoch'] = TimeUtilities.current_time_in_sec()
            card_content['header'] = chatroom_name
            card_content['has_been_named'] = True
            card_content['is_private'] = True
            card_content['custom_tag'] = custom_tag

            is_private_member = all([user_member_state == member_states.MEMBER,
                                     member_state == member_states.MEMBER])

            card_content['is_private_member'] = is_private_member

            chatroom_instance = self._create_chatroom_with_contents(card_content=card_content)
            self.set_chatroom_id(chatroom_instance.id)

            send_chatroom_creation_analytics_data.delay(self.get_chatroom_id(), int(self.get_member_id()),
                                                        event_name="DM Chatroom created (Core service)")

            # Set initial chatroom message
            initial_message_dm_chatroom(chatroom_instance, user_instance, member_instance, community_instance,
                                        [user_instance, member_instance])

            # Update All community chatrooms for user
            ElasticSearchSync.update_chatroom.delay(chatroom_instance.id)

        context = {
            'success': True,
            'chatroom': ChatroomHelper.compute_chatroom_response(chatroom_instance, user_instance, 
                                                                 community_instance, sdk_client_info_flag=True),
            'chatroom_local': ChatroomHelper.fetch_serialized_chatroom_for_local_db_sycing(self.get_member_id(),
                                                                                           chatroom_instance)
        }

        return context

    def block_member(self, req_body) -> dict:
        validated_request = ChatroomHelper.validate_block_member_request(self.get_member_id(),
                                                                         self.get_chatroom_id(),
                                                                         req_body)

        if not validated_request.get('success'):
            return validated_request

        user_instance = validated_request.get('user_instance')
        card_instance = validated_request.get('chatroom_instance')
        user_instances_list = [card_instance.user, card_instance.chatroom_with_user]
        user_member_state = Members.get_community_member_state(card_instance.community, card_instance.user)
        member_state = Members.get_community_member_state(card_instance.community, card_instance.chatroom_with_user)
        last_conversation_state = None
        last_cconversation = ModelUtilities.get_model_filter(card_answers,
                                                             {'card': card_instance}).order_by('-created_at')

        if last_cconversation:
            last_conversation_state = last_cconversation[0].state

        if validated_request.get('user_instance') not in user_instances_list:
            return get_error_context(False, 'You are not part of chatroom!')

        if any([(last_conversation_state == conversation_states.CONVERSATION_DIRECT_MESSAGE_BLOCK_MEMBER_DISABLE_CHAT)
                and (validated_request.get('status') == block_chatroom_states.BLOCK),
                (last_conversation_state == conversation_states.CONVERSATION_DIRECT_MESSAGE_UNBLOCK_MEMBER_ENABLE_CHAT)
                and (validated_request.get('status') == block_chatroom_states.UNBLOCK)]):
            return get_error_context(False, 'You cannot block/unblock twice!')

        if all([card_instance.is_private, card_instance.type == card_types.CARD_DIRECT_MESSAGE,
                card_instance.user, card_instance.chatroom_with_user]):

            if validated_request.get('status') == block_chatroom_states.BLOCK:
                answer = BLOCK_MEMBER_DM_CHATROOM_MESSAGE
                conv_state = conversation_states.CONVERSATION_DIRECT_MESSAGE_BLOCK_MEMBER_DISABLE_CHAT

                chat_request_state = chat_request_states.REJECTED

            else:
                user_route = "<<" + str(card_instance.user.userinfo.name) + "|route://member/" + str(
                    card_instance.user.id) + ">>"

                chatroom_with_user_route = "<<" + str(card_instance.chatroom_with_user.userinfo.name) + \
                                           "|route://member/" + str(card_instance.chatroom_with_user.id) + ">>"

                answer = UNBLOCK_MEMBER_DM_CHATROOM_MESSAGE.format(user_route, chatroom_with_user_route)
                conv_state = conversation_states.CONVERSATION_DIRECT_MESSAGE_UNBLOCK_MEMBER_ENABLE_CHAT

                chat_request_state = chat_request_states.ACCEPTED

            ModelUtilities.model_update(collabcardState, {'card': card_instance, 'follow_status': True},
                                        {'chat_request_state': chat_request_state,
                                         'chat_requested_by': user_instance,
                                         'updated_at': TimeUtilities.current_time_in_sec()})

            conversation_instance = initial_message_dm_chatroom(card_instance, card_instance.user,
                                                                card_instance.chatroom_with_user,
                                                                card_instance.community, user_instances_list,
                                                                answer, user_member_state, member_state,
                                                                conversation_state=conv_state)

            from collabmates_api.conversation.conversation_impl import ConversationHelper
            ConversationHelper.update_latest_conversation_id_to_firebase_v1.delay(card_instance.id,
                                                                                  conversation_instance.id,
                                                                                  card_instance.community_id,
                                                                                  only_update_home_feed=True)

            context = {"current_user_id": self.get_member_id(), "fetch_reply": True}
            conversation = CardAnswersDBSyncSerializer(conversation_instance, context=context, many=False).data

            return {'success': True, 'conversation': conversation}

        else:
            return get_error_context(False, 'Not a DM chatroom!')

    def request_dm(self, req_body) -> dict:
        validated_request = ChatroomHelper.validate_request_dm_request(self.get_member_id(),
                                                                       self.get_chatroom_id(),
                                                                       req_body)

        if not validated_request.get('success'):
            return validated_request

        user_instance = validated_request.get('user_instance')
        card_instance = validated_request.get('chatroom_instance')
        chat_request_state = validated_request.get('chat_request_state')
        message = req_body.get('text')

        user_instances_list = [card_instance.user, card_instance.chatroom_with_user]
        user_member_state = Members.get_community_member_state(card_instance.community, card_instance.user)
        member_state = Members.get_community_member_state(card_instance.community, card_instance.chatroom_with_user)

        if user_instance not in user_instances_list:
            return get_error_context(False, 'Cannot access DM chatroom!')

        card_state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': card_instance,
                                                                              'follow_status': True,
                                                                              'remove_id': None,
                                                                              'secret_chatroom_left': False})

        member_can_dm_right_state = member_rights.MEMBER_RIGHT_ENABLE_MEMBERS_CAN_DM
        user_has_dm_right = check_user_has_member_can_initiate_dm_right(user_instance.id, card_instance.community_id,
                                                                        member_can_dm_right_state)

        if chat_request_state == chat_request_states.INITIATED:
            response = ChatroomHelper.initiate_dm_connection_request(user_instance, card_instance, user_member_state,
                                                                     member_state, user_has_dm_right, message,
                                                                     chat_request_state, user_instances_list,
                                                                     card_state_filter)

            if not response.get('success'):
                return response

        elif chat_request_state == chat_request_states.ACCEPTED:
            response = ChatroomHelper.accept_dm_connection_request(user_instance, card_instance, user_member_state,
                                                                   member_state, chat_request_state, card_state_filter,
                                                                   message, user_instances_list)

            if not response.get('success'):
                return response

            if response.get('should_call_block_unblock', False):
                response = self.block_member({'status': block_chatroom_states.UNBLOCK})

        elif chat_request_state == chat_request_states.REJECTED:
            response = ChatroomHelper.reject_dm_connection_request(user_instance, card_instance, user_member_state,
                                                                   member_state, chat_request_state, card_state_filter)

            if not response.get('success'):
                return response

            if response.get('should_call_block_unblock', False):
                response = self.block_member({'status': block_chatroom_states.BLOCK})

        else:
            return get_error_context(False, 'Invalid chat request state')

        if response.get('success'):
            return {'success': True, 'conversation': response.get('conversation')}

        else:
            return response

    def scheduled_chatroom_follow(self):

        schedule_follow_instance = ModelUtilities.get_model_filter(
            ScheduledChatroomFollow,
            {
                'chatroom_id': self.get_chatroom_id()
            }
        )

        res = {
            'success': False
        }

        if schedule_follow_instance:
            instance = schedule_follow_instance[0]

            from collabmates_api.views import follow_chatroom_async

            if instance.schedule_time - instance.schedule_time_before <= \
                TimeUtilities.current_time_in_milliseconds():

                follow_chatroom_async.delay(
                    self.get_chatroom_id(),
                    self.get_member_id()

                )

            else:
                args = [self.get_chatroom_id(), self.get_member_id()]

                task_begin_time = TimeUtilities.convert_epoch_to_datetime_in_IST(
                    instance.schedule_time - instance.schedule_time_before
                )

                follow_chatroom_async.apply_async(
                    args,
                    eta=task_begin_time
                )

            res = {
                'success': True
            }

        return res

    def update_chatroom_noti_settings(self, noti_state, is_noti_paused, pause_noti_for):
        validated_request = ChatroomViewHelper.validate_update_chatroom_notification_setting_request(
            self.get_member_id(), self.get_chatroom_id())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        collabcard_state_instance = validated_request.get('collabcard_state_instance')

        if is_noti_paused:

            if pause_noti_for:
                current_time = TimeUtilities.current_time_in_milliseconds()
                unpause_noti_at = current_time + pause_noti_for

                collabcard_state_instance.update(is_noti_paused=is_noti_paused, unpause_noti_at=unpause_noti_at)

                ChatroomHelper.trigger_event_analytics_on_pausing_chatroom_noti.delay(
                    self.get_member_id(),
                    self.get_chatroom_id(),
                    pause_noti_for
                )

            else:
                return ResponseUtilities.get_impl_error_context('pause_noti_for key cannot be empty',
                                                                status_codes.HTTP_400_BAD_REQUEST)

        elif collabcard_state_instance[0].is_noti_paused:
            collabcard_state_instance.update(is_noti_paused=is_noti_paused)

        if noti_state:
            collabcard_state_instance.update(noti_state=noti_state)

            ChatroomHelper.trigger_event_analytics_on_updating_chatroom_noti_settings.delay(
                self.get_member_id(),
                self.get_chatroom_id(),
                noti_state
            )

        return {'success': True}

    def fetch_chatroom_noti_settings(self):
        validated_req_body = ChatroomViewHelper.validate_fetch_chatroom_notification_setting_request(
            self.get_member_id(), self.get_chatroom_id())

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        state_instance = validated_req_body.get('collabcard_state_instance')

        settings_data = {
            'chatroom_id': state_instance.card_id,
            'member_id': self.get_member_id(),
            'notification_state': state_instance.noti_state if state_instance.noti_state
            else noti_states.ALL_MESSAGES,
            'unpause_notification_at': state_instance.unpause_noti_at
        }

        return {
            'success': True,
            'chatroom_notification_settings': settings_data
        }

    def remove_chatroom_participant(self, removed_members_list: list = None, uuids: list = None):
        validated_req = ChatroomHelper.validate_remove_chatroom_participant_request(self.get_member_id(),
                                                                                    self.get_chatroom_id(),
                                                                                    removed_members_list,
                                                                                    uuids)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_instance = validated_req.get('chatroom_instance')
        chatroom_state = conversation_states.CONVERSATION_REMOVED_FROM_CHATROOM

        # If uuids are present, get valid user ids and update removed_members_list
        if uuids:
            removed_members_list = ModelUtilities.get_valid_user_ids_from_uuids(uuids, chatroom_instance.community_id)

        else:
            # support for user_unique_ids in secret chatroom participants parameter
            removed_members_list = ModelUtilities.get_valid_member_ids(removed_members_list,
                                                                       community_id=chatroom_instance.community_id)

        filter_dict = {
            'card': chatroom_instance,
            'user__in': removed_members_list,
            'follow_status': True
        }

        state_filter = ModelUtilities.get_model_filter(collabcardState, filter_dict)

        if not state_filter:
            return {'success': True}

        state_filter.update(**{'follow_status': False})

        # Updating all secret chatroom participants
        filter_dict = {
            'card': chatroom_instance,
        }

        update_dict = {
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        ModelUtilities.model_update(collabcardState, filter_dict, update_dict)

        # Deleting conversation engage for this chatroom for this user
        ModelUtilities.delete_record_in_model(conversationEngage,
                                              {'card': chatroom_instance,
                                               'user__in': removed_members_list})

        ChatroomHelper.run_async_tasks_for_users_removing_from_chatroom.delay(
            chatroom_id=chatroom_instance.id, removed_members_list=list(state_filter.values_list('user_id', flat=True)),
            current_user_id=self.get_member_id(), chatroom_state=chatroom_state)

        return {'success': True}

    def get_chatroom_participants_list(self) -> list:
        filter_dict = {
            'card': self.get_chatroom_id(),
            'follow_status': True,
            'is_tagged': False,
            'remove': None
        }

        followed_members = ModelUtilities.get_model_filter(collabcardState, filter_dict).values_list('user_id',
                                                                                                     flat=True)

        return list(followed_members)

    def get_chatroom_invites(self, chatroom_types: list = None, page: int = None, page_size: int = None) -> dict:
        validated_req_body = ChatroomHelper.validate_get_chatroom_invites_request(self.get_member_id(),
                                                                                  self.get_api_key())

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req_body.get('user_instance')
        community_instance = validated_req_body.get('community_instance')

        if not chatroom_types:
            chatroom_types = [card_types.CARD_NORMAL]

        chatroom_invite_ids_list = get_chatroom_invites_for_user(user_instance.id,
                                                                 community_instance.id,
                                                                 chatroom_types,
                                                                 chatroom_invite_status_types.INVITE_INITIATED,
                                                                 page,
                                                                 page_size)

        chatroom_invites_data = []

        serializer_context = {
            'user_id': user_instance.id
        }

        if chatroom_invite_ids_list:
            chatroom_invite_filter = ModelUtilities.get_model_filter(
                ChatroomInvite, {'id__in': chatroom_invite_ids_list}).order_by('-created_at')

            chatroom_invites_data = ChatroomInviteSerializer(chatroom_invite_filter, context=serializer_context,
                                                             many=True).data

        return {'success': True, 'user_invites': chatroom_invites_data}

    def update_chatroom_invites(self, invite_status: int) -> dict:
        validated_req_body = ChatroomHelper.validate_update_chatroom_invite_request(self.get_member_id(),
                                                                                    self.get_chatroom_id(),
                                                                                    invite_status)

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req_body.get('user_instance')
        chatroom_instance = validated_req_body.get('chatroom_instance')

        filter_dict = {
            'chatroom': chatroom_instance,
            'invite_receiver': user_instance,
            'invite_status': chatroom_invite_status_types.INVITE_INITIATED
        }

        chatroom_invite_filter = ModelUtilities.get_model_filter(ChatroomInvite, filter_dict)

        if not chatroom_invite_filter:
            return ResponseUtilities.get_impl_error_context('No invite to accept or reject!',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        if invite_status == chatroom_invite_status_types.INVITE_ACCEPTED:
            req_body = {
                'chatroom_id': chatroom_instance.id,
                'secret_chatroom_participants': [user_instance.id],
                'is_channel_invite': False
            }

            self.add_secret_chatroom_participant(req_body)
            chatroom_invite_filter.update(invite_status=chatroom_invite_status_types.INVITE_ACCEPTED,
                                          updated_at=TimeUtilities.current_time_in_milliseconds())

        else:
            chatroom_invite_filter.update(invite_status=chatroom_invite_status_types.INVITE_REJECTED,
                                          updated_at=TimeUtilities.current_time_in_milliseconds())
            update_models_for_syncing_apis(SyncTypes.CHATROOM, {'card': chatroom_instance}, {})

        return {'success': True}

    def update_chatroom_settings(self, chatroom_settings: list) -> dict:
        validated_req_body = ChatroomHelper.validate_update_chatroom_settings_request(self.get_member_id(),
                                                                                      self.get_chatroom_id(),
                                                                                      chatroom_settings)

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        chatroom_instance = validated_req_body.get('chatroom_instance')

        for chatroom_setting in chatroom_settings:
            setting_id = chatroom_setting.get('id')
            setting_title = chatroom_setting.get('title')
            is_selected = chatroom_setting.get('is_selected', False)

            if not (setting_id and setting_title):
                continue

            elif all([setting_id == chatroom_setting_states.TAG_ONLY_PARTICIPANTS_ID,
                      setting_title == chatroom_setting_states.TAG_ONLY_PARTICIPANTS_TITLE]):
                ChatroomHelper.update_tag_only_participants_chatroom_setting.delay(chatroom_instance.id, is_selected)

        return {'success': True}
    
    def get_chatroom_user_settings(self, participant_uuid: str, setting_types: list = None) -> dict:

        # Validate request and get instances
        validated_req = ChatroomHelper.validate_chatroom_user_settings_request(member_id=self.get_member_id(),
                                                                               api_key=self.get_api_key(),
                                                                               participant_uuid=participant_uuid,
                                                                               chatroom_id=self.get_chatroom_id())
        
        # If any error occured, return Bad Request resposne
        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'), 
                                                            status_codes.HTTP_400_BAD_REQUEST)
        
        chatroom_instance = validated_req.get('chatroom_instance')
        participant_instance = validated_req.get('participant_instance')
        is_participant_admin = validated_req.get('participant_is_admin')

        # Get computed User Channel settings
        computed_channel_settings = ChatroomHelper.compute_user_chatroom_settings(participant_instance, 
                                                                                  chatroom_instance, 
                                                                                  is_participant_admin, 
                                                                                  setting_types)
        
        serialized_data = UserChannelSettingsSerializer(computed_channel_settings, many=True).data

        return {'success': True, 'channel_settings':serialized_data}

    def update_chatroom_user_settings(self, participant_uuid: str, chatroom_settings: list) -> dict:

        # Validate request and get instances
        validated_req = ChatroomHelper.validate_chatroom_user_settings_request(member_id=self.get_member_id(),
                                                                               api_key=self.get_api_key(),
                                                                               participant_uuid=participant_uuid,
                                                                               chatroom_id=self.get_chatroom_id(),
                                                                               update_settings=True)
        
        # If any error occured, return Bad Request resposne
        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'), 
                                                            status_codes.HTTP_400_BAD_REQUEST)
        
        chatroom_instance = validated_req.get('chatroom_instance')
        member_instance = validated_req.get('member_instance')
        participant_instance = validated_req.get('participant_instance')

        # Update User Channel settings
        updated_channel_settings = ChatroomHelper.update_user_chatroom_settings_helper(participant_instance, 
                                                                                       member_instance, 
                                                                                       chatroom_instance, 
                                                                                       chatroom_settings)
        
        # Serialize User Channel settings
        serialized_data = UserChannelSettingsSerializer(updated_channel_settings, many=True).data

        # Return chatroom user settings
        return {'success': True, 'channel_settings': serialized_data} 



class ChatroomHelper:

    @staticmethod
    def fetch_card_instance(chatroom_id: Union[str, int]):
        return Collabcard.get_chatroom_or_None(chatroom_id=chatroom_id)

    @staticmethod
    def fetch_user_instance(member_id: Union[str, int]):
        return User.get_user_or_none(member_id)

    @staticmethod
    def fetch_serialized_community(card_instance: object, user_instance: object, current_user_id: str = None,
                                   platform_code: str = None, version_code: int = 0):

        context = CommunitySerializer(card_instance.community, current_user_id=current_user_id,
                                      current_user_instance=user_instance, platform_code=platform_code,
                                      version_code=version_code)
        return context

    @staticmethod
    def get_follow_user_dict(user_id: Union[str, int], chatroom_id: Union[str, int],
                             is_tagged: bool, status: bool, source: str):
        return {
            'member_id': user_id,
            'collabcard_id': chatroom_id,
            'status': status,
            'source': source,
            'is_tagged': is_tagged
        }

    @staticmethod
    def fetch_user_instance_or_raise_exception(user_id: Union[str, int]):
        return User.get_user_or_raise_exception(user_id)

    @staticmethod
    def fetch_user_info_instance(user_instance: User):
        return user_instance.userinfo

    @staticmethod
    def fetch_community_instance(community_id: Union[str, int]):
        return Community.get_community_or_raise_exception(community_id=community_id)

    @staticmethod
    def fetch_serialized_chatroom_for_local_db_sycing(member_id, chatroom_instance):
        member_data = {'member_id': member_id, 'current_user_id': member_id, 'state_instance': None}
        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_instance.id)
        chatroom_obj = GetChatroomInstanceSerializer(chatroom_instance, context=member_data, many=False)

        return chatroom_obj.data

    @staticmethod
    def fetch_serialized_user_info(user_info_instance: object):
        return UserinfoSerializer(user_info_instance)

    @staticmethod
    def check_user_auto_approve_right(user: User, community: Community) -> bool:
        return userMemberRights.check_member_auto_approve_right(user=user,
                                                                community=community)

    @staticmethod
    def fetch_member_state_in_community(community: Community, user: User) -> int:
        return Members.get_community_member_state(community,
                                                  user)

    @staticmethod
    def is_user_community_member_or_raise_exception(community: Community, user: User) -> bool:
        is_member = Members.is_community_member(community=community,
                                                member=user)
        if not is_member:
            response = {'success': False,
                        'error_message': "You cannot create a chatroom"
                        }
            raise CustomException(response, status_code=status_codes.HTTP_401_UNAUTHORIZED)
        return is_member

    @staticmethod
    def update_time_for_community_members_on_card_creation(community: Community) -> None:
        Collabcard.update_time_for_community_members(community)

    @staticmethod
    def create_answer(chatroom_instance, user_instance, state, answer=None, current_user_id=None):
        create_chatroom(chatroom_instance, user_instance, state,
                        current_user_id=current_user_id, answer=answer)

    @staticmethod
    @shared_task
    def make_secret_chatroom_relation_for_community_members(user_list, chatroom_id, community_id,
                                                            room_creator_id):

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return

        member_dict = ChatroomHelper.pre_compute_existence_of_members_in_chatroom_state(card_instance,
                                                                                        user_list)
        user_filter = ModelUtilities.get_model_filter(User,
                                                      {'id__in': user_list})
        bulk_create_list = []

        for user_instance in user_filter:

            if member_dict.get(user_instance.id) is False:

                expire_at = TimeUtilities.current_time_in_sec() + CHATROOM_EXPIRE_DURATION \
                    if user_instance.id == room_creator_id else None

                instance = collabcardState.create_chatroom_state_instances_for_bulk_create \
                    (card_instance,
                     user_instance,
                     state=0,
                     follow_status=True,
                     community_instance=community_instance,
                     external_seen=user_instance.id == room_creator_id,
                     expire_at=expire_at)

                if instance:
                    bulk_create_list.append(instance)

        ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)
        ChatroomHelper.set_chatroom_participants_created_key_in_cache(chatroom_id, True)
        ChatroomHelper.create_card_engagements_for_home_screen_for_auto_follow_all_members_with_user_list(
            card_instance.id, user_list)

        for user_id in user_list:
            update_last_unseen_in_engage(user=user_id, community=community_instance.id)

        ChatroomHelper.update_secret_chatroom_for_community_promoters(card_instance, community_instance, member_dict)
        ElasticSearchSync.update_chatroom(card_instance.id)

    @staticmethod
    def update_secret_chatroom_for_community_promoters(card_instance, community_instance, member_dict):

        member_filter = ModelUtilities.get_model_filter(Members,
                                                        {'community_id': community_instance,
                                                         'state': member_states.ADMIN}).select_related('member_id')

        bulk_create_list = []
        promoter_list = []
        for data in member_filter:

            if (data.member_id == card_instance.user) and (data.member_id_id not in member_dict):
                user_instance = data.member_id
                instance = collabcardState.create_chatroom_state_instances_for_bulk_create \
                    (card_instance,
                     user_instance,
                     follow_status=False,
                     state=0,
                     community_instance=community_instance,
                     external_seen=False,
                     expire_at=None)

                if not ModelUtilities.get_model_filter(collabcardState,
                                                       {'card': card_instance,
                                                        'user': data.member_id}):
                    instance.save()

            elif data.member_id_id not in member_dict:
                user_instance = data.member_id
                instance = collabcardState.create_chatroom_state_instances_for_bulk_create \
                    (card_instance,
                     user_instance,
                     follow_status=False,
                     state=0,
                     community_instance=community_instance,
                     external_seen=False,
                     expire_at=None)

                if instance:
                    bulk_create_list.append(instance)

                promoter_list.append(data.member_id_id)

        ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)

        for user_id in promoter_list:
            update_last_unseen_in_engage(user=user_id, community=community_instance.id)

    @staticmethod
    @shared_task
    def add_new_secret_chatroom_participants(participants_list, chatroom_id, current_user_id,
                                             add_user_joined_message: bool = True):

        chatroom_instance = Collabcard.get_chatroom_or_None(chatroom_id)

        if chatroom_instance is None:
            return

        new_participants = User.objects.filter(pk__in=participants_list)

        for user in new_participants:

            req_dict = ChatroomHelper.get_follow_user_dict(user.id, chatroom_instance.id,
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")

            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_UNSEEN,
                                       external_seen=False,
                                       set_expiry_time_none=True)

            if (user.id != NumberUtilities.get_integer_from_string(current_user_id)) and add_user_joined_message:
                ChatroomHelper.create_answer(chatroom_instance=chatroom_instance, user_instance=user,
                                             state=conversation_states.CONVERSATION_ADD_PARTICIPANT,
                                             current_user_id=current_user_id)

            update_last_unseen_in_engage(user=user.id, community=chatroom_instance.community_id)
            # update elastic search
            ElasticSearchSync.update_chatroom_for_user.delay(chatroom_instance.id, user.id)

            send_notification_for_new_secret_room_participant(user.id, chatroom_instance.id)

    @staticmethod
    def get_chatroom_expiry_time(chatroom_state_instance):

        expiry_time = None

        return expiry_time

    @staticmethod
    def has_attachments_uploaded(chatroom, user_id, device_id=''):
        if chatroom.attachment_count > 0 and \
                chatroom.attachments_uploaded is False and \
                (user_id != chatroom.user_id or
                 device_id != chatroom.device_id):
            return True

        return False

    @staticmethod
    def create_placeholder_for_introduction_card(community_instance, card_creator_userinfo_instance):
        """function to create introduction card placeholder"""

        placeholder = INTRO_PLACEHOLDER_TEXT % community_instance.name
        user_name = card_creator_userinfo_instance.name
        user_route = INTRO_PLACEHOLDER_USER_ROUTE % str(card_creator_userinfo_instance.user_id_id)
        user_name = "<<" + user_name + "|" + user_route + ">>"
        placeholder = placeholder + user_name

        return placeholder

    @staticmethod
    def create_card_engagement_for_home_screen(card_instance, user_instance, community_instance, member_state=0):

        instance_list = ModelUtilities.get_model_filter(conversationEngage,
                                                        {'card': card_instance,
                                                         'user': user_instance})

        rights_list = None

        if member_state == member_states.ADMIN:
            rights_list = json.dumps(member_rights.ALL_MEMBER_RIGHTS)
        elif member_state == member_states.MEMBER or member_state == member_states.PROFILE_UNAVAILABLE:
            rights_list = json.dumps(member_rights.DEFAULT_MEMBER_RIGHTS)

        if not instance_list:
            conversationEngage.create_instance({'card_instance': card_instance,
                                                'user_instance': user_instance,
                                                'community_instance': community_instance,
                                                'rights_list': rights_list})

        else:
            instance = instance_list[0]
            ModelUtilities.model_update(conversationEngage, {'id': instance.id},
                                        {'last_conversation': None,
                                         'updated_at': TimeUtilities.current_time_in_sec()})

        ChatroomHelper.update_rights_list_in_conversationEngage(user_instance, community_instance)

    @staticmethod
    def update_rights_list_in_conversationEngage(user_instance, community_instance):
        rights_list = list(userMemberRights.objects.filter(user=user_instance,
                                                           community=community_instance).values_list("right__state",
                                                                                                     flat=True))
        rights_list = json.dumps(rights_list)

        ModelUtilities.model_update(conversationEngage, {'user': user_instance,
                                                         'community': community_instance},
                                    {'rights_list': rights_list})

    @staticmethod
    def auto_follow_chatroom(card_instance, user_instance, community_instance, status=True, func_dict=None,
                             member_state=0):

        if func_dict is None:
            func_dict = {}

        is_guest = False
        is_tagged = False
        ref_instance = None
        mute_status = False

        if func_dict.get('is_guest') and func_dict.get('source_id'):
            is_guest = func_dict['is_guest']
            source_id = func_dict['source_id']
            ref_instance = ModelUtilities.get_model_instance_or_none(User, source_id)

            if not ref_instance:
                return

        elif func_dict.get('is_tagged'):
            is_tagged = True
            mute_status = True

        from collabmates_api.community.community_impl import CommunityHelper

        community_noti_instance = CommunityHelper.fetch_community_noti_settings_instance(community_instance)
        community_current_noti_state = community_noti_instance.noti_state if community_noti_instance else noti_states.ALL_MESSAGES

        chatroom_state_instance = None
        collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': card_instance,
                                                                                    'user': user_instance})

        if not collabcard_state_filter:

            expiry_time = ChatroomHelper.get_chatroom_expiry_time(chatroom_state_instance)
            card_state_instance = collabcardState.create_chatroom_state_instance(card_instance, user_instance,
                                                                                 noti_state=community_current_noti_state,
                                                                                 state=collabcard_states.COLLABCARD_STATE_SEEN,
                                                                                 expire_at=expiry_time,
                                                                                 is_guest=is_guest,
                                                                                 source=ref_instance,
                                                                                 follow_status=status,
                                                                                 mute_status=mute_status,
                                                                                 is_tagged=is_tagged,
                                                                                 attending_status=func_dict.get(
                                                                                     'attending_status', False)
                                                                                 )
        else:
            card_state_instance = collabcard_state_filter[0]
            expiry_time = ChatroomHelper.get_chatroom_expiry_time(chatroom_state_instance)
            card_state_instance.updated_at = TimeUtilities.current_time_in_sec()
            card_state_instance.follow_status = status
            card_state_instance.mute_status = mute_status
            card_state_instance.is_guest = is_guest
            card_state_instance.is_tagged = is_tagged
            card_state_instance.attending_status = func_dict.get('attending_status', False)
            card_state_instance.save()

        if status:
            ChatroomHelper.create_card_engagement_for_home_screen(card_instance, user_instance, community_instance,
                                                                  member_state=member_state)

        conversation_impl.ConversationHelper.update_homescreen_meta_on_chatroom_follow(community_instance,
                                                                                       card_instance,
                                                                                       card_state_instance,
                                                                                       user_instance)

        ElasticSearchSync.update_chatroom_for_user.delay(card_instance.id, user_instance.id)

    @staticmethod
    def pre_compute_existance_in_chatroom_state(chatroom_list, user_instance):

        state_filter = collabcardState.objects.filter(card__in=chatroom_list, user=user_instance)

        chatroom_state_dict = {chatroom_id: False for chatroom_id in chatroom_list}

        for data in state_filter:
            card_id = data.card_id

            if chatroom_state_dict.get(card_id) is False:
                chatroom_state_dict[card_id] = True

        return chatroom_state_dict

    @staticmethod
    def pre_compute_last_conversation_in_chatroom(chatroom_list):

        conversation_filter = card_answers.objects.filter(card__in=chatroom_list,
                                                          state=conversation_states.ANSWER).values('card'). \
            annotate(created_at=Max('created_at'))

        chatroom_set = set(chatroom_list)
        conversation_created_at = {}

        for data in conversation_filter:

            if data['card'] in chatroom_set:
                created_at = data['created_at']

                if TimeUtilities.is_epoch_in_milliseconds(created_at):
                    created_at = TimeUtilities.convert_milliseconds_to_sec(created_at)

                conversation_created_at['created_at'] = created_at

        return conversation_created_at

    @staticmethod
    def update_seen_status_for_older_chatrooms_for_new_member(community_instance, user_instance):
        chatroom_filter = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                       'is_pending': False,
                                                                       'is_deleted': False,
                                                                       'is_secret': False})

        chatroom_filter = chatroom_filter.exclude(is_private=True, type=card_types.CARD_DIRECT_MESSAGE)

        chatroom_list = list(chatroom_filter.values_list('id', flat=True))

        chatroom_state_dict = ChatroomHelper.pre_compute_existance_in_chatroom_state(chatroom_list, user_instance)
        conversation_created_at = ChatroomHelper.pre_compute_last_conversation_in_chatroom(chatroom_list)
        bulk_create_list = []
        auto_follow_chatroom_list = []

        from collabmates_api.community.community_impl import CommunityHelper
        community_noti_instance = CommunityHelper.fetch_community_noti_settings_instance(community_instance)
        community_current_noti_state = community_noti_instance.noti_state if community_noti_instance else noti_states.ALL_MESSAGES

        for card_instance in chatroom_filter:

            if chatroom_state_dict.get(card_instance.id) is False:
                expire_at = conversation_created_at.get(card_instance.id, card_instance.date_epoch) + \
                            CHATROOM_EXPIRE_DURATION

                if card_instance.auto_follow_done:
                    auto_follow_chatroom_list.append(card_instance.id)

                follow_status = card_instance.auto_follow_done and card_instance.include_members_later

                instance = collabcardState.create_chatroom_state_instances_for_bulk_create(
                    card_instance, user_instance, follow_status=follow_status, expire_at=expire_at,
                    community_instance=community_instance, noti_state=community_current_noti_state)

                if instance:
                    bulk_create_list.append(instance)

        ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)
        ChatroomHelper.create_card_engagements_for_home_screen_for_auto_follow_all_members_with_chatroom_list(
            auto_follow_chatroom_list, user_instance.id, community_instance.id, member_state=member_states.MEMBER)

    @staticmethod
    def pre_compute_existence_of_members_in_chatroom_state(card_instance, member_list):
        state_filter = collabcardState.objects.filter(card=card_instance, user__in=member_list)

        member_dict = {user_id: False for user_id in member_list}

        for data in state_filter:
            user_id = data.user_id

            if member_dict.get(user_id) is False:
                member_dict[user_id] = True

        return member_dict

    @staticmethod
    def set_state_for_all_chatroom_members_in_community(card_instance, community_instance,
                                                        chatroom_participants_list=None):

        member_filter = Members.get_members_of_community(community_instance).select_related('member_id')
        member_list = list(member_filter.values_list('member_id_id', flat=True))

        member_dict = ChatroomHelper.pre_compute_existence_of_members_in_chatroom_state(card_instance, member_list)
        bulk_create_list = []

        state = 1 if card_instance.type == card_types.CARD_INTRO else 0

        is_event_chatroom = card_instance.type == card_types.CARD_EVENT or card_instance.type == \
                            card_types.CARD_PUBLIC_EVENT

        community_admins_list = []
        event_attendees_list = []
        chatroom_participants_list = chatroom_participants_list if chatroom_participants_list else []

        from collabmates_api.notifications.tasks_impl import TasksHelper

        event_creator_and_community_owner = TasksHelper.get_community_owner_and_event_creator(community_instance,
                                                                                              card_instance)

        from collabmates_api.community.community_impl import CommunityHelper

        community_noti_instance = CommunityHelper.fetch_community_noti_settings_instance(community_instance)
        community_current_noti_state = community_noti_instance.noti_state if community_noti_instance else noti_states.ALL_MESSAGES

        auto_follow_members_list = []

        for data in member_filter:
            user_instance = data.member_id

            is_card_creator = user_instance.id == card_instance.user_id

            if not member_dict.get(user_instance.id):

                attending_status = is_event_chatroom and (user_instance.id in event_creator_and_community_owner)
                follow_status = True if (attending_status or user_instance.id in chatroom_participants_list) else \
                    card_instance.auto_follow_done

                instance = collabcardState.create_chatroom_state_instances_for_bulk_create(card_instance,
                                                                                           user_instance,
                                                                                           noti_state=community_current_noti_state,
                                                                                           state=state,
                                                                                           follow_status=follow_status,
                                                                                           community_instance=community_instance,
                                                                                           attending_status=attending_status,
                                                                                           external_seen=is_card_creator)
                if instance:
                    bulk_create_list.append(instance)

                if attending_status and (user_instance.id not in event_attendees_list):
                    event_attendees_list.append(user_instance.id)

                if user_instance.id in event_creator_and_community_owner:
                    community_admins_list.append(user_instance.id)

                if follow_status:
                    auto_follow_members_list.append(user_instance.id)

        payload_for_calendar_invite = {
            'chatroom': card_instance.id
        }

        send_calender_invite_for_event_type.delay(payload_for_calendar_invite, EVENT_TYPE.REGISTRATION,
                                                  send_to_members=False, user_list=event_creator_and_community_owner,
                                                  calendar_invite_type=CALENDAR_INVITE_TYPE.NEW_CALENDAR_CREATION)

        ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)
        ChatroomHelper.set_chatroom_participants_created_key_in_cache(card_instance.id, True)

        if event_attendees_list:
            update_event_attendees({
                "chatroom_id": card_instance.id,
                "user_id": event_attendees_list,
                "status": True
            })

        card_engagement_user_list = []

        if chatroom_participants_list:
            card_engagement_user_list = chatroom_participants_list

        if card_instance.type in [card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
            card_engagement_user_list = community_admins_list

        if auto_follow_members_list:
            card_engagement_user_list = auto_follow_members_list

        ChatroomHelper.create_card_engagements_for_home_screen_for_auto_follow_all_members_with_user_list(
            card_instance.id, card_engagement_user_list)

    @staticmethod
    def update_unseen_count_for_homescreen_communitites(card_instance, community_instance):
        # updating last unseen chatrooms for home screen
        member_filter = Members.get_members_of_community(community_instance)

        for data in member_filter:
            user_instance = data.member_id

            if card_instance.attachment_count != 0 and card_instance.attachments_uploaded is False:
                continue

            update_last_unseen_in_engage(user=user_instance.id, community=community_instance.id, is_seen=True)

    @staticmethod
    @shared_task
    def run_async_tasks_related_to_member_for_chatroom_posting(card_id, user_id, community_id,
                                                               is_intro_chatroom=False,
                                                               chatroom_participants_list=None):

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not card_instance \
                or not user_instance \
                or not community_instance:
            return

        ChatroomHelper.set_state_for_all_chatroom_members_in_community(
            card_instance, community_instance, chatroom_participants_list=chatroom_participants_list)

        # If chatroom type is not feedroom, then update unseen count 
        if card_instance.type != card_types.CARD_FEED_GROUP:
            ChatroomHelper.update_unseen_count_for_homescreen_communitites(card_instance, community_instance)
        
        update_last_answer_id(card_instance.id, "")

        if card_instance.co_hosts:
            ChatroomHelper.auto_follow_event_co_hosts_and_send_notification(card_instance, user_instance.userinfo)

        if is_intro_chatroom:
            ElasticSearchSync.update_all_community_chatrooms_for_user(community_instance.id, user_instance.id)

        ElasticSearchSync.update_chatroom(card_instance.id)

    @staticmethod
    @shared_task
    def update_old_chatrooms_relation_and_post_introduction_conversation(master_intro_id, user_id, card_id,
                                                                         community_id, member_state):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)
        master_intro_instance = ModelUtilities.get_model_instance_or_none(Collabcard, master_intro_id)

        ChatroomHelper.update_seen_status_for_older_chatrooms_for_new_member(community_instance, user_instance)

        preview_url = settings.WEB_URL + "/collabcard/" + str(card_instance.id)
        conversation_context = {'answer': card_instance.title, 'card': master_intro_instance, 'user': user_instance,
                                'community': community_instance, 'has_files': False, 'attachment_count': 0,
                                'attachments_uploaded': False, 'api_version': 1, 'preview_chatroom': card_instance,
                                'preview_community': community_instance, 'internal_link': preview_url,
                                'preview_type': "chatroom"}

        answer_instance = card_answers(**conversation_context)
        answer_instance.save()
        ChatroomHelper.auto_follow_chatroom(master_intro_instance, user_instance, community_instance,
                                            member_state=member_state)

        conversation_impl.ConversationHelper.update_the_activity_time_for_new_conversation_creation(
            master_intro_instance.id,
            user_instance.id)

        conversation_impl.ConversationHelper.update_homescreen_meta_on_conversation_creation(community_instance,
                                                                                             master_intro_instance,
                                                                                             answer_instance)

        update_preview_of_chatroom_in_cache({'chatroom_id': card_instance.id,
                                             'preview_url': preview_url,
                                             'conversation_id': answer_instance.id})
        ElasticSearchSync.update_chatroom_for_user(master_intro_instance.id, user_instance.id)

    @staticmethod
    def pre_compute_chatroom_state_of_members(card_instance, member_list):
        state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': card_instance,
                                                                         'user__in': member_list})

        chatroom_state_dict = {int(user_id): None for user_id in member_list if str(user_id).isdigit()}

        for data in state_filter:
            user_id = data.user_id

            if chatroom_state_dict.get(user_id) is None:
                chatroom_state_dict[user_id] = data

        return chatroom_state_dict

    @staticmethod
    @shared_task
    def create_card_engagements_for_home_screen_for_auto_follow_all_members_with_user_list(chatroom_id, user_list):
        card_instance = Collabcard.get_chatroom_or_None(chatroom_id)

        community_instance = card_instance.community

        member_filter = Members.get_members_of_community(community_instance).select_related('member_id').filter(
            member_id__in=user_list)

        for data in member_filter:
            user_instance = data.member_id
            state = data.state
            ChatroomHelper.create_card_engagement_for_home_screen(card_instance, user_instance,
                                                                  community_instance, state)

    @staticmethod
    @shared_task
    def create_card_engagements_for_home_screen_for_auto_follow_all_members_with_chatroom_list(chatroom_ids, user_id,
                                                                                               community_id,
                                                                                               member_state):
        user_instance = ChatroomHelper.fetch_user_instance(user_id)

        if not user_instance:
            return

        community_instance = Community.get_community_or_None(community_id)

        if not community_instance:
            return

        chatroom_dict = ChatroomHelper.pre_compute_chatroom_instances_from_chatroom_list(chatroom_ids)

        for chatroom_id in chatroom_ids:

            if chatroom_dict.get(chatroom_id):
                chatroom_instance = chatroom_dict.get(chatroom_id)
                ChatroomHelper.create_card_engagement_for_home_screen(chatroom_instance, user_instance,
                                                                      community_instance,
                                                                      member_state)

    @staticmethod
    def pre_compute_chatroom_instances_from_chatroom_list(chatroom_id_list):
        card_filter = Collabcard.objects.filter(id__in=chatroom_id_list)

        chatroom_dict = {chatroom_id: None for chatroom_id in chatroom_id_list}

        for data in card_filter:
            chatroom_id = data.id

            if chatroom_dict.get(chatroom_id) is None:
                chatroom_dict[chatroom_id] = data

        return chatroom_dict

    @staticmethod
    @shared_task
    def run_async_tasks_related_to_chatroom_edit(card_id):

        ModelUtilities.model_update(collabcardState, {'card': card_id},
                                    {'updated_at': TimeUtilities.current_time_in_sec()})

        ElasticSearchSync.update_chatroom(card_id)

    @staticmethod
    def check_user_secret_room_creation_right(user_instance, community_instance) -> bool:

        return ModelUtilities.is_model_filter_exists(userMemberRights,
                                                     {'user': user_instance,
                                                      'community': community_instance,
                                                      'right__state': member_rights.MEMBER_RIGHT_CREATE_SECRET_ROOM})

    @staticmethod
    def compute_chatroom_response(card_instance, user_instance, community_instance=None, sdk_client_info_flag=False):

        if community_instance is None:
            community_instance = card_instance.community

        chatroom_list = ModelUtilities.get_model_filter(collabcardState, {'user': user_instance,
                                                                          'card': card_instance}). \
            select_related('card')

        chatroom_member_instance = ChatroomMemberImpl(member_id=user_instance.id)
        chatroom_list = chatroom_member_instance.process_chatroom_list(chatroom_list, community_instance, 
                                                                       sdk_client_info_flag=sdk_client_info_flag)

        if chatroom_list:
            return chatroom_list[0]

        return get_chatroom_instance(card_instance, user_instance.id, send_profile=False, 
                                     sdk_client_info_flag=sdk_client_info_flag)

    @staticmethod
    def bulk_follow_chatroom_users(card_instance, user_list):

        user_list = [int(user_id) for user_id in user_list if str(user_id).isdigit()]

        community_members = list(Members.get_members_of_community(card_instance.community).values_list('member_id',
                                                                                                       flat=True))

        user_list = list(set(user_list).intersection(set(community_members)))

        chatroom_state_dict = ChatroomHelper.pre_compute_chatroom_state_of_members(card_instance, user_list)

        bulk_update_list = []
        bulk_create_list = []
        chatroom_member_list = []

        for community_member in user_list:

            collabcard_state = chatroom_state_dict.get(community_member)

            if collabcard_state is not None and not collabcard_state.follow_status:
                chatroom_member_list.append(community_member)
                collabcard_state.follow_status = True
                collabcard_state.updated_at = TimeUtilities.current_time_in_sec()
                bulk_update_list.append(collabcard_state)

            elif collabcard_state is None:
                chatroom_member_list.append(community_member)
                user_instance = ModelUtilities.get_user_instance_or_none(community_member)

                if not user_instance:
                    continue

                bulk_create_list.append(collabcardState.create_chatroom_state_instances_for_bulk_create(
                    card_instance, user_instance, state=collabcard_states.COLLABCARD_STATE_UNSEEN, follow_status=True))

        if bulk_update_list:
            ModelUtilities.bulk_update_instances(collabcardState, bulk_update_list,
                                                 ['follow_status', 'updated_at'])

        if bulk_create_list:
            ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)

        ChatroomHelper.create_card_engagements_for_home_screen_for_auto_follow_all_members_with_user_list \
            .delay(card_instance.id, chatroom_member_list)

    @staticmethod
    def auto_follow_event_co_hosts_and_send_notification(card_instance, userinfo_instance, new_co_hosts=None):

        co_host_list = json.loads(card_instance.co_hosts) if card_instance.co_hosts else []

        if new_co_hosts:
            co_host_list = new_co_hosts

        ChatroomHelper.bulk_follow_chatroom_users(card_instance, co_host_list)

        co_hosts_chatroom_state = ModelUtilities.get_model_filter(collabcardState, {'card': card_instance,
                                                                                    'user_id__in': co_host_list})

        co_hosts_chatroom_state.update(attending_status=True, updated_at=TimeUtilities.current_time_in_sec())

        if co_host_list:
            # Update Cache with Event Chatroom Attendees
            update_event_attendees({
                "chatroom_id": card_instance.id,
                "status": True,
                "user_id": [int(co_host) for co_host in co_host_list if str(co_host).isdigit()]
            })

        send_notification_to_event_co_hosts.delay(co_host_list, card_instance.id,
                                                  card_instance.header, userinfo_instance.name)

    @staticmethod
    def is_online_event_link_verified_for_user(card_instance, user_instance):

        client = ApiClient(host=subscription_url,
                           method='get',
                           path=SUBSCRIPTION_VALIDATE_EVENT_ONLINE_LINK)
        client.add_url_param('chatroom_id', card_instance.id)

        client.add_header('x-member-id', user_instance.id).request()

        response = client.fetch_response()

        return response.get('success', False)

    @staticmethod
    def create_event_metadata_for_mail(card_instance, community_instance, user_email_list):

        if not user_email_list:
            return {}

        chatroom_url = CHATROOM_URL % (settings.WEB_URL, str(card_instance.id))

        event_metadata = {
            'summary': card_instance.header,
            'description': EVENT_CARD_MAIL_DESCRIPTION % (card_instance.header,
                                                          community_instance.name, chatroom_url,
                                                          card_instance.title),
            'start': {
                'dateTime': TimeUtilities.convert_epoch_time_to_RFC3339(card_instance.date_time),
                'timeZone': settings.TIME_ZONE,
            },
            'end': {
                'dateTime': TimeUtilities.convert_epoch_time_to_RFC3339(card_instance.end_date),
                'timeZone': settings.TIME_ZONE,
            },

            'attendees': user_email_list,
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': MAIL_EVENT_NOTIFICATION},
                ],
            },
        }

        return event_metadata

    @staticmethod
    @shared_task
    def send_event_creation_mail(card_id, send_to_members=True, user_list=None):

        if not send_to_members and not user_list:
            return

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

        if not card_instance:
            return

        community_instance = card_instance.community

        if send_to_members:
            member_list = list(Members.get_members_of_community(
                community_instance=community_instance).values_list('member_id', flat=True))
        else:
            member_list = user_list

        user_email_filter = ModelUtilities.get_model_filter(userEmails,
                                                            {'user__in': member_list,
                                                             'email_state': email_states.PRIMARY,
                                                             'verified': True}).order_by('created_at')

        user_email_list = [{'email': instance.email} for instance in user_email_filter if instance.email]

        event_metadata = ChatroomHelper.create_event_metadata_for_mail(card_instance, community_instance,
                                                                       user_email_list)

        if event_metadata:
            CalendarImpl().call_calender_api(event_metadata)

    @staticmethod
    def send_first_event_creation_email_to_promoter(card_instance):
        community_get_started_instances = ModelUtilities.get_model_filter(CommunityGetStarted,
                                                                          {'community': card_instance.community,
                                                                           'get_started__type': get_started_types.CREATE_EVENT_TYPE,
                                                                           'completed': True})

        if not community_get_started_instances:
            mail_subject = FIRST_EVENT_CM_MAIL_SUBJECT.format(card_instance.user.userinfo.name)
            mail_categories = MailHelper.get_email_category_list_using_category_subcategory(
                EmailCategories.CREATE_COMMUNITY, EmailSubCategories.FIRST_EVENT_CREATED)

            branch_link = create_community_feed_url_for_cm_onboarding(card_instance.community)

            mail_template = get_template('mails/cm_onboarding/first_event_creation_cm_onboarding.html').render({
                "community_logo": card_instance.community.image_link,
                "community_name": card_instance.community.name,
                "cm_name": card_instance.user.userinfo.name,
                "community_brand_color": card_instance.community.brand_color if card_instance.community.brand_color
                else DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR,
                "button_link": branch_link,
                "button_text": FIRST_EVENT_CM_MAIL_BUTTON_TEXT
            })

            send_email_response = MailWrapper.send_email.delay(mail_subject, mail_template,
                                                               [card_instance.user.userinfo.email],
                                                               categories=mail_categories,
                                                               reply_to=[FIRST_EVENT_CM_REPLY_EMAIL])

    @staticmethod
    def get_settings_for_chatroom(chatroom_settings_list, card_instance):
        chatroom_settings = []

        for settings in chatroom_settings_list:

            settings_dict = {'id': settings['id'], 'title': settings['title'], 'is_selected': False}

            if settings['id'] == member_can_message['id']:
                settings_dict['is_selected'] = card_instance.member_can_message

            elif settings['id'] == pin_chatroom['id']:
                settings_dict['is_selected'] = card_instance.is_pinned

            elif settings['id'] == accessible_without_subscription['id']:
                settings_dict['is_selected'] = card_instance.access_without_subscription

            elif settings['id'] == make_it_secret['id']:
                settings_dict['is_selected'] = card_instance.is_secret

            elif settings['id'] == auto_joined_by_all_members['id']:
                settings_dict['is_selected'] = card_instance.include_members_later

            elif settings['id'] == chatroom_setting_states.TAG_ONLY_PARTICIPANTS_ID:
                settings_dict['is_selected'] = card_instance.tag_only_participants

            chatroom_settings.append(settings_dict)

        return chatroom_settings

    @staticmethod
    def run_async_tasks_related_to_event_chatroom_analytics(card_instance):
        schedule_event_analytics_on_event_start(card_instance)
        schedule_event_analytics_daily_7AM(card_instance, 7, 0)
        schedule_event_analytics_on_event_before_n_hour(card_instance, 1)

    @staticmethod
    def run_async_task_related_to_event_chatroom_attend_analytics(card_instance, user_instance,
                                                                  attending_status=True):
        send_analytics_on_event_registered_to_attend(card_instance.id, user_instance.id,
                                                     attending_status)

    @staticmethod
    def display_event_recordings_and_attachments(user_instance, card_instance=None, conversation_instance=None,
                                                 recordings_attachment_serialized_obj=None,
                                                 recordings_url_serialized_obj=None):
        event_dict = {}

        try:
            event_obj = card_instance if card_instance else conversation_instance

            if event_obj.has_event_recording == False:

                if Members.is_member_community_promoter(event_obj.community, user_instance) \
                        or user_instance == event_obj.user:
                    has_event_recording = 0

                else:
                    has_event_recording = 1

            else:

                if Members.is_member_community_promoter(event_obj.community, user_instance) \
                        or user_instance == event_obj.user:
                    has_event_recording = 2

                else:
                    has_event_recording = 3

            event_dict['recordings_attachments_view'] = has_event_recording

            if recordings_attachment_serialized_obj is None:
                event_recording_instances = EventRecordingsAttachments.objects.filter(chatroom_id=card_instance) \
                    if card_instance else \
                    EventRecordingsAttachments.objects.filter(conversation_id=conversation_instance)

                serializer = EventRecordingsAttachmentsSerializer(event_recording_instances, many=True)

                event_dict['recordings_attachments'] = json.loads(json.dumps(serializer.data))

            else:
                event_dict['recordings_attachments'] = recordings_attachment_serialized_obj

            if recordings_url_serialized_obj is None:
                event_url_instances = EventRecordingsURL.objects.filter(chatroom_id=card_instance) \
                    if card_instance else \
                    EventRecordingsURL.objects.filter(conversation_id=conversation_instance)

                serializer = EventRecordingsURLSerializer(event_url_instances, many=True)

                event_dict['recordings_url'] = json.loads(json.dumps(serializer.data))
                event_dict['about_recording'] = serializer.data[0].get('about_recording') \
                    if serializer.data else None
                event_dict['recording_url_og_tags'] = serializer.data[0].get('recording_url_og_tags') \
                    if serializer.data else None

            else:
                event_dict['recordings_url'] = recordings_url_serialized_obj
                event_dict['about_recording'] = recordings_url_serialized_obj[0].get('about_recording') \
                    if recordings_url_serialized_obj else None
                event_dict['recording_url_og_tags'] = recordings_url_serialized_obj[0].get('recording_url_og_tags') \
                    if recordings_url_serialized_obj else None

        except Exception as e:
            error_logger.error(e.args)

        return event_dict

    @staticmethod
    def get_attachments_count_for_event_obj(chatroom_instance=None, conversation_instance=None):

        filter_dict = {
            "chatroom_id": chatroom_instance,
            "conversation_id": conversation_instance
        }

        event_attachment_count = ModelUtilities.get_model_filter(EventRecordingsAttachments, filter_dict).count()

        event_url_count = ModelUtilities.get_model_filter(EventRecordingsURL, filter_dict).count()

        return event_attachment_count, event_url_count

    @staticmethod
    def validate_publish_event_webflow_req_body(req_body):

        if 'site_id' not in req_body:
            return {'success': False, 'error_message': 'Send site_id'}

        if 'domains' not in req_body:
            return {'success': False, 'error_message': 'Send domains'}

        if not isinstance(req_body.get('domains'), list):
            return {'success': False, 'error_message': 'Domains must be list'}

        return {'success': True, 'req_body': req_body}

    @staticmethod
    def fetch_event_recordings_and_event_urls_for_chatroom_list(user_instance, card_ids_list):

        chatroom_event_recordings_mapper = ChatroomHelper.create_chatroom_to_event_recordings_mapper(card_ids_list)

        chatroom_event_url_mapper = ChatroomHelper.create_chatroom_to_event_url_mapper(card_ids_list)

        card_instance_filter = ModelUtilities.get_model_filter(Collabcard, {'id__in': card_ids_list})

        for event_obj in card_instance_filter:
            recordings_attachment_obj = []
            recordings_url_obj = []

            if event_obj.id in chatroom_event_recordings_mapper:
                recordings_attachment_obj = chatroom_event_recordings_mapper[event_obj.id]['recording_attachments']

            if event_obj.id in chatroom_event_url_mapper:
                recordings_url_obj = chatroom_event_url_mapper[event_obj.id]['recording_url']

            event_record_data = ChatroomHelper.display_event_recordings_and_attachments(
                user_instance=user_instance, card_instance=event_obj,
                recordings_attachment_serialized_obj=recordings_attachment_obj,
                recordings_url_serialized_obj=recordings_url_obj)

            chatroom_event_recordings_mapper[event_obj.id] = event_record_data

        return chatroom_event_recordings_mapper

    @staticmethod
    def create_chatroom_to_event_recordings_mapper(card_ids_list):

        chatroom_event_recordings_mapper = {}

        event_recording_instances = ModelUtilities.get_model_filter(
            EventRecordingsAttachments, {'chatroom_id__in': card_ids_list}).prefetch_related('chatroom_id')

        serialized_event_rec = EventRecordingsAttachmentsSerializer(event_recording_instances, many=True).data

        for event_rec_obj in serialized_event_rec:
            event_rec_obj = dict(event_rec_obj)

            if event_rec_obj['chatroom_id'] not in chatroom_event_recordings_mapper:
                chatroom_event_recordings_mapper[event_rec_obj['chatroom_id']] = {}
                chatroom_event_recordings_mapper[event_rec_obj['chatroom_id']]['recording_attachments'] = [
                    event_rec_obj]

            else:
                chatroom_event_recordings_mapper[event_rec_obj['chatroom_id']]['recording_attachments'].append(
                    event_rec_obj)

        return chatroom_event_recordings_mapper

    @staticmethod
    def create_chatroom_to_event_url_mapper(card_ids_list):

        chatroom_event_url_mapper = {}

        event_url_instances = ModelUtilities.get_model_filter(
            EventRecordingsURL, {'chatroom_id__in': card_ids_list}).prefetch_related('chatroom_id')

        serialized_event_url = EventRecordingsURLSerializer(event_url_instances, many=True).data

        for event_url_obj in serialized_event_url:
            event_url_obj = dict(event_url_obj)

            if event_url_obj['chatroom_id'] not in chatroom_event_url_mapper:
                chatroom_event_url_mapper[event_url_obj['chatroom_id']] = {}
                chatroom_event_url_mapper[event_url_obj['chatroom_id']]['recording_url'] = [
                    event_url_obj]

            else:
                chatroom_event_url_mapper[event_url_obj['chatroom_id']]['recording_url'].append(
                    event_url_obj)

        return chatroom_event_url_mapper

    @staticmethod
    def get_create_dict_for_creating_url_instance_for_event(req_body, recording_url_og_tags):
        update_dict = {
            'recording_url_og_tags': json.dumps(recording_url_og_tags),
            'is_recording': req_body.get('is_recording', False),
            'about_recording': req_body.get('about_recording'),
        }

        return update_dict

    @staticmethod
    def get_meta_data_for_calendar_updation(req_body, card_instance, new_co_hosts, attending_members_list):
        meta_data_for_calendar_updation = {}

        if req_body.get('about') and req_body.get('about') != card_instance.about:
            meta_data_for_calendar_updation['description'] = req_body.get('about')

        if req_body.get('title') and req_body.get('title') != card_instance.title:
            meta_data_for_calendar_updation['summary'] = req_body.get('title')

        if req_body.get('date_time') and req_body.get('date_time') != card_instance.date_time:
            meta_data_for_calendar_updation['start'] = {
                'dateTime': TimeUtilities.convert_epoch_time_to_RFC3339(req_body.get('date_time')),
                'timeZone': settings.TIME_ZONE,
            }

        if req_body.get('end_date') and req_body.get('end_date') != card_instance.end_date:
            meta_data_for_calendar_updation['end'] = {
                'dateTime': TimeUtilities.convert_epoch_time_to_RFC3339(req_body.get('end_date')),
                'timeZone': settings.TIME_ZONE,
            }

        if new_co_hosts:
            user_email_filter = ModelUtilities.get_model_filter(userEmails,
                                                                {'user__in': attending_members_list,
                                                                 'email_state': email_states.PRIMARY,
                                                                 'verified': True}).order_by('created_at')

            user_email_list = [{'email': instance.email} for instance in user_email_filter if instance.email]
            meta_data_for_calendar_updation['attendees'] = user_email_list

        return meta_data_for_calendar_updation

    @staticmethod
    def validate_secret_chatroom_participants_or_raise_exception(secret_chatroom_participants):
        try:
            secret_chatroom_participants = NumberUtilities.convert_list_to_integer_list_or_raise_exception(
                list_to_convert=secret_chatroom_participants
            )

        except Exception as e:
            raise InvalidSecretChatroomParticipantsException()

        return secret_chatroom_participants

    @staticmethod
    def fetch_chatroom_link(chatroom_instance, domain_url=None):

        if chatroom_instance.type in [card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
            chatroom_url = chatroom_instance.single_event_url

            if not chatroom_url:
                chatroom_url = ChatroomHelper.create_or_update_single_event_branch_link(chatroom_instance.id)

        else:

            domain_url = domain_url if domain_url else settings.WEB_URL
            chatroom_url = CHATROOM_URL_WITH_COMMUNITY_ID % (domain_url, str(chatroom_instance.id),
                                                             str(chatroom_instance.community.id))

        return chatroom_url

    @staticmethod
    def post_added_all_members_conversation(chatroom_instance, user_instance):

        conversation_filter = ModelUtilities.get_model_filter(card_answers, {
            'card': chatroom_instance,
            'state': conversation_states.CONVERSATION_ADD_ALL_MEMBERS,
            'answer__endswith': ' added all members'
        })

        if not conversation_filter:
            conversation_impl.ConversationHelper.create_conversation_state(
                chatroom_instance, user_instance, conversation_states.CONVERSATION_ADD_ALL_MEMBERS)

    @staticmethod
    def get_chatroom_related_cohort_data_with_total_member_count(card_instance):
        chatroom_cohorts = ModelUtilities.get_model_filter(ChatroomCohort, {
            'chatroom_id': card_instance.id
        }).prefetch_related('cohort')

        cohort_context_list = []

        for chatroom_cohort in chatroom_cohorts:
            cohort_context = {
                'cohort_id': chatroom_cohort.cohort.id,
                'name': chatroom_cohort.cohort.name,
                'community_id': chatroom_cohort.cohort.community_id,
                'total_members': ModelUtilities.get_model_filter(CohortMember, {
                    'cohort_id': chatroom_cohort.cohort.id}).count()
            }
            cohort_context_list.append(cohort_context)

        return cohort_context_list

    @staticmethod
    def validate_block_member_request(user_id, chatroom_id, req_body):
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return get_error_context(False, "Invalid user id")

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return get_error_context(False, "Invalid chatroom id")

        if req_body.get('status') not in [block_chatroom_states.BLOCK, block_chatroom_states.UNBLOCK]:
            return get_error_context(False, "Invalid status")

        return {'success': True, 'user_instance': user_instance, 'chatroom_instance': card_instance,
                'status': req_body.get('status')}

    @staticmethod
    def validate_request_dm_request(user_id, chatroom_id, req_body):
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return get_error_context(False, "Invalid user id")

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return get_error_context(False, "Invalid chatroom id")

        if any([not card_instance.is_private, card_instance.type != card_types.CARD_DIRECT_MESSAGE]):
            return get_error_context(False, "Not a DM chatroom")

        if req_body.get('chat_request_state') not in [chat_request_states.INITIATED, chat_request_states.ACCEPTED,
                                                      chat_request_states.REJECTED]:
            return get_error_context(False, "Invalid chat request state")

        return {'success': True, 'user_instance': user_instance, 'chatroom_instance': card_instance,
                'chat_request_state': req_body.get('chat_request_state')}

    @staticmethod
    def get_dm_chatroom_from_members(community_id, user_id, chatroom_with_user_id):
        card_filter = ModelUtilities.get_model_filter(Collabcard,
                                                      {'is_private': True,
                                                       'type': card_types.CARD_DIRECT_MESSAGE,
                                                       'community_id': community_id,
                                                       'user__in': [user_id, chatroom_with_user_id],
                                                       'chatroom_with_user__in': [user_id, chatroom_with_user_id]})

        if card_filter:
            return card_filter[0]

        else:
            return None

    @staticmethod
    def initiate_dm_connection_request(user_instance, card_instance, user_member_state, member_state,
                                       user_has_dm_right, message, chat_request_state, user_instances_list,
                                       card_state_filter):

        if any([user_member_state == member_states.ADMIN, member_state == member_states.ADMIN]):
            return get_error_context(False, 'Cannot initiate DM request in which one user is CM!')

        if not user_has_dm_right:
            return get_error_context(False, 'You cannot initiate connection request!')

        if card_state_filter.exclude(Q(chat_request_state=None) |
                                     Q(chat_requested_by=None) |
                                     Q(chat_request_created_at=None)):
            return get_error_context(False, 'Connection request already initiated, accepted or rejected!')

        if not message:
            return get_error_context(False, 'Empty text!')

        ModelUtilities.model_update(collabcardState, {'card': card_instance},
                                    {'chat_request_state': chat_request_state,
                                     'chat_request_initiated_by': user_instance,
                                     'chat_requested_by': user_instance,
                                     'chat_request_created_at': TimeUtilities.current_time_in_milliseconds(),
                                     'updated_at': TimeUtilities.current_time_in_sec()})

        conv_state = conversation_states.ANSWER

        if card_instance.user == user_instance:
            other_member_instance = card_instance.chatroom_with_user

        else:
            other_member_instance = card_instance.user

        conversation_instance = initial_message_dm_chatroom(card_instance, user_instance, other_member_instance,
                                                            card_instance.community, user_instances_list,
                                                            message, user_member_state, member_state,
                                                            conversation_state=conv_state)

        send_notification_on_dm_request_initiation.delay(card_instance.id, user_instance.id,
                                                         user_instance.userinfo.name)

        from collabmates_api.conversation.conversation_impl import ConversationHelper
        ConversationHelper.update_latest_conversation_id_to_firebase_v1.delay(card_instance.id,
                                                                              conversation_instance.id,
                                                                              card_instance.community_id,
                                                                              only_update_home_feed=True)

        context = {"current_user_id": user_instance.id, "fetch_reply": True}
        conversation = CardAnswersDBSyncSerializer(conversation_instance, context=context, many=False).data

        return {'success': True, 'conversation': conversation}

    @staticmethod
    def accept_dm_connection_request(user_instance, card_instance, user_member_state, member_state,
                                     chat_request_state, card_state_filter, message=None, user_instances_list=None):

        if any([user_member_state == member_states.ADMIN, member_state == member_states.ADMIN]):
            ModelUtilities.model_update(collabcardState, {'card': card_instance},
                                        {'chat_request_state': chat_request_state,
                                         'chat_requested_by': user_instance,
                                         'chat_request_created_at': TimeUtilities.current_time_in_milliseconds(),
                                         'updated_at': TimeUtilities.current_time_in_sec()})

            conv_state = conversation_states.ANSWER

            if card_instance.user == user_instance:
                other_member_instance = card_instance.chatroom_with_user

            else:
                other_member_instance = card_instance.user

            conversation_instance = initial_message_dm_chatroom(card_instance, user_instance, other_member_instance,
                                                                card_instance.community, user_instances_list,
                                                                message, user_member_state, member_state,
                                                                conversation_state=conv_state)

            context = {"current_user_id": user_instance.id, "fetch_reply": True}
            conversation = CardAnswersDBSyncSerializer(conversation_instance, context=context, many=False).data

            return {'success': True, 'should_call_block_unblock': True, 'conversation': conversation}

        if card_state_filter.exclude(chat_request_state=chat_request_states.INITIATED):
            return get_error_context(False, 'Connection request either not initiated or is rejected!')

        chat_requested_by_filter = card_state_filter.exclude(chat_requested_by=None)

        if not chat_requested_by_filter:
            return get_error_context(False, 'Connection request is not initiated yet!')

        if chat_requested_by_filter[0].chat_requested_by.id == user_instance.id:
            return get_error_context(False, 'Connection requester and acceptor cannot be same!')

        ModelUtilities.model_update(collabcardState, {'card': card_instance},
                                    {'chat_request_state': chat_request_state,
                                     'chat_requested_by': user_instance,
                                     'updated_at': TimeUtilities.current_time_in_sec()})

        return {'success': True, 'should_call_block_unblock': True}

    @staticmethod
    def reject_dm_connection_request(user_instance, card_instance, user_member_state, member_state,
                                     chat_request_state, card_state_filter):

        if any([user_member_state == member_states.ADMIN, member_state == member_states.ADMIN]):
            return get_error_context(False, 'Cannot reject DM request in which one user is CM!')

        if card_state_filter.exclude(chat_request_state=chat_request_states.INITIATED):
            return get_error_context(False, 'Connection request either not initiated or is accepted!')

        chat_requested_by_filter = card_state_filter.exclude(chat_requested_by=None)

        if not chat_requested_by_filter:
            return get_error_context(False, 'Connection request is not initiated yet!')

        if chat_requested_by_filter[0].chat_requested_by.id == user_instance.id:
            return get_error_context(False, 'Connection requester and rejecter cannot be same!')

        ModelUtilities.model_update(collabcardState, {'card': card_instance},
                                    {'chat_request_state': chat_request_state,
                                     'chat_requested_by': user_instance,
                                     'updated_at': TimeUtilities.current_time_in_sec()})

        return {'success': True, 'should_call_block_unblock': True}

    @staticmethod
    @shared_task
    def create_or_update_single_event_branch_link(card_id):

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

        if not card_instance:
            return

        branch_link = create_single_event_branch_url(card_instance)

        if branch_link:
            card_instance.single_event_url = branch_link
            card_instance.save()

        return branch_link

    @staticmethod
    def set_chatroom_participants_created_key_in_cache(chatroom_id, are_participants_created=False):
        key = CHATROOM_PARTICIPANTS_CREATED_CACHE_KEY.format(chatroom_id)
        CacheImpl.set_cache(key, {"are_participants_created": are_participants_created})

    @staticmethod
    @shared_task
    def trigger_event_analytics_on_pausing_chatroom_noti(user_id, chatroom_id, pause_noti_for):
        event_name = CHATROOM_NOTIFICATION_PAUSE_EVENT

        chatroom = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        community_name = chatroom.community.name if chatroom else ""
        community_id = chatroom.community.id if chatroom else ""

        pause_noti_time = TimeUtilities.convert_milliseconds_to_hrs(pause_noti_for)

        if pause_noti_time == PauseChatroomNotificationTime.EIGHT_HR:
            duration = PauseChatroomNotificationTime.EIGHT_HOURS

        elif pause_noti_time == PauseChatroomNotificationTime.TWENTY_FOUR_HR:
            duration = PauseChatroomNotificationTime.TWENTY_FOUR_HOURS

        else:
            duration = PauseChatroomNotificationTime.ONE_WEEK

        event_dict = {
            'chatroom_id': chatroom_id,
            'community_id': community_id,
            'community_name': community_name,
            'duration': duration
        }

        SegmentImpl.track_event(user_id, event_name, event_dict)

    @staticmethod
    @shared_task
    def trigger_event_analytics_on_updating_chatroom_noti_settings(user_id, chatroom_id, noti_state):
        event_name = CHATROOM_NOTIFICATION_SETTING_UPDATED_EVENT

        chatroom = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        community_name = chatroom.community.name if chatroom else ""
        community_id = chatroom.community.id if chatroom else ""

        if noti_state == noti_states.ALL_MESSAGES:
            setting = noti_states.ALL_MESSAGES_ANALYTICS

        elif noti_state == noti_states.ONLY_MENTIONS_AND_REPLIES:
            setting = noti_states.ONLY_MENTIONS_AND_REPLIES_ANALYTICS

        else:
            setting = noti_states.DM_MENTION_REPLIES_POLL_ANALYTICS

        event_dict = {
            'chatroom_id': chatroom_id,
            'community_id': community_id,
            'community_name': community_name,
            'setting': setting
        }

        SegmentImpl.track_event(user_id, event_name, event_dict)

    @staticmethod
    def chatroom_participants_count(card_instance):
        return get_chatroom_participants_count(card_instance.id, card_instance.community_id)

    @staticmethod
    def set_chatroom_conversion_type_status_key_in_cache(chatroom_id, is_converting=False):
        key = CHATROOM_TYPE_CONVERSION.format(chatroom_id)
        CacheImpl.set_cache(key, {"is_converting": is_converting})

    @staticmethod
    def get_chatroom_conversion_type_status_of_chatroom_from_cache(chatroom_id):

        key = CHATROOM_TYPE_CONVERSION.format(chatroom_id)
        chatroom_conversion_type = CacheImpl.get_cache(key)

        if chatroom_conversion_type:
            return chatroom_conversion_type.get('is_converting', False)

        return False

    @staticmethod
    def fetch_new_co_hosts_list(card_instance, req_body):
        is_converted, new_co_hosts = NumberUtilities.convert_list_to_integer_list_with_conversion_status(
            req_body.get('co_hosts') if req_body.get('co_hosts') else [])

        if not is_converted:
            return ResponseUtilities.get_impl_error_context('Invalid co-hosts list',
                                                            status_codes.HTTP_400_BAD_REQUEST)

        is_converted, already_added_co_hosts = NumberUtilities.convert_list_to_integer_list_with_conversion_status(
            json.loads(card_instance.co_hosts) if card_instance.co_hosts else [])

        if not is_converted:
            return ResponseUtilities.get_impl_error_context('Invalid co-hosts list',
                                                            status_codes.HTTP_400_BAD_REQUEST)

        attending_members_list = list(ModelUtilities.get_model_filter(
            collabcardState, {'card': card_instance, 'attending_status': True}).values_list('user_id', flat=True))

        new_co_hosts = list(set(new_co_hosts) - set(already_added_co_hosts) - set(attending_members_list))

        return new_co_hosts, list(set(attending_members_list + new_co_hosts))

    @staticmethod
    def get_everyone_group_tag() -> dict:
        return {
            'name': '@everyone',
            'route': 'route://everyone',
            'tag': '<<@everyone|route://everyone>>',
            'image_url': 'https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/Group-Tag-Icon.jpg',
            'description': 'Notify all community members'
        }

    @staticmethod
    def get_participants_group_tag() -> dict:
        return {
            'name': '@participants',
            'route': 'route://participants',
            'tag': '<<@participants|route://participants>>',
            'image_url': 'https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/Group-Tag-Icon.jpg',
            'description': 'Notify all participants of this chatroom'
        }

    @staticmethod
    @shared_task
    def run_async_tasks_for_users_removing_from_chatroom(chatroom_id, removed_members_list, current_user_id,
                                                         chatroom_state=conversation_states.CONVERSATION_REMOVED_FROM_CHATROOM):

        chatroom_instance = ModelUtilities.get_model_filter(Collabcard, chatroom_id)

        if not chatroom_instance:
            return

        filter_dict = {
            'card': chatroom_id,
            'user__in': removed_members_list
        }

        state_filter = ModelUtilities.get_model_filter(collabcardState,
                                                       filter_dict).prefetch_related('user')

        for state_instance in state_filter:
            user_id = state_instance.user_id

            ChatroomHelper.create_answer(chatroom_instance=chatroom_instance, user_instance=state_instance.user,
                                         state=chatroom_state, current_user_id=current_user_id)

            update_last_unseen_in_engage(user=user_id, community=chatroom_instance.community_id)

            ElasticSearchSync.delete_chatroom_for_user(chatroom_id, user_id)

    @staticmethod
    def validate_remove_chatroom_participant_request(user_id, chatroom_id, removed_members_list: list,
                                                     uuids: list = None):

        if (removed_members_list and not isinstance(removed_members_list, list)) or \
                (uuids and not isinstance(uuids, list)) or (not removed_members_list and not uuids):
            return ResponseUtilities.get_inner_error_context("Invalid removed members or uuids list!")

        validation_params = {
            'chatroom_id': chatroom_id,
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        card_instance = validated_dict.get('chatroom_id')
        user_instance = validated_dict.get('user_id')

        if card_instance.is_secret:
            return ResponseUtilities.get_inner_error_context("Chatroom should be open!")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': card_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("You are not a part of this community.")

        member_instance = member_filter[0]

        if not (member_instance.state == member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context("You are not CM/owner of community!")

        return {'user_instance': user_instance, 'chatroom_instance': card_instance}

    @staticmethod
    def validate_add_chatroom_cohort_request(user_id, chatroom_id, cohort_ids):

        if not cohort_ids or not chatroom_id:
            return ResponseUtilities.get_inner_error_context("Send cohort IDs and chatroom ID!")

        if not isinstance(cohort_ids, list):
            return ResponseUtilities.get_inner_error_context("Invalid cohort ID list!")

        validation_params = {
            'chatroom_id': chatroom_id,
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        chatroom_instance = validated_dict.get('chatroom_id')
        user_instance = validated_dict.get('user_id')

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': chatroom_instance.community_id,
                                                                  'member_id': user_instance})
        if not member_filter:
            return ResponseUtilities.get_inner_error_context("User is not a member of community!")

        member_instance = member_filter[0]

        if not (member_instance.state == member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context(
                "User doesn’t have the ability to remove a cohort from chatroom!")

        return {'user_instance': user_instance, 'chatroom_instance': chatroom_instance}

    @staticmethod
    def validate_remove_chatroom_cohort_request(user_id, chatroom_id, cohort_id):

        if not cohort_id or not chatroom_id:
            return ResponseUtilities.get_inner_error_context("Send cohort IDs and chatroom ID!")

        validation_params = {
            'cohort_id': cohort_id,
            'chatroom_id': chatroom_id,
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        chatroom_instance = validated_dict.get('chatroom_id')
        user_instance = validated_dict.get('user_id')

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': chatroom_instance.community_id,
                                                                  'member_id': user_instance})
        if not member_filter:
            return ResponseUtilities.get_inner_error_context("User is not a member of community!")

        member_instance = member_filter[0]

        if not (member_instance.state == member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context(
                "User doesn’t have the ability to remove a cohort from chatroom!")

        return {'user_instance': user_instance, 'chatroom_instance': chatroom_instance}

    @staticmethod
    def get_ordered_user_ids_list_based_on_filter(user_ids):

        preserved = Case(*[When(user_id=user_id, then=pos) for pos, user_id in enumerate(user_ids)])
        queryset = Userinfo.objects.filter(user_id__in=user_ids).order_by(preserved)

        return queryset

    @staticmethod
    def validate_fetch_participants_meta_request(user_id, chatroom_id):
        validation_params = {
            'chatroom_id': chatroom_id,
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        card_instance = validated_dict.get('chatroom_id')
        user_instance = validated_dict.get('user_id')

        if card_instance.is_secret:
            return ResponseUtilities.get_inner_error_context("Chatroom is secret!")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_fetch_secret_participants_meta_request(user_id, chatroom_id):
        validation_params = {
            'chatroom_id': chatroom_id,
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        card_instance = validated_dict.get('chatroom_id')
        user_instance = validated_dict.get('user_id')

        if not card_instance.is_secret:
            return ResponseUtilities.get_inner_error_context("Chatroom is open!")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def get_participants_count_in_chatroom(chatroom_instance):

        if chatroom_instance.is_secret:
            secret_room_participants = json.loads(chatroom_instance.secret_chatroom_participants)
            participant_count = len(get_members_based_on_user_list_query(secret_room_participants,
                                                                         chatroom_instance.community_id))

        else:
            participant_count = ChatroomHelper.chatroom_participants_count(chatroom_instance)

        return participant_count

    @staticmethod
    @shared_task
    def create_chatroom_invite_to_users(user_id: int, chatroom_id: int, users_list: list):
        validation_params = {
            'chatroom_id': chatroom_id,
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return

        user_instance = validated_dict.get('user_id')
        chatroom_instance = validated_dict.get('chatroom_id')

        filter_dict = {
            'chatroom': chatroom_instance,
            'invite_status': chatroom_invite_status_types.INVITE_INITIATED
        }

        chatroom_invite_filter = ModelUtilities.get_model_filter(ChatroomInvite, filter_dict)
        already_invited_users_list = list(chatroom_invite_filter.values_list('invite_receiver', flat=True))

        new_users = list(set(users_list) - set(already_invited_users_list) - {user_id})

        chatroom_invite_list = []

        for user_id in new_users:
            invite_receiver_instance = ModelUtilities.get_user_instance_or_none(user_id)

            if not invite_receiver_instance:
                continue

            chatroom_invite_list.append(ChatroomInvite(**{
                'chatroom': chatroom_instance,
                'invite_sender': user_instance,
                'invite_receiver': invite_receiver_instance,
                'invite_status': chatroom_invite_status_types.INVITE_INITIATED,
                'created_at': TimeUtilities.current_time_in_milliseconds(),
                'updated_at': TimeUtilities.current_time_in_milliseconds()
            }))

        ModelUtilities.bulk_create_instances(ChatroomInvite, chatroom_invite_list)

    @staticmethod
    def validate_get_chatroom_invites_request(user_id, api_key):
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        community_instance = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_update_chatroom_invite_request(user_id, chatroom_id, invite_status):
        if invite_status not in [chatroom_invite_status_types.INVITE_ACCEPTED,
                                 chatroom_invite_status_types.INVITE_REJECTED]:
            return ResponseUtilities.get_inner_error_context('Invalid invite status!')

        validation_params = {
            'chatroom_id': chatroom_id,
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        chatroom_instance = validated_dict.get('chatroom_id')
        user_instance = validated_dict.get('user_id')

        return {'user_instance': user_instance, 'chatroom_instance': chatroom_instance}

    @staticmethod
    def validate_update_chatroom_settings_request(user_id, chatroom_id, chatroom_settings: list = None):

        if (not chatroom_settings) or (chatroom_settings and not isinstance(chatroom_settings, list)):
            return ResponseUtilities.get_inner_error_context('Invalid chatroom settings list!')

        validation_params = {
            'chatroom_id': chatroom_id,
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        chatroom_instance = validated_dict.get('chatroom_id')
        user_instance = validated_dict.get('user_id')

        if not Members.is_member_community_promoter(chatroom_instance.community, user_instance):
            return ResponseUtilities.get_inner_error_context('User cannot update chatroom settings!')

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance
        }
    
    @staticmethod
    def compute_user_chatroom_settings(participant_instance, chatroom_instance, is_admin: bool = False,
                                       setting_types: list = None) -> list:
        
        if not all([participant_instance, chatroom_instance]):
            return []
        
        response_user_channel_settings = []

        # Create user chatroom settings response list
        for setting in CHATROOM_USER_SETTINGS:
            
            # For member_can_message setting
            if setting == CHATROOM_USER_SETTINGS_MEMBER_CAN_MESSAGE:
                response_user_channel_settings.append(UserChannelSettings(user=participant_instance,
                                                                          chatroom=chatroom_instance,
                                                                          setting_type=setting,
                                                                          enabled=chatroom_instance.member_can_message))
        
        # Filter user chatroom settings based on setting_types
        if setting_types:
            response_user_channel_settings = [setting for setting in response_user_channel_settings
                                              if setting.setting_type in setting_types]

        # If ADMIN, return settings with enabled as TRUE
        if is_admin:
            for setting in response_user_channel_settings:
                setting.enabled = True

        else:
            # Get User Channel settings for participant
            user_channel_settings = ModelUtilities.get_model_filter(UserChannelSettings,
                                                                    {'user': participant_instance,
                                                                     'chatroom': chatroom_instance})
        
            for setting in user_channel_settings:
                for response_setting in response_user_channel_settings:
                    if setting.setting_type == response_setting.setting_type:
                        response_setting.enabled = setting.enabled

        return response_user_channel_settings

    @staticmethod
    def update_user_chatroom_settings_helper(participant_instance, member_instance, chatroom_instance,
                                             chatroom_settings: list):
        
        if not all([participant_instance, member_instance, chatroom_instance, chatroom_settings]):
            return []
        
        updated_settings = []

        # Update User Channel settings based on request
        for setting in chatroom_settings:
            setting_type = setting.get('setting_type')
            enabled = True if setting.get('enabled') == True else False

            if setting_type == CHATROOM_USER_SETTINGS_MEMBER_CAN_MESSAGE:
                filter_dict = {
                    'user': participant_instance,
                    'chatroom': chatroom_instance,
                    'setting_type': setting_type}
                
                update_dict = {
                    'enabled': enabled,
                    'changed_by': member_instance,
                }
            
                updated_settings.append(ModelUtilities.update_or_create_model(UserChannelSettings, filter_dict,
                                                                              update_dict)[0])

        return updated_settings

    @staticmethod
    def validate_chatroom_user_settings_request(member_id, api_key, participant_uuid, chatroom_id,
                                                update_settings: bool = False):
        """
            This method validates chatroom user settings requests and returns instances
        """    

        # Get user and community instances
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': member_id,
            'chatroom_id': chatroom_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        # If any error occured while getting user or community instance, return error
        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instance = validated_dict.get('community_id')
        member_instance = validated_dict.get('user_id')
        chatroom_instance = validated_dict.get('chatroom_id')

        member_state = Members.get_community_member_state(community_instance, member_instance)
        
        if not member_state:
            return ResponseUtilities.get_inner_error_context('You are not part of the community!')

        participant_ids = ModelUtilities.get_valid_member_ids([participant_uuid], community_instance.id)
        
        if not participant_ids or len(participant_ids) < 1:
            return ResponseUtilities.get_inner_error_context('Invalid participant_uuid!')
        
        participant_instance = ModelUtilities.get_user_instance_or_none(participant_ids[0])
        
        if not participant_instance:
            return ResponseUtilities.get_inner_error_context('Invalid participant_uuid!')
        
        participant_state = Members.get_community_member_state(community_instance, participant_instance)

        if not participant_state:
            return ResponseUtilities.get_inner_error_context('participant_uuid is not part of the community!')
        
        # Get collabcardstate for participant and chatroom
        collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState, {
            'user': participant_instance,
            'card': chatroom_instance,
            'follow_status': True,
            'remove_id': None,
            'is_tagged': False,
        })

        # If participant is not part of the chatroom and is secret
        if not collabcard_state_filter and chatroom_instance.is_secret:
            return ResponseUtilities.get_inner_error_context('participant_uuid is not part of this secret chatroom!')
        
        member_is_admin = (member_state == member_states.ADMIN)
        participant_is_admin = (participant_state == member_states.ADMIN)

        # If member_instance not equal to participant_instance and member is not ADMIN
        if member_instance != participant_instance and not member_is_admin:
            return ResponseUtilities.get_inner_error_context('You are not authorized to peform this action!')
        
        # Validate request for update request
        if update_settings:

            # If logged in user is not admin 
            if not member_is_admin:
                return ResponseUtilities.get_inner_error_context('You are not authorized to peform this action!')
            
            # Do not update settings for Admin
            if participant_is_admin:
                return ResponseUtilities.get_inner_error_context('You cannot update settings of an Admin!')
        
        validated_dict = {
            'member_instance': member_instance,
            'community_instance': community_instance,
            'chatroom_instance': chatroom_instance,
            'participant_instance': participant_instance,
            'participant_is_admin': participant_is_admin,
        }

        return validated_dict
    
    @staticmethod
    def validate_update_event_request(user_id, chatroom_id, api_key=None):

        validation_params = {
            'chatroom_id': chatroom_id,
            'user_id': user_id
        }

        if api_key:
            validation_params['community_id'] = {
                'api_key': api_key
            }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        card_instance = validated_dict.get('chatroom_id')
        user_instance = validated_dict.get('user_id')

        if card_instance.user_id != user_instance.id:
            return ResponseUtilities.get_inner_error_context("Only card creator can update the chatroom")

        return {'user_instance': user_instance, 'chatroom_instance': card_instance}
    
    @staticmethod
    def validate_create_event_request(user_id, community_id, api_key=None):

        validation_params = {
            'user_id': user_id,
            'community_id': {
                'api_key': api_key,
                'community_id': community_id
            }
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')

        member_state = Members.get_community_member_state(community_instance, user_instance)

        if member_state == member_states.GUEST:
            return {'success': False, 'error_message': "Only members can create events"}
        
        return {'user_instance': user_instance, 
                'community_instance': community_instance,
                'member_state': member_state}
    
    @staticmethod
    def validate_add_or_update_instructor_request(chatroom_id, api_key=None):

        validation_params = {
            'chatroom_id': chatroom_id,
        }
        
        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        card_instance = validated_dict.get('chatroom_id')

        return {'card_instance': card_instance}
    
    @staticmethod
    def validate_add_or_update_highlights_request(chatroom_id, api_key=None):

        validation_params = {
            'chatroom_id': chatroom_id
        }
        
        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        card_instance = validated_dict.get('chatroom_id')

        return {'card_instance': card_instance}
    
    @staticmethod
    def validate_add_or_update_member_testimonials(chatroom_id, api_key=None):

        validation_params = {
            'chatroom_id': chatroom_id
        }
        
        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        card_instance = validated_dict.get('chatroom_id')

        return {'card_instance': card_instance}
    
    @staticmethod
    def validate_add_or_update_event_faq(chatroom_id, api_key=None):

        validation_params = {
            'chatroom_id': chatroom_id
        }
        
        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        card_instance = validated_dict.get('chatroom_id')

        return {'card_instance': card_instance}
    
    @staticmethod
    def validate_update_last_seen_event_request(user_id):

        validation_params = {
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        user_instance = validated_dict.get('user_id')

        return {'user_instance': user_instance}

    @staticmethod
    def validate_fetch_unseen_count_in_event_request(user_id):

        validation_params = {
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        user_instance = validated_dict.get('user_id')

        return {'user_instance': user_instance}
    
    @staticmethod
    def validate_fetch_link_for_event_request(user_id, chatroom_id, api_key):

        validation_params = {
            'user_id': user_id,
            'chatroom_id': chatroom_id,
        }

        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        user_instance = validated_dict.get('user_id')
        card_instance = validated_dict.get('chatroom_id')

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_fetch_link_for_events_list_request(user_id, chatroom_ids, api_key):

        if not isinstance(chatroom_ids, list):
            return ResponseUtilities.get_inner_error_context("chatroom_ids should be of type 'list'")
        
        validation_params = {
            'user_id': user_id,
            'chatroom_ids': chatroom_ids,
        }

        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        user_instance = validated_dict.get('user_id')
        card_instances = validated_dict.get('chatroom_ids')

        return {'user_instance': user_instance, 'card_instances': card_instances}
    
    @staticmethod
    def validate_fetch_user_all_events_request(user_id, api_key=None):

        validation_params = {
            'user_id': user_id,
        }

        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        user_instance = validated_dict.get('user_id')

        return {'user_instance': user_instance}
    
    @staticmethod
    def validate_fetch_user_all_events_meta_request(user_id, community_id, api_key=None):

        validation_params = {
            'user_id': user_id,
            'community_id': {
                'community_id': community_id,
                'api_key': api_key
            }
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_attend_event_request(user_id, chatroom_id, api_key=None):

        validation_params = {
            'user_id': user_id,
            'chatroom_id': chatroom_id,
        }

        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        user_instance = validated_dict.get('user_id')
        card_instance = validated_dict.get('chatroom_id')

        return {'user_instance': user_instance, 'card_instance': card_instance}
    
    @staticmethod
    def validate_set_event_attended_request(user_id, chatroom_id, api_key=None):

        validation_params = {
            'user_id': user_id,
            'chatroom_id': chatroom_id,
        }

        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        user_instance = validated_dict.get('user_id')
        card_instance = validated_dict.get('chatroom_id')

        return {'user_instance': user_instance, 'card_instance': card_instance}
    
    @staticmethod
    def validate_upload_recordings_meta_request(chatroom_id, api_key=None):

        validation_params = {
            'chatroom_id': chatroom_id,
        }

        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        card_instance = validated_dict.get('chatroom_id')

        return {'card_instance': card_instance}
    
    @staticmethod
    def validate_add_event_attachments_request(api_key=None):

        validation_params = {}

        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
            validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

            if validated_dict.get('error_message'):
                return validated_dict
        
        return {}
    
    @staticmethod
    def validate_delete_event_attachments_meta_request(event_recordings_url_id, api_key=None):

        validation_params = {}

        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
            validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

            if validated_dict.get('error_message'):
                return validated_dict
            
        event_url_obj = ModelUtilities.get_model_instance_or_none(
            EventRecordingsURL,
            event_recordings_url_id
        )

        if not event_url_obj:
            return ResponseUtilities.get_inner_error_context("Invalid event url id")
        
        return {'event_url_obj': event_url_obj}
    
    @staticmethod
    def validate_delete_event_attachments_request(event_attachment_id, api_key=None):

        validation_params = {}

        if api_key:
            validation_params['community_id'] = {
                    'api_key': api_key
                }
            
            validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

            if validated_dict.get('error_message'):
                return validated_dict

        event_attachment_obj = ModelUtilities.get_model_instance_or_none(EventRecordingsAttachments,
                                                                         event_attachment_id)

        if not event_attachment_obj:
            return ResponseUtilities.get_inner_error_context("Invalid event attachment id")
        
        return {'event_attachment_obj': event_attachment_obj}

    @staticmethod
    @shared_task
    def update_tag_only_participants_chatroom_setting(chatroom_id, is_selected=False):
        update_dict = {
            'tag_only_participants': is_selected,
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        ModelUtilities.model_update(Collabcard, {'id': chatroom_id}, update_dict)

    @staticmethod
    @shared_task
    def add_cohort_members_to_secret_chatroom(current_user_id: int, chatroom_id: int, cohort_ids: list):
        if not (current_user_id or chatroom_id or cohort_ids):
            pass

        user_ids_list = list(ModelUtilities.get_model_filter(CohortMember, {'cohort__in': cohort_ids}).values_list(
            'user_id', flat=True))

        if not user_ids_list:
            return

        add_new_participants_to_secret_chatroom(current_user_id, chatroom_id, user_ids_list)
