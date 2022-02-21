from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from utility.auth_utilities import AuthUtilities
from .webhook_view_helper import WebhookViewHelper
from .webhook_impl import WebhookImpl
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class WebhookView(APIView):

    def get(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        validated_request_body = WebhookViewHelper.fetch_webhook_body_validator(request_body, member_id)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        authentication_response = AuthUtilities.is_cm(validated_request_body.get('community_id'), member_id)

        if 'error_message' in authentication_response:
            context = ResponseUtilities.get_view_impl_error_context(authentication_response['error_message'],
                                                                    authentication_response['status'])
            return JsonResponse(context['data'], status=context['status'])

        webhook_manager = WebhookImpl(member_id=member_id,
                                      community_id=validated_request_body.get('community_id'),
                                      webhook_id=validated_request_body.get('webhook_id'))
        response_data = webhook_manager.fetch_webhook()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(
            {'success': True, 'webhooks': response_data['webhooks']},
            status=status_codes.HTTP_200_OK
        )

    def post(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        validated_request_body = WebhookViewHelper.webhook_body_validator(request_body, member_id)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        authentication_response = AuthUtilities.is_cm(validated_request_body.get('community_id'), member_id)

        if 'error_message' in authentication_response:
            context = ResponseUtilities.get_view_impl_error_context(authentication_response['error_message'],
                                                                    authentication_response['status'])
            return JsonResponse(context['data'], status=context['status'])

        webhook_manager = WebhookImpl(member_id=member_id,
                                      community_id=validated_request_body.get('community_id'),
                                      webhook_id=validated_request_body.get('webhook_id'),
                                      webhook_type=validated_request_body.get('webhook_type'),
                                      url=validated_request_body.get('url'))
        response_data = webhook_manager.add_or_update_webhook()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(
            {'success': True},
            status=status_codes.HTTP_200_OK
        )

    def delete(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        validated_request_body = WebhookViewHelper.delete_webhook_body_validator(request_body, member_id)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        authentication_response = AuthUtilities.is_cm(validated_request_body.get('community_id'), member_id)

        if 'error_message' in authentication_response:
            context = ResponseUtilities.get_view_impl_error_context(authentication_response['error_message'],
                                                                    authentication_response['status'])
            return JsonResponse(context['data'], status=context['status'])

        webhook_manager = WebhookImpl(member_id=member_id,
                                      community_id=validated_request_body.get('community_id'),
                                      webhook_id=validated_request_body.get('webhook_id'))
        response_data = webhook_manager.delete_webhook()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(
            {'success': True},
            status=status_codes.HTTP_200_OK
        )
