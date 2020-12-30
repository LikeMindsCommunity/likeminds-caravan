import json
from togther.models import Members, Collabcard, card_answers, collabcardState, conversationEngage
from django.contrib.auth.models import User
from django.db.models import Q
from collabmates_api.chatroom.chatroom_manager import ChatroomManager
from collabmates_api.serializers import get_preview_for_url,get_chatroom_instance,CommunitySerializer
from collabmates_api.views import adding_guest_in_chatroom, get_chatroom_actions, get_expiry_time_of_chatroom, \
    create_chatroom_state_instance, get_icons_states_of_chatroom_version_1, save_the_latest_conversation
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.states import chatroom_states, member_states

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()

class ChatroomImpl(ChatroomManager):

    member_id = None
    chatroom_id = None
    source_id = None
    aj = None

    def __init__(self, member_id: str, chatroom_id: str, source_id: str, aj: str):
        self.member_id = member_id
        self.chatroom_id = chatroom_id
        self.source_id = source_id
        self.aj = aj

    def get_member_id(self) -> str:
        return self.member_id

    def set_member_id(self, member_id: str) -> None:
        self.member_id = member_id

    def get_chatroom_id(self):
        return self.chatroom_id

    def set_chatroom_id(self,chatroom_id):
        self.chatroom_id = chatroom_id

    def get_source_id(self):
        return self.source_id

    def set_source_id(self,source_id):
        self.source_id = source_id

    def get_aj(self):
        return self.aj

    def set_aj(self,aj):
        self.aj = aj

    def _is_user_guest(self, card_instance):

        is_guest = False
        if card_instance:
            if self.get_aj() and self.get_source_id():
                is_guest = True

        return is_guest

    def _make_user_chatroom_guest(self, card_instance):
        guest_context = adding_guest_in_chatroom({}, card_instance, self.get_aj(), self.get_source_id(),
                                               card_instance.community.id, current_user_id=self.get_member_id())
        return guest_context

    def _fetch_chatroom_dict(self, card_instance):
        chatroom_obj = get_chatroom_instance(card_instance,self.get_member_id())

        return chatroom_obj

    def _fetch_chatroom_internal_link(self, card_instance):

        if card_instance.internal_link:
            try:
                preview = get_preview_for_url(self.get_member_id(), card_instance.internal_link,
                                                      community_instance=card_instance.preview_community,
                                                      chatroom_instance=card_instance.preview_chatroom,
                                                      send_preview_text=False)

                return preview

            except Exception as e:
                error_logger.error(e.args)

    def _fetch_total_response_count(self,card_instance):

        total_response_count = card_answers.objects.filter(card=card_instance, state=chatroom_states.ANSWER).count()

        return total_response_count

    def _fetch_card_status(self,chatroom_data):

        card_status = {
            'state': chatroom_data['state'],
            'mute_status': chatroom_data['mute_status'],
            'follow_status': chatroom_data['follow_status'],
            'attending_status': chatroom_data['attending_status'],
            'is_guest': chatroom_data['is_guest'],
            'type': chatroom_data['type'],
            'is_tagged': chatroom_data['is_tagged'],
            'active': chatroom_data['active']
        }

        return card_status

    def _fetch_chatroom_actions(self, card_instance, chatroom_data):

        card_status = self._fetch_card_status(chatroom_data)
        is_promoter = False
        is_child = False
        member_instance = Members.objects.filter(member_id=self.get_member_id(),
                                                 community_id=card_instance.community).filter(
            Q(state=member_states.ADMIN))

        if member_instance.exists():
            is_promoter = True
            parent_cm_list = member_instance[0].parent_cm_list
            parent_list = json.loads(parent_cm_list) if parent_cm_list else []
            is_child = str(card_instance.user.id) in parent_list

        is_card_creator = False

        if self.get_member_id() and int(self.get_member_id()) == card_instance.user.id:
            is_card_creator = True
        # sending the chatroom actions
        chatroom_actions = get_chatroom_actions(card_status, creator=is_card_creator, promoter=is_promoter,
                                                current_user_instance=self.get_member_id(),
                                                community_instance=card_instance.community, is_child=is_child
                                                )
        return chatroom_actions


    def _save_external_seen_in_chatroom_state(self, card_instance, user_instance):

        chatroom_state = collabcardState.objects.filter(card=card_instance, user=self.get_member_id())
        # if the user is seeing this chatroom from external link or notification
        if not chatroom_state.exists() and user_instance:
            expire_at = get_expiry_time_of_chatroom()
            create_chatroom_state_instance(card_instance, user_instance, state=0, external_seen=True,
                                           expire_at=expire_at,
                                           function_called="get_chatroom_internal_version_1")
        elif user_instance:
            instance = chatroom_state[0]
            if not instance.external_seen:
                instance.external_seen = True
                instance.expiry_time = get_expiry_time_of_chatroom()
                instance.save()

    def _fetch_icon_states_for_chatroom(self, card_instance, chatroom_data):

        icons = {}
        card_status = self._fetch_card_status(chatroom_data)
        icon_states = get_icons_states_of_chatroom_version_1(card_status, card_instance, self.get_member_id())
        icons['show_follow_telescope'] = icon_states['show_follow_telescope']
        icons['show_follow_auto_tag'] = icon_states['show_follow_auto_tag']
        icons['show_active'] = icon_states['show_active']

        return icons

    def _fetch_number_of_unread_messages(self, card_instance, user_instance):

        engage_filter = conversationEngage.objects.filter(card=card_instance,user=user_instance)
        unseen_count = 0
        if engage_filter.exists():
            unseen_count = engage_filter[0].unseen_count
        return unseen_count

    def _save_latest_conversation_on_screen(self, card_instance):

        save_the_latest_conversation(card_instance, self.get_member_id())

    def _fetch_count_of_chatroom_participants(self, card_instance):

        participant_count = collabcardState.objects.filter(follow_status=True, card=card_instance).count()

        return participant_count

    def fetch_chatroom(self):


        card_instance = ChatroomHelper.fetch_card_instance(self.get_chatroom_id())

        if not card_instance:
            context = {
                'error_message': "invalid chatroom id"
            }
            return context

        user_instance = ChatroomHelper.fetch_user_instance(self.get_member_id())
        chatroom_data = self._fetch_chatroom_dict(card_instance)

        if self._is_user_guest(card_instance):
            guest_context = self._make_user_chatroom_guest(card_instance)
            chatroom_data.update(guest_context)

        preview = self._fetch_chatroom_internal_link(card_instance)

        if preview:
            chatroom_data['preview'] = preview
        chatroom_icons = self._fetch_icon_states_for_chatroom(card_instance, chatroom_data)
        chatroom_data.update(chatroom_icons)

        chatroom_obj = {}
        chatroom_obj['chatroom'] = chatroom_data
        chatroom_obj['chatroom_actions'] = self._fetch_chatroom_actions(card_instance, chatroom_data)
        chatroom_obj['total_response_count'] = self._fetch_total_response_count(card_instance)
        chatroom_obj['community'] = ChatroomHelper.fetch_serialized_community(card_instance, user_instance, self.get_member_id())
        chatroom_obj['unread_messages'] = self._fetch_number_of_unread_messages(card_instance, user_instance)
        chatroom_obj['participant_count'] = self._fetch_count_of_chatroom_participants(card_instance)
        self._save_external_seen_in_chatroom_state(card_instance, user_instance)
        self._save_latest_conversation_on_screen(card_instance)

        return chatroom_obj

class ChatroomHelper:


    def fetch_card_instance(chatroom_id: str):

        card_instance = None
        try:
            card_instance = Collabcard.objects.get(id=chatroom_id)
            return card_instance

        except Exception as e:
            error_logger.error(e.args)
        return card_instance

    def fetch_user_instance(member_id: str):

        user_instance = None
        try:
            user_instance = User.objects.get(id=member_id)
            return user_instance
        except Exception as e:
            error_logger.error(e.args)

        return user_instance

    def fetch_serialized_community(card_instance: object, user_instance: object, current_user_id: str):

        context= CommunitySerializer(card_instance.community, current_user_id=current_user_id,
                                                   current_user_instance=user_instance)
        return context
    