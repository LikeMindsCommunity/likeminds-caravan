import time

import pandas as pd
from django.conf import settings
from django.contrib.auth.models import User

from collabmates_api.cohort.cohort_impl import CohortImpl
from collabmates_api.static_text import SUBSCRIPTION_EXPIRED_COHORT_NAME
from togther.models import ModelUtilities, Community, Members, Cohort, CohortMember, CohortRights
from utility.states import member_states, cohort_types


def get_json_data_from_csv_file():
    """ function to covert csv data to json """

    # For beta
    if settings.IS_BETA:
        file = r'/home/ec2-user/likeminds/project/scripts/subscription_record.csv'

    # For prod
    else:
        file = r'/home/ec2-user/Togther/project/scripts/subscription_record.csv'

    cols = pd.read_csv(file, nrows=1).columns
    df = pd.read_csv(file, usecols=cols)
    result = df.to_dict(orient='records')
    return result


def delete_existing_subscription_expired_cohort():
    cohort_filter = ModelUtilities.get_model_filter(Cohort, {'type': cohort_types.SUBSCRIPTION_EXPIRED_PLAN})
    cohort_ids = list(cohort_filter.values_list('id', flat=True))
    cohort_member_filter = ModelUtilities.get_model_filter(CohortMember, {'cohort_id__in': cohort_ids})
    cohort_right_filter = ModelUtilities.get_model_filter(CohortRights, {'cohort_id__in': cohort_ids})
    print("Number of existing (type 2) cohorts: ", cohort_filter.count())
    cohort_member_filter.delete()
    cohort_right_filter.delete()
    cohort_filter.delete()


def create_single_subscription_expired_cohort():
    admin_does_not_exist_count = 0
    processed_community_count = 0

    communities = ModelUtilities.get_model_filter(Community, {'is_paid': True})

    for community_instance in communities:

        admins_filter = ModelUtilities.get_model_filter(Members,
                                                        {"community_id": community_instance,
                                                         "is_owner": True})

        if not admins_filter:
            admins_filter = ModelUtilities.get_model_filter(Members,
                                                            {"community_id": community_instance,
                                                             "state": member_states.ADMIN})

            if not admins_filter:
                admin_does_not_exist_count += 1
                print("Admin does not exist for community id : ", community_instance.id)
                continue

        admin_instance = admins_filter[0]
        member_id = admin_instance.member_id_id

        data = {
            'community_id': community_instance.id,
            'name': SUBSCRIPTION_EXPIRED_COHORT_NAME,
            'member_ids': [],
            'type': cohort_types.SUBSCRIPTION_EXPIRED_PLAN,
            'type_id': None
        }

        cohort_manager = CohortImpl(member_id)
        cohort_manager.create_cohort(data)

        processed_community_count += 1

    print("Total paid communities : ", communities.count())
    print("Admin does not exist for communities count : ", admin_does_not_exist_count)
    print("Created for community count : ", processed_community_count)


def backfill_subscription_cohort_members():
    subscription_list = get_json_data_from_csv_file()
    invalid_user = 0
    invalid_community = 0
    invalid_cohort = 0
    processed_for_count = 0

    for subscription in subscription_list:
        user_instance = ModelUtilities.get_model_instance_or_none(User, subscription.get('user_id'))
        community_instance = ModelUtilities.get_model_instance_or_none(Community, subscription.get('community_id'))

        if not user_instance:
            print("Invalid User: ", subscription.get('user_id'))
            invalid_user += 1
            continue

        if not community_instance:
            print("Invalid Community")
            invalid_community += 1
            continue

        if subscription.get('is_removed'):

            filter_dict = {
                'type': cohort_types.SUBSCRIPTION_EXPIRED_PLAN,
                'community_id': subscription.get('community_id')
            }
            cohort_filter = ModelUtilities.get_model_filter(Cohort, filter_dict)

            if not cohort_filter:
                invalid_cohort += 1
                print("Not a valid cohort")

            else:

                cohort_manager = CohortImpl(subscription.get('user_id'))
                cohort_info = {
                    'type': cohort_types.SUBSCRIPTION_EXPIRED_PLAN,
                    'type_id': subscription.get('plan_id'),
                    'community_id': subscription.get('community_id'),
                    'member_ids': [subscription.get('user_id')]
                }
                cohort_manager.update_cohort(cohort_info)
                processed_for_count += 1

    print("Invalid Users : ", invalid_user)
    print("Invalid Community : ", invalid_community)
    print("Invalid Cohort : ", invalid_cohort)
    print("Processed for Cohort : ", processed_for_count)


start_time = time.time()
create_single_subscription_expired_cohort()
backfill_subscription_cohort_members()
end_time = time.time()
time_taken = end_time - start_time

print("Time Taken: ", time_taken)
