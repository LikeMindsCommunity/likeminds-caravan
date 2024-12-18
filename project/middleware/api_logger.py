import json
import traceback
from multiprocessing.context import Process

from django.conf import settings
from rest_framework import status
from django.utils.deprecation import MiddlewareMixin

from external_services.logging.coralogix_api_client import CoralogixApiClient
from external_services.logging.logging_wrapper import LoggingWrapper
from .constants import API_500_ERROR_MESSAGE


class ApiLogger(MiddlewareMixin):

    logger = LoggingWrapper.get_instance()

    def process_request(self, request: {}) -> None:
        pass

    def process_response(self, request: {}, response: {}) -> {}:
        try:
            if request.path == '/status':
                return

            request_dict = self._process_request_object(request)
            response_dict = self._process_response_object(response)
            response_dict = self._process_response_dict(response_dict)
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
            'body': self._process_request_post_body(request)
        }

        return request_dict

    @staticmethod
    def _process_request_headers(request_headers: dict) -> dict:
        headers_dict = {
            'x_member_id': request_headers.get('HTTP_X_MEMBER_ID', ''),
            'timezone': request_headers.get('TZ', ''),
            'protocol': request_headers.get('SERVER_PROTOCOL', ''),
            'user_agent': request_headers.get('HTTP_USER_AGENT', ''),
            'platform_code': request_headers.get('HTTP_X_PLATFORM_CODE', ''),
            'version_code': request_headers.get('HTTP_X_VERSION_CODE', ''),
            'sdk_source' : request_headers.get('HTTP_X_SDK_SOURCE', ''),
            'accept_version': request_headers.get('HTTP_X_ACCEPT_VERSION', ''),
            'device_id': request_headers.get('HTTP_X_DEVICE_ID', ''),
            'api_key': request_headers.get('HTTP_X_API_KEY', ''),
            'api_version': request_headers.get('HTTP_X_API_VERSION', ''),
        }

        return headers_dict

    def _process_request_post_body(self, request: {}) -> dict:

        try:
            post_body = dict()

            if request.POST:
                post_body = dict(request.POST)
            elif request.body:
                post_body = json.loads(request.body)

            return post_body
        except Exception:
            self.logger.error('error parsing request body')
            return dict()

    @staticmethod
    def _process_response_object(response: {}) -> dict:
        response_dict = {
            'http_response_code': response.status_code,
            'content': response.content.decode('utf-8')
        }

        return response_dict

    @staticmethod
    def _process_response_dict(response_dict: dict) -> dict:
        if response_dict and\
                response_dict.get('http_response_code') == 500:
            response_dict['content'] = API_500_ERROR_MESSAGE

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
            """
            for coralogix logger we need to disable
            full text response for 200 OK status 
            """
            if getattr(settings, 'OMIT_200_OK_FULL_RESPONSE', False) and \
                    log_object_dict['response']['http_response_code'] == 200:
                log_object_dict['response']['content'] = dict()

            api_client = CoralogixApiClient()
            logger_process = Process(target=api_client.call_logging_api, name="logger_process", args=(log_object_dict, ))
            logger_process.start()

    def _send_to_internal_logger(self, log_object_dict: dict):
        if status.is_success(log_object_dict['response']['http_response_code']):
            self.logger.info(str(log_object_dict))
        else:
            self.logger.error(str(log_object_dict))
