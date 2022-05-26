from rest_framework import status as status_codes
from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Community)


class MemberCommunityViewHelper:

    @staticmethod
    def validate_join_community_request(member_id, req_body):
        if not req_body:
            return ResponseUtilities.get_impl_error_context("Invalid request body",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        if not member_id:
            return ResponseUtilities.get_impl_error_context("Query params missing",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        if not req_body.get('community_id'):
            return ResponseUtilities.get_impl_error_context("Query params missing",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        return {}

    @staticmethod
    def validate_join_community_sdk_request(user_id, community_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID")

        return {'user_instance': user_instance, 'community_instance': community_instance}
