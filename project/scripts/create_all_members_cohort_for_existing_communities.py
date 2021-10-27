import time

from collabmates_api.cohort.cohort_impl import CohortImpl
from collabmates_api.static_text import ALL_MEMBER_COHORT_TEXT
from togther.models import ModelUtilities, Community, Members, Cohort
from utility.states import member_states, cohort_types


def create_all_members_cohort_for_existing_communities():

    admin_does_not_exist_count = 0
    already_created_count = 0
    processed_community_count = 0
    communities = ModelUtilities.get_model_filter(Community, {})

    states_list = [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]

    for community_instance in communities:

        cohort_filter = ModelUtilities.get_model_filter(Cohort, {'community': community_instance,
                                                                 'type': cohort_types.ALL_MEMBER})

        if cohort_filter:
            already_created_count += 1
            print("ALL_MEMBER_GROUP Already exists for community id : ", community_instance.id)
            continue

        admins_filter = ModelUtilities.get_model_filter(Members,
                                                        {"community_id": community_instance,
                                                         "state": member_states.ADMIN})

        if not admins_filter:
            admin_does_not_exist_count += 1
            print("Admin does not exist for community id : ", community_instance.id)
            continue

        admin_instance = admins_filter[0]
        member_id = admin_instance.member_id_id

        filter_dict = {
            "community_id": community_instance,
            "state__in": states_list
        }

        member_list = list(ModelUtilities.get_model_filter(Members, filter_dict).values_list('member_id', flat=True))

        data = {
            'community_id': community_instance.id,
            'name': ALL_MEMBER_COHORT_TEXT,
            'member_ids': member_list,
            'type': cohort_types.ALL_MEMBER,
            'type_id': None
        }

        cohort_manager = CohortImpl(member_id)
        cohort_manager.create_cohort(data)

        print("Created for community with ID: ", community_instance.id)

        processed_community_count += 1

    print("Total communities : ", communities.count())
    print("Admin does not exist for communities count : ", admin_does_not_exist_count)
    print("Already created all member cohort count : ", already_created_count)
    print("Created for community count : ", processed_community_count)


start_time = time.time()
create_all_members_cohort_for_existing_communities()
end_time = time.time()
time_taken = end_time - start_time

print("Time Taken: ", time_taken)
