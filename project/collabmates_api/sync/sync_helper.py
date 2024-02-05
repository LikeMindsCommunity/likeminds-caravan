from utility.response_utilities import ResponseUtilities
from utility.validation_utilities import ValidationUtilities
from utility.json_utilities import JsonUtilities
from utility.time_utilities import TimeUtilities
from utility.number_utilities import NumberUtilities
from utility.cache_keys import (SYNC_LJ_MIN_TIMESTAMP)
from external_services.caching.cache_impl import CacheImpl
from .constants import (SYNC_KEY_SPLIT_VALUE, IGNORED_KEYS_LIST, META_KEYS_SUFFIX, SYNC_RESPONSE_MAP_PRIMARY_KEYS,
                        USERS_META_KEY_VALUE, MEMBERS_META_KEY_VALUE, MAIN_PRIMARY_KEY_VALUE,
                        CONVERSATIONS_META_KEY_VALUE, SYNC_DATA_KEYS, COMMUNITY_META_KEY_VALUE,
                        CHATROOM_META_KEY_VALUE, PARSE_JSON_KEYS_WITH_DEFAULT_VALUE, MESSAGE_REACTIONS_META_KEY_VALUE,
                        CONVERSATION_STATE_KEY_VALUE, POLL_CONVERSATION_TO_SHOW_RESULTS_KEY,
                        CONVERSATION_POLLS_META_KEY_VALUE, CONVERSATIONS_DATE_KEY, CHATROOM_STATE_META_KEY_VALUE,
                        CONVERSATIONS_CREATED_EPOCH_KEY, CONVERSATIONS_CREATED_AT_KEY, CONVERSATION_POLL_TYPE_TEXT_KEY,
                        INSTANT_POLL_NAME_VALUE, DEFERRED_POLL_NAME_VALUE, SECRET_VOTING_NAME_VALUE,
                        PUBLIC_VOTING_NAME_VALUE, CONVERSATION_SUBMIT_TYPE_TEXT_KEY, CHATROOM_DATE_KEY,
                        CHATROOM_DATE_EPOCH_KEY, SDK_CLIENT_META_KEY_VALUE, SDK_CLIENT_INFO_KEY_VALUE,
                        SYNC_META_DICT_KEYS, SYNC_META_KEY_VALUE)
from utility.states import (conversation_states, conversation_poll_types, APIVersionCodes, ChannelActionTypes,
                            card_types, chat_request_states, MemberRoles)
from utility.constants import (LITTLE_JOYS_ID)
from togther.models import (ModelUtilities, card_answers, Collabcard, collabcardState, Members)
from collabmates_api.static_text import (unMute_notifications, mute_notifications, view_profile, block_member_chatroom,
                                         unblock_member, rename_chatroom, view_participants, join_chatroom,
                                         unfollow_chatroom, leave_chatroom, invite, share_chatroom_link,
                                         delete_chatroom, report, add_all_members, chatroom_settings)


