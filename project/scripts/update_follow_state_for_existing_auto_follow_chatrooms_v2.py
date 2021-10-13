import json
import time
from collabmates_api.search.sync import ElasticSearchSync
from collabmates_api.views import get_expiry_time_of_chatroom, create_chatroom_engagement
from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import ModelUtilities, Collabcard, Members, collabcardState
from utility.states import member_states, SyncNotificationTypes
from utility.time_utilities import TimeUtilities
from collabmates_api.notification import send_sync_notification

HOURS_24 = 86400

info_logger = LoggingWrapper.get_instance()


def update_follow_state_for_existing_auto_follow_chatrooms_v2():
    chatroom_ids = ModelUtilities.get_model_filter(Collabcard, {'auto_follow_done': True})

    filter_dict = {'follow_status': False,
                   'card_id__in': chatroom_ids}

    collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState, filter_dict)

    for state in collabcard_state_filter:
        print("Chatroom ID: {} | User ID: {}".format(state.card_id, state.user_id))
        info_logger.info("Chatroom ID: {} | User ID: {}".format(state.card_id, state.user_id))

        chatroom_follow(state)


def chatroom_follow(card_state_instance):
    follow_status = card_state_instance.follow_status

    if follow_status:
        print("Already Followed")
        return

    status = True
    card_instance = card_state_instance.card
    user_instance = card_state_instance.user
    community_instance = card_instance.community

    member_state = Members.get_community_member_state(community_instance.id, user_instance.id)

    from collabmates_api.conversation.conversation_impl import ConversationHelper

    expiry_time = get_expiry_time_of_chatroom(card_state_instance)

    card_state_instance.follow_status = status
    card_state_instance.updated_at = TimeUtilities.current_time_in_sec()
    card_state_instance.expiry_time = expiry_time
    card_state_instance.external_seen = True
    card_state_instance.external_follow = status
    card_state_instance.save()

    print("Follow status now:", card_state_instance.follow_status)
    create_chatroom_engagement(card_instance=card_instance, user_instance=user_instance,
                               member_state=member_state)

    ConversationHelper.update_homescreen_meta_on_chatroom_follow(community_instance,
                                                                 card_instance,
                                                                 card_state_instance,
                                                                 user_instance)

    send_sync_notification.delay({'chatroom_id': card_instance.id,
                                  'member_id': user_instance.id,
                                  'sync_notification_type': SyncNotificationTypes.SINGLE_MEMBER.value})

    ElasticSearchSync.update_chatroom_for_user.delay(card_instance.id, user_instance.id)

    if card_instance.is_secret and member_state == member_states.ADMIN and status:
        participants_list = json.loads(card_instance.secret_chatroom_participants)

        if user_instance.id not in participants_list:
            participants_list.append(user_instance.id)
            ModelUtilities.model_update(Collabcard, {'id': card_instance.id},
                                        {'secret_chatroom_participants': json.dumps(participants_list)})


start_time = time.time()
update_follow_state_for_existing_auto_follow_chatrooms_v2()
end_time = time.time()
time_taken = end_time - start_time

print(time_taken)
