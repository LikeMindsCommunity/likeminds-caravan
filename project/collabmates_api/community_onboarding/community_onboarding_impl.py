from django.db.models import Q
from utility.states import card_types

from utility.time_utilities import TimeUtilities

from .community_onboarding_manager import OnboardingManager
from django.contrib.auth.models import User
from togther.models import Collabcard, collabcardState, Userinfo, Community, ModelUtilities
from ..member_community.member_community_impl import MemberCommunityImpl, MemberCommunityHelper
from ..raw_queries import get_recent_n_days_conversation_chatroom_list, \
    get_n_percentage_member_conversation_chatroom_list
from .constants import LAST_N_DAYS_DURATION, CHATROOMS_LIMIT, N_PERCENTAGE


class OnboardingImpl(OnboardingManager):
    community_id = None

    def __init__(self, community_id: str):
        self.community_id = community_id

    def get_community_id(self):
        return self.community_id

    def set_community_id(self, community_id):
        self.community_id = community_id

    def _create_chatroom_list_for_pinned_chatrooms_for_community_onboarding(self, user_instance) -> []:

        chatroom_queryset = collabcardState.objects.filter(
            community=self.get_community_id(),
            card__is_pending=False,
            card__is_deleted=False,
            card__is_pinned=True,
            secret_chatroom_left=False,
            user=user_instance,
        ).select_related('card', 'card__user'
                         ).exclude(Q(card__type=card_types.CARD_INTRO)
                                   | Q(card__type=card_types.CARD_PURPOSE)
                                   | Q(card__type=card_types.CARD_MASTER_INTRO)).order_by('-card__pinning_time')

        return chatroom_queryset

    def _create_chatroom_list_for_poll_chatrooms_for_community_onboarding(self, user_instance) -> []:

        chatroom_queryset = collabcardState.objects.filter(
            community=self.get_community_id(),
            card__is_pending=False,
            card__is_deleted=False,
            secret_chatroom_left=False,
            card__is_pinned=False,
            user=user_instance,
            card__type=card_types.CARD_POLL,
            card__end_date__gte=TimeUtilities.current_time_in_milliseconds()

        ).select_related('card', 'card__user').order_by('-card__date_epoch')

        return chatroom_queryset

    def _create_chatroom_list_for_event_chatrooms_for_community_onboarding(self, user_instance) -> []:

        chatroom_queryset = collabcardState.objects.filter(
            community=self.get_community_id(),
            card__is_pending=False,
            card__is_deleted=False,
            secret_chatroom_left=False,
            user=user_instance,
            card__end_date__gte=TimeUtilities.current_time_in_milliseconds(),
        ).filter(Q(card__type=card_types.CARD_EVENT)
                 | Q(card__type=card_types.CARD_PUBLIC_EVENT)).select_related('card'
                                                                              , 'card__user').order_by('card__end_date')
        return chatroom_queryset

    def _create_chatroom_list_for_conversation_chatrooms(self, user_instance, card_list) -> []:

        chatroom_queryset = collabcardState.objects.filter(
            community=self.get_community_id(),
            card__is_pending=False,
            card__is_deleted=False,
            secret_chatroom_left=False,
            card__is_pinned=False,
            user=user_instance,
            card_id__in=card_list,
        ).select_related('card', 'card__user').order_by('-updated_at')

        return chatroom_queryset

    def compute_n_percentage_members_count(self, community_instance) -> int:

        members_count_dict = MemberCommunityHelper.fetch_community_members_count([community_instance.id])
        members_count = members_count_dict.get(community_instance.id, 0)
        members_count = (N_PERCENTAGE * members_count) // 100

        return members_count

    def fetch_pinned_chatrooms(self, user_id, page_no, page_size) -> {}:
        user_instance = User.get_user_or_none(user_id)

        if not user_instance:
            return {'error_message': "In-correct user id"}

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "In-correct community id"}

        member_community_manager = MemberCommunityImpl(member_id=user_instance.id,
                                                       community_id=community_instance.id)

        chatroom_list = self._create_chatroom_list_for_pinned_chatrooms_for_community_onboarding(
            user_instance)

        chatroom_list = ModelUtilities.paginate_queryset(chatroom_list, page_no, paginate_by=page_size)
        chatroom_context_list = member_community_manager.process_chatroom_list(chatroom_list, community_instance)

        return {'chatrooms': chatroom_context_list}

    def fetch_poll_chatrooms(self, user_id, page_no, page_size) -> {}:
        user_instance = User.get_user_or_none(user_id)

        if not user_instance:
            return {'error_message': "In-correct user id"}

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "In-correct community id"}

        member_community_manager = MemberCommunityImpl(member_id=user_instance.id,
                                                       community_id=community_instance.id)

        chatroom_list = self._create_chatroom_list_for_poll_chatrooms_for_community_onboarding(
            user_instance)

        chatroom_list = ModelUtilities.paginate_queryset(chatroom_list, page_no, paginate_by=page_size)
        chatroom_context_list = member_community_manager.process_chatroom_list(chatroom_list, community_instance)

        return {'chatrooms': chatroom_context_list}

    def fetch_event_chatrooms(self, user_id, page_no, page_size) -> {}:
        user_instance = User.get_user_or_none(user_id)

        if not user_instance:
            return {'error_message': "In-correct user id"}

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "In-correct community id"}

        member_community_manager = MemberCommunityImpl(member_id=user_instance.id,
                                                       community_id=community_instance.id)

        chatroom_list = self._create_chatroom_list_for_event_chatrooms_for_community_onboarding(
            user_instance)

        chatroom_list = ModelUtilities.paginate_queryset(chatroom_list, page_no, paginate_by=page_size)
        chatroom_context_list = member_community_manager.process_chatroom_list(chatroom_list, community_instance)

        return {'chatrooms': chatroom_context_list}

    def recent_n_days_conversation_chatrooms(self, user_id, page_no, page_size) -> {}:
        user_instance = User.get_user_or_none(user_id)

        if not user_instance:
            return {'error_message': "In-correct user id"}

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "In-correct community id"}

        member_community_manager = MemberCommunityImpl(member_id=user_instance.id,
                                                       community_id=community_instance.id)

        duration = TimeUtilities.current_time_in_milliseconds() - LAST_N_DAYS_DURATION
        card_list = get_recent_n_days_conversation_chatroom_list(community_instance.id,
                                                                 duration, limit=CHATROOMS_LIMIT)
        chatroom_list = self._create_chatroom_list_for_conversation_chatrooms(user_instance, card_list)
        chatroom_list = ModelUtilities.paginate_queryset(chatroom_list, page_no, paginate_by=page_size)
        chatroom_context_list = member_community_manager.process_chatroom_list(chatroom_list, community_instance)

        return {'chatrooms': chatroom_context_list}

    def n_percentage_member_conversation_chatrooms(self, user_id, page_no, page_size) -> {}:
        user_instance = User.get_user_or_none(user_id)

        if not user_instance:
            return {'error_message': "In-correct user id"}

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "In-correct community id"}

        member_community_manager = MemberCommunityImpl(member_id=user_instance.id,
                                                       community_id=community_instance.id)

        percentage_count = self.compute_n_percentage_members_count(community_instance)

        card_list = get_n_percentage_member_conversation_chatroom_list(community_instance.id, percentage_count,
                                                                       limit=CHATROOMS_LIMIT)
        chatroom_list = self._create_chatroom_list_for_conversation_chatrooms(user_instance, card_list)
        chatroom_list = ModelUtilities.paginate_queryset(chatroom_list, page_no, paginate_by=page_size)
        chatroom_context_list = member_community_manager.process_chatroom_list(chatroom_list, community_instance)

        return {'chatrooms': chatroom_context_list}
