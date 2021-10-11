from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.functions import Lower

from rest_framework.utils import json
from rest_framework import status as status_codes

from external_services.caching.cache_impl import CacheImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.celery_tasks import update_chatroom_conversation_count_in_cache, \
    update_chatroom_conversation_creators_in_cache
from utility.constants import CONVERSATIONS_COUNT_CACHE_KEY, CONVERSATIONS_DISTINCT_CREATORS_KEY
from utility.number_utilities import NumberUtilities
from utility.string_utilities import StringUtilities
from .constants import *
from .member_community_manager import MemberCommunityManager

from ..chatroom_member.chatroom_member_impl import ChatroomMemberImpl
from ..raw_queries import (fetch_chatroom_polls, fetch_member_poll_votes, get_members_based_on_user_list_query,
                           get_community_introductions_based_on_user_list_query,
                           get_chatroom_count_based_on_community_list, get_distinct_chatroom_creator_list,
                           get_count_of_community_members_based_on_community_list)
from ..static_text import SECRET_CHATROOM_VERSION_CODE_IOS
from ..user.user_impl import UserImpl
from ..user_moderation_rights import check_admin_approve_right, check_admin_delete_right, \
    check_admin_edit_community_right
from ..utility import pagination
from ..views import get_home_screen_community_actions,\
    generate_internal_link_preview_for_conversation, get_latest_conversation_members
from ..rest_api import CommunitySerializerV1
from ..serializers import get_collabcard_files, \
    get_preview_for_url, is_draft_conversation, get_chatroom_instance, \
    get_draft_chatroom_instance, conversationSerializer
from ..static_files import REMOVED_USER_URL

from togther.models import (Member_Engage, Community, Members, collabcardState, ModelUtilities, removedMembers,
                            MemberPollVotes, Collabcard, card_answers, conversationEngage,
                            communityQuestions, CommunityUserDelete, communityRightsSettings)

from utility.utils import create_notification_flag, get_time_text_for_my_chatrooms
from utility.time_utilities import TimeUtilities
from utility.states import member_states, card_types, poll_types, deleted_members, question_states, \
    conversation_states, member_rights
from utility.exception_utilities import CustomException

error_logger = LoggingWrapper.get_instance()


