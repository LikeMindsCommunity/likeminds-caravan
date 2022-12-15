import time

from togther.models import (ModelUtilities, communityAnswers, questionFilters)
from cms.models import (NewAnswer)
from django.conf import settings


if settings.IS_BETA:
    community_id = 50429

else:
    community_id = 0


def remove_community_answers_for_all_members():
    filter_dict = {
        'community_id': community_id
    }

    ModelUtilities.delete_record_in_model(communityAnswers, filter_dict)
    ModelUtilities.delete_record_in_model(questionFilters, filter_dict)
    ModelUtilities.delete_record_in_model(NewAnswer, filter_dict)


start = time.time()
print("Starting script!")
remove_community_answers_for_all_members()
print("Completing script in ->", time.time() - start)
