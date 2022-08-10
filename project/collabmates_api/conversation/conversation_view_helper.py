from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Collabcard, card_answers, Members)
from utility.states import (member_states, card_types)
from .constants import (ERROR_MESSAGE_FOR_ANNOUNCEMENT_ROOM)


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

    @staticmethod
    def validate_create_conversation_request(user_instance, user_id, chatroom_instance, chatroom_id):

        if user_instance is None:
            user_instance = ModelUtilities.get_user_instance_or_none(user_id)

            if not user_instance:
                return ResponseUtilities.get_inner_error_context('Invalid member id')

        if chatroom_instance is None:
            chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

            if not chatroom_instance:
                return ResponseUtilities.get_inner_error_context('Invalid chatroom id')

        if chatroom_instance.is_pending:
            return ResponseUtilities.get_inner_error_context('This is a pending chatroom!')

        community_instance = chatroom_instance.community
        member_state = Members.get_community_member_state(community_instance, user_instance)

        if chatroom_instance.type == card_types.CARD_PURPOSE and \
                member_state != member_states.ADMIN:
            return ResponseUtilities.get_inner_error_context(ERROR_MESSAGE_FOR_ANNOUNCEMENT_ROOM)

        if chatroom_instance.type == card_types.CARD_MASTER_INTRO:
            return ResponseUtilities.get_inner_error_context("Responding is disabled")

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance,
            'member_state': member_state
        }

    @staticmethod
    def validate_add_reaction_request(user_id, chatroom_id, conversation_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context('Invalid member id')

        if not (chatroom_id or conversation_id):
            return ResponseUtilities.get_inner_error_context('Send conversation_id or chatroom_id')

        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if chatroom_id and not chatroom_instance:
            return ResponseUtilities.get_inner_error_context('Invalid chatroom id')

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

        if conversation_id and not conversation_instance:
            return ResponseUtilities.get_inner_error_context('Invalid conversation id')

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance,
            'conversation_instance': conversation_instance
        }
