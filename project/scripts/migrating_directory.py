from togther.models import communityFieldTypes,communityFieldSubTypes,communityField,communityQuestions
import time
def migrate_directory_fields_in_communityQuestions():

    question_filter = communityQuestions.objects.all().order_by('-id')

    for instance in question_filter:

        question_title = instance.question_title

        field_filter = communityField.objects.filter(question_title=question_title,field=True)

        if field_filter.exists():

            instance.field = True
            instance.save()

            print(str(instance.id) + " saved")


start_time = time.time()

migrate_directory_fields_in_communityQuestions()

end_time = time.time()


print(end_time - start_time)