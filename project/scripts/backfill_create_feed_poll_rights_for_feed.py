import time

from collabmates_api.sdk.models import SdkClient

from togther.models import (ModelUtilities, adminRights, memberRights, Members, userAdminRights, userMemberRights,
                            CommunitySettings, communityRightsSettings)

from utility.states import manager_rights, member_rights, member_states, community_setting_types


def create_member_create_feed_poll_rights():

    member_right = ModelUtilities.get_model_filter(
        memberRights, {'state': member_rights.MEMBER_RIGHT_CREATE_FEED_POLL}).first()
    
    if not member_right:
        member_right = memberRights(
            title=member_rights.MEMBER_RIGHT_CREATE_FEED_POLL_TITLE,
            sub_title="If member can create feed poll",
            state=member_rights.MEMBER_RIGHT_CREATE_FEED_POLL
        )
        member_right.save()

        print(f"Created member right: {member_right}")

    return member_right

def create_manager_create_feed_poll_rights():

    manager_right = ModelUtilities.get_model_filter(
        adminRights, {'state': manager_rights.MANAGER_RIGHT_CREATE_FEED_POLL}).first()
    
    if not manager_right:
        manager_right = adminRights(
            title=manager_rights.MANAGER_RIGHT_CREATE_FEED_POLL_TITLE,
            sub_title="If manager can create feed poll",
            state=manager_rights.MANAGER_RIGHT_CREATE_FEED_POLL,
            rank=7)
        manager_right.save()

        print(f"Created manager right: {manager_right}")

    return manager_right

def get_all_sdk_communities_where_feed_is_enabled():

    sdk_client_filter = ModelUtilities.get_model_filter(SdkClient, {'is_deleted': False})

    community_ids = []

    for sdk_client in sdk_client_filter:
        feed_settings = ModelUtilities.get_model_filter(CommunitySettings, 
                                                        {'community': sdk_client.community, 
                                                         'setting_type': community_setting_types.FEED,
                                                         'enabled': True}
                                                         ).first()
        
        if feed_settings:
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
        ModelUtilities.update_or_create_model(communityRightsSettings,
                                                {'community_id': community_id, 'right': member_right},
                                                {'community_id': community_id, 'right': member_right})
        
        count -= 1
        print(f"Added member right to community: {community_id}, count left: {count}")

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

        # fetch all the members with right not already assigned
        members_with_right = ModelUtilities.get_model_filter(userMemberRights, {
            'community_id': community_id,
            'right': member_right
        }).values_list('user', flat=True)

        members_with_no_right = community_members_filter.exclude(member_id__in=members_with_right)

        memberCount = len(members_with_no_right)

        print(f"Total Members left for member right assignment ---> {memberCount}")

        bulk_instances = []

        for member in members_with_no_right:

            # Create userMemberRight Instance
            userMemberRight_instance = userMemberRights(
                community_id=community_id,
                user=member.member_id,
                right=member_right
            )

            bulk_instances.append(userMemberRight_instance)

        ModelUtilities.bulk_create_instances(userMemberRights, bulk_instances)
            
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
    
            # All managers of the community
            community_managers = ModelUtilities.get_model_filter(Members, {
                'community_id': community_id,
                'state': member_states.ADMIN
            })

            # fetch all the managers with right already assigned
            managers_with_right = ModelUtilities.get_model_filter(userAdminRights, {
                'community_id': community_id,
                'right': manager_right
            }).values_list('user', flat=True)

            managers_with_no_right = community_managers.exclude(member_id__in=managers_with_right)

            managerCount = len(managers_with_no_right)

            print(f"Total Managers left for manager right assignment ---> {managerCount}")

            bulk_instance = []

            for manager in managers_with_no_right:

                # Create userAdminRight Instance
                userAdminRight_instance = userAdminRights(
                    community_id=community_id,
                    user=manager.member_id,
                    right=manager_right
                )

                bulk_instance.append(userAdminRight_instance)                

            ModelUtilities.bulk_create_instances(userAdminRights, bulk_instance)

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
