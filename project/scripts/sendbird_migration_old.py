import json
from typing import List

import requests
import os

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from collabmates_api.sdk.models import (SdkClient)
from togther.models import (
    ModelUtilities,
    SDKClientUsersInfo,
    Members,
    Userinfo,
    Collabcard
)

from utility.states import (
    conversation_states,
    card_types
)
from utility.time_utilities import TimeUtilities
from utility.cache_keys import SENDBIRD_MIGRATION_CHANNEL_MAP_CACHE_KEY

from external_services.caching.cache_impl import CacheImpl

from collabmates_api.community.community_impl import CommunityImpl
from collabmates_api.user.user_impl import UserImpl
from collabmates_api.chatroom.chatroom_impl import ChatroomImpl


# Older Migration Class - To be used when exporting using APIs
APPLICATION_ID = 'A7128051-8508-46A1-B4A2-821886B5781F'

LIKEMINDS_API_KEY = '35fdd780-499f-4948-a87d-cf7502948314'
PLATFORM_CODE = 'web'
PLATFORM_TYPE = 'dashboard'
VERSION_CODE = 26

TTL_FOR_CACHE = 60 * 60 * 60

user_data_sample = {
    "user_id": "needed | uuid | str",
    "nickname": "needed | name | str",
    "profile_url": "needed | image_link | str",
    "created_at": "needed | Timestamp at which user is created | epoch int"
}

open_channel_sample = {
    "channel_url": "only needed in migration for mapping | unique url of the channel | str",
    "name": "needed | Name of the channel | str",
    "cover_url": "needed | channel image | str",
    "created_at": "needed | Channel creation time | epoch int",
    "freeze": "needed | Indicates whether the channel is currently frozen. The value of true indicates that only "
              "operators can send messages to the channel. | bool",
}

group_channel_sample = {
    "channel_url": "only needed in migration for mapping | unique url of the channel | str",
    "name": "needed | Name of the channel | str",
    "cover_url": "needed | channel image | str",
    "created_at": "needed | Channel creation time | epoch int",
    "is_public": "need to ask | Indicates whether to allow a user to join the channel without an invitation. | bool",
    "freeze": "needed | Indicates whether the channel is currently frozen. The value of true indicates that only "
              "operators can send messages to the channel. | bool",
}

message_sample = {

}


class UserModel(BaseModel):
    uuid: str = Field(alias='user_id')
    user_name: str = Field(alias='nickname')
    image_url: str = Field(alias='profile_url')
    image: str = None
    created_at: int = TimeUtilities.current_time_in_sec()

    @classmethod
    @model_validator(mode='before')
    def _validate_image_url(cls, data):
        image_url = data.get('image_url') or data['image'] or data['profile_url']
        data['image_url'] = image_url
        data['image'] = image_url

        return data


class Users(BaseModel):
    users: List[UserModel]


class ChannelModel(BaseModel):
    channel_url: str
    header: str = Field(alias='name')
    title: str = Field(alias='name')
    chatroom_image_url: str = Field(alias='cover_url')
    created_at: int
    is_secret: bool = False
    members: List[UserModel] = []
    uuids: list = []
    members_can_message: bool = True
    type: int = card_types.CARD_NORMAL

    @classmethod
    @model_validator(mode='before')
    def _validate_members(cls, data):
        if data.get('is_public') is None:
            data['members'] = data.get('participants')

        return data

    @classmethod
    @model_validator(mode='before')
    def _validate_is_secret(cls, data):
        data['is_secret'] = not data.get('is_public', True)
        return data

    @classmethod
    @model_validator(mode='before')
    def _validate_members_can_message(cls, data):
        data['members_can_message'] = not data.get('freeze', False)
        return data

    @model_validator(mode='after')
    def _fill_uuids(self):
        if self.members:

            for user_data in self.members:
                self.uuids.append(user_data.uuid)

        self.uuids = list(set(self.uuids))

        return self


class Channels(BaseModel):
    channels: List[ChannelModel]


