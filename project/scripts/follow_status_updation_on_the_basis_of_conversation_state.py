import json
import time

from django.db import transaction

from togther.models import ModelUtilities, card_answers, collabcardState
from utility.states import conversation_states, card_types


def follow_status_updation_on_the_basis_of_conversation_state():
    updated_card_state_ids = []

    with transaction.atomic():
        collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState, {
            'follow_status': False,
            'card__type': card_types.CARD_NORMAL
        })
        to_be_updated_count = collabcard_state_filter.count()
        count_left = to_be_updated_count

        print("To update count:", to_be_updated_count)

        for collabcard_state_instance in collabcard_state_filter:
            count_left -= 1
            print("Count Left:", count_left)

            followed_conversation_filter = ModelUtilities.get_model_filter(card_answers, {
                'state': conversation_states.CONVERSATION_FOLLOW,
                'card_id': collabcard_state_instance.card_id,
                'user_id': collabcard_state_instance.user_id
            }).order_by('-created_at')

            unfollowed_conversation_filter = ModelUtilities.get_model_filter(card_answers, {
                'state': conversation_states.CONVERSATION_UNFOLLOW,
                'card_id': collabcard_state_instance.card_id,
                'user_id': collabcard_state_instance.user_id
            }).order_by('-created_at')

            unfollowed_conversation_instance = None

            # User didn't follow chatroom
            if not followed_conversation_filter:
                continue

            if unfollowed_conversation_filter:
                unfollowed_conversation_instance = unfollowed_conversation_filter[0]

            followed_conversation_instance = followed_conversation_filter[0]

            # User didn't unfollow chatroom.
            if not unfollowed_conversation_instance and followed_conversation_instance:
                collabcard_state_instance.follow_status = True
                collabcard_state_instance.save()
                updated_card_state_ids.append(collabcard_state_instance.id)
                time.sleep(0.5)

            # User followed chatroom after unfollowing at-least once.
            elif unfollowed_conversation_instance.created_at < followed_conversation_instance.created_at:
                collabcard_state_instance.follow_status = True
                collabcard_state_instance.save()
                updated_card_state_ids.append(collabcard_state_instance.id)
                time.sleep(0.5)

        print("To update count:", to_be_updated_count)
        print("Updated count:", len(updated_card_state_ids))

    with open('follow_status_updation_state_ids.txt', 'w+') as f:
        f.write(json.dumps(updated_card_state_ids))


start_time = time.time()
follow_status_updation_on_the_basis_of_conversation_state()
end_time = time.time()
time_taken = end_time - start_time

print(time_taken)

