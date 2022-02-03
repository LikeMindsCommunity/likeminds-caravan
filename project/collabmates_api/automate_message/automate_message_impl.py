from .automate_message_manager import AutomateMessageManager
from rest_framework import status as status_codes
from utility.states import message_template_chatroom_types, member_states, card_types
from utility.response_utilities import ResponseUtilities
from togther.models import ModelUtilities, MessageTemplate, Members, Collabcard
from collabmates_api.conversation.conversation_impl import ConversationImpl
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class AutomateMessageImpl(AutomateMessageManager):

    member_id = None
    community_id = None
    chatroom_type = None
    message = None

    def __init__(self, member_id: str, community_id: str, chatroom_type: int, message: str):
        self.member_id = member_id
        self.community_id = community_id
        self.chatroom_type = chatroom_type
        self.message = message

    def get_member_id(self) -> str:
        return self.member_id

    def get_community_id(self) -> str:
        return self.community_id

    def get_chatroom_type(self) -> int:
        return self.chatroom_type

    def get_message(self) -> str:
        return self.message

    def add_template(self) -> dict:

        message_template_instances = ModelUtilities.get_model_filter(
            MessageTemplate, {'community_id': self.get_community_id(), 'chatroom_type': self.get_chatroom_type()})

        if not message_template_instances:
            try:
                template = MessageTemplate.objects.create(community_id=self.get_community_id(),
                                                          message=self.get_message(),
                                                          chatroom_type=self.get_chatroom_type(),
                                                          cm_id=self.get_member_id())

                template.save()

            except:
                error_logger.error('error creating message template in api/automate_message/template')
                return ResponseUtilities.get_impl_error_context('error while creating template',
                                                                status_codes.HTTP_400_BAD_REQUEST)

        else:

            message_template_instance = message_template_instances[0]

            message_template_instance.message = self.get_message()
            message_template_instance.cm_id = self.get_member_id()

            message_template_instance.save()

        return {'success': True}

    def send_custom_message(self) -> dict:

        member_ids = list(ModelUtilities.get_model_filter(
            Members, {'community_id_id': self.get_community_id()}).exclude(state=member_states.ADMIN).values_list(
            'member_id_id', flat=True))

        if self.get_chatroom_type() == message_template_chatroom_types.DM_CHATROOM:

            # create dm message for all the members
            dm_chat_rooms = ModelUtilities.get_model_filter(Collabcard, {'type': card_types.CARD_DIRECT_MESSAGE,
                                                                         'is_private': True,
                                                                         'user_id': self.get_member_id(),
                                                                         'chatroom_with_user_id__in': member_ids})

            for chatroom in dm_chat_rooms:
                ConversationImpl.create_conversation_for_internal_use(self.get_member_id(),
                                                                      chatroom.id,
                                                                      self.get_message())

        return {'success': True}
