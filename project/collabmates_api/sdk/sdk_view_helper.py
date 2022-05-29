from utility.response_utilities import ResponseUtilities
from togther.models import ModelUtilities


class SdkViewHelper:

    @staticmethod
    def fetch_sdk_project_validator(request_params, member_id):

        if not request_params:
            return ResponseUtilities.get_inner_error_context('invalid request params')

        if 'project_creator' not in request_params and not request_params.get('project_creator'):
            return ResponseUtilities.get_inner_error_context('send project_creator in params')

        project_creator = ModelUtilities.get_user_instance_or_none(request_params.get('project_creator'))

        if not project_creator:
            return ResponseUtilities.get_inner_error_context('Invalid project_creator')

        if not member_id:
            return ResponseUtilities.get_inner_error_context('send member_id in headers')

        member = ModelUtilities.get_user_instance_or_none(member_id)

        if not member:
            return ResponseUtilities.get_inner_error_context('Invalid x-member-id')

        return {'project_creator': project_creator}

    @staticmethod
    def create_sdk_project_body_validator(request_body, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if not member_id:
            return ResponseUtilities.get_inner_error_context('send member_id in headers')

        member = ModelUtilities.get_user_instance_or_none(member_id)

        if not member:
            return ResponseUtilities.get_inner_error_context('Invalid x-member-id')

        if 'project_creator' not in request_body or not request_body.get('project_creator'):
            return ResponseUtilities.get_inner_error_context('send project_creator in body')

        project_creator = ModelUtilities.get_user_instance_or_none(request_body.get('project_creator'))

        if not project_creator:
            return ResponseUtilities.get_inner_error_context('Invalid project_creator')

        if 'name' not in request_body or not request_body.get('name'):
            return ResponseUtilities.get_inner_error_context('send name in body')

        if 'platform' in request_body and request_body['platform'] and not isinstance(request_body['platform'], list):
            return ResponseUtilities.get_inner_error_context('platform object should be a list')

        return {'project_creator': project_creator}

    @staticmethod
    def initiate_sdk_body_validator(request_body):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if 'user_name' not in request_body:
            return ResponseUtilities.get_inner_error_context('send user_name in body')

        return request_body
