from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.request_utilities import RequestUtilities
from ..rest_api import get_error_context
from .tasks import send_email_notification_for_event_type, send_8_pm_noti_for_new_resources_added
from .constants import EVENT_TYPE

error_logger = LoggingWrapper.get_instance()


class SendEventCreationMail(APIView):

    def _validate_request(self, req_body):
        res = {}

        if not req_body:
            res = get_error_context(False, "Invalid request body")

        elif not req_body.get('chatroom_id'):
            res = get_error_context(False, "chatroom_id cannot be empty")

        elif 'event_cost' not in req_body:
            res = get_error_context(False, "event_cost cannot be empty")

        return res

    def post(self, request):
        try:
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_request(req_body)

            if request_validation_errors:
                return JsonResponse(request_validation_errors, status=status_codes.HTTP_400_BAD_REQUEST)

            payload_for_event_creation_mail = {
                'chatroom': req_body.get('chatroom_id'),
                'event_cost': req_body.get('event_cost')
            }

            args = [payload_for_event_creation_mail, EVENT_TYPE.CREATION]

            send_email_notification_for_event_type.apply_async(
                args,
                countdown=10
            )

            res = {
                'success': True
            }

            return JsonResponse(res, status=status_codes.HTTP_200_OK)

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(res, status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)
