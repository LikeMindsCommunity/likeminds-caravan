from django.conf import settings
from collabmates_api.views import update_hidden_fields_in_questions
from utility.states import question_states
from collabmates_api.community.constants import CREATE_COMMUNITY_QUESTION_INTRODUCTION_TITLE, \
    CREATE_COMMUNITY_QUESTION_INTRODUCTION_VALUE, CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_TITLE, \
    CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_VALUE, CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_HELP_TEXT, \
    CREATE_COMMUNITY_QUESTION_EMAIL_TITLE, CREATE_COMMUNITY_QUESTION_EMAIL_VALUE, \
    CREATE_COMMUNITY_QUESTION_EMAIL_HELP_TEXT, CREATE_COMMUNITY_QUESTION_NAME_TITLE, \
    CREATE_COMMUNITY_QUESTION_NAME_HELP_TEXT
import json

prod_community_ids = []

if not settings.IS_BETA:
    prod_community_ids = [50143, 50015, 50020, 49991, 50030, 50031, 49996, 50023, 50033, 50054, 49899, 49978, 50206,
                          50173, 49813, 49844, 49907, 50073, 49833, 50198, 50211, 50256, 50271, 50275, 50290, 50299,
                          50311, 50329, 50359, 50404, 50400, 50376, 50409]

question_data_list = [
    {
        CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_TITLE: {
            'community': 0,
            'question_title': CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_TITLE,
            'question_state': question_states.MOBILE_NO,
            'value': json.dumps(CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_VALUE),
            'optional': False,
            'help_text': CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_HELP_TEXT,
            'is_hidden': True,
            'is_compulsory': True
        }
    },
    {
        CREATE_COMMUNITY_QUESTION_EMAIL_TITLE: {
            'community': 0,
            'question_title': CREATE_COMMUNITY_QUESTION_EMAIL_TITLE,
            'question_state': question_states.EMAIL_ID,
            'value': json.dumps(CREATE_COMMUNITY_QUESTION_EMAIL_VALUE),
            'optional': False,
            'help_text': CREATE_COMMUNITY_QUESTION_EMAIL_HELP_TEXT,
            'is_hidden': False,
            'is_compulsory': True
        }
    },
    {
        CREATE_COMMUNITY_QUESTION_NAME_TITLE: {
            'community': 0,
            'question_title': CREATE_COMMUNITY_QUESTION_NAME_TITLE,
            'question_state': question_states.PARAGRAPH,
            'value': None,
            'optional': False,
            'help_text': CREATE_COMMUNITY_QUESTION_NAME_HELP_TEXT,
            'is_hidden': True,
            'is_compulsory': True,
        }
    }
]


