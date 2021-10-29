from togther.models import Collabcard, conversationEngage, card_answers, ModelUtilities
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

            if conversation_engage_filter:
                conversation_engage_filter.update(updated_at=TimeUtilities.convert_milliseconds_to_sec(
                    last_card_answer_instance.last_updated))

        card_count -= 1
        print("Card count left", str(card_count))


print("STARTED")
start_time = time.time()
update_last_conversation_time_for_dm_chatroom()
print("Completed in", str(time.time() - start_time))
