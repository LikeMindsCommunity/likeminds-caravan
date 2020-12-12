import traceback

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from external_services.logging.coralogix_api_client import CoralogixApiClient
from external_services.logging.logging_wrapper import LoggingWrapper


class ApiLogger(MiddlewareMixin):

    logger = LoggingWrapper.get_instance()

    def process_request(self, request: {}) -> None:
        pass

    def process_response(self, request: {}, response: {}) -> {}:
        try:
            request_dict = self._process_request_object(request)
            response_dict = self._process_response_object(response)
            log_object_dict = self._make_log_object(request_dict, response_dict)
            self._send_to_logger(log_object_dict)

        except Exception:
            message = "ApiLogger processing failed:\n%s" % traceback.format_exc()
            self.logger.error(message)

        finally:
            return response

    def _process_request_object(self, request: {}) -> dict:
        request_dict = {
            'host': request.get_host(),
            'absolute_uri': request.build_absolute_uri(),
            'method': request.method,
            'content_type': request.content_type,
            'content_params': request.content_params,
            'headers': self._process_request_headers(request.META),
            'query': request.GET,
            'body': request.POST
        }

        return request_dict

    @staticmethod
    def _process_request_headers(request_headers: dict) -> dict:
        headers_dict = {
            'x-member-id': request_headers.get('HTTP_X_MEMBER_ID', ''),
            'timezone': request_headers.get('TZ', ''),
            'protocol': request_headers.get('SERVER_PROTOCOL', ''),
            'user_agent': request_headers.get('HTTP_USER_AGENT', '')
        }

        return headers_dict

    @staticmethod
    def _process_response_object(response: {}) -> dict:
        response_dict = {
            'http_response_code': response.status_code,
            'content': response.content.decode('utf-8')
        }

        return response_dict

    @staticmethod
    def _make_log_object(request_dict: dict, response_dict: dict) -> dict:
        log_object_dict = {
            'request': request_dict,
            'response': response_dict
        }

        return log_object_dict

    def _send_to_logger(self, log_object_dict: dict) -> None:
        if getattr(settings, 'USE_INTERNAL_FILE_LOGGER', False):
            self._send_to_internal_logger(log_object_dict)
        else:
            api_client = CoralogixApiClient()
            api_client.call_logging_api(log_object_dict)

    def _send_to_internal_logger(self, log_object_dict: dict):
        if log_object_dict['response']['http_response_code'] == 200:
            self.logger.info(str(log_object_dict))
        else:
            self.logger.error(str(log_object_dict))
