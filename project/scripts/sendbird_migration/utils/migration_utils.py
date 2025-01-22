from typing import Optional

from external_services.caching.cache_impl import CacheImpl
from ..constants import (
    SENDBIRD_MESSAGE_MAP_KEY,
    SENDBIRD_USER_MAP_KEY,
    DEFAULT_FILE_S3_PATH,
    CONVERSATION_FILE_S3_PATH,
    MENTIONED_USERS_SYMBOL,
)

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
    def get_file_path_for_conversation_files(chatroom_id: int, user_id: int) -> str:

        if not (chatroom_id and user_id):
            info_logger.error(
                f"SendbirdMigration | No chatroom id or user_id found for conversation files."
            )

            return DEFAULT_FILE_S3_PATH

        return CONVERSATION_FILE_S3_PATH.format(chatroom_id, user_id)

    @staticmethod
    # function to replace mentions
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