class MessageModel(BaseModel):
    message_id: int
    answer: str = Field(alias='message')
    state: int = 0
    created_at: int
    user: UserModel
    is_deleted: bool = Field(alias='is_removed')

    @staticmethod
    def _validate_state(data):
        # Validate the state
        conversation_states_dict = {
            'MESG': conversation_states.ANSWER
        }

        if not (data.get('type') and data.get('type') in conversation_states_dict):
            raise PydanticCustomError(
                'invalid_message_type',
                'Invalid message type.'
            )

        data['state'] = conversation_states_dict[data.get('type')]
        return data

    @classmethod
    @model_validator(mode='before')
    def _validate(cls, data):
        data = cls._validate_state(data)

        return data


class SendbirdMigration:
    BASE_URL = f'https://api-{APPLICATION_ID}.sendbird.com/v3'
    API_TOKEN = '441ddd489a87926711df7e8e6c473af1fca1c532'

    ENDPOINTS = {
        'list_users': f'{BASE_URL}/users?active_mode=all',
        'list_open_channels': f'{BASE_URL}/open_channels',
        'list_group_channels': f'{BASE_URL}/group_channels'
    }

    def __init__(self):
        # Validating the
        self._validate()

    def _create_headers(self):
        return {
            'Api-Token': f'{self.API_TOKEN}',
            'Content-Type': 'application/json'
        }

    def _send_request(self, method: str, url: str, params: dict = None, body: dict = None):
        print(f'Sending request to URL: {url}, method: {method}, params: {params}, body: {body}')
        response = requests.request(method, url, headers=self._create_headers(), params=params, data=body)

        json_response = response.json()

        return json_response

    @staticmethod
    def _validate():
        if not APPLICATION_ID:
            raise ValueError('Application ID is empty!')

    def list_users(self):
        should_break_loop = False
        token = ""

        while not should_break_loop:
            url = self.ENDPOINTS.get('list_users')

            if token:
                url += f'&token={token}'

            response = self._send_request('GET', url)
            token = response.get('next')

            if not token:
                should_break_loop = True

            for user_dict in response.get('users'):
                print(user_dict)
                print('*'*50)

    def list_channels(self, channel_type: str = 'open_channel'):
        should_break_loop = False
        token = ""

        while not should_break_loop:
            if channel_type == 'open_channel':
                url = self.ENDPOINTS.get('list_open_channels')

            elif channel_type == 'group_channel':
                url = self.ENDPOINTS.get('list_group_channels')

            else:
                raise ValueError(f'Invalid channel type: {channel_type} in list_channels method')

            if token:
                url += f'&token={token}'

            response = self._send_request('GET', url)
            token = response.get('next')

            if not token:
                should_break_loop = True

            for user_dict in response.get('users'):
                print(user_dict)
                print('*'*50)


