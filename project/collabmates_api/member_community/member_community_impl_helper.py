import uuid
from django.contrib.auth.models import User
from django.db.models import When, Case
from django.conf import settings
from rest_framework import status as status_codes
from rest_framework.utils import json
from celery import shared_task

from utility.time_utilities import TimeUtilities
from utility.number_utilities import NumberUtilities
from utility.response_utilities import ResponseUtilities
from utility.webhook_utilities import WebhookUtilties
from utility.validation_utilities import ValidationUtilities
from utility.json_utilities import JsonUtilities
from utility.api_client import ApiClient
from utility.constants import (CREATE_INTRO_TEXT_ADMIN)
from utility.cache_keys import (COMMUNITY_PINNED_CHATROOMS_LIST_CACHE_KEY)
from utility.states import (card_types, community_setting_types, member_states, question_states, SyncTypes,
                            member_rights, community_dm_settings_state_types, community_dm_settings_duration_types,
                            conversation_states, DMFabShowList, api_types, get_started_types, click_states,
                            moderation_history_types, access_types, feed_order_types, WebhookTypes,
                            webhook_profile_methods, deleted_members, report_action_types, SyncNotificationTypes,
                            ConnectionRequestActions, ConnectionRequestStatus)
from utility.utils import (get_time_text_for_my_chatrooms)
from utility.celery_tasks import (create_member_dm_chatroom, update_community_pin_chatrooms_list_in_cache,
                                  update_preview_for_account_image_change, update_multiple_previews_in_community)
from togther.models import (collabcardState, ModelUtilities, CommunitySettings, Members, communityAnswers,
                            communityQuestions, Card_Attachment, Collabcard, CommunityDirectMessageSettings,
                            card_answers, Member_Engage, moderationHistory, conversationEngage, SDKClientUsersInfo,
                            Userinfo)
from collabmates_api.search.sync import ElasticSearchSync
from collabmates_api.notification import (send_notification_to_admins)
from collabmates_api.mails import (send_community_hood_waitlist_email_to_pending_member)
from collabmates_api.webhook.constants import(WEBHOOK_SOURCE_CHAT, MAX_WEBHOOK_USERS_META_LIMIT)
from collabmates_api.sdk.models import (SdkClient)
from external_services.caching.cache_impl import CacheImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from external_services.mixpanel.events import MixpanelEvents

from ..community.constants import (ANSWER_PRIVACY_PUBLIC_VALUE, ANSWER_PRIVACY_KEY, ANSWER_PRIVACY_PRIVATE_VALUE)
from ..raw_queries import (get_chatroom_count_based_on_community_list,
                           get_count_of_community_members_based_on_community_list,
                           get_card_ids_to_exclude_based_on_cohort_access,
                           check_user_has_member_can_initiate_dm_right,
                           get_chatrooms_of_user_with_follow_status,
                           get_users_sdk_meta_dict)
from ..rest_api import (CommunityAnswersSerializer, CommunityQuestionsSerializerV2, get_error_context,
                        CommunityDMSettingsSerializer)
from ..serializers import (get_chatroom_instance, conversationSerializer, get_members_profile)
from ..static_text import (MEMBER_PROFILE_MENU_ITEMS, IMAGE_URLS_FOR_QUESTION_TITLES,
                           CREATE_COMMUNITY_QUESTION_NAME_TITLE, INVITE_MEMBERS_COMMUNITY_ACTION_TITLE,
                           INVITE_MEMBERS_COMMUNITY_ACTION_ROUTE, MEMBER_REQUEST_TOOL_ROUTE, REPORTS_TOOL_ROUTE,
                           MEMBER_REQUESTS_COMMUNITY_ACTION_TITLE, MEMBER_REQUESTS_COMMUNITY_ACTION_IMAGE_URL,
                           REVIEW_REPORTS_COMMUNITY_ACTION_TITLE, REVIEW_REPORTS_COMMUNITY_ACTION_IMAGE_URL,
                           COMMUNITY_SETTINGS_COMMUNITY_ACTION_TITLE, COMMUNITY_SETTINGS_COMMUNITY_ACTION_IMAGE_URL,
                           INVITE_MEMBERS_COMMUNITY_ACTION_IMAGE_URL, COMMUNITY_SETTINGS_ROUTE)
