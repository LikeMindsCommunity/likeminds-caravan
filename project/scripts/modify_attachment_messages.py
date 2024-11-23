import re
import time
from itertools import islice
from togther.models import answerAttachment, ModelUtilities, card_answers

# Regex to match and remove the specific lines
regex = r'\\n?\s*\*\s*This is a (gif|video|pdf|image|file) message\. Please update your app\s*\*'


def modify_attachment_messages():
    filter_dict = {
        'answer__answer__iregex': regex
    }

    all_answer_attachment = ModelUtilities.get_model_filter(answerAttachment, filter_dict).select_related(
        'answer').iterator()

    while True:
        batch = list(islice(all_answer_attachment, 1000))

        print(batch)

        if not batch:
            break

        answer_instance_list = []

        for instance in batch:
            answer_instance = instance.answer
            answer = answer_instance.answer

            if isinstance(answer, str):
                answer = re.sub(regex, '', answer)
                answer_instance.answer = answer
                answer_instance_list.append(answer_instance)

        ModelUtilities.bulk_update_instances(card_answers, answer_instance_list, ['answer'])


print("Starting the script")
start = time.time()
modify_attachment_messages()
print(f"Script completed: {time.time() - start}")
