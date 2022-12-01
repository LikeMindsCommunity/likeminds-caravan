import time

from togther.models import (ModelUtilities, collabcardState)
from utility.states import (noti_states)
from django.conf import settings

if settings.IS_BETA:
    notification_state = noti_states.ALL_MESSAGES
    chatroom_id = None

    filter_dict = {
        'user': 3877,
        'community': 50429,
        'follow_status': True,
        'remove': None
    }

else:
    notification_state = noti_states.ALL_MESSAGES
    chatroom_id = None

    filter_dict = {
        'user': 2,
        'community': 2,
        'follow_status': True,
        'remove': None
    }


def update_notification_state_for_user_in_community():
    if chatroom_id:
        filter_dict['card'] = chatroom_id

    card_state_filter = ModelUtilities.get_model_filter(collabcardState, filter_dict)

    if card_state_filter:
        card_state_filter.update(noti_state=notification_state)


start = time.time()
print('Starting script!')
update_notification_state_for_user_in_community()
print('Script completed in ->', time.time() - start)
