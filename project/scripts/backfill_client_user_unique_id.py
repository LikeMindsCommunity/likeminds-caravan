import time

from togther.models import (SDKClientUsersInfo, ModelUtilities, Members, Community)
from collabmates_api.sdk.models import (SdkClient)
from utility.time_utilities import TimeUtilities

COMMUNITY_ID = None


def backfill_client_user_unique_id(community_id: int = None):
    filter_dict = {
        'is_deleted': False
    }

    if community_id:
        filter_dict['community_id'] = community_id

    sdk_communities = ModelUtilities.get_model_filter(SdkClient, filter_dict)
    community_ids_list = list(sdk_communities.values_list('community_id', flat=True))

    members_filter = ModelUtilities.get_model_filter(Members, {'community_id__in': community_ids_list,
                                                               'member_id__userinfo__is_bot': False})

    sdk_client_records = []
    community_members_dict = {}

    for member_instance in members_filter:
        community_members_dict.setdefault(member_instance.community_id_id, set()).add(member_instance.member_id_id)

    count = len(community_members_dict)

    for community_id, members_set in community_members_dict.items():
        print("Communities left to be processed", count)

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            count -= 1
            continue

        sdk_user_ids = set(ModelUtilities.get_model_filter(SDKClientUsersInfo,
                                                           {'user__in': list(members_set),
                                                            'community': community_id}).values_list('user_id',
                                                                                                    flat=True))
        member_ids_left = list(members_set - sdk_user_ids)

        for user_id in member_ids_left:
            user_instance = ModelUtilities.get_user_instance_or_none(user_id)

            if not user_instance:
                continue

            sdk_client_records.append(SDKClientUsersInfo(
                community=community_instance,
                user=user_instance,
                user_unique_id=user_instance.userinfo.user_unique_id,
                created_at=TimeUtilities.current_time_in_milliseconds(),
                updated_at=TimeUtilities.current_time_in_milliseconds()
            ))

        count -= 1

    if sdk_client_records:
        ModelUtilities.bulk_create_instances(SDKClientUsersInfo, sdk_client_records)


start = time.time()
print("Starting script!")
backfill_client_user_unique_id(COMMUNITY_ID)
print("Script completed in", time.time() - start)
