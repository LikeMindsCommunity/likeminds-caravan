from togther.models import Collabcard,card_answers,conversationEngage
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




start_time = time.time()
add_community_in_conversations()
add_community_in_conversationEngage()
end_time = time.time()

diff = end_time - start_time

print(diff)

