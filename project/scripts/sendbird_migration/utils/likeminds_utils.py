from togther.models import ModelUtilities
from collabmates_api.sdk.models import SdkClient

from collabmates_api.user.user_impl import UserImpl

from external_services.logging.logging_wrapper import LoggingWrapper

info_logger = LoggingWrapper.get_instance()
error_logger = LoggingWrapper.get_instance()

class LikemindsUtils:

    @staticmethod
    def get_community_id_from_api_key(api_key: str) -> int:

        if not api_key:
            return 0
        
        sdk_filter = ModelUtilities.get_model_filter(
            SdkClient, {"api_key": api_key, "is_deleted": False}
        )

        if not sdk_filter:
            info_logger.error(
                (
                    f"SendbirdMigration | Sdk Community not found for API key: {api_key}"
                )
            )

            return 0
        
        return sdk_filter.first().community.id

    @staticmethod
    def get_bot_id_from_api_key(api_key) -> int:

        if not api_key:
            return 0
        
        context = UserImpl(user_id=None).fetch_user_bot(api_key=api_key)
        if context.get("error_message"):
            info_logger.error(
                (
                    f"SendbirdMigration | Error in fetch_user_bot for api_key: {api_key} " 
                    f"| error_message: {context.get('error_message')}"
                )
            )
            return 0

        if context.get("user", {}).get("id"):
            return context.get("user", {}).get("id")
        else:
            info_logger.error(
                (
                    f"SendbirdMigration | Bot ID not found for API key: {api_key} | context: {context}"
                )
            )
            return 0
