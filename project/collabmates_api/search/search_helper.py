from togther.models import (ModelUtilities, Collabcard, Members, Userinfo)
from collabmates_api.serializers import (get_menu_for_members)
from utility.states import (member_states)
from collabmates_api.user_moderation_rights import (check_all_manager_rights)
from utility.time_utilities import TimeUtilities
from ..raw_queries import (get_chatroom_participants_count, get_users_sdk_meta_dict)

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()


class SearchHelper:

    @staticmethod
    def has_attachments_uploaded(chatroom):
        if chatroom['attachment_count'] > 0 and chatroom['attachments_uploaded'] is False:
            return False

        return True

    @staticmethod
    def serialize_chatroom_data_response(chatroom_data):

        chatroom_ids_list = [data.get('chatroom').get('id') for data in chatroom_data
                             if data.get('chatroom')]

        # Get chatroom instances with user objects
        card_instances = ModelUtilities.get_model_filter(Collabcard, 
                                                           {'id__in': chatroom_ids_list})
        
        user_ids = [card.user_id for card in card_instances]

        error_logger.error(f"search/chatroom fetching fetching users_sdk_meta_dict ")

        # Get sdk_client_info for user_ids
        serialised_usersinfo_dict = get_users_sdk_meta_dict(user_ids)

        error_logger.error(f"search/chatroom done fetching fetching users_sdk_meta_dict ")
    
        chatroom_creators_meta = {}

        # Serialize chatrooms creator with UserInfoSeralizer with sdk_client_info 
        for card in card_instances:
            chatroom_creators_meta[card.id]  = serialised_usersinfo_dict.get(card.user_id)
        
        for card_data in chatroom_data:

            chatroom_id = card_data.get('chatroom').get('id')

            error_logger.error(f"search/chatroom serialising chatroom_data for {chatroom_id}")

            creator = chatroom_creators_meta.get(chatroom_id)

            creator['profile'] = {
                    'name': creator['name'],
            }

            card_data['member'] = creator
            card_data['chatroom']['member'] = creator
            card_data['chatroom']['date'] = TimeUtilities.convert_epoch_time_in_date(card_data['chatroom']['created_at'])

            error_logger.error(f"search/chatroom fetching chatroom participants count for chatroom_id: {chatroom_id} ")

            card_data['chatroom']['participants_count'] = get_chatroom_participants_count(card_data['chatroom']['id'], card_data['community']['id'])

            error_logger.error(f"search/chatroom done fetching chatroom participants count for chatroom_id: {chatroom_id} ")

        return chatroom_data
    
    @staticmethod
    def serialize_conversation_data_from_search_res(res_dict):

        conversations_data = [hit.to_dict() for hit in res_dict]

        member_ids = [conversation.get('member').get('id') for conversation in conversations_data
                                if conversation.get('member')]
        
        # Get user instances with user objects
        serialised_user_info_dict = get_users_sdk_meta_dict(member_ids)

        # Update user info in 'member' object of conversations_data
        for conversation in conversations_data:

            if conversation.get('member'):
                member_id = conversation.get('member').get('id')
                conversation.get('member').update(serialised_user_info_dict.get(member_id))

        return conversations_data

    @staticmethod
    def get_menu_items_for_member_in_search(current_user_id, user_id, community_id, user_data):
        user_menu = []

        if not (current_user_id or user_id or community_id):
            return user_menu

        current_member_instance = ModelUtilities.get_model_filter(Members,
                                                                  {'community_id': community_id,
                                                                   'member_id': current_user_id}).first()

        if not current_member_instance:
            return user_menu

        current_user_is_promoter = current_member_instance.state == member_states.ADMIN

        user_admin_rights = None

        if current_member_instance.is_owner or current_user_is_promoter:
            user_admin_rights = check_all_manager_rights(current_user_id, community_id)

        return get_menu_for_members(current_user_id=current_user_id,
                                    item_member_id=user_id,
                                    community_id=community_id,
                                    current_user_is_promoter=current_user_is_promoter,
                                    current_user_is_owner=current_member_instance.is_owner,
                                    item_member_state=user_data.get('state'),
                                    item_member_is_owner=user_data.get('is_owner'),
                                    parents_list=user_data.get('parent_cm_list'),
                                    current_user_admin_rights=user_admin_rights)
