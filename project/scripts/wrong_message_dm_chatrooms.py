import time

from django.conf import settings
from togther.models import (ModelUtilities, collabcardState, card_answers, User)
from utility.states import conversation_states, SyncTypes
from collabmates_api.static_text import MEMBER_BECOMES_CM_DM_CHATROOM_MESSAGE
from collabmates_api.sync.model_update import update_models_for_syncing_apis

answer_state = conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_ENABLE_CHAT

if settings.IS_BETA:
    user_id = 1405
    community_id = 50195
    start_time = 1651237887464
    end_time = 1651294723564

else:
    user_id = 26772
    community_id = 50376
    start_time = 1651225805021
    end_time = 1651226003892

user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)


def correct_message_in_dm_chatrooms():
    card_answer_filter = ModelUtilities.get_model_filter(card_answers, {"community_id": community_id,
                                                                        "user_id": user_id,
                                                                        "state": answer_state,
                                                                        "created_at__lte": end_time,
                                                                        "created_at__gte": start_time})

    user_route = "<<" + str(user_instance.userinfo.name) + "|route://member/" + str(user_instance.id) + ">>"
    message = MEMBER_BECOMES_CM_DM_CHATROOM_MESSAGE
    message = message.format(user_route)

    for card_answer_instance in card_answer_filter:
        print("Updating answer instance having ID", card_answer_instance.id)
        card_answer_instance.answer = message
        card_answer_instance.save()

        update_models_for_syncing_apis(SyncTypes.CHATROOM, {"card": card_answer_instance.card}, {})


start = time.time()
correct_message_in_dm_chatrooms()
print("Script ran successfully in", time.time() - start)
