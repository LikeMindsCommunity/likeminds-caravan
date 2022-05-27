from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities)
from collabmates_api.sdk.models import SdkClient


class ChatroomViewHelper:

    @staticmethod
    def validate_fetch_all_chatroom_request(user_id, api_key):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        return {'user_instance': user_instance, 'community_instance': community_instance}
