from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from .webhook_view_helper import WebhookViewHelper
from .webhook_impl import WebhookImpl


class WebhooksView(APIView):

    def get(self, request):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        validated_request_body = WebhookViewHelper.fetch_webhooks_body_validator(request_body, member_id)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        webhook_manager = WebhookImpl(member_id=member_id,
                                      community_id=validated_request_body.get('community_id'))
        response_data = webhook_manager.fetch_webhooks()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(
            {'success': True, 'webhooks': response_data['webhooks']},
            status=status_codes.HTTP_200_OK
        )

    def post(self, request):

        api_key = RequestUtilities.get_api_key_from_headers(request)
        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        validated_request_body = WebhookViewHelper.add_webhook_body_validator(request_body, member_id, api_key)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        webhook_manager = WebhookImpl(member_id=member_id, api_key=api_key,
                                      webhook_type=validated_request_body.get('webhook_type'),
                                      url=validated_request_body.get('url'))
        
        response_data = webhook_manager.add_webhook()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(response_data)


class WebhookView(APIView):

    def get(self, request, webhook_id):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        validated_request_body = WebhookViewHelper.fetch_webhook_body_validator(request_body, member_id)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        webhook_manager = WebhookImpl(member_id=member_id,
                                      webhook_id=webhook_id)
        response_data = webhook_manager.fetch_webhook()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(
            {'success': True, 'webhooks': response_data['webhooks']},
            status=status_codes.HTTP_200_OK
        )

    def patch(self, request, webhook_id):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        validated_request_body = WebhookViewHelper.update_webhook_body_validator(request_body, member_id)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        webhook_manager = WebhookImpl(member_id=member_id,
                                      webhook_id=webhook_id,
                                      url=validated_request_body.get('url'))
        response_data = webhook_manager.update_webhook()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(
            {'success': True},
            status=status_codes.HTTP_200_OK
        )

    def delete(self, request, webhook_id):

        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        validated_request_body = WebhookViewHelper.delete_webhook_body_validator(request_body, member_id)

        if 'error_message' in validated_request_body:
            context = ResponseUtilities.get_view_impl_error_context(validated_request_body['error_message'],
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

        webhook_manager = WebhookImpl(member_id=member_id,
                                      webhook_id=webhook_id)
        response_data = webhook_manager.delete_webhook()

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data['error_message'],
                                                                    response_data['status'])
            return JsonResponse(context['data'], status=context['status'])

        return JsonResponse(
            {'success': True},
            status=status_codes.HTTP_200_OK
        )
