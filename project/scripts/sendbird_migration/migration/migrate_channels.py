import traceback

from typing import List
from pathlib import Path

from ..models.channel import ChannelModel
from ..constants import (TTL_FOR_CACHE, CHATROOM_IMAGE_S3_PATH, SENDBIRD_CHANNEL_MAP_KEY)

from collabmates_api.chatroom.chatroom_impl import ChatroomImpl
from togther.models import (
    ModelUtilities,
    Collabcard,
    card_answers
)
from utility.time_utilities import TimeUtilities
from utility.states import webhook_chatroom_methods
from external_services.caching.cache_impl import CacheImpl

from ..utils.lambda_utilities import LambdaUtilities
from ..utils.migration_utils import MigrationUtils

from external_services.logging.logging_wrapper import LoggingWrapper

info_logger = LoggingWrapper.get_instance()
error_logger = LoggingWrapper.get_instance()


class MigrateChannels:

    sendbird_api_token: str = ""

    api_key: str = ""
    platform_code: str = ""
    version_code: str = ""
    member_id: int = None
    community_id: int = None
    channels_data: List[ChannelModel] = []

    def __init__(
        self, api_key: str, platform_code: str, version_code: str, bot_id: int, community_id: int, 
        channels_data: List[ChannelModel], sendbird_api_token: str = None
    ):
        self.member_id = bot_id
        self.community_id = community_id
        self.channels_data = channels_data
        self.api_key = api_key
        self.platform_code = platform_code
        self.version_code = version_code

        if sendbird_api_token:
            self.sendbird_api_token = sendbird_api_token

    @staticmethod
    def _create_s3_path_to_save_chatroom_images(url: str):
        url_path = Path(url)

        return CHATROOM_IMAGE_S3_PATH.format("".join([
            str(TimeUtilities.current_time_in_milliseconds()), url_path.suffix]))

    def _create_chatroom_in_community(self, req_body):
        chatroom_manager = ChatroomImpl(
            self.member_id,
            request_platform=self.platform_code,
            version_code=self.version_code,
            api_key=self.api_key,
        )
        chatroom_data = chatroom_manager.create_chatroom(req_body)

        if chatroom_data.get("error_message"):
            raise ValueError(chatroom_data.get("error_message"))

        return chatroom_data

    def add_participants_in_chartroom(self, chatroom_id, chatroom_participants_list: list):
        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not chatroom_instance:
            error_logger.error(f'SendbirdMigration | No chatroom found for chatroom_id: {chatroom_id}')
            return

        chatroom_manager = ChatroomImpl(
            self.member_id,
            request_platform=self.platform_code,
            version_code=self.version_code,
            api_key=self.api_key,
            chatroom_id=chatroom_id
        )

        if chatroom_instance.is_secret:
            request_body = {
                'chatroom_id': chatroom_id,
                'secret_chatroom_participants': chatroom_participants_list,
                'is_secret': chatroom_instance.is_secret
            }

            chatroom_data = chatroom_manager.add_secret_chatroom_participant(
                request_body, is_internal=True, trigger_webhook=False, join_method=webhook_chatroom_methods.CM_ADDED)

            info_logger.info(f'SendbirdMigration | Added chatroom participants to secret chatroom_id: {chatroom_id},'
                             f'response: {chatroom_data}')

        else:
            chatroom_data = chatroom_manager.add_members_to_chatroom(None, chatroom_participants_list)

            info_logger.info(f'SendbirdMigration | Added chatroom participants to open chatroom_id: {chatroom_id},'
                             f'response: {chatroom_data}')

    def create_all_chatrooms(self):
        info_logger.info(f"SendbirdMigration | Total channels to be added: {len(self.channels_data)}")

        chatroom_instances_list = []
        conversation_instances_list = []

        for channel_data in self.channels_data:

            try:
                cache_key = SENDBIRD_CHANNEL_MAP_KEY.format(self.community_id, channel_data.channel_url)
                chatroom_id = CacheImpl.get_cache(cache_key)

                if chatroom_id:
                    info_logger.info(
                        f"SendbirdMigration | Channel already created for channel url: {channel_data.channel_url}, id: {chatroom_id}"
                    )

                else:

                    if channel_data.chatroom_image_url:
                        s3_path = self._create_s3_path_to_save_chatroom_images(channel_data.chatroom_image_url)
                        s3_url = LambdaUtilities.migrate_to_s3(channel_data.chatroom_image_url, s3_path,
                                                               self.sendbird_api_token)

                        if s3_url:
                            channel_data.chatroom_image_url = s3_url

                    request_body = channel_data.model_dump(
                        include=[
                            "header",
                            "title",
                            "chatroom_image_url",
                            "is_secret",
                            "uuids",
                        ]
                    )

                    info_logger.info(
                        f"SendbirdMigration | Calling api/chatroom/create POST with request body: {request_body}"
                    )

                    chatroom_data = self._create_chatroom_in_community(request_body)

                    chatroom_id = chatroom_data.get("chatroom", {}).get("id")

                    if chatroom_id:
                        CacheImpl.set_cache(cache_key, chatroom_id, TTL_FOR_CACHE)

                    else:
                        info_logger.info(
                            f"SendbirdMigration | ID not found in chatroom data: {chatroom_data} for channel url: {channel_data.channel_url}"
                        )

                chatroom_instance: Collabcard = ModelUtilities.get_model_instance_or_none(
                    Collabcard, chatroom_id
                )

                channel_creation_time = MigrationUtils.ensure_epoch_in_ms(
                    channel_data.created_at
                )

                if chatroom_instance:
                    chatroom_instance.created_at = channel_creation_time
                    chatroom_instance.date_epoch = channel_creation_time

                    chatroom_instances_list.append(chatroom_instance)

                if not channel_data.members_can_message:
                    info_logger.info(
                        (
                            f"SendbirdMigration | Updating the channel setting of member can message for "
                            f"channel url: {channel_data.channel_url} chatroom id: {chatroom_id}"
                        )
                    )

                    chatroom_manager = ChatroomImpl(member_id=self.member_id, chatroom_id=chatroom_id)
                    response_context = chatroom_manager.toggle_member_message_post(channel_data.members_can_message)

                    if response_context.get("error_message"):
                        info_logger.error(
                            (
                                f"SendbirdMigration | Error in updating member can message "
                                f"setting: {response_context.get('error_message')}"
                            )
                        )   

                conversation_instance = ModelUtilities.get_model_filter(
                    card_answers, { "card_id":  chatroom_id }
                ).order_by("id").last()

                if conversation_instance:
                    conversation_instance.last_updated = channel_creation_time
                    conversation_instance.created_at = channel_creation_time

                    conversation_instances_list.append(conversation_instance)

            except Exception as e:
                error_logger.error(
                    f"SendbirdMigration | Error in creating chatroom for channel: {channel_data.channel_url} | Error: {e}"
                    f" | Stack trace: {traceback.format_exc()}"
                )
                continue

        # Bulk update Chatroom instances
        ModelUtilities.bulk_update_instances(
            Collabcard, chatroom_instances_list, fields=["created_at", "date_epoch"]
        )

        # Bulk update Conversation instances
        ModelUtilities.bulk_update_instances(
            card_answers, conversation_instances_list, fields=["last_updated", "created_at"]
        )