from ..user_moderation_rights import (check_admin_approve_right, check_admin_delete_right,
                                      check_admin_edit_community_right, check_admin_view_contact_right,
                                      check_admin_add_community_managers_right, get_related_reports_for_user)
from ..views import (generate_internal_link_preview_for_conversation, update_community_get_started,
                     remove_members, check_reports_and_update_action, update_pending_member_count_in_engage,
                     send_sync_notification, save_moderation_history, remove_all_manager_rights,
                     remove_all_member_rights, send_notification_to_managers_when_member_leaves_community)
from ..static_files import (ICONS)
from ..utility import (m2cm_v2_version_check)
from ..upload_attachments import save_chatroom_attachments
from ..sync.model_update import update_models_for_syncing_apis

from .constants import (ACTIVE_USER_LIMIT, MEMBER_COMMUNITY_PROFILE_ROUTE, MEMBER_SINCE_TEXT, PENDING_MEMBER_TEXT,
                        CTA_ROUTE_DIRECT_MESSAGES_MEMBER_PROFILE, CTA_ROUTE_DIRECT_MESSAGES_COMMUNITY_DETAIL_MULTIPLE_CM,
                        CTA_ROUTE_DIRECT_MESSAGES_DM_FEED, CTA_ROUTE_DIRECT_MESSAGES_DM_FEED_V2,
                        SWARM_USER_CONNECTION_UPDATE_ENDPOINT)

