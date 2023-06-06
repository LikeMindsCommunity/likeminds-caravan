import math

from django.contrib.auth.models import User
from django.db.models import Q, When, Case
from django.db.models.functions import Lower
from rest_framework import status as status_codes
from rest_framework.utils import json

from external_services.caching.cache_impl import CacheImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import (Member_Engage, Community, Members, collabcardState, ModelUtilities, removedMembers,
                            Collabcard, card_answers, conversationEngage, communityQuestions, CommunityUserDelete,
                            communityRightsSettings, CommunitySettings, communityAnswers, questionFilters,
                            Card_Attachment, CommunityDirectMessageSettings, userMemberRights, Userinfo, SDKClientUsersInfo)
from collabmates_api.sdk.models import (SdkClient)
from utility.celery_tasks import update_chatroom_conversation_creators_in_cache, set_levels_on_ctc_celery, \
    update_multiple_previews_in_chatroom, set_level_click_state, create_member_dm_chatroom, \
    update_community_pin_chatrooms_list_in_cache, update_preview_for_account_image_change
from utility.constants import CONVERSATIONS_DISTINCT_CREATORS_KEY, CREATE_INTRO_TEXT_ADMIN, CREATE_INTRO_TEXT_MEMBER, \
    CUSTOM_CLICK_TEXT
from utility.exception_utilities import CustomException
from utility.states import member_states, card_types, deleted_members, question_states, \
    conversation_states, member_rights, community_setting_types, SyncTypes, api_version_headers, \
    community_dm_settings_state_types, community_dm_settings_duration_types, dm_icon_from_states, get_started_types, \
    api_types, access_types, feed_order_types, DMFabShowList

from utility.string_utilities import StringUtilities
from utility.time_utilities import TimeUtilities
from utility.number_utilities import NumberUtilities
from utility.utils import (get_time_text_for_my_chatrooms, is_version_code_supported_for_intro_room,
                           create_notification_flag, fetch_notification_flag)
from utility.cache_keys import (COMMUNITY_PINNED_CHATROOMS_LIST_CACHE_KEY)
from .constants import *
from .member_community_view_helper import MemberCommunityViewHelper
from ..community.constants import ANSWER_PRIVACY_PUBLIC_VALUE, ANSWER_PRIVACY_KEY, ANSWER_PRIVACY_PRIVATE_VALUE, \
    DIRECTORY_QUESTIONS_V2_ANSWER_KEY, DIRECTORY_QUESTIONS_V2_QUESTION_ID_KEY
from ..sync.model_update import update_models_for_syncing_apis
from ..upload_attachments import save_chatroom_attachments
from .member_community_manager import MemberCommunityManager
from ..raw_queries import (get_members_based_on_user_list_query,
                           get_community_introductions_based_on_user_list_query,
                           get_chatroom_count_based_on_community_list, get_distinct_chatroom_creator_list,
                           get_count_of_community_members_based_on_community_list,
                           get_card_ids_to_exclude_based_on_cohort_access,
                           get_ordered_card_id_on_the_basis_of_message_count,
                           get_ordered_card_id_on_the_basis_last_message,
                           get_ordered_card_id_on_the_basis_of_participants_count,
                           check_user_has_member_can_initiate_dm_right, get_dm_chatrooms_of_user,
                           get_last_conversation_id_corresponding_to_chatrooms_list,
                           get_ordered_card_id_on_the_basis_newest_chatroom,
                           fetch_user_communities_sorted_by_order_time,
                           get_ordered_card_id_on_the_basis_of_message_count_v2,
                           get_ordered_card_id_on_the_basis_last_message_v2,
                           get_ordered_card_id_on_the_basis_of_participants_count_v2,
                           get_ordered_card_id_on_the_basis_newest_chatroom_v2,
                           get_chatrooms_of_user_with_follow_status,
                           get_conversation_users_against_chatrooms_list,
                           get_latest_conversations_against_chatrooms_list,
                           get_user_chatroom_status)
from ..rest_api import CommunitySerializerV1, CommunityAnswersSerializer, CommunityQuestionsSerializerV2, \
    get_error_context, CommunityDMSettingsSerializer, MemberNotificationFlagSerializer, SDKClientUsersInfoSerializer
from ..serializers import is_draft_conversation, get_chatroom_instance, get_draft_chatroom_instance, \
    conversationSerializer, get_members_profile
from ..static_files import REMOVED_USER_URL, ICONS
from ..static_text import SECRET_CHATROOM_VERSION_CODE_IOS, MEMBER_PROFILE_MENU_ITEMS, COMMUNITY_LEVEL_3_TEXT, \
    IMAGE_URLS_FOR_QUESTION_TITLES, CREATE_COMMUNITY_QUESTION_NAME_TITLE
from ..user.user_impl import UserImpl
from ..user_moderation_rights import check_admin_approve_right, check_admin_delete_right, \
    check_admin_edit_community_right, check_all_member_rights, check_admin_view_contact_right, \
    check_admin_add_community_managers_right, check_admin_moderate_feed_and_comments_right, \
    check_member_create_post_right, check_member_comment_and_reply_right
from ..utility import pagination, single_community_view_version_check, create_chatroom_revamp_version_check, \
    m2cm_v2_version_check
from utility.response_utilities import ResponseUtilities
from utility.validation_utilities import ValidationUtilities
from ..views import get_home_screen_community_actions, generate_internal_link_preview_for_conversation, \
    get_latest_conversation_members, post_introduction_card_for_community, update_community_get_started

from collabmates_api.search.sync import ElasticSearchSync

error_logger = LoggingWrapper.get_instance()


