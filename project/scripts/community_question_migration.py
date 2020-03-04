from togther.models import *
import time


def migrate_community_questions():

    '''function to migrate community question'''


    form_data=Form_data.objects.all()

    for form in form_data:

        check_data=communityQuestions.objects.filter(community=form.community_id,question_title=form.data)

        if not check_data:
            question_instance=communityQuestions()
            question_instance.community=form.community_id
            question_instance.question_title=form.data
            question_instance.question_state =form.question_state
            question_instance.value = form.dropdown_list
            question_instance.dropdown_selection_limit =form.dropdown_selection_limit
            question_instance.optional = True
            question_instance.save()




start_time=time.time()
migrate_community_questions()
end_time=time.time()


print(end_time-start_time)