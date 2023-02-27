from utility.response_utilities import ResponseUtilities
from utility.validation_utilities import ValidationUtilities
from utility.json_utilities import JsonUtilities
from utility.time_utilities import TimeUtilities
from utility.number_utilities import NumberUtilities
from .constants import (SYNC_KEY_SPLIT_VALUE, IGNORED_KEYS_LIST, META_KEYS_SUFFIX, SYNC_RESPONSE_MAP_PRIMARY_KEYS,
                        USERS_META_KEY_VALUE, MEMBERS_META_KEY_VALUE, MAIN_PRIMARY_KEY_VALUE,
                        CONVERSATIONS_META_KEY_VALUE, SYNC_DATA_KEYS, COMMUNITY_META_KEY_VALUE,
                        CHATROOM_META_KEY_VALUE, PARSE_JSON_KEYS_WITH_DEFAULT_VALUE, MESSAGE_REACTIONS_META_KEY_VALUE,
                        CONVERSATION_STATE_KEY_VALUE, POLL_CONVERSATION_TO_SHOW_RESULTS_KEY,
                        CONVERSATION_POLLS_META_KEY_VALUE, CONVERSATIONS_DATE_KEY, CHATROOM_STATE_META_KEY_VALUE,
                        CONVERSATIONS_CREATED_EPOCH_KEY, CONVERSATIONS_CREATED_AT_KEY, CONVERSATION_POLL_TYPE_TEXT_KEY,
                        INSTANT_POLL_NAME_VALUE, DEFERRED_POLL_NAME_VALUE, SECRET_VOTING_NAME_VALUE,
                        PUBLIC_VOTING_NAME_VALUE, CONVERSATION_SUBMIT_TYPE_TEXT_KEY, CHATROOM_DATE_KEY,
                        CHATROOM_DATE_EPOCH_KEY)
from utility.states import (conversation_states, conversation_poll_types)


class SyncHelper:

    @staticmethod
    def validate_sync_chatrooms_request(user_id, community_id, api_key: str = None, chatroom_type: list = None,
                                        min_timestamp: int = None, max_timestamp: int = None):
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
    def validate_sync_conversations_request(user_id, community_id, api_key: str = None, chatroom_id: int = None,
                                            min_timestamp: int = None, max_timestamp: int = None):
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
                        secondary_key: str = None):
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

        if not secondary_data:
            return merged_meta_data

        primary_data = secondary_data
        secondary_key = primary_key if not secondary_key else secondary_key

        if isinstance(list(primary_data.values())[0], dict):

            for key, data in primary_data.items():

                if data.get(secondary_key):
                    merged_meta_data[data.get(secondary_key)].update(data)

        else:

            if primary_data.get(secondary_key):
                merged_meta_data[primary_data.get(secondary_key)].update(primary_data)

        return merged_meta_data

    @staticmethod
    def combine_and_convert_dicts_to_sync_meta_data(data, resulting_dict, primary_key, secondary_key: str = None,
                                                    resulting_primary_key: str = MAIN_PRIMARY_KEY_VALUE,
                                                    secondary_data_merging_key: str = None):
        filter_dict = {
            'primary_data': data.get(primary_key, {}),
            'primary_key': resulting_primary_key,
            'secondary_key': secondary_data_merging_key
        }

        if secondary_key:
            filter_dict['secondary_data'] = data.get(secondary_key, {})

        if data.get(primary_key, {}):
            meta_data = SyncHelper.merge_meta_data(**filter_dict)

            if not resulting_dict.get(primary_key):
                resulting_dict[primary_key] = meta_data

            else:
                resulting_dict[primary_key] = {**resulting_dict[primary_key], **meta_data}

        return resulting_dict

    @staticmethod
    def parse_sync_raw_query_response(data, sync_data_key: str, extra_data: dict = None):

        parsed_data = list()
        sync_response = dict()

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

                if key in list(PARSE_JSON_KEYS_WITH_DEFAULT_VALUE.keys()):

                    if sync_data[key]:
                        sync_data[key] = JsonUtilities.load_json_data(sync_data[key], default=[])

                    else:
                        sync_data[key] = PARSE_JSON_KEYS_WITH_DEFAULT_VALUE.get(key)

                chatroom_data_keys = key.split(SYNC_KEY_SPLIT_VALUE)

                if len(chatroom_data_keys) == 3:

                    if chatroom_data_keys[1] in SYNC_RESPONSE_MAP_PRIMARY_KEYS:
                        chatroom_data_keys[1] = MAIN_PRIMARY_KEY_VALUE

                    if chatroom_data_keys[2] in removed_keys_list:
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

            parsed_data.append(parsed_sync_data)

            sync_response = SyncHelper.combine_and_convert_dicts_to_sync_meta_data(parsed_meta_data,
                                                                                   sync_response,
                                                                                   primary_key=USERS_META_KEY_VALUE,
                                                                                   secondary_key=MEMBERS_META_KEY_VALUE)

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
