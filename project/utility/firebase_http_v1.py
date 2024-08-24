import json
import time
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleRequest
import requests
from urllib3 import Retry
from requests.adapters import HTTPAdapter
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.constants import FCM_INITIAL_URL, FCM_PAYLOAD_FORMAT, GOOGLE_AUTH_SCOPE

error_logger = LoggingWrapper.get_instance()


class FCMHTTPV1Notification:

    FCM_MAX_RECIPIENTS = 1000

    def __init__(self, service_account_file_dict):
        self.service_account_file_dict = service_account_file_dict
        self.access_token = self.generate_access_token()
        self.requests_session = requests.Session()
        retries = Retry(backoff_factor=1, status_forcelist=[502, 503, 504],
                        method_whitelist=(Retry.DEFAULT_METHOD_WHITELIST | frozenset(['POST'])))
        self.requests_session.mount('http://', HTTPAdapter(max_retries=retries))
        self.requests_session.mount('https://', HTTPAdapter(max_retries=retries))
        self.send_request_responses = []

    def generate_access_token(self):
        # Load the service account credentials from the JSON key file
        credentials = service_account.Credentials.from_service_account_info(self.service_account_file_dict, scopes=[GOOGLE_AUTH_SCOPE])
        request = GoogleRequest()
        credentials.refresh(request)

        return credentials.token
    
    def notify_multiple_devices(self,
                                registration_ids=None,
                                stacks=None,
                                message_body=None,
                                message_title=None,
                                message_icon=None,
                                data_message=None,
                                condition=None,
                                remove_notification=False,
                                extra_kwargs_android={},
                                extra_kwargs_ios={},
                                extra_kwargs_web={}):
        
        # Set up headers and endpoint
        fcm_headers = {
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json"
        }
        self.requests_session.headers.update(fcm_headers)
        self.FCM_END_POINT = FCM_INITIAL_URL + self.service_account_file_dict['project_id'] + "/messages:send"

        if not isinstance(registration_ids, list):
            error_logger.info('Invalid registration IDs (should be list)')

        payloads = []

        registration_id_chunks = self.registration_id_chunks(registration_ids)
        
        for registration_ids in registration_id_chunks:
            
            for registration_id in registration_ids:
            # appends a payload with each registration id here
                payloads.append(self.parse_payload(
                    registration_id=registration_id,
                    stacks=stacks,
                    message_body=message_body,
                    message_title=message_title,
                    message_icon=message_icon,
                    data_message=data_message,
                    condition=condition,
                    remove_notification=remove_notification,
                    extra_kwargs_android=extra_kwargs_android,
                    extra_kwargs_ios=extra_kwargs_ios,
                    extra_kwargs_web=extra_kwargs_web
                ))
        
        self.send_request(payloads)
        return self.parse_responses()

    def parse_payload(self,
                      registration_id=None,
                      stacks=None,
                      topic_name=None,
                      message_body=None,
                      message_title=None,
                      message_icon=None,
                      condition=None,
                      data_message=None,
                      remove_notification=False,
                      extra_kwargs_android=None,
                      extra_kwargs_ios=None,
                      extra_kwargs_web=None):
        f"""
        Parses parameters of FCMNotification's methods to FCM nested json

        For payload format refer to {FCM_PAYLOAD_FORMAT}
        
        Returns:
            string: json

        Raises:
            InvalidDataError: parameters do have the wrong type or format
        """
        fcm_payload = dict()
        
        fcm_payload['message'] = {}             # entire payload has to be contructed inside messsage

        if registration_id:
            fcm_payload['message']['token'] = registration_id
        
        if condition:
            fcm_payload['message']['condition'] = condition

        else:
            if topic_name:
                fcm_payload['message']['topic'] = '%s' % topic_name        # topic format changed
        
        if data_message:                                   
            if isinstance(data_message, dict):
                fcm_payload['message']['data'] = data_message

            else:
                error_logger.info("Provided data_message is in the wrong format")
        
        fcm_payload['message']['notification'] = {}
        
        if message_icon:
            fcm_payload['message']['notification']['image'] = message_icon
        
        if message_body:
            fcm_payload['message']['notification']['body'] = message_body
        
        if message_title:
            fcm_payload['message']['notification']['title'] = message_title             # most of the v1 notification body is made till here

        if stacks:
            if 'android' in stacks:
                fcm_payload['message']['android'] = extra_kwargs_android      # stack specific options will now have to be explicitly loaded acc v1 format
            
            if 'ios' in stacks:
                fcm_payload['message']['apns'] = extra_kwargs_ios      # stack specific options will now have to be explicitly loaded acc v1 format

            if 'web' in stacks:
                fcm_payload['message']['webpush'] = extra_kwargs_web      # stack specific options will now have to be explicitly loaded acc v1 format

        # Do this if you only want to send a data message.
        if remove_notification:
            del fcm_payload['message']['notification']

        return self.json_dumps(fcm_payload)

    def registration_id_chunks(self, registration_ids):
        """
        Splits registration ids in several lists of max 1000 registration ids per list

        Args:
            registration_ids (list): FCM device registration ID

        Yields:
            generator: list including lists with registration ids
        """
        # Yield successive 1000-sized (max fcm recipients per request) chunks from registration_ids
        for i in range(0, len(registration_ids), self.FCM_MAX_RECIPIENTS):
            yield registration_ids[i:i + self.FCM_MAX_RECIPIENTS]

    def json_dumps(self, data):
        """
        Standardized json.dumps function with separators and sorted keys set

        Args:
            data (dict or list): data to be dumped

        Returns:
            string: json
        """
        return json.dumps(
            data, 
            separators=(',', ':'), 
            sort_keys=True,
            ensure_ascii=False
        ).encode('utf8')

    def do_request(self, payload):
        response = self.requests_session.post(self.FCM_END_POINT, data=payload)
        
        if 'Retry-After' in response.headers and int(response.headers['Retry-After']) > 0:
            sleep_time = int(response.headers['Retry-After'])
            time.sleep(sleep_time)
            return self.do_request(payload)
        
        return response

    def send_request(self, payloads=None):
        self.send_request_responses = []

        for payload in payloads:
            print(f"PAYLOAD: {payload}, {self.FCM_END_POINT}, {self.requests_session.headers}")
            response = self.do_request(payload)
            print(f"RESPONSE: {response.status_code}, {response.text}")
            self.send_request_responses.append(response)

    def parse_responses(self):
        """
        Parses the json response sent back by the server and tries to get out the important return variables

        Returns:
            dict: multicast_ids (list), success (int), failure (int), canonical_ids (int),
                results (list) and optional topic_message_id (str but None by default)

        Raises:
            FCMServerError: FCM is temporary not available
            AuthenticationError: error authenticating the sender account
            InvalidDataError: data passed to FCM was incorrecly structured
        """
        response_dict = {
            'multicast_ids': [],
            'success': 0,
            'failure': 0,
            'canonical_ids': 0,
            'results': [],
            'topic_message_id': None
        }

        for response in self.send_request_responses:
            
            if response.status_code == 200:
                
                if 'content-length' in response.headers and int(response.headers['content-length']) <= 0:
                    error_logger.info("FCM server connection error, the response is empty")
                
                else:
                    parsed_response = response.json()

                    if parsed_response.get('name'):
                        response_dict['success'] += 1

                    if parsed_response.get('error'):
                        response_dict['failure'] += 1
                    
                    response_dict['results'].append(parsed_response)

            elif response.status_code == 401:
                error_logger.info("There was an error authenticating the sender account")
            
            elif response.status_code == 400:
                error_logger.info(response.text)
            
            else:
                error_logger.info("FCM server is temporarily unavailable")
        
        return response_dict
