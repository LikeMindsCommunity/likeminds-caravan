from django.http import JsonResponse
from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from .sdk_impl import SdkImpl

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()

class SdkProjectView(APIView):

    def get(self, request):

        request_params = RequestUtilities.fetch_request_query_params(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        sdk_manager = SdkImpl(member_id=member_id, request_platform=request_platform, version_code=version_code,
                              api_key=api_key)
        response_data = sdk_manager.fetch_sdk_project(request_params)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)

    def post(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        sdk_manager = SdkImpl(member_id=member_id, request_platform=request_platform, version_code=version_code)
        response_data = sdk_manager.create_sdk_project(request_body)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)

    def put(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        sdk_manager = SdkImpl(member_id=member_id, request_platform=request_platform, version_code=version_code,
                              api_key=api_key)
        response_data = sdk_manager.edit_sdk_project(request_body)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)

    def delete(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        sdk_manager = SdkImpl(member_id=member_id, request_platform=request_platform, version_code=version_code,
                              api_key=api_key)
        response_data = sdk_manager.delete_sdk_project()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)


class InitiateSdkView(APIView):

    def post(self, request):

        request_body = RequestUtilities.load_request_body(request)
        request_platform = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        api_version = RequestUtilities.get_api_version_from_headers(request)

        try:
            sdk_manager = SdkImpl(api_key=api_key, request_platform=request_platform, version_code=version_code,
                                  device_id=device_id, api_version_code=api_version)
            response_data = sdk_manager.initiate_sdk(request_body)
        
        # If IntegrityError is raised, log error and return 400
        except IntegrityError as e:

            error_logger.error(f"IntegrityError Occured in sdk/initiate | Request Body: {request_body} , Request Headers: {request.headers}")

            context = ResponseUtilities.get_view_impl_error_context("Integrity Error Occured, duplicate key constraint",
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            
            return JsonResponse(context['data'], status=context['status'])
        
        except Exception as e:

            error_logger.error(f"Exception occured in sdk/initiate: {e} ")

            context = ResponseUtilities.get_view_impl_error_context("Internal server error",
                                                                    status_codes.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return JsonResponse(context['data'], status=context['status'])
        
        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        params = RequestUtilities.fetch_request_query_params(request)
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        sdk_manager = SdkImpl(member_id=member_id, api_key=api_key, request_platform=platform_code,
                              version_code=version_code)
        response_data = sdk_manager.fetch_sdk_user_info(params.get('uuid'))

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data)


class AuthenticateSdkView(APIView):

    def get(self, request):

        api_key = RequestUtilities.get_api_key_from_headers(request)
        platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        sdk_manager = SdkImpl(api_key=api_key, request_platform=platform, version_code=version_code)
        response_data = sdk_manager.authenticate_sdk()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(**context)

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)


class OnboardingScreensView(APIView):

    def get(self, request):

        request_params = RequestUtilities.fetch_request_query_params(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        sdk_manager = SdkImpl(member_id=member_id, request_platform=request_platform, version_code=version_code,
                              api_key=api_key)
        response_data = sdk_manager.fetch_onboarding_screens(request_params)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)

    def post(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        sdk_manager = SdkImpl(member_id=member_id, request_platform=request_platform, version_code=version_code,
                              api_key=api_key)
        response_data = sdk_manager.create_onboarding_screen(request_body)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_201_CREATED)

    def put(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        sdk_manager = SdkImpl(member_id=member_id, request_platform=request_platform, version_code=version_code,
                              api_key=api_key)
        response_data = sdk_manager.edit_onboarding_screen(request_body)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)

    def delete(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        sdk_manager = SdkImpl(member_id=member_id, request_platform=request_platform, version_code=version_code,
                              api_key=api_key)
        response_data = sdk_manager.delete_onboarding_screen(request_body)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)


class SdkMauView(APIView):

    def get(self, request):

        request_params = RequestUtilities.fetch_request_query_params(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        sdk_manager = SdkImpl(api_key=api_key, member_id=member_id)
        response_data = sdk_manager.get_mau_overview(request_params)

        if 'error_message' in response_data:
            return JsonResponse(response_data, status=response_data['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)


class SdkLoginView(APIView):

    def post(self, request):
        req_body = RequestUtilities.load_request_body(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not req_body:
            return JsonResponse({'success': False,
                                 'error_message': "Invalid request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)
        
        sdk_manager = SdkImpl(api_key=api_key)
        response_data = sdk_manager.sdk_login(req_body, api_key)

        if 'error_message' in response_data:
            return JsonResponse(response_data, status=status_codes.HTTP_400_BAD_REQUEST)
        
        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)