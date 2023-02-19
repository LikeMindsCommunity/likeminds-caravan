from __future__ import absolute_import, unicode_literals
from celery import shared_task
from urllib.parse import unquote, quote
import googlemaps
from django.contrib.auth import login
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from external_services.mixpanel.events import MixpanelEvents
from external_services.segment.segment_impl import SegmentImpl
from internal_services.url_tags.uri_tags_impl import UriTagsImpl
from external_services.otp.otp_api_client import OTPApiClient
from external_services.caching.cache_impl import CacheImpl
from togther.models import *
from utility.file_utilities import FileUtilities
from utility.string_utilities import StringUtilities
from utility.states import report_Tag_Types, member_states
from random import randint
from utility.cache_keys import CONVERSATION_COMMUNITY_PREVIEW, EVENT_ATTENDEES_CHATROOM, EVENT_INSTRUCTORS_CHATROOM, \
    EVENT_HIGHLIGHTS_CHATROOM, EVENT_FAQ_CHATROOM, EVENT_MEMBERTESTIMONIALS_CHATROOM, EVENT_ATTENDEES_CONVERSATION, \
    CHATROOM_PARTICIPANTS_CREATED_CACHE_KEY, INTERNATIONAL_OTP_GENERATE_CACHE_KEY
from utility.celery_tasks import (
    update_last_unseen_in_engage_on_card_creation,
    update_last_unseen_in_engage, update_my_chatrooms_for_users,
    set_chatroom_state_for_all_members_on_card_creation,
    get_chatroom_user_images_for_web, update_preview_of_chatroom_in_cache,
    update_multiple_previews_in_chatroom, update_preview_for_account_image_change,
    schedule_chatroom_unpinning_after_event_completion,
    update_chatroom_conversation_count_in_cache,
    update_chatroom_conversation_creators_in_cache, get_conversation_poll,
    update_multiple_previews_in_community, update_preview_of_community_in_cache,
    update_event_attendees, set_levels_on_ctc_celery, set_level_click_state, update_event_instructors_in_cache,
    update_event_highlights_in_cache, update_event_faq_in_cache, update_event_member_testimonials_in_cache,
    update_event_in_webflow_service, update_event_attendees_for_micro_event, member_left_removed_dm_chatroom,
    reset_unread_message_count_in_cache, fetch_conversations_unread, update_deferred_card_poll_updated_at_value,
    get_to_show_results_for_conversation_poll, send_chatroom_deleted_analytics_data, cm_removed_dm_chatroom,
    member_becomes_cm_dm_chatroom, send_chatroom_updated_analytics_data,
    update_community_pin_chatrooms_list_in_cache)

from utility.firebase import (update_last_answer_id, upload_image_to_firebase, upload_community_thumbnail)

from utility.internal_link_preview_utilities import PreviewUtilities
from .notification import *
from .raw_queries import *
from .snackbar.snackbar_impl import SnackbarImpl
from .members import *
from .sync.model_update import update_models_for_syncing_apis
from .utility import *
from .tasks import (send_verification_mail_for_email_sync, update_pending_chatrooms_and_report_count,
                    update_pending_chatroom_count_for_promoters, update_report_count_for_all_promoters,
                    cm_onboarding_version_check, directory_questions_v2_version_check,
                    get_user_email_preferred_verified, international_otp_generate_requests_blocked_mail,)
from .static_text import ALL_MEMBER_COHORT_TEXT, tool_edit_directory_questions, tool_edit_community_details, \
    tool_community_settings
from .owner_message_template import post_owner_message_template_in_intro_room, check_owner_template_posted
from .mails import *
from .sms import *
from collabmates_api.sdk.models import (SdkClient)

from .chatroom_backup import create_chatroom_delete_backup, create_chatroom_participants_backup

from cms.models import NewAnswer, userAcquition, appUninstalls, InAppReview

from cms.cms_auth_utilities import CMSAuthUtilities

from .user_moderation_rights import *
from .rest_api import (CardAnswersDBSyncSerializer, EventRecordingsURLSerializer, GetChatroomInstanceSerializer,
                       CommunitySerializerV1, YourCommunitySerializer, EventRecordingsAttachmentsSerializer,
                       EventMemberTestimonialsSerializer, EventHighlightsSerializer, EventInstructorSerializer,
                       EventFAQSerializer)

from utility.constants import INSTAGRAM_LINK, TWITTER_LINK, BRANCH_DECODE_URI
from .upload_attachments import (save_community_image, save_chatroom_attachments,
                                 save_conversation_attachments, save_poll_attachments,
                                 save_draft_attachments, save_draft_poll_attachments,
                                 get_user_image_based_on_community)
from rest_framework import status as status_codes
from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from utility.number_utilities import NumberUtilities
from utility.exception_utilities import (CustomException, InvalidHeaderException)
from utility.version_utilities import VersionUtilities
from external_services.logging.logging_wrapper import LoggingWrapper
from external_services.segment.segment_impl import SegmentImpl
from external_services.email.email_wrapper import MailWrapper
from .branch import create_community_feed_url_for_cm_onboarding

from .search.sync import ElasticSearchSync
from .community.constants import *

from urllib import parse

url = settings.URL
error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


def update_pending_member_count_in_engage(community):
    '''function to update the member count in engage'''
    pending_members_count = Members.objects.filter(community_id=community, state=member_states.PENDING_MEMBER).count()
    all_members = Members.objects.filter(community_id=community)
    current_time = time.time()

    # update pending members in case of multiple promoters
    for member in all_members:

        if member.state == member_states.ADMIN or member.state == member_states.TEMP_ADMIN:
            update_models_for_syncing_apis(SyncTypes.COMMUNITY,
                                           {'community_id': community, 'member_id': member.member_id},
                                           {'pending_members': pending_members_count,
                                            'member_state': member.state})
        else:
            update_models_for_syncing_apis(SyncTypes.COMMUNITY,
                                           {'community_id': community, 'member_id': member.member_id},
                                           {'member_state': member.state})

    info_logger.info("Member Engage Pending Count Updated")


def generate_internal_link_preview_for_conversation(conversation, current_user_id):
    preview_dict = {}

    if conversation.internal_link:
        try:
            if conversation.preview_chatroom and conversation.preview_type == "chatroom":
                key = CHATROOM_PREVIW_CACHE_KEY % (str(conversation.preview_chatroom.id), str(conversation.id))
                preview = CacheImpl.get_cache(key)

                if preview:
                    preview_dict = preview

                else:
                    preview_dict = get_preview_for_url(current_user_id, conversation.internal_link,
                                                       community_instance=conversation.preview_community,
                                                       chatroom_instance=conversation.preview_chatroom)

                    if preview_dict:
                        update_preview_of_chatroom_in_cache.delay({'chatroom_id': conversation.preview_chatroom.id,
                                                                   'preview_object': preview_dict,
                                                                   'conversation_id': conversation.id})

                preview_dict['chatroom']['conversations_unread'] = fetch_conversations_unread(
                    conversation.preview_chatroom.id, current_user_id)

            elif conversation.preview_community and \
                    (conversation.preview_type == "community" or conversation.preview_type == "directory"):

                preview_community_id = conversation.preview_community_id
                key = CONVERSATION_COMMUNITY_PREVIEW % (str(conversation.id), str(preview_community_id))
                preview = CacheImpl.get_cache(key)

                if preview:
                    preview_dict = preview

                else:

                    preview_dict = get_preview_for_url(member_id=current_user_id,
                                                       preview_url=conversation.internal_link)

                    if preview_dict:
                        update_preview_of_community_in_cache.delay({'community_id': preview_community_id,
                                                                    'preview_object': preview_dict,
                                                                    'conversation_id': conversation.id})
            else:
                preview_dict = get_preview_for_url(current_user_id, conversation.internal_link,
                                                   community_instance=conversation.preview_community,
                                                   chatroom_instance=conversation.preview_chatroom)
                if not preview_dict:
                    preview_dict = {}

        except Exception as e:
            error_logger.error(e.args)

    return preview_dict


# home screen apis
def get_active_chatroom_member_images(community_instance, member_id):
    current_time = time.time()
    state_filter = collabcardState.objects.filter(community=community_instance,
                                                  user=member_id,
                                                  card__is_deleted=False).order_by('-card')
    temp = {}
    member_list = []
    user_set = set()
    temp['count'] = state_filter.count()
    for data in state_filter:
        card_instance = data.card
        user_id = card_instance.user.id
        user_instance = card_instance.user

        if user_id not in user_set:
            member_filter = Members.objects.filter(member_id=user_instance, community_id=data.community)
            if member_filter.exists():
                image_url = user_instance.userinfo.image_link if user_instance.userinfo.image_link else ''
                member_instance = member_filter[0]
                if member_instance.image_url:
                    image_url = member_instance.image_url
            else:
                image_url = REMOVED_USER_URL

            member = get_user_profile(user_instance, community_instance, send_profile=False)
            member['image_url'] = image_url
            member_list.append(member)

    current_time = time.time()
    state_filter = collabcardState.objects.filter(community=community_instance,
                                                  user=member_id,
                                                  card__is_deleted=False).order_by('-card')
    temp = {}
    member_list = []
    user_set = set()
    temp['count'] = state_filter.count()
    for data in state_filter:
        card_instance = data.card
        user_id = card_instance.user.id
        user_instance = card_instance.user

        if user_id not in user_set:
            member_filter = Members.objects.filter(member_id=user_instance, community_id=data.community)
            if member_filter.exists():
                image_url = user_instance.userinfo.image_link if user_instance.userinfo.image_link else ''
                member_instance = member_filter[0]
                if member_instance.image_url:
                    image_url = member_instance.image_url
            else:
                image_url = REMOVED_USER_URL

            member = get_user_profile(user_instance, community_instance, send_profile=False)
            member['image_url'] = image_url
            member_list.append(member)

            user_set.add(user_id)

        if len(member_list) > 3:
            break
    temp['member_list'] = member_list
    return temp


def is_draft_conversation(conversation, current_user_id, device_id=''):
    if (conversation.attachment_count > 0 and
        conversation.attachments_uploaded is False) and \
            ((current_user_id and
              NumberUtilities.get_integer_from_string(current_user_id) != conversation.user.id) or
             conversation.api_version <= 0 or
             conversation.device_id != device_id):
        return True

    return False


def is_draft_chatroom(chatroom_instance, member_id, device_id):
    if isinstance(member_id, str):
        member_id = NumberUtilities.get_integer_from_string(member_id)

    if (chatroom_instance.attachment_count > 0 and
        chatroom_instance.attachments_uploaded is False) and \
            (member_id != chatroom_instance.user_id or
             device_id != chatroom_instance.device_id):
        return True

    return False


def my_chatrooms_version_1(request):
    '''functions to get chatrooms for users'''

    member_id = get_member_id_from_headers(request)

    if not member_id:
        context = ResponseUtilities.get_view_impl_error_context("send member id in headers",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    user_instance = ModelUtilities.get_user_instance_or_none(member_id)

    if not user_instance:
        context = ResponseUtilities.get_view_impl_error_context("Invalid user ID",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    member_id = user_instance.id

    page = NumberUtilities.get_integer_from_string(request.GET.get('page', 1))

    if page <= 1:
        page = 1

    api_key = RequestUtilities.get_api_key_from_headers(request)
    chatroom_type = NumberUtilities.get_integer_from_string(request.GET.get("type"), -1)

    community_id = request.GET.get('community_id', None)
    community_instance = SdkClient.get_community_instance_or_none(community_id, api_key)

    if (community_id or api_key) and not community_instance:
        context = ResponseUtilities.get_view_impl_error_context("Invalid community ID/API key!",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    if community_instance:
        community_id = community_instance.id

    show_dm = request.GET.get('show_dm', False)

    is_ios = RequestUtilities.is_request_ios(request)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)
    device_id = RequestUtilities.get_device_id_from_headers(request)

    is_dm_message = False
    consider_dm_chatrooms = False
    user_community_ids = []
    dm_instance_community_ids_list = []
    dm_instance_list = []
    non_dm_instance_list = []
    my_chatrooms = []
    instance_list = []

    if show_dm == 'true':
        show_dm = True
    else:
        show_dm = False

    member_filter = ModelUtilities.get_model_filter(Members, {'member_id': user_instance})

    if community_id:
        user_community_ids.append(community_id)

    else:
        user_community_ids = list(member_filter.values_list("community_id_id", flat=True))

    intro_room_community_list = ModelUtilities.get_model_filter(CommunitySettings, {
        'community_id__in': user_community_ids,
        'enabled': True,
        'setting_type': "intro_room"
    }).values_list("community_id", flat=True)

    if show_dm:
        consider_dm_chatrooms = True
        dm_right_instance = ModelUtilities.get_model_filter(communityRightsSettings, {
            "community_id__in": user_community_ids,
            "right__state": member_rights.MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES
        })

        if dm_right_instance.exists():
            is_dm_message = True
            dm_instance_community_ids_list = list(dm_right_instance.values_list("community_id", flat=True))

    should_add_dm_chatrooms = False

    dm_community_settings_filter = ModelUtilities.get_model_filter(
        CommunitySettings, {'setting_type': community_setting_types.DIRECT_MSGS_GROUP_MSGS,
                            'community': community_instance})

    if dm_community_settings_filter:
        should_add_dm_chatrooms = dm_community_settings_filter[0].enabled

    joined_chatroom_count = get_my_chatrooms_count(member_id,
                                                   version_code,
                                                   platform_code,
                                                   chatroom_type=chatroom_type,
                                                   consider_dm_chatrooms=consider_dm_chatrooms,
                                                   dm_instance_community_ids_list=dm_instance_community_ids_list,
                                                   community_id=community_id,
                                                   intro_room_community_list=intro_room_community_list,
                                                   should_add_dm_chatrooms=should_add_dm_chatrooms)

    page_count = get_total_pages(joined_chatroom_count, limit=10)

    total_pages = page_count

    engage_list = get_followed_chatrooms(member_id,
                                         page,
                                         version_code,
                                         platform_code,
                                         chatroom_type=chatroom_type,
                                         limit=10,
                                         consider_dm_chatrooms=consider_dm_chatrooms,
                                         dm_instance_community_ids_list=dm_instance_community_ids_list,
                                         community_id=community_id,
                                         intro_room_community_list=intro_room_community_list,
                                         should_add_dm_chatrooms=should_add_dm_chatrooms)

    chatroom_ids_list = []

    if engage_list:

        for id, _ in engage_list.items():
            instance = conversationEngage.objects.get(pk=id)
            instance_list.append(instance)

            if instance.card_id not in chatroom_ids_list:
                chatroom_ids_list.append(instance.card_id)

    draft_list = get_draft_chatrooms_on_home_screen(member_id, page, community_id)

    for id in draft_list:
        instance = conversationEngage.objects.get(pk=id)
        instance_list.append(instance)

        if instance.card_id not in chatroom_ids_list:
            chatroom_ids_list.append(instance.card_id)

    # Segregate DM and Non-DM chatrooms
    for instance in instance_list:
        is_dm_private_instance = instance.card.is_private

        if all([not should_add_dm_chatrooms,
                is_dm_message,
                is_dm_private_instance,
                instance.card.chatroom_with_user,
                instance.card.community_id in dm_instance_community_ids_list]):
            dm_instance_list.append(instance)

        elif (not instance.card.chatroom_with_user) and (not is_dm_private_instance):
            non_dm_instance_list.append(instance)

        elif should_add_dm_chatrooms:
            non_dm_instance_list.append(instance)

    if show_dm and is_dm_message:
        instance_list = dm_instance_list

    else:
        instance_list = non_dm_instance_list

    conversation_users = get_conversation_users_against_chatrooms_list(chatroom_ids_list)
    chatroom_conversations = get_latest_conversations_against_chatrooms_list(chatroom_ids_list)

    for instance in instance_list:

        chatroom = {}
        card_instance = instance.card
        draft_instance = instance.draft

        if card_instance:
            chatroom['chatroom'] = get_chatroom_instance(card_instance, member_id, send_profile=False)
            context = {"current_user_id": member_id}
            chatroom['community'] = CommunitySerializerV1(card_instance.community, context=context,
                                                          many=False).data
            chatroom['is_draft'] = False
        elif draft_instance:
            chatroom['chatroom'] = get_draft_chatroom_instance(draft_instance, member_id)
            context = {"current_user_id": member_id}
            chatroom['community'] = CommunitySerializerV1(draft_instance.community, context=context,
                                                          many=False).data
            chatroom['is_draft'] = True

        chatrooms_conversation_ids_list = chatroom_conversations.get(card_instance.id)

        last_conversation_id = chatrooms_conversation_ids_list[0] if chatrooms_conversation_ids_list else None

        last_conversation = ModelUtilities.get_model_instance_or_none(card_answers, last_conversation_id)

        if last_conversation and not is_draft_conversation(last_conversation, member_id, device_id):
            last_conversation_dict = conversationSerializer(last_conversation,
                                                            current_user_id=member_id, device_id=device_id)
            preview = generate_internal_link_preview_for_conversation(last_conversation, member_id)

            if preview:
                last_conversation_dict['preview'] = preview

            chatroom['last_conversation'] = last_conversation_dict

            second_last_conversation_id = chatrooms_conversation_ids_list[1] \
                if len(chatrooms_conversation_ids_list) > 1 else None

            second_last_conversation = ModelUtilities.get_model_instance_or_none(card_answers,
                                                                                 second_last_conversation_id)

            if second_last_conversation and not is_draft_conversation(second_last_conversation, member_id, device_id):
                second_last_conversation_dict = conversationSerializer(second_last_conversation,
                                                                       current_user_id=member_id, device_id=device_id)
                preview = generate_internal_link_preview_for_conversation(second_last_conversation, member_id)

                if preview:
                    second_last_conversation_dict['preview'] = preview

                chatroom['second_last_conversation'] = second_last_conversation_dict

        chatroom['unseen_conversation_count'] = instance.unseen_count
        chatroom['last_conversation_time'] = instance.updated_at

        if engage_list.get(instance.id):
            chatroom['last_conversation_time'] = get_time_text_for_my_chatrooms(
                TimeUtilities.convert_milliseconds_to_sec(engage_list.get(instance.id)))

        chatroom['conversation_users'] = conversation_users.get(card_instance.id, [])

        rights_list = json.loads(instance.rights_list) if instance.rights_list else []

        if is_ios and \
                member_rights.MEMBER_RIGHT_CREATE_SECRET_ROOM in rights_list and \
                version_code <= SECRET_CHATROOM_VERSION_CODE_IOS:
            rights_list.remove(member_rights.MEMBER_RIGHT_CREATE_SECRET_ROOM)

        chatroom['member_right_states'] = rights_list

        member_instance = Members.objects.filter(member_id=user_instance,
                                                 community_id=instance.community)
        if member_instance:
            chatroom['member_state'] = member_instance[0].state
        else:
            chatroom['member_state'] = member_states.GUEST

        my_chatrooms.append(chatroom)

    context = {
        'success': True,
        'my_chatrooms': my_chatrooms,
        'total_pages': total_pages
    }

    if page == 1:

        if show_dm and is_dm_message:
            total_unseen_count = conversationEngage.objects \
                .filter(user=user_instance,
                        community_id__in=dm_instance_community_ids_list,
                        unseen_count__gt=0) \
                .aggregate(total=Sum('unseen_count'))

        elif not show_dm:
            total_unseen_count = conversationEngage.objects \
                .filter(user=user_instance,
                        unseen_count__gt=0,
                        community_id__in=user_community_ids,
                        card__is_private=False,
                        card__chatroom_with_user=None) \
                .aggregate(total=Sum('unseen_count'))

        else:
            total_unseen_count = {'total': 0}

        if total_unseen_count['total'] is None:
            total_unseen_count['total'] = 0

        context['total_unseen_count'] = total_unseen_count['total']

        member_engages = ModelUtilities.get_model_filter(Member_Engage, {"member_id_id": member_id,
                                                                        "community_id_id": community_id})
        if member_engages:
            member_engage = member_engages[0]

            from .member_community.member_community_impl import MemberCommunityHelper

            community_chatroom_count_dict = MemberCommunityHelper.fetch_chatroom_count_for_home(
                [community_id], user_instance.id, is_chatroom_revamp=True)

            if community_chatroom_count_dict.get(member_engage.community_id_id):
                context['total_chatroom_count'] = community_chatroom_count_dict.get(member_engage.community_id_id)
            else:
                context['total_chatroom_count'] = 0

            if member_engage.member_state == member_states.ADMIN or \
                    member_engage.member_state == member_states.MEMBER or \
                    member_engage.member_state == member_states.PROFILE_UNAVAILABLE:
                context['unseen_chatroom_count'] = member_engage.last_unseen_count
            else:
                context['unseen_chatroom_count'] = 0

    return JsonResponse(context)


def get_latest_conversation_members(last_conversation_member, second_last_conversation_member,
                                    last_conversation_user, second_last_conversation_user):
    conversation_users = []
    if last_conversation_member:
        temp = {}
        temp['id'] = last_conversation_member.member_id.id
        temp['name'] = last_conversation_member.member_id.userinfo.name
        if last_conversation_member.image_url:
            temp['image_url'] = last_conversation_member.image_url
        else:
            temp['image_url'] = last_conversation_member.member_id.userinfo.image_link
        conversation_users.append(temp)

    if last_conversation_user:
        instance = last_conversation_user

        remove = False
        if instance.remove:
            remove = True

        temp = get_user_profile(instance.user, instance.community.id, send_profile=False, remove=remove)

        conversation_users.append(temp)

    if second_last_conversation_member:

        temp = {}
        temp['id'] = second_last_conversation_member.member_id.id
        temp['name'] = second_last_conversation_member.member_id.userinfo.name
        if second_last_conversation_member.image_url:
            temp['image_url'] = second_last_conversation_member.image_url
        else:
            temp['image_url'] = second_last_conversation_member.member_id.userinfo.image_link
        conversation_users.append(temp)
    if second_last_conversation_user:
        instance = second_last_conversation_user
        remove = False
        if instance.remove:
            remove = True
        temp = get_user_profile(instance.user, instance.community.id, send_profile=False, remove=remove)
        conversation_users.append(temp)

    return conversation_users


def fetch_chatroom_inactive(request):
    '''api to return the in-active chatrooms snack-bar'''

    context = {}

    return JsonResponse(context)


######################function for api utility#################################


def get_error_context(success, error_message):
    '''function to get error context for apis'''

    context = {
        'success': success,
        'error_message': error_message
    }
    return context


############# functions for  community detail screen ##########################


def get_leave_community_text():
    leave_community = []

    leave_community_title = "Leave community?"
    leave_community.append(leave_community_title)

    leave_community_subtitle = "Are you sure you want to leave this community permanently? Your community profile will be removed whereas any content created by you would remain."
    leave_community.append(leave_community_subtitle)

    leave_community_positive_title = "OK, LEAVE NOW"
    leave_community.append(leave_community_positive_title)

    leave_community_negative_title = "CANCEL"
    leave_community.append(leave_community_negative_title)

    # "leave_community_positive_action"
    # "leave_community_negative_action"

    return leave_community


def get_home_screen_community_actions(community_instance):
    actions = []

    community_details = {
        'title': "Community details",
        'route': """route://community?community_id=%s""" % (str(community_instance.id))
    }

    actions.append(community_details)

    member_directory = {
        'title': "Member directory",
        'route': """route://members_directory?community_id=%s&community_name=%s""" % (
            str(community_instance.id), community_instance.name)
    }

    actions.append(member_directory)

    invite_members = {
        'title': "Invite members",
        'route': """route://community?community_id=%s&share=true""" % (
            str(community_instance.id))
    }

    actions.append(invite_members)

    return actions


def bottom_menu(request):
    try:
        member_id = RequestUtilities.get_member_id_from_headers(request)
        member_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not member_instance:
            return JsonResponse({
                'success': False,
                'error_message': 'Invalid member-id'
            }, status=status_codes.HTTP_400_BAD_REQUEST)

        menu = _build_bottom_menu(member_instance)
        return JsonResponse({
            'success': True,
            'menu': menu
        })

    except Exception as e:
        error_logger.error('bottom menu API error: ', e)
        return JsonResponse({
            'success': False,
            'menu': []
        })


def _build_bottom_menu(user_instance) -> list:
    menu = list()
    _add_join_new_community_menu(menu)

    if settings.IS_BETA or Members.is_community_member(community=COMMUNITY_HOOD_COMMUNITY_ID, member=user_instance):
        _add_create_new_community_menu(menu)

    _add_send_feedback_menu(menu)
    _add_help_faq_menu(menu)

    return menu


def _add_join_new_community_menu(menu: list):
    join_new_community_menu = {
        'title': 'Join new community',
        'route': 'route://bottom_menu/join_new_community'
    }
    menu.append(join_new_community_menu)


def _add_create_new_community_menu(menu: list):
    create_new_community_menu = {
        'title': 'Create New Community',
        'route': 'route://browser?link=<encoded new_community_url>'
    }
    menu.append(create_new_community_menu)


def _add_send_feedback_menu(menu):
    send_feedback_menu = {
        'title': 'Send Feedback',
        'route': 'route://bottom_menu/send_feedback'
    }
    menu.append(send_feedback_menu)


def _add_help_faq_menu(menu):
    help_faq_menu = {
        'title': 'Help/FAQ',
        'route': 'route://bottom_menu/help_faq'
    }
    menu.append(help_faq_menu)


def community(request, community_id, req_dict=None):
    ''' Community detail page '''

    # handling web redirection to playstore and app store
    community = Community.get_community_or_None(community_id)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    if not community:
        error_msg = "cannot find community with id"
        context = get_error_context(False, error_msg)
        error_logger.error(error_msg)

        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    if is_request_web(request):
        context = get_redirection_links_for_android_ios(request, community_id)

        if context:
            return JsonResponse(context, safe=False)

    member_id = get_member_id_from_headers(request)

    if RequestUtilities.is_request_android(request) or RequestUtilities.is_request_ios(request):

        user_instance = User.get_user_or_none(member_id)

        if not user_instance:
            error_msg = "cannot find member with id"
            context = get_error_context(False, error_msg)
            error_logger.error(error_msg)

            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    is_promoter = False
    is_owner = False
    block_leave_community = False
    member_list = Members.objects.filter(community_id=community, member_id=member_id)

    promoter_instance = 0
    current_user_instance = None
    new_dict = {}
    menu = ""
    if member_list.exists():
        current_user_instance = member_list[0].member_id
        state = member_list[0].state

        if state == member_states.ADMIN:
            is_promoter = True
            is_owner = member_list[0].is_owner
            promoter_instance = current_user_instance
            block_leave_community = True
            menu = MENU['promoter'].copy()

            has_right = check_admin_edit_community_right(promoter_instance, community)
            if not has_right:
                del menu[3]

        if state == member_states.PENDING_MEMBER:
            block_leave_community = True
            menu = MENU['pending_member_in_paid_community'] if community.is_paid else MENU['pending_member']

        if state == member_states.MEMBER or state == member_states.PROFILE_UNAVAILABLE:
            menu = MENU['member']
    else:
        block_leave_community = True

    if is_promoter:
        serialized_object = CommunitySerializer(community, promoter_id=current_user_instance,
                                                is_owner=is_owner, current_user_id=member_id,
                                                current_user_instance=current_user_instance,
                                                platform_code=platform_code, version_code=version_code)
    else:
        serialized_object = CommunitySerializer(community, current_user_id=member_id,
                                                current_user_instance=current_user_instance,
                                                platform_code=platform_code, version_code=version_code)

    # form a dictionary of community objects
    new_dict.update(serialized_object)

    # leave community data
    if not block_leave_community:
        temp = {}
        leave_community = get_leave_community_text()
        temp['leave_community_title'] = leave_community[0]
        temp['leave_community_sub_title'] = leave_community[1]  # fix
        temp['leave_community_positive_title'] = leave_community[2]
        temp['leave_community_negative_title'] = leave_community[3]
        context = {'community': new_dict, 'leave_community': temp}
        if menu:
            context['menu'] = menu
        if req_dict:
            return context
        return JsonResponse(context)

    context = {'community': new_dict}

    if menu:
        context['menu'] = menu

    return JsonResponse(context)


def get_redirection_links_for_android_ios(request, community_id):
    aj = request.GET.get('aj', False)
    source = request.GET.get('source')
    # auto join check functionality

    context = {}
    ios_private_link = ""

    if aj and is_request_android(request) and not source:
        private_link = "https://" + request.META['HTTP_HOST'] + "/community/" + str(community_id) + "?aj=" + str(aj)
        playstore_ref_link = android_app_download_link + """&referrer=%s""" % (quote(private_link))
        context['playstore_ref_link'] = playstore_ref_link
        # return redirect(playstore_ref_link)

    if aj and is_request_ios(request) and not source:
        ios_deep_link = "Collabmates://" + request.META['HTTP_HOST'] + "/community/" + str(community_id) + "?aj=" + str(
            aj)
        ios_branch_link = """https://collabmates.app.link/q9PKG0YPR8?$deep_link=%s""" % (quote(ios_deep_link))
        context['ios_ref_link'] = ios_branch_link

        # return redirect(ios_branch_link)
    return context


def pending_members(request, community_id):
    ''' function to get members requested to join in a community '''

    # member_id = request.GET.get('member_id',None)
    # if not member_id:
    member_id = get_member_id_from_headers(request)

    has_approve_right = check_admin_approve_right(member_id, community_id)
    if has_approve_right:
        pending_requests = get_pending_members_of_community(community_id, requested_member_id=member_id)
    else:
        pending_requests = []
    return JsonResponse({'pending_members': pending_requests})


def admins(request, community_id, req_dict=None):
    ''' function to get admins of a community '''

    member_id = request.GET.get('member_id', None)

    current_user_id = get_member_id_from_headers(request)

    admins = Members.objects.filter(community_id=community_id, state=member_states.ADMIN).order_by('-updated_at')
    users = []
    current_member_data = {}
    for admin in admins:

        user_instance = admin.member_id
        if current_user_id and user_instance.id == int(current_user_id):
            temp = MembersSerializer(admin, community_id, current_user_id=current_user_id)
            current_member_data = temp
        else:
            temp = MembersSerializer(admin, community_id, current_user_id=current_user_id)
            users.append(temp)

    if current_member_data:
        users.insert(0, current_member_data)
    context = {'members': users}

    if req_dict:
        return context

    return JsonResponse(context)


############# functions for  join community  screen ##########################


def questions(request):
    '''api to send the questions for a particular community'''

    member_id = get_member_id_from_headers(request)

    user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    if not user_instance:
        context = get_error_context(False, "Invalid member id")

        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    community_id = request.GET.get('community_id')

    if not community_id:
        context = get_error_context(False, "send community id in get params")
        return JsonResponse(context)

    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

    if not community_instance:
        context = get_error_context(False, "Invalid community id")
        return JsonResponse(context)

    data = ModelUtilities.get_model_filter(communityQuestions, {"community": community_id}).order_by('-rank', 'id')

    community_serialized_object = CommunitySerializerV1(community_instance, many=False).data

    created_by = get_community_creator(community_instance)

    community_serialized_object['created_by'] = created_by

    managers = get_community_managers(community_instance)

    if managers['count'] > 1:
        managed_by = managers['manager_name'] + ".." + "+" + str(managers['count'] - 1)
    else:
        managed_by = managers['manager_name']

    community_serialized_object['managed_by'] = managed_by

    # private link share flow
    aj = request.GET.get('aj', None)
    shared_by = request.GET.get('shared_by', None)

    is_valid_private_link = False
    auto_join = {}
    title = f"You are joining {community_serialized_object['name']}"
    shared_by_user = None

    is_cm_onboarding_enabled = cm_onboarding_version_check(platform_code, version_code)

    try:
        shared_by_user = User.objects.get(pk=shared_by)
        shared_by_user_name = shared_by_user.userinfo.name
        title = f"{shared_by_user_name} invited you to join {community_serialized_object['name']}"
    except:
        error_logger.error(f"shared by user id does not exist in DB. shared by ---> {shared_by} ")

    if aj and shared_by_user:
        try:
            if is_cm_onboarding_enabled:
                auto_join = private_link_app_invite_v2(community_instance, aj, created_by, shared_by_user,
                                                       user_instance)

            else:
                auto_join = private_link_app_invite(community_instance, aj, created_by, shared_by_user)
            is_valid_private_link = True
        except:
            error_logger.error(f"aj is not valid. aj ---> {aj}")

    # add code to send join dropoff notfication
    if not is_member_verified(community_instance, user_instance):
        time_in_hrs = 2
        send_notification_to_join_drop_off.delay(user_instance.id, community_instance.id, aj, time_in_hrs)

    questions = []

    for question in data:
        serialized_question = CommunityQuestionsSerializer(question)

        if all([platform_code == PLATFORM_CODE_WEB,
                serialized_question['question_title'] == CREATE_COMMUNITY_QUESTION_NAME_TITLE,
                serialized_question['is_hidden'],
                serialized_question['field'],
                serialized_question['state'] == question_states.PARAGRAPH]):
            continue

        if serialized_question['state'] == question_states.INTRODUCTION:
            serialized_question['rank'] = 0
            answers_filter = communityAnswers.objects.filter(question=serialized_question['id'], member=member_id)
            if answers_filter.exists():
                answer_instance = answers_filter[0]
                introduction_answer = answer_instance.question_answer
                serialized_question['previous_answer'] = introduction_answer

        else:
            serialized_question['rank'] = 1

        # if the question is not deleted
        if not question.remove_state:
            questions.append(serialized_question)
    # questions = sorted(questions, key=lambda i: i['rank'])

    context = {'header': "Join community", 'title': title,
               'questions': questions, 'community': community_serialized_object}
    if is_valid_private_link:
        context.update(auto_join)
    return JsonResponse(context)


def private_link_app_invite_v2(community_instance, unique_code, created_by=None, shared_by_user=None,
                               user_instance=None):
    '''function to send private link for app invite on playstore'''

    expiry_filter = communityExpiryCodes.objects.filter(community=community_instance, unique_code=unique_code)
    shared_by_user_name = shared_by_user.userinfo.name

    auto_join = {
        'toast': PRIVATE_LINK_APP_INVITE_DEFAULT_TOAST.format(shared_by_user_name),
        'aj_expired': True
    }

    if ((not community_instance.is_paid) and (not expiry_filter)) or \
            (community_instance.is_paid and expiry_filter.filter(user=user_instance)):
        return auto_join

    if expiry_filter.exists():
        auto_join['aj_expired'] = False
        auto_join['toast'] = ""

    return auto_join


def private_link_app_invite(community_instance, unique_code, created_by=None, shared_by_user=None):
    '''function to send private link for app invite on playstore'''

    expiry_filter = communityExpiryCodes.objects.filter(community=community_instance, unique_code=unique_code)
    shared_by_user_name = shared_by_user.userinfo.name
    auto_join = {
        'toast': f"The private invite link has expired. Continue to join the community and wait for admin’s approval. Or, ask {shared_by_user_name} to resend a private invite link.",
        'aj_expired': True
    }

    if expiry_filter.exists():
        created_at = expiry_filter[0].created_at
        expire_duration = expiry_filter[0].expire_duration
        current_time = time.time()

        if current_time - created_at <= expire_duration:
            auto_join['aj_expired'] = False

        time_left = created_at + expire_duration - current_time
        time_left = ConvertSectoDay(time_left)

        if not auto_join['aj_expired']:
            auto_join['toast'] = """This private invite link expires in %s""" % (time_left)

    return auto_join


def update_community_toast(user_instance, community_instance, message=''):
    # setting the toast messages to show on community detail page
    update_dict = {
        'toast_message': message,
        "created_at": TimeUtilities.current_time_in_sec()
    }

    instance, created = communityToast.objects.update_or_create(user=user_instance,
                                                                community=community_instance,
                                                                defaults=update_dict)


def validate_private_link(aj, shared_by, community, timestamp=time.time()):
    context = {"valid_link": False, "shared_user_instance": None}

    if aj is None and shared_by is None:
        return context

    try:
        # trying to check if aj and shared by are both valid integers
        validate_time = False
        if aj is not None:
            aj = int(aj)
            validate_time = is_joining_time_valid(community, timestamp, aj)

        try:
            shared_by = int(shared_by)
            shared_user_instance = User.objects.get(pk=shared_by)
        except Exception as e:
            shared_user_instance = None

        context['shared_user_instance'] = shared_user_instance
        context['valid_link'] = validate_time and shared_user_instance

    except Exception as e:
        info_logger.info(f"aj and shared by validation failed. aj -> {aj}, shared by -> {shared_by}")

    finally:
        print(">>>>  7")
        return context


def is_joining_time_valid(community_instance, time_stamp, unique_code):
    '''function to check whether community joining time is valid or not'''
    check = communityExpiryCodes.objects.filter(community=community_instance, unique_code=unique_code)
    info_logger.info(check)
    if check.exists():
        expiry_instance = check[0]
        time_stamp = int(time_stamp)
        expiry_time = int(expiry_instance.created_at)
        info_logger.info(time_stamp)
        info_logger.info(expiry_time)
        if (time_stamp - expiry_time) <= expiry_instance.expire_duration:
            return True

    return False


def post_introduction_card_for_community(community_id, member_id):
    '''function to get introduction card of community'''

    check_intro = communityQuestions.objects.filter(community=community_id, question_state=question_states.INTRODUCTION)

    if check_intro.exists():
        question_id = check_intro[0].id
        introduction_answer_list = communityAnswers.objects.filter(community=community_id, member=member_id,
                                                                   question_id=question_id)
        if introduction_answer_list:
            introduction_answer = introduction_answer_list[0].question_answer
            req_dict = {
                'member_id': member_id,
                'community_id': community_id,
                'title': introduction_answer,
                'type': 1,
                'create_intro': 1
            }

            master_intro = ModelUtilities.get_model_filter(Collabcard,
                                                           {'community': community_id,
                                                            'type': card_types.CARD_MASTER_INTRO,
                                                            'is_deleted': False})

            if not master_intro:
                return

            intro_filter = Collabcard.objects.filter(community=community_id,
                                                     user=member_id,
                                                     type=card_types.CARD_INTRO,
                                                     is_deleted=False)

            if not intro_filter:
                context = create_card_internal(member_id, community_id, req_dict)
                card_instance = context.get('card_instance')
                user_instance = User.get_user_or_none(member_id)
                image_url = get_user_image_based_on_community(member_id, community_id)

                if card_instance and image_url:
                    save_chatroom_attachments(card_instance, body={
                        'url': image_url,
                        'type': "image",
                        'index': 1
                    })
                    ModelUtilities.model_update(Collabcard, {'id': card_instance.id},
                                                {'has_files': True, 'attachment_count': 1,
                                                 'attachments_uploaded': True})

                create_conversation_context_for_intro_chatrooms(card_instance, user_instance, master_intro[0])

                update_member_rights_in_conversation_engage(community_id, member_id)

                return True
            else:
                intro_filter.update(title=introduction_answer)

    return False


def update_chatroom_conversation_homescreen(card_instance, user_instance, conversation_instance, community_instance):
    from .conversation.conversation_impl import ConversationHelper

    ConversationHelper.update_the_activity_time_for_new_conversation_creation(card_instance.id, user_instance.id)

    ConversationHelper.update_homescreen_meta_on_conversation_creation(community_instance,
                                                                       card_instance,
                                                                       conversation_instance)


def create_conversation_context_for_intro_chatrooms(card_instance, user_instance, master_intro):
    preview_url = settings.URL + "/collabcard/" + str(card_instance.id)

    conversation_context = {}
    community_instance = card_instance.community
    conversation_context['answer'] = card_instance.title
    conversation_context['card'] = master_intro
    conversation_context['user'] = user_instance
    conversation_context['community'] = community_instance
    conversation_context['has_files'] = False
    conversation_context['attachment_count'] = 0
    conversation_context['attachments_uploaded'] = False
    conversation_context['api_version'] = 1
    conversation_context['preview_chatroom'] = card_instance
    conversation_context['preview_community'] = community_instance
    conversation_context['internal_link'] = settings.URL + "/collabcard/" + str(card_instance.id)
    conversation_context['preview_type'] = "chatroom"

    answer_instance = card_answers(**conversation_context)
    answer_instance.save()
    func_dict = {
        'member_id': user_instance.id,
        'collabcard_id': master_intro.id,
        'status': True,
        'source': "create_conversation_context_for_intro_chatrooms"
    }
    collabcard_follow_internal(func_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)
    update_preview_of_chatroom_in_cache.delay({'chatroom_id': card_instance.id,
                                               'preview_url': preview_url,
                                               'conversation_id': answer_instance.id})

    update_chatroom_conversation_homescreen(master_intro, user_instance, answer_instance, community_instance)

    return answer_instance


def post_purpose_collabcard_for_community(request, community_instance, member_id):
    '''function to post purpose card for community'''

    introduction_answer = community_instance.purpose

    if not introduction_answer:
        return

    if ModelUtilities.is_model_filter_exists(Collabcard, {'community': community_instance.id,
                                                          'type': card_types.CARD_PURPOSE}):
        return

    req_dict = {

        'member_id': member_id,
        'community_id': community_instance.id,
        'title': introduction_answer,
        'type': card_types.CARD_PURPOSE,
    }
    context = create_card_internal(member_id, community_instance.id, req_dict)

    return context['card_instance']


def post_general_collabcard_for_community(community_instance, member_id, is_script=False):
    '''function to post general card for community'''

    req_dict = {

        'member_id': member_id,
        'community_id': community_instance.id,
        'title': GENERAL_CHAT_TITLE_TEXT,
        'type': card_types.CARD_NORMAL,
        'header': GENERAL_CHAT_HEADER,
        'auto_follow_done': True,
        'include_members_later': True
    }

    if not is_script:

        if ModelUtilities.is_model_filter_exists(Collabcard, {'community': community_instance.id,
                                                              'type': card_types.CARD_NORMAL}):
            return

    context = create_card_internal(member_id, community_instance.id, req_dict)

    return context['card_instance']


def post_master_introductions_for_community(community_id, member_id):
    """function to post the master introduction card"""
    res = {
        'member_id': member_id,
        'community_id': community_id,
        'title': MASTER_INTRO_TITLE_TEXT,
        'type': card_types.CARD_MASTER_INTRO,
        'header': MASTER_INTRO_HEADER
    }

    if ModelUtilities.is_model_filter_exists(Collabcard, {'community': community_id,
                                                          'type': card_types.CARD_MASTER_INTRO,
                                                          }):
        return

    context = create_card_internal(member_id, community_id, res)

    return context


def update_hidden_fields_in_questions(user_instance, community_instance):
    '''api to update hidden fields in questions'''
    question_filter = communityQuestions.objects.filter(community=community_instance, is_hidden=True)

    for question_instance in question_filter:

        if question_instance.question_state == question_states.MOBILE_NO:
            mobile_filter = userMobiles.objects.filter(user=user_instance, state=mobile_states.PRIMARY)

            if not mobile_filter.exists():
                return

            mobile_no = "+" + str(mobile_filter[0].country_code) + " " + str(mobile_filter[0].mobile_no)

            if mobile_no:
                answer_instance = communityAnswers()
                answer_instance.question = question_instance
                answer_instance.member = user_instance
                answer_instance.community = community_instance
                answer_instance.question_answer = mobile_no
                answer_instance.question_title = question_instance.question_title
                answer_instance.save()


def update_community_actions(community_instance):
    '''function to update community actions steps'''

    promoter_filter = Members.objects.filter(community_id=community_instance, state=member_states.ADMIN)

    if promoter_filter.exists():
        if not promoter_filter[0].actions_required:
            return
    member_count = get_members_count_in_community(community_instance.id)
    instance_list = communityLevels.objects.filter(community=community_instance).order_by('id')
    community_level_filter = instance_list
    for instance in instance_list:

        if instance.level == "Level 2" and instance.state == community_level_states.PENDING:
            member_count = member_count - 1
            if instance.joined_members < instance.max_members:
                instance.joined_members = member_count
                instance.save()
                # instance.update(joined_members=F(instance.joined_members)+1)

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                instance.save()

                community_level_filter.filter(level="Level 3").update(title=LEVEL_3_TITLE,
                                                                      sub_title=LEVEL_3_SUB_TITLE,
                                                                      state=community_level_states.PENDING)

        elif instance.level == "Level 3" and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                instance.save()

                community_level_filter.filter(level="Level 4").update(title=LEVEL_4_TITLE,
                                                                      sub_title=LEVEL_4_SUB_TITLE,
                                                                      state=community_level_states.PENDING)

        elif instance.level == "Level 4" and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                promoter_filter.update(actions_required=False)
                instance.save()

def set_levels_on_ctc(community_instance, level, promoter=False):
    '''updating levels based on different call to actions'''

    if promoter:
        return

    community_level_filter = communityLevels.objects.filter(community=community_instance).order_by('id')
    for instance in community_level_filter:

        if instance.level == level and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()
                # instance.update(joined_members=F(instance.joined_members)+1)

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                instance.save()

                community_level_filter.filter(level="Level 3").update(title=LEVEL_3_TITLE,
                                                                      sub_title=LEVEL_3_SUB_TITLE,
                                                                      state=community_level_states.PENDING)


        elif instance.level == level and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                instance.save()

                community_level_filter.filter(level="Level 4").update(title=LEVEL_4_TITLE,
                                                                      sub_title=LEVEL_4_SUB_TITLE,
                                                                      state=community_level_states.PENDING)


def save_user_selected_options(question_instance, user_instance, community_instance, selected_choices):
    '''function to save user selected options in dropdown'''

    # question_instance = communityQuestions.objects.get(id=48562)

    dropdown_list = decode_option(question_instance.value)

    for choice in selected_choices:

        option = choice.strip()
        if not is_option_present(option, dropdown_list):
            # Save answer for review
            new_answer_instance = NewAnswer()
            new_answer_instance.option = option
            new_answer_instance.question = question_instance
            new_answer_instance.user = user_instance
            new_answer_instance.community = community_instance
            new_answer_instance.save()

            dropdown_list.append(option)
        filter_instance = questionFilters(question=question_instance, filter=option,
                                          member=user_instance, community=community_instance)
        filter_instance.save()

    result = []
    for value in dropdown_list:
        temp = {}
        temp['value'] = value
        result.append(temp)

    json_dump = json.dumps(result)
    question_instance.value = json_dump
    question_instance.save()


def is_option_present(option, dropdown_list):
    '''function to check is option present or not'''

    for data in dropdown_list:
        if data.lower() == option.lower():
            return True
    return False


def save_profile_links_from_handles(question_instance, answer_instance):
    '''function to generate profile links from instagram and twitter handles'''

    value_list = json.loads(question_instance.value)

    if value_list and value_list[0]['profile_platform'] == "Instagram":
        answer_instance.question_answer = INSTAGRAM_LINK + answer_instance.question_answer
        answer_instance.save()

    elif value_list and value_list[0]['profile_platform'] == "Twitter":
        answer_instance.question_answer = TWITTER_LINK + answer_instance.question_answer
        answer_instance.save()


############# functions for  members of community   ##########################

def user(request, user_id):
    '''api to send the user profile of LikeMinds'''

    context = {}
    try:

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            context['error_message'] = 'Invalid user ID'

        else:
            context['user'] = get_logged_in_user(user_instance)

    except Exception as e:

        context['error_message'] = e.args

    return JsonResponse(context)


@csrf_exempt
def edit_user(request):
    user_id = get_member_id_from_headers(request)

    type = request.POST.get('type')
    value = request.POST.get('value')

    if not type or not value:
        context = get_error_context(False, "Send correct type and value in post params")
        return JsonResponse(context)

    userinfo_filter = Userinfo.objects.filter(user_id=user_id)
    if type == 'image':

        userinfo_instance = userinfo_filter[0]
        previous_image_url = userinfo_instance.image_link
        userinfo_instance.image_link = value
        userinfo_instance.updated_at = TimeUtilities.current_time_in_sec()
        userinfo_instance.save()

        update_preview_for_account_image_change.delay({'user_id': user_id,
                                                       'image_url': value,
                                                       'previous_image_url': previous_image_url})

    elif type == 'name':
        userinfo_instance = userinfo_filter[0]
        userinfo_instance.name = value
        userinfo_instance.save()

        update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                       {'member_id': user_id},
                                       {})

        ElasticSearchSync.update_user_name.delay(user_id, userinfo_instance.name)
        ElasticSearchSync.update_member_name.delay(user_id, userinfo_instance.name)

    return JsonResponse({'success': True})


@csrf_exempt
def update_email(request):
    '''api to perform operations on email of user'''
    email = request.POST.get('email_id')
    typ = request.POST.get('type')

    user_id = get_member_id_from_headers(request)
    if not user_id:
        context = get_error_context(False, "send member id from headers")
        return JsonResponse(context)

    user_instance = User.objects.get(id=user_id)

    if typ == 'new':

        email_filter = userEmails.objects.filter(email=email, verified=True)
        if email_filter.exists():
            return JsonResponse({'error_message': "email already exists in system", 'success': False})

        save_user_primary_email(user_instance, email, email_state=email_states.NON_PRIMARY)

        # send verification mail for email
        verification_details = generate_tokens_for_email(user_instance, email, email_state=email_states.NON_PRIMARY)

        # sending a email from template
        send_verification_mail_for_email_sync(user_name=user_instance.userinfo.name,
                                              verification_link=verification_details['verify_url'], email=email)

        return JsonResponse({'success': True})

    elif typ == 'edit':

        email_filter = userEmails.objects.filter(email=email, verified=True)
        if email_filter.exists():
            return JsonResponse({'error_message': "email already exists in system", 'success': False})

        uniq_id = request.POST.get('id')
        email_filter = userEmails.objects.filter(id=uniq_id)
        if email_filter.exists():
            email_instance = email_filter[0]
            email_instance.email = email
            email_instance.verified = False
            email_instance.save()

            # send verification mail for email
            verification_details = generate_tokens_for_email(user_instance, email, email_state=email_states.NON_PRIMARY)

            # sending a email from template
            send_verification_mail_for_email_sync(user_name=user_instance.userinfo.name,
                                                  verification_link=verification_details['verify_url'], email=email)

        return JsonResponse({'success': True})

    elif typ == 'primary':

        uniq_id = request.POST.get('id')
        userEmails.objects.filter(user=user_instance).update(email_state=email_states.NON_PRIMARY)
        userEmails.objects.filter(id=uniq_id).update(email_state=email_states.PRIMARY)

    elif typ == 'resend_verification':
        uniq_id = request.POST.get('id')
        email_instance = userEmails.objects.get(id=uniq_id)
        email = email_instance.email
        # send verification mail for email
        verification_details = generate_tokens_for_email(user_instance, email, email_state=email_states.NON_PRIMARY)

        # sending a email from template
        send_verification_mail_for_email_sync(user_name=user_instance.userinfo.name,
                                              verification_link=verification_details['verify_url'], email=email)

    elif typ == 'delete':
        uniq_id = request.POST.get('id')
        userEmails.objects.filter(id=uniq_id).delete()

    return JsonResponse({'success': True})


@csrf_exempt
def update_mobiles(request):
    '''api to add mobile number'''

    typ = request.POST.get('type')

    user_id = get_member_id_from_headers(request)

    if not user_id:
        context = get_error_context(False, "send member id from headers")
        return JsonResponse(context)

    if typ == 'delete':

        uniq_id = request.POST.get('id')
        userMobiles.objects.filter(id=uniq_id).delete()

        return JsonResponse({'success': True})

    elif typ == 'primary':

        uniq_id = request.POST.get('id')

        userMobiles.objects.filter(user_id=user_id).update(state=mobile_states.NON_PRIMARY)
        userMobiles.objects.filter(id=uniq_id).update(state=mobile_states.PRIMARY)

        return JsonResponse({'success': True})

    return JsonResponse({'error_message': "send correct type"})


@csrf_exempt
def send_feedback(request):
    '''api to send feedback of user to likeminds team'''

    res = json.loads(request.body)

    user_id = res['user_id']
    try:
        user_instance = User.objects.get(id=user_id)
    except:
        return JsonResponse({'success': False, "error_message": "user does not exists"})

    feedback = res['feedback']
    mail_images = res['images'] if 'images' in res else None
    images = json.dumps(res['images']) if 'images' in res else None

    instance = userFeedback()
    instance.feedback = feedback
    instance.user = user_instance
    instance.images = images
    instance.created_at = time.time()
    instance.save()
    send_feedback_mail_to_webmaster.delay(instance.id)
    # print(mail_images)
    # print(json.loads(mail_images))

    return JsonResponse({'success': True})


def members(request, community_id):
    ''' function to get all the mebers of a community including admins and nominated members '''
    community = get_object_or_404(Community, pk=community_id)
    # get members of the community

    current_user_id = get_member_id_from_headers(request)

    if community_id == feedback_community_id:
        # if the community is feedback community sending empty list
        return JsonResponse({'members': []})

    member = Members.objects.filter(community_id=community).filter(Q(state=1) | Q(state=2) |
                                                                   Q(state=4) | Q(state=7) |
                                                                   Q(state=8) | Q(state=9))
    members = []
    for mem in member:

        if not mem.member_id.userinfo:
            continue
        usr = UserinfoSerializer(mem.member_id.userinfo)
        usr['member_state'] = mem.state
        form_response = FormResponseSerilaizer(community_id, mem.member_id.id, bl=True, current_user_id=current_user_id)
        if form_response:
            usr['response'] = form_response[0]
            usr['question_answers'] = form_response[1]

        members.append(usr)

    context = {'members': members}
    return JsonResponse(context)


@csrf_exempt
def edit_member_profile(request):
    '''api to udate member profile'''

    res = RequestUtilities.load_request_body(request)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    if not res:
        return JsonResponse({'error_message': "In-valid request body"},
                            status=status_codes.HTTP_400_BAD_REQUEST)

    community_instance = ModelUtilities.get_model_instance_or_none(Community, res.get('community_id'))

    if not community_instance:
        return JsonResponse({'error_message': "In-valid community id"},
                            status=status_codes.HTTP_400_BAD_REQUEST)

    community_id = community_instance.id
    member_id = get_member_id_from_headers(request)

    user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

    if not user_instance:
        return JsonResponse({'error_message': "In-valid user id"},
                            status=status_codes.HTTP_400_BAD_REQUEST)
    update_preview = False

    state = 0
    member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                              'member_id': member_id})

    if member_filter:
        state = member_filter[0].state

    is_promoter = member_filter[0].member_id if (state == member_states.ADMIN) else False

    is_verified_member = ((state == member_states.ADMIN) or
                          (state == member_states.MEMBER) or
                          (state == member_states.PROFILE_UNAVAILABLE))

    # getting the collabcard Id for introduction card
    collabcard_id = 0
    intro_card_instance = None

    intro_filter = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                'user': user_instance,
                                                                'is_deleted': False,
                                                                'type': card_types.CARD_INTRO})
    if intro_filter:
        intro_card_instance = intro_filter[0]
        collabcard_id = intro_card_instance.id

    ModelUtilities.delete_record_in_model(questionFilters, {'member': user_instance,
                                                            'community': community_instance})
    ModelUtilities.delete_record_in_model(communityAnswers, {'community': community_instance,
                                                             'member': user_instance})

    from .community.community_impl import CommunityHelper
    CommunityHelper.save_responses_of_member_in_community(user_instance.id, community_instance.id,
                                                          res.get('questions', []),
                                                          False)

    for data in res.get('questions', []):

        if intro_card_instance and data.get("state") == question_states.INTRODUCTION:
            ModelUtilities.model_update(Collabcard, {'id': intro_card_instance.id},
                                        {'title': data['value']})
            ModelUtilities.model_update(collabcardState,
                                        {'card': intro_card_instance, 'user': user_instance},
                                        {'updated_at': TimeUtilities.current_time_in_sec()})

            if ModelUtilities.is_model_filter_exists(card_answers,
                                                     {'preview_chatroom': intro_card_instance,
                                                      'preview_type': "chatroom"}):

                update_preview = True

    form_response = FormResponseSerilaizer(community_id, member_id, bl=True, current_user_id=member_id)

    # # setting edit status in members table
    ModelUtilities.model_update(Members,
                                {'community_id': community_instance,
                                 'member_id': user_instance},
                                {'edit_required': False, 'updated_at': TimeUtilities.current_time_in_sec()})

    if res.get('image_url'):
        member_filter.update(image_url=res['image_url'], updated_at=TimeUtilities.current_time_in_sec())

        if intro_card_instance:

            file_filter = ModelUtilities.get_model_filter(Card_Attachment,
                                                          {'collabcard_id': intro_card_instance})

            if file_filter:
                card_file_instance = file_filter[0]
                card_file_instance.file_url = res['image_url']
                card_file_instance.save()

            else:
                save_chatroom_attachments(intro_card_instance, body={
                    'url': res['image_url'],
                    'type': "image",
                    'index': 1
                })
                ModelUtilities.model_update(Collabcard, {'id': intro_card_instance.id},
                                            {'has_files': True, 'attachment_count': 1,
                                             'attachments_uploaded': True})

            update_models_for_syncing_apis(SyncTypes.CHATROOM, {'card': intro_card_instance}, {})
        update_preview = True

    # posting a introduction collabcard
    if not intro_card_instance and is_verified_member:
        post_introduction_card_for_community(community_instance.id, user_instance.id)
        update_preview = False

    # update level of community
    set_levels_on_ctc_celery.delay({"community_id": community_instance.id,
                                    "level": "Level 3",
                                    "promoter": True if is_promoter else False})

    question_answer = ""

    if form_response:
        question_answer = form_response[1]

    if update_preview:
        update_multiple_previews_in_chatroom.delay({'chatroom_id': collabcard_id})

    # setting the level click state when the promoter set-up directory and update the click state

    set_level_click_state.delay({"community_id": community_instance.id, "is_promoter": True if is_promoter else False})

    from collabmates_api.cohort.cohort_impl import CohortHelper

    CohortHelper.remove_cohort_membership_when_updating_community_answers(member_id, community_id)

    CohortHelper.add_member_to_respective_question_based_cohorts(member_id, community_id)

    if question_answer:
        return JsonResponse({'success': True, 'question_answers': question_answer}, status=status_codes.HTTP_200_OK)

    return JsonResponse({'success': True}, status=status_codes.HTTP_200_OK)


@csrf_exempt
def remove_from_member(request):
    '''function to remove member of community'''

    member_id = get_member_id_from_headers(request)

    if not member_id:
        context = ResponseUtilities.get_view_impl_error_context("Invalid member_id",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_id = request.POST.get('community_id')
    api_key = RequestUtilities.get_api_key_from_headers(request)

    if not community_id and not api_key:
        context = ResponseUtilities.get_view_impl_error_context("Invalid community_id or api_key",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    member_ids = request.POST.get('member_ids', False)
    tag_id = request.POST.get('tag_id', None)
    reason = request.POST.get('reason', '')

    community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

    if not community_instance:
        context = ResponseUtilities.get_view_impl_error_context("Invalid community_id or api_key",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_id = community_instance.id
    current_user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

    if not current_user_instance:
        context = ResponseUtilities.get_view_impl_error_context("Invalid member_id",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    is_promoter = Members.objects.filter(state=member_states.ADMIN,
                                         community_id=community_instance,
                                         member_id=current_user_instance)
    is_promoter = is_promoter.exists()

    if member_ids:
        if is_promoter:

            member_ids = unquote(member_ids)
            member_ids = json.loads(member_ids)

            for member in member_ids:
                member_filter = Members.objects.filter(community_id=community_instance, member_id=member)

                if member_filter:
                    member_state = member_filter[0].state
                    is_owner = member_filter[0].is_owner
                    eligible_member_states = [member_states.ADMIN, member_states.MEMBER,
                                              member_states.PROFILE_UNAVAILABLE,
                                              member_states.KNOWN_NOMINATED_PROMOTER]

                    if not is_owner and member_state in eligible_member_states:

                        user_instance = member_filter[0].member_id

                        remove_members(community_instance, user_instance,
                                       removed_state=deleted_members.REMOVED,
                                       current_user_instance=current_user_instance)

                        save_moderation_history(user=user_instance, community=community_instance,
                                                moderation_by=current_user_instance,
                                                type=moderation_history_types.REMOVED_FROM_COMMUNITY)

                        remove_all_member_rights(community_instance, user_instance)
                        remove_all_manager_rights(community_instance, user_instance)

                        snackbar_manager = SnackbarImpl()
                        snackbar_dict = {
                            'tag_id': tag_id,
                            'reason': reason,
                            'community_name': community_instance,
                            'type': HomeSnackbarType.REMOVED_MEMBER,
                            'user_id': member
                        }
                        snackbar_manager.create_snackbar(snackbar_dict)

                        check_reports_and_update_action.delay(action_taken_by=member_id,
                                                              action_taken=report_Action_Types.REMOVE_FROM_COMMUNITY,
                                                              user=member, community=community_id,
                                                              action_taken_tag_id=tag_id, action_taken_reason=reason)
                        send_notification_for_removed_member.delay(admin_id=member_id,
                                                                   removed_user_id=member, community_id=community_id)

                        from collabmates_api.cohort.cohort_impl import CohortHelper
                        CohortHelper.fetch_user_cohorts_having_filters_with_community_id(community_id, user_instance)

                        info_logger.info(
                            f"REMOVE_MEMBER_API (REMOVED CASE) -current user id = {member_id}, user id = {member}"
                            f", community id = {community_id}")

                        analytics_data = {
                            'removed_member_id': member,
                            'community_id': community_id,
                            'reason': reason
                        }

                        SegmentImpl.track_event(member_id, 'Member removed (Backend)', analytics_data)

                        send_sync_notification.delay({'community_id': community_id,
                                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})
                        update_multiple_previews_in_community.delay({'community_id': community_id})

                        ElasticSearchSync.delete_chatrooms_for_removed_member.delay(community_id, member)

                    else:
                        context = ResponseUtilities.get_view_impl_error_context(
                            "Cannot remove the Owner of this community", status_codes.HTTP_400_BAD_REQUEST)
                        return JsonResponse(context['data'], status=context['status'])
            return JsonResponse({'success': True})
        else:
            context = ResponseUtilities.get_view_impl_error_context(
                "You are not the promoter of this community", status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

    # pending member check
    if member_ids is False:
        is_pending = Members.objects.filter(state=member_states.PENDING_MEMBER, community_id=community_id,
                                            member_id=member_id)
        if is_pending.exists():
            remove_members(community_instance, current_user_instance, removed_state=deleted_members.LEFT,
                           current_user_instance=current_user_instance)
            toast_filter = communityToast.objects.filter(community=community_instance, user=current_user_instance)
            toast_filter.update(toast_message=PENDING_MEMBER_REQUEST_REJECTED_COMMUNITY_TOAST)

            check_reports_and_update_action.delay(action_taken_by=member_id,
                                                  action_taken=report_Action_Types.LEFT_THE_COMMUNITY,
                                                  user=member_id, community=community_id)
            update_pending_member_count_in_engage(community_instance)
            send_sync_notification.delay({'community_id': community_id,
                                          'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})
            update_multiple_previews_in_community.delay({'community_id': community_id})

            return JsonResponse({'success': True})

    # flow to leave the community
    if not is_promoter and member_ids is False:

        is_member = Members.objects.filter(community_id=community_instance, member_id=current_user_instance).filter(
            Q(state=member_states.PROFILE_UNAVAILABLE) | Q(state=member_states.MEMBER))

        if not is_member and community_instance.is_paid:
            is_member = SubscriptionExpiredMembers.objects \
                .filter(community=community_instance, member=current_user_instance) \
                .filter(Q(state=member_states.PROFILE_UNAVAILABLE) | Q(state=member_states.MEMBER) |
                        Q(state=member_states.KNOWN_NOMINATED_PROMOTER))

        if is_member:
            remove_members(community_instance, current_user_instance, removed_state=deleted_members.LEFT,
                           current_user_instance=current_user_instance)

            save_moderation_history(user=current_user_instance, community=community_instance,
                                    moderation_by=current_user_instance,
                                    type=moderation_history_types.LEFT_COMMUNITY)

            check_reports_and_update_action.delay(action_taken_by=member_id,
                                                  action_taken=report_Action_Types.LEFT_THE_COMMUNITY,
                                                  user=member_id, community=community_id)

            info_logger.info(f"REMOVE_MEMBER_API (Left CASE) - current user id = {member_id}, user id = {member_id}"
                             f", community id = {community_id}")

            remove_all_member_rights(community_instance, current_user_instance)
            remove_all_manager_rights(community_instance, current_user_instance)

            from collabmates_api.cohort.cohort_impl import CohortHelper
            CohortHelper.fetch_user_cohorts_having_filters_with_community_id(community_id, current_user_instance)

            send_sync_notification.delay({'community_id': community_id,
                                          'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

            send_notification_to_managers_when_member_leaves_community.delay(member_id, community_id)

            ElasticSearchSync.delete_chatrooms_for_removed_member.delay(community_id, member_id)
            MixpanelEvents.leave_community.delay(member_id, community_id)

            return JsonResponse({'success': True})
        else:
            context = ResponseUtilities.get_view_impl_error_context(
                "You are promoter of this community. You can be removed by other promoter",
                status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(context['data'], status=context['status'])

    context = ResponseUtilities.get_view_impl_error_context(
        "Failed to remove member(s)",
        status_codes.HTTP_400_BAD_REQUEST)
    return JsonResponse(context['data'], status=context['status'])

@csrf_exempt
def remove_members(community_instance, user_instance, removed_state, current_user_instance):
    """ function to remove member and delete user's community related data """

    update_dict = {
        'removed_state': removed_state,
        "created_at": TimeUtilities.current_time_in_sec()
    }

    instance, created = removedMembers.objects.update_or_create(member=user_instance,
                                                                community=community_instance,
                                                                defaults=update_dict)

    if removed_state == deleted_members.LEFT or removed_state == deleted_members.REMOVED:
        message = MEMBER_LEFT_COMMUNITY_TOAST if deleted_members.LEFT else MEMBER_REMOVED_FROM_COMMUNITY_TOAST

        create_info = {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'message': message
        }

        communityToast.update_or_create_toast_message(create_info)

    # removing the intro chatroom
    intro_filter = Collabcard.objects.filter(community=community_instance,
                                             user=user_instance,
                                             type=card_types.CARD_INTRO,
                                             is_deleted=False)
    if intro_filter:
        intro_instance = intro_filter[0]
        intro_instance.is_deleted = True
        intro_instance.deleted_by_user = current_user_instance
        intro_instance.save()
        update_multiple_previews_in_chatroom.delay({'chatroom_id': intro_instance.id})

    ModelUtilities.model_update(collabcardState,
                                {'community': community_instance, 'user': user_instance},
                                {'remove': instance, 'updated_at': TimeUtilities.current_time_in_sec()}
                                )

    ModelUtilities.model_update(card_answers,
                                {'community': community_instance, 'user': user_instance},
                                {'remove': instance, 'last_updated': TimeUtilities.current_time_in_milliseconds()}
                                )

    # Create Card Answer for all DM Chatroom
    member_filter = ModelUtilities.get_model_filter(Members,
                                                    {"community_id": community_instance, "member_id": user_instance})

    if member_filter.exists():
        dm_chatroom_ids_as_cm = ModelUtilities.get_model_filter(Collabcard,
                                                                {"user": user_instance,
                                                                 "community": community_instance,
                                                                 "is_private": True}).values_list("id", flat=True)

        dm_chatroom_ids_as_member = ModelUtilities.get_model_filter(Collabcard,
                                                                    {"chatroom_with_user": user_instance,
                                                                     "community": community_instance,
                                                                     "is_private": True}).exclude(
            chatroom_with_user=None).values_list("id", flat=True)

        dm_chatroom_ids = set(list(dm_chatroom_ids_as_cm) + list(dm_chatroom_ids_as_member))

        member_left_removed_dm_chatroom.delay(user_instance.id, community_instance.id, instance.id, removed_state,
                                              list(dm_chatroom_ids))

    # deleting member record
    ModelUtilities.delete_record_in_model(Members,
                                          {"community_id": community_instance, "member_id": user_instance}
                                          )

    # deleting from your communities
    ModelUtilities.delete_record_in_model(Member_Engage,
                                          {"community_id": community_instance, "member_id": user_instance}
                                          )
    # deleting user answers
    ModelUtilities.delete_record_in_model(communityAnswers,
                                          {"community": community_instance, "member": user_instance}
                                          )

    # removing the draft chatrooms
    ModelUtilities.delete_record_in_model(draftChatroom,
                                          {"community": community_instance, "user": user_instance}
                                          )

    # removing the followed chatrooms
    ModelUtilities.delete_record_in_model(conversationEngage,
                                          {"community": community_instance, "user": user_instance}
                                          )
    # removing the filter data
    ModelUtilities.delete_record_in_model(questionFilters,
                                          {"community": community_instance, "member": user_instance}
                                          )

    ModelUtilities.delete_record_in_model(SubscriptionExpiredMembers,
                                          {"community": community_instance, "member": user_instance}
                                          )

    update_last_unseen_in_engage_on_card_creation.delay(community_instance.id, is_seen=False)


def update_followed_for_rejoined_member(user, community):
    removedMembers.objects.filter(community=community, member=user).delete()
    # saving collabcard state in update status
    update_models_for_syncing_apis(SyncTypes.CONVERSATION,
                                   {'community': community, 'user': user},
                                   {'remove': None})
    card_states = collabcardState.objects.filter(community=community, user=user)
    update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                   {'community': community, 'user': user},
                                   {'remove': None})

    followed_filter = card_states.filter(follow_status=True).order_by('id')

    for instance in followed_filter:

        engage_filter = conversationEngage.objects.filter(card=instance.card, user=user)

        if not engage_filter.exists():
            engage_instance = conversationEngage()

            engage_instance.community = community
            engage_instance.card = instance.card
            engage_instance.user = instance.user
            engage_instance.created_at = instance.created_at
            engage_instance.updated_at = instance.updated_at

            engage_instance.save()

    if isinstance(community, Community):
        community_id = community.id
    else:
        community_id = community

    if isinstance(user, User):
        user_id = user.pk
    else:
        user_id = user

    update_member_rights_in_conversation_engage.delay(community_id, user_id)
    # update elastic search
    ElasticSearchSync.update_chatrooms_for_rejoined_member.delay(community_id, user_id)


def fetch_community_profile(request):
    '''api to get the community profile of user'''

    current_member_id = get_member_id_from_headers(request)
    user_id = request.GET.get('user_id')
    community_id = request.GET.get('community_id')

    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

    if not community_instance:
        return JsonResponse({'error_message': "Invalid community id"}, status=status_codes.HTTP_400_BAD_REQUEST)

    user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

    if not user_instance:
        return JsonResponse({'error_message': "Invalid requested user id"}, status=status_codes.HTTP_400_BAD_REQUEST)

    current_user_instance = ModelUtilities.get_model_instance_or_none(User, current_member_id)

    if not current_user_instance:
        return JsonResponse({'error_message': "Invalid member_id "}, status=status_codes.HTTP_400_BAD_REQUEST)

    membership_expired_filter = ModelUtilities.get_model_filter(removedMembers,
                                                                {'member': user_instance,
                                                                 'community': community_instance,
                                                                 'removed_state': deleted_members.MEMBERSHIP_EXPIRED})
    if membership_expired_filter:
        return JsonResponse({'error_message': "Membership Expired for user"},
                            status=status_codes.HTTP_400_BAD_REQUEST)

    member_filter = ModelUtilities.get_model_filter(Members, {'member_id': current_user_instance,
                                                              'community_id': community_instance})
    is_promoter = False
    is_owner = False

    if member_filter:
        is_promoter = member_filter[0].state == member_states.ADMIN
        is_owner = member_filter[0].is_owner

    user_admin_rights = None

    if is_owner or is_promoter:
        user_admin_rights = check_all_manager_rights(current_member_id, community_id)

    member_ids = [user_id]
    member = get_members_profile(member_ids, community_id, current_user_id=current_member_id, is_promoter=is_promoter,
                                 is_owner=is_owner, profile_detail_api=True, user_admin_rights=user_admin_rights)

    if member:
        member = member[0]
        member['community_name'] = community_instance.name

        return JsonResponse(member)

    return JsonResponse({})


def fetch_user_chatrooms(request):
    '''api to send chatrooms created by user or followed by user'''

    page = request.GET.get('page', 1)
    state = request.GET.get('state', 0)
    user_id = request.GET.get('user_id')
    community_id = request.GET.get('community_id')
    api_key = RequestUtilities.get_api_key_from_headers(request)
    current_user_id = get_member_id_from_headers(request)
    chatrooms = []

    if not page.isdigit():
        context = ResponseUtilities.get_view_impl_error_context("Send valid page",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    if not state.isdigit():
        context = ResponseUtilities.get_view_impl_error_context("Send valid state",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

    if not community_instance:
        context = ResponseUtilities.get_view_impl_error_context("Invalid community ID or x-api-key",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_id = community_instance.id

    # chatrooms created by user
    if int(state) == 0:

        chatroom_filter = Collabcard.objects.filter(user_id=user_id, community_id=community_id,
                                                    is_pending=False, is_deleted=False,
                                                    is_secret=False, is_private=False).order_by('-id')
        created_chatroom_count = chatroom_filter.count()
        chatroom_filter = pagination(chatroom_filter, page, paginate_by=10)

        for chatroom in chatroom_filter:

            temp = get_chatroom_instance(chatroom, user_id, current_user_id=current_user_id)
            temp['conversation_users'] = []
            engage_filter = conversationEngage.objects.filter(card=chatroom, user=user_id)
            if engage_filter.exists():
                temp['conversation_users'] = get_conversation_users(engage_filter[0])

            chatrooms.append(temp)

        return JsonResponse({'success': True,
                             'chatrooms': chatrooms,
                             'total_chatrooms_created': created_chatroom_count})

    # chatrooms not created by user but  followed by users
    elif int(state) == 1:

        chatroom_list = list(Collabcard.objects.filter(user_id=user_id, community_id=community_id,
                                                       is_pending=False, is_deleted=False,
                                                       is_private=False).values_list('id', flat=True))

        state_filter = collabcardState.objects.filter(user_id=user_id, community_id=community_id,
                                                      follow_status=True,
                                                      card__is_secret=False,
                                                      card__is_private=False).exclude(
            card__in=chatroom_list).order_by('-updated_at', '-id')

        followed_chatroom_count = len(state_filter)
        state_filter = pagination(state_filter, page, paginate_by=10)

        for chatroom in state_filter:
            chatroom_instance = chatroom.card

            temp = get_chatroom_instance(chatroom_instance, user_id, current_user_id=current_user_id)
            temp['date'] = TimeUtilities.convert_epoch_time_in_date(chatroom.updated_at)
            engage_filter = conversationEngage.objects.filter(card=chatroom_instance, user=user_id)
            temp['conversation_users'] = []

            if engage_filter:
                temp['conversation_users'] = get_conversation_users(engage_filter[0])
            chatrooms.append(temp)

        return JsonResponse({'success': True,
                             'chatrooms': chatrooms,
                             'total_chatrooms_followed': followed_chatroom_count})

    context = ResponseUtilities.get_view_impl_error_context("Send correct state",
                                                            status_codes.HTTP_400_BAD_REQUEST)
    return JsonResponse(context['data'], status=context['status'])

def fetch_common_communities(request):
    '''api to fetch common communities of user'''
    user_id = request.GET.get('user_id')
    member_id = get_member_id_from_headers(request)
    page = request.GET.get('page', 1)

    user_communities = Members.objects.filter(member_id=user_id).filter(
        Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) | Q(
            state=member_states.PROFILE_UNAVAILABLE)).values_list('community_id', flat=True)

    member_communities = Members.objects.filter(member_id=member_id).filter(
        Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) | Q(
            state=member_states.PROFILE_UNAVAILABLE)).values_list('community_id', flat=True)

    common_communities = member_communities.intersection(user_communities).order_by('community_id')
    total_count = common_communities.count()
    common_communities = pagination(common_communities, page, paginate_by=10)
    communities = []
    communities_order = {}

    # making a dictionary in order to save latest timestamp of chatroom creation in a community
    for community_id in common_communities:

        last_chatroom = Collabcard.objects.filter(community_id=community_id,
                                                  is_pending=False, is_deleted=False).last()

        if last_chatroom:
            communities_order[community_id] = last_chatroom.date_epoch
        else:
            communities_order[community_id] = 0

    communities_order = sorted(communities_order.items(), key=lambda x: x[1], reverse=True)

    for order in communities_order:
        community_instance = Community.objects.get(id=order[0])
        context = {"current_user_id": member_id}
        community_serializer = CommunitySerializerV1(community_instance, context=context, many=False).data
        communities.append(community_serializer)

    return JsonResponse({'communities': communities, 'total_count': total_count})


def get_conversation_users(instance):
    last_conversation_member = instance.last_conversation_member
    second_last_conversation_member = instance.second_last_conversation_member
    last_conversation_user = instance.last_conversation_user
    second_last_conversation_user = instance.second_last_conversation_user

    conversation_users = get_latest_conversation_members(last_conversation_member,
                                                         second_last_conversation_member,
                                                         last_conversation_user,
                                                         second_last_conversation_user)
    return conversation_users


############# functions for  create flow of card,community and members   ##########################
def set_community_actions(community_instance):
    '''function to set community action for community profiling'''

    if not ModelUtilities.is_model_filter_exists(communityLevels, {'community': community_instance}):
        # first level
        communityLevels.create_instance({
            'community': community_instance,
            'level': 'Level 1',
            'title': LEVEL_1_TITLE,
            'sub_title': LEVEL_1_SUB_TITLE,
            'level_state': community_level_states.COMPLETE,
            'image': IMAGE_LEVEL_1,
            'joined_members': None,
            'max_members': None
        })

        # second level
        communityLevels.create_instance({
            'community': community_instance,
            'level': 'Level 2',
            'title': LEVEL_2_TITLE,
            'sub_title': LEVEL_2_SUB_TITLE,
            'level_state': community_level_states.PENDING,
            'image': IMAGE_LEVEL_2,
            'joined_members': 0,
            'max_members': 1 if settings.IS_BETA else 2
        })

        # third level
        communityLevels.create_instance({
            'community': community_instance,
            'level': 'Level 3',
            'title': LEVEL_3_TITLE,
            'sub_title': LEVEL_3_SUB_TITLE,
            'level_state': community_level_states.LOCKED,
            'image': IMAGE_LEVEL_3,
            'joined_members': 0,
            'max_members': 1 if settings.IS_BETA else 10
        })

        # fourth level
        communityLevels.create_instance({
            'community': community_instance,
            'level': 'Level 4',
            'title': LEVEL_4_TITLE,
            'sub_title': None,
            'level_state': community_level_states.LOCKED,
            'image': IMAGE_LEVEL_4,
            'joined_members': 0,
            'max_members': 1 if settings.IS_BETA else 10
        })


@csrf_exempt
def create_community_version_1(request):
    '''function to create community for version for whatsapp shifting'''
    member_id = get_member_id_from_headers(request)
    user_instance = User.objects.get(pk=member_id)
    res = json.loads(request.body)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    community_name = ""
    purpose = ""
    community_type = None
    sub_type = None

    page = 1

    if 'page' in res:
        page = res['page']

    if 'name' in res:
        community_name = res['name']

    if 'purpose' in res:
        purpose = res['purpose']

    if 'type' in res:
        community_type = res['type']

    if 'sub_type' in res:
        sub_type = res['sub_type']

    community_id = None
    if 'community_id' in res:
        community_id = res['community_id']

    community_state = 0
    if 'state' in res:
        community_state = res['state']

    about = None
    if 'about' in res:
        about = res['about']

    if page == 1:

        community_instance = Community()
        community_instance.name = community_name
        community_instance.members_count = 1
        community_instance.about = about
        community_instance.image_link = community_default_image
        community_instance.thumbnail = community_default_thumbnail
        community_instance.image_link_round = community_default_image_round
        community_instance.type = community_type if community_type else None
        community_instance.sub_type = sub_type if sub_type else None
        community_instance.created_at = time.time()
        community_instance.updated_at = time.time()
        community_instance.hide_community = community_state
        community_instance.save()

        set_community_actions(community_instance)

        # making the member instance for created community
        member_instance = Members()
        member_instance.member_id = user_instance
        member_instance.community_id = community_instance
        member_instance.state = member_states.ADMIN
        member_instance.actions_required = True
        member_instance.is_owner = True
        member_instance.custom_title = "Owner"  # community creator is the owner of community
        member_instance.created_at = time.time()
        member_instance.updated_at = time.time()
        member_instance.became_member_at = time.time()
        member_instance.save()

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
        give_all_manager_rights(user=user_instance, community=community_instance)
        give_all_member_rights(user=user_instance, community=community_instance)
        # create_member_rights_history_for_owner.delay(community_instance.id, user_instance.id)
        # give all community setting rights
        give_all_community_setting_rights(community=community_instance)

        save_moderation_history(user=user_instance, community=community_instance,
                                moderation_by=user_instance,
                                type=moderation_history_types.STARTED_COMMUNITY)

        # send community created mail to the team
        email_context = {
            'member_name': member_instance.member_id.userinfo.name,
            'community_name': community_instance.name,
            'member_email': member_instance.member_id.userinfo.email,
            'community_id': community_instance.id
        }
        send_created_community_email_to_team.delay(email_context)

        # Create Content Download Settings
        content_download_settings_list = []

        for download_setting_type, download_setting_title in DOWNLOAD_SETTING_TYPE_TITLE_MAPPING.items():
            content_download_settings_list.append(ContentDownloadSettings.create_instance({
                'community_instance': community_instance,
                'download_setting_type': download_setting_type,
                'download_setting_title': download_setting_title,
                'enabled': True
            }))

        ModelUtilities.bulk_create_instances(ContentDownloadSettings, content_download_settings_list)

        add_community_settings_for_community(community_instance, user_instance)

        if cm_onboarding_version_check(platform_code, version_code):
            update_community_get_started(community_instance, get_started_types.CREATE_COMMUNITY_TYPE, is_enabled=True)

        community_serializer = CommunitySerializerV1(community_instance, context={"current_user_id": member_id},
                                                     many=False).data

        return JsonResponse({'success': True, 'community': community_serializer})

    elif page == 2:

        community_instance = Community.objects.get(id=community_id)
        community_instance.purpose = purpose
        community_instance.save()

        update_models_for_syncing_apis(SyncTypes.COMMUNITY,
                                       {'community_id': community_instance, 'member_id': member_id},
                                       {'click_state': click_states.DEFAULT})

        create_introduction_question_in_community(community_instance)
        post_purpose_collabcard_for_community(request, community_instance, member_id)
        post_master_introductions_for_community(community_id, member_id)
        post_member_directory_link(user_instance, community_instance)

        cohort_body = {
            'name': ALL_MEMBER_COHORT_TEXT,
            'member_ids': [member_id],
            'community_id': community_instance.id,
            'type': cohort_types.ALL_MEMBER,
        }

        from collabmates_api.cohort.cohort_impl import CohortImpl

        cohort_manager = CohortImpl(member_id)

        cohort_response = cohort_manager.create_cohort(cohort_body)

        if cohort_response.get('error_message'):
            error_logger.error(cohort_response)

        community_serializer = CommunitySerializerV1(community_instance, context={"current_user_id": member_id},
                                                     many=False).data

        return JsonResponse({'success': True, 'community': community_serializer})

    elif page == 3:

        try:
            community_instance = Community.objects.get(id=community_id)

            status = create_community_questions(res)
            if not status['success']:
                return JsonResponse(status)

            # updating the community level click state
            communityLevels.objects.filter(community=community_instance, level="Level 3").update(
                level_click_state=level_click_states.DIRECTORY_CREATED)

            send_notification_for_directory_creation.delay(community_id, time.time(), day=0)

        except Exception as e:

            context = get_error_context(False, e)
            return JsonResponse(context)

        community_serializer = CommunitySerializerV1(community_instance, context={"current_user_id": member_id},
                                                     many=False).data

        return JsonResponse({'success': True, 'community': community_serializer})


def create_community_questions(res):
    '''function to create community questions'''

    community_id = res['community_id']
    community_instance = Community.objects.get(id=community_id)

    question_count = 0
    current_question_count = communityQuestions.objects.filter(community=community_instance).count()

    # validating process
    for question in res['questions']:

        if question['state'] == question_states.CHOICE_SINGLE or question['state'] == question_states.CHOICE_MULTIPLE:
            if not question['value']:
                context = get_error_context(False, "The value data you are sending is wrong!!!")
                return context

    if 'questions' in res:
        for question in res['questions']:

            # counting the number of questions in order to show edit required to users
            question_count = question_count + 1

            if question['state'] == question_states.INTRODUCTION:
                question_filter = communityQuestions.objects.filter(question_state=question_states.INTRODUCTION,
                                                                    community=community_instance)
                if question_filter.exists():
                    question_instance = question_filter[0]
                    create_or_update_question_instances(question_instance, question, community_instance)

            elif question['state'] == question_states.MOBILE_NO:
                continue

            else:

                question_instance = communityQuestions()
                create_or_update_question_instances(question_instance, question, community_instance)

    # setting the state of community in order to make it editable and saving only those questions which are changed
    if current_question_count != question_count:
        update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                       {'community_id': community_instance, 'state': member_states.MEMBER},
                                       {'edit_required': True})

    return {'success': True}


def create_or_update_question_instances(question_instance, question, community_instance):
    '''function to create or update question instances'''

    # question_instance = question_instance
    question_instance.community = community_instance
    question_instance.question_title = question['question_title']
    question_instance.question_state = question['state']
    question_instance.value = question['value'] if 'value' in question else None
    question_instance.optional = question['optional']
    question_instance.help_text = question['help_text'] if 'help_text' in question else None
    question_instance.is_hidden = question['is_compulsory'] if 'is_compulsory' in question else False
    question_instance.field = question['field'] if 'field' in question else False
    question_instance.save()


def create_introduction_question_in_community(community_instance):
    '''function to create introduction question in community and mobile information'''

    help_text = ''
    field_filter = communityField.objects.filter(state=question_states.INTRODUCTION,
                                                 type=community_instance.type, sub_type=community_instance.sub_type)

    if field_filter.exists():
        help_text = field_filter[0].help_text

    if ModelUtilities.is_model_filter_exists(communityQuestions,
                                             {'community': community_instance}):
        return

    value_list = [{"min_chars": "50", "max_chars": "No limit"}]
    questions_instance = communityQuestions()
    questions_instance.community = community_instance
    questions_instance.question_title = field_filter[
        0].question_title if field_filter.exists() else "Introduce yourself"
    questions_instance.question_state = question_states.INTRODUCTION
    questions_instance.value = json.dumps(value_list)
    questions_instance.optional = False
    questions_instance.help_text = help_text
    questions_instance.is_hidden = False
    questions_instance.save()

    value_list = [{"answer_privacy": "Private"}]
    questions_instance = communityQuestions()
    questions_instance.community = community_instance
    questions_instance.question_title = "Phone No."
    questions_instance.question_state = question_states.MOBILE_NO
    questions_instance.value = json.dumps(value_list)
    questions_instance.optional = False
    questions_instance.help_text = ''
    questions_instance.is_hidden = True
    questions_instance.field = True
    questions_instance.save()


def post_member_directory_link(user_instance, community_instance):
    card_filter = Collabcard.objects.filter(user=user_instance, community=community_instance,
                                            type=card_types.CARD_MASTER_INTRO)

    if not card_filter.exists():
        return

    card_instance = card_filter[0]
    member_directory_link = url + "/community/" + str(community_instance.id) + "?source=members_directory"
    conversation = card_answers()
    conversation.answer = "Here is a link to view our member directory"
    conversation.card = card_instance
    conversation.user = user_instance
    conversation.community = community_instance
    conversation.internal_link = member_directory_link
    conversation.preview_community = community_instance
    conversation.preview_type = "directory"
    conversation.api_version = 1
    conversation.save()


def get_basic_directory_options(request):
    '''api to get basic diretory options'''

    type_id = request.GET.get('type')
    sub_type_id = request.GET.get('sub_type')

    if not type_id or not sub_type_id:
        context = get_error_context(False, "send type  sub_type  in get params")
        return JsonResponse(context)

    field_filter = communityField.objects.filter(type=type_id, sub_type=sub_type_id).order_by('-rank')

    questions = []
    for field in field_filter:
        # if field.state == question_states.GOOGLE_CITY_FETCH:
        #     continue
        temp = communityFieldSerializer(field)
        questions.append(temp)

    return JsonResponse({'questions': questions})


def send_follow_notifications_to_secret_room_participants(chatroom_id, participants_list):
    from .chatroom.chatroom_impl import ChatroomHelper

    for user_id in participants_list:
        req_dict = ChatroomHelper.get_follow_user_dict(user_id, chatroom_id,
                                                       is_tagged=False, status=True,
                                                       source="create_chatroom")
        collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)


@csrf_exempt
def create_poll(request):
    """function to create poll collabcard"""

    member_id = get_member_id_from_headers(request)
    res = json.loads(request.body)

    community_id = res['community_id']
    res['type'] = card_types.CARD_POLL  # poll chatroom type is 3

    is_member = Members.objects.filter(community_id=community_id,
                                       member_id=member_id).filter(Q(state=member_states.ADMIN) |
                                                                   Q(state=member_states.MEMBER))
    if not is_member:
        context = get_error_context(False, "You cannot create a chatroom")
        return JsonResponse(context)

    has_right = ModelUtilities.get_model_filter(userMemberRights,
                                                {'user_id': member_id, 'community_id': community_id,
                                                 'right__state': member_rights.MEMBER_RIGHT_CREATE_POLL})

    if not has_right:
        context = get_error_context(False, "You don't have the rights to create a poll")
        return JsonResponse(context)

    context = create_card_internal(member_id, community_id, res)

    # sending local
    member_data = {'member_id': member_id, 'current_user_id': member_id, 'state_instance': None}
    chatroom_obj = GetChatroomInstanceSerializer(context['card_instance'], context=member_data, many=False)

    context = {'success': True, 'collabcard': context['collabcard'], 'chatroom_local': chatroom_obj.data}

    send_sync_notification.delay({'chatroom_id': context['chatroom_local']['id'],
                                  'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

    collabcard = context.get('collabcard')
    start_time = TimeUtilities.convert_epoch_to_datetime_in_IST(collabcard.get('expiry_time'))

    args = [collabcard.get('id')]

    if collabcard.get('type') == CollabcardTypes.CARD_POLL:
        update_deferred_card_poll_updated_at_value.apply_async(args=args, kwargs={}, eta=start_time)

    return JsonResponse(context)


def create_chatroom_instance(res, community_instance, user_instance, has_auto_approve_right=False):
    '''function to create chatroom instance'''

    # getting the taaged members in chatroom
    tagged_members = get_tagged_members_list(community_instance.id, '', res['title'])
    tagged_member_list = tagged_members[0]
    res_text = tagged_members[1]
    card_type = int(res['type']) if 'type' in res else card_types.CARD_NORMAL

    card = Collabcard()
    card.title = res['title']
    card.community = community_instance
    card.user = user_instance
    card.type = card_type

    if card_type == card_types.CARD_PURPOSE:
        card.member_can_message = False

    card.image_count = res.get('image_count', 0)
    card.pdf_count = res.get('pdf_count', 0)

    attachment_count = card.image_count

    if attachment_count == 0 and card.pdf_count > 0:
        attachment_count = card.pdf_count

    card.attachment_count = attachment_count
    card.attachments_uploaded = False

    if attachment_count > 0 or card.pdf_count > 0:
        card.has_files = True

    card.date_time = res['date_time'] if ('date_time' in res) else 0
    card.duration = res['duration'] if ('duration' in res) else 0

    # for event card
    card.location = res['location'] if ('location' in res) else None
    card.location_lat = res['location_lat'] if ('location_lat' in res) else None
    card.location_long = res['location_long'] if ('location_long' in res) else None
    card.start_date = res['start_date'] if ('start_date' in res) else 0
    if res['type'] == card_types.CARD_POLL:
        # for saving poll expiry time
        expiry_time = res['expiry_time'] if ('expiry_time' in res) else 0
        if expiry_time > 0:
            # rounding off epoch time into exact minute
            # removing any extra seconds
            expiry_time = expiry_time // 1000
            expiry_time = expiry_time - (expiry_time % 60)

        card.end_date = expiry_time * 1000
    else:
        card.end_date = res['end_date'] if ('end_date' in res) else 0
    card.about = res['about'] if ('about' in res) else None
    card.co_hosts = json.dumps(res['co_hosts']) if ('co_hosts' in res) else None
    card.online_link = res['online_link'] if ('online_link' in res) else None

    # for poll card
    card.poll_type = res['poll_type'] if ('poll_type' in res) else None
    card.is_poll_anonymous = res['is_anonymous'] if ('is_anonymous' in res) else None
    card.allow_add_option = res['allow_add_option'] if ('allow_add_option' in res) else None
    if 'multiple_select' in res:
        card.multiple_select = res['multiple_select']
    if 'multiple_select_no' in res:
        card.multiple_select_no = res['multiple_select_no']
    if 'multiple_select_state' in res:
        card.multiple_select_state = res['multiple_select_state']

    # for chatroom header
    has_been_named = False
    if 'header' in res:
        card.header = res['header']
        has_been_named = True
        card.has_been_named = has_been_named

    else:

        res['title'] = res_text

        if len(res['title']) <= 30:
            card.header = res['title'][:30]
        else:
            card.header = res['title'][:27] + "..."

        if card.type == card_types.CARD_PURPOSE:
            card.header = get_chatroom_name(user_instance.userinfo.name, card)
            card.has_been_named = True
        elif card.type == card_types.CARD_INTRO:
            card.header = get_chatroom_name(user_instance.userinfo.name, card)
            card.has_been_named = True
        else:
            card.has_been_named = has_been_named

    if 'share_link' in res:
        card.share_link = res['share_link']
        og_tags = UriTagsImpl(res['share_link']).get_tags_from_uri()
        card.og_tags = json.dumps(og_tags)

    preview_utilities = PreviewUtilities()
    preview_utilities.set_preview_object(card, res, user_instance.id)

    is_intro_card = card_type == card_types.CARD_INTRO
    if not has_auto_approve_right and not is_intro_card:
        card.is_pending = True

    card.member_state = res['member_state']
    card.date_epoch = int(time.time())  # card creation time

    if card.type == card_types.CARD_PURPOSE or \
            card.type == card_types.CARD_MASTER_INTRO or \
            card.type == card_types.CARD_EVENT or \
            card.type == card_types.CARD_PUBLIC_EVENT:
        card.is_pinned = True
        card.pinning_time = TimeUtilities.current_time_in_milliseconds()

    if res.get("is_secret", False) and \
            res.get("secret_chatroom_participants", None):

        card.is_secret = True
        secret_chatroom_participants = res.get("secret_chatroom_participants", None)

        if secret_chatroom_participants:
            cm_list = set(Members.get_managers_list(community=community_instance))
            final_participants_list = list(set(secret_chatroom_participants) | cm_list)
            card.secret_chatroom_participants = json.dumps(final_participants_list)

    if res.get('auto_follow_done'):
        card.auto_follow_done = res.get('auto_follow_done')

    if res.get('include_members_later'):
        card.include_members_later = res.get('include_members_later')

    card.save()
    # add ownerflag here

    if card.type == card_types.CARD_POLL and has_auto_approve_right:
        send_chatroom_creation_notifications_and_mails(card, user_instance)

    if has_auto_approve_right or is_intro_card:
        # create relevant flags for first time conversation
        notification_list = [
            'mail_card_owner_inactivity'
        ]
        check_notification_flag(card.user.id, notification_list, card_id=card.id, community_id=None)

    # send notification to new chatroom posted
    if has_been_named:
        send_chatroom_creation_notifications_and_mails(card, user_instance)

    # sending notification to co-hosts
    if card.co_hosts:
        co_hosts = res['co_hosts']

        # making the co_host auto follow the card
        for host in co_hosts:
            req_dict = {
                'member_id': host,
                'collabcard_id': card.id,
                'status': True,
                'source': "create_chatroom"
            }
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

        send_notification_to_event_co_hosts.delay(co_hosts, card.id, card.title, user_instance.userinfo.name)

    # saving poll card details
    polls = res['polls'] if 'polls' in res else []  # res['poll'] if 'poll' in res else []

    for poll in polls:
        collabcardpolls_instance = CollabcardPolls()
        collabcardpolls_instance.card = card
        collabcardpolls_instance.user = user_instance
        collabcardpolls_instance.text = poll['text']
        collabcardpolls_instance.sub_text = poll['sub_text'] if ('sub_text' in poll) else None
        collabcardpolls_instance.image_url = poll['image_url'] if ('image_url' in poll) else None
        collabcardpolls_instance.save()

    if has_auto_approve_right or is_intro_card:
        # following the tagged member chatroom

        for user_id in tagged_member_list:
            req_dict = {
                'member_id': user_id,
                'collabcard_id': card.id,
                'status': True,
                'source': "create_chatroom",
                'is_tagged': True
            }
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

    return card


def create_card_internal(user_id, community_id, res):
    user_instance = User.objects.get(id=user_id)
    userinfo_instance = user_instance.userinfo

    try:
        community_instance = Community.objects.get(id=community_id)
    except:
        context = get_error_context(False, "the community id doesn't exists")
        return context

    res["member_state"] = None
    member_instance = Members.objects.filter(member_id=user_instance, community_id=community_instance)

    if member_instance.exists():
        res["member_state"] = member_instance[0].state

    card_type = int(res['type']) if 'type' in res else card_types.CARD_NORMAL
    is_intro_card = card_type == card_types.CARD_INTRO

    if res.get('is_secret', False) and res["member_state"] != member_states.ADMIN:
        context = get_error_context(False, "Only a CM can create a secret chatroom")
        return context

    has_auto_approve_right = check_member_auto_approve_right(user=user_instance,
                                                             community=community_instance)
    card_instance = create_chatroom_instance(res, community_instance, user_instance,
                                             has_auto_approve_right=has_auto_approve_right)

    # if the community is a ig community
    create_intro = False
    if 'create_intro' in res:
        create_intro = True

    collabcard = CollabcardSerializer(card_instance, user_id, community_instance, current_user_id=user_id)

    collabcard['date'] = datetime.today().strftime('%d-%m-%Y')

    # get user object's serialized json
    user_info_serializer = UserinfoSerializer(userinfo_instance)
    collabcard['member'] = user_info_serializer

    if create_intro:
        update_seen_status_for_new_user_in_chatroom(community_instance, user_instance)
        # intro-card notification
        send_chatroom_creation_notifications_and_mails(card_instance, user_instance)

    if has_auto_approve_right or is_intro_card or create_intro:
        # following the user created chatroom
        func_dict = {
            'member_id': user_id,
            'collabcard_id': card_instance.id,
            'status': True,
            'source': "create_chatroom"
        }

        set_expiry_time_none = card_instance.attachment_count > 0

        collabcard_follow_internal(func_dict, state=collabcard_states.COLLABCARD_STATE_SEEN,
                                   set_expiry_time_none=set_expiry_time_none)

        update_last_answer_id(card_instance.id, "")

        # creating a chatroom for the collabcard posted
        create_chatroom(card_instance=card_instance, user_instance=user_instance,
                        state=conversation_states.CONVERSATION_HEADER, current_user_id=user_id)

    # deleting the draft chatroom
    if 'draft_id' in res:
        conversationEngage.objects.filter(draft_id=res['draft_id']).delete()
        draftChatroom.objects.filter(id=res['draft_id']).delete()
        draftPolls.objects.filter(draft=res['draft_id']).delete()

    if has_auto_approve_right or is_intro_card or create_intro:
        # batch update for already existing users and saving their unseen count
        if card_instance.attachment_count == 0 and not card_instance.is_secret:
            set_chatroom_state_for_all_members_on_card_creation.delay(community_id, card_id=card_instance.id,
                                                                      function_called="create_card_internal")
        # update_last_unseen_in_engage_on_card_creation.delay(community_id=community_id)
        elif card_instance.is_secret:
            participants_list = json.loads(card_instance.secret_chatroom_participants)
            send_follow_notifications_to_secret_room_participants(card_instance.id, participants_list)

    else:
        update_pending_chatroom_count_for_promoters.delay(community_id)

    if card_instance.type == card_types.CARD_EVENT \
            or card_instance.type == card_types.CARD_PUBLIC_EVENT:
        schedule_chatroom_unpinning_after_event_completion(card_instance)

    context = {
        'collabcard': collabcard,
        'card_instance': card_instance
    }

    return context


def send_chatroom_creation_notifications_and_mails(card_instance, user_instance, set_default_unread_count=False):
    """ function to send mail and notifications for chatroom creations """

    # sending the mails and notification of simple chat rooms without files
    if not card_instance.has_files or \
            not card_instance.attachment_count > 0:
        send_chatroom_creation_notification(card_instance, user_instance,
                                            set_default_unread_count=set_default_unread_count)


def send_chatroom_creation_notification(card_instance, user_instance, set_default_unread_count=False):
    date_time = card_instance.end_date if card_instance.type == card_types.CARD_POLL else card_instance.date_time

    """
    do not send notifications for new intro room
    TODO: update logic with new intro room update
    """

    if card_instance.type == card_types.CARD_INTRO or card_instance.type == card_types.CARD_EVENT or \
            card_instance.type == card_types.CARD_PUBLIC_EVENT:
        return

    else:
        send_notification_for_new_collabcard_posted.delay(card_instance.community.id, card_instance.title,
                                                          user_instance.id, user_instance.userinfo.name,
                                                          type=card_instance.type,
                                                          date_time=date_time,
                                                          card_id=card_instance.id,
                                                          community_name=card_instance.community.name,
                                                          community_state=card_instance.community.hide_community,
                                                          set_default_unread_count=set_default_unread_count)


@csrf_exempt
def create_poll_draft_collabcard(request):
    if request.method == 'GET':
        return JsonResponse({'success': False, "error_message": "change HTTP message to POST"})

    res = json.loads(request.body)
    res['type'] = card_types.CARD_POLL
    response = create_draft_collabcard(request, res)
    return response


@csrf_exempt
def create_draft_collabcard(request, res=None):
    '''function to create draft collabcard'''

    member_id = get_member_id_from_headers(request)
    if not res:
        res = json.loads(request.body)

    community_id = res['community_id']

    community_instance = Community.objects.get(id=community_id)
    user_instance = User.objects.get(id=member_id)

    typ = int(res['type']) if 'type' in res else card_types.CARD_NORMAL

    if 'draft_id' in res:
        draft_chatroom_filter = draftChatroom.objects.filter(id=res['draft_id'])

        if draft_chatroom_filter.exists():
            card = draft_chatroom_filter[0]

            # deleting the chatrooms
            draftChatroomFiles.objects.filter(draft=card).delete()
        else:
            card = draftChatroom()
    else:
        card = draftChatroom()
    card.title = res['title']
    card.community = community_instance
    card.user = user_instance
    card.type = typ
    card.image_count = res['image_count'] if ('image_count' in res) else 0
    card.pdf_count = res['pdf_count'] if ('pdf_count' in res) else 0
    card.date_time = res['date_time'] if ('date_time' in res) else 0
    card.video_count = res['video_count'] if ('video_count' in res) else 0
    card.audio_count = res['audio_count'] if ('audio_count' in res) else 0
    card.duration = res['duration'] if ('duration' in res) else 0

    # for event card
    card.location = res['location'] if ('location' in res) else None
    card.location_lat = res['location_lat'] if ('location_lat' in res) else None
    card.location_long = res['location_long'] if ('location_long' in res) else None
    card.start_date = res['start_date'] if ('start_date' in res) else 0
    if res['type'] == card_types.CARD_POLL:
        # for saving poll expiry time
        card.end_date = res['expiry_time'] if ('expiry_time' in res) else 0
    else:
        card.end_date = res['end_date'] if ('end_date' in res) else 0
    card.about = res['about'] if ('about' in res) else None
    card.co_hosts = json.dumps(res['co_hosts']) if ('co_hosts' in res) else None
    card.online_link = res['online_link'] if ('online_link' in res) else None

    # for poll card
    card.poll_type = res['poll_type'] if ('poll_type' in res) else None
    card.is_poll_anonymous = res['is_anonymous'] if ('is_anonymous' in res) else None
    card.allow_add_option = res['allow_add_option'] if ('allow_add_option' in res) else None
    if 'multiple_select' in res:
        card.multiple_select = res['multiple_select']
    if 'multiple_select_no' in res:
        card.multiple_select_no = res['multiple_select_no']
    if 'multiple_select_state' in res:
        card.multiple_select_state = res['multiple_select_state']

    # for chatroom header
    card.header = res['header'] if ('header' in res) else card.title[:30]

    if 'share_link' in res:
        card.share_link = res['share_link']
        og_tags = UriTagsImpl(res['share_link']).get_tags_from_uri()
        card.og_tags = json.dumps(og_tags)

    preview_utilities = PreviewUtilities()
    preview_utilities.set_preview_object(card, res, user_instance.id)

    card.date_epoch = time.time()  # card creation time

    if res.get("is_secret", False) and \
            res.get("secret_chatroom_participants", None):
        card.is_secret = True
        card.secret_chatroom_participants = res.get("secret_chatroom_participants", None)

    card.save()

    # deleting the existing polls
    draftPolls.objects.filter(draft=card).delete()
    polls = res['polls'] if 'polls' in res else []  # res['poll'] if 'poll' in res else []
    for poll in polls:
        poll_instance = draftPolls()
        poll_instance.draft = card
        poll_instance.text = poll['text']
        poll_instance.sub_text = poll['sub_text'] if ('sub_text' in poll) else None
        poll_instance.save()

    chatroom = draftChatroomSerializer(card, user_instance)
    chatroom['updated_at'] = int(time.time())
    chatroom['is_draft'] = True
    engage_filter = conversationEngage.objects.filter(user=user_instance, draft=card)

    if not engage_filter.exists():
        instance = conversationEngage()
        instance.user = user_instance
        instance.draft = card
        instance.community = card.community
        instance.created_at = time.time()
        instance.updated_at = time.time()
        instance.save()
    else:
        engage_filter.update(updated_at=time.time())

    return JsonResponse({'success': True, "chatroom": chatroom})


def create_chatroom(card_instance, user_instance, state, current_user_id=None, answer="", topic_text=None, **kwargs):
    '''function to create chat-room and perform follow unfollow operations'''
    # handling answer states

    if not kwargs.get('community_instance'):
        community_instance = card_instance.community

    else:
        community_instance = kwargs.get('community_instance')

    if not answer:

        user_name = user_instance.userinfo.name

        community_id = community_instance.id
        community_name = community_instance.name

        user_route = f"route://member_profile/{user_instance.id}?member_id={user_instance.id}"
        user_name = f"<<{user_name}|{user_route}&community_id={community_id}>>"

        if state == conversation_states.CONVERSATION_HEADER:

            community_route = "route://community?community_id=" + str(community_id)
            community_name = "<<" + str(community_name) + "|" + community_route + ">>"

            if card_instance.is_secret:
                secret_participants_count = len(json.loads(card_instance.secret_chatroom_participants))

                prefix = "others"
                if secret_participants_count == 2:
                    prefix = "other"

                answer = f"{user_name} started this secret chatroom with {secret_participants_count - 1} {prefix}"

            elif (card_instance.type == card_types.CARD_POLL):
                answer = user_name + " started this poll in " + community_name

            else:
                answer = user_name + " started this chatroom in " + community_name

        elif state == conversation_states.CONVERSATION_FOLLOW:
            answer = user_name + " followed this chatroom"

        elif state == conversation_states.CONVERSATION_UNFOLLOW:
            answer = user_name + " unfollowed this chatroom"

        elif state == conversation_states.CONVERSATION_COMMUNITY_EDIT:
            answer = user_name + " edited community purpose"

        elif state == conversation_states.CONVERSATION_ADD_PARTICIPANT:
            if current_user_id is not None:
                current_user_name = Userinfo.get_username(current_user_id)

                current_user_route = f"route://member_profile/{current_user_id}?member_id={current_user_id}"
                encoded_current_user_name = f"<<{current_user_name}|{current_user_route}&community_id={community_id}>>"

                answer = f"{encoded_current_user_name} added {user_name}"

        elif state == conversation_states.CONVERSATION_LEAVE_CHATROOM:
            answer = user_name + " left this chatroom"

        elif state == conversation_states.CONVERSATION_REMOVED_FROM_CHATROOM:
            if current_user_id is not None:
                current_user_name = Userinfo.get_username(current_user_id)

                current_user_route = f"route://member_profile/{current_user_id}?member_id={current_user_id}"
                encoded_current_user_name = f"<<{current_user_name}|{current_user_route}&community_id={community_id}>>"

                answer = f"{encoded_current_user_name} removed {user_name}"

        elif state == conversation_states.CHATROOM_TOPIC:
            if topic_text is not None:
                answer = f"{user_name} {topic_text}"

    if answer:
        instance = card_answers()
        instance.answer = answer
        instance.card = card_instance
        instance.user = user_instance
        instance.community = community_instance
        instance.state = state
        instance.save()

    if state == conversation_states.CONVERSATION_HEADER and \
            card_instance.type == card_types.CARD_INTRO:
        community_id = card_instance.community_id
        member_id = user_instance.id

        post_owner_message_template_in_intro_room(card_instance.community_id, member_id)

        args = [community_id, member_id]
        # runs after 5 minutes, expires after 30 minutes
        check_owner_template_posted.apply_async(args=args, kwargs={},
                                                countdown=5 * 60, expires=30 * 60)


def create_chatroom_state_instance(card_instance, user_instance, state=collabcard_states.COLLABCARD_STATE_SEEN,
                                   expire_at=None, external_seen=True, is_guest=False, source=None, follow_status=False,
                                   mute_status=False, is_tagged=False, external_follow=False,
                                   attending_status=False, noti_state=noti_states.ALL_MESSAGES, **kwargs):
    '''function to create chatroom state instance'''

    try:
        collabcard_state_instance = collabcardState()
        collabcard_state_instance.card = card_instance
        collabcard_state_instance.community = card_instance.community
        collabcard_state_instance.user = user_instance
        collabcard_state_instance.state = state
        collabcard_state_instance.created_at = time.time()
        collabcard_state_instance.updated_at = time.time()
        collabcard_state_instance.external_seen = external_seen
        collabcard_state_instance.attending_status = attending_status
        collabcard_state_instance.follow_status = follow_status
        collabcard_state_instance.mute_status = mute_status
        collabcard_state_instance.is_tagged = is_tagged
        collabcard_state_instance.is_guest = is_guest
        collabcard_state_instance.source = source
        collabcard_state_instance.noti_state = noti_state
        collabcard_state_instance.external_follow = external_follow

        collabcard_state_instance.save()
        return collabcard_state_instance
    except Exception as e:
        info_logger.info(e.args)
        info_logger.info("Duplicate key creation in collabcardState table")
        if "function_called" in kwargs:
            info_logger.info(f"called function ---> {kwargs['function_called']}")
        info_logger.info(str(card_instance.id))
        info_logger.info(str(user_instance.id))


def create_chatroom_engagement(card_instance, user_instance, func_dict=None, member_state=0):
    '''function to create and update chatroom engagements '''

    instance_list = conversationEngage.objects.filter(card=card_instance, user=user_instance)

    rights_list = None

    if member_state == member_states.ADMIN:
        rights_list = json.dumps(member_rights.ALL_MEMBER_RIGHTS)
    elif member_state == member_states.MEMBER or member_state == member_states.PROFILE_UNAVAILABLE:
        rights_list = json.dumps(member_rights.DEFAULT_MEMBER_RIGHTS)

    if not instance_list:
        instance = conversationEngage()
        instance.card = card_instance
        instance.user = user_instance
        instance.community = card_instance.community
        instance.last_conversation = None
        instance.unseen_count = 0
        instance.rights_list = rights_list
        instance.created_at = time.time()
        instance.updated_at = time.time()
        instance.save()
    else:
        instance = instance_list[0]
        instance_list.last_conversation = None
        instance_list.unseen_count = 0
        instance.rights_list = rights_list
        instance.updated_at = time.time()
        instance.save()

    update_member_rights_in_conversation_engage.delay(card_instance.community.id, user_instance.id)


def update_seen_status_for_new_user_in_chatroom(community_instance, user_instance):
    collabcard_filter = Collabcard.objects.filter(community=community_instance,
                                                  is_pending=False, is_deleted=False,
                                                  is_secret=False).order_by('id')

    collabcard_filter = collabcard_filter.exclude(is_private=True, type=card_types.CARD_DIRECT_MESSAGE)

    chatroom_ids = []

    for card_instance in collabcard_filter:

        state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)

        if not state_filter.exists():
            last_conversation = card_answers.objects.filter(card=card_instance, state=conversation_states.ANSWER).last()

            if last_conversation:

                created_at = last_conversation.created_at

                if TimeUtilities.is_epoch_in_milliseconds(created_at):
                    created_at = TimeUtilities.convert_milliseconds_to_sec(created_at)

                expire_at = created_at + HOURS_24
            else:
                expire_at = card_instance.date_epoch + HOURS_24

            if card_instance.auto_follow_done:
                chatroom_ids.append(card_instance.id)

            follow_status = card_instance.include_members_later and card_instance.auto_follow_done

            create_chatroom_state_instance(card_instance, user_instance, expire_at=expire_at,
                                           follow_status=follow_status,
                                           function_called="update_seen_status_for_new_user_in_chatroom")

    from collabmates_api.chatroom.chatroom_impl import ChatroomHelper
    ChatroomHelper.create_card_engagements_for_home_screen_for_auto_follow_all_members_with_chatroom_list.delay(
        chatroom_ids, user_instance.id, community_instance.id, member_state=0)

    update_last_unseen_in_engage(user=user_instance, community=community_instance)

    print("updating the seen status")


@csrf_exempt
def chatroom_mute(request):
    '''function to mute and unmute chatroom'''
    chatroom_id = request.POST.get('chatroom_id')
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not card_instance:
        context = ResponseUtilities.get_view_impl_error_context('Invalid chatroom id',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    member_id = get_member_id_from_headers(request)

    user_instance = ModelUtilities.get_user_instance_or_none(member_id)

    if not user_instance:
        context = ResponseUtilities.get_view_impl_error_context('Invalid member id',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    value = request.POST.get('value', False)
    collabcard_state_filter = collabcardState.objects.filter(card_id=chatroom_id, user=member_id)

    mute_status = False

    if value == "true":
        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       {'card': chatroom_id, 'user': member_id},
                                       {'mute_status': True})
        mute_status = True

    elif collabcard_state_filter.exists():
        instance = collabcard_state_filter[0]
        instance.mute_status = False
        instance.updated_at = time.time()
        instance.external_follow = True if instance.is_tagged else False
        instance.is_tagged = False
        instance.save()

    send_sync_notification.delay({'chatroom_id': chatroom_id,
                                  'member_id': member_id,
                                  'sync_notification_type': SyncNotificationTypes.SINGLE_MEMBER.value})

    ElasticSearchSync.update_chatroom_for_user.delay(chatroom_id, member_id)

    return JsonResponse({'success': True})


@csrf_exempt
def chatroom_rename(request):
    chatroom_id = request.POST.get('chatroom_id')
    first_time_rename = request.POST.get('first_time_rename')

    member_id = get_member_id_from_headers(request)

    user_instance = ModelUtilities.get_user_instance_or_none(member_id)

    if not user_instance:
        context = ResponseUtilities.get_view_impl_error_context('Invalid member id',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    chatroom_name = request.POST.get("header", None)

    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not card_instance:
        context = ResponseUtilities.get_view_impl_error_context('Invalid chatroom id',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    card_instance.header = chatroom_name

    if first_time_rename == "true":
        card_instance.has_been_named = True
        card_instance.save()

        send_chatroom_creation_notifications_and_mails(card_instance, user_instance)

    else:
        card_instance.save()

    update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                   {'card': card_instance},
                                   {})
    chatroom_preview_update_count = update_models_for_syncing_apis(SyncTypes.CONVERSATION,
                                                                   {'preview_chatroom': card_instance,
                                                                    'preview_type': "chatroom"},
                                                                   {})

    if chatroom_preview_update_count:
        preview_chatroom_id = card_instance.id
        update_multiple_previews_in_chatroom.delay({'chatroom_id': preview_chatroom_id})

    send_sync_notification.delay({'chatroom_id': chatroom_id,
                                  'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

    chatroom_name = chatroom_name.strip() if chatroom_name else chatroom_name

    ElasticSearchSync.update_chatroom_name.delay(chatroom_id, chatroom_name.strip())

    send_chatroom_updated_analytics_data.delay(chatroom_id,
                                               int(member_id),
                                               {'chatroom_renamed': True})

    return JsonResponse({"success": True})


@csrf_exempt
def chatroom_delete(request):
    '''api to delete the chatroom '''

    if request.method == 'GET':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'})

    member_id = get_member_id_from_headers(request)
    chatroom_id = request.POST.get('chatroom_id', None)

    draft_id = request.POST.get('draft_id')
    tag_id = request.POST.get('tag_id', None)
    reason = request.POST.get('reason', None)
    disallow_create_chatroom = request.POST.get('disallow_create_chatroom', None)

    context = delete_chatroom_async(member_id,
                              chatroom_id=chatroom_id,
                              draft_id=draft_id,
                              tag_id=tag_id,
                              reason=reason,
                              disallow_create_chatroom=disallow_create_chatroom)

    return JsonResponse(context)

@shared_task
def delete_chatroom_async(member_id, chatroom_id=None, draft_id=None,
                    tag_id=None, reason=None, disallow_create_chatroom=None):

    if disallow_create_chatroom is not None:
        disallow_create_chatroom = disallow_create_chatroom.lower() == "true"

    if draft_id:
        draftChatroom.objects.filter(id=draft_id).delete()
        return {'success': True}

    if not chatroom_id:
        context = get_error_context(False, "send the chatroom_id in post params")
        return context

    try:
        collabcard_instance = Collabcard.objects.get(id=chatroom_id)
        community_instance = collabcard_instance.community
        community_id = community_instance.id

        card_creator = collabcard_instance.user
        current_user_instance = User.objects.get(pk=member_id)

        is_promoter = False
        member_instance = Members.objects.filter(member_id=member_id, community_id=community_instance,
                                                 state=member_states.ADMIN)
        if member_instance.exists():
            is_promoter = True

        is_card_creator = card_creator.id == int(member_id)

        if not is_card_creator and not is_promoter:
            context = get_error_context(False,
                                        "You are not the card creator or promoter. you cannot delete this chatroom")
            return context

        if not is_card_creator:
            if not check_admin_delete_right(user=current_user_instance, community=community_instance):
                context = get_error_context(False, "You do not have right to delete this chatroom")
                return context

        # updating collabcard delete status
        update_collabcard_delete_status(collabcard_instance, current_user_instance, is_promoter,
                                        card_creator, reason, tag_id)

        conversationEngage.objects.filter(card=collabcard_instance).delete()

        # checking is_owner bcz, owner will be by default a CM
        member_is_promoter = Members.objects.filter(community_id=community_instance,
                                                    member_id=card_creator,
                                                    state=member_states.ADMIN).exists()

        if disallow_create_chatroom and \
                not member_is_promoter:
            remove_member_create_room_right(card_creator, community_instance,
                                            current_user_id=member_id)

            save_moderation_history(user=card_creator, community=community_instance,
                                    moderation_by=current_user_instance,
                                    type=moderation_history_types.MEMBER_PERMISSION_EDITED)

            update_rights_history_for_creation_rights_removed.delay(member_id,
                                                                    community_instance.id,
                                                                    card_creator.id)

        # updates last seen count after card is deleted
        update_last_unseen_in_engage_on_card_creation.delay(community_id)

        send_chatroom_deleted_analytics_data.delay(chatroom_id, int(member_id))

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       {'card': collabcard_instance},
                                       {})

        if is_promoter:
            send_notification_for_chatroom_deleted.delay(member_id, chatroom_id, community_id)

        send_sync_notification.delay({'chatroom_id': chatroom_id,
                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

        cache_dict = {
            'chatroom_id': collabcard_instance.id,
            'community_id': community_id,
            'pin_value': False
        }

        update_community_pin_chatrooms_list_in_cache.delay(cache_dict)

        # update elastic search
        ElasticSearchSync.delete_chatroom.delay(chatroom_id)

    except Exception as e:
        context = get_error_context(False, str(e))
        return context

    info_logger.info(
        f"DELETE_CHATROOM_API - current user id = {member_id}, card creator id = {card_creator.id}, disallow_create_chatroom = {disallow_create_chatroom}")
    return {'success': True}


def update_collabcard_delete_status(collabcard_instance, current_user_instance, is_promoter,
                                    card_creator, reason=None, tag_id=None):
    tag_instance = None
    if tag_id:
        tag = Report_Tags.objects.filter(tag_id=tag_id)
        if tag.exists():
            tag_instance = tag[0]

    # delete_card = Collabcard.objects.filter(pk=chatroom_id)
    # delete_status = delete_card.update(is_deleted=True, deleted_by_user=current_user_instance,
    #                                    deleted_by_user_state=deleted_by_user_state, deleted_by_text=deleted_by_text,
    #                                    tag=tag_instance, reason=reason)

    collabcard_instance.is_deleted = True
    collabcard_instance.deleted_by_user = current_user_instance
    collabcard_instance.tag = tag_instance
    collabcard_instance.reason = reason
    collabcard_instance.updated_time = time.time()
    collabcard_instance.save()

    if int(current_user_instance.id) == int(collabcard_instance.user.id):
        action_taken = report_Action_Types.CHATROOM_DELETED_BY_CREATOR
        snackbar_manager = SnackbarImpl()
        snackbar_dict = {
            'chatroom_id': collabcard_instance.id,
            'type': HomeSnackbarType.CHATROOM_DELETED_BY_CREATOR
        }
        snackbar_manager.create_snackbar(snackbar_dict)

    else:
        action_taken = report_Action_Types.CHATROOM_DELETED_BY_CM
        snackbar_manager = SnackbarImpl()
        snackbar_dict = {
            'chatroom_id': collabcard_instance.id,
            'chatroom_creator_id': collabcard_instance.user.id,
            'type': HomeSnackbarType.CHATROOM_DELETED_BY_COMMUNITY_MANAGER,
            'tag_id': tag_id,
            'reason': reason
        }
        snackbar_manager.create_snackbar(snackbar_dict)

    check_reports_and_update_action.delay(action_taken_by=current_user_instance.id,
                                          action_taken=action_taken,
                                          chatroom_id=collabcard_instance.id, action_taken_tag_id=tag_id,
                                          action_taken_reason=reason)

    info_logger.info("successfully updated chatroom delete status")


def fetch_deleted_chatroom(request):
    """ function to fetch deleted chatrooms of a user"""
    # logic has to be updated according to new flow of card deletion
    return JsonResponse({"deleted_chatrooms": []})


def update_activity_in_chatroom(card_instance, user_instance):
    '''function to update activities in chatrooms

    in collabcardState table and conversationEngage table'''
    engage_filter = conversationEngage.objects.filter(card=card_instance, user=user_instance)
    if engage_filter.exists():
        engage_instance = engage_filter[0]
        unread_count = engage_instance.unseen_count
        if unread_count > 0:

            state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)

            if state_filter.exists():
                update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                               {'card': card_instance, 'user': user_instance},
                                               {})


def get_expiry_time_of_chatroom(card_state_instance=None):
    '''function to get expiry time of chatroom'''
    expiry_time = None

    return expiry_time


@csrf_exempt
def set_chatroom_active(request):
    '''api to make chatroom active'''

    return JsonResponse({"success": True})


def get_branch_links_for_community_share(user_instance, community_instance, platform_code, version_code):
    is_promoter = False
    is_owner = False
    is_member = False
    member_filter = Members.objects.filter(member_id=user_instance, community_id=community_instance)

    user_has_approve_right = False
    member_invite_private_right = False
    community_id = community_instance.id
    member_id = user_instance.id
    aj = community_id

    if member_filter:
        member_instance = member_filter[0]

        if member_instance.state == member_states.ADMIN:
            is_promoter = True

        if member_instance.state in [member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]:
            is_member = True

        is_owner = member_instance.is_owner

        if is_promoter or is_owner:
            user_has_approve_right = check_admin_approve_right(user_instance, community_instance)

        else:
            member_invite_private_right = userMemberRights.check_member_invite_private_right(user_instance,
                                                                                             community_instance)

        if user_has_approve_right:
            aj = generate_private_link(community_instance=community_instance,
                                       promoter_instance=user_instance,
                                       just_send_aj=True)
            branch_links = create_community_branch_links(community_id, member_id, platform_code, version_code, aj)

        else:
            branch_links = create_community_branch_links(community_id, member_id, platform_code, version_code)

    else:
        branch_links = create_community_branch_links(community_id, member_id, platform_code, version_code)

    share_context = {
        'branch_links': branch_links,
        'is_owner': is_owner,
        'is_promoter': is_promoter,
        'user_has_approve_right': user_has_approve_right,
        'member_invite_private_right': member_invite_private_right,
        'aj': aj
    }
    return share_context


def get_branch_links_for_community_share_v1(user_instance, community_instance, platform_code=None, version_code=None):
    is_promoter = False
    is_owner = False
    is_member = False
    member_filter = Members.objects.filter(member_id=user_instance, community_id=community_instance)

    user_has_approve_right = False
    member_invite_private_right = False
    community_id = community_instance.id
    member_id = user_instance.id
    aj = community_id

    if member_filter:
        member_instance = member_filter[0]

        if member_instance.state == member_states.ADMIN:
            is_promoter = True

        if member_instance.state in [member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]:
            is_member = True

        is_owner = member_instance.is_owner

        if is_promoter or is_owner:
            user_has_approve_right = check_admin_approve_right(user_instance, community_instance)

        aj = generate_private_link(community_instance=community_instance,
                                   promoter_instance=user_instance,
                                   just_send_aj=True)
        branch_links = create_community_branch_links(community_id, member_id, platform_code, version_code, aj)

    else:
        branch_links = create_community_branch_links(community_id, member_id, platform_code, version_code)

    share_context = {
        'branch_links': branch_links,
        'is_owner': is_owner,
        'is_promoter': is_promoter,
        'user_has_approve_right': user_has_approve_right,
        'aj': aj
    }
    return share_context


def fill_share_context_for_paid_community_v2(community_instance, share_context, community_share):
    branch_links = share_context['branch_links']
    aj = share_context['aj']
    community_name = community_instance.name

    if len(share_context) <= 0:
        return

    community_share['public_link'] = branch_links[0]['url']

    community_share['public_link_text'] = SHARE_TEXT_ADMIN_PUBLIC_PAID_COMMUNITY % (
        community_name, community_share['public_link'])

    if share_context['user_has_approve_right']:
        community_share['private_link'] = branch_links[1]['url']
        community_share['private_link_text'] = SHARE_TEXT_ADMIN_PRIVATE_PAID_COMMUNITY_V2 % (
            community_name, branch_links[1]['url'], aj)

    else:
        community_share['public_link'] = branch_links[0]['url']
        community_share['public_link_text'] = SHARE_TEXT_MEMBER_PUBLIC % (
            community_name, community_share['public_link'])


def fill_share_context_for_paid_community(community_instance, share_context, community_share):
    branch_links = share_context['branch_links']
    aj = share_context['aj']
    community_name = community_instance.name

    if len(share_context) <= 0:
        return

    community_share['public_link'] = branch_links[0]['url']

    community_share['public_link_text'] = SHARE_TEXT_ADMIN_PUBLIC_PAID_COMMUNITY % (
        community_name, community_share['public_link'])

    if share_context['user_has_approve_right']:
        community_share['private_link'] = branch_links[1]['url']
        community_share['private_link_text'] = SHARE_TEXT_ADMIN_PRIVATE_PAID_COMMUNITY % (
            community_name, branch_links[1]['url'], aj)

        community_share['private_link_members_directory'] = branch_links[2]['url']
        private_link_text_members_directory = PRIVATE_LINK_TEXT_MEMBERS_DIRECTORY_1 % (
            community_name, branch_links[2]['url'], aj)

        community_share['private_link_text_members_directory'] = private_link_text_members_directory

    else:
        community_share['public_link'] = branch_links[0]['url']
        community_share['public_link_text'] = SHARE_TEXT_MEMBER_PUBLIC % (
            community_name, community_share['public_link'])


def fill_share_context_for_unpaid_community_v2(community_instance, share_context, community_share):
    branch_links = share_context['branch_links']
    aj = share_context['aj']
    community_name = community_instance.name

    if len(share_context) <= 0:
        return

    community_share['private_link'] = branch_links[1]['url']

    if share_context['user_has_approve_right']:
        members_count = get_members_count_in_community(community_instance.id)

        if members_count <= 10:
            community_share['private_link_text'] = PRIVATE_LINK_TEXT_ADMIN_1_V2 % (
                community_name, branch_links[1]['url'], aj)

        else:
            community_share['private_link_text'] = PRIVATE_LINK_TEXT_ADMIN_2_V2 % (
                community_name, branch_links[1]['url'], aj)

    else:
        community_share['private_link_text'] = SHARE_TEXT_MEMBER % (
            community_name, community_share['private_link'], aj)


def fill_share_context_for_unpaid_community(community_instance, share_context, community_share):
    branch_links = share_context['branch_links']
    aj = share_context['aj']
    community_name = community_instance.name

    if len(share_context) <= 0:
        return

    community_share['public_link'] = branch_links[0]['url']

    community_share['public_link_text'] = SHARE_TEXT_ADMIN % (
        community_name, community_share['public_link'], aj)

    if share_context['user_has_approve_right']:
        community_share['private_link'] = branch_links[1]['url']
        members_count = get_members_count_in_community(community_instance.id)

        if members_count <= 10:
            community_share['private_link_text'] = PRIVATE_LINK_TEXT_ADMIN_1 % (
                community_name, branch_links[1]['url'], aj)

        else:
            community_share['private_link_text'] = PRIVATE_LINK_TEXT_ADMIN_2 % (
                community_name, branch_links[1]['url'], aj)

        community_share['private_link_members_directory'] = branch_links[2]['url']
        private_link_text_members_directory = PRIVATE_LINK_TEXT_MEMBERS_DIRECTORY_1 % (
            community_name, branch_links[2]['url'], aj)

        community_share['private_link_text_members_directory'] = private_link_text_members_directory

    else:
        community_share['public_link'] = branch_links[0]['url']
        community_share['public_link_text'] = SHARE_TEXT_MEMBER % (
            community_name, community_share['public_link'], aj)


def fetch_share_url(request):
    '''api to share the url of community and chatroom'''
    member_id = get_member_id_from_headers(request)

    api_key = RequestUtilities.get_api_key_from_headers(request)

    chatroom_id = request.GET.get('chatroom_id')
    community_id = request.GET.get('community_id')
    domain_url = request.GET.get('domain')
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)
    api_type = NumberUtilities.get_integer_from_string(request.GET.get('api_type'), return_default=api_types.Non_SDK)

    user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

    is_cm_onboarding_enabled = cm_onboarding_version_check(platform_code, version_code)

    if not user_instance:
        context = ResponseUtilities.get_view_impl_error_context("Invalid member id",
                                                                status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(**context)

    if chatroom_id:
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            context = ResponseUtilities.get_view_impl_error_context("Invalid chatroom id",
                                                                    status_codes.HTTP_400_BAD_REQUEST)

            return JsonResponse(**context)

        if card_instance.type == card_types.CARD_MASTER_INTRO or card_instance.type == card_types.CARD_PURPOSE:
            context = ResponseUtilities.get_view_impl_error_context("You cannot generate link for master or purpose "
                                                                    "chatrooms",
                                                                    status_codes.HTTP_400_BAD_REQUEST)

            return JsonResponse(**context)

        chatroom_share = {}

        if not card_instance.is_secret:
            share = get_share_url_text(card_instance, domain_url=domain_url, api_type=api_type)
            chatroom_share['share_url'] = share['share_url']
            chatroom_share['creator_share_url'] = share['creator_share_url']
            chatroom_share['link_created_at'] = share['link_created_at']

        else:
            chatroom_share['share_url'] = ''
            chatroom_share['creator_share_url'] = ''
            chatroom_share['link_created_at'] = ''

        return JsonResponse({'chatroom_share': chatroom_share, 'success': True})

    if community_id or api_key:

        community_instance = validate_community_id_or_api_key(community_id, api_key)

        if community_instance.get('error_message'):
            context = ResponseUtilities.get_view_impl_error_context(community_instance.get('error_message'),
                                                                    status_codes.HTTP_400_BAD_REQUEST)

            return JsonResponse(**context)

        community_instance = community_instance.get('community_instance')

        community_share = {}

        if is_cm_onboarding_enabled:
            share_context = get_branch_links_for_community_share_v1(user_instance, community_instance, platform_code,
                                                                    version_code)

            if community_instance.is_paid:
                fill_share_context_for_paid_community_v2(community_instance, share_context, community_share)

            else:
                fill_share_context_for_unpaid_community_v2(community_instance, share_context, community_share)

        else:
            share_context = get_branch_links_for_community_share(user_instance, community_instance, platform_code,
                                                                 version_code)

            if community_instance.is_paid:
                fill_share_context_for_paid_community(community_instance, share_context, community_share)

            else:
                fill_share_context_for_unpaid_community(community_instance, share_context, community_share)

        if not community_share:
            context = ResponseUtilities.get_view_impl_error_context("Error in generating link",
                                                                    status_codes.HTTP_400_BAD_REQUEST)

            return JsonResponse(**context)

        return JsonResponse({'community_share': community_share, 'success': True})

    return JsonResponse(**ResponseUtilities.get_view_impl_error_context("Invalid request",
                                                                        status_codes.HTTP_400_BAD_REQUEST))


@csrf_exempt
def collabcard_poll_version_1(request):
    """ function to update polls of a card for user """
    if request.method == 'POST':
        collabcard_id = request.POST.get('collabcard_id', None)

        if not collabcard_id:
            context = get_error_context(success=False, error_message="Send the correct collabcard id")
            return JsonResponse(context)

        member_id = get_member_id_from_headers(request)
        if request.user.is_authenticated and not get_request_type(request):
            member_id = request.user.id
        if not member_id:
            context = get_error_context(success=False, error_message="Send member id in headers")
            return JsonResponse(context)

        poll_ids = request.POST.get('poll_ids', None)
        if not poll_ids:
            context = get_error_context(success=False, error_message="Send array of polls_id in post params")
            return JsonResponse(context)

        user_instance = User.objects.get(pk=member_id)

        card_instance = Collabcard.objects.get(pk=collabcard_id)

        poll_ids = unquote(poll_ids)
        poll_ids = json.loads(poll_ids)
        print(poll_ids)

        # deleting the previous votes
        memberpolls_filter = MemberPollVotes.objects.filter(card=card_instance, user=user_instance)
        memberpolls_filter.delete()

        for poll_id in poll_ids:
            vote_poll(poll_id, card_instance, user_instance, collabcard_id)

        # if not str(member_id) == str(card_instance.user.id):
        #     send_poll_or_event_notification.delay(card_id=collabcard_id, user_id=member_id)

        # autofollowing the collabcard
        function_dict = {
            'member_id': user_instance.id,
            'collabcard_id': card_instance.id,
            'status': True
        }
        collabcard_follow_internal(function_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)
        return JsonResponse({"success": True})

    return JsonResponse({"success": False})


def vote_poll(poll_id, card_instance, user_instance, collabcard_id):
    '''function to vote on poll'''
    poll_instance = CollabcardPolls.objects.get(pk=poll_id)

    # check if user has already voted for the card or not

    # if not voted, create new row for user and card with opted poll by user
    memberpolls_instance = MemberPollVotes()
    memberpolls_instance.card = card_instance
    memberpolls_instance.poll = poll_instance
    memberpolls_instance.user = user_instance
    memberpolls_instance.save()

    # update the card answer text according to no of polls
    update_poll_card_text(collabcard_id)


def update_poll_card_text(card_id):
    """ function to update the answer text of card when someone polls in the card """

    poll_filter = MemberPollVotes.objects.filter(card=card_id).order_by('-id')
    total_polls = set()

    for poll in poll_filter:
        total_polls.add(poll.user)

    total_polls = list(total_polls)
    card = Collabcard.objects.get(pk=card_id)
    poll_text = ''
    total_polls_count = len(total_polls)

    if total_polls_count <= 0:
        card.answer_text = poll_text
        card.save()
        return

    elif total_polls_count == 1:
        user_names = total_polls[0].userinfo.name

    elif total_polls_count == 2:
        user_names = total_polls[0].userinfo.name + " and " + total_polls[1].userinfo.name

    else:
        user_names = total_polls[0].userinfo.name + ", " + total_polls[1].userinfo.name + " & " + str(
            total_polls_count - 2) + " others"

    poll_text += user_names + " voted on this poll"
    card.answer_text = poll_text
    card.polls_count = total_polls_count
    card.save()


def fetch_info(request):
    '''function to send info-text  for event card'''
    response = {}

    response['online_event'] = {
        'header': "Guidelines for online event url",
        'sub_header': "Use the following guidelines to best use the online event url:",

        'title_1': "What are online events",
        'sub_title_1': "Online events are the events that can be performed via web video conferencing tools. There are plenty of video conferencing tools out there like Zoom, Hangout, Skype etc.",

        'title_2': "Recommended online platforms",
        'sub_title_2': "Recommended tools are those where joining the conference is easier and can handle the number of expected participants joining your event online.",

        'title_3': "Link to online event",
        'sub_title_3': "Make sure that you provide the video conferencing urls and not the event description page from other platforms."
    }

    response['event_privacy'] = {

        'header': "Event Privacy",
        'sub_header': "An event can either be a private or a public event.",

        'title_1': "Private Event",
        'sub_title_1': "Only verified community mambers can see all the details. A non-member trying to access the event information would have to join the community first.",

        'title_2': "Public Event",
        'sub_title_2': "Anyone with the link can see this event. Attending Member’s details would be available only to the users who join the community.",

    }

    response['banner'] = {
        'header': "Guidelines for image files",
        'sub_header': "Use the following guidelines to get the highest quality event image:",

        'title_1': "Dimensions",
        'sub_title_1': "Find at least a 2160 x 1080px (2:1 ratio) image.",

        'title_2': "File Type",
        'sub_title_2': "Pictures with file types JPEG, BMP, PNG, or GIF work best.",

        'title_3': "File Size",
        'sub_title_3': "Use a photo that's not larger than 10MB.",

        'title_4': "General",
        'sub_title_4': "Avoid images that have a lot of text, logos, and fliers.",
    }

    return JsonResponse(response)


# /api/add_admin/community_id
@csrf_exempt
def add_admin(request, community_id):
    '''api to add admin directly in a community'''

    try:

        info_logger.info("\n")
        info_logger.info("----------------add admin api------------------")

        res = json.loads(request.body)

        member_id = res['member_id']

        action_required = False
        promoter_filter = Members.objects.filter(member_id=member_id, community_id=community_id)
        if promoter_filter.exists():
            action_required = promoter_filter[0].actions_required

        nominated_admin = res['nominate_member_ids']

        if len(nominated_admin) > 0:
            nominated_admin = nominated_admin[0]

        member_filter = Members.objects.filter(member_id=nominated_admin, community_id=community_id)

        engage_filter = Member_Engage.objects.filter(member_id=nominated_admin, community_id=community_id)

        info_logger.info(res)

        update_status_member = member_filter.update(state=member_states.ADMIN, updated_at=time.time(),
                                                    actions_required=action_required)

        update_status_engage = engage_filter.update(member_state=member_states.ADMIN)

        info_logger.info(update_status_member)

        user_instance = User.objects.filter(id=member_id)
        if user_instance.exists():
            admin = user_instance[0].userinfo.name
        else:
            admin = ""

        send_notification_to_new_promoter.delay(
            {'admin': admin, 'nominated_admin': nominated_admin, 'community_id': community_id})

        info_logger.info("----------------add admin api end --------------\n")


    except Exception as e:

        return JsonResponse({'error': e})

    return JsonResponse({'success': True})


@csrf_exempt
def remove_promoter(request):
    '''api to remove the promoter of community'''

    member_id = request.POST.get('member_id')
    community_id = request.POST.get('community_id')

    update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                   {'community_id': community_id, 'member_id': member_id},
                                   {'state': member_states.MEMBER})

    return JsonResponse({'success': True})


def pending_request_count(request, community_id):
    ''' fucntion to get peding members count of a community '''

    no_of_pending_members = Members.objects.filter(community_id=community_id).filter(state=3).count()
    return JsonResponse({'pending_request_count': no_of_pending_members})


def set_state_for_onboarding_chatroom(community_instance, user_id, request):
    '''function to autofollow onboarding chatroom'''
    onboarding_chatroom_instance = Collabcard.objects.filter(community=community_instance, type=card_types.CARD_PURPOSE)
    print("onboarding--", onboarding_chatroom_instance)
    if onboarding_chatroom_instance.exists():
        instance = onboarding_chatroom_instance[0]
        function_dict = {
            'collabcard_id': instance.id,
            'member_id': user_id,
            'status': True,
            'source': "onboarding room"
        }
        collabcard_follow_internal(function_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)
        print("onboarding state set for user")


############# functions for  collabcard flow   ##########################
def ConvertSectoDay(n):
    n = int(n)

    day = n // (24 * 3600)

    n = n % (24 * 3600)
    hour = n // 3600

    n %= 3600
    minutes = n // 60

    n %= 60
    seconds = n
    time_text = ""

    # checking day
    if day != 0:
        if day == 1:
            time_text = str(day) + " day "
        else:
            time_text = str(day) + " days "

    if hour != 0:
        if hour == 1:
            time_text = time_text + str(hour) + " hour "
        else:
            time_text = time_text + str(hour) + " hours "

    if minutes != 0:
        if minutes == 1:
            time_text = time_text + "and " + str(minutes) + " minute "
        else:
            time_text = time_text + "and " + str(minutes) + " minutes "

    if hour == 0 and minutes != 0:

        if minutes == 1:
            time_text = str(minutes) + " minute "
        else:
            time_text = str(minutes) + " minutes "

    if hour == 0 and minutes == 0:
        time_text = str(seconds) + " seconds"

    return time_text


@api_view(['GET', 'POST'])
@renderer_classes([JSONRenderer, TemplateHTMLRenderer])
def fetch_chatroom(request):
    '''api to get the chatroom'''

    is_ios = is_platform_ios(request)

    card_id = request.GET.get('chatroom_id', '')
    community_id = None
    if not card_id:
        context = get_error_context(False, "send chat_room_id as a get params")
        return JsonResponse(context)

    conversation_id = request.GET.get('conversation_id')
    scroll_direction = request.GET.get('scroll_direction')

    card_filter = Collabcard.objects.filter(id=card_id)

    if card_filter.exists():
        card_instance = card_filter[0]
    else:
        context = {}
        backup_filter = deletedChatrooms.objects.filter(card_id=card_id)

        if backup_filter.exists():
            community_id = backup_filter[0].community.id
        if community_id:
            context['community_id'] = community_id
        return JsonResponse(context)

    page = request.GET.get('page', 1)
    current_user_id = get_member_id_from_headers(request)
    current_user = None
    if is_request_web(request) and request.user.is_authenticated:
        current_user_id = request.user.id
        current_user_instance = Userinfo.objects.get(user_id=current_user_id)
        current_user = UserinfoSerializer(user=current_user_instance)

    context = get_chatroom_internal(request, card_instance, current_user_id, page, conversation_id,
                                    scroll_direction, is_ios=is_ios, fetch_conversation_reply=True)

    if str(current_user_id) == str(card_instance.user.id):
        notification_flag = memberNotificationFlag.objects.filter(code='mail_card_owner_inactivity', card=card_instance,
                                                                  member_id=current_user_id)
        if notification_flag.exists():
            flag = notification_flag[0]
            flag.flag = True
            flag.save()

    if request.accepted_renderer.format == 'html':
        context['conversations'] = context['conversations']
        context = {
            'answers': context,
            'current_user': current_user
        }
        return render(request, 'components/chat_bubbles.html', context)

    return JsonResponse(context)


def fetch_chatroom_version_2(request):
    card_id = request.GET.get('chatroom_id', '')

    if not card_id:
        context = ResponseUtilities.get_view_impl_error_context('send chat_room_id as a get params',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    card_filter = Collabcard.objects.filter(id=card_id)

    if card_filter.exists():
        card_instance = card_filter[0]

    else:
        context = ResponseUtilities.get_view_impl_error_context('Chat_room does not exist. Might have been deleted',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    api_type = NumberUtilities.get_integer_from_string(request.GET.get('api_type', api_types.Non_SDK),
                                                       api_types.Non_SDK)
    current_user_id = get_member_id_from_headers(request)

    context = get_chatroom_internal_version_2(request, card_instance, current_user_id, api_type=api_type)

    if context.get('error_message'):
        context = ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    # Reset Unseen message count cache key with 0
    reset_unread_message_count_in_cache.delay(card_id, current_user_id)

    if str(current_user_id) == str(card_instance.user_id):
        notification_flag = memberNotificationFlag.objects.filter(code='mail_card_owner_inactivity', card=card_instance,
                                                                  member_id=current_user_id)
        if notification_flag.exists():
            flag = notification_flag[0]
            flag.flag = True
            flag.save()

    if card_instance.type == card_types.CARD_POLL and card_instance.end_date // 1000 <= time.time():
        if not card_instance.disable_poll_announcement_mail:

            notification_flag = memberNotificationFlag.objects.filter(code='poll_results_announcement_mail',
                                                                      card=card_instance, member=current_user_id)
            if notification_flag.exists():
                memberNotificationFlag.objects.filter(code='poll_results_announcement_mail',
                                                      card=card_instance, member=current_user_id).update(flag=True)
            else:
                current_user_instance = User.objects.get(pk=current_user_id)
                memberNotificationFlag(code='poll_results_announcement_mail',
                                       card=card_instance, member=current_user_instance,
                                       flag=True).save()
    context['success'] = True

    return JsonResponse(context)


def add_poll_conversation_data(conversation_instance, current_user_id):
    poll_conversation = {}

    if conversation_instance.state == conversation_states.CONVERSATION_POLL:
        poll_conversation['state'] = conversation_instance.state
        poll_conversation['poll_type'] = conversation_instance.poll_type

        if conversation_instance.multiple_select_state:
            poll_conversation['multiple_select_state'] = conversation_instance.multiple_select_state

        if conversation_instance.multiple_select_no:
            poll_conversation['multiple_select_no'] = conversation_instance.multiple_select_no

        poll_conversation['is_anonymous'] = conversation_instance.is_anonymous
        poll_conversation['allow_add_option'] = conversation_instance.allow_add_option
        poll_conversation['expiry_time'] = conversation_instance.expiry_time

        poll_conversation['polls'] = get_conversation_poll({'conversation_instance': conversation_instance,
                                                            'member_id': current_user_id,
                                                            'conversation_id': conversation_instance.id,
                                                            'poll_type': conversation_instance.poll_type,
                                                            'multiple_select_no': conversation_instance.multiple_select_no,
                                                            'expiry_time': conversation_instance.expiry_time,
                                                            })

        poll_conversation['poll_type_text'] = "Instant poll" \
            if poll_conversation['poll_type'] == conversation_poll_types.INSTANT else "Deferred poll"

        poll_conversation['submit_type_text'] = "Secret voting" \
            if poll_conversation['is_anonymous'] else "Public voting"

        poll_conversation['poll_answer_text'] = conversation_instance.poll_answer_text

    return poll_conversation


def conversation_meta(request):
    """api to perform firebase operations on conversation for real time messaging"""

    device_id = RequestUtilities.get_device_id_from_headers(request)
    platform_code = RequestUtilities.get_platform_code(request)

    conversation_id = request.GET.get('conversation_id')
    chatroom_id = request.GET.get('chatroom_id')

    if not conversation_id or not chatroom_id:
        context = ResponseUtilities.get_view_impl_error_context("send conversation_id and chatroom_id in post params",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    user_id = get_member_id_from_headers(request)
    user_instance = ModelUtilities.get_user_instance_or_none(user_id)

    if not user_instance:
        context = ResponseUtilities.get_view_impl_error_context("Invalid user id",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    card_instance = Collabcard.get_chatroom_or_None(chatroom_id)

    if card_instance is None:
        context = ResponseUtilities.get_view_impl_error_context(f"chatroom_id {chatroom_id} does not exist",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    answer_id = NumberUtilities.get_integer_from_string(conversation_id, return_default=0)
    conversation_instances = card_answers.objects.filter(card=card_instance, id__gte=answer_id)

    conversation_list = []

    for conversation in conversation_instances:

        if conversation.device_id == device_id and \
                conversation.platform == platform_code:
            continue

        if not is_draft_conversation(conversation, user_id, device_id=device_id):
            conversation_serializer = conversationSerializer(conversation,
                                                             fetch_reply=True,
                                                             current_user_id=user_id)
            preview = generate_internal_link_preview_for_conversation(conversation, user_id)

            if preview:
                conversation_serializer['preview'] = preview

            conversation_serializer['created_at'] = TimeUtilities.convert_epoch_time_in_hh_mm(
                conversation.created_at)

            poll_conversation = add_poll_conversation_data(conversation, user_instance.id)

            if poll_conversation:
                conversation_serializer.update(poll_conversation)

            conversation_list.append(conversation_serializer)

    context = {
        'success': True,
        'conversations': conversation_list
    }

    return JsonResponse(context)


@csrf_exempt
def conversation_seen(request, req_dict=None):
    '''api to save conversation id for user'''

    if not req_dict:
        conversation_id = request.POST.get('conversation_id')
        member_id = get_member_id_from_headers(request)
    else:
        conversation_id = req_dict['conversation_id']
        member_id = req_dict['member_id']

    if not conversation_id or not member_id:
        context = get_error_context(False, "send conversation id and member id in headers")
        return context

    try:
        user_instance = User.objects.get(id=member_id)
        conversation_instance = card_answers.objects.get(id=conversation_id)
        card_instance = conversation_instance.card
        conversation_member_filter = conversationMemberState.objects.filter(user=user_instance, card=card_instance)

        # resetting flag when card owner sees the conversation
        # if member_id == card_instance.user.id:
        #     notification_flag = memberNotificationFlag.objects.get(code='mail_card_owner_inactivity',card=card_instance,member=user_instance)

        if not conversation_member_filter:
            conversation_member_instance = conversationMemberState()
            conversation_member_instance.card = card_instance
            conversation_member_instance.conversation = conversation_instance
            conversation_member_instance.user = user_instance
            conversation_member_instance.save()
        else:
            conversation_member_filter.update(conversation=conversation_instance, updated_at=time.time())
    except Exception as e:
        print(e)
        context = get_error_context(False, "send the member id in headers or conversation does'nt exists")
        return JsonResponse(context)

    update_my_chatrooms_for_users(conversation_instance.card.id, member_id)
    return JsonResponse({'success': True})


@csrf_exempt
def mark_read(request):
    '''api to mark the conversation read'''
    member_id = get_member_id_from_headers(request)
    user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

    if not user_instance:
        context = get_error_context(False, "in-correct member id")

        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    chatroom_id = request.POST.get('chatroom_id')

    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance:
        context = get_error_context(False, "in-correct chatroom id")

        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    save_the_latest_conversation(chatroom_instance, user_instance.id)

    send_sync_notification.delay({'chatroom_id': chatroom_instance.id,
                                  'member_id': member_id,
                                  'sync_notification_type': SyncNotificationTypes.SINGLE_MEMBER.value})

    return JsonResponse({'success': True})


def get_answer_data(answer_filter, community_id, current_user_id, last_seen=None,
                    fetch_reply=False, device_id=""):
    """ function to get answer for a particular collabcard """

    answers = []
    for ans in answer_filter:

        if is_draft_conversation(ans, current_user_id, device_id=device_id):
            continue

        usr = get_members_profile([ans.user.id], community_id, current_user_id, send_profile=False)
        user_context = usr[0]

        if ans.is_guest:
            user_context['is_guest'] = ans.is_guest
            state_filter = collabcardState.objects.filter(card=ans.card, user=ans.user, is_guest=True)
            if state_filter.exists() and state_filter[0].source:
                instance = state_filter[0]
                temp = get_guest_custom_text(instance)
                user_context['custom_intro_text'] = temp['custom_intro_text']
                user_context['custom_click_text'] = temp['custom_click_text']

        # if the member is removed from the community
        elif ans.remove:
            instance = ans.remove
            temp = get_removed_member_custom_text(instance)
            user_context['custom_intro_text'] = temp['custom_intro_text']
            user_context['custom_click_text'] = temp['custom_click_text']
            user_context['remove_state'] = temp['remove_state']
            user_context['image_url'] = temp['removed_user_image_url']

        # time_text = get_time_text(ans.created_at)
        time_text = TimeUtilities.convert_epoch_time_in_hh_mm(ans.created_at)

        date = TimeUtilities.convert_epoch_time_in_date(ans.created_at)
        attachements = get_answer_files(ans.id)

        context = {
            'id': ans.id,
            'answer': ans.answer,
            'created_at': time_text,
            'member': user_context,
            'images': attachements['image'],
            'audios': attachements['audios'],
            'videos': attachements['videos'],
            'pdf': attachements['pdf'],
            'attachments': attachements['attachments'],
            'attachment_count': ans.attachment_count,
            'attachments_uploaded': ans.attachments_uploaded,
            'date': date,
            'state': ans.state,
            # 'is_deleted': ans.is_deleted,
            'is_edited': ans.is_edited,
            'member_id': ans.user_id,
            'community_id': community_id,
            'chatroom_id': ans.card_id,
            'created_epoch': int(ans.created_at)
        }

        if ans.has_reactions:
            reactions = fetch_chatroom_or_conversation_reactions(conversation_id=ans.id)
        else:
            reactions = []

        context['reactions'] = reactions

        if ans.attachments_uploaded is None:
            context['attachments_uploaded'] = False

        if ans.og_tags:
            context['og_tags'] = json.loads(ans.og_tags)

        if last_seen and last_seen.id == ans.id:
            context['last_seen'] = True

        if 'location' in attachements:
            context['location'] = attachements['location']

        if ans.reply:
            context['reply_conversation'] = ans.reply_id
            if fetch_reply:
                reply_obj = get_answer_data([ans.reply], community_id, current_user_id,
                                            fetch_reply=False, device_id=device_id)
                if len(reply_obj) > 0:
                    context['reply_conversation_object'] = reply_obj[0]

        if ans.is_deleted:
            context['deleted_by'] = ans.deleted_by_user_id

        if ans.internal_link:

            try:
                if ans.preview_chatroom and ans.preview_type == "chatroom":
                    key = CHATROOM_PREVIW_CACHE_KEY % (str(ans.preview_chatroom_id), str(ans.id))
                    preview = CacheImpl.get_cache(key)

                    if preview:
                        context['preview'] = preview

                    else:
                        preview = get_preview_for_url(current_user_id, ans.internal_link,
                                                      community_instance=ans.preview_community,
                                                      chatroom_instance=ans.preview_chatroom,
                                                      send_preview_text=False)
                        if preview:
                            context['preview'] = preview
                            update_preview_of_chatroom_in_cache.delay({'preview_object': context['preview'],
                                                                       'chatroom_id': ans.preview_chatroom_id,
                                                                       'conversation_id': ans.id})

                else:
                    preview = get_preview_for_url(current_user_id, ans.internal_link,
                                                  community_instance=ans.preview_community,
                                                  chatroom_instance=ans.preview_chatroom,
                                                  send_preview_text=False)
                    if preview:
                        context['preview'] = preview

            except Exception as e:
                error_logger.error(e.args)

        context['answer_bubble'] = get_answer_bubble_context_for_web(ans)

        if ans.state == conversation_states.CONVERSATION_POLL:
            context['state'] = ans.state
            context['poll_type'] = ans.poll_type

            if ans.multiple_select_state:
                context['multiple_select_state'] = ans.multiple_select_state

            if ans.multiple_select_no:
                context['multiple_select_no'] = ans.multiple_select_no

            context['is_anonymous'] = ans.is_anonymous
            context['allow_add_option'] = ans.allow_add_option
            context['expiry_time'] = ans.expiry_time

            context['polls'] = get_conversation_poll({'conversation_instance': ans, 'member_id': current_user_id,
                                                      'conversation_id': ans.id,
                                                      'poll_type': ans.poll_type,
                                                      'multiple_select_no': ans.multiple_select_no,
                                                      'expiry_time': ans.expiry_time,
                                                      })

        answers.append(context)
    return answers


def get_answer_bubble_context_for_web(ans):
    '''function to get answer bubble context'''
    answer_bubble = ""
    if ans.state == conversation_states.CONVERSATION_GUEST:

        ans = re.findall("""\<<.*?\|""", ans.answer, re.DOTALL)
        user_list = []
        for user in ans:
            user = user.replace("<<", "")
            user = user.replace("|", "")
            user_list.append(user)

        if len(user_list) == 2:
            answer_bubble = user_list[0] + " joined via a " + user_list[1] + "'s invite"

    elif ans.state == conversation_states.CONVERSATION_FOLLOW:
        answer_bubble = str(ans.user.userinfo.name) + " followed this chatroom"

    elif ans.state == conversation_states.CONVERSATION_UNFOLLOW:
        answer_bubble = str(ans.user.userinfo.name) + " unfollowed this chatroom"

    return answer_bubble


def get_chatroom_actions(card_status, creator, card_instance, promoter=False, current_user_instance=None,
                         community_instance=None, is_child=False, request_type="", parent_list=None, version_code=None,
                         platform_code=None, api_type=api_types.Non_SDK):
    """ function to get chatroom actions """

    is_sdk = api_type == api_types.SDK

    if all([card_instance.is_private, card_instance.type == card_types.CARD_DIRECT_MESSAGE]):

        if not m2cm_v2_version_check(platform_code, version_code, is_sdk=is_sdk):

            if card_status.get('mute_status'):
                return collabcard_action_dm_user_mute

            else:
                return collabcard_action_dm_user_unmute

        dm_chatroom_actions = [view_profile]

        if card_status.get('mute_status'):
            dm_chatroom_actions.append(unMute_notifications)

        else:
            dm_chatroom_actions.append(mute_notifications)

        if not card_instance.is_private_member:
            return dm_chatroom_actions

        card_state_instance = None

        card_state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': card_instance,
                                                                              'user': current_user_instance})

        if card_state_filter:
            card_state_instance = card_state_filter[0]

        if card_state_instance and (card_state_instance.chat_request_state != chat_request_states.REJECTED):
            dm_chatroom_actions.append(block_member_chatroom)

        return dm_chatroom_actions

    purpose_card = False
    intro_card = False
    master_intro_card = False
    promoter_joined_secret_chatroom = False
    event_card = False

    if card_instance.is_secret \
            and promoter \
            and card_status.get('follow_status'):
        promoter_joined_secret_chatroom = True
        creator = True

    if parent_list is None:
        parent_list = []

    if card_status['type'] == card_types.CARD_PURPOSE:
        purpose_card = True

    elif card_status['type'] == card_types.CARD_INTRO:
        intro_card = True

    elif card_status['type'] == card_types.CARD_MASTER_INTRO:
        master_intro_card = True

    elif card_status['type'] in [card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
        event_card = True

    final_dict = None

    if creator and card_status['mute_status']:
        final_dict = chatroom_actions_creator_mute

    elif creator and not card_status['mute_status']:
        final_dict = chatroom_actions_creator_unmute

    elif card_status['follow_status'] and not card_status['mute_status']:
        final_dict = collabcard_action_user_follow_unmute

    elif card_status['follow_status'] and card_status['mute_status']:
        final_dict = collabcard_action_user_follow_mute

    if not final_dict:
        final_dict = collabcard_action_user_unfollow

    final = final_dict.copy()
    admin_has_delete_right = check_admin_delete_right(user=current_user_instance, community=community_instance)

    if promoter and not creator:

        if (platform_code == "ios" and version_code < CHATROOM_SETTINGS_VERSION_CODE_IOS) \
                or (
                platform_code == "an" and version_code < CHATROOM_SETTINGS_VERSION_CODE_AN) or platform_code == "web":

            if admin_has_delete_right:
                final.append(delete_chatroom)

    actions = []

    for action in final:

        if (api_type == api_types.SDK) and any([action['id'] == chatroom_actions.ACTION_RENAME,
                                                action['id'] == chatroom_actions.ACTION_VIEW_COMMUNITY,
                                                action['id'] == chatroom_actions.ACTION_ADD_ALL_MEMBERS,
                                                action['id'] == chatroom_actions.ACTION_SETTINGS,
                                                action['id'] == chatroom_actions.ACTION_DELETE,
                                                action['id'] == chatroom_actions.ACTION_REPORT]):
            continue

        if all([api_type == api_types.SDK,
                action['id'] == chatroom_actions.ACTION_INVITE]):

            if not VersionUtilities.check_version(platform_code, version_code, VersionUtilities.invite_settings):
                continue

            action = {
                'id': action['id'],
                'title': INVITE_ACTION_TITLE_SDK
            }

        if purpose_card or master_intro_card:

            if action['id'] == chatroom_actions.ACTION_JOIN_CHATROOM or action[
                'id'] == chatroom_actions.ACTION_UNFOLLOW:
                continue

            if not promoter:

                if action['id'] == chatroom_actions.ACTION_INVITE:
                    continue

            if promoter or creator:

                if action['id'] == chatroom_actions.ACTION_RENAME or action['id'] == chatroom_actions.ACTION_DELETE:
                    continue

            if action['id'] == chatroom_actions.ACTION_INVITE:
                continue

        elif intro_card and creator:

            if action['id'] == chatroom_actions.ACTION_JOIN_CHATROOM or \
                    action['id'] == chatroom_actions.ACTION_MUTE or \
                    action['id'] == chatroom_actions.ACTION_DELETE or \
                    action['id'] == chatroom_actions.ACTION_UNMUTE or \
                    action['id'] == chatroom_actions.ACTION_UNFOLLOW:
                continue

        elif action['id'] == chatroom_actions.ACTION_DELETE:

            if is_child and not creator:
                continue

            if promoter and \
                    not creator and \
                    not admin_has_delete_right:
                continue

        elif action['id'] == chatroom_actions.ACTION_REPORT:

            if promoter and \
                    not creator and \
                    admin_has_delete_right:
                continue

        elif card_instance.is_secret:

            if action['id'] == chatroom_actions.ACTION_JOIN_CHATROOM \
                    or action['id'] == chatroom_actions.ACTION_UNFOLLOW \
                    or action['id'] == chatroom_actions.ACTION_INVITE:
                continue

        actions.append(action)

    if (api_type != api_types.SDK) and promoter and len(actions) and not card_instance.is_secret:

        if (platform_code == "ios" and version_code < CHATROOM_SETTINGS_VERSION_CODE_IOS) \
                or (
                platform_code == "an" and version_code < CHATROOM_SETTINGS_VERSION_CODE_AN) or platform_code == "web":

            if card_instance.is_pinned:
                actions.insert(1, unpin_chatroom)

            else:
                actions.insert(1, pin_chatroom)

            actions.insert(2, add_all_members)

        else:
            actions.append(add_all_members)

    if card_instance.is_secret and \
            current_user_instance is not None:

        if isinstance(current_user_instance, User):
            current_user_id = current_user_instance.id

        else:
            current_user_id = NumberUtilities.get_integer_from_string(current_user_instance)

        participants_list = json.loads(card_instance.secret_chatroom_participants)

        if current_user_id not in participants_list \
                and report in actions:
            actions.remove(report)

        if promoter_joined_secret_chatroom or \
                creator or \
                current_user_id in participants_list:
            actions.append(leave_chatroom)

    if promoter and ((platform_code == VersionUtilities.PlatformCode.IOS and
                      version_code >= CHATROOM_SETTINGS_VERSION_CODE_IOS)
                     or (platform_code == VersionUtilities.PlatformCode.ANDROID and
                         version_code >= CHATROOM_SETTINGS_VERSION_CODE_AN)
                     or platform_code == VersionUtilities.PlatformCode.WEB) \
            and not master_intro_card and (api_type != api_types.SDK):
        actions.append(chatroom_settings)

    if (platform_code == VersionUtilities.PlatformCode.IOS and version_code >= CHATROOM_SETTINGS_VERSION_CODE_IOS) \
            or (platform_code == VersionUtilities.PlatformCode.ANDROID and
                version_code >= CHATROOM_SETTINGS_VERSION_CODE_AN) \
            or platform_code in [VersionUtilities.PlatformCode.WEB,
                                 VersionUtilities.PlatformCode.FLUTTER,
                                 VersionUtilities.PlatformCode.REACT_NATIVE]:

        if rename_chatroom in actions:
            actions.remove(rename_chatroom)

        if pin_chatroom in actions:
            actions.remove(pin_chatroom)

        if unpin_chatroom in actions:
            actions.remove(unpin_chatroom)

        if delete_chatroom in actions:
            actions.remove(delete_chatroom)

    if event_card:

        if pin_chatroom in actions:
            actions.remove(pin_chatroom)

        if unpin_chatroom in actions:
            actions.remove(unpin_chatroom)

    return actions


def get_chatroom_internal(request, card_instance, user_id, page, conversation_id, scroll_direction, is_ios=False,
                          fetch_conversation_reply=False):
    '''internal function to get the chatroom conversation screen functionalities '''
    source_id = request.GET.get('source_id')
    aj = request.GET.get('aj')

    device_id = RequestUtilities.get_device_id_from_headers(request)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    is_guest = False
    context = {}

    if aj:
        is_guest = True

    # if the chatroom is deleted
    if card_instance.type == card_types.CARD_HIDDEN:
        card = get_chatroom_instance(card_instance, user_id)
        context = {'chatroom': card}
        return context

    user_instance = None
    if user_id:
        user_instance = User.objects.get(id=user_id)

    # user has not done the scrolling
    conversations_filter = card_answers.objects.select_related('reply', 'preview_community',
                                                               'preview_chatroom').filter(card=card_instance).order_by(
        'created_at')

    total_response_count = card_answers.objects.filter(card=card_instance,
                                                       state=conversation_states.ANSWER
                                                       ).filter(Q(attachment_count=0) |
                                                                Q(attachments_uploaded=True)
                                                                ).count()

    if not conversation_id and not scroll_direction:

        if is_guest:
            context = adding_guest_in_chatroom(context, card_instance, aj, source_id,
                                               card_instance.community.id, current_user_id=user_id,
                                               platform_code=platform_code, version_code=version_code)

        instance_filter = conversationMemberState.objects.filter(user_id=user_id, card=card_instance)
        if not instance_filter.exists():

            conversations = pagination(conversations_filter, page, paginate_by=20)

            conversations = get_answer_data(conversations, card_instance.community.id, current_user_id=user_id,
                                            fetch_reply=fetch_conversation_reply, device_id=device_id)

            placeholder = create_introduction_card_placeholder(card_instance, user_id)
            if placeholder:
                context['placeholder'] = placeholder
        else:
            conversation_instance = instance_filter[0].conversation

            upward_conversation = conversations_filter.filter(id__lte=conversation_instance.id).order_by('-created_at')[
                                  :10]

            downward_conversation = conversations_filter.filter(id__gt=conversation_instance.id)[:10]

            # merging both conversations
            conversations = upward_conversation | downward_conversation
            conversations = conversations.order_by('created_at')

            conversations = get_answer_data(conversations, card_instance.community.id,
                                            current_user_id=user_id, last_seen=conversation_instance,
                                            fetch_reply=fetch_conversation_reply, device_id=device_id)
    else:

        try:
            scroll_direction = int(scroll_direction)
            conversation_id = int(conversation_id)
        except Exception as e:
            context = get_error_context(False, "conversation id is a nullable field.Don't send the key")
            return context

        if scroll_direction == 0:  # upward scroll
            upward_list = conversations_filter.filter(id__lt=conversation_id).order_by('-created_at')[:20]
            conversations = reverse_conversations_for_upward_pagination(upward_list)

        elif scroll_direction == 1:  # downward scroll
            conversations = conversations_filter.filter(id__gt=conversation_id).order_by('created_at')[:20]
        else:
            conversations = conversations_filter

        conversations = get_answer_data(conversations, card_instance.community.id, current_user_id=user_id,
                                        fetch_reply=fetch_conversation_reply, device_id=device_id)

    card = get_chatroom_instance(card_instance, user_id)
    if card_instance.internal_link:
        try:
            preview = get_preview_for_url(user_id, card_instance.internal_link,
                                          community_instance=card_instance.preview_community,
                                          chatroom_instance=card_instance.preview_chatroom,
                                          send_preview_text=False)
            if preview:
                card['preview'] = preview

        except Exception as e:
            error_logger.error(e.args)

    card_status = {
        'state': card['state'],
        'mute_status': card['mute_status'],
        'follow_status': card['follow_status'],
        'attending_status': card['attending_status'],
        'is_guest': card['is_guest'],
        'type': card['type'],
        'is_tagged': card['is_tagged'],
    }

    is_promoter = False
    is_child = False
    parent_list = []
    member_instance = Members.objects.filter(member_id=user_id,
                                             community_id=card_instance.community).filter(Q(state=member_states.ADMIN))
    if member_instance.exists():
        is_promoter = True
        parent_cm_list = member_instance[0].parent_cm_list
        parent_list = json.loads(parent_cm_list) if parent_cm_list else []

        is_child = str(card_instance.user.id) in parent_list

    is_card_creator = False
    if user_id and int(user_id) == card_instance.user.id:
        is_card_creator = True
    # sending the chatroom actions

    request_type = ""
    is_ios = is_request_ios(request)
    if is_ios:
        request_type = "iOS"

    chatroom_actions = get_chatroom_actions(card_status, creator=is_card_creator, card_instance=card_instance,
                                            promoter=is_promoter, current_user_instance=user_id,
                                            community_instance=card_instance.community, is_child=is_child,
                                            request_type=request_type, parent_list=parent_list,
                                            platform_code=platform_code, version_code=version_code
                                            )

    # getting the state of chatroom against the user
    chatroom_state = collabcardState.objects.filter(card=card_instance, user=user_id, remove=None)
    # if the user is seeing this chatroom from external link or notification
    if not chatroom_state.exists() and \
            user_instance and \
            is_member_verified(card_instance.community, user_instance):
        expire_at = get_expiry_time_of_chatroom()
        create_chatroom_state_instance(card_instance, user_instance, state=0, external_seen=True, expire_at=expire_at,
                                       function_called="get_chatroom_internal")
    elif user_instance and chatroom_state.exists():
        instance = chatroom_state[0]

        if not instance.external_seen:
            update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                           {'card': card_instance, 'user': user_instance, 'remove': None},
                                           {'external_seen': True})

    # sending the follow telescope
    latest_conversation = conversations_filter.last()

    # icons states for sending following, tagging
    icon_states = get_icons_states_of_chatroom(card_status, card_instance, user_id, latest_conversation,
                                               conversations)
    card['show_follow_telescope'] = icon_states['show_follow_telescope']
    card['show_follow_auto_tag'] = icon_states['show_follow_auto_tag']

    card['total_response_count'] = total_response_count

    if latest_conversation:
        serialized_last = get_answer_data([latest_conversation], card_instance.community.id, current_user_id=user_id,
                                          fetch_reply=fetch_conversation_reply, device_id=device_id)
        if serialized_last:
            card['last_conversation'] = serialized_last[0]

    context['chatroom'] = card
    context['conversations'] = conversations
    context['chatroom_actions'] = chatroom_actions
    context['total_response_count'] = total_response_count

    can_access_secret_chatroom = False

    if user_id is not None:
        user_id = NumberUtilities.get_integer_from_string(user_id)
        device_id = RequestUtilities.get_device_id_from_headers(request)

        if card_instance.is_secret:
            can_access_secret_chatroom = user_id in card['secret_chatroom_participants']

        elif card_instance.attachment_count > 0 and \
                card_instance.attachments_uploaded is False:
            can_access_secret_chatroom = not is_draft_chatroom(card_instance, user_id, device_id)

    context['can_access_secret_chatroom'] = can_access_secret_chatroom

    context['community'] = CommunitySerializer(card_instance.community, current_user_instance=user_instance,
                                               platform_code=platform_code, version_code=version_code)

    if card_instance.type != card_types.CARD_MASTER_INTRO:
        context['participant_count'] = collabcardState.objects.filter(follow_status=True, card=card_instance,
                                                                      remove=None, is_tagged=False).count()

    conversation_users_meta = get_chatroom_user_images_for_web(card_instance.id)
    conversation_users = get_latest_conversation_members(conversation_users_meta['last_conversation_member'],
                                                         conversation_users_meta['second_last_conversation_member'],
                                                         conversation_users_meta['last_conversation_user'],
                                                         conversation_users_meta['second_last_conversation_user'])
    context['conversation_users'] = conversation_users

    if card_instance.type == card_types.CARD_MASTER_INTRO and user_instance:
        update_models_for_syncing_apis(SyncTypes.CHATROOM, {
            'community': card_instance.community,
            'user': user_instance,
            'card__type': card_types.CARD_INTRO,
            'state': 0}, {'state': 1,
                          'external_seen': True,
                          })

    return context


def get_chatroom_internal_version_1(request, card_instance, user_id, page, conversation_id, scroll_direction,
                                    is_ios=False):
    '''version 1 function for sending chatroom instance without conversations'''
    source_id = request.GET.get('source_id')
    aj = request.GET.get('aj')
    version_code = RequestUtilities.get_version_code_from_headers(request)
    platform_code = RequestUtilities.get_platform_code(request)
    is_guest = False
    context = {}

    if aj:
        is_guest = True

    # if the chatroom is deleted
    if card_instance.type == card_types.CARD_HIDDEN:
        card = get_chatroom_instance(card_instance, user_id)
        context = {'chatroom': card}
        return context

    user_instance = None
    if user_id:
        user_instance = User.objects.get(id=user_id)

    # user has not done the scrolling
    conversations_filter = card_answers.objects.select_related('reply', 'preview_community',
                                                               'preview_chatroom').filter(card=card_instance).order_by(
        'id')
    total_response_count = card_answers.objects.filter(card=card_instance,
                                                       state=conversation_states.ANSWER
                                                       ).filter(Q(attachment_count=0) |
                                                                Q(attachments_uploaded=True)
                                                                ).count()

    conversations = []

    if not conversation_id and not scroll_direction:

        if is_guest:
            context = adding_guest_in_chatroom(context, card_instance, aj, source_id,
                                               card_instance.community.id, current_user_id=user_id,
                                               platform_code=platform_code, version_code=version_code)

    card = get_chatroom_instance(card_instance, user_id)

    if card_instance.internal_link:
        try:
            preview = get_preview_for_url(user_id, card_instance.internal_link,
                                          community_instance=card_instance.preview_community,
                                          chatroom_instance=card_instance.preview_chatroom,
                                          send_preview_text=False)
            if preview:
                card['preview'] = preview

        except Exception as e:
            error_logger.error(e.args)

    card_status = {
        'state': card['state'],
        'mute_status': card['mute_status'],
        'follow_status': card['follow_status'],
        'attending_status': card['attending_status'],
        'is_guest': card['is_guest'],
        'type': card['type'],
        'is_tagged': card['is_tagged'],
    }

    is_promoter = False
    is_child = False
    parent_list = []
    member_instance = Members.objects.filter(member_id=user_id,
                                             community_id=card_instance.community).filter(Q(state=member_states.ADMIN))
    if member_instance.exists():
        is_promoter = True
        parent_cm_list = member_instance[0].parent_cm_list
        parent_list = json.loads(parent_cm_list) if parent_cm_list else []

        is_child = str(card_instance.user.id) in parent_list

    # sending the chatroom actions
    is_card_creator = False
    if user_id and int(user_id) == card_instance.user.id:
        is_card_creator = True
    request_type = ""
    is_ios = is_request_ios(request)
    if is_ios:
        request_type = "iOS"

    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    chatroom_actions = get_chatroom_actions(card_status, creator=is_card_creator, card_instance=card_instance,
                                            promoter=is_promoter, current_user_instance=user_id,
                                            community_instance=card_instance.community, is_child=is_child,
                                            request_type=request_type, parent_list=parent_list,
                                            platform_code=platform_code, version_code=version_code
                                            )

    # getting the state of chatroom against the user
    chatroom_state = collabcardState.objects.filter(card=card_instance, user=user_id)
    # if the user is seeing this chatroom from external link or notification
    if not chatroom_state.exists() and \
            user_instance and \
            is_member_verified(card_instance.community, user_instance):
        expire_at = get_expiry_time_of_chatroom()
        create_chatroom_state_instance(card_instance, user_instance, state=0, external_seen=True, expire_at=expire_at,
                                       function_called="get_chatroom_internal_version_1")
    elif user_instance and chatroom_state.exists():
        instance = chatroom_state[0]

        if not instance.external_seen:
            update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                           {'card': card_instance, 'user': user_instance, 'remove': None},
                                           {'external_seen': True})

    # sending the follow telescope
    latest_conversation = conversations_filter.last()

    # icons states for sending following, tagging
    icon_states = get_icons_states_of_chatroom_version_1(card_status, card_instance, user_id
                                                         )
    card['show_follow_telescope'] = icon_states['show_follow_telescope']
    card['show_follow_auto_tag'] = icon_states['show_follow_auto_tag']

    card['total_response_count'] = total_response_count

    context['chatroom'] = card
    # context['conversations'] = conversations
    context['chatroom_actions'] = chatroom_actions
    context['total_response_count'] = total_response_count

    context['community'] = CommunitySerializer(card_instance.community, current_user_id=user_id,
                                               current_user_instance=user_instance, platform_code=platform_code,
                                               version_code=version_code)

    # sendig the last seen conversation of user
    conversation_member_filter = conversationMemberState.objects.filter(user=user_instance, card=card_instance)
    if conversation_member_filter.exists():
        last_seen_conversation = conversation_member_filter[0].conversation
        context['last_seen_conversation'] = last_seen_conversation.id

    else:
        placeholder = create_introduction_card_placeholder(card_instance, user_id)
        if placeholder:
            context['placeholder'] = placeholder

    save_the_latest_conversation(card_instance, user_id)

    can_access_secret_chatroom = False

    if user_id is not None:
        user_id = NumberUtilities.get_integer_from_string(user_id)
        device_id = RequestUtilities.get_device_id_from_headers(request)

        if card_instance.is_secret:
            can_access_secret_chatroom = user_id in card['secret_chatroom_participants']

        elif card_instance.attachment_count > 0 and \
                card_instance.attachments_uploaded is False:
            can_access_secret_chatroom = not is_draft_chatroom(card_instance, user_id, device_id)

    context['can_access_secret_chatroom'] = can_access_secret_chatroom

    return context


def get_chatroom_internal_version_2(request, card_instance, user_id, api_type=api_types.Non_SDK):
    '''version 1 function for sending chatroom instance without conversations'''

    context = {}

    user_instance = None

    if user_id:
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

    if not user_instance:
        return ResponseUtilities.get_inner_error_context('Invalid user id')

    chatroom_state = collabcardState.objects.filter(card=card_instance, user=user_id)
    # if the user is seeing this chatroom from external link or notification
    if not chatroom_state and \
            user_instance and \
            is_member_verified(card_instance.community, user_instance) and \
            not card_instance.is_secret:
        expire_at = get_expiry_time_of_chatroom()
        create_chatroom_state_instance(card_instance, user_instance, state=0,
                                       external_seen=True, expire_at=expire_at,
                                       function_called="get_chatroom_internal_version_1")

    elif user_instance and chatroom_state:
        instance = chatroom_state[0]

        if not instance.external_seen:
            update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                           {'card': card_instance, 'user': user_instance, 'remove': None},
                                           {'external_seen': True})

    update_last_unseen_in_engage(user=user_instance, community=card_instance.community)

    if chatroom_state:
        state_instance = chatroom_state[0]
    else:
        state_instance = None

    card_status = {}
    status = get_status_of_collabcard(user_id, card_instance, state_instance)
    card_status['state'] = status['state']
    card_status['mute_status'] = status['mute_status']
    card_status['follow_status'] = status['follow_status']
    card_status['attending_status'] = status['attending_status']
    card_status['is_guest'] = status['is_guest']
    card_status['is_tagged'] = status['is_tagged']
    card_status['type'] = card_instance.type

    is_promoter = False
    is_child = False
    parent_list = []
    member_instance = Members.objects.filter(member_id=user_id,
                                             community_id=card_instance.community).filter(Q(state=member_states.ADMIN))
    if member_instance:
        is_promoter = True
        parent_cm_list = member_instance[0].parent_cm_list
        parent_list = json.loads(parent_cm_list) if parent_cm_list else []

        is_child = str(card_instance.user.id) in parent_list

    # sending the chatroom actions
    is_card_creator = False
    if user_id and int(user_id) == card_instance.user_id:
        is_card_creator = True

    request_type = ""
    is_ios = is_request_ios(request)
    if is_ios:
        request_type = "iOS"

    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    chatroom_actions = get_chatroom_actions(card_status, creator=is_card_creator, card_instance=card_instance,
                                            promoter=is_promoter, current_user_instance=user_id,
                                            community_instance=card_instance.community, is_child=is_child,
                                            request_type=request_type, parent_list=parent_list,
                                            platform_code=platform_code, version_code=version_code, api_type=api_type)

    context['chatroom_actions'] = chatroom_actions

    if card_instance.type != card_types.CARD_MASTER_INTRO:
        if card_instance.is_secret:
            secret_room_participants = json.loads(card_instance.secret_chatroom_participants)
            context['participant_count'] = len(get_members_based_on_user_list_query(secret_room_participants,
                                                                                    card_instance.community_id))
        else:
            from collabmates_api.chatroom.chatroom_impl import ChatroomHelper
            context['participant_count'] = ChatroomHelper.chatroom_participants_count(card_instance)

    conversation_member_filter = conversationMemberState.objects.filter(user=user_instance, card=card_instance)

    if not conversation_member_filter.exists():
        placeholder = create_introduction_card_placeholder(card_instance, user_id)
        if placeholder:
            context['placeholder'] = placeholder

    if card_instance.type == card_types.CARD_MASTER_INTRO and user_instance:
        update_models_for_syncing_apis(SyncTypes.CHATROOM, {
            'community': card_instance.community,
            'user': user_instance,
            'card__type': card_types.CARD_INTRO,
            'state': 0}, {'state': 1,
                          'external_seen': True,
                          })

    can_access_secret_chatroom = False

    if user_id is not None:
        user_id = NumberUtilities.get_integer_from_string(user_id)
        device_id = RequestUtilities.get_device_id_from_headers(request)

        if card_instance.is_secret:
            can_access_secret_chatroom = user_id in json.loads(card_instance.secret_chatroom_participants)

            if not can_access_secret_chatroom:
                can_access_secret_chatroom = ModelUtilities.is_model_filter_exists(collabcardState,
                                                                                   {'card': card_instance,
                                                                                    'user': user_id,
                                                                                    'remove': None,
                                                                                    'secret_chatroom_left': False})

        elif card_instance.attachment_count > 0 and \
                card_instance.attachments_uploaded is False:
            can_access_secret_chatroom = not is_draft_chatroom(card_instance, user_id, device_id)

    context['can_access_secret_chatroom'] = can_access_secret_chatroom

    context['access_without_subscription'] = card_instance.access_without_subscription

    from collabmates_api.cohort.cohort_impl import CohortHelper
    cohort_access = CohortHelper.fetch_cohort_access_for_chatroom(card_instance.id, user_instance.id)

    if cohort_access is not None:
        context['cohort_access'] = cohort_access

    return context


def save_the_member_conversation_state(card_instance, user_instance, conversation_instance):
    conversation_member_filter = conversationMemberState.objects.filter(card=card_instance, user=user_instance)

    if not conversation_member_filter.exists():

        conversation_member_instance = conversationMemberState()
        conversation_member_instance.card = card_instance
        conversation_member_instance.conversation = conversation_instance
        conversation_member_instance.user = user_instance
        conversation_member_instance.created_at = TimeUtilities.current_time_in_sec()
        conversation_member_instance.updated_at = TimeUtilities.current_time_in_sec()
        conversation_member_instance.save()

    else:

        conversation_member_instance = conversation_member_filter[0]

        if conversation_instance.id != conversation_member_instance.conversation.id:
            conversation_member_instance.card = card_instance
            conversation_member_instance.conversation = conversation_instance
            conversation_member_instance.user = user_instance
            conversation_member_instance.updated_at = TimeUtilities.current_time_in_sec()
            conversation_member_instance.save()


def save_the_latest_conversation(card_instance, user_id):
    """function to save the lastest conversation of user"""

    if not user_id:
        return {'last_conversation': None}

    last_conversation = card_answers.objects.filter(card=card_instance). \
        filter(Q(state=conversation_states.CONVERSATION_POLL) |
               Q(state=conversation_states.ANSWER) |
               Q(state=conversation_states.CONVERSATION_HEADER) |
               Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_REMOVED_OR_LEFT) |
               Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_CM_REMOVED) |
               Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_DISABLE_CHAT) |
               Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_CM_BECOMES_MEMBER_ENABLE_CHAT) |
               Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_ENABLE_CHAT) |
               Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_BLOCK_MEMBER_DISABLE_CHAT) |
               Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_UNBLOCK_MEMBER_ENABLE_CHAT)).last()

    if last_conversation:
        user_instance = User.get_user_or_raise_exception(user_id)
        state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)

        if state_filter:

            collabcard_state_instance = state_filter[0]

            last_seen_conversation = collabcard_state_instance.last_seen_conversation

            if collabcard_state_instance.last_seen_conversation:

                if last_seen_conversation.id != last_conversation.id:
                    collabcard_state_instance.last_seen_conversation = last_conversation
                    collabcard_state_instance.updated_at = TimeUtilities.current_time_in_sec()
                    collabcard_state_instance.save()

            else:
                collabcard_state_instance.last_seen_conversation = last_conversation
                collabcard_state_instance.updated_at = TimeUtilities.current_time_in_sec()
                collabcard_state_instance.save()

        update_conversation_engage_for_chatrooms(card_id=card_instance.id, user_id=user_instance.id,
                                                 last_conversation_id=last_conversation.id,
                                                 unseen_count=0)

        save_the_member_conversation_state(card_instance, user_instance, last_conversation)

    latest_conversations = {'last_conversation': last_conversation}

    return latest_conversations


def is_chatroom_join_expired(aj, source_id, chatroom_id=None):
    '''function to check weather joining time of chatroom is valid or not'''

    expiry_filter = chatroomExpiryCodes.objects.filter(unique_code=aj, source=source_id,
                                                       card_id=chatroom_id)

    if expiry_filter.exists():
        expiry_instance = expiry_filter[0]
        time_stamp = int(time.time())
        expiry_time = int(expiry_instance.created_at)

        if (time_stamp - expiry_time) <= expiry_instance.expire_duration:
            return False

    return True


def adding_guest_in_chatroom(context, card_instance, aj, source_id, community_id, current_user_id,
                             guest_header=False, created_at=None, platform_code=None, version_code=None):
    if not created_at:
        created_at = TimeUtilities.current_time_in_milliseconds()

    aj_expired = is_chatroom_join_expired(aj, source_id, card_instance.id)
    status = is_member_verified(community_id, current_user_id)
    state_filter = collabcardState.objects.filter(card=card_instance, user=current_user_id, is_guest=True)

    if not aj_expired and not status and not state_filter.exists():
        context['aj_expired'] = aj_expired

        if guest_header:
            create_guest_header(current_user_id, source_id, card_instance, current_user_id, created_at=created_at)

            func_dict = {'collabcard_id': card_instance.id, 'member_id': current_user_id, 'status': True,
                         'is_guest': True, 'source_id': source_id, 'source': "guest access"}
            collabcard_follow_internal(func_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

            ModelUtilities.model_update(Userinfo, {'user_id': current_user_id},
                                        {'updated_at': TimeUtilities.current_time_in_sec()})

            ModelUtilities.model_update(Userinfo, {'user_id': source_id},
                                        {'updated_at': TimeUtilities.current_time_in_sec()})

    elif not status and not state_filter.exists():
        context['aj_expired'] = aj_expired
        aj_expired_disclaimer = {}
        aj_expired_disclaimer['image_url'] = WARNING_IMAGE
        aj_expired_disclaimer[
            'title'] = "Oops! The private link to participate in this chat room has expired. Join the following community to access this chat room."
        if status:
            # for promoter
            community_serializer = CommunitySerializer(card_instance.community, status.member_id,
                                                       current_user_id=current_user_id, platform_code=platform_code,
                                                       version_code=version_code)
            community_serializer['created_by'] = get_community_creator(card_instance.community)
            aj_expired_disclaimer['community'] = community_serializer
        else:
            community_serializer = CommunitySerializer(card_instance.community, current_user_id=current_user_id,
                                                       platform_code=platform_code,
                                                       version_code=version_code)
            community_serializer['created_by'] = get_community_creator(card_instance.community)
            aj_expired_disclaimer['community'] = community_serializer

        context['aj_expired_disclaimer'] = aj_expired_disclaimer

    return context


def create_guest_header(guest_id, invitee_id, card_instance, current_user_id,
                        created_at=None):
    try:
        guest_instance = User.objects.get(id=guest_id)
        invitee_instance = User.objects.get(id=invitee_id)
    except:
        return

    guest_user_name = get_user_in_route_form(card_instance, guest_instance, current_user_id)

    invitee_user_name = get_user_in_route_form(card_instance, invitee_instance, current_user_id)

    answer = guest_user_name + " joined via " + invitee_user_name + "'s link"

    if not created_at:
        created_at = TimeUtilities.current_time_in_milliseconds()

    cardAnswer_filter = card_answers.objects.filter(card=card_instance, user=guest_instance,
                                                    state=conversation_states.CONVERSATION_GUEST)
    if not cardAnswer_filter.exists():
        instance = card_answers()
        instance.answer = answer
        instance.card = card_instance
        instance.user = guest_instance
        instance.state = conversation_states.CONVERSATION_GUEST
        instance.community = card_instance.community
        instance.created_at = created_at
        instance.save()


def get_user_in_route_form(card_instance, user_instance, current_user_id):
    user_name = user_instance.userinfo.name
    member_ids = [user_instance.id]
    community_profile = get_members_profile(member_ids, card_instance.community.id, current_user_id)
    if community_profile:
        community_profile = community_profile[0]
        user_route = "route://member_profile/" + str(user_instance.id) + "?member=" + quote(str(community_profile))
    else:
        user_route = "route://member_profile/" + str(user_instance.id)
    user_name = "<<" + user_name + "|" + user_route + "&community_id=" + str(card_instance.community.id) + ">>"

    return user_name


def reverse_conversations_for_upward_pagination(upward_list):
    conversations = []

    for data in upward_list:
        conversations.append(data)

    conversations.reverse()
    return conversations


def get_icons_states_of_chatroom(card_status, card_instance, user_id, latest_conversation, conversations):
    '''function to show follow telescope of user'''

    show = False

    temp = {
        'show_follow_telescope': False,
        'show_follow_auto_tag': False
    }

    if not card_status['follow_status']:
        temp['show_follow_telescope'] = True
        show = True

    if card_instance.user.id == user_id:
        temp['show_follow_telescope'] = False
        show = True

    if card_status['is_tagged']:
        temp['show_follow_telescope'] = False
        temp['show_follow_auto_tag'] = True
        show = True

    if card_status["follow_status"] == True:
        temp['show_follow_telescope'] = False
        temp['show_follow_auto_tag'] = False
        show = True

    if show:
        last = False
        if latest_conversation:
            for conversation in conversations:
                if latest_conversation.id == conversation['id']:
                    last = True
        else:
            last = True

        if last:
            show = True
        else:
            show = False

    if show:
        return temp
    return {'show_follow_telescope': False, 'show_follow_auto_tag': False}


def get_icons_states_of_chatroom_version_1(card_status, card_instance, user_id):
    '''function to show follow telescope of user'''

    show = False

    temp = {
        'show_follow_telescope': False,
        'show_follow_auto_tag': False,
    }

    if not card_status['follow_status']:
        temp['show_follow_telescope'] = True
        show = True

    if card_instance.user.id == user_id:
        temp['show_follow_telescope'] = False
        show = True

    if card_status['is_tagged']:
        temp['show_follow_telescope'] = False
        temp['show_follow_auto_tag'] = True
        show = True

    if card_status["follow_status"] == True:
        temp['show_follow_telescope'] = False
        temp['show_follow_auto_tag'] = False
        show = True

    if show:
        return temp
    return {'show_follow_telescope': False, 'show_follow_auto_tag': False}


def create_introduction_card_placeholder(card_instance, user_id):
    '''function to create introduction card placeholder'''

    user_filter = User.objects.filter(id=user_id)
    if user_filter.exists():
        user_instance = user_filter[0]

    else:
        return

    if card_instance.type == card_types.CARD_INTRO and card_instance.user.id != user_instance.id:
        placeholder = """Welcome to """ + card_instance.community.name + ", "
        user_name = card_instance.user.userinfo.name
        user_route = "route://member_profile/" + str(card_instance.user.id)
        user_name = "<<" + user_name + "|" + user_route + ">>"
        placeholder = placeholder + user_name
        print(placeholder)
        return placeholder


def community_collabcard_invite(request, community_id):
    '''api to send collabcard invite footer'''

    community = Community.objects.get(id=community_id)
    member_id = request.GET.get('member_id')
    member_instance = User.objects.get(id=member_id)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    if is_member_promoter(community_id=community_id, member_id=member_id):
        community_serializer_instance = CommunitySerializer(community, promoter_id=member_instance,
                                                            current_user_id=member_id, platform_code=platform_code,
                                                            version_code=version_code)
    else:
        community_serializer_instance = CommunitySerializer(community, current_user_id=member_id,
                                                            platform_code=platform_code, version_code=version_code)

    # if the community is a user-created community
    if community_serializer_instance['state'] == community_states.PRIVATE or community_serializer_instance[
        'state'] == community_states.HIDDEN or community_serializer_instance['state'] == community_states.WHATSAPP:
        json_response = {

            'community': community_serializer_instance,

        }
        return JsonResponse(json_response)

    # initializing variables

    community_live_subtitle = ""
    invite_prompt = {}

    number_of_members = get_members_count_in_community(community)
    members_left = ig_members_count - number_of_members
    card_list = []

    # prompt for invite  for ig and lg community
    unlock_prompt = get_unlock_prompt(members_left)

    # community live for ig communities
    if community_serializer_instance['community_type'] == 0:
        community_name = community.name
        member_types = community_name.split("of")[0].strip()
        member_type = member_types
        if member_types[-1] == "s":
            member_type = member_types[0:-1]

        member_types = member_types.lower()
        member_type = member_type.lower()

        community_live_subtitle = compute_community_live_subtitle_for_Ig(community, member_id, number_of_members)
        invite_prompt = get_invite_prompt_for_members(community_id, member_type, member_types, member_id)


    # community live for lg communities
    elif community_serializer_instance['community_type'] == 1:

        user_instance = User.objects.get(id=member_id)

        collabcardTemp_instance_list = collabcardTemp.objects.filter(show_member=user_instance,
                                                                     community_id=community_serializer_instance[
                                                                         'id']).order_by('id')

        for instance in collabcardTemp_instance_list:
            card_dict = {}
            card_dict['id'] = instance.id
            card_dict['title'] = instance.title
            user = Userinfo.objects.get(user_id=instance.member)
            # serialize user object
            usr = UserinfoSerializer(user)
            card_dict['created_at'] = get_time_text(instance.created_at)
            card_dict['member'] = usr
            card_dict['images'] = []
            card_dict['pdf'] = []
            card_dict['state'] = instance.state
            card_dict['type'] = 5  # for unverified
            card_list.append(card_dict)

        count_of_verified_members = Members.objects.filter(community_id=community_serializer_instance['id']).filter(
            Q(state=4) | Q(state=1)).count()
        collabcard_temp_count = collabcardTemp_instance_list.count()
        total_count = count_of_verified_members + collabcard_temp_count

        community_live_subtitle = compute_community_live_subtitle_for_lg(total_count, count_of_verified_members,
                                                                         user_instance, community)

        # invite prompt logic for lg
        member_type = "relevant alumnus"
        member_types = "relevant alumini"
        invite_prompt = get_invite_prompt_for_members(community_id, member_type, member_types, member_id)

    if members_left > 0:

        community_live = {
            'members_left': members_left,
            'title': unlock_prompt['community_live_title'],
            'sub_title': community_live_subtitle,
            'action_title': "Invite Friends",
            'action': """route://community?community_id=%s&share=true&source=community_live""" % (community_id),

            'unlock_title': unlock_prompt['unlock_title'],
            'unlock_sub_title': unlock_prompt['unlock_sub_title'],
            'unlock_action_title': unlock_prompt['unlock_action_title'],
            'unlock_action': unlock_prompt['unlock_action']

        }

        json_response = {

            'community': community_serializer_instance,
            'community_live': community_live,
            'invite_prompt': invite_prompt,
            'intro_collabcards': card_list
        }

    else:

        check_member = is_member_verified(community_id, member_id)
        if check_member:
            json_response = {

                'community': community_serializer_instance,
                'invite_prompt': invite_prompt,
                'intro_collabcards': card_list
            }
        else:
            json_response = {

                'community': community_serializer_instance,
                'intro_collabcards': card_list
            }
    return JsonResponse(json_response)


@shared_task
def update_chatroom_for_users_and_send_follow_notification(card_instance_id, user_id, conversation_id,
                                                           has_files=False):
    """ function to send follow notifications to users who are following the chatroom """

    update_chatroom_conversation_count_in_cache({'chatroom_id': card_instance_id})
    update_chatroom_conversation_creators_in_cache({'chatroom_id': card_instance_id, 'user_id': user_id})
    print(card_instance_id)
    print(conversation_id)

    if not has_files:
        send_follow_notification(card_id=card_instance_id, user_id=user_id, conversation_id=conversation_id)


def update_activity_in_chatroom_for_conversation_creation(card_instance_id, user_id):
    '''function to update the activity in chatroom for conversation creations'''
    # for users who are following the chatrooms
    # updating the expire time to null for all the users who are following the chatroom in collabcardState

    card_instance = Collabcard.objects.get(id=card_instance_id)

    update_status = collabcardState.objects.filter(card=card_instance, follow_status=True, remove=None).filter(
        ~Q(user=user_id)).update(updated_at=time.time())

    # the person who is making the conversation marking his chatroom active for expiry time
    state_filter = collabcardState.objects.filter(card=card_instance, user=user_id)

    if state_filter.exists():
        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       {'card': card_instance, 'user': user_id},
                                       {})

    # #updating the expire time to null for all the users  who are following the chatroom in conversationEngage
    # conversationEngage.objects.filter(card=card_instance).update(expiry_time=expiry_time)

    # for users who have seen the chatroom
    seen_filter = collabcardState.objects.filter(card=card_instance, follow_status=False,
                                                 remove=None).filter(
        Q(state=collabcard_states.COLLABCARD_STATE_SEEN) | Q(external_seen=True))

    if seen_filter.exists():
        for data in seen_filter:
            expiry_time = get_expiry_time_of_chatroom(data)
            data.updated_at = time.time()
            data.save()

    # print(update_status)


def handle_guest_follow_case(community_instance, user_instance, card_instance, aj, source_id, member_state,
                             platform_code=None, version_code=None):
    if (not aj and not source_id) \
            and (member_state == 0 or member_state == member_states.PENDING_MEMBER):
        return {'success': False, 'error_message': "Invalid link"}

    # user is a guest in chatroom
    if aj and source_id and (member_state == 0 or member_state == member_states.PENDING_MEMBER):
        current_time = TimeUtilities.current_time_in_milliseconds()
        context = {}
        context = adding_guest_in_chatroom(context, card_instance, aj, source_id, community_instance.id,
                                           user_instance.id,
                                           guest_header=True,
                                           created_at=current_time, platform_code=platform_code,
                                           version_code=version_code)

        # updating the collabcard state external follow for guest member
        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       {'card': card_instance, 'user': user_instance},
                                       {'external_follow': True})

        send_sync_notification.delay({'chatroom_id': card_instance.id,
                                      'member_id': user_instance.id,
                                      'sync_notification_type': SyncNotificationTypes.SINGLE_MEMBER.value})

        return context


@csrf_exempt
def collabcard_follow(request, function_dict=None):
    """ Api to follow collabcard by members Post API """

    collabcard_id = request.GET.get('collabcard_id', '')
    member_id = request.GET.get('member_id', '')
    status = request.GET.get('value', 'true')
    status = (status == "true")

    context = follow_chatroom_async(collabcard_id,
                                    member_id,
                                    status)

    if context.get('success'):
        return JsonResponse(context)

    return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)


@shared_task
def follow_chatroom_async(collabcard_id,
                          member_id,
                          status=True):
    # local imports from conversations in order to resolve circular import
    from .conversation.conversation_impl import ConversationHelper

    card_instance = Collabcard.get_chatroom_or_None(collabcard_id)

    if not card_instance:
        return {'success': False, "error_message": "Invalid chatroom id"}

    if not status and card_instance.is_secret:
        return {'success': False, "error_message": "Cannot unfollow chatroom"}

    user_instance = ModelUtilities.get_user_instance_or_none(member_id)

    if not user_instance:
        return {'success': False, "error_message": "Invalid member id"}

    # user cant unfollow his own collabcard
    if not status and card_instance.user_id == user_instance.id:
        return {'success': True}

    cache_key = CHATROOM_PARTICIPANTS_CREATED_CACHE_KEY.format(collabcard_id)
    are_chatroom_participants_created = CacheImpl.get_cache(cache_key)

    if all(['are_participants_created' in are_chatroom_participants_created,
            not are_chatroom_participants_created.get('are_participants_created')]):
        return {'success': False, "error_message": "Chatroom creation in progress. Try again after some time."}

    community_instance = card_instance.community
    member_state = Members.get_community_member_state(community_instance.id, user_instance.id)

    collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': card_instance,
                                                                                'user': user_instance})

    if not collabcard_state_filter:
        card_state_instance = collabcardState.create_chatroom_state_instance(card_instance, user_instance,
                                                                             expire_at=None,
                                                                             follow_status=status, external_follow=True)

        if status:
            ConversationHelper.create_conversation_state(card_instance=card_instance, user_instance=user_instance,
                                                         state=conversation_states.CONVERSATION_FOLLOW,
                                                         community_instance=community_instance,
                                                         member_state=member_state)

            create_chatroom_engagement(card_instance=card_instance, user_instance=user_instance,
                                       member_state=member_state)

    else:

        card_state_instance = collabcard_state_filter[0]

        follow_status = card_state_instance.follow_status

        if status and follow_status:
            return {'success': True}

        if not status and not follow_status:
            return {'success': True}

        if status:

            collabcard_state_filter.update(follow_status=status, updated_at=TimeUtilities.current_time_in_sec(),
                                           external_seen=True, external_follow=status)

            ConversationHelper.create_conversation_state(card_instance=card_instance, user_instance=user_instance,
                                                         state=conversation_states.CONVERSATION_FOLLOW,
                                                         community_instance=community_instance,
                                                         member_state=member_state)
            create_chatroom_engagement(card_instance=card_instance, user_instance=user_instance,
                                       member_state=member_state)

        else:

            collabcard_state_filter.update(follow_status=status, updated_at=TimeUtilities.current_time_in_sec(),
                                           is_tagged=False, external_seen=True, external_follow=status
                                           )

            # deleting the conversation engage
            ModelUtilities.delete_record_in_model(conversationEngage, {'card': card_instance,
                                                                       'user': user_instance})
            ConversationHelper.create_conversation_state(card_instance=card_instance, user_instance=user_instance,
                                                         state=conversation_states.CONVERSATION_UNFOLLOW,
                                                         community_instance=community_instance)

    if status:
        card_state_instance = collabcard_state_filter[0]
        ConversationHelper.update_homescreen_meta_on_chatroom_follow(community_instance, card_instance,
                                                                     card_state_instance, user_instance)
    send_sync_notification.delay({'chatroom_id': card_instance.id,
                                  'member_id': user_instance.id,
                                  'sync_notification_type': SyncNotificationTypes.SINGLE_MEMBER.value})

    ElasticSearchSync.update_chatroom_for_user.delay(card_instance.id, user_instance.id)

    update_last_unseen_in_engage(user=user_instance.id, community=card_instance.community_id)

    if card_instance.is_secret \
            and member_state == member_states.ADMIN \
            and status:
        participants_list = json.loads(card_instance.secret_chatroom_participants)

        if user_instance.id not in participants_list:
            participants_list.append(user_instance.id)
            ModelUtilities.model_update(Collabcard, {'id': card_instance.id},
                                        {'secret_chatroom_participants':
                                             json.dumps(participants_list)})

    return {'success': True}


def collabcard_follow_internal(func_dict, state=collabcard_states.COLLABCARD_STATE_SEEN,
                               set_expiry_time_none=False, external_seen=True):
    """ folowing collabcard internally """

    card_id = func_dict['collabcard_id']
    member_id = func_dict['member_id']
    status = func_dict['status']
    is_guest = False
    is_tagged = False
    ref_instance = None
    mute_status = False

    if 'is_guest' in func_dict:
        is_guest = func_dict.get('is_guest')
        source_id = func_dict.get('source_id')
        ref_filter = User.objects.filter(id=source_id)
        if ref_filter.exists():
            ref_instance = ref_filter[0]
    elif 'is_tagged' in func_dict and func_dict['is_tagged']:
        is_tagged = True
        mute_status = True

    try:
        card_instance = Collabcard.objects.get(id=card_id)
        user_instance = User.objects.get(id=member_id)
    except:
        return

    collabcard_state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)

    if collabcard_state_filter.exists():
        if collabcard_state_filter[0].follow_status == status:

            if collabcard_state_filter[0].is_tagged:
                update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                               {'card': card_instance, 'user': user_instance},
                                               {'is_tagged': False, 'mute_status': False})
            return

        if is_guest:

            update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                           {'card': card_instance, 'user': user_instance},
                                           {
                                               'follow_status': status,
                                               'state': state,
                                               'is_guest': is_guest,
                                               'source': ref_instance,
                                               'is_tagged': is_tagged,
                                               'external_seen': external_seen,
                                               'mute_status': mute_status,
                                           })

        else:

            update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                           {'card': card_instance, 'user': user_instance},
                                           {
                                               'follow_status': status,
                                               'is_tagged': is_tagged,
                                               'external_seen': external_seen,
                                               'mute_status': mute_status,
                                               'state': state
                                           })

        ElasticSearchSync.update_chatroom_for_user.delay(card_id, member_id)

    else:

        if is_tagged:
            mute_status = True
        else:
            mute_status = False
        expiry_time = get_expiry_time_of_chatroom() if not set_expiry_time_none else None

        from collabmates_api.community.community_impl import CommunityHelper
        community_noti_instance = CommunityHelper.fetch_community_noti_settings_instance(card_instance.community)
        community_current_noti_state = community_noti_instance.noti_state if community_noti_instance else noti_states.ALL_MESSAGES

        create_chatroom_state_instance(card_instance, user_instance, state=0,
                                       expire_at=expiry_time, external_seen=external_seen, is_guest=is_guest,
                                       source=ref_instance, follow_status=status,
                                       mute_status=mute_status, is_tagged=is_tagged,
                                       function_called="collabcard_follow_internal",
                                       noti_state=community_current_noti_state)

    if status:
        member_state = 0
        member_instance = Members.objects.filter(member_id=user_instance, community_id=card_instance.community)
        if member_instance.exists():
            member_state = member_instance[0].state
        create_chatroom_engagement(card_instance=card_instance, user_instance=user_instance, member_state=member_state)

    update_my_chatrooms_for_users(chatroom_id=card_instance.id, user_id=member_id)

    # function to set activity of chatroom
    update_activity_in_chatroom(card_instance, user_instance)


def collabcard_follow_internal_v1(
        chatroom_instance,
        tagged_member_list,
        is_tagged,
        is_group_tag_everyone):
    """ folowing collabcard internally """

    tagged_user_datas = []

    for user_id in tagged_member_list:
        func_dict = {
            'member_id': user_id,
            'collabcard_id': chatroom_instance.id,
            'status': True,
            'source': "auto-following-chatroom",
            'is_tagged': is_tagged
        }

        card_id = func_dict['collabcard_id']
        member_id = func_dict['member_id']
        status = func_dict['status']
        is_guest = False
        is_tagged = False
        ref_instance = None
        mute_status = False

        if 'is_guest' in func_dict:
            is_guest = func_dict.get('is_guest')
            source_id = func_dict.get('source_id')
            ref_filter = User.objects.filter(id=source_id)
            if ref_filter.exists():
                ref_instance = ref_filter[0]
        elif 'is_tagged' in func_dict and func_dict['is_tagged']:
            is_tagged = True
            mute_status = True

        tagged_user_data = {
            'card_id': card_id,
            'member_id': member_id,
            'status': status,
            'is_guest': is_guest,
            'is_tagged': is_tagged,
            'ref_instance': ref_instance,
            'mute_status': mute_status
        }
        tagged_user_datas.append(tagged_user_data)

    update_collabcard_state_user_ids = [int(element['member_id']) for element in tagged_user_datas]

    if is_group_tag_everyone:
        collabcard_state_member_ids = list(ModelUtilities.get_model_filter(
            collabcardState,
            {
                'card_id': chatroom_instance.id
            }
        ).values_list(
            'user_id',
            flat=True
        ))

        existing_user_ids = ListUtilities.get_common_elements(update_collabcard_state_user_ids,
                                                              collabcard_state_member_ids)

        collabcardState.objects.filter(
            card=chatroom_instance.id,
            user__in=existing_user_ids
        ).update(
            follow_status=True,
            is_tagged=False,
            mute_status=False
        )

    elif is_tagged:
        collabcard_non_followers_list = list(ModelUtilities.get_model_filter(
            collabcardState,
            {
                'card_id': chatroom_instance.id,
                'follow_status': False
            }
        ).values_list(
            'user_id',
            flat=True
        ))
        non_followers_tagged_users = ListUtilities.get_common_elements(update_collabcard_state_user_ids,
                                                                       collabcard_non_followers_list)
        collabcardState.objects.filter(
            card=chatroom_instance.id,
            user__in=non_followers_tagged_users
        ).update(
            follow_status=True,
            is_tagged=True,
            mute_status=True
        )

    update_elastic_search_data_for_chatroom_users.delay(chatroom_instance.id, update_collabcard_state_user_ids)
    create_chatroom_engagements_for_users.delay(chatroom_instance.id, update_collabcard_state_user_ids)


@shared_task
def update_elastic_search_data_for_chatroom_users(card_id, member_ids):
    for member_id in member_ids:
        ElasticSearchSync.update_chatroom_for_user(card_id, member_id)


@shared_task
def create_chatroom_engagements_for_users(card_id, member_ids):
    for member_id in member_ids:
        card_instance = Collabcard.objects.get(id=card_id)
        user_instance = User.objects.get(id=member_id)

        member_state = 0
        member_instance = Members.objects.filter(member_id=user_instance, community_id=card_instance.community)
        if member_instance.exists():
            member_state = member_instance[0].state

        create_chatroom_engagement(card_instance=card_instance, user_instance=user_instance, member_state=member_state)
        update_my_chatrooms_for_users(chatroom_id=card_instance.id, user_id=user_instance.id)
        update_activity_in_chatroom(card_instance, user_instance)

@csrf_exempt
def collabcards_seen(request):
    '''This functions stores the details of members who have seen the card'''

    params = request.GET
    community_id = None
    card_id = None
    user_id = None

    if 'community_id' in params:
        community_id = params['community_id']

    if 'collabcard_id' in params:
        card_id = params['collabcard_id']

    if 'member_id' in params:
        user_id = params['member_id']

    api_key = RequestUtilities.get_api_key_from_headers(request)

    community = validate_community_id_or_api_key(community_id, api_key)

    if community.get('error_message'):
        return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community.get('error_message'),
                                                                            status_codes.HTTP_400_BAD_REQUEST))

    community_instance = community.get('community_instance')

    context = collabcards_seen_internal(card_id, user_id, community_instance)

    send_sync_notification.delay({'community_id': community_instance.id,
                                  'member_id': user_id,
                                  'sync_notification_type': SyncNotificationTypes.SINGLE_MEMBER.value})

    if 'error_message' in context:
        return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                            context.get('status')))

    return JsonResponse(context)


def collabcards_seen_internal(card_id, user_id, community_instance):
    '''This internal functions stores the details of members who have seen the card'''

    user_instance = ModelUtilities.get_user_instance_or_none(user_id)

    if not user_instance:
        return ResponseUtilities.get_impl_error_context('Invalid x-member-id',
                                                        status_code=status_codes.HTTP_400_BAD_REQUEST)

    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

    if not card_instance:
        return ResponseUtilities.get_impl_error_context('Invalid card id',
                                                        status_code=status_codes.HTTP_400_BAD_REQUEST)

    # saving the state in collabcard state table if it is not present
    is_present = collabcardState.objects.filter(card=card_instance, user=user_instance)

    if not is_present.exists():
        create_chatroom_state_instance(card_instance, user_instance,
                                       function_called="collabcards_seen_internal")
        update_last_unseen_in_engage(user=user_instance, community=community_instance)

    else:

        state_instance = is_present[0]
        should_update_time = False

        if state_instance.state == collabcard_states.COLLABCARD_STATE_UNSEEN:
            state_instance.state = collabcard_states.COLLABCARD_STATE_SEEN
            should_update_time = True

        if not state_instance.external_seen:
            state_instance.external_seen = True
            should_update_time = True

        if should_update_time:
            state_instance.updated_at = TimeUtilities.current_time_in_sec()

        state_instance.save()
        update_last_unseen_in_engage(user=user_instance, community=community_instance)

    return {'success': True}


@csrf_exempt
def collabcard_attend(request):
    '''attending a event on a event card'''

    member_id = get_member_id_from_headers(request)

    if request.user.is_authenticated and not get_request_type(request):
        # user id from request if user in logged in
        member_id = request.user.id

    collabcard_id = request.GET.get('collabcard_id')
    status = request.GET.get('value', 'true')

    card_instance = Collabcard.objects.get(id=collabcard_id)

    user_instance = User.objects.get(id=member_id)

    if status != 'true':
        status = False
    else:
        status = True

    # event attending
    if status:

        try:
            update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                           {'card': card_instance, 'user': user_instance},
                                           {'state': collabcard_states.COLLABCARD_STATE_ATTENDING,
                                            'attending_status': True})

        except:
            create_chatroom_state_instance(card_instance, user_instance,
                                           state=collabcard_states.COLLABCARD_STATE_ATTENDING,
                                           expire_at=None, external_seen=True, is_guest=False, source=None,
                                           follow_status=True, mute_status=False, is_tagged=False,
                                           function_called="collabcard_attend", attending_status=True)

        func_dict = {'member_id': member_id, 'collabcard_id': card_instance.id, 'status': True,
                     'source': "Event attend"}
        collabcard_follow_internal(func_dict, state=collabcard_states.COLLABCARD_STATE_ATTENDING)

    else:

        state = collabcard_states.COLLABCARD_STATE_SEEN
        try:
            update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                           {'card': card_instance, 'user': user_instance},
                                           {'state': state, 'attending_status': False})

        except:
            create_chatroom_state_instance(card_instance, user_instance,
                                           state=state,
                                           expire_at=None, external_seen=True, is_guest=False, source=None,
                                           follow_status=True, mute_status=False, is_tagged=False,
                                           function_called="collabcard_attend")

    update_event_answer_text(card_instance)  # function to update the text when a user attends an event
    update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                   {'card': card_instance},
                                   {})

    send_sync_notification.delay({'chatroom_id': collabcard_id,
                                  'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

    ElasticSearchSync.update_chatroom_for_user.delay(collabcard_id, member_id)

    return JsonResponse({'success': True})


def update_event_answer_text(collabcard_instance):
    """function to update the answer text of card when an event is created"""

    if collabcard_instance.type == card_types.CARD_EVENT or collabcard_instance.type == card_types.CARD_PUBLIC_EVENT:

        # getting the number of people interestes in event
        event_list_members = collabcardState.objects.filter(card=collabcard_instance).filter(
            Q(state=collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING) | Q(
                state=collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING)).order_by('id')
        members_count = event_list_members.count()
        ans_text = ''

        if members_count == 1:
            # get the name of the user who is attending
            username = event_list_members[0].user.userinfo.name
            ans_text = username + " is attending"
            collabcard_instance.answer_text = ans_text

        elif members_count >= 2:
            first_member = event_list_members[0].user.userinfo.name
            second_member = event_list_members[1].user.userinfo.name

            if members_count == 2:
                ans_text = """%s and %s are attending""" % (str(first_member), str(second_member))

            else:
                left_count = members_count - 2
                ans_text = """%s, %s & %s others are attending""" % (str(first_member), str(second_member), left_count)
            collabcard_instance.answer_text = ans_text

        else:
            collabcard_instance.answer_text = ans_text

        collabcard_instance.attending_count = members_count
        collabcard_instance.save()


def decode_url(request):
    """function to send og tags of the link"""

    try:
        url = request.GET.get('url')
        og_tags = UriTagsImpl(url).get_tags_from_uri()

    except Exception as e:
        error_logger.error(e)
        return JsonResponse({
            'success': False,
            'error_message': f'API failed api=decode_url, reason={e}'
        }, status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)

    return JsonResponse({
        'success': True,
        'og_tags': og_tags
    })


def get_chatrooms(chatroom_list, member_id, active=None, device_id=''):
    """function to get chatrooms"""

    member_id = NumberUtilities.get_integer_from_string(member_id)

    chatrooms = []
    for card_instance in chatroom_list:

        if is_draft_chatroom(card_instance, member_id, device_id):
            continue

        if card_instance.is_secret:
            participants_list = json.loads(card_instance.secret_chatroom_participants)

            if member_id not in participants_list:
                continue

        chatroom_instance = get_chatroom_instance(card_instance, member_id)

        if chatroom_instance['secret_chatroom_left']:
            continue

        conversation_filter = card_answers.objects.filter(card=card_instance.id,
                                                          state=conversation_states.ANSWER
                                                          ).filter(Q(attachment_count=0) |
                                                                   Q(attachments_uploaded=True)
                                                                   ).order_by('id')
        chatroom_instance['total_response_count'] = conversation_filter.count()

        if card_instance.internal_link:
            try:
                preview = get_preview_for_url(member_id, card_instance.internal_link,
                                              community_instance=card_instance.preview_community,
                                              chatroom_instance=card_instance.preview_chatroom,
                                              send_preview_text=False)

                if preview:
                    chatroom_instance['preview'] = preview

            except Exception as e:
                error_logger.error(e.args)

        last_response_members = get_member_images_of_chatroom(conversation_filter)
        chatroom_instance['members_images'] = last_response_members['members_images']
        chatroom_instance['last_response_members'] = last_response_members['last_response_members']

        chatrooms.append(chatroom_instance)

    return chatrooms


def get_chatrooms_version_2(chatroom_list, member_id, active=None, device_id=''):
    '''function to get chatrooms'''

    chatrooms = []
    for data in chatroom_list:
        card_instance = data.card

        if is_draft_chatroom(card_instance, member_id, device_id):
            continue

        chatroom_instance = get_chatroom_instance(card_instance, member_id, state_instance=data)
        conversation_filter = card_answers.objects.filter(card=card_instance.id,
                                                          state=conversation_states.ANSWER
                                                          ).filter(Q(attachment_count=0) |
                                                                   Q(attachments_uploaded=True)
                                                                   ).order_by('id')
        chatroom_instance['total_response_count'] = conversation_filter.count()

        if card_instance.internal_link:
            try:
                preview = get_preview_for_url(member_id=member_id,
                                              preview_url=card_instance.internal_link,
                                              community_instance=card_instance.preview_community,
                                              chatroom_instance=card_instance.preview_chatroom,
                                              send_preview_text=False)
                if preview:
                    chatroom_instance['preview'] = preview

            except Exception as e:
                error_logger.error(e.args)
        last_response_members = get_member_images_of_chatroom(conversation_filter)
        chatroom_instance['members_images'] = last_response_members['members_images']
        chatroom_instance['last_response_members'] = last_response_members['last_response_members']

        chatrooms.append(chatroom_instance)

    return chatrooms


def fetch_chatroom_feed(request):
    """ api to fetch chatroom feed """

    community_id = request.GET.get('community_id')
    page = request.GET.get('page', 1)
    is_ios = is_platform_ios(request)
    chatroom_id = request.GET.get('chatroom_id')
    scroll_direction = request.GET.get('scroll_direction')

    device_id = RequestUtilities.get_device_id_from_headers(request)

    if scroll_direction and not chatroom_id:
        context = get_error_context(False, "send chatroom id with scroll direction")
        return JsonResponse(context)

    active = None

    member_id = get_member_id_from_headers(request)
    if member_id is None:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context)

    chatroom_filter = Collabcard.objects.filter(community=community_id,
                                                is_pending=False, is_deleted=False, is_private=False).order_by('id')

    chatrooms = []
    context = {}

    if not chatroom_id and not scroll_direction:

        last_seen = collabcardState.objects \
            .filter(community=community_id,
                    user=member_id,
                    secret_chatroom_left=False) \
            .filter(~Q(state=0)) \
            .order_by('-card_id')
        if not last_seen.exists():
            chatroom_list = pagination(chatroom_filter, page, paginate_by=5)
            chatrooms = get_chatrooms(chatroom_list, member_id, device_id=device_id)
        else:
            last_seen = last_seen[0]
            upward = chatroom_filter.filter(id__lte=last_seen.card.id).order_by('-id')[:3]
            downward = chatroom_filter.filter(id__gt=last_seen.card.id)[:3]
            # upward = Collabcard.objects.filter(id__lt=last_seen.card.id,community=community_id).order_by('id')[:3]
            # downward = Collabcard.objects.filter(id__gt=last_seen.card.id,community=community_id).order_by('id')[:3]
            chatroom_filter = upward | downward
            chatroom_list = chatroom_filter.order_by('id')
            chatrooms = get_chatrooms(chatroom_list, member_id, active, device_id=device_id)

        context['header'] = chatroom_feed_header(community_id, member_id)

    else:
        scroll_direction = int(scroll_direction)
        if scroll_direction == 0:  # upward scroll

            upward = chatroom_filter.filter(id__lt=chatroom_id).order_by('-id')[:5]
            upward = reverse_conversations_for_upward_pagination(upward)
            # print(upward)
            chatrooms = get_chatrooms(upward, member_id, active, device_id=device_id)

        elif scroll_direction == 1:  # downward scroll

            downward = chatroom_filter.filter(id__gt=chatroom_id).order_by('id')[:5]
            chatrooms = get_chatrooms(downward, member_id, active, device_id=device_id)

    context['chatrooms'] = chatrooms

    return JsonResponse(context)


def fetch_community_chatroom_feed(request):
    '''Version 1 community collabcards'''

    member_id = get_member_id_from_headers(request)

    try:
        size = request.GET.get('size', 3)
        size = int(size)
    except Exception as e:
        error_logger.error(e)
        size = 3

    community_id = request.GET.get('community_id')
    api_key = RequestUtilities.get_api_key_from_headers(request)

    community_dict = validate_community_id_or_api_key(community_id, api_key)

    if community_dict.get('error_message'):
        context = ResponseUtilities.get_view_impl_error_context(community_dict.get('error_message'),
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    community_instance = community_dict.get('community_instance')

    chatroom_filter = \
        Collabcard.objects.filter(community=community_instance,
                                  is_pending=False,
                                  is_deleted=False).filter(~Q(type=card_types.CARD_INTRO)).order_by('-id')

    total_chatrooms = chatroom_filter.count()
    chatroom_list = []
    for chatroom in chatroom_filter:

        chatroom_data = get_chatroom_instance(chatroom, member_id)
        chatroom_list.append(chatroom_data)
        size = size - 1
        if size == 0:
            break

    context = {
        'success': True,
        'chatrooms': chatroom_list,
        'total_chatrooms': total_chatrooms
    }

    return JsonResponse(context)


def chatroom_feed_header(community_id, member_id):
    '''function to get chatroom feed header'''

    community_instance = Community.objects.get(id=community_id)

    member_list = get_tagging_list_internal(community_instance.id)

    member_names = []

    for member in member_list:

        if int(member['id']) != int(member_id):

            names = member['name'].split(" ")
            if names:
                member_names.append(names[0])
            else:
                member_names.append(member['name'])

    # sorting member names in ascending order
    member_names.sort()

    header = {
        'community_name': community_instance.name,
        'member_names': member_names[:10]
    }
    return header
    # sending member_names


############# upload files flow   ##########################

@csrf_exempt
def upload_files(request):
    """function to upload files"""
    body = request.GET

    member_id = get_member_id_from_headers(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)
    is_android = RequestUtilities.is_request_android(request)
    conversation = None
    chatroom_local = None

    context = {
        'success': True,
    }

    if request.user.is_authenticated and is_request_web(request):
        current_member_id = request.user.id

    community_id_for_sync = None

    if 'community_id' in body and body['community_id']:
        # if image to be updated in community
        community_id = body['community_id']
        community_id_for_sync = community_id
        community = Community.objects.get(id=community_id)
        community.image_link = body['url']
        community.image_link_round = body['url']
        upload_community_thumbnail.delay(community_id, body['url'])
        community.save()
        # updating the create community second step
        createCommunityAction.objects.filter(community=community, step_no="Step 2").update(
            current_point=10)

        # saving the update image details if the image is updated
        edit = request.GET.get('edit', False)
        if edit == 'true':
            if not member_id:
                return JsonResponse({'success': False, 'error_message': "Send member id in headers"})
            else:
                member_instance = User.objects.get(id=member_id)

            instance = communityUpdate()
            instance.updated_field = "image"
            instance.updated_time = time.time()
            instance.updated_member = member_instance
            instance.community = community
            instance.save()

    elif 'collabcard_id' in body and body['collabcard_id']:
        attachment_type = body['type']
        collabcard_id = body['collabcard_id']

        card_instance = Collabcard.objects.get(id=collabcard_id)
        community_id_for_sync = card_instance.community.id
        file = Card_Attachment()
        file.collabcard = card_instance
        file.type = attachment_type
        file.file_url = body['url']
        file.index = body.get('index', 0)
        file.height = body.get('height', None)
        file.width = body.get('width', None)
        file.save()

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       {'user': member_id, 'card': card_instance},
                                       {})

        uploaded_files_count = Card_Attachment.objects.filter(collabcard=card_instance).count()

        all_files_uploaded = uploaded_files_count == card_instance.attachment_count

        if all_files_uploaded:
            card_instance.attachments_uploaded = True
            card_instance.save()
            user_instance = User.objects.get(id=member_id)

            update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                           {'user': member_id, 'card': card_instance},
                                           )

            if not card_instance.is_secret:
                set_chatroom_state_for_all_members_on_card_creation.delay(card_instance.community.id,
                                                                          card_id=collabcard_id,
                                                                          function_called="upload_files_version_1")
            send_chatroom_creation_notification(card_instance, user_instance)

        member_data = {'member_id': member_id, 'current_user_id': member_id, 'state_instance': None}
        chatroom_local = GetChatroomInstanceSerializer(card_instance, context=member_data, many=False)

    elif 'answer_id' in body and body['answer_id']:
        attachment_type = body['type']
        answer_id = body['answer_id']
        files_count = NumberUtilities.get_integer_from_string(body.get('files_count', "0"))

        answer_instance = card_answers.objects.get(id=answer_id)
        answer_instance.attachment_count = files_count
        answer_instance.last_updated = int(round(time.time() * 1000))
        answer_instance.save()

        community_id_for_sync = answer_instance.community.id

        file = answerAttachment()
        file.answer = answer_instance
        file.type = attachment_type
        file.file_url = body['url'] if 'url' in body else None
        file.index = body.get('index', 0)
        file.height = body.get('height', None)
        file.width = body.get('width', None)
        file.location_name = body.get('location_name', None)
        file.location_lat = body.get('location_lat', None)
        file.location_long = body.get('location_long', None)
        file.save()

        # saving last answer id
        uploaded_files_count = answerAttachment.objects.filter(answer=answer_instance).count()

        if uploaded_files_count == files_count:
            # # updating the last updated when posting answer
            answer_instance.attachments_uploaded = True
            answer_instance.save()

            chatroom_id = answer_instance.card.id
            update_last_answer_id(chatroom_id, answer_instance.id)
            update_my_chatrooms_for_users(chatroom_id=chatroom_id)
            send_follow_notification.delay(card_id=chatroom_id, user_id=answer_instance.user.id,
                                           conversation_id=answer_instance.id)

        conversation_context = {"current_user_id": member_id, "fetch_reply": True}
        conversation = CardAnswersDBSyncSerializer(answer_instance, context=conversation_context, many=False).data

    elif 'poll_id' in body and body['poll_id']:

        try:
            instance = CollabcardPolls.objects.get(id=body['poll_id'])
            instance.image_url = body['url']
            instance.save()
            answer_instance = instance.card.id
        except:
            return JsonResponse({'success': False, 'error_message': "Send valid poll id"})

    elif 'draft_id' in body and body['draft_id']:
        attachment_type = body['type']
        draft_id = body['draft_id']
        draft_instance = draftChatroom.objects.get(id=draft_id)

        instance = draftChatroomFiles()
        instance.draft = draft_instance
        instance.file_url = body['url']
        instance.index = body.get('index', 0)
        instance.height = body.get('height', None)
        instance.width = body.get('width', None)
        instance.type = attachment_type
        instance.save()

    elif 'draft_poll_id' in body and body['draft_poll_id']:

        try:
            instance = draftPolls.objects.get(id=body['draft_poll_id'])
            instance.image_url = body['url']
            instance.save()
        except:
            return JsonResponse({'success': False, 'error_message': "Send valid draft poll id"})

    else:
        context['success'] = False
        context['error_message'] = "parameters are missing"

    # sending the conversation instance if present
    if conversation:
        context['conversation'] = conversation

    # sending the chatroom local object
    if chatroom_local:
        context['chatroom_local'] = chatroom_local.data

    if community_id_for_sync:
        send_sync_notification.delay({'community_id': community_id_for_sync,
                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

    return JsonResponse(context)


@csrf_exempt
def upload_files_version_1(request):
    """function to upload files"""
    context = save_attachments(request)

    success = context.get('success', False)
    status = status_codes.HTTP_200_OK if success else status_codes.HTTP_400_BAD_REQUEST

    return JsonResponse(context, status=status)


def get_community_id_from_v1_upload_files(res):
    community_id = None

    if 'community_id' in res and res['community_id']:
        community_id = res['community_id']

    elif 'chatroom_id' in res and res['chatroom_id']:
        chatroom_id = res['chatroom_id']
        community_instance = Collabcard.get_community_of_chatroom_or_none(chatroom_id)

        if community_instance:
            community_id = community_instance.id

    elif 'conversation_id' in res and res['conversation_id']:

        answer_instance = ModelUtilities.get_model_instance_or_none(card_answers, res['conversation_id'])

        if answer_instance:
            community_id = answer_instance.community.id

    elif 'poll_id' in res and res['poll_id']:

        poll_instance = ModelUtilities.get_model_instance_or_none(card_answers, res['poll_id'])

        if poll_instance:
            community_id = poll_instance.card.community.id

    return community_id


def save_attachments(request):
    """ save attachments for cards and conversations """
    member_id = get_member_id_from_headers(request)
    body = RequestUtilities.load_request_body(request)

    if not body:
        return {'success': False, 'error_message': "Invalid Request Body"}

    if member_id is None:
        return {'success': False, 'error_message': "Send member id in headers"}

    conversation = None
    chatroom_local = None

    context = {
        'success': True,
    }

    if is_request_web(request):
        if request.user.is_authenticated:
            member_id = request.user.id

    if 'community_id' in body and body['community_id']:
        context = save_community_image(body, member_id)
        if context is not None:
            return context

    elif 'chatroom_id' in body and body['chatroom_id']:
        version_code = RequestUtilities.get_version_code_from_headers(request)

        is_android = RequestUtilities.is_request_android(request)
        is_ios = RequestUtilities.is_request_ios(request)

        chatroom_local = upload_chatroom_attachments(body, member_id,
                                                     version_code=version_code,
                                                     is_android=is_android,
                                                     is_ios=is_ios)

        if 'success' in chatroom_local and not chatroom_local['success']:
            return chatroom_local

    elif 'conversation_id' in body and body['conversation_id']:

        conversation = upload_conversation_attachments(body, member_id)

        if 'success' in conversation and not conversation['success']:
            return conversation

    elif 'poll_id' in body and body['poll_id']:

        try:
            save_poll_attachments(body)
        except:
            return {'success': False,
                    'error_message': "Send valid poll id"}

    elif 'draft_id' in body and body['draft_id']:
        save_draft_attachments(body)

    elif 'draft_poll_id' in body and body['draft_poll_id']:

        try:
            save_draft_poll_attachments(body)
        except:
            return {'success': False,
                    'error_message': "Send valid draft poll id"}

    else:
        context['success'] = False
        context['error_message'] = "parameters are missing"

    # sending the conversation instance if present
    if conversation:
        context['conversation'] = conversation

    # sending the chatroom local object
    if chatroom_local:
        context['chatroom_local'] = chatroom_local.data

    return context


def upload_chatroom_attachments(body, member_id, version_code=0, is_android=False, is_ios=False):
    """ function to upload chatroom attachments """

    chatroom_id = body['chatroom_id']
    try:
        chatroom_instance = Collabcard.objects.get(id=chatroom_id)

    except Collabcard.DoesNotExist:
        return {'success': False,
                'error_message': "Send valid chatroom id"}

    save_chatroom_attachments(chatroom_instance, body)

    # updating updated_at for syncing apis
    update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                   {'user': member_id, 'card': chatroom_instance},
                                   {})

    uploaded_files_count = Card_Attachment.objects.filter(collabcard=chatroom_instance).count()

    all_files_uploaded = uploaded_files_count == chatroom_instance.attachment_count

    if all_files_uploaded:
        chatroom_instance.attachments_uploaded = True
        chatroom_instance.save()

        user_instance = User.objects.get(id=member_id)

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       {'card': chatroom_instance, 'user': user_instance},
                                       {})

        community_id = chatroom_instance.community_id

        if not chatroom_instance.is_secret:
            set_chatroom_state_for_all_members_on_card_creation.delay(community_id,
                                                                      card_id=chatroom_id,
                                                                      function_called="upload_files_version_1")

        if chatroom_instance.is_pending:
            update_pending_chatroom_count_for_promoters.delay(community_id)

        update_last_unseen_in_engage_on_card_creation.delay(community_id)

        send_chatroom_creation_notification(chatroom_instance, user_instance)
        update_event_in_webflow_service.delay({'chatroom_id': chatroom_instance.id,
                                               'update_type': event_webflow_update_types.FILE})

    member_data = {'member_id': member_id,
                   'current_user_id': member_id,
                   'state_instance': None}
    chatroom_local = GetChatroomInstanceSerializer(chatroom_instance, context=member_data, many=False)

    return chatroom_local


def upload_conversation_attachments(body, member_id):
    """ function to upload conversation attachments """
    conversation_id = body['conversation_id']

    conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

    if not conversation_instance:
        return {'success': False,
                'error_message': "Send valid conversation id"}

    save_conversation_attachments(body, conversation_instance)

    uploaded_files_count = answerAttachment.objects.filter(answer=conversation_instance).count()

    all_files_uploaded = uploaded_files_count == conversation_instance.attachment_count

    # updating the last updated when posting answer
    conversation_instance.last_updated = TimeUtilities.current_time_in_milliseconds()

    if body.get('type') == "gif":
        conversation_instance.answer = conversation_instance.answer + GIF_ATTACHMENT_FILL_TEXT

    if not all_files_uploaded:
        conversation_instance.save()

    elif all_files_uploaded:
        conversation_instance.attachments_uploaded = True
        conversation_instance.save()

        # local imports from conversation module for saving data in firebase
        from .conversation.conversation_impl import ConversationHelper

        chatroom_instance = conversation_instance.card
        community_instance = conversation_instance.community

        ConversationHelper.update_latest_conversation_id_to_firebase.delay(chatroom_instance.id,
                                                                           conversation_instance.id)
        ConversationHelper.update_homescreen_meta_on_conversation_creation(
            community_instance, chatroom_instance, conversation_instance)

        update_conversation_engage_for_chatrooms(card_id=chatroom_instance.id, user_id=member_id,
                                                 last_conversation_id=conversation_instance.id,
                                                 unseen_count=0)

        send_follow_notification.delay(card_id=chatroom_instance.id, user_id=conversation_instance.user_id,
                                       conversation_id=conversation_instance.id)

    conversation_context = {"current_user_id": member_id, "fetch_reply": True}
    conversation = CardAnswersDBSyncSerializer(conversation_instance, context=conversation_context, many=False).data

    return conversation


############# functions for  login flow   ##########################

def get_request_type(request):
    '''function to get the mobile type of user whether its ios or android'''

    # print(request.META)
    if 'HTTP_X_PLATFORM_CODE' in request.META:
        request_agent = request.META['HTTP_X_PLATFORM_CODE']
        if request_agent == "an":
            return "Android"
        elif request_agent == "ios":
            return "iOS"
    return False


@csrf_exempt
def login_authenticate_version_1(request):
    ''' function to login a user '''

    if request.method == 'POST':
        start_time = time.time()
        res = json.loads(request.body)
        # print(res)
        login_type = res['type']

        if login_type == "google":

            if 'google_id_token' in res:
                google_id_token = res['google_id_token']
                context = login_with_google(google_id_token, request, res)
                info_logger.info(context)

                return JsonResponse(context)

            return JsonResponse({'success': False, 'error_message': "send google id token in body"})

        elif login_type == 'facebook':

            dic_form = res['login_json']
            json_to_save = json.dumps(dic_form)

            context = login_with_facebook(request, res, json_to_save)

            return JsonResponse(context)

        elif login_type == 'linkedIn':

            dic_form = res['login_json']
            json_to_save = json.dumps(dic_form)

            context = login_with_linkedin(request, res, json_to_save)

            return JsonResponse(context)

        elif login_type == 'linkedin_web':

            dic_form = linked_in_authentication(request)
            json_to_save = json.dumps(dic_form)

            if 'success' in dic_form and not dic_form['success']:
                return JsonResponse(dic_form, status=400)

            res['login_json'] = dic_form

            context = login_with_linkedin(request, res, json_to_save, login_type=login_type)

            return JsonResponse(context)

        elif login_type == "apple":

            dic_form = res['login_json']
            json_to_save = json.dumps(dic_form)

            context = login_with_apple(request, res, json_to_save)

            return JsonResponse(context)

        elif login_type == "custom":
            # insert code here

            context = custom_login(request, res, login_type="custom")
            end_time = time.time()
            info_logger.info(f"LOGIN VIEW RESPONSE TIME = {end_time - start_time}")

            if context.get('error_message'):
                return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

            return JsonResponse(context)
    else:
        context = get_error_context(False, "Send a post request")

        return JsonResponse(context)


@csrf_exempt
def linked_in_authentication(request):
    request_body = json.loads(request.body)

    info_logger.info(f"linked in web body {request_body}")

    code = request_body.get('code', None)

    if not code:
        context = get_error_context(False, "code is not correct")
        return context

    response = get_access_token(request_body)
    info_logger.info(response)

    if 'access_token' not in response:
        context = get_error_context(False, "Try after sometime!!!!!")
        context['linked_in_error'] = response
        return context

    return get_user_details(response['access_token'])


def get_access_token(request_body):
    code = request_body.get('code', None)
    grant_type = request_body.get('grant_type', None)
    redirect_uri = request_body.get('redirect_uri', None)
    client_id = request_body.get('client_id', None)
    client_secret = request_body.get('client_secret', None)

    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': grant_type,
        'redirect_uri': redirect_uri,
        'code': code
    }

    ans = rqst.post(LINKED_IN_ACCESS_TOKEN_URL, params=params)
    response = ans.json()
    info_logger.info(response)
    return response


def get_user_details(access_token):
    user_url = LINKED_IN_USER_URL + access_token
    email_url = LINKED_IN_EMAIL_URL + access_token

    # getting public details of user from Linked In
    resp = rqst.get(user_url)
    data_main = json.loads(resp.text)
    info_logger.info(f"linked in web data_main  {data_main}")
    # getting user email details from Linked In
    resp = rqst.get(email_url)
    email_data = json.loads(resp.text)
    info_logger.info(f"linked in web email_data  {email_data}")
    data_main['email'] = email_data

    info_logger.info(f"linked in web response  {data_main}")

    return data_main


def create_user(user_name, email, id, apple_id=False):
    ''' function to create Auth-User of a user '''

    user_name = user_name + "_" + str(id)

    user = User.objects.filter(email=email)
    if apple_id and not user.exists():
        user = User.objects.filter(username=user_name)

    if not user.exists():

        user = User()
        user.username = user_name.title()
        if email is not None:
            user.email = email
        user.save()
    else:
        user = user[0]

    return user


def create_userinfo(user, email, user_name, profile_picture, login_type, json_to_save, city=None, apple_id=None):
    ''' function to create User-Info of a user '''

    userinfo = Userinfo.objects.filter(user_id=user)
    if apple_id and not userinfo.exists():
        userinfo = Userinfo.objects.filter(apple_id=apple_id)

    if not userinfo.exists():
        userinfo = Userinfo()
        userinfo.user_id = user
        if email is not None:
            user.email = email
        userinfo.name = user_name.title()
        if profile_picture is not None:
            userinfo.image_link = upload_image_to_firebase(profile_picture, user.id)
        userinfo.login_type = login_type
        userinfo.login_json = json_to_save
        userinfo.created_at = time.time()
        userinfo.city = city
        if apple_id:
            userinfo.apple_id = apple_id
        userinfo.save()
    else:
        userinfo = userinfo[0]

    return userinfo


def fetch_google_auth_data(google_id_token):
    '''function to fetch google auth token'''

    params = {'id_token': google_id_token}
    response = rqst.get("https://oauth2.googleapis.com/tokeninfo", params=params)

    response = response.text
    json_to_save = json.dumps(response)
    google_json = json.loads(response)
    x = (json_to_save, google_json)
    return x


def login_with_google(google_id_token, request, res, login_type="google"):
    '''function to login with google'''

    mobile_no = res['mobile_no'] if 'mobile_no' in res else None
    country_code = res['country_code'] if 'country_code' in res else None

    if not mobile_no or not country_code:
        context = get_error_context(False, "Invalid mobile number or country code")

        return context

    google_json = fetch_google_auth_data(google_id_token)
    json_to_save = google_json[0]
    res = google_json[1]
    info_logger.info(res)
    created = False
    context = get_error_context(False, "please give permission to use your google account")
    image_link = None

    if 'email' in res:
        email = res['email']
        email = email.lower().strip()

        user_exists = ModelUtilities.get_model_filter(userMobiles, {'mobile_no': mobile_no})

        if not user_exists:

            user_instance = create_user(user_name=res['name'], email=res['email'], id=mobile_no)

            if res.get('picture'):
                image_link = upload_image_to_firebase(res['picture'], user_instance.id)
            else:
                image_link = ""

            userinfo = create_userinfo(user=user_instance, email=res['email'], user_name=res['name'],
                                       profile_picture=image_link, login_type=login_type,
                                       json_to_save=json_to_save
                                       )
            save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY)

            save_user_primary_email(user_instance, res['email'], verified=True)

        else:
            user_instance = user_exists[0].user

        usr = get_logged_in_user(user_instance=user_instance)

        if is_request_web(request):
            login(request, user=user_instance, backend="django.contrib.auth.backends.ModelBackend")

        access = is_user_community_part(usr['id'])
        email_exists = ModelUtilities.is_model_filter_exists(userEmails,
                                                             {'email': user_instance.userinfo.email, 'verified': True})
        context = {'user': usr, 'access': access, 'email_exists': email_exists}

    return context


def login_with_facebook(request, res, json_to_save, login_type="facebook"):
    '''function to login with facebook'''

    mobile_no = res['mobile_no'] if 'mobile_no' in res else None
    country_code = res['country_code'] if 'country_code' in res else None

    if not mobile_no or not country_code:
        context = get_error_context(False, "Invalid mobile number or country code")

        return context

    res = res['login_json']
    image_link = None
    email = None

    if 'email' in res:
        email = res['email']
        # converting email to lower case and removing unwanted space
        email = email.lower().strip()

    user_exists = ModelUtilities.get_model_filter(userMobiles, {'mobile_no': mobile_no})

    if not user_exists:

        user_instance = create_user(user_name=res['name'], email=email, id=mobile_no)

        if res.get('picture'):
            image_link = upload_image_to_firebase(res['picture']['data']['url'], user_instance.id)

        else:
            image_link = ""

        city = res['location']['name'] if 'location' in res else None

        userinfo = create_userinfo(user=user_instance, email=email, user_name=res['name'],
                                   profile_picture=image_link, login_type=login_type,
                                   json_to_save=json_to_save, city=city,
                                   )

        save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY)
        save_user_primary_email(user_instance, email, verified=True)

    else:
        user_instance = user_exists[0].user

    usr = get_logged_in_user(user_instance=user_instance)

    # login in when the request is web
    if is_request_web(request):
        login(request, user=user_instance, backend="django.contrib.auth.backends.ModelBackend")

    access = is_user_community_part(usr['id'])
    email_exists = ModelUtilities.is_model_filter_exists(userEmails,
                                                         {'email': user_instance.userinfo.email, 'verified': True})
    context = {'user': usr, 'access': access, 'email_exists': email_exists}

    return context


def login_with_linkedin(request, res, json_to_save, login_type="linkedIn"):
    '''login with linkedIn '''

    mobile_no = res['mobile_no'] if 'mobile_no' in res else None
    country_code = res['country_code'] if 'country_code' in res else None

    if not mobile_no or not country_code:
        context = get_error_context(False, "Invalid mobile number or country code")

        return context

    res = res['login_json']
    email = None

    if 'email' in res:
        email = res['email']['elements'][0]['handle~']['emailAddress']

    profile_picture = None

    user_exists = ModelUtilities.get_model_filter(userMobiles, {'mobile_no': mobile_no})

    if not user_exists:

        user_name = res['firstName']['localized']['en_US'] + " " + res['lastName']['localized']['en_US']
        user_instance = create_user(user_name=user_name, email=email, id=mobile_no)

        if res.get('profilePicture'):

            profile_picture = upload_image_to_firebase(
                res['profilePicture']['displayImage~']['elements'][2]['identifiers'][0]['identifier'], user_instance.id)
        else:
            profile_picture = ""

        userinfo = create_userinfo(user=user_instance, email=email, user_name=user_name,
                                   profile_picture=profile_picture, login_type=login_type,
                                   json_to_save=json_to_save)

        save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY)
        save_user_primary_email(user_instance, email, verified=True)

    else:
        user_instance = user_exists[0].user

    usr = get_logged_in_user(user_instance=user_instance)
    access = is_user_community_part(usr['id'])
    email_exists = ModelUtilities.is_model_filter_exists(userEmails,
                                                         {'email': user_instance.userinfo.email, 'verified': True})
    context = {'user': usr, 'access': access, 'email_exists': email_exists}

    return context


def login_with_apple(request, res, json_to_save, login_type="apple"):
    '''function to login with apple'''
    # if user is logging in with Apple
    mobile_no = res['mobile_no'] if 'mobile_no' in res else None
    country_code = res['country_code'] if 'country_code' in res else None

    res = res['login_json']
    userinfo = Userinfo.objects.filter(apple_id=res['id'])
    image_link = None

    if not userinfo.exists():
        # creating a user if no user is associated with that email
        user = create_user(user_name=res['name'], email=res['email'],
                           id=res['id'], apple_id=True)
        user_instance = user
        # fb_link = res['link'] if 'link' in res else None
        if res.get('picture'):
            image_link = upload_image_to_firebase(res['picture']['data']['url'], user.id)

        else:
            image_link = ""

        city = res['location']['name'] if 'location' in res else None
        # if there is no user then user will not have userinfo too
        # create or get user info
        userinfo = create_userinfo(user=user, email=res['email'], user_name=res['name'],
                                   profile_picture=image_link, login_type=login_type,
                                   json_to_save=json_to_save, city=city, apple_id=res['id']
                                   )

        save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY)

        save_user_primary_email(user, res['email'], verified=True)
        email_exists = False

    else:
        userinfo = userinfo[0]

        email_exists = True

    # get serialized user object

    # usr = UserinfoSerializer(userinfo)
    usr = get_logged_in_user(user_instance=userinfo.user_id)

    access = is_user_community_part(usr['id'])
    context = {'user': usr, 'access': access, 'email_exists': email_exists}
    return context


def decode_landing_type_from_url(user_acquisition_url):
    url_path_dict = {}

    try:
        url_path = parse.urlparse(user_acquisition_url).path

        path_list = url_path.split("/")

        if path_list[1] == "community":
            url_path_dict['landing_type'] = "community_join"
            url_path_dict['community_id'] = path_list[2]

        elif path_list[1] == "collabcard":
            url_path_dict['landing_type'] = "chatroom_join"
            url_path_dict['chatroom_id'] = path_list[2]

    except Exception as e:
        error_logger.error(e)

    return url_path_dict


def decode_user_acquisition_url(request, user_instance, user_acquisition_url):
    user_acquired = {}
    url_path_dict = decode_landing_type_from_url(user_acquisition_url)

    try:
        query_def = parse.parse_qs(parse.urlparse(user_acquisition_url).query)

        if query_def.get('aj'):
            user_acquired['link_type'] = "private"
        else:
            user_acquired['link_type'] = "public"

        user_acquired['user_id'] = user_instance.id

        user_acquired.update(url_path_dict)

        if query_def.get('utm_source'):
            user_acquired['utm_source'] = query_def['utm_source'][0]

        if query_def.get('utm_medium'):
            user_acquired['utm_medium'] = query_def['utm_medium'][0]

        if query_def.get('utm_campaign'):
            user_acquired['utm_campaign'] = query_def['utm_campaign'][0]

        if query_def.get('shared_by'):
            user_acquired['shared_by'] = query_def['shared_by'][0]

        if query_def.get('source'):

            if query_def['source'][0] == "members_directory":
                user_acquired['landing_type'] = "directory_link"

        platform_code = RequestUtilities.get_platform_code(request)

        if platform_code:
            user_acquired['platform'] = platform_code

        device_id = RequestUtilities.get_device_id_from_headers(request)

        if device_id:
            user_acquired['device_id'] = device_id

    except Exception as e:
        error_logger.error(e)

    return user_acquired


def save_userAcquition_analytics(user_instance, user_acquired):
    '''saving the analytics of acquired user'''

    user_filter = userAcquition.objects.filter(user=user_instance)

    if not user_filter.exists():

        instance = userAcquition()
        instance.user = user_instance
        instance.landing_type = user_acquired['landing_type'] if 'landing_type' in user_acquired else ''
        instance.link_type = user_acquired['link_type'] if 'link_type' in user_acquired else ''

        instance.utm_source = user_acquired['utm_source'] if 'utm_source' in user_acquired else ''
        instance.utm_campaign = user_acquired['utm_campaign'] if 'utm_campaign' in user_acquired else ''
        instance.utm_medium = user_acquired['utm_medium'] if 'utm_medium' in user_acquired else ''
        instance.platform = user_acquired['platform'] if 'platform' in user_acquired else ''

        instance.device_id = user_acquired['device_id'] if 'device_id' in user_acquired else ''

        if 'community_id' in user_acquired and user_acquired['community_id']:
            community_instance = Community.get_community_or_None(user_acquired['community_id'])

            if not community_instance:
                log = "incorrect community id : %s" % (user_acquired['community_id'])
                error_logger.error(log)

                return

            instance.community = community_instance

        if 'shared_by' in user_acquired and user_acquired['shared_by']:
            shared_user_instance = User.objects.get(id=user_acquired['shared_by'])
            instance.shared = shared_user_instance

        if user_acquired.get('chatroom_id'):

            card_instance = Collabcard.get_chatroom_or_None(user_acquired['chatroom_id'])

            if not card_instance:
                log = "incorrect chatroom id : %s" % (user_acquired['chatroom_id'])
                error_logger.error(log)

                return
            instance.chatroom = card_instance

        instance.save()


def custom_login(request, res, login_type="custom"):
    context = {}
    mobile_no = res['mobile_no']
    country_code = res['country_code']
    # mobile_no = int(str(country_code) + str(mobile_no))

    user_instance = None

    profile = res['user']

    name = profile['name'].capitalize()
    email = profile['email'] if 'email' in profile else ''
    email_exists = get_user_from_email(email)

    if email_exists:
        context['user'] = get_logged_in_user(user_instance=email_exists)
        context['access'] = is_user_community_part(context['user']['id'])
        context['email_exists'] = True

        return context

    if profile.get('image_url'):
        image_url = profile['image_url']

    elif res.get('image_url'):
        image_url = res['image_url']

    else:
        image_url = ""

    user_instance = create_custom_user(name, mobile_no, country_code, email, image_url, login_type)

    if res.get('user_acquisition_url'):
        user_acquired = decode_user_acquisition_url(request, user_instance, res['user_acquisition_url'])
        save_userAcquition_analytics(user_instance, user_acquired)

    if is_request_web(request):
        phone_no = str(country_code) + str(mobile_no)
        if 'verified_mobile_no' in request.session:
            if phone_no == request.session['verified_mobile_no']:
                login(request, user=user_instance, backend="django.contrib.auth.backends.ModelBackend")
    # usr = UserinfoSerializer(user_instance.userinfo)
    usr = get_logged_in_user(user_instance)
    # see if user has tags or not
    has_tags = user_instance.userinfo.has_tags

    # # saving the OS type of user (Android,iOS,WEB)
    # request_type = get_request_type(request)
    # if request_type:
    #     Userinfo.objects.filter(user_id=user_instance.id).update(mobile_os=request_type)

    context['user'] = usr
    context['has_tags'] = has_tags
    context['access'] = is_user_community_part(usr['id'])
    context['email_exists'] = True if email_exists else False

    return context


def create_custom_user(name, mobile_no, country_code, email, image_url, login_type):
    has_mobile_no = userMobiles.objects.filter(mobile_no=mobile_no)
    user_name = name + "_" + str(mobile_no)

    if not has_mobile_no.exists():
        # creating user instance

        has_user = User.objects.filter(username=user_name)
        if not has_user.exists():
            user_instance = User()
            user_instance.username = user_name.title()
            user_instance.save()

            # creating userinfo instance

            userinfo_instance = Userinfo()
            userinfo_instance.name = name.title()
            userinfo_instance.email = email
            userinfo_instance.image_link = image_url
            userinfo_instance.login_type = login_type
            userinfo_instance.login_json = None
            userinfo_instance.created_at = time.time()
            userinfo_instance.user_id = user_instance
            userinfo_instance.save()

            # creating user email
            save_user_primary_email(user_instance, email, email_state=email_states.PRIMARY)
            save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY)

            # send verification mail for email
            if email:
                verification_details = generate_tokens_for_email(user_instance, email,
                                                                 email_state=email_states.NON_PRIMARY)

                # sending a email from template
                send_verification_mail_for_email_sync.delay(user_name=name,
                                                            verification_link=verification_details['verify_url'],
                                                            email=email)

            return user_instance
        else:
            return has_user[0]

    return has_mobile_no[0].user


@csrf_exempt
def merge_account(request):
    '''api to merge account '''

    member_id = request.POST.get('user_id')

    context = {}
    if not member_id:
        context = get_error_context(False, "send user_id in post params")
        return JsonResponse(context)

    mobile_no = request.POST.get('mobile_no')
    country_code = request.POST.get('country_code')

    try:
        user_instance = User.objects.get(id=member_id)
        save_user_mobile_number(user_instance, country_code, mobile_no)

        context['success'] = True

        context['access'] = is_user_community_part(user_instance.id)

    except Exception as e:
        context['error_message'] = e.args

    return JsonResponse(context)


def generate_otp(request):
    mobile_no = request.GET.get('mobile_no')
    country_code = request.GET.get('country_code')
    user_id = request.GET.get('user_id')
    international: bool = False

    # check got retry
    retry = request.GET.get('retry')

    if retry == '1':
        retry = True

    else:
        retry = False

    info_logger.info(f'Country Code: {country_code}, Mobile Number: {mobile_no}, User ID: {user_id}')

    phone_no = str(country_code) + str(mobile_no)
    context = {}

    if mobile_no:
        try:
            mobile_no = int(mobile_no)

        except:
            context = get_error_context(False, "special characters error")
            info_logger.info(context)
            return JsonResponse(context)

        if country_code != '91':
            international = True

        if international and international_otp_limit_exceeded():
            save_request_info(str(country_code), str(mobile_no), TimeUtilities.get_current_date())

            error_message: str = f"otp generate failed for={phone_no}, reason=international otp generate limit exceeded"
            error_logger.error(error_message)
            context: dict = get_error_context(False, error_message)

            return JsonResponse(status=403, data=context)

        if retry:
            otp_manager = OTPApiClient()
            context = otp_manager.send_retry_otp_via_msg_91(phone_no)

        else:
            otp_manager = OTPApiClient()
            context = otp_manager.send_otp_via_gupshup(phone_no, international)

        backup_filter = ModelUtilities.get_model_filter(mobileBackup, {'mobile_no': mobile_no})

        if not backup_filter:
            backup_info = {'mobile_no': mobile_no, 'country_code': country_code}
            mobileBackup.create_instance(backup_info)

    # user wants to merge the account
    if user_id:
        send_otp_on_user_mobiles(user_id, retry)
        send_otp_on_user_emails(user_id)

        context['success'] = True

    update_international_otp_generate_count(international, context)

    return JsonResponse(context)


def save_request_info(country_code: str, mobile_no: str, timestamp: str) -> None:
    international_otp_req_obj: list = [country_code, mobile_no, timestamp]

    file_name: str = INTERNATIONAL_OTP_LIMIT_FILE_NAME % TimeUtilities.get_current_date(date_format=0)
    file_path: str = f'./../../international_otp_blocked_requests/{file_name}'

    """
        If, file does not exists
        Create file and write header
    """
    if not FileUtilities.is_exists_file(file_path):
        header: list = ['country code', 'mobile number', 'timestamp']
        FileUtilities.write_file_csv(file_path, 'w', header)

    """
        write data row
    """
    FileUtilities.write_file_csv(file_path, 'a', international_otp_req_obj)


def international_otp_limit_exceeded() -> bool:
    HOURLY_INTERNATIONAL_OTP_GENERATE_LIMIT: int = 10
    key: str = INTERNATIONAL_OTP_GENERATE_CACHE_KEY % TimeUtilities.get_current_date(date_format=1)
    current_count: int = CacheImpl.get_cache(key)
    if isinstance(current_count, int) and current_count >= HOURLY_INTERNATIONAL_OTP_GENERATE_LIMIT:
        return True

    return False


def update_international_otp_generate_count(international: bool, context: dict) -> None:
    if not (international and context['success']):
        return

    key: str = (INTERNATIONAL_OTP_GENERATE_CACHE_KEY % TimeUtilities.get_current_date(date_format=1))
    value: int = 1

    current_count: int = CacheImpl.get_cache(key)
    if isinstance(current_count, int):
        value = current_count + 1

    CacheImpl.set_cache(key, value)


def send_otp_on_user_emails(user_id):
    email_filter = ModelUtilities.get_model_filter(userEmails, {'user_id': user_id})

    for instance in email_filter:
        email = instance.email
        context = send_otp_on_email(email)
        info_logger.info(f'OTP Context: {context}, User ID: {instance.user.id}, E-Mail: {email}')


def send_otp_on_user_mobiles(user_id, retry):
    mobile_filter = ModelUtilities.get_model_filter(userMobiles, {'user_id': user_id})

    for instance in mobile_filter:
        phone_no = str(instance.country_code) + str(instance.mobile_no)

        international = False
        if str(instance.country_code) != '91':
            international = True

        if retry:
            otp_manager = OTPApiClient()
            context = otp_manager.send_retry_otp_via_msg_91(phone_no)

        else:
            otp_manager = OTPApiClient()
            context = otp_manager.send_otp_via_gupshup(phone_no, international)

        info_logger.info(f'User ID: {instance.user.id}')
        info_logger.info(f'OTP Context: {context}')


def verify_otp(request):
    mobile_no = request.GET.get('mobile_no')
    country_code = request.GET.get('country_code')
    user_id = request.GET.get('user_id')
    otp = request.GET.get('otp')
    info_logger.info(f'Country Code: {country_code}, Mobile Number: {mobile_no}, User ID: {user_id}, OTP: {otp}')

    lm_mobile_no_list = ["9458668721", "9467796637"]

    if mobile_no in lm_mobile_no_list:

        if otp == "0000":
            context = {}
            context['success'] = True
            mobile_filter = userMobiles.objects.filter(mobile_no=mobile_no)
            context['profile_exists'] = mobile_filter.exists()

            if mobile_filter.exists():
                context['user'] = get_logged_in_user(user_instance=mobile_filter[0].user)
                context['access'] = is_user_community_part(context['user']['id'])

            return JsonResponse(context)

        else:
            return JsonResponse({'success': False, 'error_message': "Wrong otp"})

    if settings.IS_BETA:

        if otp == "9999":
            context = {}
            context['success'] = True
            mobile_filter = userMobiles.objects.filter(mobile_no=mobile_no)
            context['profile_exists'] = mobile_filter.exists()

            if mobile_filter.exists():
                context['user'] = get_logged_in_user(user_instance=mobile_filter[0].user)
                context['access'] = is_user_community_part(context['user']['id'])

                return JsonResponse(context)

            else:
                return JsonResponse({'success': False, 'error_message': "Wrong otp"})

    # for existing users flow
    member_id = get_member_id_from_headers(request)

    profile_exists = False
    phone_no = str(country_code) + str(mobile_no)
    context = {}

    if mobile_no:

        try:
            mobile_no = int(mobile_no)
        except:
            context = get_error_context(False, "special characters error")
            info_logger.info(context)

            return JsonResponse(context)

        international = False

        if country_code != '91':
            international = True

        otp_manager = OTPApiClient()
        verified = otp_manager.verify_otp_via_gupshup(phone_no, otp, international)
        verified_msg = otp_manager.verify_retry_otp_via_msg_91(phone_no, otp)
        context['success'] = False

        if verified['success'] or verified_msg['success']:
            context['success'] = True

        # saving data for existing user migrations
        if member_id and context['success']:
            user_instance = User.objects.get(id=member_id)
            mobile_filter = userMobiles.objects.filter(user=user_instance, state=mobile_states.PRIMARY)

            if mobile_filter.exists():
                save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.NON_PRIMARY)
            else:
                save_user_mobile_number(user_instance, country_code, mobile_no)

        if not context['success']:
            context['error_message'] = "Incorrect OTP"

        mobile_filter = userMobiles.objects.filter(mobile_no=mobile_no)
        context['profile_exists'] = mobile_filter.exists()

        if mobile_filter.exists():
            context['user'] = get_logged_in_user(user_instance=mobile_filter[0].user)
            context['access'] = is_user_community_part(context['user']['id'])

            if context['success'] == True:
                login(request, user=mobile_filter[0].user, backend="django.contrib.auth.backends.ModelBackend")

        return JsonResponse(context)

    # when the user wants to merge account
    if user_id:
        mobile_filter = userMobiles.objects.filter(user_id=user_id)
        context = {'success': False}

        for instance in mobile_filter:
            phone_no = str(instance.country_code) + str(instance.mobile_no)
            international = False

            if str(instance.country_code) != '91':
                international = True

            otp_manager = OTPApiClient()
            context = otp_manager.verify_otp_via_gupshup(phone_no, otp, international)
            context_msg = otp_manager.verify_retry_otp_via_msg_91(phone_no, otp)

            if context['success'] or context_msg['success']:
                login(request, user=mobile_filter[0].user, backend="django.contrib.auth.backends.ModelBackend")
                break

        context['profile_exists'] = mobile_filter.exists()

        if mobile_filter.exists():
            context['user'] = get_logged_in_user(user_instance=mobile_filter[0].user)
            context['access'] = is_user_community_part(context['user']['id'])

        if not context['success']:
            # verifying otp from email
            email_filter = userEmails.objects.filter(user_id=user_id)

            for instance in email_filter:
                email = instance.email
                context = verify_otp_on_email(email, otp)

                if context['success']:
                    break

            if email_filter.exists():
                context['user'] = get_logged_in_user(user_instance=email_filter[0].user)
                context['access'] = is_user_community_part(context['user']['id'])

        return JsonResponse(context)

    return JsonResponse(context)


def send_otp_on_email(email):
    email_key = settings.EMAIL_GHUPSHAP_KEY
    context = {}
    success = False

    generate_url = """http://enterprise.smsgupshup.com/apps/TwoFactorAuth/incoming.php?email=%s&key=%s""" % (
        email, email_key)
    response = rqst.get(generate_url)
    print(response.content)

    if response.status_code == 200:
        success = True
        response = response.text
        response_list = response.split("|")
        if response_list[0].strip() == "error":
            success = False

    context['success'] = success
    if not success:
        context['error_message'] = response

    return context


def verify_otp_on_email(email, otp):
    email_key = settings.EMAIL_GHUPSHAP_KEY
    verify_url = """http://enterprise.smsgupshup.com/apps/TwoFactorAuth/incoming.php?email=%s&key=%s&code=%s""" % (
        str(email), email_key, str(otp))

    response = rqst.get(verify_url)
    print(response.content)
    context = {}
    success = False

    if response.status_code == 200:
        success = True
        response = response.text
        response_list = response.split("|")
        if response_list[0].strip() == "error":
            success = False

    context['success'] = success
    if not success:
        context['error_message'] = "Incorrect OTP"

    return context


def save_user_primary_email(user_instance, email, verified=False, email_state=email_states.PRIMARY):
    '''function to save primary email of user for communications'''

    if not email:
        return

    email_filter = userEmails.objects.filter(email=email, verified=True)

    # if email_filter.exists():
    #     user_email_instance = email_filter[0]
    #     if not user_email_instance.verified:
    #         email_filter.delete()

    if not email_filter.exists():
        user_email_instance = userEmails()
        user_email_instance.user = user_instance
        user_email_instance.email_state = email_state
        user_email_instance.email = email
        user_email_instance.verified = verified
        user_email_instance.save()


def save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY):
    if not mobile_no:
        return

    mobile_filter = userMobiles.objects.filter(mobile_no=mobile_no)

    if not mobile_filter.exists():
        instance = userMobiles()
        instance.country_code = country_code
        instance.mobile_no = mobile_no
        instance.state = state
        instance.user = user_instance
        instance.created_at = time.time()
        instance.save()


def get_user_from_email(email):
    '''function to get user instance from email'''
    if not email:
        return None

    user = None
    user_emails = userEmails.objects.filter(email=email, verified=True)
    if user_emails.exists():
        instance = user_emails[0]
        user = instance.user
    # else:
    #     user = User.objects.filter(email=email)
    #     if user.exists():
    #         user = user[0]

    return user


def is_user_community_part(user_id):
    '''function to tell whether the user is a part of any community or nor'''

    members_filter = Members.objects.filter(member_id=user_id).filter(
        Q(state=member_states.ADMIN) |
        Q(state=member_states.MEMBER) |
        Q(state=member_states.PROFILE_UNAVAILABLE))

    return members_filter.exists()


def limit_access(request):
    '''function to limit the access of app and sending details on web screen'''

    member_id = get_member_id_from_headers(request)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    try:
        user_instance = User.objects.get(id=member_id)
    except:
        context = get_error_context(False, "send correct user id")
        return JsonResponse(context)

    context = {}

    context['header_image'] = LIMIT_ACCESS_HEADER_IMAGE
    context['image'] = LIMIT_ACCESS_IMAGE
    context['title'] = "You are on the waiting list!"
    context[
        'sub_title'] = "Your application to join this community has been submitted. You will have access to your community and other awesome features on this app as soon as you are approved."

    members_filter = Members.objects.filter(member_id=member_id).filter(state=member_states.PENDING_MEMBER)

    community_list = []
    for member in members_filter:
        community_instance = member.community_id
        community = CommunitySerializer(community_instance, current_user_id=member_id, platform_code=platform_code,
                                        version_code=version_code)

        community_creator = get_community_creator(community_instance)
        if community_creator:
            community['created_by'] = community_creator

        community_list.append(community)

    context['communities'] = community_list

    access = is_user_community_part(member_id)
    context['access'] = access

    if not community_list:
        context['title'] = "Important Message"
        context['sub_title'] = """Access to this app is restricted to invited members only. You can:
1. Click on the invitation link if you received one
2. Check login credentials if you have already registered with us
3. Stay tuned and we will let you know once we open up for public.

If you are a community builder and you wish to receive an invite, do fill out the following form:"""

    #     platform_code = get_platform_code_from_headers(request)
    #
    #     if platform_code == "an":
    #
    #         context['sub_title'] = """Access to this app is restricted to invited members only. The login credentials you used (<font color='#00897b'>%s</font>) seems to be missing from our list of invited members.
    #
    # If you are a community builder and you wish to receive an invite, do fill out the following form:"""%(user_instance.userinfo.email)
    #
    #     else:
    #
    #         context['sub_title'] = """Access to this app is restricted to invited members only. The login credentials you used (%s) seems to be missing from our list of invited members.
    #
    #         If you are a community builder and you wish to receive an invite, do fill out the following form:""" % (
    #             user_instance.userinfo.email)

    return JsonResponse(context)


def get_community_creator(community_instance):
    '''function to get the creator of community'''
    member_filter = ModelUtilities.get_model_filter(Members,
                                                    {"community_id": community_instance,
                                                     "state": member_states.ADMIN}).order_by('id')
    created_by = ""
    if member_filter.exists():
        promoter_instance = member_filter[0].member_id
        created_by = promoter_instance.userinfo.name

    return created_by


@csrf_exempt
def skip_community(request):
    '''api to skip the community'''
    member_id = get_member_id_from_headers(request)
    community_id = request.POST.get('community_id')

    # adding the members data
    member_filter = Members.objects.filter(member_id=member_id, community_id=community_id)
    user_instance = User.objects.get(id=member_id)
    community_instance = Community.objects.get(id=community_id)

    if not member_filter.exists():
        member_instance = Members()
        member_instance.member_id = user_instance
        member_instance.community_id = community_instance
        member_instance.state = member_states.PROFILE_UNAVAILABLE
        member_instance.created_at = time.time()
        member_instance.updated_at = time.time()
        member_instance.became_member_at = time.time()
        member_instance.save()

    ModelUtilities.update_or_create_model(Member_Engage, {
        'member_id': user_instance,
        'community_id': community_instance
    }, {
        'member_state': member_states.PROFILE_UNAVAILABLE,
        'click_state': click_states.SKIP_COMMUNITY,
        'order_time': TimeUtilities.current_time_in_milliseconds()
    })

    set_state_for_onboarding_chatroom(community_instance, user_instance.id, request)
    update_community_toast(user_instance, community_instance, message="Please complete your profile for full access")
    # removing its data from removed members in order to consider it a new user
    removedMembers.objects.filter(community=community_instance, member=user_instance).delete()

    # sleeping for 2 hours to remind user to complete profile via notification
    try:
        # community_instance = Community.objects.get(id=community_id)
        community_state = get_state_of_community(community_instance)
        send_notification_to_incomplete_profile.delay(member_id, community_id, community_state, community_instance.name,
                                                      time_in_hrs=2)
    except:
        print("some error occured")

    # updating the member joined level
    set_levels_on_ctc(community_instance, "Level 2")

    send_sync_notification.delay({'community_id': community_id,
                                  'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value,
                                  })
    return JsonResponse({'success': True})


def get_state_of_community(community):
    if community.hide_community:
        return int(community.hide_community)
    return 0


def compute_moderation_member_rights_list_for_ios(moderated_member_list, version_code):
    member_rights_list = []

    for data in moderated_member_list:

        if data.get('state') == member_rights.MEMBER_RIGHT_CREATE_SECRET_ROOM \
                and version_code <= SECRET_CHATROOM_VERSION_CODE_IOS:
            continue

        member_rights_list.append(data)

    return member_rights_list


def members_state(request, req_dict=None):
    '''This function gives the state of user.Get Api'''

    api_key = RequestUtilities.get_api_key_from_headers(request)

    if not req_dict:
        member_id = request.GET.get('member_id')
        community_id = request.GET.get('community_id')
        community_id = community_id if community_id else api_key
        collabcard_id = request.GET.get('collabcard_id')

        if collabcard_id and not community_id:
            card = Collabcard.get_chatroom_or_None(collabcard_id)

            if card is None:
                response = get_error_context(False, f"chatroom with id {collabcard_id} doesn't exists")
                return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

            community_id = card.community.id

        if not community_id:
            context = get_error_context(False, "Invalid API key/community ID")
            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    else:
        member_id = req_dict['member_id']

    state = 0
    tool_state = 0
    custom_title = "Member"

    version_code = RequestUtilities.get_version_code_from_headers(request)

    community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)
    user_instance = ModelUtilities.get_user_instance_or_none(member_id)

    member_id = user_instance.id if user_instance else member_id

    if not community_instance:
        response = get_error_context(False, "Invalid API key/community ID")
        return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

    community_id = community_instance.id

    query_set = ModelUtilities.get_model_filter(Members,
                                                {"member_id": member_id,
                                                 "community_id": community_instance})

    community_state = get_state_of_community(community_instance)

    is_tool_state = True

    user_email = ""
    ref_members = []
    is_owner = False
    edit_required = False
    actions_required = False
    created_at = 0
    image_url = ""

    if query_set:
        data = query_set[0]
        is_member = False
        tool_state = 0
        state = data.state
        is_owner = data.is_owner
        custom_title = data.custom_title

        if data.created_at > 0:
            created_at = time.strftime('%A, %b %d', time.localtime(data.created_at))

        if state in [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]:
            is_member = True

        if state == member_states.PENDING_MEMBER:
            user_email = data.member_id.userinfo.email

        if is_member and is_tool_state:
            tool_state = 1

        if data.edit_required:
            edit_required = data.edit_required

        if data.actions_required:
            actions_required = True

        if data.image_url:
            image_url = data.image_url

        if not is_member:
            pass

    json_response = {
        'success': True,
        'state': state,
        'tool_state': 1,
        'edit_required': edit_required,
        'created_at': created_at
    }

    if state == member_states.PENDING_MEMBER:
        json_response['member_direction_lock'] = get_data_for_filter_pop_ups(email=user_email)

    if state == member_states.ADMIN and (community_state in [community_states.PRIVATE, community_states.WHATSAPP,
                                                             community_states.HIDDEN]):
        if actions_required:
            promoter_name = query_set[0].member_id.userinfo.name
            json_response['community_levels'] = get_create_community_actions(community_id, promoter_name)

    json_response['member'] = get_user_profile(member_id, community_id)
    json_response['member']['state'] = state
    json_response['member']['is_owner'] = is_owner

    if custom_title:
        json_response['member']['custom_title'] = custom_title

    if state == member_states.ADMIN:
        admin_rights = check_all_manager_rights(query_set[0].member_id, community_instance)
        json_response['manager_rights'] = get_saved_manager_rights_list(admin_rights)

    if state in [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]:
        user_rights = check_all_member_rights(query_set[0].member_id, community_instance)
        moderated_member_rights = get_saved_member_rights_list(user_rights)

    else:
        user_rights = check_all_member_rights()
        moderated_member_rights = get_saved_member_rights_list(user_rights)

    if RequestUtilities.is_request_ios(request):
        json_response['member_rights'] = compute_moderation_member_rights_list_for_ios(moderated_member_rights,
                                                                                       version_code)

    else:
        json_response['member_rights'] = moderated_member_rights

    if image_url:
        json_response['member']['image_url'] = image_url

    toast_filter = communityToast.objects.filter(community=community_instance, user=member_id)

    if toast_filter:
        json_response['community_toast'] = toast_filter[0].toast_message

    if req_dict:
        return json_response
    return JsonResponse(json_response)


def get_create_community_actions(community_id, promoter_name):
    level_filter = communityLevels.objects.filter(community=community_id).order_by('id')

    actions = {}
    levels = []

    actions['header'] = """Welcome to your community, %s""" % (promoter_name)
    actions['header_image'] = HEADER_IMAGE
    actions['sub_header'] = "Now, step-by-step, complete each level to unlock the full potential of your community."

    for level in level_filter:
        temp = communityLevelsSerializer(level)
        levels.append(temp)

    actions['levels'] = levels

    return actions


def save_push_notification_details_for_web(user_id, token):
    user_instance = ModelUtilities.get_user_instance_or_none(user_id)

    if not user_instance:
        return {'success': False, 'error_message': "Invalid user id"}

    if not token:
        return {'success': False, 'error_message': "Invalid fcm token"}

    device_id = "web_device_%s" % (str(user_instance.id))

    device_filter = ModelUtilities.get_model_filter(userDevices, {'user': user_instance,
                                                                  'device_id': device_id})
    if not device_filter:
        userDevices.create_instance({'user_instance': user_instance,
                                     'platform_code': "web",
                                     'token': token,
                                     'device_id': device_id})
    else:
        ModelUtilities.model_update(userDevices,
                                    {'user': user_instance, 'device_id': device_id},
                                    {'updated_at': TimeUtilities.current_time_in_sec(), 'fcm_token': token})

    return {'success': True}


@csrf_exempt
def push(request):
    """This function is used to insert fcm token to the database in order to generate notifications from database"""

    member_id = request.GET.get('member_id', '')
    token = request.GET.get('token', '')
    platform_code = get_platform_code_from_headers(request)

    device_id = request.GET.get('device_id', None)

    if RequestUtilities.is_request_web(request):
        user_id = RequestUtilities.get_member_id_from_headers(request)
        response = save_push_notification_details_for_web(user_id, token)

        if response.get('error_message'):
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response)

    if member_id:
        is_member = Userinfo.objects.filter(user_id=member_id)
    else:
        is_member = None
        # send notification if the login drops
        send_login_dropoff_notification.delay(token, platform_code)

    info_logger.info("Push Notification hit without member id")

    success = False
    if is_member:
        if platform_code == VersionUtilities.PlatformCode.ANDROID:
            platform_code = 'Android'
        elif platform_code == VersionUtilities.PlatformCode.IOS:
            platform_code = 'iOS'
        elif platform_code == VersionUtilities.PlatformCode.FLUTTER:
            platform_code = 'Flutter'
        elif platform_code == VersionUtilities.PlatformCode.REACT_NATIVE:
            platform_code = 'React Native'
        else:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context("Invalid platform code",
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        success = True
        user_instance = User.objects.get(id=member_id)

        info_logger.info("push api hit")

        if device_id:

            # saving the device id for existing user
            device_filter = userDevices.objects.filter(user=user_instance)
            for data in device_filter:

                if not data.device_id:
                    data.device_id = device_id
                    data.fcm_tokem = token
                    data.updated_at = time.time()
                    data.save()

            device_filter = userDevices.objects.filter(device_id=device_id)

            if not device_filter.exists():
                instance = userDevices()
                instance.user = user_instance
                instance.mobile_os = platform_code
                instance.updated_at = time.time()
                instance.fcm_token = token
                instance.device_id = device_id
                instance.save()

            else:
                instance = device_filter[0]
                instance.user = user_instance
                instance.mobile_os = platform_code
                instance.updated_at = time.time()
                instance.fcm_token = token
                instance.device_id = device_id
                instance.save()

        else:
            device_filter = userDevices.objects.filter(user=user_instance, mobile_os=platform_code)

            if not device_filter.exists():
                instance = userDevices()
                instance.user = user_instance
                instance.mobile_os = platform_code
                instance.updated_at = time.time()
                instance.fcm_token = token
                instance.device_id = device_id
                instance.save()
            else:
                instance = device_filter[0]
                instance.fcm_token = token
                instance.updated_at = time.time()
                instance.save()

        # fcm_token = Userinfo.objects.filter(user_id=member_id).update(mobile_os=platform_code)
    return JsonResponse({'success': success})


def create_community_names_and_promoter_status_for_user_metrics(member_filter):
    is_any_community_promoter = False
    community_id_list = []
    community_names = ""

    for data in member_filter:
        community_id_list.append(data.community_id_id)

        if not is_any_community_promoter \
                and data.state == member_states.ADMIN:
            is_any_community_promoter = True

    if community_id_list:
        community_filter = Community.objects.filter(id__in=community_id_list).only('name')

        for data in community_filter:
            community_names = community_names + str(data.name) + ","

    return community_names, is_any_community_promoter


def create_mixpanel_statistics(user_instance, userinfo_instance):
    if not user_instance:
        return

    context = {}
    context['user'] = get_logged_in_user(userinfo_instance)

    user_metrics = {}
    user_metrics['first_login'] = TimeUtilities.convert_epoch_time_to_ddmmyyyy(userinfo_instance.created_at)
    user_metrics['first_login_epoch'] = userinfo_instance.created_at
    member_filter = Members.objects.filter(member_id=user_instance, state__in=COMMUNITY_MEMBER_STATES)

    user_metrics['count_communities_joined'] = len(member_filter)

    community_names, is_any_community_promoter = create_community_names_and_promoter_status_for_user_metrics(
        member_filter)

    if community_names:
        user_metrics['name_communities_joined'] = community_names

    user_metrics['is_any_community_promoter'] = is_any_community_promoter

    user_metrics['unique_chatroom_responded'] = len(card_answers.objects.filter(user=user_instance
                                                                                ).values('card').distinct())

    user_metrics['count_chatroom_created'] = Collabcard.objects.filter(user=user_instance,
                                                                       is_pending=False, is_deleted=False).count()

    followed_count = collabcardState.objects.filter(user=user_instance,
                                                    follow_status=True).filter(
        ~Q(card__user=user_instance)).count()

    user_metrics['count_chatroom_followed'] = followed_count

    context['user_metrics'] = user_metrics

    if settings.IS_BETA:
        context['token'] = "eb1e03c8be370040278bff61a4857608"
    else:
        context['token'] = "7907eb37f46b1ac2908d3881e633a85e"

    return context


def config(request):
    """function to update the version number of android for a user profile"""

    member_id = get_member_id_from_headers(request)

    context = {}

    user_instance = User.get_user_or_none(member_id)

    if not user_instance:
        context = get_error_context(False, "send member id in headers")

        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    # update version code

    version_code = get_version_code_from_headers(request)
    userinfo_instance = user_instance.userinfo

    version_code = NumberUtilities.get_integer_from_string(version_code)

    if userinfo_instance.version_code != version_code:
        userinfo_instance.version_code = version_code
        userinfo_instance.save()

    update_last_active_timestamp_for_user(userinfo_instance)

    context['success'] = True
    context['mobile_no_exists'] = ModelUtilities.is_model_filter_exists(userMobiles, {'user': user_instance})

    access = is_user_community_part(user_instance.id)
    context['access'] = access

    context['survey_seen'] = False

    # set installed flags in case of mobile devices
    if RequestUtilities.is_request_android(request) or RequestUtilities.is_request_ios(request):
        set_installed_flag(user_instance)

    # mixpanel changes
    try:
        user_detail = create_mixpanel_statistics(user_instance, userinfo_instance)
        context['user_detail'] = user_detail
    except Exception as e:
        error_logger.error(e)

    if RequestUtilities.is_request_ios(request):
        context['updatePriority'] = NumberUtilities.get_integer_from_string(settings.FORCE_UPDATE.get('ios'))

    if RequestUtilities.is_request_android(request):
        context['updatePriority'] = NumberUtilities.get_integer_from_string(settings.FORCE_UPDATE.get('android'))

    context['use_segment'] = StringUtilities.get_boolean_from_string(settings.CONFIG_FLAGS.get('SEGMENT'))
    context['micro_polls_enabled'] = StringUtilities.get_boolean_from_string(
        settings.CONFIG_FLAGS.get('MICRO_POLLS'))
    context['enable_gif'] = StringUtilities.get_boolean_from_string(settings.CONFIG_FLAGS.get('GIF'))
    context['enable_audio'] = StringUtilities.get_boolean_from_string(settings.CONFIG_FLAGS.get('AUDIO'))
    context['enable_voice_notes'] = StringUtilities.get_boolean_from_string(settings.CONFIG_FLAGS.get('VOICE_NOTES'))

    in_app_review_filter = ModelUtilities.get_model_filter(InAppReview, {'user': user_instance})

    if in_app_review_filter:
        in_app_review_instance = in_app_review_filter[0]

        if not in_app_review_instance.shown:
            context['show_in_app_review'] = True

    return JsonResponse(context)


def update_last_active_timestamp_for_user(userinfo_instance):

    userinfo_instance.last_active = TimeUtilities.current_time_in_milliseconds()
    userinfo_instance.save()


def set_installed_flag(user_instance):
    """
    event when user installed the app
    """

    try:
        notification_list = [
            'mail_has_installed_app'
        ]
        create_notification_flag(user_instance, notification_list, card_id=None, community_id=None, flag=False)

        app_uninstall, created = appUninstalls.objects.get_or_create(user=user_instance)

        if not created:
            app_uninstall.uninstall_days = 0
            app_uninstall.save()

    except Exception as e:
        error_logger.error(e)


def get_mixpanel_statistics(member_id):
    '''function to give mixpanel statistics of user'''

    if not member_id:
        return

    context = {}
    try:
        user_instance = User.objects.get(id=member_id)
    except:
        error_logger.error("User does not exist")

    context['user'] = get_logged_in_user(user_instance)

    user_metrics = {}
    user_profile = user_instance.userinfo
    user_metrics['first_login'] = "Not Available" if user_profile.created_at < 0 else time.strftime('%d-%m-%Y',
                                                                                                    time.localtime(
                                                                                                        user_profile.created_at))

    member_states_list = [
        member_states.ADMIN,
        member_states.PENDING_MEMBER,
        member_states.MEMBER,
        member_states.PROFILE_UNAVAILABLE
    ]

    member_filter = Members.objects.filter(member_id=member_id, state__in=member_states_list)

    user_metrics['count_communities_joined'] = member_filter.count()

    community_names = ""

    for data in member_filter:
        community_names = community_names + str(data.community_id.name) + ","

    if community_names:
        user_metrics['name_communities_joined'] = community_names

    user_metrics['is_any_community_promoter'] = Members.objects.filter(member_id=member_id,
                                                                       state=member_states.ADMIN).exists()

    user_metrics['unique_chatroom_responded'] = card_answers.objects.filter(user=user_instance).distinct(
        'card_id').count()

    user_metrics['count_chatroom_created'] = Collabcard.objects.filter(user_id=member_id,
                                                                       is_pending=False, is_deleted=False).count()

    state_filter = collabcardState.objects.filter(user_id=member_id,
                                                  follow_status=True)
    followed_count = 0
    for chatroom in state_filter:

        if chatroom.card.user_id == int(member_id):
            continue
        followed_count = followed_count + 1

    user_metrics['count_chatroom_followed'] = followed_count

    context['user_metrics'] = user_metrics

    if settings.IS_BETA:
        context['token'] = "eb1e03c8be370040278bff61a4857608"
    else:
        context['token'] = "7907eb37f46b1ac2908d3881e633a85e"

    return context


############# functions edit community    ##########################

@csrf_exempt
def edit_community(request):
    '''function to edit the community'''

    community_id = request.GET.get('community_id')
    member_id = get_member_id_from_headers(request)
    community = Community.objects.get(id=community_id)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    if not member_id:
        return JsonResponse({'success': False, 'error_message': "Send member id in headers"})
    else:
        member_instance = User.objects.get(id=member_id)

    json_body = json.loads(request.body)

    key = json_body['key']

    if key == 'purpose':
        value = json_body['value']
        Collabcard.objects.filter(community=community, type=card_types.CARD_PURPOSE).update(title=value)
        community.purpose = value
        community.save()

    elif key == 'questions':
        questions = json_body['questions']
        edit_questions(questions, community_id)
    else:
        value = json_body['value']
        Community.objects.filter(id=community_id).update(**{key: value})

        if key == "about":
            # saving create community action step 5
            createCommunityAction.objects.filter(community=community_id,
                                                 step_no="Step 5").update(current_point=15)

    # saving the updating details for history

    instance = communityUpdate()
    instance.updated_field = key
    instance.updated_time = time.time()
    instance.updated_member = member_instance
    instance.community = community
    instance.save()

    serialized_object = CommunitySerializer(community, current_user_id=member_id, platform_code=platform_code,
                                            version_code=version_code)
    new_dict = {}
    new_dict.update(serialized_object)
    send_sync_notification.delay({'community_id': community_id,
                                  'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

    return JsonResponse({'success': True, 'community': new_dict})


def change_community_level_context_for_paid_community(community_instance):
    if not community_instance.is_paid:
        return

    level_filter = ModelUtilities.get_model_filter(communityLevels,
                                                   {'level': "Level 4",
                                                    'community': community_instance})

    if level_filter:
        level_instance = level_filter[0]

        if level_instance.state == community_level_states.LOCKED:
            level_instance.title = PAID_COMMUNITY_LEVEL_4_TITLE

        else:
            level_instance.title = PAID_COMMUNITY_LEVEL_4_SUB_TITLE

        level_instance.save()


@csrf_exempt
def edit_community_questions(request):
    """function to update community questions"""

    member_id = get_member_id_from_headers(request)
    user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    if not user_instance:
        response = get_error_context(False, 'Send member id in headers')

        return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

    res = RequestUtilities.load_request_body(request)

    if not res:
        response = get_error_context(False, 'Invalid request body')

        return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

    community_instance = ModelUtilities.get_model_instance_or_none(Community, res.get('community_id'))

    if not community_instance:
        response = get_error_context(False, 'Invalid community_id')

        return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

    if not res.get('questions'):
        response = get_error_context(False, 'send questions data in request body')

        return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

    questions_list = res['questions']

    current_questionId_set = set(communityQuestions.objects
                                 .filter(community=community_instance)
                                 .values_list('id', flat=True))
    latest_questionId_set = set()

    major_change = False

    for question in questions_list:

        if question.get('id'):

            question_id = NumberUtilities.get_integer_from_string(question.get('id'))

            question_instance = ModelUtilities.get_model_instance_or_none(communityQuestions,
                                                                          question_id)

            if not question_instance:
                question_instance = communityQuestions()
                create_or_update_question_instances(question_instance, question, community_instance)
                major_change = True
                continue

            if question_instance.question_state == question_states.CHOICE_MULTIPLE or \
                    question_instance.question_state == question_states.CHOICE_SINGLE and \
                    not question['field']:
                current_choices = json.loads(question['value'])
                value_list = []

                for i in current_choices:
                    value_list.append(i['value'])

                # taking the user options from filter
                filter_list = list(
                    questionFilters.objects.filter(question=question['id']).values_list('filter', flat=True).distinct())

                for data in filter_list:

                    if data not in value_list:
                        dropdown_list = list(questionFilters.objects
                                             .filter(question=question['id'], filter=data)
                                             .values_list('member_id', flat=True)
                                             .distinct())
                        questionFilters.objects.filter(question=question['id'], filter=data)

                        questionFilters.objects.filter(question=question['id'], filter=data).delete()

                        for user_id in dropdown_list:
                            dropdown_option = list(
                                questionFilters.objects.filter(question=question['id'], member_id=user_id).values_list(
                                    'filter', flat=True).distinct())

                            if dropdown_option:
                                value = ""

                                for option in dropdown_option:
                                    value = option + "$#"

                                value = value[:-2]
                                answer_filter = communityAnswers.objects.filter(question=question['id'],
                                                                                member_id=user_id)
                                answer_filter.update(question_answer=value)

                            else:
                                info_logger.info("delete case")
                                answer_filter = communityAnswers.objects.filter(question=question['id'],
                                                                                member_id=user_id)
                                answer_filter.delete()

                major_change = True

            latest_questionId_set.add(question_id)

            # updating the question instance
            create_or_update_question_instances(question_instance, question, community_instance)

        else:
            question_instance = communityQuestions()
            create_or_update_question_instances(question_instance, question, community_instance)

            major_change = True

    diff = current_questionId_set - latest_questionId_set

    if len(diff) > 0:
        communityQuestions.objects.filter(pk__in=diff).delete()

    # updating members state table for editing
    if major_change:
        update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                       {'community_id': community_instance},
                                       {'edit_required': True})
        send_notification_for_directory_creation.delay(community_instance.id, time.time(), day=0)

    edit_community_data(community_instance, user_instance, edit_field="directory")

    send_sync_notification.delay({'community_id': community_instance.id,
                                  'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

    if cm_onboarding_version_check(platform_code, version_code):
        # Check if it questions are edited for first time
        community_get_started_filter = ModelUtilities.get_model_filter(CommunityGetStarted,
                                                                       {'community': community_instance,
                                                                        'get_started__type': get_started_types.CUSTOMISE_JOIN_FORM,
                                                                        'completed': True})

        if not len(community_get_started_filter):
            update_community_get_started(community_instance, get_started_types.CUSTOMISE_JOIN_FORM, is_enabled=True)

            # Send Join Form Mail
            branch_link = create_community_feed_url_for_cm_onboarding(community_instance)

            mail_template = get_template('mails/cm_onboarding/customise_join_form_cm_onboarding.html').render({
                "community_name": community_instance.name,
                "cm_name": user_instance.userinfo.name,
                "community_logo": community_instance.image_link,
                "community_brand_color": community_instance.brand_color if community_instance.brand_color else
                DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR,
                "button_text": GETTING_STARTED_CM_BUTTON_TEXT,
                "button_link": branch_link
            })

            mail_subject = CUSTOMISE_JOIN_FORM_MAIL_SUBJECT.format(user_instance.userinfo.name)

            user_email = get_user_email_preferred_verified(user_instance.id)

            if user_email:
                send_email_response = MailWrapper.send_email.delay(mail_subject, mail_template,
                                                                   [user_email],
                                                                   reply_to=[INVITE_MEMBER_REPLY_EMAIL])

    return JsonResponse({'success': True}, status=status_codes.HTTP_200_OK)


def edit_questions(questions, community_id):
    '''function to edit questions of community'''

    community_object = Community.objects.get(id=community_id)
    communityQuestions.objects.filter(community=community_object).delete()
    print('Previous Questions Deleted')

    for question in questions:
        # if any new question is added -- Insert functionality
        question_object = communityQuestions()
        question_object.question_title = question['key']
        question_object.community = community_object
        question_object.save()

    print('questions updated successfully')


@csrf_exempt
def edit_questions_version_1(request):
    '''function to edit questions in a community'''

    member_id = get_member_id_from_headers(request)
    if not member_id:
        return JsonResponse({'success': False, 'error_message': "Send member id in headers"})

    user_instance = User.objects.get(pk=member_id)
    res = json.loads(request.body)

    # error messages

    if 'community_id' not in res:
        return JsonResponse({'success': False, 'error_message': "send community id in request body"})

    if 'questions' not in res:
        return JsonResponse({'success': False, 'error_message': "send questions list"})

    questions_list = res['questions']
    community_instance = Community.objects.get(id=res['community_id'])

    current_questionId_set = set(
        communityQuestions.objects.filter(community=community_instance).values_list('id', flat=True))
    latest_questionId_set = set()

    major_change = False
    for question in questions_list:

        if 'id' in question:
            question_instance = communityQuestions.objects.get(pk=question['id'])

            # checking current question for major change
            if question_instance.question_state != question['state']:
                major_change = True

            elif question_instance.value != question['value']:
                major_change = True

            elif (question_instance.optional is True and question['optional'] is False):
                major_change = True

            latest_questionId_set.add(question['id'])

            # updating the question instance
            question_instance.community = community_instance
            question_instance.question_title = question['question_title']
            question_instance.question_state = question['state']
            question_instance.value = question['value'] if 'value' in question else None
            question_instance.optional = question['optional']
            question_instance.help_text = question['help_text'] if 'help_text' in question else None
            question_instance.save()

        else:
            question_instance = communityQuestions()
            question_instance.community = community_instance
            question_instance.question_title = question['question_title']
            question_instance.question_state = question['state']
            question_instance.value = question['value'] if 'value' in question else None
            question_instance.optional = question['optional']
            question_instance.help_text = question['help_text'] if 'help_text' in question else None
            question_instance.save()

            major_change = True

    print(major_change)

    if not major_change:

        diff = current_questionId_set - latest_questionId_set
        print(diff)

        # set is not an empty set major change

        if len(diff) > 0:
            major_change = True
            # updating the removed_state to True if the question is deleted
            communityQuestions.objects.filter(pk__in=diff).update(remove_state=True)

    # updating members state table for editing
    if major_change:
        update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                       {'community_id': community_instance},
                                       {'edit_required': True})
        send_notification_for_directory_creation.delay(community_instance.id, time.time(), day=0)

    edit_community_data(community_instance, user_instance, edit_field="directory")

    send_sync_notification.delay({'community_id': community_instance.id,
                                  'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

    return JsonResponse({'success': True})


def edit_community_data(community_instance, user_instance, edit_field):
    """function to update the purpose collabcard of community"""

    chatroom_filter = ModelUtilities.get_model_filter(Collabcard,
                                                      {'community': community_instance,
                                                       'type': card_types.CARD_PURPOSE})
    if chatroom_filter:
        card_instance = chatroom_filter[0]
        user_name = user_instance.userinfo.name
        community_route = "route://community?community_id=" + str(community_instance.id)

        if edit_field == "name":
            bubble_text = "<<" + user_name + " changed the name of this community" + "|" + community_route + ">>"
            edit_announcement_bubbles(card_instance, user_instance, bubble_text)

            ElasticSearchSync.update_community_name.delay(community_instance.id, community_instance.name)

        if edit_field == "purpose":
            card_instance.title = community_instance.purpose
            card_instance.save()
            bubble_text = "<<" + user_name + """ edited "About Community". Tap to view.""" + "|" + community_route + ">>"
            edit_announcement_bubbles(card_instance, user_instance, bubble_text)
            ModelUtilities.model_update(collabcardState,
                                        {'card': card_instance},
                                        {'updated_at': TimeUtilities.current_time_in_sec()})

        if edit_field == "image_url":
            bubble_text = "<<" + user_name + """ changed the community icon. Tap to view.""" + "|" + community_route + ">>"
            edit_announcement_bubbles(card_instance, user_instance, bubble_text)

            add_community_upload_image_analytics.delay(user_instance.id, community_instance.id, community_instance.name)

        if edit_field == "directory":
            member_directory_route = """route://members_directory?community_id=%s&community_name=%s""" % (
                str(community_instance.id), quote(community_instance.name))
            bubble_text = "<<" + user_name + """ edited member directory. Tap to view.""" + "|" + member_directory_route + ">>"
            master_intro = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                        'type': card_types.CARD_MASTER_INTRO})
            if master_intro:
                card_instance = master_intro[0]
                edit_announcement_bubbles(card_instance, user_instance, bubble_text)

        # setting the updation time of edited community

        update_models_for_syncing_apis(SyncTypes.COMMUNITY,
                                       {'community_id': community_instance, 'member_id': user_instance},
                                       {})


@shared_task
def add_community_upload_image_analytics(user_id, community_id, community_name):
    community_image_segment_metadata = {
        "community_id": community_id,
        "community_name": community_name
    }

    SegmentImpl.track_event(user_id, SEGMENT_COMMUNITY_LOGO_UPLOADED_EVENT_NAME, community_image_segment_metadata)


def edit_announcement_bubbles(card_instance, user_instance, bubble_text):
    '''function to edit the announcement bubbles text'''

    instance = card_answers()
    instance.answer = bubble_text
    instance.card = card_instance
    instance.user = user_instance
    instance.community = card_instance.community
    instance.state = conversation_states.CONVERSATION_COMMUNITY_EDIT
    instance.save()


#############################  ALL MEMBERS API ###########################
@api_view(['GET', 'POST'])
@renderer_classes([JSONRenderer, TemplateHTMLRenderer])
def all_members(request):
    # print('in all members')
    '''function to send all members of community '''

    context = get_all_members(request)

    if request.accepted_renderer.format == '*/*':
        print('in html')
        return render(request, 'filtered_members.html', context)
    else:
        return JsonResponse(context)


class AllMembersVersion1(APIView):

    def get(self, request, *args, **kwargs):

        member_id = get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        context = get_all_members_version_1(request)

        if context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                                context.get('status')))

        if request.accepted_renderer.format == '*/*':
            info_logger.info("html format")
            return render(request, 'filtered_members.html', context)
        else:
            return JsonResponse(context)


def get_tagging_list(request):
    '''api to get tag list of members'''

    community_id = request.GET.get('community_id')
    chatroom_id = request.GET.get('chatroom_id')

    current_member_id = get_member_id_from_headers(request)

    if not is_request_web(request):
        tagging_list = get_tagging_list_internal(community_id, chatroom_id, current_member_id)
    else:
        # sending tagging options for web
        tagging_list = get_tagging_list_internal_web(chatroom_id, current_user_id=current_member_id)

    return JsonResponse({'members': tagging_list})


class GetTaggingList(APIView):

    def get(self, request, *args, **kwargs):

        member_id = get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        query_params = request.query_params

        community_id = query_params.get('community_id', None)
        chatroom_id = query_params.get('chatroom_id', None)

        if community_id is None and chatroom_id is None:
            response = get_error_context(False, "send community id or chatroom id in query params")
            raise CustomException(response)

        response = get_tagging_list_internal_v1(community_id,
                                                chatroom_id=chatroom_id,
                                                current_member_id=member_id)
        return JsonResponse(response)


# functionality for filters
def fetch_filters(request):
    '''api to get all the filtered data'''

    community_id = request.GET.get('community_id')

    member_id = get_member_id_from_headers(request)

    if not member_id:
        return JsonResponse({'success': False, 'error_message': "Member id is not coming in header"})

    send_empty_list = False

    member_list = Members.objects.filter(community_id=community_id, member_id=member_id)

    if member_list:

        member_state = member_list[0].state
        if member_state == member_states.PENDING_MEMBER:
            send_empty_list = True

    else:
        send_empty_list = True

    if send_empty_list:
        return JsonResponse({'questions': []})

    community_options = communityAnswers.objects.filter(community_id=community_id
                                                        ).filter(
        Q(question__question_state=question_states.CHOICE_SINGLE)
        | Q(question__question_state=question_states.CHOICE_MULTIPLE)
    ).prefetch_related('question')

    question_set = set()
    # print("options===",community_options)

    option_list = []
    for data in community_options:

        question_instance = data.question

        serialized_instance = CommunityQuestionsSerializer(question_instance)

        if serialized_instance['state'] == question_states.CHOICE_SINGLE or serialized_instance[
            'state'] == question_states.CHOICE_MULTIPLE:

            if serialized_instance['id'] not in question_set:
                serialized_instance['value'] = get_user_selected_option_list(serialized_instance['id'])
                question_set.add(serialized_instance['id'])
                option_list.append(serialized_instance)

    return JsonResponse({'questions': option_list})


def get_user_selected_option_list(question_id):
    '''function to get user selected options'''
    filter_list = list(questionFilters.objects.filter(question=question_id).values_list('filter', flat=True).distinct())
    values = ""
    for option in filter_list:
        values = values + option + "$#"

    if len(values) >= 2:
        values = values[:-2]
    return values


@csrf_exempt
def push_email(request):
    '''api to save secondary email'''

    member_id = get_member_id_from_headers(request)
    email = request.POST.get('email')
    if not member_id:
        return JsonResponse({'success': False, 'error_message': "Member id is not coming in header"})

    Userinfo.objects.filter(user_id=member_id).update(secondary_email=email)

    return JsonResponse({'success': True})


def get_data_for_filter_pop_ups(email):
    '''function to get data for filtered pop-ups'''

    member_direction_lock = {}

    member_direction_lock['member_directory_lock_title'] = "Member profile not accessible"
    member_direction_lock['member_directory_lock_sub_title'] = """Your account is pending for approval from the admin. Once the admin approves, you would be able to view the full communtity profile of the user.

Once verified, we will send an email on: """ + str(email)
    member_direction_lock['member_directory_lock_negative_title'] = "DISMISS"
    member_direction_lock['member_directory_lock_positive_title'] = "Change EMAIL ID"

    # member_directory_lock_negative_action,member_directory_lock_positive_action

    member_direction_lock['member_directory_lock_email_title'] = "Change Email ID"
    member_direction_lock[
        'member_directory_lock_email_sub_title'] = "Update your email ID below for further communications."
    member_direction_lock['member_directory_lock_email_negative_title'] = "DISMISS"
    member_direction_lock['member_directory_lock_email_positive_title'] = "SUBMIT"

    # member_directory_lock_email_positive_action,member_directory_lock_email_negative_action

    return member_direction_lock


def get_profile(request):
    '''api to send user object'''

    member_id = request.GET.get('member_id')

    try:
        user = Userinfo.objects.get(user_id=member_id)
        usr = UserinfoSerializer(user)
        return JsonResponse({'user': usr})
    except:
        print("userinfo object does not exist")

    return JsonResponse({'user': []})


# Reporting collabcard functions

def fetch_report_tags(request):
    """ api to send report tags """

    tag_type = request.GET.get('type')

    if not tag_type:
        tag_type = report_Tag_Types.CHATROOM_REPORT_TAG

    if not isinstance(tag_type, int) and not tag_type.isdigit():
        context = ResponseUtilities.get_view_impl_error_context("send valid type in params",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    tag_type = int(tag_type)
    report_tags_instances = []

    if tag_type in [
        report_Tag_Types.CHATROOM_REPORT_TAG,
        report_Tag_Types.COMMUNITY_REPORT_TAG,
        report_Tag_Types.CONVERSATION_REPORT_TAG,
        report_Tag_Types.LINK_REPORT_TAG
    ]:
        report_tags_instances = ModelUtilities.get_model_filter(Report_Tags, {'type': 0})

    if tag_type == report_Tag_Types.MEMBER_REPORT_TAG:
        report_tags_instances = ModelUtilities.get_model_filter(Report_Tags, {'type': 1})

    report_tags = [{'id': instance.tag_id, 'name': instance.tag_name} for instance in report_tags_instances]

    return JsonResponse({'success': True, 'report_tags': report_tags})


@csrf_exempt
def push_report(request):
    """ Fucntion to report a user or a collabcard """
    if request.method == 'POST':

        member_id = get_member_id_from_headers(request)
        user_instance = User.objects.get(id=member_id)

        request_body = json.loads(request.body)
        info_logger.info(request_body)
        collabcard_id = request_body['collabcard_id'] if 'collabcard_id' in request_body else None
        collabcard_instance = Collabcard.objects.get(id=collabcard_id) if collabcard_id else None

        community_id = request_body['community_id'] if 'community_id' in request_body else None

        tag_id = request_body['tag_id'] if 'tag_id' in request_body else None

        report_tags_instance = Report_Tags.objects.get(tag_id=tag_id) if tag_id else None
        reason = request_body['reason'] if 'reason' in request_body else None
        reported_member_id = int(request_body['reported_member_id']) if 'reported_member_id' in request_body else None

        link = request_body['link'] if 'link' in request_body else None
        conversation_id = request_body['conversation_id'] if 'conversation_id' in request_body else None
        conversation_instance = None
        if conversation_id:
            conversation_instance = card_answers.objects.get(id=conversation_id)

        report_instance = Report()
        if report_tags_instance:
            report_instance.tag = report_tags_instance
        if collabcard_instance:
            report_instance.collabcard = collabcard_instance
        if reason:
            report_instance.reason = reason
        report_instance.member = user_instance

        if reported_member_id:
            report_instance.reported_member_id = reported_member_id
            report_instance.date_epoch = time.time()

        report_instance.link = link
        report_instance.conversation = conversation_instance

        if community_id:
            community_instance = Community.objects.get(id=community_id)
            report_instance.community = community_instance

        report_instance.save()

        # community_url = url + "/community/" + str(collabcard_instance.community.id)
        print(reported_member_id, community_id, collabcard_id, conversation_id)
        if reported_member_id:
            subject = '[Member reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)
        elif community_id is not None:
            subject = '[Community reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)
        elif collabcard_id is not None:
            subject = '[Chatroom reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)
        elif conversation_id:
            subject = '[Text reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)

        print(subject)

        try:
            if reported_member_id:
                reported_user_instance = User.objects.get(pk=reported_member_id)
                reported_user_name = reported_user_instance.userinfo.name
            else:
                reported_user_name = None
            # send_mail_for_report_abuse.delay(user_instance.userinfo.name, collabcard_instance.title,
            #                                                 report_tags_instance.tag_name,
            #                                                 collabcard_instance.community.name,
            #                                                 community_url, reported_user_name, reason)
        except Exception as e:
            log = """Unmatched object for user_id=%s""" % (request_body['reported_member_id'])
            info_logger.info(log)
            info_logger.info(e)
        info_logger.info("push report api successfull")
        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


@csrf_exempt
def push_report_v1(request):
    """ Fucntion to report a user, collabcard, conversation, community and a link"""
    if request.method == 'POST':

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)
        if not user_instance:
            return JsonResponse(get_error_context(False, "invalid member_id"))

        request_body = json.loads(request.body)
        collabcard_id = request_body['collabcard_id'] if 'collabcard_id' in request_body else None
        community_id = request_body['community_id'] if 'community_id' in request_body else None
        tag_id = request_body['tag_id'] if 'tag_id' in request_body else None
        reason = request_body['reason'] if 'reason' in request_body else None
        reported_member_id = int(request_body['reported_member_id']) if 'reported_member_id' in request_body else None
        link = request_body['link'] if 'link' in request_body else None
        conversation_id = request_body['conversation_id'] if 'conversation_id' in request_body else None
        entity_id = request_body['entity_id'] if 'entity_id' in request_body else None
        entity_type = request_body['entity_type'] if 'entity_type' in request_body else None
        entity_creator_id = request_body['entity_creator_id'] if 'entity_creator_id' in request_body else None

        report_type = report_Types.REPORT_COMMUNITY  # assume as community reported
        reported_member_instance = None
        collabcard_instance = None
        conversation_instance = None
        is_promoter = False
        is_owner = False
        has_right_0 = False  # right to delete chat rooms or conversations
        has_right_1 = False  # right to approve or reject pending requests

        member_instance = Members.objects.filter(community_id=community_id, member_id=member_id)
        if member_instance.exists():
            member = member_instance[0]
            is_owner = member.is_owner
            is_promoter = member.state == member_states.ADMIN
            has_right_0 = check_admin_delete_right(user=member_id, community=community_id)
            has_right_1 = check_admin_approve_right(user=member_id, community=community_id)

        if collabcard_id:
            if is_promoter and has_right_0:
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                    "you have no right to report chatroom", status_codes.HTTP_400_BAD_REQUEST))

            collabcard_instance = ModelUtilities.get_model_instance_or_none(Collabcard, collabcard_id)
            if not collabcard_instance:
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                    "invalid collabcard_id", status_codes.HTTP_400_BAD_REQUEST))

            report_type = report_Types.REPORT_CHATROOM
            if not reported_member_id:
                reported_member_instance = collabcard_instance.user

            if not community_id:
                community_id = collabcard_instance.community.id

        elif conversation_id:
            if is_promoter and has_right_0:
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                    "you have no right to report conversations", status_codes.HTTP_400_BAD_REQUEST))

            conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)
            if not conversation_instance:
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                    "invalid conversation_id", status_codes.HTTP_400_BAD_REQUEST))

            report_type = report_Types.REPORT_CONVERSATION

            if collabcard_instance is None:
                collabcard_instance = conversation_instance.card

            if not reported_member_id:
                reported_member_instance = conversation_instance.user

            if not community_id:
                community_id = conversation_instance.community.id

        elif reported_member_id and not reported_member_instance:
            if is_promoter and has_right_1:
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                    "you have no right to report a member", status_codes.HTTP_400_BAD_REQUEST))

            if not community_id and not api_key:
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                    "send community_id or api_key", status_codes.HTTP_400_BAD_REQUEST))

            report_type = report_Types.REPORT_MEMBER

            reported_member_instance = ModelUtilities.get_model_instance_or_none(User, reported_member_id)
            if not reported_member_instance:
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                    "invalid reported_member_id", status_codes.HTTP_400_BAD_REQUEST))

        elif entity_id and entity_creator_id and entity_type and not reported_member_instance:
            reported_member_instance = ModelUtilities.get_user_instance_or_none(entity_creator_id)
            if not reported_member_instance:
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                    "invalid reported_member_id", status_codes.HTTP_400_BAD_REQUEST))

            if entity_type not in [report_Types.REPORT_POST, report_Types.REPORT_COMMENT, report_Types.REPORT_REPLY]:
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                    "invalid entity_type", status_codes.HTTP_400_BAD_REQUEST))

            report_type = entity_type

        report_tag_instance = ModelUtilities.get_model_instance_or_none(Report_Tags, tag_id)

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)
        if not community_instance:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                "Invalid API key/community ID", status_codes.HTTP_400_BAD_REQUEST))

        community_id = community_instance.id

        report_instance = Report()
        report_instance.tag = report_tag_instance
        report_instance.reason = reason

        report_instance.collabcard = collabcard_instance
        report_instance.conversation = conversation_instance
        report_instance.community = community_instance
        report_instance.entity_id = entity_id

        report_instance.reported_member_id = reported_member_id  # has to be removed
        report_instance.user_reported = reported_member_instance
        report_instance.member = user_instance  # has to be removed
        report_instance.reported_by = user_instance
        if link:
            report_type = report_Types.REPORT_LINK
        report_instance.link = link
        report_instance.type = report_type
        report_instance.date_epoch = time.time()
        report_instance.save()

        update_report_count_for_all_promoters.delay(community_id)

        if report_type in [report_Types.REPORT_MEMBER, report_Types.REPORT_CHATROOM] and not is_owner:
            send_notification_for_reports.delay(report_id=report_instance.id, community_id=community_id,
                                                reported_by_user_id=member_id, card_id=collabcard_id,
                                                conversation_id=conversation_id,
                                                reported_on_user_id=reported_member_instance.id,
                                                report_type=report_type, reason=reason, tag_id=tag_id)

        if report_type == 1 and is_owner:
            subject = '[Chatroom reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)
        elif report_type == 2 and is_owner:
            subject = '[Text reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)
        elif report_type == 0 and is_owner:
            subject = '[Member reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)
        elif report_type == 3:
            subject = '[Community reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)
        elif report_type == 5 and is_owner:
            subject = '[Post reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)
        elif report_type == 6 and is_owner:
            subject = '[Comment reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)
        elif report_type == 7 and is_owner:
            subject = '[Reply reported] LikeMinds App'
            send_report_mail_to_team.delay(subject, report_instance.id)

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


def fetch_master_questions(request):
    # getting master Questions

    page = request.GET.get('page', 1)
    master_question_list = masterQuestions.objects.all().order_by('id')
    master_question_list = pagination(master_question_list, page_number=page, paginate_by=50)
    master_questions = []
    for instance in master_question_list:
        master_questions.append(masterQuestionSerializer(instance))

    return JsonResponse({
        'master_questions': master_questions
    })


# email address verification for syncing new email accounts

@csrf_exempt
def sync_email(request):
    '''function to syc the email with existing account'''

    member_id = get_member_id_from_headers(request)

    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context)

    try:
        user_instance = User.objects.get(id=member_id)
    except:
        context = get_error_context(False, "User does not exists")
        return JsonResponse(context)

    email = request.POST.get('email_id', None)
    email_state = request.POST.get('email_state', 0)
    if not email:
        context = get_error_context(False, "send a email id in post params")
        return JsonResponse(context)

    verification_details = generate_tokens_for_email(user_instance, email, email_state=email_state)

    # sending a email from template
    send_verification_mail_for_email_sync.delay(user_name=user_instance.userinfo.name,
                                                verification_link=verification_details['verify_url'], email=email)

    return JsonResponse({'success': True})


def generating_verification_link_for_email(token_list, user_id):
    '''function to generate verification link for email and saving the email'''

    token = generate_random(token_list)
    # print(token)
    # encrpt_number = encrypt(token)
    # user_id = encrypt(user_id)
    # print(user_id)
    verify_url = url + "/api/email_verify?token=" + str(token) + "&user=" + str(user_id)

    temp = {'verify_url': verify_url, 'token': token}

    return temp


def generate_tokens_for_email(user_instance, email, email_state=0):
    token_list = list(emailTokens.objects.filter(user=user_instance).values_list('token', flat=True))

    verification_details = generating_verification_link_for_email(token_list, user_instance.id)

    # saving the email token details for user
    instance = emailTokens()
    instance.user = user_instance
    instance.token = verification_details['token']
    instance.expire_time = 86400  # 24 hours
    instance.email = email
    instance.email_state = email_state
    instance.save()

    return verification_details


# web apis  flow

@api_view(['GET', 'POST'])
@renderer_classes([JSONRenderer, TemplateHTMLRenderer])
def email_verify(request):
    '''api to verify the email details'''

    if request.accepted_renderer.format == 'html':

        token = request.GET.get('token')
        user = request.GET.get('user')

        current_time = time.time()
        if not token or not user:
            return HttpResponse("Invalid link")

        # decoded_token = decrypt(token)
        # decoded_user = decrypt(user)

        decoded_token = token
        decoded_user = user

        # getting the user instance
        try:
            user_instance = User.objects.get(id=decoded_user)
        except:
            context = get_error_context(False, "User does not exists")
            return HttpResponse(context)

        info_logger.info("Email Verify")
        info_logger.info(decoded_token)
        info_logger.info(decoded_user)
        info_logger.info("\n")

        instance_list = emailTokens.objects.filter(token=decoded_token, user=user_instance)

        if instance_list.exists():
            instance = instance_list[0]
            # print(instance)

            context = {
                'verification': True,
                'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                'facebook_auth_id': settings.SOCIAL_AUTH_FACEBOOK_KEY,
                'firebase_config': settings.FIREBASE_CONFIG
            }

            # if the link is verified
            if (current_time - instance.created_at) <= instance.expire_time:

                user_email_list = userEmails.objects.filter(email=instance.email, user=user_instance, verified=False)
                if user_email_list.exists():
                    user_email_list.update(user=user_instance, email=instance.email, verified=True)
                    delete_status = userEmails.objects.filter(email=instance.email).filter(
                        ~Q(user=user_instance)).delete()

                else:
                    return HttpResponse("This email is already verified by another user!!!!!")

                return render(request, 'email_verify_landing.html', context)


            else:
                context['verification'] = False

                return render(request, 'email_verify_landing.html', context)

    return render(request, 'email_verify_landing.html', {'verification': False})


###############################mixpanel events########################################


def get_member_community_status(state):
    member = ""
    if state == 0:
        member = "not_member"
    elif state == 1:
        member = "member"
    elif state == 3:
        member = "not_member"
    elif state == 4:
        member = "member"
    elif state == 7:
        member = "not_member"

    return member


def get_event_super_properties_for_mixpanel(user_instance, community_instance):
    '''function to get event super properties for mixpanel'''

    if not user_instance or not community_instance:
        return {}

    context = {}
    user_profile = user_instance.userinfo
    context['name'] = user_profile.name
    context['email'] = user_profile.email
    context['user_unique_id'] = user_instance.id
    context['first_login_date'] = 0 if user_profile.created_at < 0 else time.strftime('%A, %b %d', time.localtime(
        user_profile.created_at))

    state_data = Members.objects.filter(community_id=community_instance.id, member_id=user_instance.id)
    state = 0
    if state_data.exists():
        state = state_data[0].state

    context['user_community_state'] = get_member_community_status(state)

    followed_count = collabcardState.objects.filter(follow_status=True, user=user_instance).count()
    context['No_of_Chatrooms_Followed'] = followed_count

    communities_count = Members.objects.filter(member_id=user_instance.id).filter(
        Q(state=member_states.MEMBER) | Q(state=member_states.ADMIN) | Q(
            state=member_states.KNOWN_NOMINATED_PROMOTER)).count()
    context['No_of_community_member'] = communities_count

    distinct_cr_count = card_answers.objects.filter(user=user_instance).distinct('card_id').count()
    context['No_of_unique_cr_responded'] = distinct_cr_count

    if settings.IS_BETA:
        context['token'] = "eb1e03c8be370040278bff61a4857608"
    else:
        context['token'] = "7907eb37f46b1ac2908d3881e633a85e"

    return context


def test_notification_api(request):
    '''function to test notification api'''

    card_id = request.GET.get('card_id')
    user_id = request.GET.get('user_id')

    if card_id:
        card_instance = Collabcard.objects.get(id=card_id)
        temp = {}
        temp['title'] = "Chatroom Creation"
        temp['sub_title'] = "payload data for chatroom creation"
        temp['route'] = "route://collabcard?collabcard_id=" + str(card_id)
        temp['unread_new_chatroom'] = get_custom_data_for_new_chatroom_created(card_instance)

        return JsonResponse(temp)

    if user_id:
        temp = {}
        temp['title'] = "Conversation Creation"
        temp['sub_title'] = "payload data for conversation creation"
        temp['route'] = "route://collabcard?collabcard_id=" + str(card_id)
        temp['unread_conversation'] = get_custom_data_for_new_conversation_created(user_id, None)

        return JsonResponse(temp)

    return JsonResponse({'error': 'send user_id or conversation_id in order to see payload'})


def unread_conversation_notification(request):
    member_id = get_member_id_from_headers(request)

    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    community_id: str = request.GET.get('community_id')

    temp = {
        'success': True,
        'unread_conversation': get_custom_data_for_new_conversation_created(member_id, community_id)
    }

    return JsonResponse(temp)


@csrf_exempt
def submit_poll(request):
    if request.method == 'POST':
        res = json.loads(request.body)
        collabcard_id = res['chatroom_id']
        # collabcard_id = request.POST.get('chatroom_id', None)

        if not collabcard_id:
            context = get_error_context(success=False, error_message="Send the correct chatroom id")
            return JsonResponse(context)

        member_id = get_member_id_from_headers(request)
        if request.user.is_authenticated and not get_request_type(request):
            member_id = request.user.id
        if not member_id:
            context = get_error_context(success=False, error_message="Send member id in headers")
            return JsonResponse(context)

        polls = res['polls']  # request.POST.get('poll', None)
        if not polls:
            context = get_error_context(success=False, error_message="Send array of polls in post params")
            return JsonResponse(context)

        user_instance = User.objects.get(pk=member_id)

        card_instance = Collabcard.objects.get(pk=collabcard_id)

        # deleting the previous votes
        memberpolls_filter = MemberPollVotes.objects.filter(card=card_instance, user=user_instance)
        memberpolls_filter.delete()

        for poll in polls:
            vote_poll(poll["id"], card_instance, user_instance, collabcard_id)

        # if not str(member_id) == str(card_instance.user.id):
        #     send_poll_or_event_notification.delay(card_id=collabcard_id, user_id=member_id)

        # autofollowing the collabcard
        function_dict = {
            'member_id': user_instance.id,
            'collabcard_id': card_instance.id,
            'status': True,
            'source': "submit poll"
        }
        collabcard_follow_internal(function_dict)

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       {'card': card_instance},
                                       {})
        send_sync_notification.delay({'chatroom_id': collabcard_id,
                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

        return JsonResponse({"success": True})

    context = get_error_context(success=False, error_message="Change HTTP method to POST")
    return JsonResponse(context)


@csrf_exempt
def add_poll(request):
    if request.method == 'POST':
        res = json.loads(request.body)
        collabcard_id = res['chatroom_id']

        if not collabcard_id:
            context = get_error_context(success=False, error_message="Send the correct chatroom id")
            return JsonResponse(context)

        member_id = get_member_id_from_headers(request)
        if not member_id:
            context = get_error_context(success=False, error_message="Send member id in headers")
            return JsonResponse(context)

        polls = res['polls']  # request.POST.get('poll', None)
        if not polls:
            context = get_error_context(success=False, error_message="Send array of polls in post params")
            return JsonResponse(context)

        user_instance = User.objects.get(pk=member_id)

        card_instance = Collabcard.objects.get(pk=collabcard_id)

        poll_list = []
        for poll in polls:
            collabcardpolls_instance = CollabcardPolls()
            collabcardpolls_instance.card = card_instance
            collabcardpolls_instance.user = user_instance
            collabcardpolls_instance.text = poll['text']
            collabcardpolls_instance.sub_text = poll['sub_text'] if ('sub_text' in poll) else None
            collabcardpolls_instance.image_url = poll['image_url'] if ('image_url' in poll) else None
            collabcardpolls_instance.save()
            poll_list.append(CollabcardPollsSerializer(collabcardpolls_instance, user_instance, card_instance))

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       {'card': card_instance},
                                       {})
        send_sync_notification.delay({'community_id': card_instance.community.id,
                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

        return JsonResponse({"success": True, "polls": poll_list})

    context = get_error_context(success=False, error_message="Change HTTP method to POST")
    return JsonResponse(context)


def fetch_poll_users(request):
    poll_id = request.GET.get('poll_id')
    chatroom_id = request.GET.get('chatroom_id')

    if not chatroom_id:
        context = get_error_context(success=False, error_message="Send the correct chatroom id")
        return JsonResponse(context)

    member_id = get_member_id_from_headers(request)
    if not member_id:
        context = get_error_context(success=False, error_message="Send member id in headers")
        return JsonResponse(context)

    if not poll_id:
        context = get_error_context(success=False, error_message="Send the correct poll id")
        return JsonResponse(context)

    user_instance = User.objects.get(pk=member_id)
    card_instance = Collabcard.objects.get(pk=chatroom_id)
    community_id = card_instance.community.id
    poll_instance = CollabcardPolls.objects.get(id=poll_id)

    option_selected_members = MemberPollVotes.objects.filter(poll=poll_instance, card=card_instance)

    members_list = []

    for member in option_selected_members:
        member_instance = Members.objects.filter(community_id=community_id, member_id=member.user)
        if member_instance.exists():
            members_list.append(MembersSerializer(member_instance[0], community_id, current_user_id=member_id))
        else:
            user_data = get_user_profile(member.user, send_profile=True)

            removed_members = ModelUtilities.get_model_filter(removedMembers, {'community': community_id,
                                                                               'member': member.user})

            removed_member_custom_text = {}

            if removed_members:
                removed_member_custom_text = get_removed_member_custom_text(removed_members[0])

            members_list.append({**user_data, **removed_member_custom_text})

    return JsonResponse({"members": members_list})


@csrf_exempt
def delete_conversation(request):
    """ function to delete a conversation """

    if request.method == 'GET':
        context = ResponseUtilities.get_view_impl_error_context('Invalid method',
                                                                status_codes.HTTP_405_METHOD_NOT_ALLOWED)
        return JsonResponse(**context)

    member_id = get_member_id_from_headers(request)
    current_user_instance = ModelUtilities.get_user_instance_or_none(member_id)

    if not current_user_instance:
        context = ResponseUtilities.get_view_impl_error_context('Invalid member id',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    req_body = json.loads(request.body)

    conversation_ids = req_body.get('conversation_ids', None)
    tag_id = req_body.get('tag_id', None)
    reason = req_body.get('reason', None)

    if not conversation_ids:
        context = ResponseUtilities.get_view_impl_error_context('Send the conversation_ids in params',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    if not member_id:
        context = ResponseUtilities.get_view_impl_error_context('Send the member_id in headers',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    conversation_list = []
    community_id = None

    for conversation_id in conversation_ids:

        conversation = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

        if not conversation:
            continue

        update_conversation_delete_status(conversation, current_user_instance, reason=reason, tag_id=tag_id)

        conversation.refresh_from_db()

        conversation_context = {"current_user_id": member_id, "fetch_reply": True}
        conversation_dict = CardAnswersDBSyncSerializer(conversation, context=conversation_context, many=False).data
        conversation_list.append(conversation_dict)
        community_id = conversation_dict['community_id']

    ElasticSearchSync.delete_conversations.delay(conversation_ids)

    if community_id:
        send_sync_notification.delay({'community_id': community_id,
                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

    return JsonResponse({'success': True, 'conversations': conversation_list})


def update_conversation_delete_status(conversation_instance, current_user_instance,
                                      reason=None, tag_id=None):
    update_models_for_syncing_apis(SyncTypes.CONVERSATION,
                                   {'id': conversation_instance.id},
                                   {'deleted_by_user': current_user_instance, 'is_deleted': True})

    if int(current_user_instance.id) == int(conversation_instance.user.id):
        action_taken = report_Action_Types.RESPONSE_DELETED_BY_CREATOR
    else:
        action_taken = report_Action_Types.RESPONSE_DELETED_BY_CM

    check_reports_and_update_action.delay(action_taken_by=current_user_instance.id,
                                          action_taken=action_taken,
                                          conversation_id=conversation_instance.id, action_taken_tag_id=tag_id,
                                          action_taken_reason=reason)

    info_logger.info("successfully updated conversation_instance delete status")


@csrf_exempt
def edit_conversation(request):
    """ function to delete a conversation """

    if request.method == 'GET':
        context = ResponseUtilities.get_view_impl_error_context('Invalid method',
                                                                status_codes.HTTP_405_METHOD_NOT_ALLOWED)
        return JsonResponse(**context)

    member_id = get_member_id_from_headers(request)
    conversation_id = request.POST.get('conversation_id', None)
    edited_answer = request.POST.get('text', None)
    share_link = request.POST.get('share_link', None)
    og_tags = request.POST.get('og_tags', None)

    user_instance = ModelUtilities.get_user_instance_or_none(member_id)

    if not user_instance:
        context = ResponseUtilities.get_view_impl_error_context('Invalid member id',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    if share_link:
        og_tags_payload = {
            'share_link': share_link
        }

    elif og_tags:
        og_tags_payload = {
            'og_tags': og_tags
        }

    else:
        og_tags_payload = {}

    if not conversation_id:
        context = ResponseUtilities.get_view_impl_error_context('Send the conversation_ids in params',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    if not member_id:
        context = ResponseUtilities.get_view_impl_error_context('Send the member_id in headers',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    conversation = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

    if not conversation:
        context = ResponseUtilities.get_view_impl_error_context('Invalid conversation id',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    if conversation.is_deleted:
        context = ResponseUtilities.get_view_impl_error_context('Cannot edit deleted conversation',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    elif int(conversation.user.id) == int(member_id):

        from collabmates_api.conversation.conversation_impl import ConversationHelper

        og_tags = ConversationHelper.fetch_og_tags(og_tags_payload)

        update_models_for_syncing_apis(SyncTypes.CONVERSATION,
                                       {'id': conversation_id},
                                       {'answer': edited_answer, 'is_edited': True, 'og_tags': og_tags})
        conversation.refresh_from_db()

        ElasticSearchSync.update_conversations.delay([conversation_id])

    else:
        context = ResponseUtilities.get_view_impl_error_context('Only conversation creator can edit their message',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    context = {"current_user_id": member_id, "fetch_reply": True}
    conversation_dict = CardAnswersDBSyncSerializer(conversation, context=context, many=False).data

    send_sync_notification.delay({'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value,
                                  'community_id': conversation.community.id})

    return JsonResponse({'success': True, 'conversation': conversation_dict})


def fetch_preview(request):
    """ function to delete a conversation """

    if request.method == 'POST':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to GET'})

    member_id = get_member_id_from_headers(request)
    preview_url = request.GET.get('url', None)

    if not member_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)

    preview_url = get_preview_url(preview_url)

    if preview_url is None:
        context = get_error_context(False, "Branch url failed. Invalid url")
        return JsonResponse(context, status=400)

    try:
        context = get_preview_for_url(member_id, preview_url)
        return JsonResponse({"preview": context})
    except:
        context = get_error_context(False, "Branch url failed. Invalid url")
        return JsonResponse(context, status=400)


def get_preview_url(preview_url):
    """ get internal link from branch link """

    if settings.URL in preview_url or \
            settings.WEB_URL in preview_url:
        return preview_url

    elif BRANCH_LINK_PREFIX_ANDROID in preview_url or \
            BRANCH_LINK_PREFIX_IOS in preview_url:

        preview_url = "https://" + preview_url.split('//')[1]
        return preview_url

    elif preview_url is None or not preview_url:
        return None

    else:
        # API request
        api_endpoint = BRANCH_DECODE_URI % (preview_url, settings.BRANCH_KEY)
        headers = {'Accept': 'application/json'}
        r = requests.get(url=api_endpoint, headers=headers)

        if r.status_code == 200:
            try:
                data = r.json()
                deep_link = data["data"]['$deep_link']
                return deep_link

            except Exception as e:
                return None

        return None


############################## static apis for sending text ##############################################


def fetch_community_types(request):
    '''api to get type and sub-type of community'''

    type_filter = communityFieldTypes.objects.all().order_by('rank')

    types = []
    other_subtype = {}
    for instance in type_filter:
        temp = communityFieldTypeSerializer(instance)
        sub_type_list = []
        subtype_queryset = communityFieldSubTypes.objects.filter(type=instance.id).order_by('sub_type')
        if subtype_queryset.exists():
            other_subtype = {}
            for subtype_instance in subtype_queryset:
                subtype_temp = communityFieldSubTypesSerializer(subtype_instance)
                if subtype_temp['sub_type'] == 'Other':
                    other_subtype = subtype_temp
                    continue
                sub_type_list.append(subtype_temp)

        if other_subtype:
            sub_type_list.append(other_subtype)
        if sub_type_list:
            temp['sub_types'] = sub_type_list

        types.append(temp)

    context = {'types': types}
    context['onboarding_examples'] = ONBOARDING_EXAMPLES
    return JsonResponse(context)


def fetch_intro_examples(request):
    '''api to send introduction questions examples'''

    intro_examples = INTRODUCTION_EXAMPLES

    return JsonResponse({'intro_examples': intro_examples})


################################# moderation rights ###############################################
def validate_community_id_or_api_key(community_id, api_key):
    community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

    if not community_instance:
        return ResponseUtilities.get_inner_error_context("Invalid API key/community ID")

    return {"community_instance": community_instance}


def fetch_community_manager_rights(request):
    """ function to fetch manager rights """

    if request.method == 'POST':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to GET'},
                            status=status_codes.HTTP_405_METHOD_NOT_ALLOWED)

    current_user_id = get_member_id_from_headers(request)
    community_id = request.GET.get('community_id', None)
    user_id = request.GET.get('user_id', None)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)
    api_key = RequestUtilities.get_api_key_from_headers(request)

    community_dict = validate_community_id_or_api_key(community_id, api_key)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    if not user_id:
        context = get_error_context(False, "send user_id in params")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    if community_dict.get('error_message'):
        context = get_error_context(False, community_dict.get('error_message'))
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    community_instance = community_dict.get('community_instance')
    current_user_instance = ModelUtilities.get_user_instance_or_none(current_user_id)

    if not current_user_instance:
        context = get_error_context(False, "Invalid member_id in headers")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    user_instance = ModelUtilities.get_user_instance_or_none(user_id)

    if not user_instance:
        context = get_error_context(False, "Invalid user_id")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing

    rights_context = []

    if admin.exists():
        admin_rights = userAdminRights.objects.filter(community=community_instance,
                                                      user=current_user_instance).order_by('-right__rank')
        user_rights = list(userAdminRights.objects.filter(community=community_instance,
                                                          user=user_instance).values_list('right__id',
                                                                                          flat=True))
        if admin_rights.exists():
            is_member = len(user_rights) == 0

            for right in admin_rights:
                right = right.right

                if all([not m2cm_v2_version_check(platform_code, version_code),
                        right.state == moderate_dm_settings.get('state')]):
                    continue

                right_dict = get_right_dict(right)
                if is_member:
                    right_dict["is_selected"] = True if right.id in manager_rights.DEFAULT_MANAGER_RIGHTS else False
                else:
                    right_dict["is_selected"] = True if right.id in user_rights else False
                rights_context.append(right_dict)
        else:
            context = get_error_context(False, "user does not have any manager rights")
            return JsonResponse(context)

    else:
        context = get_error_context(False, "user is not a admin")
        return JsonResponse(context)
    member_profile = get_members_profile([user_instance], community_instance)

    mobile_filter = userMobiles.objects.filter(user=current_user_instance)
    mobile_list = []
    for mobile_no in mobile_filter:
        mobile_list.append(userMobilesSerializer(mobile_no))

    return JsonResponse({'success': True, "admin_mobiles": mobile_list, "member": member_profile[0],
                         "rights": rights_context})


def update_attending_status_for_paid_events_for_new_community_manager(user_instance, community_instance):
    getCommmuntiyEvents = ModelUtilities.get_model_filter(collabcardState,
                                    {'card__is_pending': False,
                                     'card__is_deleted': False,
                                     'user': user_instance,
                                     'community': community_instance,
                                     'secret_chatroom_left': False,
                                     'card__date_time__gt': TimeUtilities.current_time_in_milliseconds()}). \
        filter(Q(card__type=card_types.CARD_EVENT) | Q(card__type=card_types.CARD_PUBLIC_EVENT))

    #Get all events card_id list
    eventsList = getCommmuntiyEvents.values_list('card_id',flat=True) 
    getCommmuntiyEvents.update(attending_status=True, updated_at=TimeUtilities.current_time_in_sec())

    #Update in cache the attendies list for all the events 
    for card_id in eventsList:
        update_event_attendees({
            'chatroom_id': card_id,
            'user_id': user_instance.id,
            'status': True
        })


@csrf_exempt
def update_community_manager_rights(request):
    """ function to remove a communtiy manager as manager """

    if request.method == 'GET':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'},
                            status=status_codes.HTTP_405_METHOD_NOT_ALLOWED)

    current_user_id = get_member_id_from_headers(request)
    req_body = json.loads(request.body)
    user_id = req_body['user_id'] if "user_id" in req_body else None
    community_id = req_body['community_id'] if "community_id" in req_body else None
    selected_rights = req_body['rights'] if "rights" in req_body else []
    custom_title = req_body['custom_title'] if "custom_title" in req_body else None
    api_key = RequestUtilities.get_api_key_from_headers(request)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    community_dict = validate_community_id_or_api_key(community_id, api_key)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    if not user_id:
        context = get_error_context(False, "send user_id in params")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    if community_dict.get('error_message'):
        context = get_error_context(False, community_dict.get('error_message'))
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    community_instance = community_dict.get('community_instance')
    community_id = community_instance.id

    current_user_instance = ModelUtilities.get_user_instance_or_none(current_user_id)

    if not current_user_instance:
        context = get_error_context(False, "Invalid x-member-id")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    user_instance = ModelUtilities.get_user_instance_or_none(user_id)

    if not user_instance:
        context = get_error_context(False, "Invalid user id")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing

    member_is_owner = Members.objects.filter(member_id=user_instance, community_id=community_instance,
                                             state=member_states.ADMIN,
                                             is_owner=True).exists()  # who's rights are being updated
    member_title_changed = False

    if admin.exists():
        if member_is_owner:
            log = f"UPDATING_CM_RIGHTS_FOR_OWNER - community_id = {community_id}" \
                  f" current_user id = {current_user_id} user = {user_id}"
            info_logger.info(log)

            save_owner_title(custom_title, admin, community_instance, user_instance)

            # Update index of Members
            ElasticSearchSync.update_member.delay(user_id, community_id)

            send_sync_notification.delay({'community_id': community_id,
                                          'sync_notification_type': SyncNotificationTypes.SINGLE_MEMBER.value,
                                          'member_id': current_user_id})

            return JsonResponse({'success': True})

        moderate_dm_right_filter = ModelUtilities.get_model_filter(adminRights,
                                                                   {'state': manager_rights.MODERATE_DM_SETTINGS})

        if moderate_dm_right_filter:
            existing_rights = set(userAdminRights.objects.filter(community=community_instance,
                                                                 user=user_instance).values_list("right__id",
                                                                                                 flat=True))
            rights_added, removed_rights = get_added_and_removed_rights(selected_rights=selected_rights,
                                                                        existing_rights=existing_rights)

            if moderate_dm_right_filter[0].id in (list(rights_added) + list(removed_rights)) and \
                not check_admin_moderate_dm_settings_right(current_user_instance, community_instance):
                context = get_error_context(False, "You don't have right to give right of DM setting!")
                return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        rights_added, removed_rights = save_added_removed_rights_for_manager(community_instance,
                                                                             user_instance,
                                                                             selected_rights)

        if int(user_id) != int(current_user_id):
            member = Members.objects.filter(member_id=user_instance,
                                            community_id=community_instance)
            if member:
                member_instance = member[0]
            else:
                context = get_error_context(False, "user is not a member")
                return JsonResponse(context)

            is_member_already_promoter = member_instance.state == member_states.ADMIN

            custom_title, custom_title_changed = get_manager_custom_title(member_instance, custom_title,
                                                                          is_member_already_promoter)

            parent_cm = current_user_instance
            if member_instance.parent_cm:
                parent_cm = member_instance.parent_cm

            admin_parents = json.loads(admin[0].parent_cm_list) if admin[0].parent_cm_list else []
            member_parent_list = json.loads(member_instance.parent_cm_list) if member_instance.parent_cm_list else []

            final_parent_list = get_manager_parents_list(admin_parents, member_parent_list,
                                                         current_user_id)
            # updating parent cm list
            member.update(state=member_states.ADMIN, is_owner=False, custom_title=custom_title,
                          parent_cm=parent_cm, parent_cm_list=final_parent_list, updated_at=time.time())
            # saving moderation history for permission edited
            save_moderation_history(user=user_instance, community=community_instance,
                                    moderation_by=current_user_instance,
                                    type=moderation_history_types.MANAGER_PERMISSION_EDITED)
            # updating pending chatroom count and open reports count
            # bcz the necessary rights might have been added or removed
            update_pending_chatrooms_and_report_count.delay(community_id)

            if not is_member_already_promoter:

                # giving all of the members rights to promoter
                give_all_member_rights(user=user_instance, community=community_instance)
                update_models_for_syncing_apis(SyncTypes.COMMUNITY,
                                               {'member_id': user_instance, 'community_id': community_id},
                                               {'member_state': member_states.ADMIN,
                                                'rights_list': json.dumps(member_rights.ALL_MEMBER_RIGHTS)})

                save_moderation_history(user=user_instance, community=community_instance,
                                        moderation_by=current_user_instance,
                                        type=moderation_history_types.MADE_COMMUNITY_MANAGER)

                send_notification_for_new_promoter.delay(promoter_id=current_user_id, member_id=user_id,
                                                         community_id=community_id, custom_title=custom_title)
                update_attending_status_for_paid_events_for_new_community_manager(user_instance, community_instance)

                # DM chatroom add new CM
                is_m2cm_v2 = m2cm_v2_version_check(platform_code, version_code)
                member_becomes_cm_dm_chatroom.delay(user_id, community_id, is_m2cm_v2=is_m2cm_v2)

            elif custom_title_changed:
                member_title_changed = True

                # updating time for all members of community
                update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                               {'community_id': community_instance},
                                               {})
                send_notification_for_custom_title_changed.delay(promoter_id=current_user_id, member_id=user_id,
                                                                 community_id=community_id,
                                                                 custom_title=custom_title)

            if len(rights_added) > 0:
                send_notification_for_right_given_to_manager.delay(user_id, community_id, list(rights_added))

        info_logger.info(f"UPDATING_CM_RIGHTS current user id = {current_user_id},"
                         f" user id = {user_id}, community id = {community_id}")

        send_sync_notification.delay({'community_id': community_id,
                                      'sync_notification_type': SyncNotificationTypes.SINGLE_MEMBER.value,
                                      'member_id': current_user_id})

        # Update index of Members
        ElasticSearchSync.update_member.delay(user_id, community_id)

        return JsonResponse({'success': True})
    else:
        context = get_error_context(False, "user is not a admin")
        return JsonResponse(context)


def get_added_and_removed_rights(selected_rights, existing_rights):
    selected_rights_list = set([right["id"] for right in selected_rights if right["is_selected"]])
    rights_added = selected_rights_list - existing_rights
    removed_rights = existing_rights - selected_rights_list
    return rights_added, removed_rights


@csrf_exempt
def remove_community_manager(request):
    """ function to remove a communtiy manager as manager """

    if request.method == 'GET':
        context = ResponseUtilities.get_view_impl_error_context("Change HTTP method to POST",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    current_user_id = get_member_id_from_headers(request)
    community_id = request.POST.get('community_id', None)
    api_key = RequestUtilities.get_api_key_from_headers(request)
    user_id = request.POST.get('user_id', None)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    if not current_user_id:
        context = ResponseUtilities.get_view_impl_error_context("send member_id in headers",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])
    if not user_id:
        context = ResponseUtilities.get_view_impl_error_context("send user_id in params",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])
    if not community_id and not api_key:
        context = ResponseUtilities.get_view_impl_error_context("send community_id in params or api_key in headers",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

    if not community_instance:
        context = ResponseUtilities.get_view_impl_error_context("invalid community_id or api_key",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_id = community_instance.id

    current_user_instance = User.objects.get(pk=current_user_id)
    user_instance = User.objects.get(pk=user_id)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing

    is_user_cm = False

    if admin.exists():
        # deleting all manager rights
        userAdminRights.objects.filter(community=community_instance, user=user_instance).delete()

        # updating member state of manager to member
        member_instance = Members.objects.filter(community_id=community_instance,
                                                 member_id=user_instance)
        custom_title = "Member"
        if member_instance.exists():
            custom_title = member_instance[0].custom_title
            if custom_title == "Community Manager":
                custom_title = "Member"

            is_user_cm = member_instance[0].state == member_states.ADMIN

        update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                       {'community_id': community_instance, 'member_id': user_instance},
                                       {'state': member_states.MEMBER,
                                        'custom_title': custom_title,
                                        'parent_cm': None,
                                        'parent_cm_list': '[]'})

        update_models_for_syncing_apis(SyncTypes.COMMUNITY,
                                       {'member_id': user_instance, 'community_id': community_instance},
                                       {'pending_chatrooms': 0, 'open_reports': 0,
                                        'member_state': member_states.MEMBER})
        save_moderation_history(user=user_instance, community=community_instance,
                                moderation_by=current_user_instance,
                                type=moderation_history_types.REMOVED_AS_COMMUNITY_MANAGER)
        # updating time for all members of community
        update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                       {'community_id': community_instance},
                                       {})

        restore_member_rights_from_history(user_instance, community_instance)

        info_logger.info(f"REMOVE_COMMUNITY_MANAGER_API  current user id = {current_user_id}, user id = {user_id}"
                         f", community id = {community_id}")
        send_notification_for_removed_cm.delay(user_id, community_id)

        send_sync_notification.delay({'community_id': community_id,
                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

        # Add Message in DM Chatrooms
        if is_user_cm:
            is_m2cm_v2 = m2cm_v2_version_check(platform_code, version_code)
            cm_removed_dm_chatroom.delay(user_id, community_id, is_m2cm_v2=is_m2cm_v2)

        # Update Members Index
        ElasticSearchSync.update_member.delay(user_id, community_id)

        return JsonResponse({'success': True})

    else:
        context = ResponseUtilities.get_view_impl_error_context("you are not a admin",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])


@csrf_exempt
def transfer_community_ownership(request):
    """ function to transfer community ownership as manager """

    if request.method == 'GET':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'})

    current_user_id = get_member_id_from_headers(request)
    community_id = request.POST.get('community_id', None)
    user_id = request.POST.get('user_id', None)
    otp = request.POST.get('otp', None)
    mobile_no = request.POST.get('mobile_no', None)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not user_id:
        context = get_error_context(False, "send user_id in POST params")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in POST params")
        return JsonResponse(context)
    if not otp:
        context = get_error_context(False, "send otp in POST params")
        return JsonResponse(context)
    # if not mobile_no:
    #     context = get_error_context(False, "send mobile_no in POST params")
    #     return JsonResponse(context)

    if user_id:
        mobile_filter = userMobiles.objects.filter(user_id=current_user_id).order_by("-state")

        context = {'success': False}
        for instance in mobile_filter:
            phone_no = str(instance.country_code) + str(instance.mobile_no)

            international = False
            if str(instance.country_code) != '91':
                international = True

            otp_manager = OTPApiClient()
            context = otp_manager.verify_otp_via_gupshup(phone_no, otp, international)

            if context['success']:
                break

        if not context['success']:
            # verifying otp from email
            email_filter = userEmails.objects.filter(user_id=user_id)
            for instance in email_filter:
                email = instance.email
                context = verify_otp_on_email(email, otp)
                if context['success']:
                    break

        if not context['success']:
            return JsonResponse(context)

    # verified = verify_otp_on_mobile(mobile_no, otp)
    # if not verified['success']:
    #     context = get_error_context(False, "Incorrect OTP")
    #     return JsonResponse(context)

    community_instance = Community.objects.get(pk=community_id)
    current_user_instance = User.objects.get(pk=current_user_id)
    user_instance = User.objects.get(pk=user_id)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing
    if admin.exists():

        if not admin[0].is_owner:
            context = get_error_context(False, "you are not the owner of the community")
            return JsonResponse(context)

        new_owner = Members.objects.filter(community_id=community_instance,
                                           member_id=user_instance)

        new_owner_title = "Owner"
        if new_owner.exists() and new_owner[0].custom_title:
            new_owner_title = new_owner[0].custom_title
            if new_owner_title == "Community Manager" or new_owner_title == "Member":
                new_owner_title = "Owner"

        previous_owner_title = "Community Manager"
        if admin[0].custom_title:
            previous_owner_title = admin[0].custom_title
            if previous_owner_title == "Owner":
                previous_owner_title = "Community Manager"

        update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                       {'community_id': community_instance, 'member_id': user_instance},
                                       {
                                           'state': member_states.ADMIN,
                                           'custom_title': new_owner_title,
                                           'parent_cm': None,
                                           'parent_cm_list': None,
                                           'is_owner': True})
        update_models_for_syncing_apis(SyncTypes.COMMUNITY,
                                       {'member_id': user_instance, 'community_id': community_instance},
                                       {'rights_list': json.dumps(member_rights.ALL_MEMBER_RIGHTS),
                                        'member_state': member_states.ADMIN,
                                        'click_state': click_states.DEFAULT})
        conversationEngage.objects.filter(user=user_instance, community=community_instance).update(
            rights_list=json.dumps(member_rights.ALL_MEMBER_RIGHTS))

        give_all_manager_rights(user_instance, community_instance)  # for new owner
        # current owner
        parent_cm_list = json.dumps([str(user_id)])
        admin.update(is_owner=False, custom_title=previous_owner_title,
                     parent_cm=user_instance, parent_cm_list=parent_cm_list,
                     updated_at=time.time())

        save_moderation_history(user=current_user_instance, community=community_instance,
                                moderation_by=user_instance,
                                type=moderation_history_types.TRANSFERRED_OWNERSHIP)

        update_parent_cm_list(community_id=community_id, new_owner_id=user_id, prev_owner_id=current_user_id)
        # updating pending chatroom count and open reports count
        update_pending_chatrooms_and_report_count.delay(community_id)
        send_notification_for_ownership_transfered.delay(prev_owner_id=current_user_id,
                                                         new_owner_id=user_id, community_id=community_id)
        # updating time for all members of community
        update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                       {'community_id': community_instance},
                                       {})
        info_logger.info(f"TRANSFER_OWNERSHIP_API  current user id = {current_user_id}, user id = {user_id}"
                         f", community id = {community_id}")

        send_sync_notification.delay({'community_id': community_id,
                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})
        update_multiple_previews_in_community.delay({'community_id': community_id})

        return JsonResponse({'success': True})

    else:
        context = get_error_context(False, "you are not a admin")
        return JsonResponse(context)


@shared_task
def update_parent_cm_list(community_id, new_owner_id, prev_owner_id):
    all_promoters = Members.objects.filter(community_id=community_id, is_owner=False, state=member_states.ADMIN)

    for member in all_promoters:
        member_instance = Members.objects.get(pk=member.id)  # id is members table primary key
        # need instance to update the data

        if member_instance.is_owner:
            continue

        parent_list = json.loads(member_instance.parent_cm_list) if member_instance.parent_cm_list is not None else []
        if str(new_owner_id) not in parent_list:
            parent_list.append(new_owner_id)

        # if int(prev_owner_id) != member_instance.parent_cm.id:
        #     if str(prev_owner_id) in parent_list:
        #         parent_list.remove(str(prev_owner_id))

        member_instance.parent_cm_list = json.dumps(parent_list)
        member_instance.save()


def fetch_community_member_rights(request):
    """ function to fetch member rights """

    if request.method == 'POST':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to GET'},
                            status=status_codes.HTTP_405_METHOD_NOT_ALLOWED)

    current_user_id = get_member_id_from_headers(request)
    community_id = request.GET.get('community_id', None)
    user_id = request.GET.get('user_id', None)
    api_key = RequestUtilities.get_api_key_from_headers(request)

    community_dict = validate_community_id_or_api_key(community_id, api_key)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    if not user_id:
        context = get_error_context(False, "send user_id in params")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    if community_dict.get('error_message'):
        context = get_error_context(False, community_dict.get('error_message'))
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    community_instance = community_dict.get('community_instance')

    current_user_instance = ModelUtilities.get_user_instance_or_none(current_user_id)

    if not current_user_instance:
        context = get_error_context(False, "Invalid x-member-id")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    user_instance = ModelUtilities.get_user_instance_or_none(user_id)

    if not user_instance:
        context = get_error_context(False, "Invalid user id")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing

    if admin.exists():
        admin_rights = check_all_manager_rights(current_user_instance, community_instance)
        user_rights = check_all_member_rights(user_instance, community_instance)

        rights_context = get_saved_member_rights_list(user_rights, admin_rights)

        rights_context = update_member_rights_for_sdk(rights_context, community_instance)

    else:
        context = get_error_context(False, "user is not a admin")
        return JsonResponse(context)

    member_profile = get_members_profile([user_instance], community_instance)

    return JsonResponse({"success": True, "member": member_profile[0], "rights": rights_context})


@csrf_exempt
def update_community_member_rights(request):
    """ function to remove a communtiy manager as manager """

    if request.method == 'GET':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'},
                            status=status_codes.HTTP_405_METHOD_NOT_ALLOWED)

    current_user_id = get_member_id_from_headers(request)
    req_body = json.loads(request.body)
    user_id = req_body['user_id'] if "user_id" in req_body else None
    community_id = req_body['community_id'] if "community_id" in req_body else None
    selected_rights = req_body['rights'] if "rights" in req_body else []
    custom_title = req_body['custom_title'] if "custom_title" in req_body else None
    api_key = RequestUtilities.get_api_key_from_headers(request)

    community_dict = validate_community_id_or_api_key(community_id, api_key)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    if not user_id:
        context = get_error_context(False, "send user_id in params")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    if community_dict.get('error_message'):
        context = get_error_context(False, community_dict.get('error_message'))
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    community_instance = community_dict.get('community_instance')
    community_id = community_instance.id

    current_user_instance = ModelUtilities.get_user_instance_or_none(current_user_id)

    if not current_user_instance:
        context = get_error_context(False, "Invalid x-member-id")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    user_instance = ModelUtilities.get_user_instance_or_none(user_id)

    if not user_instance:
        context = get_error_context(False, "Invalid user_id")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    info_logger.info(f"UPDATING_MEMBER_RIGHTS - current user id = {current_user_id}, user id = {user_id}"
                     f", community id = {community_id}")

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing
    member_is_promoter = Members.objects.filter(member_id=user_instance, community_id=community_instance,
                                                state=member_states.ADMIN).exists()

    if member_is_promoter:
        log = """UPDATING_MEMBER_RIGHTS_FOR_CM = community_id=%s for user=%s""" % (community_id, user_id)
        info_logger.info(log)

        return JsonResponse({'success': True})

    if admin.exists():
        # create or delete member rights
        rights_added, rights_removed = save_added_removed_rights_for_member(community_instance,
                                                                            user_instance,
                                                                            selected_rights)
        # saving custom title for member
        custom_title_changed = save_member_custom_title(custom_title, community_instance, user_instance)
        # saving members rights list in engage table
        save_member_rights_in_engage(selected_rights, user_instance, community_instance)

        if len(selected_rights) > 0:
            save_moderation_history(user=user_instance, community=community_instance,
                                    moderation_by=current_user_instance,
                                    type=moderation_history_types.MEMBER_PERMISSION_EDITED)

            check_reports_and_update_action.delay(action_taken_by=current_user_id,
                                                  action_taken=report_Action_Types.EDIT_MEMBER_PERMISSION,
                                                  user=user_id, community=community_id,
                                                  added_member_rights=list(rights_added),
                                                  removed_member_rights=list(rights_removed))

        if len(rights_added) > 0:
            send_notification_for_right_given_to_member.delay(user_id, community_id, list(rights_added))

        if custom_title_changed:
            # updating time for all members of community
            update_models_for_syncing_apis(SyncTypes.MEMBERS,
                                           {'community_id': community_instance},
                                           {})
            send_notification_for_custom_title_changed.delay(promoter_id=current_user_id, member_id=user_id,
                                                             community_id=community_id,
                                                             custom_title=custom_title)

        update_member_rights_history.delay(rights_added, rights_removed, current_user_id, community_id, user_id)

        send_sync_notification.delay({'community_id': community_id,
                                      'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value})

        # Update Members Indexing
        ElasticSearchSync.update_member.delay(user_id, community_id)

        return JsonResponse({'success': True})
    else:
        context = get_error_context(False, "user is not a admin")
        return JsonResponse(context)


@shared_task
def check_reports_and_update_action(action_taken_by, action_taken, conversation_id=None,
                                    user=None, community=None, chatroom_id=None,
                                    added_member_rights=None, removed_member_rights=None,
                                    added_admin_rights=None, removed_admin_rights=None,
                                    action_taken_tag_id=None, action_taken_reason=None):
    if chatroom_id:
        reports = Report.objects.filter(collabcard=chatroom_id)
    elif conversation_id:
        reports = Report.objects.filter(conversation=conversation_id)
    elif user and community:
        reports = Report.objects.filter(user_reported=user, community=community)
    else:
        return

    if reports.exists():
        final_rights_added = {}
        final_rights_removed = {}

        # for getting added rights
        if added_member_rights:
            added_member_rights_list = []
            added_member_rights = memberRights.objects.filter(pk__in=added_member_rights)
            for right in added_member_rights:
                right_dict = get_right_dict(right)
                added_member_rights_list.append(right_dict)
            final_rights_added = {"member_rights": added_member_rights_list}

        if added_admin_rights:
            added_admin_rights_list = []
            added_admin_rights = adminRights.objects.filter(pk__in=added_admin_rights)
            for right in added_admin_rights:
                right_dict = get_right_dict(right)
                added_admin_rights_list.append(right_dict)

            final_rights_added = {"admin_rights": added_admin_rights_list}

        # for getting removed rights
        if removed_member_rights:
            removed_member_rights_list = []
            removed_member_rights = memberRights.objects.filter(pk__in=removed_member_rights)
            for right in removed_member_rights:
                right_dict = get_right_dict(right)
                removed_member_rights_list.append(right_dict)

            final_rights_removed = {"member_rights": removed_member_rights_list}

        if removed_admin_rights:
            removed_admin_rights_list = []
            removed_admin_rights = adminRights.objects.filter(pk__in=removed_admin_rights)
            for right in removed_admin_rights:
                right_dict = get_right_dict(right)
                removed_admin_rights_list.append(right_dict)

            final_rights_removed = {"admin_rights": removed_admin_rights_list}

        action_taken_tag_instance = None
        if action_taken_tag_id:
            action_taken_tag_instance = Report_Tags.objects.get(tag_id=action_taken_tag_id)

        final_rights_added = json.dumps(final_rights_added)
        final_rights_removed = json.dumps(final_rights_removed)
        action_taken_by_user = User.objects.get(pk=action_taken_by)

        reports.update(action_taken_by=action_taken_by_user, action_taken=action_taken,
                       rights_added=final_rights_added, rights_removed=final_rights_removed,
                       action_taken_tag=action_taken_tag_instance, action_taken_reason=action_taken_reason
                       )
    return


def fetch_moderation_history(request):
    """ function to fetch moderation history of a member """

    if request.method == 'POST':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to GET'})

    current_user_id = get_member_id_from_headers(request)
    community_id = request.GET.get('community_id', None)
    user_id = request.GET.get('user_id', None)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not user_id:
        context = get_error_context(False, "send user_id in params")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in params")
        return JsonResponse(context)

    current_member_instance = Members.objects.filter(member_id=current_user_id, community_id=community_id,
                                                     state=member_states.ADMIN)
    viewed_member_instance = Members.objects.filter(member_id=user_id, community_id=community_id)

    current_user_is_promoter = False
    if current_member_instance.exists():
        current_user_is_promoter = True

    parent_cm_list = None
    is_child = False  # user id is child or grand child of x-member-id
    viewed_member_state = 0
    if viewed_member_instance.exists():
        viewed_member = viewed_member_instance[0]
        viewed_member_state = viewed_member.state
        parent_cm_list = json.loads(viewed_member.parent_cm_list) if viewed_member.parent_cm_list else None
        print("parent_cm_list ===  ", parent_cm_list)

    if parent_cm_list:
        is_child = current_user_id in parent_cm_list
    history_list = []
    moderations = moderationHistory.objects.select_related("user", "community", 'moderation_by').filter(user=user_id,
                                                                                                        community_id=community_id).order_by(
        "id")
    for moderation in moderations:
        history = get_moderation_history_title(moderation)
        history_list.append(history)

    context = {"moderations": history_list}
    print("child ===  ", is_child)
    if is_child:
        edit_type = 0
        context["edit_type"] = edit_type

    elif current_user_is_promoter and (viewed_member_state == member_states.MEMBER or
                                       viewed_member_state == member_states.PROFILE_UNAVAILABLE or
                                       viewed_member_state == member_states.KNOWN_NOMINATED_PROMOTER):
        edit_type = 1
        context["edit_type"] = edit_type

    return JsonResponse(context)


def fetch_reports(request):
    if request.method == "POST":
        context = ResponseUtilities.get_view_impl_error_context("change HTTP method to GET",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    current_user_id = get_member_id_from_headers(request)
    # user_instance = User.objects.get(id=current_user_id)

    community_id = request.GET.get('community_id', None)
    api_key = RequestUtilities.get_api_key_from_headers(request)

    if not current_user_id:
        context = ResponseUtilities.get_view_impl_error_context("send member_id in headers",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])
    if not community_id and not api_key:
        context = ResponseUtilities.get_view_impl_error_context("send community_id in params or api_key in headers",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

    if not community_instance:
        context = ResponseUtilities.get_view_impl_error_context("invalid community_id or api_key",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_id = community_instance.id
    is_promoter = False
    is_owner = False
    has_right_0 = False  # right to delete chat rooms or conversations
    has_right_1 = False  # right to approve or reject pending requests
    has_right_2 = False  # right to edit community
    parent_cm_list = []

    member_instance = Members.objects.filter(community_id=community_id, member_id=current_user_id)

    if member_instance.exists():
        member = member_instance[0]
        is_owner = member.is_owner
        is_promoter = member.state == member_states.ADMIN
        has_right_0 = check_admin_delete_right(user=current_user_id, community=community_id)
        has_right_1 = check_admin_approve_right(user=current_user_id, community=community_id)
        has_right_2 = check_admin_edit_community_right(user=current_user_id, community=community_id)

        if member.parent_cm_list:
            parent_cm_list = json.loads(member.parent_cm_list)

    if not has_right_0 and not has_right_1 and has_right_2:
        # context = get_error_context(False, "user has no required rights to view reports")
        # return JsonResponse(context)
        return JsonResponse({"reports": []})

    elif not is_owner and not is_promoter:
        context = ResponseUtilities.get_view_impl_error_context("user has not Owner or CM",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    reports = get_related_reports_for_user(user_id=current_user_id, community_id=community_id, has_right_0=has_right_0,
                                           is_owner=is_owner, has_right_1=has_right_1, has_right_2=has_right_2,
                                           parent_cm_list=parent_cm_list)

    report_list = []

    for report in reports:
        report_dict = report_serializer(report, current_user_id)
        report_list.append(report_dict)

    return JsonResponse({"success": True, "reports": report_list})


@csrf_exempt
def close_report(request):
    """ function to approve a chatroom """
    if request.method == "GET":
        context = get_error_context(False, "change HTTP method to POST")
        return JsonResponse(context)

    current_user_id = get_member_id_from_headers(request)
    user_instance = User.objects.get(id=current_user_id)

    report_id = request.POST.get('report_id', None)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not report_id:
        context = get_error_context(False, "send report_id in params")
        return JsonResponse(context)

    Report.objects.filter(pk=report_id).update(is_closed=True, closed_by=user_instance, closed_time=time.time())
    update_report_count_for_all_promoters.delay(report_id=report_id)
    return JsonResponse({'success': True})


def fetch_pending_chatroom(request):
    """ function to fetch pending chatrooms """

    if request.method == "POST":
        context = get_error_context(False, "change HTTP method to GET")
        return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

    current_user_id = get_member_id_from_headers(request)
    user_instance = ModelUtilities.get_user_instance_or_none(current_user_id)

    if not user_instance:
        context = ResponseUtilities.get_view_impl_error_context('Invalid member id',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    community_id = request.GET.get('community_id', None)
    api_key = RequestUtilities.get_api_key_from_headers(request)

    community_instance = validate_community_id_or_api_key(community_id, api_key)

    if community_instance.get('error_message'):
        context = ResponseUtilities.get_view_impl_error_context(community_instance.get('error_message'),
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    community_instance = community_instance.get('community_instance')
    community_id = community_instance.id

    member_instance = Members.objects.filter(community_id=community_id, member_id=current_user_id,
                                             state=member_states.ADMIN)
    if member_instance.exists():
        has_right_0 = check_admin_delete_right(user=current_user_id, community=community_id)

        if not has_right_0:
            context = ResponseUtilities.get_view_impl_error_context('You doesnt have required right to view pending '
                                                                    'chat rooms', status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(**context)

    else:
        context = ResponseUtilities.get_view_impl_error_context('You are not a CM of this community',
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    pending_chatrooms = Collabcard.objects.filter(community=community_id, is_pending=True,
                                                  is_deleted=False).order_by('id')

    chatrooms = []

    for chatroom in pending_chatrooms:
        chatroom_instance = get_chatroom_instance(chatroom, current_user_id)
        chatrooms.append(chatroom_instance)

    context = {
        'success': True,
        'chatrooms': chatrooms
    }

    return JsonResponse(context)


class ActionPendingChatroom(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(ActionPendingChatroom, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = get_error_context(False, "change HTTP method to POST")
        return JsonResponse(context, status=status_codes.HTTP_405_METHOD_NOT_ALLOWED)

    def post(self, request, *args, **kwargs):

        current_user_id = RequestUtilities.get_member_id_from_headers(request)

        chatroom_id = request.POST.get('chatroom_id', None)
        value = request.POST.get('value', False)
        pre_approve = request.POST.get('pre_approve', None)

        user_instance = ModelUtilities.get_user_instance_or_none(current_user_id)

        if not user_instance:
            context = ResponseUtilities.get_view_impl_error_context('Invalid member id',
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(**context)

        chatroom = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not chatroom:
            context = ResponseUtilities.get_view_impl_error_context('Invalid chatroom id',
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(**context)

        community_instance = chatroom.community
        chatroom_creator = chatroom.user
        has_right_approve = check_admin_approve_right(user=current_user_id, community=community_instance)

        if not has_right_approve:
            context = ResponseUtilities.get_view_impl_error_context('You dont have right to approve.',
                                                                    status_codes.HTTP_400_BAD_REQUEST)

            return JsonResponse(**context)

        is_approved = (value == "true" or value is True)

        if is_approved:
            # creating  a copy of existing model and saving it
            chatroom.pk = None
            chatroom.id = None
            chatroom.is_pending = False
            chatroom.date_epoch = time.time()
            chatroom.save()
            # force refresh the object to get the new created object's' id
            chatroom.refresh_from_db()

            func_dict = {
                'member_id': chatroom.user_id,
                'collabcard_id': chatroom.id,
                'status': True,
                'source': "create_chatroom"
            }
            collabcard_follow_internal(func_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

            update_last_answer_id(chatroom.id, "")

            # creating a chatroom for the collabcard posted
            create_chatroom(card_instance=chatroom, user_instance=chatroom.user,
                            state=conversation_states.CONVERSATION_HEADER, current_user_id=chatroom.user.id)

            # batch update for already existing users and saving their unseen count
            set_chatroom_state_for_all_members_on_card_creation.delay(chatroom.community.id, card_id=chatroom.id,
                                                                      function_called="action_pending_chatroom")

        else:
            snackbar_manager = SnackbarImpl()
            snackbar_dict = {
                'user_id': chatroom_creator.id,
                'type': HomeSnackbarType.CHATROOM_REJECTED_BY_COMMUNITY_MANAGER
            }
            snackbar_manager.create_snackbar(snackbar_dict)

        send_notification_for_pending_chatroom_approved_or_rejected.delay(chatroom.id, is_approved=is_approved)
        # adding pending chatroom files to new chatroom
        CollabcardPolls.objects.filter(card__id=chatroom_id).update(card=chatroom)
        # adding pending chatroom files to new chatroom
        Card_Attachment.objects.filter(collabcard__id=chatroom_id).update(collabcard=chatroom)
        # deleting the old instance even if value = true or false
        Collabcard.objects.filter(pk=chatroom_id).delete()

        update_pending_chatroom_count_for_promoters.delay(community_instance.id)

        # checking is_owner bcz, owner will be by default a CM
        member_is_promoter = Members.objects.filter(community_id=community_instance,
                                                    member_id=chatroom_creator,
                                                    state=member_states.ADMIN).exists()

        if pre_approve is not None and \
                not member_is_promoter:

            current_user_instance = User.objects.get(pk=current_user_id)

            if pre_approve == "true" or \
                    pre_approve is True:

                give_member_auto_approve_right(user=chatroom_creator, community=community_instance,
                                               current_user_instance=current_user_instance)
                update_rights_history_for_creation_rights_given.delay(current_user_id,
                                                                      community_instance.id,
                                                                      chatroom_creator.id)
            else:
                remove_member_create_room_right(user=chatroom_creator, community=community_instance,
                                                current_user_id=current_user_id)
                update_rights_history_for_creation_rights_removed.delay(current_user_id,
                                                                        community_instance.id,
                                                                        chatroom_creator.id)
            save_moderation_history(user=chatroom_creator, community=community_instance,
                                    moderation_by=current_user_instance,
                                    type=moderation_history_types.MEMBER_PERMISSION_EDITED)

        info_logger.info(
            f"ACTION_PENDING_CHATROOM - current user id = {current_user_id}, card creator id = {chatroom_creator.id}, disallow_create_chatroom = {pre_approve},"
            f"card id = {chatroom_id}, community id = {community_instance.id}")

        return JsonResponse({'success': True})


def fetch_management_tools(request):
    if request.method == "POST":
        context = ResponseUtilities.get_view_impl_error_context("change HTTP method to GET",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    current_user_id = get_member_id_from_headers(request)
    # user_instance = User.objects.get(id=current_user_id)
    platform_code = RequestUtilities.get_platform_code(request)
    is_platform_web = RequestUtilities.is_request_web(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    community_id = request.GET.get('community_id', None)
    api_key = RequestUtilities.get_api_key_from_headers(request)

    if not current_user_id:
        context = ResponseUtilities.get_view_impl_error_context("send member_id in headers",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])
    if not community_id and not api_key:
        context = ResponseUtilities.get_view_impl_error_context("send community_id in params or api_key in headers",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

    if not community_instance:
        context = ResponseUtilities.get_view_impl_error_context("invalid community_id or api_key",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_id = community_instance.id
    is_promoter = False
    is_owner = False
    has_right_0 = False  # right to delete chat rooms or conversations
    has_right_1 = False  # right to approve or reject pending requests
    has_right_2 = False  # right to edit community
    parent_cm_list = []
    member_instance = Members.objects.filter(community_id=community_id,
                                             member_id=current_user_id, state=member_states.ADMIN)

    if member_instance.exists():
        member = member_instance[0]
        is_owner = member.is_owner
        is_promoter = member.state == member_states.ADMIN
        has_right_0 = check_admin_delete_right(user=current_user_id, community=community_id)
        has_right_1 = check_admin_approve_right(user=current_user_id, community=community_id)
        has_right_2 = check_admin_edit_community_right(user=current_user_id, community=community_id)

        if member.parent_cm_list:
            parent_cm_list = json.loads(member.parent_cm_list)

    else:
        context = ResponseUtilities.get_view_impl_error_context("you are not CM for this community",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(context['data'], status=context['status'])

    community_name = community_instance.name
    header = MANAGEMENT_TOOLS_HEADER.format(community_name)
    management_tools = []

    tools = {
        "success": True,
        "header": header,
        "management_tools": management_tools}

    if not has_right_0 and not has_right_1 and not has_right_2:
        return JsonResponse(tools, status=status_codes.HTTP_200_OK)

    # cause to do this multiple duplicate checks is to send lkst in tool order as per design
    if has_right_1:
        member_request_tool = get_tool_member_requests(user_id=current_user_id, community_id=community_id)

        member_request_tool["route"] = MEMBER_REQUEST_TOOL_ROUTE.format(community_id, community_name)

        management_tools.append(member_request_tool)

    if has_right_0:
        pending_chatrooms_tool = get_tool_pending_chat_rooms(user_id=current_user_id, community_id=community_id)
        pending_chatrooms_tool["route"] = PENDING_CHATROOM_TOOL_ROUTE.format(community_id, community_name)
        management_tools.append(pending_chatrooms_tool)

    if has_right_0 or has_right_1:
        reports_tool = get_tool_review_reports(user_id=current_user_id, community_id=community_id,
                                               has_right_0=has_right_0, has_right_1=has_right_1,
                                               has_right_2=has_right_2, parent_cm_list=parent_cm_list,
                                               is_owner=is_owner)
        reports_tool["route"] = REPORTS_TOOL_ROUTE.format(community_id, community_name)
        management_tools.append(reports_tool)

    if has_right_2:
        tool_edit_directory_question = tool_edit_directory_questions.copy()
        tool_edit_community_detail = tool_edit_community_details.copy()

        if directory_questions_v2_version_check(platform_code, version_code):
            tool_edit_directory_question['title'] = DIRECTORY_QUESTIONS_MANAGEMENT_TOOLS_TITLE

        tool_edit_directory_question["route"] = tool_edit_directory_question["route"].format(community_id,
                                                                                             community_name)
        tool_edit_community_detail["route"] = tool_edit_community_detail["route"].format(community_id, community_name)

        if has_right_1:
            management_tools.append(tool_edit_directory_question)
        management_tools.append(tool_edit_community_detail)

    if is_platform_web and (version_code >= CM_ONBOARDING_WEB_VERSION_CODE):
        tool_membership_plans = MEMBERSHIP_PLANS_MANAGEMENT_TOOLS.copy()
        tool_membership_plans['route'] = tool_membership_plans['route'].format(community_id)

        management_tools.append(tool_membership_plans)

    if has_right_0 or has_right_1:
        tool_community_setting = tool_community_settings.copy()
        tool_community_setting["route"] = tool_community_setting["route"].format(community_id, community_name)
        management_tools.append(tool_community_setting)

    return JsonResponse(tools, status=status_codes.HTTP_200_OK)


def fetch_community_setting_rights(request):
    """ function to fetch community setting rights """

    if request.method == 'POST':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to GET'})

    current_user_id = get_member_id_from_headers(request)
    community_id = request.GET.get('community_id', None)
    user_id = request.GET.get('user_id', None)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    can_show = False

    if m2cm_v1_version_check(platform_code, version_code):
        can_show = True

    is_m2cm_v2 = m2cm_v2_version_check(platform_code, version_code)

    if is_m2cm_v2:
        can_show = False

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in params")
        return JsonResponse(context)

    community_instance = Community.get_community_or_None(community_id)
    if community_instance is None:
        context = get_error_context(False, f"Invalid community_id {community_id}")
        return JsonResponse(context)

    current_user_instance = User.get_user_or_none(current_user_id)
    if current_user_instance is None:
        context = get_error_context(False, f"Invalid user_id {user_id} in headers")
        return JsonResponse(context)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing
    # checking if the logged in user is Manager of the community or not
    if admin.exists():
        user_rights = check_all_member_rights(community=community_instance, is_m2cm_v2=is_m2cm_v2)
        # fetching all the rights of the community
        rights_context = get_saved_member_rights_list(user_rights, show_dm_right=can_show, is_m2cm_v2=is_m2cm_v2)
        return JsonResponse({"rights": rights_context})
    else:
        context = get_error_context(False, "user is not a admin")
        return JsonResponse(context)


@csrf_exempt
def update_community_rights(request):
    """ function to save the community setting rights """
    if request.method == 'GET':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'})

    current_user_id = get_member_id_from_headers(request)
    req_body = json.loads(request.body)
    community_id = req_body['community_id'] if "community_id" in req_body else None
    selected_rights = req_body['rights'] if "rights" in req_body else None
    api_key = RequestUtilities.get_api_key_from_headers(request)

    if not current_user_id:
        context = ResponseUtilities.get_view_impl_error_context("Send member_id in headers",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    if not community_id and not api_key:
        context = ResponseUtilities.get_view_impl_error_context("Invalid community_id or api_key",
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    community_dict = validate_community_id_or_api_key(community_id, api_key)

    if community_dict.get('error_message'):
        context = ResponseUtilities.get_view_impl_error_context(community_dict.get('error_message'),
                                                                status_codes.HTTP_400_BAD_REQUEST)
        return JsonResponse(**context)

    community_instance = community_dict.get('community_instance')
    community_id = community_instance.id

    current_user_instance = ModelUtilities.get_user_instance_or_none(current_user_id)

    admin = Members.objects.filter(member_id=current_user_instance, community_id=community_instance,
                                   state=member_states.ADMIN)

    # checking if the logged in user is Manager of the community or not
    if admin.exists():

        if selected_rights is None:
            all_rights = memberRights.objects.all()
            for right in all_rights:
                # if right is removed, the right is disabled for all the members
                communityRightsSettings.objects.filter(community=community_instance, right=right).delete()
                remove_right_for_all_members(community=community_instance, right=right)

            return JsonResponse({'success': True})

        existing_rights = set(
            communityRightsSettings.objects.filter(community=community_instance).values_list("right__id", flat=True))
        rights_added, removed_rights = get_added_and_removed_rights(selected_rights=selected_rights,
                                                                    existing_rights=existing_rights)

        for right_id in rights_added:
            # if right is added, the right is given to all the members
            try:
                right = memberRights.objects.get(pk=right_id)
                communityRightsSettings(community=community_instance, right=right).save()
                give_right_to_all_members(community=community_instance, right=right)

                if all([right.state == member_rights.MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES,
                        right.title == member_rights.MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES_TITLE]):

                    filter_dict = {
                        "community": community_instance,
                        "setting_type": community_setting_types.DIRECT_MESSAGES
                    }
                    update_dict = {
                        'setting_sub_title': DM_COMMUNITY_SETTING_SUB_TITLE_WHEN_ENABLED,
                        'enabled': True,
                        'updated_at': TimeUtilities.current_time_in_milliseconds(),
                        'enabled_by': current_user_instance
                    }

                    ModelUtilities.model_update(CommunitySettings, filter_dict, update_dict)
            except:
                error_logger.error("rights already exists for commnunity {community_id} in community settings")

        for right_id in removed_rights:
            # if right is removed, the right is disabled for all the members
            right = memberRights.objects.get(pk=right_id)
            communityRightsSettings.objects.filter(community=community_instance, right=right).delete()
            remove_right_for_all_members(community=community_instance, right=right)

            if all([right.state == member_rights.MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES,
                    right.title == member_rights.MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES_TITLE]):

                filter_dict = {
                    "community": community_instance,
                    "setting_type": community_setting_types.DIRECT_MESSAGES
                }

                update_dict = {
                    'setting_sub_title': COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING.get(
                        community_setting_types.DIRECT_MESSAGES),
                    'enabled': False,
                    'updated_at': TimeUtilities.current_time_in_milliseconds(),
                    'enabled_by': None
                }

                ModelUtilities.model_update(CommunitySettings, filter_dict, update_dict)

        info_logger.info(
            f"UPDATING_COMMUNITY_SETTINGS - current user id = {current_user_id}"
            f"community id = {community_id}")

        update_member_rights_list_for_community_members.delay(community_id)

        return JsonResponse({'success': True})
    else:
        context = get_error_context(False, "user is not a admin")
        return JsonResponse(context)


@csrf_exempt
def block_member(request):
    """ function to block member in community """
    if request.method == 'GET':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'})

    current_user_id = get_member_id_from_headers(request)
    community_id = request.POST.get('community_id', None)
    blocked_user_id = request.POST.get('user_id', None)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not blocked_user_id:
        context = get_error_context(False, "send user_id in POST params")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in POST params")
        return JsonResponse(context)

    community_instance = Community.objects.get(pk=community_id)
    current_user_instance = User.objects.get(pk=current_user_id)
    blocked_user_instance = User.objects.get(pk=blocked_user_id)

    try:
        # saving in DB
        blockedMembers(blocked_by=current_user_instance,
                       blocked_member=blocked_user_instance, community=community_instance).save()
    except:
        # a member can be blocked only once in a community
        info_logger.info("member already blocked by this user")

    return JsonResponse({'success': True})


############################## client db synching apis #################################################


class SyncChatrooms(APIView):

    def get(self, request, *args, **kwargs):

        member_id = get_member_id_from_headers(request)
        user_instance = ModelUtilities.get_user_instance_or_none(member_id)

        if not user_instance:
            context = ResponseUtilities.get_view_impl_error_context('Invalid member id',
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(**context)

        device_id = RequestUtilities.get_device_id_from_headers(request)

        version_code = RequestUtilities.get_version_code_from_headers(request)
        platform_code = RequestUtilities.get_platform_code(request)

        can_add_dm_chatrooms = False

        if m2cm_v1_version_check(platform_code, version_code):
            can_add_dm_chatrooms = True

        query_params = request.query_params

        page = RequestUtilities.get_page_number(request)
        paginate_by = RequestUtilities.get_page_size(request, default=200)
        last_updated = RequestUtilities.get_page_size(request, key='last_updated', default=0)

        chatroom_id = query_params.get('chatroom_id', '')
        community_id = query_params.get('community_id', '')
        chatroom_status = query_params.get('chatroom_status', '')
        chatroom_type = query_params.get('type')
        draft = query_params.get('draft', '')

        if not chatroom_type:
            type_list = [
                card_types.CARD_POLL,
                card_types.CARD_PURPOSE,
                card_types.CARD_EVENT,
                card_types.CARD_PUBLIC_EVENT,
                card_types.CARD_MASTER_INTRO,
                card_types.CARD_NORMAL,
                card_types.CARD_INTRO,
                card_types.CARD_DIRECT_MESSAGE
            ]
        else:

            type_list = [chatroom_type]

        if draft and draft == "true":
            draft_response = self._get_draft_chatrooms(member_id, last_updated, page, paginate_by)
            draft_response['success'] = True
            return JsonResponse(draft_response)

        if chatroom_id:

            collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState,
                                                                      {'card': chatroom_id, 'user': member_id})

            if collabcard_state_filter.exists():

                expired_member_remove_ids = list(ModelUtilities.get_model_filter(
                    removedMembers, {'community': collabcard_state_filter[0].community, 'member': member_id,
                                     'removed_state__in': [deleted_members.LEFT,
                                                           deleted_members.MEMBERSHIP_EXPIRED]}).values_list('id',
                                                                                                             flat=True))

                chatroom_data, chatroom_id_list = fetch_chatroom_id_query(chatroom_id, member_id,
                                                                          last_updated=last_updated,
                                                                          expired_member_ids=expired_member_remove_ids)
            else:
                chatroom = get_chatroom_data_in_case_of_guest(chatroom_id, member_id)

                return JsonResponse({'success': True, 'chatrooms': chatroom})

        elif community_id:

            follow_status = chatroom_status == "followed"
            chatroom_data, chatroom_id_list = fetch_community_chatroom_query(community_id, member_id, page,
                                                                             paginate_by,
                                                                             last_updated,
                                                                             follow_status=follow_status,
                                                                             type_list=type_list)
        else:
            chatroom_data, chatroom_id_list = get_user_related_chatrooms(member_id, paginate_by, page, last_updated,
                                                                         chatroom_status, type_list)
        
        poll_data = {}
        poll_votes = {}

        if chatroom_id_list:
            poll_data = fetch_chatroom_polls(chatroom_id_list)
            poll_votes = fetch_member_poll_votes(chatroom_id_list)

        event_chatroom_ids = get_event_chatroom_id_list(chatroom_data)

        from .chatroom.chatroom_impl import ChatroomHelper
        event_chatroom_dict = ChatroomHelper.pre_compute_chatroom_instances_from_chatroom_list(event_chatroom_ids)

        chatrooms = []

        # Get Chatroom IDs
        chatroom_ids_list = [data[0] for data in chatroom_data]

        # Pre-compute cohort data
        cohort_member_map = self.fetch_cohort_members_for_chatroom_list(chatroom_ids_list)

        # Pre-compute event recordings data
        chatroom_event_recordings_mapper = ChatroomHelper.fetch_event_recordings_and_event_urls_for_chatroom_list(
            user_instance,
            chatroom_ids_list)

        max_last_updated = 0
        for data in chatroom_data:

            attachment_count = data[45]
            attachments_uploaded = data[46]

            if attachment_count > 0 and \
                    attachments_uploaded is False and \
                    (int(member_id) != int(data[14]) or data[51] != device_id):
                continue

            chatroom = {}
            chatroom['id'] = data[0]
            chatroom['title'] = data[1]
            chatroom['community_id'] = data[2]
            chatroom['answer_text'] = data[3]
            chatroom['image_count'] = data[4]
            chatroom['pdf_count'] = data[5]
            chatroom['video_count'] = data[6]
            chatroom['audio_count'] = data[7]
            chatroom['attachment_count'] = attachment_count
            chatroom['attachments_uploaded'] = attachments_uploaded
            chatroom['type'] = data[8]
            chatroom['date_time'] = data[9]
            chatroom['is_pending'] = data[10]
            chatroom['attending_count'] = data[11]
            chatroom['polls_count'] = data[12]
            chatroom['date_epoch'] = data[13]
            chatroom['card_creation_time'] = time.strftime('%I:%M %p', time.localtime(chatroom['date_epoch']))
            chatroom['created_at'] = time.strftime('%H:%M', time.localtime(chatroom['date_epoch']))
            chatroom['date'] = time.strftime('%d %b %Y', time.localtime(chatroom['date_epoch']))
            chatroom['member_id'] = data[14]

            if member_id and chatroom['member_id'] == int(member_id):
                chatroom['has_been_named'] = data[15]

            chatroom['header'] = self._get_header(data[16], chatroom['title'])

            chatroom['state'] = data[17]
            chatroom['mute_status'] = data[18]
            chatroom['follow_status'] = data[19]
            chatroom['access_without_subscription'] = data[20]
            chatroom['is_tagged'] = data[21]

            if data[22]:
                chatroom['last_seen_conversation'] = data[22]

            chatroom['attending_status'] = data[24]

            has_files = data[25] or chatroom['pdf_count'] > 0 or chatroom['attachment_count'] > 0

            chatroom_files = self._get_chatroom_files(chatroom['id'], has_files)
            chatroom['images'] = chatroom_files['images']
            chatroom['pdf'] = chatroom_files['pdf']
            chatroom['audios'] = chatroom_files['audios']
            chatroom['videos'] = chatroom_files['videos']
            chatroom['attachments'] = chatroom_files['attachments']

            if chatroom['type'] == card_types.CARD_POLL:

                chatroom['is_poll_anonymous'] = data[26]
                chatroom['allow_add_option'] = data[27]
                if data[28] is not None:
                    chatroom['multiple_select_state'] = data[28]
                if data[29]:
                    chatroom['multiple_select_no'] = data[29]
                chatroom['is_anonymous'] = data[30]
                chatroom['poll_type'] = data[31]
                chatroom['poll_type_text'] = "Instant poll" if chatroom[
                                                                   'poll_type'] == poll_types.POLL_TYPE_INSTANT else "Deferred poll"
                chatroom['submit_type_text'] = "Secret voting" if chatroom['is_poll_anonymous'] else "Public voting"

                polls = self._get_polls_v1(poll_data, chatroom['id'], poll_votes, data[29], member_id)
                if polls:
                    from collabmates_api.chatroom_member.chatroom_member_impl import ChatroomMemberHelper
                    chatroom['to_show_results'] = ChatroomMemberHelper.get_to_show_results(chatroom['id'], member_id,
                                                                                           poll_votes)
                    chatroom['polls'] = polls

            if chatroom['type'] == card_types.CARD_EVENT or chatroom['type'] == card_types.CARD_PUBLIC_EVENT:

                if data[59] not in [event_access.COMMUNITY_MEMBERS, event_access.NON_COMMUNITY_USERS_AND_MEMBERS]:

                    chatroom_instance = event_chatroom_dict.get(chatroom['id'])

                    if not chatroom_instance:
                        continue

                    is_promoter = Members.is_member_community_promoter(chatroom_instance.community, user_instance)

                    if not is_promoter:
                        from collabmates_api.cohort.cohort_impl import CohortHelper

                        has_event_access = CohortHelper.check_if_user_is_member_of_chatroom_related_cohort(
                            chatroom_instance,
                            user_instance
                        )

                        if not has_event_access:
                            continue

                self._fill_event_related_details(chatroom, data)

            if data[36]:
                chatroom['og_tags'] = json.loads(data[36])

            if data[37]:
                try:
                    preview = get_preview_for_url(member_id=member_id,
                                                  preview_url=data[37],
                                                  send_preview_text=False)
                    if preview:
                        chatroom['preview'] = preview

                except Exception as e:
                    error_logger.error(f'{e.args}')

            if data[38]:
                chatroom['deleted_by'] = data[38]

            if max_last_updated < data[39]:
                max_last_updated = data[39]

            chatroom['community_name'] = data[40]

            chatroom['is_secret'] = data[47]

            if chatroom['is_secret']:
                chatroom['secret_chatroom_participants'] = json.loads(data[48])

            chatroom['secret_chatroom_left'] = data[49]

            # data[50] = has_reactions
            if data[50]:
                reactions = fetch_chatroom_or_conversation_reactions(chatroom_id=chatroom['id'])
            else:
                reactions = []

            chatroom['auto_follow_done'] = data[53]

            chatroom['reactions'] = reactions if reactions else []

            # chatroom topic
            if data[52]:
                chatroom['topic_id'] = data[52]

            chatroom['is_edited'] = data[54]

            chatroom['is_private'] = data[64]

            if data[65]:
                chatroom["chatroom_with_user_id"] = data[65]

            chatroom["member_can_message"] = data[66]

            chatroom["external_seen"] = data[67]

            chatroom["online_link_type"] = data[68]
            chatroom["is_private_member"] = data[69]

            if chatroom['is_private'] and not can_add_dm_chatrooms:
                continue

            if chatroom['is_private_member'] and not m2cm_v2_version_check(platform_code, version_code):
                continue

            if data[70] is not None:
                chatroom["chat_request_state"] = data[70]

            if data[71]:
                chatroom["chat_requested_by_id"] = data[71]

            if data[72]:
                chatroom["chat_request_created_at"] = data[72]

            if data[73]:
                chatroom["chatroom_image_url"] = data[73]

            chatroom['unread_messages'] = fetch_conversations_unread(data[0], member_id)

            chatroom['cohorts'] = cohort_member_map.get(data[0], [])

            from collabmates_api.cohort.cohort_impl import CohortHelper

            cohort_access = CohortHelper.fetch_cohort_access_for_chatroom(data[0], member_id)

            if cohort_access is not None:
                chatroom['cohort_access'] = cohort_access

            event_recordings_data = chatroom_event_recordings_mapper.get(data[0], {})

            chatroom.update(event_recordings_data)

            chatrooms.append(chatroom)

        if max_last_updated:
            return JsonResponse({'success': True, 'chatrooms': chatrooms, 'max_last_updated': max_last_updated})

        return JsonResponse({'success': True, 'chatrooms': chatrooms})

    def _get_header(self, header, title):

        if header:
            return header

        if len(title) <= 30:
            return title[:30]

        return title[:27] + "..."

    def _get_chatroom_files(self, chatroom_id, has_files):

        files = {
            'images': [],
            'pdf': [],
            'audios': [],
            'videos': [],
            'voice_notes': []
        }

        attachments = []

        if has_files:
            files_filter = Card_Attachment.objects.filter(collabcard=chatroom_id).order_by('id')

            for file in files_filter:

                if file.type == "image":
                    img = {'image_url': file.file_url, 'index': file.index, 'type': file.type}
                    img_attachment = {'url': file.file_url, 'index': file.index, 'type': file.type}

                    if file.height:
                        img['height'] = file.height
                        img_attachment['height'] = file.height

                    if file.width:
                        img['width'] = file.width
                        img_attachment['width'] = file.width

                    if file.thumbnail_url:
                        img['thumbnail_url'] = file.thumbnail_url
                        img_attachment['thumbnail_url'] = file.thumbnail_url

                    if file.name:
                        img['name'] = file.name
                        img_attachment['name'] = file.name

                    if file.meta:
                        file_meta = JsonUtilities.load_json_data(file.meta)

                        if file_meta:
                            img['meta'] = file_meta
                            img_attachment['meta'] = file_meta

                    files['images'].append(img)
                    attachments.append(img_attachment)

                elif file.type == "pdf":
                    pdf = {'pdf_file': file.file_url, 'index': file.index, 'type': file.type}
                    pdf_attachment = {'url': file.file_url, 'index': file.index, 'type': file.type}

                    if file.height:
                        pdf['height'] = file.height
                        pdf_attachment['height'] = file.height

                    if file.width:
                        pdf['width'] = file.width
                        pdf_attachment['width'] = file.width

                    if file.thumbnail_url:
                        pdf['thumbnail_url'] = file.thumbnail_url
                        pdf_attachment['thumbnail_url'] = file.thumbnail_url

                    if file.name:
                        pdf['name'] = file.name
                        pdf_attachment['name'] = file.name

                    if file.meta:
                        file_meta = JsonUtilities.load_json_data(file.meta)

                        if file_meta:
                            pdf['meta'] = file_meta
                            pdf_attachment['meta'] = file_meta

                    files['pdf'].append(pdf)
                    attachments.append(pdf_attachment)

                elif file.type == "audio":
                    audio_file_attachment = {'url': file.file_url, 'index': file.index, 'type': file.type}

                    if file.height:
                        audio_file_attachment['height'] = file.height

                    if file.width:
                        audio_file_attachment['width'] = file.width

                    if file.name:
                        audio_file_attachment['name'] = file.name

                    if file.meta:
                        file_meta = JsonUtilities.load_json_data(file.meta)

                        if file_meta:
                            audio_file_attachment['meta'] = file_meta

                    if file.thumbnail_url:
                        audio_file_attachment['thumbnail_url'] = file.thumbnail_url

                    attachments.append(audio_file_attachment)

                elif file.type == "video":
                    video_file = {'video_url': file.file_url, 'index': file.index, 'type': file.type}
                    video_attachment = {'url': file.file_url, 'index': file.index, 'type': file.type}

                    if file.height:
                        video_file['height'] = file.height
                        video_attachment['height'] = file.height

                    if file.width:
                        video_file['width'] = file.width
                        video_attachment['width'] = file.width

                    if file.thumbnail_url:
                        video_file['thumbnail_url'] = file.thumbnail_url
                        video_attachment['thumbnail_url'] = file.thumbnail_url

                    if file.name:
                        video_file['name'] = file.name
                        video_attachment['name'] = file.name

                    if file.meta:
                        file_meta = JsonUtilities.load_json_data(file.meta)

                        if file_meta:
                            video_file['meta'] = file_meta
                            video_attachment['meta'] = file_meta

                    files['videos'].append(video_file)
                    attachments.append(video_attachment)

                elif file.type == "voice_note":
                    voice_note_attachment = {'url': file.file_url, 'index': file.index, 'type': file.type}

                    if file.height:
                        voice_note_attachment['height'] = file.height

                    if file.width:
                        voice_note_attachment['width'] = file.width

                    if file.thumbnail_url:
                        voice_note_attachment['thumbnail_url'] = file.thumbnail_url

                    if file.name:
                        voice_note_attachment['name'] = file.name

                    if file.meta:
                        file_meta = JsonUtilities.load_json_data(file.meta)

                        if file_meta:
                            voice_note_attachment['meta'] = file_meta

                    attachments.append(voice_note_attachment)

        files['attachments'] = attachments

        return files

    def _get_polls_v1(self, poll_data, chatroom_id, poll_votes, is_multi, member_id):

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
            temp['no_votes'] = 0
            temp['percentage'] = 0

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

            if total_votes != 0:
                temp['no_votes'] = count
                temp['percentage'] = int((count / total_votes) * 100)

            polls.append(temp)

        return polls

    def _get_co_hosts(self, co_hosts):

        co_hosts = json.loads(co_hosts)
        co_host_list = []
        for member in co_hosts:
            temp = {}
            temp['id'] = member
            co_host_list.append(temp)

        return co_host_list

    def _get_draft_chatrooms(self, member_id, last_updated, page, paginate_by):

        draft_response = {'chatrooms': []}

        if last_updated:
            draft_filter = draftChatroom.objects.filter(date_epoch__gt=last_updated, user=member_id).order_by('id')
        else:
            draft_filter = draftChatroom.objects.filter(user=member_id).order_by('id')

        draft_filter = pagination(draft_filter, page, paginate_by=paginate_by)
        max_last_updated, chatrooms = fill_draft_chatrooms(draft_filter, member_id)

        if max_last_updated:
            draft_response = {'chatrooms': chatrooms, 'max_last_updated': max_last_updated}

        return draft_response

    def _fill_event_related_details(self, chatroom, data):

        chatroom['is_paid'] = data[58]
        chatroom['access'] = data[59]
        chatroom['online_link_enable_before'] = data[55]

        if data[33]:
            chatroom['about'] = data[33]

        if data[34]:
            chatroom['co_hosts_id'] = self._get_co_hosts(data[34])

        if data[32]:
            chatroom['end_date'] = data[32]

        chatroom['duration'] = data[41]

        if data[42]:
            chatroom['location'] = data[42]
            chatroom['location_lat'] = data[43]
            chatroom['location_long'] = data[44]

        if data[60]:
            chatroom['event_payment_link'] = data[60]

        if data[61]:
            chatroom['event_web_page'] = data[61]

        chatroom['attended'] = data[62]
        chatroom['webflow_item_id'] = data[63]

        chatroom['instructors'] = self.fetch_event_instructors(chatroom['id'])
        chatroom['highlights'] = self.fetch_event_highlights(chatroom['id'])
        chatroom['testimonials'] = self.fetch_member_testimonials(chatroom['id'])
        chatroom['faq'] = self.fetch_event_FAQ(chatroom['id'])

        self._fill_event_attendees(chatroom)

    def _fill_event_attendees(self, chatroom):

        event_attendees_dict = CacheImpl.get_cache(EVENT_ATTENDEES_CHATROOM % str(chatroom['id']))

        if event_attendees_dict:
            event_attendees_list = event_attendees_dict.get('event_attendees_list', [])
            chatroom['attendees_ids'] = event_attendees_list

            return

        event_attendees_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                                    {'card': chatroom['id'],
                                                                     'attending_status': True}
                                                                    ).values_list('user', flat=True).
                                    order_by('created_at', 'id'))

        if event_attendees_list:
            update_event_attendees.delay({'chatroom_id': chatroom['id']})

        chatroom['attendees_ids'] = event_attendees_list

    def fetch_event_instructors(self, card_id):

        instructors_dict = CacheImpl.get_cache(EVENT_INSTRUCTORS_CHATROOM % str(card_id))

        if instructors_dict:

            instructors_list = instructors_dict.get('instructors_list', [])

        else:

            instructor_filter = ModelUtilities.get_model_filter(EventInstructor,
                                                                {'card': card_id}).order_by('id')

            instructors_list = EventInstructorSerializer(instructor_filter, many=True).data

            if instructors_list:
                update_event_instructors_in_cache.delay({'chatroom_id': card_id,
                                                        'instructors_list': instructors_list})

        return instructors_list

    def fetch_event_highlights(self, card_id):

        highlights_dict = CacheImpl.get_cache(EVENT_HIGHLIGHTS_CHATROOM % str(card_id))

        if highlights_dict:
            highlights_list = highlights_dict.get('highlights_list', [])

        else:

            highlights_filter = ModelUtilities.get_model_filter(EventHighlights,
                                                                {'card': card_id}).order_by('id')

            highlights_list = EventHighlightsSerializer(highlights_filter, many=True).data

            if highlights_list:
                update_event_highlights_in_cache.delay({'chatroom_id': card_id,
                                                        'highlights_list': highlights_list})

        return highlights_list

    def fetch_event_FAQ(self, card_id):

        faq_dict = CacheImpl.get_cache(EVENT_FAQ_CHATROOM % str(card_id))

        if faq_dict:
            faqs_list = faq_dict.get('faqs_list', [])

        else:

            faq_filter = ModelUtilities.get_model_filter(EventFAQ,
                                                         {'card': card_id}).order_by('id')

            faqs_list = EventFAQSerializer(faq_filter, many=True).data

            if faqs_list:
                update_event_faq_in_cache.delay({'chatroom_id': card_id, 'faqs_list': faqs_list})

        return faqs_list

    def fetch_member_testimonials(self, card_id):

        testimonial_dict = CacheImpl.get_cache(EVENT_MEMBERTESTIMONIALS_CHATROOM % str(card_id))

        if testimonial_dict:
            testimonials_list = testimonial_dict.get('testimonials_list', [])

        else:
            testimonial_filter = ModelUtilities.get_model_filter(EventMemberTestimonials,
                                                                 {'card': card_id}).order_by('id')

            testimonials_list = EventMemberTestimonialsSerializer(testimonial_filter, many=True).data

            if testimonials_list:
                update_event_member_testimonials_in_cache.delay({'chatroom_id': card_id,
                                                                'testimonials_list': testimonials_list})

        return testimonials_list

    def fetch_cohort_members_for_chatroom_list(self, chatroom_ids_list):
        cohort_chatroom_map = {}
        cohort_member_map = {}

        cohort_filter = ModelUtilities.get_model_filter(ChatroomCohort, {'chatroom_id__in': chatroom_ids_list})

        cohort_ids_list = list(set(cohort_filter.values_list('cohort_id', flat=True)))

        cohorts = ModelUtilities.get_model_filter(Cohort, {'id__in': cohort_ids_list})

        cohort_member_context = []

        for cohort in cohorts:
            cohort_context = {
                'cohort_id': cohort.id,
                'name': cohort.name,
                'community_id': cohort.community_id,
                'total_members': ModelUtilities.get_model_filter(CohortMember, {'cohort_id': cohort.id}).count()
            }
            cohort_member_context.append(cohort_context)

        cohort_filter = cohort_filter.values('chatroom_id', 'cohort_id')

        for cohort_member_obj in cohort_member_context:
            if cohort_member_obj['cohort_id'] not in cohort_member_map:
                cohort_member_map[cohort_member_obj['cohort_id']] = [cohort_member_obj]

            else:
                cohort_member_map[cohort_member_obj['cohort_id']].append(cohort_member_obj)

        for cohort_object in cohort_filter:

            if cohort_object['chatroom_id'] not in cohort_chatroom_map:
                cohort_chatroom_map[cohort_object['chatroom_id']] = cohort_member_map[cohort_object['cohort_id']] \
                    if cohort_object['cohort_id'] in cohort_member_map else []

            else:
                cohort_chatroom_map[cohort_object['chatroom_id']] += cohort_member_map[cohort_object['cohort_id']] if \
                    cohort_object['cohort_id'] in cohort_member_map else []

        return cohort_chatroom_map


class SyncChatroomsDiff(APIView):

    def get(self, request, *args, **kwargs):

        member_id = get_member_id_from_headers(request)

        if not member_id:
            context = ResponseUtilities.get_view_impl_error_context('Invalid member id',
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(**context)

        device_id = RequestUtilities.get_device_id_from_headers(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        query_params = request.query_params

        previous_app_version = query_params.get('previous_app_version', 0)
        previous_app_version = NumberUtilities.get_integer_from_string(previous_app_version)

        page = RequestUtilities.get_page_number(request)
        paginate_by = RequestUtilities.get_page_size(request, default=200)
        is_synced = query_params.get('is_synced', "false").lower() == 'true'

        chatrooms = []
        chatroom_data = []
        poll_data = {}
        poll_votes = {}

        attachment_chatroom_list = set()
        video_chatroom_list = set()
        secret_chatroom_list = set()
        chatrooms_with_reactions_list = set()
        chatrooms_with_topics_list = set()
        chatrooms_with_edited_list = set()

        if not is_synced:

            user_instance = ModelUtilities.get_user_instance_or_none(member_id)

            if not user_instance:
                return JsonResponse({'success': True, 'chatrooms': []})

            if previous_app_version < EVENT_ATTACHMENT_VERSION_CODE_AN <= version_code:
                attachment_chatroom_list = self._get_event_recordings_of_user(user_instance)

            if previous_app_version < VIDEO_SYNC_TRIGGER_VERSION_CODE_AN <= version_code:
                video_chatroom_list = self._get_video_chatrooms_of_user(user_instance)

            if previous_app_version < SECRET_CHATROOM_SYNC_TRIGGER_VERSION_CODE_AN <= version_code:
                secret_chatroom_list = self._get_secret_chatrooms_of_user(user_instance)

            if previous_app_version < REACTIONS_SYNC_TRIGGER_VERSION_CODE_AN <= version_code:
                chatrooms_with_reactions_list = self._get_chatrooms_with_reactions_of_user(user_instance)

            if previous_app_version < TOPIC_SYNC_TRIGGER_VERSION_CODE_AN <= version_code:
                chatrooms_with_topics_list = self._get_chatrooms_with_topics_of_user(user_instance)

            if previous_app_version < CHATROOM_FIRST_MESSAGE_ACTION_VERSION_CODE_ANDROID:
                chatrooms_with_edited_list = self._get_chatrooms_with_edited_first_message(user_instance)

        common_list = tuple(secret_chatroom_list | video_chatroom_list |
                            chatrooms_with_reactions_list | chatrooms_with_topics_list |
                            chatrooms_with_edited_list | attachment_chatroom_list)

        if len(common_list) > 0:
            poll_data = fetch_chatroom_polls(common_list)
            poll_votes = fetch_member_poll_votes(common_list)

            chatroom_data, chatroom_id_list = fetch_chatroom_with_videos(paginate_by, page, common_list)

        for data in chatroom_data:

            attachment_count = data[45]
            attachments_uploaded = data[46]

            if attachment_count > 0 and \
                    attachments_uploaded is False and \
                    (int(member_id) != int(data[14]) or data[51] != device_id):
                continue

            chatroom = {}
            chatroom['id'] = data[0]
            chatroom['title'] = data[1]
            chatroom['community_id'] = data[2]
            chatroom['answer_text'] = data[3]
            chatroom['image_count'] = data[4]
            chatroom['pdf_count'] = data[5]
            chatroom['video_count'] = data[6]
            chatroom['audio_count'] = data[7]
            chatroom['attachment_count'] = attachment_count
            chatroom['attachments_uploaded'] = attachments_uploaded
            chatroom['type'] = data[8]
            chatroom['date_time'] = data[9]
            chatroom['is_pending'] = data[10]
            chatroom['attending_count'] = data[11]
            chatroom['polls_count'] = data[12]
            chatroom['date_epoch'] = data[13]
            chatroom['card_creation_time'] = time.strftime('%I:%M %p', time.localtime(chatroom['date_epoch']))
            chatroom['created_at'] = time.strftime('%H:%M', time.localtime(chatroom['date_epoch']))
            chatroom['date'] = time.strftime('%d %b %Y', time.localtime(chatroom['date_epoch']))
            chatroom['member_id'] = data[14]

            if member_id and chatroom['member_id'] == int(member_id):
                chatroom['has_been_named'] = data[15]

            chatroom['header'] = self._get_header(data[16], chatroom['title'])

            chatroom['state'] = data[17]
            chatroom['mute_status'] = data[18]
            chatroom['follow_status'] = data[19]
            chatroom['is_guest'] = data[20]
            chatroom['is_tagged'] = data[21]

            if data[22]:
                chatroom['last_seen_conversation'] = data[22]

            chatroom['attending_status'] = data[24]

            self._add_attachements(chatroom, data)

            self._add_poll_data(chatroom, data, poll_data, poll_votes, member_id)
            self._add_event_data(chatroom, data)

            if data[36]:
                chatroom['og_tags'] = json.loads(data[36])

            if data[37]:
                try:
                    preview = get_preview_for_url(member_id=member_id,
                                                  preview_url=data[37],
                                                  send_preview_text=False)
                    if preview:
                        chatroom['preview'] = preview

                except Exception as e:
                    error_logger.error(f'{e.args}')

            if data[38]:
                chatroom['deleted_by'] = data[38]

            chatroom['community_name'] = data[40]

            chatroom['is_secret'] = data[47]

            if chatroom['is_secret']:
                chatroom['secret_chatroom_participants'] = json.loads(data[48])

            chatroom['secret_chatroom_left'] = data[49]

            # has reactions
            if data[50]:
                reactions = fetch_chatroom_or_conversation_reactions(chatroom_id=chatroom['id'])
            else:
                reactions = []

            chatroom['reactions'] = reactions if reactions else []

            # chatroom topic
            if data[52]:
                chatroom['topic_id'] = data[52]

            chatroom['auto_follow_done'] = data[53]
            chatroom['is_edited'] = data[54]

            # For Event Recordings and Attachments data
            if attachment_chatroom_list:
                from .chatroom.chatroom_impl import ChatroomHelper

                card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, data[0])
                event_recordings_data = ChatroomHelper.display_event_recordings_and_attachments(
                    user_instance=user_instance,
                    card_instance=card_instance
                )

                chatroom.update(event_recordings_data)

            chatrooms.append(chatroom)

        return JsonResponse({'success': True, 'chatrooms': chatrooms})

    def _add_poll_data(self, chatroom, data, poll_data, poll_votes, member_id):
        if chatroom['type'] == card_types.CARD_POLL:

            chatroom['is_poll_anonymous'] = data[26]
            chatroom['allow_add_option'] = data[27]
            if data[28] is not None:
                chatroom['multiple_select_state'] = data[28]
            if data[29]:
                chatroom['multiple_select_no'] = data[29]
            chatroom['is_anonymous'] = data[30]
            chatroom['poll_type'] = data[31]
            chatroom['poll_type_text'] = "Instant poll" \
                if chatroom['poll_type'] == poll_types.POLL_TYPE_INSTANT else "Deferred poll"
            chatroom['submit_type_text'] = "Secret voting" if chatroom[
                'is_poll_anonymous'] else "Public voting"

            polls = self._get_polls_v1(poll_data, chatroom['id'], poll_votes, data[29], member_id)
            if polls:
                from collabmates_api.chatroom_member.chatroom_member_impl import ChatroomMemberHelper
                chatroom['to_show_results'] = ChatroomMemberHelper.get_to_show_results(chatroom['id'], member_id,
                                                                                       poll_votes)
                chatroom['polls'] = polls

    def _add_event_data(self, chatroom, data):
        if chatroom['type'] == card_types.CARD_EVENT or chatroom['type'] == card_types.CARD_PUBLIC_EVENT:
            if data[33]:
                chatroom['about'] = data[33]
            if data[34]:
                chatroom['co_hosts_id'] = self._get_co_hosts(data[34])
            if data[35]:
                chatroom['online_link'] = data[35]
            if data[32] > 0:
                chatroom['end_date'] = data[32]

            chatroom['duration'] = data[41]

            if data[42]:
                chatroom['location'] = data[42]
                chatroom['location_lat'] = data[43]
                chatroom['location_long'] = data[44]

    def _add_attachements(self, chatroom, data):
        has_files = data[25] or chatroom['pdf_count'] > 0 or chatroom['attachment_count'] > 0

        chatroom_files = self._get_chatroom_files(chatroom['id'], has_files)
        chatroom['images'] = chatroom_files['image']
        chatroom['pdf'] = chatroom_files['pdf']
        chatroom['audios'] = chatroom_files['audio']
        chatroom['videos'] = chatroom_files['video']
        chatroom['attachments'] = chatroom_files['attachments']

    def _get_header(self, header, title):

        if header:
            return header

        if len(title) <= 30:
            return title[:30]

        return title[:27] + "..."

    def _get_chatroom_files(self, chatroom_id, has_files):

        files = {
            'image': [],
            'pdf': [],
            'audio': [],
            'video': []
        }

        attachments = []

        if has_files:
            files_filter = Card_Attachment.objects.filter(collabcard=chatroom_id).order_by('id')

            for file in files_filter:

                file_dict = {f'{file.type}_url': file.file_url, 'index': file.index, 'type': file.type}
                if file.height:
                    file_dict['height'] = file.height

                if file.width:
                    file_dict['width'] = file.width

                if file.thumbnail_url:
                    file_dict['thumbnail_url'] = file.thumbnail_url

                files[file.type].append(file_dict)

                attachment_dict = file_dict.copy()
                attachment_dict['url'] = attachment_dict.pop(f'{file.type}_url')
                attachments.append(attachment_dict)

        files['attachments'] = attachments

        return files

    def _get_polls_v1(self, poll_data, chatroom_id, poll_votes, is_multi, member_id):

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
            temp['no_votes'] = 0
            temp['percentage'] = 0

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

            if total_votes != 0:
                temp['no_votes'] = count
                temp['percentage'] = int((count / total_votes) * 100)
            polls.append(temp)

        return polls

    def _get_co_hosts(self, co_hosts):

        co_hosts = json.loads(co_hosts)
        co_host_list = []
        for member in co_hosts:
            temp = {}
            temp['id'] = member
            co_host_list.append(temp)

        return co_host_list

    def _get_draft_chatrooms(self, member_id, last_updated, page, paginate_by):

        draft_response = {'chatrooms': []}

        if last_updated:
            draft_filter = draftChatroom.objects.filter(date_epoch__gt=last_updated, user=member_id).order_by('id')
        else:
            draft_filter = draftChatroom.objects.filter(user=member_id).order_by('id')

        draft_filter = pagination(draft_filter, page, paginate_by=paginate_by)
        max_last_updated, chatrooms = fill_draft_chatrooms(draft_filter, member_id)

        if max_last_updated:
            draft_response = {'chatrooms': chatrooms, 'max_last_updated': max_last_updated}

        return draft_response

    def _get_event_recordings_of_user(self, user_instance):
        attachment_chatroom_list = set(ModelUtilities.get_model_filter(
            collabcardState,
            {
                'user': user_instance,
                'card__has_event_recording': True
            }
        ).values_list(
            'card',
            flat=True
        ))

        return attachment_chatroom_list

    def _get_video_chatrooms_of_user(self, user_instance):
        card_list = set(Card_Attachment.objects.filter(type='video').values_list('collabcard', flat=True))
        card_state_list = set(collabcardState.objects.filter(user=user_instance).values_list('card', flat=True))

        return card_state_list & card_list

    def _get_secret_chatrooms_of_user(self, user_instance):

        secret_chatroom_list = set(collabcardState.objects.filter(user=user_instance,
                                                                  card__is_secret=True)
                                   .values_list('card', flat=True))

        return secret_chatroom_list

    def _get_chatrooms_with_reactions_of_user(self, user_instance):

        chatrooms_with_reactions_list = set(collabcardState.objects
                                            .filter(user=user_instance, card__has_reactions=True)
                                            .values_list('card', flat=True))

        return chatrooms_with_reactions_list

    def _get_chatrooms_with_topics_of_user(self, user_instance):

        chatrooms_with_topics_list = set(collabcardState.objects
                                         .filter(user=user_instance)
                                         .exclude(card__topic=None)
                                         .values_list('card', flat=True))

        return chatrooms_with_topics_list

    def _get_chatrooms_with_edited_first_message(self, user_instance):

        chatrooms_with_edited_list = set(collabcardState.objects
                                         .filter(user=user_instance, card__is_edited=True)
                                         .values_list('card', flat=True))

        return chatrooms_with_edited_list


class SyncConversation(APIView):

    def get(self, request, *args, **kwargs):

        member_id = get_member_id_from_headers(request)

        if not member_id:
            context = ResponseUtilities.get_view_impl_error_context("Send member id in headers",
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(**context)

        device_id = RequestUtilities.get_device_id_from_headers(request)

        query_params = request.query_params
        page = RequestUtilities.get_page_number(request)
        paginate_by = RequestUtilities.get_page_size(request, default=200)
        last_updated = RequestUtilities.get_page_number(request, key='last_updated', default=0)
        chatroom_status = query_params.get('chatroom_status', '')
        chatroom_id = query_params.get('chatroom_id', '')
        community_id = query_params.get('community_id', '')
        state = query_params.get('state')
        chatroom_type = query_params.get('chatroom_type')

        if chatroom_id:
            # seen conversation support for old versions of android users to be removed after stable release
            seen_conversation = request.GET.get('seen_conversation')

            if seen_conversation:
                conversation_filter = card_answers.objects.filter(card=chatroom_id,
                                                                  id__gt=seen_conversation).order_by('id')
                conversation_filter = pagination(conversation_filter, page, paginate_by)
                context = {"current_user_id": member_id, "fetch_reply": True}
                conversations_data = CardAnswersDBSyncSerializer(conversation_filter, context=context, many=True)
                conversations = conversations_data.data

                max_last_updated = get_attachments_filtered_conversations(conversation_filter, conversations,
                                                                          member_id, device_id)

                context = {
                    'conversations': conversations,
                }

                if max_last_updated:
                    context['max_last_updated'] = max_last_updated

                context['success'] = True

                return JsonResponse(context)

            else:
                chatroom_list = [chatroom_id]
                conversation_data, files_answer_id = get_conversation_data_based_on_chatroom_list(chatroom_list, page,
                                                                                                  paginate_by,
                                                                                                  last_updated, state)
                conversation_files_dict = get_conversation_files_based_on_conversation_list(files_answer_id)
                conversations, max_last_updated = self.get_processed_conversation_data(conversation_data,
                                                                                       conversation_files_dict,
                                                                                       member_id, device_id)

        elif community_id:

            chatroom_list = self.get_user_community_related_chatroom_list(chatroom_status, member_id, community_id)
            conversation_data, files_answer_id = get_community_conversation_data_based_on_chatroom_list(chatroom_list,
                                                                                                        page,
                                                                                                        paginate_by,
                                                                                                        last_updated,
                                                                                                        community_id,
                                                                                                        state)
            conversation_files_dict = get_conversation_files_based_on_conversation_list(files_answer_id)
            conversations, max_last_updated = self.get_processed_conversation_data(conversation_data,
                                                                                   conversation_files_dict,
                                                                                   member_id, device_id)

        else:

            chatroom_list = self.get_user_related_chatroom_list(chatroom_status,
                                                                member_id,
                                                                chatroom_type=chatroom_type)

            conversation_data, files_answer_id = get_conversation_data_based_on_chatroom_list(chatroom_list, page,
                                                                                              paginate_by, last_updated,
                                                                                              state)
            conversation_files_dict = get_conversation_files_based_on_conversation_list(files_answer_id)
            conversations, max_last_updated = self.get_processed_conversation_data(conversation_data,
                                                                                   conversation_files_dict,
                                                                                   member_id, device_id)

        context = {
            'success': True,
            'conversations': conversations
        }

        if max_last_updated:
            context['max_last_updated'] = max_last_updated

        return JsonResponse(context)

    def get_processed_conversation_data(self, conversation_data, conversation_files_dict, member_id, device_id):

        conversation_list = []
        max_last_updated = 0

        for conversation in conversation_data:

            conversation_context = dict()
            conversation_context['id'] = conversation[0]
            conversation_context['answer'] = conversation[1]
            conversation_context['created_at'] = TimeUtilities.convert_epoch_time_in_hh_mm(conversation[2])
            conversation_context['date'] = TimeUtilities.convert_epoch_time_in_date(conversation[2])
            conversation_context['created_epoch'] = conversation[2]
            conversation_context['state'] = conversation[3]
            conversation_context['is_edited'] = conversation[4]
            conversation_context['has_files'] = conversation[5]
            conversation_context['attachment_count'] = conversation[6]
            conversation_context['attachments_uploaded'] = conversation[7]
            conversation_context['chatroom_id'] = conversation[8]
            conversation_context['member_id'] = conversation[9]
            conversation_context['community_id'] = conversation[10]

            if self.is_attachments_uploaded(conversation_context['attachment_count'],
                                            conversation_context['attachments_uploaded'],
                                            member_id,
                                            conversation[18],
                                            conversation_context['member_id'],
                                            conversation[28],
                                            device_id):
                continue

            if conversation[11]:
                conversation_context['og_tags'] = json.loads(conversation[11])

            if conversation[12]:
                conversation_context['deleted_by'] = conversation[12]

            if conversation[14]:
                conversation_context['reply_conversation'] = conversation[14]

            conversation_files = conversation_files_dict.get(conversation_context['id'])

            if conversation_context['has_files'] and conversation_files:

                conversation_files_response = self.process_conversation_files(conversation_files)
                conversation_context['images'] = conversation_files_response['images']
                conversation_context['pdf'] = conversation_files_response['pdf']
                conversation_context['audios'] = conversation_files_response['audios']
                conversation_context['videos'] = conversation_files_response['videos']
                conversation_context['attachments'] = conversation_files_response['attachments']

                if conversation_files_response['location']:
                    conversation_context['location'] = conversation_files_response['location']

            if max_last_updated < conversation[15]:
                max_last_updated = conversation[15]

            if conversation[13]:

                if conversation[16] and conversation[17] == "chatroom":

                    preview_chatroom_id = conversation[16]
                    key = CHATROOM_PREVIW_CACHE_KEY % (str(preview_chatroom_id), str(conversation_context['id']))
                    preview = CacheImpl.get_cache(key)

                    if preview:
                        conversation_context['preview'] = preview

                    else:

                        try:
                            preview = get_preview_for_url(preview_url=conversation[13], member_id=member_id)

                            if preview:
                                conversation_context['preview'] = preview

                        except Exception as e:
                            error_logger.error("error occured" + str(e.args))
                            continue

                        update_preview_of_chatroom_in_cache.delay({'chatroom_id': preview_chatroom_id,
                                                                   'preview_url': conversation[13],
                                                                   'preview_object': conversation_context['preview'],
                                                                   'conversation_id': conversation_context['id']})

                    conversation_context['preview']['chatroom']['conversations_unread'] = fetch_conversations_unread(
                        preview_chatroom_id, member_id)

                elif conversation[26] and \
                        (conversation[17] == "community" or conversation[17] == "directory"):

                    preview_community_id = conversation[26]
                    key = CONVERSATION_COMMUNITY_PREVIEW % (str(conversation_context['id']), str(preview_community_id))
                    preview = CacheImpl.get_cache(key)

                    if preview:
                        conversation_context['preview'] = preview

                    else:

                        try:
                            preview = get_preview_for_url(member_id=member_id,
                                                          preview_url=conversation[13])
                            if preview:
                                conversation_context['preview'] = preview

                        except Exception as e:
                            error_logger.error("error occured" + str(e.args))
                            continue

                        update_preview_of_community_in_cache.delay({'community_id': preview_community_id,
                                                                    'preview_url': conversation[13],
                                                                    'preview_object': conversation_context['preview'],
                                                                    'conversation_id': conversation_context['id']})

            if conversation[19]:
                conversation_context['temporary_id'] = conversation[19]

            if conversation_context['state'] == ConversationStates.CONVERSATION_POLL:
                conversation_context['poll_type'] = conversation[20]

                conversation_context['poll_type_text'] = "Instant poll" \
                    if conversation_context['poll_type'] == conversation_poll_types.INSTANT else "Deferred poll"

                if conversation[21] is not None:
                    conversation_context['multiple_select_state'] = conversation[21]

                if conversation[22]:
                    conversation_context['multiple_select_no'] = conversation[22]

                conversation_context['is_anonymous'] = conversation[23]

                conversation_context['submit_type_text'] = "Secret voting" \
                    if conversation_context['is_anonymous'] else "Public voting"

                conversation_context['allow_add_option'] = conversation[24]
                conversation_context['expiry_time'] = conversation[25]

                conversation_info = {
                    'conversation_id': conversation[0],
                    'poll_type': conversation[20],
                    'multiple_select_no': conversation[22],
                    'expiry_time': conversation[25],
                    'member_id': member_id
                }
                conversation_context['polls'] = get_conversation_poll(conversation_info)
                conversation_context['to_show_results'] = get_to_show_results_for_conversation_poll(conversation_info)
                conversation_context['poll_answer_text'] = conversation[29]

            # conversation[27] = has_reactions
            if conversation[27]:
                reactions = fetch_chatroom_or_conversation_reactions(conversation_id=conversation_context['id'])

            else:
                reactions = []

            conversation_context['reactions'] = reactions if reactions else []

            if conversation[30]:
                conversation_context['reply_chatroom_id'] = conversation[30]

            if conversation_context['state'] == ConversationStates.CONVERSATION_EVENT:
                self.fill_event_conversation_data(conversation_context, conversation)

            conversation_list.append(conversation_context)

        return conversation_list, max_last_updated

    def process_conversation_files(self, conversation_files):

        conversation_files_response = {
            'images': [],
            'pdf': [],
            'audios': [],
            'videos': [],
            'voice_notes': [],
            'attachments': [],
            'location': {}
        }
        attachment_list = []

        for file in conversation_files:

            if file['type'] == 'image' and file['file_url']:
                img_attachment = {'image_url': file['file_url'], 'index': file['index'], 'type': file['type']}
                attachment_image_context = {'url': file['file_url'], 'index': file['index'], 'type': file['type']}

                if file['height']:
                    img_attachment['height'] = file['height']
                    attachment_image_context['height'] = file['height']

                if file['width']:
                    img_attachment['width'] = file['width']
                    attachment_image_context['width'] = file['width']

                if file.get('thumbnail_url'):
                    img_attachment['thumbnail_url'] = file.get('thumbnail_url')
                    attachment_image_context['thumbnail_url'] = file.get('thumbnail_url')

                if file['name']:
                    img_attachment['name'] = file['name']
                    attachment_image_context['name'] = file['name']

                if file['meta']:
                    file_meta = JsonUtilities.load_json_data(file['meta'])

                    if file_meta:
                        img_attachment['meta'] = file_meta
                        attachment_image_context['meta'] = file_meta

                conversation_files_response['images'].append(img_attachment)
                attachment_list.append(attachment_image_context)

            elif file['type'] == 'video' and file['file_url']:
                attachment_video_context = {'url': file['file_url'], 'index': file['index'], 'type': file['type']}
                video_attachment = {'video_url': file['file_url'], 'index': file['index'], 'type': file['type']}

                if file['height']:
                    attachment_video_context['height'] = file['height']
                    video_attachment['height'] = file['height']

                if file['width']:
                    attachment_video_context['width'] = file['width']
                    video_attachment['width'] = file['width']

                if file['thumbnail_url']:
                    attachment_video_context['thumbnail_url'] = file['thumbnail_url']
                    video_attachment['thumbnail_url'] = file['thumbnail_url']

                if file['name']:
                    attachment_video_context['name'] = file['name']
                    video_attachment['name'] = file['name']

                if file['meta']:
                    file_meta = JsonUtilities.load_json_data(file['meta'])

                    if file_meta:
                        attachment_video_context['meta'] = file_meta
                        video_attachment['meta'] = file_meta

                conversation_files_response['videos'].append(video_attachment)
                attachment_list.append(attachment_video_context)

            elif file['type'] == "audio" and file['file_url']:
                audio_attachment = {'url': file['file_url'], 'index': file['index'], 'type': file['type']}

                if file['height']:
                    audio_attachment['height'] = file['height']

                if file['width']:
                    audio_attachment['width'] = file['width']

                if file['name']:
                    audio_attachment['name'] = file['name']

                if file.get('thumbnail_url'):
                    audio_attachment['thumbnail_url'] = file.get('thumbnail_url')

                if file['meta']:
                    file_meta = JsonUtilities.load_json_data(file['meta'])

                    if file_meta:
                        audio_attachment['meta'] = file_meta

                attachment_list.append(audio_attachment)

            elif file['type'] == "pdf" and file['file_url']:
                pdf_attachment = {'pdf_file': file['file_url'], 'index': file['index'], 'type': file['type']}
                attachment_pdf_context = {'url': file['file_url'], 'index': file['index'], 'type': file['type']}

                if file['height']:
                    pdf_attachment['height'] = file['height']
                    attachment_pdf_context['height'] = file['height']

                if file['width']:
                    pdf_attachment['width'] = file['width']
                    attachment_pdf_context['width'] = file['width']

                if file['thumbnail_url']:
                    attachment_pdf_context['width'] = file['width']
                    attachment_pdf_context['thumbnail_url'] = file['thumbnail_url']

                if file['name']:
                    pdf_attachment['name'] = file['name']
                    attachment_pdf_context['name'] = file['name']

                if file['meta']:
                    file_meta = JsonUtilities.load_json_data(file['meta'])

                    if file_meta:
                        pdf_attachment['meta'] = file_meta
                        attachment_pdf_context['meta'] = file_meta

                conversation_files_response['pdf'].append(pdf_attachment)
                attachment_list.append(attachment_pdf_context)

            elif file['type'] == "location":
                location = {
                    'location_name': file['location_name'],
                    'location_lat': file['location_lat'],
                    'location_long': file['location_long']
                }

                conversation_files_response['location'] = location

            elif file['type'] == "gif" and file['file_url']:
                attachment_gif_context = {'url': file['file_url'], 'index': file['index'], 'type': file['type']}

                if file['height']:
                    attachment_gif_context['height'] = file['height']

                if file['width']:
                    attachment_gif_context['width'] = file['width']

                if file['thumbnail_url']:
                    attachment_gif_context['thumbnail_url'] = file['thumbnail_url']

                if file['name']:
                    attachment_gif_context['name'] = file['name']

                if file['meta']:
                    file_meta = JsonUtilities.load_json_data(file['meta'])

                    if file_meta:
                        attachment_gif_context['meta'] = file_meta

                attachment_list.append(attachment_gif_context)

            elif file['type'] == "voice_note" and file['file_url']:
                voice_note_attachment = {'url': file['file_url'], 'index': file['index'], 'type': file['type']}

                if file['height']:
                    voice_note_attachment['height'] = file['height']

                if file['width']:
                    voice_note_attachment['width'] = file['width']

                if file['name']:
                    voice_note_attachment['name'] = file['name']

                if file['thumbnail_url']:
                    voice_note_attachment['thumbnail_url'] = file['thumbnail_url']

                if file['meta']:
                    file_meta = JsonUtilities.load_json_data(file['meta'])

                    if file_meta:
                        voice_note_attachment['meta'] = file_meta

                attachment_list.append(voice_note_attachment)

        conversation_files_response['attachments'] = attachment_list

        return conversation_files_response

    def get_user_related_chatroom_list(self, chatroom_status, member_id, chatroom_type=None):
        """
            This function returns conversation filter based on different conditions of chatroom
            chatroom_status = followed/unfollowed
        """
        condition_dict = {
            'user': member_id,
            'remove': None
        }

        if chatroom_status:

            if chatroom_status == "followed":
                condition_dict['follow_status'] = True

            elif chatroom_status == "unfollowed":
                condition_dict['follow_status'] = False

        else:
            condition_dict['follow_status'] = False

        if chatroom_type:
            condition_dict['card__type'] = chatroom_type

        chatroom_list = get_id_list_of_chatrooms(condition_dict)

        return chatroom_list

    def get_user_community_related_chatroom_list(self, chatroom_status, member_id, community_id):
        """
            This function returns conversation filter based on different conditions of community chatroom
            chatroom_status = followed/unfollowed
        """
        chatroom_list = []
        if chatroom_status:

            if chatroom_status == "followed":
                condition_dict = {'user': member_id, 'follow_status': True, 'remove': None, 'community': community_id}
                chatroom_list = get_id_list_of_chatrooms(condition_dict)

            elif chatroom_status == "unfollowed":
                condition_dict = {'user': member_id, 'follow_status': False, 'remove': None, 'community': community_id}
                chatroom_list = get_id_list_of_chatrooms(condition_dict)

        else:
            condition_dict = {'user': member_id, 'follow_status': False, 'remove': None, 'community': community_id}
            chatroom_list = get_id_list_of_chatrooms(condition_dict)

        return chatroom_list

    def is_attachments_uploaded(self, attachment_count, attachment_uploaded, member_id,
                                api_version, conversation_creator_id, conversation_device_id='',
                                current_device_id=None):

        if (attachment_count > 0 and attachment_uploaded is False) \
                and ((NumberUtilities.get_integer_from_string(member_id) != conversation_creator_id)
                     or api_version <= 0 or
                     conversation_device_id != current_device_id):
            return True

        return False

    def fill_event_conversation_data(self, conversation_context, conversation_data):

        conversation_context['header'] = conversation_data[31]

        if conversation_data[32]:
            conversation_context['location'] = conversation_data[32]

        if conversation_data[33]:
            conversation_context['location_lat'] = conversation_data[33]

        if conversation_data[34]:
            conversation_context['location_long'] = conversation_data[34]

        conversation_context['start_time'] = conversation_data[35]
        conversation_context['end_time'] = conversation_data[36]
        conversation_context['online_link_enable_before'] = conversation_data[37]

        if conversation_data[38]:
            co_hosts_ids = JsonUtilities.load_json_data(conversation_data[38])

            if co_hosts_ids:
                conversation_context['co_hosts_ids'] = co_hosts_ids

        self._fill_event_attendees(conversation_context)

    def _fill_event_attendees(self, conversation_context):

        event_attendees_dict = CacheImpl.get_cache(EVENT_ATTENDEES_CONVERSATION % str(conversation_context['id']))

        if event_attendees_dict:
            event_attendees_list = event_attendees_dict.get('event_attendees_list', [])
            conversation_context['attendees_ids'] = event_attendees_list

            return

        event_attendees_list = list(ModelUtilities.get_model_filter(conversationEventMembers,
                                                                    {'conversation': conversation_context['id'],
                                                                     'attending_status': True}
                                                                    ).values_list('user', flat=True).
                                    order_by('created_at')[:10])

        update_event_attendees_for_micro_event.delay({'conversation_id': conversation_context['id'],
                                                      'event_attendees_list': event_attendees_list})

        conversation_context['attendees_ids'] = event_attendees_list


class SyncConversationDiff(APIView):

    def get(self, request, *args, **kwargs):

        member_id = get_member_id_from_headers(request)

        device_id = RequestUtilities.get_device_id_from_headers(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        if not member_id:
            context = ResponseUtilities.get_view_impl_error_context("Send member id in headers",
                                                                    status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(**context)

        query_params = request.query_params

        previous_app_version = query_params.get('previous_app_version', 0)
        previous_app_version = NumberUtilities.get_integer_from_string(previous_app_version)

        page = RequestUtilities.get_page_number(request)
        paginate_by = RequestUtilities.get_page_size(request, default=200)
        is_synced = query_params.get('is_synced', "false").lower() == 'true'

        conversations = []
        common_list = []
        video_conversations_list = set()
        conversations_with_reactions_list = set()
        conversation_with_reply_chatroom_id_list = set()

        if not is_synced:

            user_instance = ModelUtilities.get_user_instance_or_none(member_id)

            if not user_instance:
                return JsonResponse({'success': True, 'conversations': []})

            card_state_list = set(collabcardState.objects.filter(user=user_instance).values_list('card', flat=True))

            if previous_app_version < VIDEO_SYNC_TRIGGER_VERSION_CODE_AN <= version_code:
                video_conversations_list = self._get_video_conversations_list(card_state_list)
                common_list = tuple(video_conversations_list)

            if previous_app_version < REACTIONS_SYNC_TRIGGER_VERSION_CODE_AN <= version_code:
                conversations_with_reactions_list = self._get_conversation_with_reactions(card_state_list)
                common_list = tuple(conversations_with_reactions_list)

            if previous_app_version < VIDEO_SYNC_TRIGGER_VERSION_CODE_AN and \
                    version_code >= REACTIONS_SYNC_TRIGGER_VERSION_CODE_AN:
                common_list = tuple(video_conversations_list | conversations_with_reactions_list)

            if previous_app_version < CHATROOM_FIRST_MESSAGE_ACTION_VERSION_CODE_ANDROID:
                conversation_with_reply_chatroom_id_list = self._get_conversation_with_reply_chatroom_id(
                    card_state_list)

                common_list = tuple(video_conversations_list |
                                    conversations_with_reactions_list |
                                    conversation_with_reply_chatroom_id_list)

            if previous_app_version < MICRO_POLLS_ANDROID_VERSION_CODE <= version_code:
                conversation_with_micro_polls_list = self._get_conversation_with_micro_polls(card_state_list)

                common_list = tuple(video_conversations_list |
                                    conversations_with_reactions_list |
                                    conversation_with_reply_chatroom_id_list |
                                    conversation_with_micro_polls_list)

        if len(common_list) > 0:
            conversation_filter = card_answers.objects.filter(pk__in=common_list) \
                .select_related('preview_community', 'preview_chatroom').order_by('last_updated')

            conversation_list = pagination(conversation_filter, page, paginate_by=paginate_by)

            context = {"current_user_id": member_id, "fetch_reply": True, "version_code": version_code}
            conversations_data = CardAnswersDBSyncSerializer(conversation_list, context=context, many=True)
            conversations = conversations_data.data

            get_attachments_filtered_conversations(conversation_list, conversations, member_id, device_id)

        context = {
            'success': True,
            'conversations': conversations,
        }

        return JsonResponse(context)

    def _get_video_conversations_list(self, card_state_list):

        answer_card_map = answerAttachment.objects.filter(type='video').values('answer', 'answer__card__id')
        card_list = {item['answer__card__id'] for item in answer_card_map}
        common_list = card_state_list & card_list

        ans_list = {item['answer'] for item in answer_card_map if item['answer__card__id'] in common_list}

        return ans_list

    def _get_conversation_with_reactions(self, card_state_list):
        ans_list = set(card_answers.objects
                       .filter(card__id__in=card_state_list, has_reactions=True)
                       .values_list('id', flat=True))
        return ans_list

    def _get_conversation_with_reply_chatroom_id(self, card_state_list):

        ans_list = set(card_answers.objects
                       .filter(card__id__in=card_state_list).filter(~Q(reply_chatroom=None))
                       .values_list('id', flat=True))

        return ans_list

    def _get_conversation_with_micro_polls(self, card_state_list):

        ans_list = set(card_answers.objects
                       .filter(card__id__in=card_state_list).filter(state=conversation_states.CONVERSATION_POLL)
                       .values_list('id', flat=True))

        return ans_list


def get_attachments_filtered_conversations(conversation_list, conversation_data, member_id, device_id=''):
    conversation_last_index = len(conversation_data) - 1
    max_last_updated = 0

    for conversation in conversation_list[::-1]:

        if is_draft_conversation(conversation, member_id, device_id=device_id):
            del conversation_data[conversation_last_index]
            conversation_last_index -= 1
            continue

        if max_last_updated < conversation.last_updated:
            max_last_updated = conversation.last_updated

        conversation_last_index -= 1

    return max_last_updated


def get_user_related_conversations(chatroom_status, member_id, last_updated):

    """
        This function returns conversation filter based on different conditions of chatroom
        chatroom_status = followed/unfollowed
    """
    chatroom_list = []
    if chatroom_status:

        if chatroom_status == "followed":
            condition_dict = {'user': member_id, 'follow_status': True, 'remove': None}
            chatroom_list = get_id_list_of_chatrooms(condition_dict)

        elif chatroom_status == "unfollowed":
            condition_dict = {'user': member_id, 'follow_status': False, 'remove': None}
            chatroom_list = get_id_list_of_chatrooms(condition_dict)

    else:
        condition_dict = {'user': member_id, 'follow_status': False, 'remove': None}
        chatroom_list = get_id_list_of_chatrooms(condition_dict)

    conversation_filter = card_answers.objects.filter(card__id__in=chatroom_list,
                                                      last_updated__gt=last_updated).order_by('last_updated')
    conversation_filter = conversation_filter.select_related('preview_community', 'preview_chatroom')

    return conversation_filter


def get_id_list_of_chatrooms(condition_dict):

    """ return chatroom id list based on conditional dict"""
    current_time = time.time()

    chatroom_list = list(collabcardState.objects.filter(
        **condition_dict).values_list(
        "card_id", flat=True))

    return chatroom_list


def fetch_user_meta(request):
    '''api to send community ids list'''
    member_id = get_member_id_from_headers(request)

    if not member_id:
        context = get_error_context(False, "send x-member-id in header")
        return JsonResponse(context)

    community_list = list(
        Members.objects.filter(member_id=member_id).values_list("community_id", flat=True).order_by('-updated_at'))

    community_ids = []

    for community_id in community_list:
        temp = {}
        temp['id'] = community_id
        community_ids.append(temp)

    return JsonResponse({'community_ids': community_ids})


def get_guest_users_of_member_joined_communities(community_list):
    guest_filter = collabcardState.objects.filter(is_guest=True,
                                                  community__in=community_list,
                                                  remove=None).only('card_id',
                                                                    'user_id',
                                                                    'created_at',
                                                                    'source_id',
                                                                    'community_id')
    user_set = set()
    source_list = []
    user_card_dict = dict()

    for data in guest_filter:

        user_id = data.user_id
        source_id = data.source_id

        if user_id not in user_card_dict:

            user_card_dict[user_id] = [{
                'user_id': user_id,
                'card_id': data.card_id,
                'created_at': data.created_at,
                'source_id': data.source_id,
                'community_id': data.community_id
            }]

        else:
            user_card_dict[user_id].append({
                'user_id': user_id,
                'card_id': data.card_id,
                'created_at': data.created_at,
                'source_id': data.source_id,
                'community_id': data.community_id
            })

        user_set.add(user_id)

        if source_id:
            user_set.add(source_id)

    user_list = list(user_set)

    return user_card_dict, user_list


def get_guest_users_of_chatroom(chatroom_id):
    guest_filter = collabcardState.objects.filter(is_guest=True,
                                                  card=chatroom_id,
                                                  remove=None).only('card_id',
                                                                    'user_id',
                                                                    'created_at',
                                                                    'source_id',
                                                                    'community_id')
    user_set = set()
    user_card_dict = dict()

    for data in guest_filter:

        user_id = data.user_id
        source_id = data.source_id

        if user_id not in user_card_dict:

            user_card_dict[user_id] = [{
                'user_id': user_id,
                'card_id': data.card_id,
                'created_at': data.created_at,
                'source_id': data.source_id,
                'community_id': data.community_id
            }]

        else:
            user_card_dict[user_id].append({
                'user_id': user_id,
                'card_id': data.card_id,
                'created_at': data.created_at,
                'source_id': data.source_id,
                'community_id': data.community_id
            })

        user_set.add(user_id)

        if source_id:
            user_set.add(source_id)

    user_list = list(user_set)

    return user_card_dict, user_list


def get_dictionary_of_user_profiles(user_filter):
    user_data_dict = {}

    max_last_updated = 0

    for data in user_filter:

        user_id = data.user_id_id

        if user_id not in user_data_dict:
            user_data_dict[user_id] = {
                'id': user_id,
                'name': data.name,
                'image_url': data.image_link if data.image_link else '',
                'is_guest': data.is_guest,
            }

        max_last_updated = max(max_last_updated, data.updated_at)

    return user_data_dict, max_last_updated


def get_guest_list_of_chatrooms(user_data_dict, user_card_dict):
    guest_list = []

    for key, value in user_data_dict.items():

        user_id = key

        for user_data in user_card_dict.get(user_id, []):

            temp = {
                'id': value['id'],
                'name': value['name'],
                'image_url': value['image_url'],
                'is_guest': value.get('is_guest'),
                'chatroom_id': user_data.get('card_id'),
                'community_id': user_data.get('community_id')
            }

            source_id = user_data.get('source_id')

            if source_id:
                created_at = TimeUtilities.convert_epoch_time_in_date(user_data.get('created_at'))

                source_user = user_data_dict.get(source_id)

                if source_user:
                    source_user_name = source_user.get('name')
                    temp['custom_intro_text'] = """Joined as a guest via %s’s invite link on %s""" % (
                        source_user_name, created_at)

                    temp[
                        'custom_click_text'] = """The profile you are trying to access does not exist. %s joined this chatroom as a guest via %s’s invite link on %s""" % (
                        value['name'], source_user_name,
                        created_at)

            guest_list.append(temp)

    return guest_list


def get_source_users_for_guest(source_list):
    user_filter = Userinfo.objects.filter(user_id_id__in=source_list).only('user_id_id',
                                                                           'name',
                                                                           'image_link',
                                                                           'updated_at').order_by('updated_at')
    source_data_dict = {}

    for data in user_filter:

        user_id = data.user_id_id

        if user_id not in source_data_dict:
            source_data_dict[user_id] = {
                'id': user_id,
                'name': data.name,
                'image_url': data.image_link if data.image_link else '',
            }

    return source_data_dict


class SyncMembers(APIView):

    def get(self, request, *args, **kwargs):

        member_id = get_member_id_from_headers(request)

        query_params = request.query_params

        members_type = query_params.get('members_type', "")

        if not member_id:
            context = get_error_context(False, "send member id in headers")
            return JsonResponse(context)

        page = query_params.get('page', 1)
        page = NumberUtilities.get_integer_from_string(page)
        paginate_by = query_params.get('page_size', 200)
        last_updated = query_params.get('last_updated', 0)
        paginate_by = NumberUtilities.get_integer_from_string(paginate_by)
        chatroom_id = query_params.get('chatroom_id', '')
        community_id = query_params.get('community_id', None)

        member_data = dict()

        if members_type == "members":
            member_data = self.get_members_data(member_id, chatroom_id, community_id, last_updated,
                                                page, paginate_by)

        if members_type == "removed_members":
            member_data = self.get_removed_members_data(member_id, chatroom_id, community_id, last_updated,
                                                        page, paginate_by)

        if members_type == "guest":
            member_data = self.get_guest_members_data(member_id, chatroom_id, community_id, last_updated,
                                                      page, paginate_by)

        context = {'members': member_data.get('members', [])}

        if member_data.get('max_last_updated'):
            context['max_last_updated'] = member_data.get('max_last_updated')

        return JsonResponse(context)

    def get_members_data(self, member_id, chatroom_id, community_id, last_updated, page, paginate_by):

        if chatroom_id:

            return self.get_members_data_for_chatroom_id(chatroom_id, last_updated, page, paginate_by)

        elif community_id:

            return self.get_members_data_for_community_id(community_id, last_updated, page, paginate_by)

        else:

            return fetch_all_members_of_user_joined_communities(member_id, page, last_updated, paginate_by)

    def get_members_data_for_chatroom_id(self, chatroom_id, last_updated, page, paginate_by):

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return JsonResponse({'members': []})

        participants_list = collabcardState.objects.filter(card=card_instance, is_guest=False,
                                                           remove=None). \
            filter(Q(follow_status=True) | Q(attending_status=True)). \
            values_list("user__id", flat=True).order_by('id')

        community_id = card_instance.community_id
        participants_list = list_pagination(participants_list, page, paginate_by=paginate_by)
        responses_data = get_member_responses_for_community([community_id])
        member_data = get_members_of_community_based_on_user_list_for_sync(participants_list,
                                                                           community_id,
                                                                           last_updated, page, paginate_by)

        member_response = compute_response_of_members_data(member_data, responses_data)

        return member_response

    def get_members_data_for_community_id(self, community_id, last_updated, page, paginate_by):

        if not last_updated:
            member_list = list(
                Members.objects.filter(community_id=community_id).values_list('member_id', flat=True).order_by('id'))
        else:
            member_list = list(Members.objects.filter(community_id=community_id,
                                                      updated_at__gt=last_updated).values_list('member_id',
                                                                                               flat=True).order_by(
                'id'))

        responses_data = get_member_responses_for_community([community_id])
        members_data = get_members_of_community_based_on_user_list_for_sync(member_list, community_id,
                                                                            last_updated, page, paginate_by)
        member_response = compute_response_of_members_data(members_data, responses_data)

        return member_response

    def get_removed_members_data(self, member_id, chatroom_id, community_id, last_updated, page, paginate_by):

        if chatroom_id:

            return self.get_removed_members_based_on_chatroom_id(chatroom_id, last_updated, page, paginate_by)

        elif community_id:

            return self.get_removed_members_based_on_community_id(community_id, last_updated, page, paginate_by)

        else:

            return self.get_removed_members_of_member_joined_communities(member_id, last_updated, page, paginate_by)

    def get_removed_members_based_on_chatroom_id(self, chatroom_id, last_updated, page, paginate_by):

        community_instance = Collabcard.get_community_of_chatroom_or_none(chatroom_id)

        if not community_instance:
            context = {'members': []}

            return context

        chatroom_removed_members = \
            set(collabcardState.objects.filter(card=chatroom_id).filter(~Q(remove=None)).
                values_list('user', flat=True))

        if not last_updated:
            remove_member_filter = removedMembers.objects.filter(community=community_instance).order_by('id')

        else:
            remove_member_filter = removedMembers.objects.filter(community=community_instance,
                                                                 created_at__gt=last_updated).order_by('id')
        removed_member_queryset = ModelUtilities.paginate_queryset(remove_member_filter, page, paginate_by)

        return self.process_removed_members(removed_member_queryset,
                                            removed_member_set=chatroom_removed_members)

    def get_removed_members_based_on_community_id(self, community_id, last_updated, page, paginate_by):

        if not last_updated:
            remove_member_filter = removedMembers.objects.filter(community=community_id). \
                select_related('member', 'member__userinfo').order_by('id')

        else:
            remove_member_filter = removedMembers.objects.filter(community=community_id,
                                                                 created_at__gt=last_updated). \
                select_related('member', 'member__userinfo').order_by('id')

        remove_member_queryset = ModelUtilities.paginate_queryset(remove_member_filter, page, paginate_by)

        return self.process_removed_members(remove_member_queryset)

    def get_removed_members_of_member_joined_communities(self, member_id, last_updated, page, paginate_by):

        community_list = get_community_id_list(member_id)

        remove_member_filter = removedMembers.objects.filter(created_at__gt=last_updated,
                                                             community__in=community_list).order_by('id')
        remove_member_filter = ModelUtilities.paginate_queryset(remove_member_filter, page, paginate_by)

        return self.process_removed_members(remove_member_filter)

    def process_removed_members(self, removed_member_queryset, removed_member_set=None):

        max_last_updated = 0
        member_list = []

        for data in removed_member_queryset:

            if removed_member_set is not None and \
                    data.member_id not in removed_member_set:
                continue

            if max_last_updated < data.created_at:
                max_last_updated = data.created_at

            member_data = get_removed_member_instance(data)

            member_list.append(member_data)

        context = {
            'members': member_list
        }

        if max_last_updated:
            context['max_last_updated'] = max_last_updated

        return context

    def get_guest_members_data(self, member_id, chatroom_id, community_id, last_updated, page, paginate_by):

        if chatroom_id:

            guest_data = self.compute_guest_list_for_chatroom_id(chatroom_id, last_updated, page, paginate_by)

        elif community_id:
            guest_data = self.compute_guest_list_for_community_id(community_id,
                                                                  last_updated, page, paginate_by)

        else:
            guest_data = self.compute_guest_list_for_members(member_id, last_updated, page, paginate_by)

        return guest_data

    def compute_guest_list_for_chatroom_id(self, chatroom_id, last_updated, page, paginate_by):

        user_card_dict, user_list = get_guest_users_of_chatroom(chatroom_id)
        user_filter = Userinfo.objects.filter(user_id_id__in=user_list,
                                              updated_at__gt=last_updated).only('user_id_id',
                                                                                'name',
                                                                                'image_link',
                                                                                'updated_at',
                                                                                'is_guest').order_by(
            'updated_at',
            'user_id')
        user_filter = ModelUtilities.paginate_queryset(user_filter, page, paginate_by)

        user_data_dict, max_last_updated = get_dictionary_of_user_profiles(user_filter)

        guest_list = get_guest_list_of_chatrooms(user_data_dict, user_card_dict)

        return {
            'members': guest_list,
            'max_last_updated': max_last_updated
        }

    def compute_guest_list_for_community_id(self, community_id, last_updated, page, paginate_by):

        community_list = [community_id]
        user_card_dict, user_list = get_guest_users_of_member_joined_communities(community_list)

        user_filter = Userinfo.objects.filter(user_id_id__in=user_list,
                                              updated_at__gt=last_updated).only('user_id_id',
                                                                                'name',
                                                                                'image_link',
                                                                                'updated_at').order_by(
            'updated_at',
            'user_id')
        user_filter = ModelUtilities.paginate_queryset(user_filter, page, paginate_by)

        user_data_dict, max_last_updated = get_dictionary_of_user_profiles(user_filter)

        guest_list = get_guest_list_of_chatrooms(user_data_dict, user_card_dict)

        return {
            'members': guest_list,
            'max_last_updated': max_last_updated
        }

    def compute_guest_list_for_members(self, member_id, last_updated, page, paginate_by):

        community_list = get_community_id_list(member_id)
        user_card_dict, user_list = get_guest_users_of_member_joined_communities(community_list)
        user_filter = Userinfo.objects.filter(user_id_id__in=user_list,
                                              updated_at__gt=last_updated).only('user_id_id',
                                                                                'name',
                                                                                'image_link',
                                                                                'updated_at').order_by(
            'updated_at',
            'user_id')

        user_filter = ModelUtilities.paginate_queryset(user_filter, page, paginate_by)

        user_data_dict, max_last_updated = get_dictionary_of_user_profiles(user_filter)

        guest_list = get_guest_list_of_chatrooms(user_data_dict, user_card_dict)

        return {
            'members': guest_list,
            'max_last_updated': max_last_updated
        }


def fill_draft_chatrooms(draft_filter, member_id):
    '''function to fill draft chatrooms'''
    chatrooms = []
    max_last_updated = 0
    for draft in draft_filter:

        if max_last_updated < draft.date_epoch:
            max_last_updated = draft.date_epoch
        draft_chatroom = draftChatroomSerializer(draft, member_id)
        draft_chatroom['is_draft'] = True
        draft_chatroom['updated_at'] = draft.date_epoch
        chatrooms.append(draft_chatroom)

    return max_last_updated, chatrooms


def compute_response_of_members_data(members_data, responses_data):
    max_last_updated = 0
    member_list = []

    for data in members_data:
        member_context = dict()
        member_context['id'] = data['member_id']
        member_context['name'] = data['name']
        member_context['image_url'] = data['image_url']
        member_context['state'] = data['state']
        member_context['is_guest'] = data['is_guest']
        member_context['is_owner'] = data['is_owner']
        community_name = data['community_name']
        locale_time = time.localtime(data['created_at'])

        if data['custom_title'] and not data['custom_title'] == 'Member':
            member_context['custom_title'] = data['custom_title']

        if member_context['state'] == member_states.ADMIN or member_context['state'] == member_states.MEMBER or \
                member_context['state'] == member_states.PROFILE_UNAVAILABLE:
            member_context['member_since'] = "Member since " + time.strftime('%b %d %Y', locale_time)
        elif member_context['state'] == member_states.PENDING_MEMBER:
            member_context['member_since'] = "Verification pending for " + community_name

        key = str(data['member_id']) + "$" + str(data['community_id'])

        if member_context['state'] == member_states.ADMIN and not responses_data.get(key):
            member_context['custom_intro_text'] = CREATE_INTRO_TEXT_ADMIN % (
                time.strftime("%d %B %Y", locale_time))

        member_context['community_id'] = data['community_id']

        if max_last_updated < data['updated_at']:
            max_last_updated = data['updated_at']

        member_list.append(member_context)

    if max_last_updated:
        return {'members': member_list, 'max_last_updated': max_last_updated}

    return {'members': member_list}


def fetch_all_members_of_user_joined_communities(member_id, page, last_updated, limit):
    """function to get all members of community which is joined by the member"""

    community_id_list = get_community_id_list(member_id)
    responses_data = get_member_responses_for_community(community_id_list)
    members_data = get_members_of_community_based_on_community_list_for_sync(community_id_list, last_updated, page,
                                                                             limit)

    return compute_response_of_members_data(members_data, responses_data)


class SyncCommunities(APIView):

    def get(self, request, *args, **kwargs):

        member_id = get_member_id_from_headers(request)
        if not member_id:
            context = get_error_context(False, "send member id in headers")
            return JsonResponse(context)

        query_params = request.query_params

        page = query_params.get('page', 1)
        paginate_by = query_params.get('page_size', 200)
        last_updated = query_params.get('last_updated', 0)
        chatroom_id = query_params.get('chatroom_id', '')
        community_id = query_params.get('community_id', '')
        guest = query_params.get('guest', '')

        member_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not member_instance:
            return JsonResponse(get_error_context(False, "Invalid member_id"))

        try:
            page = int(page)

        except:
            context = get_error_context(False, "invalid page value")
            return JsonResponse(context)

        context = {"current_user_id": member_id}

        if guest == "true":
            community_context = fetch_guest_communities(member_id, last_updated=last_updated)
            return JsonResponse(community_context)

        if chatroom_id:
            chatroom_context = fetch_community_of_chatroom(chatroom_id, member_id, last_updated=last_updated)
            return JsonResponse(chatroom_context)

        elif community_id:
            community_obj = ModelUtilities.get_model_instance_or_none(Community, community_id)

            if not community_obj:
                return JsonResponse(get_error_context(False, "Invalid community_id"))

            engage_filter = Member_Engage.objects.filter(member_id=member_id, community_id=community_id
                                                         ).select_related('community_id')

            if not engage_filter.exists():
                community_context = create_community_context(community_id, member_id)
                return JsonResponse(community_context)

        else:
            if last_updated:
                engage_filter = Member_Engage.objects.filter(member_id=member_id, updated_at__gt=last_updated
                                                             ).select_related('community_id').order_by('updated_at')

            else:
                engage_filter = Member_Engage.objects.filter(member_id=member_id
                                                             ).select_related('community_id').order_by('updated_at')

        paginated_query_set = get_paginated_queryset_with_maxpages(engage_filter, page, paginate_by=paginate_by)
        engage_filter = paginated_query_set['page_list']
        temp = YourCommunitySerializer(engage_filter, context=context, many=True)

        max_last_updated = 0

        for data in engage_filter:

            if max_last_updated < data.updated_at:
                max_last_updated = data.updated_at

        if max_last_updated:
            context = {'communities': temp.data, 'max_last_updated': max_last_updated}
            return JsonResponse(context)

        return JsonResponse({'communities': []})


def fetch_community_of_chatroom(chatroom_id, member_id, last_updated=0):
    community_instance = Collabcard.get_community_of_chatroom_or_none(chatroom_id)

    if not community_instance:
        return {'communities': []}

    context = {"current_user_id": member_id}

    engage_filter = ModelUtilities.get_model_filter(Member_Engage, {'community_id': community_instance,
                                                                    'member_id': member_id})
    if engage_filter.exists():
        last_updated_filter = engage_filter.filter(updated_at__gt=last_updated)

        temp = YourCommunitySerializer(engage_filter, context=context, many=True)

        if last_updated_filter:
            community_context = temp.data
            chatroom_context = {'communities': community_context, 'last_updated': last_updated_filter[0].updated_at}

            return chatroom_context

        else:
            return {'communities': []}
    else:
        state_filter = Collabcard.objects.filter(id=chatroom_id).select_related('community')

        if state_filter.exists():
            temp = CommunitySerializerV1([state_filter[0].community], context=context, many=True)
            community_context = []

            member_state_filter = ModelUtilities.get_model_filter(Members,
                                                                  {"community_id": state_filter[0].community,
                                                                   "member_id": member_id})

            if member_state_filter:

                for community_ctx in temp.data:
                    community_ctx['member_state'] = member_state_filter[0].state
                    community_context.append(community_ctx)

            chatroom_context = {'communities': community_context}

        else:
            chatroom_context = {'communities': []}

    return chatroom_context


def create_community_context(community_id, member_id):
    communities = []
    community_instance = Community.get_community_or_raise_exception(community_id)
    community_list = CommunitySerializerV1(community_instance, context={"current_user_id": member_id}, many=False)
    communities.append(community_list.data)

    return {'communities': communities}


def fetch_guest_communities(member_id, last_updated=0):
    community_list = list(collabcardState.objects.filter(is_guest=True, user_id=member_id).
                          distinct('community').values_list('community_id', flat=True))

    guest_community_relation = list(Member_Engage.objects.filter(member_id=member_id).values_list('community_id',
                                                                                                  flat=True))

    state_filter = Community.objects.filter(id__in=community_list, updated_at__gt=last_updated).order_by('updated_at')

    guest_communities, max_last_updated = fill_guest_communities(state_filter, member_id, guest_community_relation)

    if max_last_updated:
        return {
            'communities': guest_communities,
            'max_last_updated': max_last_updated
        }

    return {'communities': guest_communities}


def fill_guest_communities(state_filter, member_id, guest_community_relation):
    context = {"current_user_id": member_id, 'restrict_members_count': True}

    communities = []
    max_last_updated = 0

    for community_instance in state_filter:

        if community_instance.id in guest_community_relation:
            continue

        community_list = CommunitySerializerV1(community_instance, context=context, many=False)
        communities.append(community_list.data)

        if max_last_updated < community_instance.updated_at:
            max_last_updated = community_instance.updated_at

    return communities, max_last_updated


def get_chatroom_data_in_case_of_guest(chatroom_id, member_id):
    try:
        chatroom_instance = Collabcard.objects.get(id=chatroom_id)

    except Exception as e:
        error_logger.error(e.args)
        return []

    member_data = {'member_id': member_id,
                   'current_user_id': member_id,
                   'state_instance': None}
    chatroom = GetChatroomInstanceSerializer(chatroom_instance, context=member_data, many=False)
    chatroom_context = chatroom.data
    chatroom_context['follow_status'] = False
    chatroom_list = [chatroom_context]

    return chatroom_list


def get_user_related_chatrooms(member_id, paginate_by, page, last_updated, chatroom_status, type_list):
    """
    This function returns chatrooms based on different conditions
    chatroom_status = followed/unfollowed
    """
    chatroom_data = []
    chatroom_id_list = []

    if chatroom_status:

        if chatroom_status == "followed":
            chatroom_data, chatroom_id_list = fetch_chatroom_query_with_follow_status(member_id, paginate_by, page,
                                                                                      last_updated,
                                                                                      follow_status=True,
                                                                                      type_list=type_list)

        elif chatroom_status == "unfollowed":
            chatroom_data, chatroom_id_list = fetch_chatroom_query_with_follow_status(member_id, paginate_by, page,
                                                                                      last_updated,
                                                                                      follow_status=False,
                                                                                      type_list=type_list)

    else:
        chatroom_data, chatroom_id_list = fetch_chatrooms_query(member_id, paginate_by, page, last_updated,
                                                                type_list=type_list)

    return chatroom_data, chatroom_id_list


def add_community_settings_for_community(community_instance, user_instance):
    community_settings_list = []

    for setting_type, setting_title in COMMUNITY_SETTING_TYPE_TITLE_MAPPING.items():
        is_enabled = True

        if setting_type in [community_setting_types.DIRECT_MESSAGES, community_setting_types.MEMBERS_CAN_DM,
                            community_setting_types.DIRECT_MSGS_GROUP_MSGS, community_setting_types.FEED]:
            is_enabled = False

        community_settings_data = {
            'community_instance': community_instance,
            'setting_type': setting_type,
            'setting_title': setting_title,
            'setting_sub_title': COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING.get(setting_type),
            'enabled': is_enabled,
            'enabled_by': user_instance,
        }
        community_settings_instance = CommunitySettings.create_instance(community_settings_data)
        community_settings_list.append(community_settings_instance)

    ModelUtilities.bulk_create_instances(CommunitySettings, community_settings_list)


def update_community_get_started(community_instance, community_get_started_type, is_enabled=False):
    community_get_started_instances = ModelUtilities.get_model_filter(CommunityGetStarted,
                                                                      {'community': community_instance})

    if (community_get_started_type == get_started_types.CREATE_COMMUNITY_TYPE) and \
            not len(community_get_started_instances):

        community_get_started_instance_list = []

        for get_started_instance in ModelUtilities.get_model_filter(GetStarted, {}):
            community_get_started_instance_list.append(CommunityGetStarted.create_instance({
                'get_started': get_started_instance,
                'community': community_instance,
                'completed': is_enabled if (get_started_instance.type == get_started_types.CREATE_COMMUNITY_TYPE)
                else False
            }))

        ModelUtilities.bulk_create_instances(CommunityGetStarted, community_get_started_instance_list)

    else:

        community_get_started_instance = community_get_started_instances.filter(
            get_started__type=community_get_started_type)

        if community_get_started_instance:
            community_get_started_instance = community_get_started_instance[0]
            community_get_started_instance.completed = is_enabled
            community_get_started_instance.save()


@shared_task
def check_join_community_hood_get_started(user_id, community_id):
    member_filter = ModelUtilities.get_model_filter(Members,
                                                    {'member_id': user_id,
                                                     'state': member_states.ADMIN})

    if len(member_filter):

        for member_instance in member_filter:
            update_community_get_started(member_instance.community_id, get_started_types.JOIN_COMMUNITY_HOOD,
                                         is_enabled=True)
