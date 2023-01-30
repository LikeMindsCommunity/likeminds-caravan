from rest_framework import status as status_codes

from .sync_manager import SyncManager
from .sync_helper import SyncHelper
from utility.states import (card_types)
from utility.response_utilities import ResponseUtilities

from collabmates_api.raw_queries import (get_home_feed_chatrooms_against_user, get_chatroom_conversations_data,
                                         get_unseen_count_for_chatroom_ids)


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

    def sync_chatrooms(self, page: int = None, page_size: int = None, min_timestamp: int = None,
                       max_timestamp: int = None, chatroom_type: list = None) -> dict:

        validated_request_body = SyncHelper.validate_sync_chatrooms_request(self.get_member_id(),
                                                                            self.get_community_id(),
                                                                            self.get_api_key(),
                                                                            chatroom_type,
                                                                            min_timestamp,
                                                                            max_timestamp)

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request_body.get('user_instance')
        community_instance = validated_request_body.get('community_instance')

        included_chatroom_types = [card_types.CARD_NORMAL, card_types.CARD_INTRO, card_types.CARD_EVENT,
                                   card_types.CARD_POLL, card_types.CARD_FEEDBACK, card_types.CARD_HIDDEN,
                                   card_types.CARD_PUBLIC_EVENT, card_types.CARD_PURPOSE, card_types.CARD_MASTER_INTRO]

        if chatroom_type:
            included_chatroom_types = chatroom_type

        chatrooms_data, chatroom_ids_list = get_home_feed_chatrooms_against_user(
            user_instance.id, community_instance.id, min_timestamp, max_timestamp, page=page, limit=page_size,
            included_chatroom_types=included_chatroom_types)

        card_unseen_count_map = get_unseen_count_for_chatroom_ids(chatroom_ids_list, user_id=user_instance.id)

        chatrooms_data = SyncHelper.parse_sync_raw_query_response(chatrooms_data, 'chatrooms_data',
                                                                  extra_data=card_unseen_count_map)

        return {**{'success': True}, **chatrooms_data}

    def sync_conversations(self, chatroom_id: int = None, page: int = None, page_size: int = None,
                           min_timestamp: int = None, max_timestamp: int = None) -> dict:

        validated_request_body = SyncHelper.validate_sync_conversations_request(self.get_member_id(),
                                                                                self.get_community_id(),
                                                                                self.get_api_key(),
                                                                                chatroom_id,
                                                                                min_timestamp,
                                                                                max_timestamp)

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        chatroom_instance = validated_request_body.get('chatroom_instance')
        community_instance = validated_request_body.get('community_instance')

        conversations_data = get_chatroom_conversations_data(community_instance.id, chatroom_instance.id, min_timestamp,
                                                             max_timestamp, page=page, limit=page_size)

        conversations_data = SyncHelper.parse_sync_raw_query_response(conversations_data, 'conversations_data')

        return {**{'success': True}, **conversations_data}
