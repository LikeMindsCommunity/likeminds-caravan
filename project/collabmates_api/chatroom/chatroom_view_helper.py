from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Members, Collabcard)
from collabmates_api.sdk.models import SdkClient
from rest_framework import status as status_codes
from utility.states import (member_states)


class ChatroomViewHelper:

    @staticmethod
    def validate_req_body(req_body):

        if not req_body:
            return ResponseUtilities.get_view_impl_error_context("Invalid request body",
                                                                 status_code=status_codes.HTTP_400_BAD_REQUEST)

        return {}

    @staticmethod
    def validate_fetch_all_chatroom_request(user_id, api_key):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_create_chatroom_request(user_id, api_key, req_body):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_id = req_body.get('community_id') if req_body.get('community_id') else api_key
        community_instance = SdkClient.get_community_instance_or_none(community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key/community ID")

        is_member = Members.is_community_member(community_instance, user_instance)

        if not is_member:
            return ResponseUtilities.get_inner_error_context("You cannot create a chatroom")

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_edit_chatroom_request(user_id, card_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("Invalid chatroom id")

        is_cm = Members.is_member_community_promoter(card_instance.community, user_instance)

        if card_instance.user_id != user_instance.id and not is_cm:
            return ResponseUtilities.get_inner_error_context("You don’t have ability to update chatroom meta data")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_fetch_participants_meta(user_id, chatroom_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("Invalid chatroom id")

        if card_instance.is_secret:
            return ResponseUtilities.get_inner_error_context("Chatroom is secret!")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_add_secret_chatroom_participants_request(user_id, chatroom_id, req_body):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("Invalid chatroom id")

        if not card_instance.is_secret:
            return ResponseUtilities.get_inner_error_context("Chatroom is not secret!")

        secret_chatroom_participants = req_body.get('secret_chatroom_participants', None)

        if secret_chatroom_participants is None:
            return ResponseUtilities.get_inner_error_context("send secret_chatroom_participants in body")

        return {'user_instance': user_instance, 'card_instance': card_instance,
                'secret_chatroom_participants': secret_chatroom_participants}

    @staticmethod
    def validate_add_members_to_open_chatroom(user_id, chatroom_id, chatroom_participants):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("In-valid user id")

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("In-valid chatroom id")

        if card_instance.is_secret:
            return ResponseUtilities.get_inner_error_context("Chatroom is secret!")

        if not chatroom_participants:
            return ResponseUtilities.get_inner_error_context("Invalid Chatroom participants")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': card_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("User is not a member of community")

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return ResponseUtilities.get_inner_error_context("User doesn't have the ability to perform this operation")

        return {'user_instance': user_instance, 'card_instance': card_instance}
