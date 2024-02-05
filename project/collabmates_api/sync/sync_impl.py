from rest_framework import status as status_codes

from .sync_manager import SyncManager
from .sync_helper import SyncHelper
from utility.states import (card_types, SyncTypes, conversation_states)
from .constants import (CONVERSATIONS_META_KEY_VALUE, CONVERSATION_POLLS_META_KEY_VALUE, SYNC_CHATROOMS_DATA_KEY,
                        SYNC_CONVERSATIONS_DATA_KEY)
from utility.response_utilities import ResponseUtilities
from utility.number_utilities import NumberUtilities
from togther.models import (Members)

from collabmates_api.raw_queries import (get_home_feed_chatrooms_against_user, get_chatroom_conversations_data,
                                         get_unseen_count_for_chatroom_ids,
                                         get_reactions_for_chatroom_or_conversations, get_attachments_data,
                                         get_conversation_polls_data, get_home_feed_chatrooms_against_non_local_db_user)


class SyncImpl(SyncManager):

    member_id = None
    api_key = None
    request_platform = None
    version_code = None
    device_id = None

    def __init__(self, member_id: str = None, community_id: str = None, api_key: str = None,
                 request_platform: str = None, version_code: int = None, device_id: str = None):
        self.member_id = member_id
        self.community_id = community_id
        self.api_key = api_key
        self.request_platform = request_platform
        self.version_code = version_code
        self.device_id = device_id

    def get_member_id(self) -> str:
        return self.member_id

    def get_community_id(self) -> str:
        return self.community_id

    def get_api_key(self) -> str:
        return self.api_key

    def get_request_platform(self) -> str:
        return self.request_platform

    def get_version_code(self) -> int:
        return self.version_code

    def get_device_id(self) -> str:
        return self.device_id

    def set_community_id(self, community_id) -> None:
        self.community_id = community_id

    def sync_chatrooms(self, page: int = None, page_size: int = None, min_timestamp: int = None,
                       max_timestamp: int = None, chatroom_type: list = None, is_local_db: bool = True,
                       included_conversation_states: list = None, chatroom_id: str = None) -> dict:

        validated_request_body = SyncHelper.validate_sync_chatrooms_request(self.get_member_id(),
                                                                            self.get_community_id(),
                                                                            self.get_api_key(),
                                                                            chatroom_type,
                                                                            min_timestamp,
                                                                            max_timestamp,
                                                                            chatroom_id)

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request_body.get('user_instance')
        community_instance = validated_request_body.get('community_instance')
        self.set_community_id(community_instance.id)

        min_timestamp = validated_request_body.get('min_timestamp')
        max_timestamp = validated_request_body.get('max_timestamp')

        min_timestamp = NumberUtilities.get_integer_from_string(min_timestamp, min_timestamp)

        min_timestamp = SyncHelper.get_min_timestamp_keys_for_sync_in_cache(user_instance.id,
                                                                            self.get_community_id(),
                                                                            min_timestamp)

        included_chatroom_types = [card_types.CARD_NORMAL, card_types.CARD_INTRO, card_types.CARD_EVENT,
                                   card_types.CARD_POLL, card_types.CARD_FEEDBACK, card_types.CARD_HIDDEN,
                                   card_types.CARD_PUBLIC_EVENT, card_types.CARD_PURPOSE, card_types.CARD_MASTER_INTRO]

        if chatroom_type:
            included_chatroom_types = chatroom_type

        if not included_conversation_states:
            included_conversation_states = [
                conversation_states.ANSWER, conversation_states.CONVERSATION_POLL,
                conversation_states.CONVERSATION_HEADER, conversation_states.CHATROOM_DELETE
            ]

        if not is_local_db:
            chatrooms_data, chatroom_ids_list = get_home_feed_chatrooms_against_non_local_db_user(
                user_instance.id, community_instance.id, min_timestamp, max_timestamp, page=page, limit=page_size,
                included_chatroom_types=included_chatroom_types,
                included_conversation_states=included_conversation_states, chatroom_id=chatroom_id)

        else:
            chatrooms_data, chatroom_ids_list = get_home_feed_chatrooms_against_user(
                user_instance.id, community_instance.id, min_timestamp, max_timestamp, page=page, limit=page_size,
                included_chatroom_types=included_chatroom_types, chatroom_id=chatroom_id)

        card_unseen_count_map = None

        if chatroom_ids_list:
            card_unseen_count_map = get_unseen_count_for_chatroom_ids(chatroom_ids_list, user_id=user_instance.id)

        # Chatroom data
        chatrooms_data = SyncHelper.parse_sync_raw_query_response(chatrooms_data, SYNC_CHATROOMS_DATA_KEY,
                                                                  extra_data=card_unseen_count_map)

        # Card Attachments data
        attachments_data = get_attachments_data(chatroom_ids=chatroom_ids_list)
        attachments_data = SyncHelper.parse_sync_raw_query_response(attachments_data, 'card_attachments_meta')
        chatrooms_data = SyncHelper.add_meta_info_to_sync_response(attachments_data, chatrooms_data,
                                                                   'card_attachments_meta', 'collabcard_id')

        # Conversation Attachments, Polls data
        if all([chatrooms_data.get(CONVERSATIONS_META_KEY_VALUE),
                isinstance(chatrooms_data.get(CONVERSATIONS_META_KEY_VALUE), dict)]):
            conversation_ids_list = list(chatrooms_data.get(CONVERSATIONS_META_KEY_VALUE).keys())

            # Conversation attachments data
            attachments_data = get_attachments_data(attachment_type=SyncTypes.CONVERSATION,
                                                    conversation_ids=conversation_ids_list)
            attachments_data = SyncHelper.parse_sync_raw_query_response(attachments_data, 'conv_attachments_meta')
            chatrooms_data = SyncHelper.add_meta_info_to_sync_response(attachments_data, chatrooms_data,
                                                                       'conv_attachments_meta', 'answer_id')

            # Polls data
            polls_data = None

            if conversation_ids_list:
                polls_data = get_conversation_polls_data(self.get_community_id(),
                                                         conversation_ids=conversation_ids_list,
                                                         user_id=user_instance.id)

            polls_data = SyncHelper.parse_sync_raw_query_response(polls_data, 'conv_polls_meta')
            chatrooms_data = SyncHelper.add_meta_info_to_sync_response(polls_data, chatrooms_data,
                                                                       CONVERSATION_POLLS_META_KEY_VALUE,
                                                                       'conversation_id')

            # Add additional poll conversation meta
            is_user_cm = Members.is_member_community_promoter(community_instance, user_instance)
            SyncHelper.add_additional_data_in_conversation_meta(chatrooms_data,
                                                                user_instance.id,
                                                                is_user_cm=is_user_cm)

            SyncHelper.add_additional_data_in_chatroom_meta(chatrooms_data,
                                                            chatroom_data_key=SYNC_CHATROOMS_DATA_KEY)

        return {**{'success': True}, **chatrooms_data}

    def sync_conversations(self, chatroom_id: int = None, page: int = None, page_size: int = None,
                           min_timestamp: int = None, max_timestamp: int = None, is_local_db: bool = True,
                           conversation_id: str = None, excluded_conversation_states: list = None) -> dict:

        validated_request_body = SyncHelper.validate_sync_conversations_request(self.get_member_id(),
                                                                                self.get_community_id(),
                                                                                self.get_api_key(),
                                                                                chatroom_id,
                                                                                min_timestamp,
                                                                                max_timestamp,
                                                                                conversation_id)

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request_body.get('user_instance')
        chatroom_instance = validated_request_body.get('chatroom_instance')
        community_instance = validated_request_body.get('community_instance')
        self.set_community_id(community_instance.id)

        min_timestamp = validated_request_body.get('min_timestamp')
        max_timestamp = validated_request_body.get('max_timestamp')

        conversations_data, conversation_ids_list = get_chatroom_conversations_data(
            user_instance.id, community_instance.id, chatroom_instance.id, min_timestamp, max_timestamp, page=page,
            limit=page_size, is_local_db=is_local_db, conversation_id=conversation_id,
            excluded_conversation_states=excluded_conversation_states)

        # Conversation data
        conversations_data = SyncHelper.parse_sync_raw_query_response(conversations_data, SYNC_CONVERSATIONS_DATA_KEY)

        # Chatroom reactions data
        reactions_data = get_reactions_for_chatroom_or_conversations(self.get_community_id(),
                                                                     chatroom_ids=[chatroom_id])
        reactions_data = SyncHelper.parse_sync_raw_query_response(reactions_data, 'chatroom_reactions_meta')
        conversations_data = SyncHelper.add_meta_info_to_sync_response(reactions_data, conversations_data,
                                                                       'chatroom_reactions_meta', 'chatroom_id')

        # Conversation reactions data
        reactions_data = get_reactions_for_chatroom_or_conversations(self.get_community_id(),
                                                                     reaction_type=SyncTypes.CONVERSATION,
                                                                     conversation_ids=conversation_ids_list)
        reactions_data = SyncHelper.parse_sync_raw_query_response(reactions_data, 'conv_reactions_meta')
        conversations_data = SyncHelper.add_meta_info_to_sync_response(reactions_data,
                                                                       conversations_data,
                                                                       'conv_reactions_meta',
                                                                       'conversation_id')

        # Conversation Attachments data
        attachments_data = get_attachments_data(attachment_type=SyncTypes.CONVERSATION,
                                                conversation_ids=conversation_ids_list)
        attachments_data = SyncHelper.parse_sync_raw_query_response(attachments_data, 'conv_attachments_meta')
        conversations_data = SyncHelper.add_meta_info_to_sync_response(attachments_data, conversations_data,
                                                                       'conv_attachments_meta', 'answer_id')

        # Polls data
        polls_data = None

        if conversation_ids_list:
            polls_data = get_conversation_polls_data(self.get_community_id(),
                                                     conversation_ids=conversation_ids_list,
                                                     user_id=user_instance.id)

        polls_data = SyncHelper.parse_sync_raw_query_response(polls_data, 'conv_polls_meta')
        conversations_data = SyncHelper.add_meta_info_to_sync_response(polls_data, conversations_data,
                                                                       'conv_polls_meta', 'conversation_id')

        # Add additional poll conversation meta
        is_user_cm = Members.is_member_community_promoter(community_instance, user_instance)
        SyncHelper.add_additional_data_in_conversation_meta(conversations_data,
                                                            user_instance.id,
                                                            SYNC_CONVERSATIONS_DATA_KEY,
                                                            is_user_cm)
        
        # Add additional data for conversation_meta conversations
        SyncHelper.add_additional_data_in_conversation_meta(conversations_data,
                                                            user_instance.id,
                                                            CONVERSATIONS_META_KEY_VALUE,
                                                            is_user_cm)
        
        SyncHelper.add_additional_data_in_chatroom_meta(conversations_data)

        return {**{'success': True}, **conversations_data}
