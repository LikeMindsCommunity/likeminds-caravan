import json
from .number_utilities import NumberUtilities


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
    def is_request_web(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE', '').lower() == "web"

    @staticmethod
    def is_request_android(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE', '').lower() == "an"

    @staticmethod
    def is_request_ios(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE', '').lower() == "ios"

    @staticmethod
    def get_request_type(request: str) -> str:
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

        return "Invalid request"

    @staticmethod
    def get_user_name_from_headers(request: object) -> str:
        return request.META.get('HTTP_X_USERNAME')

    @staticmethod
    def get_password_from_headers(request: object) -> str:
        return request.META.get('HTTP_X_PASSWORD')
