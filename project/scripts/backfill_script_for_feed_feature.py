import time
from collabmates_api.sdk.models import SdkClient
from collabmates_api.community.constants import COMMUNITY_SETTING_TYPE_TITLE_MAPPING, \
    COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING
from togther.models import ModelUtilities, adminRights, memberRights, Members, userAdminRights, CommunitySettings
from utility.states import manager_rights, member_rights, member_states, community_setting_types


def create_moderate_feed_admin_right():
    moderate_feed_admin_right = ModelUtilities.get_model_filter(
        adminRights, {'state': manager_rights.MODERATE_FEED_AND_COMMENTS})

    if not moderate_feed_admin_right:
        right = adminRights(
            title=manager_rights.MODERATE_FEED_AND_COMMENTS_TITLE,
            state=manager_rights.MODERATE_FEED_AND_COMMENTS,
            rank=6)
        right.save()
        return right
    return moderate_feed_admin_right[0]


def create_post_create_member_right():
    create_post_member_right = ModelUtilities.get_model_filter(
        memberRights, {'state': member_rights.MEMBER_RIGHT_CREATE_POSTS})

    if not create_post_member_right:
        right = memberRights(
            title=member_rights.MEMBER_RIGHT_CREATE_POSTS_TITLE,
            state=member_rights.MEMBER_RIGHT_CREATE_POSTS
        )
        right.save()
        return right
    return create_post_member_right[0]


def create_comment_create_member_right():
    create_comment_member_right = ModelUtilities.get_model_filter(
        memberRights, {'state': member_rights.MEMBER_RIGHT_COMMENT_AND_REPLY_ON_POSTS})

    if not create_comment_member_right:
        right = memberRights(
            title=member_rights.MEMBER_RIGHT_COMMENT_AND_REPLY_ON_POSTS_TITLE,
            state=member_rights.MEMBER_RIGHT_COMMENT_AND_REPLY_ON_POSTS
        )
        right.save()
        return right
    return create_comment_member_right[0]


def create_member_and_manager_rights_if_not_exist():
    # Create the rights if they don't exist already
    create_moderate_feed_admin_right()
    create_post_create_member_right()
    create_comment_create_member_right()


def give_manager_rights_to_existing_SDK_community_managers(community_ids: list):
    sdk_client_filter = ModelUtilities.get_model_filter(SdkClient, {'community_id__in': community_ids,
                                                                    'is_deleted': False})
    moderate_feed_admin_right = create_moderate_feed_admin_right()
    count = len(sdk_client_filter)

    # give the right to managers of all SDK communities
    for sdk_client in sdk_client_filter:
        print('Communities left for manager right assignment --->', count)

        community_instance = sdk_client.community
        community_admins_filter = ModelUtilities.get_model_filter(Members, {
            'community_id': community_instance,
            'state': member_states.ADMIN
        })

        for admin in community_admins_filter:
            user_instance = admin.member_id
            user_admin_right = ModelUtilities.get_model_filter(
                userAdminRights, {'community': community_instance,
                                  'user': user_instance,
                                  'right__state': manager_rights.MODERATE_FEED_AND_COMMENTS})

            if not user_admin_right:
                right = userAdminRights(
                    community=community_instance,
                    user=user_instance,
                    right=moderate_feed_admin_right
                )
                right.save()

        count -= 1


def give_feed_setting_to_existing_SDK_communities(community_ids: list):
    sdk_client_filter = ModelUtilities.get_model_filter(SdkClient, {'community_id__in': community_ids,
                                                                    'is_deleted': False})
    count = len(sdk_client_filter)

    # give the feed community setting to all SDK communities
    for sdk_client in sdk_client_filter:
        print('Communities left for feed community setting assignment --->', count)

        community_instance = sdk_client.community
        feed_community_setting = ModelUtilities.get_model_filter(
            CommunitySettings, {'community': community_instance, 'setting_type': community_setting_types.FEED})

        if not feed_community_setting:
            community_setting = CommunitySettings(
                community=community_instance,
                setting_type=community_setting_types.FEED,
                setting_title=COMMUNITY_SETTING_TYPE_TITLE_MAPPING[community_setting_types.FEED],
                setting_sub_title=COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING[community_setting_types.FEED],
                enabled=False,
                enabled_by=None
            )
            community_setting.save()

        count -= 1


def backfill_script_for_feed_feature(community_ids: list):
    # create member and manager rights for feed feature
    create_member_and_manager_rights_if_not_exist()

    # give new manager right to all CMs of existing SDK communities
    give_manager_rights_to_existing_SDK_community_managers(community_ids)

    # give feed setting to all existing SDK communities
    give_feed_setting_to_existing_SDK_communities(community_ids)


def main():
    print("Starting script")
    start_time = time.time()
    backfill_script_for_feed_feature()
    print("Completed in", time.time() - start_time, "seconds")


if __name__ == "__main__":
    main()
