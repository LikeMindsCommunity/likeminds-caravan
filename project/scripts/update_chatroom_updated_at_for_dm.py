import time

from togther.models import (ModelUtilities, card_answers, Collabcard)
from utility.states import (card_types, conversation_states)

COMMUNITY_ID = None


def update_chatroom_updated_at_for_dm():

    if not COMMUNITY_ID:
        return

    filter_dict = {
        'community': COMMUNITY_ID,
        'is_private': True,
        'type': card_types.CARD_DIRECT_MESSAGE
    }

    dm_chatroom_filter = ModelUtilities.get_model_filter(Collabcard, filter_dict)

    count = dm_chatroom_filter.count()

    for dm_chatroom in dm_chatroom_filter:
        print(f'Records left to be updated {count}')

        filter_dict = {
            'card': dm_chatroom,
            'state__in': [conversation_states.ANSWER, conversation_states.CONVERSATION_POLL]
        }

        last_message_instance = ModelUtilities.get_model_filter(card_answers, filter_dict).last()

        count -= 1

        if not last_message_instance:
            continue

        ModelUtilities.model_update(Collabcard,
                                    {'id': dm_chatroom.id},
                                    {'updated_at': last_message_instance.last_updated})


start_time = time.time()
print('Starting the script')
update_chatroom_updated_at_for_dm()
print(f'Script completed in {time.time() - start_time}')
