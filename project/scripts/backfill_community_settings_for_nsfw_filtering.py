import time

from togther.models import (ModelUtilities, CommunitySettings, Community)

CREATE_NSFW_FILTERING_COMMUNITY_SETTING = {
    'setting_type': 'nsfw_filtering',
    'setting_title': 'NSFW Filtering for Feed',
    'setting_sub_title': 'To enable NSFW filtering for feed posts in the community',
    'enabled': False,
    'enabled_by': None,
}


def backfill_create_NSFW_FILTERING_community_setting():
    communities_with_community_setting = list(ModelUtilities.get_model_filter(
        CommunitySettings, {'setting_type': CREATE_NSFW_FILTERING_COMMUNITY_SETTING.get('setting_type')}).values_list(
        'community_id', flat=True))

    community_filter = ModelUtilities.get_model_filter(Community, {}).exclude(id__in=communities_with_community_setting)

    community_settings_list = []

    for community_instance in community_filter:
        CREATE_NSFW_FILTERING_COMMUNITY_SETTING['community_instance'] = community_instance

        community_settings_instance = CommunitySettings.create_instance(CREATE_NSFW_FILTERING_COMMUNITY_SETTING)
        community_settings_list.append(community_settings_instance)

    ModelUtilities.bulk_create_instances(CommunitySettings, community_settings_list)


start = time.time()
print("Starting script!")
backfill_create_NSFW_FILTERING_community_setting()
print("Script completed in:", time.time() - start)
