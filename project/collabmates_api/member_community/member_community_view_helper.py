from rest_framework import status as status_codes
from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Community)
from collabmates_api.sdk.models import (SdkClient)


class MemberCommunityViewHelper:

    @staticmethod
    def validate_join_community_request(member_id):
        if not member_id:
            return ResponseUtilities.get_impl_error_context("Empty member-id",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        return {}

    @staticmethod
    def validate_join_community_sdk_request(user_id, community_id, api_key):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID")

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_fetch_feed_request(user_id, community_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID")

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_fetch_member_profile_request(current_user_id, user_id, community_id):
        current_user_instance = ModelUtilities.get_user_instance_or_none(current_user_id)

        if not current_user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid x-member-id")

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID")

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        return {'user_instance': user_instance, 'community_instance': community_instance,
                'current_user_instance': current_user_instance}
