from togther.models import Collabcard,card_answers


def add_community_in_conversations():

    '''api to add conversations in chatrooms'''

    answer_filter = card_answers.objects.all()

    for answer in answer_filter:
        community_instance = answer.card.community
        answer.community = community_instance
        answer.save()
        print(answer)



add_community_in_conversations()