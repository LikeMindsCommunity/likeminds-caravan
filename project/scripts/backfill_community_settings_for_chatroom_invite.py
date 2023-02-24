import time

from collabmates_api.community.constants import COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING
from togther.models import ModelUtilities, CommunitySettings
from collabmates_api.sdk.models import (SdkClient)

COMMUNITY_SETTING_TYPE_TITLE_MAPPING = {
    "chatrooms": "Chatrooms",
    "secret_chatrooms_invite": "Send invite for secret chatrooms",
    "post_groups": "Post Groups",
    "secret_groups_invite": "Send invite for secret groups"
}


def create_community_settings_for_sdk_communities():
    sdk_communities = ModelUtilities.get_model_filter(SdkClient, {})

    bulk_create_list = []

    for sdk_client_instance in sdk_communities:
        community_instance = sdk_client_instance.community

        existing_community_settings = ModelUtilities.get_model_filter(CommunitySettings,
                                                                      {"community": community_instance})

        if existing_community_settings:
            existing_community_setting_types = list(existing_community_settings.values_list('setting_type', flat=True))

            new_setting_types = list(set(COMMUNITY_SETTING_TYPE_TITLE_MAPPING.keys()) -
                                     set(existing_community_setting_types))

            for setting_type in new_setting_types:
                community_settings_data = {
                    'community_instance': community_instance,
                    'setting_type': setting_type,
                    'setting_sub_title': COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING.get(setting_type),
                    'setting_title': COMMUNITY_SETTING_TYPE_TITLE_MAPPING.get(setting_type),
                    'enabled': False,
                }

                community_settings_instance = CommunitySettings.create_instance(community_settings_data)
                bulk_create_list.append(community_settings_instance)
            print("Created {} Community settings for community with id: ".format(len(new_setting_types)),
                  community_instance.id)

    ModelUtilities.bulk_create_instances(CommunitySettings, bulk_create_list)


start = time.time()
print("Starting script!")
create_community_settings_for_sdk_communities()
print("Script completed in:", time.time() - start)
