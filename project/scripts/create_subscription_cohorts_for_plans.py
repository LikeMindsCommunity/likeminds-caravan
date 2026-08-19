import time

import pandas as pd
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q

from collabmates_api.cohort.cohort_impl import CohortImpl
from collabmates_api.static_text import SUBSCRIPTION_PLAN_NAMES, SUBSCRIPTION_COHORT_NAME
from togther.models import ModelUtilities, Cohort, Community, Members, CohortMember, CohortRights, ChatroomCohort, \
    CohortFilter
from utility.states import cohort_types, member_states

"""
Query Used for this file:
SELECT *
FROM   subscription_subscriptionplan WHERE is_deleted=false
"""


def get_json_data_from_plan_data_file():
    """ function to covert csv data to json """

    # For beta
    if settings.IS_BETA:
        file = r'/home/ec2-user/likeminds/project/scripts/plan_data.csv'

    # For prod
    else:
        file = r'/home/ec2-user/likeminds-caravan/project/scripts/plan_data.csv'

    cols = pd.read_csv(file, nrows=1).columns
    df = pd.read_csv(file, usecols=cols)
    result = df.to_dict(orient='records')
    return result


"""
Query Used for this file:
SELECT *
FROM   subscription_subscription
WHERE  plan_id IN (SELECT plan_id
                   FROM   subscription_subscriptionplan WHERE is_deleted=false)
       AND user_id IS NOT NULL;
"""


def get_json_data_from_subscription_record_file():
    """ function to covert csv data to json """

    # For beta
    if settings.IS_BETA:
        file = r'/home/ec2-user/likeminds/project/scripts/subscription_record.csv'

    # For prod
    else:
        file = r'/home/ec2-user/likeminds-caravan/project/scripts/subscription_record.csv'

    cols = pd.read_csv(file, nrows=1).columns
    df = pd.read_csv(file, usecols=cols)
    result = df.to_dict(orient='records')
    return result


def delete_incorrect_subscription_cohort():
    card_cohort_filter, filtered_cohort_ids = check_for_filter_or_chatroom_dependency()

    filter_dict = {
        'type__in': [cohort_types.NORMAL, cohort_types.SUBSCRIPTION_PLAN, cohort_types.SUBSCRIPTION_EXPIRED_PLAN],
        'name__startswith': 'Subscription'
    }

    cohort_filter = ModelUtilities.get_model_filter(Cohort, filter_dict).filter(
        ~Q(id__in=card_cohort_filter) & ~Q(id__in=filtered_cohort_ids))
    delete_cohort(cohort_filter)
    return


def check_for_filter_or_chatroom_dependency():
    card_cohort_filter = list(ModelUtilities.get_model_filter(ChatroomCohort, {}).values_list('cohort_id', flat=True))
    filtered_cohort_ids = list(ModelUtilities.get_model_filter(CohortFilter, {}).values_list('cohort_id', flat=True))
    print("Excluding following Cohort IDs as these cohorts are added to some chatroom", card_cohort_filter)
    print("Excluding following Cohort IDs as these cohorts have some filters", filtered_cohort_ids)
    return card_cohort_filter, filtered_cohort_ids


def delete_cohort(cohort_filter):
    cohort_ids = list(cohort_filter.values_list('id', flat=True))
    cohort_member_filter = ModelUtilities.get_model_filter(CohortMember, {'cohort_id__in': cohort_ids})
    cohort_right_filter = ModelUtilities.get_model_filter(CohortRights, {'cohort_id__in': cohort_ids})
    print("Number of deleted cohorts: ", cohort_filter.count())
    cohort_member_filter.delete()
    cohort_right_filter.delete()
    cohort_filter.delete()


def create_subscription_cohorts_for_plans():
    invalid_community_id = 0
    admin_does_not_exist_count = 0
    cohort_already_exists = 0
    processed_cohorts = 0
    subscription_plan_list = get_json_data_from_plan_data_file()

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

    print("invalid community id: ", invalid_community_id)
    print("admin does not exist count: ", admin_does_not_exist_count)
    print("cohort already exists: ", cohort_already_exists)
    print("processed cohorts: ", processed_cohorts)


def populate_subscription_cohort_members():
    subscription_list = get_json_data_from_subscription_record_file()
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
                print("Cohort doesn't exist")
                print(f"plan_id: {subscription.get('plan_id')}, community_id: {subscription.get('community_id')}")

            else:
                cohort_manager = CohortImpl(subscription.get('user_id'))
                cohort_info = {
                    'type': cohort_types.SUBSCRIPTION_PLAN,
                    'type_id': subscription.get('plan_id'),
                    'community_id': subscription.get('community_id'),
                    'member_ids': [int(subscription.get('user_id'))]
                }
                cohort_manager.update_cohort(cohort_info)
                processed_for_count += 1

    print("Invalid Users : ", invalid_user)
    print("Invalid Community : ", invalid_community)
    print("Invalid Cohort : ", invalid_cohort)
    print("Processed for Cohort : ", processed_for_count)


start_time = time.time()
delete_incorrect_subscription_cohort()
create_subscription_cohorts_for_plans()
populate_subscription_cohort_members()
end_time = time.time()
time_taken = end_time - start_time
