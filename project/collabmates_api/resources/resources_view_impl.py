from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.request_utilities import RequestUtilities
from ..rest_api import get_error_context

from .resources_impl import ResourcesImpl

error_logger = LoggingWrapper.get_instance()


class ResourceSettings(APIView):
    """ View Class for Updating Resource Settings """

    def _validate_request(self, req_body):
        res = {}

        if not req_body:
            res = get_error_context(False, "Invalid request body")

        elif not req_body.get('community_id'):
            res = get_error_context(False, "community_id cannot be empty")

        return res

    def patch(self, request):
        """to update ResourceSettings against a community_id"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_request(req_body)

            if request_validation_errors:
                return JsonResponse(request_validation_errors, status=status_codes.HTTP_400_BAD_REQUEST)

            res = ResourcesImpl.update_resource_settings(req_body, member_id)

            if res.get('success'):
                return JsonResponse(res, status=status_codes.HTTP_200_OK)

            else:
                return JsonResponse(res, status=status_codes.HTTP_400_BAD_REQUEST)

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(res, status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """to fetch ResourceSettings against a community_id"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_request(req_body)

            if request_validation_errors:
                return JsonResponse(request_validation_errors, status=status_codes.HTTP_400_BAD_REQUEST)

            res = ResourcesImpl.fetch_resource_settings(req_body, member_id)

            if res.get('success'):
                return JsonResponse(res, status=status_codes.HTTP_200_OK)

            else:
                return JsonResponse(res, status=status_codes.HTTP_400_BAD_REQUEST)

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(res, status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)
