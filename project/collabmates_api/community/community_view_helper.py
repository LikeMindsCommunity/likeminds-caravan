from togther.models import (ModelUtilities, Community, Members)
from utility.response_utilities import ResponseUtilities
from cms.cms_auth_utilities import CMSAuthUtilities
from collabmates_api.sdk.models import (SdkClient)
from utility.states import noti_states


class CommunityViewHelper:

    @staticmethod
    def validate_fetch_members_meta_request(user_id, community_id, api_key=None):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key/community ID")

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_edit_community_request(req_body, community_id, member_id, username, password):

        if not req_body:
            return ResponseUtilities.get_inner_error_context('In-valid request body')

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("In-valid community id")

        if member_id:

            user_instance = ModelUtilities.get_user_instance_or_none(member_id)

            if not user_instance:
                return ResponseUtilities.get_inner_error_context("In-valid member id")

        else:

            if not CMSAuthUtilities.validate_user(username, password):
                return ResponseUtilities.get_inner_error_context("In-valid username and password")

            members_filter = ModelUtilities.get_model_filter(Members,
                                                             {"community_id": community_instance,
                                                              "is_owner": True})

            if not members_filter:
                return ResponseUtilities.get_inner_error_context("Unable to find owner")

            user_instance = members_filter[0].member_id

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

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        is_admin = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_admin:
            return ResponseUtilities.get_inner_error_context("Invalid credentials")

        if req_body.get('user_unique_id'):
            user_body['user_unique_id'] = req_body.get('user_unique_id')

        if req_body.get('image_url'):
            user_body['image_url'] = req_body.get('image_url')

        return {'user_instance': user_instance, 'community_instance': community_instance,
                'user_body': user_body}

    @staticmethod
    def validate_update_community_member_request(user_id, api_key, req_body):

        if not req_body:
            return ResponseUtilities.get_inner_error_context("Invalid request body")

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        is_admin = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_admin:
            return ResponseUtilities.get_inner_error_context("Invalid credentials")

        member_instance = ModelUtilities.get_user_instance_or_none(req_body.get('user_unique_id'))

        if not member_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user_unique_id")

        is_community_member = Members.is_community_member(community_instance, member_instance)

        if not is_community_member:
            return ResponseUtilities.get_inner_error_context("User not part of community")

        return {'user_instance': user_instance, 'community_instance': community_instance,
                'member_instance': member_instance}

    @staticmethod
    def validate_update_community_noti_settings(user_id, community_id, req_body):

        if not req_body:
            return ResponseUtilities.get_inner_error_context("Invalid request body")

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community_id")

        is_admin = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_admin:
            return ResponseUtilities.get_inner_error_context("You are not CM/Owner of this community")

        noti_state = int(req_body.get('noti_state'))

        if not noti_state:
            return ResponseUtilities.get_inner_error_context("noti_state is required")

        if noti_state not in [ noti_states.ALL_MESSAGES, noti_states.ONLY_MENTIONS_AND_REPLIES ]:
            return ResponseUtilities.get_inner_error_context("invalid noti_state")

        return {'noti_state': noti_state, 'community_instance': community_instance}

    @staticmethod
    def validate_fetch_community_noti_settings(user_id, community_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community_id")

        is_admin = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_admin:
            return ResponseUtilities.get_inner_error_context("You are not CM/Owner of this community")

        return {'community_instance': community_instance}
