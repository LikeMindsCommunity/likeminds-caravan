from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Collabcard, card_answers)


class ConversationViewHelper:

    @staticmethod
    def validate_set_topic_request(user_id, chatroom_id, conversation_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not chatroom_instance:
            return ResponseUtilities.get_inner_error_context("Invalid chatroom id")

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

        if not conversation_instance:
            return ResponseUtilities.get_inner_error_context("Invalid conversation id")

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance,
            'conversation_instance': conversation_instance
        }
