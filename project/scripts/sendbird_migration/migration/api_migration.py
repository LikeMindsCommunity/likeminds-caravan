import requests

from ..constants import APPLICATION_ID, API_TOKEN, LIKEMINDS_API_KEY, PLATFORM_CODE, VERSION_CODE, SENDBIRD_API_BASE_URL
from ..models.user import Users
from ..models.channel import Channels
from ..utils.migrate_users import MigrateUsers
from ..utils.migrate_channels import MigrateChannels

from collabmates_api.sdk.models import SdkClient
from togther.models import ModelUtilities
from collabmates_api.user.user_impl import UserImpl


class SendbirdMigration:

    api_key: str = LIKEMINDS_API_KEY
    application_id: str = APPLICATION_ID
    api_token: str = API_TOKEN

    platform_code: str = PLATFORM_CODE
    version_code: str = VERSION_CODE

    community_id: int = None
    bot_id: int = None

    base_url = ""
    endpoints = {}

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
        
        self.endpoints = {
            "list_users": f"{self.base_url}/users",
            "list_open_channels": f"{self.base_url}/open_channels",
            "list_group_channels": f"{self.base_url}/group_channels",
        }
        
        self.community_id = self.get_community_from_api_key()
        self.bot_id = self.get_bot_id_from_bot_uuid()


    def get_community_from_api_key(self):
        if not self.api_key:
            raise ValueError(
                "LikeMinds API key not defined. Create a community using LikeMinds dashboard first."
            )

        sdk_filter = ModelUtilities.get_model_filter(
            SdkClient, {"api_key": self.api_key}
        )

        if not sdk_filter:
            raise ValueError("Invalid API key!")
        
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
        
    def _create_headers(self):
        return {"Api-Token": f"{self.api_token}", "Content-Type": "application/json"}

    def _send_request(
        self, method: str, url: str, params: dict = None, body: dict = None
    ):
        # print(
        #     f"Sending request to URL: {url}, method: {method}, params: {params}, body: {body}"
        # )
        response = requests.request(
            method, url, headers=self._create_headers(), params=params, data=body
        )

        if not response.ok:
            raise ValueError(f"Error in Sendbird API | Response: {response.json()}| status_code: {response.status_code}")

        json_response = response.json()

        return json_response

    def list_users(self, chunk_size: int = 20):
        """
        Fetch users from Sendbird API in chunks using pagination.

        Yields:
            list: A list of user dictionaries fetched from the Sendbird API.
        """
        token = None

        while True:
            url = self.endpoints.get("list_users")

            params = {
                "active_mode": "all", # This will return all users
                "limit": chunk_size,
            }

            if token:
                params["token"] = token

            response = self._send_request("GET", url, params=params)
            
            token = response.get("next")
            users = response.get("users")

            yield users

            if not token:
                break

    def list_channels(self, channel_type: str = "open_channel", chunk_size: int = 20):

        token = None

        while True:
            if channel_type == "open_channel":
                url = self.endpoints.get("list_open_channels")

            elif channel_type == "group_channel":
                url = self.endpoints.get("list_group_channels")

            else:
                raise ValueError(
                    f"Invalid channel type: {channel_type} in list_channels method"
                )
            
            params = {
                "limit": chunk_size, #Test this
            }

            if token:
                params["token"] = token #test this
                

            response = self._send_request("GET", url, params=params)

            token = response.get("next")
            channels = response.get("channels")

            yield channels

            if not token:
                break
    
    def migrate_all_users(self, chunk_size: int = 20):

        for users in self.list_users(chunk_size):

            # Load up the users and validate them
            validated_users = Users(users=users).users

            # Migrate the users
            MigrateUsers(
                bot_id=self.bot_id, community_id=self.community_id, api_key=self.api_key, platform_code=self.platform_code,
                 version_code=self.version_code, users_data=validated_users
            ).add_all_members_data()

            print(f"Successfully migrated users: {len(validated_users)}")

        return

    def migrate_all_channels(self):

        channel_types = ["open_channel", "group_channel"]

        for channel_type in channel_types:

            # Migration of open channels
            for channels in self.list_channels(channel_type=channel_type):

                # Load up the channels and validate them
                validated_channels = Channels(channels=channels).channels

                # Migrate the channels
                MigrateChannels(
                    bot_id=self.bot_id, community_id=self.community_id, api_key=self.api_key, 
                    platform_code=self.platform_code, version_code=self.version_code, channels_data=validated_channels
                ).create_all_chatrooms()

                print(f"Successfully migrated {channel_type}/s: {len(channels)}")


    def migrate_all_data(self):

        self.migrate_all_users()
        self.migrate_all_channels()

        return



