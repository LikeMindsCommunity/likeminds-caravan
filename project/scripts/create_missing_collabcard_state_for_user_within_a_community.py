import time

from django.contrib.auth.models import User
from django.db.models import Q

from togther.models import ModelUtilities, collabcardState, Collabcard
from utility.states import card_types

info = {
    'user_id': 36,
    'community_id': 49835
}


def create_missing_collabcard_state_for_user_within_a_community():
    existing_collabcard_states = ModelUtilities.get_model_filter(model=collabcardState, filter_dict=info)
    chatroom_ids = list(existing_collabcard_states.values_list('card_id', flat=True))

    filter_dict = {
        'community_id': info.get('community_id'),
        'is_secret': False,
        'is_deleted': False,
        'is_pending': False,
        'is_private': False
    }

    user_instance = ModelUtilities.get_model_instance_or_none(User, info.get('user_id'))

    # Fetch all the collabcard ids for which state instance is not present
    chatroom_list = ModelUtilities.get_model_filter(model=Collabcard, filter_dict=filter_dict).exclude(
        id__in=chatroom_ids)

    # Excluding DM Chatroom(s)
    chatroom_list = chatroom_list.filter(~Q(type=card_types.CARD_DIRECT_MESSAGE))

    print("Chatroom List:", chatroom_list)

    for card_instance in chatroom_list:

        print("Card ID {} | Type {}".format(card_instance.id, card_instance.type))
        state_exists = ModelUtilities.is_model_filter_exists(collabcardState,
                                                             {'card': card_instance, 'user': user_instance})
        if state_exists:
            continue

        card_state_instance = collabcardState.create_chatroom_state_instance(card_instance, user_instance,
                                                                             follow_status=False)

        print("Chatroom ID:", card_instance.id)
        print("Collabcard State ID:", card_state_instance.id)


start_time = time.time()
create_missing_collabcard_state_for_user_within_a_community()
end_time = time.time()
time_taken = end_time - start_time

print("Time Taken: ", time_taken)
