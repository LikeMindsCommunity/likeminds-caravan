import time
import os
import json

import pandas as pd

from .constants import (
    OPEN_CHANNELS_TYPE,
    GROUP_CHANNELS_TYPE,
    MESSAGES_DUMP_JSON_FILE_PATH,
    SENDBIRD_CHANNEL_MAP_KEY,
)
from .models.user import Users
from .models.channel import Channels
from .models.message import Messages
from .utils.sendbird_utils import SendbirdApiUtils
from .utils.likeminds_utils import LikemindsUtils
from .utils.migration_utils import MigrationUtils

from .migration.migrate_users import MigrateUsers
from .migration.migrate_channels import MigrateChannels
from .migration.migrate_messages import MigrateMessages

from external_services.logging.logging_wrapper import LoggingWrapper
from external_services.caching.cache_impl import CacheImpl
from external_services.amazon_s3.s3_utils import S3Utils


info_logger = LoggingWrapper.get_instance()
error_logger = LoggingWrapper.get_instance()


# TODO: Log all the API data in a json file and push it to s3
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

        self.channel_participants_map = None

    def _add_metadata_to_messages(self, messages: list) -> list:

        for message in messages:
            message["community_id"] = self.community_id
            message["sendbird_api_token"] = self.api_token

        return messages

    def _add_channel_participants_list_from_file(self, channel_participants_file_url: str = None):

        if not channel_participants_file_url:
            return True, ''

        # Download the file and save it in local
        local_file_path = S3Utils.download_file_from_s3_url(channel_participants_file_url)

        if not local_file_path:
            return False, error_logger.error(f'SendbirdMigration | '
                                             f'Error downloading the chatroom participants file from '
                                             f'url: {channel_participants_file_url}')

        df = pd.read_csv(local_file_path)

        if df.empty:
            return False, error_logger.error(f'SendbirdMigration | Error in creating df from CSV file whose '
                                             f'url: {channel_participants_file_url}')

        self.channel_participants_map = df.groupby("Chat link")["User ID"].apply(set).to_dict()

        if not self.channel_participants_map:
            return False, error_logger.error(f'SendbirdMigration | Error in creating map from dataframe: {df}')

        return True, ''

    @staticmethod
    def _get_channel_to_lm_chatroom_map_from_file_url(channel_lm_chatroom_mapping_file_url: str):

        if not channel_lm_chatroom_mapping_file_url:
            return True, ''

        # Download the file and save it in local
        local_file_path = S3Utils.download_file_from_s3_url(channel_lm_chatroom_mapping_file_url)

        if not local_file_path:
            return False, error_logger.error(f'SendbirdMigration | '
                                             f'Error downloading the channel -> LM chatroom mapping file from '
                                             f'url: {channel_lm_chatroom_mapping_file_url}')

        file_data = {}

        with open(local_file_path, "r+") as file:
            file_data = json.load(file)

        return True, file_data

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

    def migrate_all_channels(self, channel_participants_file_url: str = None):
        # Create channel participants map from file url
        self._add_channel_participants_list_from_file(channel_participants_file_url)

        channel_types = [OPEN_CHANNELS_TYPE, GROUP_CHANNELS_TYPE]

        for channel_type in channel_types:

            # Migration of open channels
            for channels in self.api_utils.yield_paginated_channels_list(
                channel_type=channel_type
            ):

                if channel_type == OPEN_CHANNELS_TYPE:

                    # Fetch open channel participants
                    for channel in channels:

                        if not channel.get('participant_count'):
                            continue

                        members = []
                        should_call_participants_api = False

                        if self.channel_participants_map:
                            members = list(self.channel_participants_map.get(channel.get("channel_url")))

                            if not members:
                                should_call_participants_api = True

                        else:
                            should_call_participants_api = True

                        if should_call_participants_api:

                            for participants in self.api_utils.yield_open_channel_participants(
                                channel_url=channel.get("channel_url")
                            ):
                                members.extend(participants)

                        channel["members"] = members

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

    def add_participants_to_channels(self, channel_participants_file_url: str,
                                     channel_lm_chatroom_mapping_file_url: str):
        # Create channel participants map from file url
        self._add_channel_participants_list_from_file(channel_participants_file_url)

        info_logger.info(f'SendbirdMigration | Adding participants to channels: {self.channel_participants_map}')

        channel_to_chatroom_map = {}
        is_valid_channel_chatroom_map = False

        if channel_lm_chatroom_mapping_file_url:
            is_valid_channel_chatroom_map, channel_to_chatroom_map = self._get_channel_to_lm_chatroom_map_from_file_url(
                channel_lm_chatroom_mapping_file_url)

        for channel_url, participants_list in self.channel_participants_map.items():

            if is_valid_channel_chatroom_map:
                lm_chatroom_id = channel_to_chatroom_map.get(channel_url)

            else:
                lm_chatroom_id = MigrationUtils.get_lm_chatroom_id_from_sendbird_channel_id(channel_url,
                                                                                            self.community_id)

            info_logger.info(f'SendbirdMigration | Chatroom id: {lm_chatroom_id}, '
                             f'participants list: {participants_list}')

            # Call method to add chatroom participants in chatroom
            MigrateChannels(
                bot_id=self.bot_id,
                community_id=self.community_id,
                api_key=self.api_key,
                platform_code=self.platform_code,
                version_code=self.version_code,
                channels_data=[],
            ).add_participants_in_chartroom(chatroom_id=lm_chatroom_id,
                                            chatroom_participants_list=list(participants_list))

    def migrate_all_messages(self, only_submit_polls: bool = False):

        channel_to_chatroom_ids = {}

        # fetch cache keys for all chatrooms
        channel_keys = CacheImpl.get_keys_for_pattern(
            "*" + SENDBIRD_CHANNEL_MAP_KEY.format(self.community_id, "*")
        )

        for key in channel_keys:

            # Parse the key to get the channel_url
            channel_url = str(key).split("channel_", 1)[1].rstrip("'")

            chatroom_id = MigrationUtils.get_lm_chatroom_id_from_sendbird_channel_id(
                sendbird_channel_id=channel_url, community_id=self.community_id
            )
            if not chatroom_id:
                error_logger.error(
                    f"SendbirdMigration | Chatroom ID not found for channel: {channel_url}"
                )
                continue

            channel_to_chatroom_ids[channel_url] = chatroom_id

            # Parse channel type from channel_url
            channel_type = OPEN_CHANNELS_TYPE if channel_url.split("_")[1] == "open" else GROUP_CHANNELS_TYPE

            messages_dump_file_path = MESSAGES_DUMP_JSON_FILE_PATH.format(channel_url)

            # Create json file where we will dump chatroom messages
            MigrationUtils.dump_data_to_json_file(
                file_path=messages_dump_file_path, data=[]
            )

            # Fetch messages for channel
            for messages in self.api_utils.yield_paginated_messages(
                channel_type=channel_type, channel_url=channel_url
            ):

                # Dump messages to a JSON file
                MigrationUtils.dump_data_to_json_file(
                    file_path=messages_dump_file_path, data=messages
                )

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
                ).create_all_messages(only_submit_polls=only_submit_polls)

                info_logger.info(f"SendbirdMigration | Successfully migrated {len(messages)} messages for channel: {channel_url}")

            # Delete Cache key for chatroom participants
            MigrationUtils.delete_chatroom_participants_count_cache(chatroom_id)

            # Delete Cache key for conversation count
            MigrationUtils.delete_total_messages_count_cache(chatroom_id)

            # Upload Messages Dump to S3
            MigrationUtils.upload_data_dump_to_s3(
                object_path=messages_dump_file_path, file_path=f"{self.community_id}/{messages_dump_file_path}"
            )

            # delete the json file
            os.remove(messages_dump_file_path)

        # Upload Channel TO Chatroom ID Mapping to S3
        MigrationUtils.upload_channel_to_chatroom_id_map_to_s3(
            channel_to_chatroom_ids=channel_to_chatroom_ids,
            community_id=self.community_id,
        )
        return

    def migrate_all_data(self):

        self.migrate_all_users()
        self.migrate_all_channels()

        # Adding delay before creating messages (As users need to get Rights first)
        time.sleep(60) 

        self.migrate_all_messages()

        return
