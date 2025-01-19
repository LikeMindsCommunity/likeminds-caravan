import requests

from ..constants import APPLICATION_ID, API_TOKEN, LIKEMINDS_API_KEY, PLATFORM_CODE, VERSION_CODE
from ..models.user import Users
from ..utils.migrate_users import MigrateUsers

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

    base_url = f"https://api-{APPLICATION_ID}.sendbird.com/v3"

    ENDPOINTS = {
        "list_users": f"{base_url}/users",
        "list_open_channels": f"{base_url}/open_channels",
        "list_group_channels": f"{base_url}/group_channels",
    }

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

        self.base_url = f"https://api-{self.application_id}.sendbird.com/v3"

        if not self.base_url or not self.api_token:
            raise ValueError("Base Url/Api Token is empty!")
        
        self.community_id = self.get_community_from_api_key()
        self.bot_id = self.get_bot_id_from_bot_uuid()

        return self

    def get_community_from_api_key(self):
        if not self.api_key:
            raise ValueError(
                "LikeMinds API key not defined. Create a community using LikeMinds dashboard first."
            )

        sdk_filter = ModelUtilities.get_model_filter(
            SdkClient, {"api_key": LIKEMINDS_API_KEY}
        )

        if not sdk_filter:
            raise ValueError("Invalid API key!")
        
        return sdk_filter.first().community_instance.id

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
        
    def _create_headers(self):
        return {"Api-Token": f"{self.api_token}", "Content-Type": "application/json"}

    def _send_request(
        self, method: str, url: str, params: dict = None, body: dict = None
    ):
        print(
            f"Sending request to URL: {url}, method: {method}, params: {params}, body: {body}"
        )
        response = requests.request(
            method, url, headers=self._create_headers(), params=params, data=body
        )

        if not response.ok:
            print(f"Error in response: {response.json()}")

        json_response = response.json()

        return json_response

    def list_users(self):
        """
        Fetch users from Sendbird API in chunks using pagination.

        Yields:
            list: A list of user dictionaries fetched from the Sendbird API.
        """
        token = None

        while True:
            url = self.ENDPOINTS.get("list_users")

            params = {
                "active_mode": "all", # This will return all users
                "limit": 20,
            }

            if token:
                params["token"] = token

            response = self._send_request("GET", url, params=params)

            print(response) #TODO: Remove this
            
            token = response.get("next")
            users = response.get("users")

            yield users

            if not token:
                break

    def list_channels(self, channel_type: str = "open_channel"):
        should_break_loop = False
        token = ""

        while not should_break_loop:
            if channel_type == "open_channel":
                url = self.ENDPOINTS.get("list_open_channels")

            elif channel_type == "group_channel":
                url = self.ENDPOINTS.get("list_group_channels")

            else:
                raise ValueError(
                    f"Invalid channel type: {channel_type} in list_channels method"
                )

            if token:
                url += f"&token={token}"

            response = self._send_request("GET", url)
            token = response.get("next")

            if not token:
                should_break_loop = True

            for user_dict in response.get("users"):
                print(user_dict)
                print("*" * 50)
    
    def migrate_users(self):

        for users in self.list_users():
            print(users)

            # Load up the users and validate them
            validated_users = Users(users).users

            MigrateUsers(
                bot_id=self.bot_id, community_id=self.community_id, users_data=validated_users
            ).add_all_members_data()

            print(f"Successfully migrated users: {validated_users}")

        return
    
    def migrate_all_data(self):

        self.migrate_users()
        # self.list_channels(channel_type="open_channel")
        # self.list_channels(channel_type="group_channel")
        return



