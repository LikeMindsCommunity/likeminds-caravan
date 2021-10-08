from collabmates_api.community.constants import COMMUNITY_SETTING_TYPE_TITLE_MAPPING, \
    COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING
from togther.models import ModelUtilities, Community, CommunitySettings


def create_community_settings_for_communities():
    communities = ModelUtilities.get_model_filter(Community, {})

    bulk_create_list = []

    for community in communities:
        existing_community_settings = ModelUtilities.get_model_filter(CommunitySettings, {"community_id": community})

        if not existing_community_settings:

            for setting_type, setting_title in COMMUNITY_SETTING_TYPE_TITLE_MAPPING.items():

                community_settings_data = {
                    'community_instance': community,
                    'setting_type': setting_type,
                    'setting_sub_title': COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING.get(setting_type),
                    'setting_title': setting_title,
                    'enabled': True,
                }

                community_settings_instance = CommunitySettings.create_instance(community_settings_data)
                bulk_create_list.append(community_settings_instance)
                print("Community settings for community with id: ", community.id)

    ModelUtilities.bulk_create_instances(bulk_create_list)


create_community_settings_for_communities()