error_logger = LoggingWrapper.get_instance()


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
    def extract_member_tagging_data(member_data, sdk_client_info_flag:bool=False) -> []:

        member_list = []

        for key, value in member_data.items():

            temp = dict()
            temp['id'] = value['id']
            temp['name'] = value['name']
            temp['image_url'] = value['image_url']
            temp['user_unique_id'] = value['user_unique_id']
            temp['uuid'] = value['user_unique_id']

            if value.get('is_guest') is not None:
                temp['is_guest'] = value.get('is_guest')

            if value.get('custom_title'):
                temp['custom_title'] = value.get('custom_title')

            if sdk_client_info_flag:
                temp['sdk_client_info'] = value.get('sdk_client_info')

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
                            is_community_answer_data=False, sdk_client_info_flag:bool=False):
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

        if user_instance.userinfo:
            user_data['user_unique_id'] =  user_instance.userinfo.user_unique_id
            user_data['uuid'] = user_data['user_unique_id']

        if sdk_client_info_flag:
            sdk_client_info_dict = get_users_sdk_meta_dict([user_instance.id], only_sdk_client_info=True)
            user_data['sdk_client_info'] = sdk_client_info_dict.get(user_instance.id)

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
    def update_member_profile_menu_for_sdk(user_member_instance, community_instance, current_user_member_instance, menu,
                                           community_hood_check: bool=False):

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

            # community hood check to send edit title option to logged in ADMINS
            if community_hood_check and (current_user_member_instance == user_member_instance):
                allowed_menu_items = [
                    all_menu_items.get("EDIT_TITLE")
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
                               conversation_states_to_consider, rights_list, device_id,
                               sdk_client_info_flag:bool=False):
        chatroom = {}
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)
        card_state_instance = ModelUtilities.get_model_instance_or_none(collabcardState,
                                                                        card_state_map.get(card_id))
        card_answer_instance = ModelUtilities.get_model_instance_or_none(card_answers, card_ans_id)

        if card_instance:
            chatroom['chatroom'] = get_chatroom_instance(card_instance, user_instance.id, send_profile=False,
                                                         sdk_client_info_flag=sdk_client_info_flag)
            chatroom['is_draft'] = False
            chatroom['custom_tag'] = card_instance.custom_tag

        if card_answer_instance:
            last_conversation_dict = conversationSerializer(card_answer_instance,
                                                            current_user_id=user_instance.id, device_id=device_id,
                                                            sdk_client_info_flag=sdk_client_info_flag)
            preview = generate_internal_link_preview_for_conversation(card_answer_instance, user_instance.id)

            if preview:
                last_conversation_dict['preview'] = preview

            chatroom['last_conversation'] = last_conversation_dict

            if card_state_instance.last_seen_conversation_id:
                unseen_filter = {
                    'id__gt': card_state_instance.last_seen_conversation_id,
                    'card_id': card_instance.id,
                    'state__in': conversation_states_to_consider
                }

            else:
                unseen_filter = {
                    'card_id': card_instance.id,
                    'state__in': conversation_states_to_consider
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
                                                                    community_instance.id, send_profile=False,
                                                                    sdk_client_info_flag=sdk_client_info_flag)

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
            return ResponseUtilities.get_impl_error_context('Invalid member_id or uuid',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        member_state = Members.get_community_member_state(community_instance, member_instance)
        user_state = Members.get_community_member_state(community_instance, user_instance)

        is_member_admin = member_state == member_states.ADMIN
        is_user_admin = user_state == member_states.ADMIN

        if any([member_state == member_states.PENDING_MEMBER, user_state == member_states.PENDING_MEMBER]):
            return {'success': True, 'show_dm': False}

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

        user_state = Members.get_community_member_state(community_instance, user_instance)

        if user_state == member_states.PENDING_MEMBER:
            return response_dict

        is_user_admin = user_state == member_states.ADMIN

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
            return ResponseUtilities.get_impl_error_context('Invalid chatroom id!',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

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
    @shared_task
    def trigger_webhook_for_profile_events(community_id: int, member_id: int):

        webhooks = WebhookUtilties.validate_and_fetch_all_webhook_url_and_secret(community_id,
                                                                                 WebhookTypes.PROFILE_CREATED.value)

        if not webhooks:
            return

        # generate payload for profile events
        payload = MemberCommunityHelper.generate_payload_for_profile_webhook_events(member_id)

        if not payload:
            return

        for webhook in webhooks:
            # Generate id for webhook payload
            payload['id'] = str(uuid.uuid4())

            # Send webhook request for all webhook urls
            WebhookUtilties.send_webhook_request_with_payload.delay(url=webhook.get('url'),
                                                                    payload=payload,
                                                                    webhook_type=WebhookTypes.PROFILE_CREATED.value,
                                                                    secret=webhook.get('secret'))

    @staticmethod
    def make_requesting_user_as_member_of_community(user_instance, community_instance, req_body, device_id=None,
                                                    platform=None, version_code=None, trigger_webhook=False):

        from collabmates_api.community.community_impl import CommunityHelper, CommunityImpl
        from collabmates_api.community.constants import (DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY)

        question_answers_list = req_body.get(DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY)

        if question_answers_list:
            CommunityHelper.save_responses_of_member_in_community(user_instance.id,
                                                                  community_instance.id,
                                                                  question_answers_list,
                                                                  True)

        shared_user_instance = ModelUtilities.get_user_instance_or_none(req_body.get('shared_by'),
                                                                        community_instance.id)

        Members.create_instance({'user_instance': user_instance,
                                 'community_instance': community_instance,
                                 'state': member_states.MEMBER,
                                 'image_url': req_body.get('image_url'),
                                 'custom_title': "Member",
                                 'became_member_at': TimeUtilities.current_time_in_sec(),
                                 'joined_by': shared_user_instance
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
                                                                                  user_instance,
                                                                                  trigger_webhook=trigger_webhook)

        shared_user_id = None
        auto_join_code = None

        if shared_user_instance:
            shared_user_id = shared_user_instance.id

        CommunityHelper.set_moderation_rights_and_delete_user_previous_metadata_for_auto_join.delay(
            user_instance.id,
            community_instance.id,
            shared_user_id,
            auto_join_code,
            api_type=api_types.SDK)

        members_count = Members.get_members_count_in_community(community_instance)

        community_impl = CommunityImpl(member_id=user_instance.id, community_id=community_instance.id)
        community_impl.set_members_count_in_community(community_instance.id, members_count)

        create_intro_room_setting_dict = {
            'community': community_instance,
            'setting_type': community_setting_types.CREATE_INTRO_ROOMS
        }

        community_setting_instance = ModelUtilities.get_model_filter(CommunitySettings,
                                                                     create_intro_room_setting_dict).first()

        if community_setting_instance and community_setting_instance.enabled:

            from collabmates_api.views import (post_master_introductions_for_community)

            # Get owner of community
            owner_user_instance = Members.get_community_owner_user_instance_or_none(community_instance)

            # Create MASTER intro room if not available in SDK
            post_master_introductions_for_community(community_instance.id, owner_user_instance.id)

            introduction_answer = CommunityHelper.create_introduction_text_for_intro_chatroom(
                community_instance, user_instance, req_body.get(DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY), True)

            CommunityHelper.add_introductions_room_in_master_intro(community_instance, user_instance,
                                                                   member_states.MEMBER,
                                                                   introduction_answer=introduction_answer)

        else:
            ChatroomHelper.update_seen_status_for_older_chatrooms_for_new_member(community_instance, user_instance,
                                                                                 trigger_webhook=trigger_webhook)

        # Trigger webhook event for profile creation
        if trigger_webhook:
            MemberCommunityHelper.trigger_webhook_for_profile_events.delay(community_id=community_instance.id,
                                                                           member_id=user_instance.id)

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

        from collabmates_api.sync.sync_helper import SyncHelper
        SyncHelper.update_min_timestamp_keys_for_sync_in_cache(user_instance.id, community_instance.id)

    @staticmethod
    def make_requesting_user_as_pending_member_of_community(user_instance, community_instance, req_body):

        from collabmates_api.community.community_impl import CommunityHelper, CommunityImpl
        from collabmates_api.community.constants import (DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY)

        question_answers_list = req_body.get(DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY)

        if question_answers_list:
            CommunityHelper.save_responses_of_member_in_community.delay(user_instance.id,
                                                                        community_instance.id,
                                                                        question_answers_list,
                                                                        True)

        shared_user_instance = ModelUtilities.get_user_instance_or_none(req_body.get('shared_by'),
                                                                        community_instance.id)

        Members.create_instance({'user_instance': user_instance,
                                 'community_instance': community_instance,
                                 'state': member_states.PENDING_MEMBER,
                                 'image_url': req_body.get('image_url'),
                                 'joined_by': shared_user_instance})

        ModelUtilities.update_or_create_model(Member_Engage,
                                              {'member_id': user_instance,
                                               'community_id': community_instance},
                                              {'member_state': member_states.PENDING_MEMBER,
                                               'click_state': click_states.PENDING_APPROVAL,
                                               'order_time': TimeUtilities.current_time_in_milliseconds()})

        CommunityImpl.update_pending_members_after_request_accept_or_reject(community_instance)

        history_type = moderation_history_types.SDK_PENDING_MEMBER

        moderationHistory.create_instance({'user_instance': user_instance,
                                           'community_instance': community_instance,
                                           'type': history_type,
                                           'moderation_by': shared_user_instance})

        send_notification_to_admins.delay(community_instance.id, user_instance.userinfo.name)
        send_community_hood_waitlist_email_to_pending_member.delay(user_instance.id, community_instance.id)

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

        valid_access_types = [access_types.CREATE_POST, access_types.VIEW_POST, access_types.DELETE_POST,
                              access_types.EDIT_POST, access_types.PIN_POST, access_types.LIKE_POST,
                              access_types.SAVE_POST, access_types.CREATE_COMMENT, access_types.VIEW_COMMENT,
                              access_types.DELETE_COMMENT, access_types.EDIT_COMMENT, access_types.LIKE_COMMENT,
                              access_types.CREATE_ACTIVITY, access_types.VIEW_ACTIVITY, access_types.CREATE_TOPIC,
                              access_types.EDIT_TOPIC, access_types.IS_MEMBER, access_types.CHANGE_AUTHOR,
                              access_types.VIEW_USER_ACTIVITY]

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
        state_instance = ModelUtilities.get_model_filter(collabcardState, {'card': chatroom_instance,
                                                                           'user': user_instance,
                                                                           'remove': None,
                                                                           'follow_status': True,
                                                                           'secret_chatroom_left': False}).first()

        if not state_instance:
            return ResponseUtilities.get_inner_error_context('User is not following the chatroom!')

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance,
            'state_instance': state_instance
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

    @staticmethod
    def validate_approve_decline_join_community_request(user_id, api_key: str, uuid: str, is_accepted: bool):
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

        user_member_instance = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                         'member_id': user_instance,
                                                                         'state': member_states.ADMIN}).first()

        if not user_member_instance:
            return ResponseUtilities.get_inner_error_context('You cannot approve or decline the request!')

        member_instance = ModelUtilities.get_user_instance_or_none_from_uuid(uuid, community_instance.id)

        if not member_instance:
            return ResponseUtilities.get_inner_error_context('No user record exists!')

        if not Members.get_community_member_state(community_instance, member_instance) == member_states.PENDING_MEMBER:
            return ResponseUtilities.get_inner_error_context('User is not a pending member!')

        if not isinstance(is_accepted, bool):
            return ResponseUtilities.get_inner_error_context('Invalid is_accepted value type!')

        if is_accepted and Members.is_community_member(community_instance, member_instance):
            return ResponseUtilities.get_inner_error_context('You are already a community member!')

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'member_instance': member_instance,
            'action_required_by_promoter': user_member_instance.actions_required
        }

    @staticmethod
    def approve_user_community_joining_request(user_instance, community_instance, promoter_instance,
                                               platform_code, version_code):
        from collabmates_api.community.community_impl import CommunityImpl, CommunityHelper
        from collabmates_api.cohort.cohort_impl import CohortHelper
        from collabmates_api.chatroom.chatroom_impl import ChatroomHelper

        community_impl = CommunityImpl(member_id=user_instance.id)

        community_impl.approve_community_join_request(community_instance, user_instance, promoter_instance)

        members_count = Members.get_members_count_in_community(community_instance)
        community_impl.set_members_count_in_community(community_instance.id, members_count)

        CommunityHelper.set_follow_status_for_announcement_chatroom_for_community(community_instance,
                                                                                  user_instance)

        create_intro_room_setting_dict = {
            'community': community_instance,
            'setting_type': community_setting_types.CREATE_INTRO_ROOMS
        }

        community_setting_instance = ModelUtilities.get_model_filter(CommunitySettings,
                                                                     create_intro_room_setting_dict).first()

        if community_setting_instance and community_setting_instance.enabled:
            from collabmates_api.views import (post_master_introductions_for_community)

            # Get owner of community
            owner_user_instance = Members.get_community_owner_user_instance_or_none(community_instance)

            # Create MASTER intro room if not available in SDK
            post_master_introductions_for_community(community_instance.id, owner_user_instance.id)

            introduction_answer = CommunityHelper.create_introduction_text_for_intro_chatroom(
                community_instance, user_instance, is_directory_questions_v2=True)

            CommunityHelper.add_introductions_room_in_master_intro(community_instance, user_instance,
                                                                   member_states.MEMBER,
                                                                   introduction_answer=introduction_answer)

        else:
            ChatroomHelper.update_seen_status_for_older_chatrooms_for_new_member(community_instance, user_instance)

        is_m2cm_v2 = m2cm_v2_version_check(platform_code, version_code, is_sdk=True)

        CommunityHelper.run_async_for_community_approve(community_instance, user_instance,
                                                        promoter_instance.userinfo, is_m2cm_v2=is_m2cm_v2,
                                                        is_sdk=True)

        CohortHelper.add_all_member_to_cohort(community_instance.id, [user_instance.id])

        community_impl._send_join_email_to_member(user_instance.id, community_instance.id)

        CohortHelper.add_member_to_respective_question_based_cohorts(member_id=user_instance.id,
                                                                     community_id=community_instance.id)

    @staticmethod
    def reject_user_community_joining_request(user_instance, community_instance, promoter_instance):
        from collabmates_api.community.community_impl import CommunityImpl, CommunityHelper

        community_impl = CommunityImpl(member_id=user_instance.id)

        community_impl._decline_community_join_request(community_instance, user_instance)
        members_count = Members.get_members_count_in_community(community_instance)
        community_impl.set_members_count_in_community(community_instance.id, members_count)

        CommunityHelper.run_async_task_for_community_declined(community_instance, user_instance,
                                                              promoter_instance.userinfo)

        ElasticSearchSync.delete_member_from_community.delay(user_instance.id, community_instance.id)

    @staticmethod
    def add_account_community_actions(community_id):
        invite_members_action = {
            'title': INVITE_MEMBERS_COMMUNITY_ACTION_TITLE,
            'route': INVITE_MEMBERS_COMMUNITY_ACTION_ROUTE.format(community_id),
            'image_url': INVITE_MEMBERS_COMMUNITY_ACTION_IMAGE_URL
        }

        return [invite_members_action]

    @staticmethod
    def add_management_tools_community_actions(user_instance, community_instance):
        management_tools = []

        member_instance = ModelUtilities.get_model_filter(Members, {'member_id': user_instance,
                                                                    'community_id': community_instance}).first()

        if not (member_instance and member_instance.state == member_states.ADMIN):
            return management_tools

        user_id = user_instance.id
        community_id = community_instance.id
        community_name = community_instance.name
        parent_cm_list = []

        if member_instance.parent_cm_list:
            parent_cm_list = JsonUtilities.load_json_data(member_instance.parent_cm_list, default=parent_cm_list)

        has_delete_right = check_admin_delete_right(user=user_id, community=community_id)
        has_member_approve_right = check_admin_approve_right(user=user_id, community=community_id)
        has_community_edit_right = check_admin_edit_community_right(user=user_id, community=community_id)

        if has_member_approve_right:
            # Add new member requests action
            member_request_action = {
                "title": MEMBER_REQUESTS_COMMUNITY_ACTION_TITLE,
                "image_url": MEMBER_REQUESTS_COMMUNITY_ACTION_IMAGE_URL,
                "route": MEMBER_REQUEST_TOOL_ROUTE.format(community_id, community_name),
                "count": Members.get_pending_members(community_instance).count()
            }

            management_tools.append(member_request_action)

        if has_delete_right or has_member_approve_right:
            # Add review reports action
            review_reports_action = {
                "title": REVIEW_REPORTS_COMMUNITY_ACTION_TITLE,
                "image_url": REVIEW_REPORTS_COMMUNITY_ACTION_IMAGE_URL,
                "route": REPORTS_TOOL_ROUTE.format(community_id, community_name),
                "count": get_related_reports_for_user(user_id=user_id, community_id=community_id,
                                                      has_right_0=has_delete_right, is_owner=member_instance.is_owner,
                                                      has_right_1=has_member_approve_right,
                                                      has_right_2=has_community_edit_right,
                                                      parent_cm_list=parent_cm_list, return_reports_count=True)
            }

            management_tools.append(review_reports_action)

            # Add community settings action
            community_settings_action = {
                "title": COMMUNITY_SETTINGS_COMMUNITY_ACTION_TITLE,
                "image_url": COMMUNITY_SETTINGS_COMMUNITY_ACTION_IMAGE_URL,
                "route": COMMUNITY_SETTINGS_ROUTE.format(community_id, community_name)
            }

            management_tools.append(community_settings_action)

        return management_tools

    @staticmethod
    def validate_fetch_pending_members_request(member_id, api_key):

        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': member_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        user_instance = validated_dict.get('user_id')
        community_instance = validated_dict.get('community_id')

        # check if user has member approve/remove right
        if not check_admin_approve_right(user=user_instance.id, community=community_instance.id):
            return ResponseUtilities.get_inner_error_context("You are not authorized to perform this action!")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance
        }

    @staticmethod
    def get_users_payload_for_webhook_events(user_ids: list) -> list:

        if not user_ids or not isinstance(user_ids, list):
            return []

        # Truncate users list to MAX_WEBHOOK_USERS_LIMIT
        truncated_list = user_ids[:MAX_WEBHOOK_USERS_META_LIMIT]
        users_meta = get_users_sdk_meta_dict(truncated_list)
        users_payload = []

        for key, user_meta in users_meta.items():

            user = {
                "id": user_meta.get('id'),
                "custom_title": user_meta.get('custom_title'),
                "image_url": user_meta.get('image_url'),
                "is_guest": user_meta.get('is_guest'),
                "name": user_meta.get('name'),
                "sdk_client_info": {
                    "community": user_meta.get('sdk_client_info').get('community') if user_meta.get('sdk_client_info') else None,
                    "uuid": user_meta.get('sdk_client_info').get('user_unique_id') if user_meta.get('sdk_client_info') else None
                },
                "uuid": user_meta.get('user_unique_id'),
            }

            users_payload.append(user)

        return users_payload

    @staticmethod
    def generate_payload_for_profile_webhook_events(user_id) -> dict:

        if not user_id:
            return {}

        users_data = MemberCommunityHelper.get_users_payload_for_webhook_events([user_id])

        if not users_data:
            return {}

        payload = {
            "id": str(uuid.uuid4()),
            "event": WebhookTypes.PROFILE_CREATED.value,
            "source": WEBHOOK_SOURCE_CHAT,
            "created_at": TimeUtilities.current_time_in_sec(),
            "data": {
                "user":  users_data[0],
                "creation_method": webhook_profile_methods.COMMUNITY_JOIN
            }
        }

        return payload

    @staticmethod
    def validate_self_leave_community_request(user_id, api_key):

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

        member_instance = Members.get_member_instance_or_none(community_instance, user_instance)

        if not member_instance:
            return ResponseUtilities.get_inner_error_context("You are not a member of this community")

        if member_instance.state == member_states.ADMIN:
            return ResponseUtilities.get_inner_error_context("You are an admin of this community. You can be removed by other admins")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'member_instance': member_instance
        }

    @staticmethod
    def leave_community_for_pending_member(community_instance, member_instance, user_instance) -> bool:

        if not (community_instance and user_instance and member_instance):
            return False

        if not (member_instance.state == member_states.PENDING_MEMBER):
            return False

        try:

            remove_members(community_instance, user_instance, removed_state=deleted_members.LEFT,
                            current_user_instance=user_instance)

            check_reports_and_update_action.delay(action_taken_by=user_instance.id,
                                                  action_taken=report_action_types.LEFT_THE_COMMUNITY,
                                                  user=user_instance.id, community=community_instance.id)

            update_pending_member_count_in_engage(community_instance)

            send_sync_notification.delay({'community_id': community_instance.id,
                                            'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

            update_multiple_previews_in_community.delay({'community_id': community_instance.id})

            return True

        except Exception as e:
            error_logger.error(f"Error in leave_community_for_pending_member for user_id {user_instance.id}: {e.args}")
            return False

    @staticmethod
    def leave_community_for_member_and_profile_unavailable(community_instance, member_instance, user_instance) -> bool:

        if not (community_instance and user_instance and member_instance):
            return False

        if not (member_instance.state in [member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]):
            return False

        try:
            user_id = user_instance.id
            community_id = community_instance.id

            remove_members(community_instance, user_instance, removed_state=deleted_members.LEFT,
                            current_user_instance=user_instance)

            save_moderation_history(user=user_instance, community=community_instance,
                                    moderation_by=user_instance,
                                    type=moderation_history_types.LEFT_COMMUNITY)

            check_reports_and_update_action.delay(action_taken_by=user_id,
                                                  action_taken=report_action_types.LEFT_THE_COMMUNITY,
                                                  user=user_id, community=community_id)

            remove_all_member_rights(community_instance, user_instance)
            remove_all_manager_rights(community_instance, user_instance)

            from collabmates_api.cohort.cohort_impl import CohortHelper
            CohortHelper.fetch_user_cohorts_having_filters_with_community_id(community_id, user_instance)

            send_sync_notification.delay({'community_id': community_id,
                                        'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

            send_notification_to_managers_when_member_leaves_community.delay(user_id, community_id)

            ElasticSearchSync.delete_chatrooms_for_removed_member.delay(community_id, user_id)
            MixpanelEvents.leave_community.delay(user_id, community_id)

            # Send delete request to swarm service to delete feed data
            from collabmates_api.community.community_impl import CommunityHelper

            CommunityHelper.remove_users_feed_data.delay(community_instance.id, user_instance.id,
                                                         [user_instance.userinfo.user_unique_id], False)

            return True

        except Exception as e:
            error_logger.error(f"Error in leave_community_for_member_and_unavailable for user_id {user_instance.id}: {e.args}")
            return False

    @staticmethod
    def update_widget_id_for_user(user_id: int, widget_id: str) -> bool:
        """
            Updates widget_id in sdk_client_info for user
        """

        if not (user_id and widget_id):
            return False

        try:
            sdk_client_info_instance = ModelUtilities.get_model_filter(SDKClientUsersInfo, {'user_id': user_id}).first()

            if not sdk_client_info_instance:
                return False

            sdk_client_info_instance.widget_id = widget_id
            sdk_client_info_instance.save()

            return True

        except Exception as e:
            error_logger.error(f"Error in update_widget_id_for_member for user_id {user_id}: {e.args}")
            return False

    @staticmethod
    def validate_connection_users(member_id, api_key, user_id):

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        user_instance_x_member_id = ModelUtilities.get_user_instance_or_none(member_id)

        if not user_instance_x_member_id:
            return ResponseUtilities.get_inner_error_context("Invalid x-member-id")

        user_instance_user_id = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance_user_id:
            return ResponseUtilities.get_inner_error_context("Invalid member_uuid")

        member_instance_x_member_id = Members.get_member_instance_or_none(community_instance, user_instance_x_member_id)

        if not member_instance_x_member_id:
            return ResponseUtilities.get_inner_error_context("Invalid x-member-id")

        member_instance_user_id = Members.get_member_instance_or_none(community_instance, user_instance_user_id)

        if not member_instance_user_id:
            return ResponseUtilities.get_inner_error_context("Invalid member_uuid")

        return {
            'community_instance': community_instance,
            'member_instance': user_instance_x_member_id,
            'user_instance': user_instance_user_id
        }

    @staticmethod
    def validate_create_connection_request(member_id, api_key, user_id):
        validated_request = MemberCommunityHelper.validate_connection_users(member_id, api_key, user_id)

        if validated_request.get('error_message'):
            return validated_request

        if member_id == user_id:
            return ResponseUtilities.get_inner_error_context("You can't request a connection to yourself")

        community_instance = validated_request.get('community_instance')

        community_setting = ModelUtilities.get_model_filter(CommunitySettings,
                                                            {'community': community_instance,
                                                             'setting_type': community_setting_types.USER_CONNECTION,
                                                             'enabled': True})

        if not community_setting:
            return ResponseUtilities.get_inner_error_context("Enable User Connection Setting to use this api")

        return validated_request

    @staticmethod
    def validate_update_connection_request(member_id, api_key, user_id, action):
        validated_request = MemberCommunityHelper.validate_connection_users(member_id, api_key, user_id)

        if validated_request.get('error_message'):
            return validated_request

        if member_id == user_id:
            return ResponseUtilities.get_inner_error_context("You can't perform a connection action on yourself")

        community_instance = validated_request.get('community_instance')

        community_setting = ModelUtilities.get_model_filter(CommunitySettings,
                                                            {'community': community_instance,
                                                             'setting_type': community_setting_types.USER_CONNECTION,
                                                             'enabled': True})

        if not community_setting:
            return ResponseUtilities.get_inner_error_context("Enable User Connection Setting to use this api")

        if action not in [ConnectionRequestActions.ACCEPT.value, ConnectionRequestActions.REJECT.value]:
            return ResponseUtilities.get_inner_error_context("Invalid connection action sent")

        return validated_request

    @staticmethod
    def validate_fetch_connection_request(member_id, api_key, user_id, status):
        validated_request = MemberCommunityHelper.validate_connection_users(member_id, api_key, user_id)

        if validated_request.get('error_message'):
            return validated_request

        community_instance = validated_request.get('community_instance')

        community_setting = ModelUtilities.get_model_filter(CommunitySettings,
                                                            {'community': community_instance,
                                                             'setting_type': community_setting_types.USER_CONNECTION,
                                                             'enabled': True})

        if not community_setting:
            return ResponseUtilities.get_inner_error_context("Enable User Connection Setting to use this api")

        if member_id == user_id and status == ConnectionRequestStatus.PENDING.value:
            return ResponseUtilities.get_inner_error_context("You can't access other's pending requests")

        return validated_request

    @staticmethod
    def parse_users_dict_for_lm_id_mapping(users):
        output = {}

        for value in users.values():
            UUID = value["user_unique_id"]
            output[UUID] = value

        return output

    @staticmethod
    @shared_task
    def update_connection_data_cache_in_swarm_service(community_id, member_id, user_id, connection_status):
        user_info_filter = ModelUtilities.get_model_filter(Userinfo, {'user_id': user_id}).first()
        member_info_filter = ModelUtilities.get_model_filter(Userinfo, {'user_id': member_id}).first()
        sdk_client_instance = ModelUtilities.get_model_filter(SdkClient, {'community_id': community_id,
                                                                          'is_deleted': False}).first()

        if not (user_info_filter and sdk_client_instance):
            return

        endpoint = settings.SWARM_BASE_URL + SWARM_USER_CONNECTION_UPDATE_ENDPOINT.format(
            user_info_filter.user_unique_id)

        client = ApiClient()
        client.update_request_url(endpoint)

        # Add headers
        client.update_headers({
            'x-member-id': member_info_filter.user_unique_id,
            'x-api-key': sdk_client_instance.api_key
        })

        # Add Delete request body
        client.update_body({
            "status": connection_status
        })

        # Send delete request
        response = client.patch().response

        if response.status_code != 200:
            error_logger.error(
                f"Failed to update connection data: api_key = {community_id}, member_id: {member_id}, user_id: {user_id}, connection_status: {connection_status} - status code: {response.status_code} | response: {response.json()}")

        return
