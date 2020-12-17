from togther.models import card_answers, collabcardState
from collabmates_api.conversation.conversation_manager import ConversationManager
from collabmates_api.serializers import conversationSerializer
from collabmates_api.views import reverse_conversations_for_upward_pagination
from external_services.logging.logging_wrapper import LoggingWrapper
from collabmates_api.utility import pagination

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()

class ConversationImpl(ConversationManager):

    member_id = None
    chatroom_id = None
    scroll_direction = None
    conversation_id = None
    page = None
    paginate_by=None




    def __init__(self, member_id: str, chatroom_id: str, scroll_direction: str, conversation_id: str,page: str,paginate_by: str):

        self.member_id = member_id
        self.chatroom_id = chatroom_id
        self.scroll_direction = scroll_direction
        self.conversation_id = conversation_id
        self.page = page
        self.paginate_by = paginate_by


    def get_member_id(self) -> str:
        return self.member_id

    def set_member_id(self, member_id: str) -> None:
        self.member_id = member_id

    def get_chatroom_id(self) -> {}:
        return self.chatroom_id

    def set_chatroom_id(self,chatroom_id):
       self.chatroom_id =  chatroom_id

    def get_scoll_direction(self):
        return self.scroll_direction

    def set_scroll_direction(self,scroll_direction):
        self.scroll_direction = scroll_direction

    def get_conversation_id(self):
        return self.conversation_id

    def set_conversation_id(self, conversation_id):
        self.conversation_id = conversation_id

    def get_page(self):
        return self.page

    def set_page(self, page):
        self.page = page

    def get_paginate_by(self):
        return self.paginate_by

    def set_paginate_by(self, paginate_by):
        self.set_paginate_by = paginate_by


    def _fetch_conversation_queryset(self):

        return card_answers.objects.select_related('reply', 'preview_community',
                                                               'preview_chatroom').filter(card=self.get_chatroom_id()).order_by('id')

    def _fetch_upward_conversation_queryset(self, list_size):

        return card_answers.objects.select_related('reply', 'preview_community',
                                                               'preview_chatroom').filter(card=self.get_chatroom_id()).filter(id__lte=self.get_conversation_id()).order_by('-id')[:list_size]

    def _fetch_downward_conversation_queryset(self, list_size):
        return card_answers.objects.select_related('reply', 'preview_community',
                                                               'preview_chatroom').filter(card=self.get_chatroom_id()).filter(id__gt=self.get_conversation_id()).order_by('-id')[:list_size]

    def _paged_queryset(self, conversation_filter):
        page = self.get_page()
        paginate_by = self.get_paginate_by()
        return pagination(conversation_filter, page, paginate_by = paginate_by)


    def _fetch_last_seen_conversation(self):

        last_seen_conversation = None
        user_chatroom_instance = collabcardState.objects.filter(card=self.get_chatroom_id(),user=self.get_member_id()).first()

        if user_chatroom_instance:
            last_seen_conversation = user_chatroom_instance.last_seen_conversation

        return last_seen_conversation

    def _serialize_conversation(self,conversation_instance):
        return conversationSerializer(conversation_instance)

    def _create_conversation_list(self,conversations):

        conversation_list = []
        for conversation in conversations:
            conversation_dict = self._serialize_conversation(conversation)
            conversation_list.append(conversation_dict)

        return conversation_list


    def fetch_conversation(self):

        if not self.get_scoll_direction() and self.get_conversation_id():
            last_seen_conversation = self._fetch_last_seen_conversation()

            if last_seen_conversation:
                conversations = [last_seen_conversation]
                conversations = self._create_conversation_list(conversations)
                return conversations

        if not self.get_scoll_direction() and not self.get_conversation_id():

            last_seen = self._fetch_last_seen_conversation()

            if not last_seen:
                conversations = self._fetch_conversation_queryset()
                conversations = self._paged_queryset(conversations)
                conversations = self._create_conversation_list(conversations)
            else:

                upward_conversation = self._fetch_upward_conversation_queryset(10)
                downward_conversation = self._fetch_downward_conversation_queryset(10)
                # merging both conversations
                conversations = upward_conversation | downward_conversation
                conversations = conversations.order_by('id')
                conversations = self._create_conversation_list(conversations)

        else:
            if self.get_scoll_direction() and int(self.get_scoll_direction()) == 0:  # upward scroll
                upward_list = self._fetch_upward_conversation_queryset(list_size=20)
                conversations = reverse_conversations_for_upward_pagination(upward_list)

            elif self.get_scoll_direction() and self.get_scoll_direction() == 1:  # downward scroll
                conversations = self._fetch_downward_conversation_queryset(list_size=20)
            else:
                conversations = self._fetch_conversation_queryset()

            conversations = self._create_conversation_list(conversations)

        return conversations

