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

    @staticmethod
    def validate_add_community_member_request(user_id, api_key, req_body):

        if not req_body:
            return ResponseUtilities.get_inner_error_context("Invalid request body")

        if not req_body.get('user_name'):
            return ResponseUtilities.get_inner_error_context("Empty user name!")

        user_body = {
            "name": req_body.get('user_name')
        }

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        if req_body.get('user_unique_id'):
            user_body['user_unique_id'] = req_body.get('user_unique_id')

        if req_body.get('image_url'):
            user_body['image_url'] = req_body.get('image_url')

        return {'user_instance': user_instance, 'community_instance': community_instance,
                'user_body': user_body}
