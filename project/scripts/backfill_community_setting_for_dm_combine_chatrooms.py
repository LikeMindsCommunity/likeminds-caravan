import time
from togther.models import (ModelUtilities, CommunitySettings)
from collabmates_api.sdk.models import (SdkClient)
from utility.states import (community_setting_types)
from collabmates_api.community.constants import COMMUNITY_SETTING_TYPE_TITLE_MAPPING, \
    COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING, DM_COMMUNITY_SETTING_SUB_TITLE_WHEN_ENABLED


def backfill_community_settings_for_direct_messages():
    all_sdk_communities_filter = ModelUtilities.get_model_filter(SdkClient, {})
    community_settings_list = []

    setting_type = community_setting_types.DIRECT_MSGS_GROUP_MSGS

    for community_instance in all_sdk_communities_filter:

        community_instance = community_instance.community

        community_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                                   {'setting_type': setting_type,
                                                                    'community': community_instance})
        if community_setting_filter:
            continue

        community_settings_data = {
            'community_instance': community_instance,
            'setting_type': setting_type,
            'setting_title': COMMUNITY_SETTING_TYPE_TITLE_MAPPING.get(setting_type),
            'setting_sub_title': COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING.get(setting_type),
            'enabled': False
        }
        community_settings_instance = CommunitySettings.create_instance(community_settings_data)
        community_settings_list.append(community_settings_instance)

    ModelUtilities.bulk_create_instances(CommunitySettings, community_settings_list)


print("Starting script")
start_time = time.time()
backfill_community_settings_for_direct_messages()
print("Completed in", time.time() - start_time)
