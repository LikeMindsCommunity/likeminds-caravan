import time
import json, uuid
import re
from django.contrib.auth.models import User
from django.db import transaction
from typing import Union

from django.db.models import F, Q, Count
from django.conf import settings
from rest_framework import status as status_codes

from external_services.caching.cache_impl import CacheImpl
from internal_services.url_tags.uri_tags_impl import UriTagsImpl
from utility.cache_keys import EVENT_ATTENDEES_CONVERSATION
from utility.json_utilities import JsonUtilities
from utility.constants import CREATE_INTRO_TEXT_ADMIN, CREATE_INTRO_TEXT_MEMBER, CUSTOM_CLICK_TEXT, MINUTES_5, \
    MINUTES_30, MINUTES_60, PLATFORM_CODE_WEB, SWARM_WIDGET_ENDPOINT
from utility.response_utilities import ResponseUtilities

from .conversation_manager import ConversationManager
from .conversation_view_helper import ConversationViewHelper
from .reactions import fetch_chatroom_or_conversation_reactions
from ..chatroom import chatroom_impl
from ..chatroom.chatroom_impl import ChatroomHelper
from ..notification import send_notification_to_message_creator_on_reaction, get_tagged_members_list, \
    send_notification_on_chatroom_topic_update, send_poll_conversation_creation_notification_v1
from ..notifications.tasks import send_communication_when_chatroom_not_opened
from ..member_community.member_community_impl import MemberCommunityImpl, MemberCommunityHelper
from ..raw_queries import activate_chatroom_on_conversation_creation, \
    get_latest_conversation_creator_users_for_homescreen, update_conversation_engage_for_chatrooms, \
    get_count_of_new_event_conversation_created_for_user, get_last_seen_event_conversation_id_for_user, \
    update_conversation_engage_data_for_chatroom, activate_chatroom_for_followed_users_on_conversation_creation, \
    get_users_sdk_meta_dict
from ..rest_api import CardAnswersDBSyncSerializer
from ..serializers import conversationSerializer, UserinfoSerializer
from ..sync.model_update import update_models_for_syncing_apis
# from ..tasks import send_chatroom_owner_mail
from ..utility import (pagination, m2cm_v2_version_check, is_community_widget_enabled)
from ..user.user_impl import UserHelper
from ..views import (adding_guest_in_chatroom, collabcard_follow_internal,
                     save_the_latest_conversation, update_activity_in_chatroom_for_conversation_creation,
                     update_chatroom_for_users_and_send_follow_notification,
                     reverse_conversations_for_upward_pagination, send_sync_notification,
                     generate_internal_link_preview_for_conversation, send_poll_conversation_creation_notification,
                     create_chatroom_engagement, create_chatroom, collabcard_follow_internal_v1)

from ..static_text import (EVERYONE_TAG_REGEX, PARTICIPANTS_TAG_REGEX, GIF_ATTACHMENT_FILL_TEXT)

from .constants import *
from ..chatroom.constants import CHATROOM_USER_SETTINGS_MEMBER_CAN_MESSAGE, CREATE_CONVERSATION_OG_TAGS_REQUEST_TIMEOUT

from togther.models import (card_answers, collabcardState, Collabcard, Members,
                            Community, ModelUtilities, MessageReactions, conversationPolls,
                            conversationPollMembers, Userinfo, conversationEngage, answerAttachment,
                            conversationEventMembers, conversationEventNudge, UserEmailsSendStatus, userDevices,
                            userMemberRights, UserChannelSettings)
from collabmates_api.sdk.models import SdkClient

from external_services.logging.logging_wrapper import LoggingWrapper

from utility.exception_utilities import CustomException, InvalidChatroomException
from utility.internal_link_preview_utilities import PreviewUtilities
from utility.request_utilities import RequestUtilities
from utility.states import (member_states, collabcard_states, card_types, SyncNotificationTypes, SyncTypes,
                            conversation_states, conversation_poll_types, chatroom_not_opened_types,
                            user_email_send_status_types, member_rights, unsubscribe_types, noti_states,
                            chat_request_states, webhook_chatroom_methods, attachment_types, WidgetTypes, WebhookTypes)

from utility.webhook_utilities import (WebhookUtilties)
from collabmates_api.webhook.constants import (WEBHOOK_SOURCE_CHAT, MAX_WEBHOOK_USERS_META_LIMIT)
from utility.utils import check_notification_flag, is_version_code_supported_for_intro_room, \
    is_member_verified, filter_user_instances_based_on_notification_flag
from utility.firebase import update_last_answer_id, update_my_chatrooms_on_homefeed_in_firebase_for_users_list, \
    update_chatroom_conversation_ids_against_community
from utility.celery_tasks import (update_my_chatrooms_for_users, update_multiple_previews_in_chatroom,
                                  update_preview_of_chatroom_in_cache,
                                  get_conversation_poll, save_conversation_poll_options_in_cache,
                                  save_conversation_poll_voters_in_cache, update_multiple_previews_in_community,
                                  update_event_attendees_for_micro_event, update_unread_message_count_in_cache,
                                  fetch_conversations_unread, reset_unread_message_count_in_cache,
                                  update_deferred_conversation_poll_updated_at_value,
                                  get_to_show_results_for_conversation_poll)

