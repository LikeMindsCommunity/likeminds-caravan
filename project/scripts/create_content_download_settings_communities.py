from togther.models import (Community, ContentDownloadSettings, ModelUtilities)
from collabmates_api.community.constants import DOWNLOAD_SETTING_TYPE_TITLE_MAPPING


def create_content_download_settings_for_communities():
    get_all_communities = ModelUtilities.get_model_filter(Community, {})

    for community in get_all_communities:

        # Check whether data already present
        get_content_data = ModelUtilities.get_model_filter(ContentDownloadSettings, {"community_id": community})

        if len(get_content_data) == 0:
            for download_setting_type, download_setting_title in DOWNLOAD_SETTING_TYPE_TITLE_MAPPING.items():
                ContentDownloadSettings.create_instance({
                    'community_instance': community,
                    'download_setting_type': download_setting_type,
                    'download_setting_title': download_setting_title,
                    'enabled': True
                })


create_content_download_settings_for_communities()
