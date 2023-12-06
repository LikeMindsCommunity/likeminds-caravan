import time

from django.db.models import Q
from collabmates_api.sdk.models import (SdkClient)
from togther.models import (ModelUtilities, Collabcard, card_answers)
from utility.celery_tasks import (post_state_message_in_chatroom)
from collabmates_api.static_text import (CHATROOM_DELETE_DEFAULT_STATE_MESSAGE)
from utility.states import (conversation_states)

COMMUNITY_ID = None


def backfill_state_message_for_deleted_chatrooms():

    if not COMMUNITY_ID:
        community_ids = list(ModelUtilities.get_model_filter(SdkClient, {'is_deleted': False}).values_list(
            'community_id', flat=True))

    else:
        community_ids = [COMMUNITY_ID]

    deleted_card_filter = ModelUtilities.get_model_filter(Collabcard, {'community__in': community_ids}).filter(
        Q(is_deleted=True) | ~Q(deleted_by_user=None))

    for deleted_card_instance in deleted_card_filter:

        if not deleted_card_instance.deleted_by_user_id:
            continue

        card_answer_filter = ModelUtilities.get_model_filter(card_answers,
                                                             {'card': deleted_card_instance,
                                                              'state': conversation_states.CHATROOM_DELETE})

        if card_answer_filter:
            continue

        conv_instance = post_state_message_in_chatroom(user_id=deleted_card_instance.deleted_by_user_id,
                                                       chatroom_id=deleted_card_instance.id,
                                                       conversation_answer=CHATROOM_DELETE_DEFAULT_STATE_MESSAGE,
                                                       conversation_state=conversation_states.CHATROOM_DELETE)

        ModelUtilities.model_update(card_answers,
                                    {'id': conv_instance.id},
                                    {'created_at': deleted_card_instance.updated_at,
                                     'last_updated': deleted_card_instance.updated_at})


start = time.time()
print("Starting the script!")
backfill_state_message_for_deleted_chatrooms()
print(f"Script completed in {time.time() - start}")
