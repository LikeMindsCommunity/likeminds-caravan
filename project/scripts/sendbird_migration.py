import json

import requests
import os

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from utility.states import conversation_states

APPLICATION_ID = '25354ED6-BEA1-48F0-B6E3-69CC94D4AFE6'


class UserModel(BaseModel):
    uuid: str = Field(alias='user_id')
    user_name: str = Field(alias='nickname')
    image_url: str = Field(alias='profile_url')
    image: str
    created_at: int

    @classmethod
    @model_validator(mode='before')
    def _validate_image_url(cls, data):
        image_url = data.get('image_url') or data['image'] or data['profile_url']
        data['image_url'] = image_url
        data['image'] = image_url

        return data


class Users(BaseModel):
    active_users: list = [UserModel]


class ChannelModel(BaseModel):
    name: str
    tag: str
    chatroom_image_url: str = Field(alias='cover_url')
    created_at: int
    is_secret: bool = not Field(alias='is_public')
    members: [UserModel]


class Channels(BaseModel):
    group_channels: list = [ChannelModel]


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
    API_TOKEN = 'd3b3fd46f645b6237bfca1e9d7215ca8a0e9812a'

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
    def _list_files_from_folder_path(folder_path):
        return [folder_path + '/' + file_name for file_name in os.listdir(folder_path)]

    def _load_data(self):
        for user_file in self.users_files_list:
            with open(user_file, 'r') as file_data:
                self.users_json_data += Users(**json.load(file_data)).active_users

        for channel_file in self.channels_files_list:
            with open(channel_file, 'r') as file_data:
                self.channels_json_data += Channels(**json.load(file_data)).group_channels

        for message_file in self.messages_files_list:
            pass


users_folder_path = '/Users/ankitgarg/Desktop/LikemindsDjango/app/Togther/project/users'
channels_folder_path = '/Users/ankitgarg/Desktop/LikemindsDjango/app/Togther/project/channels'
messages_folder_path = '/Users/ankitgarg/Desktop/LikemindsDjango/app/Togther/project/messages/group_channels'

migration_instance = SendbirdMigrationV2(users_folder_path, channels_folder_path, messages_folder_path)
