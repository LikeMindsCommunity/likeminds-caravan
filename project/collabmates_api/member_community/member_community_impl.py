from django.contrib.auth.models import User
from rest_framework.utils import json
from django.db.models import Q

from .constants import ACTIVE_USER_LIMIT
from .member_community_manager import MemberCommunityManager
from ..user_moderation_rights import check_admin_approve_right
from ..utility import pagination
from ..views import get_home_screen_community_actions, get_active_chatroom_member_images
from ..rest_api import CommunitySerializerV1
from ..serializers import get_user_profile
from ..static_files import REMOVED_USER_URL

from togther.models import Member_Engage, Community, Members, collabcardState

from utility.utils import create_notification_flag
from utility.time_utilities import TimeUtilities
from utility.states import member_states, card_types


class MemberCommunityImpl(MemberCommunityManager):

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

    def set_community_id(self, community_id: str) -> None:
        self.community_id = community_id

    def extract_member_communities(self, page: int) -> list:

        communities = self._find_member_communities(self.get_member_id())
        communities = self._paged_queryset(communities, page)
        communities = self._add_additional_information(communities)

        return communities


    @staticmethod
    def _find_member_communities(member_id: str) -> list:
        """
        TODO: move to model definition file
        """
        return Member_Engage.objects.filter(member_id=member_id).order_by('-order_time')

    @staticmethod
    def _paged_queryset(communities: list, page: int) -> list:
        result_per_page = 10
        return pagination(communities, page, paginate_by=result_per_page)

    def _add_additional_information(self, communities: list) -> list:
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

        return member_communities_additional_info

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

        if community.member_state == member_states.ADMIN:
            user = self._extract_user(self.get_member_id())

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

        if member_community['collabcard_unseen'] > 0 and \
                community.new_chatroom_users:
            member_community['new_chatroom_users'] = json.loads(community.new_chatroom_users)
        else:
            active_chatroom = MemberCommunityHelper.get_active_chatroom_member_images(
                community_instance=community.community_id, member_id=member_id)

            active_chatroom_count = active_chatroom['count']
            member_community['active_chatroom_count'] = active_chatroom_count
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

    def _fetch_member_community_data(self, community_id, member_id) -> list:
        return Members.objects.filter(member_id=member_id, community_id=community_id)

    def community_member_state(self) -> int:
        state = 0
        member_data = self._fetch_member_community_data(self.get_community_id(), self.get_member_id())

        if member_data:
            state = member_data[0].state

        return state


class MemberCommunityHelper:
    @staticmethod
    def get_active_chatroom_member_images(community_instance, member_id):

        current_time = TimeUtilities.current_time_in_sec()
        state_filter = collabcardState.objects.filter(
            community=community_instance, user=member_id, card__is_deleted=False
            ).exclude(card__type=card_types.CARD_INTRO).select_related('card').filter(Q(expiry_time=None) |
                                            Q(expiry_time__gt=current_time)
                                            ).order_by('-expiry_time', '-card')
        temp = {}
        member_list = []
        user_set = set()
        temp['count'] = state_filter.count()
        
        for data in state_filter:
            card_instance = data.card
            user_instance = card_instance.user
            user_id = user_instance.id

            if user_id not in user_set:
                member = MemberCommunityHelper.add_member_profile(user_instance, data.community)
                member_list.append(member)
                user_set.add(user_id)

            if len(member_list) > ACTIVE_USER_LIMIT:
                break

        temp['member_list'] = member_list
        
        return temp
    
    @staticmethod
    def add_member_profile(user_instance, community_instance):
        
        member_filter = Members.objects.filter(member_id=user_instance, community_id=community_instance)

        if member_filter.exists():
            image_url = user_instance.userinfo.image_link if user_instance.userinfo.image_link else ''
            member_instance = member_filter[0]

            if member_instance.image_url:
                image_url = member_instance.image_url
        else:
            image_url = REMOVED_USER_URL

        member = get_user_profile(user_instance, community_instance, send_profile=False)
        member['image_url'] = image_url
        
        return member
