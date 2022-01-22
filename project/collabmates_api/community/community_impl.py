import json

from celery import shared_task
from django.contrib.auth.models import User
from django.template.loader import get_template
import re

from cms.models import NewAnswer
from collabmates_api.community.constants import *
from collabmates_api.rest_api import CommunitySerializerV1, CommunitySettingsSerializer, CommunityToastV1Serializer, \
    CommunityGetStartedSerializer
from collabmates_api.views import get_leave_community_text, send_notification_for_join_requests, \
    give_default_member_rights, send_notification_to_admins, update_member_rights_in_conversation_engage, \
    set_community_actions, add_community_settings_for_community, create_introduction_question_in_community_v2, \
    post_purpose_collabcard_for_community, post_master_introductions_for_community, post_member_directory_link, \
    post_general_collabcard_for_community, update_community_get_started, get_branch_links_for_community_share, \
    fill_share_context_for_paid_community, fill_share_context_for_unpaid_community, \
    check_join_community_hood_get_started, add_community_upload_image_analytics, \
    create_introduction_question_in_community
from collabmates_api.sync.model_update import update_models_for_syncing_apis
from utility.number_utilities import NumberUtilities
from external_services.email.email_wrapper import MailWrapper
from external_services.airtable.airtable_wrapper import AirtableWrapper
from togther.models import Community, Userinfo, Collabcard, Members, ModelUtilities, CommunityUserDelete, \
    card_answers, collabcardState, Member_Engage, communityAnswers, removedMembers, communityToast, userMobiles, \
    communityLevels, conversationEngage, userMemberRights, moderationHistory, communityQuestions, questionFilters, \
    communityExpiryCodes, CommunitySettings, CommunityToastV1, CommunityJoinEmail, CommunityJoinDefaultEmail, \
    userEmails, ContentDownloadSettings, CommunityGetStarted, UserEmailsSendStatus, communityFieldTypes, \
    communityFieldSubTypes
from collabmates_api.static_text import ALL_MEMBER_COHORT_TEXT
from collabmates_api.branch import create_community_feed_url, create_community_otl_url, create_payment_page_url, \
    create_community_feed_url_for_cm_onboarding
from collabmates_api.user_moderation_rights import check_admin_edit_community_right, give_all_manager_rights, \
    give_all_member_rights, save_moderation_history, give_all_community_setting_rights, \
    update_member_rights_in_member_engage
from django.db.models import Q, F

from external_services.mixpanel.events import MixpanelEvents
from external_services.wa_notification.wa_notification_impl import NotificationImpl

from external_services.segment.segment_impl import SegmentImpl

from collabmates_api.community.community_manager import CommunityManager
from collabmates_api.member_community.member_community_impl import MemberCommunityImpl

from collabmates_api.mails import send_created_community_email_to_team

from collabmates_api.cohort.cohort_impl import CohortHelper, CohortImpl

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.states import member_states, card_types, click_states, member_rights, mobile_states, \
    community_level_states, moderation_history_types, question_states, level_click_states, community_setting_types, \
    SyncTypes, cohort_types, get_started_types, send_invite_types, user_email_send_status_types, email_states
from utility.time_utilities import TimeUtilities
from utility.url_utilities import UrlUtilities
from utility.states import (mobile_states)
from utility.utils import check_notification_flag, get_first_name_from_name, is_version_code_supported_for_intro_room, \
    decode_option, community_default_image, community_default_thumbnail
from utility.celery_tasks import create_member_dm_chatroom, create_intro_room_disabled_text_for_community_members
from ..chatroom.chatroom_impl import ChatroomImpl, ChatroomHelper
from ..mails import send_8am_level_mails_to_admin_scheduler
from ..search.sync import ElasticSearchSync

