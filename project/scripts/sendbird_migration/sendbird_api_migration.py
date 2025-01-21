import requests

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
            ).add_all_members_data()

            print(f"Successfully migrated users: {len(validated_users)}")

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

                print(f"Successfully migrated {channel_type}/s: {len(channels)}")

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

                        # Add LM community_id to each message
                        messages = [
                            {**message, "community_id": self.community_id}
                            for message in messages
                        ]

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

                        print(
                            f"Successfully migrated {len(messages)} messages for channel: {channel_url}"
                        )
        return

    def migrate_all_data(self):

        self.migrate_all_users()
        self.migrate_all_channels()
        self.migrate_all_messages()

        return
