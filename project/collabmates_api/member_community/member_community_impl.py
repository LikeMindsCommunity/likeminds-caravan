from django.contrib.auth.models import User
from rest_framework.utils import json
from django.db.models import Q

from external_services.caching.cache_impl import CacheImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.celery_tasks import update_chatroom_conversation_count_in_cache, \
    update_chatroom_conversation_creators_in_cache
from utility.constants import CONVERSATIONS_COUNT_CACHE_KEY, CONVERSATIONS_DISTINCT_CREATORS_KEY
from utility.number_utilities import NumberUtilities
from utility.string_utilities import StringUtilities
from .constants import ACTIVE_USER_LIMIT, CHATROOM_COUNT_LIMIT, INVITE_MEMBERS, NEW_CHATROOM, DIRECTORY, PINNED, \
    COMMUNITY_DETAILS, INVITE_MEMBERS_ROUTE, NEW_CHATROOM_ROUTE, DIRECTORY_ROUTE, PINNED_ROUTE, COMMUNITY_DETAILS_ROUTE, \
    PINNED_TOP_BAR_TITLE, PINNED_TOP_BAR_IMAGE, CUSTOM_INTRO_TEXT_LEFT, CUSTOM_CLICK_TEXT_LEFT, \
    CUSTOM_INTRO_TEXT_DELETED, CUSTOM_CLICK_TEXT_DELETED, MEMBER_COMMUNITY_PROFILE_ROUTE, MEMBER_SINCE_TEXT
from .member_community_manager import MemberCommunityManager
from .constants import FEED_UPWARD_SCROLL, FEED_DOWNWARD_SCROLL
from ..raw_queries import fetch_chatroom_polls, fetch_member_poll_votes, get_members_based_on_user_list_query
from ..user_moderation_rights import check_admin_approve_right
from ..utility import pagination
from ..views import get_home_screen_community_actions, get_active_chatroom_member_images
from ..rest_api import CommunitySerializerV1
from ..serializers import get_user_profile, get_members_profile, get_collabcard_files, get_removed_member_custom_text, \
    CollabcardPollsSerializer, get_preview_for_url
from ..static_files import REMOVED_USER_URL

from togther.models import Member_Engage, Community, Members, collabcardState, ModelUtilities, removedMembers, \
    CollabcardPolls, MemberPollVotes, Collabcard, card_answers

from utility.utils import create_notification_flag
from utility.time_utilities import TimeUtilities
from utility.states import member_states, card_types, poll_types, deleted_members, chatroom_states

