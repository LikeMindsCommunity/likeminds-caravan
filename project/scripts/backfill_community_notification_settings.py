import time

from togther.models import (Community, CommunityNotificationSettings, ModelUtilities)
from collabmates_api.community.community_impl import CommunityHelper


def backfill_community_notification_settings():
    all_communities = ModelUtilities.get_model_filter(Community, {})

    count = len(all_communities)

    for community_instance in all_communities:
        print('Communities left:', count)
        community_notification_filter = ModelUtilities.get_model_filter(CommunityNotificationSettings,
                                                                        {'community': community_instance})

        if not community_notification_filter:
            CommunityHelper.create_community_noti_settings_instance_on_community_creation.delay(community_instance.id)

        count -= 1


start = time.time()
print('Starting script!')
backfill_community_notification_settings()
print('Script completed in', time.time() - start)