class SyncHelper:

    @staticmethod
    def validate_sync_chatrooms_request(user_id, community_id, api_key: str = None, chatroom_type: list = None,
                                        min_timestamp: int = None, max_timestamp: int = None, chatroom_id: str = None):

        if chatroom_id:
            chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

            if not chatroom_instance:
                return ResponseUtilities.get_inner_error_context('Invalid chatroom ID!')

        validation_params = {
            'community_id': {
                'community_id': community_id,
                'api_key': api_key
            },
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        if chatroom_type and not isinstance(chatroom_type, list):
            return ResponseUtilities.get_inner_error_context('Invalid chatroom types!')

        if not max_timestamp:
            max_timestamp = TimeUtilities.current_time_in_sec()

        if not min_timestamp:
            min_timestamp = 0

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'max_timestamp': max_timestamp,
            'min_timestamp': min_timestamp
        }

    @staticmethod
    def validate_sync_channel_detail_request(user_id, api_key: str = None, chatroom_id: str = None):
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id,
            'chatroom_id': chatroom_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')
        chatroom_instance = validated_dict.get('chatroom_id')

        if community_instance.id != chatroom_instance.community_id:
            return ResponseUtilities.get_inner_error_context('Chatroom doesn\'t belongs to the community!')

        member_instance = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                    'member_id': user_instance}).first()

        if not member_instance:
            return ResponseUtilities.get_inner_error_context('You are not part of community!')

        state_instance = ModelUtilities.get_model_filter(collabcardState, {'user': user_instance,
                                                                           'card': chatroom_instance}).first()

        if not state_instance:
            return ResponseUtilities.get_inner_error_context('No chatroom data exists!')

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'chatroom_instance': chatroom_instance,
            'state_instance': state_instance,
            'member_instance': member_instance
        }

    @staticmethod
    def validate_sync_conversations_request(user_id, community_id, api_key: str = None, chatroom_id: int = None,
                                            min_timestamp: int = None, max_timestamp: int = None,
                                            conversation_id: str = None):
        validation_params = {
            'community_id': {
                'community_id': community_id,
                'api_key': api_key
            },
            'user_id': user_id,
            'chatroom_id': chatroom_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        if not max_timestamp:
            max_timestamp = TimeUtilities.current_time_in_sec()

        else:
            max_timestamp = NumberUtilities.get_integer_from_string(max_timestamp, TimeUtilities.current_time_in_sec())

        if not min_timestamp:
            min_timestamp = 0

        else:
            min_timestamp = NumberUtilities.get_integer_from_string(min_timestamp, return_default=0)

        if conversation_id:
            conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

            if not conversation_instance:
                return ResponseUtilities.get_inner_error_context("Invalid conversation ID!")

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')
        chatroom_instance = validated_dict.get('chatroom_id')

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'chatroom_instance': chatroom_instance,
            'max_timestamp': max_timestamp,
            'min_timestamp': min_timestamp
        }

    @staticmethod
    def merge_meta_data(primary_data: dict, secondary_data: dict = None, primary_key: str = MAIN_PRIMARY_KEY_VALUE,
                        secondary_key: str = None, extra_key: str = None, extra_data: dict = None):
        merged_meta_data = {}

        if not primary_data:
            return merged_meta_data

        if isinstance(list(primary_data.values())[0], dict):

            for key, data in primary_data.items():

                if data.get(primary_key):
                    merged_meta_data[data.get(primary_key)] = data

        else:

            if primary_data.get(primary_key):
                merged_meta_data[primary_data.get(primary_key)] = primary_data

        if secondary_data:
            primary_data = secondary_data
            secondary_key = primary_key if not secondary_key else secondary_key

            if isinstance(list(primary_data.values())[0], dict):

                for key, data in primary_data.items():

                    if data.get(secondary_key):
                        merged_meta_data[data.get(secondary_key)].update(data)

            else:

                if primary_data.get(secondary_key):
                    merged_meta_data[primary_data.get(secondary_key)].update(primary_data)

        # Only for adding sdk_client_info to users_meta
        if extra_data and extra_key == SDK_CLIENT_META_KEY_VALUE:
            
            for key, data in extra_data.items():
                
                if data.get(primary_key):
                    merged_meta_data[data.get(primary_key)][SDK_CLIENT_INFO_KEY_VALUE] = data
                    
        return merged_meta_data

    @staticmethod
    def combine_and_convert_dicts_to_sync_meta_data(data, resulting_dict, primary_key, secondary_key: str = None,
                                                    resulting_primary_key: str = MAIN_PRIMARY_KEY_VALUE,
                                                    secondary_data_merging_key: str = None, extra_key: str = None):
        filter_dict = {
            'primary_data': data.get(primary_key, {}),
            'primary_key': resulting_primary_key,
            'secondary_key': secondary_data_merging_key
        }

        if secondary_key:
            filter_dict['secondary_data'] = data.get(secondary_key, {})

        if extra_key:
            filter_dict['extra_key'] = extra_key
            filter_dict['extra_data'] = data.get(extra_key, {})

        if data.get(primary_key, {}):
            meta_data = SyncHelper.merge_meta_data(**filter_dict)

            if not resulting_dict.get(primary_key):
                resulting_dict[primary_key] = meta_data

            else:
                resulting_dict[primary_key] = {**resulting_dict[primary_key], **meta_data}

        return resulting_dict

    @staticmethod
    def parse_sync_raw_query_response(data, sync_data_key: str, extra_data: dict = None, api_version_code: int = 0,
                                      add_sync_meta_dict: bool = False):

        parsed_data = list()
        sync_response = dict()
        sync_meta_dict = dict()

        if not data:
            sync_response[sync_data_key] = parsed_data
            return sync_response

        for sync_data in data:
            parsed_sync_data = dict()
            parsed_meta_data = dict()
            removed_keys_list = list()

            for key in sync_data:

                if key in IGNORED_KEYS_LIST:
                    continue

                if key in list(SYNC_DATA_KEYS.keys()):
                    parsed_sync_data[SYNC_DATA_KEYS[key]] = sync_data.get(key)

                if key in ['updated_at']:
                    sync_data[key] = TimeUtilities.convert_milliseconds_to_sec(sync_data[key])

                if key in list(PARSE_JSON_KEYS_WITH_DEFAULT_VALUE.keys()):

                    if sync_data[key]:
                        sync_data[key] = JsonUtilities.load_json_data(sync_data[key], default=[])

                    else:
                        sync_data[key] = PARSE_JSON_KEYS_WITH_DEFAULT_VALUE.get(key)

                chatroom_data_keys = key.split(SYNC_KEY_SPLIT_VALUE)

                if len(chatroom_data_keys) == 3:

                    if chatroom_data_keys[1] in SYNC_RESPONSE_MAP_PRIMARY_KEYS:
                        chatroom_data_keys[1] = MAIN_PRIMARY_KEY_VALUE

                    if chatroom_data_keys[2] in removed_keys_list and \
                          not chatroom_data_keys[0] == SDK_CLIENT_INFO_KEY_VALUE:
                        continue

                    if all([chatroom_data_keys[1] in SYNC_RESPONSE_MAP_PRIMARY_KEYS,
                            not sync_data[key]]):
                        removed_keys_list.append(chatroom_data_keys[2])
                        continue

                    meta_key = "".join([chatroom_data_keys[0], META_KEYS_SUFFIX])

                    if parsed_meta_data.get(meta_key):

                        if parsed_meta_data[meta_key].get(chatroom_data_keys[2]):
                            parsed_meta_data[meta_key][chatroom_data_keys[2]][chatroom_data_keys[1]] = sync_data[key]

                        else:
                            parsed_meta_data[meta_key][chatroom_data_keys[2]] = {
                                chatroom_data_keys[1]: sync_data[key]
                            }

                    else:
                        parsed_meta_data[meta_key] = {
                            chatroom_data_keys[2]: {
                                chatroom_data_keys[1]: sync_data[key]
                            }
                        }

                elif len(chatroom_data_keys) == 2:
                    meta_key = "".join([chatroom_data_keys[0], META_KEYS_SUFFIX])

                    if parsed_meta_data.get(meta_key):
                        parsed_meta_data[meta_key][chatroom_data_keys[1]] = sync_data[key]

                    else:
                        parsed_meta_data[meta_key] = {
                            chatroom_data_keys[1]: sync_data[key]
                        }

                else:
                    parsed_sync_data[key] = sync_data[key]

            if extra_data and isinstance(extra_data, dict):
                parsed_sync_data.update(extra_data.get(parsed_sync_data.get('id')))

            if all([add_sync_meta_dict, api_version_code >= APIVersionCodes.V1.value,
                    set(parsed_sync_data.keys()).intersection(SYNC_META_DICT_KEYS)]):

                for sync_meta_key in SYNC_META_DICT_KEYS:

                    if parsed_sync_data.get('id') in sync_meta_dict:
                        sync_meta_dict[parsed_sync_data.get('id')][sync_meta_key] = parsed_sync_data[sync_meta_key]

                    else:
                        sync_meta_dict[parsed_sync_data.get('id')] = {
                            sync_meta_key: parsed_sync_data[sync_meta_key]
                        }

                    del parsed_sync_data[sync_meta_key]

            parsed_data.append(parsed_sync_data)

            sync_response = SyncHelper.combine_and_convert_dicts_to_sync_meta_data(parsed_meta_data,
                                                                                   sync_response,
                                                                                   primary_key=USERS_META_KEY_VALUE,
                                                                                   secondary_key=MEMBERS_META_KEY_VALUE,
                                                                                   extra_key=SDK_CLIENT_META_KEY_VALUE)

            sync_response = SyncHelper.combine_and_convert_dicts_to_sync_meta_data(
                parsed_meta_data, sync_response, primary_key=CONVERSATIONS_META_KEY_VALUE)

            sync_response = SyncHelper.combine_and_convert_dicts_to_sync_meta_data(
                parsed_meta_data, sync_response, primary_key=COMMUNITY_META_KEY_VALUE)

            sync_response = SyncHelper.combine_and_convert_dicts_to_sync_meta_data(
                parsed_meta_data, sync_response, primary_key=CHATROOM_META_KEY_VALUE)

            sync_response = SyncHelper.combine_and_convert_dicts_to_sync_meta_data(
                parsed_meta_data, sync_response, primary_key=MESSAGE_REACTIONS_META_KEY_VALUE)

            sync_response = SyncHelper.combine_and_convert_dicts_to_sync_meta_data(
                parsed_meta_data, sync_response, primary_key=CHATROOM_META_KEY_VALUE,
                secondary_key=CHATROOM_STATE_META_KEY_VALUE, secondary_data_merging_key='card_id')

        sync_response[sync_data_key] = parsed_data

        if add_sync_meta_dict:
            sync_response[SYNC_META_KEY_VALUE] = sync_meta_dict

        return sync_response

    @staticmethod
    def add_meta_info_to_sync_response(meta_data, sync_data, main_data_key: str, merge_key: str):
        main_data = meta_data.get(main_data_key)
        main_data_dict = {}

        if main_data and isinstance(main_data, list):

            for data in main_data:

                if not data.get(merge_key):
                    continue

                if main_data_dict.get(data.get(merge_key)):
                    main_data_dict.get(data.get(merge_key)).append(data)

                else:
                    main_data_dict[data.get(merge_key)] = [data]

        sync_data[main_data_key] = main_data_dict

        # Add users meta data
        sync_data = SyncHelper.combine_and_convert_dicts_to_sync_meta_data(meta_data, sync_data,
                                                                           primary_key=USERS_META_KEY_VALUE)

        return sync_data

    @staticmethod
    def compute_show_poll_results_for_conversation_meta(conv_data: dict, user_id: int, is_user_cm: bool = None,
                                                        conv_polls_data: list = None):
        to_show_results = False

        if conv_data.get(CONVERSATION_STATE_KEY_VALUE) != conversation_states.CONVERSATION_POLL:
            return to_show_results

        elif is_user_cm:
            to_show_results = True

        elif conv_data.get('user_id') == user_id:
            to_show_results = True

        elif not conv_data.get('expiry_time'):
            to_show_results = True

        elif conv_data.get('expiry_time') <= TimeUtilities.current_time_in_milliseconds():
            to_show_results = True

        elif conv_data.get('poll_type') == conversation_poll_types.INSTANT and conv_polls_data:

            for poll_selection_data in conv_polls_data:

                if poll_selection_data.get('is_selected'):
                    return True

        return to_show_results

    @staticmethod
    def compute_poll_type_text_for_conversation_meta(conv_data: dict):
        if conv_data.get(CONVERSATION_STATE_KEY_VALUE) != conversation_states.CONVERSATION_POLL:
            return None

        if conv_data.get('poll_type') == conversation_poll_types.INSTANT:
            return INSTANT_POLL_NAME_VALUE

        else:
            return DEFERRED_POLL_NAME_VALUE

    @staticmethod
    def compute_submit_type_text_for_conversation_meta(conv_data: dict):
        if conv_data.get(CONVERSATION_STATE_KEY_VALUE) != conversation_states.CONVERSATION_POLL:
            return None

        if conv_data.get('is_anonymous'):
            return SECRET_VOTING_NAME_VALUE

        else:
            return PUBLIC_VOTING_NAME_VALUE

    @staticmethod
    def compute_conversation_additional_data(conversation_data, user_id: int, is_user_cm: bool = False,
                                             conv_polls_data: list = None):

        if not conv_polls_data:
            conv_polls_data = {}

        conversation_data[POLL_CONVERSATION_TO_SHOW_RESULTS_KEY] = \
            SyncHelper.compute_show_poll_results_for_conversation_meta(
                conversation_data, user_id, is_user_cm, conv_polls_data)

        conversation_data[CONVERSATION_POLL_TYPE_TEXT_KEY] = SyncHelper.compute_poll_type_text_for_conversation_meta(
            conversation_data)

        conversation_data[CONVERSATION_SUBMIT_TYPE_TEXT_KEY] = \
            SyncHelper.compute_submit_type_text_for_conversation_meta(conversation_data)

        if conversation_data.get(CONVERSATIONS_CREATED_AT_KEY):
            conversation_data[CONVERSATIONS_CREATED_EPOCH_KEY] = conversation_data.get(CONVERSATIONS_CREATED_AT_KEY)

            conversation_data[CONVERSATIONS_DATE_KEY] = TimeUtilities.convert_epoch_time_in_date(
                conversation_data.get(CONVERSATIONS_CREATED_AT_KEY))

            conversation_data[CONVERSATIONS_CREATED_AT_KEY] = TimeUtilities.convert_epoch_time_in_hh_mm(
                conversation_data.get(CONVERSATIONS_CREATED_AT_KEY))

        if len(set(PARSE_JSON_KEYS_WITH_DEFAULT_VALUE.keys()).intersection(set(conversation_data.keys()))):

            for data_key in list(set(PARSE_JSON_KEYS_WITH_DEFAULT_VALUE.keys()
                                     ).intersection(set(conversation_data.keys()))):

                if isinstance(conversation_data[data_key], str):
                    conversation_data[data_key] = JsonUtilities.load_json_data(conversation_data[data_key],
                                                                               default=None)

    @staticmethod
    def add_additional_data_in_conversation_meta(sync_data,
                                                 user_id: int,
                                                 conversation_data_key: str = CONVERSATIONS_META_KEY_VALUE,
                                                 is_user_cm: bool = False):
        conversations_data = sync_data.get(conversation_data_key)
        conv_polls_data = sync_data.get(CONVERSATION_POLLS_META_KEY_VALUE)

        if isinstance(conversations_data, dict):
            conversations_data_list = list(conversations_data.values())

        elif isinstance(conversations_data, list):
            conversations_data_list = conversations_data

        else:
            return

        for conversation_data in conversations_data_list:
            SyncHelper.compute_conversation_additional_data(conversation_data,
                                                            user_id,
                                                            is_user_cm,
                                                            conv_polls_data.get(conversation_data.get('id')))

    @staticmethod
    def compute_chatroom_additional_data(chatroom_data):

        if chatroom_data.get(CHATROOM_DATE_EPOCH_KEY):
            chatroom_data[CHATROOM_DATE_KEY] = TimeUtilities.convert_epoch_time_in_date(
                chatroom_data.get(CHATROOM_DATE_EPOCH_KEY))

        if len(set(PARSE_JSON_KEYS_WITH_DEFAULT_VALUE.keys()).intersection(set(chatroom_data.keys()))):

            for data_key in list(set(PARSE_JSON_KEYS_WITH_DEFAULT_VALUE.keys()
                                     ).intersection(set(chatroom_data.keys()))):

                if isinstance(chatroom_data[data_key], str):
                    chatroom_data[data_key] = JsonUtilities.load_json_data(chatroom_data[data_key], default=None)

    @staticmethod
    def add_additional_data_in_chatroom_meta(sync_data,
                                             chatroom_data_key: str = CHATROOM_META_KEY_VALUE):
        chatroom_data = sync_data.get(chatroom_data_key)

        if isinstance(chatroom_data, dict):
            chatroom_data_list = list(chatroom_data.values())

        elif isinstance(chatroom_data, list):
            chatroom_data_list = chatroom_data

        else:
            return

        for chatroom_data in chatroom_data_list:
            SyncHelper.compute_chatroom_additional_data(chatroom_data)

    @staticmethod
    def update_min_timestamp_keys_for_sync_in_cache(user_id, community_id, min_timestamp: int = 0):

        if community_id != LITTLE_JOYS_ID:
            return

        key = SYNC_LJ_MIN_TIMESTAMP.format(community_id, user_id)
        min_timestamp_cache_data = CacheImpl.get_cache(key)

        if not min_timestamp_cache_data:
            cache_data = {
                'current_min': 0
            }

        else:
            current_min = min_timestamp_cache_data.get('current_min')

            if current_min >= min_timestamp:
                return

            cache_data = {
                'current_min': min_timestamp
            }

        CacheImpl.set_cache(key, cache_data)

    @staticmethod
    def get_min_timestamp_keys_for_sync_in_cache(user_id, community_id, min_timestamp: int = 0):

        if community_id != LITTLE_JOYS_ID:
            return min_timestamp

        key = SYNC_LJ_MIN_TIMESTAMP.format(community_id, user_id)
        min_timestamp_cache_data = CacheImpl.get_cache(key)

        updated_min_timestamp = min_timestamp
        needs_updation = True

        if min_timestamp_cache_data:
            current_min = min_timestamp_cache_data.get('current_min')

            if current_min == 0 and (current_min < min_timestamp):
                needs_updation = True
                updated_min_timestamp = current_min

            else:
                needs_updation = False

        if needs_updation:
            SyncHelper.update_min_timestamp_keys_for_sync_in_cache(user_id, community_id, min_timestamp)

        return updated_min_timestamp

    @staticmethod
    def compute_channel_actions_for_user(channel_id: int, channel_action_types: list, is_channel_creator: bool,
                                         channel_type: int, is_channel_muted: bool, dm_chat_request_state: int,
                                         is_dm_chat_requester: bool, is_channel_followed: bool,
                                         is_secret_channel: bool, is_secret_chatroom_participant: bool,
                                         member_state: int, is_chatroom_delete_right: bool) -> dict:
        channel_actions = list()

        if not channel_action_types:
            return {}

        for channel_action_type in channel_action_types:

            if channel_action_type == ChannelActionTypes.MUTE_UNMUTE.value:

                if any([not is_channel_followed,
                        is_channel_creator and (channel_type == card_types.CARD_INTRO)]):
                    continue

                elif is_channel_muted:
                    channel_actions.append(unMute_notifications)

                else:
                    channel_actions.append(mute_notifications)

            elif channel_action_type == ChannelActionTypes.VIEW_PROFILE.value:

                if channel_type != card_types.CARD_DIRECT_MESSAGE:
                    continue

                channel_actions.append(view_profile)

            elif channel_action_type == ChannelActionTypes.BLOCK_UNBLOCK_MEMBER.value:

                if any([channel_type != card_types.CARD_DIRECT_MESSAGE,
                        dm_chat_request_state not in [chat_request_states.ACCEPTED, chat_request_states.REJECTED]]):
                    continue

                elif dm_chat_request_state != chat_request_states.REJECTED:
                    channel_actions.append(block_member_chatroom)

                elif all([dm_chat_request_state == chat_request_states.REJECTED,
                          is_dm_chat_requester]):
                    channel_actions.append(unblock_member)

                else:
                    continue

            elif channel_action_type == ChannelActionTypes.VIEW_PARTICIPANTS.value:

                if channel_type == card_types.CARD_DIRECT_MESSAGE:
                    continue

                channel_actions.append(view_participants)

            elif channel_action_type == ChannelActionTypes.INVITE_MEMBER.value:

                if any([channel_type in [card_types.CARD_PURPOSE, card_types.CARD_MASTER_INTRO,
                                         card_types.CARD_DIRECT_MESSAGE],
                        is_secret_channel]):
                    continue

                channel_actions.append(invite)

            elif channel_action_type == ChannelActionTypes.JOIN_CHANNEL.value:

                if any([is_channel_followed, is_secret_channel,
                        channel_type in [card_types.CARD_PURPOSE, card_types.CARD_MASTER_INTRO,
                                         card_types.CARD_DIRECT_MESSAGE],
                        is_channel_creator and channel_type == card_types.CARD_INTRO]):
                    continue

                channel_actions.append(join_chatroom)

            elif channel_action_type == ChannelActionTypes.LEAVE_CHANNEL.value:

                if any([not is_channel_followed,
                        channel_type in [card_types.CARD_PURPOSE, card_types.CARD_MASTER_INTRO,
                                         card_types.CARD_DIRECT_MESSAGE]]):
                    continue

                if not is_secret_channel:

                    if all([is_channel_creator, channel_type == card_types.CARD_INTRO]):
                        continue

                    else:
                        channel_actions.append(unfollow_chatroom)

                elif all([is_secret_channel, is_secret_chatroom_participant]):
                    channel_actions.append(leave_chatroom)

                else:
                    continue

            elif channel_action_type == ChannelActionTypes.SHARE.value:

                if any([channel_type in [card_types.CARD_PURPOSE, card_types.CARD_MASTER_INTRO,
                                         card_types.CARD_DIRECT_MESSAGE],
                        is_secret_channel]):
                    continue

                channel_actions.append(share_chatroom_link)

            elif channel_action_type == ChannelActionTypes.REPORT_SPAM_ABUSE.value:

                if any([is_channel_creator,
                        all([member_state == MemberRoles.ADMIN.value,
                             not is_channel_creator,
                             not is_chatroom_delete_right]),
                        all([is_secret_channel, not is_secret_chatroom_participant]),
                        channel_type == card_types.CARD_DIRECT_MESSAGE]):
                    continue

                channel_actions.append(report)

            elif channel_action_type == ChannelActionTypes.ADD_ALL_MEMBERS.value:

                if any([member_state != MemberRoles.ADMIN.value, is_secret_channel, not len(channel_actions),
                        channel_type == card_types.CARD_DIRECT_MESSAGE]):
                    continue

                channel_actions.append(add_all_members)

            elif channel_action_type == ChannelActionTypes.CHANNEL_SETTINGS.value:

                if any([[member_state != MemberRoles.ADMIN.value, is_secret_channel,
                         channel_type in [card_types.CARD_MASTER_INTRO, card_types.CARD_DIRECT_MESSAGE]]]):
                    continue

                channel_actions.append(chatroom_settings)

        if not channel_actions:
            return {}

        return {channel_id: channel_actions}
