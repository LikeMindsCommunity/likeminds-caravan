import time
import pandas as pd
from django.conf import settings
from django.contrib.auth.models import User
from collabmates_api.cohort.cohort_impl import CohortImpl
from togther.models import ModelUtilities, Community, Cohort
from utility.states import cohort_types

"""
Query Used: 

SELECT *
FROM   subscription_subscription
WHERE  plan_id IN (SELECT plan_id
                   FROM   subscription_subscriptionplan)
       AND user_id IS NOT NULL;
"""


def get_json_data_from_csv_file():
    """ function to covert csv data to json """

    # For beta
    if settings.IS_BETA:
        file = r'/home/ec2-user/likeminds/project/scripts/data_to_backfill.csv'

    # For prod
    else:
        file = r'/home/ec2-user/likeminds-caravan/project/scripts/data_to_backfill.csv'

    cols = pd.read_csv(file, nrows=1).columns
    df = pd.read_csv(file, usecols=cols)
    result = df.to_dict(orient='records')
    return result


def backfill_subscription_plan():
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

        if not subscription.get('is_removed'):

            filter_dict = {
                'type': cohort_types.SUBSCRIPTION_PLAN,
                'type_id': subscription.get('plan_id'),
                'community_id': subscription.get('community_id')
            }

            cohort_filter = ModelUtilities.get_model_filter(Cohort, filter_dict)

            if not cohort_filter:
                invalid_cohort += 1
                print("Not a valid cohort")

            else:

                cohort_manager = CohortImpl(subscription.get('user_id'))
                cohort_info = {
                    'type': cohort_types.SUBSCRIPTION_PLAN,
                    'type_id': subscription.get('plan_id'),
                    'community_id': subscription.get('community_id'),
                    'member_ids': [subscription.get('user_id')]
                }
                cohort_manager.update_cohort(cohort_info)
                processed_for_count += 1

        else:

            filter_dict = {
                'type': cohort_types.SUBSCRIPTION_EXPIRED_PLAN,
                'type_id': subscription.get('plan_id'),
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
backfill_subscription_plan()
end_time = time.time()
time_taken = end_time - start_time

print(time_taken)