class MemberCommunityImpl(MemberCommunityManager):
    member_id = None
    community_id = None
    device_id = None
    platform_code = None
    version_code = None

    def __init__(self, member_id: str, community_id: str, device_id: str = None, platform_code: str = "",
                 version_code: int = 0):
        self.member_id = member_id
        self.community_id = community_id
        self.device_id = device_id
        self.platform_code = platform_code
        self.version_code = version_code

    def get_member_id(self) -> str:
        return self.member_id

    def set_member_id(self, member_id: str) -> None:
        self.member_id = member_id

    def get_community_id(self) -> str:
        return self.community_id

    def set_community_id(self, community_id: str) -> None:
        self.community_id = community_id

    def get_platform_code(self) -> str:
        return self.platform_code

    def get_version_code(self) -> int:
        return self.version_code

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
        return Member_Engage.objects.filter(member_id=member_id).select_related('community_id', 'member_id').order_by(
            '-order_time')

    @staticmethod
    def _paged_queryset(communities: list, page: int, result_per_page=10) -> list:

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

        context = {"current_user_id": member_id, 'restrict_members_count': True}
        return CommunitySerializerV1(community_id, context=context, many=False).data

    def _add_admin_info(self, member_community: dict, community: {}) -> None:

        if community.member_state == member_states.ADMIN:
            user = community.member_id

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

    @staticmethod
    def has_promoter_management_rights(user_id, community_id):

        return check_admin_delete_right(user=user_id, community=community_id) \
               or check_admin_approve_right(user=user_id, community=community_id) \
               or check_admin_edit_community_right(user=user_id,
                                                   community=community_id)

    def _add_community_actions(self, member_community: dict, community: {}) -> None:
        actions = get_home_screen_community_actions(community.community_id)

        if community.member_state == member_states.ADMIN and \
                self.has_promoter_management_rights(self.get_member_id(), member_community['id']):
            self._add_admin_actions(member_community, actions)

        member_community['actions'] = actions

    @staticmethod
    def _add_admin_actions(member_community: dict, actions: list) -> None:

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

    def _add_member_rights_info(self, member_community: dict, community: {}) -> None:

        is_ios = self.get_platform_code() == "ios"

        if community.rights_list:
            rights_list = json.loads(community.rights_list)

            if is_ios and \
                    member_rights.MEMBER_RIGHT_CREATE_SECRET_ROOM in rights_list and \
                    self.get_version_code() <= SECRET_CHATROOM_VERSION_CODE_IOS:
                rights_list.remove(member_rights.MEMBER_RIGHT_CREATE_SECRET_ROOM)

        else:
            rights_list = []

        member_community['member_right_states'] = rights_list

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

    @staticmethod
    def add_chatroom_count_and_member_images(member_community: dict, community: {},
                                             member_id: str, community_chatroom_count_dict) -> None:

        if member_community['collabcard_unseen'] > 0 and \
                community.new_chatroom_users:
            member_community['new_chatroom_users'] = json.loads(community.new_chatroom_users)
        else:

            if community_chatroom_count_dict.get(community.community_id_id):
                chatroom_count = community_chatroom_count_dict.get(community.community_id_id)
            else:
                chatroom_count = 0

            member_community['chatroom_count'] = chatroom_count

            user_list = get_distinct_chatroom_creator_list(community.community_id_id, member_id)
            member_dict = MemberCommunityImpl.fetch_members_based_on_user_list(user_list, community.community_id)
            chatroom_users = MemberCommunityHelper.extract_member_tagging_data(member_dict)

            if chatroom_users:
                member_community['chatroom_users'] = chatroom_users

    @staticmethod
    def _add_members_count_in_home_communities(member_community, community_id, community_members_count_dict):

        members_count = community_members_count_dict.get(community_id)

        if members_count:
            member_community['members_count'] = members_count

        else:
            member_community['members_count'] = 0

    def _process_communities(self, community_queryset, community_id_list, user_instance) -> []:

        member_communities_additional_info = list()

        community_chatroom_count_dict = MemberCommunityHelper.fetch_chatroom_count_for_home(community_id_list,
                                                                                            user_instance.id)

        community_members_count_dict = MemberCommunityHelper.fetch_community_members_count(community_id_list)

        for community in community_queryset:
            member_community = self._community_serializer(community.community_id, self.get_member_id())
            self._add_members_count_in_home_communities(member_community,
                                                        community.community_id_id,
                                                        community_members_count_dict)
            self._add_admin_info(member_community, community)
            self._add_community_actions(member_community, community)
            self._add_unseen_count_info(member_community, community)
            self._add_member_rights_info(member_community, community)
            self._add_additional_keys(member_community, community)
            self.add_chatroom_count_and_member_images(member_community, community, self.get_member_id(),
                                                      community_chatroom_count_dict)
            member_communities_additional_info.append(member_community)

        return member_communities_additional_info

    def process_onboarding_communities(self, communities, community_id_list, user_instance) -> []:

        communities_list = []
        community_members_count_dict = MemberCommunityHelper.fetch_community_members_count(community_id_list)

        for community in communities:
            member_community = self._community_serializer(community.community_id, self.get_member_id())
            self._add_members_count_in_home_communities(member_community,
                                                        community.community_id_id,
                                                        community_members_count_dict)
            communities_list.append(member_community)

        return communities_list

    @staticmethod
    def compute_community_id_list_from_queryset(community_queryset):

        community_id_list = []

        for data in community_queryset:
            community_id_list.append(data.community_id_id)

        return community_id_list

    def fetch_home_communities(self, page, show_dm=False, is_cm=False, is_paid=False) -> {}:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'error_message': "Invalid user id", 'status': 400}

        communities = self._find_member_communities(self.get_member_id())
        community_ids_list = list(communities.values_list("community_id_id", flat=True))

        if is_cm and (is_cm == 'true'):
            cm_communities_filter = ModelUtilities.get_model_filter(Members,
                                                                    {"member_id": user_instance,
                                                                     "community_id__in": community_ids_list,
                                                                     "state": member_states.ADMIN})

            community_ids_list = list(cm_communities_filter.values_list("community_id_id", flat=True))

            communities = communities.filter(community_id__in=community_ids_list)

            total_communities_count = len(community_ids_list)

        if is_paid and (is_paid == 'true'):
            communities = communities.filter(community_id__is_paid=True)

            community_ids_list = list(communities.values_list("community_id_id", flat=True))

            total_communities_count = len(community_ids_list)

        if show_dm and (show_dm == 'true'):
            communities_with_dm_rights_list = ModelUtilities.get_model_filter(communityRightsSettings,
                                              {"community_id__in": community_ids_list,
                                               "right__state": member_rights.MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES})

            communities_with_dm_rights_list = communities_with_dm_rights_list.values_list("community_id", flat=True)

            communities = communities.filter(community_id__in=communities_with_dm_rights_list)

            total_communities_count = len(communities_with_dm_rights_list)

        else:
            total_communities_count = len(community_ids_list)

        community_queryset = self._paged_queryset(communities, page)
        community_id_list = self.compute_community_id_list_from_queryset(community_queryset)
        community_list = self._process_communities(community_queryset, community_id_list, user_instance)

        return {'your_communities': community_list, 'total_communities_count': total_communities_count}

    def fetch_community_chatrooms_queryset_with_web_scroll(self, pin_status, card_instance, limit_size=5) -> []:

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               user=self.get_member_id(),
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               card_id__pinning_time__lt=card_instance.pinning_time).select_related(
            'card', 'card__user').exclude(card__type__in=[card_types.CARD_INTRO,
                                                          card_types.CARD_EVENT,
                                                          card_types.CARD_PUBLIC_EVENT]).order_by('-card__pinning_time')[:limit_size]
        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               user=self.get_member_id(),
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               card_id__lt=card_instance.id).select_related('card',
                                                                                                            'card__user'). \
        exclude(card__type__in=[card_types.CARD_INTRO,
                                card_types.CARD_EVENT,
                                card_types.CARD_PUBLIC_EVENT]).order_by('-card_id')[:limit_size]

        return chatroom_queryset

    def fetch_community_chatrooms_queryset_with_last_seen_chatroom(self, pin_status, last_seen_id, limit_size=5) -> []:

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               user=self.get_member_id(),
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               card__id__gte=last_seen_id).select_related('card',
                                                                                                          'card__user').\
            exclude(card__type__in=[card_types.CARD_INTRO,
                                    card_types.CARD_EVENT,
                                    card_types.CARD_PUBLIC_EVENT]).order_by('card_id')[:limit_size]
        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               user=self.get_member_id(),
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               card__id__gte=last_seen_id).select_related('card',
                                                                                                          'card__user').\
            exclude(card__type__in=[card_types.CARD_INTRO,
                                    card_types.CARD_EVENT,
                                    card_types.CARD_PUBLIC_EVENT]).order_by('card_id')[:limit_size]

        return chatroom_queryset

    def fetch_community_chatrooms_queryset_without_last_seen(self, pin_status) -> []:

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user'). \
        exclude(card__type__in=[card_types.CARD_INTRO,
                                card_types.CARD_EVENT,
                                card_types.CARD_PUBLIC_EVENT]).order_by('card_id')
        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user'). \
        exclude(card__type__in=[card_types.CARD_INTRO,
                                card_types.CARD_EVENT,
                                card_types.CARD_PUBLIC_EVENT]).order_by('card_id')

        return chatroom_queryset

    def fetch_chatroom_queryset_for_web(self, pin_status):

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user'). \
        exclude(card__type__in=[card_types.CARD_INTRO,
                                card_types.CARD_EVENT,
                                card_types.CARD_PUBLIC_EVENT]).order_by('-card__pinning_time')
        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user'). \
        exclude(card__type__in=[card_types.CARD_INTRO,
                                card_types.CARD_EVENT,
                                card_types.CARD_PUBLIC_EVENT]).order_by('-card_id')

        return chatroom_queryset

    def last_seen_chatroom_query(self, pin_status) -> []:

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).exclude(
                card__type__in=[card_types.CARD_INTRO,
                                card_types.CARD_EVENT,
                                card_types.CARD_PUBLIC_EVENT]).only('card','state').order_by('card_id')
        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).exclude(
                card__type__in=[card_types.CARD_INTRO,
                                card_types.CARD_EVENT,
                                card_types.CARD_PUBLIC_EVENT]).only('card', 'state').order_by('card_id')

        last_seen_chatroom = None

        for data in chatroom_queryset:

            if data.state != 0:
                last_seen_chatroom = data

            else:
                break

        return last_seen_chatroom

    @staticmethod
    def extract_chatrooms_on_scroll(chatroom_id, scroll_direction, chatroom_queryset, limit_size=10) -> []:

        chatroom_list = []

        if scroll_direction == FEED_UPWARD_SCROLL:
            chatroom_list = chatroom_queryset.filter(card__lt=chatroom_id).order_by('-card_id')[:limit_size]
            chatroom_list = MemberCommunityHelper.reverse_queryset(chatroom_list)

        elif scroll_direction == FEED_DOWNWARD_SCROLL:
            chatroom_list = chatroom_queryset.filter(card__gt=chatroom_id)[:limit_size]

        return chatroom_list

    @staticmethod
    def extract_chatrooms_without_scroll(chatroom_queryset, limit_size=10) -> []:

        chatroom_list = chatroom_queryset[:limit_size]

        return chatroom_list

    @staticmethod
    def fetch_list_of_community_members(community_instance):

        member_list = \
            list(Members.objects.filter(community_id=community_instance).filter(Q(state=member_states.ADMIN)
                                                                                | Q(state=member_states.MEMBER)
                                                                                | Q(
                state=member_states.PROFILE_UNAVAILABLE)).values_list('member_id'
                                                                      , flat=True))

        return member_list

    @staticmethod
    def fetch_members_for_membership_expired(user_list, community_instance):

        membership_expired_dict = {user_id: False for user_id in user_list}

        membership_expired_filter = \
            ModelUtilities.get_model_filter(removedMembers, {'member__in': user_list,
                                                             'community': community_instance,
                                                             'removed_state': deleted_members.MEMBERSHIP_EXPIRED})
        for instance in membership_expired_filter:

            if membership_expired_dict.get(instance.member_id) is False:
                membership_expired_dict[instance.member_id] = instance

        return membership_expired_dict

    @staticmethod
    def fetch_members_based_on_user_list(user_list, community_instance, order_by_name=False,
                                         send_expired_info=True) -> {}:

        member_dict = {}
        membership_expired_dict ={}
        member_list = get_members_based_on_user_list_query(user_list, community_instance.id,
                                                           order_by_name=order_by_name)
        community_name = community_instance.name

        if send_expired_info:
            membership_expired_dict = MemberCommunityImpl.fetch_members_for_membership_expired(user_list,
                                                                                               community_instance)

        for data in member_list:

            if not member_dict.get(data['member_id']):
                member = {
                    'id': data['member_id'],
                    'name': data['name'],
                    'state': data['state'],
                    'is_owner': data['is_owner'],
                    'community_id': data['community_id'],
                    'route': MEMBER_COMMUNITY_PROFILE_ROUTE % (str(data['community_id']), str(data['member_id'])),
                    'created_at': data['created_at']
                }

                if member['state'] == member_states.ADMIN or \
                        member['state'] == member_states.MEMBER or \
                        member['state'] == member_states.PROFILE_UNAVAILABLE:
                    member['member_since'] = MEMBER_SINCE_TEXT % (community_name,
                                                                  TimeUtilities.convert_epoch_time_to_date_with_mon_day_year(
                                                                      data['created_at']))

                elif member['state'] == member_states.PENDING_MEMBER:
                    member['member_since'] = PENDING_MEMBER_TEXT % community_name

                if data['image_url']:
                    image_url = data['image_url']

                elif data['image_link']:
                    image_url = data['image_link']
                else:
                    image_url = ""

                member['image_url'] = image_url

                if data['custom_title'] and not data['custom_title'] == 'Member':
                    member['custom_title'] = data['custom_title']

                if membership_expired_dict.get(data['member_id']):
                    membership_expired_instance = membership_expired_dict[data['member_id']]
                    userinfo_instance = membership_expired_instance.member.userinfo
                    member['custom_intro_text'] = CUSTOM_INTRO_TEXT_MEMBERSHIP_EXPIRED
                    member['custom_click_text'] = CUSTOM_CLICK_TEXT_MEMBERSHIP_EXPIRED % \
                                                  (userinfo_instance.name,
                                                   TimeUtilities.convert_epoch_time_in_date(
                                                       membership_expired_instance.created_at))

                member_dict[data['member_id']] = member

        return member_dict

    @staticmethod
    def fetch_community_introductions_based_on_user_list(user_list, community_instance) -> {}:

        introduction_filter = ModelUtilities.get_model_filter(communityQuestions,
                                                              {'question_state': question_states.INTRODUCTION,
                                                               'community': community_instance})
        if introduction_filter:
            question_instance = introduction_filter[0]

            member_data = get_community_introductions_based_on_user_list_query(user_list,
                                                                               community_instance.id,
                                                                               question_instance.id)
            member_introduction_dict = dict()

            for data in member_data:
                member_dict = dict()
                member_dict['member_id'] = data[0]
                member_dict['community_id'] = data[1]
                member_dict['state'] = question_instance.question_state
                member_dict['value'] = data[2]
                member_dict['question_id'] = question_instance.id
                member_dict['is_hidden'] = question_instance.is_hidden
                member_dict['directory_fields'] = question_instance.field
                member_dict['question_title'] = data[3]
                member_introduction_dict[member_dict['member_id']] = member_dict

            return member_introduction_dict

        return {}

    @staticmethod
    def compute_user_id_list_of_chatroom_creators(chatroom_list) -> []:

        user_list = []
        user_set = set()

        for data in chatroom_list:
            user_id = data.card.user_id

            if user_id not in user_set:
                user_list.append(user_id)
                user_set.add(user_id)

        return user_list

    @staticmethod
    def compute_user_id_list_of_conversation_creators(card_instance) -> []:

        conversation_creator_list = []

        key = CONVERSATIONS_DISTINCT_CREATORS_KEY % str(card_instance.id)
        conversation_creator_dict = CacheImpl.get_cache(key)

        if conversation_creator_dict:
            conversation_creator_list = conversation_creator_dict['conversation_creator_list']

        else:

            conversation_filter = card_answers.objects \
                                      .filter(card=card_instance, state=conversation_states.ANSWER) \
                                      .filter(Q(attachment_count=0) |
                                              Q(attachments_uploaded=True)) \
                                      .distinct('user') \
                                      .order_by('user', '-id')[:5]

            for data in conversation_filter:
                user_id = data.user_id
                conversation_creator_list.append(user_id)

            update_chatroom_conversation_creators_in_cache({'chatroom_id': card_instance.id,
                                                            'conversation_creator_list': conversation_creator_list})

        return conversation_creator_list

    @staticmethod
    def create_removed_members_custom_text(instance, userinfo_instance):

        temp = {}

        created_time = TimeUtilities.convert_epoch_time_in_date(instance.created_at)
        remove_state = instance.removed_state

        if remove_state == deleted_members.LEFT:
            temp['custom_intro_text'] = CUSTOM_INTRO_TEXT_LEFT % created_time
            temp['custom_click_text'] = CUSTOM_CLICK_TEXT_LEFT % (userinfo_instance.name, created_time)

        elif remove_state == deleted_members.REMOVED:
            temp['custom_intro_text'] = CUSTOM_INTRO_TEXT_DELETED % created_time
            temp['custom_click_text'] = CUSTOM_CLICK_TEXT_DELETED % (userinfo_instance.name, created_time)

        elif remove_state == deleted_members.MEMBERSHIP_EXPIRED:
            temp['custom_intro_text'] = CUSTOM_INTRO_TEXT_MEMBERSHIP_EXPIRED
            temp['custom_click_text'] = CUSTOM_CLICK_TEXT_MEMBERSHIP_EXPIRED % (userinfo_instance.name, created_time)

        temp['remove_state'] = remove_state
        temp['removed_user_image_url'] = REMOVED_USER_URL

        return temp

    def compute_removed_user_context(self, user_instance, community_instance) -> {}:

        remove_filter = ModelUtilities.get_model_filter(removedMembers, {'community': community_instance,
                                                                         'member_id': user_instance})
        remove_member = {}

        userinfo_instance = user_instance.userinfo
        remove_member['id'] = userinfo_instance.user_id_id
        remove_member['name'] = userinfo_instance.name
        remove_member['image_url'] = userinfo_instance.image_link if userinfo_instance.image_link else ""

        if remove_filter:
            temp = self.create_removed_members_custom_text(remove_filter[0], userinfo_instance)
            remove_member['custom_intro_text'] = temp['custom_intro_text']
            remove_member['custom_click_text'] = temp['custom_click_text']
            remove_member['remove_state'] = temp['remove_state']
            remove_member['image_url'] = temp['removed_user_image_url']

        return remove_member

    def fetch_user_onboarding_communities_queryset(self) -> []:

        member_queryset = \
            Members.objects.filter(member_id=self.get_member_id(),
                                   has_onboarded=False).filter(Q(state=member_states.MEMBER)
                                                               | Q(
                state=member_states.PROFILE_UNAVAILABLE)).select_related('community_id'
                                                                         ).order_by('created_at')
        return member_queryset

    def fetch_feed(self, pin_status, chatroom_id=None, scroll_direction=None) -> {}:

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "Invalid community_id", 'status': 400}

        if not chatroom_id and not scroll_direction:

            last_seen_chatroom = self.last_seen_chatroom_query(pin_status)

            if not last_seen_chatroom:
                chatroom_queryset = self.fetch_community_chatrooms_queryset_without_last_seen(pin_status)
                chatroom_list = self.extract_chatrooms_without_scroll(chatroom_queryset, limit_size=5)

            else:
                last_seen_chatroom_id = last_seen_chatroom.card_id
                chatroom_list = self.fetch_community_chatrooms_queryset_with_last_seen_chatroom(pin_status,
                                                                                                last_seen_chatroom_id,
                                                                                                limit_size=5)
        else:

            chatroom_instance = Collabcard.get_chatroom_or_None(chatroom_id)

            if not chatroom_instance:
                return {'error_message': "Invalid chatroom id", 'status': 400}

            chatroom_queryset = self.fetch_community_chatrooms_queryset_without_last_seen(pin_status)
            chatroom_list = self.extract_chatrooms_on_scroll(chatroom_id, scroll_direction, chatroom_queryset,
                                                             limit_size=5)

        from ..chatroom_member.chatroom_member_impl import ChatroomMemberImpl

        chatroom_member_impl = ChatroomMemberImpl(member_id=self.get_member_id(), device_id=self.device_id)
        chatroom_context_list = chatroom_member_impl.process_chatroom_list(chatroom_list, community_instance)

        return {'chatrooms': chatroom_context_list}

    def fetch_feed_web(self, pin_status, chatroom_id=None, scroll_direction=None) -> {}:

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "Invalid community_id", 'status': 400}

        if not chatroom_id and not scroll_direction:
            chatroom_list = self.fetch_chatroom_queryset_for_web(pin_status)
            chatroom_list = chatroom_list[:5]
        else:
            chatroom_instance = Collabcard.get_chatroom_or_None(chatroom_id)

            if not chatroom_instance:
                return {'error_message': "Invalid chatroom id", 'status': 400}

            chatroom_list = self.fetch_community_chatrooms_queryset_with_web_scroll(pin_status, chatroom_instance,
                                                                                    intro_room_setting_enabled)
        from ..chatroom_member.chatroom_member_impl import ChatroomMemberImpl

        chatroom_member_impl = ChatroomMemberImpl(member_id=self.get_member_id(), device_id=self.device_id)
        chatroom_context_list = chatroom_member_impl.process_chatroom_list(chatroom_list, community_instance)

        return {'chatrooms': chatroom_context_list}

    @staticmethod
    def create_feed_actions(community_instance, pinned_top_bar) -> []:

        actions = []
        community_id = StringUtilities.get_string_from_integer(community_instance.id)
        community_name = community_instance.name

        INVITE_MEMBERS['route'] = INVITE_MEMBERS_ROUTE % community_id
        NEW_CHATROOM['route'] = NEW_CHATROOM_ROUTE % (community_id, community_name)
        DIRECTORY['route'] = DIRECTORY_ROUTE % (community_id, community_name)
        PINNED['route'] = PINNED_ROUTE % community_id
        COMMUNITY_DETAILS['route'] = COMMUNITY_DETAILS_ROUTE % community_id

        actions.append(INVITE_MEMBERS)
        actions.append(NEW_CHATROOM)
        actions.append(DIRECTORY)

        if pinned_top_bar:
            actions.append(PINNED)

        actions.append(COMMUNITY_DETAILS)

        return actions

    @staticmethod
    def create_pinned_chatrooms_header(community_instance) -> {}:

        pinned_top_bar = {}

        pinned_chatrooms = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                        'is_pinned': True, 'is_deleted': False}).\
            exclude(type__in=[card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]).\
            only('header').order_by('-pinning_time')

        if pinned_chatrooms:

            sub_title = ""
            count = 0

            for data in pinned_chatrooms:

                sub_title = sub_title + data.header + ", "
                count = count + 1

                if count == 5:
                    break

            pinned_top_bar['title'] = PINNED_TOP_BAR_TITLE
            pinned_top_bar['sub_title'] = sub_title[:-2]
            pinned_chatroom_count = pinned_chatrooms.count()

            pinned_top_bar['icon'] = PINNED_TOP_BAR_IMAGE
            pinned_top_bar['count'] = pinned_chatroom_count

        return pinned_top_bar

    def fetch_feed_meta(self) -> {}:

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "Invalid community id", 'status': 400}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'error_message': "Invalid user id", 'status': 400}

        feed_context = dict()
        pinned_top_bar = self.create_pinned_chatrooms_header(community_instance)

        if pinned_top_bar:
            feed_context['pinned_top_bar'] = pinned_top_bar

        actions = self.create_feed_actions(community_instance, pinned_top_bar)
        community = self._community_serializer(community_instance, self.get_member_id())
        feed_context['actions'] = actions
        feed_context['community'] = community

        return feed_context

    def fetch_chatroom_home(self, chatroom_id) -> {}:

        chatroom_instance = Collabcard.get_chatroom_or_None(chatroom_id)

        if not chatroom_instance:
            return {'error_message': "Invalid chatroom id", 'status': 400}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'error_message': "Invalid user id", 'status': 400}

        engage_filter = ModelUtilities.get_model_filter(conversationEngage, {'card': chatroom_instance,
                                                                             'user': user_instance})
        chatroom_home = dict()

        if engage_filter:

            engage_instance = engage_filter[0]

            card_instance = engage_instance.card
            draft_instance = engage_instance.draft

            member_id = user_instance.id

            if card_instance:
                chatroom_home['chatroom'] = get_chatroom_instance(card_instance, member_id, send_profile=False)

                context = {"current_user_id": member_id}
                chatroom_home['community'] = CommunitySerializerV1(card_instance.community, context=context,
                                                                   many=False).data
                chatroom_home['is_draft'] = False

            elif draft_instance:
                chatroom_home['chatroom'] = get_draft_chatroom_instance(draft_instance, member_id)

                context = {"current_user_id": user_instance.id}
                chatroom_home['community'] = CommunitySerializerV1(draft_instance.community, context=context,
                                                                   many=False).data
                chatroom_home['is_draft'] = True

            last_conversation = engage_instance.last_conversation

            if last_conversation and not is_draft_conversation(last_conversation, member_id):

                last_conversation_dict = conversationSerializer(last_conversation, current_user_id=member_id)

                preview = generate_internal_link_preview_for_conversation(last_conversation, member_id)

                if preview:
                    last_conversation_dict['preview'] = preview

                chatroom_home['last_conversation'] = last_conversation_dict

            chatroom_home['unseen_conversation_count'] = engage_instance.unseen_count
            chatroom_home['last_conversation_time'] = get_time_text_for_my_chatrooms(engage_instance.updated_at)

            last_conversation_member = engage_instance.last_conversation_member
            second_last_conversation_member = engage_instance.second_last_conversation_member
            last_conversation_user = engage_instance.last_conversation_user
            second_last_conversation_user = engage_instance.second_last_conversation_user

            conversation_users = get_latest_conversation_members(last_conversation_member,
                                                                 second_last_conversation_member,
                                                                 last_conversation_user,
                                                                 second_last_conversation_user)
            chatroom_home['conversation_users'] = conversation_users
            chatroom_home['member_right_states'] = json.loads(
                engage_instance.rights_list) if engage_instance.rights_list else []

            member_filter = Members.objects.filter(member_id=member_id,
                                                   community_id=engage_instance.community)
            if member_filter:
                chatroom_home['member_state'] = member_filter[0].state
            else:
                chatroom_home['member_state'] = member_states.GUEST

        return chatroom_home

    def pending_onboarding_communities(self, page_no, paginate_by) -> {}:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'error_message': "In-correct user id"}

        member_queryset = self.fetch_user_onboarding_communities_queryset()
        communities = ModelUtilities.paginate_queryset(member_queryset, page_no, paginate_by)
        community_id_list = self.compute_community_id_list_from_queryset(communities)
        communities = self.process_onboarding_communities(communities, community_id_list, user_instance)

        return {'communities': communities}

    def completed_onboarding_communites(self) -> {}:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'error_message': "In-correct user id"}

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "In-correct community id"}

        ModelUtilities.model_update(Members,
                                    {'community_id': community_instance,
                                     'member_id': user_instance},
                                    {'has_onboarded': True,
                                     'updated_at': TimeUtilities.current_time_in_sec()})

        return {'success': True}

    def fetch_deleted_communities(self) -> {}:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'error_message': "In-correct user id"}

        community_id_list = list(ModelUtilities.get_model_filter(CommunityUserDelete,
                                                                 {'user': user_instance}).values_list(
            'deleted_community_id',
            flat=True))
        return {'community_ids': community_id_list}

    def _add_emails_and_mobiles_to_member_profie_data(self, members_data, user_mobiles, user_emails):

        final_data = []

        for user_id, data in members_data.items():
            profile = data
            profile['mobiles'] = user_mobiles.get(user_id, [])
            profile['emails'] = user_emails.get(user_id, [])

            final_data.append(profile)

        return final_data

    def fetch_members_detail(self, page, page_size) -> dict:

        user_instance = User.get_user_or_raise_exception(self.get_member_id())
        community_instance = Community.get_community_or_raise_exception(self.get_community_id())

        is_promoter = Members.is_member_community_promoter(community=community_instance,
                                                           member=user_instance)

        if not is_promoter:
            response = {
                "success": False,
                "error_message": f"You are not the Owner/CM of the community {community_instance.name}"
            }
            raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

        total_member_count = Members.objects.filter(community_id=community_instance).count()

        user_id_list = list(Members.objects
                            .filter(community_id=community_instance)
                            .order_by(Lower('member_id__userinfo__name'))
                            .values_list("member_id_id", flat=True))

        user_id_list = ModelUtilities.paginate_queryset(user_id_list, page, page_size)

        members_data = self.fetch_members_based_on_user_list(user_id_list, community_instance, order_by_name=True)

        user_mobiles = UserImpl.fetch_user_verified_mobile_numbers(user_id_list)

        user_emails = UserImpl.fetch_user_verified_emails(user_id_list)

        final_data = self._add_emails_and_mobiles_to_member_profie_data(members_data, user_mobiles, user_emails)

        return {"success": True, "total_count": total_member_count, "members": final_data}

    def show_dm(self, req_body) -> {}:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {"success": False, "error_message": "Invalid User ID."}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, self.get_community_id())

        if not community_instance:
            return {"success": False, "error_message": "Invalid Community ID."}

        req_from = req_body.get("from")

        if not req_from:
            return {"success": False, "error_message": "Send the key 'from'."}

        member_id = req_body.get("member_id")

        if user_instance.id == member_id:
            return {"success": False, "error_message": "You cannot DM yourself."}

        user_admin = ModelUtilities.get_model_filter(Members,
                                                     {"member_id": user_instance,
                                                      "community_id": community_instance,
                                                      "state": member_states.ADMIN})

        dm_right_instance = ModelUtilities.get_model_filter(communityRightsSettings,
                                                            {"community": community_instance,
                                                             "right__state":
                                                                 member_rights.MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES})

        if req_from == "member_profile":

            member_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

            if not member_instance:
                return {"success": False, "error_message": "Invalid Member ID."}

            member_admin = ModelUtilities.get_model_filter(Members,
                                                           {"member_id": member_instance,
                                                            "community_id": community_instance,
                                                            "state": member_states.ADMIN})

            if user_admin.exists() and member_admin.exists():
                return {"success": True, "show_dm": False}

            elif (user_admin.exists() or member_admin.exists()) and dm_right_instance.exists():

                dm_chatroom_instance = ModelUtilities.get_model_filter(Collabcard,
                                                       {"user__in": [user_instance, member_instance],
                                                        "community_id": community_instance,
                                                        "chatroom_with_user__in": [user_instance, member_instance],
                                                        "is_private": True})

                if dm_chatroom_instance.exists():

                    return {
                        "success": True,
                        "cta": CTA_ROUTE_DIRECT_MESSAGES_MEMBER_PROFILE.format(dm_chatroom_instance[0].id,
                                                                               community_instance.id),
                        "show_dm": True
                    }

                else:
                    return {"success": True, "show_dm": False}

            else:
                return {"success": True, "show_dm": False}

        elif req_from == "community_detail":

            if (not user_admin.exists()) and dm_right_instance.exists():

                # Check if community has only one CM
                cm_instances = ModelUtilities.get_model_filter(Members,
                                                               {"community_id": community_instance,
                                                                "state": member_states.ADMIN})

                if len(cm_instances) == 1:
                    # Get chatroom of CM and User
                    chatroom_instance = ModelUtilities.get_model_filter(Collabcard,
                                            {"community": community_instance,
                                             "user__in": [cm_instances[0].member_id, user_instance],
                                             "chatroom_with_user__in": [cm_instances[0].member_id, user_instance],
                                             "is_private": True})

                    if chatroom_instance:
                        return {
                            "success": True,
                            "cta": CTA_ROUTE_DIRECT_MESSAGES_COMMUNITY_DETAIL_SINGLE_CM.format(chatroom_instance[0].id),
                            "show_dm": True
                        }

                return {
                    "success": True,
                    "cta": CTA_ROUTE_DIRECT_MESSAGES,
                    "show_dm": True
                }

            else:
                return {"success": True, "show_dm": False}

        else:
            return {"success": False, "error_message": "Invalid value of key 'from'."}


