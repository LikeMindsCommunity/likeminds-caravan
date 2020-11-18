from django.contrib.auth.models import User
from rest_framework.utils import json

from togther.models import Member_Engage
from utility.states import member_states
from collabmates_api.landing_page.member_community_manager import MemberCommunityManager
from collabmates_api.serializers import CommunitySerializer
from collabmates_api.user_moderation_rights import check_admin_approve_right
from collabmates_api.views import get_home_screen_community_actions, get_active_chatroom_member_images


class MemberCommunityImpl(MemberCommunityManager):
    member_id = None
    communities = []

    def __init__(self, member_id: str):
        self.member_id = member_id

    def get_member_id(self) -> int:
        return self.member_id

    def set_member_id(self, member_id: str) -> None:
        self.member_id = member_id

    def get_communities(self) -> []:
        return self.communities

    def set_communities(self, communities: []) -> None:
        self.communities = communities

    def extract_member_communities(self) -> None:
        self.set_communities(self._get_member_communities(self.get_member_id()))
        self._add_additional_information()

    @staticmethod
    def _get_member_communities(member_id: int) -> {}:
        """TODO: move to model definition file"""
        return Member_Engage.objects.filter(member_id=member_id).order_by('-updated_at')

    def _add_additional_information(self) -> None:
        member_communities_additional_info = []

        for community in self.get_communities():
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
    def _community_serializer(community_id: int, member_id: int) -> {}:
        """TODO: move to model definition file"""
        return CommunitySerializer(community_id, current_user_id=member_id)

    def _add_admin_info(self, member_community: {}, community: {}) -> None:
        user = self._get_user_info(self.get_member_id())

        if community.member_state == member_states.ADMIN:

            member_community['pending_chatroom_count'] = community.pending_chatrooms
            member_community['open_reports_count'] = community.open_reports

            if check_admin_approve_right(user, community.community_id):
                member_community['pending_members_count'] = community.pending_members
            else:
                member_community['pending_members_count'] = 0

    @staticmethod
    def _get_user_info(member_id: int) -> {}:
        """TODO: move to model definition file"""
        return User.objects.get(id=member_id)

    def _add_community_actions(self, member_community: {}, community: {}) -> None:
        actions = get_home_screen_community_actions(community.community_id)
        self._add_admin_actions(actions, community)
        member_community['actions'] = actions

    @staticmethod
    def _add_admin_actions(actions: {}, community: {}) -> None:

        if community.member_state == member_states.ADMIN:
            management_tools = {
                'title': """Management tools""",
                'route': """route://management_tools?community_id=%s&community_name=%s""" % (
                    str(community['id']), community['name'])
            }
            actions.append(management_tools)

    @staticmethod
    def _add_unseen_count_info(member_community: {}, community: {}) -> None:
        if community.member_state == member_states.ADMIN or \
                community.member_state == member_states.MEMBER or \
                community.member_state == member_states.PROFILE_UNAVAILABLE:
            member_community['collabcard_unseen'] = community.last_unseen_count
        else:
            member_community['collabcard_unseen'] = 0

    @staticmethod
    def _add_active_chatroom_info(member_community: {}, community: {}, member_id: int) -> None:
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
    def _add_member_rights_info(member_community: {}, community: {}) -> None:
        member_community['member_right_states'] = json.loads(community.rights_list) \
            if community.rights_list \
            else []

    @staticmethod
    def _add_additional_keys(member_community: {}, community: {}) -> None:
        member_community['member_state'] = community.member_state
        member_community['click_state'] = community.click_state
