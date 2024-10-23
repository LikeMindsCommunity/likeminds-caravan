import json, csv, os

from celery import shared_task
from django.contrib.auth.models import User
from django.template.loader import get_template

import re
from rest_framework import status as status_codes

from cms.models import NewAnswer
from collabmates_api.community.constants import *
from collabmates_api.rest_api import CommunitySerializerV1, CommunitySettingsSerializer, CommunityToastV1Serializer, \
    CommunityGetStartedSerializer, CommunityQuestionsSerializerV2, CommunityAnswersSerializer, get_error_context, \
    CommunityDMSettingsSerializer, CommunityNotificationSettingsSerializer, FeedNotificationSettingsSerializer, \
    ReportTagsSerializer, CommunityConfigurationsSerializer, ChatbotMetaSerializer, CommunityIntegrationStatusSerializer

from collabmates_api.serializers import UserinfoSerializer

from collabmates_api.views import get_leave_community_text, send_notification_for_join_requests, \
    give_default_member_rights, send_notification_to_admins, update_member_rights_in_conversation_engage, \
    set_community_actions, add_community_settings_for_community, post_purpose_collabcard_for_community, \
    post_master_introductions_for_community, post_member_directory_link, post_general_collabcard_for_community, \
    update_community_get_started, get_branch_links_for_community_share_v1, fill_share_context_for_paid_community, \
    fill_share_context_for_unpaid_community, check_join_community_hood_get_started, \
    add_community_upload_image_analytics, create_introduction_question_in_community, edit_community_data, \
    get_community_creator, change_community_level_context_for_paid_community, remove_members, save_moderation_history, \
    remove_all_member_rights, remove_all_manager_rights, check_reports_and_update_action, send_notification_for_removed_member

from collabmates_api.notification import send_sync_notification, send_notification_for_reports

from collabmates_api.sync.model_update import update_models_for_syncing_apis
from utility.mail_category_constants import EmailCategories, EmailSubCategories
from utility.number_utilities import NumberUtilities
from utility.internal_service_utilities import InternalServiceUtilities
from external_services.email.email_wrapper import MailWrapper, MailHelper
from external_services.airtable.airtable_wrapper import AirtableWrapper
from external_services.open_ai.open_ai_wrapper import OpenAiWrapper
from togther.models import Community, Userinfo, Collabcard, Members, ModelUtilities, CommunityUserDelete, \
    card_answers, collabcardState, Member_Engage, communityAnswers, removedMembers, communityToast, userMobiles, \
    communityLevels, conversationEngage, userMemberRights, moderationHistory, communityQuestions, questionFilters, \
    communityExpiryCodes, CommunitySettings, CommunityToastV1, CommunityJoinEmail, userEmails,\
    ContentDownloadSettings, CommunityGetStarted, UserEmailsSendStatus, communityFieldTypes, \
    communityFieldSubTypes, CommunityDirectMessageSettings, CommunityNotificationSettings, FeedNotificationSettings, \
    Report_Tags, Report, CommunityConfigurations, CommunityBillingDates, communityRightsSettings, userAdminRights, \
    memberRights, adminRights, ChatbotMeta, BlockUser, CommunityIntegrationStatus
from collabmates_api.webhook.models import CommunityWebhook
from collabmates_api.static_text import ALL_MEMBER_COHORT_TEXT, CUSTOMISE_JOIN_FORM_MAIL_SUBJECT, \
    PRIVATE_LINK_APP_INVITE_DEFAULT_TOAST, IMAGE_URLS_FOR_QUESTION_TITLES, SENDER_NAME_FOR_EMAIL_COMMS, \
    SENDER_EMAIL_FOR_EMAIL_COMMS
from collabmates_api.static_files import (ICONS)
from collabmates_api.branch import create_community_feed_url, create_community_otl_url, create_payment_page_url, \
    create_community_feed_url_for_cm_onboarding
from collabmates_api.user_moderation_rights import check_admin_edit_community_right, give_all_manager_rights, \
    give_all_member_rights, save_moderation_history, give_all_community_setting_rights, \
    update_member_rights_in_member_engage, check_admin_moderate_dm_settings_right, \
    update_direct_message_right_in_member_rights_schema, check_admin_moderate_feed_and_comments_right, \
    update_feed_rights_in_user_member_rights_table, check_admin_delete_right, check_admin_approve_right, \
    update_poll_rights_in_user_member_rights_table
from django.db.models import Q, F

from external_services.mixpanel.events import MixpanelEvents
from external_services.wa_notification.wa_notification_impl import NotificationImpl

from external_services.segment.segment_impl import SegmentImpl
from external_services.caching.cache_impl import CacheImpl

from utility.cache_keys import (SWARM_CACHE_KEY_CONFIGURATIONS, SWARM_TOP_LIKED_COMMENTS_CACHE_KEY, 
                                KETTLE_CACHE_KEY_COMMUNITY_SETTINGS, KETTLE_CACHE_KEY_USER_META, 
                                KETTLE_CACHE_KEY_PROFILE_META_CONFIGURATIONS, WIDGET_CONFIGURATIONS_CACHE_KEY,
                                SWARM_CACHE_KEY_COMMUNITY_SETTINGS, KETTLE_CACHE_KEY_ANONYMOUS_USER_META,
                                KETTLE_CACHE_KEY_FEED_META_CONFIGURATIONS)
from collabmates_api.community.community_manager import CommunityManager
from .community_view_helper import CommunityViewHelper
from collabmates_api.member_community.member_community_impl import MemberCommunityImpl
from collabmates_api.sdk.models import (SdkClient, CommunityEmailConfiguration)

from collabmates_api.mails import send_created_community_email_to_team, send_report_mail_to_team

from collabmates_api.cohort.cohort_impl import CohortHelper, CohortImpl

from external_services.amazon_s3.s3_client_impl import S3ClientImpl

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.states import member_states, card_types, click_states, member_rights, manager_rights, mobile_states, \
    community_level_states, moderation_history_types, question_states, level_click_states, community_setting_types, \
    SyncTypes, cohort_types, get_started_types, send_invite_types, user_email_send_status_types, \
    email_states, question_change_states, SyncNotificationTypes, edit_field_community_data_types, \
    airtable_webhook_types, WebhookTypes, community_dm_settings_state_types, community_dm_settings_duration_types, \
    api_types, login_types, noti_states, feed_notification_states, deleted_members, report_action_types, \
    CommunityDMSettingTypes, ChatNotificationTypes, FeedNotifcationTypes, ReportClosingStatus, GuestFlowUserTypes, \
    UserRoles, CommunityIntegrationStatusTypes

from utility.time_utilities import TimeUtilities
from utility.url_utilities import UrlUtilities
from utility.constants import (PLATFORM_CODE_WEB, COMMUNITY_CONFIGURATIONS, MEDIA_LIMITS_CONFIGURATION,
                               FEED_METADATA_CONFIGURATION, PROFILE_METADATA_CONFIGURATION, NSFW_FILTERING_CONFIGURATION, 
                               PLATFORM_TYPE_CARAVAN_SERVICE, GUEST_FLOW_METADATA_CONFIGURATION,
                               WIDGETS_METADATA_CONFIGURATION, PERSONALISED_FEED_WEIGHTS, FEED_SETTINGS_CONFIGURATION,
                               CREATE_FEED_POLL_COMMUNITY_VALUES, CHATBOT_CONFIGURATIONS, CHATBOT_PROVIDER_OPENAI,
                               CHATBOT_DEFAULT_THREAD_CONTEXT)
from utility.api_client import ApiClient
from utility.response_utilities import ResponseUtilities
from utility.validation_utilities import ValidationUtilities
from utility.version_utilities import VersionUtilities
from utility.string_utilities import StringUtilities

from utility.utils import check_notification_flag, get_first_name_from_name, is_version_code_supported_for_intro_room, \
    decode_option, community_default_image, community_default_thumbnail
from utility.celery_tasks import (create_member_dm_chatroom, create_intro_room_disabled_text_for_community_members,
                                  update_preview_for_account_image_change, update_multiple_previews_in_community,
                                  update_community_pin_chatrooms_list_in_cache)
from ..chatroom.chatroom_impl import ChatroomImpl, ChatroomHelper
from ..search.sync import ElasticSearchSync
from ..notifications.tasks import send_mail_for_first_time_edit_community_questions
from ..notifications.tasks_impl import TasksHelper
from ..user.user_impl import UserHelper, UserImpl

from ..raw_queries import get_members_meta_list, get_users_meta_info

from ..tasks import send_community_confirmation_email, cm_onboarding_version_check, get_user_email_preferred_verified, \
    directory_questions_v2_version_check, get_user_phone, update_report_count_for_all_promoters

from ..sms import send_community_confirmation_sms
from ..utility import single_community_view_version_check, free_link_and_freemium_community_version_check, \
    m2cm_v2_version_check
