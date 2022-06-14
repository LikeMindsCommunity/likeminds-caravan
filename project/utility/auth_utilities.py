from rest_framework import status as status_codes
from .response_utilities import ResponseUtilities
from .states import member_states
from togther.models import ModelUtilities, User, Community, Members
from collabmates_api.sdk.models import SdkClient


class AuthUtilities:

    @staticmethod
    def is_cm(community_id, member_id):

        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not user_instance:
            return ResponseUtilities.get_impl_error_context('invalid user_id', status_codes.HTTP_404_NOT_FOUND)

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return ResponseUtilities.get_impl_error_context('invalid community_id', status_codes.HTTP_404_NOT_FOUND)

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_id,
                                                                  'member_id': user_instance})

        if not member_filter:
            return ResponseUtilities.get_impl_error_context('User is not a member of community',
                                                            status_codes.HTTP_403_FORBIDDEN)

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return ResponseUtilities.get_impl_error_context('You are not the owner/CM of community',
                                                            status_codes.HTTP_403_FORBIDDEN)

        return {'success': True}

    @staticmethod
    def validate_api_key(api_key):

        if not api_key:
            return ResponseUtilities.get_impl_error_context('Send x-api-key in headers',
                                                            status_codes.HTTP_400_BAD_REQUEST)

        sdk_clients = ModelUtilities.get_model_filter(SdkClient, {'api_key': api_key, 'is_deleted': False})

        if not sdk_clients:
            return ResponseUtilities.get_impl_error_context('Invalid API key', status_codes.HTTP_400_BAD_REQUEST)

        return {'success': True, 'sdk_client': sdk_clients[0]}
