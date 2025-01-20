import requests

from ..constants import APPLICATION_ID, API_TOKEN, LIKEMINDS_API_KEY, PLATFORM_CODE, VERSION_CODE, SENDBIRD_API_BASE_URL
from ..models.user import Users
from ..models.channel import Channels
from ..models.message import Messages

from ..utils.migrate_users import MigrateUsers
from ..utils.migrate_channels import MigrateChannels
from ..utils.migrate_messages import MigrateMessages

from collabmates_api.sdk.models import SdkClient
from togther.models import ModelUtilities
from collabmates_api.user.user_impl import UserImpl


OPEN_CHANNELS_TYPE = "open_channels"
GROUP_CHANNELS_TYPE = "group_channels"


class SendbirdMigration:

    api_key: str = LIKEMINDS_API_KEY
    application_id: str = APPLICATION_ID
    api_token: str = API_TOKEN

    platform_code: str = PLATFORM_CODE
    version_code: str = VERSION_CODE

    community_id: int = None
    bot_id: int = None

    base_url = ""

    def __init__(self, api_key: str = None, application_id: str = None, api_token: str = None, 
                 platform_code: str = None, version_code: str = None):

        if api_key:
            self.api_key = api_key

        if application_id:
            self.application_id = application_id

        if api_token:
            self.api_token = api_token

        if platform_code:
            self.platform_code = platform_code

        if version_code:
            self.version_code = version_code

        self.base_url = SENDBIRD_API_BASE_URL.format(self.application_id)

        if not self.base_url or not self.api_token:
            raise ValueError("Base Url/Api Token is empty!")
        
        self.community_id = self.get_community_from_api_key()
        self.bot_id = self.get_bot_id_from_bot_uuid()

        if not self.community_id or not self.bot_id:
            raise ValueError("Community ID/Bot ID not found using API key")

    def get_community_from_api_key(self):
        if not self.api_key:
            raise ValueError(
                "LikeMinds API key not defined. Create a community using LikeMinds dashboard first."
            )

        sdk_filter = ModelUtilities.get_model_filter(
            SdkClient, {"api_key": self.api_key, "is_deleted": False}
        )

        if not sdk_filter:
            raise ValueError("Invalid API key! No SdkClient found for the given API key")
        
        return sdk_filter.first().community.id

    def get_bot_id_from_bot_uuid(self):

        if not self.api_key:
            raise ValueError("API Key is empty!")

        user_manager = UserImpl(
            user_id=None, platform_code=self.platform_code, version_code=self.version_code
        )

        context = user_manager.fetch_user_bot(api_key=self.api_key)
        if context.get("error_message"):
            raise ValueError(context.get("error_message"))

        if context.get("user", {}).get("id"):
            return context.get("user", {}).get("id")
        else:
            raise ValueError("Bot ID not found using fetch_user_bot")
    
    def _construct_url(self, endpoint_type: str, channel_type: str = None, channel_url: str = None):

        base_url = self.base_url
        LIST_USERS_ENDPOINT = "{base_url}/users"
        LIST_CHANNELS_ENDPOINT = "{base_url}/{channel_type}"
        LIST_MESSAGES_ENDPOINT = "{base_url}/{channel_type}/{channel_url}/messages"

        if endpoint_type == "list_users":
            return LIST_USERS_ENDPOINT.format(base_url=base_url)
        
        elif endpoint_type == "list_channels":
            if not channel_type:
                raise ValueError("Channel type is empty in _construct_url method for list_channels")
            
            return LIST_CHANNELS_ENDPOINT.format(base_url=base_url, channel_type=channel_type)
        
        elif endpoint_type == "list_messages":
            if not channel_type or not channel_url:
                raise ValueError("Channel type or channel url is empty in _construct_url method for list_messages")
            
            return LIST_MESSAGES_ENDPOINT.format(base_url=base_url, channel_type=channel_type, channel_url=channel_url)
        
        else:
            raise ValueError(f"Invalid type: {endpoint_type} in _construct_url method")

    def _create_headers(self):
        return {"Api-Token": f"{self.api_token}", "Content-Type": "application/json"}

    def _send_request(
        self, method: str, url: str, params: dict = None, body: dict = None
    ):
        response = requests.request(
            method, url, headers=self._create_headers(), params=params, data=body
        )

        if not response.ok:
            raise ValueError(f"Error in Sendbird API | Response: {response.json()}| "
                             f"status_code: {response.status_code}")

        json_response = response.json()

        return json_response

    def get_paginated_users_list(self, chunk_size: int = 20):
        """
        Fetch users from Sendbird API in chunks using pagination.

        Yields:
            list: A list of user dictionaries fetched from the Sendbird API.
        """

        url = self._construct_url("list_users")
        
        token = None
        params = {
            "active_mode": "all",  # This will return all users
            "limit": chunk_size,
        }

        while True:

            if token:
                params["token"] = token

            response = self._send_request("GET", url, params=params)
            
            token = response.get("next")
            users = response.get("users")

            yield users

            if not token:
                break

    def get_paginated_channels_list(self, channel_type: str = OPEN_CHANNELS_TYPE, chunk_size: int = 20):

        if channel_type == OPEN_CHANNELS_TYPE:
            url = self._construct_url("list_channels", channel_type=OPEN_CHANNELS_TYPE)

        elif channel_type == GROUP_CHANNELS_TYPE:
            url = self._construct_url("list_channels", channel_type=GROUP_CHANNELS_TYPE)

        else:
            raise ValueError(
                f"Invalid channel type: {channel_type} in list_channels method"
            )
        
        params = {
            "limit": chunk_size,  # Test this
        }

        token = None
        while True:

            if token:
                params["token"] = token  # Test this

            response = self._send_request("GET", url, params=params)

            token = response.get("next")
            channels = response.get("channels")

            yield channels

            if not token:
                break
    
    def get_paginated_messages(self, channel_type: str, channel_url: str, chunk_size: int = 10):
        """
        Get paginated messages data from the Sendbird v3 API.

        Yields:
            list: A list of message dictionaries fetched from the Sendbird API.
        """ 

        url = self._construct_url("list_messages", channel_type=channel_type, channel_url=channel_url)

        params = {
                    "include_reactions": "true",
                    "include_reply_type": "ONLY_REPLY_TO_CHANNEL",
                    "include_poll_details": "true",
                    "including_removed": "true",
                    "include_parent_message_info": "true",
                    "include": False,
                    "message_ts": 0,
                    "prev_limit": 0,
                    "next_limit": chunk_size,
                }
        
        while True:

            response = self._send_request("GET", url, params=params)

            messages = response.get('messages', [])
            if not messages:
                break

            # Update message_ts to the created_at of the last message in the current page
            params['message_ts'] = messages[-1]['created_at']

            yield messages

    def migrate_all_users(self, chunk_size: int = 20):

        for users in self.get_paginated_users_list(chunk_size):

            # Load up the users and validate them
            validated_users = Users(users=users).users

            # Migrate the users
            MigrateUsers(
                bot_id=self.bot_id, community_id=self.community_id, api_key=self.api_key,
                platform_code=self.platform_code, version_code=self.version_code, users_data=validated_users
            ).add_all_members_data()

            print(f"Successfully migrated users: {len(validated_users)}")

        return

    def migrate_all_channels(self):

        channel_types = [OPEN_CHANNELS_TYPE, GROUP_CHANNELS_TYPE]

        for channel_type in channel_types:

            # Migration of open channels
            for channels in self.get_paginated_channels_list(channel_type=channel_type):

                # Load up the channels and validate them
                validated_channels = Channels(channels=channels).channels

                # Migrate the channels
                MigrateChannels(
                    bot_id=self.bot_id, community_id=self.community_id, api_key=self.api_key, 
                    platform_code=self.platform_code, version_code=self.version_code, channels_data=validated_channels
                ).create_all_chatrooms()

                print(f"Successfully migrated {channel_type}/s: {len(channels)}")

    def migrate_all_messages(self):

        channel_types = [OPEN_CHANNELS_TYPE, GROUP_CHANNELS_TYPE]

        for channel_type in channel_types:
            
            # Fetch channels
            for channels in self.get_paginated_channels_list(channel_type=channel_type):

                for channel in channels:
                    channel_url = channel.get("channel_url")

                    # Fetch messages for each channel
                    for messages in self.get_paginated_messages(channel_type=channel_type, channel_url=channel_url):

                        # Add LM community_id to each message
                        messages = [{**message, "community_id": self.community_id} for message in messages]

                        # Load up the messages and validate them
                        validated_messages = Messages(messages=messages).messages

                        # Migrate the messages
                        MigrateMessages(
                            api_key=self.api_key, community_id=self.community_id, 
                            platform_code=self.platform_code, version_code=self.version_code, 
                            messages_data=validated_messages
                        ).create_all_messages()

                        print(f"Successfully migrated {len(messages)} messages for channel: {channel_url}")
        return

    def migrate_all_data(self):

        self.migrate_all_users()
        self.migrate_all_channels()
        self.migrate_all_messages()

        return
