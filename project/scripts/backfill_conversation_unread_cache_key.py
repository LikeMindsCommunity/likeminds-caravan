import time

from external_services.caching.cache_impl import CacheImpl
from togther.models import ModelUtilities, conversationEngage
from utility.constants import CONVERSATIONS_UNREAD_USER_CHATROOM_KEY


def backfill_conversation_unread_cache_key():
    updated_count = 0
    invalid_count = 0
    existing_cache_count = 0
    set_status_false_count = 0

    conversation_engage_list = ModelUtilities.get_model_filter(conversationEngage, {})

    for conversation_engage_instance in conversation_engage_list:
        user_id = conversation_engage_instance.user_id
        card_id = conversation_engage_instance.card_id

        if not user_id:
            print("Invalid user_id | ID: {}".format(conversation_engage_instance.id))
            invalid_count += 1
            continue

        if not card_id:
            print("Invalid card_id | ID: {}".format(conversation_engage_instance.id))
            invalid_count += 1
            continue

        key = CONVERSATIONS_UNREAD_USER_CHATROOM_KEY % (str(user_id), str(card_id))
        previous_count = CacheImpl.get_cache(key)

        if not previous_count:

            previous_count = {}
            unread_count_for_user = conversation_engage_instance.unseen_count
            previous_count['unseen_count'] = unread_count_for_user

            status = CacheImpl.set_cache(key, previous_count)

            if status:
                print("Card ID: {} | User ID: {} | Count : {} ".format(card_id, user_id, unread_count_for_user))
                updated_count += 1

            else:
                print("Set Cache status: False | ID: {}".format(conversation_engage_instance.id))
                set_status_false_count += 1

        else:
            print("Cache already exists status: False | ID: {}".format(conversation_engage_instance.id))
            existing_cache_count += 1

    print("Updated Count:", updated_count)
    print("Invalid Count:", invalid_count)
    print("Set Cache False Count:", set_status_false_count)
    print("Already Existing Cache Count:", existing_cache_count)


start_time = time.time()
backfill_conversation_unread_cache_key()
end_time = time.time()
time_taken = end_time - start_time

print("Time Taken: ", time_taken)
