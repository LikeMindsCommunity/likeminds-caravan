import time
import json
from django.contrib.auth.models import User
from typing import Union
from rest_framework import status as status_codes

from .conversation_manager import ConversationManager
from ..rest_api import CardAnswersDBSyncSerializer
from ..serializers import conversationSerializer, get_preview_for_url, get_guest_custom_text, \
    get_removed_member_custom_text, get_conversation_instance_for_db_synching
from ..sync.model_update import update_models_for_syncing_apis
from ..utility import pagination
from ..user.user_impl import UserHelper
from ..views import (adding_guest_in_chatroom, conversation_tagging, collabcard_follow_internal,
                     save_the_latest_conversation, update_activity_in_chatroom_for_conversation_creation,
                     update_chatroom_for_users_and_send_follow_notification,
                     reverse_conversations_for_upward_pagination, send_sync_notification,
                     generate_internal_link_preview_for_conversation)

from .constants import (LIST_SIZE, UPWARD_SCROLL_LIST_SIZE, DOWNWARD_SCROLL_LIST_SIZE, UPWARD_SCROLL_DIRECTION,
                        DOWNWARD_SCROLL_DIRECTION, ERROR_MESSAGE_FOR_ANNOUNCEMENT_ROOM)

from togther.models import card_answers, collabcardState, Collabcard, Members, Community
from external_services.logging.logging_wrapper import LoggingWrapper

from utility.exception_utilities import CustomException, InvalidChatroomException
from utility.internal_link_preview_utilities import PreviewUtilities
from utility.request_utilities import RequestUtilities
from utility.states import member_states, collabcard_states, card_types, SyncNotificationTypes, SyncTypes
from utility.utils import decode_meta_from_url
from utility.firebase import update_last_answer_id
from utility.celery_tasks import update_my_chatrooms_for_users, update_multiple_previews_in_chatroom, \
    update_preview_of_chatroom_in_cache
