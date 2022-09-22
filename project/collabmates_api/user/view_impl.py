import json
from django.http import JsonResponse
from rest_framework.views import APIView

from collabmates_api.utility import single_community_view_version_check
from utility.exception_utilities import InvalidHeaderException
from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from cms.cms_auth_utilities import CMSAuthUtilities
from django.conf import settings
from collabmates_api.user.user_impl import UserImpl
from collabmates_api.user.user_view_helper import UserViewHelper
from rest_framework import status as status_codes


class DeleteUserView(APIView):
    '''inheriting API view class for using class based views in django'''

    def post(self, request):

        if settings.IS_BETA:

            request_body = RequestUtilities.fetch_request_body(request)
            request_values = self.process_request_body(request_body)
            user_manager = UserImpl(user_id=request_values[0], mobile_no=request_values[1])
            user_deleted = user_manager.delete_user()

            if user_deleted:
                return JsonResponse({'success': True})

            return JsonResponse({
                'success': False,
                'error_message': "credentials not found"
            }, status=400)

        else:
            api_response = {
                'success': False,
                'error_message': "resource not found"
            }
            return JsonResponse(api_response, status=404)

    def process_request_body(self, request_body):

        user_id = None
        mobile_no = None

        if 'user_id' in request_body and request_body['user_id']:
            user_id = request_body['user_id']

        elif 'mobile_no' in request_body and request_body['mobile_no']:
            mobile_no = request_body['mobile_no']

        return user_id, mobile_no


class UserSeenSurvey(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        user_manager = UserImpl(user_id=member_id, mobile_no="")
        user_context = user_manager.survey_seen()

        if user_context.get('error_message'):
            return JsonResponse(user_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(user_context)


class UserLogout(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        user_manager = UserImpl(user_id=member_id, mobile_no="")
        device_id = RequestUtilities.get_device_id_from_headers(request)

        user_context = user_manager.logout(device_id)

        if not user_context.get('error_message'):
            return JsonResponse(user_context)

        return JsonResponse(**ResponseUtilities.get_view_impl_error_context(user_context.get('error_message'),
                                                                            user_context.get('status')))


class UserRemoveProfile(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        user_manager = UserImpl(user_id=member_id, mobile_no="")
        user_context = user_manager.remove_profile()

        if user_context.get('error_message'):
            return JsonResponse(user_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(user_context)


class UserLoginView(APIView):

    def post(self, request):
        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False,
                                 'error_message': "Invalid request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        user_manager = UserImpl(user_id="",
                                mobile_no="")
        user_context = user_manager.login(req_body,
                                          RequestUtilities.get_platform_code(request),
                                          RequestUtilities.get_device_id_from_headers(request),
                                          RequestUtilities.get_version_code_from_headers(request),
                                          api_key=RequestUtilities.get_api_key_from_headers(request))

        if user_context.get('error_message'):
            return JsonResponse(user_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(user_context)


class FetchUserAccess(APIView):
    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        user_manager = UserImpl(user_id=member_id, mobile_no="")
        user_context = user_manager.fetch_app_access()

        return JsonResponse(user_context)


class FetchDmHome(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id = request.GET.get('community_id', None)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        if single_community_view_version_check(platform_code, version_code):
            if not (community_id or api_key):
                return JsonResponse({
                    'status': status_codes.HTTP_400_BAD_REQUEST,
                    'success': False,
                    'error_message': 'missing required parameter: community_id'
                })

        user_manager = UserImpl(user_id=member_id,
                                community_id=community_id,
                                platform_code=platform_code,
                                version_code=version_code,
                                api_key=api_key)
        user_context = user_manager.fetch_dm_home()

        if 'error_message' in user_context:
            response_context = user_context

            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(user_context)


class UpdateDmTutorial(APIView):

    def post(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'error_message': "Invalid request body"}, status=status_codes.HTTP_400_BAD_REQUEST)

        user_manager = UserImpl(user_id=member_id)
        update_dm_tutorial = user_manager.update_dm_tutorial(req_body)

        if 'error_message' in update_dm_tutorial:
            response_context = update_dm_tutorial

            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(update_dm_tutorial)


class FetchDmFeed(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        community_id: str = request.GET.get('community_id')

        user_manager = UserImpl(user_id=member_id, community_id=community_id, api_key=api_key)
        user_context = user_manager.fetch_dm_feed()

        if 'error_message' in user_context:
            response_context = user_context

            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(user_context)


class FetchAllUsers(APIView):
    """
    Fetch all the users
    """

    def get(self, request):
        page = RequestUtilities.get_page_number(request, default=1)

        try:
            user_ids = json.loads(request.GET.get('user_ids'))

        except:
            user_ids = None

        user_name, password = CMSAuthUtilities.get_username_and_password_from_headers(request)

        if not CMSAuthUtilities.validate_user(user_name, password):
            return JsonResponse({
                'success': False,
                'error_message': 'user name and password does not match'
            }, status=status_codes.HTTP_401_UNAUTHORIZED)

        user_manager = UserImpl(user_id=None)
        user_response = user_manager.fetch_all_users(page=page, user_ids=user_ids)

        if 'error_message' in user_response:
            return JsonResponse({
                'success': False,
                'error_message': user_response['error_message']
            }, status=user_response['status'])

        return JsonResponse(user_response)


class BotView(APIView):

    def post(self, request):
        req_body = RequestUtilities.load_request_body(request)
        platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        context = UserViewHelper.validate_user_bot_request_body(req_body)

        if context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                                context.get('status')))

        user_manager = UserImpl(user_id=None, platform_code=platform, version_code=version_code)
        context = user_manager.create_user_bot(req_body)

        if context.get('success'):
            return JsonResponse(context, status=status_codes.HTTP_200_OK)

        return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                            context.get('status')))

    def put(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)
        platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        context = UserViewHelper.validate_user_bot_request_body(req_body)

        if context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                                context.get('status')))

        user_manager = UserImpl(user_id=member_id, platform_code=platform, version_code=version_code)
        context = user_manager.update_user_bot(req_body)

        if context.get('success'):
            return JsonResponse(context, status=status_codes.HTTP_200_OK)

        return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                            context.get('status')))

    def get(self, request):
        platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        user_manager = UserImpl(user_id=None, platform_code=platform, version_code=version_code)
        context = user_manager.fetch_user_bot(api_key=api_key)

        if context.get('success'):
            return JsonResponse(context, status=status_codes.HTTP_200_OK)

        return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                            context.get('status')))


class FetchUser(APIView):
    """
    Fetch user
    """

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        user_manager = UserImpl(user_id=member_id)
        user_response = user_manager.fetch_user_info()

        if 'error_message' not in user_response:
            return JsonResponse(user_response, status=status_codes.HTTP_200_OK)

        return JsonResponse(**ResponseUtilities.get_view_impl_error_context(user_response.get('error_message'),
                                                                            user_response.get('status')))
