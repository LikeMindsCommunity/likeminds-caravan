from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities)
from collabmates_api.sdk.models import (SdkClient)
from rest_framework import status as status_codes


class UserViewHelper:

    @staticmethod
    def validate_user_bot_request_body(req_body):

        if not req_body:
            return ResponseUtilities.get_impl_error_context("Invalid request body",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        return {}

    @staticmethod
    def validate_create_user_bot_request(req_body):
        if 'community_name' not in req_body:
            return ResponseUtilities.get_inner_error_context('Empty community name!')

        return {'community_name': req_body.get('community_name')}

    @staticmethod
    def validate_update_user_bot_request(user_id, req_body):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context('Invalid user id!')

        if not req_body.get('community_name'):
            return ResponseUtilities.get_inner_error_context('Empty community name!')

        return {'user_instance': user_instance, 'community_name': req_body.get('community_name')}

    @staticmethod
    def validate_fetch_user_bot_request(api_key):
        community_instance = SdkClient.get_community_instance_or_none(api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context('Invalid API key!')

        return {'community_instance': community_instance}
