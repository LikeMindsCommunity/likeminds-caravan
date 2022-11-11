import re

from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Collabcard, card_answers, Members, userMemberRights)
from utility.states import (member_states, card_types, conversation_states, member_rights)
from .constants import (ERROR_MESSAGE_FOR_ANNOUNCEMENT_ROOM)
from utility.time_utilities import TimeUtilities
from ..static_text import EVERYONE_TAG_REGEX, PARTICIPANTS_TAG_REGEX


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

    def validate_create_conversation_request(self, user_instance, user_id, chatroom_instance, chatroom_id, message):

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

        is_tag_allowed = self._validate_group_tags(
            message,
            member_state,
            user_id,
            chatroom_instance.user.id,
            chatroom_instance.is_secret
        )
        if not is_tag_allowed:
            return ResponseUtilities.get_inner_error_context('tag not allowed')

        if chatroom_instance.type == card_types.CARD_PURPOSE and \
                member_state != member_states.ADMIN:
            return ResponseUtilities.get_inner_error_context(ERROR_MESSAGE_FOR_ANNOUNCEMENT_ROOM)

        if chatroom_instance.type == card_types.CARD_MASTER_INTRO:
            return ResponseUtilities.get_inner_error_context("Responding is disabled")

        has_right = ModelUtilities.get_model_filter(userMemberRights,
                                                    {'user': user_instance, 'community': community_instance,
                                                     'right__state': member_rights.MEMBER_RIGHT_RESPOND_IN_ROOM})

        if not has_right:
            return ResponseUtilities.get_inner_error_context("You don't have right to respond in chatroom!")

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance,
            'member_state': member_state
        }

    @staticmethod
    def _validate_group_tags(
            message: str,
            member_state: int,
            user_id: int,
            chatroom_creator_id: int,
            is_secret_chatroom: bool
    ) -> bool:
        is_everyone_tag: list = re.findall(EVERYONE_TAG_REGEX, message)
        if is_everyone_tag and is_secret_chatroom:
            return False

        if is_everyone_tag and member_state != member_states.ADMIN:
            return False

        is_participants_tag: list = re.findall(PARTICIPANTS_TAG_REGEX, message)
        if is_participants_tag and member_state != member_states.ADMIN and user_id != chatroom_creator_id:
            return False

        return True

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

    @staticmethod
    def validate_remove_reaction_request(user_id, chatroom_id, conversation_id):
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

    @staticmethod
    def validate_add_poll_request(user_id, req_body):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context('Invalid member id')

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, req_body.get('conversation_id'))

        if not conversation_instance:
            return ResponseUtilities.get_inner_error_context('Invalid conversation id')

        if not isinstance(req_body.get('poll'), dict):
            return ResponseUtilities.get_inner_error_context('Send correct structure of poll data')

        if not conversation_instance.allow_add_option:
            return ResponseUtilities.get_inner_error_context('New option cannot be added!')

        return {
            'user_instance': user_instance,
            'conversation_instance': conversation_instance
        }

    @staticmethod
    def validate_submit_poll_request(user_id, req_body):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context('Invalid member id')

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, req_body.get('conversation_id'))

        if not conversation_instance:
            return ResponseUtilities.get_inner_error_context('Invalid conversation id')

        if not isinstance(req_body.get('polls'), list):
            return ResponseUtilities.get_inner_error_context('Send correct structure of polls data')

        if (not conversation_instance.expiry_time) or conversation_instance.expiry_time < \
                TimeUtilities.current_time_in_milliseconds():
            return ResponseUtilities.get_inner_error_context('Poll has been ended')

        return {
            'user_instance': user_instance,
            'conversation_instance': conversation_instance
        }

    @staticmethod
    def validate_poll_users_request(user_id, conversation_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context('Invalid member id')

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

        if not conversation_instance:
            return ResponseUtilities.get_inner_error_context('Invalid conversation id')

        return {
            'user_instance': user_instance,
            'conversation_instance': conversation_instance
        }

    @staticmethod
    def validate_event_attend_request(user_id, conversation_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context('Invalid member id')

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

        if not conversation_instance:
            return ResponseUtilities.get_inner_error_context('Invalid conversation id')

        if conversation_instance.state != conversation_states.CONVERSATION_EVENT:
            return ResponseUtilities.get_inner_error_context('Not an event conversation')

        return {
            'user_instance': user_instance,
            'conversation_instance': conversation_instance
        }

    @staticmethod
    def validate_event_attended_request(user_id, conversation_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context('Invalid member id')

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

        if not conversation_instance:
            return ResponseUtilities.get_inner_error_context('Invalid conversation id')

        if conversation_instance.state != conversation_states.CONVERSATION_EVENT:
            return ResponseUtilities.get_inner_error_context('Not an event conversation')

        return {
            'user_instance': user_instance,
            'conversation_instance': conversation_instance
        }

    @staticmethod
    def validate_event_fetch_link_request(user_id, conversation_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context('Invalid member id')

        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

        if not conversation_instance:
            return ResponseUtilities.get_inner_error_context('Invalid conversation id')

        return {
            'user_instance': user_instance,
            'conversation_instance': conversation_instance
        }

    @staticmethod
    def validate_fetch_unread_previews_request(user_id, chatroom_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context('Invalid member id')

        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not chatroom_instance:
            return ResponseUtilities.get_inner_error_context('Invalid chatroom id')

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': chatroom_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context('User is not a member of community')

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance
        }

    @staticmethod
    def validate_fetch_preview_unread_messages_count_request(user_id, chatroom_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context('Invalid member id')

        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not chatroom_instance:
            return ResponseUtilities.get_inner_error_context('Invalid chatroom id')

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': chatroom_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context('User is not a member of community')

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance
        }

