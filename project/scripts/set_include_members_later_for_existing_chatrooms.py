import json
import time
from collabmates_api.search.sync import ElasticSearchSync
from collabmates_api.views import get_expiry_time_of_chatroom, create_chatroom_engagement
from togther.models import ModelUtilities, Collabcard, Members, collabcardState
from utility.states import member_states, conversation_states, SyncNotificationTypes
from utility.time_utilities import TimeUtilities
from collabmates_api.notification import send_sync_notification

HOURS_24 = 86400


def set_include_members_later_for_existing_chatrooms():
    filter_dict = {
        'auto_follow_done': True,
        'include_members_later': False
    }

    chatroom_filter = list(ModelUtilities.get_model_filter(Collabcard, filter_dict).values_list('id', flat=True))
    chatroom_count = ModelUtilities.get_model_filter(Collabcard, filter_dict).values_list('id', flat=True).count()

    print("Chatroom IDs: {}".format(chatroom_filter))

    update_dict = {
        'include_members_later': True,
        'updated_at': TimeUtilities.current_time_in_sec()
    }

    ModelUtilities.model_update(Collabcard, filter_dict, update_dict)

    print("Chatroom Count: {}".format(chatroom_count))


def update_follow_state_for_existing_auto_follow_chatrooms():
    filter_dict = {
        'auto_follow_done': True,
        'include_members_later': False
    }

    chatroom_filter = ModelUtilities.get_model_filter(Collabcard, filter_dict)

    for chatroom_instance in chatroom_filter:

        member_state_list = [member_states.MEMBER, member_states.KNOWN_NOMINATED_PROMOTER, member_states.ADMIN,
                             member_states.PROFILE_UNAVAILABLE]

        community_members = ModelUtilities.get_model_filter(Members, {'state__in': member_state_list,
                                                                      'community_id_id': chatroom_instance.community_id})

        for member in community_members:
            print("Chatroom ID: {} | User ID: {}".format(chatroom_instance.id, member.member_id))

            try:
                chatroom_follow(card_instance=chatroom_instance, user_instance=member.member_id)

            except Exception as e:
                print(str(e))


def chatroom_follow(card_instance, user_instance):
    print("Card: ", card_instance.id, "User: ", user_instance.id, )
    status = True

    if not card_instance:
        print("Card Instance does not exist")
        return

    if not user_instance:
        print("Invalid User instance")
        return

    community_instance = card_instance.community
    member_state = Members.get_community_member_state(community_instance.id, user_instance.id)
    expiry_time = get_expiry_time_of_chatroom()

    chatroom_state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': card_instance,
                                                                              'user': user_instance})

    from collabmates_api.conversation.conversation_impl import ConversationHelper

    if not chatroom_state_filter:
        card_state_instance = collabcardState.create_chatroom_state_instance(card_instance, user_instance,
                                                                             expire_at=expiry_time,
                                                                             follow_status=status, external_follow=True)

        ConversationHelper.create_conversation_state(card_instance=card_instance,
                                                     user_instance=user_instance,
                                                     state=conversation_states.CONVERSATION_FOLLOW,
                                                     community_instance=community_instance,
                                                     member_state=member_state)

        create_chatroom_engagement(card_instance=card_instance, user_instance=user_instance,
                                   member_state=member_state)

    else:

        card_state_instance = chatroom_state_filter[0]

        follow_status = card_state_instance.follow_status

        if follow_status:
            print("Already Followed")
            return

        expiry_time = get_expiry_time_of_chatroom(card_state_instance)

        chatroom_state_filter.update(follow_status=status, updated_at=TimeUtilities.current_time_in_sec(),
                                     external_seen=True, external_follow=status)

        ConversationHelper.create_conversation_state(card_instance=card_instance,
                                                     user_instance=user_instance,
                                                     state=conversation_states.CONVERSATION_FOLLOW,
                                                     community_instance=community_instance,
                                                     member_state=member_state)
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
update_follow_state_for_existing_auto_follow_chatrooms()
set_include_members_later_for_existing_chatrooms()
end_time = time.time()
time_taken = end_time - start_time

print(time_taken)
