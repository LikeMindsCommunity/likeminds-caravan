from django.contrib.auth.models import User

from collabmates_api.community.constants import MENU
from collabmates_api.rest_api import CommunitySerializerV1
from collabmates_api.user_moderation_rights import check_admin_edit_community_right
from collabmates_api.views import get_leave_community_text
from django.db.models import Q, F
from togther.models import Community, Userinfo, Collabcard, Members, ModelUtilities, CommunityUserDelete, \
    card_answers, collabcardState, Member_Engage, communityAnswers, communityQuestions
from collabmates_api.community.community_manager import CommunityManager
from collabmates_api.member_community.member_community_impl import MemberCommunityImpl, MemberCommunityHelper
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.states import member_states, card_types
from utility.time_utilities import TimeUtilities

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class CommunityImpl(CommunityManager):
    member_id = None
    community_id = None

    def __init__(self, member_id: str, community_id: str):

        self.member_id = member_id
        self.community_id = community_id

    def get_member_id(self) -> str:
        return self.member_id

    def set_member_id(self, member_id: str) -> None:
        self.member_id = member_id

    def get_community_id(self) -> str:
        return self.community_id

    def set_community_id(self, community_id) -> None:
        self.community_id = community_id

    def _community_menu_options(self, state, community_instance) -> []:

        menu = []
        if state == member_states.ADMIN:
            user_instance = CommunityHelper.fetch_user_instance(self.get_member_id())

            menu = MENU['promoter'].copy()
            has_right = check_admin_edit_community_right(user_instance, community_instance)

            if not has_right:
                del menu[3]

        elif state == member_states.PENDING_MEMBER:
            menu = MENU['pending_member'].copy()

        elif state == member_states.MEMBER or state == member_states.PROFILE_UNAVAILABLE:
            menu = MENU['member'].copy()

        return menu

    def _is_leave_community_blocked(self, state) -> bool:
        block_leave_community = False

        if state == member_states.ADMIN:
            block_leave_community = True

        elif state == member_states.PENDING_MEMBER:
            block_leave_community = True

        elif state == member_states.GUEST:
            block_leave_community = True

        return block_leave_community

    def _leave_community_object(self) -> {}:
        leave_community_popup = {}
        leave_community = get_leave_community_text()
        leave_community_popup['leave_community_title'] = leave_community[0]
        leave_community_popup['leave_community_sub_title'] = leave_community[1]
        leave_community_popup['leave_community_positive_title'] = leave_community[2]
        leave_community_popup['leave_community_negative_title'] = leave_community[3]

        return leave_community_popup

    def _fetch_serialize_community(self, community_instance) -> []:
        return CommunitySerializerV1(community_instance).data

    def _fetch_queryset_of_community_chatrooms(self):

        return Collabcard.objects.filter(community=self.get_community_id(),
                                         is_pending=False,
                                         is_deleted=False,
                                         is_secret=False).filter(~Q(type=card_types.CARD_INTRO)).order_by('-id')

    def _compute_chatroom_creator_list(self, queryset):

        user_list = []

        for data in queryset:
            user_list.append(data.user_id)

        return user_list

    @staticmethod
    def create_chatroom_object_for_community_detail(chatroom_instance) -> {}:

        chatroom_context = dict()
        chatroom_context['id'] = chatroom_instance.id
        chatroom_context['title'] = chatroom_instance.title
        chatroom_context['header'] = chatroom_instance.header
        chatroom_context['community_id'] = chatroom_instance.community_id
        chatroom_context['type'] = chatroom_instance.type
        chatroom_context['date'] = TimeUtilities.convert_epoch_time_in_date(chatroom_instance.date_epoch)

        return chatroom_context

    @staticmethod
    def create_chatroom_creator_context(member_dict, chatroom_instance):

        if chatroom_instance.user_id in member_dict:
            member_context = member_dict.get(chatroom_instance.user_id)

        else:
            userinfo_instance = chatroom_instance.user.userinfo
            member_context = {
                'id': userinfo_instance.user_id_id,
                'name': userinfo_instance.name,
                'image_url': userinfo_instance.image_link
            }

        return member_context

    def _compute_chatroom_list_based_on_query_set(self, community_instance, queryset) -> []:

        chatroom_list = []

        chatroom_creator_list = self._compute_chatroom_creator_list(queryset)
        member_dict = MemberCommunityImpl.fetch_members_based_on_user_list(chatroom_creator_list, community_instance)

        for chatroom_instance in queryset:
            chatroom_context = self.create_chatroom_object_for_community_detail(chatroom_instance)

            member_context = self.create_chatroom_creator_context(member_dict, chatroom_instance)

            chatroom_context['member'] = member_context

            chatroom_list.append(chatroom_context)

        return chatroom_list

    def fetch_community(self, client_type) -> {}:

        community_instance = CommunityHelper.fetch_community_instance(self.get_community_id())
        response_context = dict()

        if not community_instance:
            response_context['error_message'] = "Invalid community_id"
            response_context['response_code'] = 400
            response_context['status'] = False

            return response_context

        user_instance = CommunityHelper.fetch_user_instance(self.get_member_id())

        if (client_type == "an" or client_type == "ios") and not user_instance:
            response_context['error_message'] = "Invalid user_id"
            response_context['response_code'] = 400
            response_context['status'] = False

            return response_context

        community_member = MemberCommunityImpl(self.get_member_id(), self.get_community_id())
        state = community_member.community_member_state()
        community_instance = CommunityHelper.fetch_community_instance(self.get_community_id())
        block_leave_community = self._is_leave_community_blocked(state)
        community_context = {}

        if not block_leave_community:
            leave_community = self._leave_community_object()
            community_context['leave_community'] = leave_community

        menu = self._community_menu_options(state, community_instance)

        if menu:
            community_context['menu'] = menu

        community_serialized_instance = self._fetch_serialize_community(community_instance)
        community_context.update(community_serialized_instance)
        response_context['community_context'] = community_context
        response_context['response_code'] = 200
        response_context['status'] = True

        return response_context

    def fetch_chatroom_feed(self, size) -> {}:

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "In-correct community_id"}

        userinfo_instance = Userinfo.get_userinfo_or_None(self.get_member_id())

        if not userinfo_instance:
            return {'error_message': "In-correct user id"}

        community_chatroom_queryset = self._fetch_queryset_of_community_chatrooms()

        response_context = dict()
        response_context['total_chatrooms'] = community_chatroom_queryset.count()

        sliced_queryset = community_chatroom_queryset[:size]
        chatroom_list = self._compute_chatroom_list_based_on_query_set(community_instance, sliced_queryset)

        response_context['chatroom_list'] = chatroom_list

        return response_context

    def _set_community_delete_relation_for_users(self, community_instance):

        community_members = ModelUtilities.get_model_filter(Members, {'community_id':
                                                                          community_instance}).select_related(
            'member_id')

        for data in community_members:
            user_instance = data.member_id

            CommunityUserDelete.create_instance({'user_instance': user_instance,
                                                 'community_id': community_instance.id})

    def _set_deleted_by_for_community_chatrooms_and_conversations(self, community_instance):

        card_list = list(ModelUtilities.get_model_filter(Collabcard, {'preview_community':
                                                                          community_instance}).values_list('id',
                                                                                                           flat=True))

        if card_list:
            Collabcard.objects.filter(preview_community=community_instance).update(is_deleted=True, preview_type=None,
                                                                                   internal_link=None,
                                                                                   deleted_by_user=F('user'))

            ModelUtilities.get_model_filter(
                collabcardState, {'card__in': card_list}
            ).update(updated_at=TimeUtilities.current_time_in_sec())

        card_answers.objects.filter(
            preview_community=community_instance).update(preview_type=None,
                                                         internal_link=None,
                                                         deleted_by_user=F('user'),
                                                         last_updated=TimeUtilities.current_time_in_milliseconds())

    def _delete_community_relationships(self, community_instance):
        ModelUtilities.delete_record_in_model(Community, {'id': community_instance.id})

    def delete_community(self) -> {}:

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'success': False, 'error_message': "Invalid community id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        owner_instance = Members.is_member_community_owner(community_instance, user_instance)

        if not owner_instance:
            return {'success': False, 'error_message': "You are not the owner of community."}

        self._set_community_delete_relation_for_users(community_instance)
        self._set_deleted_by_for_community_chatrooms_and_conversations(community_instance)
        self._delete_community_relationships(community_instance)

        return {'success': True}


class CommunityHelper:
    
    @staticmethod
    def fetch_community_instance(community_id: str) -> object:
        community_instance = None
        try:
            community_instance = Community.objects.get(id=community_id)

            return community_instance
        except Exception as e:
            error_logger.error(e.args)

        return community_instance

    @staticmethod
    def fetch_user_instance(user_id: str) -> object:
        user_instance = None
        try:
            user_instance = User.objects.get(id=user_id)

            return user_instance
        except Exception as e:
            error_logger.error(e.args)

        return user_instance
