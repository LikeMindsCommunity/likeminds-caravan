from togther.models import (Collabcard, card_answers, Card_Attachment,
                            answerAttachment, collabcardState)
import time

files_type = ['image', 'video']


def get_chatroom_list_with_files():
    return list(Card_Attachment.objects.all().distinct('collabcard').values_list('collabcard__id', flat=True))


def get_conversation_list_with_files():
    return list(answerAttachment.objects.all().distinct('answer').values_list('answer__id', flat=True))


def get_chatroom_files_count(chatroom):
    return Card_Attachment.objects.filter(collabcard=chatroom, type__in=files_type).count()


def get_conversation_files_count(answer):
    return answerAttachment.objects.filter(answer=answer, type__in=files_type).count()


def update_chatroom_files_attachment_count():
    chatroom_list = get_chatroom_list_with_files()

    count = 0
    for chatroom_id in chatroom_list:
        try:
            print(f"updating chatroom with id {chatroom_id}")
            chatroom_instance = Collabcard.objects.get(pk=chatroom_id)
            attachment_count = get_chatroom_files_count(chatroom_instance)
            chatroom_instance.attachment_count = attachment_count
            chatroom_instance.attachments_uploaded = attachment_count > 0
            chatroom_instance.has_files = attachment_count > 0
            chatroom_instance.save()

            collabcardState.objects.filter(card=chatroom_instance).update(updated_at=time.time())

            count += 1
            if count == 10:
                count = 0
                time.sleep(0.2)

        except:
            print(f"chatroom with id {chatroom_id} not found")
            continue


def update_conversation_files_attachment_count():
    conversation_list = get_conversation_list_with_files()

    count = 0
    for conversation_id in conversation_list:
        try:
            print(f"updating conversation with id {conversation_id}")
            answer_instance = card_answers.objects.get(pk=conversation_id)
            attachment_count = get_conversation_files_count(answer_instance)
            answer_instance.attachment_count = attachment_count
            answer_instance.attachments_uploaded = attachment_count > 0
            answer_instance.has_files = attachment_count > 0

            answer_instance.last_updated = time.time()
            answer_instance.save()

            count += 1
            if count == 10:
                count = 0
                time.sleep(0.2)

        except:
            print(f"conversation with id {conversation_id} not found")
            continue


def update_attachment_count():
    print('updating chatrooms ================ >>>>>>>>>>>>>')
    update_chatroom_files_attachment_count()
    print('updating conversation ================ >>>>>>>>>>>>>')
    update_conversation_files_attachment_count()


start_time = time.time()
print(">>>>>> started >>>>>>>>   ", start_time)

update_attachment_count()

end_time = time.time()
print(">>>>>> end >>>>>>>>  ", end_time)
diff = end_time - start_time
print(">>>>>> total >>>>>>>>  ", diff)

# from scripts import update_attachments_count
