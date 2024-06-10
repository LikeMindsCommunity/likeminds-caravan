import time

from collabmates_api.sdk.models import SdkClient

from togther.models import (ModelUtilities, adminRights, memberRights, Members, userAdminRights, userMemberRights,
                            CommunitySettings, communityRightsSettings)

from utility.states import manager_rights, member_rights, member_states, community_setting_types


def create_member_create_feed_poll_rights():

    member_right = ModelUtilities.get_model_filter(
        memberRights, {'state': member_rights.MEMBER_RIGHT_CREATE_FEED_POLL})
    
    if not member_right:
        right = memberRights(
            title=member_rights.MEMBER_RIGHT_CREATE_FEED_POLL_TITLE,
            sub_title="If member can create feed poll",
            state=member_rights.MEMBER_RIGHT_CREATE_FEED_POLL
        )
        right.save()

        print(f"Created member right: {right}")

    return right

def create_manager_create_feed_poll_rights():

    manager_right = ModelUtilities.get_model_filter(
        adminRights, {'state': manager_rights.MANAGER_RIGHT_CREATE_FEED_POLL})
    
    if not manager_right:
        right = adminRights(
            title=manager_rights.MANAGER_RIGHT_CREATE_FEED_POLL_TITLE,
            sub_title="If manager can create feed poll",
            state=manager_rights.MANAGER_RIGHT_CREATE_FEED_POLL,
            rank=7)
        right.save()

        print(f"Created manager right: {right}")

    return right

def get_all_sdk_communities_where_feed_is_enabled():

    sdk_client_filter = ModelUtilities.get_model_filter(SdkClient, {'is_deleted': False})

    community_ids = []

    for sdk_client in sdk_client_filter:
        feed_settings = ModelUtilities.get_model_filter(CommunitySettings, 
                                                        {'community': sdk_client.community, 
                                                         'setting_type': community_setting_types.FEED})
        
        if feed_settings and feed_settings.enabled:
            community_ids.append(sdk_client.community_id)

    print(f"Communities where feed is enabled: {community_ids}")

    return community_ids

def add_create_feed_poll_right_to_community_right_settings(community_ids):

    member_right = create_member_create_feed_poll_rights()
    if not member_right:
        print("Error creating member right")
        return
    
    count = len(community_ids)

    for community_id in community_ids:

        print(f"Communities left for member right assignment ---> {count}")

        ModelUtilities.update_or_create_model(communityRightsSettings,
                                                {'community_id': community_id, 'right': member_right},
                                                {'community_id': community_id, 'right': member_right})
        
        print(f"Added member right to community: {community_id}")
        count -= 1

    print("Added create_feed_poll right to communityRightSettingsm for all communities")

def add_create_feed_poll_right_for_each_member(community_ids):

    member_right = create_member_create_feed_poll_rights()
    if not member_right:
        print("Error creating manager right")
        return

    communityCount = len(community_ids)

    for community_id in community_ids:

        print(f"Communities left for member & manager right assignment ---> {communityCount}")

        # Add member right to all members
        community_members_filter = ModelUtilities.get_model_filter(Members, {
            'community_id': community_id,
            'state': member_states.MEMBER
        })

        memberCount = len(community_members_filter)

        for member in community_members_filter:

            print(f"Members left for member right assignment ---> {memberCount}")
            user_instance = member.member_id

            # Add member right
            ModelUtilities.update_or_create_model(userMemberRights,
                                                {'community_id': community_id, 'user_id': user_instance, 'right': member_right},
                                                {'community_id': community_id, 'user_id': user_instance, 'right': member_right})
            
            memberCount -= 1
            
        communityCount -= 1

    print("Added member right to all members for all comunities")

def add_create_feed_poll_right_for_each_manager(community_ids):
    
        manager_right = create_manager_create_feed_poll_rights()
        if not manager_right:
            print("Error creating manager right")
            return
    
        communityCount = len(community_ids)
    
        for community_id in community_ids:
    
            print(f"Communities left for manager right assignment ---> {communityCount}")
    
            # Add manager right to all managers
            community_managers = ModelUtilities.get_model_filter(Members, {
                'community_id': community_id,
                'state': member_states.ADMIN
            })

            managerCount = len(community_managers)

            for manager in community_managers:
    
                print(f"managers left for manager right assignment ---> {managerCount}")
                user_instance = manager.member_id
    
                # Add manager right
                ModelUtilities.update_or_create_model(userAdminRights,
                                                    {'community_id': community_id, 'user_id': user_instance, 'right': manager_right},
                                                    {'community_id': community_id, 'user_id': user_instance, 'right': manager_right})
                
                managerCount -= 1

            communityCount -= 1

        print("Added manager right to all managers for all comunities")


def run():

    start_time = time.time()

    print("Starting backfill script for create_feed_poll rights for feed feature")

    print("___________________Starting 'create member and manager rights if they don't exist already'____________________")

    # Create the rights if they don't exist already
    create_member_create_feed_poll_rights()
    create_manager_create_feed_poll_rights() 

    print("___________________Starting 'get all SDK communities where feed is enabled'____________________")

    # Get all the SDK clients that are not deleted
    community_ids = get_all_sdk_communities_where_feed_is_enabled()

    print("___________________Starting 'add create_feed_poll right to communityRightSettings'____________________")

    # for each community where feed is enabled, add create_feed_poll right to communityRightSettings
    add_create_feed_poll_right_to_community_right_settings(community_ids)

    print("___________________Starting 'add create_feed_poll right for each member and manager'____________________")

    # for each community give member & manager rights
    add_create_feed_poll_right_for_each_member(community_ids)
    add_create_feed_poll_right_for_each_manager(community_ids)

    print(f"Time taken: {time.time() - start_time} seconds")
