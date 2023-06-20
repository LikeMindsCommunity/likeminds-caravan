import time

from togther.models import (ModelUtilities, Members, SDKClientUsersInfo)
from collabmates_api.sdk.models import SdkClient


def backfill_bot_uuid_in_sdkclientsuserinfo():
    sdk_client_filter = ModelUtilities.get_model_filter(SdkClient, {})
    sdk_communities = list(sdk_client_filter.values_list('community_id', flat=True))

    bot_member_instances = ModelUtilities.get_model_filter(Members, {'community_id__in': sdk_communities,
                                                                     'member_id__userinfo__is_bot': True,
                                                                     'is_owner': True})

    bot_uuid_list = []

    count = bot_member_instances.count()

    for bot_member_instance in bot_member_instances:
        print("Bot instances left", count)

        filter_dict = {
            'community': bot_member_instance.community_id,
            'user_unique_id': bot_member_instance.member_id.userinfo.user_unique_id
        }

        if not ModelUtilities.get_model_filter(SDKClientUsersInfo, filter_dict).exists():
            sdk_client_user_info_instance = SDKClientUsersInfo()
            sdk_client_user_info_instance.community = bot_member_instance.community_id
            sdk_client_user_info_instance.user = bot_member_instance.member_id
            sdk_client_user_info_instance.user_unique_id = bot_member_instance.member_id.userinfo.user_unique_id

            bot_uuid_list.append(sdk_client_user_info_instance)

        count -= 1

    if len(bot_uuid_list):
        print("Creating {} records".format(len(bot_uuid_list)))
        ModelUtilities.bulk_create_instances(SDKClientUsersInfo, bot_uuid_list)


start = time.time()
print("Starting script!")
backfill_bot_uuid_in_sdkclientsuserinfo()
print("Script completed in", time.time() - start)
