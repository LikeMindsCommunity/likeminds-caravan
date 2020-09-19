from togther.models import Collabcard, card_answers, conversationEngage, collabcardState
import time

HOURS_24 = 86400


def get_expiry_time_of_chatroom(card_state_instance=None):
    '''function to get expiry time of chatroom'''
    expiry_time = time.time() + 86400

    if card_state_instance:
        if card_state_instance.expiry_time and card_state_instance.expiry_time > expiry_time:
            expiry_time = card_state_instance.expiry_time

    return expiry_time


def update_activity_in_chatroom(card_instance, user_instance):
    '''function to update activities in chatrooms

    in collabcardState table and conversationEngage table'''
    engage_filter = conversationEngage.objects.filter(card=card_instance, user=user_instance)
    # expiry_time = get_expiry_time_of_chatroom()
    if engage_filter.exists():
        engage_instance = engage_filter[0]
        unread_count = engage_instance.unseen_count

        state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)
        expiry_time = get_expiry_time_of_chatroom(card_state_instance=state_filter[0])

        if unread_count > 0:
            if state_filter.exists():
                state_filter[0].expiry_time = None
                state_filter[0].save()
        else:

            expire_at = get_expire_at(card_instance)

            state_filter.update(expiry_time=expire_at)





def get_expire_at(card_instance):

    last_conversation = card_answers.objects.filter(card=card_instance, state=0).last()
    if last_conversation:
        expire_at = last_conversation.created_at + HOURS_24
    else:
        expire_at = card_instance.date_epoch + HOURS_24

    return expire_at



def get_all_chatroom_states():
    chatroooms = collabcardState.objects.filter(remove=None).order_by('id')
    for data in chatroooms:

        card_instance = data.card
        user_instance = data.user
        follow_status = data.follow_status


        if follow_status:
            update_activity_in_chatroom(card_instance, user_instance)
        else:
            if not data.expiry_time:
                data.expiry_time = get_expire_at(card_instance)
                data.save()

        print(card_instance)
        print(user_instance)




start_time = time.time()
get_all_chatroom_states()
end_time = time.time()

diff = end_time - start_time

print(diff)
