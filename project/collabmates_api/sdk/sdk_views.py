from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from .sdk_impl import SdkImpl


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
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        sdk_manager = SdkImpl(api_key=api_key, request_platform=request_platform,
                              version_code=version_code, device_id=device_id)
        response_data = sdk_manager.initiate_sdk(request_body)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data, status=status_codes.HTTP_200_OK)


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
