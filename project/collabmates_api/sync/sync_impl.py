from rest_framework import status as status_codes

from .sync_manager import SyncManager
from .sync_helper import SyncHelper
from utility.states import (card_types, SyncTypes, conversation_states, WidgetTypes)
from .constants import (CONVERSATIONS_META_KEY_VALUE, CONVERSATION_POLLS_META_KEY_VALUE, SYNC_CHATROOMS_DATA_KEY,
                        SYNC_CONVERSATIONS_DATA_KEY, SYNC_CHANNEL_DETAILS_DATA_KEY)
from utility.response_utilities import ResponseUtilities
from utility.number_utilities import NumberUtilities
from utility.json_utilities import JsonUtilities
from togther.models import (Members)

from collabmates_api.raw_queries import (get_home_feed_chatrooms_against_user, get_chatroom_conversations_data,
                                         get_unseen_count_for_chatroom_ids,
                                         get_reactions_for_chatroom_or_conversations, get_attachments_data,
                                         get_conversation_polls_data,
                                         get_home_feed_chatrooms_against_non_local_db_user,
                                         get_channel_detail_data, get_cohort_access_corresponding_to_card_ids,
                                         get_event_recordings_attachments_data,
                                         get_event_recordings_url_data, get_chatroom_participants_count)

from collabmates_api.user_moderation_rights import (check_admin_delete_right)
from collabmates_api.utility import (is_community_widget_enabled)


