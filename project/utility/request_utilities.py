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
        return request.META.get('HTTP_X_PLATFORM_CODE') == "web"

    @staticmethod
    def is_request_android(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE') == "an"

    @staticmethod
    def is_request_ios(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE').lower() == "ios"

    @staticmethod
    def get_request_type(request: str) -> str:
        platform_code = request.META.get('HTTP_X_PLATFORM_CODE')

        if platform_code:

            if platform_code == "an":
                return "android"

            elif platform_code == "iOS":
                return "iOS"

            elif platform_code == "web":
                return "web"

        return "Invalid request"


