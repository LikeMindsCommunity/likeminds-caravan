from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities)
from collabmates_api.sdk.models import (SdkClient)


class UserViewHelper:

    @staticmethod
    def validate_create_user_bot_request(req_body):
        if 'community_name' not in req_body:
            return ResponseUtilities.get_error_context(False, 'Empty community name!')

        return {'success': True, 'community_name': req_body.get('community_name')}

    @staticmethod
    def validate_update_user_bot_request(user_id, req_body):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_error_context(False, 'Invalid user id!')

        if not req_body.get('community_name'):
            return ResponseUtilities.get_error_context(False, 'Empty community name!')

        return {'success': True, 'user_instance': user_instance, 'community_name': req_body.get('community_name')}

    @staticmethod
    def validate_fetch_user_bot_request(api_key):
        community_instance = SdkClient.get_community_instance_or_none(api_key)

        if not community_instance:
            return ResponseUtilities.get_error_context(False, 'Invalid API key!')

        return {'success': True, 'community_instance': community_instance}
