from utility.response_utilities import ResponseUtilities
from utility.validation_utilities import ValidationUtilities
from .constants import (SYNC_KEY_SPLIT_VALUE, IGNORED_KEYS_LIST, META_KEYS_SUFFIX, SYNC_RESPONSE_MAP_PRIMARY_KEYS,
                        USERS_META_KEY_VALUE, MEMBERS_META_KEY_VALUE, MAIN_PRIMARY_KEY_VALUE,
                        CONVERSATIONS_META_KEY_VALUE, SYNC_DATA_KEYS, COMMUNITY_META_KEY_VALUE, CHATROOM_META_KEY_VALUE)


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

        if (not min_timestamp) and (not max_timestamp):
            return ResponseUtilities.get_inner_error_context('Send either min_timestamp or max_timestamp values!')

        if min_timestamp and not str(min_timestamp).isdigit():
            return ResponseUtilities.get_inner_error_context('Invalid min_timestamp!')

        if max_timestamp and not str(max_timestamp).isdigit():
            return ResponseUtilities.get_inner_error_context('Invalid max_timestamp!')

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')

        return {
            'user_instance': user_instance,
            'community_instance': community_instance
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

        if (not min_timestamp) and (not max_timestamp):
            return ResponseUtilities.get_inner_error_context('Send either min_timestamp or max_timestamp values!')

        if min_timestamp and not str(min_timestamp).isdigit():
            return ResponseUtilities.get_inner_error_context('Invalid min_timestamp!')

        if max_timestamp and not str(max_timestamp).isdigit():
            return ResponseUtilities.get_inner_error_context('Invalid max_timestamp!')

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')
        chatroom_instance = validated_dict.get('chatroom_id')

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'chatroom_instance': chatroom_instance
        }

    @staticmethod
    def merge_meta_data(primary_data: dict, secondary_data: dict = None):
        merged_meta_data = {}

        if not primary_data:
            return merged_meta_data

        if isinstance(list(primary_data.values())[0], dict):

            for key, data in primary_data.items():

                if data.get(MAIN_PRIMARY_KEY_VALUE):
                    merged_meta_data[data.get(MAIN_PRIMARY_KEY_VALUE)] = data

        else:

            if primary_data.get(MAIN_PRIMARY_KEY_VALUE):
                merged_meta_data[primary_data.get(MAIN_PRIMARY_KEY_VALUE)] = primary_data

        if not secondary_data:
            return merged_meta_data

        primary_data = secondary_data

        if isinstance(list(primary_data.values())[0], dict):

            for key, data in primary_data.items():

                if data.get(MAIN_PRIMARY_KEY_VALUE):
                    merged_meta_data[data.get(MAIN_PRIMARY_KEY_VALUE)].update(data)

        else:

            if primary_data.get(MAIN_PRIMARY_KEY_VALUE):
                merged_meta_data[primary_data.get(MAIN_PRIMARY_KEY_VALUE)].update(primary_data)

        return merged_meta_data

    @staticmethod
    def combine_and_convert_dicts_to_sync_meta_data(data, resulting_dict, primary_key, secondary_key: str = None):
        filter_dict = {
            'primary_data': data.get(primary_key, {})
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

        for sync_data in data:
            parsed_sync_data = dict()
            parsed_meta_data = dict()
            removed_keys_list = list()

            for key in sync_data:

                if key in IGNORED_KEYS_LIST:
                    continue

                if key in list(SYNC_DATA_KEYS.keys()):
                    parsed_sync_data[SYNC_DATA_KEYS[key]] = sync_data.get(key)

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

        sync_response[sync_data_key] = parsed_data

        return sync_response
