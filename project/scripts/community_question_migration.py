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



def migrate_community_answers():

    '''functions to migrate community answers'''

    form_responses=Form_response.objects.all()

    for form in form_responses:

        check_data=communityAnswers.objects.filter(member=form.user,community=form.community,question_answer=form.data)
        if not check_data:
            question_details=communityQuestions.objects.filter(question_title=form.data)
            if question_details:
                question_id=question_details[0]

                community_instance=Community.objects.filter(id=form.community)

                user_instance=User.objects.filter(id=form.user)

                if user_instance and community_instance:
                    answer_instance=communityAnswers()
                    answer_instance.community =community_instance[0]
                    answer_instance.question_title = form.data
                    answer_instance.question_answer =form.response
                    answer_instance.member = user_instance[0]
                    answer_instance.question = question_id
                    answer_instance.save()


start_time=time.time()
migrate_community_questions()
migrate_community_answers()
end_time=time.time()


print(end_time-start_time)