import requests

from ..constants import APPLICATION_ID


class SendbirdMigration:
    BASE_URL = f"https://api-{APPLICATION_ID}.sendbird.com/v3"
    API_TOKEN = "441ddd489a87926711df7e8e6c473af1fca1c532"

    ENDPOINTS = {
        "list_users": f"{BASE_URL}/users?active_mode=all",
        "list_open_channels": f"{BASE_URL}/open_channels",
        "list_group_channels": f"{BASE_URL}/group_channels",
    }

    def __init__(self):
        # Validating the
        self._validate()

    def _create_headers(self):
        return {"Api-Token": f"{self.API_TOKEN}", "Content-Type": "application/json"}

    def _send_request(
        self, method: str, url: str, params: dict = None, body: dict = None
    ):
        print(
            f"Sending request to URL: {url}, method: {method}, params: {params}, body: {body}"
        )
        response = requests.request(
            method, url, headers=self._create_headers(), params=params, data=body
        )

        json_response = response.json()

        return json_response

    @staticmethod
    def _validate():
        if not APPLICATION_ID:
            raise ValueError("Application ID is empty!")

    def list_users(self):
        should_break_loop = False
        token = ""

        while not should_break_loop:
            url = self.ENDPOINTS.get("list_users")

            if token:
                url += f"&token={token}"

            response = self._send_request("GET", url)
            token = response.get("next")

            if not token:
                should_break_loop = True

            for user_dict in response.get("users"):
                print(user_dict)
                print("*" * 50)

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
