from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Members)
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

    @staticmethod
    def validate_create_chatroom_request(user_id, api_key, req_body):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_id = req_body.get('community_id') if req_body.get('community_id') else api_key
        community_instance = SdkClient.get_community_instance_or_none(community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key/community ID")

        is_member = Members.is_community_member(community_instance, user_instance)

        if not is_member:
            return ResponseUtilities.get_inner_error_context("You cannot create a chatroom")

        return {'user_instance': user_instance, 'community_instance': community_instance}
