from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Members, Collabcard)
from collabmates_api.sdk.models import SdkClient
from rest_framework import status as status_codes


class ChatroomViewHelper:

    @staticmethod
    def validate_req_body(req_body):

        if not req_body:
            return ResponseUtilities.get_view_impl_error_context("Invalid request body",
                                                                 status_code=status_codes.HTTP_400_BAD_REQUEST)

        return {}

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

    @staticmethod
    def validate_edit_chatroom_request(user_id, card_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("Invalid chatroom id")

        is_cm = Members.is_member_community_promoter(card_instance.community, user_instance)

        if card_instance.user_id != user_instance.id and not is_cm:
            return ResponseUtilities.get_inner_error_context("You don’t have ability to update chatroom meta data")

        return {'user_instance': user_instance, 'card_instance': card_instance}
