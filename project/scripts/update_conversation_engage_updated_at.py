from togther.models import Collabcard, conversationEngage, card_answers, ModelUtilities, collabcardState
import time
from utility.time_utilities import TimeUtilities


def update_last_conversation_time_for_dm_chatroom():
    dm_card_instances = ModelUtilities.get_model_filter(Collabcard, {"is_private": True})
    card_count = dm_card_instances.count()

    for card in dm_card_instances:
        card_answers_filter = ModelUtilities.get_model_filter(card_answers, {"card": card})

        if card_answers_filter:
            last_card_answer_instance = card_answers_filter.last()
            conversation_engage_filter = ModelUtilities.get_model_filter(conversationEngage, {"card": card})

            card_created_at = TimeUtilities.convert_milliseconds_to_sec(last_card_answer_instance.last_updated)

            if conversation_engage_filter:
                conversation_engage_filter.update(updated_at=card_created_at)

            collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState, {"card": card})

            if collabcard_state_filter:
                collabcard_state_filter.update(expiry_time=TimeUtilities.add_hours_to_epoch_time(card_created_at, 24))

        card_count -= 1
        print("Card count left", str(card_count))


print("STARTED")
start_time = time.time()
update_last_conversation_time_for_dm_chatroom()
print("Completed in", str(time.time() - start_time))
