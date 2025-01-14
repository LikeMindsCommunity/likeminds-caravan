from typing import List
from pathlib import Path

from ..models.channel import ChannelModel
from ..constants import PLATFORM_CODE, VERSION_CODE, LIKEMINDS_API_KEY, TTL_FOR_CACHE, CHATROOM_IMAGE_S3_PATH

from collabmates_api.chatroom.chatroom_impl import ChatroomImpl
from togther.models import (
    ModelUtilities,
    Collabcard
)
from utility.cache_keys import SENDBIRD_MIGRATION_CHANNEL_MAP_CACHE_KEY
from utility.time_utilities import TimeUtilities
from external_services.caching.cache_impl import CacheImpl

from ..utils.lambda_utilities import LambdaUtilities


class MigrateChannels:

    def __init__(
        self, bot_id: int, community_id: int, channels_data: List[ChannelModel]
    ):
        self.member_id = bot_id
        self.community_id = community_id
        self.channels_data = channels_data

    @staticmethod
    def _create_s3_path_to_save_chatroom_images(url: str):
        url_path = Path(url)

        return CHATROOM_IMAGE_S3_PATH.format("".join([
            str(TimeUtilities.current_time_in_milliseconds()), url_path.suffix]))

    def _create_chatroom_in_community(self, req_body):
        chatroom_manager = ChatroomImpl(
            self.member_id,
            request_platform=PLATFORM_CODE,
            version_code=VERSION_CODE,
            api_key=LIKEMINDS_API_KEY,
        )
        chatroom_data = chatroom_manager.create_chatroom(req_body)

        if chatroom_data.get("error_message"):
            raise ValueError(chatroom_data.get("error_message"))

        return chatroom_data

    def create_all_chatrooms(self):
        print("*" * 50)
        print(f"Total channels to be added: {len(self.channels_data)}")

        chatroom_instances_list = []

        for channel_data in self.channels_data:
            cache_key = SENDBIRD_MIGRATION_CHANNEL_MAP_CACHE_KEY.format(
                LIKEMINDS_API_KEY, channel_data.channel_url
            )
            chatroom_id = CacheImpl.get_cache(cache_key)

            if chatroom_id:
                print(
                    f"Channel already created for channel url: {channel_data.channel_url}, id: {chatroom_id}"
                )

            else:
                # TODO: Add code to upload image url to S3 and replace the image_url with the new one
                s3_path = self._create_s3_path_to_save_chatroom_images(channel_data.chatroom_image_url)
                s3_url = LambdaUtilities.migrate_to_s3(channel_data.chatroom_image_url, s3_path, is_prod=False)

                if not s3_url:
                    raise ValueError(f"Error in uploading file to s3: {s3_url} for user uuid: {channel_data.channel_url}")

                request_body = channel_data.model_dump(
                    include=[
                        "header",
                        "title",
                        "chatroom_image_url",
                        "is_secret",
                        "uuids",
                    ]
                )

                print(
                    f"Calling api/chatroom/create POST with request body: {request_body}"
                )
                chatroom_data = self._create_chatroom_in_community(request_body)

                chatroom_id = chatroom_data.get("chatroom", {}).get("id")

                if chatroom_id:
                    CacheImpl.set_cache(cache_key, chatroom_id, TTL_FOR_CACHE)

                else:
                    print(
                        f"ID not found in chatroom data: {chatroom_data} for channel url: {channel_data.channel_url}"
                    )

            chatroom_instance: Collabcard = ModelUtilities.get_model_instance_or_none(
                Collabcard, chatroom_id
            )

            if chatroom_instance:
                chatroom_instance.created_at = (
                    TimeUtilities.convert_sec_to_milliseconds(channel_data.created_at)
                )
                chatroom_instance.date_epoch = channel_data.created_at

                chatroom_instances_list.append(chatroom_instance)

            if not channel_data.members_can_message:
                print(
                    f"Update the channel setting of member can message for channel url: {channel_data.channel_url}"
                    f"chatroom id: {chatroom_id}"
                )

                chatroom_manager = ChatroomImpl(member_id=self.member_id, chatroom_id=chatroom_id)
                response_context = chatroom_manager.toggle_member_message_post(channel_data.members_can_message)

                if response_context.get("error_message"):
                    print(f"Error in updating member can message setting: {response_context.get('error_message')}")

        ModelUtilities.bulk_update_instances(
            Collabcard, chatroom_instances_list, fields=["created_at", "date_epoch"]
        )
