class RequestUtilities:

    @staticmethod
    def get_member_id_from_headers(request: {}) -> int:
        return request.META['HTTP_X_MEMBER_ID']
