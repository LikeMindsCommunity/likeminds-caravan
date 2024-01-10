import time

from togther.models import (ModelUtilities, CommunitySettings, Community)

# Update this dict to the default community setting you want to backfill
# Refer 'COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING' CONSTANTs in Community Module
DEFAULT_COMMUNITY_SETTINGS_DICT = {
    'setting_type': '',
    'setting_title': '',
    'setting_sub_title': '',
    'enabled': False,
    'enabled_by': None,
}


def backfill_community_settings():

    if not DEFAULT_COMMUNITY_SETTINGS_DICT.get('setting_type'):
        raise Exception('Please update the DEFAULT_COMMUNITY_SETTINGS_DICT dict with the setting_type')
    
    communities_with_community_setting = list(ModelUtilities.get_model_filter(
        CommunitySettings, {'setting_type': DEFAULT_COMMUNITY_SETTINGS_DICT.get('setting_type')}).values_list(
        'community_id', flat=True))

    community_filter = ModelUtilities.get_model_filter(Community, {}).exclude(id__in=communities_with_community_setting)

    community_settings_list = []

    for community_instance in community_filter:
        DEFAULT_COMMUNITY_SETTINGS_DICT['community_instance'] = community_instance

        community_settings_instance = CommunitySettings.create_instance(DEFAULT_COMMUNITY_SETTINGS_DICT)
        community_settings_list.append(community_settings_instance)

    ModelUtilities.bulk_create_instances(CommunitySettings, community_settings_list)


start = time.time()
print("Starting script!")
backfill_community_settings()
print("Script completed in:", time.time() - start)
