from utility.states import WebhookTypes
from utility.response_utilities import ResponseUtilities

class WebhookViewHelper:

    @staticmethod
    def validate_basic_webhook_request(member_id, api_key):

        if not member_id:
            return ResponseUtilities.get_inner_error_context('send x-member-id in headers')
        
        if not api_key:
            return ResponseUtilities.get_inner_error_context('send x-api-key in headers')

        return {'success': True}

    @staticmethod
    def validate_body_webhook_request(request_body, member_id, api_key=None):

        basic_validation = WebhookViewHelper.validate_basic_webhook_request(member_id, api_key)

        if 'error_message' in basic_validation:
            return basic_validation

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        return {'success': True}

    @staticmethod
    def add_webhook_body_validator(request_body, member_id, api_key=None):

        basic_validation = WebhookViewHelper.validate_body_webhook_request(request_body, member_id, api_key)

        if 'error_message' in basic_validation:
            return basic_validation

        if 'webhook_type' not in request_body:
            return ResponseUtilities.get_inner_error_context('send webhook_type in body')

        if not WebhookTypes.validate_webhook_type(request_body['webhook_type']):
            return ResponseUtilities.get_inner_error_context('send valid webhook_type in body')

        if 'url' not in request_body:
            return ResponseUtilities.get_inner_error_context('send url in body')
        
        if 'is_active' not in request_body:
            return ResponseUtilities.get_inner_error_context('send is_active in body')

        return request_body

    @staticmethod
    def update_webhook_body_validator(request_body, member_id, api_key):

        basic_validator = WebhookViewHelper.validate_basic_webhook_request(member_id, api_key)

        if 'error_message' in basic_validator:
            return basic_validator

        url = request_body.get('url')
        is_active = request_body.get('is_active')

        if (not url) and (is_active is None):
            return ResponseUtilities.get_inner_error_context('Please send url or is_active in body')
        
        if is_active and not isinstance(is_active, bool):
            return ResponseUtilities.get_inner_error_context('is_active should be boolean')

        return request_body