from utility.time_utilities import TimeUtilities
from utility.number_utilities import NumberUtilities
from utility.list_utilities import ListUtilities
from utility.string_utilities import StringUtilities
from celery import shared_task
from ..owner_message_template import post_owner_message_template_in_intro_room, check_owner_template_posted
from collabmates_api.search.sync import ElasticSearchSync
from utility.internal_service_utilities import InternalServiceUtilities

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class ConversationImpl(ConversationManager):
    member_id = None
    chatroom_id = None
    scroll_direction = None
    conversation_id = None
    page = None
    paginate_by = None
    device_id = None
    platform_code = None
    version_code = None

    def __init__(self, member_id: str, chatroom_id: str = None, scroll_direction: str = None,
                 conversation_id: str = None, page: str = None, paginate_by: str = None,
                 device_id: str = None, platform_code: str = None, include_conversation_id: bool = False,
                 version_code: str = None, api_version_code: int = 0):

        self.member_id = member_id
        self.chatroom_id = chatroom_id
        self.scroll_direction = scroll_direction
        self.conversation_id = conversation_id
        self.page = page
        self.paginate_by = paginate_by
        self.device_id = device_id
        self.platform_code = platform_code
        self.include_conversation_id = include_conversation_id
        self.version_code = version_code
        self.api_version_code = api_version_code

    def get_member_id(self) -> Union[str, int]:
        return self.member_id

    def get_version_code(self) -> Union[str, int]:
        return self.version_code

    def get_platform_code(self) -> Union[str, int]:
        return self.platform_code

    def get_api_version_code(self) -> int:
        return self.api_version_code

    def set_member_id(self, member_id: Union[str, int]) -> None:
        self.member_id = member_id

    def get_chatroom_id(self) -> Union[str, int]:
        return self.chatroom_id

    def set_chatroom_id(self, chatroom_id: Union[str, int]):
        self.chatroom_id = chatroom_id

    def get_scroll_direction(self):
        return self.scroll_direction

    def set_scroll_direction(self, scroll_direction: Union[str, int]):
        self.scroll_direction = scroll_direction

    def get_conversation_id(self) -> Union[str, int]:
        return self.conversation_id

    def set_conversation_id(self, conversation_id: Union[str, int]):
        self.conversation_id = conversation_id

    def get_page(self) -> Union[str, int]:
        return self.page

    def set_page(self, page: Union[str, int]):
        self.page = page

    def get_paginate_by(self) -> Union[str, int]:
        return NumberUtilities.get_integer_from_string(self.paginate_by)

    def set_paginate_by(self, paginate_by: Union[str, int]):
        self.paginate_by = paginate_by

    def _fetch_conversation_queryset(self, excluded_conversation_states: list = None):
        conversations = card_answers.objects.filter(card=self.get_chatroom_id())

        if excluded_conversation_states and isinstance(excluded_conversation_states, list):
            conversations = conversations.exclude(state__in=excluded_conversation_states)

        conversations = conversations.select_related('reply', 'preview_community', 'preview_chatroom'
                                                     ).order_by('created_at')

        if is_version_code_supported_for_intro_room(self.get_version_code(), self.get_platform_code()):
            excluded_ids = self.chatroom_previews_with_non_zero_conversation_unread(conversations)
            conversations = conversations.exclude(id__in=excluded_ids)

        return conversations

    def _fetch_unread_preview_queryset(self):
        conversations = card_answers.objects.select_related('reply', 'preview_community',
                                                            'preview_chatroom').filter(card=self.get_chatroom_id()
                                                                                       ).order_by('-created_at')
        included_ids = self.chatroom_previews_with_non_zero_conversation_unread(conversations)
        conversations = conversations.filter(id__in=included_ids)

        return conversations

    def _fetch_scroll_conversations(self, excluded_conversation_states: list = None):
        conversations = ModelUtilities.get_model_filter(card_answers, {'card': self.get_chatroom_id()})

        if excluded_conversation_states and isinstance(excluded_conversation_states, list):
            conversations = conversations.exclude(state__in=excluded_conversation_states)

        conversations = conversations.select_related('reply', 'preview_community', 'preview_chatroom')

        if is_version_code_supported_for_intro_room(self.get_version_code(), self.get_platform_code()):
            excluded_ids = self.chatroom_previews_with_non_zero_conversation_unread(conversations)
            conversations = conversations.exclude(id__in=excluded_ids)

        return conversations

    def _fetch_upward_conversation_queryset(self, list_size, conversation_id,
                                            excluded_conversation_states: list = None):
        conversations = self._fetch_scroll_conversations(excluded_conversation_states)
        conversations = conversations.filter(id__lt=conversation_id).order_by('-created_at')

        return conversations[:list_size]

    def _fetch_upward_conversation_including_given_conversation(self, list_size, conversation_id,
                                                                excluded_conversation_states: list = None):
        conversations = self._fetch_scroll_conversations(excluded_conversation_states)
        conversations = conversations.filter(id__lte=conversation_id).order_by('-created_at')

        return conversations[:list_size]

    def _fetch_downward_conversation_queryset(self, list_size, conversation_id,
                                              excluded_conversation_states: list = None):
        conversations = self._fetch_scroll_conversations(excluded_conversation_states)
        conversations = conversations.filter(id__gt=conversation_id).order_by('created_at')

        return conversations[:list_size]

    def _fetch_downward_conversation_including_given_conversation(self, list_size, conversation_id,
                                                                  excluded_conversation_states: list = None):
        conversations = self._fetch_scroll_conversations(excluded_conversation_states)
        conversations = conversations.filter(id__gte=conversation_id).order_by('created_at')

        return conversations[:list_size]

    def _paged_queryset(self, conversation_filter):
        page = self.get_page()
        paginate_by = self.get_paginate_by()

        return pagination(conversation_filter, page, paginate_by=paginate_by)

    def _fetch_last_seen_conversation(self):

        last_seen_conversation = None
        user_chatroom_instance = collabcardState.objects.filter(card=self.get_chatroom_id(),
                                                                user=self.get_member_id()).first()

        if user_chatroom_instance:
            last_seen_conversation = user_chatroom_instance.last_seen_conversation

        return last_seen_conversation

    def _generate_internal_link_preview(self, conversation_instance):

        preview = generate_internal_link_preview_for_conversation(conversation_instance, self.get_member_id())
        return preview

    def _fetch_conversation_polls(self, conversation_instance):

        member_id = NumberUtilities.get_integer_from_string(self.get_member_id())
        polls = get_conversation_poll({'conversation_instance': conversation_instance, 'member_id': member_id,
                                       'conversation_id': conversation_instance.id,
                                       'poll_type': conversation_instance.poll_type,
                                       'multiple_select_no': conversation_instance.multiple_select_no,
                                       'expiry_time': conversation_instance.expiry_time,
                                       })

        return polls

    def fetch_conversation_poll_to_show_results(self, conversation_instance):
        member_id = NumberUtilities.get_integer_from_string(self.get_member_id())
        to_show_results = get_to_show_results_for_conversation_poll({'conversation_instance': conversation_instance,
                                                                     'member_id': member_id,
                                                                     'conversation_id': conversation_instance.id,
                                                                     'poll_type': conversation_instance.poll_type,
                                                                     'multiple_select_no': conversation_instance.multiple_select_no,
                                                                     'expiry_time': conversation_instance.expiry_time,
                                                                     })
        return to_show_results

    def _serialize_conversation(self, conversation_instance, sdk_client_info_flag:bool=False):

        conversation_serializer = conversationSerializer(conversation_instance,
                                                         fetch_reply=True,
                                                         current_user_id=self.get_member_id(),
                                                         sdk_client_info_flag=sdk_client_info_flag)
        conversation_serializer['created_at'] = TimeUtilities.convert_epoch_time_in_hh_mm(
            conversation_instance.created_at)

        preview = self._generate_internal_link_preview(conversation_instance)

        if preview:
            conversation_serializer['preview'] = preview

        poll_conversation = self._serialize_poll_conversation(conversation_instance)

        if poll_conversation:
            conversation_serializer.update(poll_conversation)

        event_conversation = self._serialize_event_conversation(conversation_instance)

        if event_conversation:
            conversation_serializer.update(event_conversation)

        return conversation_serializer

    def _serialize_poll_conversation(self, conversation_instance):

        poll_conversation = {}

        if conversation_instance.state == conversation_states.CONVERSATION_POLL:
            poll_conversation['state'] = conversation_instance.state
            poll_conversation['poll_type'] = conversation_instance.poll_type

            if conversation_instance.multiple_select_state:
                poll_conversation['multiple_select_state'] = conversation_instance.multiple_select_state

            if conversation_instance.multiple_select_no:
                poll_conversation['multiple_select_no'] = conversation_instance.multiple_select_no

            poll_conversation['is_anonymous'] = conversation_instance.is_anonymous
            poll_conversation['allow_add_option'] = conversation_instance.allow_add_option
            poll_conversation['expiry_time'] = conversation_instance.expiry_time

            poll_conversation['polls'] = self._fetch_conversation_polls(conversation_instance)
            poll_conversation['to_show_results'] = self.fetch_conversation_poll_to_show_results(conversation_instance)

            poll_conversation['poll_type_text'] = "Instant poll" \
                if poll_conversation['poll_type'] == conversation_poll_types.INSTANT else "Deferred poll"

            poll_conversation['submit_type_text'] = "Secret voting" \
                if poll_conversation['is_anonymous'] else "Public voting"

            poll_conversation['poll_answer_text'] = conversation_instance.poll_answer_text

        return poll_conversation

    def _serialize_event_conversation(self, conversation_instance):

        event_conversation = {}

        if conversation_instance.state == conversation_states.CONVERSATION_EVENT:
            event_conversation['state'] = conversation_instance.state
            event_conversation['header'] = conversation_instance.header
            event_conversation['location'] = conversation_instance.location
            event_conversation['location_lat'] = conversation_instance.location_lat
            event_conversation['location_long'] = conversation_instance.location_long

            event_conversation['start_time'] = conversation_instance.start_time
            event_conversation['end_time'] = conversation_instance.end_time
            event_conversation['online_link_enable_before'] = conversation_instance.online_link_enable_before
            members_data = ConversationHelper.compute_members_data_for_conversation(conversation_instance)
            event_conversation.update(members_data)

        return event_conversation

    def _create_conversation_list(self, conversations, last_conversation_id=None, sdk_client_info_flag: bool = False):

        conversation_list = []

        for conversation in conversations:

            if (conversation.attachment_count > 0 and
                conversation.attachments_uploaded is False) and (
                    (self.get_member_id() and
                     conversation.user.id != NumberUtilities.get_integer_from_string(self.get_member_id())) or
                    conversation.api_version <= 0 or conversation.device_id != self.device_id):
                continue

            conversation_dict = self._serialize_conversation(conversation, 
                                                             sdk_client_info_flag=sdk_client_info_flag)

            if last_conversation_id and last_conversation_id == conversation_dict['id']:
                conversation_dict['last_seen'] = True

            conversation_list.append(conversation_dict)

        return conversation_list

    def _is_user_already_guest(self, chatroom, user):
        return collabcardState.objects.filter(card=chatroom,
                                              user=user,
                                              is_guest=True).exists()

    def _fill_basic_conversation_content(self, req_body, conversation_content,
                                         chatroom_instance, user_instance, community_instance,
                                         has_files, chatroom_state_instance, is_guest: bool = False):

        conversation_content['answer'] = req_body['text']
        conversation_content['card'] = chatroom_instance
        conversation_content['user'] = user_instance
        conversation_content['community'] = community_instance

        conversation_content['created_at'] = time.time()
        conversation_content['has_files'] = has_files

        conversation_content['attachment_count'] = req_body.get('attachment_count', 0)
        conversation_content['attachments_uploaded'] = False

        if conversation_content['attachment_count'] > 0:
            conversation_content['has_files'] = True
            req_body['has_files'] = True
        conversation_content['temporary_id'] = req_body.get('temporary_id')
        conversation_content['api_version'] = 1
        conversation_content['device_id'] = self.device_id
        conversation_content['platform'] = self.platform_code
        conversation_content['is_guest'] = chatroom_state_instance.is_guest if chatroom_state_instance else is_guest

        if req_body.get('replied_chatroom_id'):
            conversation_content['reply_chatroom'] = chatroom_instance \
                if chatroom_instance.id == req_body.get('replied_chatroom_id') \
                else ModelUtilities.get_model_instance_or_none(Collabcard, req_body.get('replied_chatroom_id'))

        poll_context = self._fill_poll_conversation_context(req_body)

        if poll_context:
            conversation_content.update(poll_context)

        event_context = self._fill_event_conversation_context(req_body)

        if event_context:
            conversation_content.update(event_context)

    def _fill_poll_conversation_context(self, req_body):

        poll_context = {}

        if req_body.get('state') and req_body['state'] == conversation_states.CONVERSATION_POLL:
            poll_context['state'] = req_body['state']
            poll_context['poll_type'] = req_body['poll_type'] if 'poll_type' in req_body else 0
            poll_context['multiple_select_state'] = \
                (req_body['multiple_select_state'] if 'multiple_select_state'
                                                      in req_body else None)
            poll_context['multiple_select_no'] = req_body[
                'multiple_select_no'] if 'multiple_select_no' in req_body else None
            poll_context['is_anonymous'] = req_body['is_anonymous'] if 'is_anonymous' in req_body else False
            poll_context['allow_add_option'] = req_body['allow_add_option'] if 'allow_add_option' in req_body else False
            poll_context['expiry_time'] = req_body['expiry_time']

            poll_context['poll_answer_text'] = POLL_ANSWER_TEXT

        return poll_context

    def _fill_event_conversation_context(self, req_body):

        event_context = {}

        if req_body.get('state') and req_body['state'] == conversation_states.CONVERSATION_EVENT:
            event_context['state'] = req_body['state']
            event_context['header'] = req_body.get('header')
            event_context['online_link'] = req_body.get('online_link')
            event_context['online_link_id'] = req_body.get('online_link_id')
            event_context['online_link_password'] = req_body.get('online_link_password')
            event_context['location'] = req_body.get('location')
            event_context['location_lat'] = req_body.get('location_lat')
            event_context['location_long'] = req_body.get('location_long')
            event_context['start_time'] = req_body.get('start_time', 0)
            event_context['end_time'] = req_body.get('end_time', 0)
            event_context['online_link_enable_before'] = req_body.get('online_link_enable_before',
                                                                      TimeUtilities.get_minutes_in_milliseconds(15))
            event_context['co_hosts'] = json.dumps(req_body['co_hosts']) if req_body.get('co_hosts') else None

        return event_context

    @staticmethod
    def _fill_poll_options(user_instance, conversation_instance, req_body):

        polls = req_body.get('polls')

        if not polls:
            return

        poll_instances = []

        member = UserinfoSerializer(user_instance.userinfo, sdk_client_info_flag=True)

        for poll in polls:
            poll_instance = conversationPolls.create_instance({'user_instance': user_instance,
                                                               'conversation_instance': conversation_instance,
                                                               'text': poll.get('text', '')})
            temp = {
                'id': poll_instance.id,
                'text': poll_instance.text,
                'user_id': poll_instance.user_id,
                'member': member
            }

            poll_instances.append(temp)

        save_conversation_poll_options_in_cache({'polls': poll_instances,
                                                 'user_id': user_instance.id,
                                                 'conversation_id': conversation_instance.id})

    def _set_preview_for_conversation(self, conversation_instance, req_body):
        preview_utilities = PreviewUtilities()
        preview_utilities.set_preview_object(conversation_instance, req_body, self.get_member_id())
        self._save_conversation(conversation_instance)

    def _create_conversation_instance(self, conversation_content):
        conversation_instance = card_answers(**conversation_content)
        self._save_conversation(conversation_instance)
        return conversation_instance

    def _save_conversation(self, conversation_instance):
        conversation_instance.save()

    def _add_guest_in_chatroom(self, chatroom_instance, community_id, member_state, is_guest, aj, source_id,
                               created_at=TimeUtilities.current_time_in_milliseconds()):

        if is_guest and (member_state == member_states.GUEST or member_state == member_states.PENDING_MEMBER):
            context = {}
            context = adding_guest_in_chatroom(context, chatroom_instance, aj, source_id,
                                               community_id, self.get_member_id(), guest_header=True,
                                               created_at=created_at, platform_code=self.get_platform_code(),
                                               version_code=self.get_version_code())

    def _auto_follow_chatroom(self, chatroom_id, member_state):

        if member_state == member_states.ADMIN or \
                member_state == member_states.MEMBER or \
                member_state == member_states.PROFILE_UNAVAILABLE:
            payload = ConversationHelper.fetch_auto_follow_dict(member_id=self.get_member_id(),
                                                                chatroom_id=chatroom_id,
                                                                status=True, source="create_conversation")

            collabcard_follow_internal(payload, state=collabcard_states.COLLABCARD_STATE_SEEN)

    def _save_latest_conversation_for_members(self, chatroom_instance):
        save_the_latest_conversation(chatroom_instance, self.get_member_id())

    @staticmethod
    def _auto_follow_and_save_last_conversation(chatroom_instance, chatroom_state_instance,
                                                conversation_instance, user_instance, member_state):

        if chatroom_state_instance:
            current_follow_status = chatroom_state_instance.follow_status

            chatroom_state_instance.last_seen_conversation = conversation_instance
            chatroom_state_instance.follow_status = True
            chatroom_state_instance.updated_at = TimeUtilities.current_time_in_sec()
            chatroom_state_instance.save()

            if not current_follow_status:
                create_chatroom_engagement(chatroom_instance, user_instance, member_state=member_state)

        else:

            if member_state == member_states.ADMIN or \
                    member_state == member_states.MEMBER or \
                    member_state == member_states.PROFILE_UNAVAILABLE:
                expiry_time = chatroom_impl.ChatroomHelper.get_chatroom_expiry_time(chatroom_state_instance)
                state_instance = collabcardState.create_chatroom_state_instance(chatroom_instance,
                                                                                user_instance, state=0,
                                                                                expire_at=expiry_time)
                create_chatroom_engagement(chatroom_instance, user_instance, member_state=member_state)

    @staticmethod
    def _auto_follow_for_tagged_members(community_id, chatroom_instance, conversation_instance, user_instance):

        conversation_text = conversation_instance.answer
        tagged_member_list, answer_text, tagged_user_names, should_unmute_members, _ = get_tagged_members_list(
            community_id,
            chatroom_instance.id,
            conversation_text
        )

        if not tagged_member_list:
            return

        is_tagged = True
        is_group_tag_everyone = False

        if should_unmute_members:
            is_tagged = False
            is_group_tag_everyone = True

        if chatroom_instance.type == card_types.CARD_PURPOSE:
            is_tagged = False

        collabcard_follow_internal_v1(
            chatroom_instance,
            tagged_member_list,
            is_tagged,
            is_group_tag_everyone
        )

        # ConversationHelper.run_async_tasks_for_conversation_tagging(tagged_member_list,
        #                                                             user_instance,
        #                                                             chatroom_instance)

    @staticmethod
    def _handle_dm_chatroom_communication(chatroom_instance, user_instance, conversation_instance):

        user_id = chatroom_instance.user_id
        chatroom_with_user_id = chatroom_instance.chatroom_with_user_id

        if chatroom_instance.type == card_types.CARD_DIRECT_MESSAGE and chatroom_instance.is_private:
            sender_id = user_id if user_instance.id == user_id else chatroom_with_user_id
            receiver_id = user_id if user_instance.id != user_id else chatroom_with_user_id

            ConversationHelper.send_engagement_communication(receiver_id, sender_id, chatroom_instance.id,
                                                             chatroom_not_opened_types.DM_CHATROOM)

    def _update_home_page(self, community_instance, chatroom_instance, conversation_instance):
        ConversationHelper.update_the_activity_time_for_new_conversation_creation.delay(chatroom_instance.id,
                                                                                        self.get_member_id())

        ConversationHelper.update_homescreen_meta_on_conversation_creation(community_instance,
                                                                           chatroom_instance,
                                                                           conversation_instance)

    def _send_conversation_creation_notifications(self, chatroom_instance, conversation_instance, has_files):

        is_poll_conversation = (conversation_instance.state == conversation_states.CONVERSATION_POLL)

        if is_poll_conversation:
            send_poll_conversation_creation_notification.delay(conversation_instance.card_id,
                                                               conversation_instance.user_id, conversation_instance.id)

        update_chatroom_for_users_and_send_follow_notification.delay(chatroom_instance.id,
                                                                     self.get_member_id(),
                                                                     conversation_instance.id,
                                                                     has_files=has_files)

    @staticmethod
    def _fetch_member_list_for_poll_conversation(conversation_instance, poll_instance, page, paginated_by):

        poll_member_filter = ModelUtilities.get_model_filter(conversationPollMembers,
                                                             {'conversation': conversation_instance,
                                                              'poll': poll_instance}).order_by('user_id')
        poll_member_filter = pagination(poll_member_filter, page, paginate_by=paginated_by)

        user_list = []

        for data in poll_member_filter:
            user_list.append(data.user_id)

        return user_list

    @staticmethod
    def _create_member_instances_from_user_list(user_list, community_instance):

        member_dict = MemberCommunityImpl.fetch_members_based_on_user_list(user_list, community_instance, 
                                                                           sdk_client_info_flag=True)
        member_introduction_dict = MemberCommunityImpl.fetch_community_introductions_based_on_user_list(user_list,
                                                                                                        community_instance)
        member_list = []

        for user_id in user_list:

            if member_dict.get(user_id):
                member_data = member_dict[user_id]

                if member_introduction_dict.get(user_id):
                    member_data['question_answers'] = [member_introduction_dict[user_id]]

                else:

                    created_at = TimeUtilities.convert_epoch_time_to_date_month_year(member_data['created_at'])

                    if member_data['state'] == member_states.ADMIN:
                        member_data['custom_intro_text'] = CREATE_INTRO_TEXT_ADMIN % created_at

            else:
                userinfo_filter = ModelUtilities.get_model_filter(Userinfo, {'user_id': user_id})

                if userinfo_filter:

                    userinfo_instance = userinfo_filter[0]

                    member_data = MemberCommunityImpl(member_id=user_id, community_id=community_instance.id).\
                        compute_removed_user_context(user_instance=userinfo_instance.user_id,
                                                     community_instance=community_instance)

                else:
                    continue

            member_list.append(member_data)

        return member_list

    def _fill_online_link_for_event(self, conversation_context, conversation_instance):

        if conversation_instance.online_link:
            conversation_context['online_link'] = conversation_instance.online_link

        if conversation_instance.online_link_id:
            conversation_context['online_link_id'] = conversation_instance.online_link_id

        if conversation_instance.online_link_password:
            conversation_context['online_link_password'] = conversation_instance.online_link_password

    @staticmethod
    def fetch_conversation_events_queryset(user_instance, attending_status, past_events):

        current_time_ms = TimeUtilities.current_time_in_milliseconds()
        chatroom_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                             {'user': user_instance, 'remove': None}).
                             values_list('card_id', flat=True))
        attending_list = list(ModelUtilities.get_model_filter(conversationEventMembers,
                                                              {'user': user_instance,
                                                               'attending_status': True}). \
                              values_list('conversation_id', flat=True))

        if not past_events:

            if attending_status:
                conversation_queryset = ModelUtilities.get_model_filter(card_answers, {
                    'state': conversation_states.CONVERSATION_EVENT,
                    'card__in': chatroom_list,
                    'id__in': attending_list,
                    'start_time__gt': current_time_ms
                }). \
                    select_related('community').order_by('start_time')

            else:
                conversation_queryset = ModelUtilities.get_model_filter(card_answers, {
                    'state': conversation_states.CONVERSATION_EVENT,
                    'card__in': chatroom_list,
                    'start_time__gt': current_time_ms
                }).filter(~Q(id__in=attending_list)).select_related('community').order_by('start_time')

        else:

            if attending_status:
                conversation_queryset = ModelUtilities.get_model_filter(card_answers, {
                    'state': conversation_states.CONVERSATION_EVENT,
                    'card__in': chatroom_list,
                    'id__in': attending_list,
                    'start_time__lte': current_time_ms
                }). \
                    select_related('community').order_by('-start_time')

            else:
                conversation_queryset = ModelUtilities.get_model_filter(card_answers, {
                    'state': conversation_states.CONVERSATION_EVENT,
                    'card__in': chatroom_list,
                    'start_time__lte': current_time_ms
                }). \
                    select_related('community').filter(~Q(id__in=attending_list)).order_by('-start_time')

        return conversation_queryset

    def fetch_conversation(self, top_navigate=False, excluded_conversation_states: list = None):

        if excluded_conversation_states:
            excluded_conversation_states = StringUtilities.get_list_from_string(excluded_conversation_states,
                                                                                default=None)

        if top_navigate:
            conversations = self._fetch_conversation_queryset(excluded_conversation_states)
            conversations = conversations[:self.get_paginate_by()]
            conversations = self._create_conversation_list(conversations, sdk_client_info_flag=True)
            return {'success': True, 'conversations': conversations}

        # Client is not sending scroll direction and only sending conversation id
        if self.get_conversation_id() and not self.get_scroll_direction():
            conversation = ModelUtilities.get_model_instance_or_none(card_answers, self.get_conversation_id())

            if not conversation:
                return ResponseUtilities.get_impl_error_context('Invalid conversation ID provided',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            conversations = [conversation]
            conversations = self._create_conversation_list(conversations, sdk_client_info_flag=True)
            return {'success': True, 'conversations': conversations}

        # Client is sending scroll direction as False with conversation ID
        if not self.get_scroll_direction() and self.get_conversation_id():
            last_seen_conversation = self._fetch_last_seen_conversation()

            if last_seen_conversation:
                conversations = [last_seen_conversation]
                conversations = self._create_conversation_list(conversations, sdk_client_info_flag=True)

                return {'success': True, 'conversations': conversations}

        if not self.get_scroll_direction() and not self.get_conversation_id():

            last_seen = self._fetch_last_seen_conversation()

            if not last_seen:
                conversations = self._fetch_conversation_queryset(excluded_conversation_states)
                conversations = conversations[:self.get_paginate_by()]
                conversations = self._create_conversation_list(conversations, sdk_client_info_flag=True)

            else:

                list_size = self.get_paginate_by() / 2
                upward_conversation = self._fetch_upward_conversation_including_given_conversation(
                    list_size, last_seen.id, excluded_conversation_states)
                downward_conversation = self._fetch_downward_conversation_queryset(
                    list_size, last_seen.id, excluded_conversation_states)

                # merging both conversations
                conversations = upward_conversation | downward_conversation
                conversations = conversations.order_by('created_at')
                conversations = self._create_conversation_list(conversations, last_conversation_id=last_seen.id, 
                                                               sdk_client_info_flag=True)

        else:

            if self.get_scroll_direction() and NumberUtilities.get_integer_from_string(
                    self.get_scroll_direction()) == UPWARD_SCROLL_DIRECTION:  # upward scroll

                upward_scroll_list_size = self.get_paginate_by()

                if self.include_conversation_id:
                    upward_list = self._fetch_upward_conversation_including_given_conversation(
                        upward_scroll_list_size, self.get_conversation_id(), excluded_conversation_states)
                else:
                    upward_list = self._fetch_upward_conversation_queryset(upward_scroll_list_size,
                                                                           self.get_conversation_id(),
                                                                           excluded_conversation_states)

                conversations = reverse_conversations_for_upward_pagination(upward_list)

            elif self.get_scroll_direction() and NumberUtilities.get_integer_from_string(
                    self.get_scroll_direction()) == DOWNWARD_SCROLL_DIRECTION:  # downward scroll
                downward_scroll_list_size = self.get_paginate_by()

                if self.include_conversation_id:
                    conversations = self._fetch_downward_conversation_including_given_conversation(
                        downward_scroll_list_size, self.get_conversation_id(), excluded_conversation_states)

                else:
                    conversations = self._fetch_downward_conversation_queryset(downward_scroll_list_size,
                                                                               self.get_conversation_id(),
                                                                               excluded_conversation_states)

            else:
                conversations = self._fetch_conversation_queryset(excluded_conversation_states)

            conversations = self._create_conversation_list(conversations, sdk_client_info_flag=True)

        return {'success': True, 'conversations': conversations}

    def create_conversation(self, req_body: dict, is_ios: bool = False,
                            user_instance: User = None, chatroom_instance: Collabcard = None) -> {}:

        chatroom_id = req_body.get('chatroom_id', None)
        has_files = req_body.get('has_files', False)

        validated_request = ConversationHelper.validate_create_conversation_request(
            user_instance,
            self.get_member_id(),
            chatroom_instance,
            chatroom_id,
            req_body['text']
        )

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        chatroom_instance = validated_request.get('chatroom_instance')
        member_state = validated_request.get('member_state')

        community_instance = chatroom_instance.community

        if chatroom_instance.is_secret and \
                not ConversationHelper.is_user_secret_chatroom_participant(chatroom_instance, self.get_member_id()):
            return ResponseUtilities.get_impl_error_context('You are not a part of this secret chatroom',
                                                            status_codes.HTTP_400_BAD_REQUEST)

        if req_body.get('state') and req_body['state'] == conversation_states.CONVERSATION_POLL:
            has_right = ModelUtilities.get_model_filter(userMemberRights,
                                                        {'user': user_instance, 'community': community_instance,
                                                         'right__state': member_rights.MEMBER_RIGHT_CREATE_POLL})

            if not has_right:
                return {'success': False, 'error_message': "You don't have the rights to create a poll"}

        if chatroom_instance.access_without_subscription:
            status = is_member_verified(community_instance.id, self.get_member_id())
            state_filter = ModelUtilities.get_model_filter(collabcardState, {'card_id': chatroom_id,
                                                                             'user_id': self.get_member_id()})

            if not status and not state_filter:
                func_dict = {'collabcard_id': chatroom_id, 'member_id': self.get_member_id(), 'status': True,
                             'is_guest': True}

                collabcard_follow_internal(func_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

                ModelUtilities.model_update(Userinfo, {'user_id': self.get_member_id()},
                                            {'updated_at': TimeUtilities.current_time_in_sec()})

        created_at = TimeUtilities.current_time_in_milliseconds()

        chatroom_state_instance = collabcardState.get_chatroom_state_instance(chatroom_instance.id,
                                                                              user_instance.id)

        conversation_content = {}
        self._fill_basic_conversation_content(req_body, conversation_content,
                                              chatroom_instance, user_instance, community_instance,
                                              has_files, chatroom_state_instance)
        conversation_content['reply'] = ConversationHelper.fetch_replied_conversation(req_body)
        conversation_content['og_tags'] = ConversationHelper.fetch_og_tags(req_body)
        conversation_content['created_at'] = created_at
        conversation_instance = self._create_conversation_instance(conversation_content)
        self._set_preview_for_conversation(conversation_instance, req_body)
        self._fill_poll_options(user_instance, conversation_instance, req_body)

        attachment_count = req_body.get('attachment_count', 0)

        has_files = has_files or attachment_count > 0

        self._auto_follow_and_save_last_conversation(chatroom_instance,
                                                     chatroom_state_instance,
                                                     conversation_instance,
                                                     user_instance, member_state)

        self._update_home_page(community_instance, chatroom_instance, conversation_instance)

        if not has_files:
            ConversationHelper.update_latest_conversation_id_to_firebase.delay(chatroom_instance.id,
                                                                               conversation_instance.id)

        self._auto_follow_for_tagged_members(community_instance.id, chatroom_instance, conversation_instance, user_instance)

        self._handle_dm_chatroom_communication(chatroom_instance, user_instance, conversation_instance)

        update_conversation_engage_for_chatrooms(card_id=chatroom_instance.id, user_id=user_instance.id,
                                                 last_conversation_id=conversation_instance.id,
                                                 unseen_count=0)

        ConversationHelper.update_previews_on_conversation_creation(chatroom_instance)
        self._send_conversation_creation_notifications(chatroom_instance, conversation_instance, has_files)

        conversation_creator_id = int(self.get_member_id()) if self.get_member_id() else 0

        update_unread_message_count_in_cache.delay(chatroom_id=chatroom_id,
                                                   conversation_creator_id=conversation_creator_id)

        context = {"current_user_id": self.get_member_id(), "fetch_reply": True}
        conversation = CardAnswersDBSyncSerializer(conversation_instance, context=context, many=False).data
        args = [conversation_instance.id]

        if conversation_instance.state == conversation_states.CONVERSATION_POLL:
            start_time = TimeUtilities.convert_epoch_to_datetime_in_IST(conversation_instance.expiry_time)
            update_deferred_conversation_poll_updated_at_value.apply_async(args=args, kwargs={},
                                                                           eta=start_time)

        conversation_response = {
            'success': True,
            'id': conversation_instance.id,
            'conversation': conversation
        }

        return conversation_response

    def create_conversation_v1(self, req_body: dict) -> {}:
        chatroom_id = req_body.get('chatroom_id', None)
        has_files = req_body.get('has_files', False)
        replied_conversation_id = req_body.get('replied_conversation_id')
        attachments_data = req_body.get('attachments')
        attachment_count = req_body.get('attachment_count', 0)
        widget_metadata = req_body.get('metadata', {})

        if attachments_data and isinstance(attachments_data, list):
            attachment_count = len(attachments_data)

        validated_request = ConversationHelper.validate_create_conversation_request(None,
                                                                                    self.get_member_id(),
                                                                                    None,
                                                                                    chatroom_id,
                                                                                    req_body['text'],
                                                                                    replied_conversation_id,
                                                                                    req_body.get('temporary_id'))

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        chatroom_instance = validated_request.get('chatroom_instance')
        member_state = validated_request.get('member_state')

        community_instance = chatroom_instance.community

        if chatroom_instance.is_secret and \
                not ConversationHelper.is_user_secret_chatroom_participant(chatroom_instance, self.get_member_id()):
            return ResponseUtilities.get_impl_error_context('You are not a part of this secret chatroom',
                                                            status_codes.HTTP_400_BAD_REQUEST)

        if req_body.get('state') and (req_body['state'] == conversation_states.CONVERSATION_POLL):
            has_right = ModelUtilities.get_model_filter(userMemberRights,
                                                        {'user': user_instance, 'community': community_instance,
                                                         'right__state': member_rights.MEMBER_RIGHT_CREATE_POLL})

            if not has_right:
                return ResponseUtilities.get_impl_error_context("You don't have the rights to create a poll",
                                                                status_codes.HTTP_400_BAD_REQUEST)

        is_guest = False
        is_widgets_enabled = False

        chatroom_state_instance = None
        state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': chatroom_instance,
                                                                         'user': user_instance})

        if state_filter:
            chatroom_state_instance = state_filter[0]

            is_m2cm_v2 = m2cm_v2_version_check(self.get_platform_code(), self.get_version_code(),
                                               api_version_code=self.get_api_version_code())

            if all([is_m2cm_v2, chatroom_instance.is_private,
                    chatroom_instance.type == card_types.CARD_DIRECT_MESSAGE,
                    chatroom_instance.is_private_member,
                    chatroom_state_instance.chat_request_state == chat_request_states.REJECTED]):
                return ResponseUtilities.get_impl_error_context("Chatroom messaging is blocked!",
                                                                status_codes.HTTP_403_FORBIDDEN)

        if chatroom_instance.access_without_subscription:
            status = is_member_verified(community_instance.id, self.get_member_id())

            if not status and not state_filter:
                is_guest = True

        conversation_content = {}
        self._fill_basic_conversation_content(req_body, conversation_content,
                                              chatroom_instance, user_instance, community_instance,
                                              has_files, chatroom_state_instance, is_guest=is_guest)

        conversation_content['attachment_count'] = attachment_count

        conversation_content['reply'] = validated_request.get('replied_conv_instance')
        conversation_content['created_at'] = TimeUtilities.current_time_in_milliseconds()

        if 'og_tags' in req_body:
            conversation_content['og_tags'] = json.dumps(req_body['og_tags'])

        try:

            with transaction.atomic():
                conversation_instance = self._create_conversation_instance(conversation_content)

                if widget_metadata:
                    is_widgets_enabled = is_community_widget_enabled(community_instance, WidgetTypes.MESSAGE.value)

                    if not is_widgets_enabled:
                        return ResponseUtilities.get_impl_error_context("Widgets are disabled!",
                                                                        status_codes.HTTP_400_BAD_REQUEST)

                    widget_response = InternalServiceUtilities.create_widget_in_swarm(
                        user_instance.userinfo.user_unique_id, chatroom_instance.community_id,
                        entity_id=str(conversation_instance.id), entity_type=WidgetTypes.MESSAGE.value,
                        metadata=widget_metadata)

                    if "error_message" in widget_response:
                        conversation_instance.delete()

                        return ResponseUtilities.get_impl_error_context(widget_response.get('error_message'),
                                                                        status_codes.HTTP_400_BAD_REQUEST)

                    conversation_instance.widget_id = widget_response.get('_id')
                    conversation_instance.save()

                self._fill_poll_options(user_instance, conversation_instance, req_body)

                ConversationHelper.auto_follow_chatroom(chatroom_instance, chatroom_state_instance,
                                                        conversation_instance, user_instance, member_state,
                                                        trigger_webhook=True)

                tagged_members_list, is_group_tag = ConversationHelper.auto_follow_for_tagged_members(
                    chatroom_instance, conversation_instance)

                all_files_uploaded = False

                if attachments_data:
                    all_files_uploaded = ConversationHelper.save_attachments(conversation_instance, attachments_data)

                # Updating the updated_at of Collabcard schema
                chatroom_instance.save()

            ConversationHelper.run_async_task_on_conversation_create.delay(user_id=user_instance.id,
                                                                           chatroom_id=chatroom_instance.id,
                                                                           conversation_id=conversation_instance.id,
                                                                           req_body=req_body,
                                                                           member_state=member_state,
                                                                           trigger_webhook=True,
                                                                           attachments_data=attachments_data,
                                                                           tagged_members_list=tagged_members_list,
                                                                           is_group_tag=is_group_tag,
                                                                           all_files_uploaded=all_files_uploaded)

            context = {
                "current_user_id": self.get_member_id(),
                "fetch_reply": True,
                "is_widget_enabled": is_widgets_enabled
            }

            conversation = CardAnswersDBSyncSerializer(conversation_instance, context=context, many=False).data

            conversation_response = {
                'success': True,
                'id': conversation_instance.id,
                'conversation': conversation
            }

            return conversation_response

        except Exception as error:
            transaction.rollback()
            return ResponseUtilities.get_impl_error_context("Some error occurred in creating conversation!",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

    def add_reaction(self, reaction: str) -> dict:
        validated_request = ConversationViewHelper.validate_add_reaction_request(self.get_member_id(),
                                                                                 self.get_chatroom_id(),
                                                                                 self.get_conversation_id())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        chatroom_instance = validated_request.get('chatroom_instance')
        conversation_instance = validated_request.get('conversation_instance')

        if conversation_instance:
            chatroom_instance = conversation_instance.card
            conversation_instance.has_reactions = True
            conversation_instance.save()

        if chatroom_instance:
            chatroom_instance.has_reactions = True
            chatroom_instance.save()

        update_context = {'reaction': reaction, 'updated_at': TimeUtilities.current_time_in_milliseconds()}

        MessageReactions.objects.update_or_create(user=user_instance,
                                                  chatroom=chatroom_instance,
                                                  conversation=conversation_instance,
                                                  defaults=update_context)

        fetch_chatroom_or_conversation_reactions(self.get_chatroom_id(),
                                                 self.get_conversation_id(),
                                                 update_cache=True)

        send_notification_to_message_creator_on_reaction.delay(self.get_member_id(),
                                                               self.get_chatroom_id(),
                                                               self.get_conversation_id(),
                                                               reaction)

        if self.get_chatroom_id():
            ModelUtilities.model_update(collabcardState,
                                        {'card': chatroom_instance},
                                        {'updated_at': TimeUtilities.current_time_in_sec()})

        else:
            ModelUtilities.model_update(card_answers,
                                        {'pk': self.get_conversation_id()},
                                        {'last_updated': TimeUtilities.current_time_in_milliseconds()})

        context = {
            "success": True
        }

        return context

    def remove_reaction(self) -> dict:
        validated_request = ConversationViewHelper.validate_remove_reaction_request(self.get_member_id(),
                                                                                    self.get_chatroom_id(),
                                                                                    self.get_conversation_id())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        chatroom_instance = validated_request.get('chatroom_instance')
        conversation_instance = validated_request.get('conversation_instance')

        if conversation_instance:
            chatroom_instance = conversation_instance.card

        MessageReactions.objects.filter(user=user_instance,
                                        chatroom=chatroom_instance,
                                        conversation=conversation_instance).delete()

        fetch_chatroom_or_conversation_reactions(self.get_chatroom_id(),
                                                 self.get_conversation_id(),
                                                 update_cache=True)

        if self.get_chatroom_id():
            ModelUtilities.model_update(collabcardState,
                                        {'card': chatroom_instance},
                                        {'updated_at': TimeUtilities.current_time_in_sec()})

        else:
            ModelUtilities.model_update(card_answers,
                                        {'pk': self.get_conversation_id()},
                                        {'last_updated': TimeUtilities.current_time_in_milliseconds()})

        context = {
            "success": True
        }

        return context

    def add_poll(self, request_body):
        validated_request = ConversationViewHelper.validate_add_poll_request(self.get_member_id(),
                                                                             request_body)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        conversation_instance = validated_request.get('conversation_instance')

        poll = request_body.get('poll', {})

        poll_instance = conversationPolls.create_instance({'user_instance': user_instance,
                                                           'conversation_instance': conversation_instance,
                                                           'text': poll.get('text', '')})

        save_conversation_poll_options_in_cache(
            {'conversation_id': conversation_instance.id, 'user_id': user_instance.id})

        poll_response = {
            'id': poll_instance.id,
            'text': poll_instance.text,
            'user_id': poll_instance.user_id
        }

        # Get serialized member details from 
        user_sdk_meta = get_users_sdk_meta_dict([user_instance.id])
        
        if user_sdk_meta:
            poll_response['member'] = user_sdk_meta.get(user_instance.id)
        
        return {'success': True, 'poll': poll_response}

    def submit_poll(self, request_body):
        validated_request = ConversationViewHelper.validate_submit_poll_request(self.get_member_id(),
                                                                                request_body)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        conversation_instance = validated_request.get('conversation_instance')

        polls = request_body.get('polls', [])

        poll_filter = ModelUtilities.get_model_filter(conversationPollMembers, {'user': user_instance,
                                                                                'conversation': conversation_instance})
        poll_filter.delete()

        for poll in polls:
            poll_filter = ModelUtilities.get_model_filter(conversationPolls, {'id': poll.get('id'),
                                                                              'conversation': conversation_instance})

            if not poll_filter:
                return ResponseUtilities.get_impl_error_context('Invalid poll id',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)

            poll_instance = poll_filter[0]
            conversationPollMembers.create_instance({'user_instance': user_instance,
                                                     'poll_instance': poll_instance,
                                                     'conversation_instance': conversation_instance})

        conversation_instance.poll_answer_text = ConversationHelper.compute_conversation_poll_answer_text(
            conversation_instance)
        conversation_instance.last_updated = TimeUtilities.current_time_in_milliseconds()
        conversation_instance.save()

        save_conversation_poll_voters_in_cache({'conversation_instance': conversation_instance})

        return {'success': True}

    def poll_users(self, poll_id, page, page_size):
        validated_request = ConversationViewHelper.validate_poll_users_request(self.get_member_id(),
                                                                               self.get_conversation_id())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        conversation_instance = validated_request.get('conversation_instance')

        poll_filter = ModelUtilities.get_model_filter(conversationPolls, {'id': poll_id,
                                                                          'conversation': conversation_instance})

        if not poll_filter:
            return ResponseUtilities.get_impl_error_context("Incorrect poll_id conversation pair",
                                                            status_codes.HTTP_400_BAD_REQUEST)

        poll_instance = poll_filter[0]

        community_instance = conversation_instance.community

        member_list = []

        # Check if poll is not anonymous, then only send members list, else send empty list
        if not conversation_instance.is_anonymous:
            user_list = self._fetch_member_list_for_poll_conversation(conversation_instance, poll_instance,page, page_size)                                           
            member_list = self._create_member_instances_from_user_list(user_list, community_instance)

        return {'success': True, 'members': member_list}

    def _fetch_chatroom_topic_text(self):

        conversation_attachments = answerAttachment.objects.filter(
            answer__id=self.get_conversation_id()) \
            .values('type') \
            .annotate(count=Count('type'))

        topic_text = None

        image_count = 0
        video_count = 0
        pdf_count = 0
        audio_count = 0
        gif_count = 0

        for attachment in conversation_attachments:

            if attachment['type'] == 'image':
                image_count = attachment['count']

            elif attachment['type'] == 'video':
                video_count = attachment['count']

            elif attachment['type'] == 'pdf':
                pdf_count = attachment['count']

            elif attachment['type'] == 'audio':
                audio_count = attachment['count']

            elif attachment['type'] == 'gif':
                gif_count = attachment['count']

        if video_count > 0:
            topic_text = TOPIC_TEXT_VIDEO

        elif image_count > 0:
            topic_text = TOPIC_TEXT_IMAGE

        elif gif_count > 0:
            topic_text = TOPIC_TEXT_GIF

        elif audio_count > 0:
            topic_text = TOPIC_TEXT_AUDIO

        elif pdf_count > 1:
            topic_text = TOPIC_TEXT_MULTIPLE_PDF

        elif pdf_count == 1:
            topic_text = TOPIC_TEXT_PDF

        return topic_text

    def set_chatroom_topic(self) -> dict:
        validated_request = ConversationViewHelper.validate_set_topic_request(self.get_member_id(),
                                                                              self.get_chatroom_id(),
                                                                              self.get_conversation_id())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        conversation_instance = validated_request.get('conversation_instance')
        chatroom_instance = validated_request.get('chatroom_instance')

        validation_dict = ConversationHelper.validate_set_topic_request(user_instance, chatroom_instance)

        if validation_dict.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validation_dict.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_instance.topic = conversation_instance
        chatroom_instance.save()

        if len(conversation_instance.answer) == 0:
            topic_text = self._fetch_chatroom_topic_text()

        else:
            topic_text = TOPIC_TEXT_NORMAL + conversation_instance.answer

        ConversationHelper.create_conversation_state(chatroom_instance, user_instance,
                                                     state=conversation_states.CHATROOM_TOPIC,
                                                     topic_text=topic_text)

        ModelUtilities.model_update(collabcardState,
                                    {'card': chatroom_instance},
                                    {'updated_at': TimeUtilities.current_time_in_sec()})

        #If Chatroom is part of an SDK community, do not send notification
        if not SdkClient.is_sdk_community(chatroom_instance.community_id):
            send_notification_on_chatroom_topic_update.delay(chatroom_instance.id, user_instance.id)

        return {'success': True}

    def attend_event(self, req_body):
        validated_request = ConversationViewHelper.validate_event_attend_request(self.get_member_id(),
                                                                                 req_body.get('conversation_id'))

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        conversation_instance = validated_request.get('conversation_instance')

        attending_status = req_body.get('attending_status', False)

        ConversationHelper.attend_conversation_event(conversation_instance, user_instance, attending_status)

        update_event_attendees_for_micro_event.delay({'conversation_id': conversation_instance.id,
                                                      'user_id': user_instance.id,
                                                      'attending_status': attending_status})

        return {'success': True}

    def set_event_attended(self, req_body):
        validated_request = ConversationViewHelper.validate_event_attended_request(self.get_member_id(),
                                                                                   req_body.get('conversation_id'))

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        conversation_instance = validated_request.get('conversation_instance')

        ModelUtilities.model_update(conversationEventMembers,
                                    {'conversation': conversation_instance,
                                     'user': user_instance},
                                    {'attended': True,
                                     'updated_at': TimeUtilities.current_time_in_milliseconds()})

        return {'success': True}

    def update_last_seen_event(self) -> dict:

        user_instance = ModelUtilities.get_user_instance_or_none(self.get_member_id())

        if not user_instance:
            return ResponseUtilities.get_impl_error_context("Invalid user id", status_codes.HTTP_400_BAD_REQUEST)

        chatroom_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                             {'user': user_instance, 'remove': None}).
                             values_list('card_id', flat=True))

        last_seen_event_conversation_id = get_last_seen_event_conversation_id_for_user(chatroom_list)

        if not last_seen_event_conversation_id:
            return {'success': True}

        event_nudge_filter = ModelUtilities.get_model_filter(conversationEventNudge,
                                                             {'user': user_instance})

        if event_nudge_filter:
            nudge_instance = event_nudge_filter[0]

            if nudge_instance.event_id_seen != last_seen_event_conversation_id:
                conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers,
                                                                                  last_seen_event_conversation_id)
                nudge_instance.event_id_seen = conversation_instance
                nudge_instance.save()

        else:

            conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers,
                                                                              last_seen_event_conversation_id)
            conversationEventNudge.create_instance({'conversation_instance': conversation_instance,
                                                    'user_instance': user_instance})

        return {'success': True}

    def fetch_unseen_count_in_event(self) -> dict:

        user_instance = ModelUtilities.get_user_instance_or_none(self.get_member_id())

        if not user_instance:
            return ResponseUtilities.get_impl_error_context("Invalid user id", status_codes.HTTP_400_BAD_REQUEST)

        unseen_count = 0

        nudge_filter = ModelUtilities.get_model_filter(conversationEventNudge, {'user': user_instance})

        if nudge_filter:
            conversation_instance = nudge_filter[0].event_id_seen
            chatroom_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                                 {'user': user_instance, 'remove': None}).
                                 values_list('card_id', flat=True))
            unseen_count = get_count_of_new_event_conversation_created_for_user(conversation_instance.id, chatroom_list)

        return {'success': True, 'count': unseen_count}

    def fetch_link_for_event(self) -> dict:
        validated_request = ConversationViewHelper.validate_event_fetch_link_request(self.get_member_id(),
                                                                                     self.get_conversation_id())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        conversation_instance = validated_request.get('conversation_instance')

        if TimeUtilities.current_time_in_milliseconds() >= \
                (conversation_instance.start_time - conversation_instance.online_link_enable_before):
            conversation_context = {'success': True}

            self._fill_online_link_for_event(conversation_context, conversation_instance)

            return conversation_context

        return ResponseUtilities.get_impl_error_context("Link doesn't exists",
                                                        status_code=status_codes.HTTP_400_BAD_REQUEST)

    def fetch_user_all_events(self, page, attending_status, past_events=False) -> dict:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return ResponseUtilities.get_impl_error_context("Invalid user id", status_codes.HTTP_400_BAD_REQUEST)

        conversation_queryset = self.fetch_conversation_events_queryset(user_instance,
                                                                        attending_status=attending_status,
                                                                        past_events=past_events)

        conversation_list = ModelUtilities.paginate_queryset(conversation_queryset, page, paginate_by=5)
        conversations = self._create_conversation_list(conversation_list, sdk_client_info_flag=True)

        return {'success': True, 'events': conversations}

    def fetch_unread_previews(self):
        validated_request = ConversationViewHelper.validate_fetch_unread_previews_request(self.get_member_id(),
                                                                                          self.get_chatroom_id())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        conversations = self._fetch_unread_preview_queryset()
        conversations = ModelUtilities.paginate_queryset(conversations, self.get_page(),
                                                         paginate_by=self.get_paginate_by())
        conversations = self._create_conversation_list(conversations, sdk_client_info_flag=True)
        return {'success': True, 'conversations': conversations}

    def fetch_preview_unread_message_count(self):
        validated_request = ConversationViewHelper.validate_fetch_preview_unread_messages_count_request(
            self.get_member_id(), self.get_chatroom_id())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        conversations = card_answers.objects.select_related('reply', 'preview_community', 'preview_chatroom').filter(
            card=self.get_chatroom_id()).order_by('-created_at')

        total_unread_message_count = self.calculate_preview_unread_message_count(conversations)

        response = {
            'success': True,
            'count': total_unread_message_count
        }

        return response

    def chatroom_previews_with_non_zero_conversation_unread(self, conversations):
        conversation_ids = []

        for conversation in conversations:

            if conversation.preview_chatroom and not conversation.preview_chatroom.is_deleted:

                state_filter_dict = {
                    'card': conversation.preview_chatroom,
                    'user_id': self.get_member_id(),
                    'follow_status': True,
                    'remove': None
                }

                state_filter = ModelUtilities.get_model_filter(collabcardState, state_filter_dict)

                if not state_filter:
                    continue

                unread_count = fetch_conversations_unread(conversation.preview_chatroom.id, self.get_member_id())

                if unread_count != 0:
                    conversation_ids.append(conversation.id)

        return conversation_ids

    def calculate_preview_unread_message_count(self, conversations):
        total_unread_count = 0

        for conversation in conversations:

            if conversation.preview_chatroom and not conversation.preview_chatroom.is_deleted:

                state_filter_dict = {
                    'card': conversation.preview_chatroom,
                    'user_id': self.get_member_id(),
                    'follow_status': True,
                    'remove': None
                }

                state_filter = ModelUtilities.get_model_filter(collabcardState, state_filter_dict)

                if not state_filter:
                    continue

                unread_count = fetch_conversations_unread(conversation.preview_chatroom.id, self.get_member_id())

                if unread_count != 0:
                    total_unread_count += 1

        return total_unread_count

    @staticmethod
    def create_conversation_internally(member_id, chatroom_id, message):

        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not user_instance:
            return ResponseUtilities.get_impl_error_context('invalid user_id', status_codes.HTTP_404_NOT_FOUND)

        req_body = {
            "chatroom_id": chatroom_id,
            "text": message
        }

        user_devices_list = ModelUtilities.get_model_filter(userDevices, {'user_id': member_id}).order_by('-updated_at')
        device_id = None if not user_devices_list else user_devices_list[0].device_id

        conversation_manager = ConversationImpl(member_id, platform_code=PLATFORM_CODE_WEB, device_id=device_id)

        conversation_response = conversation_manager.create_conversation_revamp(req_body)

        if conversation_response.get('error_message'):
            return ResponseUtilities.get_impl_error_context(conversation_response, status_codes.HTTP_400_BAD_REQUEST)

        return conversation_response

    @staticmethod
    def genereate_payload_data_for_chatroom_user_tagged_webhook(conversation_id: int, users_list: list, event_type: str):

        payload_data = {}
          
        conversation_payload = ConversationHelper.get_conversation_payload_for_webhook_events(conversation_id, 
                                                                                              event_type)
        
        if not conversation_payload:
            return {}
        
        chatroom_payload = chatroom_impl.ChatroomHelper.get_chatroom_payload_for_webhook_events(
            conversation_payload['chatroom_id'])
        
        payload_data['chatroom'] = chatroom_payload

        payload_data['conversation'] = conversation_payload
        
        created_by_user = MemberCommunityHelper.get_users_payload_for_webhook_events([conversation_payload['user_id']])

        if not created_by_user:
            return {}
    
        payload_data['created_by_user'] = created_by_user[0]

        tagged_users = MemberCommunityHelper.get_users_payload_for_webhook_events(users_list)

        payload_data['tagged_users'] = tagged_users

        return payload_data
    
    @staticmethod
    def genereate_payload_data_for_chatroom_conversation_replied_webhook(conversation_id: int, event_type: str):

        payload_data = {}
        
        conversation_payload = ConversationHelper.get_conversation_payload_for_webhook_events(conversation_id, 
                                                                                              event_type)
        
        if not conversation_payload:
            return {}
        
        chatroom_payload = chatroom_impl.ChatroomHelper.get_chatroom_payload_for_webhook_events(
            conversation_payload['chatroom_id'])
        
        payload_data['chatroom'] = chatroom_payload
        original_conversation = ConversationHelper.get_conversation_payload_for_webhook_events(
                conversation_payload['replied_conversation_id'], "")
            
        if not original_conversation:
            return {}
        
        payload_data['original_conversation'] = original_conversation
        payload_data['replied_conversation'] = conversation_payload

        original_conversation_user = MemberCommunityHelper.get_users_payload_for_webhook_events(
            [original_conversation['user_id']])
        replied_conversation_user = MemberCommunityHelper.get_users_payload_for_webhook_events(
            [conversation_payload['user_id']])

        if not (original_conversation_user and replied_conversation_user):
            return {}
        
        payload_data['original_conversation_user'] = original_conversation_user[0]
        payload_data['replied_conversation_user'] = replied_conversation_user[0]

        return payload_data

    @staticmethod
    def generate_payload_for_conversation_webhook_event(conversation_id: int, users_list: list, event_type: str) -> dict:
        
        payload = {
            "event": event_type,
            "source": WEBHOOK_SOURCE_CHAT,
            "created_at": TimeUtilities.current_time_in_milliseconds(),
            "data": {}
        }

        # If event `user is tagged in a chatroom`
        if event_type == WebhookTypes.CHATROOM_USER_TAGGED.value:
            payload_data = ConversationImpl.genereate_payload_data_for_chatroom_user_tagged_webhook(conversation_id,
                                                                                                    users_list,
                                                                                                    event_type)

        # If event `user replied in a chatroom`
        elif event_type == WebhookTypes.CHATROOM_CONVERSATION_REPLIED.value:
            payload_data = ConversationImpl.genereate_payload_data_for_chatroom_conversation_replied_webhook(
                conversation_id, event_type)
            
        else:
            return {}
        
        if not payload_data:
            return {}
        
        payload['data'] = payload_data

        return payload
    
    @staticmethod
    @shared_task
    def trigger_webhook_for_conversation_event(community_id: int, conversation_id: int, users_list: list, 
                                               event_type: str):
        
        if not (community_id and conversation_id and event_type):
            return
        
        webhooks = WebhookUtilties.validate_and_fetch_all_webhook_url_and_secret(community_id, 
                                                                                 event_type)
        
        if not webhooks:
            return
        
        payload = ConversationImpl.generate_payload_for_conversation_webhook_event(conversation_id, 
                                                                                   users_list, 
                                                                                   event_type)
        
        if not payload:
            return
        
        for webhook in webhooks:

            payload['id'] = str(uuid.uuid4())

            # Send webhook request
            WebhookUtilties.send_webhook_request_with_payload.delay(url=webhook.get('url'),
                                                                    payload=payload,
                                                                    webhook_type=event_type,
                                                                    secret=webhook.get('secret'))


