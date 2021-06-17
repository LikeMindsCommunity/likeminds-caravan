import json

from celery import shared_task
from django.contrib.auth.models import User

from collabmates_api.community.constants import MENU, COMMUNITY_REJECT_TOAST, LEVEL_3_TITLE, LEVEL_3_SUB_TITLE, \
    LEVEL_4_TITLE, LEVEL_4_SUB_TITLE
from collabmates_api.branch import create_community_feed_url, create_community_otl_url
from collabmates_api.community.constants import MENU
from collabmates_api.rest_api import CommunitySerializerV1
from collabmates_api.user_moderation_rights import check_admin_edit_community_right
from collabmates_api.views import get_leave_community_text, send_notification_for_join_requests, \
    give_default_member_rights
from django.db.models import Q, F

from external_services.mixpanel.events import MixpanelEvents
from togther.models import Community, Userinfo, Collabcard, Members, ModelUtilities, CommunityUserDelete, \
    card_answers, collabcardState, Member_Engage, communityAnswers, removedMembers, communityToast, userMobiles, \
    communityLevels, conversationEngage, userMemberRights, moderationHistory

from collabmates_api.community.community_manager import CommunityManager
from collabmates_api.member_community.member_community_impl import MemberCommunityImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.states import member_states, card_types, click_states, member_rights, mobile_states, \
    community_level_states, moderation_history_types, question_states
from utility.time_utilities import TimeUtilities
from utility.utils import check_notification_flag, get_first_name_from_name
from ..chatroom.chatroom_impl import ChatroomImpl, ChatroomHelper
from ..mails import send_8am_level_mails_to_admin_scheduler
from ..search.sync import ElasticSearchSync

