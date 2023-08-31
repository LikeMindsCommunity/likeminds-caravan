import time

from togther.models import (ModelUtilities, communityQuestions, questionFilters, communityAnswers, Community)
from collabmates_api.community.community_impl import CommunityHelper

COMMUNITY_ID = None
USER_ID = None

REPLACE_QUESTION_OPTIONS = {
    '50020': {
        'Moderation': 'Community Moderation',
        'Events': 'Event Planning and Management',
        'Strategy': 'Community Strategy',
        'Data Analytics': 'Data Analysis',
        'Training and Development': 'Education and Training',
        'Engagement': 'Community Engagement'
    }
}

CREATE_OR_UPDATE_QUESTIONS_LIST = []


def replace_options_of_questions():
    print('Replacing question options')

    for question_id, replace_dict in REPLACE_QUESTION_OPTIONS.items():
        question_instance = ModelUtilities.get_model_filter(communityQuestions, {'community_id': COMMUNITY_ID,
                                                                                 'id': question_id}).first()

        if not question_instance:
            continue

        for old_val, new_val in replace_dict.items():
            print(f'Replacing {old_val} with {new_val}')
            filter_dict = {
                'question': question_instance,
                'community': COMMUNITY_ID,
                'question_answer__contains': old_val
            }

            answers_filter = ModelUtilities.get_model_filter(communityAnswers, filter_dict)

            for answer_instance in answers_filter:
                old_answer = answer_instance.question_answer
                new_answer = old_answer.replace(old_val, new_val)
                answer_instance.question_answer = new_answer
                answer_instance.save()

            filter_dict = {
                'question': question_instance,
                'community': COMMUNITY_ID,
                'filter__contains': old_val
            }

            question_filters = ModelUtilities.get_model_filter(questionFilters, filter_dict)

            for question_filter in question_filters:
                old_answer = question_filter.filter
                new_answer = old_answer.replace(old_val, new_val)
                question_filter.filter = new_answer
                question_filter.save()


def create_or_update_questions():
    new_questions_list = []

    community_instance = ModelUtilities.get_model_instance_or_none(Community, COMMUNITY_ID)

    if not community_instance:
        return

    print('Creating or updating questions!')

    for question_dict in CREATE_OR_UPDATE_QUESTIONS_LIST:

        if not question_dict.get('id'):
            new_questions_list.append(question_dict)

        print(f"Updating question having question id {question_dict.get('id')}!")

        question_filter = ModelUtilities.get_model_filter(communityQuestions, {'id': question_dict.get('id')})

        if not question_filter:
            print(f"No question found corresponding to {question_dict.get('id')}!")
            continue

        del question_dict['id']

        question_filter.update(**question_dict)

    # Create new questions
    CommunityHelper.create_new_community_questions(community_instance, new_questions_list, USER_ID)


start = time.time()
print('Starting the script!')
create_or_update_questions()
replace_options_of_questions()
print('Script completed in', time.time() - start)
