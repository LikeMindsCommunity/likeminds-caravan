from togther.models import Collabcard,card_answers,conversationEngage,Members,collabcardState
import time

def add_community_in_conversations():

    '''api to add conversations in chatrooms'''

    answer_filter = card_answers.objects.all()

    for answer in answer_filter:
        community_instance = answer.card.community
        answer.community = community_instance
        answer.save()
        print(answer)



def add_community_in_conversationEngage():

    '''api to add conversations in chatrooms'''

    engage_filter = conversationEngage.objects.all()

    for data in engage_filter:


        if data.card:
            community_instance = data.card.community
        elif data.draft:
            community_instance = data.draft.community
        else:
            continue


        data.community = community_instance
        data.save()
        print(data)




def get_latest_conversation_members(chatroom_id):

    '''function to get last conversation members'''

    card_instance = Collabcard.objects.get(id=chatroom_id)

    answer_filter = card_answers.objects.filter(card=card_instance, state=0).order_by('-id')

    user_set = set()

    member_conversarions = []
    user_conversations = []
    for data in answer_filter:

        if data.card.user.id == data.user.id:
            continue

        if data.user not in user_set:

            member_filter = Members.objects.filter(community_id=card_instance.community,member_id=data.user)
            if member_filter.exists():
                member_instance=member_filter[0]
                member_conversarions.append(member_instance)
            else:
                state_filter = collabcardState.objects.filter(card=card_instance,user=data.user)
                if state_filter.exists():
                    state_instance=state_filter[0]
                    user_conversations.append(state_instance)

            user_set.add(data.user)

        if len(user_set) > 1:
            break


    return (member_conversarions,user_conversations)



def migrate_last_conversation(chatroom_id):



    last_conversations = get_latest_conversation_members(chatroom_id)

    member_conversations = last_conversations[0]
    user_conversations = last_conversations[1]

    last_conversation_member = None
    second_last_conversation_member = None
    if len(member_conversations) > 1:
        last_conversation_member = member_conversations[0]
        second_last_conversation_member = member_conversations[1]
    elif len(member_conversations) == 1:
        last_conversation_member = member_conversations[0]

    last_conversation_user = None
    second_last_conversation_user = None
    if len(user_conversations) > 1:
        last_conversation_user = user_conversations[0]
        second_last_conversation_user = user_conversations[1]
    elif len(user_conversations) == 1:
        last_conversation_user = user_conversations[0]

    update_status =  conversationEngage.objects.filter(card=chatroom_id).update(
        last_conversation_member=last_conversation_member,
        second_last_conversation_member=second_last_conversation_member,
        last_conversation_user=last_conversation_user,
        second_last_conversation_user=second_last_conversation_user
    )
    print(update_status)


def get_unique_conversation_engage():

    unique_chatrooms = conversationEngage.objects.all().order_by('-updated_at')
    #print(unique_chatrooms.query)
    chatroom_set = set()
    i =0
    for data in unique_chatrooms:

        if not data.card:
            continue
        if data.card not in chatroom_set:
            print(data.card)
            migrate_last_conversation(chatroom_id=data.card.id)
            chatroom_set.add(data.card)








start_time = time.time()

get_unique_conversation_engage()

end_time = time.time()

diff = end_time - start_time

print(diff)

