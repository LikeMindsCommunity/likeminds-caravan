from dataclasses import dataclass
from utility.json_utilities import JsonUtilities
from collabmates_api.sync.sync_helper import SyncHelper


@dataclass
class CommunitySerializer:
    id: int
    name: str
    is_paid: bool
    type: int = None
    sub_type: int = None
    purpose: str = None
    image_url: str = None

    def __init__(self, **kwargs):
        super(CommunitySerializer, self).__init__()

        # filter out any keys that are not defined in the class
        kwargs = {k: v for k, v in kwargs.items() if k in self.__dataclass_fields__}

        # assign the filtered kwargs to the attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


@dataclass
class UserSerializer:
    id: int
    name: str
    image_link: str
    user_unique_id: str
    is_owner: bool
    is_guest: bool = None
    state: int = None
    image_url: str = None
    custom_title: str = None
    created_at: int = None

    def __init__(self, **kwargs):
        super(UserSerializer, self).__init__()

        if kwargs.get('image_url') and not kwargs.get('image_link'):
            kwargs['image_link'] = kwargs.get('image_url')

        elif kwargs.get('image_link') and not kwargs.get('image_url'):
            kwargs['image_url'] = kwargs.get('image_link')

        # filter out any keys that are not defined in the class
        kwargs = {k: v for k, v in kwargs.items() if k in self.__dataclass_fields__}

        # assign the filtered kwargs to the attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


@dataclass
class ChatroomSerializer:
    id: int
    title: str
    community_id: int
    type: int
    date_time: int
    is_pending: bool
    date_epoch: int
    share_link: str
    user_id: int
    has_been_named: bool
    header: str
    access_without_subscription: bool
    has_files: bool
    attachment_count: int
    attachments_uploaded: bool
    is_secret: bool
    has_reactions: bool
    auto_follow_done: bool
    is_edited: bool
    is_paid: bool
    is_private: bool
    member_can_message: bool
    is_private_member: bool
    created_at: int
    chatroom_image_url: str = None
    online_link_type: int = None
    access: int = None
    about: str = None
    co_hosts: list = None
    online_link: str = None
    og_tags: str = None
    internal_link: str = None
    deleted_by_user_id: int = None
    secret_chatroom_participants: list = None
    device_id: str = None
    topic_id: int = None
    chatroom_with_user_id: int = None

    def __init__(self, **kwargs):
        super(ChatroomSerializer, self).__init__()

        # filter out any keys that are not defined in the class
        kwargs = {k: v for k, v in kwargs.items() if k in self.__dataclass_fields__}

        # assign the filtered kwargs to the attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __post_init__(self):

        if isinstance(self.secret_chatroom_participants, str):
            self.secret_chatroom_participants = JsonUtilities.load_json_data(self.secret_chatroom_participants)


@dataclass
class ChatroomStateSerializer:
    mute_status: bool
    follow_status: bool
    is_tagged: bool
    attending_status: bool
    secret_chatroom_left: bool
    updated_at: int
    external_seen: bool
    last_seen_conversation_id: int = None
    state: int = None
    expiry_time: int = None
    chat_request_state: int = None
    chat_requested_by_id: int = None
    chat_request_created_at: int = None

    def __init__(self, **kwargs):
        super(ChatroomStateSerializer, self).__init__()

        # filter out any keys that are not defined in the class
        kwargs = {k: v for k, v in kwargs.items() if k in self.__dataclass_fields__}

        # assign the filtered kwargs to the attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


class DataSerializer:

    @staticmethod
    def parse_sync_raw_query_response(data, sync_data_key: str, extra_data: dict = None):
        return SyncHelper.parse_sync_raw_query_response(data, sync_data_key, extra_data)

    @staticmethod
    def serialize_users_data(data):

        if isinstance(data, dict):

            for key in data:

                if str(key).isdigit():
                    data[key] = DataSerializer.serialize_users_data(data.get(key))

                else:
                    return UserSerializer(**data).__dict__

            return data

        elif isinstance(data, list):
            response = []

            for data_dict in data:
                community_response = DataSerializer.serialize_users_data(data_dict)

                if community_response:
                    response.append(community_response)

            return response

        else:
            return data

    @staticmethod
    def serialize_community_data(data):

        if isinstance(data, dict):

            for key in data:

                if str(key).isdigit():
                    data[key] = DataSerializer.serialize_community_data(data.get(key))

                else:
                    return CommunitySerializer(**data).__dict__

            return data

        elif isinstance(data, list):
            response = []

            for data_dict in data:
                community_response = DataSerializer.serialize_community_data(data_dict)

                if community_response:
                    response.append(community_response)

            return response

        else:
            return data

    @staticmethod
    def serialize_chatroom_data(data, includes_user_state=False):

        if isinstance(data, dict):

            for key in data:

                if str(key).isdigit():
                    data[key] = DataSerializer.serialize_chatroom_data(data.get(key), includes_user_state)

                else:
                    chatroom_response = ChatroomSerializer(**data).__dict__

                    if includes_user_state:
                        chatroom_state_serializer = ChatroomStateSerializer(**data)
                        chatroom_response = {**chatroom_response, **chatroom_state_serializer.__dict__}

                    return chatroom_response

            return data

        elif isinstance(data, list):
            response = []

            for data_dict in data:
                chatroom_response = DataSerializer.serialize_chatroom_data(data_dict, includes_user_state)

                if chatroom_response:
                    response.append(chatroom_response)

            return response

        else:
            return data