from collabmates_api.utility import paginate_list

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class CommunityImpl(CommunityManager):
    member_id = None
    community_id = None
    version_code = None

    def __init__(self, member_id: str, community_id: str = None, version_code: str = None, device_id: str = None,
                 request_platform: str = None, api_key: str = None, sdk_source: str = None, api_version_code: int = 0):

        self.member_id = member_id
        self.community_id = community_id
        self.version_code = version_code
        self.device_id = device_id
        self.request_platform = request_platform
        self.api_key = api_key
        self.sdk_source = sdk_source
        self.api_version_code = api_version_code

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

    def get_api_key(self):
        return self.api_key

    def get_sdk_source(self):
        return self.sdk_source

    def get_api_version_code(self):
        return self.api_version_code

    def set_community_id(self, community_id) -> None:
        self.community_id = community_id

    def _community_menu_options(self, state, community_instance, platform_code: str, version_code: int) -> []:

        menu = []
        delete_menu_option = EDIT_COMMUNITY_RIGHT_MENU_OPTION_NUMBER

        if state == member_states.ADMIN:
            user_instance = CommunityHelper.fetch_user_instance(self.get_member_id())

            menu = MENU['promoter'].copy()

            if directory_questions_v2_version_check(platform_code, version_code):
                menu = MENU['promoter2'].copy()
                delete_menu_option = EDIT_COMMUNITY_RIGHT_MENU_OPTION_NUMBER_FOR_DIRECTORY_QUESTIONS

            has_right = check_admin_edit_community_right(user_instance, community_instance)

            if not has_right:
                del menu[delete_menu_option]

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

        if chatroom_instance.chatroom_image_url:
            chatroom_context['chatroom_image_url'] = chatroom_instance.chatroom_image_url

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
        validated_req = CommunityHelper.validate_fetch_community_request(self.get_community_id(),
                                                                         api_key=self.get_api_key())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_req.get('community_instance')
        self.set_community_id(community_instance.id)

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

        return {'success': True, 'community': community_context}

    def get_community_members(self) -> list:
        return Members.fetch_community_members([self.get_community_id()])

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

        CacheImpl.delete_key('COMMUNITY_BRANDING_{}'.format(self.get_community_id()))
        CacheImpl.delete_key('WHITELABEL_COMMUNITY_{}'.format(self.get_community_id()))

        domains_data = CacheImpl.get_cache('WHITELABEL_DOMAINS')
        domains_json = json.loads(domains_data) if domains_data else {}
        updated_domains_json = {**domains_json}

        for domain, community_id in domains_json.items():
            if community_id == self.get_community_id():
                del updated_domains_json[domain]
                domains_cache_data = json.dumps(updated_domains_json)

                CacheImpl.delete_key('WHITELABEL_DOMAINS')
                CacheImpl.set_cache('WHITELABEL_DOMAINS', domains_cache_data)

        return {'success': True}

    @staticmethod
    def generate_join_data_for_webhook(member_id, community_id):

        webhook_data = {
            'question_answers': [],
            'plan_type': FREE_PLAN,
            'plan_name': None
        }

        community_questions_list = list(ModelUtilities.get_model_filter(
            communityQuestions, {'community_id': community_id}).values_list('id', flat=True))

        community_answers = ModelUtilities.get_model_filter(
            communityAnswers, {'community_id': community_id, 'member_id': member_id,
                               'question_id__in': community_questions_list}
        )

        for answer in community_answers:
            answer_object = {
                'question': answer.question_title,
                'answer': answer.question_answer
            }

            webhook_data['question_answers'].append(answer_object)

        subscriptions = UserHelper.fetch_user_subscriptions(member_id, community_id=community_id)

        for subscription in subscriptions:

            if subscription.get('plan'):
                webhook_data['plan_type'] = PAID_PLAN if subscription['plan'].get('is_paid') else FREE_PLAN
                webhook_data['plan_name'] = subscription['plan'].get('name')

        return webhook_data

    @staticmethod
    @shared_task
    def send_join_data_on_webhook(member_id, community_id):

        webhook_instances = ModelUtilities.get_model_filter(
            CommunityWebhook, {'community_id': community_id, 'webhook_type': WebhookTypes.COMMUNITY_JOINED.value})

        if not webhook_instances:
            return

        webhook_instance = webhook_instances[0]

        webhook_data = CommunityImpl.generate_join_data_for_webhook(member_id, community_id)

        client = ApiClient()
        client.update_request_url(webhook_instance.url)
        client.update_body(webhook_data)
        client.post()
        client.fetch_response()

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

        ModelUtilities.delete_record_in_model(removedMembers, {'community': community_instance,
                                                               'member': user_instance})

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
        self.send_join_data_on_webhook.delay(user_instance.id, community_instance.id)

    def set_members_count_in_community(self, community_id, members_count):

        ModelUtilities.model_update(Community, {'id': community_id}, {'members_count': members_count})

    def make_requesting_user_as_pending_member(self, community_instance, user_instance, shared_by_user, req_body):
        questions_list_key = DEFAULT_QUESTIONS_LIST_KEY

        if req_body.get('is_directory_questions_v2'):
            questions_list_key = DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY

        CommunityHelper.save_responses_of_member_in_community.delay(user_instance.id,
                                                                    community_instance.id,
                                                                    req_body.get(questions_list_key),
                                                                    req_body.get('is_directory_questions_v2'))

        Members.create_instance({'user_instance': user_instance,
                                 'community_instance': community_instance,
                                 'state': member_states.PENDING_MEMBER,
                                 'joined_by': shared_by_user
                                 })

        ModelUtilities.update_or_create_model(Member_Engage, {
            'member_id': user_instance,
            'community_id': community_instance
        }, {
            'member_state': member_states.PENDING_MEMBER,
            'click_state': click_states.PENDING_APPROVAL,
            'order_time': TimeUtilities.current_time_in_milliseconds()
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
        questions_list_key = DEFAULT_QUESTIONS_LIST_KEY

        if req_body.get('is_directory_questions_v2'):
            questions_list_key = DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY

        CommunityHelper.save_responses_of_member_in_community.delay(user_instance.id,
                                                                    community_instance.id,
                                                                    req_body.get(questions_list_key),
                                                                    req_body.get('is_directory_questions_v2'))
        introduction_answer = CommunityHelper.create_introduction_text_for_intro_chatroom(community_instance,
                                                                                          user_instance,
                                                                                          req_body.get(questions_list_key),
                                                                                          req_body.get('is_directory_questions_v2'))
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
        questions_list_key = DEFAULT_QUESTIONS_LIST_KEY

        if req_body.get('is_directory_questions_v2'):
            questions_list_key = DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY

        CommunityHelper.save_responses_of_member_in_community.delay(user_instance.id,
                                                                    community_instance.id,
                                                                    req_body.get(questions_list_key),
                                                                    req_body.get('is_directory_questions_v2'))
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
                                                                                          req_body.get(questions_list_key),
                                                                                          req_body.get('is_directory_questions_v2'))
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
        create_member_dm_chatroom.delay(user_instance.id, community_instance.id, is_joining=True,
                                        is_m2cm_v2=req_body.get('is_m2cm_v2'))

        CohortHelper.add_all_member_to_cohort(community_instance.id, [user_instance.id])

    def make_requesting_user_as_member_of_community_automatically(self, user_instance, community_instance,
                                                                  auto_join_code, shared_by_user, req_body):
        questions_list_key = DEFAULT_QUESTIONS_LIST_KEY

        if req_body.get('is_directory_questions_v2'):
            questions_list_key = DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY

        CommunityHelper.save_responses_of_member_in_community.delay(user_instance.id,
                                                                    community_instance.id,
                                                                    req_body.get(questions_list_key),
                                                                    req_body.get('is_directory_questions_v2'))
        Members.create_instance({'user_instance': user_instance,
                                 'community_instance': community_instance,
                                 'state': member_states.MEMBER,
                                 'joined_by': shared_by_user,
                                 'custom_title': "Member",
                                 'became_member_at': TimeUtilities.current_time_in_sec()
                                 })

        ModelUtilities.update_or_create_model(Member_Engage, {
            'member_id': user_instance,
            'community_id': community_instance
        }, {
            'member_state': member_states.MEMBER,
            'order_time': TimeUtilities.current_time_in_milliseconds()
        })

        update_member_rights_in_member_engage.delay(community_instance.id, user_instance.id)

        CommunityHelper.set_follow_status_for_announcement_chatroom_for_community(community_instance,
                                                                                  user_instance)
        introduction_answer = CommunityHelper.create_introduction_text_for_intro_chatroom(community_instance,
                                                                                          user_instance,
                                                                                          req_body.get(questions_list_key),
                                                                                          req_body.get('is_directory_questions_v2'))
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
                                        request_platform=platform, is_joining=True,
                                        is_m2cm_v2=req_body.get('is_m2cm_v2'))

        CohortHelper.add_all_member_to_cohort(self.get_community_id(), [self.get_member_id()])

        self._send_join_email_to_member(user_instance.id, community_instance.id)

        CohortHelper.add_member_to_respective_question_based_cohorts(self.get_member_id(), self.get_community_id())

        self.send_join_data_on_webhook.delay(user_instance.id, community_instance.id)

    @staticmethod
    def send_approve_reject_data_on_airtable(user_instance, community_instance, approved):
        email = get_user_email_preferred_verified(user_instance.id)

        airtable_data = {
            'user_id': user_instance.id,
            'community_id': community_instance.id,
            'user_email': email,
            'approved': approved
        }

        airtable_manager = AirtableWrapper(endpoint_type=airtable_webhook_types.APPROVE_REQUEST)
        airtable_manager.send_data(airtable_data)

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

            is_m2cm_v2 = m2cm_v2_version_check(self.get_request_platform(), self.get_version_code())

            CommunityHelper.run_async_for_community_approve(community_instance, user_instance,
                                                            promoter_userinfo_instance, is_m2cm_v2=is_m2cm_v2)

            CohortHelper.add_all_member_to_cohort(community_instance.id, [user_instance.id])

            self._send_join_email_to_member(user_instance.id, community_instance.id)

            cohort_manager = CohortImpl(member_id=user_instance.id)

            member_cohort_response = cohort_manager.add_user_to_subscription_plans_when_membership_approved(
                community_id=community_instance.id
            )

            if member_cohort_response.get('error_message'):
                info_logger.info(
                    f'Unable to add member to respective subscription plan cohort: {member_cohort_response}')

            CohortHelper.add_member_to_respective_question_based_cohorts(member_id=user_instance.id,
                                                                         community_id=community_instance.id)

        else:

            member_state = Members.get_community_member_state(community_instance, user_instance)

            if member_state != member_states.PENDING_MEMBER:
                return {'success': False, 'error_message': "User is not a pending member!"}

            self._decline_community_join_request(community_instance, user_instance)
            members_count = Members.get_members_count_in_community(community_instance)
            self.set_members_count_in_community(community_instance.id, members_count)

            CommunityHelper.run_async_task_for_community_declined(community_instance, user_instance,
                                                                  promoter_userinfo_instance)

            ElasticSearchSync.delete_member_from_community.delay(self.get_member_id(), self.get_community_id())

        self.send_approve_reject_data_on_airtable(user_instance, community_instance, req_body.get('accepted'))

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
        is_directory_questions_enabled = directory_questions_v2_version_check(self.get_request_platform(),
                                                                              self.get_version_code())
        is_m2cm_v2 = m2cm_v2_version_check(self.get_request_platform(), self.get_version_code())

        req_body['is_directory_questions_v2'] = is_directory_questions_enabled
        req_body['is_m2cm_v2'] = is_m2cm_v2

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

    def fetch_members_meta(self, member_ids, search_name: str = None, page: int = None, page_size: int = None,
                           order_by_name: bool = None):
        validated_req = CommunityViewHelper.validate_fetch_members_meta_request(self.get_member_id(),
                                                                                self.get_community_id(),
                                                                                member_ids,
                                                                                api_key=self.get_api_key())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_req.get('community_instance')
        member_ids = validated_req.get('member_ids')

        members = ChatroomImpl.compute_tagging_list_of_community_members(community_instance, member_ids, 
                                                                         search_name, page, page_size, 
                                                                         order_by_name=order_by_name,
                                                                         sdk_client_info_flag=True)
        members = ChatroomImpl.remove_guest_user_from_participants_data_list(members)

        # Add question answers data in users info
        members_question_answer_data = CommunityHelper.get_members_filled_community_answers_data(community_instance,
                                                                                                 members)

        for member in members:

            if member.get('id') in members_question_answer_data:
                member['question_answers'] = members_question_answer_data.get(member.get('id'))

        return {'success': True, 'members': members}

    # Fetch members meta v2, with pagination & search and returns is_deleted key in member object
    def fetch_members_meta_v2(self, member_ids, page, page_size, search_name):

        # validate request and load validated data
        validated_req = CommunityViewHelper.validate_fetch_members_meta_request(self.get_member_id(),
                                                                                self.get_community_id(),
                                                                                member_ids,
                                                                                api_key=self.get_api_key())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_req.get('community_instance')
        member_ids = validated_req.get('member_ids')

        # Fetch users blocked by user
        filter_dict = {
            'community_id': community_instance.id
        }

        excluded_user_filter = ModelUtilities.get_model_filter(BlockUser, filter_dict).filter(
            Q(blocking_user=self.get_member_id()) | Q(blocked_user=self.get_member_id()))

        excluded_user_ids = list(excluded_user_filter.values_list('blocking_user', flat=True)) + \
                            list(excluded_user_filter.values_list('blocked_user', flat=True))

        # Get members meta list
        members_list = CommunityHelper.compute_members_meta_list(community_instance, member_ids, page, 
                                                                 page_size, search_name, excluded_user_ids)

        # Add question answers data in users info
        members_question_answer_data = CommunityHelper.get_members_filled_community_answers_data(community_instance,
                                                                                                 members_list)

        for member in members_list:

            if member.get('id') in members_question_answer_data:
                member['question_answers'] = members_question_answer_data.get(member.get('id'))
                
            else:
                member['question_answers'] = None

        return {'success': True, 'members': members_list}

    def fetch_content_download_settings(self, chatroom_id=None):
        validated_req = CommunityHelper.validate_fetch_content_download_settings_request(
            self.get_member_id(), self.get_community_id(), self.get_api_key(), chatroom_id)

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_req.get('community_instance')

        # Now fetch settings from ContentDownloadSettings table
        content_settings_instance = ModelUtilities.get_model_filter(ContentDownloadSettings,
                                                                    {"community_id": community_instance}).order_by("id")

        content_settings = {
            "success": True,
            "content_download_settings": self.content_download_settings_serializer(content_settings_instance)
        }

        return content_settings

    def update_content_download_settings(self, content_download_settings_list):
        validated_req = CommunityHelper.validate_update_content_download_settings_request(
            self.get_member_id(), self.get_api_key())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        community_instance = validated_req.get('community_instance')

        member_community_mapping = {}
        community_mapping = {}

        if len(content_download_settings_list):

            for content_download_setting in content_download_settings_list:

                community_id = community_instance.id if community_instance else content_download_setting["community_id"]

                if community_id in community_mapping:
                    community_instance = community_mapping[community_id]

                elif not community_instance:
                    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

                    if not community_instance:
                        return ResponseUtilities.get_impl_error_context("Invalid community ID",
                                                                        status_code=status_codes.HTTP_400_BAD_REQUEST)

                    else:
                        community_mapping[community_id] = community_instance

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
                                                    "community_id_id": community_id,
                                                    "download_setting_type": content_download_setting[
                                                        "download_setting_type"],
                                                    "download_setting_title": content_download_setting[
                                                        "download_setting_title"]
                                                },
                                                {
                                                    "enabled": content_download_setting["enabled"],
                                                    "updated_at": TimeUtilities.current_time_in_milliseconds()
                                                })

                else:
                    return ResponseUtilities.get_impl_error_context("User doesn’t have ability to update content "
                                                                    "download settings",
                                                                    status_code=status_codes.HTTP_400_BAD_REQUEST)

        else:
            return ResponseUtilities.get_impl_error_context("Error in fetching content download settings.",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        return {'success': True}

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

        community_instance = SdkClient.get_community_instance_or_none(community_id=self.get_community_id(),
                                                                      api_key=self.get_api_key())

        if not community_instance:
            return {'success': False, 'error_message': "Invalid community ID/API Key!"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of this community"}

        community_settings_list = ModelUtilities.get_model_filter(CommunitySettings, {"community": community_instance})

        community_settings_serializer = CommunitySettingsSerializer(community_settings_list, many=True)

        community_settings = json.loads(json.dumps(community_settings_serializer.data))
        filtered_community_settings_list = []
        is_m2cm_v2 = m2cm_v2_version_check(self.get_request_platform(),
                                           self.get_version_code(),
                                           api_version_code=self.get_api_version_code())

        is_chatroom_invite = VersionUtilities.check_version(self.get_request_platform(), self.get_version_code(),
                                                            VersionUtilities.chatroom_invite)
        is_create_intro_room_check = VersionUtilities.check_version(self.get_request_platform(),
                                                                    self.get_version_code(),
                                                                    VersionUtilities.create_intro_room)

        for community_setting in community_settings:

            if all([community_setting.get('setting_type') in [community_setting_types.DIRECT_MESSAGES,
                                                              community_setting_types.MEMBERS_CAN_DM,
                                                              community_setting_types.DIRECT_MESSAGE_SETTING,
                                                              community_setting_types.DIRECT_MSGS_GROUP_MSGS],
                    not is_m2cm_v2]):
                continue

            if all([community_setting.get('setting_type') in [community_setting_types.CHATROOMS,
                                                              community_setting_types.SECRET_CHATROOMS_INVITE,
                                                              community_setting_types.POST_GROUPS,
                                                              community_setting_types.SECRET_GROUP_INVITE],
                    not is_chatroom_invite]):
                continue

            if all([not check_admin_moderate_dm_settings_right(user_instance, community_instance),
                    community_setting.get('setting_type') == community_setting_types.DIRECT_MESSAGE_SETTING]):
                continue

            if all([community_setting.get('setting_type') in [community_setting_types.CREATE_INTRO_ROOMS],
                    not is_create_intro_room_check]):
                continue

            filtered_community_settings_list.append(community_setting)

        response = {
            'success': True,
            'community_settings': filtered_community_settings_list
        }

        return response

    def update_community_settings(self, community_settings_list):

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid User ID"}

        community_instance = SdkClient.get_community_instance_or_none(community_id=self.get_community_id(),
                                                                      api_key=self.get_api_key())

        if not community_instance:
            return {'success': False, 'error_message': "Invalid Community ID/API key!"}

        self.set_community_id(community_instance.id)

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of this community"}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return {'success': False, 'error_message': "User doesn’t have ability to update community settings"}

        disabled_community_settings_context_list = []

        for community_setting in community_settings_list:

            if all([community_setting["setting_type"] in (community_setting_types.DIRECT_MESSAGES,
                                                          community_setting_types.MEMBERS_CAN_DM,
                                                          community_setting_types.DIRECT_MSGS_GROUP_MSGS),
                    not check_admin_moderate_dm_settings_right(user_instance, community_instance)]):
                continue

            if all([community_setting["setting_type"] == community_setting_types.FEED,
                   not check_admin_moderate_feed_and_comments_right(user_instance, community_instance)]):
                continue

            if all([community_setting["setting_type"] == community_setting_types.SECRET_CHATROOMS_INVITE,
                    community_setting['enabled']]):
                is_chatroom_setting_enabled = False

                chatroom_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                                          {'community': self.get_community_id(),
                                                                           'setting_type': community_setting_types.CHATROOMS})

                if chatroom_setting_filter:
                    is_chatroom_setting_enabled = chatroom_setting_filter[0].enabled

                for com_setting in community_settings_list:

                    if com_setting["setting_type"] == community_setting_types.CHATROOMS:
                        is_chatroom_setting_enabled = com_setting["enabled"]

                if not is_chatroom_setting_enabled:
                    return {'success': False, 'error_message': "Chatroom setting is disabled!"}

            if all([community_setting["setting_type"] == community_setting_types.CHATROOMS,
                    not community_setting['enabled']]):
                filter_dict = {
                    "community_id": self.get_community_id(),
                    "setting_type": community_setting_types.SECRET_CHATROOMS_INVITE,
                }

                update_dict = {
                    'enabled': False,
                    'updated_at': TimeUtilities.current_time_in_milliseconds(),
                    'enabled_by': None
                }

                ModelUtilities.model_update(CommunitySettings, filter_dict, update_dict)

            if all([community_setting["setting_type"] == community_setting_types.SECRET_GROUP_INVITE,
                    community_setting['enabled']]):
                is_post_group_setting_enabled = False

                post_group_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                                            {'community': self.get_community_id(),
                                                                             'setting_type': community_setting_types.POST_GROUPS})

                if post_group_setting_filter:
                    is_post_group_setting_enabled = post_group_setting_filter[0].enabled

                for com_setting in community_settings_list:

                    if com_setting["setting_type"] == community_setting_types.POST_GROUPS:
                        is_post_group_setting_enabled = com_setting["enabled"]

                if not is_post_group_setting_enabled:
                    return {'success': False, 'error_message': "Post group setting is disabled!"}

            if all([community_setting["setting_type"] == community_setting_types.POST_GROUPS,
                    not community_setting['enabled']]):
                filter_dict = {
                    "community_id": self.get_community_id(),
                    "setting_type": community_setting_types.SECRET_GROUP_INVITE,
                }

                update_dict = {
                    'enabled': False,
                    'updated_at': TimeUtilities.current_time_in_milliseconds(),
                    'enabled_by': None
                }

                ModelUtilities.model_update(CommunitySettings, filter_dict, update_dict)

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

            if all([community_setting["setting_type"] == community_setting_types.DIRECT_MESSAGES,
                    community_setting['enabled']]):
                update_dict['setting_sub_title'] = DM_COMMUNITY_SETTING_SUB_TITLE_WHEN_ENABLED
                update_direct_message_right_in_member_rights_schema.delay(community_id=community_instance.id,
                                                                          is_enabled=True)
                community_instance.hide_dm_tab = False
                community_instance.save()

            elif all([community_setting["setting_type"] == community_setting_types.DIRECT_MESSAGES,
                      not community_setting['enabled']]):
                update_dict['setting_sub_title'] = COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING.get(
                    community_setting_types.DIRECT_MESSAGES)
                update_direct_message_right_in_member_rights_schema.delay(community_id=community_instance.id,
                                                                          is_enabled=False)

                community_instance.hide_dm_tab = True
                community_instance.save()

            if community_setting["setting_type"] == community_setting_types.FEED:
                update_feed_rights_in_user_member_rights_table.delay(community_id=community_instance.id,
                                                                     is_enabled=community_setting['enabled'])
                CommunityHelper.update_feed_notification_settings_based_on_feed_setting.delay(
                    community_id=community_instance.id, is_enabled=community_setting['enabled'])
                
                CommunityHelper.update_feed_create_poll_settings_based_on_feed_setting.delay(
                    community_id=community_instance.id, user_id=user_instance.id ,is_enabled=community_setting['enabled']
                    )

            if all([community_setting["setting_type"] == community_setting_types.MEMBERS_CAN_DM,
                    community_setting['enabled']]):
                community_dm_settings = ModelUtilities.get_model_filter(CommunityDirectMessageSettings,
                                                                        {'community_id': community_instance.id})
                if not community_dm_settings:
                    ModelUtilities.update_or_create_model(CommunityDirectMessageSettings,
                                                          {'community_id': community_instance.id},
                                                          {'state': community_dm_settings_state_types.UNLIMITED})

                cohort_right_add = CohortHelper.add_members_can_dm_right_in_all_member_cohort(community_instance)

                if not cohort_right_add.get('success'):
                    return cohort_right_add

            if community_setting["setting_type"] == community_setting_types.CREATE_POLL:
                update_poll_rights_in_user_member_rights_table.delay(community_id=community_instance.id,
                                                                     is_enabled=community_setting['enabled'])
                
            if community_setting["setting_type"] == community_setting_types.NSFW_FILTERING:

                # Update NSFW filtering configuration in community
                CommunityHelper.update_configuration_of_community.delay(community_instance.id, 
                                                                        user_instance.id,
                                                                        NSFW_FILTERING_CONFIGURATION,
                                                                        {'enabled': community_setting["enabled"]})
                
            if community_setting["setting_type"] in [community_setting_types.USER_TOPICS_CONNECTION,
                                                     community_setting_types.FEED_REPOST,
                                                     community_setting_types.POST_APPROVAL_NEEDED,
                                                     community_setting_types.ENABLE_PERSONALISED_FEED,
                                                     community_setting_types.USER_CONNECTION]:

                # Delete kettle community settings cache if user topics connection, feed repost, post approval needed
                # setting is updated
                InternalServiceUtilities.delete_cache_from_kettle_service.delay(
                    community_instance.id, user_instance.id,
                    [KETTLE_CACHE_KEY_COMMUNITY_SETTINGS.format(community_instance.id)])

            if community_setting["setting_type"] in [community_setting_types.POST_APPROVAL_NEEDED,
                                                     community_setting_types.FEED_REPOST,
                                                     community_setting_types.ENABLE_PERSONALISED_FEED,
                                                     community_setting_types.USER_TOPICS_CONNECTION, 
                                                     community_setting_types.USER_CONNECTION]:
                
                # Delete swarm community settings cache if post apporval needed setting is updated
                InternalServiceUtilities.delete_cache_from_swarm_service.delay(
                    community_instance.id, user_instance.id,
                    SWARM_CACHE_KEY_COMMUNITY_SETTINGS.format(community_instance.id))

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

        mail_data, should_send_email = CommunityImpl._fetch_join_email_data(community_id, community_instance)

        if should_send_email:
            from collabmates_api.sdk.models import (CommunityEmailConfiguration)

            email_sender_data = CommunityEmailConfiguration.get_email_sender_data_for_community(community_id)

            sender_name = email_sender_data.get('name') if email_sender_data.get('name') \
                else SENDER_NAME_FOR_EMAIL_COMMS

            sender_email = email_sender_data.get('from_email') if email_sender_data.get('from_email') \
                else SENDER_EMAIL_FOR_EMAIL_COMMS

            reply_to_email = mail_data.get('reply_email') if email_sender_data.get('reply_email') \
                else SENDER_EMAIL_FOR_EMAIL_COMMS

            mail_categories = MailHelper.get_email_category_list_using_category_subcategory(EmailCategories.WELCOME,
                                                                                            EmailSubCategories.WELCOME)

            MailWrapper.send_email_with_custom_from_email.delay(
                mail_data["subject"],
                mail_data["body"],
                to_mails_list=mail_to,
                from_email=sender_email,
                reply_to=reply_to_email,
                categories=mail_categories,
                from_name=sender_name)

    @staticmethod
    def _fetch_join_email_data(community_id, community_instance) -> {}:

        data = {
            "reply_to": None,
            "subject": None,
            "body": None
        }

        should_send_email = False

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
            data["body"] = DEFAULT_JOIN_EMAIL_BODY

        else:
            join_email_instance = join_email_instances[0]
            data["reply_to"] = [join_email_instance.reply_to]
            data["subject"] = join_email_instance.subject
            data["body"] = join_email_instance.body

            should_send_email = True

        return data, should_send_email

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

        join_email_data, _ = self._fetch_join_email_data(self.get_community_id(), community_instance)

        return {"success": True, "join_email": join_email_data}

    def create_community(self, req_body) -> {}:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': 'Invalid member-id'}

        validate_req_body = CommunityHelper.create_community_validation(req_body)

        if 'error_message' in validate_req_body:
            return validate_req_body

        community_state = 0
        branding = None
        whitelabel_info = None

        if validate_req_body.get('branding'):
            try:
                branding = json.dumps(validate_req_body['branding'])

            except:
                error_logger.error('error in branding key while community creation')

        if validate_req_body.get('is_whitelabel') and validate_req_body.get('whitelabel_info'):
            try:
                whitelabel_info = json.dumps(validate_req_body['whitelabel_info'])

            except:
                error_logger.error('error in whitelabel_info key while community creation')

        if directory_questions_v2_version_check(self.get_request_platform(), self.get_version_code()):
            type_id, sub_type_id = CommunityHelper.get_default_community_type_subtype_id()

        else:
            type_id = TYPE_ID_WITH_NO_DIRECTORY_QUESTIONS
            sub_type_id = SUB_TYPE_ID_WITH_NO_DIRECTORY_QUESTIONS

        purpose = validate_req_body.get('headline', None)

        is_sdk = req_body.get('type', api_types.Non_SDK) == api_types.SDK

        if is_sdk and (not purpose):
            purpose = SDK_COMMUNITY_HEADLINE

        community_instance = Community.create_instance({'name': validate_req_body['name'],
                                                        'members_count': 1,
                                                        'purpose': purpose,
                                                        'brand_color': validate_req_body.get('brand_color', None),
                                                        'image_link': validate_req_body.get('image_url', None),
                                                        'thumbnail': community_default_thumbnail,
                                                        'type': type_id,
                                                        'sub_type': sub_type_id,
                                                        'hide_community': community_state,
                                                        'branding': branding,
                                                        'is_whitelabel': validate_req_body.get('is_whitelabel', False),
                                                        'whitelabel_info': whitelabel_info})

        if validate_req_body.get('has_logo_uploaded', False):
            add_community_upload_image_analytics.delay(user_instance.id, community_instance.id, community_instance.name)

        self.set_community_id(community_instance.id)

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

        CommunityHelper.send_create_community_welcome_whatsapp_message.delay(user_instance.id,
                                                                             community_instance.id)
        CommunityHelper.send_communtiy_creation_segment_events.delay(user_instance.id,
                                                                     SEGMENT_COMMUNITY_CREATION_EVENT_NAME,
                                                                     {"community_id": community_instance.id,
                                                                      "community_name": community_instance.name})
        CommunityHelper.set_user_email_status.delay(user_instance.id, community_instance.id)

        CommunityHelper.set_community_data_in_cache(community_instance.id)

        CommunityHelper.create_community_noti_settings_instance_on_community_creation.delay(community_instance.id)

        community_serializer = CommunitySerializerV1(community_instance,
                                                     context={"current_user_id": self.get_member_id(),
                                                              "is_sdk": is_sdk},
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
        validated_req = CommunityHelper.validate_send_invite_request(self.get_member_id(),
                                                                     req_body,
                                                                     self.get_api_key())

        if validated_req.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req.get('user_instance')
        community_instance = validated_req.get('community_instance')

        self.set_community_id(community_instance.id)

        if req_body.get('type') == send_invite_types.EMAIL_INVITE:
            email_ids_list = CommunityHelper.get_list_from_comma_string(req_body.get('email_id'))

            valid_email_ids_list = [email_id for email_id in email_ids_list if CommunityHelper.is_valid_email(email_id)]

            if not len(valid_email_ids_list):

                if len(email_ids_list) < 2:
                    error_text = 'Invalid email ID!'

                else:
                    error_text = "Invalid email ID's!"

                return ResponseUtilities.get_impl_error_context(error_text,
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)

            mail_text = req_body.get('text')

            CommunityHelper.send_invite_email_to_given_emails_list(user_instance, community_instance,
                                                                   valid_email_ids_list, req_body,
                                                                   self.get_request_platform(),
                                                                   self.get_version_code(), mail_text)

            update_community_get_started(community_instance, get_started_types.INVITE_MEMBERS_TYPE, is_enabled=True)
            return {'success': True}

        elif req_body.get('type') == send_invite_types.WHATSAPP_INVITE:
            mobile_nos_list = CommunityHelper.get_list_from_comma_string(req_body.get('mobile_no'))
            mobile_nos_list = [NumberUtilities.get_integer_from_string(i) if str(i).isdigit() else i for i in
                               mobile_nos_list]

            template_name = WHATSAPP_INVITE_TEMPLATE_WITH_CODE_NAME if req_body.get('link_type') == FREE_PLAN \
                else WHATSAPP_INVITE_TEMPLATE_WITHOUT_CODE_NAME

            receivers_list = CommunityHelper.send_invite_whatsapp_context_dict(user_instance, community_instance,
                                                                               mobile_nos_list, req_body,
                                                                               self.get_request_platform(),
                                                                               self.get_version_code())

            updated_user_data = TasksHelper.update_wa_subscription_user_data(receivers_list, template_name)

            for user_data in updated_user_data:
                NotificationImpl.send_bulk_wa_notification.delay(user_data["user_data_list"],
                                                                 user_data["template_name"],
                                                                 user_data["broadcast_name"])

            update_community_get_started(community_instance, get_started_types.INVITE_MEMBERS_TYPE, is_enabled=True)

            return {'success': True}

        else:
            return ResponseUtilities.get_impl_error_context('Invalid type!',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

    def edit_questions(self, req_body) -> {}:
        validated_req_body = CommunityHelper.validate_edit_question_request(self.get_member_id(),
                                                                            self.get_community_id(),
                                                                            self.get_api_key(),
                                                                            req_body)

        if not validated_req_body.get('success'):
            return validated_req_body

        user_instance = validated_req_body.get('user_instance')
        community_instance = validated_req_body.get('community_instance')
        questions_list = validated_req_body.get('questions_list')

        self.set_community_id(community_instance.id)

        new_questions_list = []
        edited_questions_list = []
        deleted_questions_list = []
        is_edit_required = False

        for question in questions_list:

            if question.get('question_change_state', None) is None:
                return get_error_context(False, 'Please send question_change_state')

            if question.get('question_change_state') == question_change_states.NEW_QUESTION:
                new_questions_list.append(question)

            elif question.get('question_change_state') == question_change_states.EDIT_QUESTION:
                edited_questions_list.append(question)

            elif question.get('question_change_state') == question_change_states.DELETE_QUESTION:
                deleted_questions_list.append(question)

        if new_questions_list:
            CommunityHelper.create_new_community_questions(community_instance, new_questions_list,
                                                           user_id=self.get_member_id())
            is_edit_required = True

        if edited_questions_list:
            CommunityHelper.update_community_questions(community_instance, edited_questions_list,
                                                       user_id=self.get_member_id())
            is_edit_required = True

        if deleted_questions_list:
            CommunityHelper.delete_community_questions(community_instance, deleted_questions_list,
                                                       user_id=self.get_member_id())

        edit_community_data(community_instance, user_instance,
                            edit_field=edit_field_community_data_types.EDIT_DIRECTORY)

        from collabmates_api.notification import send_notification_for_directory_creation, send_sync_notification
        send_sync_notification.delay({'community_id': community_instance.id,
                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

        if not SdkClient.is_sdk_community(community_id=self.get_community_id()):

            # Updating members state table for editing
            if is_edit_required:
                update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                               {'community_id': community_instance},
                                               {'edit_required': True})

                send_notification_for_directory_creation.delay(community_instance.id,
                                                               TimeUtilities.current_time_in_sec(),
                                                               day=0)

            send_mail_for_first_time_edit_community_questions.delay(user_instance.id, community_instance.id)

        return {'success': True}

    def fetch_community_questions(self, req_body) -> {}:
        validated_req_body = CommunityHelper.validate_fetch_questions_request(self.get_member_id(),
                                                                              self.get_community_id(),
                                                                              req_body,
                                                                              self.get_api_key())

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req_body.get('user_instance')
        community_instance = validated_req_body.get('community_instance')
        aj = validated_req_body.get('aj')
        shared_by = validated_req_body.get('shared_by')

        community_meta_data = CommunityHelper.compute_community_meta_data_according_to_aj_shared_by(user_instance,
                                                                                                    community_instance,
                                                                                                    aj, shared_by)

        if user_instance and community_instance:
            CommunityHelper.send_drop_off_notification_in_join(user_instance, community_instance, aj)

        community_meta_data['questions'] = CommunityHelper.get_community_questions_data(user_instance,
                                                                                        community_instance,
                                                                                        self.get_request_platform(),
                                                                                        self.get_version_code(),
                                                                                        self.get_sdk_source())

        community_meta_data['success'] = True

        return community_meta_data

    def fetch_community_branding_info(self, req_body) -> {}:

        output = {}
        branding_cache_key = 'COMMUNITY_BRANDING_{}'.format(self.get_community_id())

        branding = CacheImpl.get_cache(branding_cache_key)

        if branding:
            output['branding'] = json.loads(branding)

        else:

            validated_req_body = CommunityHelper.validate_fetch_branding_info_request(self.get_member_id(),
                                                                                      self.get_community_id(),
                                                                                      req_body)

            if not validated_req_body.get('success'):
                return validated_req_body

            community_instance = validated_req_body.get('community_instance')

            output['branding'] = json.loads(community_instance.branding) if community_instance.branding else None

            CacheImpl.set_cache(branding_cache_key, community_instance.branding)

        output['success'] = True

        return output

    def fetch_community_id_from_domain(self, req_body) -> dict:
        output = {}
        whitelabel_domain_key = 'WHITELABEL_DOMAINS'

        whitelabel_domains = CacheImpl.get_cache(whitelabel_domain_key)
        domains_json = json.loads(whitelabel_domains) if whitelabel_domains else {}
        print(domains_json)

        community_id = domains_json.get(req_body.get('domain'), None)

        if community_id:
            output['community_id'] = community_id
            output['success'] = True

        else:

            community_instances = ModelUtilities.get_model_filter(
                Community, {'whitelabel_info__contains': req_body.get('domain')})

            if community_instances:
                community_instance = community_instances[0]
                CommunityHelper.set_community_data_in_cache.delay(community_instance.id)
                output['community_id'] = community_instance.id
                output['success'] = True

            else:
                output['success'] = False
                output['error_message'] = "Invalid domain"

        return output

    def update_community_dm_settings(self, req_body, api_revamp_v1_check=False) -> {}:
        validated_req_body = CommunityHelper.validate_update_community_dm_settings_request(self.get_member_id(),
                                                                                           self.get_community_id(),
                                                                                           self.get_api_key(),
                                                                                           req_body,
                                                                                           api_revamp_v1_check)

        if not validated_req_body.get('success'):
            return validated_req_body

        filter_dict = {
            'community': validated_req_body.get('community_instance')
        }

        ModelUtilities.update_or_create_model(CommunityDirectMessageSettings, filter_dict,
                                              validated_req_body.get('update_dict'))

        return {'success': True}

    def fetch_community_dm_settings(self, api_revamp_v1_check=False) -> {}:
        validated_req_body = CommunityHelper.validate_fetch_community_dm_settings_request(self.get_member_id(),
                                                                                          self.get_community_id(),
                                                                                          self.get_api_key())

        if not validated_req_body.get('success'):
            return validated_req_body

        filter_dict = {
            'community': validated_req_body.get('community_instance')
        }

        community_dm_settings_filter = ModelUtilities.get_model_filter(CommunityDirectMessageSettings, filter_dict)

        if community_dm_settings_filter:
            community_dm_setting_object = CommunityDMSettingsSerializer(community_dm_settings_filter[0]).data

            # If api_revamp_v1_check is True, then convert state from int to string
            if api_revamp_v1_check:
                community_dm_setting_object['state'] = CommunityDMSettingTypes.get_string_state_type_from_int(
                    community_dm_setting_object['state'])

            return {'success': True, 'community_dm_settings': community_dm_setting_object}

        else:
            return {'success': False, 'error_message': 'No setting found!'}

    def fetch_community_dm_right(self, req_body) -> {}:
        validated_req_body = CommunityHelper.validate_fetch_community_dm_right_request(self.get_member_id(),
                                                                                       self.get_community_id(),
                                                                                       req_body)

        if not validated_req_body.get('success'):
            return validated_req_body

        community_instance = validated_req_body.get('community_instance')
        state = validated_req_body.get('state')
        is_m2cm_v2 = m2cm_v2_version_check(self.get_request_platform(), self.get_version_code())

        right_data = CohortHelper.get_cohorts_with_specific_right(community_instance, state, is_m2cm_v2=is_m2cm_v2)

        return {'success': True, 'cohorts': right_data}

    @staticmethod
    def _update_community_object(community_instance, user_instance, req_body):

        purpose = req_body.get('purpose', community_instance.purpose)
        name = req_body.get('community_name', community_instance.name)
        image_link = req_body.get('image_url', community_instance.image_link)

        edit_fields = []

        if community_instance.name != name:
            edit_fields.append("name")

        if community_instance.purpose != purpose:
            edit_fields.append("purpose")

        if community_instance.image_link != image_link:
            edit_fields.append("image_url")

        community_instance.purpose = purpose
        community_instance.name = name
        community_instance.image_link = image_link

        community_instance.type = req_body.get('type', community_instance.type)
        community_instance.subtype = req_body.get('sub_type', community_instance.sub_type)

        community_instance.is_paid = req_body.get('is_paid', community_instance.is_paid)
        community_instance.is_discoverable = req_body.get('is_discoverable', community_instance.is_discoverable)
        community_instance.website_url = req_body.get('website_url', community_instance.website_url)
        community_instance.community_category = req_body.get('community_category',
                                                             community_instance.community_category)
        community_instance.referral_enabled = req_body.get('referral_enabled', community_instance.referral_enabled)
        community_instance.dashboard_link = req_body.get('dashboard_link', community_instance.dashboard_link)

        community_instance.branding = json.dumps(req_body.get('branding')) if req_body.get(
            'branding') else community_instance.branding

        community_instance.is_whitelabel = req_body.get('is_whitelabel', community_instance.is_whitelabel)
        community_instance.whitelabel_info = json.dumps(req_body.get('whitelabel_info')) if req_body.get(
            'whitelabel_info') else community_instance.whitelabel_info

        community_instance.fee_membership = req_body.get('fee_membership', community_instance.fee_membership)
        community_instance.fee_event = req_body.get('fee_event', community_instance.fee_event)
        community_instance.fee_payment_pages = req_body.get('fee_payment_pages', community_instance.fee_payment_pages)
        community_instance.brand_color = req_body.get('brand_color', community_instance.brand_color)
        community_instance.likeminds_plan = req_body.get('likeminds_plan', community_instance.likeminds_plan)
        community_instance.hide_dm_tab = req_body.get('hide_dm_tab', community_instance.hide_dm_tab)
        community_instance.is_freemium_community = req_body.get('is_freemium_community',
                                                                community_instance.is_freemium_community)

        community_instance.save()

        for edit_field in edit_fields:
            edit_community_data(community_instance, user_instance, edit_field=edit_field)

    def edit_community(self, req_body, username=None, password=None) -> dict:

        validated_request_body = CommunityViewHelper.validate_edit_community_request(req_body,
                                                                                     self.get_community_id(),
                                                                                     self.get_member_id(),
                                                                                     username, password)

        if 'error_message' in validated_request_body:
            return ResponseUtilities.get_impl_error_context(validated_request_body['error_message'],
                                                            status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request_body.get('community_instance')
        user_instance = validated_request_body.get('user_instance')

        self._update_community_object(community_instance, user_instance, req_body)

        CacheImpl.set_cache('COMMUNITY_BRANDING_{}'.format(community_instance.id), community_instance.branding)

        CommunityHelper.set_community_data_in_cache(community_instance.id)

        change_community_level_context_for_paid_community(community_instance)

        send_sync_notification.delay({'community_id': community_instance.id,
                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})
        update_multiple_previews_in_community.delay({'community_id': community_instance.id})

        return {'success': True}

    def add_community_member(self, req_body: dict, auto_join: bool=False) -> {}:
        validated_req_body = CommunityViewHelper.validate_add_community_member_request(self.get_member_id(),
                                                                                       self.get_api_key(),
                                                                                       req_body)

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = validated_req_body.get('user_instance')
        community_instance = validated_req_body.get('community_instance')

        req_body = {
            "user": validated_req_body.get('user_body'),
            "type": login_types.SDK
        }

        user_manager = UserImpl(user_id="", mobile_no="")
        login_user = user_manager.login(req_body, self.get_request_platform(), self.get_device_id(),
                                        self.get_version_code(), api_key=self.get_api_key())

        if login_user.get('error_message'):
            return ResponseUtilities.get_impl_error_context('Unable to login/sign-up!',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_object = login_user.get('user')

        member_community_manager = MemberCommunityImpl(user_object.get('id'),
                                                       community_id=community_instance.id,
                                                       device_id=self.get_device_id(),
                                                       platform_code=self.get_request_platform(),
                                                       version_code=self.get_version_code(),
                                                       api_version_code=self.get_api_version_code())

        community_req_body = {
            "image_url": validated_req_body['user_body'].get('image_url')
        }

        join_community_context = member_community_manager.join_community_sdk(community_req_body, auto_join=auto_join)

        if not join_community_context.get('success'):
            return ResponseUtilities.get_impl_error_context('Unable to join community!',
                                                            status_codes.HTTP_400_BAD_REQUEST)

        return {'success': True, 'user': user_object, 'community': CommunitySerializerV1(community_instance).data}

    def update_community_member(self, req_body: dict) -> {}:
        validated_req_body = CommunityViewHelper.validate_update_community_member_request(self.get_member_id(),
                                                                                          self.get_api_key(),
                                                                                          req_body)

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        member_instance = validated_req_body.get('member_instance')
        community_instance = validated_req_body.get('community_instance')
        userinfo_instance = member_instance.userinfo
        user_meta_updated = False

        if req_body.get('user_name'):
            userinfo_instance.name = req_body.get('user_name')
            userinfo_instance.save()

            update_models_for_syncing_apis(SyncTypes.MEMBERS, {'member_id': member_instance.id}, {})

            ElasticSearchSync.update_user_name.delay(member_instance.id, userinfo_instance.name)
            ElasticSearchSync.update_member_name.delay(member_instance.id, userinfo_instance.name)

            user_meta_updated = True

        if req_body.get('image_url'):
            previous_image_url = userinfo_instance.image_link
            userinfo_instance.image_link = req_body.get('image_url')
            userinfo_instance.updated_at = TimeUtilities.current_time_in_sec()
            userinfo_instance.save()

            update_preview_for_account_image_change.delay({'user_id': member_instance.id,
                                                           'image_url': req_body.get('image_url'),
                                                           'previous_image_url': previous_image_url})
            
            user_meta_updated = True

        # Delete user meta cache in kettle service
        if user_meta_updated:
            cache_key = KETTLE_CACHE_KEY_USER_META.format(community_instance.id, userinfo_instance.user_unique_id)

            InternalServiceUtilities.delete_cache_from_kettle_service.delay(
                community_id=community_instance.id, user_id=member_instance.id,
                key_patterns=[cache_key] 
            )

        return {'success': True}

    def update_community_noti_settings(self, req_body):
        
        validated_req_body = CommunityHelper.validate_update_community_noti_settings(self.get_member_id(),
                                                                                     self.get_community_id(),
                                                                                     self.get_api_key(),
                                                                                     req_body)

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        noti_setting_instance = CommunityHelper.fetch_community_noti_settings_instance(
            validated_req_body.get('community_instance'))

        serializer = CommunityNotificationSettingsSerializer(noti_setting_instance, req_body, partial=True)

        if serializer.is_valid():
            serializer.save()

            CommunityHelper.trigger_event_analytics_on_updating_community_noti_settings.delay(
                self.get_member_id(),
                self.get_community_id(),
                req_body.get('noti_state')
            )

            res = {
                'success': True,
                'community_notification_settings': serializer.data
            }

            return res

        return ResponseUtilities.get_impl_error_context(serializer.errors, status_codes.HTTP_400_BAD_REQUEST)

    def fetch_community_noti_settings(self, api_revamp_v1_check=False):
        
        validated_req_body = CommunityHelper.validate_fetch_community_noti_settings(self.get_member_id(),
                                                                                    self.get_community_id(),
                                                                                    self.get_api_key())

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        noti_setting_instance = CommunityHelper.fetch_community_noti_settings_instance(
            validated_req_body.get('community_instance'))

        response = CommunityNotificationSettingsSerializer(noti_setting_instance).data

        # If api_revamp_v1_check is True, then add notification title
        if api_revamp_v1_check:
            response['notification_title'] = ChatNotificationTypes.get_string_state_type_from_int(response.get('noti_state'))

        res = {
            'success': True,
            'community_notification_settings': response
        }

        return res

    def fetch_feed_notification_settings(self, api_revamp_v1_check=False):

        validated_req_body = CommunityHelper.validate_fetch_feed_notification_settings(self.get_member_id(),
                                                                                       self.get_api_key())

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        notification_setting_instances = CommunityHelper.fetch_feed_notification_settings_instances(
            validated_req_body.get('community_instance'))

        response = FeedNotificationSettingsSerializer(notification_setting_instances, many=True).data

        if api_revamp_v1_check:

            for notification_setting in response:
                notification_setting['notification_title'] = FeedNotifcationTypes.get_string_state_type_from_int(
                    notification_setting.get('notification_type'))

        response = {
            'success': True,
            'community_notification_settings': response
        }

        return response

    def update_feed_notification_settings(self, notification_settings):

        validated_req_body = CommunityHelper.validate_update_feed_notification_settings(self.get_member_id(),
                                                                                        self.get_api_key(),
                                                                                        notification_settings)

        if validated_req_body.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_req_body.get('error_message'),
                                                            status_codes.HTTP_400_BAD_REQUEST)

        notification_settings = validated_req_body.get('notification_settings')

        for notification_setting in notification_settings:
            filter_dict = {
                'community': notification_setting.get('community'),
                'notification_type': notification_setting.get('notification_type')
            }
            update_dict = {
                'enabled': notification_setting.get('enabled')
            }
            ModelUtilities.update_or_create_model(FeedNotificationSettings, filter_dict, update_dict)

        return {'success': True}

    def fetch_users_meta_info(self, member_ids: list) -> dict:
        validated_request = CommunityHelper.validate_fetch_users_meta_info_request(self.get_member_id(),
                                                                                   self.get_api_key(),
                                                                                   member_ids)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        member_ids = validated_request.get('member_ids')

        user_data = get_users_meta_info(community_instance.id, member_ids)

        return {'success': True, 'users': user_data}
    
    def fetch_report_Tags(self, entity_type: str) -> dict:

        validated_request = CommunityHelper.validate_fetch_report_tags_request(self.get_member_id(),
                                                                               self.get_api_key(),
                                                                               entity_type)
        
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        report_type = validated_request.get('report_type')

        # Fetch report tags with type 1 for member and type 0 for rest
        if report_type == REPORT_TYPE_MEMBER_INT:
            report_tags_instances = ModelUtilities.get_model_filter(Report_Tags, {'type': 1})

        else:
            report_tags_instances = ModelUtilities.get_model_filter(Report_Tags, {'type': 0})

        # Serialize report tags
        report_tags = ReportTagsSerializer(report_tags_instances, many=True).data

        return {'success': True, 'report_tags': report_tags}

    def push_community_report(self, req_body) -> dict:
        
        entity_id = req_body.get('entity_id')
        entity_type = req_body.get('entity_type')
        reason = req_body.get('reason')
        accused_uuid = req_body.get('accused_uuid')
        link = req_body.get('link')

        validated_request = CommunityHelper.validate_push_community_report_request(self.get_member_id(),
                                                                                   self.get_api_key(), 
                                                                                   req_body.get('community_id'),
                                                                                   req_body)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        report_type = validated_request.get('report_type')
        user_instance = validated_request.get('user_instance')
        community_instance = validated_request.get('community_instance')
        member_instance = validated_request.get('member_instance')
        has_admin_delete_right = validated_request.get('has_admin_delete_right')
        has_admin_approve_right = validated_request.get('has_admin_approve_right')
        tag_instance = validated_request.get('report_tag_instance')

        is_owner = member_instance.is_owner
        is_admin = member_instance.state == member_states.ADMIN

        reported_member_instance = None
        chatroom_instance = None
        conversation_instance = None
        feed_entity_id = None
        subject = ""
        tag_id = tag_instance.tag_id if tag_instance else None

        # If a member is reported
        if report_type == REPORT_TYPE_MEMBER_INT:

            if is_admin and has_admin_approve_right:
                return ResponseUtilities.get_impl_error_context('You have no right to report a member!',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            valid_id = ModelUtilities.get_valid_user_ids_from_uuids([entity_id], community_instance.id)

            if not valid_id:
                return ResponseUtilities.get_impl_error_context('Invalid entity_id for member reporting!',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            reported_member_instance = ModelUtilities.get_user_instance_or_none(valid_id[0])
                                                                
            subject = REPORT_MAIL_TO_TEAM_SUBJECT.format("Member")
            
        # If a chatroom is reported
        elif report_type == REPORT_TYPE_CHATROOM_INT:

            if is_admin and has_admin_delete_right:
                return ResponseUtilities.get_impl_error_context('You have no right to report a chatroom!',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, entity_id)

            if not chatroom_instance:
                return ResponseUtilities.get_impl_error_context('Invalid entity_id for chatroom reporting!',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            subject = REPORT_MAIL_TO_TEAM_SUBJECT.format("Chatroom")

        # If a conversation is reported
        elif report_type == REPORT_TYPE_CONVERSATION_INT:

            if is_admin and has_admin_delete_right:
                return ResponseUtilities.get_impl_error_context('You have no right to report a conversation!',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, entity_id)

            if not conversation_instance:
                return ResponseUtilities.get_impl_error_context('Invalid entity_id for conversation reporting!',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            subject = REPORT_MAIL_TO_TEAM_SUBJECT.format("Text")

        # If a feed entity (post,comment,reply) is reported
        elif report_type in [REPORT_TYPE_POST_INT, REPORT_TYPE_COMMENT_INT, REPORT_TYPE_REPLY_INT, 
                             REPORT_TYPE_PENDING_POST_INT]:

            feed_entity_id = entity_id

            # Get valid user id from uuid
            valid_id = ModelUtilities.get_valid_user_ids_from_uuids([accused_uuid], community_instance.id)

            if not valid_id:
                return ResponseUtilities.get_impl_error_context(f'Invalid accused_uuid for {entity_type} reporting!!',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)

            reported_member_instance = ModelUtilities.get_user_instance_or_none(valid_id[0])

            subject = REPORT_MAIL_TO_TEAM_SUBJECT.format(entity_type)

        # Create report instance
        report_instance = Report(
            type=report_type,
            tag=tag_instance,
            reason=reason,
            collabcard=chatroom_instance,
            conversation=conversation_instance,
            community=community_instance,
            reported_by=user_instance,
            user_reported=reported_member_instance,
            entity_id=feed_entity_id,
            date_epoch=TimeUtilities.current_time_in_sec()
        )

        if link:
            report_instance.type = REPORT_TYPE_LINK_INT
            report_instance.link = link

        report_instance.save()

        #  Send notification if report is for member or chatroom
        if report_type in [REPORT_TYPE_MEMBER_INT, REPORT_TYPE_CHATROOM_INT] and not is_owner:
            chatroom_id = chatroom_instance.id if chatroom_instance else None
            conversation_id = conversation_instance.id if conversation_instance else None
            reported_member_id = reported_member_instance.id if reported_member_instance else None

            send_notification_for_reports.delay(report_id=report_instance.id, community_id=community_instance.id,
                                                reported_by_user_id=user_instance.id, card_id=chatroom_id,
                                                conversation_id=conversation_id,reported_on_user_id=reported_member_id,
                                                report_type=report_type, reason=reason, tag_id=tag_id)

        # Send report mail to team if owner is reporting
        if is_owner:
            send_report_mail_to_team.delay(subject, report_instance.id)

        # Update report count for all admins in community 
        update_report_count_for_all_promoters.delay(community_id=community_instance.id)

        return {'success': True, 'report_id': report_instance.id}
    
    def close_community_reports(self, report_ids, status) -> dict:
            
            validated_request = CommunityHelper.validate_close_community_reports_request(self.get_member_id(),
                                                                                         self.get_api_key(),
                                                                                         report_ids,
                                                                                         status)
    
            if validated_request.get('error_message'):
                return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            user_instance = validated_request.get('user_instance')
            community_instance = validated_request.get('community_instance')
            report_instances = validated_request.get('report_instances')

            # If status is sent, then approve or reject under review pending posts
            if status:
                
                report_ids = [report.id for report in report_instances]

                CommunityHelper.close_under_review_pending_post_reports.delay(community_instance.id, user_instance.id,
                                                                              report_ids, status)

            else:

                # Update report instances
                report_instances.update(is_closed=True, closed_by=user_instance, closed_time=TimeUtilities.current_time_in_sec())

            # Update report count for all admins in community
            update_report_count_for_all_promoters.delay(community_id=community_instance.id)
            
            return {'success': True}
    
    def fetch_community_configurations(self, configuration_types=None) -> dict:
        validated_request = CommunityHelper.validate_fetch_community_configurations_request(self.get_member_id(),
                                                                                            self.get_community_id(),
                                                                                            self.get_api_key(),
                                                                                            configuration_types)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        community_instance = validated_request.get('community_instance')
        community_configuration_types = validated_request.get('community_configuration_types')

        # serialize community configurations
        serialised_community_configurations = CommunityHelper.fetch_or_return_default_community_configurations(
            community_instance, community_configuration_types)

        response = {
            'success': True,
            'community_configurations': serialised_community_configurations
        }

        return response

    def update_community_configurations(self, req_body: dict = None) -> dict:
        validated_request = CommunityHelper.validate_update_community_configurations_request(self.get_member_id(),
                                                                                             self.get_api_key(),
                                                                                             req_body)

        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        community_instance = validated_request.get('community_instance')
        user_instance = validated_request.get('user_instance')
        configuration_type = validated_request.get('configuration_type')
        update_values = validated_request.get('update_values')

        record_updated, configuration_instance = CommunityHelper.update_configuration_of_community(
            community_instance.id, user_instance.id, configuration_type, update_values)

        response = {
            'success': True,
            'record_updated': record_updated,
            'community_configuration': CommunityConfigurationsSerializer(configuration_instance).data
        }

        return response
    
    def remove_community_members(self, req_body: dict) -> dict:

        uuids = req_body.get('uuids')
        tag_id = req_body.get('tag_id')
        reason = req_body.get('reason')
   
        validated_request = CommunityHelper.validate_remove_community_members_request(self.get_member_id(),
                                                                                      self.get_api_key(), 
                                                                                      uuids)
    
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
     
        community_instance = validated_request.get('community_instance')
        user_instance = validated_request.get('user_instance')
        uuids = validated_request.get('uuids')

        # If uuids are more than the limit, then remove members asynchronously
        if len(uuids) > COMMUNITY_REMOVE_MEMBER_ASYNC_LIMIT:
            CommunityHelper.remove_community_members.delay(is_async=True, community_id=community_instance.id, 
                                                           current_user_id=user_instance.id, uuids=uuids, 
                                                           tag_id=tag_id, reason=reason)
            
            return {
                'success': True, 
                'message': COMMUNITY_REMOVE_MEMBER_ASYNC_MESSAGE
            }
        
        # Else remove members synchronously and return response
        else:
            response = CommunityHelper.remove_community_members(is_async=False, community_id=community_instance.id, 
                                                                current_user_id=user_instance.id, uuids=uuids, 
                                                                tag_id=tag_id, reason=reason)
            
            removal_status = response.get('removal_status')
            message = response.get('message')
            
            return {
                'success': True, 
                'removal_status': removal_status, 
                'message': message
            }
        
    def fetch_community_removal_reports(self) -> dict:
        validated_request = CommunityHelper.validate_fetch_community_removal_reports_request(self.get_member_id(),
                                                                                             self.get_api_key())
    
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        community_instance = validated_request.get('community_instance')

        # Fetch user removal reports from s3 bucket
        removal_reports = CommunityHelper.fetch_users_removal_reports_from_s3(community_instance.id)
        
        response = {
            'success': True,
            'removal_reports': removal_reports
        }

        return response
    
    def fetch_chatbots(self, page, page_size, uuids) -> dict:

        validated_request = CommunityHelper.validate_fetch_chatbots_request(self.get_member_id(),
                                                                            self.get_api_key())
        
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        user_instance = validated_request.get('user_instance')

        
        # Fetch chatbots along with related userInfo data
        chatbotMetas = ModelUtilities.get_model_filter(ChatbotMeta, {'community': community_instance,}
                                                       ).select_related('user__userinfo')

        # fetch user_ids from uuids
        user_ids = ModelUtilities.get_valid_user_ids_from_uuids(uuids, community_instance.id)
        if user_ids:
            chatbotMetas = chatbotMetas.filter(user__id__in=user_ids)

        # Get paginated data
        chatbots_page, total_pages, total_count = paginate_list(chatbotMetas, page, page_size)

        users = []

        # Prepare the response
        for chatbot in chatbots_page:
            chatbot_user = UserinfoSerializer(chatbot.user.userinfo, sdk_client_info_flag=True)
            chatbot_user['chatbot_meta'] = ChatbotMetaSerializer(chatbot).data
            users.append(chatbot_user)

        # Prepare the response
        response = {
            'success': True,
            'users': users,
            'page': page,
            'total_pages': total_pages,
            'total_chatbots': total_count,
        }

        return response
    
    def create_chatbot_user_in_community(self, community_instance, name: str, uuid: str, image_url: str, 
                                         chatbot_meta: dict):
        
        default_text = chatbot_meta.get('default_text', "")
        provider = chatbot_meta.get('provider', "")
        provider_meta = chatbot_meta.get('provider_meta', {})
        
        # Create user instance for chatbot
        add_community_member_req_body = {
            'uuid': uuid,
            'user_name': name,
            'image_url': image_url
        }

        # Add user as community member
        response = self.add_community_member(add_community_member_req_body, auto_join=True)
        if not response.get('success'):
            return response
        
        user_id = response.get('user').get('id')
        chatbot_user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)
        if not chatbot_user_instance:
            return ResponseUtilities.get_impl_error_context('Chatbot user instance not found!',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        chatbot_member_instance = Members.get_member_instance_or_none(community_instance, chatbot_user_instance)
        if not chatbot_member_instance:
            return ResponseUtilities.get_impl_error_context('Chatbot member instance not found!',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        # Update chatbot member instance as admin
        chatbot_member_instance.state = member_states.ADMIN
        chatbot_member_instance.custom_title="chatbot"
        chatbot_member_instance.save()

        # Add chatbot role to user info
        Userinfo.add_role_to_user(chatbot_user_instance, UserRoles.CHATBOT.value)

        # Create chatbotMeta instance
        chatbot_meta_instance = ChatbotMeta(
            user=chatbot_user_instance,
            community=community_instance,
            default_text=default_text,
            provider=provider,
            provider_meta=provider_meta,
        )

        chatbot_meta_instance.save()

        return chatbot_user_instance, chatbot_meta_instance
    
    def create_chatbot(self, req_body:dict = {}) -> dict:

        validated_request = CommunityHelper.validate_create_chatbot_request(self.get_member_id(), self.get_api_key(), 
                                                                            req_body)
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        community_instance = validated_request.get('community_instance')

        chatbot_meta = req_body.get('chatbot_meta', {})
        name = req_body.get('name', "").strip()
        image_url = req_body.get('image_url', "").strip()
        uuid = req_body.get('uuid', "")

        # Create chatbot user in community
        chatbot_user_instance, chatbot_meta_instance = self.create_chatbot_user_in_community(
            community_instance, name, uuid, image_url, chatbot_meta)


        # Serialise chatbot user object with chatbotMeta
        chatbot_user = UserinfoSerializer(chatbot_user_instance.userinfo, sdk_client_info_flag=True)
        chatbot_user['chatbot_meta'] = ChatbotMetaSerializer(chatbot_meta_instance).data

        return {
            'success': True,
            'user': chatbot_user
        }
    
    def update_chatbot(self, req_body:dict = {}) -> dict:

        validated_request = CommunityHelper.validate_update_chatbot_request(self.get_member_id(),self.get_api_key(),
                                                                            req_body)
        if validated_request.get('error_message'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        community_instance = validated_request.get('community_instance')
        chatbot_meta_instance = validated_request.get('chatbot_meta_instance')
        chatbot_user_instance = validated_request.get('chatbot_user_instance')

        chatbot_meta = req_body.get('chatbot_meta', {})
        name = req_body.get('name', "").strip()
        image_url = req_body.get('image_url', "").strip()

        if name:
            CommunityHelper.update_user_alias_name(chatbot_user_instance.id, community_instance.id, name, 
                                                   question_states.NAME)

        if image_url:
            from collabmates_api.member_community.member_community_impl import MemberCommunityHelper

            chatbot_member_instance = Members.get_member_instance_or_none(community_instance, chatbot_user_instance)
            if not chatbot_member_instance:
                return ResponseUtilities.get_impl_error_context('Chatbot member instance not found!',
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)
            
            MemberCommunityHelper.update_users_image_url_in_community(chatbot_member_instance, image_url)
            MemberCommunityHelper.update_user_image_in_sdk(chatbot_user_instance, image_url)

        record_updated = False
        if chatbot_meta:
            if chatbot_meta.get('default_text'):
                chatbot_meta_instance.default_text = chatbot_meta.get('default_text')
                record_updated = True

            if chatbot_meta.get('provider'):
                chatbot_meta_instance.provider = chatbot_meta.get('provider')
                record_updated = True

            if chatbot_meta.get('provider_meta'):
                if chatbot_meta.get('provider_meta').get('assistant_id'):
                    chatbot_meta_instance.provider_meta['assistant_id'] = chatbot_meta.get('provider_meta').get('assistant_id')
                    record_updated = True

                if chatbot_meta.get('provider_meta').get('thread_context'):
                    chatbot_meta_instance.provider_meta['thread_context'] = chatbot_meta.get('provider_meta').get('thread_context')
                    record_updated = True

                if chatbot_meta.get('provider_meta').get('max_prompt_tokens') is not None:
                    chatbot_meta_instance.provider_meta['max_prompt_tokens'] = chatbot_meta.get('provider_meta').get('max_prompt_tokens')
                    record_updated = True

                if chatbot_meta.get('provider_meta').get('max_completion_tokens') is not None:
                    chatbot_meta_instance.provider_meta['max_completion_tokens'] = chatbot_meta.get('provider_meta').get('max_completion_tokens')
                    record_updated = True
                    
                if chatbot_meta.get('provider_meta').get('vision_model') is not None:
                    chatbot_meta_instance.provider_meta['vision_model'] = chatbot_meta.get('provider_meta').get('vision_model')
                    record_updated = True
            
            if record_updated:
                chatbot_meta_instance.save()

        chatbot_user = UserinfoSerializer(chatbot_user_instance.userinfo, sdk_client_info_flag=True)
        chatbot_user['chatbot_meta'] = ChatbotMetaSerializer(chatbot_meta_instance).data

        return {
            'success': True,
            'user': chatbot_user
        }

    def fetch_community_integration_status(self) -> dict:
        validated_req = CommunityHelper.validate_fetch_community_integration_request(self.get_api_key())

        if 'error_message' in validated_req:
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_req.get('community_instance')
        integration_data = CommunityHelper.fetch_or_return_default_community_integration_status(community_instance)

        return {
            'success': True,
            'community_integration_data': integration_data
        }

    def update_community_integration_status(self, status_type: str, status: bool, is_internal: bool) -> dict:
        validated_req = CommunityHelper.validate_update_community_integration_request(self.get_api_key(),
                                                                                      status_type, status, is_internal)

        if 'error_message' in validated_req:
            return ResponseUtilities.get_impl_error_context(validated_req.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_req.get('community_instance')

        # Update the community integration status
        filter_dict = {
            "community": community_instance,
            "status_type": status_type
        }
        community_integration_instance = ModelUtilities.get_model_filter(CommunityIntegrationStatus,
                                                                         filter_dict).first()

        if not community_integration_instance:
            ModelUtilities.update_or_create_model(CommunityIntegrationStatus, filter_dict, {"status": status})

        elif community_integration_instance.status != status:
            community_integration_instance.status = status
            community_integration_instance.save()

        return {
            'success': True
        }


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
    def run_async_for_community_approve(community_instance, user_instance, promoter_userinfo_instance,
                                        is_m2cm_v2=False, is_sdk=False):
        CommunityHelper.set_moderation_rights_and_delete_user_previous_metadata.delay(
            user_instance.id, community_instance.id, promoter_userinfo_instance.user_id_id, is_sdk)

        CommunityHelper.send_sms_to_the_approved_member_of_community.delay(user_instance.id, community_instance.id)
        send_notification_for_join_requests.delay(community_instance.id, True, user_instance.id,
                                                  promoter_userinfo_instance.name)
        send_community_confirmation_email.delay(user_instance.id, community_instance.id)
        MixpanelEvents.member_approved_by_cm.delay(user_instance.id, promoter_userinfo_instance.user_id_id,
                                                   community_instance.id)

        ElasticSearchSync.update_member.delay(user_instance.id, community_instance.id)

        # Create DM chatrooms
        create_member_dm_chatroom.delay(user_instance.id, community_instance.id, is_joining=True, is_m2cm_v2=is_m2cm_v2)

    @staticmethod
    def run_async_task_for_community_declined(community_instance, user_instance, promoter_userinfo_instance):
        send_notification_for_join_requests.delay(community_instance.id, False,
                                                  user_instance.id, promoter_userinfo_instance.name)
        MixpanelEvents.member_rejected_by_cm.delay(user_instance.id, promoter_userinfo_instance.user_id_id,
                                                   community_instance.id)

    @staticmethod
    @shared_task
    def set_moderation_rights_and_delete_user_previous_metadata(user_id, community_id, promoter_id, is_sdk=False):

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

        if is_rejoined and not is_sdk:
            history_type = moderation_history_types.REJOINED_COMMUNITY_PUBLIC_LINK

        elif is_rejoined and is_sdk:
            history_type = moderation_history_types.SDK_REJOINED_MEMBER

        if is_rejoined:
            CommunityHelper.update_followed_chatrooms_for_rejoined_member(user_instance, community_instance)

        moderationHistory.create_instance({'user_instance': user_instance, 'community_instance': community_instance,
                                           'moderation_by': promoter_instance, 'type': history_type})

    @staticmethod
    @shared_task
    def set_moderation_rights_and_delete_user_previous_metadata_for_auto_join(user_id, community_id, shared_id,
                                                                              auto_join_code,
                                                                              api_type=api_types.Non_SDK):

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

        is_sdk = api_type == api_types.SDK

        if is_sdk:
            history_type = moderation_history_types.SDK_JOIN

        is_rejoined = ModelUtilities.is_model_filter_exists(removedMembers, {'member': user_instance,
                                                                             'community': community_instance})

        ModelUtilities.delete_record_in_model(communityToast, {'community': community_instance,
                                                               'user': user_instance})
        ModelUtilities.delete_record_in_model(removedMembers, {'community': community_instance,
                                                               'member': user_instance})

        if is_rejoined:
            history_type = moderation_history_types.REJOINED_COMMUNITY_PRIVATE_LINK

            if is_sdk:
                history_type = moderation_history_types.SDK_REJOINED_MEMBER

            CommunityHelper.update_followed_chatrooms_for_rejoined_member(user_instance, community_instance)

        moderationHistory.create_instance({'user_instance': user_instance, 'community_instance': community_instance,
                                           'moderation_by': shared_by_user, 'type': history_type})

    @staticmethod
    def update_followed_chatrooms_for_rejoined_member(user_instance, community_instance):

        followed_filter = collabcardState.objects \
            .filter(user=user_instance, community=community_instance, follow_status=True) \
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
    def set_follow_status_for_announcement_chatroom_for_community(community_instance, user_instance, trigger_webhook=False):

        card_filter = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                   'type': card_types.CARD_PURPOSE})
        if card_filter:
            card_instance = card_filter[0]

            ChatroomHelper.auto_follow_chatroom(card_instance, user_instance, community_instance, status=True,
                                                member_state=member_states.MEMBER, trigger_webhook=trigger_webhook)

    @staticmethod
    def create_introduction_text_for_intro_chatroom(community_instance, user_instance, question_list=None,
                                                    is_directory_questions_v2=False):

        introduction_answer = ""

        question_id_key = DEFAULT_QUESTION_ID_KEY
        answer_key = DEFAULT_ANSWER_KEY

        if is_directory_questions_v2:
            question_id_key = DIRECTORY_QUESTIONS_V2_QUESTION_ID_KEY
            answer_key = DIRECTORY_QUESTIONS_V2_ANSWER_KEY

        if question_list is not None:

            for question in question_list:

                if not question.get(answer_key):
                    continue

                question_instance = ModelUtilities.get_model_instance_or_none(communityQuestions,
                                                                              question.get(question_id_key))

                if not question_instance:
                    continue

                if question_instance.question_state == question_states.INTRODUCTION:
                    introduction_answer = question.get(answer_key)

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
    def pre_compute_question_instances_for_saving_responses(community_instance, question_list, question_id_key):

        question_id_list = [question[question_id_key] for question in question_list if question.get(question_id_key)]
        question_instances = ModelUtilities.get_model_filter(communityQuestions, {'id__in': question_id_list,
                                                                                  'community': community_instance})
        question_instance_dict = {}

        for data in question_instances:
            question_instance_dict[data.id] = data

        return question_instance_dict

    @staticmethod
    def pre_compute_answer_instances_of_member(user_instance, community_instance, question_list, question_id_key):

        question_id_list = [question[question_id_key] for question in question_list if question.get(question_id_key)]
        answer_instances = ModelUtilities.get_model_filter(communityAnswers, {'question__in': question_id_list,
                                                                              'member': user_instance,
                                                                              'community': community_instance})
        answer_instance_dict = {}

        for data in answer_instances:
            answer_instance_dict[data.question_id] = data

        return answer_instance_dict

    @staticmethod
    def is_dropdown_option_present(option, dropdown_list):

        for data in dropdown_list:
            if data.lower() == option.lower():
                return True
        return False

    @staticmethod
    def save_user_selected_options_for_member_directory_filter(question_instance, value, user_instance,
                                                               community_instance):

        if (question_instance.question_state == question_states.CHOICE_SINGLE
                or question_instance.question_state == question_states.CHOICE_MULTIPLE):
            selected_choices = value.split("$#")

            dropdown_list = decode_option(question_instance.value)

            for choice in selected_choices:
                option = choice.strip()

                if question_instance.can_add_options and not CommunityHelper.is_dropdown_option_present(option,
                                                                                                        dropdown_list):
                    new_answer_instance = NewAnswer()
                    new_answer_instance.option = option
                    new_answer_instance.question = question_instance
                    new_answer_instance.user = user_instance
                    new_answer_instance.community = community_instance
                    new_answer_instance.save()

                    if not question_instance.options_only_for_self:
                        dropdown_list.append(option)

                if not question_instance.options_only_for_self:  
                    questionFilters.create_instance({'question_instance': question_instance,
                                                    'option': option,
                                                    'user_instance': user_instance,
                                                    'community_instance': community_instance})

            if not question_instance.options_only_for_self:

                result = [{'value': value} for value in dropdown_list]
                json_dump = json.dumps(result)
                question_instance.value = json_dump
                question_instance.save()

    @staticmethod
    def save_profile_links_for_social_handles(question_instance, community_answer_id):
        answer_instance = ModelUtilities.get_model_instance_or_none(communityAnswers, community_answer_id)

        if not answer_instance:
            return

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
    def update_hidden_fields_in_member_responses(user_instance, community_instance, is_directory_questions_v2=False):

        question_filter = ModelUtilities.get_model_filter(communityQuestions, {
            'community': community_instance,
            'is_hidden': True,
            'question_state': question_states.MOBILE_NO
        })

        if question_filter:
            question_instance = question_filter[0]
            mobile_filter = get_user_phone(user_instance.id)

            answer_instance = ModelUtilities.get_model_filter(communityAnswers, {'member': user_instance,
                                                                                 'question': question_instance}).first()

            if mobile_filter:
                mobile_no = "+{} {}".format(str(mobile_filter.get('country_code')), str(mobile_filter.get('mobile_no')))
                CommunityHelper.create_or_update_answer_instance(user_instance, community_instance,
                                                                 question_instance, mobile_no,
                                                                 question_title=question_instance.question_title,
                                                                 answer_instance=answer_instance)

        question_filter = ModelUtilities.get_model_filter(communityQuestions, {
            'community': community_instance,
            'is_hidden': True,
            'question_state': question_states.PARAGRAPH
        })

        if question_filter:
            question_instance = question_filter[0]

            answer_instance = ModelUtilities.get_model_filter(communityAnswers, {'member': user_instance,
                                                                                 'question': question_instance}).first()

            CommunityHelper.create_or_update_answer_instance(user_instance, community_instance,
                                                             question_instance, user_instance.userinfo.name,
                                                             question_title=question_instance.question_title,
                                                             answer_instance=answer_instance)

    @staticmethod
    def send_questions_data_on_airtable(user_instance, community_instance, question_data):
        email = get_user_email_preferred_verified(user_instance.id)
        phone_dict = get_user_phone(user_instance.id)
        phone = '+{}{}'.format(phone_dict.get('country_code'), phone_dict.get('mobile_no')) if phone_dict else ''

        airtable_data = {
            'user_id': user_instance.id,
            'community_id': community_instance.id,
            'user_name': user_instance.userinfo.name,
            'user_email': email,
            'phone_number': phone,
            'question_list': question_data
        }

        airtable_manager = AirtableWrapper(endpoint_type=airtable_webhook_types.JOIN_COMMUNITY)
        airtable_manager.send_data(airtable_data)

    @staticmethod
    def create_or_update_answer_instance(user_instance, community_instance, question_instance, answer,
                                         question_title=None, answer_instance: communityAnswers = None):

        community_answer_id = 0 if not answer_instance else answer_instance.id

        data = {
            'question_answer': answer
        }

        if not answer_instance:
            data.update({
                'community': community_instance.id,
                'member': user_instance.id,
                'question': question_instance.id,
                'question_title': question_title
            })

            serializer_params = {
                'data': data
            }

        else:
            serializer_params = {
                'instance': answer_instance,
                'data': data,
                'partial': True
            }

        answer_serializer = CommunityAnswersSerializer(**serializer_params)

        if answer_serializer.is_valid():
            answer_serializer.save()
            community_answer_id = answer_serializer.data.get('id')

        return community_answer_id

    @staticmethod
    def update_user_alias_name(user_id, community_id, user_name, question_state):

        if question_state != question_states.NAME:
            return

        ModelUtilities.model_update(Userinfo,
                                    {
                                        'user_id': user_id
                                    },
                                    {
                                        'name': user_name
                                    })

        ModelUtilities.model_update(Members,
                                    {
                                        'member_id': user_id,
                                        'community_id': community_id
                                    },
                                    {
                                        'updated_at': TimeUtilities.current_time_in_sec()
                                    })

        ElasticSearchSync.update_user_name.delay(user_id, user_name)
        ElasticSearchSync.update_member_name.delay(user_id, user_name)

    @staticmethod
    def validate_number_of_options_for_dropdown_selection(question_instance, value):

        if not question_instance.dropdown_selection_limit:
            return True

        if (question_instance.question_state == question_states.CHOICE_SINGLE
                or question_instance.question_state == question_states.CHOICE_MULTIPLE):
            selected_choices = value.split("$#")

            if len(selected_choices) > question_instance.dropdown_selection_limit:
                return False

        return True

    @staticmethod
    @shared_task
    def save_responses_of_member_in_community(user_id, community_id, question_list, is_directory_questions_v2=False):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not (question_list and user_instance and community_instance):
            return

        question_id_key = DEFAULT_QUESTION_ID_KEY
        answer_key = DEFAULT_ANSWER_KEY

        if is_directory_questions_v2:
            question_id_key = DIRECTORY_QUESTIONS_V2_QUESTION_ID_KEY
            answer_key = DIRECTORY_QUESTIONS_V2_ANSWER_KEY

        question_instance_dict = CommunityHelper.pre_compute_question_instances_for_saving_responses(community_instance,
                                                                                                     question_list,
                                                                                                     question_id_key)

        answer_instance_dict = CommunityHelper.pre_compute_answer_instances_of_member(user_instance,
                                                                                      community_instance,
                                                                                      question_list,
                                                                                      question_id_key)

        airtable_data = {}

        for question in question_list:

            if question.get(answer_key) is None:
                continue

            question_id = NumberUtilities.get_integer_from_string(question.get(question_id_key))
            question_instance = question_instance_dict.get(question_id)
            answer_instance = answer_instance_dict.get(question_id)

            if not question_instance:
                continue

            if question_instance.is_hidden:
                continue

            if answer_instance and not question_instance.is_answer_editable:
                continue

            if not CommunityHelper.validate_number_of_options_for_dropdown_selection(question_instance,
                                                                                     question.get(answer_key)):
                continue

            if answer_instance:
                ModelUtilities.delete_record_in_model(questionFilters, {'member': user_instance,
                                                                        'community': community_instance,
                                                                        'question': question_instance})
            
            # If answer is empty, delete the answer instance
            if answer_instance and question.get(answer_key) == "":
                answer_instance.delete()
                continue

            question_title = question.get('question_title') if question.get('question_title') else \
                question_instance.question_title

            community_answer_id = CommunityHelper.create_or_update_answer_instance(user_instance, community_instance,
                                                                                   question_instance,
                                                                                   question.get(answer_key),
                                                                                   question_title=question_title,
                                                                                   answer_instance=answer_instance)

            CommunityHelper.save_user_selected_options_for_member_directory_filter(question_instance,
                                                                                   question.get(answer_key),
                                                                                   user_instance,
                                                                                   community_instance)
            CommunityHelper.save_profile_links_for_social_handles(question_instance, community_answer_id)

            CommunityHelper.update_user_alias_name(user_instance.id, community_instance.id, question.get(answer_key),
                                                   question_instance.question_state)

            airtable_data[question_instance.id] = question.get(answer_key)

        CommunityHelper.update_hidden_fields_in_member_responses(user_instance, community_instance,
                                                                 is_directory_questions_v2=is_directory_questions_v2)

        CommunityHelper.send_questions_data_on_airtable(user_instance, community_instance, airtable_data)

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

        auto_approval = community_setting_instance[0].enabled if len(
            community_setting_instance) else community_instance.auto_approval

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
    def fetch_community_for_aj(aj, platform_code, version_code):
        res = {
            'success': False
        }

        is_aj_present = ModelUtilities.get_model_filter(communityExpiryCodes, {'unique_code': aj})

        if is_aj_present:
            aj_instance = is_aj_present[0]
            is_cm_onboarding_enabled = cm_onboarding_version_check(platform_code, version_code)

            if is_cm_onboarding_enabled and aj_instance.community.is_paid and aj_instance.user:
                res['error_message'] = 'Invite code already used!'
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

        api_type = req_body.get('type', api_types.Non_SDK)

        if not req_body.get('name'):
            return {'success': False, 'error_message': 'Empty name!'}

        if api_type == api_types.Non_SDK:

            if ('headline' not in req_body) or (not req_body.get('headline')):
                return {'success': False, 'error_message': 'Empty headline!'}

            if 'branding' not in req_body and 'brand_color' not in req_body:
                return {'success': False, 'error_message': 'Empty brand color!'}

            if ('image_url' not in req_body) or (not req_body.get('headline')):
                return {'success': False, 'error_message': 'Empty image url!'}

        return req_body

    @staticmethod
    def get_list_from_comma_string(comma_seperated_string):

        comma_seperated_string = comma_seperated_string.split(',')
        comma_seperated_string = [i.strip() if isinstance(i, str) else i for i in comma_seperated_string]

        return comma_seperated_string

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

        template_name = WHATSAPP_COMMUNITY_CREATED_TEMPLATE_FOR_CM_NAME

        updated_user_data = TasksHelper.update_wa_subscription_user_data(receivers_list, template_name)

        for user_data in updated_user_data:
            NotificationImpl.send_bulk_wa_notification.delay(user_data["user_data_list"],
                                                             user_data["template_name"],
                                                             user_data["broadcast_name"])

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
    @shared_task
    def set_community_data_in_cache(community_id):
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return

        whitelabel_cache_key = 'WHITELABEL_COMMUNITY_{}'.format(community_instance.id)
        domains_cache_key = 'WHITELABEL_DOMAINS'

        whitelabel_cache_value = community_instance.whitelabel_info
        whitelabel_json = json.loads(whitelabel_cache_value) if whitelabel_cache_value else None

        CacheImpl.delete_key(whitelabel_cache_key)
        CacheImpl.set_cache(whitelabel_cache_key, whitelabel_cache_value)

        if whitelabel_json and 'website' in whitelabel_json:
            domains_cache_value = CacheImpl.get_cache(domains_cache_key)
            domains_json = json.loads(domains_cache_value) if domains_cache_value else {}
            updated_domains_json = {**domains_json}

            for domain, community_id in domains_json.items():
                if community_id == community_instance.id:
                    del updated_domains_json[domain]

            updated_domains_json[whitelabel_json['website']] = community_instance.id
            domains_cache_value = json.dumps(updated_domains_json)

            CacheImpl.delete_key(domains_cache_key)
            CacheImpl.set_cache(domains_cache_key, domains_cache_value)

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

        mail_categories = MailHelper.get_email_category_list_using_category_subcategory(
            EmailCategories.CREATE_COMMUNITY, EmailSubCategories.GETTING_STARTED)

        mail_body = {
            'subject': mail_subject,
            'mail_body': mail_template,
            'mail_recipient_list': [user_instance.userinfo.email],
            'reply_to': [INVITE_MEMBER_REPLY_EMAIL],
            'mail_categories': mail_categories
        }

        return mail_body

    @staticmethod
    def give_owner_all_member_manager_rights(user_instance, community_instance):
        give_all_manager_rights(user=user_instance, community=community_instance)
        give_all_member_rights(user=user_instance, community=community_instance)

    @staticmethod
    def send_community_creation_email_to_team(member_instance, community_instance, project_creator_instance=None):
        # send community created mail to the team
        email_context = {
            'member_name': member_instance.member_id.userinfo.name,
            'community_name': community_instance.name,
            'member_email': member_instance.member_id.userinfo.email,
            'community_id': community_instance.id
        }

        if project_creator_instance:
            email_context['member_name'] = project_creator_instance.userinfo.name
            project_creator_email_instance = ModelUtilities.get_model_filter(userEmails,
                                                                             {'user': project_creator_instance,
                                                                              'email_state': email_states.PRIMARY}).first()
            if project_creator_email_instance:
                email_context['member_email'] = project_creator_email_instance.email

            else:
                email_context['member_email'] = project_creator_instance.userinfo.email

            project_creator_mobile_instance = ModelUtilities.get_model_filter(userMobiles, {
                'user': project_creator_instance,
            }).first()

            if project_creator_mobile_instance:
                email_context['member_mobile'] =  "+" + str(project_creator_mobile_instance.country_code) + " " + str(project_creator_mobile_instance.mobile_no)


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
    def validate_send_invite_request(member_id, req_body, api_key: str = None):
        if 'type' not in req_body:
            return ResponseUtilities.get_inner_error_context('Send type!')

        if not (api_key or 'community_id' in req_body):
            return ResponseUtilities.get_inner_error_context('Send API key/community ID!')

        if req_body.get('type') not in [send_invite_types.EMAIL_INVITE, send_invite_types.WHATSAPP_INVITE]:
            return ResponseUtilities.get_inner_error_context('Invalid type!')

        if (req_body.get('type') == send_invite_types.EMAIL_INVITE) and ('email_id' not in req_body):
            return ResponseUtilities.get_inner_error_context('Send email ID!')

        if (req_body.get('type') == send_invite_types.WHATSAPP_INVITE) and ('mobile_no' not in req_body):
            return ResponseUtilities.get_inner_error_context('Send mobile no!')

        if 'text' not in req_body:
            return ResponseUtilities.get_inner_error_context('Send text!')

        if 'link_type' not in req_body:
            return ResponseUtilities.get_inner_error_context('Send link type!')

        validation_params = {
            'community_id': {
                'community_id': req_body.get('community_id'),
                'api_key': api_key
            },
            'user_id': member_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')

        members_filter = ModelUtilities.get_model_filter(Members,
                                                         {'member_id': user_instance,
                                                          'community_id': community_instance})

        if not members_filter:
            return ResponseUtilities.get_inner_error_context('You are not part of the community.')

        is_admin = members_filter[0].state == member_states.ADMIN

        if not is_admin:
            return ResponseUtilities.get_inner_error_context('You are not the CM of this community!')

        return {
            'community_instance': community_instance,
            'user_instance': user_instance
        }

    @staticmethod
    def send_invite_email_to_given_emails_list(user_instance, community_instance, valid_email_ids_list,
                                               validated_req_body, platform_code, version_code, mail_body):

        is_free_plan = validated_req_body.get('link_type') == FREE_PLAN

        hidden_text = 'flex' if is_free_plan else 'none'

        community_share_link = CommunityHelper.generate_community_share_link(user_instance, community_instance,
                                                                             platform_code, version_code,
                                                                             validated_req_body.get('link_type'))

        email_sender_data = CommunityEmailConfiguration.get_email_sender_data_for_community(community_instance.id)

        sender_name = email_sender_data.get('name') if email_sender_data.get('name') \
            else SENDER_NAME_FOR_EMAIL_COMMS

        sender_email = email_sender_data.get('from_email') if email_sender_data.get('from_email') \
            else SENDER_EMAIL_FOR_EMAIL_COMMS

        reply_to_email = email_sender_data.get('reply_email') if email_sender_data.get('reply_email') \
            else INVITE_MEMBER_REPLY_EMAIL

        for valid_email_id in valid_email_ids_list:

            if community_instance.is_paid and is_free_plan:
                community_share_link = CommunityHelper.generate_community_share_link(user_instance, community_instance,
                                                                                     platform_code, version_code,
                                                                                     validated_req_body.get('link_type'))

            if not community_share_link.get('success'):
                continue

            changed_mail_body = "<br>".join(mail_body.split("\n"))

            mail_template = get_template('mails/cm_onboarding/invite_members_cm_onboarding.html').render({
                "community_logo": community_instance.image_link,
                "community_name": community_instance.name,
                "cm_name": user_instance.userinfo.name,
                "mail_text": changed_mail_body,
                "community_brand_color": community_instance.brand_color if community_instance.brand_color else
                DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR,
                "join_code": community_share_link.get('aj'),
                "button_text": INVITE_MEMBERS_BUTTON_TEXT,
                "button_link": community_share_link.get('link'),
                "is_hidden": hidden_text
            })

            mail_subject = INVITE_MEMBERS_SUBJECT.format(community_instance.name)
            mail_categories = MailHelper.get_email_category_list_using_category_subcategory(
                EmailCategories.INVITE_MEMBER, EmailSubCategories.WITH_JOIN_CODE)

            MailWrapper.send_email_with_custom_from_email.delay(
                subject=mail_subject, template=mail_template, to_mails_list=[valid_email_id],
                from_email=sender_email, categories=mail_categories, reply_to=reply_to_email,
                from_name=sender_name)

    @staticmethod
    def send_invite_whatsapp_context_dict(user_instance, community_instance, mobile_nos_list, validated_req_body,
                                          platform_code, version_code):
        receivers_list = []
        community_share_link_dict = CommunityHelper.generate_community_share_link(user_instance, community_instance,
                                                                                  platform_code, version_code,
                                                                                  validated_req_body.get('link_type'))

        for mobile_no in mobile_nos_list:

            if community_instance.is_paid and (validated_req_body.get('link_type') == FREE_PLAN):
                community_share_link_dict = CommunityHelper.generate_community_share_link(user_instance,
                                                                                          community_instance,
                                                                                          platform_code, version_code,
                                                                                          validated_req_body.get('link_type'))

            if not community_share_link_dict.get('success'):
                continue

            link_path = UrlUtilities.extract_part_from_url(community_share_link_dict.get('link'), 'path',
                                                           init_slash_off=True)

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
                    "value": community_share_link_dict.get("aj")
                })

            receivers_list.append(receiver_info)

        return receivers_list

    @staticmethod
    def create_introduction_question_in_community_v2(community_instance, is_sdk=False):
        '''function to create introduction question in community and mobile information'''

        if ModelUtilities.is_model_filter_exists(communityQuestions,
                                                 {'community': community_instance}):
            return

        question_data_list = [
            {
                'community': community_instance.id,
                'question_title': CREATE_COMMUNITY_QUESTION_INTRODUCTION_TITLE,
                'question_state': question_states.INTRODUCTION,
                'value': json.dumps(CREATE_COMMUNITY_QUESTION_INTRODUCTION_VALUE),
                'optional': True if is_sdk else False,
                'help_text': None,
                'is_hidden': False,
                'is_compulsory': False,
                'field': False,
                'can_add_options': False
            },
            {
                'community': community_instance.id,
                'question_title': CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_TITLE,
                'question_state': question_states.MOBILE_NO,
                'value': json.dumps(CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_VALUE),
                'optional': False,
                'help_text': CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_HELP_TEXT,
                'is_hidden': True,
                'is_compulsory': True,
                'field': True,
                'can_add_options': False,
            }
        ]

        if is_sdk:
            question_data_list.append({
                'community': community_instance.id,
                'question_title': CREATE_COMMUNITY_QUESTION_ALIAS_TITLE,
                'question_state': question_states.NAME,
                'value': None,
                'optional': False,
                'help_text': CREATE_COMMUNITY_QUESTION_NAME_HELP_TEXT,
                'is_hidden': False,
                'is_compulsory': False,
                'field': False,
                'can_add_options': False,
                'rank': 1
            })

        else:
            question_data_list.append({
                'community': community_instance.id,
                'question_title': CREATE_COMMUNITY_QUESTION_EMAIL_TITLE,
                'question_state': question_states.EMAIL_ID,
                'value': json.dumps(CREATE_COMMUNITY_QUESTION_EMAIL_VALUE),
                'optional': True if is_sdk else False,
                'help_text': CREATE_COMMUNITY_QUESTION_EMAIL_HELP_TEXT,
                'is_hidden': False,
                'is_compulsory': True,
                'field': True,
                'can_add_options': False
            })

        community_question_serializer = CommunityQuestionsSerializerV2(data=question_data_list, many=True)

        if community_question_serializer.is_valid():
            community_question_serializer.save()

        else:
            error_logger.error(
                'CREATE INTRODUCTION QUESTION, Not valid: ' + str(community_question_serializer.errors))

    @staticmethod
    @shared_task
    def create_community_async_tasks(user_id, community_id, req_body):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return

        api_type = req_body.get('type', api_types.Non_SDK)

        # Add branding key to cache
        CacheImpl.set_cache('COMMUNITY_BRANDING_{}'.format(community_id), community_instance.branding)

        # Set community levels
        set_community_actions(community_instance)

        member_filter = ModelUtilities.get_model_filter(Members,
                                                        {'community_id': community_instance,
                                                         'member_id': user_instance})

        if not member_filter:
            return

        member_instance = member_filter[0]

        # making the member engage instance for created community
        ModelUtilities.update_or_create_model(Member_Engage, {
            'member_id': user_instance,
            'community_id': community_instance
        }, {
            'member_state': member_states.ADMIN,
            'click_state': click_states.SET_PURPOSE,
            'member_referral': 'Finish setting up your community',
            'rights_list': json.dumps(member_rights.ALL_MEMBER_RIGHTS),
            'order_time': TimeUtilities.current_time_in_milliseconds()
        })

        # give all the CM and member rights to the community creator i.e owner
        CommunityHelper.give_owner_all_member_manager_rights(user_instance, community_instance)

        # give all community setting rights
        give_all_community_setting_rights(community=community_instance)

        CommunityHelper.update_feed_notification_settings_based_on_feed_setting(community_id=community_id, 
                                                                                is_enabled=True)

        save_moderation_history(user=user_instance, community=community_instance,
                                moderation_by=user_instance,
                                type=moderation_history_types.STARTED_COMMUNITY)

        project_creator_instance = None

        if req_body.get('project_creator'):
            project_creator_instance = ModelUtilities.get_user_instance_or_none(req_body.get('project_creator'))

        # send community created mail to the team
        CommunityHelper.send_community_creation_email_to_team(member_instance, community_instance,
                                                              project_creator_instance=project_creator_instance)

        # Create Content Download Settings
        CommunityHelper.create_content_download_settings_for_community(community_instance)

        add_community_settings_for_community(community_instance, user_instance)

        CommunityHelper.create_introduction_question_in_community_v2(community_instance,
                                                                     is_sdk=api_type == api_types.SDK)

        post_purpose_collabcard_for_community(req_body, community_instance, user_instance.id)

        if api_type != api_types.SDK:
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

        pin_chatroom_cache = {
            'community_id': community_instance.id
        }

        update_community_pin_chatrooms_list_in_cache.delay(pin_chatroom_cache)
        
        # Set Community Billing date for MAU
        CommunityHelper.create_community_billing_date_for_mau_tracking(community_instance.id)

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
    
    @staticmethod
    def validate_edit_question_request(member_id, community_id, api_key, req_body):
        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not user_instance:
            return get_error_context(False, 'Invalid member_id')

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return get_error_context(False, 'Invalid community_id')

        member_filter = ModelUtilities.get_model_filter(Members, {'member_id': user_instance,
                                                                  'community_id': community_instance})

        if not member_filter:
            return get_error_context(False, 'Member not part of community')

        member_instance = member_filter[0]

        if not member_instance.state == member_states.ADMIN:
            return get_error_context(False, 'You are not CM of community!')

        questions_list = req_body.get('questions')

        if not (questions_list and isinstance(questions_list, list)):
            return get_error_context(False, 'Send questions structure in list')

        return {'success': True, 'user_instance': user_instance, 'community_instance': community_instance,
                'questions_list': questions_list, 'member_instance': member_instance}

    @staticmethod
    def create_community_questions_question_dict(question_data, community_instance):

        if question_data.get('state'):
            question_data['question_state'] = question_data.get('state')

        if not question_data.get('community'):
            question_data['community'] = community_instance.id

        return question_data

    @staticmethod
    @shared_task
    def add_create_edit_question_analytics(question_id, user_id, question_state, questions_metadata={}):

        if not question_state == question_change_states.DELETE_QUESTION:
            question_instance = ModelUtilities.get_model_instance_or_none(communityQuestions, question_id)

            if not question_instance:
                return

            questions_metadata = {
                "community_id": question_instance.community.id,
                "community_name": question_instance.community.name,
                "questions_type": question_instance.question_state
            }

        event_name = DIRECTORY_QUESTIONS_CREATE_EVENT_NAME

        if question_state == question_change_states.EDIT_QUESTION:
            event_name = DIRECTORY_QUESTIONS_EDIT_EVENT_NAME

        elif question_state == question_change_states.DELETE_QUESTION:
            event_name = DIRECTORY_QUESTIONS_DELETE_EVENT_NAME

        if question_state in [question_change_states.NEW_QUESTION, question_change_states.EDIT_QUESTION]:
            question_value = json.loads(question_instance.value) if question_instance.value else None
            other_options_list = []
            private = False
            mandatory = False
            added_helptext = False

            if question_value:

                for value_dict in question_value:

                    if isinstance(value_dict, dict) and value_dict.get(ANSWER_PRIVACY_KEY) and \
                            (value_dict.get(ANSWER_PRIVACY_KEY) == ANSWER_PRIVACY_PRIVATE_VALUE):
                        private = True
                        break

            if not question_instance.optional:
                mandatory = True

            if question_instance.help_text:
                added_helptext = True

            other_options_list.append({"private": private,
                                       "public": not private,
                                       "mandatory": mandatory,
                                       "added_helptext": added_helptext})

            questions_metadata["other_options"] = other_options_list

        SegmentImpl.track_event(user_id, event_name, questions_metadata)

    @staticmethod
    def create_new_community_questions(community_instance, questions_list, user_id):

        for question_data in questions_list:
            question_data = CommunityHelper.create_community_questions_question_dict(question_data, community_instance)
            community_question_instance = CommunityQuestionsSerializerV2(data=question_data)

            if community_question_instance.is_valid():
                community_question_instance.save()

                CommunityHelper.add_create_edit_question_analytics.delay(
                    community_question_instance.data.get('id'), user_id,
                    question_state=question_change_states.NEW_QUESTION)

            else:
                error_logger.error("CREATE NEW QUESTION, Not valid: " + str(community_question_instance.errors))

    @staticmethod
    def update_user_answers_and_filter_in_multi_choice_questions(question_instance, question_data):
        current_choices = json.loads(question_data.get('value')) if question_data.get('value') else []
        value_list = []

        for i in current_choices:
            value_list.append(i['value'])

        filter_list = list(questionFilters.objects.filter(question=question_instance).
                           values_list('filter', flat=True).distinct())

        user_ids_with_data = []

        for data in filter_list:

            if data not in value_list:
                user_ids_with_data += list(ModelUtilities.get_model_filter(
                    questionFilters, {'question': question_instance, 'filter': data})
                                           .values_list('member_id', flat=True).distinct())

                ModelUtilities.get_model_filter(
                    questionFilters, {'question': question_instance, 'filter': data}).delete()

        if user_ids_with_data:

            for user_id in user_ids_with_data:
                dropdown_option = list(ModelUtilities.get_model_filter(
                    questionFilters, {'question': question_instance, 'member_id': user_id})
                                       .values_list('filter', flat=True).distinct())

                answer_filter = ModelUtilities.get_model_filter(communityAnswers,
                                                                {'question': question_instance,
                                                                 'member_id': user_id})

                if dropdown_option:
                    value = "$#".join(dropdown_option)
                    answer_filter.update(question_answer=value)

                else:
                    info_logger.info("delete case")
                    answer_filter.delete()

    @staticmethod
    def update_community_questions(community_instance, questions_list, user_id):
        new_question_list = []

        for question_data in questions_list:
            question_data = CommunityHelper.create_community_questions_question_dict(question_data, community_instance)
            question_id = question_data.get('id') if question_data.get('id') else 0
            question_instance = ModelUtilities.get_model_instance_or_none(communityQuestions, question_id)

            if not question_instance:
                new_question_list.append(question_data)
                continue

            if question_instance.question_state == question_states.CHOICE_MULTIPLE or \
                    question_instance.question_state == question_states.CHOICE_SINGLE:
                CommunityHelper.update_user_answers_and_filter_in_multi_choice_questions(question_instance,
                                                                                         question_data)

            community_question_serializer = CommunityQuestionsSerializerV2(question_instance, data=question_data,
                                                                           partial=True)

            if community_question_serializer.is_valid():
                community_question_serializer.save()

                CommunityHelper.add_create_edit_question_analytics.delay(
                    question_instance.id, user_id, question_state=question_change_states.EDIT_QUESTION)
                
                # Delete user meta cache for users with this question
                CommunityHelper.delete_user_meta_cache_for_users_with_question(question_instance.id, 
                                                                               community_instance.id)

            else:
                error_logger.error("UPDATE COMMUNITY QUESTIONS, Not valid: " + str(
                    community_question_serializer.errors))

        if new_question_list:
            CommunityHelper.create_new_community_questions(community_instance, new_question_list, user_id=user_id)

    @staticmethod
    def delete_community_questions(community_instance, questions_list, user_id):
        delete_question_ids = []

        for question_data in questions_list:
            question_id = question_data.get('id') if question_data.get('id') else 0
            question_instance = ModelUtilities.get_model_instance_or_none(communityQuestions, question_id)

            if not question_instance:
                continue

            delete_question_ids.append(question_id)

            CommunityHelper.add_create_edit_question_analytics.delay(question_id, user_id,
                                                                     question_state=question_change_states.DELETE_QUESTION,
                                                                     questions_metadata={
                                                                         'community_id': community_instance.id,
                                                                         'community_name': community_instance.name,
                                                                         'questions_type':
                                                                             question_instance.question_state
                                                                     })
            
            # Delete user meta cache for users with this question
            CommunityHelper.delete_user_meta_cache_for_users_with_question(question_instance.id, 
                                                                           community_instance.id)


        ModelUtilities.get_model_filter(communityQuestions, {'id__in': delete_question_ids,
                                                             'community': community_instance}).delete()

    @staticmethod
    def validate_fetch_questions_request(user_id, community_id, req_body, api_key=None):
        validation_params = {
            'community_id': {
                'community_id': community_id,
                'api_key': api_key
            }
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        community_instance = validated_dict.get('community_id')
        user_instance = None

        if user_id:
            user_instance = ModelUtilities.get_user_instance_or_none(user_id, community_instance.id)

            if not user_instance:
                return ResponseUtilities.get_inner_error_context('Invalid user ID!')

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'aj': req_body.get('aj', None),
            'shared_by': req_body.get('shared_by', None)
        }

    @staticmethod
    def get_toast_according_to_aj_expiry(community_instance, unique_code, shared_by_user=None, user_instance=None):
        '''function to send private link for app invite on playstore'''

        expiry_filter = communityExpiryCodes.objects.filter(community=community_instance, unique_code=unique_code)
        shared_by_user_name = shared_by_user.userinfo.name

        auto_join = {
            'toast': PRIVATE_LINK_APP_INVITE_DEFAULT_TOAST.format(shared_by_user_name),
            'aj_expired': True
        }

        if (not community_instance.is_paid) and (not expiry_filter) or \
                (community_instance.is_paid and expiry_filter.filter(user=user_instance)):
            return auto_join

        if expiry_filter.exists():
            auto_join['aj_expired'] = False
            auto_join['toast'] = ""

        return auto_join

    @staticmethod
    def get_community_managers(community_instance):
        '''function to get count of community managers'''

        manager_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                   'state': member_states.ADMIN}).order_by('created_at')
        temp = {}
        manager_name = ""
        for manager in manager_filter:
            manager_name = manager.member_id.userinfo.name
            break
        temp['manager_name'] = manager_name
        temp['count'] = manager_filter.count()

        return temp

    @staticmethod
    def send_drop_off_notification_in_join(user_instance, community_instance, aj):
        is_verified = Members.objects.filter(community_id=community_instance, member_id=user_instance).filter(
            Q(state=member_states.ADMIN) | Q(state=member_states.PROFILE_UNAVAILABLE) |
            Q(state=member_states.MEMBER) | Q(state=member_states.KNOWN_NOMINATED_PROMOTER))

        if not is_verified:
            from collabmates_api.notification import send_notification_to_join_drop_off
            send_notification_to_join_drop_off.delay(user_instance.id, community_instance.id, aj,
                                                     TIME_IN_HRS_TO_SEND_JOIN_DROP_OFF_NOTIFICATION)

        return is_verified

    @staticmethod
    def compute_community_meta_data_according_to_aj_shared_by(user_instance, community_instance, aj, shared_by):
        community_serialized_object = CommunitySerializerV1(community_instance, many=False).data
        community_serialized_object['created_by'] = get_community_creator(community_instance)
        managers = CommunityHelper.get_community_managers(community_instance)

        if managers['count'] > 1:
            managed_by = COMMUNITY_QUESTIONS_MORE_MANAGER_NAME_VALUE.format(managers['manager_name'],
                                                                            str(managers['count'] - 1))
        else:
            managed_by = managers['manager_name']

        community_serialized_object['managed_by'] = managed_by

        is_valid_private_link = False
        auto_join = {}
        title = COMMUNITY_QUESTIONS_DEFAULT_TITLE.format(community_serialized_object['name'])

        if shared_by:
            shared_by = ModelUtilities.get_model_instance_or_none(User, shared_by)
            shared_by_user_name = shared_by.userinfo.name
            title = FETCH_QUESTIONS_SHARED_BY_USER_TITLE.format(shared_by_user_name,
                                                                community_serialized_object['name'])

        if aj and shared_by:
            auto_join = CommunityHelper.get_toast_according_to_aj_expiry(community_instance, aj, shared_by, user_instance)
            is_valid_private_link = True

        context = {'header': FETCH_COMMUNITY_QUESTIONS_JOIN_TITLE,
                   'title': title, 'community': community_serialized_object}

        if is_valid_private_link:
            context.update(auto_join)

        return context

    @staticmethod
    def get_community_questions_data(user_instance, community_instance, platform_code='web', version_code=0,
                                     sdk_source=None):
        data = ModelUtilities.get_model_filter(communityQuestions,
                                               {"community": community_instance}).order_by('-rank', 'id')

        questions = []

        serialized_questions = CommunityQuestionsSerializerV2(data, many=True).data

        for serialized_question in serialized_questions:

            if all([platform_code == PLATFORM_CODE_WEB,
                    serialized_question['question_title'] == CREATE_COMMUNITY_QUESTION_NAME_TITLE,
                    serialized_question['is_hidden'],
                    serialized_question['field'],
                    serialized_question['question_state'] == question_states.PARAGRAPH]):
                continue

            if all([serialized_question['question_state'] == question_states.NAME,
                    not VersionUtilities.check_version(platform_code, version_code, VersionUtilities.alias_question,
                                                       sdk_source)]):
                continue

            serialized_question['state'] = serialized_question['question_state']
            serialized_question['community_id'] = serialized_question['community']
            del serialized_question['question_state']
            del serialized_question['community']

            if serialized_question['state'] == question_states.INTRODUCTION:
                serialized_question['rank'] = 0

                if user_instance:
                    answers_filter = ModelUtilities.get_model_filter(communityAnswers,
                                                                     {'question': serialized_question['id'],
                                                                      'member': user_instance.id})
                    if answers_filter.exists():
                        answer_instance = answers_filter[0]
                        introduction_answer = answer_instance.question_answer
                        serialized_question['previous_answer'] = introduction_answer

            # Don't append question if remove_state is True
            if not serialized_question['remove_state']:
                del serialized_question['remove_state']
                questions.append(serialized_question)

        return questions

    @staticmethod
    def generate_community_share_link(user_instance, community_instance, platform_code, version_code, link_type='free'):
        share_context = get_branch_links_for_community_share_v1(user_instance, community_instance,
                                                                platform_code, version_code)

        community_share = {}

        if community_instance.is_paid:
            fill_share_context_for_paid_community(community_instance, share_context, community_share)

        else:
            fill_share_context_for_unpaid_community(community_instance, share_context, community_share)

        if not community_share:
            return get_error_context(False, "Error in generating link")

        aj = ''

        if link_type == 'free':
            link = community_share.get('private_link')
            aj = share_context.get('aj')

        else:
            link = community_share.get('public_link')

        return {'success': True, 'community_share': community_share, 'share_context': share_context, 'link': link,
                'aj': aj}

    @staticmethod
    def get_default_community_type_subtype_id():
        type_id = TYPE_ID_WITH_NO_DIRECTORY_QUESTIONS
        sub_type_id = SUB_TYPE_ID_WITH_NO_DIRECTORY_QUESTIONS

        community_field_type_filter_dict = {
            'type': DEFAULT_COMMUNITY_FIELD_TYPE_NAME,
            'sub_type_header': DEFAULT_COMMUNITY_FIELD_TYPE_NAME,
            'sub_type_placeholder': DEFAULT_COMMUNITY_FIELD_TYPE_NAME,
            'rank': DEFAULT_COMMUNITY_FIELD_TYPE_RANK
        }

        community_field_sub_type_filter_dict = {
            'sub_type': DEFAULT_COMMUNITY_FIELD_TYPE_NAME,
            'rank': DEFAULT_COMMUNITY_FIELD_TYPE_RANK
        }

        community_type_filter = ModelUtilities.get_model_filter(communityFieldTypes,
                                                                community_field_type_filter_dict)

        if community_type_filter:
            type_id = community_type_filter[0].id

        community_sub_type_filter = ModelUtilities.get_model_filter(communityFieldSubTypes,
                                                                    community_field_sub_type_filter_dict)

        if community_sub_type_filter:
            sub_type_id = community_sub_type_filter[0].id

        return type_id, sub_type_id

    @staticmethod
    def validate_fetch_branding_info_request(user_id, community_id, req_body):
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return {'success': False, 'error_message': 'Invalid member-id'}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return {'success': False, 'error_message': 'Invalid community_id'}

        return {'success': True, 'user_instance': user_instance, 'community_instance': community_instance,
                'aj': req_body.get('aj', None), 'shared_by': req_body.get('shared_by', None)}

    @staticmethod
    def validate_update_community_dm_settings_request(user_id, community_id, api_key, req_body, 
                                                      api_revamp_v1_check=False):
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return {'success': False, 'error_message': 'Invalid member-id'}

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return {'success': False, 'error_message': 'Invalid community ID/API Key!'}

        if not Members.is_member_community_promoter(community_instance, user_instance):
            return {'success': False, 'error_message': 'You are not CM/Owner of this community!'}

        if not check_admin_moderate_dm_settings_right(user_instance, community_instance):
            return {'success': False, 'error_message': "You don't have right to update this setting!"}

        update_dict = {}

        if req_body.get('state') is not None:

            # If api revamp v1 is TRUE, update state
            if api_revamp_v1_check:
                req_body['state'] = CommunityDMSettingTypes.get_int_state_type_from_string(req_body.get('state'))

            if req_body.get('state') not in [community_dm_settings_state_types.UNLIMITED,
                                             community_dm_settings_state_types.LIMITED]:
                return {'success': False, 'error_message': 'Invalid state value!'}

            else:
                update_dict['state'] = req_body.get('state')

        if req_body.get('duration'):

            if req_body.get('duration') not in [community_dm_settings_duration_types.DAYS,
                                                community_dm_settings_duration_types.WEEKS,
                                                community_dm_settings_duration_types.MONTHS]:
                return {'success': False, 'error_message': 'Invalid duration value!'}

            else:

                if not req_body.get('number_in_duration'):
                    return {'success': False, 'error_message': 'Invalid number_in_duration value!'}

                update_dict['duration'] = req_body.get('duration')

        if req_body.get('number_in_duration'):

            if not isinstance(req_body.get('number_in_duration'), int):
                return {'success': False, 'error_message': 'Invalid number_in_duration value!'}

            else:
                update_dict['number_in_duration'] = req_body.get('number_in_duration')

        return {'success': True, 'user_instance': user_instance, 'community_instance': community_instance,
                'update_dict': update_dict}

    @staticmethod
    def validate_fetch_community_dm_settings_request(user_id, community_id, api_key):
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return {'success': False, 'error_message': 'Invalid member-id'}

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return {'success': False, 'error_message': 'Invalid community ID/API Key!'}

        if not Members.is_member_community_promoter(community_instance, user_instance):
            return {'success': False, 'error_message': 'You are not CM/Owner of this community!'}

        if not check_admin_moderate_dm_settings_right(user_instance, community_instance):
            return {'success': False, 'error_message': "You don't have right to fetch this setting!"}

        return {'success': True, 'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_fetch_community_dm_right_request(user_id, community_id, req_body):
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return {'success': False, 'error_message': 'Invalid member-id'}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return {'success': False, 'error_message': 'Invalid community_id'}

        if req_body.get('state') is None:
            return {'success': False, 'error_message': 'Empty state'}

        state = NumberUtilities.get_integer_from_string(req_body.get('state'), -1)

        if state < LEAST_MEMBER_RIGHT_STATE_VALUE:
            return {'success': False, 'error_message': 'Invalid state'}

        return {'success': True, 'user_instance': user_instance, 'community_instance': community_instance,
                'state': state}

    @staticmethod
    @shared_task
    def create_community_noti_settings_instance_on_community_creation(community_id):

        current_time = TimeUtilities.current_time_in_milliseconds()

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        try:
            CommunityNotificationSettings.objects.create(
                community=community_instance,
                created_at=current_time,
                updated_at=current_time
            )

        except Exception as e:
            error_logger.error("Exception occurred while creating ResourceSettings on community creation - %s" % e.args)

    @staticmethod
    def fetch_community_noti_settings_instance(community_instance):

        noti_setting_instance = ModelUtilities.get_model_filter(CommunityNotificationSettings,
                                                                {'community': community_instance})

        return noti_setting_instance[0] if noti_setting_instance else None

    @staticmethod
    @shared_task
    def trigger_event_analytics_on_updating_community_noti_settings(user_id, community_id, noti_state):
        event_name = COMMUNITY_NOTIFICATION_SETTING_UPDATED_EVENT

        community = ModelUtilities.get_model_instance_or_none(Community, community_id)

        community_name = community.name if community else ""

        if noti_state == noti_states.ALL_MESSAGES:
            setting = noti_states.ALL_MESSAGES_ANALYTICS

        elif noti_state == noti_states.ONLY_MENTIONS_AND_REPLIES:
            setting = noti_states.ONLY_MENTIONS_AND_REPLIES_ANALYTICS

        else:
            setting = noti_states.DM_MENTION_REPLIES_POLL_ANALYTICS

        event_dict = {
            'community_id': community_id,
            'community_name': community_name,
            'setting': setting
        }

        SegmentImpl.track_event(user_id, event_name, event_dict)

    @staticmethod
    def fetch_feed_notification_settings_instances(community_instance):
        notification_setting_instances = ModelUtilities.get_model_filter(FeedNotificationSettings,
                                                                         {'community': community_instance})

        return notification_setting_instances

    @staticmethod
    @shared_task
    def update_feed_notification_settings_based_on_feed_setting(community_id, is_enabled=False):
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)
        if not community_instance:
            return

        if is_enabled:
            valid_notification_types = [feed_notification_states.LIKES,
                                        feed_notification_states.COMMENTS,
                                        feed_notification_states.REPLIES_ON_YOUR_COMMENTS,
                                        feed_notification_states.UPDATES_ON_COMMENTED_POST]
            for notification_type in valid_notification_types:
                ModelUtilities.update_or_create_model(
                    FeedNotificationSettings, {'community': community_instance, 'notification_type': notification_type},
                    {'enabled': True}
                )

        if not is_enabled:
            ModelUtilities.delete_record_in_model(FeedNotificationSettings, {'community': community_instance})

    @staticmethod
    @shared_task
    def update_feed_create_poll_settings_based_on_feed_setting(community_id: int, user_id: int, is_enabled: bool):

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)
        if not community_instance:
            return
        
        # Fetch community configurations
        configurations = CommunityHelper.fetch_or_return_default_community_configurations(community_id, [FEED_SETTINGS_CONFIGURATION])
        if not configurations:
            return
        
        if is_enabled:

            if configurations[0].get('value').get('create_feed_poll') != "everyone":
                update_values = {
                    'create_feed_poll': 'everyone'
                }

                CommunityHelper.update_configuration_of_community(community_id, user_id, FEED_SETTINGS_CONFIGURATION, update_values)

        else:
            update_values = {
                'create_feed_poll': 'no_one'
            }

            CommunityHelper.update_configuration_of_community(community_id, user_id, FEED_SETTINGS_CONFIGURATION, update_values)

    @staticmethod
    def validate_fetch_community_noti_settings(user_id, community_id, api_key):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)
        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)
        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community_id or API Key")

        is_admin = Members.is_member_community_promoter(community_instance, user_instance)
        if not is_admin:
            return ResponseUtilities.get_inner_error_context("You are not CM/Owner of this community")

        return {'community_instance': community_instance}

    @staticmethod
    def validate_update_community_noti_settings(user_id, community_id, api_key, req_body):

        if not req_body:
            return ResponseUtilities.get_inner_error_context("Invalid request body")

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)
        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)
        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community_id")

        is_admin = Members.is_member_community_promoter(community_instance, user_instance)
        if not is_admin:
            return ResponseUtilities.get_inner_error_context("You are not CM/Owner of this community")

        noti_state = int(req_body.get('noti_state'))
        if not noti_state:
            return ResponseUtilities.get_inner_error_context("noti_state is required")

        if noti_state not in [noti_states.ALL_MESSAGES,
                              noti_states.ONLY_MENTIONS_AND_REPLIES,
                              noti_states.DM_MENTION_REPLIES_POLL]:
            return ResponseUtilities.get_inner_error_context("invalid noti_state")

        return {'noti_state': noti_state, 'community_instance': community_instance}

    @staticmethod
    def validate_fetch_feed_notification_settings(user_id, api_key):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)
        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)
        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        is_admin = Members.is_member_community_promoter(community_instance, user_instance)
        if not is_admin:
            return ResponseUtilities.get_inner_error_context("You are not CM/Owner of this community")

        feed_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                              {'community': community_instance,
                                                               'setting_type': community_setting_types.FEED,
                                                               'enabled': True})
        if not feed_setting_filter:
            return ResponseUtilities.get_inner_error_context("Feed feature is disabled in this community")

        return {'community_instance': community_instance}

    @staticmethod
    def validate_update_feed_notification_settings(user_id, api_key, notification_settings):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)
        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)
        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        is_admin = Members.is_member_community_promoter(community_instance, user_instance)
        if not is_admin:
            return ResponseUtilities.get_inner_error_context("You are not CM/Owner of this community")

        has_moderate_feed_right = check_admin_moderate_feed_and_comments_right(user_instance, community_instance)
        if not has_moderate_feed_right:
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this operation")

        feed_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                              {'community': community_instance,
                                                               'setting_type': community_setting_types.FEED,
                                                               'enabled': True})
        if not feed_setting_filter:
            return ResponseUtilities.get_inner_error_context("Feed feature is disabled in this community")

        valid_notification_types = [feed_notification_states.LIKES,
                                    feed_notification_states.COMMENTS,
                                    feed_notification_states.REPLIES_ON_YOUR_COMMENTS,
                                    feed_notification_states.UPDATES_ON_COMMENTED_POST]

        new_notification_settings = []

        if not isinstance(notification_settings, list):
            return ResponseUtilities.get_inner_error_context("Invalid notification_settings sent")

        for notification_setting in notification_settings:
            if any([notification_setting.get('notification_type', 0) not in valid_notification_types,
                    not isinstance(notification_setting.get('enabled'), bool)]):
                return ResponseUtilities.get_inner_error_context("Invalid notification_settings sent")
            else:
                new_notification_settings.append({
                    'notification_type': notification_setting.get('notification_type'),
                    'community': community_instance,
                    'enabled': notification_setting.get('enabled')
                })

        return {'community_instance': community_instance, 'notification_settings': new_notification_settings}
    
    @staticmethod
    def compute_members_meta_list(community_instance, member_ids, page, page_size, search_name, 
                                  excluded_member_ids: list = None):
        
        members_data = []

        # Get valid user_ids from member_ids
        user_ids = ModelUtilities.get_valid_member_ids(member_ids, community_id=community_instance.id)

        # If all member_ids are invalid return empty list
        if member_ids and not user_ids:
            return members_data

        # Get query result
        members_data = get_members_meta_list(community_id=community_instance.id,
                                             member_ids=user_ids,
                                             page=page,
                                             page_size=page_size,
                                             search_string=search_name,
                                             excluded_member_ids=excluded_member_ids)

        return members_data
    
    @staticmethod
    def validate_fetch_users_meta_info_request(user_id, api_key, member_ids):
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        member_ids = StringUtilities.get_list_from_string(member_ids)

        if (not member_ids) or (member_ids and not isinstance(member_ids, list)):
            return ResponseUtilities.get_inner_error_context('Invalid member ids')

        member_ids = [str(member_id) for member_id in member_ids]

        return {
            'user_instance': validated_dict.get('user_id'),
            'community_instance': validated_dict.get('community_id'),
            'member_ids': member_ids
        }

    @staticmethod
    def validate_fetch_content_download_settings_request(user_id, community_id, api_key, chatroom_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return {'error_message': "Invalid user ID"}

        validation_params = {
            'community_id': {
                'community_id': community_id,
                'api_key': api_key
            }
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if not validated_dict.get('error_message'):
            community_instance = validated_dict.get('community_id')

        else:
            chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

            if not chatroom_instance:
                return ResponseUtilities.get_inner_error_context("Invalid community/chatroom ID.")

            else:
                community_instance = chatroom_instance.community

        return {
            'user_instance': user_instance,
            'community_instance': community_instance
        }

    @staticmethod
    def validate_update_content_download_settings_request(user_id, api_key):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return {'error_message': "Invalid user ID"}

        validation_params = {
            'community_id': {
                'api_key': api_key
            }
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        community_instance = None

        if not validated_dict.get('error_message'):
            community_instance = validated_dict.get('community_id')

        return {
            'user_instance': user_instance,
            'community_instance': community_instance
        }

    @staticmethod
    def validate_fetch_community_request(community_id, api_key):
        validation_params = {
            'community_id': {
                'api_key': api_key,
                'community_id': community_id
            }
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        return {
            'community_instance': validated_dict.get('community_id')
        }    

    @staticmethod
    def validate_fetch_report_tags_request(user_id, api_key, entity_type: str):

        if not entity_type:
            return ResponseUtilities.get_inner_error_context("Please provide entity_type in query params")
        
        if entity_type not in REPORT_TYPES:
            return ResponseUtilities.get_inner_error_context("Invalid entity_type in query params")

        # Get report_type from constants
        report_type = REPORT_TYPES[entity_type]

        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instance = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        # Check if user is community member
        is_community_member = Members.is_community_member(community_instance, user_instance)

        if not is_community_member:
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this operation")
        
        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'report_type': report_type
        }
    
    @staticmethod
    def validate_push_community_report_request(user_id, api_key, community_id, req_body):

        entity_type = req_body.get('entity_type')
        entity_id = req_body.get('entity_id')

        if not entity_id:
            return ResponseUtilities.get_inner_error_context("Please provide entity_id in request body")
        
        if not entity_type:
            return ResponseUtilities.get_inner_error_context("Please provide entity_type in request body")

        if entity_type not in REPORT_TYPES:
            return ResponseUtilities.get_inner_error_context("Invalid entity_type")
        
        report_type = REPORT_TYPES[entity_type]
        
        validation_params = {
            'community_id': {
                'community_id': community_id,
                'api_key': api_key
            },
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instance = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        member_instance = Members.get_member_instance_or_none(community_instance, user_instance)
        if not member_instance:
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this operation")

        has_admin_delete_right = check_admin_delete_right(user_instance, community_instance)
        has_admin_approve_right = check_admin_approve_right(user_instance, community_instance)

        report_tag_instance = ModelUtilities.get_model_filter(Report_Tags, 
                                                              {'tag_id': req_body.get('tag_id')}).first()

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'report_tag_instance': report_tag_instance,
            'member_instance': member_instance,
            'has_admin_delete_right': has_admin_delete_right,
            'has_admin_approve_right': has_admin_approve_right,
            'report_type': report_type
        }
    
    @staticmethod
    def validate_close_community_reports_request(user_id, api_key, report_ids, status):

        if not report_ids or not isinstance(report_ids, list):
            return ResponseUtilities.get_inner_error_context("Invalid report_ids")
        
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instance = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        member_instance = Members.get_member_instance_or_none(community_instance, user_instance)

        # Validate if user is admin or not
        if not member_instance or (member_instance.state != member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this operation")
        
        report_instances = ModelUtilities.get_model_filter(Report, {'id__in': report_ids, 
                                                                    'is_closed': False,
                                                                    'community': community_instance})

        # If status is passed for pending post reports, then filter only pending post reports else exclude 
        if status: 

            if not ReportClosingStatus.is_valid_status(status):
                return ResponseUtilities.get_inner_error_context("Invalid status sent for pending post reports")
            
            report_instances.filter(type=REPORT_TYPE_PENDING_POST_INT)

        else:
            report_instances.exclude(type=REPORT_TYPE_PENDING_POST_INT)
        
        # Check if report ids are valid
        if len(report_instances) != len(report_ids):
            return ResponseUtilities.get_inner_error_context("Invalid report_id/s sent")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'member_instance': member_instance,
            'report_instances': report_instances,
        }

    @staticmethod
    def create_answer_data_dict(user_answer, question_data):
        user_answer_dict = {
            'answer': user_answer.get('question_answer'),
            'member_id': user_answer.get('member'),
            'question_id': user_answer.get('question'),
            'community_id': user_answer.get('community')
        }

        # If question_state is present in question_data, then replace it with state
        if question_data.get('question_state') is not None:
            question_data['state'] = question_data.get('question_state')
            del question_data['question_state']

        if all([question_data.get('question_title'),
                (question_data.get('question_title') in IMAGE_URLS_FOR_QUESTION_TITLES),
                (question_data.get('question_title') in ICONS)]):
            user_answer_dict['image_url'] = ICONS[question_data.get('question_title')]

        return {
            'question_answer': user_answer_dict,
            'question': question_data
        }

    @staticmethod
    def get_members_filled_community_answers_data(community_instance, members_object_list):
        users_question_answer_dict = {}

        from collabmates_api.member_community.member_community_impl import MemberCommunityHelper
        member_ids_list = [member_object.get('id') for member_object in members_object_list]

        community_questions_filter = ModelUtilities.get_model_filter(communityQuestions,
                                                                     {'community': community_instance})

        if not community_questions_filter:
            return users_question_answer_dict

        else:
            questions_data = CommunityQuestionsSerializerV2(community_questions_filter, many=True).data
            questions_data_dict = {question_data.get('id'): dict(question_data) for question_data in questions_data}

            community_answers_filter = ModelUtilities.get_model_filter(communityAnswers,
                                                                       {'member__in': member_ids_list,
                                                                        'community': community_instance})

            if community_answers_filter:
                user_answers = CommunityAnswersSerializer(community_answers_filter, many=True).data

                for user_answer in user_answers:
                    user_answer = dict(user_answer)
                    question_data = questions_data_dict.get(user_answer.get('question'))

                    if any([all([question_data.get('question_title') == CREATE_COMMUNITY_QUESTION_NAME_TITLE,
                                 question_data.get('is_hidden'),
                                 question_data.get('field'),
                                 question_data.get('question_state') == question_states.PARAGRAPH]),
                            question_data.get('question_state') == question_states.NAME]):
                        continue

                    discard_question = True

                    if not MemberCommunityHelper.is_user_answer_private(question_data):
                        discard_question = False

                    if not discard_question:
                        question_answer_data = CommunityHelper.create_answer_data_dict(user_answer, question_data)

                        if users_question_answer_dict.get(user_answer.get('member')):
                            users_question_answer_dict[user_answer.get('member')].append(question_answer_data)

                        else:
                            users_question_answer_dict[user_answer.get('member')] = [question_answer_data]

            return users_question_answer_dict

    @staticmethod
    def validate_fetch_community_configurations_request(user_id, community_id, api_key, configuration_types=None):

        validation_params = {
            'community_id': {
                'community_id': community_id,
                'api_key': api_key
            },
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        community_instance = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        # Check if user is community member
        if not Members.is_community_member(community_instance, user_instance):
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this operation")
        
        community_configuration_types = StringUtilities.get_list_from_string(configuration_types)

        valid_configuration_types = COMMUNITY_CONFIGURATIONS.keys()

        # Validate configuration_types if present
        if community_configuration_types:

            if not isinstance(community_configuration_types, list):
                return ResponseUtilities.get_inner_error_context("Invalid configuration_types")

            for community_configuration in community_configuration_types:

                if community_configuration not in valid_configuration_types:
                    return ResponseUtilities.get_inner_error_context("Invalid configuration_types sent in query params")
                
        else:
            community_configuration_types = valid_configuration_types

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'community_configuration_types': community_configuration_types
        }
    
    @staticmethod
    def validate_update_community_configurations_request(user_id, api_key, req_body):

        if not req_body:
            return ResponseUtilities.get_inner_error_context("Invalid request body")
        
        configuration_type = req_body.get('type')
        update_values = req_body.get('value')

        if configuration_type not in COMMUNITY_CONFIGURATIONS.keys():
            return ResponseUtilities.get_inner_error_context("Invalid configuration type")

        if not isinstance(update_values, dict):
            return ResponseUtilities.get_inner_error_context("Invalid value sent in request body")

        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instance = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        # Check if user is an admin
        if not Members.is_member_community_promoter(community_instance, user_instance):
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this operation")
        
        # validation for nsfw filtering configurations
        if configuration_type == NSFW_FILTERING_CONFIGURATION:

            if update_values.get('cutoff_score'):
                
                if not isinstance(update_values.get('cutoff_score'), float):
                    return ResponseUtilities.get_inner_error_context("Send cutoff_score in decimals")
                
                if update_values.get('cutoff_score') < 0 or update_values.get('cutoff_score') > 1:
                    return ResponseUtilities.get_inner_error_context("Invalid cutoff_score sent in request body")
                
            if update_values.get('inferdo_api_key') and isinstance(update_values.get('inferdo_api_key'), str):
                
                # Validate inferdo_api_key
                api_key_validation = CommunityHelper.validate_inferdo_api_key_for_nsfw_filtering(update_values.get('inferdo_api_key'),
                                                                                                 community_instance,
                                                                                                 user_instance)
                if api_key_validation.get('error_message'):
                    return api_key_validation

        elif configuration_type == FEED_METADATA_CONFIGURATION:

            if update_values.get('post') and not (
                    isinstance(update_values.get('post'), str) and update_values.get('post').strip() and
                    len(update_values.get('post').strip()) <= FEED_POST_VARIABLE_MAX_LENGTH):
                return ResponseUtilities.get_inner_error_context("Invalid post value!")

            if update_values.get('comment') and not (
                    isinstance(update_values.get('comment'), str) and update_values.get('comment').strip() and
                    len(update_values.get('comment').strip()) <= FEED_COMMENT_VARIABLE_MAX_LENGTH):
                return ResponseUtilities.get_inner_error_context("Invalid comment value!")
            
            # Validate like_entity_variable values
            if update_values.get('like_entity_variable') is not None and (
                not isinstance(update_values.get('like_entity_variable'), dict) or not (
                    isinstance(update_values.get('like_entity_variable').get('entity_name'), str) and update_values.get('like_entity_variable').get('entity_name').strip() and
                    len(update_values.get('like_entity_variable').get('entity_name').strip()) <= FEED_LIKE_VARIABLE_MAX_LENGTH) or not (
                        isinstance(update_values.get('like_entity_variable').get('past_tense_verb'), str) and update_values.get('like_entity_variable').get('past_tense_verb').strip() and
                        len(update_values.get('like_entity_variable').get('past_tense_verb').strip()) <= FEED_LIKE_VARIABLE_MAX_LENGTH)
                        ):
                    return ResponseUtilities.get_inner_error_context("Invalid like_entity_variable value!")
                
            if update_values.get('anonymous_user_meta'):
                if not isinstance(update_values.get('anonymous_user_meta'), dict):
                    return ResponseUtilities.get_inner_error_context("Invalid anonymous_user_meta value")
                
                if update_values.get('anonymous_user_meta').get('name') and not isinstance(update_values.get('anonymous_user_meta').get('name'), str):
                    return ResponseUtilities.get_inner_error_context("Invalid name value")
                
                if update_values.get('anonymous_user_meta').get('image_url') and not isinstance(update_values.get('anonymous_user_meta').get('image_url'), str):
                    return ResponseUtilities.get_inner_error_context("Invalid image_url value")

        elif configuration_type == FEED_SETTINGS_CONFIGURATION:

            # Fetch community settings
            community_settings_instance = ModelUtilities.get_model_filter(CommunitySettings, 
                                                                          {'community': community_instance,
                                                                           'setting_type': community_setting_types.FEED}
                                                                           ).first()
            
            if community_settings_instance and not community_settings_instance.enabled:
                return ResponseUtilities.get_inner_error_context("Please enable feed settings first")

            if update_values.get('create_feed_poll'):
                if not isinstance(update_values.get('create_feed_poll'), str
                    ) or (update_values.get('create_feed_poll') not in CREATE_FEED_POLL_COMMUNITY_VALUES):
                    return ResponseUtilities.get_inner_error_context(
                        "Please send valid value for create_feed_poll (possible values - 'everyone', 'only_cm', 'no_one')")      
                
            if update_values.get('menu_items_config'): 
                if not isinstance(update_values.get('menu_items_config'), dict):
                    return ResponseUtilities.get_inner_error_context("Invalid menu_items_config value")    
                
                if update_values.get('menu_items_config').get('hide_post'
                    ) and not isinstance(update_values.get('menu_items_config').get('hide_post'), bool):
                    return ResponseUtilities.get_inner_error_context("Invalid hide_post value")
                

        elif configuration_type == CHATBOT_CONFIGURATIONS:

            if update_values.get('enabled') and not isinstance(update_values.get('enabled'), bool):
                return ResponseUtilities.get_inner_error_context("Invalid enabled value")

            if update_values.get('provider') and isinstance(update_values.get('provider'), str) and not (
                update_values.get('provider').strip() == CHATBOT_PROVIDER_OPENAI):
                    return ResponseUtilities.get_inner_error_context(f"Invalid provider value. Supported values - '{CHATBOT_PROVIDER_OPENAI}'")
            
            if update_values.get('api_key'):
                if not isinstance(update_values.get('api_key'), str) or not update_values.get('api_key').strip():
                    return ResponseUtilities.get_inner_error_context("Invalid api_key value")
                
                # Validate open ai api_key
                api_key_validation = OpenAiWrapper(update_values.get('api_key')).validate_open_ai_api_key_or_assistant()
                if api_key_validation.get('error_message'):
                    return api_key_validation
             
        return {
            'community_instance': community_instance,
            'user_instance': user_instance,
            'configuration_type': configuration_type,
            'update_values': update_values
        }

    @staticmethod
    def validate_remove_community_members_request(user_id, api_key, uuids):

        if not uuids or not (isinstance(uuids, list)):
            return ResponseUtilities.get_inner_error_context("Please send uuids in request body") 

        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instance = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        member_instance = Members.get_member_instance_or_none(community_instance, user_instance)

        # Validate if user is admin or not
        if not member_instance or (member_instance.state != member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this operation")
        
        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'member_instance': member_instance,
            'uuids': uuids
        }
    
    @staticmethod
    @shared_task
    def remove_community_members(is_async: bool, community_id: int, current_user_id:int, uuids: list,
                                 tag_id: int, reason: str) -> dict:
                
        if not uuids and not (isinstance(uuids, list)):
            return {}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)
        current_user_instance = ModelUtilities.get_model_instance_or_none(User, current_user_id)

        if not (community_instance and current_user_instance):
            return {}

        users_removal_status = []
        lm_uuids = []
        users_removed = 0

        users_meta_dict = get_users_meta_info(community_id=community_id, member_ids=uuids, user_meta_or_none_dict=True)

        if is_async:
            info_logger.info(f"Running async tasks for removing {len(uuids)} members from community {community_id}")

        for uuid, user_meta in users_meta_dict.items():

            status = {
                "uuid": uuid,
                "lm_uuid": "",
                "is_removed": False,
                "status": ""
            }
            
            # If invalid uuid is sent, append to users_removal_status and continue
            if not user_meta:
                status['status'] = "Invalid uuid sent"
                users_removal_status.append(status)
                continue
            
            else:
                status['lm_uuid'] = user_meta.get('user_unique_id')

            user_id = user_meta.get('user_id')

            member_instance = Members.get_member_instance_or_none(community_instance, user_id)

            if not member_instance:
                status['status'] = "User is not a member of community"
                users_removal_status.append(status)
                continue

            if member_instance.is_owner:
                status['status'] = "Cannot remove owner"
                users_removal_status.append(status)
                continue

            eligible_member_states = [member_states.ADMIN, member_states.MEMBER,
                                      member_states.PROFILE_UNAVAILABLE]

            if member_instance.state not in eligible_member_states:
                status['status'] = f"Cannot remove member with state {member_instance.state}" 
                users_removal_status.append(status)
                continue

            # Run async tasks for member removal
            CommunityHelper.run_async_tasks_for_member_removal.delay(community_id=community_id,
                                                                     user_id=user_id,
                                                                     current_user_id=current_user_id,
                                                                     reason=reason, tag_id=tag_id)

            status['is_removed'] = True
            status['status'] = "Successfully removed user"

            lm_uuids.append(status['lm_uuid'])
            users_removal_status.append(status)

            users_removed += 1

        # Call swarm service to remove users feed data
        if lm_uuids:
            InternalServiceUtilities.remove_users_feed_data.delay(
                community_id=community_id, user_id=current_user_id, lm_uuids=lm_uuids, is_cm=True)

        # If function call is Async, upload reports to s3
        if is_async:
            CommunityHelper.upload_users_removal_reports.delay(removal_status=users_removal_status, 
                                                               community_id=community_id)
        
        else: 
            return {
                "removal_status": users_removal_status,
                "message": f"Successfully removed {users_removed} users"
            }
        
    @staticmethod
    @shared_task
    def run_async_tasks_for_member_removal(community_id: int, user_id: int, current_user_id, reason: str, tag_id: int):

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)
        current_user_instance = ModelUtilities.get_model_instance_or_none(User, current_user_id)

        if not (community_instance and user_instance and current_user_instance):
            return
        
        try:
            info_logger.info(f"Removing user {user_id} from community {community_id} by {current_user_id}")

            remove_members(community_instance, user_instance, 
                           removed_state=deleted_members.REMOVED,
                           current_user_instance=current_user_instance)
                
            save_moderation_history(user=user_instance, community=community_instance,
                                    moderation_by=current_user_instance,
                                    type=moderation_history_types.REMOVED_FROM_COMMUNITY)

            remove_all_member_rights(community_instance, user_instance)
            
            remove_all_manager_rights(community_instance, user_instance)

            check_reports_and_update_action.delay(action_taken_by=current_user_instance.id,
                                                    action_taken=report_action_types.REMOVE_FROM_COMMUNITY,
                                                    user=user_id, community=community_id,
                                                    action_taken_tag_id=tag_id, action_taken_reason=reason)
            
            send_notification_for_removed_member.delay(admin_id=current_user_instance.id,
                                                       removed_user_id=user_id, community_id=community_id)
            
            analytics_data = {
                'removed_member_id': user_id,
                'community_id': community_id,
                'reason': reason
            }

            SegmentImpl.track_event(current_user_instance.id, 'Member removed (Backend)', analytics_data)

            send_sync_notification.delay({'community_id': community_id,
                                            'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})
            update_multiple_previews_in_community.delay({'community_id': community_id})

            ElasticSearchSync.delete_chatrooms_for_removed_member.delay(community_id, user_id)

            CohortHelper.fetch_user_cohorts_having_filters_with_community_id(community_id, user_instance)

            # Delete user meta cache in kettle service
            cache_key = KETTLE_CACHE_KEY_USER_META.format(community_instance.id, user_instance.userinfo.user_unique_id)

            InternalServiceUtilities.delete_cache_from_kettle_service.delay(
                community_id=community_instance.id, user_id=user_instance.id,
                key_patterns=[cache_key] 
            )

            info_logger.info(f"Successfully removed user {user_id} from community {community_id} by {current_user_id}")

        except Exception as e:
            error_logger.error(f"Exception occurred while removing member {user_id} from community {community_id } - {e.args}")
        
    @staticmethod
    @shared_task
    def upload_users_removal_reports(removal_status: list, community_id: int) -> bool:
        
        if not (removal_status and community_id):
            return False

        try:
            info_logger.info(f"Uploading user removal reports to s3 for community {community_id}")
        
            csv_file_path = CommunityHelper.parse_json_to_csv_for_users_removal_reports(removal_status)

            if not csv_file_path:
                return False

            uploaded = CommunityHelper.upload_users_removal_reports_to_s3(community_id=community_id,
                                                                          csv_file_path=csv_file_path)
            
            # delete csv file from local
            os.remove(csv_file_path)

            if uploaded:
                info_logger.info(f"Successfully uploaded user removal reports to s3 for community {community_id}")

            return uploaded
        
        except Exception as e:
            error_logger.error(f"Exception occurred while uploading user removal reports to s3 - {e.args}")
            return False
    
    @staticmethod
    def parse_json_to_csv_for_users_removal_reports(removal_status: list):

        if not removal_status:
            return None
        
        try:        
            absolute_path = os.path.abspath(os.getcwd())
            
            file_path = COMMUNITY_REMOVE_MEMBER_CSV_REPORT_LOCAL_PATH.format(absolute_path, TimeUtilities.current_time_in_sec())
            csv_file = open(file_path, 'w')
    
            csv_writer = csv.writer(csv_file)
    
            count = 0 
            for user_removal in removal_status:
                
                if count == 0:
                    header = user_removal.keys()
                    csv_writer.writerow(header)
                    count += 1

                csv_writer.writerow(user_removal.values())

            csv_file.close()

            return file_path

        except Exception as e:
            error_logger.error(f"Exception occurred while parsing json to csv for user removal reports - {e.args}")
            return None
    
    @staticmethod
    def upload_users_removal_reports_to_s3(community_id: int, csv_file_path: str) -> bool:

        if not (community_id and csv_file_path):
            return

        bucket = settings.S3_BUCKETS.get(COMMUNITY_REMOVE_MEMBER_S3_BUCKET)
        s3_client = S3ClientImpl(bucket)

        current_date_time_in_str = TimeUtilities.get_current_datetime_in_IST().strftime("%d-%m-%y-%X")

        s3_user_removal_reports_path = COMMUNITY_REMOVE_MEMBER_S3_FILE_PATH.format(community_id, 
                                                                                   community_id, 
                                                                                   current_date_time_in_str)

        uploaded = s3_client.upload_file_to_s3_bucket(object_path=csv_file_path, file_path=s3_user_removal_reports_path)

        return uploaded

    @staticmethod
    def validate_fetch_community_removal_reports_request(user_id, api_key) -> dict:
            
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instance = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        member_instance = Members.get_member_instance_or_none(community_instance, user_instance)

        # Validate if user is admin or not
        if not member_instance or (member_instance.state != member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this operation")
        
        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'member_instance': member_instance
        }

    @staticmethod
    def fetch_users_removal_reports_from_s3(community_id: int) -> list:

        if not community_id:
            return

        removal_reports = []

        bucket = settings.S3_BUCKETS.get(COMMUNITY_REMOVE_MEMBER_S3_BUCKET)
        s3_client = S3ClientImpl(bucket)

        s3_user_removal_community_path = COMMUNITY_MEMBER_REMOVAL_REPORTS_PATH.format(community_id)

        # Fetch all objects from s3 bucket for the community
        s3_objects = s3_client.fetch_files_from_s3_bucket(file_path=s3_user_removal_community_path)

        for object in s3_objects:
            object_key = object.get('Key')
            last_modified = object.get('LastModified')

            download_url = COMMUNITYY_MEMBER_REMOVAL_S3_DOWNLOAD_URL.format(bucket.get("name"), 
                                                                           bucket.get("region"), 
                                                                           object_key)
            
            # Append download url and last modified date to response
            removal_reports.append({
                "url": download_url,
                "last_modified": last_modified
            })

        return removal_reports

    @staticmethod
    def fetch_or_return_default_community_configurations(community_instance, community_configuration_types: list):
        # fetch community configurations from db
        community_configurations_instances = ModelUtilities.get_model_filter(
            CommunityConfigurations, {'community': community_instance, 'type__in': community_configuration_types})

        # key value pair of configuration_type -> configuration instance
        configuration_instances_response = {instance.type: instance for instance in community_configurations_instances}

        # Add default configurations if not present
        for configuration_type in community_configuration_types:

            if configuration_type not in configuration_instances_response:
                instance = CommunityConfigurations(**COMMUNITY_CONFIGURATIONS[configuration_type])
                configuration_instances_response[configuration_type] = instance

        # serialize community configurations
        serialised_community_configurations = CommunityConfigurationsSerializer(
            configuration_instances_response.values(), many=True).data

        return serialised_community_configurations
    
    @staticmethod
    @shared_task
    def update_configuration_of_community(community_id: int, user_id: int, configuration_type: str, update_values: dict):

        record_updated = False

        # Fetch configuration instance if present
        configuration_instance = ModelUtilities.get_model_filter(CommunityConfigurations, 
                                                                 {'community_id': community_id,
                                                                  'type': configuration_type}).first()
        
        # If configuration instance is not present, create instance with default values
        if not configuration_instance:
            configuration_instance = CommunityConfigurations(**COMMUNITY_CONFIGURATIONS[configuration_type], 
                                                             community_id=community_id)
            
        configuration_value = configuration_instance.value

        if configuration_type == MEDIA_LIMITS_CONFIGURATION:

            if update_values.get('max_image_size') and isinstance(update_values.get('max_image_size'), int):
                configuration_value['max_image_size'] = update_values.get('max_image_size')
                record_updated = True

            if update_values.get('max_video_size') and isinstance(update_values.get('max_video_size'), int):
                configuration_value['max_video_size'] = update_values.get('max_video_size')
                record_updated = True

        elif configuration_type == FEED_METADATA_CONFIGURATION:

            if update_values.get('post'):
                configuration_value['post'] = update_values.get('post').strip()
                record_updated = True

            if update_values.get('comment'):
                configuration_value['comment'] = update_values.get('comment').strip()
                record_updated = True

            if update_values.get('like_entity_variable') and isinstance(update_values.get('like_entity_variable'), dict):

                if not (configuration_value.get('like_entity_variable') or isinstance(configuration_value.get('like_entity_variable'), dict)):
                    configuration_value['like_entity_variable'] = {}

                if update_values.get('like_entity_variable').get('entity_name'):
                    configuration_value['like_entity_variable']['entity_name'] = update_values.get('like_entity_variable').get('entity_name').strip()
                    record_updated = True

                if update_values.get('like_entity_variable').get('past_tense_verb'):
                    configuration_value['like_entity_variable']['past_tense_verb'] = update_values.get('like_entity_variable').get('past_tense_verb').strip()
                    record_updated = True

            if isinstance(update_values.get('universal_feed'), dict):
                configuration_value['universal_feed'] = update_values.get('universal_feed')

                if not isinstance(configuration_value['universal_feed'], dict):
                    configuration_value['universal_feed'] = {}

                comment_sort_order_on = update_values.get('universal_feed').get('comment_sort_order_key')
                comment_sort_order = update_values.get('universal_feed').get('comment_sort_order')
                comment_count = update_values.get('universal_feed').get('comment_count')

                if isinstance(comment_sort_order_on, str):
                    configuration_value['universal_feed']['comment_sort_order_key'] = comment_sort_order_on

                if isinstance(comment_sort_order, str):
                    configuration_value['universal_feed']['comment_sort_order'] = comment_sort_order

                if isinstance(comment_count, int):
                    configuration_value['universal_feed']['comment_count'] = comment_count

                record_updated = True

                # Delete swarm cache corresponding to universal feed
                InternalServiceUtilities.delete_cache_from_swarm_service.delay(
                    community_id=community_id, user_id=user_id,
                    key_pattern=SWARM_TOP_LIKED_COMMENTS_CACHE_KEY.format(community_id))
                
            if update_values.get('anonymous_user_meta') and isinstance(update_values.get('anonymous_user_meta'), dict):

                if not (configuration_value.get('anonymous_user_meta') or isinstance(configuration_value.get('anonymous_user_meta'), dict)):
                    configuration_value['anonymous_user_meta'] = {}

                if update_values.get('anonymous_user_meta').get('name'):
                    configuration_value['anonymous_user_meta']['name'] = update_values.get('anonymous_user_meta').get('name')
                    record_updated = True

                if update_values.get('anonymous_user_meta').get('image_url'):
                    configuration_value['anonymous_user_meta']['image_url'] = update_values.get('anonymous_user_meta').get('image_url')
                    record_updated = True
                    
                if record_updated:
                    
                    # Delete kettle cache for anonymous user
                    InternalServiceUtilities.delete_cache_from_kettle_service.delay(
                        community_id=community_id, user_id=user_id,
                        key_patterns=[KETTLE_CACHE_KEY_ANONYMOUS_USER_META.format(community_id)])

        elif configuration_type == PROFILE_METADATA_CONFIGURATION:
            
            if (update_values.get('widgets_enabled') is not None) and isinstance(
                    update_values.get('widgets_enabled'), bool):
                configuration_value['widgets_enabled'] = update_values.get('widgets_enabled')
                record_updated = True

        elif configuration_type == NSFW_FILTERING_CONFIGURATION:
            # If NSFW Filtering is toggled, update configurations and community settings
            if (update_values.get('enabled') is not None) and isinstance(update_values.get('enabled'), bool) and \
                    update_values.get('enabled') != configuration_value.get('enabled'):
                configuration_value['enabled'] = update_values.get('enabled')
                record_updated = True

                filter_dict = {
                    'community_id': community_id,
                    'setting_type': community_setting_types.NSFW_FILTERING
                }

                # Update community settings to keep in sync with configurations
                community_settings_filter = ModelUtilities.get_model_filter(CommunitySettings, filter_dict).first()

                if community_settings_filter and community_settings_filter.enabled != update_values.get('enabled'):
                    community_settings_filter.enabled = update_values.get('enabled')
                    community_settings_filter.enabled_by_id = user_id if update_values.get('enabled') else None
                    community_settings_filter.save()
                        
            if update_values.get('cutoff_score') and isinstance(update_values.get('cutoff_score'), float):
                configuration_value['cutoff_score'] = update_values.get('cutoff_score')
                record_updated = True

            if update_values.get('inferdo_api_key') and isinstance(update_values.get('inferdo_api_key'), str):
                configuration_value['inferdo_api_key'] = update_values.get('inferdo_api_key')
                record_updated = True

        elif configuration_type == WIDGETS_METADATA_CONFIGURATION:

            if (update_values.get('message') is not None) and isinstance(update_values.get(
                    'message'), bool):
                configuration_value['message'] = update_values.get('message')
                record_updated = True

        elif configuration_type == GUEST_FLOW_METADATA_CONFIGURATION:
            filter_dict = {
                'community': community_id,
                'setting_type': community_setting_types.ENABLE_GUEST_FLOW
            }

            community_setting_instance = ModelUtilities.get_model_filter(CommunitySettings, filter_dict).first()

            if community_setting_instance and community_setting_instance.enabled:

                if update_values.get('guest_users') and isinstance(update_values.get('guest_users'), str) and (
                        update_values.get('guest_users') in [GuestFlowUserTypes.SINGLE.value,
                                                             GuestFlowUserTypes.MULTIPLE.value]):
                    configuration_value['guest_users'] = update_values.get('guest_users')
                    record_updated = True

        elif configuration_type == FEED_SETTINGS_CONFIGURATION:

            if update_values.get('create_feed_poll') and isinstance(update_values.get('create_feed_poll'), str) and (
                update_values.get('create_feed_poll') in CREATE_FEED_POLL_COMMUNITY_VALUES):

                # if create_feed_poll value is updated, update rights for all members & managers in the community
                if configuration_value['create_feed_poll'] != update_values.get('create_feed_poll'):

                    configuration_value['create_feed_poll'] = update_values.get('create_feed_poll')
                    
                    # Update rights for all members & managers in the community
                    CommunityHelper.update_create_feed_poll_settings_for_community.delay(community_id, user_id, update_values.get('create_feed_poll'))

                    record_updated = True
                    
            if update_values.get('menu_items_config') and isinstance(update_values.get('menu_items_config'), dict):
                
                if not (configuration_value.get('menu_items_config') or isinstance(configuration_value.get('menu_items_config'), dict)):
                    configuration_value['menu_items_config'] = {}
                    
                if update_values.get('menu_items_config').get('hide_post') is not None and isinstance(
                    update_values.get('menu_items_config').get('hide_post'), bool):
                    
                    configuration_value['menu_items_config']['hide_post'] = update_values.get('menu_items_config').get('hide_post')
                    record_updated = True
                
        elif configuration_type == PERSONALISED_FEED_WEIGHTS:
            filter_dict = {
                'community': community_id,
                'setting_type': community_setting_types.ENABLE_PERSONALISED_FEED
            }

            community_setting_instance = ModelUtilities.get_model_filter(CommunitySettings, filter_dict).first()

            if community_setting_instance and community_setting_instance.enabled:
                configuration_value = {**COMMUNITY_CONFIGURATIONS[PERSONALISED_FEED_WEIGHTS].get('value'),
                                       **configuration_value}

                if update_values.get('recency_metrics') and isinstance(update_values.get('recency_metrics'), dict) and \
                        (update_values.get('recency_metrics').get('weight') is not None) and \
                        type(update_values.get('recency_metrics').get('weight')) in [int, float]:
                    configuration_value['recency_metrics']['weight'] = update_values.get('recency_metrics').get('weight')
                    record_updated = True

                if update_values.get('recency_metrics') and isinstance(update_values.get('recency_metrics'), dict) and \
                        (update_values.get('recency_metrics').get('max_threshold') is not None) and \
                        type(update_values.get('recency_metrics').get('max_threshold')) in [int, float]:
                    configuration_value['recency_metrics']['max_threshold'] = \
                        update_values.get('recency_metrics').get('max_threshold')
                    record_updated = True

                if update_values.get('likes_metrics') and isinstance(update_values.get('likes_metrics'), dict) and \
                        (update_values.get('likes_metrics').get('weight') is not None) and \
                        type(update_values.get('likes_metrics').get('weight')) in [int, float]:
                    configuration_value['likes_metrics']['weight'] = update_values.get('likes_metrics').get('weight')
                    record_updated = True

                if update_values.get('likes_metrics') and isinstance(update_values.get('likes_metrics'), dict) and \
                        (update_values.get('likes_metrics').get('max_threshold') is not None) and \
                        type(update_values.get('likes_metrics').get('max_threshold')) in [int, float]:
                    configuration_value['likes_metrics']['max_threshold'] = \
                        update_values.get('likes_metrics').get('max_threshold')
                    record_updated = True

                if update_values.get('comments_metrics') and isinstance(update_values.get('comments_metrics'), dict) and \
                        (update_values.get('comments_metrics').get('weight') is not None) and \
                        type(update_values.get('comments_metrics').get('weight')) in [int, float]:
                    configuration_value['comments_metrics']['weight'] = update_values.get('comments_metrics').get('weight')
                    record_updated = True

                if update_values.get('comments_metrics') and isinstance(update_values.get('comments_metrics'), dict) and \
                        (update_values.get('comments_metrics').get('max_threshold') is not None) and \
                        type(update_values.get('comments_metrics').get('max_threshold')) in [int, float]:
                    configuration_value['comments_metrics']['max_threshold'] = \
                        update_values.get('comments_metrics').get('max_threshold')
                    record_updated = True

                if update_values.get('user_groups_metrics') and isinstance(update_values.get('user_groups_metrics'), dict) \
                        and (update_values.get('user_groups_metrics').get('weight') is not None) and \
                        type(update_values.get('user_groups_metrics').get('weight')) in [int, float]:
                    configuration_value['user_groups_metrics']['weight'] = \
                        update_values.get('user_groups_metrics').get('weight')
                    record_updated = True

                if update_values.get('user_groups_metrics') and isinstance(update_values.get('user_groups_metrics'), dict) \
                        and (update_values.get('user_groups_metrics').get('max_threshold') is not None) and \
                        type(update_values.get('user_groups_metrics').get('max_threshold')) in [int, float]:
                    configuration_value['user_groups_metrics']['max_threshold'] = \
                        update_values.get('user_groups_metrics').get('max_threshold')
                    record_updated = True

                if update_values.get('user_topics_metrics') and isinstance(update_values.get('user_topics_metrics'), dict) \
                        and (update_values.get('user_topics_metrics').get('weight') is not None) and \
                        type(update_values.get('user_topics_metrics').get('weight')) in [int, float]:
                    configuration_value['user_topics_metrics']['weight'] = \
                        update_values.get('user_topics_metrics').get('weight')
                    record_updated = True

                if update_values.get('user_topics_metrics') and isinstance(update_values.get('user_topics_metrics'), dict) \
                        and (update_values.get('user_topics_metrics').get('max_threshold') is not None) and \
                        type(update_values.get('user_topics_metrics').get('max_threshold')) in [int, float]:
                    configuration_value['user_topics_metrics']['max_threshold'] = \
                        update_values.get('user_topics_metrics').get('max_threshold')
                    record_updated = True

                if update_values.get('post_dampening_metrics') and isinstance(
                        update_values.get('post_dampening_metrics'), dict) and \
                        (update_values.get('post_dampening_metrics').get('weight') is not None) and \
                        type(update_values.get('post_dampening_metrics').get('weight')) in [int, float]:
                    configuration_value['post_dampening_metrics']['weight'] = \
                        update_values.get('post_dampening_metrics').get('weight')
                    record_updated = True

                if update_values.get('post_dampening_metrics') and isinstance(
                        update_values.get('post_dampening_metrics'), dict) and \
                        (update_values.get('post_dampening_metrics').get('max_threshold') is not None) and \
                        type(update_values.get('post_dampening_metrics').get('max_threshold')) in [int, float]:
                    configuration_value['post_dampening_metrics']['max_threshold'] = \
                        update_values.get('post_dampening_metrics').get('max_threshold')
                    record_updated = True

                if update_values.get('user_connection_metrics') and isinstance(
                        update_values.get('user_connection_metrics'), dict) and \
                        (update_values.get('user_connection_metrics').get('weight') is not None) and \
                        type(update_values.get('user_connection_metrics').get('weight')) in [int, float]:

                    configuration_value['user_connection_metrics']['weight'] = \
                        update_values.get('user_connection_metrics').get('weight')
                    record_updated = True

                if update_values.get('user_connection_metrics') and isinstance(
                        update_values.get('user_connection_metrics'), dict) and \
                        (update_values.get('user_connection_metrics').get('max_threshold') is not None) and \
                        type(update_values.get('user_connection_metrics').get('max_threshold')) in [int, float]:
                    configuration_value['user_connection_metrics']['max_threshold'] = \
                        update_values.get('user_connection_metrics').get('max_threshold')
                    record_updated = True

        elif configuration_type == CHATBOT_CONFIGURATIONS:
                
            if update_values.get('enabled') and isinstance(update_values.get('enabled'), bool):
                configuration_value['enabled'] = update_values.get('enabled')
                record_updated = True

            if update_values.get('provider') and isinstance(update_values.get('provider'), str) and (
                update_values.get('provider').strip() == CHATBOT_PROVIDER_OPENAI):

                configuration_value['provider'] = update_values.get('provider')
                record_updated = True

            if update_values.get('api_key') and isinstance(update_values.get('api_key'), str):
                configuration_value['api_key'] = update_values.get('api_key')
                record_updated = True

        # Update configuration instance if record is updated
        if record_updated:
            configuration_instance.value = configuration_value
            configuration_instance.save()

            # Call SWARM api to delete cache key to update configurations
            if configuration_type in [FEED_METADATA_CONFIGURATION, NSFW_FILTERING_CONFIGURATION,
                                      PERSONALISED_FEED_WEIGHTS, FEED_SETTINGS_CONFIGURATION]:
                InternalServiceUtilities.delete_cache_from_swarm_service.delay(
                    community_id=community_id, user_id=user_id, 
                    cache_key=(SWARM_CACHE_KEY_CONFIGURATIONS % str(community_id)))

            # Call Kettle api to delete cache key for profile metadata
            if configuration_type in [PROFILE_METADATA_CONFIGURATION]:
                InternalServiceUtilities.delete_cache_from_kettle_service.delay(
                    community_id=community_id, user_id=user_id,
                    key_patterns=[KETTLE_CACHE_KEY_PROFILE_META_CONFIGURATIONS.format(community_id)]
                )
                
            if configuration_type in [FEED_METADATA_CONFIGURATION]:
                # Delete kettle feed_metadata cache corresponding to anonymous user
                InternalServiceUtilities.delete_cache_from_kettle_service.delay(
                    community_id=community_id, user_id=user_id,
                    key_patterns=[KETTLE_CACHE_KEY_FEED_META_CONFIGURATIONS.format(community_id)])

            # Delete cache key for widget configurations
            if configuration_type in [WIDGETS_METADATA_CONFIGURATION]:
                cache_key = WIDGET_CONFIGURATIONS_CACHE_KEY.format(community_id)
                CacheImpl.delete_key(cache_key)

        return record_updated, configuration_instance
    
    @staticmethod
    def validate_inferdo_api_key_for_nsfw_filtering(api_key:str, community_instance, user_instance) -> dict:
        
        if not (api_key and community_instance and user_instance):
            return ResponseUtilities.get_inner_error_context("Invalid request body")
        
        try:    

            client = ApiClient()
            client.update_request_url(INFERDO_NSFW_FILTER_ENDPOINT)

            # Add headers
            client.update_headers({
                'X-RapidAPI-Key': api_key,
                'x-RapidAPI-Host': INFERDO_HEADER_API_HOST
            })

            # Add request body
            client.update_body({
                "url": INFERDO_SAMPLE_NSFW_IMAGE_URL
            })

            # Send POST request
            response = client.post().response

            if response.status_code != 200:
                error_logger.error(f"Error occured setting up Inferdo's API Key for community - {community_instance.id} \
                                   -  {community_instance.name} | StatusCode: {response.status_code} , Response: {response.json()}")
                return ResponseUtilities.get_inner_error_context(f"Error occured setting up Inferdo's API Key: {response.json()}")

            return {'success': True}
        
        except Exception as e:
            error_logger.error(f"Exception occurred while setting up Inferdo's API Key for community - {community_instance.id} -  {community_instance.name} | Error: {e.args}")
            return ResponseUtilities.get_inner_error_context(f"Some error occured setting up Inferdo's API Key, please contact support")
        
    @staticmethod
    @shared_task    
    def close_under_review_pending_post_reports(community_id: int, user_id: int, report_ids: list, status: str):

        if not ReportClosingStatus.is_valid_status(status):
            return
        
        action_taken = report_action_types.PENDING_POST_APPROVED \
            if status == ReportClosingStatus.STATUS_APPROVED.value else report_action_types.PENDING_POST_REJECTED
        sdk_client_instance = ModelUtilities.get_model_filter(SdkClient, {'community_id': community_id}).first()
        user_instance = ModelUtilities.get_user_instance_or_none(user_id, community_id)
        report_instances = ModelUtilities.get_model_filter(Report, {'id__in': report_ids})

        if not (sdk_client_instance and user_instance and report_instances):
            info_logger.info(f"Missing params: sdk_client_instance: {sdk_client_instance}, "
                             f"user_instance: {user_instance}, report_instances: {report_instances}")
            return
        
        # For each report, approve or reject the pending post in swarm service and close the report
        for report in report_instances:

            pending_post_id = report.entity_id
            response = InternalServiceUtilities.approve_or_reject_pending_post_in_swarm_service(
                sdk_client_instance.api_key, user_instance.userinfo.user_unique_id, pending_post_id, status)
            
            # If there was an error from swarm service log the error and continue
            if response.get('error_message'):
                error_logger.error(f"Error occurred while approving/rejecting pending post: {pending_post_id} for report: {report.id} - {response.get('error_message')}")
                continue

            # Close the report if the pending post was approved or rejected successfully
            report.is_closed = True
            report.closed_by = user_instance
            report.action_taken = action_taken
            report.save()

            info_logger.info(f"Successfully approved/rejected {pending_post_id} pending post for report: {report.id}")

        return
    
    @staticmethod
    def delete_user_meta_cache_for_users_with_question(question_id: int, community_id: int):

        if not (question_id and community_id):
            return

        # Fetch question answers
        user_answer_instances = ModelUtilities.get_model_filter(communityAnswers, 
                                                   {'question_id': question_id, 
                                                    'community_id': community_id}
                                                    )

        for user_answer_instance in user_answer_instances:
            user_instance = user_answer_instance.member
            cache_key = KETTLE_CACHE_KEY_USER_META.format(community_id, user_instance.userinfo.user_unique_id)
            InternalServiceUtilities.delete_cache_from_kettle_service.delay(
                community_id=community_id, user_id=user_instance.id, key_patterns=[cache_key]
            )
    
    @staticmethod
    def create_community_billing_date_for_mau_tracking(community_id: int):
        """
        Create a billing date for the community for MAU tracking for chat and feed
        """

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return
        
        for sdk_source in VersionUtilities.SdkSource.get_all_sdk_source_list():

            ModelUtilities.update_or_create_model(CommunityBillingDates, {'community': community_instance, 
                                                                          'sdk': sdk_source, 
                                                                          'start_date': 1
                                                                          }, {})
        
            info_logger.info(f"Successfully added billing date for community {community_id} for MAU tracking for {sdk_source}")

        return
    
    @staticmethod
    @shared_task
    def update_create_feed_poll_settings_for_community(community_id: int, user_id: int, create_feed_poll: str):

        info_logger.info(f"Updating create_feed_poll settings for community {community_id} to {create_feed_poll}")

        if not (community_id and user_id and create_feed_poll):
            info_logger.info(f"Missing params: community_id: {community_id}, user_id: {user_id}, create_feed_poll: {create_feed_poll}")
            return
        
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not (community_instance and user_instance):
            info_logger.info(f"Community/User instance not found: community_id: {community_id}, user_id: {user_id}")
            return
        
        member_right = ModelUtilities.get_model_filter(memberRights, {'state': member_rights.MEMBER_RIGHT_CREATE_FEED_POLL}).first()
        admin_right = ModelUtilities.get_model_filter(adminRights, {'state': manager_rights.MANAGER_RIGHT_CREATE_FEED_POLL}).first()
        
        if not (member_right and admin_right):
            info_logger.info(f"Member/Manager right not found: community_id: {community_id}")
            return

        if create_feed_poll == 'everyone':
            CommunityHelper.update_create_feed_poll_settings_to_everyone(community_instance, member_right, admin_right)

        elif create_feed_poll == 'only_cm':
            CommunityHelper.update_create_feed_poll_settings_to_only_cm(community_instance, member_right, admin_right)

        elif create_feed_poll == 'no_one':
            CommunityHelper.update_create_feed_poll_settings_to_no_one(community_instance, member_right, admin_right)

        else:
            info_logger.info(f"Invalid create_feed_poll value: {create_feed_poll}")
        
        return

    @staticmethod
    def update_create_feed_poll_settings_to_everyone(community_instance, member_right, admin_right):

        
        # Add create_feed_poll right to default community rights settings
        ModelUtilities.update_or_create_model(communityRightsSettings, {'community': community_instance,
                                                                        'right': member_right}, {})
        
        # For each member in the community, add create_feed_poll right
        member_instances = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                     'state': member_states.MEMBER})

        existing_member_rights = ModelUtilities.get_model_filter(userMemberRights, {'community': community_instance,
                                                                                    'right': member_right}
                                                                                    ).values('user')

        remaining_member_rights = member_instances.exclude(member_id__in=existing_member_rights)
        
        bulk_user_member_right_instances =[]
        
        for member_instance in remaining_member_rights:
            bulk_user_member_right_instances.append(userMemberRights(user=member_instance.member_id,
                                                                     community=community_instance,
                                                                     right=member_right))

        ModelUtilities.bulk_create_instances(userMemberRights, bulk_user_member_right_instances)
            
        # For each manager in the community, add create_feed_poll right
        manager_instances = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                      'state': member_states.ADMIN})

        existing_manager_rights = ModelUtilities.get_model_filter(userAdminRights, {'community': community_instance,
                                                                                    'right': admin_right}
                                                                                    ).values('user')
        
        remaining_manager_rights = manager_instances.exclude(member_id__in=existing_manager_rights)
        
        bulk_user_admin_right_instances = []
        
        for manager_instance in remaining_manager_rights:
            bulk_user_admin_right_instances.append(userAdminRights(user=manager_instance.member_id,
                                                                   community=community_instance,
                                                                   right=admin_right))

        ModelUtilities.bulk_create_instances(userAdminRights, bulk_user_admin_right_instances)
            
        info_logger.info(f"Successfully updated create_feed_poll to 'everyone' for community {community_instance.id}")

    @staticmethod
    def update_create_feed_poll_settings_to_only_cm(community_instance, member_right, admin_right):

        # Remove create_feed_poll right from default community rights settings
        ModelUtilities.delete_record_in_model(communityRightsSettings, {'community': community_instance,
                                                                        'right': member_right})

        # For each member in the community, remove create_feed_poll right
        member_instances = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                     'state': member_states.MEMBER}
                                                                     ).values('member_id')

        ModelUtilities.delete_record_in_model(userMemberRights, {'community': community_instance,
                                                                 'right': member_right,
                                                                 'user__in': member_instances})
            
        # For each manager in the community, add create_feed_poll right
        manager_instances = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                      'state': member_states.ADMIN})

        existing_manager_rights = ModelUtilities.get_model_filter(userAdminRights, {'community': community_instance,
                                                                                    'right': admin_right}
                                                                                    ).values('user')
        
        remaining_manager_rights = manager_instances.exclude(member_id__in=existing_manager_rights)
        
        bulk_user_admin_right_instances = []
        
        for manager_instance in remaining_manager_rights:
            bulk_user_admin_right_instances.append(userAdminRights(user=manager_instance.member_id,
                                                                   community=community_instance,
                                                                   right=admin_right))
        
        ModelUtilities.bulk_create_instances(userAdminRights, bulk_user_admin_right_instances)
            
        info_logger.info(f"Successfully updated create_feed_poll to 'only_cm' for community {community_instance.id}")

    @staticmethod
    def update_create_feed_poll_settings_to_no_one(community_instance, member_right, admin_right): 
        
        # Remove create_feed_poll right from default community rights settings
        ModelUtilities.delete_record_in_model(communityRightsSettings, {'community': community_instance,
                                                                        'right': member_right})
        
        # For each member in the community, remove create_feed_poll right
        member_instances = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                     'state': member_states.MEMBER}
                                                                     ).values('member_id')

        ModelUtilities.delete_record_in_model(userMemberRights, {'community': community_instance,
                                                                 'right': member_right,
                                                                 'user__in': member_instances})

        # For each manager in the community, remove create_feed_poll right
        manager_instances = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                     'state': member_states.ADMIN,
                                                                     'is_owner': False}
                                                                     ).values('member_id')

        ModelUtilities.delete_record_in_model(userAdminRights, {'community': community_instance,
                                                                'right': admin_right,
                                                                'user__in': manager_instances})
            
        info_logger.info(f"Successfully updated create_feed_poll to 'no_one' for community {community_instance.id}")

    @staticmethod
    def validate_fetch_chatbots_request(user_id:int, api_key: str) -> dict:

        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id
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
    
    @staticmethod
    def validate_create_chatbot_request(user_id: int, api_key: str, req_body: dict) -> dict:

        if not req_body:
            return ResponseUtilities.get_inner_error_context("Invalid request body")
        
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)
        if validated_dict.get('error_message'):
            return validated_dict

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')

        # Validate if user is admin or not
        if not Members.is_member_community_promoter(community_instance, user_instance):
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this operation")
        
        # Validate configurations for chatbot
        configurations = CommunityHelper.fetch_or_return_default_community_configurations(community_instance, 
                                                                                          [CHATBOT_CONFIGURATIONS])
        if not configurations:
            return ResponseUtilities.get_inner_error_context("Community configurations not found")
        
        chatbot_configurations = configurations[0].get('value')

        if not chatbot_configurations.get('enabled'):
            return ResponseUtilities.get_inner_error_context("Chatbot is not enabled for this community")

        if not (chatbot_configurations.get('provider') and chatbot_configurations.get('api_key')):
            return ResponseUtilities.get_inner_error_context("Please set chatbot configurations first")

        if req_body.get('uuid'):
            user_instance = ModelUtilities.get_user_instance_or_none_from_uuid(req_body.get('uuid'), 
                                                                               community_instance.id)
            if user_instance:
                return ResponseUtilities.get_inner_error_context("Chatbot already exists against this uuid.")

        
        # Validation for required req body values
        if not req_body.get('name'):
            return ResponseUtilities.get_inner_error_context("Please send name in request body")
        
        chatbot_meta = req_body.get('chatbot_meta', {})

        if not (chatbot_meta and isinstance(chatbot_meta, dict)):
            return ResponseUtilities.get_inner_error_context("Please send chatbot_meta in request body")

        provider = chatbot_meta.get('provider')
        provider_meta = chatbot_meta.get('provider_meta')
        default_text = chatbot_meta.get('default_text')
        
        if default_text and not isinstance(default_text, str):
            return ResponseUtilities.get_inner_error_context("Invalid default_text value. Please send string")

        if not ((provider and isinstance(provider, str)) or (provider_meta and isinstance(provider_meta, dict))):
            return ResponseUtilities.get_inner_error_context("Please send provider and provider_meta in chatbot_meta")
        
        if not provider == CHATBOT_PROVIDER_OPENAI:
            return ResponseUtilities.get_inner_error_context(f"Invalid provider value. Supported values - '{CHATBOT_PROVIDER_OPENAI}'")
        
        if not (provider_meta.get('assistant_id') and isinstance(provider_meta.get('assistant_id'), str)):
            return ResponseUtilities.get_inner_error_context("Please send assistant_id in provider_meta")

        # Validate open ai assistant_id
        validated_request = OpenAiWrapper(chatbot_configurations.get('api_key')
                                          ).validate_open_ai_api_key_or_assistant(provider_meta.get('assistant_id'))
        if validated_request.get('error_message'):
            return validated_request
        
        # Validation for optional Values
        if provider_meta.get('thread_context'):
            if not isinstance(provider_meta.get('thread_context'), int):
                return ResponseUtilities.get_inner_error_context("Invalid thread_context value. Please send integer in seconds")
        else:
            provider_meta['thread_context'] = CHATBOT_DEFAULT_THREAD_CONTEXT
        
        if provider_meta.get('max_prompt_tokens') and not isinstance(provider_meta.get('max_prompt_tokens'), int):
            return ResponseUtilities.get_inner_error_context("Invalid max_prompt_tokens value.")

        if provider_meta.get('max_completion_tokens') and not isinstance(provider_meta.get('max_completion_tokens'), int):
            return ResponseUtilities.get_inner_error_context("Invalid max_completion_tokens value.")
        
        if provider_meta.get('vision_model') and not isinstance(provider_meta.get('vision_model'), str):
            return ResponseUtilities.get_inner_error_context("Invalid vision_model value. Please send string")
        
        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
        }
    
    @staticmethod
    def validate_update_chatbot_request(user_id: int, api_key: str, req_body: dict) -> dict:

        if not req_body:
            return ResponseUtilities.get_inner_error_context("Invalid request body")
        
        if not req_body.get('chatbot_uuid'):
            return ResponseUtilities.get_inner_error_context("Please send chatbot_uuid")
        
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)
        if validated_dict.get('error_message'):
            return validated_dict

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')

        # Validate if user is admin or not
        if not Members.is_member_community_promoter(community_instance, user_instance):
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this operation")

        user_ids = ModelUtilities.get_valid_user_ids_from_uuids([req_body.get('chatbot_uuid')], community_instance.id)
        if not user_ids:
            return ResponseUtilities.get_inner_error_context("Invalid chatbot_uuid")
        
        # Validate configurations for chatbot
        configurations = CommunityHelper.fetch_or_return_default_community_configurations(community_instance, 
                                                                                          [CHATBOT_CONFIGURATIONS])
        if not configurations:
            return ResponseUtilities.get_inner_error_context("Community configurations not found")
        
        chatbot_configurations = configurations[0].get('value')

        if not chatbot_configurations.get('enabled'):
            return ResponseUtilities.get_inner_error_context("Chatbot is not enabled for this community")

        if not (chatbot_configurations.get('provider') and chatbot_configurations.get('api_key')):
            return ResponseUtilities.get_inner_error_context("Please set chatbot configurations first")
        
        chatbot_meta_instance = ModelUtilities.get_model_filter(ChatbotMeta, {'community_id': community_instance,
                                                                              'user_id': user_ids[0]}).first()
        if not chatbot_meta_instance:
            return ResponseUtilities.get_inner_erwror_context("Chatbot not found against uuid")
        
        chatbot_meta = req_body.get('chatbot_meta', {})

        provider = chatbot_meta.get('provider', "")
        provider_meta = chatbot_meta.get('provider_meta', {})
        
        if provider and provider != CHATBOT_PROVIDER_OPENAI:
            return ResponseUtilities.get_inner_error_context(f"Invalid provider value. Supported values - '{CHATBOT_PROVIDER_OPENAI}'")

        if provider_meta and provider_meta.get('assistant_id'):
            if not isinstance(provider_meta.get('assistant_id'), str):
                return ResponseUtilities.get_inner_error_context("Please send valid assistant_id in provider_meta")
            

            validated_request = OpenAiWrapper(chatbot_configurations.get('api_key')
                                              ).validate_open_ai_api_key_or_assistant(provider_meta.get('assistant_id'))
            if validated_request.get('error_message'):
                return validated_request
        
        if provider_meta and provider_meta.get('thread_context') and not isinstance(provider_meta.get('thread_context'), int):
            return ResponseUtilities.get_inner_error_context("Invalid thread_context value. Please send integer in seconds")
        
        if provider_meta and provider_meta.get('max_prompt_tokens') and not isinstance(provider_meta.get('max_prompt_tokens'), int):
            return ResponseUtilities.get_inner_error_context("Invalid max_prompt_tokens value.")

        if provider_meta and provider_meta.get('max_completion_tokens') and not isinstance(provider_meta.get('max_completion_tokens'), int):
            return ResponseUtilities.get_inner_error_context("Invalid max_completion_tokens value.")
        
        if provider_meta and provider_meta.get('vision_model') and not isinstance(provider_meta.get('vision_model'), str):
            return ResponseUtilities.get_inner_error_context("Invalid vision_model value. Please send string")
        
        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'chatbot_meta_instance': chatbot_meta_instance,
            'chatbot_user_instance': chatbot_meta_instance.user,
        }

    @staticmethod
    def validate_fetch_community_integration_request(api_key: str) -> dict:

        validation_params = {
            'community_id': {
                'api_key': api_key
            }
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        community_instance = validated_dict.get('community_id')

        return {
            'community_instance': community_instance
        }

    @staticmethod
    def validate_update_community_integration_request(api_key: str, status_type: str, status: bool,
                                                      is_internal: bool) -> dict:

        validation_params = {
            'community_id': {
                'api_key': api_key
            }
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        if isinstance(status_type, str) and status_type in CommunityIntegrationStatusTypes.get_choices_list() and \
                not is_internal:
            return ResponseUtilities.get_inner_error_context("You cannot update the reserved state.")

        if not (isinstance(status_type, str) and status_type):
            return ResponseUtilities.get_inner_error_context("Invalid status type")

        if not isinstance(status, bool):
            return ResponseUtilities.get_inner_error_context("Invalid status value")

        return {
            "community_instance": validated_dict.get('community_id')
        }

    @staticmethod
    def fetch_or_return_default_community_integration_status(community_instance) -> dict:
        # fetch community integration from db
        community_integration_instances = ModelUtilities.get_model_filter(
            CommunityIntegrationStatus, {'community': community_instance})

        # key value pair of status_type -> integration instance
        integration_instances_response = {instance.status_type: instance for instance in
                                          community_integration_instances}

        # Add default integrations if not present
        for status_type in CommunityIntegrationStatusTypes.get_choices_list():

            if status_type not in integration_instances_response:
                instance = CommunityIntegrationStatus(community=community_instance,
                                                      status_type=status_type,
                                                      status=False)
                integration_instances_response[status_type] = instance

        # serialize community integrations
        serialised_community_integrations = CommunityIntegrationStatusSerializer(
            integration_instances_response.values(), many=True).data

        return serialised_community_integrations
