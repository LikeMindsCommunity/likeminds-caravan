from rest_framework import status as status_codes
from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Community)
from collabmates_api.sdk.models import (SdkClient)
from utility.states import (unsubscribe_types)


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

        community_id = community_id if community_id else api_key

        community_instance = SdkClient.get_community_instance_or_none(community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID")

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_unsubscribe_email_notifications_request(user_id, community_id, req_body):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID")

        if (not req_body.get('code_flag')) or (not isinstance(req_body.get('code_flag'), dict)) or \
                (set(req_body.get('code_flag').keys()) - {unsubscribe_types.MAIL_EVENT_NOTIFICATIONS,
                                                          unsubscribe_types.MAIL_CHATROOM_OR_DM}):
            return ResponseUtilities.get_inner_error_context("Invalid Invalid code flag object!")

        return {'user_instance': user_instance, 'community_instance': community_instance,
                'code_flag': req_body.get('code_flag')}
