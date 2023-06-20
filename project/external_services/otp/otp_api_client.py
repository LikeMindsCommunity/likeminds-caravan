import json
import os

import requests
from django.conf import settings

from external_services.logging.logging_wrapper import LoggingWrapper
from external_services.otp.constants import OTP_GUPSHUP_URL, OTP_MESSAGE_ON_BETA, OTP_MESSAGE_ON_PRODUCTION, \
    GUPSHUP_VERIFY_OTP_URL
from external_services.otp.otp_api_manager import OTPApiManager
from utility.constants import MSG91_SENDOTP_URI, MSG91_VERIFYOTP_URI

info_logger = LoggingWrapper.get_instance()
error_logger = LoggingWrapper.get_instance()


class OTPApiClient(OTPApiManager):

    def send_otp_via_gupshup(self, phone_number, is_international) -> dict:

        try:

            if is_international:
                phone_number = "00" + str(phone_number)

            info_logger.info(f'Calling GUPSHUP Generate OTP API, Phone Number: {phone_number}')

            gupshup_user_id, gupshup_password = OTPHelper.get_gupshup_credentials(is_international)

            url = OTP_GUPSHUP_URL.format(gupshup_user_id, gupshup_password, phone_number,
                                         OTPHelper.get_otp_message())

            api_response = requests.request('GET', url)

            info_logger.info(f"""GUPSHUP Generate OTP API Response Status Code: {api_response.status_code}, 
            Response : {api_response.text}""")

            return OTPHelper.generate_json_response_from_gupshup_api_response_text(api_response)

        except Exception as e:
            error_logger.error(e.args)
            response = {
                'success': False,
                'error_message': str(e)
            }

            return response

    def send_retry_otp_via_msg_91(self, phone_number) -> dict:

        try:

            template_id = settings.OTP_TEMPLATE_ID
            msg91_auth_key = settings.MSG91_AUTH_KEY
            url = MSG91_SENDOTP_URI % (msg91_auth_key, template_id, phone_number)

            api_response = requests.request('GET', url)

            info_logger.info(
                f'MSG 91 Generate OTP API Response Status Code: {api_response.status_code}, Response : {api_response.json()}')

            if api_response.status_code == 200:
                result = json.loads(api_response.text)

            else:
                context = {
                    'success': False,
                    'error_message': "Service down. Try again later."
                }
                error_logger.error("MSG91 server not responding with status code =" + (str(api_response.status_code)))

                return context

            context = {}

            if result['type'] == 'success':
                context['success'] = True
                info_logger.info("MSG91 mobile generate otp success")

            else:
                error_logger.error("MSG91 mobile generate otp fail due to " + str(result['message']))
                context['success'] = False
                context['error_message'] = result['message']

            return context

        except Exception as e:
            error_logger.error(e.args)
            response = {
                'success': False,
                'error_message': str(e)
            }

            return response

    def verify_otp_via_gupshup(self, phone_number, otp, is_international) -> dict:
        try:

            if is_international:
                phone_number = "00" + str(phone_number)

            info_logger.info(
                f'Calling GUPSHUP Verify OTP API, Phone Number: {phone_number}')

            gupshup_user_id, gupshup_password = OTPHelper.get_gupshup_credentials(is_international)

            url = GUPSHUP_VERIFY_OTP_URL.format(gupshup_user_id, gupshup_password, phone_number, otp)

            api_response = requests.request('GET', url)

            info_logger.info(
                f'GUPSHUP Verify OTP API Response Status Code: {api_response.status_code}, Response : {api_response.text}')

            return OTPHelper.generate_json_response_from_gupshup_verify_api_response_text(api_response)

        except Exception as e:
            error_logger.error(e.args)
            response = {
                'success': False,
                'error_message': str(e)
            }

            return response

    def verify_retry_otp_via_msg_91(self, phone_number, otp):

        try:

            msg91_auth_key = settings.MSG91_AUTH_KEY

            url = MSG91_VERIFYOTP_URI % (msg91_auth_key, str(phone_number), str(otp))

            api_response = requests.request('GET', url)

            info_logger.info(
                f'MSG 91 Verify OTP API Response Status Code: {api_response.status_code}, Response : {api_response.json()}')

            if api_response.status_code == 200:
                result = json.loads(api_response.text)

            else:
                context = {
                    'success': False,
                    'error_message': "Service down. Try again later."
                }
                error_logger.error("MSG91 server not responding with status code =" + (str(api_response.status_code)))
                return context

            context = {}

            if result['type'] == 'success':
                context['success'] = True
                info_logger.info("MSG91 mobile verify otp success")

            else:
                error_logger.error("MSG91 mobile verify otp fail due to " + str(result['message']))
                context['success'] = False
                context['error_message'] = result['message']

            return context

        except Exception as e:
            error_logger.error(e.args)
            response = {
                'success': False,
                'error_message': str(e)
            }

            return response


class OTPHelper:

    @staticmethod
    def generate_json_response_from_gupshup_api_response_text(api_response) -> dict:
        json_response = {
            'success': False,
        }

        if api_response.status_code == 200:
            json_response['success'] = True
            api_response_text = api_response.text
            response_list = api_response_text.split("|")[0]
            if response_list[0].strip() == "error":
                json_response['success'] = False

        if not json_response['success']:
            json_response['error_message'] = api_response_text

        info_logger.info(json_response)

        return json_response

    @staticmethod
    def get_otp_message():
        otp_message = ''

        if settings.IS_BETA:
            otp_message = OTP_MESSAGE_ON_BETA

        else:
            otp_message = OTP_MESSAGE_ON_PRODUCTION

        return otp_message

    @staticmethod
    def get_gupshup_credentials(is_international):
        gupshup_user_id = os.getenv('GUPSHUP_USER_ID_FOR_INDIA')
        gupshup_password = os.getenv('GUPSHUP_PASSWORD_ID_FOR_INDIA')

        if is_international:
            gupshup_user_id = os.getenv('GUPSHUP_USER_ID_FOR_INTERNATIONAL')
            gupshup_password = os.getenv('GUPSHUP_PASSWORD_FOR_INTERNATIONAL')

        return gupshup_user_id, gupshup_password

    @staticmethod
    def generate_json_response_from_gupshup_verify_api_response_text(api_response) -> dict:

        info_logger.info(api_response.text)
        json_response = {}
        success = False

        if api_response.status_code == 200:
            success = True
            response = api_response.text
            response_list = response.split("|")

            if response_list[0].strip() == "error":
                success = False

        json_response['success'] = success

        if not success:
            json_response['error_message'] = "Incorrect OTP"

        return json_response
