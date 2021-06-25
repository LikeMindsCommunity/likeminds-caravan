import time
import json
from django.contrib.auth.models import User
from typing import Union

from django.db.models import F, Q, Count
from rest_framework import status as status_codes

from utility.constants import CREATE_INTRO_TEXT_ADMIN, CREATE_INTRO_TEXT_MEMBER, CUSTOM_CLICK_TEXT, MINUTES_5, \
    MINUTES_30

from .conversation_manager import ConversationManager
from .reactions import fetch_chatroom_or_conversation_reactions
from ..chatroom.chatroom_impl import ChatroomHelper
from ..notification import send_notification_to_message_creator_on_reaction, get_tagged_members_list
from ..member_community.member_community_impl import MemberCommunityImpl
from ..raw_queries import activate_chatroom_on_conversation_creation, \
    get_latest_conversation_creator_users_for_homescreen, update_conversation_engage_for_chatrooms
from ..rest_api import CardAnswersDBSyncSerializer
from ..serializers import conversationSerializer, UserinfoSerializer
from ..sync.model_update import update_models_for_syncing_apis
from ..tasks import send_tagged_user_mail, send_chatroom_owner_mail
from ..utility import pagination
from ..user.user_impl import UserHelper
from ..views import (adding_guest_in_chatroom, conversation_tagging, collabcard_follow_internal,
                     save_the_latest_conversation, update_activity_in_chatroom_for_conversation_creation,
                     update_chatroom_for_users_and_send_follow_notification,
                     reverse_conversations_for_upward_pagination, send_sync_notification,
                     generate_internal_link_preview_for_conversation, send_poll_conversation_creation_notification,
                     create_chatroom_engagement, create_chatroom)

from .constants import *

from togther.models import (card_answers, collabcardState, Collabcard, Members,
                            Community, ModelUtilities, MessageReactions, conversationPolls,
                            conversationPollMembers, Userinfo, conversationEngage, answerAttachment)
from external_services.logging.logging_wrapper import LoggingWrapper

from utility.exception_utilities import CustomException, InvalidChatroomException
from utility.internal_link_preview_utilities import PreviewUtilities
from utility.request_utilities import RequestUtilities
from utility.states import member_states, collabcard_states, card_types, SyncNotificationTypes, SyncTypes, \
    conversation_states, conversation_poll_types
from utility.utils import decode_meta_from_url, check_notification_flag
from utility.firebase import update_last_answer_id, update_my_chatrooms_on_homefeed_in_firebase
from utility.celery_tasks import (update_my_chatrooms_for_users, update_multiple_previews_in_chatroom,
                                  update_preview_of_chatroom_in_cache,
                                  get_conversation_poll, save_conversation_poll_options_in_cache,
                                  save_conversation_poll_voters_in_cache, update_multiple_previews_in_community)

