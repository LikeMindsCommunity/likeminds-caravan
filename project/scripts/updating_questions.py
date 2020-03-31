import time
from togther.models import Community,communityQuestions
from django.db.models import Count



#function to change the state of intoduction questions

def get_count_of_communityQuestions(community_id):

    '''function to get count of community questions'''

    count=communityQuestions.objects.filter(community_id=community_id).count()
    return count


def change_state_of_introduction():

    question_list = communityQuestions.objects.all()

    for question in question_list:

        community_filter = Community.objects.filter(id=question.community_id)
        if community_filter.exists():
            community_instance = community_filter[0]
            question_count = get_count_of_communityQuestions(community_instance)
            if community_instance.hide_community == '3' and question_count == 1:
                question.question_state = 7
                question.value = """[{"min_chars":"50","max_chars":"No limit"}]"""
                question.optional = False
                question.save()
                print("Community Introduction Updated for community_id=",community_instance.id)






start_time=time.time()
end_time=time.time()
change_state_of_introduction()
diff = (end_time - start_time)
print(diff)