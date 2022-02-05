from utility.states import message_template_chatroom_types
from utility.response_utilities import ResponseUtilities


class AutomateMessageViewHelper:

    @staticmethod
    def template_body_validator(request_body, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        if 'community_id' not in request_body:
            return ResponseUtilities.get_inner_error_context('send community_id in body')

        if 'chatroom_type' not in request_body:
            return ResponseUtilities.get_inner_error_context('send chatroom_type in body')

        if request_body['chatroom_type'] not in [message_template_chatroom_types.DM_CHATROOM]:
            return ResponseUtilities.get_inner_error_context('send valid chatroom_type in body')

        if 'message' not in request_body:
            return ResponseUtilities.get_inner_error_context('send message in body')

        if not member_id:
            return ResponseUtilities.get_inner_error_context('send member_id in headers')

        return request_body