from utility.time_utilities import TimeUtilities
from utility.number_utilities import NumberUtilities
from celery import shared_task
from ..owner_message_template import post_owner_message_template_in_intro_room, check_owner_template_posted

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

    def __init__(self, member_id: str, chatroom_id: str = None, scroll_direction: str = None,
                 conversation_id: str = None, page: str = None, paginate_by: str = None,
                 device_id: str = None, platform_code: str = None, include_conversation_id: bool = False):

        self.member_id = member_id
        self.chatroom_id = chatroom_id
        self.scroll_direction = scroll_direction
        self.conversation_id = conversation_id
        self.page = page
        self.paginate_by = paginate_by
        self.device_id = device_id
        self.platform_code = platform_code
        self.include_conversation_id = include_conversation_id

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
        return NumberUtilities.get_integer_from_string(self.paginate_by)

    def set_paginate_by(self, paginate_by: Union[str, int]):
        self.paginate_by = paginate_by

    def _fetch_conversation_queryset(self):
        return card_answers.objects.select_related('reply', 'preview_community',
                                                   'preview_chatroom').filter(card=self.get_chatroom_id()
                                                                              ).order_by('created_at')

    def _fetch_scroll_conversations(self):
        conversations = card_answers.objects\
            .select_related('reply', 'preview_community', 'preview_chatroom')\
            .filter(card=self.get_chatroom_id())

        return conversations

    def _fetch_upward_conversation_queryset(self, list_size, conversation_id):
        conversations = self._fetch_scroll_conversations()
        conversations = conversations.filter(id__lt=conversation_id).order_by('-created_at')

        return conversations[:list_size]

    def _fetch_upward_conversation_including_given_conversation(self, list_size, conversation_id):
        conversations = self._fetch_scroll_conversations()
        conversations = conversations.filter(id__lte=conversation_id).order_by('-created_at')

        return conversations[:list_size]

    def _fetch_downward_conversation_queryset(self, list_size, conversation_id):
        conversations = self._fetch_scroll_conversations()
        conversations = conversations.filter(id__gt=conversation_id).order_by('created_at')

        return conversations[:list_size]

    def _fetch_downward_conversation_including_given_conversation(self, list_size, conversation_id):
        conversations = self._fetch_scroll_conversations()
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

    def _serialize_conversation(self, conversation_instance):

        conversation_serializer = conversationSerializer(conversation_instance,
                                                         fetch_reply=True,
                                                         current_user_id=self.get_member_id())
        conversation_serializer['created_at'] = TimeUtilities.convert_epoch_time_in_hh_mm(
            conversation_instance.created_at)

        preview = self._generate_internal_link_preview(conversation_instance)

        if preview:
            conversation_serializer['preview'] = preview

        poll_conversation = self._serialize_poll_conversation(conversation_instance)

        if poll_conversation:
            conversation_serializer.update(poll_conversation)

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

            poll_conversation['poll_type_text'] = "Instant poll" \
                if poll_conversation['poll_type'] == conversation_poll_types.INSTANT else "Deferred poll"

            poll_conversation['submit_type_text'] = "Secret voting" \
                if poll_conversation['is_anonymous'] else "Public voting"

            poll_conversation['poll_answer_text'] = conversation_instance.poll_answer_text

        return poll_conversation

    def _create_conversation_list(self, conversations, last_conversation_id=None):

        conversation_list = []

        for conversation in conversations:

            if (conversation.attachment_count > 0 and
                conversation.attachments_uploaded is False) and (
                    (self.get_member_id() and
                     conversation.user.id != NumberUtilities.get_integer_from_string(self.get_member_id())) or
                    conversation.api_version <= 0 or conversation.device_id != self.device_id):
                continue

            conversation_dict = self._serialize_conversation(conversation)

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
                                         has_files, chatroom_state_instance):

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
        conversation_content['is_guest'] = chatroom_state_instance.is_guest if chatroom_state_instance else False

        if req_body.get('replied_chatroom_id'):
            conversation_content['reply_chatroom'] = chatroom_instance \
                if chatroom_instance.id == req_body.get('replied_chatroom_id') \
                else ModelUtilities.get_model_instance_or_none(Collabcard, req_body.get('replied_chatroom_id'))

        poll_context = self._fill_poll_conversation_context(req_body)

        if poll_context:
            conversation_content.update(poll_context)

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

    @staticmethod
    def _fill_poll_options(user_instance, conversation_instance, req_body):

        polls = req_body.get('polls')

        if not polls:
            return

        poll_instances = []

        member = UserinfoSerializer(user_instance.userinfo)

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
                                               created_at=created_at)

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
            chatroom_state_instance.expiry_time = ChatroomHelper.get_chatroom_expiry_time(chatroom_state_instance)
            chatroom_state_instance.updated_at = TimeUtilities.current_time_in_sec()
            chatroom_state_instance.save()

            if not current_follow_status:
                create_chatroom_engagement(chatroom_instance, user_instance, member_state=member_state)

        else:

            if member_state == member_states.ADMIN or \
                    member_state == member_states.MEMBER or \
                    member_state == member_states.PROFILE_UNAVAILABLE:
                expiry_time = ChatroomHelper.get_chatroom_expiry_time(chatroom_state_instance)
                state_instance = collabcardState.create_chatroom_state_instance(chatroom_instance,
                                                                                user_instance, state=0,
                                                                                expire_at=expiry_time)
                create_chatroom_engagement(chatroom_instance, user_instance, member_state=member_state)

    @staticmethod
    def _auto_follow_for_tagged_members(chatroom_instance, user_instance, conversation_instance):

        conversation_text = conversation_instance.answer
        tagged_member_list, answer_text, tagged_user_names = get_tagged_members_list(conversation_text)

        if not tagged_member_list:
            return

        is_tagged = True

        if chatroom_instance.type == card_types.CARD_PURPOSE:
            is_tagged = False

        for user_id in tagged_member_list:
            function_dict = {
                'member_id': user_id,
                'collabcard_id': chatroom_instance.id,
                'status': True,
                'source': "auto-following-chatroom",
                'is_tagged': is_tagged
            }
            collabcard_follow_internal(function_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

        ConversationHelper.run_async_tasks_for_conversation_tagging(tagged_member_list,
                                                                    user_instance,
                                                                    chatroom_instance)

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

        member_dict = MemberCommunityImpl.fetch_members_based_on_user_list(user_list, community_instance)
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

                    elif member_data['state'] == member_states.MEMBER or \
                            member_data['state'] == member_states.PROFILE_UNAVAILABLE:

                        member_data['custom_intro_text'] = CREATE_INTRO_TEXT_MEMBER % created_at
                        member_data['custom_click_text'] = CUSTOM_CLICK_TEXT % (
                            member_data['name'],
                            created_at)
            else:
                userinfo_filter = ModelUtilities.get_model_filter(Userinfo, {'user_id': user_id})

                if userinfo_filter:

                    userinfo_instance = userinfo_filter[0]

                    member_data = {
                        'id': user_id,
                        'name': userinfo_instance.name,
                        'image_url': userinfo_instance.image_link if userinfo_instance.image_link else ""
                    }

                else:
                    continue

            member_list.append(member_data)

        return member_list

    def fetch_conversation(self, top_navigate=False):

        if top_navigate:
            conversations = self._fetch_conversation_queryset()
            conversations = conversations[:self.get_paginate_by()]
            conversations = self._create_conversation_list(conversations)
            return conversations

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
                conversations = conversations[:self.get_paginate_by()]
                conversations = self._create_conversation_list(conversations)

            else:

                list_size = self.get_paginate_by() / 2
                upward_conversation = self._fetch_upward_conversation_including_given_conversation(list_size,
                                                                                                   last_seen.id)
                downward_conversation = self._fetch_downward_conversation_queryset(list_size, last_seen.id)

                # merging both conversations
                conversations = upward_conversation | downward_conversation
                conversations = conversations.order_by('created_at')
                conversations = self._create_conversation_list(conversations, last_conversation_id=last_seen.id)

        else:

            if self.get_scroll_direction() and NumberUtilities.get_integer_from_string(
                    self.get_scroll_direction()) == UPWARD_SCROLL_DIRECTION:  # upward scroll

                upward_scroll_list_size = self.get_paginate_by()

                if self.include_conversation_id:
                    upward_list = self._fetch_upward_conversation_including_given_conversation(upward_scroll_list_size,
                                                                                               self.get_conversation_id())
                else:
                    upward_list = self._fetch_upward_conversation_queryset(upward_scroll_list_size,
                                                                           self.get_conversation_id())

                conversations = reverse_conversations_for_upward_pagination(upward_list)

            elif self.get_scroll_direction() and NumberUtilities.get_integer_from_string(
                    self.get_scroll_direction()) == DOWNWARD_SCROLL_DIRECTION:  # downward scroll
                downward_scroll_list_size = self.get_paginate_by()

                if self.include_conversation_id:
                    conversations = self._fetch_downward_conversation_including_given_conversation(downward_scroll_list_size,
                                                                                                   self.get_conversation_id())

                else:
                    conversations = self._fetch_downward_conversation_queryset(downward_scroll_list_size,
                                                                               self.get_conversation_id())

            else:
                conversations = self._fetch_conversation_queryset()

            conversations = self._create_conversation_list(conversations)

        chatroom_instance = ConversationHelper.fetch_chatroom_instance(self.get_chatroom_id())
        self._save_latest_conversation_for_members(chatroom_instance)

        return conversations

    def create_conversation(self, req_body: dict, is_ios: bool = False,
                            is_user_guest: bool = False,
                            user_instance: User = None, chatroom_instance: Collabcard = None) -> {}:

        chatroom_id = req_body.get('chatroom_id', None)
        created_at = req_body.get('created_at', TimeUtilities.current_time_in_milliseconds())
        has_files = req_body.get('has_files', False)

        if not chatroom_id:
            response = {
                'success': False,
                "error_message": "send chatroom id in body"
            }
            raise InvalidChatroomException(response)

        if user_instance is None:
            user_instance = ConversationHelper.fetch_user_instance(user_id=self.get_member_id())

        if chatroom_instance is None:
            chatroom_instance = ConversationHelper.fetch_chatroom_instance(chatroom_id=chatroom_id)

        if chatroom_instance.is_secret and \
                not ConversationHelper.is_user_secret_chatroom_participant(chatroom_instance, self.get_member_id()):
            response = {
                'success': False,
                "error_message": "You are not a part of this secret chatroom"
            }

            raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

        if chatroom_instance.is_pending:
            response = {
                'success': False,
                "error_message": "This is a pending chatroom, conversations cannot be created here"
            }

            raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

        community_id = chatroom_instance.community_id

        community_instance = ConversationHelper.fetch_community_instance(community_id=community_id)

        member_state = ConversationHelper.fetch_member_state(community=community_instance, user=user_instance)

        if chatroom_instance.type == card_types.CARD_PURPOSE and \
                member_state != member_states.ADMIN:
            return {'success': False, 'error_message': ERROR_MESSAGE_FOR_ANNOUNCEMENT_ROOM}

        if chatroom_instance.type == card_types.CARD_MASTER_INTRO:
            return {'success': False, 'error_message': "Responding is disabled"}

        self._add_guest_in_chatroom(chatroom_instance, community_id, member_state,
                                    is_guest=is_user_guest,
                                    aj=req_body.get('aj', None),
                                    source_id=req_body.get('source_id', None),
                                    created_at=created_at)

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

        self._auto_follow_for_tagged_members(chatroom_instance, user_instance, conversation_instance)

        update_conversation_engage_for_chatrooms(card_id=chatroom_instance.id, user_id=user_instance.id,
                                                 last_conversation_id=conversation_instance.id,
                                                 unseen_count=0)

        ConversationHelper.update_previews_on_conversation_creation(chatroom_instance)
        self._send_conversation_creation_notifications(chatroom_instance, conversation_instance, has_files)

        context = {"current_user_id": self.get_member_id(), "fetch_reply": True}
        conversation = CardAnswersDBSyncSerializer(conversation_instance, context=context, many=False).data

        conversation_response = {
            'success': True,
            'id': conversation_instance.id,
            'conversation': conversation
        }

        return conversation_response

    def add_reaction(self, reaction: str) -> dict:

        if self.get_conversation_id() is None and self.get_chatroom_id() is None:
            response = {
                'success': False,
                'error_message': 'send conversation_id or chatroom_id in post params'
            }

            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = ConversationHelper.fetch_user_instance(self.get_member_id())

        chatroom_instance = None
        conversation_instance = None

        if self.get_conversation_id() is not None:
            conversation_instance = ConversationHelper.fetch_conversation_instance(self.get_conversation_id())
            chatroom_instance = conversation_instance.card

            conversation_instance.has_reactions = True
            conversation_instance.save()

        if self.get_chatroom_id() is not None and \
                chatroom_instance is None:
            chatroom_instance = ConversationHelper.fetch_chatroom_instance(self.get_chatroom_id())

            chatroom_instance.has_reactions = True
            chatroom_instance.save()

        current_time = TimeUtilities.current_time_in_milliseconds()

        update_context = {'reaction': reaction, 'updated_at': current_time}

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
                                        {'updated_at': TimeUtilities.current_time_in_sec()}
                                        )

        else:
            ModelUtilities.model_update(card_answers,
                                        {'pk': self.get_conversation_id()},
                                        {'last_updated': TimeUtilities.current_time_in_milliseconds()}
                                        )

        context = {
            "success": True
        }

        return context

    def remove_reaction(self) -> dict:

        if self.get_conversation_id() is None and self.get_chatroom_id() is None:
            response = {
                'success': False,
                'error_message': 'send conversation_id or chatroom_id in post params'
            }

            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = ConversationHelper.fetch_user_instance(self.get_member_id())

        chatroom_instance = None
        conversation_instance = None

        if self.get_conversation_id() is not None:
            conversation_instance = ConversationHelper.fetch_conversation_instance(self.get_conversation_id())
            chatroom_instance = conversation_instance.card

        if self.get_chatroom_id() is not None and \
                chatroom_instance is None:
            chatroom_instance = ConversationHelper.fetch_chatroom_instance(self.get_chatroom_id())

        MessageReactions.objects.filter(user=user_instance,
                                        chatroom=chatroom_instance,
                                        conversation=conversation_instance).delete()

        fetch_chatroom_or_conversation_reactions(self.get_chatroom_id(),
                                                 self.get_conversation_id(),
                                                 update_cache=True)

        if self.get_chatroom_id():

            ModelUtilities.model_update(collabcardState,
                                        {'card': chatroom_instance},
                                        {'updated_at': TimeUtilities.current_time_in_sec()}
                                        )

        else:
            ModelUtilities.model_update(card_answers,
                                        {'pk': self.get_conversation_id()},
                                        {'last_updated': TimeUtilities.current_time_in_milliseconds()}
                                        )

        context = {
            "success": True
        }

        return context

    def add_poll(self, request_body):

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers,
                                                                          request_body.get('conversation_id'))

        if not conversation_instance:
            return {'status': False, 'error_message': "send correct conversation id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'status': False, 'error_message': "incorrect user id"}

        if not conversation_instance.allow_add_option:
            return {'status': False, 'error_message': "new option cannot be added"}

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

        return {'success': True, 'poll': poll_response}

    def submit_poll(self, request_body):

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers,
                                                                          request_body.get('conversation_id'))

        if not conversation_instance:
            return {'status': False, 'error_message': "send correct conversation id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'status': False, 'error_message': "incorrect user id"}

        polls = request_body.get('polls', [])

        if conversation_instance.expiry_time < TimeUtilities.current_time_in_milliseconds():
            return {'success': False, 'error_message': "poll has been ended"}

        poll_filter = ModelUtilities.get_model_filter(conversationPollMembers, {'user': user_instance,
                                                                                'conversation': conversation_instance})
        poll_filter.delete()

        for poll in polls:

            poll_filter = ModelUtilities.get_model_filter(conversationPolls, {'id': poll.get('id'),
                                                                              'conversation': conversation_instance})

            if not poll_filter:
                return {'success': False, 'error_message': "invalid poll id"}

            poll_instance = poll_filter[0]
            poll_member_instance = conversationPollMembers.create_instance({'user_instance': user_instance,
                                                                            'poll_instance': poll_instance,
                                                                            'conversation_instance':
                                                                                conversation_instance})

        conversation_instance.poll_answer_text = ConversationHelper.compute_conversation_poll_answer_text(
            conversation_instance)
        conversation_instance.last_updated = TimeUtilities.current_time_in_milliseconds()
        conversation_instance.save()

        save_conversation_poll_voters_in_cache({'conversation_instance': conversation_instance})

        return {'success': True}

    def poll_users(self, poll_id, page, page_size):

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, self.get_conversation_id())

        if not conversation_instance:
            return {'status': False, 'error_message': "send correct conversation id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'status': False, 'error_message': "incorrect user id"}

        poll_filter = ModelUtilities.get_model_filter(conversationPolls, {'id': poll_id,
                                                                          'conversation': conversation_instance})
        poll_instance = None

        if poll_filter:
            poll_instance = poll_filter[0]

        if not poll_instance:
            return {'status': False, 'error_message': "incorrect poll_id conversation pair"}

        community_instance = conversation_instance.community
        user_list = self._fetch_member_list_for_poll_conversation(conversation_instance, poll_instance,
                                                                  page, page_size)
        member_list = self._create_member_instances_from_user_list(user_list, community_instance)

        return {'status': True, 'members': member_list}

    def _fetch_chatroom_topic_text(self):

        conversation_attachments = answerAttachment.objects.filter(
            answer__id=self.get_conversation_id())\
            .values('type')\
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

        user_instance = User.get_user_or_raise_exception(self.get_member_id())
        conversation_instance = card_answers.get_conversation_or_raise_exception(self.get_conversation_id())
        chatroom_instance = Collabcard.get_chatroom_or_raise_exception(self.get_chatroom_id())

        validation_dict = ConversationHelper.validate_set_topic_request(user_instance, conversation_instance, chatroom_instance)

        if not validation_dict['success']:
            raise CustomException(validation_dict, status_code=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_instance.topic = conversation_instance
        chatroom_instance.save()

        if len(conversation_instance.answer) == 0:
            topic_text = self._fetch_chatroom_topic_text()
        else:
            topic_text = TOPIC_TEXT_NORMAL + conversation_instance.answer

        ConversationHelper.create_answer(chatroom_instance, user_instance,
                                         state=conversation_states.CHATROOM_TOPIC,
                                         topic_text=topic_text)

        ModelUtilities.model_update(collabcardState,
                                    {'card': chatroom_instance},
                                    {'updated_at': TimeUtilities.current_time_in_sec()}
                                    )

        return {'success': True}


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

        if len(tagged_member_list) > 0:
            send_tagged_user_mail.delay(user_instance.id, chatroom_instance.id, tagged_member_list, time_in_hrs=24)

        notification_list = [
            'mail_card_owner_inactivity'
        ]

        # check if sender is not the owner and  notification flag is true
        if check_notification_flag(chatroom_instance.user_id, notification_list, card_id=chatroom_instance.id,
                                   community_id=None) and str(user_instance.id) != str(chatroom_instance.user_id):
            send_chatroom_owner_mail.delay(chatroom_instance.user_id, chatroom_instance.id, time_in_hrs=12)

    @staticmethod
    def update_homefeed_for_all_chatroom_followers(chatroom_id, conversation_id):

        user_list = list(ModelUtilities.get_model_filter(collabcardState, {'card': chatroom_id,
                                                                           'remove': None,
                                                                           'follow_status': True}
                                                         ).values_list('user_id', flat=True))

        for user_id in user_list:
            update_my_chatrooms_on_homefeed_in_firebase(chatroom_id, user_id, conversation_id)

    @staticmethod
    @shared_task
    def update_latest_conversation_id_to_firebase(chatroom_id, conversation_id):
        update_last_answer_id(chatroom_id, conversation_id)
        ConversationHelper.update_homefeed_for_all_chatroom_followers(chatroom_id, conversation_id)

    @staticmethod
    @shared_task
    def update_the_activity_time_for_new_conversation_creation(chatroom_id, user_id):
        activate_chatroom_on_conversation_creation(chatroom_id, user_id)

    @staticmethod
    def compute_member_images_for_homescreen(chatroom_instance, community_instance):

        user_list = get_latest_conversation_creator_users_for_homescreen(chatroom_instance.id, chatroom_instance.id)

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
            card_state_instance.expiry_time = None
            card_state_instance.updated_at = TimeUtilities.current_time_in_sec()
            card_state_instance.save()

    @staticmethod
    def create_answer(chatroom_instance, user_instance, state, topic_text=None, answer=None, current_user_id=None):
        create_chatroom(chatroom_instance, user_instance, state,
                        current_user_id=current_user_id, answer=answer,
                        topic_text=topic_text)

    @staticmethod
    def validate_set_topic_request(user_instance, conversation_instance, chatroom_instance):

        response = {
            "success": True,
        }

        if chatroom_instance.user_id != user_instance.id:
            response['success'] = False
            response['error_message'] = "only chatroom creator can change the topic of chatroom"

        return response

    @staticmethod
    def create_conversation_state(card_instance, user_instance, state, current_user_id=None, answer="", topic_text=None,
                        **kwargs):

        if not kwargs.get('community_instance'):
            community_instance = card_instance.community

        else:
            community_instance = kwargs.get('community_instance')

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
                answer = user_name + " followed this chatroom"

            elif state == conversation_states.CONVERSATION_UNFOLLOW:
                answer = user_name + " unfollowed this chatroom"
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
                    answer = f"{user_name} changed current topic to {topic_text}"

            elif state == conversation_states.CONVERSATION_ADD_ALL_MEMBERS:
                user_route = f"route://member_profile/{user_instance.id}?member_id={user_instance.id}"
                user_name = f"<<{user_name}|{user_route}&community_id={community_id}>>"

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
