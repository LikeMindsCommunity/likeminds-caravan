import time

import pandas as pd
from django.conf import settings

from collabmates_api.cohort.cohort_impl import CohortImpl
from collabmates_api.static_text import SUBSCRIPTION_EXPIRED_COHORT_NAME, SUBSCRIPTION_PLAN_NAMES, \
    SUBSCRIPTION_COHORT_NAME
from togther.models import ModelUtilities, Cohort, Community, Members
from utility.states import cohort_types, member_states


def get_json_data_from_csv_file():
    """ function to covert csv data to json """

    # For beta
    if settings.IS_BETA:
        file = r'/home/ec2-user/likeminds/project/scripts/plan_data.csv'

    # For prod
    else:
        file = r'/home/ec2-user/Togther/project/scripts/plan_data.csv'

    cols = pd.read_csv(file, nrows=1).columns
    df = pd.read_csv(file, usecols=cols)
    result = df.to_dict(orient='records')
    return result


def create_subscription_cohorts_for_plans():
    invalid_community_id = 0
    admin_does_not_exist_count = 0
    cohort_already_exists = 0
    processed_cohorts = 0
    subscription_plan_list = get_json_data_from_csv_file()

    for subscription in subscription_plan_list:

        filter_dict = {
            'type': cohort_types.SUBSCRIPTION_PLAN,
            'type_id': subscription.get('plan_id'),
            'community_id': subscription.get('community_id')
        }

        cohort_filter = ModelUtilities.get_model_filter(Cohort, filter_dict)

        community_instance = None

        if subscription.get('community_id'):
            community_instance = ModelUtilities.get_model_instance_or_none(Community, subscription.get('community_id'))

        if not community_instance:
            print("Invalid Community ID: ", subscription.get("community_id"))
            invalid_community_id += 1
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

        if SUBSCRIPTION_PLAN_NAMES[subscription['duration_name']]['unique']:
            plan_title = SUBSCRIPTION_PLAN_NAMES[subscription['duration_name']]['title']

        else:
            plan_title = '{} "{}" Plan'.format(subscription['duration_in_months'],
                                               SUBSCRIPTION_PLAN_NAMES[subscription['duration_name']]['title'])

        cohort_manager = CohortImpl(member_id)

        if cohort_filter:
            print("subscription cohort already exists type_id: ", subscription.get('plan_id'))
            cohort_already_exists += 1

        else:
            cohort_subscription_info = {
                'name': SUBSCRIPTION_COHORT_NAME.format(plan_title),
                'type': cohort_types.SUBSCRIPTION_PLAN,
                'type_id': subscription.get('plan_id'),
                'community_id': subscription.get('community_id'),
                'member_ids': []
            }

            cohort_manager.create_cohort(cohort_subscription_info)
            processed_cohorts += 1

        filter_dict = {
            'type': cohort_types.SUBSCRIPTION_EXPIRED_PLAN,
            'type_id': subscription.get('plan_id'),
            'community_id': subscription.get('community_id')
        }

        cohort_filter = ModelUtilities.get_model_filter(Cohort, filter_dict)

        if cohort_filter:
            print("subscription expired cohort already exists type_id: ", subscription.get('plan_id'))
            cohort_already_exists += 1

        else:
            cohort_subscription_expired_info = {
                'name': SUBSCRIPTION_EXPIRED_COHORT_NAME.format(plan_title),
                'type': cohort_types.SUBSCRIPTION_EXPIRED_PLAN,
                'type_id': subscription.get('plan_id'),
                'community_id': subscription.get('community_id'),
                'member_ids': []
            }
            cohort_manager.create_cohort(cohort_subscription_expired_info)
            processed_cohorts += 1

    print("invalid community id: ", invalid_community_id)
    print("admin does not exist count: ", admin_does_not_exist_count)
    print("cohort already exists: ", cohort_already_exists)
    print("processed cohorts: ", processed_cohorts)


start_time = time.time()
create_subscription_cohorts_for_plans()
end_time = time.time()
time_taken = end_time - start_time