class MigrateUsers:

    def __init__(self, bot_id: int, community_id: int, users_data: List[UserModel]):
        self.member_id = bot_id
        self.community_id = community_id
        self.users_data = users_data

    def _add_member_to_community(self, req_body):
        community_manager = CommunityImpl(member_id=self.member_id, api_key=LIKEMINDS_API_KEY,
                                          request_platform=PLATFORM_CODE, version_code=VERSION_CODE)
        community_data = community_manager.add_community_member(req_body)

        if community_data.get('error_message'):
            raise ValueError(community_data.get('error_message'))

        return community_data

    def add_all_members_data(self):
        print('*'*50)
        print(f'Total users to be added: {len(self.users_data)}')

        sdk_instances_list = []
        userinfo_instances_list = []
        member_instances_list = []

        for user_data in self.users_data:
            # TODO: Add code to upload image url to S3 and replace the image_url with the new one

            request_body = user_data.model_dump(include=['uuid', 'user_name', 'image_url'])

            print(f'Calling api/community/member POST with request body: {request_body}')
            response = self._add_member_to_community(request_body)

            # Update the created_at for Users, SdkClientUsersInfo, Members schema
            sdk_user_instance: SDKClientUsersInfo = ModelUtilities.get_model_filter(
                SDKClientUsersInfo, {'user_unique_id': user_data.uuid, 'community': self.community_id}).first()

            if sdk_user_instance:
                created_at = TimeUtilities.convert_sec_to_milliseconds(user_data.created_at)

                sdk_user_instance.created_at = created_at
                sdk_user_instance.user.userinfo.created_at = user_data.created_at

                sdk_instances_list.append(sdk_user_instance)
                userinfo_instances_list.append(sdk_user_instance.user.userinfo)

                member_instance: Members = ModelUtilities.get_model_filter(
                    Members, {'community_id': self.community_id, 'member_id': sdk_user_instance.user}).first()

                if member_instance:
                    member_instance.created_at = user_data.created_at
                    member_instance.became_member_at = user_data.created_at
                    member_instances_list.append(member_instance)

        ModelUtilities.bulk_update_instances(SDKClientUsersInfo, sdk_instances_list, fields=['created_at'])
        ModelUtilities.bulk_update_instances(Userinfo, userinfo_instances_list, fields=['created_at'])
        ModelUtilities.bulk_update_instances(Members, member_instances_list, fields=['created_at', 'became_member_at'])


class MigrateChannels:

    def __init__(self, bot_id: int, community_id: int, channels_data: List[ChannelModel]):
        self.member_id = bot_id
        self.community_id = community_id
        self.channels_data = channels_data

    def _create_chatroom_in_community(self, req_body):
        chatroom_manager = ChatroomImpl(self.member_id, request_platform=PLATFORM_CODE, version_code=VERSION_CODE,
                                        api_key=LIKEMINDS_API_KEY)
        chatroom_data = chatroom_manager.create_chatroom(req_body)

        if chatroom_data.get('error_message'):
            raise ValueError(chatroom_data.get('error_message'))

        return chatroom_data

    def create_all_chatrooms(self):
        print('*' * 50)
        print(f'Total channels to be added: {len(self.channels_data)}')

        chatroom_instances_list = []

        for channel_data in self.channels_data:
            cache_key = SENDBIRD_MIGRATION_CHANNEL_MAP_CACHE_KEY.format(LIKEMINDS_API_KEY, channel_data.channel_url)
            chatroom_id = CacheImpl.get_cache(cache_key)

            if chatroom_id:
                print(f'Channel already created for channel url: {channel_data.channel_url}, id: {chatroom_id}')

            else:
                # TODO: Add code to upload image url to S3 and replace the image_url with the new one

                request_body = channel_data.model_dump(
                    include=['header', 'title', 'chatroom_image_url', 'is_secret', 'uuids']
                )

                print(f'Calling api/chatroom/create POST with request body: {request_body}')
                chatroom_data = self._create_chatroom_in_community(request_body)

                chatroom_id = chatroom_data.get('chatroom', {}).get('id')

                if chatroom_id:
                    CacheImpl.set_cache(cache_key, chatroom_id, TTL_FOR_CACHE)

                else:
                    print(f'ID not found in chatroom data: {chatroom_data} for channel url: {channel_data.channel_url}')

            chatroom_instance: Collabcard = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

            if chatroom_instance:
                chatroom_instance.created_at = TimeUtilities.convert_sec_to_milliseconds(channel_data.created_at)
                chatroom_instance.date_epoch = channel_data.created_at

                chatroom_instances_list.append(chatroom_instance)

            if not channel_data.members_can_message:
                print(f'Update the channel setting of member can message for channel url: {channel_data.channel_url}'
                      f'chatroom id: {chatroom_id}')

                # TODO: Call the chatroom setting of member can message for the chatroom above

        ModelUtilities.bulk_update_instances(Collabcard, chatroom_instances_list, fields=['created_at', 'date_epoch'])


