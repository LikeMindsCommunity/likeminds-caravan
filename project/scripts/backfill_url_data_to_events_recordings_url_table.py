from django.db.models import Q

from togther.models import Collabcard, EventRecordingsURL
from utility.time_utilities import TimeUtilities


def backfill_data():
    chatroom_instances = Collabcard.objects.filter(
        Q(about_recording__isnull=False) |
        Q(recording_url_og_tags__isnull=False)
    )

    for chatroom in chatroom_instances:
        try:
            instance, created = EventRecordingsURL.objects.update_or_create(
                chatroom_id=chatroom,
                defaults={
                    'recording_url_og_tags': chatroom.recording_url_og_tags,
                    'about_recording': chatroom.about_recording
                }
            )

            print('successfully created EventRecordingsURL for chatroom_id = %s' % chatroom.id)

        except Exception as e:
            print('Got error while creating EventRecordingsURL instance for chatroom_id = %s' % chatroom.id)
            print('Exception occurred = %s' % str(e))

    return chatroom_instances.count()


start_time = TimeUtilities.get_current_datetime_in_IST()

chatroom_instances_count = backfill_data()

end_time = TimeUtilities.get_current_datetime_in_IST()

time_taken = end_time-start_time

print('script for backfilling data ran successfully for %s chatroom_instances' % str(chatroom_instances_count))
print('time taken = %s' % str(time_taken))
