import json

from rest_framework import serializers
from django_elasticsearch_dsl_drf.serializers import DocumentSerializer

from .chatroom_index import ChatroomDocument
from .conversation_index import ConversationDocument
from .member_directory_index import MemberDirectoryDocument


class ChatroomDocumentSerializer(DocumentSerializer):
    """Serializer for the Book document."""

    class Meta:
        """Meta options."""

        # Specify the correspondent document class
        document = ChatroomDocument

        # List the serializer fields. Note, that the order of the fields
        # is preserved in the ViewSet.
        fields = '__all__'

    def to_representation(self, obj):
        data = super(ChatroomDocumentSerializer, self).to_representation(obj)

        fields = self._readable_fields

        for field in fields:

            if data[field.field_name] is None:
                del data[field.field_name]

        if 'attachments' in data:
            data['chatroom']['attachments'] = data.pop('attachments')

        return data


class ConversationDocumentSerializer(DocumentSerializer):
    """Serializer for the Book document."""

    class Meta:
        """Meta options."""

        # Specify the correspondent document class
        document = ConversationDocument

        # List the serializer fields. Note, that the order of the fields
        # is preserved in the ViewSet.
        fields = '__all__'


class MemberDirectoryDocumentSerializer(DocumentSerializer):
    """Serializer for the Book document."""

    class Meta:
        """Meta options."""

        # Specify the correspondent document class
        document = MemberDirectoryDocument

        # List the serializer fields. Note, that the order of the fields
        # is preserved in the ViewSet.
        fields = '__all__'
