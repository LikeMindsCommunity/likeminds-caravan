import time

from togther.models import memberRights, ModelUtilities, Community, CommunitySettings, Members, \
    communityRightsSettings, adminRights, userAdminRights, Collabcard, collabcardState, card_answers
from collabmates_api.community.constants import COMMUNITY_SETTING_TYPE_TITLE_MAPPING, \
    COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING, DM_COMMUNITY_SETTING_SUB_TITLE_WHEN_ENABLED
from utility.states import member_rights, community_setting_types, card_types, member_states, SyncTypes, \
    conversation_states, chat_request_states
from collabmates_api.static_text import members_can_dm_right, delete_room_manager_right, approve_manager_right, \
    moderate_dm_settings, edit_community_manager_right, view_contact_manager_right, add_manager_manager_right
from collabmates_api.sync.model_update import update_models_for_syncing_apis


all_manager_rights = [delete_room_manager_right, approve_manager_right, edit_community_manager_right,
                      view_contact_manager_right, add_manager_manager_right, moderate_dm_settings]


def create_or_update_manager_rights_data():
    print("Creating or Updating manager rights")

    for manager_right in all_manager_rights:
        ModelUtilities.update_or_create_model(adminRights, {'state': manager_right.get('state')}, manager_right)


def add_members_can_dm_right():
    print("Creating members can DM right")
    ModelUtilities.update_or_create_model(memberRights, {'state': members_can_dm_right.get('state')},
                                          members_can_dm_right)


def backfill_manager_moderate_dm_setting_right():
    all_community_owners_filter = ModelUtilities.get_model_filter(Members, {'is_owner': True})
    moderate_dm_admin_right = ModelUtilities.get_model_filter(adminRights,
                                                              {'state': moderate_dm_settings.get('state')})[0]

    for member_instance in all_community_owners_filter:

        filter_dict = {
            'community': member_instance.community_id,
            'user': member_instance.member_id,
            'right': moderate_dm_admin_right
        }

        ModelUtilities.update_or_create_model(userAdminRights, filter_dict, filter_dict)


def backfill_community_settings_for_direct_messages():
    all_communities_filter = ModelUtilities.get_model_filter(Community, {})
    community_settings_list = []

    for community_instance in all_communities_filter:

        user_instance = Members.get_community_owner_user_instance_or_none(community_instance)

        for setting_type in [community_setting_types.DIRECT_MESSAGES, community_setting_types.MEMBERS_CAN_DM,
                             community_setting_types.DIRECT_MESSAGE_SETTING]:

            community_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                                       {'setting_type': setting_type,
                                                                        'community': community_instance})
            if community_setting_filter:
                continue

            is_enabled = False
            sub_title = COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING.get(setting_type)

            community_dm_right = ModelUtilities.get_model_filter(
                communityRightsSettings, {"community": community_instance,
                                          "right__state": member_rights.MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES})

            if setting_type == community_setting_types.DIRECT_MESSAGES:
                is_enabled = community_dm_right.exists()
                sub_title = DM_COMMUNITY_SETTING_SUB_TITLE_WHEN_ENABLED

            if setting_type == community_setting_types.DIRECT_MESSAGE_SETTING:
                is_enabled = True

            community_settings_data = {
                'community_instance': community_instance,
                'setting_type': setting_type,
                'setting_title': COMMUNITY_SETTING_TYPE_TITLE_MAPPING.get(setting_type),
                'setting_sub_title': sub_title,
                'enabled': is_enabled,
                'enabled_by': user_instance,
            }
            community_settings_instance = CommunitySettings.create_instance(community_settings_data)
            community_settings_list.append(community_settings_instance)

    ModelUtilities.bulk_create_instances(CommunitySettings, community_settings_list)


def backfill_community_settings_for_direct_messages_setting():
    all_communities_filter = ModelUtilities.get_model_filter(Community, {})
    community_settings_list = []

    for community_instance in all_communities_filter:

        user_instance = Members.get_community_owner_user_instance_or_none(community_instance)

        for setting_type in [community_setting_types.DIRECT_MESSAGE_SETTING]:

            community_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                                       {'setting_type': setting_type,
                                                                        'community': community_instance})
            if community_setting_filter:
                continue

            is_enabled = True
            sub_title = COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING.get(setting_type)

            community_settings_data = {
                'community_instance': community_instance,
                'setting_type': setting_type,
                'setting_title': COMMUNITY_SETTING_TYPE_TITLE_MAPPING.get(setting_type),
                'setting_sub_title': sub_title,
                'enabled': is_enabled,
                'enabled_by': user_instance,
            }
            community_settings_instance = CommunitySettings.create_instance(community_settings_data)
            community_settings_list.append(community_settings_instance)

    ModelUtilities.bulk_create_instances(CommunitySettings, community_settings_list)


def backfill_is_private_member_value():
    card_filter = ModelUtilities.get_model_filter(Collabcard, {'is_private': True,
                                                               'type': card_types.CARD_DIRECT_MESSAGE})

    count = card_filter.count()

    for card_instance in card_filter:

        print("Chatrooms Left -->", count)

        if not card_instance.community:
            continue

        if (not card_instance.user) or (not card_instance.chatroom_with_user):
            continue

        user_member_state = Members.get_community_member_state(card_instance.community, card_instance.user)
        chatroom_with_user_member_state = Members.get_community_member_state(card_instance.community,
                                                                             card_instance.chatroom_with_user)

        if (user_member_state == member_states.ADMIN) or (chatroom_with_user_member_state == member_states.ADMIN):
            card_instance.is_private_member = False
            card_instance.save()

        else:
            card_instance.is_private_member = True
            card_instance.save()

        card_state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': card_instance,
                                                                              'chat_request_state': None,
                                                                              'chat_requested_by': None,
                                                                              'chat_request_created_at': None})
        update_dict = {}
        filter_dict = {'card': card_instance}

        if card_state_filter:
            filter_dict['id__in'] = list(card_state_filter.values_list('id', flat=True))
            card_answer_filter = ModelUtilities.get_model_filter(card_answers, {'card': card_instance,
                                                                                'state': conversation_states.ANSWER})

            if card_answer_filter:
                card_answer_instance = card_answer_filter.order_by('created_at')[0]
                update_dict = {
                    'chat_request_state': chat_request_states.ACCEPTED,
                    'chat_requested_by': card_answer_instance.user,
                    'chat_request_created_at': card_answer_instance.created_at
                }

        update_models_for_syncing_apis(SyncTypes.CHATROOM, filter_dict, update_dict)

        count -= 1


def remove_collabcardstate_created_on_join_for_dm():
    card_filter = ModelUtilities.get_model_filter(Collabcard, {'is_private': True,
                                                               'type': card_types.CARD_DIRECT_MESSAGE})

    card_ids_list = list(card_filter.values_list('id', flat=True))

    ModelUtilities.delete_record_in_model(collabcardState, {'card__in': card_ids_list, 'follow_status': False,
                                                            'secret_chatroom_left': False})


print("Starting script")
start_time = time.time()
create_or_update_manager_rights_data()
backfill_manager_moderate_dm_setting_right()
add_members_can_dm_right()
backfill_community_settings_for_direct_messages()
backfill_community_settings_for_direct_messages_setting()
remove_collabcardstate_created_on_join_for_dm()
backfill_is_private_member_value()
print("Completed in", time.time() - start_time)
