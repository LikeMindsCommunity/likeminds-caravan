import uuid

from utility.time_utilities import TimeUtilities

from togther.models import Community
from collabmates_api.resources.models import ResourceSettings

day_of_weekly_email = 0
time_of_weekly_email = 9

def populate_resource_settings():
    community_ids = Community.objects.all().distinct()

    current_time = TimeUtilities.current_time_in_milliseconds()

    objs = [ResourceSettings(
        community_id=community_id,
        day_of_weekly_email=day_of_weekly_email,
        time_of_weekly_email=time_of_weekly_email,
        created_at=current_time,
        updated_at=current_time
        ) for community_id in community_ids]

    ResourceSettings.objects.bulk_create(objs)

start_time = TimeUtilities.get_current_datetime_in_IST()

chatroom_instances_count = populate_resource_settings()

end_time = TimeUtilities.get_current_datetime_in_IST()

time_taken = end_time-start_time

print('script for populating resource settings schema ran successfully')
print('time taken = %s' % str(time_taken))
