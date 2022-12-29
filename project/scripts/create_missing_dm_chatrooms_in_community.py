import time

from django.conf import settings
from togther.models import (ModelUtilities, Members)
from utility.states import (member_states)
from utility.celery_tasks import (create_member_dm_chatroom)


if settings.IS_BETA:
    community_id = 50430

else:
    community_id = 0


def create_missing_dm_chatrooms_in_community():
    admins_filter = ModelUtilities.get_model_filter(Members,
                                                    {"community_id": community_id,
                                                     "state": member_states.ADMIN})

    if not admins_filter.exists():
        return

    members_filter = ModelUtilities.get_model_filter(Members,
                                                     {"community_id": community_id,
                                                      "state": member_states.MEMBER})

    if not members_filter.exists():
        return

    total_users_count = members_filter.count()

    for member_instance in members_filter:
        print("User left ->", total_users_count)

        create_member_dm_chatroom(member_instance.member_id_id, community_id, is_script=True)

        total_users_count -= 1


start = time.time()
print("Starting script!")
create_missing_dm_chatrooms_in_community()
print("Script completed in ->", time.time() - start)
