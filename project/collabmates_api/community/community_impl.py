from django.contrib.auth.models import User

from collabmates_api.community.constants import MENU
from collabmates_api.rest_api import CommunitySerializerV1
from collabmates_api.user_moderation_rights import check_admin_edit_community_right
from collabmates_api.views import get_leave_community_text
from togther.models import Community
from collabmates_api.community.community_manager import CommunityManager
from collabmates_api.member_community.member_community_impl import MemberCommunityImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from collabmates_api.utilities.states import member_states

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

        return leave_community

    def _fetch_serialize_community(self, community_instance) -> []:
        return CommunitySerializerV1(community_instance).data


    def fetch_community(self, client_type) -> {}:

        community_instance = CommunityHelper.fetch_community_instance(self.get_community_id())
        response_context = dict()

        if not community_instance:
            response_context['error_message'] = "Invalid community_id"
            response_context['response_code'] = 400
            response_context['status'] = False

            return response_context

        user_instance = CommunityHelper.fetch_user_instance(self.get_member_id())

        if (client_type == "android" or client_type == "iOS") and not user_instance:
            response_context['error_message'] = "Invalid user_id"
            response_context['response_code'] = 400
            response_context['status'] = False

            return response_context

        community_member = MemberCommunityImpl(self.get_member_id(), self.get_community_id())
        state = community_member.fetch_member_state_of_community()
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



class CommunityHelper:

    def fetch_community_instance(community_id: str) -> object:
        community_instance = None
        try:
            community_instance = Community.objects.get(id=community_id)

            return community_instance
        except Exception as e:
            error_logger.error(e.args)

        return community_instance

    def fetch_user_instance(user_id: str) -> object:
        user_instance = None
        try:
            user_instance = User.objects.get(id=user_id)

            return user_instance
        except Exception as e:
            error_logger.error(e.args)

        return user_instance
