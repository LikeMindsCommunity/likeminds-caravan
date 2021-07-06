import json
from rest_framework import status as status_codes

from .exception_utilities import JsonDecodeException
from .number_utilities import NumberUtilities
from .constants import INVALID_PLATFORM


class RequestUtilities:

    @staticmethod
    def get_member_id_from_headers(request: object) -> str:
        return request.META.get('HTTP_X_MEMBER_ID')

    @staticmethod
    def get_version_code_from_headers(request: object) -> int:
        return NumberUtilities.get_integer_from_string(request.META.get('HTTP_X_VERSION_CODE', 0))

    @staticmethod
    def fetch_request_body(request):
        request_body = json.loads(request.body)

        return request_body

    @staticmethod
    def fetch_request_post_data(request):
        return request.data

    @staticmethod
    def fetch_request_query_params(request):
        return request.query_params

    @staticmethod
    def is_request_web(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE', '').lower() == "web"

    @staticmethod
    def is_request_android(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE', '').lower() == "an"

    @staticmethod
    def is_request_ios(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE', '').lower() == "ios"

    @staticmethod
    def get_request_type(request: object) -> str:
        platform_code = request.META.get('HTTP_X_PLATFORM_CODE', '').lower()

        if platform_code:
            if platform_code == "an":
                return "an"

            elif platform_code == "ios":
                return "ios"

            elif platform_code == "web":
                return "web"

            elif platform_code == "web-mobile":
                return "web-mobile"

            elif platform_code == "web-desktop":
                return "web-desktop"

        return INVALID_PLATFORM

    @staticmethod
    def get_platform_code(request: object):
        platform_code = request.META.get('HTTP_X_PLATFORM_CODE', None)

        if platform_code is not None:
            return platform_code.lower()

    @staticmethod
    def get_user_name_from_headers(request: object) -> str:
        return request.META.get('HTTP_X_USERNAME')

    @staticmethod
    def get_password_from_headers(request: object) -> str:
        return request.META.get('HTTP_X_PASSWORD')

    @staticmethod
    def get_device_id_from_headers(request: object) -> str:
        return request.META.get('HTTP_X_DEVICE_ID')

    @staticmethod
    def load_request_body(request):

        try:
            request_body = json.loads(request.body)
        except Exception as e:
            request_body = {}

        return request_body

    @staticmethod
    def fetch_body_or_raise_exception(request):
        try:
            return RequestUtilities.fetch_request_body(request)
        except Exception as e:
            response = {
                'success': False,
                'error_message': f'Error in request body: {e.__class__.__name__} - {e.__str__()}'
            }
            raise JsonDecodeException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)


    @staticmethod
    def get_page_number(request: object, key: str = "page", default: int = 1) -> int:
        return NumberUtilities.get_integer_from_string(request.query_params.get('page', default))

    @staticmethod
    def get_page_size(request: object, key: str = "page_size", default: int = 100) -> int:
        return NumberUtilities.get_integer_from_string(request.query_params.get(key, default))
