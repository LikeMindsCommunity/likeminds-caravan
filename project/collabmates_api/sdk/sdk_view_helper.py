from utility.response_utilities import ResponseUtilities


class SdkViewHelper:

    @staticmethod
    def create_sdk_body_validator(request_body, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if not member_id:
            return ResponseUtilities.get_inner_error_context('send member_id in headers')

        if 'name' not in request_body:
            return ResponseUtilities.get_inner_error_context('send name in body')

        if 'headline' not in request_body:
            return ResponseUtilities.get_inner_error_context('send headline in body')

        if 'brand_color' not in request_body:
            return ResponseUtilities.get_inner_error_context('send brand_color in body')

        if 'platform' in request_body and not isinstance(request_body['platform'], list):
            return ResponseUtilities.get_inner_error_context('platform object should be a list')

        return request_body

    @staticmethod
    def initiate_sdk_body_validator(request_body):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if 'user_name' not in request_body:
            return ResponseUtilities.get_inner_error_context('send user_name in body')

        if 'api_key' not in request_body:
            return ResponseUtilities.get_inner_error_context('send api_key in body')

        return request_body

    @staticmethod
    def authenticate_sdk_body_validator(request_body):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if 'api_key' not in request_body:
            return ResponseUtilities.get_inner_error_context('send api_key in body')

        return request_body
