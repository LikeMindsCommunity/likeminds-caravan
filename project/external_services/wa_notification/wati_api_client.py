import json
import traceback

import requests
from django.conf import settings

from external_services.wa_notification.constants import WATI_NOTIFICATION_CONST
from external_services.wa_notification.wati_api_manager import WAApiManager
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.number_utilities import NumberUtilities


class WAApiClient(WAApiManager):

    logger = LoggingWrapper.get_instance()
    URL = WATI_NOTIFICATION_CONST.get('WATI_BROADCAST_URL')
    BULK_URL = WATI_NOTIFICATION_CONST.get('WATI_BROADCAST_BULK_URL')
    WA_BROADCAST_METHOD = WATI_NOTIFICATION_CONST.get('WATI_BROADCAST_METHOD')
    AUTH_TOKEN = settings.WA_API_KEY

    def get_url(self) -> str:
        return self.URL

    def get_auth_token(self) -> str:
        return self.AUTH_TOKEN

    def get_wa_broadcast_method(self) -> str:
        return self.WA_BROADCAST_METHOD

    @classmethod
    def call_wa_broadcast_api(self, user_data, template_name, broadcast_name) -> None:
        try:
            user_phone = self._get_user_phone(self, user_data)
            user_parameters = self._get_user_parameters(self, user_data)

            api_payload = self._create_api_payload(self, template_name, broadcast_name, user_parameters)
            api_endpoint = self._create_api_endpoint(self, user_phone)

            api_response = requests.request(self.get_wa_broadcast_method(self),
                                            api_endpoint,
                                            headers=api_payload.get('headers'),
                                            data=json.dumps(api_payload.get('body')))

            if hasattr(api_response, 'status_code') and \
                    NumberUtilities.get_integer_from_string(api_response.status_code) != 200:
                message = "Error response from wati broadcast api:\n%s" % api_response.content.decode('utf-8')

                raise Exception(message)

        except Exception:
            message = "Wa broadcast api call failed:\n%s" % traceback.format_exc()
            self.logger.error(message)

    @classmethod
    def call_wa_bulk_broadcast_api(self, receivers_list, template_name, broadcast_name) -> None:

        try:
            api_payload = self._create_bulk_api_payload(self, template_name, broadcast_name, receivers_list)
            api_endpoint = self._create_bulk_api_endpoint(self)

            api_response = requests.request(self.get_wa_broadcast_method(self),
                                            api_endpoint,
                                            headers=api_payload.get('headers'),
                                            data=json.dumps(api_payload.get('body')))

            if hasattr(api_response, 'status_code') and \
                    NumberUtilities.get_integer_from_string(api_response.status_code) != 200:
                message = "Error response from wati bulk broadcast api:\n%s" % api_response.content.decode('utf-8')

                raise Exception(message)

        except Exception:
            message = "Wa bulk broadcast api call failed:\n%s" % traceback.format_exc()
            self.logger.error(message)

    def _create_api_payload(self, template_name: str, broadcast_name: str, parameters: list) -> dict:
        api_body = WATI_NOTIFICATION_CONST.get('WATI_BROADCAST_SCHEMA')
        api_body['parameters'] = parameters
        api_body['broadcast_name'] = broadcast_name
        api_body['template_name'] = template_name

        api_headers = self._create_api_headers(self)

        payload = {
            'headers': api_headers,
            'body': api_body
        }

        return payload

    def _create_bulk_api_payload(self, template_name: str, broadcast_name: str, receivers_list: list) -> dict:
        api_body = WATI_NOTIFICATION_CONST.get('WATI_BROADCAST_BULK_SCHEMA')
        api_body['receivers'] = receivers_list
        api_body['broadcast_name'] = broadcast_name
        api_body['template_name'] = template_name

        api_headers = self._create_api_headers(self)

        payload = {
            'headers': api_headers,
            'body': api_body
        }

        return payload

    def _create_api_headers(self) -> dict:
        return dict({
            "Content-type": "application/json",
            "Authorization": self.AUTH_TOKEN,
        })

    def _create_api_endpoint(self, phone) -> str:
        return self.URL % phone

    def _create_bulk_api_endpoint(self) -> str:
        return self.BULK_URL

    def _get_user_phone(self, user_data) -> str:
        return user_data['phone']

    def _get_user_parameters(self, user_data) -> {}:
        return user_data['parameters']
