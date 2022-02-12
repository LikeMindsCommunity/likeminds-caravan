import time

from django.conf import settings
from togther.models import ModelUtilities, Community, communityQuestions, communityAnswers, Members
from collabmates_api.rest_api import CommunityQuestionsSerializerV2, CommunityAnswersSerializer
from collabmates_api.community.community_impl import CommunityHelper
from utility.states import question_states
from collabmates_api.community.constants import CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_TITLE, \
    CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_VALUE, CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_HELP_TEXT, \
    CREATE_COMMUNITY_QUESTION_EMAIL_TITLE, CREATE_COMMUNITY_QUESTION_EMAIL_VALUE, \
    CREATE_COMMUNITY_QUESTION_EMAIL_HELP_TEXT, CREATE_COMMUNITY_QUESTION_NAME_TITLE, \
    CREATE_COMMUNITY_QUESTION_NAME_HELP_TEXT
import json

prod_community_ids = [49768]

if not settings.IS_BETA:
    prod_community_ids = [50143, 50015, 50020, 49991, 50030, 50031, 49996, 50023, 50033, 50054, 49899, 49978, 50206,
                          50173, 49813, 49844, 49907, 50073, 49833, 50198, 50211, 50256, 50271, 50275, 50290, 50299,
                          50311, 50329, 50359, 50404, 50400, 50376, 50409]

question_data_list = {
    CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_TITLE: {
        'community': 0,
        'question_title': CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_TITLE,
        'question_state': question_states.MOBILE_NO,
        'value': json.dumps(CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_VALUE),
        'optional': False,
        'help_text': CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_HELP_TEXT,
        'is_hidden': True,
        'is_compulsory': True,
        'field': True
    },
    CREATE_COMMUNITY_QUESTION_EMAIL_TITLE: {
        'community': 0,
        'question_title': CREATE_COMMUNITY_QUESTION_EMAIL_TITLE,
        'question_state': question_states.EMAIL_ID,
        'value': json.dumps(CREATE_COMMUNITY_QUESTION_EMAIL_VALUE),
        'optional': False,
        'help_text': CREATE_COMMUNITY_QUESTION_EMAIL_HELP_TEXT,
        'is_hidden': False,
        'is_compulsory': True,
        'field': True
    },
    CREATE_COMMUNITY_QUESTION_NAME_TITLE: {
        'community': 0,
        'question_title': CREATE_COMMUNITY_QUESTION_NAME_TITLE,
        'question_state': question_states.PARAGRAPH,
        'value': None,
        'optional': False,
        'help_text': CREATE_COMMUNITY_QUESTION_NAME_HELP_TEXT,
        'is_hidden': True,
        'is_compulsory': True,
        'field': True
    }
}


def create_or_update_community_answers_for_community_members(community_instance, question_ids_list=[]):
    members_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance})

    for member_instance in members_filter:
        ModelUtilities.get_model_filter(communityAnswers, {'community': community_instance,
                                                           'question_id__in': question_ids_list,
                                                           'member': member_instance.member_id}).delete()
        CommunityHelper.update_hidden_fields_in_member_responses(member_instance.member_id, community_instance)


def backfill_community_question_v2_for_older_communities():
    communities_filter = ModelUtilities.get_model_filter(Community, {'id__in': prod_community_ids})
    type_id, sub_type_id = CommunityHelper.get_default_community_type_subtype_id()

    for community in communities_filter:
        print("Community ->", community.id)

        # Update type, sub_type of community
        community.type = type_id
        community.sub_type = sub_type_id
        community.save()

        name_question_filter = ModelUtilities.get_model_filter(communityQuestions,
                                                               {'community': community,
                                                                'question_title': "Name",
                                                                'field': True,
                                                                'question_state': question_states.PARAGRAPH})
        name_question_data = question_data_list[CREATE_COMMUNITY_QUESTION_NAME_TITLE].copy()
        name_question_data['community'] = community.id

        if not name_question_filter:
            name_question_instance = CommunityQuestionsSerializerV2(data=name_question_data)

        else:
            name_question_instance = CommunityQuestionsSerializerV2(name_question_filter[0],
                                                                    data=name_question_data,
                                                                    partial=True)

        if name_question_instance.is_valid():
            name_question_instance.save()

        name_question_id = name_question_instance.data.get('id')

        email_question_filter = ModelUtilities.get_model_filter(communityQuestions,
                                                                {'community': community,
                                                                 'question_title__in': ["Email", "Email ID"],
                                                                 'field': True,
                                                                 'question_state': question_states.EMAIL_ID})

        email_question_data = question_data_list[CREATE_COMMUNITY_QUESTION_EMAIL_TITLE].copy()
        email_question_data['community'] = community.id

        if not email_question_filter:
            email_question_instance = CommunityQuestionsSerializerV2(data=email_question_data)

        else:
            email_question_instance = CommunityQuestionsSerializerV2(email_question_filter[0],
                                                                     data=email_question_data,
                                                                     partial=True)

        if email_question_instance.is_valid():
            email_question_instance.save()

        email_question_id = email_question_instance.data.get('id')

        phone_question_filter = ModelUtilities.get_model_filter(communityQuestions,
                                                                {'community': community,
                                                                 'question_title__in': ["Phone Number", "Phone No."],
                                                                 'field': True,
                                                                 'question_state': question_states.MOBILE_NO})

        phone_question_data = question_data_list[CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_TITLE].copy()
        phone_question_data['community'] = community.id

        if not phone_question_filter:
            phone_question_instance = CommunityQuestionsSerializerV2(data=phone_question_data)

        else:
            phone_question_instance = CommunityQuestionsSerializerV2(phone_question_filter[0],
                                                                     data=phone_question_data,
                                                                     partial=True)

        if phone_question_instance.is_valid():
            phone_question_instance.save()

        phone_question_id = phone_question_instance.data.get('id')

        # Update Other questions except Name, Email, Phone Number
        community_questions_filter = ModelUtilities.get_model_filter(communityQuestions, {'community': community}).\
            exclude(id__in=[name_question_id, email_question_id, phone_question_id])
        community_questions_filter.update(field=False, is_hidden=False, is_compulsory=False)

        create_or_update_community_answers_for_community_members(community_instance=community,
                                                                 question_ids_list=[name_question_id,
                                                                                    phone_question_id])


start = time.time()
print("Starting Script")
backfill_community_question_v2_for_older_communities()
print("Ended in", time.time() - start)
