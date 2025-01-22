import time

from .constants import (
    OPEN_CHANNELS_TYPE,
    GROUP_CHANNELS_TYPE,
)
from .models.user import Users
from .models.channel import Channels
from .models.message import Messages
from .utils.sendbird_utils import SendbirdApiUtils
from .utils.likeminds_utils import LikemindsUtils

from .migration.migrate_users import MigrateUsers
from .migration.migrate_channels import MigrateChannels
from .migration.migrate_messages import MigrateMessages

from external_services.logging.logging_wrapper import LoggingWrapper

info_logger = LoggingWrapper.get_instance()
error_logger = LoggingWrapper.get_instance()


# TODO: Add Migration Symbol to all the logs. (And log everything to a file as well which can be stored to s3)
class SendbirdApiMigration:

    api_key: str = ""

    platform_code: str = "web"
    version_code: str = "26"

    community_id: int = None
    bot_id: int = None

    api_utils = None

    def __init__(
        self,
        api_key: str,
        application_id: str,
        api_token: str,
        platform_code: str = None,
        version_code: str = None,
    ):

        if not (api_key or application_id or api_token):
            raise ValueError("API Key/Application ID/Api Token is empty!")

        self.api_utils = SendbirdApiUtils(
            application_id=application_id, api_token=api_token
        )

        self.api_key = api_key
        self.api_token = api_token

        if platform_code:
            self.platform_code = platform_code

        if version_code:
            self.version_code = version_code

        self.community_id = LikemindsUtils.get_community_id_from_api_key(
            api_key=api_key
        )
        if not self.community_id:
            raise ValueError("Community ID not found using API key")

        self.bot_id = LikemindsUtils.get_bot_id_from_api_key(api_key=api_key)
        if not self.bot_id:
            raise ValueError("Bot ID not found using API key")

    def _add_metadata_to_messages(self, messages: list) -> list:

        for message in messages:
            message["community_id"] = self.community_id
            message["sendbird_api_token"] = self.api_token

        return messages

    def migrate_all_users(self, chunk_size: int = 20):

        for users in self.api_utils.yield_paginated_users_list(chunk_size):

            # Load up the users and validate them
            validated_users = Users(users=users).users

            # Migrate the users
            MigrateUsers(
                bot_id=self.bot_id,
                community_id=self.community_id,
                api_key=self.api_key,
                platform_code=self.platform_code,
                version_code=self.version_code,
                users_data=validated_users,
                sendbird_api_token=self.api_token,
            ).add_all_members_data()

            info_logger.info(f"SendbirdMigration | Successfully migrated users: {len(validated_users)}")

        return

    def migrate_all_channels(self):

        channel_types = [OPEN_CHANNELS_TYPE, GROUP_CHANNELS_TYPE]

        for channel_type in channel_types:

            # Migration of open channels
            for channels in self.api_utils.yield_paginated_channels_list(
                channel_type=channel_type
            ):

                # Load up the channels and validate them
                validated_channels = Channels(channels=channels).channels

                # Migrate the channels
                MigrateChannels(
                    bot_id=self.bot_id,
                    community_id=self.community_id,
                    api_key=self.api_key,
                    platform_code=self.platform_code,
                    version_code=self.version_code,
                    channels_data=validated_channels,
                ).create_all_chatrooms()

                info_logger.info(
                    f"SendbirdMigration | Successfully migrated {channel_type}/s: {len(channels)}"
                )

    def migrate_all_messages(self):

        channel_types = [OPEN_CHANNELS_TYPE, GROUP_CHANNELS_TYPE]

        for channel_type in channel_types:

            # Fetch channels
            for channels in self.api_utils.yield_paginated_channels_list(
                channel_type=channel_type
            ):

                for channel in channels:
                    channel_url = channel.get("channel_url")

                    # Fetch messages for each channel
                    for messages in self.api_utils.yield_paginated_messages(
                        channel_type=channel_type, channel_url=channel_url
                    ):

                        # Add community_id & api_token to each messages
                        messages = self._add_metadata_to_messages(messages)

                        # Load up the messages and validate them
                        validated_messages = Messages(messages=messages).messages

                        # Migrate the messages
                        MigrateMessages(
                            api_key=self.api_key,
                            community_id=self.community_id,
                            platform_code=self.platform_code,
                            version_code=self.version_code,
                            messages_data=validated_messages,
                            sendbird_api_utils=self.api_utils,
                        ).create_all_messages()

                        info_logger.info(f"SendbirdMigration | Successfully migrated {len(messages)} messages for channel: {channel_url}")
        return

    def migrate_all_data(self):

        self.migrate_all_users()
        self.migrate_all_channels()

        # Adding delay before creating messages (As users need to get Rights first)
        time.sleep(60) 

        self.migrate_all_messages()

        return
