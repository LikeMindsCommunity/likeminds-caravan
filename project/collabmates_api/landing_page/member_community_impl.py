from django.contrib.auth.models import User
from rest_framework.utils import json

from togther.models import Member_Engage, Community
from utility.states import member_states
from collabmates_api.landing_page.member_community_manager import MemberCommunityManager
from collabmates_api.serializers import CommunitySerializer
from collabmates_api.user_moderation_rights import check_admin_approve_right
from collabmates_api.utility import pagination
from collabmates_api.views import get_home_screen_community_actions, get_active_chatroom_member_images
from utility.utils import create_notification_flag
from collabmates_api.rest_api import CommunitySerializerV1


class MemberCommunityImpl(MemberCommunityManager):
    member_id = None
    page = None
    communities = None

    def __init__(self, member_id: str, page: int):
        self.member_id = member_id
        self.page = page
        self.communities = list()

    def get_member_id(self) -> str:
        return self.member_id

    def set_member_id(self, member_id: str) -> None:
        self.member_id = member_id

    def get_page(self) -> int:
        return self.page

    def set_page(self, page: int) -> None:
        self.page = page

    def get_communities(self) -> list:
        return self.communities

    def set_communities(self, communities: list) -> None:
        self.communities = communities

    def extract_member_communities(self) -> None:
        self._send_app_install_notification(self.get_member_id())

        communities = self._find_member_communities(self.get_member_id())
        communities = self._paged_queryset(communities, self.get_page())

        self._add_additional_information(communities)

    @staticmethod
    def _send_app_install_notification(member_id: str) -> None:
        """
        TODO: move to notification module
        """
        """
        event when user installed the app
        """

        notification_list = [
            'mail_has_installed_app'
        ]
        create_notification_flag(member_id, notification_list, card_id=None, community_id=None, flag=False)

    @staticmethod
    def _find_member_communities(member_id: str) -> list:
        """
        TODO: move to model definition file
        """
        return Member_Engage.objects.filter(member_id=member_id).order_by('-updated_at')

    @staticmethod
    def _paged_queryset(communities: list, page: int):
        result_per_page = 10
        return pagination(communities, page, paginate_by=result_per_page)

    def _add_additional_information(self, communities: list) -> None:
        member_communities_additional_info = list()

        for community in communities:
            member_community = self._community_serializer(community.community_id, self.get_member_id())

            self._add_admin_info(member_community, community)
            self._add_community_actions(member_community, community)
            self._add_unseen_count_info(member_community, community)
            self._add_active_chatroom_info(member_community, community, self.get_member_id())
            self._add_member_rights_info(member_community, community)
            self._add_additional_keys(member_community, community)

            member_communities_additional_info.append(member_community)

        self.set_communities(member_communities_additional_info)

    @staticmethod
    def _community_serializer(community_id: int, member_id: str) -> dict:
        """
        TODO: move to model definition file
        """
        if not isinstance(community_id, Community):
            community_id = Community.objects.get(pk=community_id)

        context = {"current_user_id": member_id}
        return CommunitySerializerV1(community_id, context=context, many=False).data

    def _add_admin_info(self, member_community: dict, community: {}) -> None:
        user = self._extract_user(self.get_member_id())

        if community.member_state == member_states.ADMIN:

            member_community['pending_chatroom_count'] = community.pending_chatrooms
            member_community['open_reports_count'] = community.open_reports

            if check_admin_approve_right(user, community.community_id):
                member_community['pending_members_count'] = community.pending_members
            else:
                member_community['pending_members_count'] = 0

    @staticmethod
    def _extract_user(member_id: str) -> {}:
        """
        TODO: move to model definition file
        """
        return User.objects.get(id=member_id)

    def _add_community_actions(self, member_community: dict, community: {}) -> None:
        actions = get_home_screen_community_actions(community.community_id)
        self._add_admin_actions(member_community, actions, community)
        member_community['actions'] = actions

    @staticmethod
    def _add_admin_actions(member_community: dict, actions: list, community: {}) -> None:

        if community.member_state == member_states.ADMIN:
            management_tools = {
                'title': """Management tools""",
                'route': """route://management_tools?community_id=%s&community_name=%s""" % (
                    str(member_community['id']), member_community['name'])
            }
            actions.append(management_tools)

    @staticmethod
    def _add_unseen_count_info(member_community: dict, community: {}) -> None:
        if community.member_state == member_states.ADMIN or \
                community.member_state == member_states.MEMBER or \
                community.member_state == member_states.PROFILE_UNAVAILABLE:
            member_community['collabcard_unseen'] = community.last_unseen_count
        else:
            member_community['collabcard_unseen'] = 0

    @staticmethod
    def _add_active_chatroom_info(member_community: dict, community: {}, member_id: str) -> None:
        active_chatroom = get_active_chatroom_member_images(community_instance=community.community_id,
                                                            member_id=member_id)
        active_chatroom_count = active_chatroom['count']
        member_community['active_chatroom_count'] = active_chatroom_count

        if member_community['collabcard_unseen'] > 0 and \
                community.new_chatroom_users:
            member_community['new_chatroom_users'] = json.loads(community.new_chatroom_users)
        else:
            active_chatroom_users = active_chatroom['member_list']
            if active_chatroom_users:
                member_community['active_chatroom_users'] = active_chatroom_users

    @staticmethod
    def _add_member_rights_info(member_community: dict, community: {}) -> None:
        member_community['member_right_states'] = json.loads(community.rights_list) \
            if community.rights_list \
            else []

    @staticmethod
    def _add_additional_keys(member_community: dict, community: {}) -> None:
        member_community['member_state'] = community.member_state
        member_community['click_state'] = community.click_state
