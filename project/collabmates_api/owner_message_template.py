from celery import shared_task
from django.contrib.auth.models import User

from cms.models import MessageTemplate
from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import Community, Members, Collabcard, card_answers
from utility.states import card_types

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


@shared_task
def post_owner_message_template_in_intro_room(community_id, user_id, check_template=False):

    user_instance = User.get_user_or_raise_exception(user_id)
    community_instance = Community.get_community_or_raise_exception(community_id)

    # according to the current flow, only owner will have a message template,
    # which means a community will have only one template
    template = MessageTemplate.objects.filter(community=community_instance)

    if not template.exists():
        info_logger.info(f"post_owner_message_template_in_intro_room - user_id = {user_id}, community_id = {community_id}, returning at template existence check")
        return

    # has to get owner from records
    # because, owner can transfer his owner ship to other members of community
    owner_user_instance = Members.get_community_owner_user_instance_or_none(community_instance)
    # check if owner is present in community or not
    if owner_user_instance is None:
        info_logger.info(f"post_owner_message_template_in_intro_room - user_id = {user_id}, community_id = {community_id}, returning at owner existence check")
        return

    intro_filter = Collabcard.objects.filter(community=community_instance,
                                             user=user_instance,
                                             type=card_types.CARD_INTRO)
    # check if intro card exist or not for the joined user
    if not intro_filter.exists():
        info_logger.info(f"post_owner_message_template_in_intro_room - user_id = {user_id}, community_id = {community_id}, returning at intro room existence check")
        raise Exception("retrying")

    chatroom = intro_filter[0]

    if check_template:
        # check if template is already posted or not, if posted, return
        template_answer = card_answers.objects.filter(answer=template[0].message, card=chatroom)
        if template_answer.exists():
            info_logger.info(f"post_owner_message_template_in_intro_room - user_id = {user_id}, community_id = {community_id}, template already posted")
            return

    if chatroom.user.id == owner_user_instance.id:
        # if intro card is owner's, return
        info_logger.info(f"post_owner_message_template_in_intro_room - user_id = {user_id}, community_id = {community_id}, returning at owner id and chatroom creator id matching check")
        return

    from collabmates_api.chatroom.chatroom_impl import ChatroomImpl
    from collabmates_api.conversation.conversation_impl import ConversationImpl

    # creating a conversation on behalf of owner of community in new member's intro room
    conversation_req_body = {
        "chatroom_id": chatroom.id,
        "text": template[0].message
    }

    conversation_manager = ConversationImpl(owner_user_instance.id)
    conversation_response = conversation_manager.create_conversation(conversation_req_body,
                                                                     user_instance=owner_user_instance,
                                                                     chatroom_instance=chatroom)

    info_logger.info(
        f"post_owner_message_template_in_intro_room - user_id = {user_id}, community_id = {community_id}, response = {conversation_response}")

    # making the intro room of new member inactive for the owner
    chatroom_req_body = {
        "chatroom_id": chatroom.id,
        "value": False
    }

    chatroom_manager = ChatroomImpl(member_id=owner_user_instance.id)
    chatroom_response = chatroom_manager.set_chatroom_active_or_inactive(chatroom_req_body)

    info_logger.info(
        f"post_owner_message_template_in_intro_room inactivate chatroom for owner - user_id = {user_id}, community_id = {community_id}, chatroom_id = {chatroom.id}, response = {chatroom_response}")


@shared_task(bind=True, autoretry_for=(Exception,), default_retry_delay=60, max_retries=3)
def check_owner_template_posted(self, community_id, user_id):
    try:
        post_owner_message_template_in_intro_room(community_id, user_id, check_template=True)
    except Exception as exc:
        raise self.retry(exc=exc)
