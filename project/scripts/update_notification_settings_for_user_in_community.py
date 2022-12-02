import time

from togther.models import (ModelUtilities, collabcardState)
from utility.states import (noti_states)
from collabmates_api.chatroom.chatroom_impl import (ChatroomImpl)
from django.conf import settings

if settings.IS_BETA:
    notification_state = noti_states.ALL_MESSAGES
    chatroom_id = None
    user_id = 3877

    filter_dict = {
        'user': user_id,
        'community': 50429,
        'follow_status': True,
        'remove': None
    }

else:
    notification_state = noti_states.ALL_MESSAGES
    chatroom_id = None
    user_id = 3877

    filter_dict = {
        'user': user_id,
        'community': 2,
        'follow_status': True,
        'remove': None
    }


def update_notification_state_for_user_in_community():
    if chatroom_id:
        filter_dict['card'] = chatroom_id

    card_state_filter = ModelUtilities.get_model_filter(collabcardState, filter_dict)

    if card_state_filter:

        for card_state_instance in card_state_filter:
            ChatroomImpl(member_id=user_id, chatroom_id=card_state_instance.card_id).update_chatroom_noti_settings(
                noti_state=notification_state, is_noti_paused=None, pause_noti_for=None)


start = time.time()
print('Starting script!')
update_notification_state_for_user_in_community()
print('Script completed in ->', time.time() - start)
