import time

from togther.models import (ModelUtilities, Collabcard, card_answers)
from utility.states import conversation_states


def script_for_updating_updated_at_of_collabcard():
    non_deleted_cards = ModelUtilities.get_model_filter(Collabcard, {'is_deleted': False})

    included_conversation_state_list = [conversation_states.ANSWER, conversation_states.CONVERSATION_POLL]

    count = non_deleted_cards.count()

    for card_instance in non_deleted_cards:
        print('Chatroom left:', count)
        last_answer = ModelUtilities.get_model_filter(card_answers,
                                                      {'card': card_instance,
                                                       'state__in': included_conversation_state_list}).last()

        if last_answer and last_answer.last_updated > card_instance.updated_at:
            ModelUtilities.model_update(Collabcard, {'id': card_instance.id}, {'updated_at': last_answer.last_updated})

        count -= 1


start = time.time()
print('Starting the script!')
script_for_updating_updated_at_of_collabcard()
print('Script completed in:', time.time() - start)
