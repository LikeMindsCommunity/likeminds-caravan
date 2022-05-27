from utility.response_utilities import ResponseUtilities


class SdkViewHelper:

    @staticmethod
    def create_sdk_project_body_validator(request_body, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if not member_id:
            return ResponseUtilities.get_inner_error_context('send member_id in headers')

        if 'project_creator' not in request_body or not request_body.get('project_creator'):
            return ResponseUtilities.get_inner_error_context('send project_creator in body')

        if 'name' not in request_body or not request_body.get('name'):
            return ResponseUtilities.get_inner_error_context('send name in body')

        if 'platform' in request_body and request_body['platform'] and not isinstance(request_body['platform'], list):
            return ResponseUtilities.get_inner_error_context('platform object should be a list')

        return request_body

    @staticmethod
    def initiate_sdk_body_validator(request_body):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if 'user_name' not in request_body:
            return ResponseUtilities.get_inner_error_context('send user_name in body')

        return request_body