from ..tasks import send_community_confirmation_email, cm_onboarding_version_check, get_user_email_preferred_verified
from ..sms import send_community_confirmation_sms
from ..utility import single_community_view_version_check

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class CommunityImpl(CommunityManager):
    member_id = None
    community_id = None
    version_code = None

    def __init__(self, member_id: str, community_id: str = None, version_code: str = None,
                 device_id: str = None, request_platform: str = None):

        self.member_id = member_id
        self.community_id = community_id
        self.version_code = version_code
        self.device_id = device_id
        self.request_platform = request_platform

    def get_member_id(self) -> str:
        return self.member_id

    def set_member_id(self, member_id: str) -> None:
        self.member_id = member_id

    def get_community_id(self) -> str:
        return self.community_id

    def get_device_id(self) -> str:
        return self.device_id

    def get_request_platform(self):
        return self.request_platform

    def get_version_code(self):
        return self.version_code

    def set_community_id(self, community_id) -> None:
        self.community_id = community_id

    def _community_menu_options(self, state, community_instance, platform_code: str, version_code: int) -> []:

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

        if single_community_view_version_check(platform_code, version_code):
            menu = menu + MENU["Subscription"]

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

    def _fetch_queryset_of_community_chatrooms(self, intro_room_settings_enabled, version_code, platform_code):

        if is_version_code_supported_for_intro_room(version_code, platform_code):

            if not intro_room_settings_enabled:
                return Collabcard.objects.filter(community=self.get_community_id(),
                                                is_pending=False,
                                                is_deleted=False,
                                                is_private=False,
                                                is_secret=False).filter(
                    ~Q(type__in=[card_types.CARD_INTRO, card_types.CARD_MASTER_INTRO])).order_by('-id')

            else:
                return Collabcard.objects.filter(community=self.get_community_id(),
                                                is_pending=False,
                                                is_deleted=False,
                                                is_private=False,
                                                is_secret=False).filter(
                    ~Q(~Q(user_id=self.get_member_id()) & Q(type=card_types.CARD_INTRO))).order_by('-id')

        else:
            return Collabcard.objects.filter(community=self.get_community_id(),
                                            is_pending=False,
                                            is_deleted=False,
                                            is_private=False,
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

    def fetch_community(self, client_type, platform_code: str, version_code: int) -> {}:

        community_instance = CommunityHelper.fetch_community_instance(self.get_community_id())
        response_context = dict()

        if not community_instance:
            response_context['error_message'] = "Invalid community_id"
            response_context['response_code'] = 400
            response_context['status'] = False

            return response_context

        community_member = MemberCommunityImpl(self.get_member_id(), self.get_community_id())
        state = community_member.community_member_state()
        block_leave_community = self._is_leave_community_blocked(state)
        community_context = {}

        if not block_leave_community:
            leave_community = self._leave_community_object()
            community_context['leave_community'] = leave_community

        menu = self._community_menu_options(state,
                                            community_instance,
                                            platform_code,
                                            version_code)

        if menu:
            community_context['menu'] = menu

        community_serialized_instance = self._fetch_serialize_community(community_instance)
        community_context.update(community_serialized_instance)
        response_context['community_context'] = community_context
        response_context['response_code'] = 200
        response_context['status'] = True

        return response_context

    def fetch_all_communities(self, page, community_ids: list = None) -> {}:

        community_filter = {}

        if community_ids is not None:
            community_filter['pk__in'] = community_ids

        community_instances = ModelUtilities.get_model_filter(Community, community_filter).order_by('-created_at')
        total_communities_count = len(community_instances)

        community_instances = ModelUtilities.paginate_queryset(community_instances, page, paginate_by=50)

        community_serialized_instances = CommunitySerializerV1(community_instances, many=True).data

        response_context = {
            'communities': [dict(i) for i in community_serialized_instances],
            'success': True,
            'total_communities_count': total_communities_count
        }

        return response_context

    def fetch_chatroom_feed(self, size) -> {}:

        community_instance = Community.get_community_or_None(self.get_community_id())

        if not community_instance:
            return {'error_message': "In-correct community_id"}

        userinfo_instance = Userinfo.get_userinfo_or_None(self.get_member_id())

        if not userinfo_instance:
            return {'error_message': "In-correct user id"}

        filter_dict = {
            'community_id': self.get_community_id(),
            'setting_type': community_setting_types.INTRO_ROOM,
            'enabled': True
        }

        intro_room_setting_enabled = False

        intro_room_setting_filter = ModelUtilities.get_model_filter(CommunitySettings, filter_dict)

        if intro_room_setting_filter:
            intro_room_setting_enabled = True

        community_chatroom_queryset = self._fetch_queryset_of_community_chatrooms(intro_room_setting_enabled,
                                                                                self.get_version_code(),
                                                                                self.get_request_platform())

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

    def _decline_community_join_request(self, community_instance, user_instance):

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

    def make_requesting_user_as_pending_member(self, community_instance, user_instance, shared_by_user, req_body):

        CommunityHelper.save_responses_of_member_in_community.delay(user_instance.id,
                                                                    community_instance.id,
                                                                    req_body.get('questions'))

        ModelUtilities.delete_record_in_model(removedMembers, {'community': community_instance,
                                                               'member': user_instance})
        Members.create_instance({'user_instance': user_instance,
                                 'community_instance': community_instance,
                                 'state': member_states.PENDING_MEMBER,
                                 'joined_by': shared_by_user
                                 })
        Member_Engage.create_instance({'user_instance': user_instance,
                                       'community_instance': community_instance,
                                       'state': member_states.PENDING_MEMBER,
                                       'click_state': click_states.PENDING_APPROVAL
                                       })
        self.update_pending_members_after_request_accept_or_reject(community_instance)

        history_type = moderation_history_types.APPLIED_PUBLIC_LINK if shared_by_user \
            else moderation_history_types.APPLIED_PUBLIC_LINK_WEBSITE

        moderationHistory.create_instance({'user_instance': user_instance, 'community_instance': community_instance,
                                           'moderation_by': shared_by_user, 'type': history_type})

        message = PAID_COMMUNITY_PENDING_MEMBER_TOAST if community_instance.is_paid else COMMUNITY_PENDING_MEMBER_TOAST

        communityToast.update_or_create_toast_message({'user_instance': user_instance,
                                                       'community_instance': community_instance,
                                                       'message': message})

        send_notification_to_admins.delay(community_instance.id, user_instance.userinfo.name)

    @staticmethod
    def make_promoter_profile_in_community(user_instance, community_instance, req_body):
        CommunityHelper.save_responses_of_member_in_community.delay(user_instance.id,
                                                                    community_instance.id,
                                                                    req_body.get('questions'))
        introduction_answer = CommunityHelper.create_introduction_text_for_intro_chatroom(community_instance,
                                                                                          user_instance,
                                                                                          req_body.get('questions'))
        CommunityHelper.add_introductions_room_in_master_intro(community_instance, user_instance,
                                                               member_states.ADMIN,
                                                               introduction_answer=introduction_answer)
        ModelUtilities.model_update(Members, {'member_id': user_instance, 'community_id': community_instance},
                                    {'updated_at': TimeUtilities.current_time_in_sec()})
        ModelUtilities.model_update(Member_Engage, {'community_id': community_instance, 'member_id': user_instance},
                                    {'click_state': click_states.DEFAULT})
        ModelUtilities.model_update(communityLevels, {'community': community_instance},
                                    {'level_click_state': level_click_states.COMMUNITY_JOINED})

    @staticmethod
    def make_skipped_member_profile_in_community(user_instance, community_instance, req_body):

        CommunityHelper.save_responses_of_member_in_community.delay(user_instance.id,
                                                                    community_instance.id,
                                                                    req_body.get('questions'))
        ModelUtilities.model_update(Members, {'member_id': user_instance, 'community_id': community_instance},
                                    {'updated_at': TimeUtilities.current_time_in_sec(),
                                     'state': member_states.MEMBER})
        ModelUtilities.model_update(Member_Engage, {'community_id': community_instance, 'member_id': user_instance},
                                    {'click_state': click_states.DEFAULT,
                                     'member_state': member_states.MEMBER,
                                     'updated_at': TimeUtilities.current_time_in_sec()})
        CommunityHelper.set_follow_status_for_announcement_chatroom_for_community(community_instance,
                                                                                  user_instance)
        introduction_answer = CommunityHelper.create_introduction_text_for_intro_chatroom(community_instance,
                                                                                          user_instance,
                                                                                          req_body.get('questions'))
        CommunityHelper.add_introductions_room_in_master_intro(community_instance, user_instance,
                                                               member_states.MEMBER,
                                                               introduction_answer=introduction_answer)
        ModelUtilities.delete_record_in_model(communityToast, {'community': community_instance,
                                                               'user': user_instance})
        ModelUtilities.delete_record_in_model(removedMembers, {'community': community_instance,
                                                               'member': user_instance})
        give_default_member_rights(user=user_instance, community=community_instance)
        update_member_rights_in_member_engage.delay(community_instance.id, user_instance.id)
        update_member_rights_in_conversation_engage.delay(community_instance.id, user_instance.id)

        # Add DM Chatrooms
        create_member_dm_chatroom.delay(user_instance.id, community_instance.id, is_joining=True)

        CohortHelper.add_all_member_to_cohort(community_instance.id, [user_instance.id])

    def make_requesting_user_as_member_of_community_automatically(self, user_instance, community_instance,
                                                                  auto_join_code, shared_by_user, req_body):

        CommunityHelper.save_responses_of_member_in_community.delay(user_instance.id,
                                                                    community_instance.id,
                                                                    req_body.get('questions'))
        Members.create_instance({'user_instance': user_instance,
                                 'community_instance': community_instance,
                                 'state': member_states.MEMBER,
                                 'joined_by': shared_by_user,
                                 'custom_title': "Member",
                                 'became_member_at': TimeUtilities.current_time_in_sec()
                                 })
        Member_Engage.create_instance({'user_instance': user_instance,
                                       'community_instance': community_instance,
                                       'state': member_states.MEMBER,
                                       })
        update_member_rights_in_member_engage.delay(community_instance.id, user_instance.id)

        CommunityHelper.set_follow_status_for_announcement_chatroom_for_community(community_instance,
                                                                                  user_instance)
        introduction_answer = CommunityHelper.create_introduction_text_for_intro_chatroom(community_instance,
                                                                                          user_instance,
                                                                                          req_body.get('questions'))
        CommunityHelper.add_introductions_room_in_master_intro(community_instance, user_instance,
                                                               member_states.MEMBER,
                                                               introduction_answer=introduction_answer)

        shared_user_id = shared_by_user.id if shared_by_user else None
        CommunityHelper.set_moderation_rights_and_delete_user_previous_metadata_for_auto_join.delay(
            user_instance.id,
            community_instance.id,
            shared_user_id,
            auto_join_code)

        members_count = Members.get_members_count_in_community(community_instance)
        self.set_members_count_in_community(community_instance.id, members_count)
        action_required_by_promoter = ModelUtilities.is_model_filter_exists(Members,
                                                                            {'community_id': community_instance,
                                                                             'state': member_states.ADMIN,
                                                                             'actions_required': True})

        if action_required_by_promoter:
            CommunityHelper.update_community_level_actions(community_instance,
                                                           action_required_by_promoter, members_count)

        # Create DM chatrooms
        device_id = self.get_device_id()
        platform = self.get_request_platform()

        create_member_dm_chatroom.delay(self.get_member_id(), self.get_community_id(), device_id=device_id,
                                        request_platform=platform, req_body=req_body, is_joining=True)

        CohortHelper.add_all_member_to_cohort(self.get_community_id(), [self.get_member_id()])

        self._send_join_email_to_member(user_instance.id, community_instance.id)

        CohortHelper.add_member_to_respective_question_based_cohorts(self.get_member_id(), self.get_community_id())

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

            CommunityHelper.run_async_for_community_approve(community_instance, user_instance,
                                                            promoter_userinfo_instance)

            CohortHelper.add_all_member_to_cohort(community_instance.id, [user_instance.id])

            self._send_join_email_to_member(user_instance.id, community_instance.id)

            cohort_manager = CohortImpl(member_id=user_instance.id)

            member_cohort_response = cohort_manager.add_user_to_subscription_plans_when_membership_approved(
                community_id=community_instance.id
            )

            if member_cohort_response.get('error_message'):
                info_logger.info(f'Unable to add member to respective subscription plan cohort: {member_cohort_response}')

            CohortHelper.add_member_to_respective_question_based_cohorts(member_id=user_instance.id,
                                                                         community_id=community_instance.id)

        else:
            self._decline_community_join_request(community_instance, user_instance)
            members_count = Members.get_members_count_in_community(community_instance)
            self.set_members_count_in_community(community_instance.id, members_count)

            CommunityHelper.run_async_task_for_community_declined(community_instance, user_instance,
                                                               promoter_userinfo_instance)

            ElasticSearchSync.delete_member_from_community.delay(self.get_member_id(), self.get_community_id())

        return {'success': True}

    def fetch_feed_url(self):
        community_instance = Community.get_community_or_raise_exception(self.get_community_id())

        feed_url = create_community_feed_url(community_instance)

        return {'success': True, 'feed_url': feed_url}

    def fetch_feed_url_for_cm_onboarding(self):
        community_instance = Community.get_community_or_raise_exception(self.get_community_id())

        feed_url = create_community_feed_url_for_cm_onboarding(community_instance)

        return {'success': True, 'feed_url': feed_url}

    def fetch_otl_url(self, payment_id, shared_by):
        community_instance = Community.get_community_or_raise_exception(self.get_community_id())

        private_link = create_community_otl_url(community_instance, payment_id, shared_by)

        return {'success': True, 'private_link': private_link}

    def fetch_payment_page_url(self, payment_page_id):
        community_instance = Community.get_community_or_raise_exception(self.get_community_id())

        payment_page_link = create_payment_page_url(community_instance, payment_page_id)

        return {'success': True, 'payment_page_link': payment_page_link}

    def fetch_discoverable_communities(self, page, page_size):
        communities = Community.objects.filter(is_discoverable=True).order_by("id")

        communities = ModelUtilities.paginate_queryset(communities, page, page_size)

        community_data = CommunitySerializerV1(communities, many=True).data

        return {'success': True, 'community': community_data}

    def join_community(self, req_body):

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, self.get_community_id())

        if not community_instance:
            return {'success': False, 'error_message': "Invalid community id"}

        member_state = Members.get_community_member_state(community_instance, user_instance)

        if member_state == member_states.MEMBER:
            return {'success': False, 'error_message': "You are already a member of this community"}

        auto_join_code = req_body.get('aj')
        shared_by_user = ModelUtilities.get_model_instance_or_none(User, req_body.get('shared_by'))

        join_link_invalid_message = ''
        is_cm_onboarding_enabled = cm_onboarding_version_check(self.get_request_platform(), self.get_version_code())

        if member_state == member_states.GUEST:

            if is_cm_onboarding_enabled:
                join_link_valid, join_link_invalid_message = CommunityHelper.is_join_link_valid_v2(auto_join_code,
                                                                                                   shared_by_user,
                                                                                                   community_instance,
                                                                                                   user_instance)

            else:
                join_link_valid = CommunityHelper.is_join_link_valid(auto_join_code, shared_by_user, community_instance)

            if join_link_valid:
                self.make_requesting_user_as_member_of_community_automatically(user_instance, community_instance,
                                                                               auto_join_code, shared_by_user, req_body)

            elif (not join_link_valid) and join_link_invalid_message:
                return {'success': False, 'error_message': join_link_invalid_message}

            else:
                self.make_requesting_user_as_pending_member(community_instance, user_instance, shared_by_user, req_body)

        elif member_state == member_states.ADMIN:
            self.make_promoter_profile_in_community(user_instance, community_instance, req_body)

        elif member_state == member_states.PROFILE_UNAVAILABLE:
            self.make_skipped_member_profile_in_community(user_instance, community_instance, req_body)

        else:

            return {'success': False, 'error_message': "Invalid member state"}

        user_has_access = Members.user_has_app_access(user_instance.id)

        ElasticSearchSync.update_member.delay(self.get_member_id(), self.get_community_id())

        if is_cm_onboarding_enabled:

            if community_instance.id == COMMUNITY_HOOD_COMMUNITY_ID:
                check_join_community_hood_get_started.delay(user_instance.id, COMMUNITY_HOOD_COMMUNITY_ID)

            update_community_get_started(community_instance, get_started_types.INVITE_MEMBERS_TYPE, is_enabled=True)

            CommunityHelper.send_community_moderation_mail_to_cm.delay(community_instance.id)

        return {'success': True, 'access': user_has_access}

    def fetch_members_meta(self, community_id):

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'error_message': "invalid user id"}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return {'error_message': "invalid community id"}

        members = ChatroomImpl.compute_tagging_list_of_community_members(community_instance)

        return {'members': members}

    def fetch_content_download_settings(self, chatroom_id=None):

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'error_message': "Invalid user ID"}

        community_id = self.get_community_id()

        community_instance = None

        if community_id:
            community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

            if not chatroom_instance:
                return {"error_message": "Invalid community/chatroom ID."}

            else:
                community_instance = chatroom_instance.community

        # Now fetch settings from ContentDownloadSettings table
        content_settings_instance = ModelUtilities.get_model_filter(ContentDownloadSettings,
                                                                    {"community_id": community_instance}).order_by("id")

        content_settings = {
            "content_download_settings": self.content_download_settings_serializer(content_settings_instance)
        }

        return content_settings

    def update_content_download_settings(self, content_download_settings_list):

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'error_message': "Invalid user ID"}

        content_setting_status = {
            "success": False
        }

        member_community_mapping = {}
        community_mapping = {}

        if len(content_download_settings_list):

            for content_download_setting in content_download_settings_list:

                if content_download_setting["community_id"] in community_mapping:
                    community_instance = community_mapping[content_download_setting["community_id"]]

                else:
                    community_instance = ModelUtilities.get_model_instance_or_none(Community,
                                                                            content_download_setting["community_id"])

                    if not community_instance:
                        return {'error_message': "Invalid community ID"}

                    else:
                        community_mapping[content_download_setting["community_id"]] = community_instance

                if community_instance.id in member_community_mapping:
                    member_state = member_community_mapping[community_instance.id]

                else:
                    member_state = Members.get_community_member_state(community_instance, user_instance)

                    if member_state == member_states.GUEST:
                        return {'error_message': "User is a GUEST."}

                    member_community_mapping[community_instance.id] = member_state

                if member_state == member_states.ADMIN:
                    ModelUtilities.model_update(ContentDownloadSettings,
                                    {
                                        "community_id_id": content_download_setting["community_id"],
                                        "download_setting_type": content_download_setting["download_setting_type"],
                                        "download_setting_title": content_download_setting["download_setting_title"]
                                    },
                                    {
                                        "enabled": content_download_setting["enabled"],
                                        "updated_at": TimeUtilities.current_time_in_milliseconds()
                                    })
                    content_setting_status["success"] = True

                else:
                    content_setting_status["error_message"] = "User doesn’t have ability to update content download " \
                                                              "settings"
                    content_setting_status["success"] = False
                    break

        else:
            content_setting_status["error_message"] = "Error in fetching content download settings."

        return content_setting_status

    @staticmethod
    def content_download_settings_serializer(content_settings_filter):
        content_setting_list = []

        for content_setting in content_settings_filter:
            content_setting_dict = {
                "community_id": content_setting.community_id_id,
                "download_setting_type": content_setting.download_setting_type,
                "download_setting_title": content_setting.download_setting_title,
                "enabled": content_setting.enabled
            }

            content_setting_list.append(content_setting_dict)

        return content_setting_list

    def fetch_community_settings(self):

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user ID"}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, self.get_community_id())

        if not community_instance:
            return {'success': False, 'error_message': "Invalid community ID"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': self.get_community_id(),
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of this community"}

        community_settings_list = ModelUtilities.get_model_filter(CommunitySettings,
                                                                  {"community_id": community_instance.id})

        community_settings_serializer = CommunitySettingsSerializer(community_settings_list, many=True)

        response = {
            'success': True,
            'community_settings': json.loads(json.dumps(community_settings_serializer.data))
        }

        return response

    def update_community_settings(self, community_settings_list):

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid User ID"}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, self.get_community_id())

        if not community_instance:
            return {'success': False, 'error_message': "Invalid Community ID"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': self.get_community_id(),
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of this community"}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return {'success': False, 'error_message': "User doesn’t have ability to update community settings"}

        disabled_community_settings_context_list = []

        for community_setting in community_settings_list:

            filter_dict = {
                "community_id": self.get_community_id(),
                "setting_type": community_setting["setting_type"],
                "setting_title": community_setting["setting_title"]
            }

            update_dict = {
                'enabled': community_setting['enabled'],
                'updated_at': TimeUtilities.current_time_in_milliseconds(),
                'enabled_by': user_instance if community_setting['enabled'] else None
            }

            if not community_setting['enabled']:
                disabled_community_setting_context = {
                    'community_id': self.get_community_id(),
                    'setting_type': community_setting['setting_type']
                }
                disabled_community_settings_context_list.append(disabled_community_setting_context)

            ModelUtilities.model_update(CommunitySettings, filter_dict, update_dict)

        create_intro_room_disabled_text_for_community_members.delay(disabled_community_settings_context_list)
        return {'success': True}

    def fetch_community_toasts_v1(self):

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid User ID"}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, self.get_community_id())

        if not community_instance:
            return {'success': False, 'error_message': "Invalid Community ID"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': self.get_community_id(),
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of this community"}

        filter_dict = {
            'community_id': self.get_community_id(),
            'user_id': self.get_member_id(),
            'is_shown': False
        }

        unseen_app_toast_filter = ModelUtilities.get_model_filter(CommunityToastV1, filter_dict).order_by('-updated_at')
        app_toast_serializer = CommunityToastV1Serializer(unseen_app_toast_filter, many=True)

        response = {
            'success': True,
            'community_toasts': json.loads(json.dumps(app_toast_serializer.data))
        }

        return response

    def update_community_toast_v1(self, toast_id) -> dict:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "In-valid user id"}

        toast_filter = ModelUtilities.get_model_filter(CommunityToastV1, {'id': toast_id})

        if not toast_filter:
            return {'success': False, 'error_message': "In-valid toast id"}

        toast_instance = toast_filter[0]

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': toast_instance.community,
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of community"}

        toast_filter.update(is_shown=True, updated_at=TimeUtilities.current_time_in_sec())

        return {'success': True}

    @staticmethod
    def _create_join_email_instance(req_body):

        if 'reply_to' not in req_body:
            return {'success': False, 'error_message': 'send reply_to in request body'}

        if 'subject' not in req_body:
            return {'success': False, 'error_message': 'send subject in request body'}

        if 'body' not in req_body:
            return {'success': False, 'error_message': 'send body in request body'}

        join_email_instances = ModelUtilities.get_model_filter(CommunityJoinEmail,
                                                               {'community_id': req_body['community_id']})

        if len(join_email_instances) == 0:
            CommunityJoinEmail.create_instance(req_body)

        else:
            join_email_instance = join_email_instances[0]
            join_email_instance.reply_to = req_body['reply_to']
            join_email_instance.subject = req_body['subject']
            join_email_instance.body = req_body['body']
            join_email_instance.save()
        return {'success': True}

    def add_join_email(self, req_body) -> {}:

        community_instance = ModelUtilities.get_model_instance_or_none(Community, self.get_community_id())

        if community_instance is None:
            return {'success': False, 'error_message': "Invalid community id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if user_instance is None:
            return {'success': False, 'error_message': "Invalid User ID"}

        is_promoter = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_promoter:
            return {'success': False, 'error_message': "You are not the owner/cm of community."}

        req_body['community_instance'] = community_instance

        join_email_instance = self._create_join_email_instance(req_body)

        if not join_email_instance['success']:
            return {'success': False, 'error_message': join_email_instance['error_message']}

        analytics_data = {
            'community_id': community_instance.id,
            'community_name': community_instance.name
        }

        SegmentImpl.track_event(self.get_member_id(), "Welcome email added (Backend)", analytics_data)

        return {'success': True}

    @staticmethod
    def _send_join_email_to_member(member_id, community_id):

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return {'success': False, 'error_message': "Invalid community id"}

        mail_to = []

        user_emails = ModelUtilities.get_model_filter(userEmails, {'user': member_id})

        if len(user_emails) > 0:
            mail_to.append(user_emails[0].email)

        mail_data = CommunityImpl._fetch_join_email_data(community_id, community_instance)

        MailWrapper.send_email.delay(mail_data["subject"], mail_data["body"], mail_to, reply_to=mail_data["reply_to"])

    @staticmethod
    def _fetch_join_email_data(community_id, community_instance) -> {}:

        data = {
            "reply_to": None,
            "subject": None,
            "body": None
        }

        join_email_instances = ModelUtilities.get_model_filter(CommunityJoinEmail, {'community_id': community_id})

        if len(join_email_instances) == 0:
            member_instances = ModelUtilities.get_model_filter(
                Members, {'community_id': community_id, 'is_owner': True})

            member_id = None

            if len(member_instances) != 0:
                member_id = member_instances[0].member_id

            user_emails = ModelUtilities.get_model_filter(userEmails, {'user': member_id})

            if len(user_emails) > 0:
                data["reply_to"] = [user_emails[0].email]

            data["subject"] = community_instance.name
            default_body = ModelUtilities.get_model_filter(CommunityJoinDefaultEmail, {})
            data["body"] = default_body[0].body

        else:
            join_email_instance = join_email_instances[0]
            data["reply_to"] = [join_email_instance.reply_to]
            data["subject"] = join_email_instance.subject
            data["body"] = join_email_instance.body

        return data

    def fetch_join_email(self) -> {}:

        community_instance = ModelUtilities.get_model_instance_or_none(Community, self.get_community_id())

        if not community_instance:
            return {'success': False, 'error_message': "Invalid community id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        is_promoter = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_promoter:
            return {'success': False, 'error_message': "You are not the owner/cm of community."}

        join_email_data = self._fetch_join_email_data(self.get_community_id(), community_instance)

        return {"success": True, "join_email": join_email_data}

    def create_community(self, req_body) -> {}:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': 'Invalid member-id'}

        validate_req_body = CommunityHelper.create_community_validation(req_body)

        if 'error_message' in validate_req_body:
            return validate_req_body

        community_state = 0

        community_instance = Community.create_instance({'name': validate_req_body['name'],
                                                        'members_count': 1,
                                                        'purpose': validate_req_body['headline'],
                                                        'brand_color': validate_req_body['brand_color'],
                                                        'image_link': validate_req_body['image_url'],
                                                        'thumbnail': community_default_thumbnail,
                                                        'type': TYPE_ID_WITH_NO_DIRECTORY_QUESTIONS,
                                                        'sub_type': SUB_TYPE_ID_WITH_NO_DIRECTORY_QUESTIONS,
                                                        'hide_community': community_state})

        if validate_req_body.get('has_logo_uploaded', False):
            add_community_upload_image_analytics.delay(user_instance.id, community_instance.id, community_instance.name)

        self.set_community_id(community_instance.id)

        set_community_actions(community_instance)

        # making the member instance for created community
        member_instance = Members.create_instance({'user_instance': user_instance,
                                                   'community_instance': community_instance,
                                                   'state': member_states.ADMIN,
                                                   'actions_required': True,
                                                   'is_owner': True,
                                                   'custom_title': 'Owner',
                                                   'became_member_at': TimeUtilities.current_time_in_sec()})

        CommunityHelper.create_community_async_tasks.delay(user_instance.id, community_instance.id, req_body)

        update_community_get_started(community_instance, get_started_types.CREATE_COMMUNITY_TYPE, is_enabled=True)

        # Create All member cohort
        CommunityHelper.create_all_member_cohort_for_new_community.delay(self.get_member_id(), community_instance.id)

        # send mails to ask cm to upgrade level
        send_8am_level_mails_to_admin_scheduler.delay(community_instance.id,
                                                      TimeUtilities.current_time_in_sec(),
                                                      level=1, day=0, counter=0)

        CommunityHelper.send_create_community_welcome_whatsapp_message.delay(user_instance.id,
                                                                             community_instance.id)
        CommunityHelper.send_communtiy_creation_segment_events.delay(user_instance.id,
                                                                     SEGMENT_COMMUNITY_CREATION_EVENT_NAME,
                                                                     {"community_id": community_instance.id,
                                                                      "community_name": community_instance.name})
        CommunityHelper.set_user_email_status.delay(user_instance.id, community_instance.id)

        community_serializer = CommunitySerializerV1(community_instance,
                                                     context={"current_user_id": self.get_member_id()},
                                                     many=False).data

        return {'success': True, 'community': community_serializer}

    def fetch_get_started(self) -> {}:

        validated_body = CommunityHelper.validate_fetch_get_started(self.get_member_id(), self.get_community_id())

        if not validated_body.get('success'):
            return validated_body

        community_instance = validated_body.get('community_instance')

        community_get_started_filter = ModelUtilities.get_model_filter(CommunityGetStarted,
                                                                       {'community': community_instance})

        get_started_list = CommunityGetStartedSerializer(community_get_started_filter, many=True).data

        return {'success': True,
                'heading': FETCH_GET_STARTED_HEADING.format(community_instance.name),
                'title': FETCH_GET_STARTED_TITLE,
                'sub_title': FETCH_GET_STARTED_SUB_TITLE,
                'image': FETCH_GET_STARTED_IMAGE,
                'bottom_text': FETCH_GET_STARTED_BOTTOM_TEXT,
                'get_started_list': get_started_list}

    def send_invite(self, req_body) -> {}:

        validated_req_body = CommunityHelper.validate_send_invite(req_body)

        if not validated_req_body.get('success'):
            return validated_req_body

        validated_req_body = validated_req_body.get('req_body')

        validated_logic = CommunityHelper.validate_send_invite_logic(self.get_member_id(), validated_req_body)

        if not validated_logic.get('success'):
            return validated_logic

        user_instance = validated_logic.get('user_instance')

        community_instance = validated_logic.get('community_instance')

        self.set_community_id(community_instance.id)

        share_context = get_branch_links_for_community_share(user_instance, community_instance)
        community_share = {}

        if community_instance.is_paid:
            fill_share_context_for_paid_community(community_instance, share_context, community_share)

        else:
            fill_share_context_for_unpaid_community(community_instance, share_context, community_share)

        if not community_share:
            return {'error_message': "Error in generating link", 'success': False}

        if validated_req_body.get('link_type') == 'free':
            link = community_share.get('private_link')

        else:
            link = community_share.get('public_link')

        if validated_req_body.get('type') == send_invite_types.EMAIL_INVITE:
            email_ids_list = CommunityHelper.get_list_from_comma_string(validated_req_body.get('email_id'))

            valid_email_ids_list = [email_id for email_id in email_ids_list if CommunityHelper.is_valid_email(email_id)]

            if not len(valid_email_ids_list):

                if len(email_ids_list) < 2:
                    error_text = 'Invalid email ID!'

                else:
                    error_text = "Invalid email ID's!"

                return {'success': False, 'error_message': error_text}

            mail_text = validated_req_body.get('text')

            send_email_response = CommunityHelper.send_invite_email_to_given_emails_list(user_instance,
                                                                                         community_instance,
                                                                                         valid_email_ids_list,
                                                                                         validated_req_body,
                                                                                         share_context, link,
                                                                                         mail_text)

            if not send_email_response:
                return {'success': False, "error_message": "Error while sending email."}

            update_community_get_started(community_instance, get_started_types.INVITE_MEMBERS_TYPE, is_enabled=True)

            return {'success': True}

        elif validated_req_body.get('type') == send_invite_types.WHATSAPP_INVITE:
            mobile_nos_list = CommunityHelper.get_list_from_comma_string(validated_req_body.get('mobile_no'))
            mobile_nos_list = [NumberUtilities.get_integer_from_string(i) if str(i).isdigit() else i for i in
                               mobile_nos_list]

            link_path = UrlUtilities.extract_part_from_url(link, 'path', init_slash_off=True)

            template_name = WHATSAPP_INVITE_TEMPLATE_WITH_CODE_NAME if validated_req_body.get('link_type') == 'free' \
                else WHATSAPP_INVITE_TEMPLATE_WITHOUT_CODE_NAME

            receivers_list = CommunityHelper.send_invite_whatsapp_context_dict(user_instance, community_instance,
                                                                               mobile_nos_list, validated_req_body,
                                                                               share_context, link_path)

            NotificationImpl.send_bulk_wa_notification.delay(receivers_list, template_name, template_name)

            update_community_get_started(community_instance, get_started_types.INVITE_MEMBERS_TYPE, is_enabled=True)

            return {'success': True}

        else:
            return {'success': False, 'error_message': 'Invalid type!'}


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
    def run_async_for_community_approve(community_instance, user_instance, promoter_userinfo_instance):
        CommunityHelper.set_moderation_rights_and_delete_user_previous_metadata.delay(user_instance.id,
                                                                                      community_instance.id,
                                                                                      promoter_userinfo_instance.user_id_id)
        CommunityHelper.send_sms_to_the_approved_member_of_community.delay(user_instance.id, community_instance.id)
        send_notification_for_join_requests.delay(community_instance.id, True, user_instance.id,
                                                  promoter_userinfo_instance.name)
        send_community_confirmation_email.delay(user_instance.id, community_instance.id)
        MixpanelEvents.member_approved_by_cm.delay(user_instance.id, promoter_userinfo_instance.user_id_id,
                                                   community_instance.id)

        ElasticSearchSync.update_member.delay(user_instance.id, community_instance.id)

        # Create DM chatrooms
        create_member_dm_chatroom.delay(user_instance.id, community_instance.id, is_joining=True)

    @staticmethod
    def run_async_task_for_community_declined(community_instance, user_instance, promoter_userinfo_instance):
        send_notification_for_join_requests.delay(community_instance.id, False,
                                                  user_instance.id, promoter_userinfo_instance.name)
        MixpanelEvents.member_rejected_by_cm.delay(user_instance.id, promoter_userinfo_instance.user_id_id,
                                                   community_instance.id)

    @staticmethod
    @shared_task
    def set_moderation_rights_and_delete_user_previous_metadata(user_id, community_id, promoter_id):

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
    @shared_task
    def set_moderation_rights_and_delete_user_previous_metadata_for_auto_join(user_id, community_id, shared_id,
                                                                                  auto_join_code):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return

        shared_by_user = ModelUtilities.get_model_instance_or_none(User, shared_id)

        ModelUtilities.model_update(collabcardState,
                                    {'community': community_instance, 'user': user_instance},
                                    {'is_guest': False, 'remove': None,
                                     'updated_at': TimeUtilities.current_time_in_sec()})

        ModelUtilities.model_update(card_answers,
                                    {'community': community_instance, 'user': user_instance},
                                    {'is_guest': False, 'remove': None,
                                     'last_updated': TimeUtilities.current_time_in_milliseconds()})

        give_default_member_rights(user=user_instance, community=community_instance)

        history_type = moderation_history_types.APPLIED_PRIVATE_LINK

        if auto_join_code is None and shared_by_user is None:
            history_type = moderation_history_types.APPLIED_PUBLIC_LINK_WEBSITE

        is_rejoined = ModelUtilities.is_model_filter_exists(removedMembers, {'member': user_instance,
                                                                             'community': community_instance})

        ModelUtilities.delete_record_in_model(communityToast, {'community': community_instance,
                                                               'user': user_instance})
        ModelUtilities.delete_record_in_model(removedMembers, {'community': community_instance,
                                                               'member': user_instance})

        if is_rejoined:
            history_type = moderation_history_types.REJOINED_COMMUNITY_PRIVATE_LINK
            CommunityHelper.update_followed_chatrooms_for_rejoined_member(user_instance, community_instance)

        moderationHistory.create_instance({'user_instance': user_instance, 'community_instance': community_instance,
                                           'moderation_by': shared_by_user, 'type': history_type})

    @staticmethod
    def update_followed_chatrooms_for_rejoined_member(user_instance, community_instance):

        followed_filter = collabcardState.objects\
            .filter(user=user_instance, community=community_instance, follow_status=True)\
            .select_related('card')

        engage_list = []

        for instance in followed_filter:
            engage_filter = ModelUtilities.get_model_filter(conversationEngage, {'community': community_instance,
                                                                                 'card': instance.card,
                                                                                 'user': user_instance})
            if not engage_filter:
                engage_instance = conversationEngage.create_instance_for_bulk_create(community_instance, instance.card,
                                                                                     user_instance,
                                                                                     created_at=instance.created_at,
                                                                                     updated_at=instance.updated_at)
                engage_list.append(engage_instance)

        ModelUtilities.bulk_create_instances(conversationEngage, engage_list)

        rights_list = list(ModelUtilities.get_model_filter(userMemberRights,
                                                           {'user': user_instance,
                                                            'community': community_instance}).
                           values_list("right__state", flat=True))
        rights_list = json.dumps(rights_list)
        ModelUtilities.model_update(conversationEngage, {'user': user_instance,
                                                         'community': community_instance},
                                    {'rights_list': rights_list})

        # update elastic search
        ElasticSearchSync.update_chatrooms_for_rejoined_member.delay(community_instance.id, user_instance.id)

    @staticmethod
    def set_follow_status_for_announcement_chatroom_for_community(community_instance, user_instance):

        card_filter = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                   'type': card_types.CARD_PURPOSE})
        if card_filter:
            card_instance = card_filter[0]

            ChatroomHelper.auto_follow_chatroom(card_instance, user_instance, community_instance, status=True,
                                                member_state=member_states.MEMBER)

    @staticmethod
    def create_introduction_text_for_intro_chatroom(community_instance, user_instance, question_list=None):

        introduction_answer = ""

        if question_list is not None:

            for question in question_list:

                if not question.get('value'):
                    continue

                if question.get('state') == question_states.INTRODUCTION:
                    introduction_answer = question.get('value')

        else:

            intro_answer = ModelUtilities.get_model_filter(communityAnswers,
                                                           {'community': community_instance,
                                                            'member': user_instance,
                                                            'question__question_state': question_states.INTRODUCTION})

            if intro_answer:
                introduction_answer = intro_answer[0].question_answer

        return introduction_answer

    @staticmethod
    def add_introductions_room_in_master_intro(community_instance, user_instance, member_state,
                                               introduction_answer=""):

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

        if not introduction_answer:
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

    @staticmethod
    def pre_compute_question_instances_for_saving_responses(question_list):

        question_id_list = [question['id'] for question in question_list if question.get('id')]
        question_instances = ModelUtilities.get_model_filter(communityQuestions, {'id__in': question_id_list})
        question_instance_dict = {}

        for data in question_instances:
            question_instance_dict[data.id] = data

        return question_instance_dict

    @staticmethod
    def is_dropdown_option_present(option, dropdown_list):

        for data in dropdown_list:
            if data.lower() == option.lower():
                return True
        return False

    @staticmethod
    def save_user_selected_options_for_member_directory_filter(question_instance, value, user_instance,
                                                               community_instance):

        if question_instance.question_state == question_states.CHOICE_SINGLE \
                or question_instance.question_state == question_states.CHOICE_MULTIPLE:
            selected_choices = value.split("$#")

            dropdown_list = decode_option(question_instance.value)

            for choice in selected_choices:
                option = choice.strip()

                if not CommunityHelper.is_dropdown_option_present(option, dropdown_list):
                    new_answer_instance = NewAnswer()
                    new_answer_instance.option = option
                    new_answer_instance.question = question_instance
                    new_answer_instance.user = user_instance
                    new_answer_instance.community = community_instance
                    new_answer_instance.save()

                    dropdown_list.append(option)
                questionFilters.create_instance({'question_instance': question_instance,
                                                 'option': option,
                                                 'user_instance': user_instance,
                                                 'community_instance': community_instance})

            result = [{'value': value} for value in dropdown_list]
            json_dump = json.dumps(result)
            question_instance.value = json_dump
            question_instance.save()

    @staticmethod
    def save_profile_links_for_social_handles(question_instance, answer_instance):

        if question_instance.question_state == question_states.PROFILE_LINK:

            try:
                value_list = json.loads(question_instance.value)

            except Exception as e:
                error_logger.error(e)

                return

            if value_list and value_list[0]['profile_platform'] == INSTAGRAM:
                answer_instance.question_answer = INSTAGRAM_URL + answer_instance.question_answer
                answer_instance.save()

            elif value_list and value_list[0]['profile_platform'] == TWITTER:
                answer_instance.question_answer = TWITTER_URL + answer_instance.question_answer
                answer_instance.save()

    @staticmethod
    def update_hidden_fields_in_member_responses(user_instance, community_instance):

        question_filter = ModelUtilities.get_model_filter(communityQuestions, {
            'community': community_instance,
            'is_hidden': True,
            'question_state': question_states.MOBILE_NO
        })

        if question_filter:
            question_instance = question_filter[0]
            mobile_filter = ModelUtilities.get_model_filter(userMobiles, {'user': user_instance,
                                                                          'state': mobile_states.PRIMARY})
            if mobile_filter:
                mobile_no = "+" + str(mobile_filter[0].country_code) + " " + str(mobile_filter[0].mobile_no)
                communityAnswers.create_instance({
                    'question_instance': question_instance,
                    'user_instance': user_instance,
                    'community_instance': community_instance,
                    'question_answer': mobile_no,
                    'question_title': question_instance.question_title
                })

    @staticmethod
    @shared_task
    def save_responses_of_member_in_community(user_id, community_id, question_list):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)
        userinfo_instance = user_instance.userinfo
        user_mobiles = ModelUtilities.get_model_filter(userMobiles, {'user_id': user_id,
                                                                     'state': mobile_states.PRIMARY})
        user_emails = ModelUtilities.get_model_filter(userEmails, {'user_id': user_id})
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not question_list or \
                not user_instance or \
                not community_instance:
            return

        question_instance_dict = CommunityHelper.pre_compute_question_instances_for_saving_responses(question_list)

        phone = '+{}{}'.format(user_mobiles[0].country_code, user_mobiles[0].mobile_no) if len(user_mobiles) else ''
        email = user_emails[0].email if len(user_emails) else ''

        airtable_data = {
            'user_id': user_id,
            'community_id': community_id,
            'user_name': userinfo_instance.name,
            'user_email': email,
            'phone_number': phone,
            'question_list': {}
        }

        for question in question_list:

            if not question.get('value'):
                continue

            question_id = NumberUtilities.get_integer_from_string(question['id'])
            question_instance = question_instance_dict.get(question_id)

            if question_instance.is_hidden:
                continue

            answer_instance = communityAnswers.create_instance({'question_instance': question_instance,
                                                                'user_instance': user_instance,
                                                                'community_instance': community_instance,
                                                                'question_answer': question['value'],
                                                                'question_title': question['question_title']})

            CommunityHelper.save_user_selected_options_for_member_directory_filter(question_instance,
                                                                                   question.get('value'),
                                                                                   user_instance,
                                                                                   community_instance)
            CommunityHelper.save_profile_links_for_social_handles(question_instance, answer_instance)

            airtable_data['question_list'][question_instance.id] = question.get('value')

        CommunityHelper.update_hidden_fields_in_member_responses(user_instance, community_instance)
        airtable_manager = AirtableWrapper()
        airtable_manager.send_data(airtable_data)

    @staticmethod
    def is_join_link_valid_v2(auto_join_code, shared_by_user, community_instance, user_instance=None):
        join_link_valid = False
        join_link_invalid_message = ''

        if (not community_instance.is_paid) and (not auto_join_code) and (not shared_by_user):
            join_link_invalid_message = FREE_COMMUNITY_NOT_AJ_NOT_SHARED_BY_MESSAGE
            return join_link_valid, join_link_invalid_message

        community_setting_instance = ModelUtilities.get_model_filter(CommunitySettings,
                                                                     {'community': community_instance,
                                                                      'setting_type': community_setting_types.MEMBERS_AUTO_JOIN})

        auto_approval = community_setting_instance[0].enabled if len(community_setting_instance) else community_instance.auto_approval

        if community_instance.is_paid and (auto_join_code is None) and (shared_by_user is None):
            join_link_valid = auto_approval

        else:

            auto_join_code = NumberUtilities.get_integer_from_string(auto_join_code)
            aj_filter = ModelUtilities.get_model_filter(communityExpiryCodes, {'community': community_instance,
                                                                               'unique_code': auto_join_code})

            if (not community_instance.is_paid) and (not aj_filter):
                join_link_invalid_message = INVALID_INVITE_CODE_MESSAGE
                return join_link_valid, join_link_invalid_message

            if community_instance.is_paid and (aj_filter and aj_filter[0].user_id is not None):
                join_link_invalid_message = FREE_INVITE_CODE_ALREADY_USED_MESSAGE
                return join_link_valid, join_link_invalid_message

            if community_instance.is_paid:
                aj_filter.update(user=user_instance)

            if not aj_filter:
                join_link_invalid_message = INVALID_INVITE_CODE_MESSAGE

            else:
                join_link_valid = auto_approval

        return join_link_valid, join_link_invalid_message

    @staticmethod
    def is_join_link_valid(auto_join_code, shared_by_user, community_instance):
        join_link_valid = False

        if auto_join_code is None \
                and shared_by_user is None:
            join_link_valid = community_instance.is_paid and community_instance.auto_approval

        else:

            auto_join_code = NumberUtilities.get_integer_from_string(auto_join_code)
            aj_filter = ModelUtilities.get_model_filter(communityExpiryCodes, {'community': community_instance,
                                                                               'unique_code': auto_join_code})
            timestamp = TimeUtilities.current_time_in_sec()

            if aj_filter:
                expiry_instance = aj_filter[0]
                expiry_time = expiry_instance.created_at
                join_link_valid = (timestamp - expiry_time) <= expiry_instance.expire_duration

        return join_link_valid

    @staticmethod
    def fetch_community_for_aj(aj, user_id, platform_code, version_code):
        res = {
            'success': False
        }

        is_aj_present = ModelUtilities.get_model_filter(communityExpiryCodes, {'unique_code': aj})

        if is_aj_present:
            aj_instance = is_aj_present[0]
            is_cm_onboarding_enabled = cm_onboarding_version_check(platform_code, version_code)

            if is_cm_onboarding_enabled and aj_instance.community.is_paid:
                user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

                if not user_instance:
                    res['error_message'] = 'Invalid member-id'
                    return res

                if aj_instance.user != user_instance:
                    res['error_message'] = 'Invalid aj'
                    return res

            res['success'] = True
            res['community_id'] = aj_instance.community.id
            res['shared_by'] = aj_instance.promoter.id
            return res

        res['error_message'] = 'Invalid aj'
        return res

    @staticmethod
    def is_aj_valid(aj_instance):
        current_time = TimeUtilities.current_time_in_sec()

        expiry_time = aj_instance.created_at
        is_aj_valid = (current_time - expiry_time) <= aj_instance.expire_duration

        return is_aj_valid

    @staticmethod
    def create_community_validation(req_body):

        if 'name' not in req_body:
            return {'success': False, 'error_message': 'Empty name!'}

        if len(req_body.get('name')) > CHARACTER_LIMIT_ON_COMMUNITY_NAME:
            return {'success': False, 'error_message': 'Characters length should not be greater than 30'}

        if 'headline' not in req_body:
            return {'success': False, 'error_message': 'Empty headline!'}

        if 'brand_color' not in req_body:
            return {'success': False, 'error_message': 'Empty brand color!'}

        if 'image_url' not in req_body:
            return {'success': False, 'error_message': 'Empty image url!'}

        return req_body

    @staticmethod
    def validate_send_invite(req_body):

        if 'type' not in req_body:
            return {'success': False, 'error_message': 'Send type'}

        if 'community_id' not in req_body:
            return {'success': False, 'error_message': 'Send community_id'}

        if req_body.get('type') not in [send_invite_types.EMAIL_INVITE, send_invite_types.WHATSAPP_INVITE]:
            return {'success': False, 'error_message': 'invalid type'}

        if (req_body.get('type') == send_invite_types.EMAIL_INVITE) and ('email_id' not in req_body):
            return {'success': False, 'error_message': 'Send email_id'}

        if (req_body.get('type') == send_invite_types.WHATSAPP_INVITE) and ('mobile_no' not in req_body):
            return {'success': False, 'error_message': 'send mobile_no'}

        if 'text' not in req_body:
            return {'success': False, 'error_message': 'Send text'}

        if 'link_type' not in req_body:
            return {'success': False, 'error_message': 'Send link_type'}

        return {'success': True, 'req_body': req_body}

    @staticmethod
    def get_list_from_comma_string(comma_seperated_string):

        comma_seperated_string = comma_seperated_string.split(',')
        comma_seperated_string = [i.strip() if isinstance(i, str) else i for i in comma_seperated_string]

        return  comma_seperated_string

    @staticmethod
    def is_valid_email(email_id):
        return re.fullmatch(EMAIL_VALIDATION_REGEX, email_id)

    @staticmethod
    def create_community_creation_whatsapp_context_dict(user_instance, cm_primary_mobile, community_dash_link_path):
        receivers_list = [
            {
                'whatsappNumber': '{}{}'.format(cm_primary_mobile.country_code, cm_primary_mobile.mobile_no),
                "customParams": [
                    {
                        "name": "name",
                        "value": user_instance.userinfo.name
                    },
                    {
                        "name": "link",
                        "value": community_dash_link_path
                    }
                ]
            }
        ]

        return receivers_list

    @staticmethod
    @shared_task
    def send_create_community_welcome_whatsapp_message(user_id, community_id):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return

        cm_primary_mobile = ModelUtilities.get_model_filter(userMobiles,
                                                            {'user': user_instance,
                                                             'state': mobile_states.PRIMARY})

        if not len(cm_primary_mobile):
            return

        cm_primary_mobile = cm_primary_mobile[0]

        branch_link = create_community_feed_url_for_cm_onboarding(community_instance)

        community_dash_link_path = UrlUtilities.extract_part_from_url(branch_link, 'path', init_slash_off=True)

        receivers_list = CommunityHelper.create_community_creation_whatsapp_context_dict(user_instance,
                                                                                         cm_primary_mobile,
                                                                                         community_dash_link_path)

        template_name = broadcast_name = WHATSAPP_COMMUNITY_CREATED_TEMPLATE_FOR_CM_NAME
        NotificationImpl.send_bulk_wa_notification.delay(receivers_list, template_name, broadcast_name)

        return

    @staticmethod
    @shared_task
    def send_communtiy_creation_segment_events(user_id, event_name, event_metadata):
        SegmentImpl.track_event(user_id, event_name, event_metadata)

    @staticmethod
    @shared_task
    def set_user_email_status(user_id, community_id):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return

        user_email_status_filter = ModelUtilities.get_model_filter(UserEmailsSendStatus,
                                                                   {"community": community_instance,
                                                                    "user": user_instance,
                                                                    "status_type": user_email_send_status_types.CM_ONBOARDING})

        if not user_email_status_filter:
            branch_link = create_community_feed_url_for_cm_onboarding(community_instance)

            mail_body = CommunityHelper.get_mail_body_for_community_creation_get_started(user_instance,
                                                                                         community_instance,
                                                                                         branch_link)

            user_email_status = UserEmailsSendStatus.create_instance({
                "user": user_instance,
                "community": community_instance,
                "status_type": user_email_send_status_types.CM_ONBOARDING,
                "frequency_in_minutes": FREQUENCY_OF_GETTING_STARTED_EMAIL_IN_MINS,
                "count": 0,
                "max_count": MAX_NUMBER_OF_TIMES_GETTING_STARTED_EMAIL_SHOULD_FIRE,
                "mail_data": json.dumps(mail_body),
                "expires_at": TimeUtilities.add_hours_to_epoch_time(TimeUtilities.current_time_in_sec(),
                                                                    hours=MAX_NUMBER_OF_TIMES_GETTING_STARTED_EMAIL_SHOULD_FIRE * 24)
            })


    @staticmethod
    def get_mail_body_for_community_creation_get_started(user_instance, community_instance, branch_link=''):
        mail_template = get_template('mails/cm_onboarding/getting_started_cm_onboarding.html').render({
            "community_logo": community_instance.image_link,
            "community_name": community_instance.name,
            "cm_name": user_instance.userinfo.name,
            "dashboard_link": CM_ONBOARDING_CREATE_COMMUNITY_DASHBOARD_LINK,
            "community_brand_color": community_instance.brand_color if community_instance.brand_color else
            DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR,
            "button_text": GETTING_STARTED_CM_BUTTON_TEXT,
            "button_link": branch_link
        })

        mail_subject = GETTING_STARTED_CM_MAIL_SUBJECT.format(user_instance.userinfo.name)

        mail_body = {
            'subject': mail_subject,
            'mail_body': mail_template,
            'mail_recipient_list': [user_instance.userinfo.email],
            'reply_to': [INVITE_MEMBER_REPLY_EMAIL]
        }

        return mail_body

    @staticmethod
    def give_owner_all_member_manager_rights(user_instance, community_instance):
        give_all_manager_rights(user=user_instance, community=community_instance)
        give_all_member_rights(user=user_instance, community=community_instance)

    @staticmethod
    def send_community_creation_email_to_team(member_instance, community_instance):
        # send community created mail to the team
        email_context = {
            'member_name': member_instance.member_id.userinfo.name,
            'community_name': community_instance.name,
            'member_email': member_instance.member_id.userinfo.email,
            'community_id': community_instance.id
        }
        send_created_community_email_to_team.delay(email_context)

    @staticmethod
    def create_content_download_settings_for_community(community_instance):
        content_download_settings_list = []

        for download_setting_type, download_setting_title in DOWNLOAD_SETTING_TYPE_TITLE_MAPPING.items():
            content_download_settings_list.append(ContentDownloadSettings.create_instance({
                'community_instance': community_instance,
                'download_setting_type': download_setting_type,
                'download_setting_title': download_setting_title,
                'enabled': True
            }))

        ModelUtilities.bulk_create_instances(ContentDownloadSettings, content_download_settings_list)

    @staticmethod
    @shared_task
    def create_all_member_cohort_for_new_community(member_id, community_id):
        cohort_body = {
            'name': ALL_MEMBER_COHORT_TEXT,
            'member_ids': [member_id],
            'community_id': community_id,
            'type': cohort_types.ALL_MEMBER,
        }

        from collabmates_api.cohort.cohort_impl import CohortImpl

        cohort_manager = CohortImpl(member_id)

        cohort_response = cohort_manager.create_cohort(cohort_body)

        if cohort_response.get('error_message'):
            error_logger.error(cohort_response)

    @staticmethod
    def validate_fetch_get_started(member_id, community_id):
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return {'success': False, 'error_message': 'Invalid community_id'}

        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not user_instance:
            return {'success': False, 'error_message': 'Invalid member_id'}

        is_admin = Members.get_community_member_state(community_instance, user_instance) == member_states.ADMIN

        if not is_admin:
            return {'success': False, 'error_message': 'You are not the CM of this community!'}

        return {'success': True, 'community_instance': community_instance, 'user_instance': user_instance}

    @staticmethod
    def validate_send_invite_logic(member_id, validated_req_body):
        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not user_instance:
            return {'success': False, 'error_message': 'Invalid member_id'}

        community_instance = ModelUtilities.get_model_instance_or_none(Community,
                                                                       validated_req_body.get('community_id'))

        if not community_instance:
            return {'success': False, 'error_message': 'Invalid community_id'}

        members_filter = ModelUtilities.get_model_filter(Members,
                                                         {'member_id': user_instance,
                                                          'community_id': community_instance})

        if not members_filter:
            return {'success': False, 'error_message': 'You are not part of the community.'}

        is_admin = members_filter[0].state == member_states.ADMIN

        if not is_admin:
            return {'success': False, 'error_message': 'You are not the CM of this community!'}

        return {'success': True, 'community_instance': community_instance, 'user_instance': user_instance}

    @staticmethod
    def send_invite_email_to_given_emails_list(user_instance, community_instance, valid_email_ids_list,
                                               validated_req_body, share_context, link, mail_body):

        mail_body = "<br>".join(mail_body.split("\n"))

        mail_template = get_template('mails/cm_onboarding/invite_members_cm_onboarding.html').render({
            "community_logo": community_instance.image_link,
            "community_name": community_instance.name,
            "cm_name": user_instance.userinfo.name,
            "mail_text": mail_body,
            "community_brand_color": community_instance.brand_color if community_instance.brand_color else
            DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR,
            "join_code": share_context.get('aj') if validated_req_body.get('link_type') == 'free' else '',
            "button_text": INVITE_MEMBERS_BUTTON_TEXT,
            "button_link": link
        })

        mail_subject = INVITE_MEMBERS_SUBJECT.format(community_instance.name)

        send_email_response = MailWrapper.send_email.delay(mail_subject, mail_template,
                                                           valid_email_ids_list, reply_to=[INVITE_MEMBER_REPLY_EMAIL])

        return send_email_response

    @staticmethod
    def send_invite_whatsapp_context_dict(user_instance, community_instance, mobile_nos_list, validated_req_body,
                                          share_context, link_path):
        receivers_list = []

        for mobile_no in mobile_nos_list:
            receiver_info = {
                "whatsappNumber": mobile_no,
                "customParams": [
                    {
                        "name": "community_name",
                        "value": community_instance.name
                    },
                    {
                        "name": "cm_name",
                        "value": user_instance.userinfo.name
                    },
                    {
                        "name": "link",
                        "value": link_path
                    }
                ]
            }

            if validated_req_body.get('link_type') == 'free':
                receiver_info['customParams'].append({
                    "name": "join_code",
                    "value": share_context.get("aj")
                })

            receivers_list.append(receiver_info)

        return receivers_list

    @staticmethod
    @shared_task
    def create_community_async_tasks(user_id, community_id, req_body):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return

        member_filter = ModelUtilities.get_model_filter(Members,
                                                        {'community_id': community_instance,
                                                         'member_id': user_instance})

        if not member_filter:
            return

        member_instance = member_filter[0]

        # making the member engage instance for created community
        engage = Member_Engage.create_instance({'user_instance': user_instance,
                                                'community_instance': community_instance,
                                                'state': member_states.ADMIN,
                                                'click_state': click_states.SET_PURPOSE,
                                                'member_referral': 'Finish setting up your community',
                                                'rights_list': json.dumps(member_rights.ALL_MEMBER_RIGHTS)})

        # give all the CM and member rights to the community creator i.e owner
        CommunityHelper.give_owner_all_member_manager_rights(user_instance, community_instance)

        # give all community setting rights
        give_all_community_setting_rights(community=community_instance)

        save_moderation_history(user=user_instance, community=community_instance,
                                moderation_by=user_instance,
                                type=moderation_history_types.STARTED_COMMUNITY)

        # send community created mail to the team
        CommunityHelper.send_community_creation_email_to_team(member_instance, community_instance)

        # Create Content Download Settings
        CommunityHelper.create_content_download_settings_for_community(community_instance)

        add_community_settings_for_community(community_instance, user_instance)

        create_introduction_question_in_community(community_instance)
        post_purpose_collabcard_for_community(req_body, community_instance, user_instance.id)
        post_master_introductions_for_community(community_instance.id, user_instance.id)
        post_general_collabcard_for_community(community_instance, user_instance.id)
        post_member_directory_link(user_instance, community_instance)

        update_models_for_syncing_apis(SyncTypes.COMMUNITY,
                                       {'community_id': community_instance, 'member_id': user_id},
                                       {'click_state': click_states.DEFAULT})

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': COMMUNITY_HOOD_COMMUNITY_ID,
                                                                  'member_id': user_instance})

        if len(member_filter):
            update_community_get_started(community_instance, get_started_types.JOIN_COMMUNITY_HOOD, is_enabled=True)

    @staticmethod
    @shared_task
    def send_community_moderation_mail_to_cm(community_id):
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return

        members_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance})

        if members_filter.count() < CM_ONBOARDING_COMMUNITY_MODERATION_MIN_MEMBERS_COUNT:
            return

        community_owner_filter = members_filter.filter(is_owner=True)

        if not community_owner_filter:
            return

        community_owner = community_owner_filter[0]

        # CommunityOwner email
        community_owner_email = get_user_email_preferred_verified(community_owner.member_id)

        if not community_owner_email:
            return

        # Check if mail already sent
        user_email_filter = ModelUtilities.get_model_filter(UserEmailsSendStatus,
                                                            {'user': community_owner.member_id,
                                                             'community': community_instance,
                                                             'status_type': user_email_send_status_types.COMMUNITY_MODERATION_EMAIL,
                                                             'is_completed': True})

        if user_email_filter:
            return

        mail_subject = CM_ONBOARDING_COMMUNITY_MODERATION_MAIL_SUBJECT

        mail_template = get_template('mails/cm_onboarding/community_moderation_mail_cm_onboarding.html').render({
            "community_logo": community_instance.image_link,
            "cm_name": community_owner.member_id.userinfo.name,
            "community_brand_color": community_instance.brand_color if community_instance.brand_color
            else DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR,
            "button_link": CM_ONBOARDING_COMMUNITY_MODERATION_BUTTON_LINK,
            "button_text": CM_ONBOARDING_COMMUNITY_MODERATION_BUTTON_TEXT
        })

        send_email_response = MailWrapper.send_email(mail_subject, mail_template,
                                                     [community_owner_email],
                                                     reply_to=[MEMBER_REPLY_EMAIL])

        if send_email_response:
            UserEmailsSendStatus.create_instance({'user': community_owner.member_id,
                                                  'community': community_instance,
                                                  'status_type': user_email_send_status_types.COMMUNITY_MODERATION_EMAIL,
                                                  'is_completed': True})
