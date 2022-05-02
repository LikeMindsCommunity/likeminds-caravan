from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from .sdk_view_helper import SdkViewHelper
from .sdk_impl import SdkImpl


class CreateSdkView(APIView):

    def post(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        validated_request_body = SdkViewHelper.create_sdk_body_validator(request_body, member_id)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        sdk_manager = SdkImpl(member_id=member_id, request_platform=request_platform, version_code=version_code)
        response_data = sdk_manager.create_sdk(validated_request_body)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(
            {'success': True, 'api_key': response_data.get('api_key')},
            status=status_codes.HTTP_200_OK
        )


class InitiateSdkView(APIView):

    def post(self, request):

        request_body = RequestUtilities.load_request_body(request)
        validated_request_body = SdkViewHelper.initiate_sdk_body_validator(request_body)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        sdk_manager = SdkImpl(api_key=validated_request_body.get('api_key'))
        response_data = sdk_manager.initiate_sdk(validated_request_body)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(
            {'success': True},
            status=status_codes.HTTP_200_OK
        )
