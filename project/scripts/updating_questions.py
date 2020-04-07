import time
from togther.models import Community,communityQuestions
from django.db.models import Count,Q
import json
import ast

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



#function to change the format of dropdown questions

def get_dropdown_questions():

    dropdown_questions = communityQuestions.objects.filter(Q(question_state=1)|Q(question_state=2))

    for question in dropdown_questions:


        if question.community.hide_community == '3' or question.community.hide_community == '4' :

            index = question.value.find("value")

            if index == -1:

                value = change_structure_of_question(question.value)
                #print("value--",value)
                print("community_id",question.community.id)
                print("value--",value)
                print("\n")
                question.value = value
                question.save()





#[{"value":"Engineering"},{"value":"Design \/ Product"},{"value":"Growth \/ Marketing"},{"value":"Community \/ Partnerships"},{"value":"Other"},{"value":"Hiring \/ Legal \/ Finance"},{"value":"Other"}]

def change_structure_of_question(value_list):


    try:
        value_list = json.loads(value_list)
    except:
        return
    ans=[]
    for value in value_list:
        temp={}
        temp['value'] = value
        ans.append(temp)

    json_dump=json.dumps(ans)

    return json_dump





start_time=time.time()
end_time=time.time()
get_dropdown_questions()
diff = (end_time - start_time)
print(diff)
