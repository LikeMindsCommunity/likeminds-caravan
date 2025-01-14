import json, os

from typing import List

from ..constants import LIKEMINDS_API_KEY, PLATFORM_CODE, VERSION_CODE, JSON_FILE_TYPE
from ..models.user import Users
from ..models.channel import Channels
from ..models.message import MessageModel, Messages

from utils.migrate_users import MigrateUsers
from utils.migrate_channels import MigrateChannels
from utils.migrate_messages import MigrateMessages


from collabmates_api.sdk.models import SdkClient
from togther.models import ModelUtilities
from collabmates_api.user.user_impl import UserImpl


class SendbirdMigrationV2:

    supported_file_types = [JSON_FILE_TYPE]
    chunk_size = 1000 # TO be used for message migration

    def __init__(
        self,
        users_folder_path: str,
        channels_folder_path: str,
        messages_folder_path: str,
        is_csv: bool = False,
    ):
        self.users_folder_path = users_folder_path
        self.channels_folder_path = channels_folder_path
        self.messages_folder_path = messages_folder_path
        self.is_csv = is_csv

        self.users_files_list = []
        self.channels_files_list = []
        self.messages_files_list = []

        self.users_json_data = []
        self.channels_json_data = []
        self.messages_json_data = List[MessageModel]

        # Validate and load data
        self._validate()
        self._load_data()

        self.community_instance = self.get_community_from_api_key()
        self.bot_id = self.get_bot_id_from_bot_uuid()

    def _validate(self):

        if not any(
            [
                os.path.isdir(self.users_folder_path),
                os.path.isdir(self.channels_folder_path),
                os.path.isdir(self.messages_folder_path),
            ]
        ):
            raise ValueError(
                "Please provide the correct folder path for users, channels or messages."
            )

        self.users_files_list = self._list_files_from_folder_path(
            self.users_folder_path
        )
        self.channels_files_list = self._list_files_from_folder_path(
            self.channels_folder_path
        )
        self.messages_files_list = self._list_files_from_folder_path(
            self.messages_folder_path
        )

        if not any(
            [
                len(self.users_files_list),
                len(self.channels_files_list),
                len(self.messages_files_list),
            ]
        ):
            raise ValueError(
                "Some of the folder paths provided are empty. Please provide the correct folder path."
            )

        files_with_wrong_extension = []

        for file_name in (
            self.users_files_list + self.channels_files_list + self.messages_files_list
        ):
            file_extension = os.path.splitext(file_name)[1]

            if not (file_extension and file_extension in self.supported_file_types):
                files_with_wrong_extension.append(file_name)

        if files_with_wrong_extension:
            raise ValueError(f"Invalid files: {files_with_wrong_extension}")

    @staticmethod
    def get_community_from_api_key():
        if not LIKEMINDS_API_KEY:
            raise ValueError(
                "LikeMinds API key not defined. Create a community using LikeMinds dashboard first."
            )

        sdk_filter = ModelUtilities.get_model_filter(
            SdkClient, {"api_key": LIKEMINDS_API_KEY}
        )

        if not sdk_filter:
            raise ValueError("Invalid API key!")

        return sdk_filter.first().community

    @staticmethod
    def get_bot_id_from_bot_uuid():
        user_manager = UserImpl(
            user_id=None, platform_code=PLATFORM_CODE, version_code=VERSION_CODE
        )
        context = user_manager.fetch_user_bot(api_key=LIKEMINDS_API_KEY)

        if context.get("error_message"):
            raise ValueError(context.get("error_message"))

        if context.get("user", {}).get("id"):
            return context.get("user", {}).get("id")

    @staticmethod
    def _list_files_from_folder_path(folder_path):
        return [folder_path + "/" + file_name for file_name in os.listdir(folder_path)]

    def _load_data(self):

        for user_file in self.users_files_list:
            with open(user_file, "r") as file_data:
                self.users_json_data += Users(**json.load(file_data)).users

        for channel_file in self.channels_files_list:
            with open(channel_file, "r") as file_data:
                self.channels_json_data += Channels(**json.load(file_data)).channels

        for message_file in self.messages_files_list:
            with open(message_file, "r") as file_data:
                messages = json.load(file_data)

                for i in range(0, len(messages), self.chunk_size):    
                    chunk = messages[i : i + self.chunk_size]
                    self.messages_json_data += Messages(**chunk).messages # TEST For large files

    def migrate_data(self):
        # Migrate channels
        MigrateUsers(
            bot_id=self.bot_id,
            community_id=self.community_instance.id,
            users_data=self.users_json_data,
        ).add_all_members_data()

        # Migrate channels
        MigrateChannels(
            bot_id=self.bot_id,
            community_id=self.community_instance.id,
            channels_data=self.channels_json_data,
        ).create_all_chatrooms()
