import json, os
from typing import Optional

from external_services.caching.cache_impl import CacheImpl
from ..constants import (
    SENDBIRD_MESSAGE_MAP_KEY,
    SENDBIRD_USER_MAP_KEY,
    DEFAULT_FILE_S3_PATH,
    CONVERSATION_FILE_S3_PATH,
    MENTIONED_USERS_SYMBOL,
    SENDBIRD_CHANNEL_MAP_KEY
)

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
    def get_file_path_for_conversation_files(chatroom_id: int, user_id: int) -> str:

        if not (chatroom_id and user_id):
            info_logger.error(
                f"SendbirdMigration | No chatroom id or user_id found for conversation files."
            )

            return DEFAULT_FILE_S3_PATH

        return CONVERSATION_FILE_S3_PATH.format(chatroom_id, user_id)

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
                    data = json.load(file)
                    data.extend(data)
                    file.seek(0)
                    json.dump(data, file, indent=4)
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
        bucket_name = "likeminds-sendbird-migration" #TODO: move to constants and to beta and prod.py | Create bucket in s3 as well

        s3_client = S3ClientImpl(bucket_name) 
        s3_client.upload_file_to_s3_bucket(object_path=object_path, file_path=file_path)

        info_logger.info(f"SendbirdMigration | Successfully uploaded {file_path} to S3")
