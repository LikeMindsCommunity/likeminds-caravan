from togther.models import Card_Attachment, answerAttachment, Collabcard, card_answers
from ..rest_api import ChatroomAttachmentsSerializer, ConversationAttachmentsSerializer


class IndexUtilities:

    def __init__(self, instance):

        if not isinstance(instance, Collabcard) and not isinstance(instance, card_answers):
            raise Exception('Invalid class')

        self.instance = instance

        self.serializer = ChatroomAttachmentsSerializer if isinstance(instance, Collabcard) else ConversationAttachmentsSerializer

    def get_attachments(self):
        return self.serializer(self.get_query_set(), many=True).data

    def get_query_set(self):
        if isinstance(self.instance, Collabcard):
            return Card_Attachment.objects.filter(collabcard=self.instance)

        else:
            return answerAttachment.objects.filter(answer=self.instance)
