import time

from togther.models import (ModelUtilities, collabcardState)
from utility.states import (noti_states)
from collabmates_api.chatroom.chatroom_impl import (ChatroomImpl)
from django.conf import settings

if settings.IS_BETA:
    previous_notification_state = noti_states.ONLY_MENTIONS_AND_REPLIES
    notification_state = noti_states.ALL_MESSAGES
    chatroom_id = None
    user_id = None
    community_id = 50441

    filter_dict = {
        'community': community_id
    }

else:
    previous_notification_state = noti_states.ONLY_MENTIONS_AND_REPLIES
    notification_state = noti_states.ALL_MESSAGES
    chatroom_id = None
    community_id = None
    user_id = None

    filter_dict = {
        'community': community_id
    }


def update_notification_state_for_users_in_community():
    if chatroom_id:
        filter_dict['card'] = chatroom_id

    if user_id:
        filter_dict['user'] = user_id

    if not filter_dict:
        return

    card_state_filter = ModelUtilities.get_model_filter(collabcardState, filter_dict)

    count = card_state_filter.count()

    print("Records to be updated ->", count)

    for card_state_instance in card_state_filter:
        print(count)

        ChatroomImpl(member_id=card_state_instance.user_id,
                     chatroom_id=card_state_instance.card_id).update_chatroom_noti_settings(
            noti_state=notification_state, is_noti_paused=None, pause_noti_for=None)

        count -= 1


def update_notification_state_for_users_in_community_in_bulk():
    if chatroom_id:
        filter_dict['card'] = chatroom_id

    if user_id:
        filter_dict['user'] = user_id

    if previous_notification_state:
        filter_dict['noti_state'] = previous_notification_state

    if not filter_dict:
        return

    card_state_filter = ModelUtilities.get_model_filter(collabcardState, filter_dict)

    count = card_state_filter.count()

    print("Records to be updated ->", count)
    records_updated_count = ModelUtilities.model_update(collabcardState,
                                                        filter_dict,
                                                        {'noti_state': notification_state})

    print("Updated records count ->", records_updated_count)


start = time.time()
print('Starting script!')
# update_notification_state_for_users_in_community()
update_notification_state_for_users_in_community_in_bulk()
print('Script completed in ->', time.time() - start)