class MemberCommunityImpl(MemberCommunityManager):
    member_id = None
    community_id = None

    def __init__(self, member_id: str, community_id: str, device_id: str = None, platform_code: str = "",
                 version_code: int = 0, api_key: str = None):
        self.member_id = member_id
        self.community_id = community_id
        self.device_id = device_id
        self.platform_code = platform_code
        self.version_code = version_code
        self.api_key = api_key

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

    def get_device_id(self) -> str:
        return self.device_id

    def get_api_key(self) -> str:
        return self.api_key

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

        if member_community.get('is_paid') and single_community_view_version_check(self.get_platform_code(),
                                                                                   self.get_version_code()):
            self._add_subscription_action(member_community['id'], actions)

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
    def _add_subscription_action(community_id: str, actions: list) -> None:
        subscription_action = SUBSCRIPTION_ACTION_DICT
        subscription_action['route'] = subscription_action['route'].format(community_id)

        actions.append(subscription_action)

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
            user_list = get_distinct_chatroom_creator_list(community.community_id_id, member_id)
            member_dict = MemberCommunityImpl.fetch_members_based_on_user_list(user_list, community.community_id)
            chatroom_users = MemberCommunityHelper.extract_member_tagging_data(member_dict)

            if chatroom_users:
                member_community['chatroom_users'] = chatroom_users

        if community_chatroom_count_dict.get(community.community_id_id):
            chatroom_count = community_chatroom_count_dict.get(community.community_id_id)
        else:
            chatroom_count = 0

        member_community['chatroom_count'] = chatroom_count

    @staticmethod
    def _add_members_count_in_home_communities(member_community, community_id, community_members_count_dict):

        members_count = community_members_count_dict.get(community_id)

        if members_count:
            member_community['members_count'] = members_count

        else:
            member_community['members_count'] = 0

    def _process_communities(self, community_queryset, community_id_list, user_instance,
                             is_chatroom_revamp=False) -> []:

        member_communities_additional_info = list()

        community_chatroom_count_dict = MemberCommunityHelper.fetch_chatroom_count_for_home(
            community_id_list, user_instance.id, is_chatroom_revamp)

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

        member_engage_ids = fetch_user_communities_sorted_by_order_time(self.get_member_id(),
                                                                        community_id=self.get_community_id())
        communities = MemberCommunityHelper.get_ordered_home_communities_list_based_on_engage_ids(member_engage_ids)
        community_ids_list = list(communities.values_list("community_id_id", flat=True))
        total_communities_count = len(community_ids_list)

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

        is_chatroom_revamp = create_chatroom_revamp_version_check(platform_code=self.get_platform_code(),
                                                                  version_code=self.get_version_code())

        community_queryset = self._paged_queryset(communities, page)
        community_id_list = self.compute_community_id_list_from_queryset(community_queryset)
        community_list = self._process_communities(community_queryset, community_id_list, user_instance,
                                                   is_chatroom_revamp)

        return {
            'success': True,
            'your_communities': community_list,
            'total_communities_count': total_communities_count
        }

    def fetch_community_chatrooms_queryset_with_web_scroll(self, pin_status, card_instance,
                                                           intro_room_settings_enabled, excluded_card_ids,
                                                           limit_size=5) -> []:

        excluded_card_types = [card_types.CARD_INTRO, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]

        if not intro_room_settings_enabled:
            excluded_card_types.append(card_types.CARD_MASTER_INTRO)

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               user=self.get_member_id(),
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               card_id__pinning_time__lt=card_instance.pinning_time
                                                               ).select_related('card', 'card__user').exclude(
                Q(card__type__in=excluded_card_types) | Q(card_id__in=excluded_card_ids)
            ).order_by('-card__pinning_time')[:limit_size]

        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               user=self.get_member_id(),
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               card_id__lt=card_instance.id
                                                               ).select_related('card', 'card__user').exclude(
                Q(card__type__in=excluded_card_types) | Q(card_id__in=excluded_card_ids)
            ).order_by('-card_id')[:limit_size]

        return chatroom_queryset

    def fetch_community_chatrooms_queryset_with_last_seen_chatroom(self, pin_status, last_seen_id,
                                                                   intro_room_settings_enabled, excluded_card_ids,
                                                                   limit_size=5) -> []:

        excluded_card_types = [card_types.CARD_INTRO, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]

        if not intro_room_settings_enabled:
            excluded_card_types.append(card_types.CARD_MASTER_INTRO)

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               user=self.get_member_id(),
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               card__id__gte=last_seen_id).select_related('card',
                                                                                                          'card__user'). \
                                    exclude(Q(card__type__in=excluded_card_types) |
                                            Q(card_id__in=excluded_card_ids)).order_by('card_id')[:limit_size]

        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               user=self.get_member_id(),
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               card__id__gte=last_seen_id).select_related('card',
                                                                                                          'card__user'). \
                                    exclude(Q(card__type__in=excluded_card_types) |
                                            Q(card_id__in=excluded_card_ids)).order_by('card_id')[:limit_size]

        return chatroom_queryset

    def fetch_community_chatrooms_queryset_without_last_seen(self, pin_status, intro_room_settings_enabled,
                                                             excluded_card_ids) -> []:

        excluded_card_types = [card_types.CARD_INTRO, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]

        if not intro_room_settings_enabled:
            excluded_card_types.append(card_types.CARD_MASTER_INTRO)

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user').\
                exclude(Q(card__type__in=excluded_card_types) | Q(card_id__in=excluded_card_ids)).order_by('card_id')

        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user').\
                exclude(Q(card__type__in=excluded_card_types) | Q(card_id__in=excluded_card_ids)).order_by('card_id')

        return chatroom_queryset

    def fetch_chatroom_queryset_for_web(self, pin_status, intro_room_settings_enabled, excluded_card_ids):

        excluded_card_types = [card_types.CARD_INTRO, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]

        if not intro_room_settings_enabled:
            excluded_card_types.append(card_types.CARD_MASTER_INTRO)

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user').\
                exclude(Q(card__type__in=excluded_card_types) | Q(card_id__in=excluded_card_ids)).\
                order_by('-card__pinning_time')

        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user').\
                exclude(Q(card__type__in=excluded_card_types) | Q(card_id__in=excluded_card_ids)).order_by('-card_id')

        return chatroom_queryset

    def last_seen_chatroom_query(self, pin_status, intro_room_settings_enabled, excluded_card_ids) -> []:

        excluded_card_types = [card_types.CARD_INTRO, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]

        if not intro_room_settings_enabled:
            excluded_card_types.append(card_types.CARD_MASTER_INTRO)

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).exclude(
                Q(card__type__in=excluded_card_types) | Q(card_id__in=excluded_card_ids)
            ).only('card', 'state').order_by('card_id')

        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               secret_chatroom_left=False,
                                                               card__is_private=False,
                                                               user=self.get_member_id()).exclude(
                Q(card__type__in=excluded_card_types) | Q(card_id__in=excluded_card_ids)
            ).only('card', 'state').order_by('card_id')

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
    def fetch_list_of_community_members(community_instance, member_ids=None):
        if member_ids:
            user_ids = ModelUtilities.get_valid_member_ids(member_ids, community_id=community_instance.id)
            member_list = list(Members.objects.filter(
                Q(community_id=community_instance),
                Q(member_id_id__in=user_ids),
                Q(state=member_states.ADMIN)
                | Q(state=member_states.MEMBER)
                | Q(state=member_states.PROFILE_UNAVAILABLE)
            ).values_list('member_id', flat=True))

        else:
            member_list = \
                list(Members.objects.filter(community_id=community_instance).filter(
                    Q(state=member_states.ADMIN)
                    | Q(state=member_states.MEMBER)
                    | Q(state=member_states.PROFILE_UNAVAILABLE)
                ).values_list('member_id', flat=True))

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
                                         send_expired_info=True, page=0, page_size=0,
                                         member_name_search_string="") -> {}:

        member_dict = {}
        membership_expired_dict = {}
        member_list = get_members_based_on_user_list_query(user_list, community_instance.id,
                                                           order_by_name=order_by_name, page=page, page_size=page_size,
                                                           member_name_search_string=member_name_search_string)
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
                    'created_at': data['created_at'],
                    'user_unique_id': data['user_unique_id'],
                    'is_guest': data['is_guest']
                }

                if member['state'] == member_states.ADMIN or \
                        member['state'] == member_states.MEMBER or \
                        member['state'] == member_states.PROFILE_UNAVAILABLE:
                    member['member_since'] = MEMBER_SINCE_TEXT % (TimeUtilities.convert_epoch_time_to_date_with_mon_day_year(
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

    def fetch_feed(self, pin_status, order_type, chatroom_id=None, scroll_direction=None, api_version="", page=1) -> {}:

        validated_req = MemberCommunityViewHelper.validate_fetch_feed_request(self.get_member_id(),
                                                                              self.get_community_id(),
                                                                              self.get_api_key())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_req.get('community_instance')
        self.set_community_id(community_instance.id)

        filter_dict = {
            'community_id': self.get_community_id(),
            'setting_type': community_setting_types.INTRO_ROOM,
            'enabled': True
        }

        if is_version_code_supported_for_intro_room(self.get_version_code(), self.get_platform_code()):
            intro_room_setting_enabled = False

            intro_room_setting_filter = ModelUtilities.get_model_filter(CommunitySettings, filter_dict)

            if intro_room_setting_filter:
                intro_room_setting_enabled = True

        else:
            intro_room_setting_enabled = True

        excluded_card_ids = []

        if create_chatroom_revamp_version_check(self.get_platform_code(), self.get_version_code()):
            excluded_card_ids = get_card_ids_to_exclude_based_on_cohort_access(self.get_member_id(),
                                                                               self.get_community_id())
            followed_card_ids = get_chatrooms_of_user_with_follow_status(self.get_member_id(),
                                                                         self.get_community_id())

            excluded_card_ids = list(set(excluded_card_ids) - set(followed_card_ids))

        if api_version in [api_version_headers.V1, api_version_headers.V2]:
            chatroom_list = self._get_sorted_chatroom_queryset_based_on_order_type(intro_room_setting_enabled,
                                                                                   pin_status, excluded_card_ids,
                                                                                   order_type, page=page,
                                                                                   api_version=api_version)

        else:

            if not chatroom_id and not scroll_direction:

                last_seen_chatroom = self.last_seen_chatroom_query(pin_status, intro_room_setting_enabled,
                                                                   excluded_card_ids)

                if not last_seen_chatroom:
                    chatroom_queryset = self.fetch_community_chatrooms_queryset_without_last_seen(
                        pin_status, intro_room_setting_enabled, excluded_card_ids)
                    chatroom_list = self.extract_chatrooms_without_scroll(chatroom_queryset, limit_size=5)

                else:
                    last_seen_chatroom_id = last_seen_chatroom.card_id
                    chatroom_list = self.fetch_community_chatrooms_queryset_with_last_seen_chatroom(
                        pin_status, last_seen_chatroom_id, intro_room_setting_enabled, excluded_card_ids, limit_size=5)
            else:

                chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

                if not chatroom_instance:
                    return ResponseUtilities.get_impl_error_context("Invalid chatroom ID",
                                                                    status_code=status_codes.HTTP_400_BAD_REQUEST)

                chatroom_queryset = self.fetch_community_chatrooms_queryset_without_last_seen(
                    pin_status, intro_room_setting_enabled, excluded_card_ids)

                chatroom_list = self.extract_chatrooms_on_scroll(chatroom_id, scroll_direction,
                                                                 chatroom_queryset, limit_size=5)

        from ..chatroom_member.chatroom_member_impl import ChatroomMemberImpl

        chatroom_member_impl = ChatroomMemberImpl(member_id=self.get_member_id(), device_id=self.device_id)
        chatroom_context_list = chatroom_member_impl.process_chatroom_list(chatroom_list, community_instance)
        pinned_chatrooms_list = MemberCommunityHelper.get_pinned_chatrooms_in_community_from_cache(
            community_id=community_instance.id)

        return {
            'success': True,
            'chatrooms': chatroom_context_list,
            'pinned_chatrooms_count': len(pinned_chatrooms_list)
        }

    def fetch_feed_web(self, pin_status, order_type, chatroom_id=None, scroll_direction=None, api_version="",
                       page=1) -> {}:

        validated_req = MemberCommunityViewHelper.validate_fetch_feed_request(self.get_member_id(),
                                                                              self.get_community_id(),
                                                                              self.get_api_key())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_req.get('community_instance')
        self.set_community_id(community_instance.id)

        filter_dict = {
            'community_id': self.get_community_id(),
            'setting_type': community_setting_types.INTRO_ROOM,
            'enabled': True
        }

        if is_version_code_supported_for_intro_room(self.get_version_code(), self.get_platform_code()):
            intro_room_setting_enabled = False

            intro_room_setting_filter = ModelUtilities.get_model_filter(CommunitySettings, filter_dict)

            if intro_room_setting_filter:
                intro_room_setting_enabled = True

        else:
            intro_room_setting_enabled = True

        excluded_card_ids = []

        if create_chatroom_revamp_version_check(self.get_platform_code(), self.get_version_code()):
            excluded_card_ids = get_card_ids_to_exclude_based_on_cohort_access(self.get_member_id(),
                                                                               self.get_community_id())

            followed_card_ids = get_chatrooms_of_user_with_follow_status(self.get_member_id(),
                                                                         self.get_community_id())

            excluded_card_ids = list(set(excluded_card_ids) - set(followed_card_ids))

        if api_version in [api_version_headers.V1, api_version_headers.V2]:
            chatroom_list = self._get_sorted_chatroom_queryset_based_on_order_type(intro_room_setting_enabled,
                                                                                   pin_status, excluded_card_ids,
                                                                                   order_type, page=page,
                                                                                   api_version=api_version)

        else:

            if not chatroom_id and not scroll_direction:
                chatroom_list = self.fetch_chatroom_queryset_for_web(pin_status, intro_room_setting_enabled,
                                                                     excluded_card_ids)
                chatroom_list = chatroom_list[:5]
            else:
                chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

                if not chatroom_instance:
                    return ResponseUtilities.get_impl_error_context("Invalid chatroom ID",
                                                                    status_code=status_codes.HTTP_400_BAD_REQUEST)

                chatroom_list = self.fetch_community_chatrooms_queryset_with_web_scroll(pin_status, chatroom_instance,
                                                                                        intro_room_setting_enabled,
                                                                                        excluded_card_ids)

        from ..chatroom_member.chatroom_member_impl import ChatroomMemberImpl

        chatroom_member_impl = ChatroomMemberImpl(member_id=self.get_member_id(), device_id=self.device_id)
        chatroom_context_list = chatroom_member_impl.process_chatroom_list(chatroom_list, community_instance)
        pinned_chatrooms_list = MemberCommunityHelper.get_pinned_chatrooms_in_community_from_cache(
            community_id=community_instance.id)

        return {
            'success': True,
            'chatrooms': chatroom_context_list,
            'pinned_chatrooms_count': len(pinned_chatrooms_list)
        }

    @staticmethod
    def create_feed_actions(community_instance,
                            platform_code,
                            version_code,
                            pinned_top_bar,
                            user_id=None) -> []:

        actions = []
        community_id = StringUtilities.get_string_from_integer(community_instance.id)
        community_name = community_instance.name

        member_rights = COMMUNITY_FEED_ACTIONS

        if user_id:
            member_rights = check_all_member_rights(user_id, community_instance)

        INVITE_MEMBERS['route'] = INVITE_MEMBERS_ROUTE % community_id
        actions.append(INVITE_MEMBERS)

        if member_rights["create_room"]:
            NEW_CHATROOM['route'] = NEW_CHATROOM_ROUTE % (community_id, community_name)
            actions.append(NEW_CHATROOM)

        DIRECTORY['route'] = DIRECTORY_ROUTE % (community_id, community_name)
        actions.append(DIRECTORY)

        PINNED['route'] = PINNED_ROUTE % community_id
        COMMUNITY_DETAILS['route'] = COMMUNITY_DETAILS_ROUTE % community_id

        if pinned_top_bar:
            actions.append(PINNED)

        actions.append(COMMUNITY_DETAILS)

        """
        Single community view removes all actions 
        barring pinned chatrooms
        """
        if single_community_view_version_check(platform_code, version_code):
            actions = [PINNED]

        return actions

    @staticmethod
    def create_pinned_chatrooms_header(community_instance, version_code, platform_code) -> {}:

        pinned_top_bar = {}

        excluded_card_types = [card_types.CARD_INTRO, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]

        filter_dict = {
            'community_id': community_instance.id,
            'setting_type': community_setting_types.INTRO_ROOM,
            'enabled': True
        }

        intro_room_setting_filter = ModelUtilities.get_model_filter(CommunitySettings, filter_dict)

        if not intro_room_setting_filter and is_version_code_supported_for_intro_room(version_code, platform_code):
            excluded_card_types.append(card_types.CARD_MASTER_INTRO)

        pinned_chatrooms = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                        'is_pinned': True, 'is_deleted': False}).\
            exclude(type__in=excluded_card_types).only('header').order_by('-pinning_time')

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
        pinned_top_bar = self.create_pinned_chatrooms_header(community_instance, self.get_version_code(),
                                                            self.get_platform_code())

        if pinned_top_bar:
            feed_context['pinned_top_bar'] = pinned_top_bar

        actions = self.create_feed_actions(community_instance,
                                           self.get_platform_code(),
                                           self.get_version_code(),
                                           pinned_top_bar,
                                           user_id=self.get_member_id())
        community = self._community_serializer(community_instance, self.get_member_id())
        feed_context['actions'] = actions
        feed_context['community'] = community

        return feed_context

    def fetch_chatroom_home(self, chatroom_id) -> {}:

        validated_req = MemberCommunityHelper.validate_fetch_chatroom_home_request(self.get_member_id(),
                                                                                   chatroom_id)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        engage_instance = validated_req.get('engage_instance')

        chatroom_home = {
            'success': True
        }

        if engage_instance:
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

            chatroom_conversations = get_latest_conversations_against_chatrooms_list([card_instance.id])
            chatrooms_conversation_ids_list = chatroom_conversations.get(card_instance.id)
            last_conversation_id = chatrooms_conversation_ids_list[0] if chatrooms_conversation_ids_list else None
            last_conversation = ModelUtilities.get_model_instance_or_none(card_answers, last_conversation_id)

            if last_conversation and not is_draft_conversation(last_conversation, member_id):

                last_conversation_dict = conversationSerializer(last_conversation, current_user_id=member_id)

                preview = generate_internal_link_preview_for_conversation(last_conversation, member_id)

                if preview:
                    last_conversation_dict['preview'] = preview

                chatroom_home['last_conversation'] = last_conversation_dict

            chatroom_home['unseen_conversation_count'] = engage_instance.unseen_count
            chatroom_home['last_conversation_time'] = get_time_text_for_my_chatrooms(engage_instance.updated_at)

            conversation_users = get_conversation_users_against_chatrooms_list([card_instance.id])

            chatroom_home['conversation_users'] = conversation_users.get(card_instance.id, [])
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
            return get_error_context(False, "Invalid User ID.")

        community_instance = ModelUtilities.get_model_instance_or_none(Community, self.get_community_id())

        if not community_instance:
            return get_error_context(False, "Invalid Community ID.")

        req_from = req_body.get("from")

        if not req_from:
            return get_error_context(False, "Send the key 'from'.")

        member_id = req_body.get("member_id")

        if user_instance.id == member_id:
            return get_error_context(False, "You cannot DM yourself.")

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
                return get_error_context(False, "Invalid Member ID.")

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
                    "cta": CTA_ROUTE_DIRECT_MESSAGES + f"?community_id={community_instance.id}",
                    "show_dm": True
                }

            else:
                return {"success": True, "show_dm": False}

        else:
            return get_error_context(False, "Invalid value of key 'from'.")

    def fetch_member_profile(self, user_id, uuid: str = None):
        validated_req = MemberCommunityViewHelper.validate_fetch_member_profile_request(self.get_member_id(), user_id,
                                                                                        self.get_community_id(),
                                                                                        self.get_api_key(),
                                                                                        uuid)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        current_user_instance = validated_req.get('current_user_instance')
        community_instance = validated_req.get('community_instance')
        user_instance = validated_req.get('user_instance')

        removed_user_state = self.compute_removed_user_context(user_instance, community_instance)

        if removed_user_state.get('remove_state'):
            return ResponseUtilities.get_impl_error_context("Profile doesn't exists!",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        current_user_member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                               'member_id': current_user_instance})

        if not current_user_member_filter:
            return ResponseUtilities.get_impl_error_context("You are not part of the community!",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        current_user_member_instance = current_user_member_filter[0]

        user_member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                       'member_id': user_instance})

        if not user_member_filter:
            return ResponseUtilities.get_impl_error_context("Profile doesn't exists!",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_member_instance = user_member_filter[0]

        question_answers_data = MemberCommunityHelper.get_question_answer_data_in_member_profile(
            current_user_member_instance, user_member_instance, community_instance)

        is_community_answer_data = len(question_answers_data) > 0

        user_member_data = MemberCommunityHelper.add_member_metadata(user_member_instance, community_instance,
                                                                     current_user_member_instance,
                                                                     is_community_answer_data)

        user_menu = MemberCommunityHelper.get_member_profile_menu(user_member_instance, community_instance,
                                                                  current_user_member_instance)

        user_menu = MemberCommunityHelper.update_member_profile_menu_for_sdk(user_member_instance, community_instance,
                                                                             current_user_member_instance, user_menu)

        member_profile_response = {
            'success': True,
            'member': user_member_data,
            'community_name': community_instance.name,
            'question_answers': question_answers_data,
            'menu': user_menu
        }

        return member_profile_response

    def edit_member_profile(self, req_body: dict) -> {}:
        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return get_error_context(False, "Invalid x-member-id")

        community_instance = SdkClient.get_community_instance_or_none(community_id=self.get_community_id(),
                                                                      api_key=self.get_api_key())

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID or x-api-key")

        user_member_filter = ModelUtilities.get_model_filter(Members,
                                                             {'member_id': user_instance,
                                                              'community_id': community_instance})

        if not user_member_filter:
            return get_error_context(False, "You are not part of community!")

        user_member_instance = user_member_filter[0]
        user_intro_card_instance = None
        update_preview = False
        intro_filter = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                    'user': user_instance,
                                                                    'is_deleted': False,
                                                                    'type': card_types.CARD_INTRO})
        if intro_filter:
            user_intro_card_instance = intro_filter[0]

        question_answers = req_body.get('question_answers', [])
        image_url = req_body.get('image_url')
        name = req_body.get('name')

        if question_answers:

            from ..community.community_impl import CommunityHelper

            CommunityHelper.save_responses_of_member_in_community(user_instance.id, community_instance.id,
                                                                  question_answers, True)

            for question in question_answers:

                question_instance = ModelUtilities.get_model_instance_or_none(communityQuestions, question.get(
                    DIRECTORY_QUESTIONS_V2_QUESTION_ID_KEY))

                if not question_instance:
                    continue

                if user_intro_card_instance and question_instance.question_state == question_states.INTRODUCTION:
                    ModelUtilities.model_update(Collabcard, {'id': user_intro_card_instance.id},
                                                {'title': question.get(DIRECTORY_QUESTIONS_V2_ANSWER_KEY)})
                    update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                                   {'card': user_intro_card_instance, 'user': user_instance},
                                                   {})

                    card_answer_filter = ModelUtilities.is_model_filter_exists(card_answers,
                                                                               {'preview_chatroom': user_intro_card_instance,
                                                                                'preview_type': "chatroom"})

                    if card_answer_filter:
                        ModelUtilities.model_update(card_answers,
                                                    {'preview_chatroom': user_intro_card_instance,
                                                     'preview_type': "chatroom",
                                                     'card__type': card_types.CARD_MASTER_INTRO,
                                                     'is_deleted': False,
                                                     'card__community': community_instance},
                                                    {'answer': question.get(DIRECTORY_QUESTIONS_V2_ANSWER_KEY),
                                                     'last_updated': TimeUtilities.current_time_in_milliseconds()})
                        update_preview = True

        question_answers_data = MemberCommunityHelper.get_question_answer_data_in_member_profile(user_member_instance,
                                                                                                 user_member_instance,
                                                                                                 community_instance)

        user_member_filter.update(edit_required=False, updated_at=TimeUtilities.current_time_in_sec())

        if name:

            from ..community.community_impl import CommunityHelper

            CommunityHelper.update_user_alias_name(user_instance.id, community_instance.id, name, question_states.NAME)

            update_preview = True


        if image_url:
            MemberCommunityHelper.update_users_image_url_in_community(user_member_filter, image_url,
                                                                      user_intro_card_instance)
            update_preview = True

            community = ModelUtilities.get_model_filter(SdkClient,
                                                        {"community": community_instance, "is_deleted": False})

            if len(community):
                MemberCommunityHelper.update_user_image_in_sdk(user_instance, image_url)

        if (not user_intro_card_instance) and (user_member_instance.state in [member_states.ADMIN,
                                                                              member_states.MEMBER,
                                                                              member_states.PROFILE_UNAVAILABLE]):
            post_introduction_card_for_community(community_instance.id, user_instance.id)
            update_preview = False

        set_levels_on_ctc_celery.delay({"community_id": community_instance.id,
                                        "level": COMMUNITY_LEVEL_3_TEXT,
                                        "promoter": user_member_instance.state == member_states.ADMIN})

        if update_preview and user_intro_card_instance:
            update_multiple_previews_in_chatroom.delay({'chatroom_id': user_intro_card_instance.id})

        set_level_click_state.delay({"community_id": community_instance.id,
                                     "promoter": user_member_instance.state == member_states.ADMIN})

        from collabmates_api.cohort.cohort_impl import CohortHelper
        CohortHelper.remove_cohort_membership_when_updating_community_answers(user_instance.id,
                                                                              community_instance.id)
        CohortHelper.add_member_to_respective_question_based_cohorts(user_instance.id, community_instance.id)

        if question_answers_data:
            return {'success': True, 'question_answers': question_answers_data}

        return {'success': True}
    
    def _get_sorted_chatroom_queryset_based_on_order_type(self, intro_room_settings_enabled, pin_status,
                                                          excluded_card_ids, order_type, page=1,
                                                          api_version=api_version_headers.V1, limit=10):

        excluded_card_types = [card_types.CARD_INTRO, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]

        if not intro_room_settings_enabled:
            excluded_card_types.append(card_types.CARD_MASTER_INTRO)

        pinned_chatrooms_list = MemberCommunityHelper.get_pinned_chatrooms_in_community_from_cache(
            self.get_community_id())

        ordered_card_ids = []

        if (order_type == 0) and (api_version == api_version_headers.V1):
            ordered_card_ids = get_ordered_card_id_on_the_basis_newest_chatroom(self.get_member_id(),
                                                                                self.get_community_id(),
                                                                                pin_status, excluded_card_ids,
                                                                                excluded_card_types, page, limit)

        if (order_type == 0) and (api_version == api_version_headers.V2):
            ordered_card_ids = get_ordered_card_id_on_the_basis_newest_chatroom_v2(self.get_member_id(),
                                                                                   self.get_community_id(),
                                                                                   pin_status, excluded_card_ids,
                                                                                   excluded_card_types,
                                                                                   pinned_chatrooms_list, page, limit)
        # Recently Active
        if (order_type == 1) and (api_version == api_version_headers.V1):
            ordered_card_ids = get_ordered_card_id_on_the_basis_last_message(self.get_member_id(),
                                                                             self.get_community_id(),
                                                                             pin_status, excluded_card_ids,
                                                                             excluded_card_types, page, limit)

        if (order_type == 1) and (api_version == api_version_headers.V2):
            ordered_card_ids = get_ordered_card_id_on_the_basis_last_message_v2(self.get_member_id(),
                                                                                self.get_community_id(),
                                                                                pin_status, excluded_card_ids,
                                                                                excluded_card_types,
                                                                                pinned_chatrooms_list, page, limit)

        # Most Messages
        if (order_type == 2) and (api_version == api_version_headers.V1):
            ordered_card_ids = get_ordered_card_id_on_the_basis_of_message_count(self.get_member_id(),
                                                                                 self.get_community_id(),
                                                                                 pin_status, excluded_card_ids,
                                                                                 excluded_card_types, page, limit)

        if (order_type == 2) and (api_version == api_version_headers.V2):
            ordered_card_ids = get_ordered_card_id_on_the_basis_of_message_count_v2(self.get_member_id(),
                                                                                    self.get_community_id(),
                                                                                    pin_status, excluded_card_ids,
                                                                                    excluded_card_types,
                                                                                    pinned_chatrooms_list, page, limit)

        # Most Participants
        if (order_type == 3) and (api_version == api_version_headers.V1):
            ordered_card_ids = get_ordered_card_id_on_the_basis_of_participants_count(self.get_member_id(),
                                                                                      self.get_community_id(),
                                                                                      pin_status, excluded_card_ids,
                                                                                      excluded_card_types, page, limit)

        if (order_type == 3) and (api_version == api_version_headers.V2):
            ordered_card_ids = get_ordered_card_id_on_the_basis_of_participants_count_v2(self.get_member_id(),
                                                                                         self.get_community_id(),
                                                                                         pin_status, excluded_card_ids,
                                                                                         excluded_card_types,
                                                                                         pinned_chatrooms_list, page,
                                                                                         limit)

        chatroom_queryset = MemberCommunityHelper.get_ordered_collabcard_state_list_based_on_card_ids(
            self.get_member_id(), ordered_card_ids)

        return chatroom_queryset

    def request_dm_limit(self, member_id: str, uuid: str = None) -> {}:
        validated_request = MemberCommunityViewHelper.validate_request_dm_limit_request(self.get_member_id(),
                                                                                        self.get_community_id(),
                                                                                        self.get_api_key(),
                                                                                        member_id,
                                                                                        uuid)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        user_instance = validated_request.get('user_instance')
        member_instance = validated_request.get('member_instance')
        is_one_user_cm = validated_request.get('is_one_user_cm')

        dm_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                            {'community': community_instance,
                                                             'setting_type': community_setting_types.DIRECT_MESSAGES})

        if all([dm_setting_filter, not dm_setting_filter[0].enabled]):
            return ResponseUtilities.get_impl_error_context('Direct message is disabled for the community!',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        from collabmates_api.chatroom.chatroom_impl import ChatroomHelper

        user_member_dm_chatroom = ChatroomHelper.get_dm_chatroom_from_members(community_instance.id,
                                                                              user_instance.id, member_instance.id)

        response = {
            'is_request_dm_limit_exceeded': False,
            'new_request_dm_timestamp': None,
            'success': True,
            'user_dm_limit': None
        }

        if user_member_dm_chatroom:
            response['chatroom_id'] = user_member_dm_chatroom.id

        if not is_one_user_cm:
            response = MemberCommunityHelper.member_request_dm_limit(user_instance, community_instance, response)

        return response

    def fetch_dm_chatrooms(self, page: int = 1, custom_tag: str = '') -> {}:
        validated_request = MemberCommunityViewHelper.validate_fetch_dm_chatrooms_request(self.get_member_id(),
                                                                                          self.get_community_id(),
                                                                                          self.get_api_key())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        user_instance = validated_request.get('user_instance')

        dm_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                            {'community': community_instance,
                                                             'setting_type': community_setting_types.DIRECT_MESSAGES})

        if all([dm_setting_filter, not dm_setting_filter[0].enabled]):
            return ResponseUtilities.get_impl_error_context('Direct message is disabled!',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        total_pages = 0

        card_state_tuple = get_dm_chatrooms_of_user(user_instance.id, community_instance.id, custom_tag=custom_tag)

        card_state_map = {data[0]: data[1] for data in card_state_tuple}

        if not card_state_map:
            return {'success': True, 'dm_chatrooms': [], 'total_pages': total_pages}

        total_pages = int(math.ceil(len(card_state_map) / CHATROOMS_RECORD_LIMIT))

        convsersation_states_to_consider = [
            conversation_states.ANSWER,
            conversation_states.CONVERSATION_DIRECT_MESSAGE_BLOCK_MEMBER_DISABLE_CHAT,
            conversation_states.CONVERSATION_DIRECT_MESSAGE_UNBLOCK_MEMBER_ENABLE_CHAT
        ]

        conversation_states_excluded = [
            conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_REMOVED_OR_LEFT,
            conversation_states.CONVERSATION_DIRECT_MESSAGE_CM_REMOVED,
            conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_DISABLE_CHAT,
            conversation_states.CONVERSATION_DIRECT_MESSAGE_CM_BECOMES_MEMBER_ENABLE_CHAT,
            conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_ENABLE_CHAT
        ]

        card_ans_map = get_last_conversation_id_corresponding_to_chatrooms_list(
            list(card_state_map.keys()), excluded_conversation_state=conversation_states_excluded, page=page)

        if not card_ans_map:
            return {'success': True, 'dm_chatrooms': [], 'total_pages': total_pages}

        dm_chatrooms = []

        rights_list = list(ModelUtilities.get_model_filter(userMemberRights,
                                                           {'user': user_instance,
                                                            'community': community_instance}).
                           values_list("right__state", flat=True))

        context = {"current_user_id": user_instance.id}
        community_serializer_object = CommunitySerializerV1(community_instance, context=context, many=False).data

        for card_id, card_ans_id in card_ans_map.items():
            chatroom = MemberCommunityHelper.serialise_dm_chatrooms(user_instance, community_instance, card_id,
                                                                    card_ans_id, card_state_map,
                                                                    convsersation_states_to_consider, rights_list,
                                                                    device_id=self.get_device_id())

            chatroom['community'] = community_serializer_object

            if chatroom:
                dm_chatrooms.append(chatroom)

        return {'success': True, 'dm_chatrooms': dm_chatrooms, 'total_pages': total_pages}

    def member_can_dm(self, req_body: dict) -> {}:
        validated_request = MemberCommunityViewHelper.validate_member_can_dm_request(self.get_member_id(),
                                                                                     self.get_community_id(),
                                                                                     self.get_api_key(),
                                                                                     req_body)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        user_instance = validated_request.get('user_instance')
        member_instance = validated_request.get('member_instance')
        req_from = validated_request.get('req_from')

        if req_from == dm_icon_from_states.MEMBER_PROFILE:
            response = MemberCommunityHelper.can_member_dm_from_member_profile(user_instance, member_instance,
                                                                               community_instance)

        elif req_from == dm_icon_from_states.COMMUNITY_DETAIL:
            response = MemberCommunityHelper.can_member_dm_from_community_detail(user_instance, community_instance)

        elif req_from in [dm_icon_from_states.DM_FEED, dm_icon_from_states.MEMBER_DIRECTORY]:
            response = MemberCommunityHelper.can_member_from_dm_feed_or_member_directory(user_instance,
                                                                                         community_instance)

        elif req_from in [dm_icon_from_states.DM_FEED_V2, dm_icon_from_states.GROUP_CHANNEL]:
            response = MemberCommunityHelper.can_member_request_from_dm_feed_v2(user_instance, community_instance)

        else:
            response = MemberCommunityHelper.can_member_dm_from_dm_chatroom(user_instance, validated_request)

        return response

    def join_community_sdk(self, req_body: dict) -> {}:
        validated_request = MemberCommunityViewHelper.validate_join_community_sdk_request(self.get_member_id(),
                                                                                          self.get_community_id(),
                                                                                          self.get_api_key())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        user_instance = validated_request.get('user_instance')

        members_filter = ModelUtilities.get_model_filter(Members, {'member_id': user_instance,
                                                                   'community_id': community_instance})

        req_body = req_body if req_body else {}

        if not members_filter:
            MemberCommunityHelper.make_requesting_user_as_member_of_community(user_instance, community_instance,
                                                                              req_body, device_id=self.get_device_id(),
                                                                              platform=self.get_platform_code(),
                                                                              version_code=self.get_version_code())

        user_has_access = Members.user_has_app_access(user_instance.id)

        return {'success': True, 'access': user_has_access}

    def unsubscribe_email_notifications(self, code_flags: dict) -> {}:
        validated_request = MemberCommunityViewHelper.validate_unsubscribe_email_notifications_request(
            self.get_member_id(), self.get_community_id(), code_flags=code_flags)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        user_instance = validated_request.get('user_instance')

        for code, value in code_flags.items():

            if not isinstance(value, bool):
                return ResponseUtilities.get_impl_error_context('Invalid flag values for code',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)

            create_notification_flag(user_instance, [code], community_id=community_instance.id, flag=value)

        return {'success': True}

    def fetch_unsubscribe_email_notifications(self, chatroom_id: str = None, codes: str = None) -> {}:
        validated_request = MemberCommunityViewHelper.validate_fetch_unsubscribe_email_notifications_request(
            self.get_member_id(), self.get_community_id(), chatroom_id=chatroom_id, codes=codes)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        user_instance = validated_request.get('user_instance')
        chatroom_instance = validated_request.get('chatroom_instance')
        notification_codes = validated_request.get('notification_codes')

        notification_flags = fetch_notification_flag(user_instance, community_instance, chatroom=chatroom_instance,
                                                     notification_codes=notification_codes)

        serialized_flags = MemberNotificationFlagSerializer(notification_flags, many=True)

        return {'success': True, 'notification_flags': serialized_flags.data}

    def fetch_member_access(self, access_type: str) -> {}:
        validated_request = MemberCommunityHelper.validate_fetch_member_access_request(
            self.get_member_id(), self.get_api_key(), access_type)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        user_instance = validated_request.get('user_instance')
        member_state = validated_request.get('member_state')
        access_type = validated_request.get('access_type')

        output_context = {
            'success': True,
            'access': False,
            'is_cm': False
        }

        if member_state == member_states.ADMIN:
            output_context['is_cm'] = True

            if all([access_type in [access_types.DELETE_POST, access_types.PIN_POST, access_types.DELETE_COMMENT,
                                    access_types.CREATE_ACTIVITY, access_types.EDIT_COMMENT, access_types.EDIT_POST],
                    check_admin_moderate_feed_and_comments_right(user_instance, community_instance)]):
                output_context['access'] = True

            if access_type in [access_types.CREATE_POST, access_types.VIEW_POST, access_types.LIKE_POST,
                               access_types.CREATE_COMMENT, access_types.VIEW_COMMENT, access_types.LIKE_COMMENT,
                               access_types.SAVE_POST, access_types.VIEW_ACTIVITY, access_types.VIEW_REPORT_ENTITY]:
                output_context['access'] = True

        if member_state == member_states.MEMBER:
            if access_type == access_types.CREATE_POST and check_member_create_post_right(user_instance,
                                                                                          community_instance):
                output_context['access'] = True

            if access_type == access_types.CREATE_COMMENT and check_member_comment_and_reply_right(user_instance,
                                                                                                   community_instance):
                output_context['access'] = True

            if access_type in [access_types.VIEW_POST, access_types.DELETE_POST, access_types.LIKE_POST,
                               access_types.VIEW_COMMENT, access_types.DELETE_COMMENT, access_types.LIKE_COMMENT,
                               access_types.SAVE_POST, access_types.VIEW_ACTIVITY, access_types.EDIT_COMMENT, access_types.EDIT_POST]:
                output_context['access'] = True

            if access_type in [access_types.PIN_POST, access_types.CREATE_ACTIVITY, access_types.VIEW_REPORT_ENTITY]:
                output_context['access'] = False

        return output_context

    def fetch_post_feed(self, order_type: int = 0, pinned: bool = False, page: int = 1, page_size: int = 10,
                        chatroom_ids: list = None):
        validated_request = MemberCommunityHelper.validate_fetch_post_feed_request(
            self.get_member_id(), self.get_api_key(), order_type, chatroom_ids)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        self.set_community_id(community_instance.id)

        ordered_card_ids = []
        pinned_chatrooms = list(set(ModelUtilities.get_model_filter(
            Collabcard, {'community': self.get_community_id(), 'is_pinned': True,
                         'is_deleted': False, 'type': card_types.CARD_FEED_GROUP}
        ).values_list('id', flat=True)))

        # Case handled for Feed order based on Newest chatroom and Most participants
        if order_type in [feed_order_types.NEWEST_ORDER_TYPE, feed_order_types.MOST_PARTICIPANTS_ORDER_TYPE]:
            excluded_card_ids = get_card_ids_to_exclude_based_on_cohort_access(self.get_member_id(),
                                                                               self.get_community_id())
            followed_card_ids = get_chatrooms_of_user_with_follow_status(self.get_member_id(),
                                                                         self.get_community_id())

            excluded_card_ids = list(set(excluded_card_ids) - set(followed_card_ids))

            filter_dict = {
                'community_id': self.get_community_id(),
                'setting_type': community_setting_types.INTRO_ROOM,
                'enabled': True
            }

            intro_room_setting_enabled = False

            intro_room_setting_filter = ModelUtilities.get_model_filter(CommunitySettings, filter_dict)

            if intro_room_setting_filter:
                intro_room_setting_enabled = True

            excluded_card_types = [card_types.CARD_INTRO, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]

            if not intro_room_setting_enabled:
                excluded_card_types.append(card_types.CARD_MASTER_INTRO)

            if order_type == feed_order_types.NEWEST_ORDER_TYPE:
                ordered_card_ids = get_ordered_card_id_on_the_basis_newest_chatroom_v2(self.get_member_id(),
                                                                                       self.get_community_id(),
                                                                                       pinned, excluded_card_ids,
                                                                                       excluded_card_types,
                                                                                       pinned_chatrooms, page, page_size,
                                                                                       card_types.CARD_FEED_GROUP)

            if order_type == feed_order_types.MOST_PARTICIPANTS_ORDER_TYPE:
                ordered_card_ids = get_ordered_card_id_on_the_basis_of_participants_count_v2(self.get_member_id(),
                                                                                             self.get_community_id(),
                                                                                             pinned, excluded_card_ids,
                                                                                             excluded_card_types,
                                                                                             pinned_chatrooms, page,
                                                                                             page_size,
                                                                                             card_types.CARD_FEED_GROUP)

        # Case handled for Feed order based on Recently Active and Most messages
        elif order_type in [feed_order_types.RECENTLY_ACTIVE_ORDER_TYPE,
                            feed_order_types.MOST_MESSAGES_ORDER_TYPE] and chatroom_ids:
            ordered_card_ids = validated_request.get('chatroom_ids')

        chatroom_queryset = MemberCommunityHelper.get_ordered_collabcard_state_list_based_on_card_ids(
            self.get_member_id(), ordered_card_ids)

        from ..chatroom_member.chatroom_member_impl import ChatroomMemberImpl

        chatroom_member_impl = ChatroomMemberImpl(member_id=self.get_member_id(), device_id=self.device_id)
        chatroom_context_list = chatroom_member_impl.process_chatroom_list(chatroom_queryset, community_instance)

        return {
            'success': True,
            'chatrooms': chatroom_context_list,
            'pinned_chatrooms_count': len(pinned_chatrooms)
        }

    def fetch_excluded_chatrooms_for_user(self):
        validated_request = MemberCommunityHelper.validate_fetch_excluded_chatrooms_request(
            self.get_member_id(), self.get_api_key())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        self.set_community_id(community_instance.id)

        excluded_card_ids = get_card_ids_to_exclude_based_on_cohort_access(self.get_member_id(),
                                                                           self.get_community_id())
        followed_card_ids = get_chatrooms_of_user_with_follow_status(self.get_member_id(),
                                                                     self.get_community_id())

        excluded_card_ids = list(set(excluded_card_ids) - set(followed_card_ids))

        return {
            'success': True,
            'chatroom_ids': excluded_card_ids
        }

    def fetch_user_chatroom_status(self, user_id: str = None, chatroom_types: list = None, page: int = None,
                                   page_size: int = None, uuid: str = None) -> dict:
        validated_request = MemberCommunityHelper.validate_fetch_user_chatroom_status_request(
            self.get_member_id(), self.get_api_key(), user_id, uuid)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        member_instance = validated_request.get('member_instance')
        community_instance = validated_request.get('community_instance')
        self.set_community_id(community_instance.id)

        if not chatroom_types:
            chatroom_types = [card_types.CARD_NORMAL, card_types.CARD_PURPOSE]

        user_chatroom_status_query = get_user_chatroom_status(member_instance.id, self.get_community_id(),
                                                              chatroom_types, page, page_size)

        filter_dict = {
            'community': community_instance,
            'type__in': chatroom_types,
            'is_deleted': False
        }

        total_chatrooms_count = ModelUtilities.get_model_filter(Collabcard, filter_dict).count()

        return {
            'success': True,
            'chatrooms_data': user_chatroom_status_query,
            'total_chatrooms_count': total_chatrooms_count
        }

    def fetch_user_home_meta(self):
        validated_request = MemberCommunityHelper.validate_fetch_user_home_meta_request(self.get_member_id(),
                                                                                        self.get_api_key())

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_request.get('user_instance')
        community_instance = validated_request.get('community_instance')
        self.set_community_id(community_instance.id)

        community_chatroom_count_dict = MemberCommunityHelper.fetch_chatroom_count_for_home(
            [self.get_community_id()], user_instance.id, is_chatroom_revamp=False)

        user_engage_filter = ModelUtilities.get_model_filter(Member_Engage,
                                                             {'member_id': self.get_member_id(),
                                                              'community_id': self.get_community_id()})

        unseen_channel_count = 0

        if user_engage_filter:
            unseen_channel_count = user_engage_filter[0].last_unseen_count

        return {
            'success': True,
            'total_channel_count': community_chatroom_count_dict.get(self.get_community_id()),
            'unseen_channel_count': unseen_channel_count
        }


class MemberCommunityHelper:
    @staticmethod
    def get_active_chatroom_member_images(community_instance, member_id):

        current_time = TimeUtilities.current_time_in_sec()
        state_filter = collabcardState.objects.filter(
            community=community_instance, user=member_id, card__is_deleted=False, secret_chatroom_left=False,
        ).exclude(card__type=card_types.CARD_INTRO).select_related('card').order_by('-card')
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
    def fetch_chatroom_count_for_home(community_id_list, member_id, is_chatroom_revamp=False) -> {}:

        excluded_card_ids = []

        if is_chatroom_revamp:
            excluded_card_ids = get_card_ids_to_exclude_based_on_cohort_access(member_id)
            followed_card_ids = get_chatrooms_of_user_with_follow_status(member_id)

            excluded_card_ids = list(set(excluded_card_ids) - set(followed_card_ids))

        community_count_dict = get_chatroom_count_based_on_community_list(community_id_list, member_id,
                                                                          excluded_card_ids=excluded_card_ids)

        filter_dict = {
            'community_id__in': community_count_dict.keys(),
            'setting_type': community_setting_types.INTRO_ROOM,
            'enabled': False
        }
        intro_room_setting_filter = ModelUtilities.get_model_filter(CommunitySettings, filter_dict)

        for intro_room_setting_instance in intro_room_setting_filter:
            community_count_dict[intro_room_setting_instance.community_id] -= 1

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
    def extract_member_tagging_data(member_data, sdk_client_info_flag:bool = None) -> []:

        member_list = []

        for key, value in member_data.items():

            temp = dict()
            temp['id'] = value['id']
            temp['name'] = value['name']
            temp['image_url'] = value['image_url']
            temp['user_unique_id'] = value['user_unique_id']

            if value.get('is_guest') is not None:
                temp['is_guest'] = value.get('is_guest')

            if value.get('custom_title'):
                temp['custom_title'] = value.get('custom_title')

            if sdk_client_info_flag:
                sdk_client_info = ModelUtilities.get_model_filter(SDKClientUsersInfo, {'user_id': value['id']}).first()

                if sdk_client_info:
                    temp['sdk_client_info'] = SDKClientUsersInfoSerializer(sdk_client_info, many=False).data

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

    @staticmethod
    def add_member_metadata(member_instance, community_instance, current_user_member_instance,
                            is_community_answer_data=False):
        user_instance = member_instance.member_id

        user_data = MemberCommunityHelper.add_member_profile(user_instance, community_instance)

        if not user_data.get('image_url'):
            del user_data['image_url']

        user_data['updated_at'] = member_instance.member_id.userinfo.updated_at
        user_data['route'] = MEMBER_COMMUNITY_PROFILE_ROUTE % (community_instance.id, member_instance.member_id_id)
        user_data['state'] = member_instance.state
        user_data['is_owner'] = member_instance.is_owner

        if member_instance.custom_title:
            user_data['custom_title'] = member_instance.custom_title

        if user_data['state'] in [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]:
            user_data['member_since'] = MEMBER_SINCE_TEXT % (TimeUtilities.convert_epoch_time_to_date_with_mon_day_year(
                member_instance.created_at))

        elif user_data['state'] == member_states.PENDING_MEMBER:
            user_data['member_since'] = PENDING_MEMBER_TEXT % community_instance.name

        if not is_community_answer_data:

            if member_instance.state == member_states.ADMIN:
                user_data['custom_intro_text'] = CREATE_INTRO_TEXT_ADMIN % \
                                                 TimeUtilities.convert_epoch_time_in_date(member_instance.created_at)

        return user_data

    @staticmethod
    def is_user_answer_private(answer_data):
        if answer_data.get('value'):
            value_list = json.loads(answer_data.get('value'))
            privacy = ANSWER_PRIVACY_PUBLIC_VALUE

            for value in value_list:
                if ANSWER_PRIVACY_KEY in value:
                    privacy = value['answer_privacy']

            if privacy == ANSWER_PRIVACY_PRIVATE_VALUE:
                return True

        return False

    @staticmethod
    def get_question_answer_data_in_member_profile(current_user_member_instance, user_member_instance,
                                                   community_instance):
        question_answers = []

        user_instance = user_member_instance.member_id

        community_answers_filter = ModelUtilities.get_model_filter(communityAnswers,
                                                                   {'member': user_instance,
                                                                    'community': community_instance})

        is_same_user = current_user_member_instance == user_member_instance

        if community_answers_filter:
            user_answers = CommunityAnswersSerializer(community_answers_filter, many=True).data

            for user_answer in user_answers:
                user_answer = dict(user_answer)

                community_question_instance = ModelUtilities.get_model_instance_or_none(communityQuestions,
                                                                                        user_answer.get('question'))

                if not community_question_instance:
                    continue

                if any([all([community_question_instance.question_title == CREATE_COMMUNITY_QUESTION_NAME_TITLE,
                        community_question_instance.is_hidden,
                        community_question_instance.field,
                        community_question_instance.question_state == question_states.PARAGRAPH]),
                        community_question_instance.question_state == question_states.NAME]):
                    continue

                question_data = CommunityQuestionsSerializerV2(community_question_instance, many=False).data

                discard_question = True

                if any([not MemberCommunityHelper.is_user_answer_private(question_data), is_same_user,
                        all([current_user_member_instance.state == member_states.ADMIN,
                             check_admin_view_contact_right(current_user_member_instance.member_id_id,
                                                            community_instance.id)])]):
                    discard_question = False

                if not discard_question:
                    user_answer_dict = {
                        'answer': user_answer.get('question_answer'),
                        'member_id': user_answer.get('member'),
                        'question_id': user_answer.get('question'),
                        'community_id': user_answer.get('community')
                    }

                    question_data['state'] = question_data['question_state']
                    del question_data['question_state']

                    if all([question_data.get('question_title'),
                            (question_data.get('question_title') in IMAGE_URLS_FOR_QUESTION_TITLES),
                            (question_data.get('question_title') in ICONS)]):
                        user_answer_dict['image_url'] = ICONS[question_data.get('question_title')]

                    question_answers.append({'question_answer': user_answer_dict,
                                             'question': question_data})

        return question_answers

    @staticmethod
    def add_menu_items_if_current_user_is_owner_and_user_is_admin(menu, all_menu_items):

        menu.append(all_menu_items.get('EDIT_CM_RIGHTS'))
        menu.append(all_menu_items.get('REMOVE_FROM_COMMUNITY'))

        return menu

    @staticmethod
    def add_menu_items_if_current_user_is_owner_and_user_is_non_admin(menu, all_menu_items):

        menu.append(all_menu_items.get('EDIT_PERMISSIONS'))
        menu.append(all_menu_items.get('GIVE_CM_RIGHTS'))
        menu.append(all_menu_items.get('REMOVE_FROM_COMMUNITY'))

        return menu

    @staticmethod
    def add_menu_items_if_current_user_is_admin_and_user_is_admin(current_user_member_instance, community_instance,
                                                                  menu, all_menu_items, is_parent_cm=False):

        if all([check_admin_approve_right(current_user_member_instance.member_id, community_instance),
                is_parent_cm]):
            menu.append(all_menu_items.get('REMOVE_FROM_COMMUNITY'))

        if all([check_admin_add_community_managers_right(current_user_member_instance.member_id,
                                                         community_instance),
                is_parent_cm]):
            menu.append(all_menu_items.get('EDIT_CM_RIGHTS'))

        menu.append(all_menu_items.get('REPORT_MEMBER'))

        return menu

    @staticmethod
    def add_menu_items_if_current_user_is_admin_and_user_is_non_admin(current_user_member_instance, community_instance,
                                                                  menu, all_menu_items, is_parent_cm=False):
        if any([check_admin_approve_right(current_user_member_instance.member_id, community_instance),
                check_admin_delete_right(current_user_member_instance.member_id_id, community_instance)]):
            menu.append(all_menu_items.get('EDIT_PERMISSIONS'))

        if check_admin_approve_right(current_user_member_instance.member_id, community_instance):
            menu.append(all_menu_items.get('REMOVE_FROM_COMMUNITY'))

        if all([check_admin_add_community_managers_right(current_user_member_instance.member_id,
                                                         community_instance)]):
            menu.append(all_menu_items.get('GIVE_CM_RIGHTS'))

        if not check_admin_approve_right(current_user_member_instance.member_id, community_instance):
            menu.append(all_menu_items.get('REPORT_MEMBER'))

        return menu

    @staticmethod
    def get_member_profile_menu(user_member_instance, community_instance, current_user_member_instance):
        menu = []

        is_same_user = user_member_instance.member_id_id == current_user_member_instance.member_id_id
        all_menu_items = {key: {k1: v1 for k1, v1 in value.items()} for key, value in MEMBER_PROFILE_MENU_ITEMS.items()}
        parents_list = json.loads(user_member_instance.parent_cm_list) if user_member_instance.parent_cm_list else []
        parents_cm_list = []

        for user_id in parents_list:
            user_id = NumberUtilities.get_integer_from_string(user_id, 0)

            if user_id:
                parents_cm_list.append(user_id)

        is_parent_cm = current_user_member_instance.member_id_id in parents_cm_list

        for menu_item in all_menu_items:
            all_menu_items[menu_item]['route'] = all_menu_items[menu_item]['route'].format(
                community_instance.id, user_member_instance.member_id_id)

        if (not is_same_user) and current_user_member_instance.is_owner:

            if user_member_instance.state == member_states.ADMIN:
                menu = MemberCommunityHelper.add_menu_items_if_current_user_is_owner_and_user_is_admin(menu,
                                                                                                       all_menu_items)

            elif user_member_instance.state in [member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]:
                menu = MemberCommunityHelper.add_menu_items_if_current_user_is_owner_and_user_is_non_admin(
                    menu, all_menu_items)

            else:
                menu.append(all_menu_items.get('REPORT_MEMBER'))

            menu.append(all_menu_items.get('BLOCK_MEMBER'))

        elif (not is_same_user) and current_user_member_instance.state == member_states.ADMIN:

            if user_member_instance.state == member_states.ADMIN:

                menu = MemberCommunityHelper.add_menu_items_if_current_user_is_admin_and_user_is_admin(
                    current_user_member_instance, community_instance, menu, all_menu_items, is_parent_cm)

            elif user_member_instance.state in [member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]:

                menu = MemberCommunityHelper.add_menu_items_if_current_user_is_admin_and_user_is_non_admin(
                    current_user_member_instance, community_instance, menu, all_menu_items, is_parent_cm)

            else:
                menu.append(all_menu_items.get('REPORT_MEMBER'))

            menu.append(all_menu_items.get('BLOCK_MEMBER'))

        elif (not is_same_user) and current_user_member_instance.state == member_states.MEMBER:

            if (user_member_instance.state == member_states.ADMIN) and user_member_instance.is_owner:
                menu.append(all_menu_items.get('REPORT_MEMBER'))

            else:
                menu.append(all_menu_items.get('REPORT_MEMBER'))

            menu.append(all_menu_items.get('BLOCK_MEMBER'))

        elif is_same_user and (current_user_member_instance.state == member_states.ADMIN):
            menu.append(all_menu_items.get('EDIT_TITLE'))

        return menu

    @staticmethod
    def update_member_profile_menu_for_sdk(user_member_instance, community_instance, current_user_member_instance, menu):

        community = ModelUtilities.get_model_filter(SdkClient, {"community": community_instance, "is_deleted": False})

        if not community:
            return menu

        all_menu_items = {key: {k1: v1 for k1, v1 in value.items()} for key, value in
                          MEMBER_PROFILE_MENU_ITEMS.items()}
        updated_menu = []
        allowed_menu_items = []

        if current_user_member_instance.state == member_states.ADMIN:
            if user_member_instance.state == member_states.ADMIN:
                allowed_menu_items = [
                    all_menu_items.get("REPORT_MEMBER")
                ]

            elif user_member_instance.state == member_states.MEMBER:
                allowed_menu_items = [
                    all_menu_items.get("EDIT_PERMISSIONS"),
                    all_menu_items.get("REMOVE_FROM_COMMUNITY"),
                    all_menu_items.get("REPORT_MEMBER")
                ]

        elif current_user_member_instance.state == member_states.MEMBER:
            if user_member_instance.state == member_states.ADMIN:
                allowed_menu_items = [
                    all_menu_items.get("REPORT_MEMBER")
                ]

            elif user_member_instance.state == member_states.MEMBER:
                allowed_menu_items = [
                    all_menu_items.get("REPORT_MEMBER")
                ]

        allowed_menu_item_titles = [item.get("title") for item in allowed_menu_items]
        for menu_item in menu:
            if menu_item.get("title") in allowed_menu_item_titles:
                updated_menu.append(menu_item)

        return updated_menu

    @staticmethod
    def update_users_image_url_in_community(user_member_filter, image_url, user_intro_card_instance):
        user_member_filter.update(image_url=image_url, updated_at=TimeUtilities.current_time_in_sec())

        if user_intro_card_instance:
            file_filter = ModelUtilities.get_model_filter(Card_Attachment,
                                                          {'collabcard_id': user_intro_card_instance})

            if file_filter:
                card_file_instance = file_filter[0]
                card_file_instance.file_url = image_url
                card_file_instance.save()

            else:
                save_chatroom_attachments(user_intro_card_instance, body={
                    'url': image_url,
                    'type': "image",
                    'index': 1
                })
                ModelUtilities.model_update(Collabcard, {'id': user_intro_card_instance.id},
                                            {'has_files': True, 'attachment_count': 1,
                                             'attachments_uploaded': True})

            update_models_for_syncing_apis(SyncTypes.CHATROOM, {'card': user_intro_card_instance}, {})
    
    @staticmethod
    def get_ordered_collabcard_state_list_based_on_card_ids(user_id, card_ids):

        preserved = Case(*[When(card_id=card_id, then=pos) for pos, card_id in enumerate(card_ids)])
        queryset = collabcardState.objects.filter(card_id__in=card_ids, user_id=user_id).order_by(preserved)

        return queryset

    @staticmethod
    def member_request_dm_limit(user_instance, community_instance, response):
        members_can_dm_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                                {'community': community_instance,
                                                                 'setting_type': community_setting_types.MEMBERS_CAN_DM})

        if all([members_can_dm_filter, not members_can_dm_filter[0].enabled]):
            return get_error_context(False, 'Members cannot initiate direct messages!')

        member_can_dm_right_state = member_rights.MEMBER_RIGHT_ENABLE_MEMBERS_CAN_DM
        user_has_dm_right = check_user_has_member_can_initiate_dm_right(user_instance.id, community_instance.id,
                                                                        member_can_dm_right_state)

        if not user_has_dm_right:
            return get_error_context(False, "You don't have right to DM members!")

        community_dm_settings_filter = ModelUtilities.get_model_filter(CommunityDirectMessageSettings,
                                                                       {'community': community_instance})

        if not community_dm_settings_filter:
            return get_error_context(False, "Community DM settings are not set yet!")

        # Start, end epoch for day
        start_epoch_time = TimeUtilities.get_epoch_time_for_start_of_day_in_millisec(
            TimeUtilities.get_current_datetime())

        end_epoch_time = TimeUtilities.get_epoch_time_for_end_of_day_in_millisec(
            TimeUtilities.get_current_datetime())

        community_dm_settings_instance = community_dm_settings_filter[0]

        if community_dm_settings_instance.state == community_dm_settings_state_types.UNLIMITED:
            return response

        elif community_dm_settings_instance.state == community_dm_settings_state_types.LIMITED:

            if community_dm_settings_instance.duration == community_dm_settings_duration_types.WEEKS:
                start_epoch_time = TimeUtilities.get_epoch_time_for_start_of_day_in_millisec(
                    TimeUtilities.get_week_first_day_in_datetime())
                end_epoch_time = TimeUtilities.get_epoch_time_for_end_of_day_in_millisec(
                    TimeUtilities.get_week_end_day_in_datetime())

            elif community_dm_settings_instance.duration == community_dm_settings_duration_types.MONTHS:
                start_epoch_time = TimeUtilities.get_epoch_time_for_start_of_day_in_millisec(
                    TimeUtilities.get_month_first_day_in_datetime())
                end_epoch_time = TimeUtilities.get_epoch_time_for_end_of_day_in_millisec(
                    TimeUtilities.get_month_last_day_in_datetime())

        else:
            return get_error_context(False, "Invalid state or duration!")

        card_state_filter_object = {
            'community': community_instance,
            'card__is_private': True,
            'card__type': card_types.CARD_DIRECT_MESSAGE,
            'follow_status': True,
            'chat_request_initiated_by': user_instance,
            'user': user_instance,
            'chat_request_created_at__gte': start_epoch_time,
            'chat_request_created_at__lte': end_epoch_time
        }

        card_state_filter = ModelUtilities.get_model_filter(collabcardState, card_state_filter_object)

        if card_state_filter.count() >= community_dm_settings_instance.number_in_duration:
            user_dm_limit = None

            filter_dict = {
                'community': community_instance
            }

            community_dm_settings_filter = ModelUtilities.get_model_filter(CommunityDirectMessageSettings, filter_dict)

            if community_dm_settings_filter:
                context_dict = {
                    'send_community_id': False
                }

                user_dm_limit = CommunityDMSettingsSerializer(community_dm_settings_filter[0],
                                                              context=context_dict).data

            limit_response = {
                'is_request_dm_limit_exceeded': True,
                'new_request_dm_timestamp': end_epoch_time,
                'success': True,
                'user_dm_limit': user_dm_limit
            }

            if response.get('chatroom_id'):
                filter_dict = {
                    'card': response.get('chatroom_id'),
                    'state': conversation_states.ANSWER
                }

                chatroom_user_messages_filter = ModelUtilities.get_model_filter(card_answers, filter_dict)

                if chatroom_user_messages_filter.exists():
                    limit_response['chatroom_id'] = response.get('chatroom_id')

            return limit_response

        return response

    @staticmethod
    def serialise_dm_chatrooms(user_instance, community_instance, card_id, card_ans_id, card_state_map,
                               convsersation_states_to_consider, rights_list, device_id):
        chatroom = {}
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)
        card_state_instance = ModelUtilities.get_model_instance_or_none(collabcardState,
                                                                        card_state_map.get(card_id))
        card_answer_instance = ModelUtilities.get_model_instance_or_none(card_answers, card_ans_id)

        if card_instance:
            chatroom['chatroom'] = get_chatroom_instance(card_instance, user_instance.id, send_profile=False)
            chatroom['is_draft'] = False
            chatroom['custom_tag'] = card_instance.custom_tag

        if card_answer_instance:
            last_conversation_dict = conversationSerializer(card_answer_instance,
                                                            current_user_id=user_instance.id, device_id=device_id)
            preview = generate_internal_link_preview_for_conversation(card_answer_instance, user_instance.id)

            if preview:
                last_conversation_dict['preview'] = preview

            chatroom['last_conversation'] = last_conversation_dict

            if card_state_instance.last_seen_conversation_id:
                unseen_filter = {
                    'id__gt': card_state_instance.last_seen_conversation_id,
                    'card_id': card_instance.id,
                    'state__in': convsersation_states_to_consider
                }

            else:
                unseen_filter = {
                    'card_id': card_instance.id,
                    'state__in': convsersation_states_to_consider
                }

            chatroom['unseen_conversation_count'] = ModelUtilities.get_model_filter(card_answers,
                                                                                    unseen_filter).count()
            chatroom['last_conversation_time'] = get_time_text_for_my_chatrooms(
                TimeUtilities.convert_milliseconds_to_sec(card_answer_instance.created_at))
            chatroom['member_state'] = Members.get_community_member_state(community_instance, user_instance)

            if card_state_instance.chat_request_state:
                chatroom['chat_request_state'] = card_state_instance.chat_request_state

            if card_state_instance.chat_request_created_at:
                chatroom['chat_request_created_at'] = card_state_instance.chat_request_created_at

            if card_state_instance.chat_requested_by:
                chatroom['chat_requested_by'] = get_members_profile([card_state_instance.chat_requested_by],
                                                                    community_instance.id, send_profile=False)

            chatroom['is_private_member'] = card_instance.is_private_member
            chatroom['member_right_states'] = rights_list

        return chatroom

    @staticmethod
    def can_member_dm_from_member_profile(user_instance, member_instance, community_instance):
        dm_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                            {'community': community_instance,
                                                             'setting_type': community_setting_types.DIRECT_MESSAGES})

        if all([dm_setting_filter, not dm_setting_filter[0].enabled]):
            return {'success': True, 'show_dm': False}

        if not member_instance:
            return get_error_context(False, 'Invalid member_id or uuid')

        is_member_admin = Members.get_community_member_state(community_instance, member_instance) == member_states.ADMIN
        is_user_admin = Members.get_community_member_state(community_instance, user_instance) == member_states.ADMIN

        from collabmates_api.chatroom.chatroom_impl import ChatroomHelper
        user_member_dm_chatroom = ChatroomHelper.get_dm_chatroom_from_members(community_instance.id,
                                                                              user_instance.id,
                                                                              member_instance.id)

        if is_user_admin or is_member_admin:
            cta = CTA_ROUTE_DIRECT_MESSAGES_COMMUNITY_DETAIL_MULTIPLE_CM.format(community_instance.id)

            if user_member_dm_chatroom:
                cta = CTA_ROUTE_DIRECT_MESSAGES_MEMBER_PROFILE.format(user_member_dm_chatroom.id,
                                                                      community_instance.id)

            return {'success': True, 'show_dm': True, 'cta': cta}

        else:
            members_can_dm_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                                    {'community': community_instance,
                                                                     'setting_type': community_setting_types.MEMBERS_CAN_DM})

            if all([members_can_dm_filter, not members_can_dm_filter[0].enabled]):
                return {'success': True, 'show_dm': False}

            member_can_dm_right_state = member_rights.MEMBER_RIGHT_ENABLE_MEMBERS_CAN_DM
            user_has_dm_right = check_user_has_member_can_initiate_dm_right(user_instance.id, community_instance.id,
                                                                            member_can_dm_right_state)

            if not user_has_dm_right:
                return {'success': True, 'show_dm': False}

            cta = CTA_ROUTE_DIRECT_MESSAGES_COMMUNITY_DETAIL_MULTIPLE_CM.format(community_instance.id)

            if user_member_dm_chatroom:
                cta = CTA_ROUTE_DIRECT_MESSAGES_MEMBER_PROFILE.format(user_member_dm_chatroom.id,
                                                                      community_instance.id)

            return {'success': True, 'show_dm': True, 'cta': cta}

    @staticmethod
    def can_member_dm_from_community_detail(user_instance, community_instance):
        is_user_admin = Members.get_community_member_state(community_instance, user_instance) == member_states.ADMIN

        if is_user_admin:
            return {'success': True, 'show_dm': False}

        dm_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                            {'community': community_instance,
                                                             'setting_type': community_setting_types.DIRECT_MESSAGES})

        if all([dm_setting_filter, not dm_setting_filter[0].enabled]):
            return {'success': True, 'show_dm': False}

        else:
            cms_list = Members.get_managers_list(community_instance)

            if len(cms_list) == 1:

                from collabmates_api.chatroom.chatroom_impl import ChatroomHelper
                user_member_dm_chatroom = ChatroomHelper.get_dm_chatroom_from_members(community_instance.id,
                                                                                      user_instance.id,
                                                                                      cms_list[0])

                cta = CTA_ROUTE_DIRECT_MESSAGES_COMMUNITY_DETAIL_MULTIPLE_CM.format(community_instance.id)

                if user_member_dm_chatroom:
                    cta = CTA_ROUTE_DIRECT_MESSAGES_MEMBER_PROFILE.format(user_member_dm_chatroom.id,
                                                                          community_instance.id)

                return {'success': True, 'show_dm': True, 'cta': cta}

            else:
                return {'success': True, 'show_dm': True,
                        'cta': CTA_ROUTE_DIRECT_MESSAGES_COMMUNITY_DETAIL_MULTIPLE_CM.format(community_instance.id)}

    @staticmethod
    def can_member_from_dm_feed_or_member_directory(user_instance, community_instance):
        is_user_admin = Members.get_community_member_state(community_instance, user_instance) == member_states.ADMIN

        if is_user_admin:
            return {'success': True, 'show_dm': False}

        members_can_dm_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                                {'community': community_instance,
                                                                 'setting_type': community_setting_types.MEMBERS_CAN_DM})

        if all([members_can_dm_filter, not members_can_dm_filter[0].enabled]):
            return {'success': True, 'show_dm': False}

        member_can_dm_right_state = member_rights.MEMBER_RIGHT_ENABLE_MEMBERS_CAN_DM
        user_has_dm_right = check_user_has_member_can_initiate_dm_right(user_instance.id, community_instance.id,
                                                                        member_can_dm_right_state)

        if not user_has_dm_right:
            return {'success': True, 'show_dm': False}

        return {'success': True, 'show_dm': True,
                'cta': CTA_ROUTE_DIRECT_MESSAGES_DM_FEED.format(community_instance.id)}

    @staticmethod
    def can_member_request_from_dm_feed_v2(user_instance, community_instance):
        response_dict = {
            'success': True,
            'show_dm': False
        }

        dm_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                    {'community': community_instance,
                                                     'setting_type': community_setting_types.DIRECT_MESSAGES})

        if dm_filter and not dm_filter[0].enabled:
            return response_dict

        is_user_admin = Members.get_community_member_state(community_instance, user_instance) == member_states.ADMIN

        response_dict['show_dm'] = True

        if is_user_admin:
            response_dict['cta'] = CTA_ROUTE_DIRECT_MESSAGES_DM_FEED_V2.format(community_instance.id,
                                                                               DMFabShowList.ALL_MEMBERS)
            return response_dict

        filter_dict = {
            'community': community_instance,
            'setting_type': community_setting_types.MEMBERS_CAN_DM
        }

        members_can_dm_filter = ModelUtilities.get_model_filter(CommunitySettings, filter_dict)

        if members_can_dm_filter and not members_can_dm_filter[0].enabled:
            response_dict['cta'] = CTA_ROUTE_DIRECT_MESSAGES_DM_FEED_V2.format(community_instance.id,
                                                                               DMFabShowList.ONLY_CM)

        else:
            member_can_dm_right_state = member_rights.MEMBER_RIGHT_ENABLE_MEMBERS_CAN_DM
            user_has_dm_right = check_user_has_member_can_initiate_dm_right(user_instance.id,
                                                                            community_instance.id,
                                                                            member_can_dm_right_state)

            if not user_has_dm_right:
                response_dict['cta'] = CTA_ROUTE_DIRECT_MESSAGES_DM_FEED_V2.format(community_instance.id,
                                                                                   DMFabShowList.ONLY_CM)

            else:
                response_dict['cta'] = CTA_ROUTE_DIRECT_MESSAGES_DM_FEED_V2.format(community_instance.id,
                                                                                   DMFabShowList.ALL_MEMBERS)

        return response_dict

    @staticmethod
    def can_member_dm_from_dm_chatroom(user_instance, validated_request):
        chatroom_instance = validated_request.get('chatroom_instance')

        if not chatroom_instance:
            return get_error_context(False, 'Invalid chatroom id')

        community_instance = chatroom_instance.community

        response = {'success': True, 'show_dm': False}

        if any([not chatroom_instance.is_private, chatroom_instance.type != card_types.CARD_DIRECT_MESSAGE,
                user_instance not in [chatroom_instance.user, chatroom_instance.chatroom_with_user]]):
            return response

        dm_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                            {'community': community_instance,
                                                             'setting_type': community_setting_types.DIRECT_MESSAGES})

        if all([dm_setting_filter, not dm_setting_filter[0].enabled]):
            return response

        is_user_admin = Members.is_member_community_promoter(community_instance, chatroom_instance.user)
        is_chatroom_with_user_admin = Members.is_member_community_promoter(community_instance,
                                                                           chatroom_instance.chatroom_with_user)

        if is_user_admin or is_chatroom_with_user_admin:
            return {'success': True, 'show_dm': True,
                    'cta': CTA_ROUTE_DIRECT_MESSAGES_MEMBER_PROFILE.format(chatroom_instance.id,
                                                                           community_instance.id)}

        members_can_dm_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                                {'community': community_instance,
                                                                 'setting_type': community_setting_types.MEMBERS_CAN_DM})

        if all([members_can_dm_filter, not members_can_dm_filter[0].enabled]):
            return response

        member_can_dm_right_state = member_rights.MEMBER_RIGHT_ENABLE_MEMBERS_CAN_DM
        user_has_dm_right = check_user_has_member_can_initiate_dm_right(
            chatroom_instance.user_id, community_instance.id, member_can_dm_right_state)

        if user_has_dm_right:
            return {'success': True, 'show_dm': True,
                    'cta': CTA_ROUTE_DIRECT_MESSAGES_MEMBER_PROFILE.format(chatroom_instance.id,
                                                                           community_instance.id)}

        else:
            chatroom_with_user_has_dm_right = check_user_has_member_can_initiate_dm_right(
                chatroom_instance.chatroom_with_user_id, community_instance.id, member_can_dm_right_state)

            if chatroom_with_user_has_dm_right:
                return {'success': True, 'show_dm': True,
                        'cta': CTA_ROUTE_DIRECT_MESSAGES_MEMBER_PROFILE.format(chatroom_instance.id,
                                                                               community_instance.id)}

            return response

    @staticmethod
    def make_requesting_user_as_member_of_community(user_instance, community_instance, req_body, device_id=None,
                                                    platform=None, version_code=None):

        from collabmates_api.community.community_impl import CommunityHelper, CommunityImpl
        from collabmates_api.community.constants import (DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY)

        question_answers_list = req_body.get(DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY)

        if question_answers_list:
            CommunityHelper.save_responses_of_member_in_community(user_instance.id,
                                                                  community_instance.id,
                                                                  question_answers_list,
                                                                  True)

        Members.create_instance({'user_instance': user_instance,
                                 'community_instance': community_instance,
                                 'state': member_states.MEMBER,
                                 'image_url': req_body.get('image_url'),
                                 'custom_title': "Member",
                                 'became_member_at': TimeUtilities.current_time_in_sec()
                                 })

        if req_body.get('image_url'):
            MemberCommunityHelper.update_user_image_in_sdk(user_instance, req_body.get('image_url'))

        ModelUtilities.update_or_create_model(Member_Engage, {
            'member_id': user_instance,
            'community_id': community_instance
        }, {
            'member_state': member_states.MEMBER,
            'order_time': TimeUtilities.current_time_in_milliseconds()})

        from collabmates_api.chatroom.chatroom_impl import ChatroomHelper
        CommunityHelper.set_follow_status_for_announcement_chatroom_for_community(community_instance,
                                                                                  user_instance)

        shared_user_id = None
        auto_join_code = None
        CommunityHelper.set_moderation_rights_and_delete_user_previous_metadata_for_auto_join.delay(
            user_instance.id,
            community_instance.id,
            shared_user_id,
            auto_join_code,
            api_type=api_types.SDK)

        members_count = Members.get_members_count_in_community(community_instance)

        community_impl = CommunityImpl(member_id=user_instance.id, community_id=community_instance.id)
        community_impl.set_members_count_in_community(community_instance.id, members_count)

        ChatroomHelper.update_seen_status_for_older_chatrooms_for_new_member(community_instance, user_instance)

        action_required_by_promoter = ModelUtilities.is_model_filter_exists(Members,
                                                                            {'community_id': community_instance,
                                                                             'state': member_states.ADMIN,
                                                                             'actions_required': True})

        if action_required_by_promoter:
            CommunityHelper.update_community_level_actions(community_instance,
                                                           action_required_by_promoter, members_count)

        is_m2cm_v2 = m2cm_v2_version_check(platform, version_code)

        create_member_dm_chatroom.delay(community_impl.get_member_id(), community_impl.get_community_id(),
                                        device_id=device_id, request_platform=platform, is_joining=True,
                                        is_m2cm_v2=is_m2cm_v2)

        from collabmates_api.cohort.cohort_impl import CohortHelper
        CohortHelper.add_all_member_to_cohort(community_impl.get_community_id(), [community_impl.get_member_id()])

        community_impl._send_join_email_to_member(user_instance.id, community_instance.id)

        CohortHelper.add_member_to_respective_question_based_cohorts(community_impl.get_member_id(),
                                                                     community_impl.get_community_id())

        community_impl.send_join_data_on_webhook.delay(user_instance.id, community_instance.id)

        ElasticSearchSync.update_member.delay(community_impl.get_member_id(), community_impl.get_community_id())
        ElasticSearchSync.update_all_community_chatrooms_for_user.delay(community_instance.id, user_instance.id)

        update_community_get_started(community_instance, get_started_types.INVITE_MEMBERS_TYPE, is_enabled=True)

        CommunityHelper.send_community_moderation_mail_to_cm.delay(community_instance.id)

    @staticmethod
    def get_ordered_home_communities_list_based_on_engage_ids(member_engage_ids):

        preserved = Case(*[When(id=id, then=pos) for pos, id in enumerate(member_engage_ids)])
        queryset = ModelUtilities.get_model_filter(Member_Engage, {"id__in": member_engage_ids}).order_by(preserved)

        return queryset

    @staticmethod
    def get_pinned_chatrooms_in_community_from_cache(community_id):

        key = COMMUNITY_PINNED_CHATROOMS_LIST_CACHE_KEY.format(community_id)
        pinned_chatrooms_list = CacheImpl.get_cache(key)

        if not pinned_chatrooms_list:
            return update_community_pin_chatrooms_list_in_cache({'community_id': community_id})

        else:
            return pinned_chatrooms_list.get('pinned_chatrooms', [])

    @staticmethod
    def update_user_image_in_sdk(user_instance, image_url):

        userinfo_instance = user_instance.userinfo
        previous_image_url = userinfo_instance.image_link
        userinfo_instance.image_link = image_url
        userinfo_instance.updated_at = TimeUtilities.current_time_in_sec()
        userinfo_instance.save()

        update_preview_for_account_image_change.delay({'user_id': user_instance.id,
                                                       'image_url': image_url,
                                                       'previous_image_url': previous_image_url})

    @staticmethod
    def validate_fetch_member_access_request(user_id, api_key, access_type_value):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)
        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)
        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key")

        is_community_member = Members.is_community_member(community_instance, user_instance)
        if not is_community_member:
            return ResponseUtilities.get_inner_error_context("You are not a member of the community")

        member_state = Members.get_community_member_state(community_instance, user_instance)

        valid_access_types = [access_types.CREATE_POST, access_types.VIEW_POST, access_types.DELETE_POST, access_types.EDIT_POST, access_types.EDIT_COMMENT,
                              access_types.PIN_POST, access_types.LIKE_POST, access_types.SAVE_POST,
                              access_types.CREATE_COMMENT, access_types.VIEW_COMMENT, access_types.DELETE_COMMENT,
                              access_types.LIKE_COMMENT, access_types.CREATE_ACTIVITY, access_types.VIEW_ACTIVITY]

        access_type = access_type_value
        if access_type not in valid_access_types:
            return ResponseUtilities.get_inner_error_context("Send valid access type")

        return {'community_instance': community_instance, 'user_instance': user_instance,
                'member_state': member_state, 'access_type': access_type}

    @staticmethod
    def validate_fetch_post_feed_request(user_id, api_key, order_type, chatroom_ids):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)
        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)
        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key")

        is_community_member = Members.is_community_member(community_instance, user_instance)
        if not is_community_member:
            return ResponseUtilities.get_inner_error_context("You are not a member of the community")

        valid_order_types = [feed_order_types.NEWEST_ORDER_TYPE, feed_order_types.RECENTLY_ACTIVE_ORDER_TYPE,
                             feed_order_types.MOST_MESSAGES_ORDER_TYPE, feed_order_types.MOST_PARTICIPANTS_ORDER_TYPE]

        if order_type not in valid_order_types:
            return ResponseUtilities.get_inner_error_context("Invalid order_type")

        chatroom_ids_list = []
        if chatroom_ids and isinstance(chatroom_ids, str):
            try:
                chatroom_ids_list = json.loads(chatroom_ids)
            except:
                return ResponseUtilities.get_inner_error_context("Invalid chatroom_ids object")

        return {'community_instance': community_instance, 'user_instance': user_instance,
                'chatroom_ids': chatroom_ids_list}

    @staticmethod
    def validate_fetch_excluded_chatrooms_request(user_id, api_key):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)
        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)
        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key")

        is_community_member = Members.is_community_member(community_instance, user_instance)
        if not is_community_member:
            return ResponseUtilities.get_inner_error_context("You are not a member of the community")

        return {'community_instance': community_instance, 'user_instance': user_instance}

    @staticmethod
    def validate_fetch_chatroom_home_request(user_id, chatroom_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not chatroom_instance:
            return ResponseUtilities.get_inner_error_context("Invalid chatroom ID")

        engage_filter = ModelUtilities.get_model_filter(conversationEngage, {'card': chatroom_instance,
                                                                             'user': user_instance})

        if not engage_filter:
            return ResponseUtilities.get_inner_error_context('User is not following the chatroom!')

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance,
            'engage_instance': engage_filter[0]
        }

    @staticmethod
    def validate_fetch_user_chatroom_status_request(user_id, api_key, member_id, uuid: str = None):
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')

        if not Members.is_member_community_promoter(community_instance, user_instance):
            return ResponseUtilities.get_inner_error_context("You are not CM/Owner of community!")

        # If uuid is passed, get valid member instance
        if uuid:
            valid_id = ModelUtilities.get_valid_user_ids_from_uuids([uuid], community_instance.id)

            if not valid_id:
                return ResponseUtilities.get_inner_error_context("Invalid uuid!")
            
            member_id = valid_id[0]

        member_instance = ModelUtilities.get_user_instance_or_none(member_id)

        if not member_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user_id or uuid!")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'member_instance': member_instance
        }

    @staticmethod
    def validate_fetch_user_home_meta_request(user_id, api_key):
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')

        return {
            'user_instance': user_instance,
            'community_instance': community_instance
        }
