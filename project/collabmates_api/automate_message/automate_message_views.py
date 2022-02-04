from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from utility.auth_utilities import AuthUtilities
from .automate_message_view_helper import AutomateMessageViewHelper
from .automate_message_impl import AutomateMessageImpl
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class AddMessageTemplateView(APIView):

    def post(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        validated_request_body = AutomateMessageViewHelper.template_body_validator(request_body, member_id)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        authentication_response = AuthUtilities.is_cm(validated_request_body.get('community_id'), member_id)

        if 'error_message' in authentication_response:
            context = ResponseUtilities.get_view_impl_error_context(authentication_response['error_message'],
                                                                    authentication_response['status'])
            return JsonResponse(context['data'], status=context['status'])

        automate_message_manager = AutomateMessageImpl(member_id=member_id,
                                                       community_id=validated_request_body.get('community_id'),
                                                       chatroom_type=validated_request_body.get('chatroom_type'),
                                                       message=validated_request_body.get('message'))
        response_data = automate_message_manager.add_template()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(
            {'success': True},
            status=status_codes.HTTP_200_OK
        )


class SendCustomMessageView(APIView):

    def post(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        validated_request_body = AutomateMessageViewHelper.template_body_validator(request_body, member_id)

        if 'error_message' in validated_request_body:
            response = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                     status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(response['data'], status=response['status'])

        authentication_response = AuthUtilities.is_cm(validated_request_body.get('community_id'), member_id)

        if 'error_message' in authentication_response:
            response = ResponseUtilities.get_view_impl_error_context(authentication_response['error_message'],
                                                                     authentication_response['status'])
            return JsonResponse(response['data'], status=response['status'])

        automate_message_manager = AutomateMessageImpl(member_id=member_id,
                                                       community_id=validated_request_body.get('community_id'),
                                                       chatroom_type=validated_request_body.get('chatroom_type'),
                                                       message=validated_request_body.get('message'))
        response_data = automate_message_manager.send_custom_message()

        if 'error_message' in response_data:
            response = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                     response_data['status'])
            return JsonResponse(response['data'], status=response['status'])

        return JsonResponse(
            {'success': True},
            status=status_codes.HTTP_200_OK
        )