class ConversationHelper:

    @staticmethod
    def fetch_user_instance(user_id) -> User:
        return User.get_user_or_raise_exception(user_id)

    @staticmethod
    def fetch_community_instance(community_id) -> Community:
        return Community.get_community_or_raise_exception(community_id)

    @staticmethod
    def fetch_chatroom_instance(chatroom_id) -> Collabcard:
        return Collabcard.get_chatroom_or_raise_exception(chatroom_id)

    @staticmethod
    def fetch_conversation_instance(conversation_id) -> card_answers:
        return card_answers.get_conversation_with_joins_or_raise_exception(conversation_id)

    @staticmethod
    def fetch_replied_conversation(req_body):
        try:
            if 'replied_conversation_id' in req_body:
                return card_answers.objects.get(pk=req_body['replied_conversation_id'])
            else:
                return None

        except:
            replied_conversation_id = req_body["replied_conversation_id"]
            response = {
                'success': False,
                'error_message': f'replied_conversation_id {replied_conversation_id} is wrong'
            }
            raise CustomException(response)

    @staticmethod
    def fetch_og_tags(req_body):
        if 'og_tags' in req_body:
            og_tags = json.dumps(req_body['og_tags'])
        elif 'share_link' in req_body:
            og_tags = json.dumps(UriTagsImpl(req_body['share_link']).get_tags_from_uri())
        else:
            return
        return og_tags
    
    @staticmethod
    @shared_task
    def update_share_link_og_tags_in_conversation(conversation_id, share_link):

        try:
            conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)
            
            if not (conversation_instance and share_link):
                return
            
            og_tags = UriTagsImpl(share_link).get_tags_from_uri(timeout=CREATE_CONVERSATION_OG_TAGS_REQUEST_TIMEOUT)

            if og_tags:
                og_tags = json.dumps(og_tags)
                conversation_instance.og_tags = og_tags
                conversation_instance.save()  

        except Exception as e:
            error_logger.error(f'Error in fetching og tags from share_link url: {share_link}, errors: {e}')
            return

    @staticmethod
    def fetch_auto_follow_dict(member_id, chatroom_id, status, source):

        return {
            'member_id': member_id,
            'collabcard_id': chatroom_id,
            'status': status,
            'source': source
        }

    @staticmethod
    def is_user_secret_chatroom_participant(chatroom, user_id):
        secret_chatroom_participants = json.loads(chatroom.secret_chatroom_participants)

        if user_id is not None:
            logged_in_user_id = NumberUtilities.get_integer_from_string(user_id)
            return logged_in_user_id in secret_chatroom_participants

        return False

    @staticmethod
    def update_previews_on_conversation_creation(chatroom_instance):

        update_multiple_previews_in_chatroom.delay({'chatroom_id': chatroom_instance.id})

    @staticmethod
    def run_async_tasks_for_conversation_tagging(tagged_member_list, user_instance, chatroom_instance):

        for tagged_member in tagged_member_list:
            ConversationHelper.send_engagement_communication(tagged_member, user_instance.id, chatroom_instance.id,
                                                             chatroom_not_opened_types.TAGGED_CHATROOM)

    @staticmethod
    def send_engagement_communication(receiver_id, sender_id, chatroom_id, chatroom_not_opened_type):

        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not chatroom_instance:
            return

        user_instance = ModelUtilities.get_user_instance_or_none(receiver_id)

        if not user_instance:
            return

        receiver_id = user_instance.id

        receiver_id_list = filter_user_instances_based_on_notification_flag(
            [receiver_id], community_id=chatroom_instance.community_id, flag_code=unsubscribe_types.MAIL_CHATROOM_OR_DM)

        if not receiver_id_list:
            return

        status_type = None

        if chatroom_not_opened_type == chatroom_not_opened_types.TAGGED_CHATROOM:
            status_type = user_email_send_status_types.TAGGED_CHATROOM_NOT_OPENED

        if chatroom_not_opened_type == chatroom_not_opened_types.DM_CHATROOM:
            status_type = user_email_send_status_types.DM_CHATROOM_NOT_OPENED

        user_email_send_status_instance = ModelUtilities.get_model_filter(
            UserEmailsSendStatus, {'user_id': receiver_id, 'chatroom_id': chatroom_id, 'is_completed': False,
                                   'status_type': status_type})

        if not user_email_send_status_instance and status_type:

            collabcard_state_instances = ModelUtilities.get_model_filter(collabcardState, {'card_id': chatroom_id,
                                                                                           'user_id': receiver_id})

            if not collabcard_state_instances:
                return

            collabcard_state_instance = collabcard_state_instances[0]

            last_seen_conversation = None

            if collabcard_state_instance.last_seen_conversation:
                last_seen_conversation = collabcard_state_instance.last_seen_conversation.id

            user_email_send_status_data = {
                'user': ModelUtilities.get_model_instance_or_none(User, receiver_id),
                'community': chatroom_instance.community,
                'chatroom_id': chatroom_id,
                'status_type': status_type
            }

            UserEmailsSendStatus.create_instance(user_email_send_status_data)

            args = [receiver_id, sender_id, chatroom_id, chatroom_not_opened_type, last_seen_conversation]
            countdown = ENGAGEMENT_COMMUNICATION_DURATION_IN_HOURS * MINUTES_60

            # runs after 6 hours, expires after 6 hours and 30 minutes
            send_communication_when_chatroom_not_opened.apply_async(args=args, kwargs={}, countdown=countdown,
                                                                    expires=countdown + MINUTES_30)

    @staticmethod
    def update_homefeed_for_all_chatroom_followers(chatroom_id, conversation_id):

        user_list = list(ModelUtilities.get_model_filter(collabcardState, {'card': chatroom_id,
                                                                           'remove': None,
                                                                           'follow_status': True}
                                                         ).values_list('user_id', flat=True))

        update_my_chatrooms_on_homefeed_in_firebase_for_users_list(chatroom_id, user_list, conversation_id)

    @staticmethod
    @shared_task
    def update_latest_conversation_id_to_firebase(chatroom_id, conversation_id):
        update_last_answer_id(chatroom_id, conversation_id)
        ConversationHelper.update_homefeed_for_all_chatroom_followers(chatroom_id, conversation_id)

    @staticmethod
    @shared_task
    def update_latest_conversation_id_to_firebase_v1(chatroom_id, conversation_id, community_id=None,
                                                     only_update_home_feed=False):
        if not only_update_home_feed:
            update_last_answer_id(chatroom_id, conversation_id)

        update_chatroom_conversation_ids_against_community(community_id, card_id=chatroom_id,
                                                           conversation_id=conversation_id)

    @staticmethod
    @shared_task
    def update_the_activity_time_for_new_conversation_creation(chatroom_id, user_id):
        activate_chatroom_on_conversation_creation(chatroom_id, user_id)

    @staticmethod
    def compute_member_images_for_homescreen(chatroom_instance, community_instance):

        user_list = get_latest_conversation_creator_users_for_homescreen(chatroom_instance.id,
                                                                         chatroom_instance.user_id)

        member_conversations = []
        user_conversations = []

        for user_id in user_list:

            member_filter = Members.objects.filter(community_id=community_instance, member_id=user_id)

            if member_filter:
                member_instance = member_filter[0]
                member_conversations.append(member_instance)

            else:
                state_filter = collabcardState.objects.filter(card=chatroom_instance, user=user_id)

                if state_filter:
                    state_instance = state_filter[0]
                    user_conversations.append(state_instance)

        # if last conversation creators are members

        last_conversation_member = None
        second_last_conversation_member = None

        if len(member_conversations) > 1:
            last_conversation_member = member_conversations[0]
            second_last_conversation_member = member_conversations[1]

        elif len(member_conversations) == 1:
            last_conversation_member = member_conversations[0]

        # if last conversation creators are users(can be guest or removed members)
        last_conversation_user = None
        second_last_conversation_user = None

        if len(user_conversations) > 1:
            last_conversation_user = user_conversations[0]
            second_last_conversation_user = user_conversations[1]

        elif len(user_conversations) == 1:
            last_conversation_user = user_conversations[0]

        return last_conversation_member, second_last_conversation_member, last_conversation_user, \
               second_last_conversation_user

    @staticmethod
    def update_homescreen_meta_on_conversation_creation(community_instance, chatroom_instance, conversation_instance):

        if conversation_instance.attachment_count > 0 and conversation_instance.attachments_uploaded is False:
            user_id = conversation_instance.user_id
        else:
            user_id = None

        last_conversation_member, \
        second_last_conversation_member, \
        last_conversation_user, second_last_conversation_user = \
            ConversationHelper.compute_member_images_for_homescreen(chatroom_instance, community_instance)

        if user_id:

            conversationEngage.objects.filter(card=chatroom_instance,
                                              user=user_id).update(
                unseen_count=F('unseen_count') + 1,
                last_conversation=conversation_instance,
                updated_at=TimeUtilities.current_time_in_sec(),
                last_conversation_member=last_conversation_member,
                second_last_conversation_member=second_last_conversation_member,
                last_conversation_user=last_conversation_user,
                second_last_conversation_user=second_last_conversation_user,
            )

        else:
            conversationEngage.objects.filter(card=chatroom_instance).update(
                unseen_count=F('unseen_count') + 1,
                last_conversation=conversation_instance,
                updated_at=TimeUtilities.current_time_in_sec(),
                last_conversation_member=last_conversation_member,
                second_last_conversation_member=second_last_conversation_member,
                last_conversation_user=last_conversation_user,
                second_last_conversation_user=second_last_conversation_user,
            )

    @staticmethod
    def update_last_seen_conversation_in_collabcard_state(conversation_instance, user_instance, chatroom_instance):

        collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState,
                                                                  {'card': chatroom_instance,
                                                                   'user': user_instance}).first()

        if collabcard_state_filter:
            collabcard_state_filter.last_seen_conversation = conversation_instance
            collabcard_state_filter.updated_at = TimeUtilities.current_time_in_sec()
            collabcard_state_filter.save()


    @staticmethod
    def compute_conversation_poll_answer_text(conversation_instance) -> str:

        total_users = ModelUtilities.get_model_filter(conversationPollMembers,
                                                      {'conversation': conversation_instance}).values(
            'user').distinct().count()

        if total_users == 1:
            poll_text = POLL_ANSWER_TEXT_FOR_ONE_MEMBER

        elif total_users > 1:
            poll_text = POLL_ANSWER_TEXT_FOR_MULTIPLE_MEMBER % str(total_users)

        else:
            poll_text = POLL_ANSWER_TEXT

        return poll_text

    @staticmethod
    def update_homescreen_meta_on_chatroom_follow(community_instance, card_instance, card_state_instance,
                                                  user_instance):

        last_conversation_member, \
        second_last_conversation_member, \
        last_conversation_user, second_last_conversation_user = \
            ConversationHelper.compute_member_images_for_homescreen(card_instance, community_instance)

        conversation_filter = card_answers.objects.filter(card=card_instance).filter(
            Q(state=conversation_states.ANSWER) |
            Q(state=conversation_states.CONVERSATION_POLL)).filter(
            Q(attachment_count=0) | Q(attachments_uploaded=True) | Q(api_version=1)).order_by("created_at")

        last_conversation = conversation_filter.last()

        last_seen_conversation = card_state_instance.last_seen_conversation_id

        if not last_seen_conversation:
            unseen_count = conversation_filter.count()

        else:
            unseen_count = card_answers.objects.filter(
                card_id=card_instance, id__gt=last_seen_conversation
            ).filter(Q(state=conversation_states.ANSWER) |
                     Q(state=conversation_states.CONVERSATION_POLL)
                     ).count()

        if user_instance:
            conversationEngage.objects.filter(card=card_instance,
                                              user=user_instance.id).update(
                unseen_count=unseen_count,
                last_conversation=last_conversation,
                updated_at=TimeUtilities.current_time_in_sec(),
                last_conversation_member=last_conversation_member,
                second_last_conversation_member=second_last_conversation_member,
                last_conversation_user=last_conversation_user,
                second_last_conversation_user=second_last_conversation_user,
            )

        if unseen_count > 0:
            card_state_instance.updated_at = TimeUtilities.current_time_in_sec()
            card_state_instance.save()

    @staticmethod
    def create_answer(chatroom_instance, user_instance, state, topic_text=None, answer=None, current_user_id=None):
        create_chatroom(chatroom_instance, user_instance, state,
                        current_user_id=current_user_id, answer=answer,
                        topic_text=topic_text)

    @staticmethod
    def validate_set_topic_request(user_instance, chatroom_instance):

        response = {
            "success": True,
        }

        if all([chatroom_instance.user_id != user_instance.id,
                not Members.is_member_community_promoter(chatroom_instance.community, user_instance)]):
            return ResponseUtilities.get_inner_error_context('Only chatroom creator or CM can change the topic of '
                                                             'chatroom')

        return response

    @staticmethod
    def create_conversation_state(card_instance, user_instance, state, current_user_id=None, answer="",
                                  topic_text=None, member_state=0, community_instance=None, added_member_count=0):

        if not community_instance:
            community_instance = card_instance.community

        if not answer:

            user_name = user_instance.userinfo.name

            community_id = community_instance.id
            community_name = community_instance.name

            user_route = f"route://member_profile/{user_instance.id}?member_id={user_instance.id}"
            user_name = f"<<{user_name}|{user_route}&community_id={community_id}>>"

            if state == conversation_states.CONVERSATION_HEADER:

                community_route = "route://community?community_id=" + str(community_id)
                community_name = "<<" + str(community_name) + "|" + community_route + ">>"

                if card_instance.is_secret:
                    secret_participants_count = len(json.loads(card_instance.secret_chatroom_participants))

                    prefix = "others"
                    if secret_participants_count == 2:
                        prefix = "other"

                    answer = f"{user_name} started this secret chatroom with {secret_participants_count - 1} {prefix}"

                elif (card_instance.type == card_types.CARD_POLL):
                    answer = user_name + " started this poll in " + community_name

                else:
                    answer = user_name + " started this chatroom in " + community_name

            elif state == conversation_states.CONVERSATION_FOLLOW:
                answer = user_name + " joined this chatroom"

                if card_instance.is_secret and member_state == member_states.ADMIN:
                    answer = user_name + " joined this chatroom"

            elif state == conversation_states.CONVERSATION_UNFOLLOW:
                answer = user_name + " left this chatroom"

            elif state == conversation_states.CONVERSATION_COMMUNITY_EDIT:
                answer = user_name + " edited community purpose"

            elif state == conversation_states.CONVERSATION_ADD_PARTICIPANT:

                if current_user_id is not None:
                    current_user_name = Userinfo.get_username(current_user_id)

                    current_user_route = f"route://member_profile/{current_user_id}?member_id={current_user_id}"
                    encoded_current_user_name = f"<<{current_user_name}|{current_user_route}&community_id={community_id}>>"

                    answer = f"{encoded_current_user_name} added {user_name}"

            elif state == conversation_states.CONVERSATION_LEAVE_CHATROOM:

                answer = user_name + " left this chatroom"

            elif state == conversation_states.CONVERSATION_REMOVED_FROM_CHATROOM:
                if current_user_id is not None:
                    current_user_name = Userinfo.get_username(current_user_id)

                    current_user_route = f"route://member_profile/{current_user_id}?member_id={current_user_id}"
                    encoded_current_user_name = f"<<{current_user_name}|{current_user_route}&community_id={community_id}>>"

                    answer = f"{encoded_current_user_name} removed {user_name}"

            elif state == conversation_states.CHATROOM_TOPIC:
                if topic_text is not None:
                    answer = f"{user_name} {topic_text}"

            elif state == conversation_states.CONVERSATION_ADD_ALL_MEMBERS:

                if added_member_count > 1:
                    answer = user_name + " added " + str(added_member_count) + " members"

                elif added_member_count == 1:
                    answer = user_name + " added " + str(added_member_count) + " member"

                else:
                    answer = user_name + " added all members"

        if answer:
            instance = card_answers()
            instance.answer = answer
            instance.card = card_instance
            instance.user = user_instance
            instance.community = community_instance
            instance.state = state
            instance.save()

        if state == conversation_states.CONVERSATION_HEADER and \
                card_instance.type == card_types.CARD_INTRO:
            community_id = card_instance.community_id
            member_id = user_instance.id

            post_owner_message_template_in_intro_room(card_instance.community_id, member_id)

            args = [community_id, member_id]
            # runs after 5 minutes, expires after 30 minutes
            check_owner_template_posted.apply_async(args=args, kwargs={},
                                                    countdown=MINUTES_5, expires=MINUTES_30)

    @staticmethod
    def attend_conversation_event(conversation_instance, user_instance, attending_status):
        attend_filter = ModelUtilities.get_model_filter(conversationEventMembers,
                                                        {'conversation': conversation_instance,
                                                         'user': user_instance})

        if not attend_filter:
            conversationEventMembers.create_instance({
                'conversation_instance': conversation_instance,
                'user_instance': user_instance,
                'attending_status': attending_status
            })

        else:
            instance = attend_filter[0]
            instance.attending_status = attending_status
            instance.save()

    @staticmethod
    @shared_task
    def set_event_conversation_co_hosts_attending_status(conversation_id, conversation_creator_id):

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

        if not conversation_instance:
            return

        attending_list = JsonUtilities.load_json_data(conversation_instance.co_hosts)

        if not attending_list:
            attending_list = []

        if conversation_creator_id not in attending_list:
            attending_list.append(conversation_creator_id)

        user_dict = MemberCommunityHelper.pre_compute_users_by_member_id_list(attending_list)

        for data in attending_list:
            ConversationHelper.attend_conversation_event(conversation_instance,
                                                         user_dict.get(data), True)

        update_event_attendees_for_micro_event.delay({'conversation_instance': conversation_instance,
                                                      'event_attendees_list': attending_list})

    @staticmethod
    def process_members_data_for_conversation_event(user_list, community_instance, 
                                                    sdk_client_info_flag:bool=True):

        info_list = []
        member_dict = MemberCommunityImpl. \
            fetch_members_based_on_user_list(user_list, community_instance, 
                                             sdk_client_info_flag=sdk_client_info_flag)

        for data in user_list:
            user_id = NumberUtilities.get_integer_from_string(data)

            if user_id in member_dict:
                info_list.append(member_dict[user_id])

            else:
                user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

                if not user_instance:
                    continue

                removed_context = dict()
                userinfo_instance = user_instance.userinfo
                removed_context['id'] = userinfo_instance.user_id_id
                removed_context['name'] = userinfo_instance.name
                removed_context['image_url'] = userinfo_instance.image_link if userinfo_instance.image_link else ""
                info_list.append(removed_context)

        return info_list

    @staticmethod
    def compute_event_attendees_of_chatroom(conversation_instance, community_instance):

        event_attendees_dict = CacheImpl.get_cache(EVENT_ATTENDEES_CONVERSATION % str(conversation_instance.id))

        if event_attendees_dict:
            event_attendees_list = event_attendees_dict.get('event_attendees_list', [])
            attendees_list = ConversationHelper.process_members_data_for_conversation_event(event_attendees_list,
                                                                                            community_instance)

            return attendees_list

        event_attendees_list = list(ModelUtilities.get_model_filter(conversationEventMembers,
                                                                    {'conversation': conversation_instance,
                                                                     'attending_status': True}
                                                                    ).values_list('user', flat=True).
                                    order_by('created_at')[:10])

        attendees_list = ConversationHelper.process_members_data_for_conversation_event(event_attendees_list,
                                                                                        community_instance)
        update_event_attendees_for_micro_event.delay({'conversation_id': conversation_instance.id,
                                                      'event_attendees_list': event_attendees_list})
        return attendees_list

    @staticmethod
    def compute_members_data_for_conversation(conversation_instance):

        co_hosts_list = JsonUtilities.load_json_data(conversation_instance.co_hosts)
        members_data = {}
        community_instance = conversation_instance.community

        if co_hosts_list:
            members_data['co_hosts_ids'] = co_hosts_list
            members_data['co_hosts'] = ConversationHelper. \
                process_members_data_for_conversation_event(co_hosts_list, community_instance)

        members_data['attendees'] = ConversationHelper. \
            compute_event_attendees_of_chatroom(conversation_instance, community_instance)

        return members_data

    @staticmethod
    def _get_community_notification_state(chatroom_instance):

        from collabmates_api.community.community_impl import CommunityHelper

        community_noti_instance = CommunityHelper.fetch_community_noti_settings_instance(
            chatroom_instance.community)

        return community_noti_instance.noti_state if community_noti_instance else noti_states.ALL_MESSAGES

    @staticmethod
    def _set_preview_for_conversation(conversation_instance, user_id, req_body):
        preview_utilities = PreviewUtilities()
        preview_utilities.set_preview_object(conversation_instance, req_body, user_id)
        conversation_instance.save()

    @staticmethod
    def auto_follow_for_tagged_members(chatroom_instance, conversation_instance):
        conversation_text = conversation_instance.answer
        tagged_member_list, answer_text, tagged_user_names, should_unmute_members, is_group_tag = get_tagged_members_list(
            chatroom_instance.community_id,
            chatroom_instance.id,
            conversation_text
        )

        if not tagged_member_list:
            return tagged_member_list, False

        is_tagged = True
        mute_status = True

        if chatroom_instance.type == card_types.CARD_PURPOSE:
            mute_status = is_tagged = False

        if should_unmute_members:
            is_tagged = False
            mute_status = False

        chatroom_state_update_dict = {
            'is_tagged': is_tagged,
            'mute_status': mute_status,
            'follow_status': True,
            'external_seen': True,
            'state': collabcard_states.COLLABCARD_STATE_SEEN
        }

        bulk_state_instance_list = []

        state_filter = ModelUtilities.get_model_filter(collabcardState,
                                                       {'card': chatroom_instance,
                                                        'user__in': tagged_member_list})

        search_update_users_list = []

        if should_unmute_members:
            filter_dict = {
                'follow_status': True
            }
            search_update_users_list = list(state_filter.filter(**filter_dict).values_list('user_id', flat=True))
            state_filter.filter(**filter_dict).update(mute_status=mute_status, is_tagged=is_tagged)

        filter_dict = {
            'follow_status': False
        }

        search_update_users_list += list(state_filter.filter(**filter_dict).values_list('user_id', flat=True))
        state_filter.filter(**filter_dict).update(**chatroom_state_update_dict)

        state_filter_user_ids_list = state_filter.values_list('user_id', flat=True)
        user_instances_filter = ModelUtilities.get_model_filter(
            User, {'id__in': tagged_member_list}).exclude(id__in=state_filter_user_ids_list)

        community_current_noti_state = ConversationHelper._get_community_notification_state(chatroom_instance)

        for user_inst in user_instances_filter:
            state_instance = collabcardState.create_chatroom_state_instances_for_bulk_create(
                chatroom_instance, user_inst, noti_state=community_current_noti_state,
                **chatroom_state_update_dict)

            bulk_state_instance_list.append(state_instance)

        if bulk_state_instance_list:
            ModelUtilities.bulk_create_instances(collabcardState, bulk_state_instance_list)

        if search_update_users_list:
            search_update_users_list = list(set(search_update_users_list))
            ElasticSearchSync.update_chatroom_for_users_list.delay(chatroom_instance.id, search_update_users_list)

        return tagged_member_list, is_group_tag

    @staticmethod
    def _handle_dm_chatroom_communication(chatroom_instance, user_instance):

        user_id = chatroom_instance.user_id
        chatroom_with_user_id = chatroom_instance.chatroom_with_user_id

        if chatroom_instance.type == card_types.CARD_DIRECT_MESSAGE and chatroom_instance.is_private:
            sender_id = user_id if user_instance.id == user_id else chatroom_with_user_id
            receiver_id = user_id if user_instance.id != user_id else chatroom_with_user_id

            ConversationHelper.send_engagement_communication(receiver_id, sender_id, chatroom_instance.id,
                                                             chatroom_not_opened_types.DM_CHATROOM)

    @staticmethod
    def _create_or_update_conversation_engage(chatroom_instance: Collabcard, user_instance: User,
                                              conversation_instance: card_answers, tagged_members=None):

        users_list = []
        create_engage_list = []

        if not (conversation_instance.attachment_count > 0 and not conversation_instance.attachments_uploaded):
            update_conversation_engage_data_for_chatroom.delay(chatroom_instance.id, user_instance.id,
                                                               TimeUtilities.current_time_in_sec())

        engage_members = tagged_members + [user_instance.id] if tagged_members else [user_instance.id]
        is_converted, engage_members = NumberUtilities.convert_list_to_integer_list_with_conversion_status(
            engage_members)

        if not is_converted:
            return

        engage_users_list = list(ModelUtilities.get_model_filter(
            conversationEngage, {'card': chatroom_instance}).values_list('user_id', flat=True))

        engage_members = ListUtilities.remove_list_elements(engage_members, engage_users_list)

        if not engage_members:
            return

        conversations_filter = ModelUtilities.get_model_filter(card_answers,
                                                               {'card': chatroom_instance, 'state': 0}). \
            filter(Q(attachment_count=0) | Q(attachments_uploaded=True) | Q(api_version=1)).order_by('id')

        total_conversations = conversations_filter.count()

        for user_id in engage_members:
            engage_user_instance = ModelUtilities.get_user_instance_or_none(user_id)

            if not engage_user_instance:
                continue

            if engage_user_instance.id not in users_list:
                rights_list = list(userMemberRights.objects.filter(user=engage_user_instance,
                                                                   community=chatroom_instance.community).exclude(
                    right__state=4).values_list("right__state", flat=True))

                rights_list = json.dumps(rights_list)

                unseen_count = total_conversations if engage_user_instance != user_instance else 0

                instance = conversationEngage.create_instance_for_bulk_create(
                    community_instance=chatroom_instance.community, chatroom_instance=chatroom_instance,
                    user_instance=engage_user_instance, rights_list=rights_list, unseen_count=unseen_count)

                create_engage_list.append(instance)

                users_list.append(engage_user_instance.user_id)

        ModelUtilities.bulk_create_instances(conversationEngage, create_engage_list)

    @staticmethod
    def auto_follow_chatroom(chatroom_instance, chatroom_state_instance, conversation_instance, user_instance,
                             member_state, trigger_webhook=False):

        empty_conversation = (conversation_instance.attachment_count > 0 and not conversation_instance.attachments_uploaded)

        followed_chatroom = False

        if chatroom_state_instance:

            follow_status_old = chatroom_state_instance.follow_status

            if not empty_conversation:
                chatroom_state_instance.last_seen_conversation = conversation_instance

            chatroom_state_instance.follow_status = True
            chatroom_state_instance.updated_at = TimeUtilities.current_time_in_sec()

            if chatroom_state_instance.is_tagged:
                chatroom_state_instance.is_tagged = False
                chatroom_state_instance.mute_status = False

            chatroom_state_instance.save()

            ElasticSearchSync.update_chatroom_for_user.delay(chatroom_instance.id, user_instance.id)

            if follow_status_old != chatroom_state_instance.follow_status:
                followed_chatroom = True

        else:
            community_current_noti_state = ConversationHelper._get_community_notification_state(chatroom_instance)

            if any([member_state == member_states.ADMIN,
                    member_state == member_states.MEMBER,
                    member_state == member_states.PROFILE_UNAVAILABLE]):

                collabcardState.create_chatroom_state_instance(chatroom_instance, user_instance,
                                                               state=collabcard_states.COLLABCARD_STATE_UNSEEN,
                                                               follow_status=True,
                                                               noti_state=community_current_noti_state)

            elif member_state != member_states.KNOWN_NOMINATED_PROMOTER:
                collabcardState.create_chatroom_state_instance(chatroom_instance, user_instance,
                                                               state=collabcard_states.COLLABCARD_STATE_UNSEEN,
                                                               is_guest=True, follow_status=True,
                                                               noti_state=community_current_noti_state)

                ModelUtilities.model_update(Userinfo, {'user': user_instance},
                                            {'updated_at': TimeUtilities.current_time_in_sec()})

            followed_chatroom = True
                
        if followed_chatroom and trigger_webhook:
            chatroom_impl.ChatroomImpl.trigger_webhook_for_chatroom_event.delay(community_id=chatroom_instance.community_id,
                                                                                chatroom_id=chatroom_instance.id,
                                                                                users_list=[user_instance.id],
                                                                                event_type=WebhookTypes.CHATROOM_JOINED.value,
                                                                                type_method=webhook_chatroom_methods.SELF_JOINED)

        ChatroomHelper.delete_chatroom_participants_cache.delay(chatroom_instance.community_id,
                                                                user_instance.id,
                                                                chatroom_instance.id)

    @staticmethod
    def _send_conversation_creation_notifications(user_instance, chatroom_instance, conversation_instance, has_files,
                                                  all_files_uploaded: bool = False):

        is_poll_conversation = (conversation_instance.state == conversation_states.CONVERSATION_POLL)

        if is_poll_conversation:
            send_poll_conversation_creation_notification_v1.delay(conversation_instance.card_id,
                                                                  conversation_instance.user_id,
                                                                  conversation_instance.id)

        update_chatroom_for_users_and_send_follow_notification.delay(chatroom_instance.id,
                                                                     user_instance.id,
                                                                     conversation_instance.id,
                                                                     has_files=has_files,
                                                                     all_files_uploaded=all_files_uploaded)

    @staticmethod
    def save_attachments(conversation_instance, attachments_data: list):

        with transaction.atomic():

            for attachment_data in attachments_data:
                index = attachment_data.get('index', None)
                attachment_meta = JsonUtilities.dump_json_data(attachment_data.get('meta'))

                attachment_context = {
                    'type': attachment_data.get('type', None),
                    'file_url': attachment_data.get('url', None),
                    'location_name': attachment_data.get('location_name', None),
                    'location_lat': attachment_data.get('location_lat', None),
                    'location_long': attachment_data.get('location_long', None),
                    'width': attachment_data.get('width', None),
                    'height': attachment_data.get('height', None),
                    'thumbnail_url': attachment_data.get('thumbnail_url', None),
                    'meta': attachment_meta,
                    'name': attachment_data.get('name', None)
                }

                filter_dict = {
                    'answer': conversation_instance,
                    'index': index
                }

                ModelUtilities.update_or_create_model(answerAttachment, filter_dict, attachment_context)

                if attachment_data.get('type') == attachment_types.GIF:
                    conversation_instance.answer = conversation_instance.answer + GIF_ATTACHMENT_FILL_TEXT

            uploaded_files_count = ModelUtilities.get_model_filter(answerAttachment,
                                                                   {'answer': conversation_instance}).count()

            all_files_uploaded = uploaded_files_count == conversation_instance.attachment_count

            # updating the last updated when posting answer
            conversation_instance.last_updated = TimeUtilities.current_time_in_milliseconds()

            if not all_files_uploaded:
                conversation_instance.save()

            elif all_files_uploaded:
                conversation_instance.attachments_uploaded = True
                conversation_instance.save()

        return all_files_uploaded

    @staticmethod
    @shared_task
    def update_activity_in_chatroom_for_followed_users(chatroom_id, user_id):
        activate_chatroom_for_followed_users_on_conversation_creation(chatroom_id, user_id)

    @staticmethod
    @shared_task
    def run_async_task_on_conversation_create(user_id: int, chatroom_id: int, conversation_id: int,
                                              req_body: dict = None, member_state: int = member_states.GUEST,
                                              trigger_webhook: bool = False, attachments_data: list = [],
                                              tagged_members_list: list = [], is_group_tag: bool = False,
                                              all_files_uploaded: bool = False):

        if req_body is None:
            req_body = dict()

        has_files = req_body.get('has_files', False)
        attachment_count = req_body.get('attachment_count', 0)

        replied_conversation = req_body.get('replied_conversation_id', None)

        has_files = has_files or attachment_count > 0

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)
        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)
        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

        if 'share_link' in req_body:
            ConversationHelper.update_share_link_og_tags_in_conversation.delay(conversation_instance.id, 
                                                                               req_body['share_link'])
            
        if replied_conversation:
            # Trigger webhook if user replies to a conversation in a chatroom
            ConversationImpl.trigger_webhook_for_conversation_event.delay(conversation_instance.community_id,
                                                                          conversation_instance.id,
                                                                          [],
                                                                          WebhookTypes.CHATROOM_CONVERSATION_REPLIED.value)

        ConversationHelper._set_preview_for_conversation(conversation_instance, user_id, req_body)

        if tagged_members_list and (not is_group_tag):
            # Trigger webhook for user tagging in a chatroom
            ConversationImpl.trigger_webhook_for_conversation_event.delay(conversation_instance.community_id,
                                                                          conversation_instance.id,
                                                                          tagged_members_list,
                                                                          WebhookTypes.CHATROOM_USER_TAGGED.value)

        if (not has_files) or all_files_uploaded:
            ConversationHelper.update_latest_conversation_id_to_firebase_v1.delay(chatroom_instance.id,
                                                                                  conversation_instance.id,
                                                                                  chatroom_instance.community_id)

        ConversationHelper.update_previews_on_conversation_creation(chatroom_instance)
        ConversationHelper._send_conversation_creation_notifications(user_instance, chatroom_instance,
                                                                     conversation_instance, has_files,
                                                                     all_files_uploaded)

        ConversationHelper.update_last_seen_conversation_in_collabcard_state(conversation_instance,
                                                                             user_instance, chatroom_instance)

        # Updating the chatroom index for updated at
        ElasticSearchSync.update_chatroom.delay(chatroom_id)

        args = [conversation_instance.id]

        if conversation_instance.state == conversation_states.CONVERSATION_POLL:
            start_time = TimeUtilities.convert_epoch_to_datetime_in_IST(conversation_instance.expiry_time)
            update_deferred_conversation_poll_updated_at_value.apply_async(args=args, kwargs={},
                                                                           eta=start_time)

    @staticmethod
    def _validate_group_tags(
            message: str,
            member_state: int,
            user_id: int,
            chatroom_creator_id: int,
            is_secret_chatroom: bool
    ) -> bool:
        is_everyone_tag: list = re.findall(EVERYONE_TAG_REGEX, message)
        if is_everyone_tag and is_secret_chatroom:
            return False

        if is_everyone_tag and member_state != member_states.ADMIN:
            return False

        is_participants_tag: list = re.findall(PARTICIPANTS_TAG_REGEX, message)
        if is_participants_tag and member_state != member_states.ADMIN and user_id != chatroom_creator_id:
            return False

        return True

    @staticmethod
    def validate_create_conversation_request(user_instance, user_id, chatroom_instance, chatroom_id, message,
                                             replied_conversation_id=None, temporary_id=None):

        start = time.time()

        if user_instance is None:
            user_instance = ModelUtilities.get_user_instance_or_none(user_id)

            if not user_instance:
                return ResponseUtilities.get_inner_error_context('Invalid member id')

        if chatroom_instance is None:
            chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

            if not chatroom_instance:
                return ResponseUtilities.get_inner_error_context('Invalid chatroom id')

        replied_conv_instance = None

        if replied_conversation_id:
            replied_conv_instance = ModelUtilities.get_model_instance_or_none(card_answers, replied_conversation_id)

            if not replied_conv_instance:
                return ResponseUtilities.get_inner_error_context('Invalid replied conversation id')

        community_instance = chatroom_instance.community
        member_state = Members.get_community_member_state(community_instance, user_instance)
        is_admin = (member_state == member_states.ADMIN)

        is_tag_allowed = ConversationHelper._validate_group_tags(
            message,
            member_state,
            user_id,
            chatroom_instance.user.id,
            chatroom_instance.is_secret
        )

        if not is_tag_allowed:
            return ResponseUtilities.get_inner_error_context('tag not allowed')

        if chatroom_instance.type == card_types.CARD_MASTER_INTRO:
            return ResponseUtilities.get_inner_error_context("Responding is disabled")

        has_right = ModelUtilities.get_model_filter(userMemberRights,
                                                    {'user': user_instance, 'community': community_instance,
                                                     'right__state': member_rights.MEMBER_RIGHT_RESPOND_IN_ROOM})

        if not has_right:
            return ResponseUtilities.get_inner_error_context("You don't have right to respond in chatroom!")

        # Get user specific chatroom settings
        user_chatroom_settings = chatroom_impl.ChatroomHelper.compute_user_chatroom_settings(user_instance, 
                                                                                             chatroom_instance, 
                                                                                             is_admin,
                                                                                             [CHATROOM_USER_SETTINGS_MEMBER_CAN_MESSAGE])

        # If user_chatroom_settings for 'member_can_message' is false, then return error
        if not user_chatroom_settings or not user_chatroom_settings[0].enabled :
            return ResponseUtilities.get_inner_error_context("You don't have right to respond in chatroom!")

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance,
            'member_state': member_state,
            'replied_conv_instance': replied_conv_instance
        }
    
    @staticmethod
    def get_conversation_payload_for_webhook_events(conversation_id: int, event_type: str):
        
        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)
        
        if not conversation_instance:
            return {}
        
        payload = {
            "id": conversation_instance.id,
            "text": conversation_instance.answer,
            "created_at": conversation_instance.created_at,
            "chatroom_id": conversation_instance.card_id,
            "user_id": conversation_instance.user_id,
        }

        if event_type == WebhookTypes.CHATROOM_CONVERSATION_REPLIED.value:
            payload['replied_conversation_id'] = conversation_instance.reply_id
        
        return payload
