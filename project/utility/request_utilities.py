import json
class RequestUtilities:

    @staticmethod
    def get_member_id_from_headers(request: object) -> str:
        return request.META.get('HTTP_X_MEMBER_ID')

    def fetch_request_body(request):

        request_body = json.loads(request.body)

        return request_body

    def is_request_web(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE') == "web"

    def is_request_android(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE') == "an"

    def is_request_ios(request: object):
        return request.META.get('HTTP_X_PLATFORM_CODE') == "iOS"

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


