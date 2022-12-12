from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.request_utilities import RequestUtilities
from utility.exception_utilities import InvalidHeaderException
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from ..external_service_apis.external_service_apis_impl import ExternalServiceApisImpl
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()


class SendEmailView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SendEmailView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False,
                                 'error_message': 'invalid request body'},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        external_service_manager = ExternalServiceApisImpl(member_id, device_id=device_id,
                                                           request_platform=request_platform, version_code=version_code)
        external_service_context = external_service_manager.send_email(req_body)

        if external_service_context.get('error_message'):
            return JsonResponse(external_service_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(external_service_context)


class SendWhatsAppMessageView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SendWhatsAppMessageView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False,
                                 'error_message': 'invalid request body'},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        external_service_manager = ExternalServiceApisImpl(member_id, device_id=device_id,
                                                           request_platform=request_platform, version_code=version_code)
        external_service_context = external_service_manager.send_wa_message(req_body)

        if external_service_context.get('error_message'):
            return JsonResponse(external_service_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(external_service_context)


class SendNotificationsView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SendNotificationsView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False,
                                 'error_message': 'invalid request body'},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        external_service_manager = ExternalServiceApisImpl(member_id, device_id=device_id,
                                                           request_platform=request_platform, version_code=version_code,
                                                           api_key=api_key)
        external_service_context = external_service_manager.send_notifications(req_body)

        if external_service_context.get('error_message'):
            return JsonResponse(external_service_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(external_service_context)
