import json
import logging
import traceback

import requests
from rest_framework import status
from django.conf import settings

from external_services.logging.constants import CORALOGIX_CONSTS
from external_services.logging.coralogix_api_manager import CoralogixApiManager
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.time_utilities import TimeUtilities


class CoralogixApiClient(CoralogixApiManager):
    URL = None
    METHOD = None
    PRIVATE_API_KEY = None
    APPLICATION_NAME = None
    SUBSYSTEM_NAME = None

    logger = LoggingWrapper.get_instance()
    # error_logger = logging.getLogger('stream_error_logger')

    def __init__(self):
        self.URL = CORALOGIX_CONSTS.get('LOGGING_API_URL')
        self.METHOD = CORALOGIX_CONSTS.get('LOGGING_API_METHOD')
        self.PRIVATE_API_KEY = settings.CORALOGIX_LOGGER.get('PRIVATE_API_KEY')
        self.APPLICATION_NAME = settings.CORALOGIX_LOGGER.get('APPLICATION_NAME')
        self.SUBSYSTEM_NAME = settings.CORALOGIX_LOGGER.get('SUBSYSTEM_NAME_API')

    def get_url(self) -> str:
        return self.URL

    def get_method(self) -> str:
        return self.METHOD

    def get_api_key(self) -> str:
        return self.PRIVATE_API_KEY

    def get_app_name(self) -> str:
        return self.APPLICATION_NAME

    def get_sub_name(self) -> str:
        return self.SUBSYSTEM_NAME

    def call_logging_api(self, payload: dict) -> None:
        try:
            api_payload = self._create_logging_api_payload(payload)
            payload_data = api_payload.get('data')
            api_response = requests.request(self.get_method(),
                                            self.get_url(),
                                            headers=api_payload.get('headers'),
                                            data=json.dumps(payload_data))

            self._send_to_stream_logger(payload_data)

            if hasattr(api_response, 'status_code') and \
                    int(api_response.status_code) != 200:
                message = "Error response from coralogix api:\n%s" % api_response.content.decode('utf-8')
                raise Exception(message)

        except Exception:
            message = "Coralogix api call failed:\n%s" % traceback.format_exc()
            self.error_logger.error(message)

    def _create_logging_api_payload(self, payload: dict) -> dict:
        log_entry_object = CORALOGIX_CONSTS.get('LOG_ENTRY_SCHEMA')
        log_entry_object['timestamp'] = TimeUtilities.current_time_in_millis()
        log_entry_object['severity'] = self._get_log_severity_level(payload['response']['http_response_code'])
        log_entry_object['text'] = payload

        api_data = self._create_logging_api_data(log_entry_object)
        api_headers = self._get_api_headers()

        return dict({
            'headers': api_headers,
            'data': api_data
        })

    @staticmethod
    def _get_log_severity_level(http_response_code: int) -> int:
        if status.is_success(http_response_code):
            return CORALOGIX_CONSTS['LOG_LEVEL']['Info']

        return CORALOGIX_CONSTS['LOG_LEVEL']['Error']

    @staticmethod
    def _get_api_headers() -> dict:
        return dict({
            'Content-Type': 'application/json'
        })

    def _create_logging_api_data(self, log_entry_object: dict) -> dict:
        api_log_object = CORALOGIX_CONSTS.get('PAYLOAD_SCHEMA')
        api_log_object['privateKey'] = self.get_api_key()
        api_log_object['applicationName'] = self.get_app_name()
        api_log_object['subsystemName'] = self.get_sub_name()
        api_log_object['logEntries'] = [log_entry_object]

        return api_log_object

    def _send_to_stream_logger(self, payload_data: dict) -> None:
        severity_level = payload_data.get('logEntries')[0].get('severity')

        if severity_level <= CORALOGIX_CONSTS['LOG_LEVEL']['Info']:
            self.logger.info(json.dumps(payload_data.get('logEntries')[0]))
        else:
            self.error_logger.error((json.dumps(payload_data.get('logEntries')[0])))
