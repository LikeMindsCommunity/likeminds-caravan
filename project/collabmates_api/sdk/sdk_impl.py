from rest_framework import status as status_codes

from .sdk_manager import SdkManager
from utility.response_utilities import ResponseUtilities
from utility.states import (api_types, login_types, question_states)
from utility.auth_utilities import AuthUtilities
from utility.version_utilities import VersionUtilities
from togther.models import (ModelUtilities, communityAnswers, Community, SDKClientUsersInfo)
from .models import SdkClient, SdkPlatform, SdkOnboardingScreen
from .sdk_view_helper import SdkViewHelper
from .serializers import SdkProjectSerializer, OnboardingScreenSerializer
from .constants import (GCP_SERVICE_ACCOUNT_PARAM)
from collabmates_api.community.community_impl import (CommunityImpl, CommunityHelper)
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
                 version_code: str = None, device_id: str = None, api_version_code: int = 0):
        self.member_id = member_id
        self.api_key = api_key
        self.request_platform = request_platform
        self.version_code = version_code
        self.device_id = device_id
        self.api_version_code = api_version_code

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

    def get_api_version_code(self) -> int:
        return self.api_version_code

    def fetch_sdk_project(self, request_params) -> dict:

        validated_request = SdkViewHelper.fetch_sdk_project_validator(request_params, self.get_member_id())

        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        filters = {
            'project_creator': validated_request.get('project_creator'),
            'is_deleted': False
        }

        api_key = self.get_api_key()

        if api_key:
            api_key_validation = AuthUtilities.validate_api_key(self.get_api_key())

            if 'error_message' in api_key_validation:
                return ResponseUtilities.get_impl_error_context(api_key_validation.get('error_message'),
                                                                api_key_validation.get('status'))

            sdk_client = api_key_validation.get('sdk_client')

            if sdk_client.project_creator != validated_request.get('project_creator'):
                return ResponseUtilities.get_impl_error_context('No projects found', status_codes.HTTP_404_NOT_FOUND)

            projects = [sdk_client]

        else:
            projects = ModelUtilities.get_model_filter(SdkClient, filters)

        return {'success': True, 'projects': SdkProjectSerializer(projects, many=True).data}

    def create_sdk_project(self, req_body) -> dict:

        validated_request_body = SdkViewHelper.create_sdk_project_body_validator(req_body, self.get_member_id())

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        req_body['type'] = api_types.SDK

        community_manager = CommunityImpl(self.get_member_id(),
                                          request_platform=self.get_request_platform(),
                                          version_code=self.get_version_code())
        create_community = community_manager.create_community(req_body)

        if 'error_message' in create_community:
            return ResponseUtilities.get_impl_error_context(create_community['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        unique_id = str(uuid.uuid4())
        community_id = create_community['community'].get('id')
        firebase_server_key = req_body.get('firebase_server_key', None)
        is_join_form_enabled = req_body.get('is_join_form_enabled', False)

        sdk_client = SdkClient(community_id=community_id, api_key=unique_id,
                               project_creator=validated_request_body.get('project_creator'),
                               firebase_server_key=firebase_server_key,
                               is_join_form_enabled=is_join_form_enabled)
        sdk_client.save()

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)
        user_instance = ModelUtilities.get_user_instance_or_none(self.get_member_id())

        if community_instance and user_instance:
            sdk_client_user_info_instance = SDKClientUsersInfo()
            sdk_client_user_info_instance.community = community_instance
            sdk_client_user_info_instance.user = user_instance
            sdk_client_user_info_instance.user_unique_id = user_instance.userinfo.user_unique_id
            sdk_client_user_info_instance.save()

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

        return {'success': True, 'api_key': unique_id}

    def edit_sdk_project(self, req_body) -> dict:

        validated_request_body = SdkViewHelper.edit_sdk_project_body_validator(req_body, self.get_member_id(),
                                                                               self.get_api_key())

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        api_key_validation = AuthUtilities.validate_api_key(self.get_api_key())

        if 'error_message' in api_key_validation:
            return ResponseUtilities.get_impl_error_context(api_key_validation.get('error_message'),
                                                            api_key_validation.get('status'))

        sdk_client = api_key_validation.get('sdk_client')

        is_cm = AuthUtilities.is_cm(sdk_client.community.id, self.get_member_id())

        if 'error_message' in is_cm:
            return ResponseUtilities.get_impl_error_context(is_cm.get('error_message'), is_cm.get('status'))

        if req_body.get(GCP_SERVICE_ACCOUNT_PARAM):
            sdk_client.firebase_service_account_file = req_body.get(GCP_SERVICE_ACCOUNT_PARAM)

        if req_body.get('firebase_server_key'):
            sdk_client.firebase_server_key = req_body.get('firebase_server_key')

        sdk_client.is_join_form_enabled = req_body.get('is_join_form_enabled')
        sdk_client.save()

        platforms = req_body.get('platform')

        if platforms:

            for platform in platforms:

                if None in [platform.get('type'), platform.get('package'), platform.get('certificate')]:
                    continue

                sdk_platforms = ModelUtilities.get_model_filter(SdkPlatform, {'community_id': sdk_client.community.id,
                                                                              'type': platform.get('type')})
                if sdk_platforms:
                    sdk_platform = sdk_platforms[0]
                    sdk_platform.package = platform.get('package')
                    sdk_platform.certificate = platform.get('certificate')
                    sdk_platform.save()

        community_manager = CommunityImpl(member_id=self.get_member_id(),
                                          community_id=sdk_client.community.id,
                                          request_platform=self.get_request_platform(),
                                          version_code=self.get_version_code())
        edit_community = community_manager.edit_community(validated_request_body.get('req_body'))

        if 'error_message' in edit_community:
            return ResponseUtilities.get_impl_error_context(edit_community['error_message'],
                                                            edit_community['status'])

        if req_body.get('name'):

            user_manager = UserImpl(user_id=self.get_member_id(), platform_code=self.get_request_platform(),
                                    version_code=self.get_version_code())
            update_bot = user_manager.update_user_bot({'name': req_body.get('name')})

            if 'error_message' in update_bot:
                return ResponseUtilities.get_impl_error_context(update_bot['error_message'],
                                                                update_bot['status'])

        return {'success': True}

    def delete_sdk_project(self) -> dict:

        validated_request_body = SdkViewHelper.delete_sdk_project_validator(self.get_member_id())

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        api_key_validation = AuthUtilities.validate_api_key(self.get_api_key())

        if 'error_message' in api_key_validation:
            return ResponseUtilities.get_impl_error_context(api_key_validation.get('error_message'),
                                                            api_key_validation.get('status'))

        sdk_client = api_key_validation.get('sdk_client')

        is_cm = AuthUtilities.is_cm(sdk_client.community.id, self.get_member_id())

        if 'error_message' in is_cm:
            return ResponseUtilities.get_impl_error_context(is_cm.get('error_message'), is_cm.get('status'))

        sdk_client.is_deleted = True
        sdk_client.save()

        return {'success': True}

    def initiate_sdk(self, req_body) -> dict:

        api_key_validation = AuthUtilities.validate_api_key(self.get_api_key())

        if 'error_message' in api_key_validation:
            return ResponseUtilities.get_impl_error_context(api_key_validation.get('error_message'),
                                                            api_key_validation.get('status'))

        sdk_client = api_key_validation.get('sdk_client')

        validated_request_body = SdkViewHelper.initiate_sdk_body_validator(sdk_client.community_id, req_body)

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        user_manager = UserImpl(user_id="", mobile_no="")
        login_user = user_manager.login(validated_request_body.get('login_req_body'), self.get_request_platform(),
                                        self.get_device_id(), self.get_version_code(), api_key=self.get_api_key())

        if 'error_message' in login_user:
            return ResponseUtilities.get_impl_error_context(login_user.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        user_object = login_user.get('user')
        app_access = login_user.get('app_access', True)

        response = {
            'success': True,
            'user': user_object,
            'community': CommunitySerializerV1(sdk_client.community, context={'send_community_settings': True}).data,
            'app_access': app_access,
            'has_answers': True
        }

        is_community_join_form = VersionUtilities.check_version(self.get_request_platform(), self.get_version_code(),
                                                                VersionUtilities.community_join_form)

        if is_community_join_form and sdk_client.is_join_form_enabled:
            filter_dict = {
                'community': sdk_client.community,
                'member': user_object.get('id')
            }

            exclude_filter_dict = {
                'question__question_state__in': [question_states.NAME, question_states.INTRODUCTION]
            }

            answers_filter = ModelUtilities.get_model_filter(communityAnswers, filter_dict).exclude(
                **exclude_filter_dict)

            if (not answers_filter) and (not req_body.get('question_answers')):
                response['has_answers'] = False
                return response

        if app_access:
            member_community_manager = MemberCommunityImpl(member_id=user_object.get('user_unique_id'),
                                                           community_id=sdk_client.community.id,
                                                           device_id=self.get_device_id(),
                                                           platform_code=self.get_request_platform(),
                                                           version_code=self.get_version_code(),
                                                           api_key=self.get_api_key(),
                                                           api_version_code=self.get_api_version_code())
            join_community_context = member_community_manager.join_community_sdk(
                validated_request_body.get('join_req_body'))

            if 'error_message' in join_community_context:
                return ResponseUtilities.get_impl_error_context(join_community_context.get('error_message'),
                                                                join_community_context.get('status'))

        req_body = validated_request_body.get('join_req_body')

        if req_body.get('image_url'):
            user_instance = ModelUtilities.get_user_instance_or_none(user_object.get('user_unique_id'))

            if user_instance:
                response['user']['image_url'] = user_instance.userinfo.image_link

        return response

    def fetch_sdk_user_info(self, uuid: str) -> dict:
        validated_request_body = SdkViewHelper.validate_fetch_sdk_user_info_request(self.member_id,
                                                                                          self.api_key,
                                                                                          uuid)

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request_body.get('community_instance')
        uuid_sdk_client_instance = validated_request_body.get('uuid_sdk_client_instance')

        user_impl = UserImpl(user_id="", mobile_no="")
        user_object = user_impl.compute_logged_in_user(uuid_sdk_client_instance.user.userinfo,
                                                       sdk_client_user_info_instance=uuid_sdk_client_instance)

        return {
            'success': True,
            'user': user_object,
            'community': CommunitySerializerV1(community_instance, context={'send_community_settings': True}).data,
            'app_access': validated_request_body.get('app_access', True)
        }

    def authenticate_sdk(self) -> dict:

        api_key_validation = AuthUtilities.validate_api_key(self.get_api_key())

        if 'error_message' in api_key_validation:
            return ResponseUtilities.get_impl_error_context(api_key_validation.get('error_message'),
                                                            api_key_validation.get('status'))

        sdk_client = api_key_validation.get('sdk_client')

        return {
            'success': True,
            'community_id': sdk_client.community_id
        }

    def fetch_onboarding_screens(self, req_params) -> dict:

        validated_request = SdkViewHelper.fetch_onboarding_screens_validator(req_params, self.get_api_key())

        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        screens = validated_request.get('onboarding_screens')

        return {'success': True, 'screens': OnboardingScreenSerializer(screens, many=True).data}

    def create_onboarding_screen(self, req_body) -> dict:

        validated_request = SdkViewHelper.create_onboarding_screen_validator(req_body, self.get_api_key(),
                                                                             self.get_member_id())

        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        community = validated_request.get('community_instance')
        user = validated_request.get('user_instance')

        is_cm = AuthUtilities.is_cm(community.id, user.id)

        if 'error_message' in is_cm:
            return ResponseUtilities.get_impl_error_context(is_cm.get('error_message'), is_cm.get('status'))

        screen = SdkOnboardingScreen(community=community, index=req_body.get('index'), image=req_body.get('image'),
                                     heading=req_body.get('heading'), text=req_body.get('text'),
                                     cta_colour=req_body.get('cta_colour'), cta_text=req_body.get('cta_text'))

        screen.save()

        return {'success': True}

    @staticmethod
    def _edit_onboarding_screen_instance(screen: SdkOnboardingScreen, req_body: dict):

        screen.index = req_body.get('index') if req_body.get('index') else screen.index
        screen.image = req_body.get('image') if req_body.get('image') else screen.image
        screen.heading = req_body.get('heading') if req_body.get('heading') else screen.heading
        screen.text = req_body.get('text') if req_body.get('text') else screen.text
        screen.cta_text = req_body.get('cta_text') if req_body.get('cta_text') else screen.cta_text
        screen.cta_colour = req_body.get('cta_colour') if req_body.get('cta_colour') else screen.cta_colour
        screen.save()

    def edit_onboarding_screen(self, req_body) -> dict:

        validated_request = SdkViewHelper.edit_onboarding_screen_validator(req_body, self.get_api_key(),
                                                                           self.get_member_id())

        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        community = validated_request.get('community_instance')
        user = validated_request.get('user_instance')
        screen = validated_request.get('screen_instance')

        is_cm = AuthUtilities.is_cm(community.id, user.id)

        if 'error_message' in is_cm:
            return ResponseUtilities.get_impl_error_context(is_cm.get('error_message'), is_cm.get('status'))

        self._edit_onboarding_screen_instance(screen, req_body)

        return {'success': True}

    def delete_onboarding_screen(self, req_body) -> dict:

        validated_request = SdkViewHelper.delete_onboarding_screen_validator(req_body, self.get_api_key(),
                                                                             self.get_member_id())

        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        community = validated_request.get('community_instance')
        user = validated_request.get('user_instance')
        screen = validated_request.get('screen_instance')

        is_cm = AuthUtilities.is_cm(community.id, user.id)

        if 'error_message' in is_cm:
            return ResponseUtilities.get_impl_error_context(is_cm.get('error_message'), is_cm.get('status'))

        screen.delete()

        return {'success': True}