class SendbirdMigrationV2:
    SUPPORTED_FILE_TYPE = ".json"

    def __init__(self, users_folder_path: str, channels_folder_path: str, messages_folder_path: str,
                 is_csv: bool = False):
        self.users_folder_path = users_folder_path
        self.channels_folder_path = channels_folder_path
        self.messages_folder_path = messages_folder_path
        self.is_csv = is_csv

        self.users_files_list = []
        self.channels_files_list = []
        self.messages_files_list = []

        self.users_json_data = []
        self.channels_json_data = []
        self.messages_json_data = []

        # Validate and load data
        self._validate()
        self._load_data()

        self.community_instance = self.get_community_from_api_key()
        self.bot_id = self.get_bot_id_from_bot_uuid()

    def _validate(self):

        if not any([os.path.isdir(self.users_folder_path),
                    os.path.isdir(self.channels_folder_path),
                    os.path.isdir(self.messages_folder_path)]):
            raise ValueError('Please provide the correct folder path for users, channels or messages.')

        self.users_files_list = self._list_files_from_folder_path(self.users_folder_path)
        self.channels_files_list = self._list_files_from_folder_path(self.channels_folder_path)
        self.messages_files_list = self._list_files_from_folder_path(self.messages_folder_path)

        if not any([len(self.users_files_list),
                    len(self.channels_files_list),
                    len(self.messages_files_list)]):
            raise ValueError('Some of the folder paths provided are empty. Please provide the correct folder path.')

        files_with_wrong_extension = []

        for file_name in self.users_files_list + self.channels_files_list + self.messages_files_list:
            file_extension = os.path.splitext(file_name)[1]

            if not (file_extension and file_extension in self.SUPPORTED_FILE_TYPE):
                files_with_wrong_extension.append(file_name)

        if files_with_wrong_extension:
            raise ValueError(f'Invalid files: {files_with_wrong_extension}')

    @staticmethod
    def get_community_from_api_key():
        if not LIKEMINDS_API_KEY:
            raise ValueError('LikeMinds API key not defined. Create a community using LikeMinds dashboard first.')

        sdk_filter = ModelUtilities.get_model_filter(SdkClient, {'api_key': LIKEMINDS_API_KEY})

        if not sdk_filter:
            raise ValueError('Invalid API key!')

        return sdk_filter.first().community

    @staticmethod
    def get_bot_id_from_bot_uuid():
        user_manager = UserImpl(user_id=None, platform_code=PLATFORM_CODE, version_code=VERSION_CODE)
        context = user_manager.fetch_user_bot(api_key=LIKEMINDS_API_KEY)

        if context.get('error_message'):
            raise ValueError(context.get('error_message'))

        if context.get('user', {}).get('id'):
            return context.get('user', {}).get('id')

    @staticmethod
    def _list_files_from_folder_path(folder_path):
        return [folder_path + '/' + file_name for file_name in os.listdir(folder_path)]

    def _load_data(self):
        for user_file in self.users_files_list:
            with open(user_file, 'r') as file_data:
                self.users_json_data += Users(**json.load(file_data)).users

        for channel_file in self.channels_files_list:
            with open(channel_file, 'r') as file_data:
                self.channels_json_data += Channels(**json.load(file_data)).channels

        # for message_file in self.messages_files_list:
        #     pass

    def migrate_data(self):
        # Migrate channels
        MigrateUsers(
            bot_id=self.bot_id,
            community_id=self.community_instance.id,
            users_data=self.users_json_data
        ).add_all_members_data()

        # Migrate channels
        MigrateChannels(
            bot_id=self.bot_id,
            community_id=self.community_instance.id,
            channels_data=self.channels_json_data
        ).create_all_chatrooms()


users_folder_path = '/Users/ankitgarg/Desktop/LikemindsDjango/app/Togther/project/users'
channels_folder_path = '/Users/ankitgarg/Desktop/LikemindsDjango/app/Togther/project/channels'
messages_folder_path = '/Users/ankitgarg/Desktop/LikemindsDjango/app/Togther/project/messages/group_channels'

migration_instance = SendbirdMigrationV2(users_folder_path, channels_folder_path, messages_folder_path)
# migration_instance.migrate_data()