class MemberCommunityHelper:
    @staticmethod
    def get_active_chatroom_member_images(community_instance, member_id):

        current_time = TimeUtilities.current_time_in_sec()
        state_filter = collabcardState.objects.filter(
            community=community_instance, user=member_id, card__is_deleted=False, secret_chatroom_left=False,
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
    def fetch_chatroom_count_for_home(community_id_list, member_id) -> {}:

        community_count_dict = get_chatroom_count_based_on_community_list(community_id_list, member_id)

        return community_count_dict

    @staticmethod
    def fetch_community_members_count(community_id_list):
        community_members_count = get_count_of_community_members_based_on_community_list(community_id_list)

        return community_members_count

    @staticmethod
    def add_member_profile(user_instance, community_instance):

        member_filter = Members.objects.filter(member_id=user_instance, community_id=community_instance)

        userinfo_instance = user_instance.userinfo
        image_url = ""

        if member_filter:

            member_instance = member_filter[0]

            if member_instance.image_url:
                image_url = member_instance.image_url

            else:
                image_url = userinfo_instance.image_link if userinfo_instance.image_link else ''

        member = dict()
        member['id'] = userinfo_instance.user_id_id
        member['name'] = userinfo_instance.name
        member['image_url'] = image_url

        return member

    @staticmethod
    def reverse_queryset(queryset) -> []:

        query_list = []

        for data in queryset:
            query_list.append(data)

        query_list.reverse()
        return query_list

    @staticmethod
    def get_card_header(card_instance) -> str:

        if card_instance.header:
            header = card_instance.header
        else:

            if len(card_instance.title) <= 30:
                header = card_instance.title[:30]
            else:
                header = card_instance.title[:27] + "..."

        return header

    @staticmethod
    def extract_member_tagging_data(member_data, community_expired_dict=None) -> []:

        if community_expired_dict is None:
            community_expired_dict = {}

        member_list = []

        for key, value in member_data.items():

            if community_expired_dict.get(value['id']):
                continue

            temp = dict()
            temp['id'] = value['id']
            temp['name'] = value['name']
            temp['image_url'] = value['image_url']

            member_list.append(temp)

        return member_list

    @staticmethod
    def pre_compute_users_by_member_id_list(member_ids):
        user_filter = ModelUtilities.get_model_filter(User, {'id__in': member_ids})
        user_dict = {member_id: None for member_id in member_ids}

        for data in user_filter:

            if user_dict.get(data.id) is None:
                user_dict[data.id] = data

        return user_dict
