class RequestUtilities:

    @staticmethod
    def get_member_id_from_headers(request: object) -> str:
        return request.META.get('HTTP_X_MEMBER_ID')
