import time

from togther.models import (ModelUtilities, collabcardState)
from utility.states import (noti_states)
from collabmates_api.chatroom.chatroom_impl import (ChatroomImpl)
from django.conf import settings

if settings.IS_BETA:
    notification_state = noti_states.ONLY_MENTIONS_AND_REPLIES
    chatroom_id = None
    user_id = None
    community_id = None

    filter_dict = {
        'community': community_id,
        'remove': None
    }

else:
    notification_state = noti_states.ALL_MESSAGES
    chatroom_id = None
    community_id = None
    user_id = None

    filter_dict = {
        'community': community_id,
        'remove': None
    }


def update_notification_state_for_users_in_community():
    if chatroom_id:
        filter_dict['card'] = chatroom_id

    if user_id:
        filter_dict['user'] = user_id

    card_state_filter = ModelUtilities.get_model_filter(collabcardState, filter_dict)

    count = card_state_filter.count()

    print("Records to be updated ->", count)

    for card_state_instance in card_state_filter:
        print(count)

        ChatroomImpl(member_id=card_state_instance.user_id,
                     chatroom_id=card_state_instance.card_id).update_chatroom_noti_settings(
            noti_state=notification_state, is_noti_paused=None, pause_noti_for=None)

        count -= 1


start = time.time()
print('Starting script!')
update_notification_state_for_users_in_community()
print('Script completed in ->', time.time() - start)