from utility.time_utilities import TimeUtilities
from utility.number_utilities import NumberUtilities

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class ConversationImpl(ConversationManager):
    member_id = None
    chatroom_id = None
    scroll_direction = None
    conversation_id = None
    page = None
    paginate_by = None

    def __init__(self, member_id: str, chatroom_id: str = None, scroll_direction: str = None,
                 conversation_id: str = None, page: str = None,
                 paginate_by: str = None):

        self.member_id = member_id
        self.chatroom_id = chatroom_id
        self.scroll_direction = scroll_direction
        self.conversation_id = conversation_id
        self.page = page
        self.paginate_by = paginate_by

    def get_member_id(self) -> Union[str, int]:
        return self.member_id

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
        return self.paginate_by

    def set_paginate_by(self, paginate_by: Union[str, int]):
        self.paginate_by = paginate_by

    def _fetch_conversation_queryset(self):
        return card_answers.objects.select_related('reply', 'preview_community',
                                                   'preview_chatroom').filter(card=self.get_chatroom_id()
                                                                              ).order_by('id')

    def _fetch_upward_conversation_queryset(self, list_size, conversation_id):
        return card_answers.objects.select_related('reply', 'preview_community',
                                                   'preview_chatroom').filter(card=self.get_chatroom_id()).filter(
            id__lte=conversation_id).order_by('-id')[:list_size]

    def _fetch_downward_conversation_queryset(self, list_size, conversation_id):
        return card_answers.objects.select_related('reply', 'preview_community',
                                                   'preview_chatroom').filter(card=self.get_chatroom_id()).filter(
            id__gt=conversation_id).order_by('-id')[:list_size]

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

    def _serialize_conversation(self, conversation_instance):

        conversation_serializer = conversationSerializer(conversation_instance,
                                                         fetch_reply=True,
                                                         current_user_id=self.get_member_id())
        conversation_serializer['created_at'] = TimeUtilities.convert_epoch_time_in_hh_mm(
            conversation_instance.created_at)

        preview = self._generate_internal_link_preview(conversation_instance)

        if preview:
            conversation_serializer['preview'] = preview

        return conversation_serializer

    def _create_conversation_list(self, conversations):

        conversation_list = []

        for conversation in conversations:

            if (conversation.attachment_count > 0 and
                conversation.attachments_uploaded is False) and (
                    (self.get_member_id() and
                     conversation.user.id != NumberUtilities.get_integer_from_string(self.get_member_id())) or
                    conversation.api_version <= 0):
                continue

            conversation_dict = self._serialize_conversation(conversation)
            conversation_list.append(conversation_dict)

        return conversation_list

    def _is_user_already_guest(self, chatroom, user):
        return collabcardState.objects.filter(card=chatroom,
                                              user=user,
                                              is_guest=True).exists()

    def _fill_basic_conversation_content(self, req_body, conversation_content,
                                         chatroom_instance, user_instance, community_instance,
                                         has_files):

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

        conversation_content['api_version'] = 1

        conversation_content['is_guest'] = self._is_user_already_guest(user=user_instance,
                                                                       chatroom=chatroom_instance)

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

    def _add_guest_in_chatroom(self, chatroom_instance, community_id, member_state, is_guest, aj, source_id):

        if is_guest and (member_state == member_states.GUEST or member_state == member_states.PENDING_MEMBER):
            context = {}
            context = adding_guest_in_chatroom(context, chatroom_instance, aj, source_id,
                                               community_id, self.get_member_id(), guest_header=True)

    def _update_latest_conversation_id_to_firebase(self, chatroom_id, conversation_id):
        update_last_answer_id(chatroom_id, conversation_id)

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

    def _auto_follow_for_tagged_members(self, req_body, chatroom_instance, user_instance):
        conversation_tagging(None, req_body, chatroom_instance,
                             user_instance, self.get_member_id())

    def _update_home_page(self, chatroom_id, req_body, has_files, is_ios):
        user_id = self.get_member_id() if has_files else None
        update_my_chatrooms_for_users(chatroom_id=chatroom_id, user_id=user_id)

        update_activity_in_chatroom_for_conversation_creation(chatroom_id,
                                                              user_id=self.get_member_id())

        update_chatroom_for_users_and_send_follow_notification.delay(chatroom_id,
                                                                     self.get_member_id(),
                                                                     req_body['text'],
                                                                     has_files=has_files)

    def fetch_conversation(self):

        if not self.get_scroll_direction() and self.get_conversation_id():
            last_seen_conversation = self._fetch_last_seen_conversation()

            if last_seen_conversation:
                conversations = [last_seen_conversation]
                conversations = self._create_conversation_list(conversations)

                return conversations

        if not self.get_scroll_direction() and not self.get_conversation_id():

            last_seen = self._fetch_last_seen_conversation()

            if not last_seen:
                conversations = self._fetch_conversation_queryset()
                conversations = self._paged_queryset(conversations)
                conversations = self._create_conversation_list(conversations)

            else:

                upward_conversation = self._fetch_upward_conversation_queryset(LIST_SIZE, last_seen.id)
                downward_conversation = self._fetch_downward_conversation_queryset(LIST_SIZE, last_seen.id)

                # merging both conversations
                conversations = upward_conversation | downward_conversation
                conversations = conversations.order_by('id')
                conversations = self._create_conversation_list(conversations)

        else:

            if self.get_scroll_direction() and NumberUtilities.get_integer_from_string(
                    self.get_scroll_direction()) == UPWARD_SCROLL_DIRECTION:  # upward scroll
                upward_list = self._fetch_upward_conversation_queryset(UPWARD_SCROLL_LIST_SIZE,
                                                                       self.get_conversation_id())
                conversations = reverse_conversations_for_upward_pagination(upward_list)

            elif self.get_scroll_direction() and NumberUtilities.get_integer_from_string(
                    self.get_scroll_direction()) == DOWNWARD_SCROLL_DIRECTION:  # downward scroll
                conversations = self._fetch_downward_conversation_queryset(DOWNWARD_SCROLL_LIST_SIZE,
                                                                           self.get_conversation_id())

            else:
                conversations = self._fetch_conversation_queryset()

            conversations = self._create_conversation_list(conversations)

        chatroom_instance = ConversationHelper.fetch_chatroom_instance(self.get_chatroom_id())
        self._save_latest_conversation_for_members(chatroom_instance)


        return conversations

    def create_conversation(self, req_body: dict, is_ios: bool,
                            is_user_guest: bool, has_files: bool) -> {}:

        chatroom_id = req_body.get('chatroom_id', None)

        if not chatroom_id:
            response = {
                'success': False,
                "error_message": "send chatroom id in body"
            }
            raise InvalidChatroomException(response)

        user_instance = ConversationHelper.fetch_user_instance(user_id=self.get_member_id())

        chatroom_instance = ConversationHelper.fetch_chatroom_instance(chatroom_id=chatroom_id)

        community_id = chatroom_instance.community.id

        community_instance = ConversationHelper.fetch_community_instance(community_id=community_id)

        member_state = ConversationHelper.fetch_member_state(community=community_instance, user=user_instance)

        if chatroom_instance.type == card_types.CARD_PURPOSE and\
                member_state != member_states.ADMIN:

            return {'success': False, 'error_message': ERROR_MESSAGE_FOR_ANNOUNCEMENT_ROOM}

        if chatroom_instance.type == card_types.CARD_MASTER_INTRO:
            return {'success': False, 'error_message': "Responding is disabled"}

        self._add_guest_in_chatroom(chatroom_instance, community_id, member_state,
                                    is_guest=is_user_guest,
                                    aj=req_body.get('aj', None),
                                    source_id=req_body.get('source_id', None))

        conversation_content = {}

        self._fill_basic_conversation_content(req_body, conversation_content,
                                              chatroom_instance, user_instance, community_instance,
                                              has_files)
        conversation_content['reply'] = ConversationHelper.fetch_replied_conversation(req_body)
        conversation_content['og_tags'] = ConversationHelper.fetch_og_tags(req_body)

        conversation_instance = self._create_conversation_instance(conversation_content)
        self._set_preview_for_conversation(conversation_instance, req_body)

        attachment_count = req_body.get('attachment_count', 0)

        has_files = has_files or attachment_count > 0

        if not has_files:
            self._update_latest_conversation_id_to_firebase(chatroom_id,
                                                            conversation_instance.id)

        self._save_latest_conversation_for_members(chatroom_instance)

        self._auto_follow_chatroom(chatroom_id, member_state)

        self._auto_follow_for_tagged_members(req_body, chatroom_instance, user_instance)

        self._update_home_page(chatroom_id, req_body,
                               has_files=has_files,
                               is_ios=is_ios)
        chatroom_preview_update_count = update_models_for_syncing_apis(SyncTypes.CONVERSATION,
                                       {'preview_chatroom': chatroom_instance, 'preview_type': "chatroom"},
                                       {})

        if chatroom_preview_update_count:
            preview_chatroom_id = chatroom_instance.id
            update_multiple_previews_in_chatroom.delay({'chatroom_id': preview_chatroom_id})

        context = {"current_user_id": self.get_member_id(), "fetch_reply": True}
        conversation = CardAnswersDBSyncSerializer(conversation_instance, context=context, many=False).data

        send_sync_notification.delay({'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value,
                                      'community_id': community_id})

        conversation_response = {
            'success': True,
            'id': conversation_instance.id,
            'conversation': conversation
        }

        return conversation_response


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
            og_tags = json.dumps(decode_meta_from_url(req_body['share_link']))
        else:
            return
        return og_tags

    @staticmethod
    def fetch_member_state(community, user) -> int:
        return Members.get_community_member_state(community, user)

    @staticmethod
    def fetch_auto_follow_dict(member_id, chatroom_id, status, source):

        return {
            'member_id': member_id,
            'collabcard_id': chatroom_id,
            'status': status,
            'source': source
        }
