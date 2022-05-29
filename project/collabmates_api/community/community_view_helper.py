from togther.models import (ModelUtilities)
from collabmates_api.sdk.models import (SdkClient)
from utility.response_utilities import ResponseUtilities


class CommunityViewHelper:

    @staticmethod
    def validate_fetch_members_meta_request(user_id, community_id, api_key=None):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_id = community_id if community_id else api_key
        community_instance = SdkClient.get_community_instance_or_none(community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key/community ID")

        return {'user_instance': user_instance, 'community_instance': community_instance}
