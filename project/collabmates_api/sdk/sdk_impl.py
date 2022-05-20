from rest_framework import status as status_codes

from .sdk_manager import SdkManager
from utility.response_utilities import ResponseUtilities
from utility.states import api_types
from utility.auth_utilities import AuthUtilities
from togther.models import ModelUtilities
from .models import SdkClient, SdkPlatform
from collabmates_api.community.community_impl import CommunityImpl
from collabmates_api.user.view_impl import UserImpl
from collabmates_api.member_community.member_community_impl import MemberCommunityImpl
from collabmates_api.rest_api import CommunitySerializerV1
import uuid


class SdkImpl(SdkManager):

    member_id = None
    api_key = None
    request_platform = None
    version_code = None
    device_id = None

    def __init__(self, member_id: str = None, api_key: str = None, request_platform: str = None,
                 version_code: str = None, device_id: str = None):
        self.member_id = member_id
        self.api_key = api_key
        self.request_platform = request_platform
        self.version_code = version_code
        self.device_id = device_id

    def get_member_id(self) -> str:
        return self.member_id

    def get_api_key(self) -> str:
        return self.api_key

    def get_request_platform(self) -> str:
        return self.request_platform

    def get_version_code(self) -> str:
        return self.version_code

    def get_device_id(self) -> str:
        return self.device_id

    def create_sdk(self, req_body) -> dict:

        req_body['type'] = api_types.SDK

        community_manager = CommunityImpl(self.get_member_id(),
                                          request_platform=self.get_request_platform(),
                                          version_code=self.get_version_code())
        create_community = community_manager.create_community(req_body)

        if 'error_message' in create_community:
            return ResponseUtilities.get_impl_error_context('Community Creation Failed',
                                                            status_codes.HTTP_400_BAD_REQUEST)

        unique_id = str(uuid.uuid4())
        community_id = create_community['community'].get('id')

        sdk_client = SdkClient(community_id=community_id, api_key=unique_id)
        sdk_client.save()

        platforms = req_body.get('platform')

        if platforms:

            for platform in platforms:

                if None in [platform.get('type'), platform.get('package'), platform.get('certificate')]:
                    continue

                sdk_platform = SdkPlatform(community_id=community_id,
                                           type=platform.get('type'),
                                           package=platform.get('package'),
                                           certificate=platform.get('certificate'))
                sdk_platform.save()

        return {'api_key': unique_id}

    def initiate_sdk(self, req_body) -> dict:

        api_key_validation = AuthUtilities.validate_api_key(self.get_api_key())

        if 'error_message' in api_key_validation:
            return ResponseUtilities.get_impl_error_context(api_key_validation.get('error_message'),
                                                            api_key_validation.get('status'))

        sdk_client = api_key_validation.get('sdk_client')

        req_body['type'] = str(api_types.SDK)

        user_manager = UserImpl(user_id="", mobile_no="")
        login_user = user_manager.login(req_body, self.get_request_platform(), self.get_device_id(),
                                        self.get_version_code(), api_key=self.get_api_key())

        if not login_user.get('success'):
            return ResponseUtilities.get_impl_error_context('Unable to login/sign-up!',
                                                            status_codes.HTTP_400_BAD_REQUEST)

        user_instance = login_user.get('user')

        member_community_manager = MemberCommunityImpl(user_instance.get('id'),
                                                       community_id=sdk_client.community.id,
                                                       device_id=self.get_device_id(),
                                                       platform_code=self.get_request_platform())
        join_community_context = member_community_manager.join_community_sdk()

        if not join_community_context.get('success'):
            return ResponseUtilities.get_impl_error_context('Unable to join community!',
                                                            status_codes.HTTP_400_BAD_REQUEST)

        return {'user': user_instance, 'community': CommunitySerializerV1(sdk_client.community).data}

    def authenticate_sdk(self) -> dict:

        api_key_validation = AuthUtilities.validate_api_key(self.get_api_key())

        if 'error_message' in api_key_validation:
            return ResponseUtilities.get_impl_error_context(api_key_validation.get('error_message'),
                                                            api_key_validation.get('status'))

        sdk_client = api_key_validation.get('sdk_client')

        return {'success': True, 'community_id': sdk_client.community_id}
