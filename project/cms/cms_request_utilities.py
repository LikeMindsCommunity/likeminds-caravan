from rest_framework import status as status_codes
from project.utility.exception_utilities import (CustomException)
from project.utility.request_utilities import RequestUtilities
from project.cms.constants import *


class CMSUtilities:

    @staticmethod
    def get_username_and_password_from_headers(request):
        user_name = RequestUtilities.get_user_name_from_headers(request)
        password = RequestUtilities.get_password_from_headers(request)

        if user_name is None and password is None:
            CMSUtilities.raise_credentials_missing_exception()
        else:
            return user_name, password

    @staticmethod
    def validate_user(user_name, password):
        return user_name == CMS_USER_NAME and password == CMS_PASSWORD

    @staticmethod
    def raise_credentials_missing_exception():
        response = {
            'success': False,
            'error_message': 'send user name and password in headers'
        }

        raise CustomException(response, status_code=status_codes.HTTP_401_UNAUTHORIZED)

    @staticmethod
    def raise_authentication_error():
        response = {
            'success': False,
            'error_message': 'user name and password does not match'
        }

        raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)
