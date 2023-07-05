from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Members, Collabcard, collabcardState, userMemberRights)
from rest_framework import status as status_codes
from utility.states import (member_states, card_types)
from collabmates_api.sdk.models import (SdkClient)
import json


class ChatroomViewHelper:

    @staticmethod
    def validate_req_body(req_body):

        if not req_body:
            return ResponseUtilities.get_view_impl_error_context("Invalid request body",
                                                                 status_code=status_codes.HTTP_400_BAD_REQUEST)

        return {}

    @staticmethod
    def validate_fetch_all_chatroom_request(user_id, api_key, chatroom_filter_type, chatroom_excluded_type):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        is_cm = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_cm:
            return ResponseUtilities.get_inner_error_context('You are not the owner/CM of community')

        chatroom_type_filter = []
        if isinstance(chatroom_filter_type, str):
            try:
                chatroom_type_filter = json.loads(chatroom_filter_type)
            except:
                return ResponseUtilities.get_inner_error_context("Invalid filter_type object")

        chatroom_type_excluded = []
        if isinstance(chatroom_excluded_type, str):
            try:
                chatroom_type_excluded = json.loads(chatroom_excluded_type)
            except:
                return ResponseUtilities.get_inner_error_context("Invalid excluded_type object")

        return {'user_instance': user_instance, 'community_instance': community_instance,
                'chatroom_filter_type': chatroom_type_filter, 'chatroom_excluded_type': chatroom_type_excluded}

    @staticmethod
    def validate_create_chatroom_request(user_id, api_key, req_body):

        if not req_body.get('title'):
            return ResponseUtilities.get_inner_error_context("Invalid chatroom title!")

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(community_id=req_body.get('community_id'),
                                                                      api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key/community ID")

        is_member = Members.is_community_member(community_instance, user_instance)

        if not is_member:
            return ResponseUtilities.get_inner_error_context("You cannot create a chatroom")

        has_rights = userMemberRights.check_member_create_room_right(user_instance, community_instance)
        
        if not has_rights:
            return ResponseUtilities.get_inner_error_context("You don't have the rights to create a chatroom")

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
        uuids = req_body.get('uuids', None)
        
        if (secret_chatroom_participants or uuids) is None:
            return ResponseUtilities.get_inner_error_context("send secret_chatroom_participants or uuids in body")

        return {'user_instance': user_instance, 'card_instance': card_instance,
                'secret_chatroom_participants': secret_chatroom_participants, 'uuids': uuids}

    @staticmethod
    def validate_add_members_to_open_chatroom(user_id, chatroom_id, chatroom_participants, uuids = None):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("In-valid user id")

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("In-valid chatroom id")

        if card_instance.is_secret:
            return ResponseUtilities.get_inner_error_context("Chatroom is secret!")

        if not (chatroom_participants or uuids):
            return ResponseUtilities.get_inner_error_context("Invalid Chatroom participants or uuids")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': card_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("User is not a member of community")

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return ResponseUtilities.get_inner_error_context("User doesn't have the ability to perform this operation")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_chatroom_auto_follow_for_all_members_request(chatroom_id, member_id):
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("In-valid chatroom id")

        user_instance = ModelUtilities.get_user_instance_or_none(member_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("In-valid user id")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': card_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("You are not a part of this community.")

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return ResponseUtilities.get_inner_error_context("You need to be Owner/CM of the community to enable auto "
                                                             "follow")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_pin_unpin_chatroom_request(chatroom_id, member_id):

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("In-valid chatroom id")

        user_instance = ModelUtilities.get_user_instance_or_none(member_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("In-valid user id")

        if card_instance.is_secret:
            return ResponseUtilities.get_inner_error_context("Secret chatroom cannot be pinned!")

        if card_instance.type not in [card_types.CARD_NORMAL, card_types.CARD_POLL, card_types.CARD_PURPOSE]:
            return ResponseUtilities.get_inner_error_context("Invalid chatroom type!")

        if not ModelUtilities.is_model_filter_exists(Members, {'state': member_states.ADMIN,
                                                               'member_id': member_id,
                                                               'community_id': card_instance.community}):
            return ResponseUtilities.get_inner_error_context("You need to be promoter in order to pin unpin!")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_fetch_chatroom_settings_request(member_id, chatroom_id):
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("In-valid chatroom id")

        user_instance = ModelUtilities.get_user_instance_or_none(member_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("In-valid user id")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': card_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("You are not a part of this community.")

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return ResponseUtilities.get_inner_error_context("You can’t view settings of this chatroom!")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_change_chatroom_type_request(member_id, req_body):
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, req_body.get('chatroom_id'))

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("In-valid chatroom id")

        user_instance = ModelUtilities.get_user_instance_or_none(member_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("In-valid user id")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': card_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("You are not a part of this community.")

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return ResponseUtilities.get_inner_error_context("You don’t have ability to change chatroom type")

        if 'is_secret' not in req_body:
            return ResponseUtilities.get_inner_error_context("Send chatroom type to update")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_change_chatroom_type_status_request(member_id, chatroom_id):
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("In-valid chatroom id")

        user_instance = ModelUtilities.get_user_instance_or_none(member_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("In-valid user id")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': card_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("You are not a part of this community.")

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return ResponseUtilities.get_inner_error_context("You are not CM/owner or chatroom creator!")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_update_chatroom_notification_setting_request(user_id, chatroom_id):
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("In-valid chatroom id")

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("In-valid user id")

        collabcard_state_instance = ModelUtilities.get_model_filter(collabcardState,
                                                                    {'card': card_instance,
                                                                     'user': user_instance})

        if not collabcard_state_instance:
            return ResponseUtilities.get_inner_error_context("You are not part of the chatroom.")

        return {'collabcard_state_instance': collabcard_state_instance}

    @staticmethod
    def validate_get_tagging_list_request(member_id, chatroom_id):
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("In-valid chatroom id")

        user_instance = ModelUtilities.get_user_instance_or_none(member_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("In-valid user id")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_update_files_request(member_id, chatroom_id):
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("Invalid chatroom id")

        user_instance = ModelUtilities.get_user_instance_or_none(member_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        if card_instance.user_id != user_instance.id:
            return ResponseUtilities.get_inner_error_context("Only chatroom creator can update files")

        return {'user_instance': user_instance, 'card_instance': card_instance}

    @staticmethod
    def validate_fetch_chatroom_notification_setting_request(user_id, chatroom_id):
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return ResponseUtilities.get_inner_error_context("In-valid chatroom id")

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("In-valid user id")

        collabcard_state_instance = ModelUtilities.get_model_filter(collabcardState,
                                                                    {'card': card_instance,
                                                                     'user': user_instance})

        if not collabcard_state_instance:
            return ResponseUtilities.get_inner_error_context("You are not part of the chatroom.")

        return {'collabcard_state_instance': collabcard_state_instance[0]}

    @staticmethod
    def validate_create_dm_chatroom_request(user_id, req_body, api_key):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(community_id=req_body.get('community_id'),
                                                                      api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community id")
        
        member_id = req_body.get('member_id')
        uuid = req_body.get('uuid')

        member_instance = None

        # If uuid is present, get valid user id from uuid 
        if uuid:
            valid_id = ModelUtilities.get_valid_user_ids_from_uuids([uuid], community_instance.id)
            
            if not valid_id:
                return ResponseUtilities.get_inner_error_context("Invalid uuid")
            
            member_instance = ModelUtilities.get_user_instance_or_none(valid_id[0])
        
        else:    
            member_instance = ModelUtilities.get_user_instance_or_none(member_id,
                                                                       community_id=community_instance.id)

        if not member_instance:
            return ResponseUtilities.get_inner_error_context("Invalid member id")

        is_user_member = Members.is_community_member(community=community_instance, member=user_instance)

        if not is_user_member:
            return ResponseUtilities.get_inner_error_context("You are not a member")

        is_member = Members.is_community_member(community=community_instance, member=member_instance)

        if not is_member:
            return ResponseUtilities.get_inner_error_context("User with member-id is not member of community")
        
        if user_instance.id == member_instance.id:
            return ResponseUtilities.get_inner_error_context("You cannot create a chatroom with yourself")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'member_instance': member_instance,
            'custom_tag': req_body.get('tag', ''),
        }