class SyncImpl(SyncManager):

    member_id = None
    api_key = None
    request_platform = None
    version_code = None
    device_id = None

    def __init__(self, member_id: str = None, community_id: str = None, api_key: str = None,
                 request_platform: str = None, version_code: int = None, device_id: str = None,
                 api_version_code: int = 0):
        self.member_id = member_id
        self.community_id = community_id
        self.api_key = api_key
        self.request_platform = request_platform
        self.version_code = version_code
        self.device_id = device_id
        self.api_version_code = api_version_code

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

    def get_api_version_code(self) -> int:
        return self.api_version_code

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

        is_widget_enabled = is_community_widget_enabled(community_instance, WidgetTypes.MESSAGE.value)

        if not is_local_db:
            chatrooms_data, chatroom_ids_list = get_home_feed_chatrooms_against_non_local_db_user(
                user_instance.id, community_instance.id, min_timestamp, max_timestamp, page=page, limit=page_size,
                included_chatroom_types=included_chatroom_types,
                included_conversation_states=included_conversation_states, chatroom_id=chatroom_id,
                is_widget_enabled=is_widget_enabled)

        else:
            chatrooms_data, chatroom_ids_list = get_home_feed_chatrooms_against_user(
                user_instance.id, community_instance.id, min_timestamp, max_timestamp, page=page, limit=page_size,
                included_chatroom_types=included_chatroom_types, chatroom_id=chatroom_id,
                is_widget_enabled=is_widget_enabled)

        card_unseen_count_map = None

        if chatroom_ids_list:
            card_unseen_count_map = get_unseen_count_for_chatroom_ids(chatroom_ids_list, user_id=user_instance.id)

        # Chatroom data
        chatrooms_data = SyncHelper.parse_sync_raw_query_response(chatrooms_data, SYNC_CHATROOMS_DATA_KEY,
                                                                  extra_data=card_unseen_count_map,
                                                                  api_version_code=self.get_api_version_code(),
                                                                  add_sync_meta_dict=True)

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

    def sync_channel_detail(self, channel_id: str, channel_action_types: list):
        validated_request_body = SyncHelper.validate_sync_channel_detail_request(self.get_member_id(),
                                                                                 self.get_api_key(),
                                                                                 channel_id)

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request_body.get('user_instance')
        chatroom_instance = validated_request_body.get('chatroom_instance')
        state_instance = validated_request_body.get('state_instance')
        member_instance = validated_request_body.get('member_instance')

        self.set_community_id(chatroom_instance.community_id)

        secret_chatroom_participants = None
        is_secret_chatroom = chatroom_instance.is_secret

        if is_secret_chatroom:
            secret_chatroom_participants = JsonUtilities.load_json_data(chatroom_instance.secret_chatroom_participants)

        chatroom_detail_data = get_channel_detail_data(user_instance.id, self.get_community_id(), channel_id,
                                                       is_secret_chatroom=is_secret_chatroom,
                                                       secret_chatroom_participants_list=secret_chatroom_participants)

        intro_room_placeholder = ""

        if all([chatroom_instance.type == card_types.CARD_INTRO,
                chatroom_instance.user_id != self.get_member_id(),
                not state_instance.last_seen_conversation_id]):
            from collabmates_api.chatroom.chatroom_impl import ChatroomHelper

            intro_room_placeholder = ChatroomHelper.create_placeholder_for_introduction_card(
                chatroom_instance.community, chatroom_instance.user.userinfo)

        participants_count = get_chatroom_participants_count(channel_id, self.get_community_id())

        extra_data = {
            chatroom_instance.id: {
                'cohort_access': None,
                'placeholder': intro_room_placeholder,
                'participant_count': participants_count
            }
        }

        # Add cohort access data
        chatroom_cohort_access_dict = get_cohort_access_corresponding_to_card_ids(user_id=user_instance.id,
                                                                                  chatroom_ids=[channel_id])

        if chatroom_instance.id in chatroom_cohort_access_dict:
            extra_data[chatroom_instance.id].update(chatroom_cohort_access_dict.get(chatroom_instance.id))

        chatroom_detail_data = SyncHelper.parse_sync_raw_query_response(chatroom_detail_data,
                                                                        SYNC_CHANNEL_DETAILS_DATA_KEY,
                                                                        extra_data=extra_data)

        chatroom_detail_data['event_rec_attach_meta'] = {}
        chatroom_detail_data['event_rec_url_meta'] = {}

        if chatroom_instance.type in [card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
            event_rec_attach_data = get_event_recordings_attachments_data(
                chatroom_ids=[chatroom_instance.id])

            event_rec_attach_data = SyncHelper.parse_sync_raw_query_response(
                event_rec_attach_data, 'event_rec_attach_meta')

            chatroom_detail_data = SyncHelper.add_meta_info_to_sync_response(event_rec_attach_data,
                                                                             chatroom_detail_data,
                                                                             'event_rec_attach_meta',
                                                                             'chatroom_id')

            event_recordings_url_data = get_event_recordings_url_data(
                chatroom_ids=[channel_id])

            event_recordings_url_data = SyncHelper.parse_sync_raw_query_response(
                event_recordings_url_data, 'event_rec_url_meta')

            chatroom_detail_data = SyncHelper.add_meta_info_to_sync_response(event_recordings_url_data,
                                                                             chatroom_detail_data,
                                                                             'event_rec_url_meta',
                                                                             'chatroom_id_id')

        channel_actions = {}

        if channel_action_types:
            is_channel_creator = chatroom_instance.user_id == user_instance.id
            is_dm_chat_requester = state_instance.chat_requested_by_id == user_instance.id
            is_secret_chatroom_participant = user_instance.id in secret_chatroom_participants if \
                secret_chatroom_participants else False
            is_chatroom_delete_right = check_admin_delete_right(user_instance.id, self.get_community_id())

            channel_actions = SyncHelper.compute_channel_actions_for_user(
                channel_id=chatroom_instance.id, channel_action_types=channel_action_types,
                is_channel_creator=is_channel_creator, channel_type=chatroom_instance.type,
                is_channel_muted=state_instance.mute_status, dm_chat_request_state=state_instance.chat_request_state,
                is_dm_chat_requester=is_dm_chat_requester, is_channel_followed=state_instance.follow_status,
                is_secret_channel=chatroom_instance.is_secret,
                is_secret_chatroom_participant=is_secret_chatroom_participant, member_state=member_instance.state,
                is_chatroom_delete_right=is_chatroom_delete_right)

        chatroom_detail_data['channel_actions'] = channel_actions

        return {**{'success': True}, **chatroom_detail_data}

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

        is_widget_enabled = is_community_widget_enabled(community_instance, WidgetTypes.MESSAGE.value)

        conversations_data, conversation_ids_list = get_chatroom_conversations_data(
            user_instance.id, community_instance.id, chatroom_instance.id, min_timestamp, max_timestamp, page=page,
            limit=page_size, is_local_db=is_local_db, conversation_id=conversation_id,
            excluded_conversation_states=excluded_conversation_states, is_widget_enabled=is_widget_enabled)

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
