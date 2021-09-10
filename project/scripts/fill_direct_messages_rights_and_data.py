from togther.models import memberRights, Members, Community, ModelUtilities
import time
from utility.celery_tasks import create_member_dm_chatroom
from utility.states import member_states
from collabmates_api.static_text import show_direct_messages_right

show_dm = show_direct_messages_right


def show_dm_right_records():
    print("\n>>>>>>>>>    creating new member rights")

    memberRights.objects.filter(state=show_dm["state"]).delete()

    memberRights(pk=show_dm["id"],
                 title=show_dm["title"],
                 sub_title=show_dm["sub_title"],
                 state=show_dm["state"]).save()


def create_dm_chatrooms_for_existing_records():
    all_community_instances = ModelUtilities.get_model_filter(Community, {})

    communities_count = len(all_community_instances)
    communities_processed = 0

    for community_instance in all_community_instances:
        admins_filter = ModelUtilities.get_model_filter(Members,
                                                        {"community_id": community_instance,
                                                         "state": member_states.ADMIN})

        if not admins_filter.exists():
            continue

        members_filter = ModelUtilities.get_model_filter(Members,
                                                         {"community_id": community_instance,
                                                          "state": member_states.MEMBER})

        if not members_filter.exists():
            continue

        for member_instance in members_filter:
            create_member_dm_chatroom.delay(member_instance.member_id_id, community_instance.id, is_script=True)

            # time.sleep(1)

        communities_processed += 1

        print("Communities LEFT", communities_count - communities_processed)

        time.sleep(5)


start_time = time.time()
print(">>>>>> started >>>>>>>>   ", start_time)

show_dm_right_records()

print("Creating DM chatrooms")
create_dm_chatrooms_for_existing_records()

end_time = time.time()
print(">>>>>> end >>>>>>>>  ", end_time)
diff = end_time - start_time
print(">>>>>> total >>>>>>>>  ", diff)


