#script to update question text in a pre created community
import time
from togther.models import *
from django.db.models import Count

def update_question_text():

    '''function to update question text in a pre-created community'''

    question_list=Form_data.objects.filter().values('community_id','id').annotate(question_count=Count('community_id'))

    for question in question_list:

        if question['question_count'] == 1 and question['community_id'] < 46975 :
            community_instance=Community.objects.get(id=question['community_id'])
            if community_instance.hide_community == '3' and community_instance.introduction_text:
                form_data_instance=Form_data.objects.get(id=question['id'])
                form_data_instance.data=community_instance.introduction_text
                form_data_instance.save()
                print("Question updated for")
                print(community_instance)





start_time=time.time()
update_question_text()
end_time=time.time()

diff = (end_time - start_time)
print(diff)