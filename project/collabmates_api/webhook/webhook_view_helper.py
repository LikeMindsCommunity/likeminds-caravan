from utility.states import webhook_types
from utility.response_utilities import ResponseUtilities


class WebhookViewHelper:

    @staticmethod
    def webhook_body_validator(request_body, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if 'community_id' not in request_body:
            return ResponseUtilities.get_inner_error_context('send community_id in body')

        if 'webhook_type' not in request_body:
            return ResponseUtilities.get_inner_error_context('send webhook_type in body')

        if request_body['webhook_type'] not in [webhook_types.COMMUNITY_JOIN]:
            return ResponseUtilities.get_inner_error_context('send valid webhook_type in body')

        if 'url' not in request_body:
            return ResponseUtilities.get_inner_error_context('send url in body')

        if not member_id:
            return ResponseUtilities.get_inner_error_context('send member_id in headers')

        return request_body

    @staticmethod
    def fetch_webhook_body_validator(request_body, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if 'community_id' not in request_body:
            return ResponseUtilities.get_inner_error_context('send community_id in body')

        if not member_id:
            return ResponseUtilities.get_inner_error_context('send member_id in headers')

        return request_body

    @staticmethod
    def delete_webhook_body_validator(request_body, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if 'community_id' not in request_body:
            return ResponseUtilities.get_inner_error_context('send community_id in body')

        if 'webhook_id' not in request_body:
            return ResponseUtilities.get_inner_error_context('send webhook_id in body')

        if not member_id:
            return ResponseUtilities.get_inner_error_context('send member_id in headers')

        return request_body