from ..tasks import send_community_confirmation_email
from ..sms import send_community_confirmation_sms

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class CommunityImpl(CommunityManager):
    member_id = None
    community_id = None

    def __init__(self, member_id: str, community_id: str = None):

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
            menu = MENU['pending_member_in_paid_community'] if community_instance.is_paid else MENU['pending_member']

        elif state == member_states.MEMBER or state == member_states.PROFILE_UNAVAILABLE:
            menu = MENU['member']

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

    @staticmethod
    def update_pending_members_after_request_accept_or_reject(community_instance):

        pending_members = Members.get_pending_members(community_instance)
        pending_members_count = len(pending_members)

        ModelUtilities.model_update(Member_Engage, {'community_id': community_instance,
                                                    'member_state': member_states.ADMIN},
                                    {'pending_members': pending_members_count})

    def decline_community_join_request(self, community_instance, user_instance):

        ModelUtilities.delete_record_in_model(Members, {'member_id': user_instance.id,
                                                        'community_id': community_instance.id})

        ModelUtilities.delete_record_in_model(Member_Engage, {'member_id': user_instance.id,
                                                              'community_id': community_instance.id})

        ModelUtilities.delete_record_in_model(communityAnswers, {'member_id': user_instance.id,
                                                                 'community_id': community_instance.id})

        ModelUtilities.model_update(communityToast, {'community': community_instance.id,
                                                     'user': user_instance.id},
                                    {'toast_message': COMMUNITY_REJECT_TOAST})

        self.update_pending_members_after_request_accept_or_reject(community_instance)

    def approve_community_join_request(self, community_instance, user_instance, promoter_instance):

        ModelUtilities.model_update(
            Members,
            {"member_id": user_instance, "community_id": community_instance},
            {
                "state": member_states.MEMBER,
                "approved_by": promoter_instance,
                "custom_title": "Member",
                "created_at": TimeUtilities.current_time_in_sec(),
                "updated_at": TimeUtilities.current_time_in_sec(),
                "became_member_at": TimeUtilities.current_time_in_sec(),
            }
        )
        ModelUtilities.model_update(
            Member_Engage,
            {"community_id": community_instance, "member_id": user_instance},
            {
                "click_state": click_states.DEFAULT,
                "member_state": member_states.MEMBER,
                "updated_at": TimeUtilities.current_time_in_sec(),
                "rights_list": json.dumps(member_rights.DEFAULT_MEMBER_RIGHTS),
            }
        )
        ModelUtilities.model_update(collabcardState,
                                    {'community': community_instance, 'user': user_instance},
                                    {'is_guest': False, 'remove': None,
                                     'updated_at': TimeUtilities.current_time_in_sec()})

        ModelUtilities.model_update(card_answers,
                                    {'community': community_instance, 'user': user_instance},
                                    {'is_guest': False, 'remove': None,
                                     'last_updated': TimeUtilities.current_time_in_milliseconds()})
        self.update_pending_members_after_request_accept_or_reject(community_instance)

    def set_members_count_in_community(self, community_id, members_count):

        ModelUtilities.model_update(Community, {'id': community_id}, {'members_count': members_count})

    def approve_or_decline_community(self, req_body) -> {}:

        user_instance = ModelUtilities.get_model_instance_or_none(User, req_body.get('member_id'))

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, req_body.get('community_id'))

        if not community_instance:
            return {'success': False, 'error_message': "Invalid community id"}

        promoter_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                    'member_id': self.get_member_id(),
                                                                    'state': member_states.ADMIN})

        if promoter_filter:
            promoter_instance = promoter_filter[0].member_id
            promoter_userinfo_instance = promoter_instance.userinfo
            action_required_by_promoter = promoter_filter[0].actions_required

        else:
            return {'success': False, 'error_message': "You cannot approve or decline the request"}

        if req_body.get('accepted'):

            if Members.is_community_member(community_instance, user_instance):
                return {'success': False, 'error_message': "You are already a community member"}

            self.approve_community_join_request(community_instance, user_instance, promoter_instance)
            members_count = Members.get_members_count_in_community(community_instance)
            self.set_members_count_in_community(community_instance.id, members_count)

            CommunityHelper.update_community_level_actions(community_instance,
                                                           action_required_by_promoter, members_count)
            CommunityHelper.set_follow_status_for_announcement_chatroom_for_community(community_instance,
                                                                                      user_instance)

            card_instance = CommunityHelper.add_introductions_room_in_master_intro(community_instance, user_instance,
                                                                                   member_states.MEMBER)

            CommunityHelper.run_async_for_for_community_approve(community_instance, user_instance,
                                                                promoter_userinfo_instance)

        else:
            self.decline_community_join_request(community_instance, user_instance)
            members_count = Members.get_members_count_in_community(community_instance)
            self.set_members_count_in_community(community_instance.id, members_count)

            CommunityHelper.run_async_task_for_community_declined(community_instance, user_instance,
                                                               promoter_userinfo_instance)

        return {'success': True}

    def fetch_feed_url(self):
        community_instance = Community.get_community_or_raise_exception(self.get_community_id())

        feed_url = create_community_feed_url(community_instance)

        return {'success': True, 'feed_url': feed_url}

    def fetch_otl_url(self, payment_id, shared_by_id):
        community_instance = Community.get_community_or_raise_exception(self.get_community_id())

        private_link = create_community_otl_url(community_instance, payment_id, shared_by_id)

        return {'success': True, 'private_link': private_link}

    def fetch_discoverable_communities(self, page, page_size):
        communities = Community.objects.filter(is_discoverable=True).order_by("id")

        communities = ModelUtilities.paginate_queryset(communities, page, page_size)

        community_data = CommunitySerializerV1(communities, many=True).data

        return {'success': True, 'community': community_data}


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

    @staticmethod
    def save_level_2_details_in_community(level_instance, member_count, community_instance):

        if level_instance.level == "Level 2" and level_instance.state == community_level_states.PENDING:
            member_count = member_count - 1

            if level_instance.joined_members < level_instance.max_members:
                level_instance.joined_members = member_count
                level_instance.save()

            if level_instance.joined_members >= level_instance.max_members:
                level_instance.state = community_level_states.COMPLETE
                level_instance.save()

                ModelUtilities.model_update(
                    communityLevels,
                    {'community': community_instance, 'level': "Level 3"},
                    {
                        'title': LEVEL_3_TITLE,
                        'sub_title': LEVEL_3_SUB_TITLE,
                        'state': community_level_states.PENDING,
                    })
                # community managers emails
                send_8am_level_mails_to_admin_scheduler.delay(community_instance.id,
                                                              TimeUtilities.current_time_in_sec(), level=2, day=0,
                                                              counter=0)

    @staticmethod
    def save_level_3_details_in_community(level_instance, community_instance):

        if level_instance.level == "Level 3" and level_instance.state == community_level_states.PENDING:

            if level_instance.joined_members < level_instance.max_members:
                level_instance.joined_members = level_instance.joined_members + 1
                level_instance.save()

            if level_instance.joined_members >= level_instance.max_members:
                level_instance.state = community_level_states.COMPLETE
                level_instance.save()

                ModelUtilities.model_update(
                    communityLevels,
                    {'community': community_instance, 'level': "Level 4"},
                    {
                        'title': LEVEL_4_TITLE,
                        'sub_title': LEVEL_4_SUB_TITLE,
                        'state': community_level_states.PENDING,
                    })

                send_8am_level_mails_to_admin_scheduler.delay(community_instance.id,
                                                              TimeUtilities.current_time_in_sec(), level=3, day=0,
                                                              counter=0)

    @staticmethod
    def save_level_4_details_in_community(level_instance, community_instance):

        if level_instance.level == "Level 4" and level_instance.state == community_level_states.PENDING:

            if level_instance.joined_members < level_instance.max_members:
                level_instance.joined_members = level_instance.joined_members + 1
                level_instance.save()

            if level_instance.joined_members >= level_instance.max_members:
                level_instance.state = community_level_states.COMPLETE
                level_instance.save()

                ModelUtilities.model_update(Members, {'community_id': community_instance,
                                                      'state': member_states.ADMIN},
                                            {'actions_required': False,
                                             'updated_at': TimeUtilities.current_time_in_sec()})

                # community managers emails
                send_8am_level_mails_to_admin_scheduler.delay(community_instance.id,
                                                              TimeUtilities.current_time_in_sec(), level=4, day=0,
                                                              counter=0)

    @staticmethod
    def update_community_level_actions(community_instance, action_required_by_promoter, member_count):

        if not action_required_by_promoter:
            return

        instance_list = ModelUtilities.get_model_filter(communityLevels,
                                                        {'community': community_instance}).order_by('id')

        for instance in instance_list:
            CommunityHelper.save_level_2_details_in_community(instance, member_count, community_instance)
            CommunityHelper.save_level_3_details_in_community(instance, community_instance)
            CommunityHelper.save_level_4_details_in_community(instance, community_instance)

    @staticmethod
    @shared_task
    def send_sms_to_the_approved_member_of_community(user_id, community_id):

        notification_list = [
            'mail_has_installed_app'
        ]

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return

        if check_notification_flag(user_instance.id, notification_list, card_id=None, community_id=None):
            userinfo_instance = user_instance.userinfo
            new_user_name = get_first_name_from_name(userinfo_instance.name)

            mobile_filter = ModelUtilities.get_model_filter(userMobiles, {'user': user_instance,
                                                                          'state': mobile_states.PRIMARY})

            community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

            if not community_instance:
                return

            for instance in mobile_filter:
                phone_no = str(instance.country_code) + str(instance.mobile_no)
                send_community_confirmation_sms.delay(phone_no, community_instance.name,
                                                      new_user_name, user_instance.id)

    @staticmethod
    def run_async_for_for_community_approve(community_instance, user_instance, promoter_userinfo_instance):
        CommunityHelper.set_moderation_rights_and_and_delete_user_previous_metadata.delay(user_instance.id,
                                                                                          community_instance.id,
                                                                                          promoter_userinfo_instance.user_id_id)
        CommunityHelper.send_sms_to_the_approved_member_of_community.delay(user_instance.id, community_instance.id)
        send_notification_for_join_requests.delay(community_instance.id, True, user_instance.id,
                                                  promoter_userinfo_instance.name)
        send_community_confirmation_email.delay(user_instance.id, community_instance.id)
        MixpanelEvents.member_approved_by_cm.delay(user_instance.id, promoter_userinfo_instance.user_id_id
                                                   , community_instance.id)

    @staticmethod
    def run_async_task_for_community_declined(community_instance, user_instance, promoter_userinfo_instance):
        send_notification_for_join_requests.delay(community_instance.id, False,
                                                  user_instance.id, promoter_userinfo_instance.name)
        MixpanelEvents.member_rejected_by_cm.delay(user_instance.id, promoter_userinfo_instance.user_id_id,
                                                   community_instance.id)

    @staticmethod
    @shared_task
    def set_moderation_rights_and_and_delete_user_previous_metadata(user_id, community_id, promoter_id):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return

        promoter_instance = ModelUtilities.get_model_instance_or_none(User, promoter_id)

        if not promoter_instance:
            return

        give_default_member_rights(user=user_instance, community=community_instance)

        history_type = moderation_history_types.APPROVED_FROM

        is_rejoined = ModelUtilities.is_model_filter_exists(removedMembers, {'member': user_instance,
                                                                             'community': community_instance})

        ModelUtilities.delete_record_in_model(communityToast, {'community': community_instance,
                                                               'user': user_instance})
        ModelUtilities.delete_record_in_model(removedMembers, {'community': community_instance,
                                                               'member': user_instance})

        if is_rejoined:
            history_type = moderation_history_types.REJOINED_COMMUNITY_PUBLIC_LINK
            CommunityHelper.update_followed_chatrooms_for_rejoined_member(user_instance, community_instance)

        moderationHistory.create_instance({'user_instance': user_instance, 'community_instance': community_instance,
                                           'moderation_by': promoter_instance, 'type': history_type})

    @staticmethod
    def update_followed_chatrooms_for_rejoined_member(user_instance, community_instance):

        followed_filter = ModelUtilities.get_model_filter(collabcardState, {'user': user_instance,
                                                                            'community': community_instance})
        for instance in followed_filter:

            engage_filter_exists = ModelUtilities.is_model_filter_exists(conversationEngage,
                                                                         {'card': instance.card,
                                                                          'user': user_instance})
            if not engage_filter_exists:
                engage_instance = conversationEngage()
                engage_instance.community = community_instance
                engage_instance.card = instance.card
                engage_instance.user = instance.user
                engage_instance.created_at = instance.created_at
                engage_instance.updated_at = instance.updated_at
                engage_instance.save()

        rights_list = list(ModelUtilities.get_model_filter(userMemberRights,
                                                           {'user': user_instance,
                                                            'community': community_instance}).
                           values_list("right__state", flat=True))
        rights_list = json.dumps(rights_list)
        ModelUtilities.model_update(conversationEngage, {'user': user_instance,
                                                         'community': community_instance},
                                    {'rights_list': rights_list})

        # update elastic search
        ElasticSearchSync.update_chatrooms_for_rejoined_member(community_instance.id, user_instance.id)

    @staticmethod
    def set_follow_status_for_announcement_chatroom_for_community(community_instance, user_instance):

        card_filter = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                   'type': card_types.CARD_PURPOSE})
        if card_filter:
            card_instance = card_filter[0]

            ChatroomHelper.auto_follow_chatroom(card_instance, user_instance, community_instance, status=True,
                                                member_state=member_states.MEMBER)

    @staticmethod
    def create_introduction_text_for_intro_chatroom(community_instance, user_instance):
        intro_answer = ModelUtilities.get_model_filter(communityAnswers, {'community': community_instance,
                                                                          'member': user_instance,
                                                                          'question__question_state': question_states.INTRODUCTION})

        if intro_answer:
            return intro_answer[0].question_answer

    @staticmethod
    def add_introductions_room_in_master_intro(community_instance, user_instance, member_state):

        master_intro = ModelUtilities.get_model_filter(Collabcard,
                                                       {'community': community_instance,
                                                        'type': card_types.CARD_MASTER_INTRO,
                                                        'is_deleted': False})

        if not master_intro:
            return

        intro_filter = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                    'user': user_instance,
                                                                    'type': card_types.CARD_INTRO,
                                                                    'is_deleted': False})

        if intro_filter:
            return

        userinfo_instance = user_instance.userinfo
        master_intro_instance = master_intro[0]

        introduction_answer = CommunityHelper.create_introduction_text_for_intro_chatroom(community_instance,
                                                                                          user_instance)
        req_dict = {
            'title': introduction_answer,
            'type': 1,
            'header': userinfo_instance.name
        }

        chatroom_manager = ChatroomImpl(user_instance.id)

        card_instance = chatroom_manager.create_introduction_card_in_community(community_instance, user_instance,
                                                                               req_dict,
                                                                               member_state, master_intro_instance)

        return card_instance
