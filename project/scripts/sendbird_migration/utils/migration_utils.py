import json, os
from typing import Optional
from pathlib import Path

from django.conf import settings

from external_services.caching.cache_impl import CacheImpl
from utility.cache_keys import CHATROOM_PARTICIPANTS_COUNT_CACHE_KEY
from utility.constants import CONVERSATIONS_COUNT_CACHE_KEY

from ..constants import (
    SENDBIRD_MESSAGE_MAP_KEY,
    SENDBIRD_USER_MAP_KEY,
    DEFAULT_FILE_S3_PATH,
    CONVERSATION_FILE_S3_PATH,
    MENTIONED_USERS_SYMBOL,
    SENDBIRD_CHANNEL_MAP_KEY,
    CHANNEL_TO_CHATROOM_ID_MAP_JSON_FILE_PATH,
)

from utility.time_utilities import TimeUtilities
from external_services.amazon_s3.s3_client_impl import S3ClientImpl
from external_services.logging.logging_wrapper import LoggingWrapper

info_logger = LoggingWrapper.get_instance()
error_logger = LoggingWrapper.get_instance()


class MigrationUtils:

    @staticmethod
    def get_lm_id_from_sendbird_message_id(
        sendbird_message_id: int, community_id: int
    ) -> Optional[int]:

        lm_id = CacheImpl.get_cache(
            SENDBIRD_MESSAGE_MAP_KEY.format(community_id, sendbird_message_id)
        )
        if not lm_id:
            info_logger.info(
                (
                    f"SendbirdMigration | No conversation id found in the cache for " 
                    f"sendbird message id: {sendbird_message_id}"
                )
            )
            return None

        return lm_id

    @staticmethod
    def get_lm_user_id_from_sendbird_user_id(
        sendbird_user_id: str, community_id: int
    ) -> Optional[int]:
        lm_user_id = CacheImpl.get_cache(
            SENDBIRD_USER_MAP_KEY.format(community_id, sendbird_user_id)
        )
        if not lm_user_id:
            info_logger.error(
                (
                    f"SendbirdMigration | No user id found in the cache for sendbird user id: {sendbird_user_id}"
                )
            )
            return None

        return lm_user_id

    @staticmethod
    def get_lm_chatroom_id_from_sendbird_channel_id(
        sendbird_channel_id: str, community_id: int
    ) -> Optional[int]:
        lm_chatroom_id = CacheImpl.get_cache(
            SENDBIRD_CHANNEL_MAP_KEY.format(community_id, sendbird_channel_id)
        )
        if not lm_chatroom_id:
            info_logger.error(
                (
                    f"SendbirdMigration | No chatroom id found in the cache for sendbird channel id: {sendbird_channel_id}"
                )
            )
            return None

        return lm_chatroom_id

    @staticmethod
    def get_file_path_for_conversation_files(chatroom_id: int, user_id: int, url: str) -> str:

        url_path = Path(url)

        if not (chatroom_id and user_id and url):
            info_logger.error(
                f"SendbirdMigration | No chatroom id or user_id or url found for conversation files."
            )

            return DEFAULT_FILE_S3_PATH

        file_name = f"{url_path.stem}-{str(TimeUtilities.current_time_in_milliseconds())}{url_path.suffix}"

        return CONVERSATION_FILE_S3_PATH.format(chatroom_id, user_id, file_name)

    # function to replace mentions
    @staticmethod
    def replace_mentions(text, users):
        while users:
            text = text.replace(MENTIONED_USERS_SYMBOL, users.pop(0), 1)
        return text

    @staticmethod
    def ensure_epoch_in_ms(epoch_time):
        # Check if the epoch time is in seconds (10 digits) or milliseconds (13 digits)
        if len(str(epoch_time)) == 10:
            # Convert seconds to milliseconds
            return epoch_time * 1000
        return epoch_time

    @staticmethod
    def dump_data_to_json_file(file_path: str, data):

        try:
            # Dump data to a JSON file
            if os.path.exists(file_path):
                with open(file_path, "r+") as file:
                    file_data = json.load(file)
                    file_data.extend(data)
                    file.seek(0)
                    json.dump(file_data, file, indent=4)
            else:
                with open(file_path, "w") as file:
                    json.dump(data, file, indent=4)

        except Exception as e:
            error_logger.error(
                f"SendbirdMigration | Error while dumping messages to JSON file: {str(e)}"
            )

    @staticmethod
    def upload_data_dump_to_s3(object_path: str, file_path: str):

        # Upload the JSON file to S3
        bucket = settings.S3_BUCKETS.get("sendbird_migration")

        s3_client = S3ClientImpl(bucket) 
        uploaded = s3_client.upload_file_to_s3_bucket(object_path=object_path, file_path=file_path)

        if uploaded:
            info_logger.info(f"SendbirdMigration | Successfully uploaded {file_path} to S3")

    @staticmethod
    def upload_channel_to_chatroom_id_map_to_s3(channel_to_chatroom_ids: dict, community_id: int):

        local_path = CHANNEL_TO_CHATROOM_ID_MAP_JSON_FILE_PATH.format(community_id)

        # Dump Dict to a JSON file
        MigrationUtils.dump_data_to_json_file(
            file_path=local_path,
            data=channel_to_chatroom_ids,
        )

        # Upload the JSON file to S3
        bucket = settings.S3_BUCKETS.get("sendbird_migration")

        s3_client = S3ClientImpl(bucket) 
        uploaded = s3_client.upload_file_to_s3_bucket(
            object_path=local_path,
            file_path=f"{community_id}/channel_to_chatroom_id_map/{local_path}",
        )

        if uploaded:
            info_logger.info(
                f"SendbirdMigration | Successfully uploaded channel to chatroom ids to S3 for community: {community_id}"
            )
        else:
            error_logger.error(
                f"SendbirdMigration | Error while uploading channel to chatroom ids to S3 for community: {community_id}"
            )

        # Remove the local file
        os.remove(local_path)

    @staticmethod
    def delete_chatroom_participants_count_cache(
        chatroom_id: int
    ):
        
        if not chatroom_id:
            error_logger.error(
                f"SendbirdMigration | No chatroom id found for clearing chatroom participants count cache."
            )

            return

        deleted = CacheImpl.delete_key(CHATROOM_PARTICIPANTS_COUNT_CACHE_KEY.format(chatroom_id))

        if deleted:
            info_logger.info(
                f"SendbirdMigration | Cleared chatroom participants count cache for chatroom: {chatroom_id}"
            )
        else:
            error_logger.error(
                f"SendbirdMigration | Error while clearing chatroom participants count cache for chatroom: {chatroom_id}"
            )

    @staticmethod
    def delete_total_messages_count_cache(chatroom_id: int):
        if not chatroom_id:
            error_logger.error(
                f"SendbirdMigration | No chatroom id found for clearing conversation count cache."
            )

            return

        deleted = CacheImpl.delete_key(CONVERSATIONS_COUNT_CACHE_KEY.format(chatroom_id))

        if deleted:
            info_logger.info(
                f"SendbirdMigration | Cleared conversation count cache for chatroom: {chatroom_id}"
            )
        else:
            error_logger.error(
                f"SendbirdMigration | Error while clearing conversation count cache for chatroom: {chatroom_id}"
            )
