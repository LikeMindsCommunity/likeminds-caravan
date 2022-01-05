import time

from collabmates_api.static_text import ALL_MEMBER_COHORT_TEXT
from togther.models import ModelUtilities, Cohort
from utility.states import cohort_types
from utility.time_utilities import TimeUtilities


def update_all_member_group_type():
    """
    Updates type of All Member groups from 0 to 3
    @return: None
    """
    current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

    filter_dict = {'type': cohort_types.NORMAL, 'name': ALL_MEMBER_COHORT_TEXT}
    update_dict = {'updated_at': current_time_in_ms, 'type': cohort_types.ALL_MEMBER}

    cohort_filter = ModelUtilities.get_model_filter(model=Cohort, filter_dict=filter_dict)
    ModelUtilities.model_update(model=Cohort, filter_dict=filter_dict, update_dict=update_dict)

    updated_cohort_ids = cohort_filter.values_list('id', flat=True)

    print(f'Updated All Member Group Count: {cohort_filter.count()}')
    print(f'Cohort IDs: {updated_cohort_ids}')


start_time = time.time()
update_all_member_group_type()
end_time = time.time()
time_taken = end_time - start_time

print("Time Taken: ", time_taken)