error_logger = LoggingWrapper.get_instance()


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

    @staticmethod
    def add_chatroom_count_and_member_images(member_community: dict, community: {}, member_id: str) -> None:

        if member_community['collabcard_unseen'] > 0 and \
                community.new_chatroom_users:
            member_community['new_chatroom_users'] = json.loads(community.new_chatroom_users)
        else:
            chatroom_dict = MemberCommunityHelper.get_chatroom_count_member_images(
                community_instance=community.community_id, member_id=member_id)

            member_community['chatroom_count'] = chatroom_dict['count']
            chatroom_users = chatroom_dict['member_list']

            if chatroom_users:
                member_community['chatroom_users'] = chatroom_users

    def _process_communities(self, community_list) -> []:

        member_communities_additional_info = list()

        for community in community_list:
            member_community = self._community_serializer(community.community_id, self.get_member_id())
            self._add_admin_info(member_community, community)
            self._add_community_actions(member_community, community)
            self._add_unseen_count_info(member_community, community)
            self._add_member_rights_info(member_community, community)
            self._add_additional_keys(member_community, community)
            self.add_chatroom_count_and_member_images(member_community, community, self.get_member_id())
            member_communities_additional_info.append(member_community)

        return member_communities_additional_info

    def fetch_home_communities(self, page) -> {}:

        user_instance = User.get_user_or_none(self.get_member_id())

        if not user_instance:
            return {'error_message': "Invalid user id", 'status': 400}

        communities = self._find_member_communities(self.get_member_id())
        community_list = self._paged_queryset(communities, page)
        community_list = self._process_communities(community_list)

        return {'your_communities': community_list}

    def fetch_community_chatrooms_queryset_without_last_seen(self, pin_status) -> []:

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user'). \
                exclude(card__type=card_types.CARD_INTRO).order_by('card_id')
        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user'). \
                exclude(card__type=card_types.CARD_INTRO).order_by('card_id')

        return chatroom_queryset

    def fetch_community_chatrooms_queryset_with_last_seen_chatroom(self, pin_status, last_seen_id, limit_size=5) -> []:

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               user=self.get_member_id(),
                                                               card__id__gte=last_seen_id).select_related('card',
                                                                                                          'card__user'). \
                                    exclude(card__type=card_types.CARD_INTRO).order_by('card_id')[:limit_size]
        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               user=self.get_member_id(),
                                                               card__id__gte=last_seen_id).select_related('card',
                                                                                                          'card__user'). \
                                    exclude(card__type=card_types.CARD_INTRO).order_by('card_id')[:limit_size]

        return chatroom_queryset

    def fetch_chatroom_queryset_for_web(self, pin_status):

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user'). \
                exclude(card__type=card_types.CARD_INTRO).order_by('-card__pinning_time')
        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               user=self.get_member_id()).select_related('card',
                                                                                                         'card__user'). \
                exclude(card__type=card_types.CARD_INTRO).order_by('-card_id')

        return chatroom_queryset

    def create_chatroom_preview(self, card_instance):

        preview = {}

        if card_instance.internal_link:
            try:
                preview = get_preview_for_url(self.get_member_id(), card_instance.internal_link,
                                              community_instance=card_instance.preview_community,
                                              chatroom_instance=card_instance.preview_chatroom,
                                              send_preview_text=False)
            except Exception as e:
                error_logger.error(e.args)

        return preview

    def last_seen_chatroom_query(self, pin_status) -> []:

        if pin_status:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               card__is_pinned=pin_status,
                                                               user=self.get_member_id()).exclude(
                card__type=card_types.CARD_INTRO).filter(~Q(state=0)).only('card').order_by('-card_id')
        else:
            chatroom_queryset = collabcardState.objects.filter(community=self.get_community_id(),
                                                               card__is_pending=False,
                                                               card__is_deleted=False,
                                                               user=self.get_member_id()).exclude(
                card__type=card_types.CARD_INTRO).filter(~Q(state=0)).only('card').order_by('-card_id')

        return chatroom_queryset[:1]

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
    def fetch_chatroom_files(card_instance) -> {}:

        chatroom_files = {}
        collabcard_files = get_collabcard_files(card_instance.id)
        chatroom_files['images'] = collabcard_files[0]
        chatroom_files['pdf'] = collabcard_files[1]
        chatroom_files['audios'] = collabcard_files[2]
        chatroom_files['videos'] = collabcard_files[3]
        chatroom_files['attachments'] = collabcard_files[4]

        return chatroom_files

    @staticmethod
    def fetch_members_based_on_user_list(user_list, community_instance) -> {}:

        member_dict = {}
        member_list = get_members_based_on_user_list_query(user_list, community_instance.id)
        community_name = community_instance.name

        for data in member_list:

            if not member_dict.get(data['member_id']):
                member = {
                    'id': data['member_id'],
                    'name': data['name'],
                    'state': data['state'],
                    'is_owner': data['is_owner'],
                    'community_id': data['community_id'],
                    'route': MEMBER_COMMUNITY_PROFILE_ROUTE % (str(data['community_id']), str(data['member_id'])),
                    'member_since': MEMBER_SINCE_TEXT % (community_name,
                                                         TimeUtilities.convert_epoch_time_to_date_with_mon_day_year(
                                                             data['created_at']))
                }

                if data['image_url']:
                    image_url = data['image_url']

                elif data['image_link']:
                    image_url = data['image_link']
                else:
                    image_url = ""

                member['image_url'] = image_url

                if data['custom_title'] and not data['custom_title'] == 'Member':
                    member['custom_title'] = data['custom_title']

                member_dict[data['member_id']] = member

        return member_dict

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
                                      .filter(card=card_instance, state=chatroom_states.ANSWER) \
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

        temp['remove_state'] = remove_state
        temp['removed_user_image_url'] = REMOVED_USER_URL

        return temp

    def compute_removed_user_context(self, user_instance, community_instance) -> {}:

        remove_filter = ModelUtilities.get_model_filter(removedMembers, {'community': community_instance,
                                                                         'member_id': user_instance})
        remove_member = {}

        userinfo_instance = user_instance.userinfo
        remove_member['id'] = userinfo_instance.id
        remove_member['name'] = userinfo_instance.name
        remove_member['image_link'] = userinfo_instance.image_link if userinfo_instance.image_link else ""

        if remove_filter:
            temp = self.create_removed_members_custom_text(remove_filter[0], userinfo_instance)
            remove_member['custom_intro_text'] = temp['custom_intro_text']
            remove_member['custom_click_text'] = temp['custom_click_text']
            remove_member['remove_state'] = temp['remove_state']
            remove_member['image_url'] = temp['removed_user_image_url']

        return remove_member

    def compute_co_host_of_chatroom_events(self, co_host_list, community_instance) -> []:

        co_hosts = []
        member_dict = self.fetch_members_based_on_user_list(co_host_list, community_instance)

        for data in co_host_list:
            user_id = NumberUtilities.get_integer_from_string(data)

            if user_id in member_dict:
                co_hosts.append(member_dict[user_id])

        return co_hosts

    @staticmethod
    def fetch_poll_id_list(chatroom_list):
        poll_list = []

        for data in chatroom_list:
            card_instance = data.card

            if card_instance.type == card_types.CARD_POLL:
                poll_list.append(card_instance.id)

        return poll_list

    @staticmethod
    def process_poll_list(poll_list):

        poll_data = {}
        poll_votes = {}

        if poll_list:
            poll_data = fetch_chatroom_polls(poll_list)
            poll_votes = fetch_member_poll_votes(poll_list)

        return poll_data, poll_votes

    @staticmethod
    def process_poll(poll_data, chatroom_id, poll_votes, is_multi, member_id):

        chatroom_poll_data = poll_data.get(chatroom_id)
        chatroom_votes = poll_votes.get(chatroom_id)

        if not chatroom_poll_data:
            chatroom_poll_data = []

        if not chatroom_votes:
            chatroom_votes = []

        total_votes = len(chatroom_votes)
        polls = []

        for data in chatroom_poll_data:

            poll_id = data['id']
            member_set = set()
            count = 0
            total_member_set = set()
            temp = {}
            temp['id'] = poll_id
            temp['text'] = data['text']
            temp['is_selected'] = False
            temp['member'] = data['member']
            if total_votes == 0:
                temp['no_votes'] = 0
                temp['percentage'] = 0
                polls.append(temp)
                continue
            for member in chatroom_votes:

                if member['user_id'] not in total_member_set:
                    total_member_set.add(member['user_id'])

                if member['poll_id'] == poll_id:
                    count = count + 1
                    if member['user_id'] not in member_set:
                        if member['user_id'] == int(member_id):
                            temp['is_selected'] = True
                        member_set.add(member['user_id'])

            if is_multi:
                count = len(member_set)
                total_votes = len(total_member_set)

            temp['no_votes'] = count

            temp['percentage'] = int((count / total_votes) * 100)

            polls.append(temp)

        return polls

    @staticmethod
    def compute_total_response_count(card_instance):

        key = CONVERSATIONS_COUNT_CACHE_KEY % str(card_instance.id)

        conversation_count = CacheImpl.get_cache(key)

        if conversation_count:
            return conversation_count['total_responses_count']
        else:
            conversations_count = card_answers.objects.filter(card=card_instance.id,
                                                              state=chatroom_states.ANSWER).filter(Q(attachment_count=0)
                                                                                                   | Q(
                attachments_uploaded=True)).count()
            update_chatroom_conversation_count_in_cache({'chatroom_id': card_instance.id,
                                                         'total_responses_count': conversations_count})

            return conversations_count

    def create_last_response_members_images(self, card_instance, community_instance):

        conversation_members = []

        user_list = self.compute_user_id_list_of_conversation_creators(card_instance)
        member_dict = self.fetch_members_based_on_user_list(user_list, community_instance)

        for user_id in user_list:

            member_data = {}

            member = member_dict.get(user_id)

            if member:
                member_data = member
                member_data['chatroom_id'] = card_instance.id

            else:
                user_instance = User.get_user_or_none(user_id)

                if not user_instance:
                    continue

                userinfo_instance = user_instance.userinfo

                if user_instance:
                    member_dict = {
                        'id': user_instance.id,
                        'name': userinfo_instance.name,
                        'image_url': userinfo_instance.image_link
                    }

            conversation_members.append(member_data)

        return conversation_members

    def process_chatroom(self, card_instance, state_instance, community_instance, poll_data,
                         poll_votes) -> {}:

        chatroom_context = MemberCommunityHelper.serialize_chatroom(card_instance)
        chatroom_context['community_name'] = community_instance.name

        if NumberUtilities.get_integer_from_string(self.get_member_id()) == card_instance.user.id:
            chatroom_context['has_been_named'] = card_instance.has_been_named
            chatroom_context['member_id'] = card_instance.user.id

        state_context = MemberCommunityHelper.serialize_chatroom_user_actions(state_instance)

        if card_instance.attachment_count > 0:
            chatroom_files = self.fetch_chatroom_files(card_instance)
            chatroom_context.update(chatroom_files)

        if card_instance.type == card_types.CARD_POLL:
            poll_serializer = MemberCommunityHelper.serialize_poll_chatroom(card_instance, self.get_member_id())
            polls = self.process_poll(poll_data, card_instance.id, poll_votes,
                                      poll_serializer.get('multiple_select_no'),
                                      self.get_member_id())

            if polls:
                poll_serializer['polls'] = polls

            chatroom_context.update(poll_serializer)

        if card_instance.type == card_types.CARD_EVENT or card_instance.type == card_types.CARD_PUBLIC_EVENT:
            co_host_list = chatroom_context.get('co_hosts') if chatroom_context.get('co_hosts') else []

            co_hosts = self.compute_co_host_of_chatroom_events(co_host_list, community_instance)

            if co_hosts:
                chatroom_context['co_hosts'] = co_hosts

        chatroom_context.update(state_context)

        preview = self.create_chatroom_preview(card_instance)

        if preview:
            chatroom_context['preview'] = preview

        chatroom_context['total_response_count'] = self.compute_total_response_count(card_instance)

        if chatroom_context['total_response_count']:
            chatroom_context['last_response_members'] = self.create_last_response_members_images(card_instance,
                                                                                                 community_instance)

        return chatroom_context

    def process_chatroom_list(self, chatroom_list, community_instance) -> []:

        chatroom_context_list = []
        user_list = self.compute_user_id_list_of_chatroom_creators(chatroom_list)
        member_dict = self.fetch_members_based_on_user_list(user_list, community_instance)
        poll_list = self.fetch_poll_id_list(chatroom_list)
        poll_data, poll_votes = self.process_poll_list(poll_list)

        removed_member_dict = {}

        for data in chatroom_list:
            card_instance = data.card
            state_instance = data
            card_creator_id = card_instance.user.id
            chatroom_context = self.process_chatroom(card_instance, state_instance, community_instance
                                                     , poll_data, poll_votes)
            if card_creator_id in member_dict:
                chatroom_context['member'] = member_dict[card_creator_id]

            else:

                if card_creator_id in removed_member_dict:
                    chatroom_context['member'] = removed_member_dict.get(card_creator_id)
                else:
                    chatroom_context['member'] = self.compute_removed_user_context(card_instance.user,
                                                                                   community_instance)
                    removed_member_dict[card_creator_id] = chatroom_context['member']

            chatroom_context_list.append(chatroom_context)

        return chatroom_context_list

    def fetch_feed(self, pin_status, chatroom_id=None, scroll_direction=None) -> {}:

        community_instance = Community.get_community_or_None(self.get_community_id())
        chatroom_list = []
        chatroom_context_list = []
        if not community_instance:
            return {'error_message': "Invalid community_id", 'status': 400}

        if not chatroom_id and not scroll_direction:

            last_seen_chatroom = self.last_seen_chatroom_query(pin_status)

            if not last_seen_chatroom:
                chatroom_queryset = self.fetch_community_chatrooms_queryset_without_last_seen(pin_status)
                chatroom_list = self.extract_chatrooms_without_scroll(chatroom_queryset, limit_size=5)

            else:
                last_seen_chatroom_id = last_seen_chatroom[0].card_id
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

        chatroom_context_list = self.process_chatroom_list(chatroom_list, community_instance)

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

            chatroom_queryset = self.fetch_community_chatrooms_queryset_without_last_seen(pin_status)
            chatroom_list = self.extract_chatrooms_on_scroll(chatroom_id, scroll_direction, chatroom_queryset,
                                                             limit_size=5)

        chatroom_context_list = self.process_chatroom_list(chatroom_list, community_instance)

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
                                                                        'is_pinned': True, 'is_deleted': False}). \
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

        user_instance = User.get_user_or_none(self.get_member_id())

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
    def get_chatroom_count_member_images(community_instance, member_id) -> {}:

        state_filter = collabcardState.objects.filter(
            community=community_instance, user=member_id, card__is_deleted=False
        ).exclude(card__type=card_types.CARD_INTRO).select_related('card').order_by('-expiry_time', '-card')

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

            if len(member_list) > CHATROOM_COUNT_LIMIT:
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
    def compute_card_poll_answer_text(card_instance, current_user_id) -> str:

        current_user_vote_exists = ModelUtilities.is_model_filter_exists(MemberPollVotes, {'card': card_instance,
                                                                                           'user__id': current_user_id})

        total_users = ModelUtilities.get_model_filter(MemberPollVotes,
                                                      {'card': card_instance}).values('user').distinct().count()

        poll_text = "Be the first one to vote"

        if current_user_vote_exists:

            if total_users > 1:

                if total_users == 2:
                    poll_text = f"You and 1 other voted"

                else:
                    poll_text = f"You and {total_users - 1} others voted"

            elif total_users == 1:
                poll_text = f"You voted on this poll"

        elif total_users > 0:

            if total_users == 1:
                poll_text = "1 member voted"

            else:
                poll_text = f"{total_users} members voted"

        return poll_text

    @staticmethod
    def serialize_poll_chatroom(card_instance, current_user_id):

        poll_context = {}
        poll_context["answer_text"] = MemberCommunityHelper.compute_card_poll_answer_text(card_instance,
                                                                                          current_user_id)

        if card_instance.multiple_select:
            poll_context['multiple_select'] = card_instance.multiple_select

        if card_instance.multiple_select_no is not None:
            poll_context['multiple_select_no'] = card_instance.multiple_select_no
        if card_instance.multiple_select_state is not None:
            poll_context['multiple_select_state'] = card_instance.multiple_select_state

        poll_context['is_anonymous'] = card_instance.is_poll_anonymous
        poll_context['allow_add_option'] = card_instance.allow_add_option
        poll_context['poll_type'] = card_instance.poll_type
        poll_context[
            'poll_type_text'] = "Instant poll" if card_instance.poll_type == poll_types.POLL_TYPE_INSTANT else "Deferred poll"
        poll_context['submit_type_text'] = "Secret voting" if card_instance.is_poll_anonymous else "Public voting"

        poll_context['expiry_time'] = card_instance.end_date

        return poll_context

    @staticmethod
    def serialize_chatroom(card_instance) -> {}:

        chatroom_context = {'id': card_instance.id,
                            'title': card_instance.title,
                            'community_id': card_instance.community_id,
                            'answer_text': card_instance.answer_text,
                            'share_link': card_instance.share_link,
                            'image_count': card_instance.image_count,
                            'pdf_count': card_instance.pdf_count,
                            'video_count': card_instance.video_count,
                            'audio_count': card_instance.audio_count,
                            'attachment_count': card_instance.attachment_count,
                            'attachments_uploaded': card_instance.attachments_uploaded,
                            'type': card_instance.type,
                            'date_time': card_instance.date_time,
                            'duration': card_instance.duration,
                            'is_pending': card_instance.is_pending,
                            'answers_count': card_instance.answers_count,
                            'attending_count': card_instance.attending_count,
                            'polls_count': card_instance.polls_count,
                            'date_epoch': card_instance.date_epoch,
                            'header': MemberCommunityHelper.get_card_header(card_instance),
                            'date': TimeUtilities.convert_epoch_time_in_date(card_instance.date_epoch),
                            'created_at': TimeUtilities.convert_epoch_time_in_hh_mm(card_instance.date_epoch),
                            'card_creation_time': TimeUtilities.convert_epoch_time_in_hh_mm_am_pm(
                                card_instance.date_epoch)}

        if card_instance.og_tags:
            chatroom_context['og_tags'] = json.loads(card_instance.og_tags)

        if card_instance.location:
            chatroom_context['location'] = card_instance.location

        if card_instance.location_lat:
            chatroom_context['location_lat'] = card_instance.location_lat

        if card_instance.location_long:
            chatroom_context['location_long'] = card_instance.location_long

        if card_instance.start_date:
            chatroom_context['start_date'] = card_instance.start_date

        if card_instance.end_date:
            chatroom_context['end_date'] = card_instance.end_date

        if card_instance.about:
            chatroom_context['about'] = card_instance.about

        if card_instance.co_hosts:

            try:
                co_host_list = json.loads(card_instance.co_hosts)
            except Exception as e:
                co_host_list = []

            chatroom_context['co_hosts'] = co_host_list

        if card_instance.online_link:
            chatroom_context['online_link'] = card_instance.online_link

        return chatroom_context

    @staticmethod
    def serialize_chatroom_user_actions(state_instance) -> {}:

        chatroom_user_actions = {}

        chatroom_user_actions['state'] = state_instance.state
        chatroom_user_actions['mute_status'] = state_instance.mute_status
        chatroom_user_actions['follow_status'] = state_instance.follow_status
        chatroom_user_actions['attending_status'] = state_instance.attending_status
        chatroom_user_actions['is_guest'] = state_instance.is_guest
        chatroom_user_actions['active'] = False
        chatroom_user_actions['is_tagged'] = state_instance.is_tagged
        expiry_time = state_instance.expiry_time

        if not expiry_time or expiry_time >= TimeUtilities.current_time_in_sec():
            chatroom_user_actions['active'] = True

        return chatroom_user_actions
