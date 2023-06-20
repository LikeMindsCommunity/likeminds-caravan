import time

from togther.models import (ModelUtilities, questionFilters, communityAnswers, Community)
from utility.states import (question_states)
from collabmates_api.community.community_impl import CommunityHelper
from collabmates_api.cohort.cohort_impl import CohortHelper

community_id = None


def backfill_members_to_cohorts_missed_in_8788():

    if not community_id:
        return

    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

    if not community_instance:
        return

    already_present_user_ids = list(ModelUtilities.get_model_filter(
        questionFilters, {'community': community_id}).values_list('member_id', flat=True))

    filter_dict = {
        'community': community_id,
        'question__question_state__in': [question_states.CHOICE_MULTIPLE, question_states.CHOICE_SINGLE]
    }

    absent_answers_in_question_filters = ModelUtilities.get_model_filter(
        communityAnswers, filter_dict).exclude(member_id__in=already_present_user_ids)

    count = absent_answers_in_question_filters.count()

    for absent_answer in absent_answers_in_question_filters:
        print("Records left", count)
        CommunityHelper.save_user_selected_options_for_member_directory_filter(absent_answer.question,
                                                                               absent_answer.question_answer,
                                                                               absent_answer.member,
                                                                               absent_answer.community)

        CohortHelper.add_member_to_respective_question_based_cohorts(absent_answer.member_id, community_id)

        count -= 1

        time.sleep(1)


start = time.time()
print("Script started!")
backfill_members_to_cohorts_missed_in_8788()
print("Script completed in", time.time() - start)

