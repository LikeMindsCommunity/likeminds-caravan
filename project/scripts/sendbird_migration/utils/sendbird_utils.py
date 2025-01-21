import requests

from ..constants import (
    SENDBIRD_API_BASE_URL,
    ENDPOINT_TYPE_LIST_USERS,
    ENDPOINT_TYPE_LIST_CHANNELS,
    ENDPOINT_TYPE_LIST_MESSAGES,
    ENDPOINT_TYPE_LIST_POLL_OPTIONS,
    ENDPOINT_TYPE_LIST_POLL_VOTERS,
    LIST_USERS_ENDPOINT,
    LIST_CHANNELS_ENDPOINT,
    LIST_MESSAGES_ENDPOINT,
    LIST_POLL_OPTIONS,
    LIST_POLL_VOTERS_ENDPOINT,
    OPEN_CHANNELS_TYPE,
    GROUP_CHANNELS_TYPE,
)


class SendbirdApiUtils:

    application_id: str = ""
    api_token: str = ""

    base_url = ""

    def __init__(self, application_id: str, api_token: str):

        self.application_id = application_id
        self.api_token = api_token

        self._validate()

        self.base_url = SENDBIRD_API_BASE_URL.format(application_id)

    def _validate(self):

        if not self.application_id or not self.api_token:
            raise ValueError("Application ID/Api Token is empty!")

        # Fetch users to validate the API token
        url = self._construct_url(ENDPOINT_TYPE_LIST_USERS)

        # Raise Exception if response is not 200
        self._send_request("GET", url)

    def _construct_url(
        self,
        endpoint_type: str,
        channel_type: str = None,
        channel_url: str = None,
        poll_id: str = None,
        poll_option_id: str = None,
    ):

        base_url = self.base_url

        if endpoint_type == ENDPOINT_TYPE_LIST_USERS:
            return LIST_USERS_ENDPOINT.format(base_url=base_url)

        elif endpoint_type == ENDPOINT_TYPE_LIST_CHANNELS:
            if not channel_type:
                raise ValueError(
                    "Channel type is empty in _construct_url method for list_channels"
                )

            return LIST_CHANNELS_ENDPOINT.format(
                base_url=base_url, channel_type=channel_type
            )

        elif endpoint_type == ENDPOINT_TYPE_LIST_MESSAGES:
            if not channel_type or not channel_url:
                raise ValueError(
                    "Channel type or channel url is empty in _construct_url method for list_messages"
                )

            return LIST_MESSAGES_ENDPOINT.format(
                base_url=base_url, channel_type=channel_type, channel_url=channel_url
            )

        elif endpoint_type == ENDPOINT_TYPE_LIST_POLL_OPTIONS:
            if not poll_id:
                raise ValueError(
                    "Poll ID is empty in _construct_url method for list_poll_options"
                )

            return LIST_POLL_OPTIONS.format(base_url=base_url, poll_id=poll_id)

        elif endpoint_type == ENDPOINT_TYPE_LIST_POLL_VOTERS:
            if not poll_id or not poll_option_id:
                raise ValueError(
                    "Poll ID or Poll Option ID is empty in _construct_url method for list_poll_voters"
                )

            return LIST_POLL_VOTERS_ENDPOINT.format(
                base_url=base_url, poll_id=poll_id, poll_option_id=poll_option_id
            )

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
            raise ValueError(
                f"Error in Sendbird API | Response: {response.json()} | status_code: {response.status_code}"
            )

        json_response = response.json()

        return json_response

    @staticmethod
    def validate_sendbird_creds(application_id: str, api_token: str) -> dict :

        if not application_id or not api_token:
            return {"error_message": "Application ID/Api Token is empty!"}

        base_url = SENDBIRD_API_BASE_URL.format(application_id)
        list_users_endbpoint = LIST_USERS_ENDPOINT.format(base_url=base_url)

        response = requests.request(
            "GET", list_users_endbpoint, headers={"Api-Token": api_token}
        )

        if not response.ok:
            return {
                "error_message": f"Error in Sendbird API | Response: {response.json()} | status_code: {response.status_code}"
            }

        return {}

    def yield_paginated_users_list(self, chunk_size: int = 20):

        url = self._construct_url(ENDPOINT_TYPE_LIST_USERS)
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

    def yield_paginated_channels_list(
        self, channel_type: str = OPEN_CHANNELS_TYPE, chunk_size: int = 20
    ):

        if channel_type == OPEN_CHANNELS_TYPE:
            url = self._construct_url(
                ENDPOINT_TYPE_LIST_CHANNELS, channel_type=OPEN_CHANNELS_TYPE
            )

        elif channel_type == GROUP_CHANNELS_TYPE:
            url = self._construct_url(
                ENDPOINT_TYPE_LIST_CHANNELS, channel_type=GROUP_CHANNELS_TYPE
            )

        else:
            raise ValueError(
                f"Invalid channel type: {channel_type} in list_channels method"
            )

        params = {
            "limit": chunk_size,
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

    def yield_paginated_messages(
        self, channel_type: str, channel_url: str, chunk_size: int = 10
    ):

        url = self._construct_url(
            ENDPOINT_TYPE_LIST_MESSAGES,
            channel_type=channel_type,
            channel_url=channel_url,
        )

        params = {
            "include_reactions": "true",  # Include reactions in the message
            "include_reply_type": "ONLY_REPLY_TO_CHANNEL",  # Include Only channel replies and no threaded messages
            "include_poll_details": "true",  # Include poll details in the message (Options,etc)
            "including_removed": "true",  # Include removed messages
            "include_parent_message_info": "true",  # Include parent message info in the message
            "include": False,  # Do not include message_ts message
            "message_ts": 0,  # Message timestamp to fetch messages after
            "prev_limit": 0,  # Do not include previous messages
            "next_limit": chunk_size,  # Fetch next N messages
        }

        while True:

            response = self._send_request("GET", url, params=params)

            messages = response.get("messages", [])
            if not messages:
                break

            # Update message_ts to the created_at of the last message in the current page
            params["message_ts"] = messages[-1]["created_at"]

            yield messages

    def yield_poll_voters_for_option(self, poll_id: str, poll_option_id: str):

        if not poll_id or not poll_option_id:
            raise ValueError(
                "Poll ID or Poll Option ID is empty in get_poll_voters_for_option method"
            )

        list_poll_voters_endpoint = self._construct_url(
            endpoint_type=ENDPOINT_TYPE_LIST_POLL_VOTERS,
            poll_id=poll_id,
            poll_option_id=poll_option_id,
        )

        params = {
            "limit": 100,
        }

        while True:

            response = self._send_request(
                "GET", list_poll_voters_endpoint, params=params
            )

            poll_voters = response.get("voters", [])
            if not poll_voters:
                break

            params["token"] = response.get("next")

            yield poll_voters

        return response

    def get_poll_options(self, poll_id: str):

        if not poll_id:
            raise ValueError("Poll ID is empty in get_poll_options method")

        list_poll_options_endpoint = self._construct_url(
            endpoint_type=ENDPOINT_TYPE_LIST_POLL_OPTIONS, poll_id=poll_id
        )

        response = self._send_request("GET", list_poll_options_endpoint)

        return response.get("options", [])
