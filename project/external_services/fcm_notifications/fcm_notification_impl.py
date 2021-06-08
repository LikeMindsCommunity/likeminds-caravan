import json
import time
from django.conf import settings
from pyfcm import FCMNotification
from oauth2client.service_account import ServiceAccountCredentials
from pyfcm.errors import FCMServerError, AuthenticationError, InvalidDataError

from external_services.fcm_notifications.constants import SCOPES
from external_services.fcm_notifications.fcm_notification_manager import FCMNotificationManager
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.number_utilities import NumberUtilities

from external_services.mixpanel.mixpanel_impl import MixpanelImpl

FCM_CREDENTIALS = settings.FCM_CREDENTIALS

logger = LoggingWrapper.get_instance()


class FCMNotificationImpl(FCMNotificationManager, FCMNotification):
    FCM_UPDATED_END_POINT = "https://fcm.googleapis.com/v1/projects/collabmates-beta/messages:send"

    def __init__(self, api_key, is_android_device, user_id=None, proxy_dict=None, env=None, json_encoder=None):
        super().__init__(api_key, proxy_dict, env, json_encoder)
        self.api_key = api_key
        self.is_android_device = is_android_device
        self._FCM_API_KEY = api_key
        self.user_id = user_id

    def get_user_id(self):
        return self.user_id

    def _track_notification(self, notification_payload):
        if self.get_user_id() is not None:
            MixpanelImpl().track_notification(str(self.get_user_id()),
                                              properties=notification_payload)

    def get_access_token_for_auth(self):
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(FCM_CREDENTIALS, SCOPES)
        token_information = credentials.get_access_token()

        return token_information.access_token

    def update_payload(self, payload):
        payload_str = payload.decode('utf8')
        payload_dict = json.loads(payload_str)
        fcm_payload = dict()
        message = dict()
        logger.info("updating payload for FCM HTTP v1 API")

        if 'data' in payload_dict:
            message['data'] = payload_dict['data']
        message['token'] = payload_dict['to']

        if 'notification' in payload_dict:
            message['notification'] = {
                "title": payload_dict['data']['title'],
                "body": payload_dict['data']['sub_title']
            }

        if self.is_android_device:
            android = {
                'priority': payload_dict['priority']
            }
            message['android'] = android

        else:
            apns = {
                'payload': {
                    'aps': {
                        'priority': 10
                    }
                }
            }
            message['apns'] = apns
        fcm_payload['message'] = message
        updated_payload = json.dumps(fcm_payload)
        logger.info("updated payload " + updated_payload)

        return updated_payload

    def do_request(self, payload, timeout):
        headers = {
            "Authorization": "Bearer " + self.get_access_token_for_auth(),
            'Content-Type': 'application/json; UTF-8',
        }

        try:
            response = self.requests_session.post(self.FCM_UPDATED_END_POINT, data=payload, timeout=timeout,
                                                  headers=headers)
            if 'Retry-After' in response.headers and NumberUtilities.get_integer_from_string(response.headers['Retry-After']) > 0:
                sleep_time = NumberUtilities.get_integer_from_string(response.headers['Retry-After'])
                time.sleep(sleep_time)

                return self.do_request(payload, timeout)
            logger.info(response.json())

            return response
        except Exception as e:
            logger.error(e.args)

    def send_request(self, payloads=None, timeout=None):
        self.send_request_responses = []
        logger.info("sending FCM requests")

        for payload in payloads:

            try:
                payload = self.update_payload(payload)
            except KeyError as e:
                logger.error(e.args)

            response = self.do_request(payload, timeout)
            self.send_request_responses.append(response)
            self._track_notification(payload)

    def parse_responses(self):
        response_dict = {
            "success": 0,
        }

        for response in self.send_request_responses:

            if response.status_code == 200:

                if 'content-length' in response.headers and NumberUtilities.get_integer_from_string(response.headers['content-length']) <= 0:
                    error_message = "FCM server connection error, the response is empty"
                    logger.error(error_message)
                    raise FCMServerError(error_message)

                else:
                    if 'name' in response.json():
                        logger.info("Notification successfully sent ")
                        response_dict['success'] += 1

            elif response.status_code == 401:
                error_message = "There was an error authenticating the sender account"
                logger.error(error_message)
                raise AuthenticationError(error_message)

            elif response.status_code == 400:
                logger.error(response.text)
                raise InvalidDataError(response.text)

            else:
                error_message = "FCM server is temporarily unavailable"
                logger.error(error_message)
                raise FCMServerError(error_message)

        return response_dict
