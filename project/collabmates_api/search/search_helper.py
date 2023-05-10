from togther.models import (ModelUtilities, Collabcard, Members)
from collabmates_api.serializers import (get_menu_for_members)
from utility.states import (member_states)
from collabmates_api.user_moderation_rights import (check_all_manager_rights)


class SearchHelper:

    @staticmethod
    def has_attachments_uploaded(chatroom):
        if chatroom['attachment_count'] > 0 and chatroom['attachments_uploaded'] is False:
            return False

        return True

    @staticmethod
    def update_chatroom_member_to_creator_for_card_data(chatroom_data):

        chatroom_ids_list = [state_data.get('chatroom').get('id') for state_data in chatroom_data
                             if state_data.get('chatroom')]

        card_creators_data = list(ModelUtilities.get_model_filter(
            Collabcard, {'id__in': chatroom_ids_list}).select_related('user').values('id', 'user__id',
                                                                                     'user__userinfo__name'))

        card_creators_data = {creator_data.get('id'): creator_data for creator_data in card_creators_data}

        for card_data in chatroom_data:
            creator_data = card_creators_data.get(card_data.get('chatroom').get('id'))

            card_data['member'] = {
                'id': creator_data.get('user__id'),
                'profile': {
                    'name': creator_data.get('user__userinfo__name')
                }
            }

        return chatroom_data

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
