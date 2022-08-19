import time

from togther.models import (ModelUtilities, communityQuestions)
from collabmates_api.sdk.models import (SdkClient)
from utility.states import (question_states)
from collabmates_api.rest_api import CommunityQuestionsSerializerV2
from collabmates_api.community.constants import (CREATE_COMMUNITY_QUESTION_ALIAS_TITLE,
                                                 CREATE_COMMUNITY_QUESTION_NAME_HELP_TEXT)


def backfill_alias_question_in_sdk_communities():
    sdk_client_filter = ModelUtilities.get_model_filter(SdkClient, {})

    count = len(sdk_client_filter)

    for sdk_client in sdk_client_filter:
        print('Communities left --->', count)

        community_question_filter = ModelUtilities.get_model_filter(communityQuestions,
                                                                    {'community': sdk_client.community,
                                                                     'question_state': question_states.NAME})

        if not community_question_filter:
            question_data = {
                'community':  sdk_client.community.id,
                'question_title': CREATE_COMMUNITY_QUESTION_ALIAS_TITLE,
                'question_state': question_states.NAME,
                'value': None,
                'optional': False,
                'help_text': CREATE_COMMUNITY_QUESTION_NAME_HELP_TEXT,
                'is_hidden': False,
                'is_compulsory': False,
                'field': False,
                'can_add_options': False,
                'rank': 1
            }

            community_question_serializer = CommunityQuestionsSerializerV2(data=question_data, many=False)

            if community_question_serializer.is_valid():
                community_question_serializer.save()

            else:
                print('CREATE INTRODUCTION QUESTION, Not valid: ', sdk_client.community.id,
                      str(community_question_serializer.errors))

            count -= 1


start = time.time()
print("Starting script")
backfill_alias_question_in_sdk_communities()
print("Script completed in", time.time() - start)
