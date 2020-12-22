import json
class RequestUtilities:

    @staticmethod
    def get_member_id_from_headers(request: object) -> str:
        return request.META.get('HTTP_X_MEMBER_ID')

    def fetch_request_body(request):

        request_body = json.loads(request.body)

        return request_body
