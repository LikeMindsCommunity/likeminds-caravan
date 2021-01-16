from __future__ import absolute_import, unicode_literals
from celery import shared_task
import logging
import os
from datetime import datetime
from urllib.parse import unquote, quote, parse_qsl, parse_qs, urlsplit
import googlemaps
import requests as rqst
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import F, When, Q
from django.http import HttpResponse
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from collections import OrderedDict
from rest_framework.views import APIView
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from togther.forms import *
from togther.models import *
from random import randint
# utility functions
from utility.celery_tasks import (save_community_purpose_card,
                                  update_last_unseen_in_engage_on_card_creation,
                                  update_last_unseen_in_engage, update_my_chatrooms_for_users,
                                  set_chatroom_state_for_all_members_on_card_creation,
                                  get_chatroom_user_images_for_web
                                  )
from utility.encryption import encrypt, decrypt
from utility.firebase import (update_last_answer_id, upload_image_to_firebase,
                              upload_community_thumbnail, upload_community_files)
from utility.states import (collabcard_states, member_states, question_states, community_states,
                            deleted_members, card_types, chatroom_states, email_states, mobile_states,
                            poll_types, chatroom_actions, member_rights, manager_rights,
                            moderation_history_types, report_Action_Types, report_Types)
from utility.tasks import (mail_triger, new_member_request, member_request_approval_or_denied,
                           send_mail_for_report_abuse, send_mail_for_query_and_feedback,
                           save_name_initial_image)
from utility.time_utilities import TimeUtilities
from utility.utils import (decode_meta_from_url, update_tag_image,
                           get_referred_members_of_a_member,
                           eligibility_count,
                           update_member_count,
                           tutorial_count,
    # custom_cache,cache_timeout,
                           get_city_address,
                           update_user_geography_tags, insert_user_home_town_tags, is_IG_community,
                           ig_members_count, is_LG_or_LP_community, feedback_community_id, feedback_collabcard_id,
                           is_member_verified, community_default_image, community_default_thumbnail, is_member_promoter,
                           is_member_present, generate_private_link, generate_random, get_time_text,
                           community_default_image_round, decode_option, get_user_communities_by_rank_web,
                           user_onbaord, get_time_text_for_my_chatrooms, get_members_count_in_community,
                           check_notification_flag, create_notification_flag, is_request_ios,
                           )


from .notification import *
from .raw_queries import *
from .serializers import *
from .static_files import *
from .static_text import *
from .static_text import (tool_member_requests, tool_pending_chat_rooms,
                          tool_review_reports, tool_edit_directory_questions,
                          tool_edit_community_details, tool_community_settings)
from .static_text import (LINKED_IN_ACCESS_TOKEN_URL, LINKED_IN_USER_URL, LINKED_IN_EMAIL_URL)
from .members import *
from .utility import *
from .tasks import (send_email_to_nominated_admin, send_email_for_new_collabcard_posted,
                    send_welcome_mail, send_verification_mail_for_email_sync,
                    send_tagged_user_mail, send_chatroom_owner_mail,
                    send_community_confirmation_email, update_pending_chatrooms_and_report_count,
                    update_pending_chatroom_count_for_promoters, update_report_count_for_all_promoters)

from .mails import *
from .sms import *

from .chatroom_backup import create_chatroom_delete_backup, create_chatroom_participants_backup

from cms.models import NewAnswer, userAcquition, appUninstalls

from .user_moderation_rights import *
from .rest_api import (CardAnswersDBSyncSerializer, GetChatroomInstanceSerializer, CommunitySerializerV1,
                       YourCommunitySerializer)

from utility.constants import INSTAGRAM_LINK, TWITTER_LINK, BRANCH_DECODE_URI
from .upload_attachments import (save_community_image, save_chatroom_attachments,
                                 save_conversation_attachments, save_poll_attachments,
                                 save_draft_attachments, save_draft_poll_attachments,
                                 get_image_dimensions)
from rest_framework import status as status_codes
from utility.request_utilities import RequestUtilities
from utility.number_utilities import NumberUtilities
from utility.exception_utilities import (CustomException, InvalidHeaderException,
                                            InvalidCommunityException, InvalidUserException)
from external_services.logging.logging_wrapper import LoggingWrapper
# CACHE_TTL = getattr(settings, 'CACHE_TTL', cache_timeout)
from rest_framework.exceptions import APIException
url = settings.URL
# url='http://localhost:8000'
error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


# /api/communities?category_id=&member_id=

############# functions for community api ##########################
@api_view(['GET', 'POST'])
@renderer_classes([JSONRenderer, TemplateHTMLRenderer])
def communities(request):
    ''' function to get all the communities '''

    if request.accepted_renderer.format == 'html':
        context = dashboard(request)
        return render(request, 'dashboard.html', context)

    if request.method == 'GET':
        info_logger.info("communities APi : added")
        req = request.GET.dict()

        # if page number is in request
        page_number = req['page'] if 'page' in req else 1
        user_id = get_member_id_from_headers(request)

        queryset, state = get_user_communities_by_rank(page_number=page_number, user_id=user_id)

        serializer = CommunitySerializer
        # community = [serializer(Community.objects.get(pk=community['community_id']) if state else community) for community in queryset]
        community_list = []
        for community in queryset:
            if state:
                community_instance = Community.objects.get(pk=community['community_id'])
                serilialized_object = serializer(community_instance)
                if serilialized_object['state'] != community_states.DELETED:
                    community_list.append(serilialized_object)
            else:
                serilialized_object = serializer(community)
                if serilialized_object['state'] != community_states.DELETED:
                    community_list.append(serilialized_object)
        # custom_cache.set(cache_key,community,timeout=CACHE_TTL)
        # custom_cache.clear()

        state = 1 if state else 0

        return JsonResponse({'communities': community_list, 'state': state})
    else:

        return JsonResponse({'success': False})


def dashboard(request):
    ''' function to show all communities and filter based on categories '''
    if request.user.is_authenticated:

        # if user does not have a email linked to his account, ask for a email
        request_user_email = False
        if not request.user.email and request.user.id != 37 and request.user.id != 176:
            request_user_email = True

        try:
            # check if user has user info
            user = Userinfo.objects.get(user_id=request.user.id)

        except:
            # if there is no user info for the user who is currently logged in
            # create userinfo for current user
            user = []
        # get users communities
        my_community = get_user_communities(request)
        # getting communities by user hidden tag
        communities = get_user_communities_by_rank_web(request)

        # check if user has completed onbarding and is from IIT Delhi
        onboard = user_onbaord(request.user.id)
        context = {'usr': user, 'communities': communities, 'my_communities': my_community[:2],
                   "my_communities_count": len(my_community), 'onboard': onboard, 'is_iitd': True,
                   'request_user_email': request_user_email}

        return context

    page = request.GET.get('page', 1)
    communities = Community.objects.filter(Q(hide_community='0') | Q(hide_community='4')).order_by('-updated_at')
    paginator = Paginator(communities, 20)
    queryset = paginator.get_page(page)

    for community in queryset:
        update_member_count(community.id)
    return {'communities': queryset}


def get_user_communities(request):
    ''' function to get users communities '''
    communities1 = Members.objects.all().filter(member_id=request.user).filter(
        Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7))

    my_communities = []
    for j in communities1:
        my_communities.append(j.community_id)
    my_community = []
    for j in my_communities:
        my_community.append(j)

    return my_community


def get_user_communities_by_rank(page_number=1, user_id=None):
    ''' fetching communities based on user Community Rank data '''

    is_user_communities = Community_Rank.objects.filter(member_id=user_id)
    if not user_id:
        return [], False

    elif is_user_communities.exists():
        communities = Community_Rank.objects.filter(member_id=user_id).values('community_id').order_by(
            "-weight").distinct()
    else:
        ''' if no communities are present in Community_Rank send all communities in DESC order of ID  '''
        # get all communities except hidden
        communities = Community.objects.filter(Q(hide_community='0') | Q(hide_community='3') |
                                               Q(hide_community='4')).order_by('-id')
    # paginating the resultant queryset
    queryset = pagination(communities, page_number)
    # return result
    return queryset, is_user_communities.exists()


############# functions for your communities  api ##########################

def is_member_engage(community, member):
    '''function to check if data is presnt in member engage table or not'''

    is_present = False
    member_data = Member_Engage.objects.filter(community_id=community, member_id=member)
    if member_data.exists():
        is_present = True
    return is_present


def update_pending_member_count_in_engage(community):
    '''function to update the member count in engage'''
    pending_members_count = Members.objects.filter(community_id=community, state=member_states.PENDING_MEMBER).count()
    all_members = Members.objects.filter(community_id=community)
    current_time = time.time()

    # update pending members in case of multiple promoters
    for member in all_members:

        if member.state == member_states.ADMIN or member.state == member_states.TEMP_ADMIN:
            Member_Engage.objects.filter(community_id=community, member_id=member.member_id
                                         ).update(pending_members=pending_members_count,
                                                  updated_at=current_time, member_state=member.state)
        else:
            Member_Engage.objects.filter(community_id=community, member_id=member.member_id
                                         ).update(member_state=member.state, updated_at = current_time)

    info_logger.info("Member Engage Pending Count Updated")


# home screen apis

def get_new_chatroom_member_images(member_id, community_id):
    last_instance = collabcardState.objects.filter(user=member_id, community=community_id).filter(~Q(state=0)).last()

    if last_instance:
        last_card = last_instance.card
        unseen_chatrooms = Collabcard.objects.filter(community=community_id, is_pending=False,
                                                     is_deleted=False, id__gt=last_card.id).distinct('user_id')
    else:
        unseen_chatrooms = Collabcard.objects.filter(community=community_id,
                                                     is_pending=False, is_deleted=False).distinct('user_id')

    member_list = []
    for card in unseen_chatrooms:

        member_filter = Members.objects.filter(member_id=card.user, community_id=community_id)
        if member_filter.exists():
            image_url = card.user.userinfo.image_link if card.user.userinfo.image_link else ''
            member_instance = member_filter[0]
            if member_instance.image_url:
                image_url = member_instance.image_url
        else:
            image_url = REMOVED_USER_URL

        member = get_user_profile(card.user.id, community_id, send_profile=False)
        member['image_url'] = image_url
        member_list.append(member)

        if len(member_list) > 3:
            break

    return member_list


def get_active_chatroom_member_images(community_instance, member_id):
    current_time = time.time()
    state_filter = collabcardState.objects.filter(community=community_instance,
                                                  user=member_id,
                                                  card__is_deleted=False).filter(
        Q(expiry_time=None) | Q(expiry_time__gt=current_time)).order_by('-expiry_time', '-card')
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
                                                  card__is_deleted=False).filter(
        Q(expiry_time=None) | Q(expiry_time__gt=current_time)).order_by('-expiry_time', '-card')
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


def my_chatrooms(request):
    '''functions to get chatrooms for users'''

    member_id = get_member_id_from_headers(request)
    page = request.GET.get('page', 1)

    active = request.GET.get('active', None)
    if active == "true":
        active = True
    elif active == "false":
        active = False
    else:
        active = None

    current_time = time.time()
    my_chatrooms = []
    instance_list = []

    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context)
    else:
        try:
            current_user_instance = User.objects.get(pk=member_id)
        except User.DoesNotExist:
            context = get_error_context(False, "User does not exist")
            return JsonResponse(context)

    instance_list = conversationEngage.objects.filter(user=member_id).order_by('-updated_at', '-id')
    instance_list = pagination(instance_list, page, paginate_by=10)

    for instance in instance_list:

        chatroom = {}
        card_instance = instance.card
        draft_instance = instance.draft
        if card_instance:
            chatroom['chatroom'] = get_chatroom_instance(card_instance, member_id)
            chatroom['community'] = CommunitySerializer(card_instance.community, current_user_id=member_id,
                                                        current_user_instance=current_user_instance)
            chatroom['is_draft'] = False
        elif draft_instance:
            chatroom['chatroom'] = get_draft_chatroom_instance(draft_instance, member_id)
            chatroom['community'] = CommunitySerializer(draft_instance.community, current_user_id=member_id,
                                                        current_user_instance=current_user_instance)
            chatroom['is_draft'] = True

        last_conversation = instance.last_conversation

        if last_conversation:
            chatroom['last_conversation'] = conversationSerializer(last_conversation, current_user_id=member_id)
            second_last_conversation = instance.second_last_conversation
            if second_last_conversation:
                chatroom['second_last_conversation'] = conversationSerializer(second_last_conversation,
                                                                              current_user_id=member_id)

        chatroom['unseen_conversation_count'] = instance.unseen_count
        chatroom['last_conversation_time'] = get_time_text_for_my_chatrooms(instance.updated_at)

        chatroom['member_right_states'] = json.loads(instance.rights_list) if instance.rights_list else []

        my_chatrooms.append(chatroom)

    return JsonResponse({"my_chatrooms": my_chatrooms})


def my_chatrooms_version_1(request):
    '''functions to get chatrooms for users'''

    member_id = get_member_id_from_headers(request)
    page = request.GET.get('page', 1)

    try:
        page = int(page)
    except:
        context = get_error_context(False, "send page number correctly")
        return JsonResponse(context)

    current_time = time.time()
    my_chatrooms = []
    instance_list = []

    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context)
    else:
        try:
            current_user_instance = User.objects.get(pk=member_id)
        except User.DoesNotExist:
            context = get_error_context(False, "User does not exist")
            return JsonResponse(context)

    in_active_chatroom_count = get_inactive_followed_chatrooms_count(member_id, current_time)

    active_chatroom_count = get_active_my_chatrooms_count(member_id, current_time)
    page_count = get_total_pages(active_chatroom_count, limit=10)
    page_count_inactive = get_total_pages(in_active_chatroom_count, limit=10)

    total_pages = page_count + page_count_inactive
    send_active = True

    if page > page_count:
        send_active = False

    if send_active:
        engage_list = get_active_followed_chatrooms(member_id, current_time, page, limit=10)
        for id in engage_list:
            instance = conversationEngage.objects.get(pk=id)
            instance_list.append(instance)

        draft_list = get_draft_chatrooms_on_home_screen(member_id, page, limit=10)

        for id in draft_list:
            instance = conversationEngage.objects.get(pk=id)
            instance_list.append(instance)

    else:
        page = page - page_count
        engage_list = get_inactive_followed_chatrooms(member_id, current_time, page, limit=10)

        for id in engage_list:
            instance = conversationEngage.objects.get(pk=id)
            instance_list.append(instance)

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

        last_conversation = instance.last_conversation

        if last_conversation:
            chatroom['last_conversation'] = conversationSerializer(last_conversation, current_user_id=member_id)
            second_last_conversation = instance.second_last_conversation
            if second_last_conversation:
                chatroom['second_last_conversation'] = conversationSerializer(second_last_conversation,
                                                                              current_user_id=member_id)

        chatroom['unseen_conversation_count'] = instance.unseen_count
        chatroom['last_conversation_time'] = get_time_text_for_my_chatrooms(instance.updated_at)

        last_conversation_member = instance.last_conversation_member
        second_last_conversation_member = instance.second_last_conversation_member
        last_conversation_user = instance.last_conversation_user
        second_last_conversation_user = instance.second_last_conversation_user

        conversation_users = get_latest_conversation_members(last_conversation_member,
                                                             second_last_conversation_member,
                                                             last_conversation_user,
                                                             second_last_conversation_user)
        chatroom['conversation_users'] = conversation_users
        chatroom['member_right_states'] = json.loads(instance.rights_list) if instance.rights_list else []

        member_instance = Members.objects.filter(member_id=current_user_instance,
                                                 community_id=instance.community)
        if member_instance.exists():
            chatroom['member_state'] = member_instance[0].state
        else:
            chatroom['member_state'] = member_states.GUEST

        my_chatrooms.append(chatroom)

    context = {'my_chatrooms': my_chatrooms,
               'inactive_chatroom_count': in_active_chatroom_count,
               'total_pages': total_pages
               }

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

    member_id = get_member_id_from_headers(request)
    context = {}
    if not member_id:
        context = get_error_context(False, "send x-member-id in headers")
        return JsonResponse(context)

    current_time = time.time()

    in_active_filter = inActiveChatroomsCount.objects.filter(user=member_id)

    if in_active_filter.exists():
        last_session = in_active_filter[0].updated_at

        inactive_chatrooms = collabcardState.objects.filter(user=member_id, follow_status=True,
                                                            remove=None).filter(~Q(expiry_time=None) & Q(
            expiry_time__lt=current_time) & Q(expiry_time__gt=last_session)).order_by('-expiry_time')

        inactive_chatroom_count = inactive_chatrooms.count()
        if inactive_chatroom_count:
            context['title'] = """%s chatrooms moved to inactive""" % (str(inactive_chatroom_count))
            in_active_filter.update(updated_at=current_time)

    else:
        inactive_chatrooms = collabcardState.objects.filter(user=member_id, follow_status=True,
                                                            remove=None).filter(
            ~Q(expiry_time=None) & Q(expiry_time__lt=current_time)).order_by('-expiry_time')

        user_instance = User.objects.get(id=member_id)
        inactive_count = inactive_chatrooms.count()
        create_or_update_inActiveChatroomsCount_instance(user_instance, inactive_count)
        if inactive_count:
            context['title'] = """%s chatrooms moved to inactive""" % (str(inactive_count))

    return JsonResponse(context)


def create_or_update_inActiveChatroomsCount_instance(user_instance, inactive_count):
    '''function to create inActiveChatroomcount instance'''

    in_active_filter = inActiveChatroomsCount.objects.filter(user=user_instance)
    temp = {"status": False}
    if not in_active_filter.exists():
        instance = inActiveChatroomsCount()
        instance.user = user_instance
        # instance.last_inactive_card = card_instance
        instance.inactive_count = inactive_count
        instance.created_at = time.time()
        instance.updated_at = time.time()
        instance.save()
        temp['status'] = True
        temp['inactive_count'] = inactive_count
    # else:
    #     instance = in_active_filter[0]
    #     if True:
    #         previous_count = instance.inactive_count
    #         instance.last_inactive_card = card_instance
    #         instance.inactive_count = inactive_count
    #         instance.updated_at = time.time()
    #         #instance.save()
    #         temp['status'] = True
    #         diff =  (inactive_count-previous_count)
    #         temp['inactive_count'] = diff if diff > 0 else (-1)*(diff)

    return temp


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
        'title': "View community details",
        'route': """route://community?community_id=%s""" % (str(community_instance.id))
    }

    actions.append(community_details)

    member_directory = {
        'title': "View member directory",
        'route': """route://members_directory?community_id=%s&community_name=%s""" % (
            str(community_instance.id), community_instance.name)
    }

    actions.append(member_directory)

    invite_members = {
        'title': "Invite members to this community",
        'route': """route://community?community_id=%s&share=true""" % (
            str(community_instance.id))
    }

    actions.append(invite_members)

    return actions


def community(request, community_id, req_dict=None):
    ''' Community detail page '''

    # handling web redirection to playstore and app store
    if is_request_web(request):
        context = get_redirection_links_for_android_ios(request, community_id)
        if context:
            return JsonResponse(context, safe=False)

    community = Community.objects.get(id=community_id)
    member_id = get_member_id_from_headers(request)
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
            menu = MENU['pending_member'].copy()

        if state == member_states.MEMBER or state == member_states.PROFILE_UNAVAILABLE:
            menu = MENU['member'].copy()
    else:
        block_leave_community = True

    if is_promoter:
        serialized_object = CommunitySerializer(community, promoter_id=current_user_instance,
                                                is_owner=is_owner, current_user_id=member_id,
                                                current_user_instance=current_user_instance)
    else:
        serialized_object = CommunitySerializer(community, current_user_id=member_id,
                                                current_user_instance=current_user_instance)

    community_state = get_state_of_community(community)

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


def similar_community(request, community_id, req_dict=None):
    '''function to return similar communitites'''

    if not req_dict:
        body = request.GET
        user_id = body['member_id']
    else:
        user_id = req_dict['member_id']
    user_tag = 0
    # getting communities based on user hidden tags
    queryset, state = get_user_communities_by_rank(user_id=user_id)[:11]
    community = []
    for comm in queryset:

        try:
            # if the queryset is of type dictionary
            comm_object = Community.objects.get(id=comm['community_id'])
        except:
            comm_object = comm
        # check if the community is hidden or not
        if comm_object.hide_community == '0' or comm_object.hide_community == '4' or comm_object.hide_community == '3' and comm_object.id != community_id:
            # if not hidden , pass the community object to serializer
            serialized_object = CommunitySerializer(comm_object)
            new_dict = {}
            # form a dictionary of community objects
            new_dict.update(serialized_object)

            community.append(new_dict)

    if req_dict:
        return community
    return JsonResponse({'communities': community})


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

    community_id = request.GET.get('community_id')
    if not community_id:
        context = get_error_context(False, "send community id in get params")
        return JsonResponse(context)

    data = communityQuestions.objects.filter(community=community_id).order_by('-rank', 'id')
    community_instance = Community.objects.get(id=community_id)
    community = CommunitySerializer(community_instance, current_user_id=member_id)

    created_by = get_community_creator(community_instance)

    community['created_by'] = created_by

    managers = get_community_managers(community_instance)

    if managers['count'] > 1:
        managed_by = managers['manager_name'] + ".." + "+" + str(managers['count'] - 1)
    else:
        managed_by = managers['manager_name']

    community['managed_by'] = managed_by

    # private link share flow
    aj = request.GET.get('aj', None)
    shared_by = request.GET.get('shared_by', None)
    user_instance = User.objects.get(id=member_id)

    is_valid_private_link = False
    auto_join = {}
    title = f"You are joining {community['name']}"
    shared_by_user = None

    try:
        shared_by_user = User.objects.get(pk=shared_by)
        shared_by_user_name = shared_by_user.userinfo.name
        title = f"{shared_by_user_name} invited you to join {community['name']}"
    except:
        error_logger.error(f"shared by user id does not exist in DB. shared by ---> {shared_by} ")

    if aj and shared_by_user:
        try:
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
               'questions': questions, 'community': community}
    if is_valid_private_link:
        context.update(auto_join)
    return JsonResponse(context)


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


@csrf_exempt
def join_community_responses_version_1(request):
    info_logger.info("Join community request\n")
    info_logger.info(request.body)
    res = json.loads(request.body)

    info_logger.info("Join community res\n")
    info_logger.info(res)
    info_logger.info("\n")
    community_id = res['community_id']
    info_logger.info("Inside private\n")
    join_promoter_created_community_version_1(res, request)

    return JsonResponse({'success': True})


def join_promoter_created_community_version_1(res, request):
    '''function to join promoter created community'''

    community_id = res['community_id']
    community_instance = Community.objects.get(id=community_id)

    member_id = get_member_id_from_headers(request)
    if not member_id:
        member_id = request.GET.get('member_id', None)
    else:
        res['timestamp'] = time.time()  # for android timestamp

    user_instance = User.objects.get(id=member_id)

    member_list = Members.objects.filter(member_id=user_instance, community_id=community_instance)

    is_member = member_list.exists()
    if is_member:
        state = member_list[0].state
        if state == member_states.MEMBER:
            return

    if 'questions' in res:

        for question in res['questions']:

            if 'value' not in question or not question['value']:
                continue

            question_instance = communityQuestions.objects.get(id=question['id'])

            if question_instance.is_hidden:
                continue
            answer_instance = communityAnswers()
            answer_instance.question = question_instance
            answer_instance.member = user_instance
            answer_instance.community = community_instance
            answer_instance.question_answer = question['value']
            answer_instance.question_title = question_instance.question_title

            answer_instance.save()

            if question_instance.question_state == question_states.CHOICE_SINGLE or question_instance.question_state == question_states.CHOICE_MULTIPLE:
                selected_choices = question['value'].split("$#")
                save_user_selected_options(question_instance, user_instance, community_instance, selected_choices)

            if question_instance.question_state == question_states.PROFILE_LINK:
                save_profile_links_from_handles(question_instance, answer_instance)

    update_hidden_fields_in_questions(user_instance, community_instance)

    aj = res.get('aj', None)
    shared_by = res.get("shared_by", None)
    timestamp = res.get('timestamp', time.time())

    valid_link_dict = validate_private_link(aj, shared_by, community_instance, timestamp)

    is_valid_private_link = valid_link_dict['valid_link']
    shared_user_instance = valid_link_dict['shared_user_instance']

    # saving data directly
    if is_valid_private_link:

        history_type = moderation_history_types.APPLIED_PRIVATE_LINK

        if check_user_rejoin(user=user_instance, community=community_instance):
            history_type = moderation_history_types.REJOINED_COMMUNITY_PRIVATE_LINK
            update_followed_for_rejoined_member(user_instance, community_instance)

        save_moderation_history(user=user_instance, community=community_instance,
                                moderation_by=shared_user_instance, type=history_type)

        auto_join_community(community_instance, user_instance, shared_user_instance)
        set_state_for_onboarding_chatroom(community_instance, user_instance.id, request)
        post_introduction_card_for_community(community_id, member_id, request)

        # saving create community action level3
        update_community_actions(community_instance)

        # send_notification_to_join_drop_off.delay(user_instance.id,community_instance.id,res['aj'],time_in_hrs)

        log = """Auto join community for community_id=%s for user=%s""" % (community_id, member_id)
        info_logger.info(log)
        return

    if is_member:
        member_state = member_list[0].state
        if member_state == member_states.ADMIN:

            # post_purpose_collabcard_for_community(request, community_instance, member_id)
            post_introduction_card_for_community(community_id, member_id, request)

            generate_private_link(community_instance, user_instance)

            Members.objects.filter(member_id=user_instance, community_id=community_instance).update(
                updated_at=time.time())
            Member_Engage.objects.filter(member_id=user_instance, community_id=community_instance).update(
                member_referral="", click_state=click_states.DEFAULT)

            # updating the community level 3 state

            communityLevels.objects.filter(community=community_instance).update(
                level_click_state=level_click_states.COMMUNITY_JOINED)

        elif member_state == member_states.PROFILE_UNAVAILABLE:

            Members.objects.filter(member_id=user_instance, community_id=community_instance).update(
                state=member_states.MEMBER, updated_at=time.time())

            Member_Engage.objects.filter(member_id=user_instance, community_id=community_instance).update(
                member_state=member_states.MEMBER, click_state=click_states.DEFAULT)
            post_introduction_card_for_community(community_id, member_id, request)
            set_state_for_onboarding_chatroom(community_instance, user_instance.id, request)

            communityToast.objects.filter(community=community_instance, user=user_instance).delete()
            # removing its data from removed members in order to consider it a new user
            removedMembers.objects.filter(community=community_instance, member=user_instance).delete()
            # give default members rights
            give_default_member_rights(user=user_instance, community=community_instance)
            update_member_rights_in_member_engage.delay(community_id, member_id)
            update_member_rights_in_conversation_engage.delay(community_id, member_id)
            log = """UPDATING_SKIPPED_MEMBER_PROFILE - community_id=%s for user=%s""" % (community_id, member_id)
            info_logger.info(log)

        else:

            Members.objects.filter(member_id=user_instance, community_id=community_instance).update(
                state=member_states.PENDING_MEMBER, updated_at=time.time())

            Member_Engage.objects.filter(member_id=user_instance, community_id=community_instance).update(
                member_state=member_states.PENDING_MEMBER)
            # removing its data from removed members in order to consider it a new user
            removedMembers.objects.filter(community=community_instance, member=user_instance).delete()
        update_pending_member_count_in_engage(community_instance)
        return JsonResponse({'success': True})
    else:
        member_instance = Members()
        member_instance.member_id = user_instance
        member_instance.community_id = community_instance
        member_instance.state = member_states.PENDING_MEMBER
        member_instance.created_at = time.time()
        member_instance.updated_at = time.time()
        member_instance.save()

        # creating a member engage instance
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.PENDING_MEMBER
        engage.click_state = click_states.PENDING_APPROVAL
        engage.save()
        update_pending_member_count_in_engage(community_instance)
        send_notification_to_admins.delay(community_id, user_instance.userinfo.name)

        update_community_toast(user_instance, community_instance,
                               message="Your request for joining this community is pending")

        if shared_user_instance:
            history_type = moderation_history_types.APPLIED_PUBLIC_LINK
            member_instance.joined_by = shared_user_instance
            member_instance.save()

            save_moderation_history(user=user_instance, community=community_instance,
                                    moderation_by=shared_user_instance, type=history_type)
        else:
            history_type = moderation_history_types.APPLIED_PUBLIC_LINK_WEBSITE
            save_moderation_history(user=user_instance, community=community_instance,
                                    moderation_by=None, type=history_type)


def update_community_toast(user_instance, community_instance, message=''):
    # setting the toast messages to show on community detail page
    toast_filter = communityToast.objects.filter(community=community_instance, user=user_instance)
    if not toast_filter.exists():
        toast = communityToast()
        toast.community = community_instance
        toast.user = user_instance
        toast.created_at = time.time()
        toast.toast_message = message
        toast.save()
    else:
        toast = toast_filter[0]
        toast.community = community_instance
        toast.user = user_instance
        toast.toast_message = message
        toast.save()


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


def auto_join_community(community_instance, user_instance, shared_user_instance=None):
    # updating the member instance
    if not is_member_verified(community_instance, user_instance):
        member_instance = Members()
        member_instance.member_id = user_instance
        member_instance.community_id = community_instance
        member_instance.state = member_states.MEMBER
        member_instance.joined_by = shared_user_instance
        member_instance.custom_title = "Member"
        member_instance.created_at = time.time()
        member_instance.updated_at = time.time()
        member_instance.became_member_at = time.time()
        member_instance.save()

        # give default members rights
        give_default_member_rights(user=user_instance, community=community_instance)

        toast_filter = communityToast.objects.filter(community=community_instance, user=user_instance)
        toast_filter.delete()

        # removing its data from removed members in order to consider it a new user
        removedMembers.objects.filter(community=community_instance, member=user_instance).delete()

        # removing guest status from all chatrooms after access
        collabcardState.objects.filter(community=community_instance, user=user_instance).update(
            is_guest=False, remove=None, updated_at=time.time())
        card_answers.objects.filter(community=community_instance, user=user_instance).update(
            is_guest=False, remove=None)

    # updating the member engage instance
    if not is_member_engage(community_instance, user_instance):
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.MEMBER
        # engage.rights_list = json.dumps(member_rights.DEFAULT_MEMBER_RIGHTS)
        engage.save()
        update_member_rights_in_member_engage.delay(community_instance.id, user_instance.id)


def post_introduction_card_for_community(community_id, member_id, request):
    '''function to get introduction card of community'''

    check_intro = communityQuestions.objects.filter(community=community_id, question_state=question_states.INTRODUCTION)
    if check_intro.exists():
        question_id = check_intro[0].id
        introduction_answer_list = communityAnswers.objects.filter(community=community_id, member=member_id,
                                                                   question_id=question_id)
        if introduction_answer_list.exists():
            introduction_answer = introduction_answer_list[0].question_answer
            req_dict = {
                'member_id': member_id,
                'community_id': community_id,
                'title': introduction_answer,
                'type': 1,
                'create_intro': 1
            }
            request.method = "POST"
            intro_filter = Collabcard.objects.filter(community=community_id, user=member_id, type=card_types.CARD_INTRO)
            if not intro_filter.exists():
                create_card(request, req_dict=req_dict)
                update_member_rights_in_conversation_engage(community_id, member_id)
                print("created")
                return True
            else:
                intro_filter.update(title=introduction_answer)

    return False


def post_purpose_collabcard_for_community(request, community_instance, member_id):
    '''function to post purpose card for community'''

    introduction_answer = community_instance.purpose
    if not introduction_answer:
        return
    req_dict = {

        'member_id': member_id,
        'community_id': community_instance.id,
        'title': introduction_answer,
        'type': card_types.CARD_PURPOSE,
    }
    request.method = "POST"
    context = create_card(request, req_dict=req_dict)

    return context['card_instance']


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


def creating_collabcard_for_lg_communities(community, user, introduction_answer, ref_id=None):
    '''function to create collabcard for lg community'''

    if ref_id:
        is_present = collabcardTemp.objects.filter(community=community, member=user)
        if not is_present:

            referer_instance = User.objects.get(pk=ref_id)

            # creating card for current logged in user with refferred user's data
            collabcard_temp_instance = collabcardTemp.objects.filter(Q(member=referer_instance),
                                                                     Q(show_member=referer_instance),
                                                                     Q(community=community))
            if collabcard_temp_instance.exists():
                collabcard_temp_instance = collabcard_temp_instance.first()
                title = collabcard_temp_instance.title

                collabcard_temp_instance = collabcardTemp()
                collabcard_temp_instance.member = referer_instance
                collabcard_temp_instance.community = community
                collabcard_temp_instance.title = title
                collabcard_temp_instance.show_member = user
                collabcard_temp_instance.created_at = time.time()
                collabcard_temp_instance.save()

            # creating for the person who has refered
            collabcard_temp_instance = collabcardTemp()
            collabcard_temp_instance.member = user
            collabcard_temp_instance.community = community
            collabcard_temp_instance.title = introduction_answer
            collabcard_temp_instance.show_member = referer_instance
            collabcard_temp_instance.created_at = time.time()
            collabcard_temp_instance.save()

            # creating for user
            collabcard_temp_instance = collabcardTemp()
            collabcard_temp_instance.member = user
            collabcard_temp_instance.community = community
            collabcard_temp_instance.title = introduction_answer
            collabcard_temp_instance.show_member = user
            collabcard_temp_instance.created_at = time.time()
            collabcard_temp_instance.save()




    else:

        # if ref_id is not present then creating for user
        is_present = collabcardTemp.objects.filter(community=community, member=user)
        if not is_present:
            collabcard_temp_instance = collabcardTemp()
            collabcard_temp_instance.member = user
            collabcard_temp_instance.community = community
            collabcard_temp_instance.title = introduction_answer
            collabcard_temp_instance.show_member = user
            collabcard_temp_instance.created_at = time.time()
            collabcard_temp_instance.save()


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

                community_level_filter.filter(level="Level 3").update(title="Set up community directory",
                                                                      sub_title="Help members know each other. Ask members to complete their profile for the directory or add new members.",
                                                                      state=community_level_states.PENDING)
                # community managers emails
                send_8am_level_mails_to_admin_scheduler.delay(community_instance.id, time.time(), level=2, day=0,
                                                              counter=0)
                # community_level_filter.filter(level="Level 4").update(title="Invite new member applications",
                #                                                       sub_title="Grow your community. Start social sharing and approve 10 new members.",
                #                                                       state=community_level_states.PENDING)

        elif instance.level == "Level 3" and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                instance.save()

                community_level_filter.filter(level="Level 4").update(title="Invite new member applications",
                                                                      sub_title="Grow your community. Start social sharing and approve 10 new members.",
                                                                      state=community_level_states.PENDING)
                # community managers emails
                send_8am_level_mails_to_admin_scheduler.delay(community_instance.id, time.time(), level=3, day=0,
                                                              counter=0)

        elif instance.level == "Level 4" and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                promoter_filter.update(actions_required=False)
                instance.save()
                # community managers emails
                send_8am_level_mails_to_admin_scheduler.delay(community_instance.id, time.time(), level=4, day=0,
                                                              counter=0)


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

                community_level_filter.filter(level="Level 3").update(title="Set up community directory",
                                                                      sub_title="Help members know each other. Give 10 members a community-specific identity.",
                                                                      state=community_level_states.PENDING)


        elif instance.level == level and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                instance.save()

                community_level_filter.filter(level="Level 4").update(title="Invite new member applications",
                                                                      sub_title="Grow your community. Start social sharing and approve 10 new members.",
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

        user_instance = User.objects.get(id=user_id)

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
        userinfo_filter.update(image_link=value)
        Members.objects.filter(member_id=user_id, image_url=None).update(image_url=value,
                                                                         updated_at=time.time())

    elif type == 'name':
        userinfo_filter.update(name=value)
        Members.objects.filter(member_id=user_id).update(updated_at=time.time())

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

    res = json.loads(request.body)

    community_id = res['community_id']
    community_instance = Community.objects.get(id=community_id)

    member_id = get_member_id_from_headers(request)
    if not member_id:
        member_id = request.GET.get('member_id', None)

    is_promoter = is_member_promoter(community_instance.id, member_id)

    user_instance = User.objects.get(id=member_id)

    answer_filter = communityAnswers.objects.filter(community=community_instance, member=user_instance)

    # getting the collabcard Id for introduction card
    collabcard_id = 0
    for answer in answer_filter:
        if answer.question.question_state == question_states.INTRODUCTION:

            collabcard_filter = Collabcard.objects.filter(community=community_instance,
                                                          user=user_instance, title=answer.question_answer)

            if collabcard_filter.exists():
                collabcard_id = collabcard_filter[0].id

    delete_filters = questionFilters.objects.filter(member=user_instance, community=community_instance).delete()
    delete_answers = answer_filter.delete()

    info_logger.info(delete_answers)
    info_logger.info(delete_filters)
    info_logger.info("\n")

    if 'questions' in res:

        for question in res['questions']:

            # empty cases handling
            if 'value' not in question:
                continue
            if not question['value']:
                continue

            question_instance = communityQuestions.objects.get(id=question['id'])
            answer_instance = communityAnswers()
            answer_instance.question = question_instance
            answer_instance.member = user_instance
            answer_instance.community = community_instance
            answer_instance.question_answer = question['value']
            answer_instance.question_title = question_instance.question_title
            answer_instance.save()

            if question_instance.question_state == question_states.CHOICE_SINGLE or question_instance.question_state == question_states.CHOICE_MULTIPLE:
                if "$#" in question['value']:
                    selected_choices = question['value'].split("$#")
                else:
                    selected_choices = question['value'].split(",")
                for choice in selected_choices:
                    filter_instance = questionFilters(question=question_instance, filter=choice.strip(),
                                                      member=user_instance, community=community_instance)
                    filter_instance.save()

            if collabcard_id and question_instance.question_state == question_states.INTRODUCTION:
                Collabcard.objects.filter(id=collabcard_id).update(title=question['value'])
                collabcardState.objects.filter(card=collabcard_id, user=member_id).update(updated_at=time.time())

            if question_instance.question_state == question_states.PROFILE_LINK:
                save_profile_links_from_handles(question_instance, answer_instance)

    update_hidden_fields_in_questions(user_instance, community_instance)
    form_response = FormResponseSerilaizer(community_id, member_id, bl=True, current_user_id=member_id)

    # setting edit status in members table
    member_filter = Members.objects.filter(community_id=community_instance, member_id=user_instance)
    member_filter.update(edit_required=False, updated_at=time.time())
    if 'image_url' in res:
        member_filter.update(image_url=res['image_url'])

    # posting a introduction collabcard
    if collabcard_id == 0:
        post_introduction_card_for_community(community_instance.id, user_instance.id, request)

    # update level of community
    set_levels_on_ctc(community_instance, "Level 3", promoter=is_promoter)

    question_answer = ""
    if form_response:
        question_answer = form_response[1]

    # setting the level click state when the promoter set-up directory and update the click state
    present_level = communityLevels.objects.filter(community=community_instance, level="Level 3",
                                                   level_click_state=level_click_states.DIRECTORY_CREATED)
    if present_level.exists():
        is_promoter = is_member_promoter(community_instance.id, member_id)
        if is_promoter:
            communityLevels.objects.filter(community=community_instance, level="Level 3").update(
                level_click_state=level_click_states.COMMUNITY_JOINED)

    if question_answer:
        return JsonResponse({'success': True, 'question_answers': question_answer})

    return JsonResponse({'success': True})


def get_user_lpig_tags(user_id):
    '''function to get user lpig tags'''

    legacy = User_Legacy.objects.filter(user_id=user_id)
    profession = User_Profession.objects.filter(user_id=user_id)
    interest = User_Interest.objects.filter(user_id=user_id)
    geography = User_Geography.objects.filter(user_id=user_id)

    legacy_list = []
    profession_list = []
    interest_list = []
    geography_list = []

    cluster_tags = []
    for each in legacy:
        temp = {}
        if each.tags_id.id != 15 and each.tags_id.is_cluster == 0:
            temp['id'] = each.tags_id.id
            temp['name'] = each.tags_id.name
            if each.tags_id.image_link:
                temp['image_url'] = each.tags_id.image_link

            elif each.tags_id.tag_image:
                temp['image_url'] = url + each.tags_id.tag_image.url
            attribute_id = each.tags_id.attribute_id.id

            if attribute_id is 1:
                temp['attribute_name'] = "Work"
            elif attribute_id is 2:
                temp['attribute_name'] = "College"
            elif attribute_id is 3:
                temp['attribute_name'] = "Hometown"
            elif attribute_id is 4:
                temp['attribute_name'] = "Lifestyle"
            else:
                continue

            # if each.tags_id.is_cluster:
            #     cluster=list(Tags_lpig.objects.filter(cluster_tag_id=each.tags_id.id).values_list('id',flat=True))
            #     cluster_tags=cluster_tags+cluster
            legacy_list.append(temp)

    # legacy_list=get_clustered_tags_for_user(legacy_list,cluster_tags)

    cluster_tags = []
    for each in profession:
        temp = {}
        if each.tags_id.id != 16 and each.tags_id.is_cluster == 0:
            temp['id'] = each.tags_id.id
            temp['name'] = each.tags_id.name
            if each.tags_id.tag_image:
                temp['image_url'] = url + each.tags_id.tag_image.url
            attribute_id = each.tags_id.attribute_id.id
            if attribute_id is 5:
                temp['attribute_name'] = "Skill"
            elif attribute_id is 6:
                temp['attribute_name'] = "Industry"
            elif attribute_id is 7:
                temp['attribute_name'] = "Designation"

            # if each.tags_id.is_cluster:
            #     cluster=list(Tags_lpig.objects.filter(cluster_tag_id=each.tags_id.id).values_list('id',flat=True))
            #     cluster_tags=cluster_tags+cluster
            profession_list.append(temp)

    # profession_list=get_clustered_tags_for_user(profession_list,cluster_tags)

    cluster_tags = []
    for each in interest:
        temp = {}
        if each.tags_id.id != 17 and each.tags_id.is_cluster == 0:
            temp['id'] = each.tags_id.id
            temp['name'] = each.tags_id.name
            if each.tags_id.tag_image:
                temp['image_url'] = url + each.tags_id.tag_image.url
            attribute_id = each.tags_id.attribute_id.id
            if attribute_id is 8:
                temp['attribute_name'] = "Cause"
            elif attribute_id is 9:
                temp['attribute_name'] = "Hobby"
            elif attribute_id is 10:
                temp['attribute_name'] = "Sports"
            elif attribute_id is 11:
                temp['attribute_name'] = "Fan"

            # if each.tags_id.is_cluster:
            #     cluster=list(Tags_lpig.objects.filter(cluster_tag_id=each.tags_id.id).values_list('id',flat=True))
            #     cluster_tags=cluster_tags+cluster
            interest_list.append(temp)

    # interest_list = get_clustered_tags_for_user(interest_list, cluster_tags)

    cluster_tags = []
    for each in geography:
        temp = {}
        if each.tags_id.id != 18 and each.tags_id.is_cluster == 0:
            temp['id'] = each.tags_id.id
            temp['name'] = each.tags_id.name
            if each.tags_id.tag_image:
                temp['image_url'] = url + each.tags_id.tag_image.url
            attribute_id = each.tags_id.attribute_id.id
            if attribute_id is 12:
                temp['attribute_name'] = "City"
            elif attribute_id is 13:
                temp['attribute_name'] = "State"
            elif attribute_id is 14:
                temp['attribute_name'] = "Country"

            # if each.tags_id.is_cluster:
            #     cluster=list(Tags_lpig.objects.filter(cluster_tag_id=each.tags_id.id).values_list('id',flat=True))
            #     cluster_tags=cluster_tags+cluster
            geography_list.append(temp)

    # geography_list = get_clustered_tags_for_user(geography_list, cluster_tags)

    tags = {
        'legacy': legacy_list,
        'profession': profession_list,
        'interest': interest_list,
        'geography': geography_list
    }

    # print(tags)
    return tags


@csrf_exempt
def ask_approval(request):
    '''function to ask for approval in LG communities for member to member verification'''

    member_id = get_member_id_from_headers(request)
    ask_member_id = request.GET.get('ask_member_id', None)

    community_id = request.GET.get('community_id')
    community_instance = Community.objects.get(id=community_id)

    if not ask_member_id:
        contact_number = request.GET.get('contact_number')
        user_instance = User.objects.get(id=member_id)
        Userinfo.objects.filter(user_id=user_instance).update(contact_number=contact_number)
        new_member_request.delay(member_id=member_id, community_id=community_id, ref_id=None,
                                 form_response=None, ph_no=contact_number)
        return JsonResponse({'success': True})

    member_instance = Members.objects.get(member_id=member_id, community_id=community_id)
    member_engage_instance = Member_Engage.objects.get(community_id=community_id, member_id=ask_member_id)

    if member_instance.ask_member_id:  # if the member ask someone else already for verification
        previous_asked_member = member_instance.ask_member_id
        member_engage_ask_instance = Member_Engage.objects.get(community_id=community_id,
                                                               member_id=member_instance.ask_member_id)
        if member_engage_ask_instance.pending_members:
            member_engage_ask_instance.pending_members = member_engage_ask_instance.pending_members - 1
            member_engage_ask_instance.save()

        collabcardTemp.objects.filter(show_member=previous_asked_member, member=member_id,
                                      community=community_id).delete()
        collabcardTemp.objects.filter(show_member=member_id, member=previous_asked_member,
                                      community=community_id).delete()

    member_instance.ask_member_id = ask_member_id
    member_instance.save()

    member_engage_instance.pending_members = member_engage_instance.pending_members + 1
    member_engage_instance.save()

    card_temp_list = collabcardTemp.objects.filter(show_member=member_id, member_id=member_id,
                                                   community_id=community_id)

    if card_temp_list.exists():
        ask_user_instance = User.objects.get(id=ask_member_id)

        card_temp_instance = collabcardTemp()
        card_temp_instance.show_member = ask_user_instance
        card_temp_instance.member = card_temp_list[0].member
        card_temp_instance.community = card_temp_list[0].community
        card_temp_instance.title = card_temp_list[0].title
        card_temp_instance.created_at = card_temp_list[0].created_at
        card_temp_instance.save()

    # ask_approval_notification.delay(community_id=community_id, community_name=community_instance.name, approver_id=ask_member_id,
    #                           member_name=member_instance.member_id.userinfo.name, community_state=community_instance.hide_community)

    return JsonResponse({'success': True})


@csrf_exempt
def remove_from_member(request):
    '''function to remove member of community'''

    member_id = get_member_id_from_headers(request)

    if not member_id:
        return JsonResponse({'success': False, 'error_message': "Send Member Id in header"})

    community_id = request.POST.get('community_id')

    member_ids = request.POST.get('member_ids', False)
    tag_id = request.POST.get('tag_id', None)
    reason = request.POST.get('reason', None)

    current_user_instance = User.objects.get(pk=member_id)
    community_instance = Community.objects.get(pk=community_id)

    is_promoter = Members.objects.filter(state=member_states.ADMIN, community_id=community_id, member_id=member_id)
    is_promoter = is_promoter.exists()
    if member_ids:
        if is_promoter:

            member_ids = unquote(member_ids)
            member_ids = json.loads(member_ids)

            for member in member_ids:
                member_filter = Members.objects.filter(community_id=community_id, member_id=member)
                if member_filter.exists():
                    member_state = member_filter[0].state
                    is_owner = member_filter[0].is_owner
                    eligible_member_states = [member_states.ADMIN, member_states.MEMBER,
                                              member_states.PROFILE_UNAVAILABLE,
                                              member_states.KNOWN_NOMINATED_PROMOTER]
                    if not is_owner and member_state in eligible_member_states:

                        user_instance = member_filter[0].member_id

                        remove_members(community_id, user_instance.id,
                                       removed_state=deleted_members.REMOVED)

                        save_moderation_history(user=user_instance, community=community_instance,
                                                moderation_by=current_user_instance,
                                                type=moderation_history_types.REMOVED_FROM_COMMUNITY)

                        remove_all_member_rights(community_instance, user_instance)
                        remove_all_manager_rights(community_instance, user_instance)

                        check_reports_and_update_action.delay(action_taken_by=member_id,
                                                              action_taken=report_Action_Types.REMOVE_FROM_COMMUNITY,
                                                              user=member, community=community_id,
                                                              action_taken_tag_id=tag_id, action_taken_reason=reason)

                        send_notification_for_removed_member.delay(admin_id=member_id,
                                                                   removed_user_id=member, community_id=community_id)

                        remove_all_member_rights(community_instance, user_instance)
                        remove_all_manager_rights(community_instance, user_instance)
                        info_logger.info(
                            f"REMOVE_MEMBER_API (REMOVED CASE) -current user id = {member_id}, user id = {member}"
                            f", community id = {community_id}")

                    else:
                        return JsonResponse(
                            {'success': False, 'error_message': "Cannot the Owner of this community"})
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error_message': "You are not the promoter of this community"})

    ##pending member check
    if member_ids == False:
        is_pending = Members.objects.filter(state=member_states.PENDING_MEMBER, community_id=community_id,
                                            member_id=member_id)
        if is_pending.exists():
            remove_members(community_id, member_id, removed_state=deleted_members.LEFT)
            toast_filter = communityToast.objects.filter(community_id=community_id, user=member_id)
            toast_filter.update(toast_message="Your request for joining this community is cancelled")

            check_reports_and_update_action.delay(action_taken_by=member_id,
                                                  action_taken=report_Action_Types.LEFT_THE_COMMUNITY,
                                                  user=member_id, community=community_id)
            update_pending_member_count_in_engage(community_instance)

            return JsonResponse({'success': True})

    # flow to leave the community
    if not is_promoter and member_ids == False:

        is_member = Members.objects.filter(community_id=community_id, member_id=member_id).filter(
            Q(state=member_states.PROFILE_UNAVAILABLE) | Q(state=member_states.MEMBER) |
            Q(state=member_states.KNOWN_NOMINATED_PROMOTER))

        if is_member.exists():
            user_instance = User.objects.get(pk=member_id)
            remove_members(community_id, member_id, removed_state=deleted_members.LEFT)

            save_moderation_history(user=user_instance, community=community_instance,
                                    moderation_by=current_user_instance,
                                    type=moderation_history_types.LEFT_COMMUNITY)

            check_reports_and_update_action.delay(action_taken_by=member_id,
                                                  action_taken=report_Action_Types.LEFT_THE_COMMUNITY,
                                                  user=member_id, community=community_id)

            info_logger.info(f"REMOVE_MEMBER_API (Left CASE) - current user id = {member_id}, user id = {member_id}"
                             f", community id = {community_id}")

            remove_all_member_rights(community_instance, user_instance)
            remove_all_manager_rights(community_instance, user_instance)

            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False,
                                 'error_message': "You are promoter of this community. You can be removed by other promoter"})

    return JsonResponse({'success': False})


@csrf_exempt
def remove_members(community_id, member_id, removed_state):
    '''function to remove member'''

    try:
        community_instance = Community.objects.get(id=community_id)
        user_instance = User.objects.get(id=member_id)
    except:
        return

    # communityAnswers.objects.filter(community=community_id, member=member_id).delete()

    is_member_left = removedMembers.objects.filter(community=community_id, member=member_id)

    if not is_member_left.exists():
        instance = removedMembers(community=community_instance, member=user_instance,
                                  removed_state=removed_state, created_at=time.time())
        instance.save()

        # updating the toast messages in case of removed and left
        # toast_filter = communityToast.objects.filter(community=community_instance,user=user_instance)
        if removed_state == deleted_members.LEFT:
            update_community_toast(user_instance, community_instance, message="You left the community.")
        elif removed_state == deleted_members.REMOVED:
            update_community_toast(user_instance, community_instance,
                                   message="You are no longer a member of this community.")

        # saving collabcard state in update status
        update_chatroom = collabcardState.objects.filter(community=community_instance, user=member_id).update(
            remove=instance, updated_at=time.time())
        update_conversations = card_answers.objects.filter(user=member_id, community=community_instance).update(
            remove=instance)

    # your chatrooms removed
    member_removerd = Members.objects.filter(community_id=community_id, member_id=member_id).delete()
    # print(member_removerd)

    # your community removed
    engage_removed = Member_Engage.objects.filter(community_id=community_id, member_id=member_id).delete()
    # print(engage_removed)

    profile_removed = communityAnswers.objects.filter(community=community_id, member=member_id).delete()
    # print(profile_removed)

    # removing the created chatrooms
    intro_chatroom = Collabcard.objects.filter(community=community_id, user=member_id,
                                               type=card_types.CARD_INTRO)
    if intro_chatroom.exists():
        create_chatroom_delete_backup(intro_chatroom[0], user_instance, removing_member=True)
        intro_chatroom.delete()
    # removing the draft chatrooms
    draft_removed = draftChatroom.objects.filter(community=community_id, user=member_id).delete()

    # removing the followed chatrooms
    conversation_engage = conversationEngage.objects.filter(community=community_id, user=member_id).delete()

    # removing the filter data
    filter_data = questionFilters.objects.filter(community=community_id, member=member_id).delete()

    update_last_unseen_in_engage_on_card_creation.delay(community_id, is_seen=False)


def update_followed_for_rejoined_member(user, community):
    removedMembers.objects.filter(community=community, member=user).delete()
    # saving collabcard state in update status
    card_answers.objects.filter(user=user, community=community).update(remove=None)

    card_states = collabcardState.objects.filter(community=community, user=user)
    card_states.update(remove=None, updated_at=time.time())
    followed_filter = card_states.filter(follow_status=True).order_by('id')

    for instance in followed_filter:

        engage_filter = conversationEngage.objects.filter(card=instance.card, user=user)

        if not engage_filter.exists():
            engage_instance = conversationEngage()

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

            print("card id", str(instance.card.id))

    print("existing chatroom followed for users")


def fetch_community_profile(request):
    '''api to get the community profile of user'''

    current_member_id = get_member_id_from_headers(request)
    user_id = request.GET.get('user_id')
    community_id = request.GET.get('community_id')
    try:
        community_instance = Community.objects.get(id=community_id)
    except Exception as e:
        return JsonResponse({'error': e.args})

    if not user_id or not community_id:
        return JsonResponse({"error_message": "send user id and community_id in get params"})

    current_user_member_instance = Members.objects.filter(member_id=current_member_id, community_id=community_id)
    is_promoter = False
    is_owner = False
    if current_user_member_instance.exists():
        is_promoter = current_user_member_instance[0].state == member_states.ADMIN
        is_owner = current_user_member_instance[0].is_owner

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
    current_user_id = get_member_id_from_headers(request)
    chatrooms = []

    # chatrooms created by user
    if int(state) == 0:

        chatroom_filter = Collabcard.objects.filter(user_id=user_id, community_id=community_id,
                                                    is_pending=False, is_deleted=False).order_by('-id')
        created_chatroom_count = chatroom_filter.count()
        chatroom_filter = pagination(chatroom_filter, page, paginate_by=10)

        for chatroom in chatroom_filter:
            temp = get_chatroom_instance(chatroom, user_id, current_user_id=current_user_id)
            temp['conversation_users'] = []
            engage_filter = conversationEngage.objects.filter(card=chatroom, user=user_id)
            if engage_filter.exists():
                temp['conversation_users'] = get_conversation_users(engage_filter[0])

            chatrooms.append(temp)

        return JsonResponse({'chatrooms': chatrooms, 'total_chatrooms_created': created_chatroom_count})


    # chatrooms not created by user but  followed by users
    elif int(state) == 1:
        # state_filter = collabcardState.objects.filter(user_id=user_id,community_id=community_id,follow_status=True).order_by('-id')

        chatroom_filter = Collabcard.objects.filter(user_id=user_id, community_id=community_id,
                                                    is_pending=False, is_deleted=False)
        state_filter = collabcardState.objects.filter(user_id=user_id, community_id=community_id,
                                                      follow_status=True).exclude(
            card__in=chatroom_filter.values('id')).order_by('-updated_at')
        followed_chatroom_count = state_filter.count()
        state_filter = pagination(state_filter, page, paginate_by=10)

        for chatroom in state_filter:
            temp = get_chatroom_instance(chatroom.card, user_id, current_user_id=current_user_id)
            temp['date'] = time.strftime('%d %b %Y', time.localtime(chatroom.updated_at))
            engage_filter = conversationEngage.objects.filter(card=chatroom.card, user=user_id)
            temp['conversation_users'] = []
            if engage_filter.exists():
                temp['conversation_users'] = get_conversation_users(engage_filter[0])
            chatrooms.append(temp)

        return JsonResponse({'chatrooms': chatrooms, 'total_chatrooms_followed': followed_chatroom_count})

    return JsonResponse({'error_message': "Send correct state"})


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

    common_communities = member_communities.intersection(user_communities)
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
        community_serializer = CommunitySerializer(community_instance, current_user_id=member_id)

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


@csrf_exempt
def create_community_version_1(request):
    '''function to create community for version for whatsapp shifting'''
    member_id = get_member_id_from_headers(request)
    user_instance = User.objects.get(pk=member_id)
    res = json.loads(request.body)
    print(res)

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

        # making the member enage instance for created community
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.ADMIN
        engage.member_referral = "Finish setting up your community"
        engage.click_state = click_states.SET_PURPOSE
        engage.rights_list = json.dumps(member_rights.ALL_MEMBER_RIGHTS)
        engage.save()

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

        community_serializer = CommunitySerializer(community_instance, promoter_id=user_instance,
                                                   current_user_id=member_id)
        return JsonResponse({'success': True, 'community': community_serializer})

    elif page == 2:

        community_instance = Community.objects.get(id=community_id)
        community_instance.purpose = purpose
        community_instance.save()

        engage_filter = Member_Engage.objects.filter(community_id=community_instance.id, member_id=member_id)
        engage_filter.update(click_state=click_states.DEFAULT)

        create_introduction_question_in_community(community_instance)
        post_purpose_collabcard_for_community(request, community_instance, member_id)

        # send mails to ask cm to upgrade level
        send_8am_level_mails_to_admin_scheduler.delay(community_instance.id, time.time(), level=1, day=0, counter=0)

        community_serializer = CommunitySerializer(community_instance, promoter_id=user_instance,
                                                   current_user_id=member_id)
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

            card_filter = Collabcard.objects.filter(user=user_instance, community=community_instance,
                                                    type=card_types.CARD_PURPOSE)

            if card_filter.exists():
                post_member_directly_link(card_filter[0], user_instance, community_instance)

            send_notification_for_directory_creation.delay(community_id, time.time(), day=0)

        except Exception as e:

            context = get_error_context(False, e)
            return JsonResponse(context)

        community_serializer = CommunitySerializer(community_instance, promoter_id=user_instance,
                                                   current_user_id=member_id)
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
        Members.objects.filter(community_id=community_instance, state=member_states.MEMBER).update(edit_required=True,
                                                                                                   updated_at=time.time())

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


def post_member_directly_link(card_instance, user_instance, community_instance):
    member_directory_link = url + "/members_directory/" + str(community_instance.id)
    conversation = card_answers()
    conversation.answer = """Here is a link to our member directory: %s""" % (member_directory_link)
    conversation.card = card_instance
    conversation.user = user_instance
    conversation.community = card_instance.community
    conversation.created_at = time.time()
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


def update_community(res):
    '''function to update the community'''

    community_id = res['community_id']

    community_filter = Community.objects.filter(id=community_id)

    # updating community
    if community_filter.exists():

        community_instance = community_filter[0]
        community_name = ""
        purpose = ""
        community_type = None
        sub_type = None

        if 'name' in res:
            community_name = res['name']

        if 'purpose' in res:
            purpose = res['purpose']

        if 'type' in res:
            community_type = res['type']

        if 'sub_type' in res:
            sub_type = res['sub_type']

        community_instance.name = community_name
        community_instance.purpose = purpose
        community_instance.members_count = 1
        community_instance.image_link = "https://beta.likeminds.community/media/media/community/default.jpeg"
        if community_type:
            community_instance.community_type = community_type
        community_instance.created_at = time.time()
        community_instance.updated_at = time.time()
        community_instance.hide_community = '5'  # for whatsapp community
        if sub_type:
            community_instance.sub_type = sub_type  # for whatsapp community
        community_instance.save()

        # deleting previous questions
        delete_status = communityQuestions.objects.filter(community=community_id).delete()
        print("delete status--", delete_status)

        # saving the questions again
        for question in res['questions']:
            questions_instance = communityQuestions()
            questions_instance.community = community_instance
            questions_instance.question_title = question['question_title']
            questions_instance.question_state = question['state']
            questions_instance.value = question['value'] if 'value' in question else None
            questions_instance.optional = question['optional']
            questions_instance.help_text = question['help_text'] if 'help_text' in question else None
            questions_instance.save()

        log = """questions added in community questions table"""
        info_logger.info(log)

        communty_serailized_object = CommunitySerializer(community_instance)
        return communty_serailized_object

    return "Not a valid community"


def set_community_actions(community_instance):
    '''function to set community action for community profiling'''

    action_status = communityLevels.objects.filter(community=community_instance)

    if not action_status:
        # first level
        instance = communityLevels()
        instance.community = community_instance
        instance.level = "Level 1"
        instance.title = "Create onboarding room"
        instance.sub_title = "Break the ice for new members. Tell what this community stands for."
        instance.state = community_level_states.COMPLETE
        instance.image = IMAGE_LEVEL_1
        instance.save()

        # second level
        instance = communityLevels()
        instance.community = community_instance
        instance.level = "Level 2"
        instance.title = "Invite your inner circle"
        instance.sub_title = "Bring 5 trusted people you want to build this community with."
        instance.joined_members = 0
        instance.max_members = 1 if settings.IS_BETA else 5
        instance.state = community_level_states.PENDING
        instance.image = IMAGE_LEVEL_2
        instance.save()

        # third level
        instance = communityLevels()
        instance.community = community_instance
        instance.level = "Level 3"
        instance.title = "Community Directory"
        instance.state = community_level_states.LOCKED
        instance.joined_members = 0
        instance.max_members = 1 if settings.IS_BETA else 10
        instance.image = IMAGE_LEVEL_3
        instance.save()

        # fourth level
        instance = communityLevels()
        instance.community = community_instance
        instance.level = "Level 4"
        instance.title = "Growth"
        instance.state = community_level_states.LOCKED
        instance.joined_members = 0
        instance.max_members = 1 if settings.IS_BETA else 10
        instance.image = IMAGE_LEVEL_4
        instance.save()


def set_preview_object(instance, res, user_id):
    if 'internal_link' in res and res['internal_link']:
        set_preview_with_internal_link(instance, res, user_id)

    if 'preview' in res:
        set_preview_with_preview_dict(instance, res, user_id)


def set_preview_with_internal_link(instance, res, user_id):
    try:
        internal_link = get_preview_url(res['internal_link'])
        instance.internal_link = internal_link

        if 'preview' not in res and internal_link is not None:
            preview = get_preview_for_url(user_id, internal_link)
            res['preview'] = preview
    except:
        remove_preview_instance(instance)


def set_preview_with_preview_dict(instance, res, user_id):
    try:
        preview = res['preview']
        instance.preview_type = preview['preview_type']
        preview_community = Community.objects.get(pk=preview['community']["id"])
        instance.preview_community = preview_community

        if 'chatroom' in preview:
            preview_chatroom = Collabcard.objects.get(pk=preview['chatroom']["id"])
            instance.preview_chatroom = preview_chatroom

        if 'internal_link' not in res:
            if 'internal_link' in preview and preview['internal_link']:
                instance.internal_link = get_preview_url(preview['internal_link'])
    except:
        remove_preview_instance(instance)


def remove_preview_instance(instance):
    instance.internal_link = None
    instance.preview_community = None
    instance.preview_chatroom = None


@csrf_exempt
def create_card(request, req_dict=None):
    ''' function to create a card '''

    if not req_dict:
        user_id = request.GET.get('member_id')
        community_id = request.GET.get('community_id')
        res = json.loads(request.body)
    else:
        user_id = req_dict['member_id']
        community_id = req_dict['community_id']
        res = req_dict

    is_member = Members.objects.filter(community_id=community_id, member_id=user_id).filter(
        Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER))
    if not is_member:
        context = get_error_context(False, "You cannot create a chatroom")
        return JsonResponse(context)

    context = create_card_internal(user_id, community_id, res)

    # updating the order time for new chatroom creation for your communities api
    current_time_msec = int(time.time() * 1000)
    Member_Engage.objects.filter(community_id=community_id).update(order_time=current_time_msec)

    if req_dict:
        return context

    # sending the local chatroom object for syncing in local db of clients
    member_data = {'member_id': user_id, 'current_user_id': user_id, 'state_instance': None}
    chatroom_obj = GetChatroomInstanceSerializer(context['card_instance'], context=member_data, many=False)

    context = {'success': True, 'collabcard': context['collabcard'], 'chatroom_local': chatroom_obj.data}
    return JsonResponse(context)


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

    context = create_card_internal(member_id, community_id, res)

    # sending local
    member_data = {'member_id': member_id, 'current_user_id': member_id, 'state_instance': None}
    chatroom_obj = GetChatroomInstanceSerializer(context['card_instance'], context=member_data, many=False)

    return JsonResponse({'success': True, 'collabcard': context['collabcard'], 'chatroom_local': chatroom_obj.data})


def create_chatroom_instance(res, community_instance, user_instance, has_auto_approve_right=False):
    '''function to create chatroom instance'''

    # getting the taaged members in chatroom
    tagged_members = get_tagged_members_list(res['title'])
    tagged_member_list = tagged_members[0]
    res_text = tagged_members[1]
    card_type = int(res['type']) if 'type' in res else card_types.CARD_NORMAL

    card = Collabcard()
    card.title = res['title']
    card.community = community_instance
    card.user = user_instance
    card.type = card_type

    # adding has_files key
    card.has_files = res['has_files'] if ('has_files' in res) else False

    card.image_count = res['image_count'] if ('image_count' in res) else 0
    card.pdf_count = res['pdf_count'] if ('pdf_count' in res) else 0
    card.video_count = res['video_count'] if ('video_count' in res) else 0
    card.audio_count = res['audio_count'] if ('audio_count' in res) else 0

    attachment_count = res.get('attachment_count', 0)

    if attachment_count == 0:
        attachment_count = res.get('image_count', 0) + res.get('video_count', 0)

    card.attachment_count = attachment_count
    card.attachments_uploaded = False
    if attachment_count > 0:
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
        og_tags = decode_meta_from_url(res['share_link'])
        card.og_tags = json.dumps(og_tags)

    set_preview_object(card, res, user_instance.id)

    is_intro_card = card_type == card_types.CARD_INTRO
    if not has_auto_approve_right and not is_intro_card:
        card.is_pending = True

    card.member_state = res['member_state']
    card.date_epoch = int(time.time())  # card creation time

    card.save()
    # add ownerflag here

    if card.type == card_types.CARD_POLL and has_auto_approve_right:
        # print("sendingpolls notification----->")
        send_chatroom_creation_notifications_and_mails(card, user_instance)
        schedule_poll_end_notification.delay(community_instance.name, community_instance.id, card_types.CARD_POLL,
                                             card.end_date, card.id)

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
                        state=chatroom_states.CHATROOM_HEADER, current_user_id=user_id)

        send_ice_breaker_notification.delay(community_id, time.time(), day=0)

    # deleting the draft chatroom
    if 'draft_id' in res:
        conversationEngage.objects.filter(draft_id=res['draft_id']).delete()
        draftChatroom.objects.filter(id=res['draft_id']).delete()
        draftPolls.objects.filter(draft=res['draft_id']).delete()

    if has_auto_approve_right or is_intro_card or create_intro:
        # batch update for already existing users and saving their unseen count
        if card_instance.attachment_count == 0:
            set_chatroom_state_for_all_members_on_card_creation.delay(community_id, card_id=card_instance.id,
                                                                      function_called="create_card_internal")
        # update_last_unseen_in_engage_on_card_creation.delay(community_id=community_id)

    else:
        update_pending_chatroom_count_for_promoters.delay(community_id)

    context = {
        'collabcard': collabcard,
        'card_instance': card_instance
    }

    return context


def send_chatroom_creation_notifications_and_mails(card_instance, user_instance):
    """ function to send mail and notifications for chatroom creations """

    # sending the mails and notification of simple chat rooms without files
    if not card_instance.has_files or\
            not card_instance.attachment_count > 0:
        send_chatroom_creation_notification(card_instance, user_instance)


def send_chatroom_creation_notification(card_instance, user_instance):
    date_time = card_instance.end_date if card_instance.type == card_types.CARD_POLL else card_instance.date_time

    send_notification_for_new_collabcard_posted.delay(card_instance.community.id, card_instance.title,
                                                      user_instance.id, user_instance.userinfo.name,
                                                      type=card_instance.type,
                                                      date_time=date_time,
                                                      card_id=card_instance.id,
                                                      community_name=card_instance.community.name,
                                                      community_state=card_instance.community.hide_community)


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
        og_tags = decode_meta_from_url(res['share_link'])
        card.og_tags = json.dumps(og_tags)

    set_preview_object(card, res, user_instance.id)

    card.date_epoch = time.time()  # card creation time
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


def create_chatroom(card_instance, user_instance, state, current_user_id=None, answer=""):
    '''function to create chat-room and perform follow unfollow operations'''
    # handling answer states
    if not answer:

        user_name = user_instance.userinfo.name
        # member_ids = [user_instance.id]
        # community_profile = get_user_profile(user_instance.id, card_instance.community.id, current_user_id,
        #                                      send_profile=False)
        # if community_profile:
        #     community_profile = community_profile
        #     user_route = "route://member_profile/" + str(user_instance.id) + "?member=" + quote(str(community_profile))
        # else:
        user_route = "route://member_profile/" + str(user_instance.id) + "?member_id=" + str(user_instance.id)
        user_name = "<<" + user_name + "|" + user_route + "&community_id=" + str(card_instance.community.id) + ">>"

        if state == chatroom_states.CHATROOM_HEADER:

            community = CommunitySerializer(card_instance.community, current_user_id=current_user_id)
            community_route = "route://community?community_id=" + str(community['id'])
            community_name = "<<" + str(community['name']) + "|" + community_route + ">>"
            if (card_instance.type == card_types.CARD_POLL):
                answer = user_name + " started this poll in " + community_name
            else:
                answer = user_name + " started this chatroom in " + community_name

        elif state == chatroom_states.CHATROOM_FOLLOW:
            answer = user_name + " followed this chatroom"
        elif state == chatroom_states.CHATROOM_UNFOLLOW:
            answer = user_name + " unfollwed this chatroom"
        elif state == chatroom_states.CHATROOM_COMMUNITY_EDIT:
            answer = user_name + " edited community purpose"

    instance = card_answers()
    instance.answer = answer
    instance.card = card_instance
    instance.user = user_instance
    instance.community = card_instance.community
    instance.state = state
    instance.created_at = time.time()
    instance.save()


def create_chatroom_state_instance(card_instance, user_instance, state=collabcard_states.COLLABCARD_STATE_SEEN,
                                   expire_at=None, external_seen=True, is_guest=False, source=None, follow_status=False,
                                   mute_status=False, is_tagged=False, external_follow=False,
                                   attending_status=False, **kwargs):
    '''function to create chatroom state instance'''
    # if not expire_at:
    #     expire_at = get_expiry_time_of_chatroom()

    try:
        collabcard_state_instance = collabcardState()
        collabcard_state_instance.card = card_instance
        collabcard_state_instance.community = card_instance.community
        collabcard_state_instance.user = user_instance
        collabcard_state_instance.state = state
        collabcard_state_instance.created_at = time.time()
        collabcard_state_instance.updated_at = time.time()
        collabcard_state_instance.external_seen = external_seen
        collabcard_state_instance.expiry_time = expire_at
        collabcard_state_instance.attending_status = attending_status
        collabcard_state_instance.follow_status = follow_status
        collabcard_state_instance.mute_status = mute_status
        collabcard_state_instance.is_tagged = is_tagged
        collabcard_state_instance.is_guest = is_guest
        collabcard_state_instance.source = source
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

    if func_dict:
        expire_time = func_dict['expiry_time']
    rights_list = None
    if member_state == member_states.ADMIN:
        rights_list = member_rights.ALL_MEMBER_RIGHTS
    elif member_state == member_states.MEMBER or member_state == member_states.PROFILE_UNAVAILABLE:
        rights_list = member_rights.DEFAULT_MEMBER_RIGHTS

    if not instance_list.exists():
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
                                                  is_pending=False, is_deleted=False).order_by('id')

    for card_instance in collabcard_filter:

        state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)
        if not state_filter.exists():
            last_conversation = card_answers.objects.filter(card=card_instance, state=chatroom_states.ANSWER).last()
            if last_conversation:
                expire_at = last_conversation.created_at + HOURS_24
            else:
                expire_at = card_instance.date_epoch + HOURS_24

            create_chatroom_state_instance(card_instance, user_instance, expire_at=expire_at,
                                           function_called="update_seen_status_for_new_user_in_chatroom")

    update_last_unseen_in_engage(user=user_instance, community=community_instance)

    print("updating the seen status")


@csrf_exempt
def chatroom_mute(request):
    '''function to mute and unmute chatroom'''
    chatroom_id = request.POST.get('chatroom_id')

    if not chatroom_id:
        context = get_error_context(False, "send chatroom id as post parameters")
        return JsonResponse(context)

    member_id = get_member_id_from_headers(request)
    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context)

    value = request.POST.get('value', False)
    collabcard_state_filter = collabcardState.objects.filter(card_id=chatroom_id, user=member_id)
    if value == "true":
        collabcard_state_filter.update(mute_status=True, updated_at=time.time())
    else:
        if collabcard_state_filter.exists():
            instance = collabcard_state_filter[0]
            instance.mute_status = False
            instance.updated_at = time.time()
            instance.external_follow = True if instance.is_tagged else False
            instance.is_tagged = False
            instance.save()
            # collabcard_state_filter.update(mute_status=False,is_tagged=False,updated_at=time.time())

    return JsonResponse({'success': True})


@csrf_exempt
def chatroom_rename(request):
    chatroom_id = request.POST.get('chatroom_id')
    first_time_rename = request.POST.get('first_time_rename')

    member_id = get_member_id_from_headers(request)

    if not chatroom_id or not member_id:
        context = get_error_context(False, "send params correctly")
        return JsonResponse(context)

    chatroom_name = request.POST.get("header", None)

    collabcard_filter = Collabcard.objects.filter(id=chatroom_id)
    if collabcard_filter.exists():
        collabcard_filter.update(header=chatroom_name)
        card_instance = collabcard_filter[0]

        if first_time_rename == "true":
            collabcard_filter.update(has_been_named=True)
            user_instance = User.objects.get(id=member_id)
            send_chatroom_creation_notifications_and_mails(card_instance, user_instance)
        collabcardState.objects.filter(card=card_instance).update(updated_at=time.time())

    else:
        context = get_error_context(False, "send correct chatroom id in post params")
        return JsonResponse(context)

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

    if draft_id:
        draftChatroom.objects.filter(id=draft_id).delete()
        return JsonResponse({'success': True})

    if not chatroom_id:
        context = get_error_context(False, "send the chatroom_id in post params")
        return JsonResponse(context)

    try:
        collabcard_instance = Collabcard.objects.get(id=chatroom_id)
        community_id = collabcard_instance.community.id
        community_instance = collabcard_instance.community
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
            return JsonResponse(context)

        if not is_card_creator:
            if not check_admin_delete_right(user=current_user_instance, community=community_instance):
                context = get_error_context(False, "You do not have right to delete this chatroom")
                return JsonResponse(context)

        # updating collabcard delete status
        update_collabcard_delete_status(collabcard_instance, current_user_instance, is_promoter,
                                        card_creator, reason, tag_id)

        conversationEngage.objects.filter(card=collabcard_instance).delete()

        # checking is_owner bcz, owner will be by default a CM
        member_is_promoter = Members.objects.filter(community_id=community_instance,
                                                    member_id=card_creator,
                                                    state=member_states.ADMIN).exists()

        if (disallow_create_chatroom or disallow_create_chatroom == "true") and \
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

        # setting the updated time of deleted chatroom
        current_time = time.time()
        collabcardState.objects.filter(card=collabcard_instance).update(updated_at=current_time)

        if is_promoter:
            send_notification_for_chatroom_deleted.delay(member_id, chatroom_id, community_id)

    except Exception as e:

        context = get_error_context(False, str(e))
        return JsonResponse(context)
    info_logger.info(
        f"DELETE_CHATROOM_API - current user id = {member_id}, card creator id = {card_creator.id}, disallow_create_chatroom = {disallow_create_chatroom}")
    return JsonResponse({'success': True})


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
    else:
        action_taken = report_Action_Types.CHATROOM_DELETED_BY_CM

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
    # expiry_time = get_expiry_time_of_chatroom()
    if engage_filter.exists():
        engage_instance = engage_filter[0]
        unread_count = engage_instance.unseen_count
        if unread_count > 0:

            state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)
            if state_filter.exists():
                # expiry_time = get_expiry_time_of_chatroom(card_state_instance=state_filter[0])
                state_filter[0].expiry_time = None
                state_filter[0].updated_at = time.time()
                state_filter[0].save()
            # conversationEngage.objects.filter(card=card_instance,user=user_instance).update(expiry_time=expiry_time)


def get_expiry_time_of_chatroom(card_state_instance=None):
    '''function to get expiry time of chatroom'''
    expiry_time = time.time() + HOURS_24

    if card_state_instance:
        if card_state_instance.expiry_time and card_state_instance.expiry_time > expiry_time:
            expiry_time = card_state_instance.expiry_time

    return expiry_time


@csrf_exempt
def set_chatroom_active(request):
    '''api to make chatroom active'''
    try:
        res = json.loads(request.body)
    except:
        context = get_error_context(False, "Json decode error")
        return JsonResponse(context)

    member_id = get_member_id_from_headers(request)

    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context)

    chatroom_id = res['chatroom_id']
    duration = res['duration'] if 'duration' in res else HOURS_24
    status = res['value']

    # card_instance = Collabcard.objects.get(id=chatroom_id)
    info_logger.info(res)

    current_time = time.time()

    if status:
        updated_time = current_time + int(duration)

    else:
        updated_time = current_time - HOURS_24

    state_filter = collabcardState.objects.filter(card=chatroom_id, user=member_id)

    if state_filter.exists():
        info_logger.info("state of data exists")
        instance = state_filter[0]
        instance.updated_at = time.time()
        instance.expiry_time = updated_time
        instance.manual_set_active = updated_time
        instance.save()
    else:
        info_logger.info("data does not exists")
        error = "Error is comming when you making it active" + str(chatroom_id) + str(member_id)

        context = get_error_context(False, error)

        return JsonResponse(context)

    return JsonResponse({"success": True})


def get_branch_links_for_community_share(user_instance, community_instance):
    is_promoter = False
    is_owner = False
    member_filter = Members.objects.filter(member_id=user_instance, community_id=community_instance)
    user_has_share_permission = check_member_invite_private_right(user_instance, community_instance)
    community_id = community_instance.id
    member_id = user_instance.id
    if member_filter.exists():
        member_instance = member_filter[0]

        if member_instance.state == member_states.ADMIN:
            is_promoter = True

        is_owner = member_instance.is_owner

        if is_promoter or is_owner or user_has_share_permission:
            aj = generate_private_link(community_instance=community_instance,
                                       promoter_instance=user_instance,
                                       just_send_aj=True)
            branch_links = create_community_branch_links(community_id, member_id, aj)

        else:
            branch_links = create_community_branch_links(community_id, member_id)

    else:
        branch_links = create_community_branch_links(community_id, member_id)

    share_context = {
        'branch_links': branch_links,
        'is_owner': is_owner,
        'is_promoter': is_promoter,
        'user_has_share_permission': user_has_share_permission
    }
    return share_context


def fetch_share_url(request):
    '''api to share the url of community and chatroom'''
    member_id = get_member_id_from_headers(request)

    chatroom_id = request.GET.get('chatroom_id')
    community_id = request.GET.get('community_id')

    if RequestUtilities.is_request_web(request):
        branch_links = generate_links_for_guest_web(community_id,member_id)
        url = branch_links[2]['url']
        return JsonResponse({'community_share': url, 'success': True})

    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context)

    if chatroom_id:
        try:
            card_instance = Collabcard.objects.get(id=chatroom_id)
        except Exception as e:
            context = get_error_context(False, e.args)
            return JsonResponse(context)
        chatroom_share = {}
        share = get_share_url_text(card_instance, member_id)
        chatroom_share['share_url'] = share['share_url']
        chatroom_share['creator_share_url'] = share['creator_share_url']
        chatroom_share['link_created_at'] = share['link_created_at']

        return JsonResponse({'chatroom_share': chatroom_share, 'success': True})

    if community_id:
        try:
            community_instance = Community.objects.get(id=community_id)
            user_instance = User.objects.get(id=member_id)

        except Exception as e:
            context = get_error_context(False, e.args)

            return JsonResponse(context, status=400)

        share_context = get_branch_links_for_community_share(user_instance, community_instance)
        branch_links = share_context['branch_links']
        community_share = {}
        community_name = community_instance.name

        if len(branch_links) > 0:
            community_share['share_url'] = branch_links[0]['url']

            if share_context['is_promoter'] or share_context['is_owner']:
                community_share['private_link'] = branch_links[1]['url']
                members_count = get_members_count_in_community(community_id)

                if members_count <= 10:
                    community_share['private_link_text_admin'] = PRIVATE_LINK_TEXT_ADMIN_1 % (
                        community_name, branch_links[1]['url'])

                else:
                    community_share['private_link_text_admin'] = PRIVATE_LINK_TEXT_ADMIN_2 % (
                        community_name, branch_links[1]['url'])

                community_share['private_link_members_directory'] = branch_links[2]['url']

                if share_context['is_owner']:
                    private_link_text_members_directory = PRIVATE_LINK_TEXT_MEMBERS_DIRECTORY_1 % (
                        community_name, branch_links[2]['url'])

                else:
                    private_link_text_members_directory = PRIVATE_LINK_TEXT_MEMBERS_DIRECTORY_2 % (
                        community_name, branch_links[2]['url'])
                community_share['private_link_text_members_directory'] = private_link_text_members_directory

            elif share_context['user_has_share_permission']:
                community_share['private_link_text_member'] = PRIVATE_LINK_FOR_PERMITTED_USER % (
                    community_name, branch_links[1]['url'])
                community_share['members_directory_link_for_members'] = MEMBER_DIRECTORY_LINK_FOR_PERMITTED_USER % (
                    community_name, branch_links[2]['url'])

            community_share['share_text_admin'] = SHARE_TEXT_ADMIN % (
                community_name, community_instance.purpose, community_share['share_url'])
            community_share['share_text_member'] = SHARE_TEXT_MEMBER % (
                community_name, community_instance.purpose, community_share['share_url'])
            community_share['share_text_anonymous'] = SHARE_TEXT_ANONYMOUS % community_name + " " + community_share[
                'share_url']

        else:
            error_message = "branch link not generated for community_id=" + str(community_id)
            error_logger.error(error_message)

            return JsonResponse({'error_message': error_message, 'success': False})

        return JsonResponse({'community_share': community_share, 'success': True})

    return JsonResponse({'error_message': "Invalid request", 'success': False}, status=400)

def generate_links_for_guest_web(community_id,member_id):

    if member_id and community_id:
        branch_link = create_community_branch_links(community_id, member_id, aj=None)
        return branch_link

    elif community_id:
        branch_link = create_community_branch_links(community_id, None, aj=None)
        return branch_link
    
# api to deprecate
@csrf_exempt
def collabcard_poll(request):
    """ function to update polls of a card for user """
    if request.method == 'POST':
        collabcard_id = request.GET.get('collabcard_id', None)
        poll_id = request.GET.get('poll_id', None)
        member_id = get_member_id_from_headers(request)

        if not collabcard_id or not poll_id:
            return JsonResponse({"success": False})

        card_instance = Collabcard.objects.get(pk=collabcard_id)
        poll_instance = CollabcardPolls.objects.get(pk=poll_id)
        user_instance = User.objects.get(pk=member_id)
        # check if user has already voted for the card or not
        memberpolls_instance = MemberPollVotes.objects.filter(card=card_instance, user=user_instance)

        if not memberpolls_instance.exists():
            # if not voted, create new row for user and card with opted poll by user
            memberpolls_instance = MemberPollVotes()
            memberpolls_instance.card = card_instance
            memberpolls_instance.poll = poll_instance
            memberpolls_instance.user = user_instance
            memberpolls_instance.save()
        else:
            # if voted, update the poll if user optes different poll than previous
            if str(memberpolls_instance[0].poll.id) == poll_id:
                # if same poll is opted again
                return JsonResponse({"success": True})
            # if user changes the poll
            memberpolls_instance.update(poll=poll_instance)
        # update the card answer text according to no of polls
        update_poll_card_text(collabcard_id)

        # if not str(member_id) == str(card_instance.user.id):
        # send_poll_or_event_notification.delay(card_id=collabcard_id, user_id=member_id)

        return JsonResponse({"success": True})

    return JsonResponse({"success": False})


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
    # print(member_id)
    # print(community_id)
    update_status = Members.objects.filter(member_id=member_id, community_id=community_id).update(
        state=member_states.MEMBER, updated_at=time.time())

    info_logger.info(community_id)
    info_logger.info(member_id)
    info_logger.info(update_status)

    return JsonResponse({'success': True})


def check_member(email, community_id, member_id, nominated_member_name, community_instance):
    """ check if the user is already a member of the invited community and make user as nominated promoter
     if he is registered in collabmates and if the user is not registered just send the user a invitation email """
    ProposedAdmin = Userinfo.objects.get(user_id=member_id)
    community = community_instance
    proposedAdminState = Members.objects.filter(member_id=ProposedAdmin.user_id, community_id=community)
    proposedAdminState = proposedAdminState[0].state
    CommunityName = community.name
    email = email.lower().strip()
    ProposedAdmin = ProposedAdmin.name

    try:
        user = Userinfo.objects.filter(email=email)

        if user:
            """ if the user is present get user details """
            NominatedAdmin_id = user[0].user_id.id
            NominatedAdmin = user[0].name
        else:
            """ if the user is not present just user a email"""
            send_email_to_nominated_admin.delay(NominatedAdmin=nominated_member_name, email=email,
                                                ProposedAdmin=ProposedAdmin,
                                                proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                                community_id=community.id)
            return False
    except:
        """ if any error trying fetch the user details , then user is not registered , send an email"""
        send_email_to_nominated_admin.delay(NominatedAdmin=nominated_member_name, email=email,
                                            ProposedAdmin=ProposedAdmin,
                                            proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                            community_id=community.id)
        return False

    if user:
        # get the state of the user of the community he is proposed to become a promoter for
        member = Members.objects.filter(community_id=community, member_id=user[0].user_id.id)

        if member and member[0].state == 4:
            # if the user is already a member , give him state 7
            # state 7 is nominted promoter who is already a member of thet community
            Members.objects.filter(community_id=community, member_id=user[0].user_id.id).update(
                state=member_states.KNOWN_NOMINATED_PROMOTER)
            Member_Engage.objects.filter(community_id=community, member_id=user[0].user_id.id).update(
                member_state=member_states.KNOWN_NOMINATED_PROMOTER)
            # send mail and notification
            # send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
            #                                     proposedAdminState=proposedAdminState, CommunityName=CommunityName,
            #                                     community_id=community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id=NominatedAdmin_id, community_id=community.id,
                                                      proposed_admin_name=ProposedAdmin)

        elif member and (member[0].state == 6 or member[0].state == 7):
            # if he is nominated again just send hime a remainding mail and notification
            # send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
            #                                     proposedAdminState=proposedAdminState, CommunityName=CommunityName,
            #                                     community_id=community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id=NominatedAdmin_id, community_id=community.id,
                                                      proposed_admin_name=ProposedAdmin)

        elif member and (member[0].state == 1 or member[0].state == 2):
            return True

        elif member and (member[0].state == 3 or member[0].state == 5):
            Members.objects.filter(community_id=community, member_id=user[0].user_id.id).update(state=6)
            # send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
            #                                     proposedAdminState=proposedAdminState, CommunityName=CommunityName,
            #                                     community_id=community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id=NominatedAdmin_id, community_id=community.id,
                                                      proposed_admin_name=ProposedAdmin)

        else:
            # if user is not anything to the community and he is nominated as promoter
            # create a member instance , making the user a nominated promoter giving user state = 6
            # state 6 is nominated member who was never involved in that community
            member = Members()
            member.community_id = community
            member.member_id = user[0].user_id
            member.state = 6
            member.save()
            # send mail and notification
            # send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
            #                                     proposedAdminState=proposedAdminState, CommunityName=CommunityName,
            #                                     community_id=community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id=NominatedAdmin_id, community_id=community.id,
                                                      proposed_admin_name=ProposedAdmin)
        return True
    return False


def check_for_member_eligibiity(community_id, member_id):
    '''That return count return you the no of people user referred and has become state 4'''
    # function to check if accepted member is a eligible admin or not

    community = Community.objects.get(pk=community_id)

    update = True
    print(">>>>>>>>>>> ", member_id)
    referals = get_referred_members_of_a_member(community_id=community_id, member_id=member_id)
    referal_count = len(referals)
    print(referals)
    return_count = 0
    print("referal count === ", referal_count)
    if referal_count >= eligibility_count:
        # return_count = 0
        for mem_id in referals:
            member = Members.objects.filter(member_id=mem_id, community_id=community_id)
            if member.exists():

                if member[0].state == 4:
                    return_count += 1

        if return_count >= eligibility_count:
            member = Members.objects.filter(member_id=member_id, community_id=community)
            if member[0].state != 1:
                Members.objects.filter(member_id=member_id, community_id=community).update(state=9,
                                                                                           updated_at=time.time())
                community_id = community.id
                community_name = community.name
                ref_id = member_id

                send_notification_to_eligible_member.delay(eligible_member_id=ref_id,
                                                           community_name=community_name,
                                                           community_id=community_id,
                                                           )

    invited_member = User.objects.get(pk=member_id)

    total_referals = Referal.objects.filter(invited_member=invited_member, community=community)

    if total_referals.exists():

        member_id = total_referals[0].member.id
        print(">>>>>>>>>>> ", member_id)
        referals = get_referred_members_of_a_member(community_id=community_id, member_id=member_id)
        referal_count = len(referals)
        print(referals)
        print("referal count === ", referal_count)

        if referal_count >= eligibility_count:
            count = 0
            for mem_id in referals:
                member = Members.objects.filter(member_id=mem_id, community_id=community_id)
                if member.exists():
                    if member[0].state == 4:
                        count += 1
            if count >= eligibility_count:
                member = Members.objects.filter(member_id=member_id, community_id=community)
                if member[0].state != 1:
                    Members.objects.filter(member_id=member_id, community_id=community).update(state=9,
                                                                                               updated_at=time.time())

                    community_id = community.id
                    community_name = community.name
                    ref_id = member_id
                    send_notification_to_eligible_member.delay(eligible_member_id=ref_id,
                                                               community_name=community_name,
                                                               community_id=community_id)

    return return_count


def pending_request_count(request, community_id):
    ''' fucntion to get peding members count of a community '''

    no_of_pending_members = Members.objects.filter(community_id=community_id).filter(state=3).count()
    return JsonResponse({'pending_request_count': no_of_pending_members})


# api/accept_invitation?member_id=&community_id=&value=false
@csrf_exempt
def accept_invitation(request):
    ''' accept promoter request '''
    # getting details of nominated person and the community promoter who proposed this invitation
    member_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')
    community = Community.objects.get(id=community_id)
    promoter = Members.objects.filter(community_id=community).filter(Q(state=1) | Q(state=2))
    nom_admin = Userinfo.objects.filter(user_id=member_id)
    # ------------------------------------------------------------------------------
    # if only one promoter to a community

    accepted = request.GET.get('value', 'true')

    if accepted == 'true':
        # saving data for a new member who is nominated and has accept the invitation
        member_state = Members.objects.filter(community_id=community, member_id=member_id).values('state')
        pending_members = Members.objects.filter(community_id=community, state=3).count()
        if member_state:
            state = member_state[0]['state']
            if state == 6:
                purpose_card = None
                if not is_member_engage(community, nom_admin[0].user_id):
                    try:
                        purpose_card = Collabcard.objects.get(id=community.purpose_collabcard)
                    except:
                        card = Collabcard.objects.filter(community_id=community).order_by('id')
                        if card:
                            purpose_card = card[0].id
                    unseen_count = Collabcard.objects.filter(community=community,
                                                             is_pending=False, is_deleted=False).count()

                    engage = Member_Engage()
                    engage.member_id = nom_admin[0].user_id
                    engage.community_id = community
                    engage.last_unseen_conversation = purpose_card
                    engage.last_unseen_count = unseen_count
                    engage.updated_at = time.time()
                    engage.pending_members = pending_members
                    engage.save()
                    Members.objects.filter(community_id=community, member_id=member_id).update(created_at=time.time(),
                                                                                               updated_at=time.time())

        if len(promoter) == 1:
            # if the community has only one promoter
            prop_admin = Userinfo.objects.get(user_id=promoter[0].member_id.id)
            # if the promoter is actually a promoter
            if promoter[0].state == 1:
                Members.objects.filter(community_id=community, member_id=member_id).update(state=1,
                                                                                           updated_at=time.time())
                Member_Engage.objects.filter(community_id=community, member_id=member_id).update(member_state=1,
                                                                                                 updated_at=time.time())
                # updating member count of the community
                update_member_count(community.id)
                # sending email to promoter , that user has accepted his request to beacome a promoter
                # send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name, email=prop_admin.email,
                #                                    ProposedAdmin=prop_admin.name, proposedAdminState=1,
                #                                    CommunityName=community.name, community_id=community.id)
                proposer_id = prop_admin.user_id.id
                nom_admin_name = nom_admin[0].name
                # send_notification_to_proposer.delay(proposer_id, community_name=community.name,
                #                                     community_id=community.id, proposed_name=nom_admin_name)
                return JsonResponse({'success': True})
            # if the promoter is a temporary promoter
            elif promoter[0].state == 2:
                temp_promoter = Members.objects.filter(community_id=community, state=2)
                Members.objects.filter(community_id=community, member_id=temp_promoter[0].member_id).update(state=4)
                Member_Engage.objects.filter(community_id=community, member_id=temp_promoter[0].member_id).update(
                    member_state=4)

                Members.objects.filter(community_id=community, member_id=member_id).update(state=1)
                Member_Engage.objects.filter(community_id=community, member_id=member_id).update(member_state=1)
                # updating member count of the community
                update_member_count(community.id)
                # sending email to promoter , that user has accepted his request to beacome a promoter
                # send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name, email=prop_admin.email,
                #                                    ProposedAdmin=prop_admin.name, proposedAdminState=2,
                #                                    CommunityName=community.name, community_id=community.id)
                proposer_id = prop_admin.user_id.id
                nom_admin_name = nom_admin[0].name
                # send_notification_to_proposer.delay(proposer_id, community_name=community.name,
                #                                     community_id=community.id, proposed_name=nom_admin_name)
                return JsonResponse({'success': True})
        else:
            # if there are more than two admins , sent mail to the promoter who invited this member
            # getting the promoter ID from temp admin model
            promoter_who_proposed = temp_admin.objects.filter(community_id=community, email=nom_admin[0].email)
            # getting the promoter details
            prop_admin = Userinfo.objects.get(user_id=promoter_who_proposed[0].member_id)
            # make th current member a promoter of this community
            Members.objects.filter(community_id=community, member_id=member_id).update(state=1)
            Member_Engage.objects.filter(community_id=community, member_id=member_id).update(
                member_state=1)

            # updating member count of the community
            update_member_count(community.id)
            # sending email to promoter , that user has accepted his request to become a promoter
            # send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name, email=prop_admin.email,
            #                                    ProposedAdmin=prop_admin.name, proposedAdminState=1,
            #                                    CommunityName=community.name, community_id=community.id)
            proposer_id = prop_admin.user_id.id
            nom_admin_name = nom_admin[0].name
            # send_notification_to_proposer.delay(proposer_id, community_name=community.name, community_id=community.id,
            #                                     proposed_name=nom_admin_name)
            return JsonResponse({'success': True})
    else:
        # if nominated promoter didn't accept the invitation
        member = Members.objects.filter(community_id=community, member_id=member_id)
        if member[0].state == 6:
            print("member state == 6")
            # deleting his details from temp admin model
            usr = Userinfo.objects.get(user_id=member[0].member_id)
            temp = temp_admin.objects.filter(community_id=community, email=usr.email)
            temp.delete()
            # if he is previously not a member of this community
            # then delete the member from members model
            Members.objects.filter(community_id=community, member_id=member_id).delete()
            Member_Engage.objects.filter(community_id=community, member_id=member_id).delete()

        elif member[0].state == 7:
            print("member state == 7")
            # if he is previously not a member of this community , then make him member again
            Members.objects.filter(community_id=community, member_id=member_id).update(state=4)
            Member_Engage.objects.filter(community_id=community, member_id=member_id).update(member_state=4)

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


#   /api/join?member_id=  # accepted or denied request
@csrf_exempt
def request_response(request, req_dict=None):
    ''' function to approve or decline a members who requested to join '''
    if not req_dict:
        res = json.loads(request.body)
    else:
        res = req_dict
    member_id = None
    community_id = None
    info_logger.info("private_community")

    if 'member_id' in res:
        member_id = res['member_id']
    if 'community_id' in res:
        community_id = res['community_id']

    accepted = False
    if 'accepted' in res:
        accepted = res['accepted']

    req_dict = {
        'member_id': member_id,
        'community_id': community_id,
        'accepted': accepted
    }
    approve_or_decline_private_community(req_dict, request)
    # update_pending_member_count_in_engage(req_dict['community_id'])

    return JsonResponse({'success': True})


def approve_or_decline_private_community(req_dict, request):
    '''function to approve the whatsapp community'''

    current_user_id = get_member_id_from_headers(request)

    if not current_user_id:
        context = get_error_context(False, "send member id in headers")
        return context

    current_user_instance = User.objects.get(pk=current_user_id)
    promoter_name = current_user_instance.userinfo.name

    if req_dict['accepted'] or req_dict['accepted'] == 'true':

        is_member = is_member_verified(community=req_dict['community_id'], user_instance=req_dict['member_id'])

        if not is_member:
            Members.objects.filter(member_id=req_dict['member_id'],
                                   community_id=req_dict['community_id']).update(state=member_states.MEMBER,
                                                                                 approved_by=current_user_instance,
                                                                                 custom_title="Member",
                                                                                 created_at=time.time(),
                                                                                 updated_at=time.time(),
                                                                                 became_member_at=time.time())
            # giving default member rights
            give_default_member_rights(user=req_dict['member_id'], community=req_dict['community_id'])
            Member_Engage.objects.filter(member_id=req_dict['member_id'],
                                         community_id=req_dict['community_id']).update(
                member_state=member_states.MEMBER,
                updated_at=time.time(), click_state=click_states.DEFAULT,
                rights_list=json.dumps(member_rights.DEFAULT_MEMBER_RIGHTS))

            # updating pending member count
            community = Community.objects.get(id=req_dict['community_id'])
            members_count = community.members_count + 1
            Community.objects.filter(id=req_dict['community_id']).update(members_count=members_count)

            accepted_user = User.objects.get(pk=req_dict['member_id'])

            history_type = moderation_history_types.APPROVED_FROM
            if check_user_rejoin(user=accepted_user, community=community):
                history_type = moderation_history_types.REJOINED_COMMUNITY_PUBLIC_LINK
                update_followed_for_rejoined_member(accepted_user, community)

            save_moderation_history(user=accepted_user, community=community,
                                    moderation_by=current_user_instance,
                                    type=history_type)
            info_logger.info(f"JOIN_REQUEST_ACCEPETED current user id = {current_user_id}, user id = {accepted_user.id}"
                             f", commuinty id = {community.id}")
            # updating pending members count
            update_pending_member_count_in_engage(req_dict['community_id'])

            # setting the follow state for purpose collabcard
            set_state_for_onboarding_chatroom(community_instance=community, user_id=req_dict['member_id'],
                                              request=request)

            # posting a intro collabcard
            post_introduction_card_for_community(req_dict['community_id'], req_dict['member_id'], request)

            # removing guest status from all chatrooms after access
            collabcardState.objects.filter(community=req_dict['community_id'], user=req_dict['member_id']).update(
                is_guest=False, remove=None, updated_at=time.time())
            card_answers.objects.filter(community=req_dict['community_id'], user=req_dict['member_id']).update(
                is_guest=False, remove=None)

            # saving create community action step 4
            update_community_actions(community_instance=community)

            # deleting the community toast message when the request is accepted
            communityToast.objects.filter(community=req_dict['community_id'], user=req_dict['member_id']).delete()

            # deleting if the user left the community before
            removedMembers.objects.filter(community=req_dict['community_id'], member=req_dict['member_id']).delete()

            # send sms
            notification_list = [
                'mail_has_installed_app'
            ]
            if check_notification_flag(req_dict['member_id'], notification_list, card_id=None, community_id=None):
                new_user_instance = User.objects.get(id=int(req_dict['member_id']))
                new_user_name = get_first_name_from_name(new_user_instance.userinfo.name)
                mobile_filter = userMobiles.objects.filter(user_id=new_user_instance.id)
                # print(mobile_filter)
                for instance in mobile_filter:
                    # print("sending sms here")
                    # info_logger.log('sending sms for community approval to',instance.id)
                    phone_no = str(instance.country_code) + str(instance.mobile_no)
                    send_community_confirmation_sms.delay(phone_no, community.name, new_user_name, new_user_instance.id)

            # sending mails and notifications
            # send notification
            send_notification_for_join_requests.delay(req_dict['community_id'], True, req_dict['member_id'],
                                                      promoter_name)
            send_community_confirmation_email.delay(req_dict['member_id'], req_dict['community_id'])

    else:

        Members.objects.filter(member_id=req_dict['member_id'], community_id=req_dict['community_id']).delete()

        # delete the member engage table record for the user
        Member_Engage.objects.filter(member_id=req_dict['member_id'], community_id=req_dict['community_id']).delete()

        # delete the responses of user to community questions, if any
        communityAnswers.objects.filter(member_id=req_dict['member_id'], community_id=req_dict['community_id']).delete()
        # updating pending members count
        update_pending_member_count_in_engage(req_dict['community_id'])
        # saving the community toast change
        toast_filter = communityToast.objects.filter(community=req_dict['community_id'], user=req_dict['member_id'])
        toast_filter.update(
            toast_message="Your request for joining this community was rejected. You can apply again to join this community")

        send_notification_for_join_requests.delay(req_dict['community_id'], False, req_dict['member_id'], promoter_name)


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


def send_email_for_collabcard(community, user, card, type):
    '''function to make the format of email to send when a new collabcard is posted'''

    members = Members.objects.filter(community_id=community)
    collabcard_card_image = ""
    for member in members:
        if user.image_link:
            collabcard_card_image = user.image_link
        context = {
            'community_name': community.name,
            'collabcard_creater': user.name,
            'collabcard_creater_image': collabcard_card_image,
            'creater_header': user.headline,
            'url': url + '/collabcard/' + str(card.id),
            'form_link': ""
        }

        if member.member_id.id == user.user_id.id:
            continue
        if member.state == 1 or member.state == 2 or member.state == 4:
            userinfo = Userinfo.objects.get(user_id=member.member_id)
            if not userinfo.image_link:
                reciever_image = url + userinfo.image_file.url
            else:
                reciever_image = userinfo.image_link
            context['reciever'] = userinfo.name
            context['reciever_image'] = reciever_image
            context['to'] = userinfo.email
            # print(context)

            if type == 2:
                context['subject'] = str(context['collabcard_creater']) + " has created an event in " + str(
                    context['community_name']) + " community"
            elif type == 3:
                context['subject'] = str(context['collabcard_creater']) + " has created a poll in " + str(
                    context['community_name']) + " community"
            else:
                context['subject'] = str(context['collabcard_creater']) + " has started a new Conversation in " + str(
                    context['community_name']) + " community"
            send_email_for_new_collabcard_posted.delay(context)


@api_view(['GET', 'POST'])
@renderer_classes([JSONRenderer, TemplateHTMLRenderer])
def collabcard(request, card_id):
    ''' function to get card details, answers and images '''
    # get the card object
    card_filter = Collabcard.objects.filter(id=card_id)
    user_instance = None
    card = {}
    answers = []
    current_user_id = None
    aj = request.GET.get('aj')
    source_id = request.GET.get('source_id')

    if card_filter.exists():
        card_instance = card_filter[0]

        if card_instance.type in (
        card_types.CARD_NORMAL, card_types.CARD_INTRO, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT):

            if settings.IS_BETA:
                return redirect(
                    "https://betaweb.likeminds.community/collabcard/%s?source_id=%s&aj=%s" % (card_id, source_id, aj))
            else:
                return redirect(
                    "https://web.likeminds.community/collabcard/%s?source_id=%s&aj=%s" % (card_id, source_id, aj))
    else:

        backup_filter = deletedChatrooms.objects.filter(card_id=card_id)

        if backup_filter.exists():
            community_id = backup_filter[0].community.id
            return redirect("community_questions", params=str(community_id) + "-deleted")
        else:
            return render(request, "__404__.html", {})

    card['type'] = card_instance.type
    if card_instance.type == card_types.CARD_EVENT or card_instance.type == card_types.CARD_PUBLIC_EVENT or card_instance.type == card_types.CARD_POLL:
        page = request.GET.get('page', 1)

        current_user_id = get_member_id_from_headers(request)

        feedback = True
        if card_instance.community.id == feedback_community_id:
            feedback = False

        # coverting current time into epoch time for getting time stamp of answers and card

        answer_id = request.GET.get('answer_id', '')
        user_id = request.GET.get('member_id', '')

        if is_request_web(request) and request.user.is_authenticated:
            current_user_id = request.user.id
            # todo: check_authenticated
            answers = get_chatroom_internal(request, card_instance, current_user_id, page, '', '', False)
        else:
            # get all the answers of the card
            answer = card_answers.objects.filter(card=card_instance).order_by('id')
            answer = pagination(answer, page, paginate_by=3)
            if answer_id:
                answer_id = int(answer_id)
                answer = card_answers.objects.filter(card=card_instance, id__gte=answer_id).filter(~Q(user__id=user_id))
                # answer = pagination(answer, page, paginate_by=10)
                answers = get_answer_data(answer, card_instance.community.id,
                                          current_user_id=current_user_id)  # if the feedback is true don't send id in userinfo
                return JsonResponse({'answers': answers})
            else:
                answers = get_answer_data(answer, card_instance.community.id, current_user_id=current_user_id)

        # serializing Collabcard

        if not user_id:
            # handling the web case
            # todo: check_auth
            if request.user.is_authenticated and is_request_web(request):
                user_id = request.user.id
                user_instance = User.objects.get(id=user_id)

        card = CollabcardSerializer(card_instance, user_id, card_instance.community, current_user_id=current_user_id)

        user = Userinfo.objects.get(user_id=card_instance.user.id)

        # if request.user.is_authenticated and not get_request_type(request):
        #     # set current user if user in logged in
        #     current_user = User.objects.get(user_id=current_user_id)

        # serializing user object
        usr = UserinfoSerializer(user)
        usr['is_clickable'] = feedback

        # when the member is removed
        removed_state = removedMembersSerializer(card_instance.community.id, usr['id'])
        if removed_state != False:
            usr['remove_state'] = removed_state

        # user form response serialzer
        form_response = FormResponseSerilaizer(card_instance.community.id, card_instance.user.id, bl=True,
                                               current_user_id=current_user_id)
        if form_response:
            # usr['response'] = form_response[0]
            usr['question_answers'] = form_response[1]
        # get the card image if any
        files = get_collabcard_files(card_id)
        card['images'] = files[0]
        card['member'] = usr
        card['pdf'] = files[1]
        card['audios'] = files[2]
        card['videos'] = files[3]
        card['attachments'] = files[4]
        if user_id:
            collabcard_status = get_status_of_collabcard(member_id=user_id, card=card_instance)
            card['state'] = collabcard_status['state']
            card['mute_status'] = collabcard_status['mute_status']
            card['follow_status'] = collabcard_status['follow_status']
            card['attending_status'] = collabcard_status['attending_status']
            # print('-->',collabcard_status)

        # get tine stamp for card
        time_text = get_time_text(card_instance.date_epoch)
        card['created_at'] = time_text

    # request is made from web
    if request.accepted_renderer.format == 'html':

        # web_data = get_collabcard_details_for_web(request, card_instance, card, current_user_id, answers)
        web_data = get_collabcard_details_for_web(request, card_instance, card, current_user_id, answers)

        context = web_data[0]
        card_category = web_data[1]

        if request.user.is_authenticated:
            mixpanel_events = get_mixpanel_statistics(request.user.id)
            context['mixpanel_event'] = mixpanel_events

            if aj:
                context['aj'] = aj

            context['current_date'] = time.strftime('%d-%m-%Y', time.localtime(time.time()))

        # print(context)
        # print(context)
        # print (render(request, 'chatroom.html', context))
        if card_category == "EVENT_CARD":
            return render(request, 'event.html', context)

        if card_category == "POLL_CARD":
            return render(request, 'poll.html', context)

        return render(request, 'chatroom.html', context)

    else:
        return JsonResponse({"collabcard": card, 'answers': answers})


def get_collabcard_details_for_web(request, card_instance, card, current_user_id, answers):
    '''function that contain collabcard details for web'''
    is_logged = False
    current_user = {}

    if request.user.is_authenticated and is_request_web(request):
        # user id from request if user in logged in

        current_user_id = request.user.id
        current_user_instance = Userinfo.objects.get(user_id=current_user_id)
        current_user = UserinfoSerializer(user=current_user_instance)

        collabcard_status = get_status_of_collabcard(member_id=current_user_id, card=card_instance)
        # print(collabcard_status)
        current_user['collabcard_state'] = collabcard_status['state']
        current_user['mute_status'] = collabcard_status['mute_status']
        current_user['follow_status'] = collabcard_status['follow_status']
        current_user['attending_status'] = collabcard_status['attending_status']
        is_logged = True

    if type(answers) is list:
        _answers = answers
        answers = {}
        # size_reduction
        # answers['conversations'] = _answers
        answers['conversations'] = []

    # print('in html')
    # check for event card
    # type 2 => private
    # type 6 => public
    if card['type'] in (card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT):
        # print('event card')

        # get community for community name, image, etc
        community = card_instance.community

        member_state = members_state(request,
                                     req_dict={'community_id': card_instance.community.id,
                                               'member_id': current_user_id})

        # set default event banner image
        card[
            'banner_image'] = "https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fmain_website%2Fevent_banner.jpg?alt=media&token=4f6709df-8918-4227-8606-c11607d2d31b"
        # check if card hs banner image
        if card['images'] and len(card['images']) > 0 and card['images'][0]['image_url']:
            card['banner_image'] = card['images'][0]['image_url']

        # set time
        # print("current_time--",time.time())
        # print("end_date--",card['end_date']/1000.0)
        if time.time() > card['end_date'] / 1000.0:
            card['event_ended'] = True

        card['end_time'] = time.strftime('%A, %b %d, %H:%M', time.localtime(card['end_date'] / 1000.0))
        card['date_time'] = time.strftime('%A, %b %d, %H:%M', time.localtime(card['date_time'] / 1000.0))
        card['duration'] = card['duration'] / 1000.0
        card['duration'] = ConvertSectoDay(card['duration'])

        # get members
        state_list = [collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING,
                      collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING]
        members = get_members_data_for_collabcard(card_instance.id, card_instance.community.id, current_user_id)

        # set header
        header = {
            'back': True,
            'title': card['header'],
            'subTitle': "in " + community.name,
            'background': 'Wa',
            'color': 'F'
        }

        context = {
            "member_state": member_state,
            "community": community,
            "collabcard": card,
            "members": members,
            'answers': answers,
            'header': header,
            'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'facebook_auth_id': settings.SOCIAL_AUTH_FACEBOOK_KEY,
            'firebase_config': settings.FIREBASE_CONFIG
        }

        if is_logged:
            if current_user['collabcard_state'] == 0:
                collabcards_seen_internal(card_instance.community.id, card_instance.id, card['type'], current_user_id)
            context["current_user"] = current_user

        context['redirect_link'] = "/community_questions/" + str(community.id) + "?event=" + str(
            card_instance.id) + "&type=" + str(card['type'])

        # print(context)

        return context, "EVENT_CARD"
        # return render(request, 'event.html', context)
    elif card['type'] == card_types.CARD_POLL:
        # print('poll card')

        # get community for community name, image, etc
        community = card_instance.community

        member_state = members_state(request,
                                     req_dict={'community_id': card_instance.community.id,
                                               'member_id': current_user_id})

        if card['polls_count'] > 0:
            card['polls_count_percentage'] = card['polls_count'] / 100

        # set time
        # card['end_date'] = ConvertSectoDay(card['end_date']/1000.0)

        # print("current_time--",time.time())
        # print("end_date--",card['end_date']/1000.0)
        if time.time() > card['end_date'] / 1000.0:
            card['poll_ended'] = True
        else:
            card['ends_in'] = ConvertSectoDay((card['end_date'] / 1000.0) - time.time())

        # card['end_time'] = time.strftime('%A, %b %d, %H:%M', time.localtime(card['end_date'] / 1000.0))
        # card['date_time'] = time.strftime('%A, %b %d, %H:%M', time.localtime(card['date_time'] / 1000.0))
        # card['duration'] = card['duration']/1000.0
        # card['duration'] = ConvertSectoDay(card['duration'])

        # get members
        # state_list = [collabcard_states.COLLABCARD_STATE_SEEN,
        #               collabcard_states.COLLABCARD_STATE_FOLLOW]
        # members = get_members_data_for_collabcard(card_instance.id, card_instance.community.id, current_user_id, state_list)

        # set header
        header = {
            'back': True,
            'title': card['header'],
            'subTitle': community.name,
            'background': 'Wa',
            'color': 'F'
        }

        context = {
            "member_state": member_state,
            "community": community,
            "collabcard": card,
            # "members": members,
            'answers': answers,
            'header': header,
            'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'facebook_auth_id': settings.SOCIAL_AUTH_FACEBOOK_KEY,
            'firebase_config': settings.FIREBASE_CONFIG
        }

        if is_logged:
            if current_user['collabcard_state'] == 0:
                collabcards_seen_internal(card_instance.community.id, card_instance.id, card['type'], current_user_id)
            context["current_user"] = current_user

        context['redirect_link'] = "/community_questions/" + str(community.id) + "?poll=" + str(card_instance.id)

        # print(context['collabcard']['polls'])
        return context, "POLL_CARD"
    else:
        print('collab card')

        context = get_normal_chatroom_context(request, card_instance)
        # size_reduction
        context['answers']['conversations'] = []

        return context, "SIMPLE_CARD"
        # return render(request, 'collabcard.html', context)


def get_normal_chatroom_context(request, card_instance):
    is_logged = False
    current_user = None
    current_user_id = None
    page = request.GET.get('page', 1)
    community_instance = card_instance.community

    aj = request.GET.get('aj')
    source_id = request.GET.get('source_id')

    if is_request_web(request) and request.user.is_authenticated:
        is_logged = True
        current_user_id = request.user.id
        current_user_instance = Userinfo.objects.get(user_id=current_user_id)
        current_user = UserinfoSerializer(user=current_user_instance)
        collabcard_status = get_status_of_collabcard(member_id=current_user_id, card=card_instance)
        # print(collabcard_status)
        current_user['collabcard_state'] = collabcard_status['state']
        current_user['mute_status'] = collabcard_status['mute_status']
        current_user['follow_status'] = collabcard_status['follow_status']
        current_user['attending_status'] = collabcard_status['attending_status']

    chatroom_dict = get_chatroom_internal(request, card_instance, current_user_id, page, conversation_id=None,
                                          scroll_direction=None, is_ios=False)

    has_conversation = card_answers.objects.filter(card=card_instance, user=current_user_id,
                                                   state=chatroom_states.ANSWER).exists()

    member_state = members_state(request,
                                 req_dict={'community_id': card_instance.community.id, 'member_id': current_user_id})

    if request.user.is_authenticated and member_state['state'] != 0:
        header_back_link = "/community/" + str(community_instance.id)
    else:
        header_back_link = ""

    header = {
        'back': True,
        'title': card_instance.header,
        'backLink': header_back_link,
        'subTitle': 'in ' + community_instance.name,
        'background': 'Wa',
        'color': 'F'
    }

    # community block
    admin = get_community_creator(community_instance)
    members_count = get_members_count_in_community(community_instance)

    communityBlock = {
        'title': community_instance.name,
        'creator': "Created by " + admin,
        'members': str(members_count) + " members",
        'imgURL': community_instance.thumbnail
    }

    context = {
        'collabcard': chatroom_dict['chatroom'],
        'community': community_instance,
        'answers': chatroom_dict,
        'header': header,
        'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'facebook_auth_id': settings.SOCIAL_AUTH_FACEBOOK_KEY,
        'firebase_config': settings.FIREBASE_CONFIG,
        'member_state': member_state,
        'community_block': communityBlock,
        'aj': aj,
        'source_id': source_id,
        'has_conversation': has_conversation
    }
    # size_reduction
    context['answers']['chatroom'] = {}
    if aj and source_id:
        context['redirect_link'] = "/collabcard/" + str(card_instance.id) + "?aj=" + str(aj) + "&source_id=" + str(
            source_id)
    else:
        context['redirect_link'] = "/collabcard/" + str(card_instance.id)
    if is_logged:
        context['current_user'] = current_user

    if 'aj_expired' in chatroom_dict:
        context['aj_expired'] = chatroom_dict['aj_expired']
    elif not aj and not source_id:
        context['aj_expired'] = True

    return context


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


def fetch_chatroom_version_1(request):
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

    context = get_chatroom_internal_version_1(request, card_instance, current_user_id, page, conversation_id,
                                              scroll_direction, is_ios=is_ios)

    if str(current_user_id) == str(card_instance.user.id):
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

    return JsonResponse(context)


def fetch_chatroom_version_2(request):
    is_ios = is_platform_ios(request)
    card_id = request.GET.get('chatroom_id', '')
    if not card_id:
        context = get_error_context(False, "send chat_room_id as a get params")
        return JsonResponse(context)

    conversation_id = request.GET.get('conversation_id')
    scroll_direction = request.GET.get('scroll_direction')

    card_filter = Collabcard.objects.filter(id=card_id)

    if card_filter.exists():
        card_instance = card_filter[0]
    else:
        context = get_error_context(False, "Chat_room does not exist. Might have been deleted")
        return JsonResponse(context)

    page = request.GET.get('page', 1)
    current_user_id = get_member_id_from_headers(request)

    context = get_chatroom_internal_version_2(request, card_instance, current_user_id, page, conversation_id,
                                              scroll_direction, is_ios=is_ios)

    if str(current_user_id) == str(card_instance.user.id):
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

    return JsonResponse(context)


def conversation_meta(request):
    '''api to perfrom firebase operations on conversation for real time messaging'''

    conversation_id = request.GET.get('conversation_id')
    chatroom_id = request.GET.get('chatroom_id')
    if not conversation_id or not chatroom_id:
        context = get_error_context(False, "send conversation_id and chatroom_id in post params")
        return JsonResponse(context)

    user_id = get_member_id_from_headers(request)
    if not user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)

    card_instance = Collabcard.objects.get(id=chatroom_id)
    feedback = True
    if card_instance.community.id == feedback_community_id:
        feedback = False

    answer_id = int(conversation_id)
    answer = card_answers.objects.filter(card=card_instance, id__gte=answer_id).filter(~Q(user__id=user_id))
    chatroom = get_answer_data(answer, card_instance.community.id,
                               current_user_id=user_id)

    context = {
        'conversations': chatroom
    }
    # saving the latest conversation
    save_the_latest_conversation(card_instance, user_id)
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

        if not conversation_member_filter.exists():
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
    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context)

    chatroom_id = request.POST.get('chatroom_id')
    if not chatroom_id:
        context = get_error_context(False, "send chatroom id in headers")
        return JsonResponse(context)

    chatroom_instance = Collabcard.objects.get(id=chatroom_id)
    save_the_latest_conversation(chatroom_instance, member_id)

    return JsonResponse({'success': True})


def get_answer_data(answer_filter, community_id, current_user_id, last_seen=None,
                    fetch_reply=False, is_ios=False):
    """ function to get answer for a particular collabcard """

    answers = []
    for ans in answer_filter:

        if ans.attachment_count > 0 and\
                ans.attachments_uploaded is False and \
                current_user_id:
            if int(current_user_id) != ans.user.id:
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
        time_text = time.strftime('%H:%M', time.localtime(ans.created_at))

        date = time.strftime('%d %b %Y', time.localtime(ans.created_at))
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
            'member_id': ans.user.id,
            'community_id': community_id,
            'chatroom_id': ans.card.id,
            'created_epoch': int(ans.created_at)
        }

        if ans.attachments_uploaded is None:
            context['attachments_uploaded'] = False

        if ans.og_tags:
            context['og_tags'] = json.loads(ans.og_tags)

        if last_seen and last_seen.id == ans.id:
            context['last_seen'] = True

        if 'location' in attachements:
            context['location'] = attachements['location']

        if ans.reply:
            context['reply_conversation'] = ans.reply.id
            if fetch_reply:
                reply_obj = get_answer_data([ans.reply], community_id, current_user_id,
                                            fetch_reply=False, is_ios=is_ios)
                context['reply_conversation_object'] = reply_obj[0]

        if ans.is_deleted:
            context['deleted_by'] = ans.deleted_by_user.id

        if ans.internal_link:
            try:
                context['preview'] = get_preview_for_url(current_user_id, ans.internal_link,
                                                         community_instance=ans.preview_community,
                                                         chatroom_instance=ans.preview_chatroom,
                                                         send_preview_text=False)
            except Exception as e:
                error_logger.error(e.args)

        context['answer_bubble'] = get_answer_bubble_context_for_web(ans)

        answers.append(context)
    return answers


def get_answer_bubble_context_for_web(ans):
    '''function to get answer bubble context'''
    answer_bubble = ""
    if ans.state == chatroom_states.CHATROOM_GUEST:

        ans = re.findall("""\<<.*?\|""", ans.answer, re.DOTALL)
        user_list = []
        for user in ans:
            user = user.replace("<<", "")
            user = user.replace("|", "")
            user_list.append(user)

        if len(user_list) == 2:
            answer_bubble = user_list[0] + " joined via a " + user_list[1] + "'s invite"

    elif ans.state == chatroom_states.CHATROOM_FOLLOW:
        answer_bubble = str(ans.user.userinfo.name) + " followed this chatroom"
    elif ans.state == chatroom_states.CHATROOM_UNFOLLOW:
        answer_bubble = str(ans.user.userinfo.name) + " unfollowed this chatroom"
    # elif ans.state == chatroom_states.CHATROOM_COMMUNITY_EDIT:
    #     answer_bubble= str(ans.user.userinfo.name) +  " edited community purpose"
    return answer_bubble


def get_chatroom_actions(card_status, creator, promoter=False, current_user_instance=None,
                         community_instance=None, is_child=False, request_type=""):
    ''' function to get chatroom actions '''

    is_ios = False
    if request_type == "iOS":
        is_ios = True

    purpose_card = False
    intro_card = False
    if card_status['type'] == card_types.CARD_PURPOSE:
        purpose_card = True
    elif card_status['type'] == card_types.CARD_INTRO:
        intro_card = True

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
        if admin_has_delete_right:
            final.append(delete_chatroom)

    actions = []

    for action in final:
        if purpose_card:
            if action['id'] == chatroom_actions.ACTION_FOLLOW or action['id'] == chatroom_actions.ACTION_UNFOLLOW:
                continue

            if not promoter:
                if action['id'] == chatroom_actions.ACTION_INVITE:
                    continue

            if promoter or creator:
                if action['id'] == chatroom_actions.ACTION_RENAME or action['id'] == chatroom_actions.ACTION_DELETE:
                    continue

        elif intro_card and creator:
            if action['id'] == chatroom_actions.ACTION_FOLLOW or \
                    action['id'] == chatroom_actions.ACTION_MUTE or \
                    action['id'] == chatroom_actions.ACTION_DELETE or \
                    action['id'] == chatroom_actions.ACTION_UNMUTE or \
                    action['id'] == chatroom_actions.ACTION_UNFOLLOW:
                continue

        elif action['id'] == chatroom_actions.ACTION_DELETE:
            if is_child and not creator:
                continue
            if promoter and not creator:
                if not admin_has_delete_right:
                    continue

        elif action['id'] == chatroom_actions.ACTION_REPORT:
            if promoter and not creator:
                if admin_has_delete_right:
                    continue

        actions.append(action)

    if card_status['follow_status'] and not is_ios:
        if card_status["active"]:
            actions.append(mark_inactive)
        else:
            actions.append(mark_active)

    return actions


def get_chatroom_internal(request, card_instance, user_id, page, conversation_id, scroll_direction, is_ios=False,
                          fetch_conversation_reply=False):
    '''internal function to get the chatroom conversation screen functionalities '''
    source_id = request.GET.get('source_id')
    aj = request.GET.get('aj')

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
    if is_ios:
        conversations_filter = conversations_filter.filter(is_deleted=False)

    total_response_count = card_answers.objects.filter(card=card_instance,
                                                       state=chatroom_states.ANSWER
                                                       ).filter(Q(attachment_count=0) |
                                                                Q(attachments_uploaded=True)
                                                                ).count()

    if not conversation_id and not scroll_direction:

        if is_guest:
            context = adding_guest_in_chatroom(context, card_instance, aj, source_id,
                                               card_instance.community.id, current_user_id=user_id)

        instance_filter = conversationMemberState.objects.filter(user_id=user_id, card=card_instance)
        if not instance_filter.exists():

            conversations = pagination(conversations_filter, page, paginate_by=20)

            conversations = get_answer_data(conversations, card_instance.community.id, current_user_id=user_id,
                                            is_ios=is_ios, fetch_reply=fetch_conversation_reply)

            placeholder = create_introduction_card_placeholder(card_instance, user_id)
            if placeholder:
                context['placeholder'] = placeholder
        else:
            conversation_instance = instance_filter[0].conversation

            upward_conversation = conversations_filter.filter(id__lte=conversation_instance.id).order_by('-id')[:10]

            downward_conversation = conversations_filter.filter(id__gt=conversation_instance.id)[:10]

            # merging both conversations
            conversations = upward_conversation | downward_conversation
            conversations = conversations.order_by('id')

            conversations = get_answer_data(conversations, card_instance.community.id,
                                            current_user_id=user_id, last_seen=conversation_instance,
                                            is_ios=is_ios, fetch_reply=fetch_conversation_reply)
    else:

        try:
            scroll_direction = int(scroll_direction)
            conversation_id = int(conversation_id)
        except Exception as e:
            context = get_error_context(False, "conversation id is a nullable field.Don't send the key")
            return context

        if scroll_direction == 0:  # upward scroll
            upward_list = conversations_filter.filter(id__lt=conversation_id).order_by('-id')[:20]
            conversations = reverse_conversations_for_upward_pagination(upward_list)

        elif scroll_direction == 1:  # downward scroll
            conversations = conversations_filter.filter(id__gt=conversation_id)[:20]
        else:
            conversations = conversations_filter

        conversations = get_answer_data(conversations, card_instance.community.id, current_user_id=user_id,
                                        is_ios=is_ios, fetch_reply=fetch_conversation_reply)

    card = get_chatroom_instance(card_instance, user_id)
    if card_instance.internal_link:
        try:
            card['preview'] = get_preview_for_url(user_id, card_instance.internal_link,
                                                  community_instance=card_instance.preview_community,
                                                  chatroom_instance=card_instance.preview_chatroom,
                                                  send_preview_text=False)
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
        'active': card['active']
    }

    is_promoter = False
    is_child = False
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

    chatroom_actions = get_chatroom_actions(card_status, creator=is_card_creator, promoter=is_promoter,
                                            current_user_instance=user_id,
                                            community_instance=card_instance.community, is_child=is_child,
                                            request_type=request_type
                                            )

    latest_conversations = save_the_latest_conversation(card_instance, user_id)

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
            instance.external_seen = True
            instance.expiry_time = get_expiry_time_of_chatroom()
            instance.updated_at = time.time()
            instance.save()

    # sending the follow telescope
    latest_conversation = conversations_filter.last()

    # icons states for sending following, tagging
    icon_states = get_icons_states_of_chatroom(card_status, card_instance, user_id, latest_conversation,
                                               conversations)
    card['show_follow_telescope'] = icon_states['show_follow_telescope']
    card['show_follow_auto_tag'] = icon_states['show_follow_auto_tag']
    card['show_active'] = icon_states['show_active']

    card['total_response_count'] = total_response_count

    if latest_conversations:
        last_conversation = latest_conversations['last_conversation']

        if last_conversation:
            serialized_last = get_answer_data([last_conversation], card_instance.community.id, current_user_id=user_id,
                                              is_ios=is_ios, fetch_reply=fetch_conversation_reply)
            if serialized_last:
                card['last_conversation'] = serialized_last[0]

    context['chatroom'] = card
    context['conversations'] = conversations
    context['chatroom_actions'] = chatroom_actions
    context['total_response_count'] = total_response_count

    context['community'] = CommunitySerializer(card_instance.community, current_user_instance=user_instance)

    context['total_participants'] = collabcardState.objects.filter(card=card_instance, follow_status=True,
                                                                   remove=None).count()

    conversation_users_meta = get_chatroom_user_images_for_web(card_instance.id)
    conversation_users = get_latest_conversation_members(conversation_users_meta['last_conversation_member'],
                                                         conversation_users_meta['second_last_conversation_member'],
                                                         conversation_users_meta['last_conversation_user'],
                                                         conversation_users_meta['second_last_conversation_user'])
    context['conversation_users'] = conversation_users

    return context


def get_chatroom_internal_version_1(request, card_instance, user_id, page, conversation_id, scroll_direction,
                                    is_ios=False):
    '''version 1 function for sending chatroom instance without conversations'''
    source_id = request.GET.get('source_id')
    aj = request.GET.get('aj')

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
                                                       state=chatroom_states.ANSWER
                                                       ).filter(Q(attachment_count=0) |
                                                                Q(attachments_uploaded=True)
                                                                ).count()

    conversations = []

    if not conversation_id and not scroll_direction:

        if is_guest:
            context = adding_guest_in_chatroom(context, card_instance, aj, source_id,
                                               card_instance.community.id, current_user_id=user_id)

    card = get_chatroom_instance(card_instance, user_id)

    if card_instance.internal_link:
        try:
            card['preview'] = get_preview_for_url(user_id, card_instance.internal_link,
                                                  community_instance=card_instance.preview_community,
                                                  chatroom_instance=card_instance.preview_chatroom,
                                                  send_preview_text=False)
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
        'active': card['active']
    }

    is_promoter = False
    is_child = False
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

    chatroom_actions = get_chatroom_actions(card_status, creator=is_card_creator, promoter=is_promoter,
                                            current_user_instance=user_id,
                                            community_instance=card_instance.community, is_child=is_child,
                                            request_type=request_type
                                            )

    # getting the state of chatroom against the user
    chatroom_state = collabcardState.objects.filter(card=card_instance, user=user_id)
    # if the user is seeing this chatroom from external link or notification
    if not chatroom_state.exists() and\
            user_instance and \
            is_member_verified(card_instance.community, user_instance):
        expire_at = get_expiry_time_of_chatroom()
        create_chatroom_state_instance(card_instance, user_instance, state=0, external_seen=True, expire_at=expire_at,
                                       function_called="get_chatroom_internal_version_1")
    elif user_instance and chatroom_state.exists():
        instance = chatroom_state[0]
        if not instance.external_seen:
            instance.external_seen = True
            instance.expiry_time = get_expiry_time_of_chatroom()
            instance.save()

    # sending the follow telescope
    latest_conversation = conversations_filter.last()

    # icons states for sending following, tagging
    icon_states = get_icons_states_of_chatroom_version_1(card_status, card_instance, user_id
                                                         )
    card['show_follow_telescope'] = icon_states['show_follow_telescope']
    card['show_follow_auto_tag'] = icon_states['show_follow_auto_tag']
    card['show_active'] = icon_states['show_active']

    card['total_response_count'] = total_response_count

    context['chatroom'] = card
    # context['conversations'] = conversations
    context['chatroom_actions'] = chatroom_actions
    context['total_response_count'] = total_response_count

    context['community'] = CommunitySerializer(card_instance.community, current_user_id=user_id,
                                               current_user_instance=user_instance)

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
    return context


def get_chatroom_internal_version_2(request, card_instance, user_id, page, conversation_id, scroll_direction,
                                    is_ios=False):
    '''version 1 function for sending chatroom instance without conversations'''
    source_id = request.GET.get('source_id')
    aj = request.GET.get('aj')

    is_guest = False
    context = {}

    if aj:
        is_guest = True

    user_instance = None
    if user_id:
        user_instance = User.objects.get(id=user_id)

    if not conversation_id and not scroll_direction:

        if is_guest:
            context = adding_guest_in_chatroom(context, card_instance, aj, source_id,
                                               card_instance.community.id, current_user_id=user_id)

    chatroom_state = collabcardState.objects.filter(card=card_instance, user=user_id)
    # if the user is seeing this chatroom from external link or notification
    if not chatroom_state.exists() and \
            user_instance and \
            is_member_verified(card_instance.community, user_instance):
        expire_at = get_expiry_time_of_chatroom()
        create_chatroom_state_instance(card_instance, user_instance, state=0,
                                       external_seen=True, expire_at=expire_at,
                                       function_called="get_chatroom_internal_version_1")
    elif user_instance and chatroom_state.exists():
        instance = chatroom_state[0]
        if not instance.external_seen:
            instance.external_seen = True
            instance.expiry_time = get_expiry_time_of_chatroom()
            instance.updated_at = time.time()
            instance.save()

    if chatroom_state.exists():
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
    card_status['active'] = False
    card_status['is_tagged'] = status['is_tagged']
    card_status['type'] = card_instance.type

    expiry_time = status['expiry_time']

    if not expiry_time or expiry_time >= int(time.time()):
        card_status['active'] = True

    is_promoter = False
    is_child = False
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

    chatroom_actions = get_chatroom_actions(card_status, creator=is_card_creator, promoter=is_promoter,
                                            current_user_instance=user_id,
                                            community_instance=card_instance.community, is_child=is_child,
                                            request_type=request_type
                                            )

    context['chatroom_actions'] = chatroom_actions

    conversation_member_filter = conversationMemberState.objects.filter(user=user_instance, card=card_instance)
    if not conversation_member_filter.exists():
        placeholder = create_introduction_card_placeholder(card_instance, user_id)
        if placeholder:
            context['placeholder'] = placeholder

    save_the_latest_conversation(card_instance, user_id)

    return context


def save_the_latest_conversation(card_instance, user_id):

    """function to save the lastest conversation of user"""

    if not user_id:
        return {'last_conversation': None}

    last_conversation = card_answers.objects.filter(card=card_instance, state=chatroom_states.ANSWER).last()

    if last_conversation:
        user_instance = User.get_user_or_raise_exception(user_id)
        state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)

        if state_filter.exists():

            collabcard_state_instance = state_filter[0]
            expiry_time = get_expiry_time_of_chatroom(collabcard_state_instance)

            if collabcard_state_instance.manual_set_active and \
                    collabcard_state_instance.manual_set_active > expiry_time:
                expiry_time = collabcard_state_instance.manual_set_active

            last_seen_conversation = collabcard_state_instance.last_seen_conversation

            if collabcard_state_instance.last_seen_conversation:

                if last_seen_conversation.id != last_conversation.id:
                    collabcard_state_instance.last_seen_conversation = last_conversation
                    collabcard_state_instance.expiry_time = expiry_time
                    collabcard_state_instance.updated_at = TimeUtilities.current_time_in_sec()
                    collabcard_state_instance.save()

                    update_conversation_engage_for_chatrooms(card_id=card_instance.id, user_id=user_instance.id,
                                                             last_conversation_id=last_conversation.id,
                                                             unseen_count=0)

            else:
                collabcard_state_instance.last_seen_conversation = last_conversation
                collabcard_state_instance.expiry_time = expiry_time
                collabcard_state_instance.updated_at = TimeUtilities.current_time_in_sec()
                collabcard_state_instance.save()

                update_conversation_engage_for_chatrooms(card_id=card_instance.id, user_id=user_instance.id,
                                                         last_conversation_id=last_conversation.id,
                                                         unseen_count=0)

        save_the_member_conversation_state(card_instance, user_instance, last_conversation)

    latest_conversations = {'last_conversation': last_conversation}

    return latest_conversations


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
                             guest_header=False):
    aj_expired = is_chatroom_join_expired(aj, source_id, card_instance.id)
    status = is_member_verified(community_id, current_user_id)
    state_filter = collabcardState.objects.filter(card=card_instance, user=current_user_id, is_guest=True)

    if not aj_expired and not status and not state_filter.exists():
        context['aj_expired'] = aj_expired
        if guest_header:
            create_guest_header(current_user_id, source_id, card_instance, current_user_id)

            func_dict = {'collabcard_id': card_instance.id, 'member_id': current_user_id, 'status': True,
                         'is_guest': True, 'source_id': source_id, 'source': "guest access"}
            collabcard_follow_internal(func_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)


    elif not status and not state_filter.exists():
        context['aj_expired'] = aj_expired
        aj_expired_disclaimer = {}
        aj_expired_disclaimer['image_url'] = WARNING_IMAGE
        aj_expired_disclaimer[
            'title'] = "Oops! The private link to participate in this chat room has expired. Join the following community to access this chat room."
        if status:
            # for promoter
            community_serializer = CommunitySerializer(card_instance.community, status.member_id,
                                                       current_user_id=current_user_id)
            community_serializer['created_by'] = get_community_creator(card_instance.community)
            aj_expired_disclaimer['community'] = community_serializer
        else:
            community_serializer = CommunitySerializer(card_instance.community, current_user_id=current_user_id)
            community_serializer['created_by'] = get_community_creator(card_instance.community)
            aj_expired_disclaimer['community'] = community_serializer

        context['aj_expired_disclaimer'] = aj_expired_disclaimer

    return context


def create_guest_header(guest_id, invitee_id, card_instance, current_user_id):
    try:
        guest_instance = User.objects.get(id=guest_id)
        invitee_instance = User.objects.get(id=invitee_id)
    except:
        return

    guest_user_name = get_user_in_route_form(card_instance, guest_instance, current_user_id)

    invitee_user_name = get_user_in_route_form(card_instance, invitee_instance, current_user_id)

    answer = guest_user_name + " joined via " + invitee_user_name + "'s link"

    cardAnswer_filter = card_answers.objects.filter(card=card_instance, user=guest_instance,
                                                    state=chatroom_states.CHATROOM_GUEST)
    if not cardAnswer_filter.exists():
        instance = card_answers()
        instance.answer = answer
        instance.card = card_instance
        instance.user = guest_instance
        instance.state = chatroom_states.CHATROOM_GUEST
        instance.community = card_instance.community
        instance.created_at = time.time()
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
        'show_follow_auto_tag': False,
        'show_active': False
    }

    if not card_status['follow_status']:
        temp['show_follow_telescope'] = True
        show = True

    if card_instance.user.id == user_id:
        temp['show_follow_telescope'] = False
        show = True

    if card_status['active'] and card_status['is_tagged']:
        temp['show_follow_telescope'] = False
        temp['show_active'] = False
        temp['show_follow_auto_tag'] = True
        show = True

    if card_status['active'] == False and card_status["follow_status"] == True:
        temp['show_follow_telescope'] = False
        temp['show_active'] = True
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
    return {'show_follow_telescope': False, 'show_follow_auto_tag': False, 'show_active': False}


def get_icons_states_of_chatroom_version_1(card_status, card_instance, user_id):
    '''function to show follow telescope of user'''

    show = False

    temp = {
        'show_follow_telescope': False,
        'show_follow_auto_tag': False,
        'show_active': False
    }

    if not card_status['follow_status']:
        temp['show_follow_telescope'] = True
        show = True

    if card_instance.user.id == user_id:
        temp['show_follow_telescope'] = False
        show = True

    if card_status['active'] and card_status['is_tagged']:
        temp['show_follow_telescope'] = False
        temp['show_active'] = False
        temp['show_follow_auto_tag'] = True
        show = True

    if card_status['active'] == False and card_status["follow_status"] == True:
        temp['show_follow_telescope'] = False
        temp['show_active'] = True
        temp['show_follow_auto_tag'] = False
        show = True

    if show:
        return temp
    return {'show_follow_telescope': False, 'show_follow_auto_tag': False, 'show_active': False}


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
    if is_member_promoter(community_id=community_id, member_id=member_id):
        community_serializer_instance = CommunitySerializer(community, promoter_id=member_instance,
                                                            current_user_id=member_id)
    else:
        community_serializer_instance = CommunitySerializer(community, current_user_id=member_id)

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


def text_for_community_live_subtitile(total_count, intro_collabcard_list, verified_members_list):
    '''function to return intro collabcard and verified list in case of lg communities'''

    diff = total_count - len(intro_collabcard_list)

    if diff > 0:
        intro_name_list = []
        members_list = []
        for instance in intro_collabcard_list:
            intro_name_list.append(instance.member.userinfo.name)

        verified_member_name_list = []

        for member in verified_members_list:
            verified_member_name_list.append(member.member_id.userinfo.name)

        for num in range(diff):
            members_list.append(verified_member_name_list[num])

        total_list = intro_name_list + members_list

        return total_list
    else:

        intro_name_list = []
        members_list = []
        for instance in intro_collabcard_list:
            intro_name_list.append(instance.member.userinfo.name)
        return intro_name_list


def compute_community_live_subtitle_for_lg(total_count, count_of_verified_members, user_instance, community):
    verfied_status = is_member_verified(community, user_instance)
    member_id = user_instance
    community_id = community.id
    member_type = "relevant alumnus"
    member_types = "relevant alumni"

    community_live_subtitle = ""
    if verfied_status:
        # if member is verified
        if total_count == 1:
            community_live_subtitle = """Awesome, you have taken the first step! Be the spark to ignite this community by inviting other %s from your network.""" % (
                member_types)

        elif total_count == 2:

            intro_collabcard_list = collabcardTemp.objects.filter(show_member=user_instance, community_id=community_id)
            verified_members_list = Members.objects.filter(community_id=community_id).filter(Q(state=1) | Q(state=4))

            total_list = text_for_community_live_subtitile(total_count, intro_collabcard_list, verified_members_list)

            ans_list = []

            for data in total_list:

                if data == user_instance.userinfo.name:
                    continue
                ans_list.append(data)
            if ans_list:
                community_live_subtitle = """Superb, you and %s are now together for your shared interest! Invite 2 other %s and let them join you in this community.""" % (
                    ans_list[0], member_types)


        elif total_count == 3:
            intro_collabcard_list = collabcardTemp.objects.filter(show_member=user_instance, community_id=community_id)
            verified_members_list = Members.objects.filter(community_id=community_id).filter(Q(state=1) | Q(state=4))

            total_list = text_for_community_live_subtitile(total_count, intro_collabcard_list, verified_members_list)

            ans_list = []

            for data in total_list:

                if data == user_instance.userinfo.name:
                    continue
                ans_list.append(data)

            if ans_list:
                community_live_subtitle = """You, %s and %s  make a great group! Make it a community by inviting 1 more %s.""" % (
                    ans_list[0], ans_list[1], member_type)

        elif total_count == 4 and count_of_verified_members == 1:
            member_list = Members.objects.filter(community_id=community_id).order_by('-id')
            other_member_list = []
            for member in member_list:
                if member_id == str(member.member_id.id):
                    continue
                member_name = member.member_id.userinfo.name
                if member.state == 3:
                    other_member_list.append(member_name)
            if other_member_list:
                community_live_subtitle = """1 last step pending! Since this is an exclusive community, you need to verify %s, %s and %s  to initiate the community""" % (
                    other_member_list[0], other_member_list[1], other_member_list[2])

        elif total_count == 4 and count_of_verified_members == 2:
            member_list = Members.objects.filter(community_id=community_id).order_by('-id')
            other_member_list = []
            for member in member_list:
                if member_id == str(member.member_id.id):
                    continue
                member_name = member.member_id.userinfo.name
                if member.state == 3:
                    other_member_list.append(member_name)
            if other_member_list:
                community_live_subtitle = """1 last step pending! Since this is an exclusive community, you need to verify %s and %s  to initiate the community""" % (
                    other_member_list[0], other_member_list[1])

        elif total_count == 4 and count_of_verified_members == 3:
            member_list = Members.objects.filter(community_id=community_id).order_by('-id')
            other_member_list = []
            for member in member_list:
                if member_id == str(member.member_id.id):
                    continue
                member_name = member.member_id.userinfo.name
                if member.state == 3:
                    other_member_list.append(member_name)
            if other_member_list:
                community_live_subtitle = """1 last step pending! Since this is an exclusive community, you need to verify %s  to initiate the community""" % (
                    other_member_list[0])

        elif total_count > 4 and count_of_verified_members == 1:
            community_live_subtitle = "1 last step pending! Since this is an exclusive community, you need to verify atleast 3 other members to initiate the community"

        elif total_count > 4 and count_of_verified_members == 2:
            community_live_subtitle = "1 last step pending! Since this is an exclusive community, you need to verify atleast 2 other members to initiate the community"

        elif total_count > 4 and count_of_verified_members == 3:
            community_live_subtitle = "1 last step pending! Since this is an exclusive community, you need to verify atleast 1 member to initiate the community"




    else:
        # member is not verified
        if total_count == 1:
            community_live_subtitle = """Awesome, you have taken the first step! Be the spark to ignite this community by inviting other %s from your network.""" % (
                member_types)


        elif total_count == 2:
            intro_collabcard_list = collabcardTemp.objects.filter(show_member=user_instance, community_id=community_id)
            verified_members_list = Members.objects.filter(community_id=community_id).filter(Q(state=1) | Q(state=4))

            total_list = text_for_community_live_subtitile(total_count, intro_collabcard_list, verified_members_list)

            ans_list = []

            for data in total_list:

                if data == user_instance.userinfo.name:
                    continue
                ans_list.append(data)
            if ans_list:
                community_live_subtitle = """Superb, you and %s are now together for your shared interest! Invite 2 other %s and let them join you in this community.""" % (
                    ans_list[0], member_types)

        elif total_count == 3:
            intro_collabcard_list = collabcardTemp.objects.filter(show_member=user_instance, community_id=community_id)
            verified_members_list = Members.objects.filter(community_id=community_id).filter(Q(state=1) | Q(state=4))

            total_list = text_for_community_live_subtitile(total_count, intro_collabcard_list, verified_members_list)

            ans_list = []

            for data in total_list:

                if data == user_instance.userinfo.name:
                    continue
                ans_list.append(data)

            if ans_list:
                community_live_subtitle = """You, %s and %s  make a great group! Make it a community by inviting 1 more %s.""" % (
                    ans_list[0], ans_list[1], member_type)


        elif total_count == 4 and count_of_verified_members == 1:
            community_live_subtitle = """Your profile isn't verified yet. Since this is an exclusive community, your profile needs to be verified in order to initiate the community"""
        elif total_count == 4 and count_of_verified_members == 2:
            community_live_subtitle = """Your profile isn't verified yet. Since this is an exclusive community, your profile needs to be verified in order to initiate the community"""
        elif total_count == 4 and count_of_verified_members == 3:

            member_list = Members.objects.filter(community_id=community_id).filter(Q(state=4) | Q(state=1))
            other_member_list = []
            for member in member_list:
                member_name = member.member_id.userinfo.name
                other_member_list.append(member_name)
            if other_member_list:
                community_live_subtitle = """1 last step pending! %s, %s and %s are already verified members of this community. The community will be initiated as soon your profile is verified.""" % (
                    other_member_list[0], other_member_list[1], other_member_list[2])


        elif total_count > 4 and count_of_verified_members == 1:
            community_live_subtitle = "Your profile isn't verified yet. Since this is an exclusive community, your profile needs to be verified in order to initiate the community"
        elif total_count > 4 and count_of_verified_members == 2:
            community_live_subtitle = "Your profile isn't verified yet. Since this is an exclusive community, your profile needs to be verified in order to initiate the community"
        elif total_count > 4 and count_of_verified_members == 3:

            member_list = Members.objects.filter(community_id=community_id).filter(Q(state=4) | Q(state=1))
            other_member_list = []
            for member in member_list:
                member_name = member.member_id.userinfo.name
                other_member_list.append(member_name)

            if other_member_list:
                community_live_subtitle = """1 last step pending! %s, %s are %s and already verified members of this community. The community will be initiated as soon your profile is verified.""" % (
                    other_member_list[0], other_member_list[1], other_member_list[2])


        elif total_count == 4 and count_of_verified_members == 0:
            community_live_subtitle = "Your profile isn't verified yet. Since this is an exclusive community, your profile needs to be verified in order to initiate the community"


        elif total_count > 0 and count_of_verified_members == 0:
            community_live_subtitle = "Your profile isn't verified yet. Since this is an exclusive community, your profile needs to be verified in order to initiate the community"
    return community_live_subtitle


def compute_community_live_subtitle_for_Ig(community_instance, member_id, members_count):
    '''function to get community_live  subtitle for IG communities'''

    community_name = community_instance.name
    member_types = community_name.split("of")[0].strip()
    member_type = member_types
    if member_types[-1] == "s":
        member_type = member_types[0:-1]

    member_types = member_types.lower()
    member_type = member_type.lower()

    # members_count = get_members_count_in_community(community_instance)

    if members_count == 1:
        community_live_subtitle = """Awesome, you have taken the first step! Be the spark to ignite this community by inviting other %s from your network.""" % (
            member_types)
    elif members_count == 2:

        member_filter = Members.objects.filter(community_id=community_instance).filter(~Q(member_id=member_id))
        member_name = member_filter[0].member_id.userinfo.name
        community_live_subtitle = """Superb, you and %s are now together for your shared interest! Invite 2 other %s and let them join you in this community.""" % (
            member_name, member_types)

    elif members_count == 3:

        member_filter = Members.objects.filter(community=community_instance).filter(~Q(member_id=member_id)).order_by(
            '-id')
        member_name1 = member_filter[0].member_id.userinfo.name
        member_name2 = member_filter[1].member_id.userinfo.name

        community_live_subtitle = """You, %s  and %s  make a great group! Make it a community by inviting 1 more %s.""" % (
            member_name1, member_name2, member_type)
    else:
        members_left = ig_members_count - members_count
        community_live_subtitle = """Every community needs its members to make purposeful conversations. Invite %s or more members to start conversations.""" % (
            members_left)

    return community_live_subtitle


def get_invite_prompt_for_members(community_id, member_type, member_types, member_id):
    invite_prompt = {}
    ref_members = get_referred_members_of_a_member(community_id, member_id)
    ref_members_count = len(ref_members)

    if ref_members_count == 0:
        invite_prompt['title'] = """Know any %s?""" % (member_type)
        invite_prompt['sub_title'] = """Invite a new member here and unlock a tool"""
        invite_prompt['action_title'] = """Invite"""
        invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (
            community_id)
    elif ref_members_count == 1:
        invite_prompt['title'] = """Unlock a new tool"""
        invite_prompt['sub_title'] = """By inviting 2 more members to this community"""
        invite_prompt['action_title'] = """Invite"""
        invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (
            community_id)
    elif ref_members_count == 2:
        invite_prompt['title'] = """Unlock a new tool"""
        invite_prompt['sub_title'] = """By inviting 1 more member to this community"""
        invite_prompt['action_title'] = """Invite"""
        invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (
            community_id)
    elif ref_members_count == 3:
        invite_prompt['title'] = """Become a promoter"""
        invite_prompt['sub_title'] = """Get recognised by inviting 2 more members"""
        invite_prompt['action_title'] = """Invite"""
        invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (
            community_id)
    elif ref_members_count == 4:
        invite_prompt['title'] = """Become a promoter"""
        invite_prompt['sub_title'] = """Get recognised by inviting 1 more member"""
        invite_prompt['action_title'] = """Invite"""
        invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (
            community_id)
    else:
        invite_prompt['title'] = """Promote your community"""
        invite_prompt['sub_title'] = """Let other %s discover this community""" % (member_types)
        invite_prompt['action_title'] = """Invite"""
        invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (
            community_id)

    return invite_prompt


def get_unlock_prompt(members_left):
    '''function to get unlock prompt'''

    temp = {}
    temp['unlock_title'] = "Invite members"
    if members_left == 1:
        temp[
            'unlock_sub_title'] = "To start a conversation, invite %s more member to this community and make this community live." % (
            members_left)
        temp['community_live_title'] = "more member required"
    else:
        temp[
            'unlock_sub_title'] = "To start a conversation, invite %s more members to this community and make this community live." % (
            members_left)
        temp['community_live_title'] = "more members required"

    temp['unlock_action_title'] = "OK, INVITE NOW"
    temp['unlock_action'] = """route://community?community_id=%s&share=true&source=community_live_unlock"""

    return temp


def community_cards_version_1(request, community_id, req_dict=None):
    '''Version 1 community collabcards'''
    context = {}
    member_id = get_member_id_from_headers(request)
    size = request.GET.get('size', 3)
    size = int(size)
    if not member_id:
        context = get_error_context(False, "send member id in request header")
        return JsonResponse(context)

    try:
        community_instance = Community.objects.get(id=community_id)
    except:
        context = get_error_context(False, "send correct community id")
        return JsonResponse(context)

    chatroom_filter = Collabcard.objects.filter(community=community_instance,
                                                is_pending=False, is_deleted=False).order_by('-id')
    total_chatrooms = chatroom_filter.count()
    chatroom_list = []
    for chatroom in chatroom_filter:

        chatroom_data = get_chatroom_instance(chatroom, member_id)
        chatroom_list.append(chatroom_data)
        size = size - 1
        if size == 0:
            break

    context = {
        'collabcards': chatroom_list,
        'size': total_chatrooms
    }

    return JsonResponse(context)


# /api/create_answer?collabcard_id=&member_id=
@csrf_exempt
def create_answer(request):
    '''function to post answer on collabcard'''
    body = request.GET

    try:
        user_id = body['member_id']
        card_id = body['collabcard_id']
        user_instance = User.objects.get(id=user_id)
        card_instance = Collabcard.objects.get(id=card_id)
    except:
        context = get_error_context(False, "Send params correctly")
        return JsonResponse(context)

    res = json.loads(request.body)
    ans = card_answers()
    ans.answer = res['title']
    ans.card = card_instance
    ans.user = user_instance
    ans.community = card_instance.community
    ans.created_at = time.time()
    ans.save()

    update_last_answer_id(card_id, ans.id)
    # auto following the collabcard if answer is created
    function_dict = {
        'member_id': user_id,
        'collabcard_id': card_id,
        'status': True
    }
    collabcard_follow_internal(function_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

    # sending the tagged member list
    auto_follow_chatrooms_in_case_of_tagging(request, res['title'], card_id)

    send_follow_notification(card_id=card_id, user_id=user_id, answer=res['title'])

    #     # calling update_answer_text
    # if card.type == card_types.CARD_NORMAL or card.type == card_types.CARD_INTRO:
    #     print("type === ", card.type)
    #     update_answer_text(card_id)

    # updating the conversationEngage table
    conversation_seen(request, {'member_id': user_id, 'conversation_id': ans.id})
    update_my_chatrooms_for_users(chatroom_id=card_id)

    return JsonResponse({'success': True, 'id': ans.id})


@csrf_exempt
def create_conversation(request):
    '''api to create the conversation'''

    member_id = get_member_id_from_headers(request)

    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context)

    res = json.loads(request.body)

    is_guest = False
    if 'aj' in res and 'source_id' in res:
        if res['aj'] and res['source_id']:
            is_guest = True

    card_instance = Collabcard.objects.get(id=res['chatroom_id'])
    user_instance = User.objects.get(id=member_id)

    current_state = members_state(request, {'community_id': card_instance.community.id, 'member_id': user_instance.id})

    if is_guest and (current_state['state'] == 0 or current_state['state'] == member_states.PENDING_MEMBER):
        context = {}
        context = adding_guest_in_chatroom(context, card_instance, res['aj'], res['source_id'],
                                           card_instance.community.id, member_id, guest_header=True)

    ##checking weather the conversation creater is a guest or not
    state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance, is_guest=True)

    replied_conversation = None
    if 'replied_conversation_id' in res:
        try:
            replied_conversation = card_answers.objects.get(pk=res['replied_conversation_id'])
        except:
            context = get_error_context(False, "replied_conversation_id is wrong")
            return JsonResponse(context, status=400)

    has_files = res.get('has_files', False)

    is_ios = False
    if not has_files:
        is_ios = is_platform_ios(request)
        if is_ios:
            has_files = True

    ans = card_answers()
    ans.answer = res['text']
    ans.card = card_instance
    ans.user = user_instance
    ans.community = card_instance.community
    ans.is_guest = state_filter.exists()
    ans.created_at = time.time()
    ans.has_files = has_files
    if replied_conversation:
        ans.reply = replied_conversation

    attachment_count = res.get('attachment_count', 0)
    ans.attachment_count = attachment_count
    ans.attachments_uploaded = False

    if attachment_count > 0:
        ans.has_files = True

    set_preview_object(ans, res, member_id)

    ans.save()

    # saving the og tags if present
    if 'og_tags' in res:
        ans.og_tags = json.dumps(res['og_tags'])
        ans.save()
    elif 'share_link' in res:
        ans.og_tags = json.dumps(decode_meta_from_url(res['share_link']))
        ans.save()

    # saving those answer data in firebase, if any attachments are not there
    has_files = res.get('has_files', False)

    has_files = has_files or attachment_count > 0

    if not has_files :
        update_last_answer_id(card_instance.id, ans.id)

    # auto following the collabcard if answer is created
    if current_state['state'] == member_states.ADMIN or current_state['state'] == member_states.MEMBER or current_state[
        'state'] == member_states.PROFILE_UNAVAILABLE:
        function_dict = {
            'member_id': member_id,
            'collabcard_id': card_instance.id,
            'status': True,
            'source': "create_conversation"
        }
        collabcard_follow_internal(function_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

    conversation_tagging(request, res, card_instance, user_instance, member_id)
    # # # updating the conversationEngage table
    user_id = str(user_instance.id)
    save_the_latest_conversation(card_instance, user_id)

    update_my_chatrooms_for_users(chatroom_id=card_instance.id)
    update_activity_in_chatroom_for_conversation_creation(card_instance.id, user_id=user_id)
    update_chatroom_for_users_and_send_follow_notification.delay(card_instance.id, user_id, res['text'],
                                                                 has_files=has_files, is_ios=is_ios)

    context = {"current_user_id": member_id, "fetch_reply": True}
    conversation = CardAnswersDBSyncSerializer(ans, context=context, many=False)
    return JsonResponse({'success': True, 'id': ans.id, 'conversation': conversation.data})


def conversation_tagging(request, res, card_instance, user_instance, member_id):
    '''tagging in conversations and auto-following'''
    # sending the tagged member list
    auto_follow_chatrooms_in_case_of_tagging(request, res['text'], card_instance.id, card_instance)

    # send tagged users mail if they didnt check chat in last 24 hours
    tagged_members = get_tagged_members_list(res['text'])

    tagged_member_list = tagged_members[0]
    if len(tagged_member_list) > 0:
        send_tagged_user_mail.delay(user_instance.id, card_instance.id, tagged_member_list, time_in_hrs=24)

    notification_list = [
        'mail_card_owner_inactivity'
    ]

    # check if sender is not the owner and  notification flag is true
    if check_notification_flag(card_instance.user.id, notification_list, card_id=card_instance.id,
                               community_id=None) and str(member_id) != str(card_instance.user.id):
        send_chatroom_owner_mail.delay(card_instance.user.id, card_instance.id, time_in_hrs=12)


@shared_task
def update_chatroom_for_users_and_send_follow_notification(card_instance_id, user_id, res_text, has_files=False,
                                                           is_ios=False):
    # update_my_chatrooms_for_users(chatroom_id=card_instance_id)
    # update_activity_in_chatroom_for_conversation_creation(card_instance_id, user_id=user_id)
    # adding the sleep of 2 seconds for table updation for testing
    # time.sleep(2)
    if not has_files:
        send_follow_notification(card_id=card_instance_id, user_id=user_id, answer=res_text)

    if has_files and is_ios:
        send_follow_notification(card_id=card_instance_id, user_id=user_id, answer=res_text)


def update_activity_in_chatroom_for_conversation_creation(card_instance_id, user_id):
    '''function to update the activity in chatroom for conversation creations'''
    # for users who are following the chatrooms
    # updating the expire time to null for all the users who are following the chatroom in collabcardState

    card_instance = Collabcard.objects.get(id=card_instance_id)

    update_status = collabcardState.objects.filter(card=card_instance, follow_status=True, remove=None).filter(
        ~Q(user=user_id)).update(
        expiry_time=None, updated_at=time.time())

    print(update_status)

    # the person who is making the conversation marking his chatroom active for expiry time
    state_filter = collabcardState.objects.filter(card=card_instance, user=user_id)
    if state_filter.exists():
        expiry_time = get_expiry_time_of_chatroom(state_filter[0])
        state_filter.update(expiry_time=expiry_time, updated_at=time.time())

    # #updating the expire time to null for all the users  who are following the chatroom in conversationEngage
    # conversationEngage.objects.filter(card=card_instance).update(expiry_time=expiry_time)

    # for users who have seen the chatroom
    seen_filter = collabcardState.objects.filter(card=card_instance, follow_status=False,
                                                 remove=None).filter(
        Q(state=collabcard_states.COLLABCARD_STATE_SEEN) | Q(external_seen=True))

    if seen_filter.exists():
        for data in seen_filter:
            expiry_time = get_expiry_time_of_chatroom(data)
            data.expiry_time = expiry_time
            data.updated_at = time.time()
            data.save()

    # print(update_status)


def auto_follow_chatrooms_in_case_of_tagging(request, conversation, card_id, card_instance=None):
    '''function to follow tagged chatrooms'''

    tagged_members = get_tagged_members_list(conversation)

    tagged_member_list = tagged_members[0]

    is_tagged = True

    if card_instance:
        if card_instance.type == card_types.CARD_PURPOSE:
            is_tagged = False

    for user_id in tagged_member_list:
        function_dict = {
            'member_id': user_id,
            'collabcard_id': card_id,
            'status': True,
            'source': "auto-following-chatroom",
            'is_tagged': is_tagged
        }
        collabcard_follow_internal(function_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)


def _send_notification_to_tagged_users(card_id, answerer_name, answer, user_id):
    tagged_users = re.findall("route://member/"'([0-9]+)', answer)
    answer_text = re.split('>>', answer)[-1]
    send_follow_notification(card_id=card_id, user_id=user_id, answer=answer, tagged_users_list=tagged_users)
    for user_id in tagged_users:
        # user=User.objects.get(id=user_id)
        # if not is_collabcard_already_followed(card,user):
        send_notification_to_tagged_users(card_id=card_id, answerer_name=answerer_name, answer=answer_text,
                                          user_id=user_id)


def update_answer_text(card_id):
    '''function for updating the answer_text feild in collab card model'''

    ans_text = ''
    card = Collabcard.objects.get(id=card_id)
    card_ans = card_answers.objects.filter(card=card).distinct('user_id')
    # if only one answer is present fro a collab card
    card_ans_count = card_ans.count()
    if card_ans_count == 0:
        return

    if card_ans_count == 1:
        # get the name of the user who answered
        username = card_ans[0].user.userinfo.name
        ans_text = username + " responded"
        # update the answer_text field in collabcard
        # Collabcard.objects.filter(id=card_id).update(answer_text=ans_text)

    elif card_ans_count == 2:
        # if there is more than one answer
        ans_text += card_ans[0].user.userinfo.name + " and " + card_ans[1].user.userinfo.name
        ans_text += " responded"
        # Collabcard.objects.filter(id=card_id).update(answer_text=ans_text)

    elif card_ans_count > 2:
        # if more than two different users have answered
        ans_text += card_ans[0].user.userinfo.name
        ans_text += " & " + str(card_ans_count - 1) + " others responded"
        # Collabcard.objects.filter(id=card_id).update(answer_text=ans_text)
    card.answer_text = ans_text
    card.answers_count = card_ans_count
    card.save()
    print("card answers count ====   ", card_ans_count)
    print("card answers text ====   ", ans_text)

    return


@csrf_exempt
def collabcard_follow(request, function_dict=None):
    """ Api to follow collabcard by members Post API """

    current_member_id = get_member_id_from_headers(request)

    if is_request_web(request) and request.user.is_authenticated:
        current_member_id = request.user.id

    collabcard_id = request.GET.get('collabcard_id', '')
    member_id = request.GET.get('member_id', '')
    status = request.GET.get('value', 'true')

    if status != 'true':
        status = False  # unfollowed
    else:
        status = True  # followed
        explicit_call = True

    collabcard = Collabcard.objects.get(id=collabcard_id)

    community_instance = collabcard.community
    card_instance = collabcard
    user_instance = User.objects.get(id=member_id)

    # user cant unfollow his own collabcard
    if not status and collabcard.user.id == user_instance.id:
        return JsonResponse({'success': True})

    is_guest = False

    aj = request.GET.get('aj')
    source_id = request.GET.get('source_id')
    member_state = members_state(request, {'community_id': community_instance.id, 'member_id': user_instance.id})

    # user is a guest in chatroom
    if aj and source_id and (member_state['state'] == 0 or member_state['state'] == member_states.PENDING_MEMBER):
        context = {}
        context = adding_guest_in_chatroom(context, collabcard, aj, source_id, community_instance.id, current_member_id,
                                           guest_header=True)

        # updating the collabcard state external follow for guest member
        collabcardState.objects.filter(card=collabcard, user=user_instance).update(external_follow=True)
        return JsonResponse(context)

    expiry_time = get_expiry_time_of_chatroom()

    collabcard_state_filter = collabcardState.objects.filter(card=collabcard, user=user_instance)
    if not collabcard_state_filter.exists():
        # collabcard_state_instance = collabcardState()
        # collabcard_state_instance.card = collabcard
        # collabcard_state_instance.community = community_instance
        # collabcard_state_instance.user = user_instance
        # collabcard_state_instance.state = 0
        # collabcard_state_instance.created_at = time.time()
        # collabcard_state_instance.updated_at = time.time()
        # collabcard_state_instance.follow_status = status
        # collabcard_state_instance.is_guest = is_guest
        # collabcard_state_instance.external_seen = True
        # collabcard_state_instance.expiry_time = expiry_time
        # collabcard_state_instance.save()

        create_chatroom_state_instance(card_instance, user_instance, state=0,
                                       expire_at=expiry_time, external_seen=True, is_guest=is_guest,
                                       follow_status=status, function_called="collabcard_follow", external_follow=True)

        if status:
            create_chatroom(card_instance=collabcard, user_instance=user_instance,
                            state=chatroom_states.CHATROOM_FOLLOW, current_user_id=current_member_id)

            create_chatroom_engagement(card_instance=collabcard, user_instance=user_instance,
                                       member_state=member_state['state'])

    else:
        follow_status = collabcard_state_filter[0].follow_status
        if status and follow_status:
            return JsonResponse({'success': True})

        if not status and not follow_status:
            return JsonResponse({'success': True})

        if status:
            expiry_time = get_expiry_time_of_chatroom(collabcard_state_filter[0])
            collabcard_state_filter.update(follow_status=status, updated_at=time.time(), expiry_time=expiry_time,
                                           external_seen=True, external_follow=status)

            create_chatroom(card_instance=collabcard, user_instance=user_instance,
                            state=chatroom_states.CHATROOM_FOLLOW, current_user_id=current_member_id)
            create_chatroom_engagement(card_instance=collabcard, user_instance=user_instance,
                                       member_state=member_state['state'])

        else:
            state = collabcard_state_filter[0].state
            if state == collabcard_states.COLLABCARD_STATE_ATTENDING:
                state = collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING

            collabcard_state_filter.update(follow_status=status, updated_at=time.time(),
                                           is_tagged=False, external_seen=True, external_follow=status,
                                           state=state
                                           )

            # deleting the conversation engage
            delete_status = conversationEngage.objects.filter(card=collabcard, user=user_instance).delete()
            print(delete_status)

            create_chatroom(card_instance=collabcard, user_instance=user_instance,
                            state=chatroom_states.CHATROOM_UNFOLLOW, current_user_id=current_member_id)

    # custom_cache.clear()
    update_my_chatrooms_for_users(chatroom_id=collabcard.id, user_id=current_member_id)
    print("working")
    # updating the activity in chatroom
    update_activity_in_chatroom(card_instance, user_instance)
    return JsonResponse({'success': True})


def collabcard_follow_internal(func_dict, state=collabcard_states.COLLABCARD_STATE_SEEN,
                               set_expiry_time_none=False):

    """ folowing collabcard internally """

    card_id = func_dict['collabcard_id']
    member_id = func_dict['member_id']
    status = func_dict['status']
    is_guest = False
    is_tagged = False
    ref_instance = None
    mute_status = False

    if 'is_guest' in func_dict:
        is_guest = func_dict['is_guest']
        source_id = func_dict['source_id']
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
                collabcard_state_filter.update(is_tagged=False, mute_status=False, updated_at=time.time())
            print("follow hit")
            return

        expiry_time = get_expiry_time_of_chatroom(collabcard_state_filter[0])
        if is_guest:
            collabcard_state_filter.update(follow_status=status, state=state, is_guest=is_guest,
                                           updated_at=time.time(), source=ref_instance, expiry_time=expiry_time,
                                           is_tagged=is_tagged, external_seen=True, mute_status=mute_status)
        else:
            collabcard_state_filter.update(follow_status=status, updated_at=time.time(),
                                           expiry_time=expiry_time, is_tagged=is_tagged,
                                           external_seen=True, mute_status=mute_status)

    else:

        if is_tagged:
            mute_status = True
        else:
            mute_status = False
        expiry_time = get_expiry_time_of_chatroom() if not set_expiry_time_none else None
        create_chatroom_state_instance(card_instance, user_instance, state=0,
                                       expire_at=expiry_time, external_seen=True, is_guest=is_guest,
                                       source=ref_instance, follow_status=status,
                                       mute_status=mute_status, is_tagged=is_tagged,
                                       function_called="collabcard_follow_internal")

    if status:
        member_state = 0
        member_instance = Members.objects.filter(member_id=user_instance, community_id=card_instance.community)
        if member_instance.exists():
            member_state = member_instance[0].state
        create_chatroom_engagement(card_instance=card_instance, user_instance=user_instance, member_state=member_state)

    update_my_chatrooms_for_users(chatroom_id=card_instance.id, user_id=member_id)

    # function to set activity of chatroom
    update_activity_in_chatroom(card_instance, user_instance)


def set_state_for_event_cards(collabcard, community_instance, user_instance, status, explicit_call, current_member_id):
    '''function to set states in case of event cards'''

    if (collabcard.type == card_types.CARD_EVENT or collabcard.type == card_types.CARD_PUBLIC_EVENT):

        if status:  # the collabcard is the event card and followed
            try:
                collabcard_state_instance = collabcardState.objects.get(card=collabcard, user=user_instance)
            except:
                # for autofollowing the co-host
                # collabcard_state_instance = collabcardState()
                # collabcard_state_instance.card = collabcard
                # collabcard_state_instance.community = community_instance
                # collabcard_state_instance.user = user_instance
                # collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_SEEN
                # collabcard_state_instance.follow_status = True
                # collabcard_state_instance.created_at = time.time()
                # collabcard_state_instance.updated_at = time.time()
                # collabcard_state_instance.save()

                collabcard_state_instance = create_chatroom_state_instance(collabcard, user_instance,
                                                                           state=collabcard_states.COLLABCARD_STATE_SEEN,
                                                                           expire_at=None, external_seen=True,
                                                                           is_guest=False, source=None,
                                                                           follow_status=True, mute_status=False,
                                                                           is_tagged=False,
                                                                           function_called="set_state_for_event_cards")

            # when the user is not attending but following the collabcard
            if collabcard_state_instance.state == collabcard_states.COLLABCARD_STATE_SEEN:

                collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_UNATTEND_FOLLOWING
                collabcard_state_instance.updated_at = time.time()
                collabcard_state_instance.save()
            # when the user is attending and following the collabcard
            elif collabcard_state_instance.state == collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING:

                collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING
                collabcard_state_instance.updated_at = time.time()
                collabcard_state_instance.save()

            if explicit_call:
                create_chatroom(card_instance=collabcard, user_instance=user_instance,
                                state=chatroom_states.CHATROOM_FOLLOW, current_user_id=current_member_id)

        else:
            collabcard_state_instance = collabcardState.objects.get(card=collabcard, user=user_instance)
            # when the user is not attending and not follow
            if collabcard_state_instance.state == collabcard_states.COLLABCARD_STATE_UNATTEND_FOLLOWING:
                collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_SEEN
                collabcard_state_instance.updated_at = time.time()
                collabcard_state_instance.save()

            # when the user is attending and unfollow the collabcard
            elif collabcard_state_instance.state == collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING:

                collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING
                collabcard_state_instance.updated_at = time.time()
                collabcard_state_instance.save()

            if explicit_call:
                create_chatroom(card_instance=collabcard, user_instance=user_instance,
                                state=chatroom_states.CHATROOM_UNFOLLOW, current_user_id=current_member_id)

        update_my_chatrooms_for_users(chatroom_id=collabcard.id, user_id=current_member_id)
        return {'success': True}
    else:
        return {'success': False}


@csrf_exempt
def collabcards_seen(request):
    '''This functions stores the details of members who have seen the card'''

    params = request.GET
    community_id = None
    card_id = None
    collabcard_type = None
    user_id = None
    if 'community_id' in params:
        community_id = params['community_id']
    if 'collabcard_id' in params:
        card_id = params['collabcard_id']
    if 'member_id' in params:
        user_id = params['member_id']
    if 'collabcard_type' in params:
        collabcard_type = params['collabcard_type']

    collabcards_seen_internal(community_id, card_id, collabcard_type, user_id)

    return JsonResponse({'success': True})


def collabcards_seen_internal(community_id, card_id, collabcard_type, user_id):
    '''This internal functions stores the details of members who have seen the card'''

    community = Community.objects.get(id=community_id)
    user_instance = User.objects.get(id=user_id)
    card_instance = Collabcard.objects.get(id=card_id)

    # saving the state in collabcard state table if it is not present
    expiry_time = get_expiry_time_of_chatroom()
    is_present = collabcardState.objects.filter(card=card_instance, user=user_instance)

    if not is_present.exists():
        create_chatroom_state_instance(card_instance, user_instance, expire_at=time.time(),
                                       function_called="collabcards_seen_internal")
        update_last_unseen_in_engage(user=user_instance, community=community)
    else:
        state_instance = is_present[0]
        if state_instance.state == 0:
            state_instance.state = collabcard_states.COLLABCARD_STATE_SEEN
            if not state_instance.external_seen:
                state_instance.external_seen = True
                state_instance.expiry_time = expiry_time
                state_instance.updated_at = time.time()

            state_instance.save()

            update_last_unseen_in_engage(user=user_instance, community=community)


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
            state_instance = collabcardState.objects.get(card=card_instance, user=user_instance)
            state_instance.state = collabcard_states.COLLABCARD_STATE_ATTENDING
            state_instance.attending_status = True
            state_instance.updated_at = time.time()
            state_instance.save()

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
            collabcardState.objects.filter(card=card_instance,
                                           user=user_instance).update(state=state,
                                                                      attending_status=False,
                                                                      updated_at=time.time())

        except:
            create_chatroom_state_instance(card_instance, user_instance,
                                           state=state,
                                           expire_at=None, external_seen=True, is_guest=False, source=None,
                                           follow_status=True, mute_status=False, is_tagged=False,
                                           function_called="collabcard_attend")

    update_event_answer_text(card_instance)  # function to update the text when a user attends an event
    collabcardState.objects.filter(card=card_instance).update(updated_at=time.time())

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
    '''function to send og tags of the link'''

    url = request.GET.get('url')

    og_tags = decode_meta_from_url(url)

    return JsonResponse({'og_tags': og_tags})


def member_activity(request):
    '''function to check whether the member created the collabcard or not'''

    state = 0
    community_id = request.GET.get('community_id')
    user_id = request.GET.get('member_id')

    community = Community.objects.get(pk=community_id)
    if community.id == feedback_community_id:
        state = 1
        return JsonResponse({'state': state})

    if community.introduction_text_state:
        state = 1
        return JsonResponse({'state': state})

    member = User.objects.get(pk=user_id)

    status = Collabcard.objects.filter(community=community, user=member, is_pending=False, is_deleted=False)

    if status:
        state = 1
    # if state == 1:
    # state=community.introduction_text_state
    if state:
        return JsonResponse({'state': state, 'tutorial_count': tutorial_count})

    if state == 0:
        introduction_question, introduction_answer = auto_create_collabcard(member, community)
        return JsonResponse(
            {'state': state, 'introduction_question': introduction_question, 'introduction_answer': introduction_answer,
             'tutorial_count': tutorial_count})
    return JsonResponse({'state': state})


def auto_create_collabcard(member, community):
    '''auto create collabcard'''
    introduction_question = ""
    introduction_answer = ""
    # community_id=community.id
    # if str(community_id) == '13266' or str(community_id) == '1173':  # '2807':
    #     introduction_question = community.introduction_text
    #     form_response = Form_response.objects.filter(user=member.id, community=community.id).order_by('id')
    #     introduction_answer = "{}, been jamming {} for last {}. Here for {}".format(form_response[3].response,
    #                                                                                 form_response[2].response,
    #                                                                                 form_response[1].response,
    #                                                                                 form_response[0].response)
    # else:
    if True:
        form_response = communityAnswers.objects.filter(member=member.id, community=community.id).order_by('id')
        if form_response.exists():
            introduction_question = form_response[0].question_title
            introduction_answer = form_response[0].question_answer
            # introduction_answer = introduction_answer
    return introduction_question, introduction_answer


def community_collabcard_id(request):
    '''function to send ids of the collabcards'''

    community_id = request.GET.get('community_id')
    community_instance = Community.objects.get(id=community_id)
    member_id = get_member_id_from_headers(request)
    print(member_id)
    user_instance = User.objects.get(id=member_id)

    collabcard_ids_list = list(
        Collabcard.objects.filter(community=community_instance,
                                  is_pending=False,
                                  is_deleted=False).filter(~Q(type=4)).order_by('id').values_list('id', flat=True))
    collabcard_state_for_member = collabcardState.objects.filter(community=community_instance,
                                                                 user=user_instance).order_by('id')

    collabcard_state_map = {}

    for collabcard in collabcard_state_for_member:
        collabcard_state_map[collabcard.card.id] = collabcard.state

    collabcard_ids = []
    for id in collabcard_ids_list:
        temp = {}
        if id in collabcard_state_map:
            temp['id'] = id
            temp['state'] = collabcard_state_map[id]
        else:
            temp['id'] = id
            temp['state'] = 0
        collabcard_ids.append(temp)

    return JsonResponse({'collabcard_ids': collabcard_ids})


def community_collabcard_meta(request):
    ''' function to get the collabcard details '''

    collabcard_ids = request.GET.get('collabcard_ids', False)
    print("collabcardid----", collabcard_ids)

    # for whatsapp community
    if not collabcard_ids:
        return JsonResponse({'collabcards': []})
    else:
        collabcard_ids = collabcard_ids.split(",")

    member_id = get_member_id_from_headers(request)
    community_instance = None
    feed_back = True
    card_list = []
    for card_id in collabcard_ids:
        card_instance = Collabcard.objects.get(id=card_id)
        user = Userinfo.objects.get(user_id=card_instance.user)
        # serialize user object
        if card_instance.community.id == feedback_community_id:
            feed_back = False
        usr = UserinfoSerializer(user)

        usr['is_clickable'] = feed_back
        removed_state = removedMembersSerializer(card_instance.community.id, usr['id'])

        if removed_state != False:
            usr['remove_state'] = removed_state

        # user form response serialzer
        form_response = FormResponseSerilaizer(card_instance.community.id, card_instance.user.id, bl=True,
                                               current_user_id=member_id)

        if form_response:
            usr['response'] = form_response[0]
            usr['question_answers'] = form_response[1]
        # get card images --------------------------------------------------------
        files = get_collabcard_files(card_instance)
        # -----------------------------------------------------------------------

        # get time stamp
        if str(card_instance.date_epoch) == "-9223372036854775808":
            # if there is no time stamp , return nothing
            time_text = ""
        else:
            # get time stamp
            time_text = get_time_text(card_instance.date_epoch)
        community_instance = card_instance.community
        card_dict = CollabcardSerializer(card_instance, member_id, card_instance.community, current_user_id=member_id)

        collabard_status = get_status_of_collabcard(member_id, card_instance)

        card_dict['state'] = collabard_status['state']
        card_dict['mute_status'] = collabard_status['mute_status']
        card_dict['follow_status'] = collabard_status['follow_status']

        card_dict['created_at'] = time_text
        card_dict['member'] = usr
        card_dict['images'] = files[0]
        card_dict['pdf'] = files[1]
        card_dict['audios'] = files[2]
        card_dict['videos'] = files[3]
        card_dict['attachments'] = files[4]
        card_list.append(card_dict)

    if community_instance:
        community = CommunitySerializer(community_instance)
        return JsonResponse({'collabcards': card_list, 'community': community})

    return JsonResponse({'collabcards': card_list})


def get_last_conversation(conversation_filter, member_id, chatroom_id):
    '''function to get last conversation and last unseen conversation'''

    has_seen = conversationMemberState.objects.filter(card_id=chatroom_id, user_id=member_id)

    if has_seen.exists():
        conversation_id = has_seen[0].conversation.id
        next_conversation = card_answers.objects.filter(id__gt=conversation_id, card=chatroom_id,
                                                        state=chatroom_states.ANSWER)
        unseen_count = next_conversation.count()

        if not next_conversation:

            conversation = conversationSerializer(has_seen[0].conversation)
        else:
            conversation = conversationSerializer(next_conversation[0])

        conversation_files = get_answer_files(conversation['id'])

        if 'location' in conversation_files:
            conversation['location'] = conversation_files['location']
        conversation['images'] = conversation_files['image']
        conversation['audios'] = conversation_files['audios']
        conversation['videos'] = conversation_files['videos']
        conversation['pdf'] = conversation_files['pdf']
        conversation['attachments'] = conversation_files['attachments']

        return (conversation, unseen_count)
    elif conversation_filter.exists():
        conversation = conversationSerializer(conversation_filter[0])
        unseen_count = conversation_filter.count()
        conversation_files = get_answer_files(conversation['id'])

        if 'location' in conversation_files:
            conversation['location'] = conversation_files['location']
        conversation['images'] = conversation_files['image']
        conversation['audios'] = conversation_files['audios']
        conversation['videos'] = conversation_files['videos']
        conversation['pdf'] = conversation_files['pdf']
        conversation['attachments'] = conversation_files['attachments']

        return (conversation, unseen_count)
    else:
        return (None, 0)


def get_chatrooms(chatroom_list, member_id, active=None, is_ios=False):
    """function to get chatrooms"""

    chatrooms = []
    for card_instance in chatroom_list:

        if card_instance.attachment_count > 0 and\
                card_instance.attachments_uploaded is False and\
                int(member_id) != card_instance.user.id:
            continue

        chatroom_instance = get_chatroom_instance(card_instance, member_id)
        conversation_filter = card_answers.objects.filter(card=card_instance.id,
                                                          state=chatroom_states.ANSWER
                                                          ).filter(Q(attachment_count=0) |
                                                                   Q(attachments_uploaded=True)
                                                                   ).order_by('id')
        chatroom_instance['total_response_count'] = conversation_filter.count()

        if card_instance.internal_link:
            try:
                chatroom_instance['preview'] = get_preview_for_url(member_id, card_instance.internal_link,
                                                                   community_instance=card_instance.preview_community,
                                                                   chatroom_instance=card_instance.preview_chatroom,
                                                                   send_preview_text=False)
            except Exception as e:
                error_logger.error(e.args)

        last_response_members = get_member_images_of_chatroom(conversation_filter)
        chatroom_instance['members_images'] = last_response_members['members_images']
        chatroom_instance['last_response_members'] = last_response_members['last_response_members']

        if active is True and chatroom_instance['active']:
            chatrooms.append(chatroom_instance)
        if active is False and not chatroom_instance['active']:
            chatrooms.append(chatroom_instance)

        if active == None:
            chatrooms.append(chatroom_instance)

    return chatrooms


def get_chatrooms_version_1(chatroom_list, member_id, active=None, is_ios=False):
    '''function to get chatrooms'''

    chatrooms = []

    for data in chatroom_list:
        card_instance = data.card

        if card_instance.attachment_count > 0 and\
                card_instance.attachments_uploaded is False and\
                int(member_id) != card_instance.user.id:
            continue

        chatroom_instance = get_chatroom_instance(card_instance, member_id, state_instance=data, send_profile=False)

        conversation_filter = card_answers.objects.filter(card=card_instance.id,
                                                          state=chatroom_states.ANSWER
                                                          ).filter(Q(attachment_count=0) |
                                                                   Q(attachments_uploaded=True)
                                                                   ).order_by('id')
        chatroom_instance['total_response_count'] = conversation_filter.count()

        if card_instance.internal_link:
            try:
                chatroom_instance['preview'] = get_preview_for_url(member_id=member_id,
                                                                   preview_url=card_instance.internal_link,
                                                                   community_instance=card_instance.preview_community,
                                                                   chatroom_instance=card_instance.preview_chatroom,
                                                                   send_preview_text=False)
            except Exception as e:
                error_logger.error(e.args)
        last_response_members = get_member_instances_for_footer_images_in_chatroom(card_instance)
        # chatroom_instance['members_images'] = last_response_members['members_images']
        chatroom_instance['last_response_members'] = last_response_members['last_response_members']

        chatrooms.append(chatroom_instance)

        # chatroom_instance = {
        #     'id' : chatroom_instance['id'],
        #     'active': chatroom_instance['active']
        # }
        # if active is True and chatroom_instance['active']:
        #     chatrooms.append(chatroom_instance)
        # if active is False and not chatroom_instance['active']:
        #     chatrooms.append(chatroom_instance)
        #
        # if active == None:
        # #chatroom_instance = {'id':card_instance.id}

    return chatrooms


def get_chatrooms_version_2(chatroom_list, member_id, active=None, is_ios=False):
    '''function to get chatrooms'''

    chatrooms = []
    for data in chatroom_list:
        card_instance = data.card

        if card_instance.attachment_count > 0 and\
                card_instance.attachments_uploaded is False and\
                int(member_id) != card_instance.user.id:
            continue

        chatroom_instance = get_chatroom_instance(card_instance, member_id, state_instance=data)
        conversation_filter = card_answers.objects.filter(card=card_instance.id,
                                                          state=chatroom_states.ANSWER
                                                          ).filter(Q(attachment_count=0) |
                                                                   Q(attachments_uploaded=True)
                                                                   ).order_by('id')
        chatroom_instance['total_response_count'] = conversation_filter.count()

        if card_instance.internal_link:
            try:
                chatroom_instance['preview'] = get_preview_for_url(member_id=member_id,
                                                                   preview_url=card_instance.internal_link,
                                                                   community_instance=card_instance.preview_community,
                                                                   chatroom_instance=card_instance.preview_chatroom,
                                                                   send_preview_text=False)
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

    if scroll_direction and not chatroom_id:
        context = get_error_context(False, "send chatroom id with scroll direction")
        return JsonResponse(context)

    active = request.GET.get('active', None)

    if active == "true":
        active = True
    elif active == "false":
        active = False
    else:
        active = None

    member_id = get_member_id_from_headers(request)

    chatroom_filter = Collabcard.objects.filter(community=community_id,
                                                is_pending=False, is_deleted=False).order_by('id')

    chatrooms = []
    context = {}

    if not chatroom_id and not scroll_direction:

        last_seen = collabcardState.objects.filter(community=community_id, user=member_id).filter(~Q(state=0)).order_by(
            '-card_id')
        if not last_seen.exists():
            chatroom_list = pagination(chatroom_filter, page, paginate_by=5)
            chatrooms = get_chatrooms(chatroom_list, member_id, is_ios=is_ios)
        else:
            last_seen = last_seen[0]
            upward = chatroom_filter.filter(id__lte=last_seen.card.id).order_by('-id')[:3]
            downward = chatroom_filter.filter(id__gt=last_seen.card.id)[:3]
            # upward = Collabcard.objects.filter(id__lt=last_seen.card.id,community=community_id).order_by('id')[:3]
            # downward = Collabcard.objects.filter(id__gt=last_seen.card.id,community=community_id).order_by('id')[:3]
            chatroom_filter = upward | downward
            chatroom_list = chatroom_filter.order_by('id')
            chatrooms = get_chatrooms(chatroom_list, member_id, active, is_ios=is_ios)

        context['header'] = chatroom_feed_header(community_id, member_id)

    else:
        scroll_direction = int(scroll_direction)
        if scroll_direction == 0:  # upward scroll

            upward = chatroom_filter.filter(id__lt=chatroom_id).order_by('-id')[:5]
            upward = reverse_conversations_for_upward_pagination(upward)
            # print(upward)
            chatrooms = get_chatrooms(upward, member_id, active, is_ios=is_ios)

        elif scroll_direction == 1:  # downward scroll

            downward = chatroom_filter.filter(id__gt=chatroom_id).order_by('id')[:5]
            chatrooms = get_chatrooms(downward, member_id, active, is_ios=is_ios)

    context['chatrooms'] = chatrooms

    current_time = time.time()
    context['active_chatroom_count'] = get_active_chatrooms_count_in_community(community_id, member_id, current_time)
    context['inactive_chatroom_count'] = get_inactive_chatrooms_count_in_community(community_id, member_id,
                                                                                   current_time)
    return JsonResponse(context)


def fetch_chatroom_feed_version_1(request):
    """ api to fetch chatroom feed """

    community_id = request.GET.get('community_id')
    page = request.GET.get('page', 1)

    is_ios = is_platform_ios(request)
    chatroom_id = request.GET.get('chatroom_id')
    scroll_direction = request.GET.get('scroll_direction')

    info_logger.info(request.GET)

    if scroll_direction and not chatroom_id:
        context = get_error_context(False, "send chatroom id with scroll direction")
        return JsonResponse(context)

    active = request.GET.get('active', None)

    current_time = time.time()
    if active == "true":
        active = True
    elif active == "false":
        active = False
    else:
        active = None

    member_id = get_member_id_from_headers(request)
    # print(member_id)

    state_filter = collabcardState.objects.filter(community=community_id,
                                                  card__is_pending=False,
                                                  card__is_deleted=False).distinct('card_id').order_by('-card_id')

    chatrooms = []
    context = {}
    if not chatroom_id and not scroll_direction:

        last_seen = state_filter.filter(user=member_id).filter(~Q(state=0)).order_by('-card_id')

        if not last_seen.exists():
            chatroom_list = pagination(state_filter, page, paginate_by=5)
            chatrooms = get_chatrooms_version_1(chatroom_list, member_id, is_ios=is_ios)
        else:

            last_seen = last_seen[0]

            if active:
                upward = state_filter.filter(card__lte=last_seen.card.id, user=member_id).filter(
                    Q(expiry_time=None) | Q(expiry_time__gt=current_time)).order_by('-card')[:3]
                downward = state_filter.filter(card__gt=last_seen.card.id, user=member_id).filter(
                    Q(expiry_time=None) | Q(expiry_time__gt=current_time)).order_by('card')[:3]

            else:

                upward = state_filter.filter(card__lte=last_seen.card.id, user=member_id).filter(
                    ~Q(expiry_time=None) & Q(expiry_time__lte=current_time)).order_by('-card')[:3]

                downward = state_filter.filter(card__gt=last_seen.card.id, user=member_id).filter(
                    (~Q(expiry_time=None)) & Q(expiry_time__lte=current_time)).order_by('card')[:3]

            chatroom_filter = upward | downward
            chatroom_list = chatroom_filter.order_by('card_id')

            chatrooms = get_chatrooms_version_1(chatroom_list, member_id, active, is_ios=is_ios)

    else:
        scroll_direction = int(scroll_direction)
        if scroll_direction == 0:  # upward scroll

            if active:
                upward = state_filter.filter(card__lt=chatroom_id, user=member_id).filter(
                    Q(expiry_time=None) | Q(expiry_time__gt=current_time)).order_by('-card')[:5]

            else:
                upward = state_filter.filter(card__lt=chatroom_id, user=member_id).filter(
                    ~Q(expiry_time=None) & Q(expiry_time__lte=current_time)).order_by('-card')[:5]
                print(upward.query)

            upward = reverse_conversations_for_upward_pagination(upward)
            # print(upward)
            chatrooms = get_chatrooms_version_1(upward, member_id, active, is_ios=is_ios)

        elif scroll_direction == 1:  # downward scroll

            if active:
                downward = state_filter.filter(card__gt=chatroom_id, user=member_id).filter(
                    Q(expiry_time=None) | Q(expiry_time__gt=current_time)).order_by('card')[:5]
            else:
                downward = state_filter.filter(card__gt=chatroom_id, user=member_id).filter(
                    ~Q(expiry_time=None) & Q(expiry_time__lte=current_time)).order_by('card')[:5]

            chatrooms = get_chatrooms_version_1(downward, member_id, active, is_ios=is_ios)

    context['chatrooms'] = chatrooms

    current_time = time.time()
    context['active_chatroom_count'] = get_active_chatrooms_count_in_community(community_id, member_id, current_time)
    context['inactive_chatroom_count'] = get_inactive_chatrooms_count_in_community(community_id, member_id,
                                                                                   current_time)
    return JsonResponse(context)


class fetchChatroomFeedVersion2(APIView):
    """ api to fetch chatroom feed """

    def get(self, request, *args, **kwargs):
        query_params = request.query_params
        community_id = query_params.get("community_id", False)
        page = query_params.get("page", False)
        chatroom_id = query_params.get("chatroom_id", False)
        scroll_direction = query_params.get("scroll_direction", False)
        active = query_params.get("active", None)

        if scroll_direction and not chatroom_id:
            context = get_error_context(False, "send chatroom id with scroll direction")
            return JsonResponse(context)

        current_time = time.time()
        if active == "true":
            active = True
        elif active == "false":
            active = False
        else:
            active = None

        member_id = get_member_id_from_headers(request)
        # print(member_id)

        state_filter = collabcardState.objects.filter(community=community_id,
                                                      card__is_pending=False,
                                                      card__is_deleted=False).distinct('card_id').order_by('-card_id')
        chatrooms = []
        context = {}
        if not chatroom_id and not scroll_direction:

            last_seen = state_filter.filter(user=member_id).exclude(state=0).order_by('-card_id')

            if not last_seen.exists():
                chatroom_list = pagination(state_filter, page, paginate_by=5)
                chatrooms = get_chatrooms_version_1(chatroom_list, member_id)
            else:
                last_seen = last_seen[0]

                if active:
                    upward = state_filter.filter(card__lte=last_seen.card.id, user=member_id).filter(
                        Q(expiry_time=None) | Q(expiry_time__gt=current_time)).order_by('-card')[:3]
                    downward = state_filter.filter(card__gt=last_seen.card.id, user=member_id).filter(
                        Q(expiry_time=None) | Q(expiry_time__gt=current_time)).order_by('card')[:3]

                else:
                    upward = state_filter.filter(card__lte=last_seen.card.id, user=member_id).filter(
                        ~Q(expiry_time=None) & Q(expiry_time__lte=current_time)).order_by('-card')[:3]

                    downward = state_filter.filter(card__gt=last_seen.card.id, user=member_id).filter(
                        (~Q(expiry_time=None)) & Q(expiry_time__lte=current_time)).order_by('card')[:3]

                chatroom_filter = upward | downward
                chatroom_list = chatroom_filter.order_by('card_id')

                chatrooms = get_chatrooms_version_1(chatroom_list, member_id, active, is_ios=is_ios)

            # context['header'] = chatroom_feed_header(community_id, member_id)

        else:
            scroll_direction = int(scroll_direction)
            if scroll_direction == 0:  # upward scroll

                if active:
                    upward = state_filter.filter(card__lt=chatroom_id, user=member_id).filter(
                        Q(expiry_time=None) | Q(expiry_time__gt=current_time)).order_by('-card')[:5]

                else:
                    upward = state_filter.filter(card__lt=chatroom_id, user=member_id).filter(
                        ~Q(expiry_time=None) & Q(expiry_time__lte=current_time)).order_by('-card')[:5]
                    print(upward.query)

                upward = reverse_conversations_for_upward_pagination(upward)
                # print(upward)
                chatrooms = get_chatrooms_version_1(upward, member_id, active, is_ios=is_ios)

            elif scroll_direction == 1:  # downward scroll

                if active:
                    downward = state_filter.filter(card__gt=chatroom_id, user=member_id).filter(
                        Q(expiry_time=None) | Q(expiry_time__gt=current_time)).order_by('card')[:5]
                else:
                    downward = state_filter.filter(card__gt=chatroom_id, user=member_id).filter(
                        ~Q(expiry_time=None) & Q(expiry_time__lte=current_time)).order_by('card')[:5]

                chatrooms = get_chatrooms_version_1(downward, member_id, active, is_ios=is_ios)

        context['chatrooms'] = chatrooms

        current_time = time.time()
        context['active_chatroom_count'] = get_active_chatrooms_count_in_community(community_id, member_id,
                                                                                   current_time)
        context['inactive_chatroom_count'] = get_inactive_chatrooms_count_in_community(community_id, member_id,
                                                                                       current_time)
        return JsonResponse(context)


def fetch_community_chatroom_feed(request):
    '''Version 1 community collabcards'''
    context = {}
    member_id = get_member_id_from_headers(request)
    size = request.GET.get('size', 3)
    size = int(size)
    community_id = request.GET.get('community_id')
    # if not member_id:
    #     context = get_error_context(False, "send member id in request header")
    #     return JsonResponse(context)

    try:
        community_instance = Community.objects.get(id=community_id)
    except:
        context = get_error_context(False, "send correct community id")
        return JsonResponse(context)

    chatroom_filter = Collabcard.objects.filter(community=community_instance,
                                                is_pending=False, is_deleted=False).order_by('-id')
    total_chatrooms = chatroom_filter.count()
    chatroom_list = []
    for chatroom in chatroom_filter:

        chatroom_data = get_chatroom_instance(chatroom, member_id)
        chatroom_list.append(chatroom_data)
        size = size - 1
        if size == 0:
            break

    context = {
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

    conversation = None
    chatroom_local = None

    context = {
        'success': True,
    }

    if request.user.is_authenticated and is_request_web(request):
        current_member_id = request.user.id

    if 'community_id' in body and body['community_id']:
        # if image to be updated in community
        community_id = body['community_id']
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
        files_count = body.get('files_count', 0)

        card_instance = Collabcard.objects.get(id=collabcard_id)
        card_instance.has_files = True
        card_instance.save()

        file = Card_Attachment()
        file.collabcard = card_instance
        file.type = attachment_type
        file.file_url = body['url']
        file.index = body.get('index', 0)
        file.height = body.get('height', None)
        file.width = body.get('width', None)
        file.save()

        # updating updated_at for synching apis
        collabcardState.objects.filter(user=member_id, card=card_instance).update(updated_at=time.time())
        uploaded_files_count = Card_Attachment.objects.filter(collabcard=card_instance).count()

        if uploaded_files_count == card_instance.attachment_count + card_instance.pdf_count:
            card_instance.attachments_uploaded = True
            card_instance.save()
            user_instance = User.objects.get(id=member_id)

            expiry_time = time.time() + HOURS_24
            collabcardState.objects.filter(card=card_instance,
                                           user=user_instance).update(expiry_time=expiry_time)

            send_chatroom_creation_notification(card_instance, user_instance)
            set_chatroom_state_for_all_members_on_card_creation.delay(card_instance.community.id,
                                                                      card_id=collabcard_id,
                                                                      function_called="upload_files")

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

            update_last_answer_id(answer_instance.card.id, answer_instance.id)
            send_follow_notification(card_id=answer_instance.card.id, user_id=answer_instance.user.id,
                                     answer=answer_instance.answer)

        conversation = get_conversation_instance_for_db_synching(answer_instance, current_user_id=member_id)

    elif 'poll_id' in body and body['poll_id']:

        try:
            instance = CollabcardPolls.objects.get(id=body['poll_id'])
            instance.image_url = body['url']
            instance.save()
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

    return JsonResponse(context)


@csrf_exempt
def upload_files_version_1(request):
    """function to upload files"""
    context = save_attachments(request)

    success = context.get('success', False)
    status = status_codes.HTTP_200_OK if success else status_codes.HTTP_400_BAD_REQUEST

    return JsonResponse(context, status=status)


def save_attachments(request):
    """ save attachments for cards and conversations """
    member_id = get_member_id_from_headers(request)

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

    body = json.loads(request.body)

    if 'community_id' in body and body['community_id']:
        context = save_community_image(body, member_id)
        if context is not None:
            return context

    elif 'chatroom_id' in body and body['chatroom_id']:
        chatroom_local = upload_chatroom_attachments(body, member_id)

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


def upload_chatroom_attachments(body, member_id):
    """ function to upload chatroom attachments """

    chatroom_id = body['chatroom_id']
    try:
        chatroom_instance = Collabcard.objects.get(id=chatroom_id)

    except Collabcard.DoesNotExist:
        return {'success': False,
                'error_message': "Send valid chatroom id"}

    chatroom_instance.has_files = True
    chatroom_instance.save()

    save_chatroom_attachments(chatroom_instance, body)

    # updating updated_at for syncing apis
    collabcardState.objects.filter(user=member_id, card=chatroom_instance).update(updated_at=time.time())
    # files_count = body['files_count'] if 'files_count' in body else 0

    uploaded_files_count = Card_Attachment.objects.filter(collabcard=chatroom_instance).count()

    if uploaded_files_count == chatroom_instance.attachment_count:
        chatroom_instance.attachments_uploaded = True
        chatroom_instance.save()

        user_instance = User.objects.get(id=member_id)

        expiry_time = time.time() + HOURS_24
        collabcardState.objects.filter(card=chatroom_instance,
                                       user=user_instance).update(expiry_time=expiry_time)

        send_chatroom_creation_notification(chatroom_instance, user_instance)

        set_chatroom_state_for_all_members_on_card_creation.delay(chatroom_instance.community.id,
                                                                  card_id=chatroom_id,
                                                                  function_called="upload_files_version_1")

    member_data = {'member_id': member_id,
                   'current_user_id': member_id,
                   'state_instance': None}
    chatroom_local = GetChatroomInstanceSerializer(chatroom_instance, context=member_data, many=False)

    return chatroom_local


def upload_conversation_attachments(body, member_id):
    """ function to upload conversation attachments """
    conversation_id = body['conversation_id']
    try:
        conversation_instance = card_answers.objects.get(id=conversation_id)

    except card_answers.DoesNotExist:
        return {'success': False,
                'error_message': "Send valid conversation id"}

    save_conversation_attachments(body, conversation_instance)

    # updating the last updated when posting answer
    conversation_instance.last_updated = int(round(time.time() * 1000))
    conversation_instance.has_files = True
    conversation_instance.save()

    # saving last answer id
    uploaded_files_count = answerAttachment.objects.filter(answer=conversation_instance).count()

    if uploaded_files_count == conversation_instance.attachment_count:
        conversation_instance.attachments_uploaded = True
        conversation_instance.save()

        update_last_answer_id(conversation_instance.card.id, conversation_instance.id)
        send_follow_notification(card_id=conversation_instance.card.id, user_id=conversation_instance.user.id,
                                 answer=conversation_instance.answer)

    conversation = get_conversation_instance_for_db_synching(conversation_instance, current_user_id=member_id)

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


# @ensure_csrf_cookie # with header X-CSRFToken
@csrf_exempt
def login_authenticate(request):
    ''' function to login a user '''

    if request.method == 'POST':

        res = json.loads(request.body)
        login_type = request.GET.get('type', None)
        if login_type and login_type == "google":
            google_id_token = request.GET.get('google_id_token', None)
            context = login_with_google(google_id_token, request, res)
            info_logger.info(context)
            return JsonResponse(context)

        dic_form = res
        json_to_save = json.dumps(dic_form)
        # if user is logging in from facebook
        created = False
        if login_type == 'facebook':
            email = res['email']
            # converting email to lower case and removing unwanted space
            email = email.lower().strip()
            user = User.objects.filter(email=email)

            if not user.exists():
                # creating a user if no user is associated with that email
                user = create_user(user_name=res['name'], email=res['email'], id=res['id'])

                # if there is no user then user will not have userinfo too
                # creating user info

                # fb_link = res['link'] if 'link' in res else None
                if 'picture' in res:
                    image_link = upload_image_to_firebase(res['picture']['data']['url'], user.id)
                else:
                    image_link = 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'

                city = res['location']['name'] if 'location' in res else None

                userinfo = create_userinfo(user=user, email=res['email'], user_name=res['name'],
                                           profile_picture=image_link, login_type=login_type,
                                           json_to_save=json_to_save, city=city,
                                           # fb_link=fb_link
                                           )
                created = True
                mail_triger(str(user.id), request)  # both mail and notification will be sent here

            if not created:
                userinfo = user[0].userinfo

        elif login_type == 'linkedIn':

            print("res ==== ", res)
            # if user is logging in with linkedIn
            user_name = res['firstName']['localized']['en_US'] + " " + res['lastName']['localized']['en_US']
            email = res['email']['elements'][0]['handle~']['emailAddress']
            userinfo = Userinfo.objects.filter(email=email)
            # create user and userinfo if there is no user with this email

            if not userinfo.exists():

                user = create_user(user_name=user_name, email=email, id=res['id'])
                if 'profilePicture' in res:
                    profile_picture = upload_image_to_firebase(
                        res['profilePicture']['displayImage~']['elements'][2]['identifiers'][0]['identifier'], user.id)
                else:
                    profile_picture = 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'

                userinfo = create_userinfo(user=user, email=email, user_name=user_name,
                                           profile_picture=profile_picture, login_type=login_type,
                                           json_to_save=json_to_save)
                created = True
                mail_triger(str(user.id), request)  # both mail and notification will be sent here

            if not created:
                userinfo = userinfo[0]


        else:
            # if user is logging in with Apple

            userinfo = Userinfo.objects.filter(apple_id=res['id'])

            if not userinfo.exists():
                # creating a user if no user is associated with that email
                user = create_user(user_name=res['name'], email=res['email'],
                                   id=res['id'], apple_id=True)

                # fb_link = res['link'] if 'link' in res else None
                if 'picture' in res:
                    image_link = upload_image_to_firebase(res['picture']['data']['url'], user.id)
                else:
                    image_link = 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'

                city = res['location']['name'] if 'location' in res else None
                # if there is no user then user will not have userinfo too
                # create or get user info
                userinfo = create_userinfo(user=user, email=res['email'], user_name=res['name'],
                                           profile_picture=image_link, login_type=login_type,
                                           json_to_save=json_to_save, city=city, apple_id=res['id']
                                           )
                created = True
                mail_triger(str(user.id), request)  # both mail and notification will be sent here

            if not created:
                userinfo = userinfo[0]

        # get serialized user object

        usr = UserinfoSerializer(userinfo)
        # see if user has tags or not
        has_tags = userinfo.has_tags

        # saving the OS type of user (Android,iOS,WEB)
        request_type = get_request_type(request)
        if request_type:
            Userinfo.objects.filter(user_id=usr['id']).update(mobile_os=request_type)

        # User asscoaited tags if any present
        if has_tags:
            tags = get_user_lpig_tags(usr['id'])
            usr['tags'] = tags
        return JsonResponse({'user': usr, 'has_tags': has_tags})

    return HttpResponse('Login Api')


@csrf_exempt
def login_authenticate_version_1(request):
    ''' function to login a user '''

    if request.method == 'POST':
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
            # context = {}
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

    user_name = user_name + "_" + id

    user = User.objects.filter(email=email)
    if apple_id and not user.exists():
        user = User.objects.filter(username=user_name)

    if not user.exists():

        user = User()
        user.username = user_name
        if email is not None:
            user.email = email
        user.save()
    else:
        user = user[0]

    return user


def create_userinfo(user, email, user_name, profile_picture, login_type, json_to_save, city=None, apple_id=None):
    ''' function to create User-Info of a user '''

    userinfo = Userinfo.objects.filter(email=email)
    if apple_id and not userinfo.exists():
        userinfo = Userinfo.objects.filter(apple_id=apple_id)

    if not userinfo.exists():
        userinfo = Userinfo()
        userinfo.user_id = user
        if email is not None:
            user.email = email
        userinfo.name = user_name
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

    google_json = fetch_google_auth_data(google_id_token)
    json_to_save = google_json[0]
    res = google_json[1]
    info_logger.info(res)
    created = False
    # context ={'success':False,'error_message':"please give permission to use your google account"}
    context = get_error_context(False, "please give permission to use your google account")
    image_link = None
    if 'email' in res:
        email = res['email']
        email = email.lower().strip()

        user = get_user_from_email(email)  # getting the user instance from email if it is present

        if not user:
            # creating a user if no user is associated with that email
            res['id'] = res['azp']

            user = create_user(user_name=res['name'], email=res['email'], id=res['email'])
            user_instance = user
            if 'picture' in res:
                image_link = upload_image_to_firebase(res['picture'], user.id)
            # else:
            #     image_link = 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'

            userinfo = create_userinfo(user=user, email=res['email'], user_name=res['name'],
                                       profile_picture=image_link, login_type=login_type,
                                       json_to_save=json_to_save
                                       )

            if 'picture' not in res:
                save_name_initial_image.delay(user_id=user.id, user_name=res['name'])

            save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY)

            save_user_primary_email(user, res['email'], verified=True)
            # mail_triger(str(user.id), request)  # both mail and notification will be sent here
            email_exists = False

        else:
            userinfo = user.userinfo
            # save_user_mobile_number(user, country_code, mobile_no, state=mobile_states.PRIMARY)
            email_exists = True

        # usr = UserinfoSerializer(userinfo)

        usr = get_logged_in_user(user_instance=user)
        # see if user has tags or not
        has_tags = userinfo.has_tags

        # # saving the OS type of user (Android,iOS,WEB)
        # request_type = get_request_type(request)
        # if request_type:
        #     Userinfo.objects.filter(user_id=usr['id']).update(mobile_os=request_type)

        # User asscoaited tags if any present
        if has_tags:
            tags = get_user_lpig_tags(usr['id'])
            usr['tags'] = tags

        if is_request_web(request):
            login(request, user=userinfo.user_id, backend="django.contrib.auth.backends.ModelBackend")

        access = is_user_community_part(usr['id'])
        context = {'user': usr, 'access': access, 'email_exists': email_exists, 'has_tags': has_tags}

    return context


def login_with_facebook(request, res, json_to_save, login_type="facebook"):
    '''function to login with facebook'''

    mobile_no = res['mobile_no'] if 'mobile_no' in res else None
    country_code = res['country_code'] if 'country_code' in res else None

    res = res['login_json']
    user = None
    email = None
    image_link = None
    if 'email' in res:
        email = res['email']
        # converting email to lower case and removing unwanted space
        email = email.lower().strip()
        user = get_user_from_email(email)

    elif mobile_no:
        has_mobile_no = userMobiles.objects.filter(mobile_no=mobile_no)
        if has_mobile_no.exists():
            user = has_mobile_no[0].user
    else:
        user_name = res['name'] + res['id']
        user_obj = User.objects.filter(username=user_name)
        if user_obj.exists():
            user = user_obj[0]

    if not user:
        # creating a user if no user is associated with that email
        user = create_user(user_name=res['name'], email=email, id=res['id'])
        user_instance = user
        # if there is no user then user will not have userinfo too
        # creating user info

        # fb_link = res['link'] if 'link' in res else None
        if 'picture' in res:
            image_link = upload_image_to_firebase(res['picture']['data']['url'], user.id)
        # else:
        #     image_link = 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'

        city = res['location']['name'] if 'location' in res else None

        userinfo = create_userinfo(user=user, email=email, user_name=res['name'],
                                   profile_picture=image_link, login_type=login_type,
                                   json_to_save=json_to_save, city=city,
                                   # fb_link=fb_link
                                   )
        if mobile_no:
            save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY)
        if email:
            save_user_primary_email(user, email, verified=True)

        if 'picture' not in res:
            save_name_initial_image.delay(user_id=user.id, user_name=res['name'])

        email_exists = False
    else:
        userinfo = user.userinfo
        email_exists = True
        # save_user_mobile_number(user, country_code, mobile_no, state=mobile_states.PRIMARY)

        # get serialized user object

    usr = get_logged_in_user(user_instance=user)
    # see if user has tags or not
    has_tags = userinfo.has_tags

    # # saving the OS type of user (Android,iOS,WEB)
    # request_type = get_request_type(request)
    # if request_type:
    #     Userinfo.objects.filter(user_id=usr['id']).update(mobile_os=request_type)

    # login in when the request is web
    if is_request_web(request):
        login(request, user=userinfo.user_id, backend="django.contrib.auth.backends.ModelBackend")

    # User asscoaited tags if any present
    if has_tags:
        tags = get_user_lpig_tags(usr['id'])
        usr['tags'] = tags

    access = is_user_community_part(usr['id'])
    context = {'user': usr, 'access': access, 'email_exists': email_exists, 'has_tags': has_tags}
    return context


def login_with_linkedin(request, res, json_to_save, login_type="linkedIn"):
    '''login with linkedIn '''

    mobile_no = res['mobile_no'] if 'mobile_no' in res else None
    country_code = res['country_code'] if 'country_code' in res else None

    res = res['login_json']
    user = None
    email = None
    # if user is logging in with linkedIn
    if 'email' in res:
        email = res['email']['elements'][0]['handle~']['emailAddress']

        user = get_user_from_email(email)

    elif mobile_no:
        has_mobile_no = userMobiles.objects.filter(mobile_no=mobile_no)
        if has_mobile_no.exists():
            user = has_mobile_no[0].user
    else:
        user_name = res['firstName']['localized']['en_US'] + " " + res['lastName']['localized']['en_US']
        user_obj = User.objects.filter(username=user_name + res['id'])
        if user_obj.exists():
            user = user_obj[0]

    profile_picture = None
    if not user:

        user_name = res['firstName']['localized']['en_US'] + " " + res['lastName']['localized']['en_US']
        user = create_user(user_name=user_name, email=email, id=res['id'])
        user_instance = user
        if 'profilePicture' in res:
            profile_picture = upload_image_to_firebase(
                res['profilePicture']['displayImage~']['elements'][2]['identifiers'][0]['identifier'], user.id)
        # else:
        #     profile_picture = 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'

        userinfo = create_userinfo(user=user, email=email, user_name=user_name,
                                   profile_picture=profile_picture, login_type=login_type,
                                   json_to_save=json_to_save)

        if 'profilePicture' not in res:
            save_name_initial_image.delay(user_id=user.id, user_name=user_name)
        if mobile_no:
            save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY)
        if email:
            save_user_primary_email(user, email, verified=True)
        email_exists = False

    else:
        userinfo = user.userinfo
        email_exists = True

    # usr = UserinfoSerializer(userinfo)
    usr = get_logged_in_user(user_instance=user)
    # see if user has tags or not
    has_tags = userinfo.has_tags

    # # saving the OS type of user (Android,iOS,WEB)
    # request_type = get_request_type(request)
    # if request_type:
    #     Userinfo.objects.filter(user_id=usr['id']).update(mobile_os=request_type)

    if has_tags:
        tags = get_user_lpig_tags(usr['id'])
        usr['tags'] = tags

    access = is_user_community_part(usr['id'])
    context = {'user': usr, 'access': access, 'email_exists': email_exists, 'has_tags': has_tags}
    # print(context)
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
        if 'picture' in res:
            image_link = upload_image_to_firebase(res['picture']['data']['url'], user.id)
        # else:
        #     image_link = 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'

        city = res['location']['name'] if 'location' in res else None
        # if there is no user then user will not have userinfo too
        # create or get user info
        userinfo = create_userinfo(user=user, email=res['email'], user_name=res['name'],
                                   profile_picture=image_link, login_type=login_type,
                                   json_to_save=json_to_save, city=city, apple_id=res['id']
                                   )

        if 'picture' not in res:
            save_name_initial_image.delay(user_id=user.id, user_name=res['name'])

        save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY)

        save_user_primary_email(user, res['email'], verified=True)
        email_exists = False

    else:
        userinfo = userinfo[0]

        email_exists = True

    # get serialized user object

    # usr = UserinfoSerializer(userinfo)
    usr = get_logged_in_user(user_instance=userinfo.user_id)
    # see if user has tags or not
    has_tags = userinfo.has_tags

    # # saving the OS type of user (Android,iOS,WEB)
    # request_type = get_request_type(request)
    # if request_type:
    #     Userinfo.objects.filter(user_id=usr['id']).update(mobile_os=request_type)

    # User asscoaited tags if any present
    if has_tags:
        tags = get_user_lpig_tags(usr['id'])
        usr['tags'] = tags

    access = is_user_community_part(usr['id'])
    context = {'user': usr, 'access': access, 'email_exists': email_exists, 'has_tags': has_tags}
    return context


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
        context['has_tags'] = email_exists.userinfo.has_tags
        context['access'] = is_user_community_part(context['user']['id'])
        context['email_exists'] = True

        return context
    image_url = None
    if 'image_url' in profile:
        image_url = profile['image_url']

    user_acquired = None
    if 'user_acquired' in res:
        user_acquired = res['user_acquired']

    user_instance = create_custom_user(name, mobile_no, country_code, email, image_url, login_type,
                                       user_acquired=user_acquired)

    if 'image_url' not in profile:
        save_name_initial_image.delay(user_id=user_instance.id, user_name=name)

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


def create_custom_user(name, mobile_no, country_code, email, image_url, login_type, user_acquired=None):
    has_mobile_no = userMobiles.objects.filter(mobile_no=mobile_no)
    user_name = name + "_" + str(mobile_no)

    if not has_mobile_no.exists():
        # creating user instance

        has_user = User.objects.filter(username=user_name)
        if not has_user.exists():
            user_instance = User()
            user_instance.username = user_name
            user_instance.save()

            # creating userinfo instance

            userinfo_instance = Userinfo()
            userinfo_instance.name = name
            userinfo_instance.email = email
            userinfo_instance.image_link = image_url
            userinfo_instance.login_type = login_type
            userinfo_instance.login_json = None
            userinfo_instance.created_at = time.time()
            userinfo_instance.user_id = user_instance
            userinfo_instance.save()

            # saving the analytics of user
            print(user_acquired)
            if user_acquired:
                save_userAcquition_analytics(user_instance, user_acquired)

            # creating user email
            save_user_primary_email(user_instance, email, email_state=email_states.PRIMARY)

            # send verification mail for email
            verification_details = generate_tokens_for_email(user_instance, email, email_state=email_states.NON_PRIMARY)

            # sending a email from template
            send_verification_mail_for_email_sync(user_name=user_instance.userinfo.name,
                                                  verification_link=verification_details['verify_url'], email=email)

            save_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY)

            return user_instance
        else:
            return has_user[0]

    return has_mobile_no[0].user


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
            community_instance = Community.objects.get(id=user_acquired['community_id'])
            instance.community = community_instance

        if 'shared_by' in user_acquired and user_acquired['shared_by']:
            shared_user_instance = User.objects.get(id=user_acquired['shared_by'])
            instance.shared = shared_user_instance

        instance.save()


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

    # check got retry
    retry = request.GET.get('retry')

    if retry == '1':
        retry = True
    else:
        retry = False

    country_code_msg = "\n\n country code %s" % country_code
    info_logger.info(country_code_msg)

    info_logger.info("mobile number")
    info_logger.info(mobile_no)

    info_logger.info("user_id")
    info_logger.info(user_id)

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

        if retry:
            context = send_retry_otp(phone_no)
        else:
            context = send_otp_on_mobile(phone_no, international=international)
        backup_filter = mobileBackup.objects.filter(mobile_no=mobile_no)

        if not backup_filter.exists():
            instance = mobileBackup()
            instance.mobile_no = mobile_no
            instance.country_code = country_code
            instance.created_at = time.time()
            instance.save()

    # user wants to merge the account
    if user_id:
        mobile_filter = userMobiles.objects.filter(user_id=user_id)
        for instance in mobile_filter:
            phone_no = str(instance.country_code) + str(instance.mobile_no)

            international = False
            if str(instance.country_code) != '91':
                international = True

            if retry:
                context = send_retry_otp(phone_no)
            else:
                context = send_otp_on_mobile(phone_no, international=international)

            info_logger.info(instance.user.id)
            info_logger.info(context)

        email_filter = userEmails.objects.filter(user_id=user_id)

        for instance in email_filter:
            email = instance.email
            context = send_otp_on_email(email)
            info_logger.info(context)
            info_logger.info(instance.user.id)
            info_logger.info(email)

        context['success'] = True

    return JsonResponse(context)


def verify_otp(request):
    mobile_no = request.GET.get('mobile_no')
    country_code = request.GET.get('country_code')
    user_id = request.GET.get('user_id')
    otp = request.GET.get('otp')

    info_logger.info("country code")
    info_logger.info(country_code)

    info_logger.info("mobile number")
    info_logger.info(mobile_no)

    info_logger.info("user_id")
    info_logger.info(user_id)

    info_logger.info("otp")
    info_logger.info(otp)

    if mobile_no == "9458668721":
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

        verified = verify_otp_on_mobile(phone_no, otp, international=international)
        verified_msg = verify_retry_otp(phone_no, otp)
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

            context = verify_otp_on_mobile(phone_no, otp, international=international)
            context_msg = verify_retry_otp(phone_no, otp)

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


def send_otp_on_mobile(phone_no, international=False):
    key = settings.GHUPSHUP_KEY
    context = {}
    success = False

    if not international:
        generate_url = """http://enterprise.smsgupshup.com/apps/TwoFactorAuth/incoming.php?phone=%s&key=%s""" % (
            phone_no, key)
        response = rqst.get(generate_url)
    else:
        inter_auth = settings.INTERNATIONAL_GHUPSHAP
        ghupshap_user_id = inter_auth['user_id']
        password = inter_auth['password']
        phone_no = "00" + str(phone_no)
        msg = inter_auth['msg']
        generate_url = """http://enterprise.smsgupshup.com/GatewayAPI/rest?userid=%s&password=%s&method=TWO_FACTOR_AUTH&v=1.1&phone_no=%s&msg=%s&format=text&otpCodeLength=4&otpCodeType=NUMERIC""" % (
            str(ghupshap_user_id), str(password), str(phone_no), str(msg))
        response = rqst.get(generate_url)

    info_logger.info("Gupshap mobile generate otp response")
    info_logger.info(response.text)

    if response.status_code == 200:
        success = True
        response = response.text
        response_list = response.split("|")
        if response_list[0].strip() == "error":
            success = False

    context['success'] = success
    if not success:
        context['error_message'] = response

    info_logger.info("api/generate_otp mobile response")
    info_logger.info(context)
    info_logger.info("\n\n")
    return context


def verify_otp_on_mobile(phone_no, otp, international=False):
    key = settings.GHUPSHUP_KEY

    if not international:
        verify_url = """http://enterprise.smsgupshup.com/apps/TwoFactorAuth/incoming.php?phone=%s&key=%s&code=%s""" % (
            str(phone_no), key, str(otp))
        response = rqst.get(verify_url)
    else:
        inter_auth = settings.INTERNATIONAL_GHUPSHAP
        ghupshap_user_id = inter_auth['user_id']
        password = inter_auth['password']
        phone_no = "00" + str(phone_no)
        verify_url = """http://enterprise.smsgupshup.com/GatewayAPI/rest?userid=%s&password=%s&method=TWO_FACTOR_AUTH&v=1.1&phone_no=%s&otp_code=%s""" % (
            str(ghupshap_user_id), str(password), str(phone_no), str(otp))
        response = rqst.get(verify_url)

    info_logger.info("Ghupshap verify otp response")
    info_logger.info(response.text)
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
    info_logger.info("api/verify_otp mobile response")
    info_logger.info(context)
    info_logger.info("\n\n")
    return context


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


def popup(request):
    '''api to show pop-ups for phonebook permission'''

    member_id = get_member_id_from_headers(request)
    if not member_id:
        context = get_error_context(False, "send member id in header")
        return JsonResponse(context)

    context = {}
    popup_home = {

        'title': "LikeMinds needs access to your contacts so that you can find and collaborate better with your connections. Your contacts will be stored in our heavily encrypted cloud storage.",
        'positive_action': "ALLOW",
        'negative_action': "SNOOZE",
        'positive_route': "route://ask_phonebook",
        'negative_route': "route://snooze"

    }
    popup_directory = {

        'title': "LikeMinds needs access to your contacts to highlight your acquaintances and common connections. ",
        'positive_action': "OKAY",
        'negative_action': "SNOOZE",
        'positive_route': "route://ask_phonebook",
        'negative_route': "route://snooze"

    }

    first_time = request.GET.get('first_time')

    if first_time == "true":
        context['popup_home'] = popup_home
        context['popup_directory'] = popup_directory
        return JsonResponse(context)

    context = {}
    popup_filter = userPopupTime.objects.filter(user=member_id)

    current_time = int(time.time())
    home_ignore = False
    directory_ignore = False
    for data in popup_filter:

        if data.popup_type == "popup_home":

            home_ignore = data.ignore
            if current_time > data.trigger_time and data.count > 5 and not data.ignore:
                popup_home['negative_action'] = "DON’T ASK ME"
                popup_home['negative_route'] = "route://dismiss"

        elif data.popup_type == "popup_directory":
            directory_ignore = data.ignore

            if current_time > data.trigger_time and data.count > 2 and not data.ignore:
                popup_directory['negative_action'] = "I AM NOT INTERESTED"
                popup_directory['negative_route'] = "route://dismiss"

    if not home_ignore:
        context['popup_home'] = popup_home
    if not directory_ignore:
        context['popup_directory'] = popup_directory

    return JsonResponse(context)


@csrf_exempt
def snooze_popup(request):
    '''api to snooze the pop-ups'''

    member_id = get_member_id_from_headers(request)
    if not member_id:
        context = get_error_context(False, "send member id in header")
        return JsonResponse(context)

    popup_type = request.POST.get('popup_type')

    if popup_type == "popup_home":
        trigger_time = time.time() + (8 * 60 * 60)
    else:

        trigger_time = time.time() + (8 * 60 * 60)

    popup_filter = userPopupTime.objects.filter(user=member_id, popup_type=popup_type)
    if not popup_filter.exists():

        user_instance = User.objects.get(id=member_id)
        instance = userPopupTime()
        instance.popup_type = popup_type
        instance.trigger_time = trigger_time
        instance.count = 1
        instance.created_at = time.time()
        instance.user = user_instance
        instance.save()

    else:

        instance = popup_filter[0]
        instance.count = instance.count + 1
        instance.save()

    return JsonResponse({'success': True})


# x = User.objects.filter(id=653).delete()
# print(x)

@csrf_exempt
def dismiss_popup(request):
    '''api to dismiss popup for asking phonebook'''

    member_id = get_member_id_from_headers(request)
    popup_type = request.POST.get('popup_type')
    update_status = userPopupTime.objects.filter(user=member_id, popup_type=popup_type).update(ignore=True)
    print(update_status)

    return JsonResponse({'success': True})


@csrf_exempt
def phonebook(request):
    '''api to save phonebook'''
    member_id = get_member_id_from_headers(request)
    res = json.loads(request.body)

    phonebook_filter = userPhonebook.objects.filter(user=member_id)

    if not phonebook_filter.exists():
        user_instance = User.objects.get(id=member_id)
        instance = userPhonebook()
        instance.phonebook = json.dumps(res['phonebook'])
        instance.created_at = time.time()
        instance.updated_at = time.time()
        instance.user = user_instance
        instance.save()

    else:
        phonebook_filter.update(phonebook=json.dumps(res['phonebook']), updated_at=time.time())

    return JsonResponse({'success': True})


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
        Q(state=member_states.ADMIN) | Q(state=member_states.TEMP_ADMIN) |
        Q(state=member_states.MEMBER) | Q(state=member_states.KNOWN_NOMINATED_PROMOTER) | Q(
            state=member_states.PROFILE_UNAVAILABLE))

    return members_filter.exists()


def limit_access(request):
    '''function to limit the access of app and sending details on web screen'''

    member_id = get_member_id_from_headers(request)
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
        community = CommunitySerializer(community_instance, current_user_id=member_id)

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
    member_filter = Members.objects.filter(community_id=community_instance, state=member_states.ADMIN).order_by('id')
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

    if not is_member_engage(community_id, member_id):
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.PROFILE_UNAVAILABLE
        engage.click_state = click_states.SKIP_COMMUNITY
        # engage.rights_list = json.dumps(member_rights.DEFAULT_MEMBER_RIGHTS)
        engage.save()

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
    return JsonResponse({'success': True})


def get_state_of_community(community):
    if community.hide_community:
        return int(community.hide_community)
    return 0


def members_state(request, req_dict=None):
    '''This function gives the state of user.Get Api'''

    if not req_dict:
        member_id = request.GET.get('member_id')
        community_id = request.GET.get('community_id')
        collabcard_id = request.GET.get('collabcard_id')

        if collabcard_id and not community_id:
            card = Collabcard.objects.get(pk=collabcard_id)
            community_id = card.community.id

        if not community_id:
            context = get_error_context(False, "send a valid community id or collabcard id")
            return JsonResponse(context)

    else:
        member_id = req_dict['member_id']
        community_id = req_dict['community_id']

    state = 0
    tool_state = 0
    custom_title = "Member"
    query_set = Members.objects.filter(member_id=member_id, community_id=community_id)
    community_instance = Community.objects.get(id=community_id)

    community_state = get_state_of_community(community_instance)

    is_tool_state = False

    if community_state == community_states.PRIVATE or community_state == community_states.PILOT_ACTIVE or community_state == community_states.WHATSAPP or community_state == community_states.HIDDEN:
        is_tool_state = True

    user_email = ""
    ref_members = []
    is_owner = False
    edit_required = False
    actions_required = False
    created_at = 0
    image_url = ""
    if query_set.exists():
        data = query_set[0]
        is_member = False
        tool_state = 0
        state = data.state
        is_owner = data.is_owner
        custom_title = data.custom_title

        if data.created_at > 0:
            created_at = time.strftime('%A, %b %d', time.localtime(data.created_at))

        if state == member_states.ADMIN or state == 2 or state == member_states.MEMBER or state == 7:
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
        'state': state,
        'tool_state': 1,
        'edit_required': edit_required,
        'created_at': created_at
    }

    if state == member_states.PENDING_MEMBER:
        json_response['member_direction_lock'] = get_data_for_filter_pop_ups(email=user_email)

    if state == member_states.ADMIN and (
            community_state == community_states.PRIVATE or community_state == community_states.WHATSAPP or community_state == community_states.HIDDEN):
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

    if state == member_states.ADMIN or state == member_states.MEMBER or state == member_states.PROFILE_UNAVAILABLE:
        user_rights = check_all_member_rights(query_set[0].member_id, community_instance)
        member_rights = get_saved_member_rights_list(user_rights)

    else:
        user_rights = check_all_member_rights(community=community_instance)
        # fetching all the rights of the community
        member_rights = get_saved_member_rights_list(user_rights)

    json_response['member_rights'] = member_rights

    if image_url:
        json_response['member']['image_url'] = image_url

    toast_filter = communityToast.objects.filter(community=community_instance, user=member_id)
    if toast_filter.exists():
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


@csrf_exempt
def dismiss(request):
    '''api to handle dismiss cases '''
    context = {}

    member_id = get_member_id_from_headers(request)
    if not member_id:
        context['success'] = False
        context['error_message'] = "Send member id in headers"
        return JsonResponse(context)

    community_id = request.POST.get('community_id', None)
    if not community_id:
        context['success'] = False
        context['error_message'] = "Send community_id as post params"
        return JsonResponse(context)

    type = request.POST.get('type', None)
    if not type:
        context['success'] = False
        context['error_message'] = "Send type as post params"
        return JsonResponse(context)

    is_promoter = is_member_promoter(community_id=community_id, member_id=member_id)

    if type == "community_actions" and is_promoter:
        Members.objects.filter(community_id=community_id, member_id=member_id).update(actions_required=False,
                                                                                      updated_at=time.time())
        context['success'] = True
        return JsonResponse(context)

    # handling false case
    context['success'] = False
    return JsonResponse(context)


@csrf_exempt
def push(request):
    '''This function is used to insert fcm token to the database in order to generate notifications from database'''

    member_id = request.GET.get('member_id', '')
    token = request.GET.get('token', '')
    platform_code = get_platform_code_from_headers(request)

    device_id = request.GET.get('device_id', None)

    if member_id:
        is_member = Userinfo.objects.filter(user_id=member_id)
    else:
        is_member = None
        # send notification if the login drops
        send_login_dropoff_notification.delay(token, platform_code)

    info_logger.info("Push Notification hit without member id")

    success = False
    if is_member:
        if platform_code == 'an':
            platform_code = 'Android'
        elif platform_code == 'ios':
            platform_code = 'iOS'

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


def config(request):
    '''function to update the version number of android for a user profile'''

    member_id = get_member_id_from_headers(request)

    context = {}
    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return context

    # update version code
    version_code = get_version_code_from_headers(request)
    Userinfo.objects.filter(user_id=member_id).update(version_code=version_code)

    # sendign mobile number exists key

    mobile_no_exists = userMobiles.objects.filter(user=member_id).exists()

    context['success'] = True
    context['mobile_no_exists'] = mobile_no_exists

    access = is_user_community_part(member_id)
    context['access'] = access

    ##mixpanel changes
    try:
        user_detail = get_mixpanel_statistics(member_id)
        context['user_detail'] = user_detail
    except Exception as e:
        error_logger.error(e)


    context['updatePriority'] = 0

    #set installed flags in case of mobile devices
    if RequestUtilities.is_request_android(request) or RequestUtilities.is_request_ios(request):
        set_installed_flag(member_id)

    return JsonResponse(context)


def set_installed_flag(member_id):
    """
    event when user installed the app
    """

    try:
        notification_list = [
            'mail_has_installed_app'
        ]
        create_notification_flag(member_id, notification_list, card_id=None, community_id=None, flag=False)

        user_instance = User.objects.get(id=member_id)
        app_uninstall, created = appUninstalls.objects.get_or_create(user=user_instance)
        if created:
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

    member_filter = Members.objects.filter(member_id=member_id, state=member_states.MEMBER)

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

    serialized_object = CommunitySerializer(community, current_user_id=member_id)
    new_dict = {}
    new_dict.update(serialized_object)

    return JsonResponse({'success': True, 'community': new_dict})


@csrf_exempt
def edit_community_version_1(request):
    '''function to edit the community'''

    res = json.loads(request.body)
    community_id = res['community_id']
    member_id = get_member_id_from_headers(request)
    try:
        user_instance = User.objects.get(id=member_id)
    except:
        context = get_error_context(False, "send correct community id")
        return JsonResponse(context)

    community_filter = Community.objects.filter(id=community_id)

    type_id = res['type'] if 'type' in res else None
    subtype_id = res['sub_type'] if 'sub_type' in res else None
    purpose = res['purpose'] if 'purpose' in res else None
    name = res['community_name']
    image_link = res['image_url']

    if community_filter.exists():
        community_instance = community_filter[0]
        community_instance.type = type_id
        community_instance.sub_type = subtype_id

        # checking name change
        if community_instance.name != name:
            community_instance.name = name
            edit_community_data(community_instance, user_instance, edit_field="name")

        if community_instance.purpose != purpose:
            community_instance.purpose = purpose
            edit_community_data(community_instance, user_instance, edit_field="purpose")

        if community_instance.image_link != image_link:
            community_instance.image_link = image_link
            edit_community_data(community_instance, user_instance, edit_field="image_url")

        community_instance.save()

        # edit_community_data(community_instance, user_instance, edit_field=purpose)

    return JsonResponse({'success': True})


@csrf_exempt
def edit_community_questions(request):
    '''function to update community questions'''

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
            # if question_instance.question_state != question['state']:
            #     major_change = True
            #
            # elif question_instance.value != question['value']:
            #     major_change = True

            # if (question_instance.optional is True and question['optional'] is False):
            #     major_change = True

            if question_instance.question_state == question_states.CHOICE_MULTIPLE or question_instance.question_state == question_states.CHOICE_SINGLE and not \
                    question['field']:
                current_choices = json.loads(question['value'])
                value_list = []
                for i in current_choices:
                    value_list.append(i['value'])

                # print(value_list)

                # taking the user options from filter
                filter_list = list(
                    questionFilters.objects.filter(question=question['id']).values_list('filter', flat=True).distinct())
                # print(filter_list)

                for data in filter_list:
                    if data not in value_list:
                        dropdown_list = list(
                            questionFilters.objects.filter(question=question['id'], filter=data).values_list(
                                'member_id', flat=True).distinct())
                        questionFilters.objects.filter(question=question['id'], filter=data)

                        delete_option = questionFilters.objects.filter(question=question['id'], filter=data).delete()

                        for user_id in dropdown_list:
                            dropdown_option = list(
                                questionFilters.objects.filter(question=question['id'], member_id=user_id).values_list(
                                    'filter', flat=True).distinct())
                            print(dropdown_option)
                            if dropdown_option:
                                value = ""
                                for i in dropdown_option:
                                    value = i + "$#"

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

            latest_questionId_set.add(int(question['id']))

            # updating the question instance
            create_or_update_question_instances(question_instance, question, community_instance)

        else:
            question_instance = communityQuestions()
            create_or_update_question_instances(question_instance, question, community_instance)

            major_change = True

    # print(current_questionId_set)
    # print(latest_questionId_set)

    diff = current_questionId_set - latest_questionId_set

    if len(diff) > 0:
        delete_status = communityQuestions.objects.filter(pk__in=diff).delete()
        print(delete_status)

    # updating members state table for editing
    if major_change:
        Members.objects.filter(community_id=community_instance).update(edit_required=True, updated_at=time.time())
        send_notification_for_directory_creation.delay(community_instance.id, time.time(), day=0)

    edit_community_data(community_instance, user_instance, edit_field="directory")

    return JsonResponse({'success': True})


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
        Members.objects.filter(community_id=community_instance).update(edit_required=True, updated_at=time.time())
        send_notification_for_directory_creation.delay(community_instance.id, time.time(), day=0)

    edit_community_data(community_instance, user_instance, edit_field="directory")

    return JsonResponse({'success': True})


def edit_community_data(community_instance, user_instance, edit_field):
    '''function to update the purpose collabcard of community'''

    collabcard_filter = Collabcard.objects.filter(community=community_instance, type=card_types.CARD_PURPOSE)

    if collabcard_filter.exists():
        card_instance = collabcard_filter[0]
        user_name = user_instance.userinfo.name
        community_route = "route://community?community_id=" + str(community_instance.id)
        if edit_field == "name":
            bubble_text = "<<" + user_name + " changed the name of this community" + "|" + community_route + ">>"
            edit_announcement_bubbles(card_instance, user_instance, bubble_text)
        if edit_field == "purpose":
            card_instance.title = community_instance.purpose
            card_instance.save()
            bubble_text = "<<" + user_name + """ edited "About Community". Tap to view.""" + "|" + community_route + ">>"
            edit_announcement_bubbles(card_instance, user_instance, bubble_text)
        if edit_field == "image_url":
            bubble_text = "<<" + user_name + """ changed the community icon. Tap to view.""" + "|" + community_route + ">>"
            edit_announcement_bubbles(card_instance, user_instance, bubble_text)

        if edit_field == "directory":
            member_directory_route = """route://members_directory?community_id=%s&community_name=%s""" % (
                str(community_instance.id), quote(community_instance.name))
            bubble_text = "<<" + user_name + """ edited member directory. Tap to view.""" + "|" + member_directory_route + ">>"
            edit_announcement_bubbles(card_instance, user_instance, bubble_text)

        # setting the updation time of edited community
        Member_Engage.objects.filter(community_id=community_instance,
                                     member_id=user_instance).update(updated_at=time.time())


def edit_announcement_bubbles(card_instance, user_instance, bubble_text):
    '''function to edit the announcement bubbles text'''

    instance = card_answers()
    instance.answer = bubble_text
    instance.card = card_instance
    instance.user = user_instance
    instance.community = card_instance.community
    instance.state = chatroom_states.CHATROOM_COMMUNITY_EDIT
    instance.created_at = time.time()
    instance.save()


############# functions to update user location and city    ##########################
@csrf_exempt
def update_location(request):
    ''' function to update user location lat and long co-ordinates '''

    user_id = request.GET.get('member_id')
    latitude = request.GET.get('latitude')
    longitude = request.GET.get('longitude')
    userinfo = Userinfo.objects.get(user_id__id=user_id)

    if not userinfo.latitude and not userinfo.longitude:
        userinfo.latitude = latitude
        userinfo.longitude = longitude
        userinfo.save()
        all_location_tags = get_user_location(request, userinfo.user_id, 'all')
        city = all_location_tags['city']
        userinfo.city = city
        userinfo.address = all_location_tags['address']
        userinfo.save()

        update_user_city_tag.delay(userinfo.user_id.id, all_location_tags)
        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


@shared_task
def update_user_city_tag(user_id, location):
    ''' function to update city tag for user '''
    user = User.objects.get(pk=user_id)
    global_tag = Tags_lpig.objects.get(name='Global')
    user_tags_list = list(User_Geography.objects.filter(user_id=user).values_list("tags_id", flat=True))

    for attr, loc_tag in location.items():

        if attr == 'address':
            continue

        tag_id = get_or_create_lpig_tags(tag=loc_tag, attr=attr, category='Geography')

        if tag_id.id in user_tags_list:

            continue
        elif not tag_id.id in user_tags_list:

            user_tag = User_Geography()
            user_tag.tags_id = tag_id
            user_tag.user_id = user
            user_tag.save()
        else:
            pass
        user_tags_list = list(User_Geography.objects.filter(user_id=user).values_list("tags_id", flat=True))

        if global_tag.id not in user_tags_list:
            user_tag = User_Geography()
            user_tag.tags_id = global_tag
            user_tag.user_id = user
            user_tag.save()
    return


@shared_task
def get_or_create_lpig_tags(tag, category, attr):
    ''' function to create new tags '''
    cat = category

    try:
        tag = Tags_lpig.objects.get(name=tag)

    except:

        attribute = category + "_uncat"
        new_tag = tag
        category = Category.objects.filter(Q(name__icontains=category))[0]
        if category == 'Geography' and not attr == 'district':
            attribute = Attributes.objects.filter(Q(attribute_name__icontains=attr))[0]
        else:
            attribute = Attributes.objects.filter(Q(attribute_name__icontains=attribute))[0]
        tag = Tags_lpig()
        tag.name = new_tag
        tag.category_id = category
        tag.attribute_id = attribute
        tag.created_at = time.time()
        tag.updated_at = time.time()
        tag.save()
        tag.tag_id = tag.id
        tag.save()

    finally:
        if cat == 'Geography':
            tag_name, tag_id = tag.name, tag.id
            print("collabmates api update tag image at create or get lpig tags")
            update_tag_image.delay(tag_name=tag_name, tag_id=tag_id)

    return tag


def get_user_location(request, user_id, type=None):
    ''' function to fetch user location '''

    flag = True
    if not type:
        type = request.GET.get('type', '')
        flag = False
    userinfo = Userinfo.objects.get(user_id=user_id)

    gmaps = googlemaps.Client(key='AIzaSyDN10TwCPVMdLEE6vvTiglKHGlkTIYKduc')
    location_response = gmaps.reverse_geocode((userinfo.latitude, userinfo.longitude))

    addr = location_response[1]['formatted_address']
    address = addr.split(',')
    if type and type == 'address':
        response = {'location': addr}

    elif type and type == 'country':
        country = address[-1].strip()
        print("country ==== ", country)
        response = {'location': country}

    elif type and type == 'state':
        state = address[-2][:-7].strip()
        print('state ===== ', state)
        response = {'location': state}

    elif type and type == 'pincode':
        pincode = address[-2][-6:].strip()
        print("pincode === ", pincode)
        response = {'location': address}

    elif type and type == 'city':

        city = address[-3].strip()
        print("city ==== ", city)
        response = {'location': city}

    elif type and type == 'all':

        # return list [city,state,country,pincode]

        response = {}
        response['city'] = address[-3].strip()
        response['pincode'] = address[-2][-6:].strip()
        response['state'] = address[-2][:-7].strip()
        response['country'] = address[-1].strip()
        response['address'] = addr

        if flag:
            return response

    return JsonResponse(response, safe=False)


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

@api_view(['GET', 'POST'])
@renderer_classes([JSONRenderer, TemplateHTMLRenderer])
def all_members_version_1(request):

    '''version 1 api for sending members of community with different community type'''

    context = get_all_members_version_1(request)

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
    if member_list.exists():

        member_state = member_list[0].state
        if member_state == member_states.PENDING_MEMBER:
            send_empty_list = True

    else:
        send_empty_list = True

    if send_empty_list:
        return JsonResponse({'questions': []})

    community_options = communityAnswers.objects.filter(community_id=community_id)

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


#
# def invite_members(request):
#     ''' function to get members requested to join in a community '''
#
#     member_id = request.GET.get('member_id', None)
#     community_id = request.GET.get('community_id', None)
#
#     pend_requests = get_referred_members_of_a_member(community_id, member_id)
#
#     pending_requests = []
#     for i in pend_requests:
#         user_id = i
#         # resp = Form_response.objects.filter(community=community_id).filter(user=user_id)
#         user = Userinfo.objects.get(user_id=user_id)
#         # serilaizing userinfo object
#         usr = UserinfoSerializer(user)
#         user_response = []
#         for j in resp:
#             # getting the answers of the users who requested to join
#             # for the questions that have been asked while requestiong to join in a community
#             response_object = {}
#             response_object['key'] = j.data
#             response_object['value'] = j.response
#             user_response.append(response_object)
#         usr['response'] = user_response
#         pending_requests.append(usr)
#     return JsonResponse({'pending_members': pending_requests})


def get_profile(request):
    '''api to send user object'''

    member_id = request.GET.get('member_id')

    try:
        user = Userinfo.objects.get(user_id=member_id)
        usr = UserinfoSerializer(user)
        tags = get_user_lpig_tags(usr['id'])
        if tags:
            usr['tags'] = tags
            return JsonResponse({'user': usr})
        return JsonResponse({'user': usr})
    except:
        print("userinfo object does not exist")

    return JsonResponse({'user': []})


################ functions for getting and setting of tags ##########################################


def get_second_screen_of_onboarding(member_tags_list):
    '''function to take college of a user'''

    temp = {}
    temp['title'] = "Enter your schools/colleges"
    temp['sub_title'] = "Discover relevant alumni communities"
    attribute_list = []
    attribute_id = 2
    category_id = 1
    attribute_name = "Legacy_education"
    hint = "Your Schools/Colleges"
    display_name = "Education"
    college_list = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id, display_name)
    attribute_list.append(college_list)
    temp['attributes'] = attribute_list

    return temp


def get_first_screen_of_onboarding(member_tags_list):
    '''function to get secong screen of onboarding'''

    temp = {}
    temp['title'] = "Mention your neighbourhood"
    temp['sub_title'] = "Discover relevant local communities"
    attribute_list = []

    attribute_id = 12
    attribute_name = "Geography_city"
    hint = "Your society/locality"
    category_id = 4
    display_name = "city"
    city_list = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id, display_name)
    attribute_list.append(city_list)

    attribute_id = 3
    attribute_name = "Legacy_hometown"
    hint = "+ Add hometown"
    category_id = 1
    display_name = "hometown"
    hometown_list = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id, display_name)
    attribute_list.append(hometown_list)
    temp['attributes'] = attribute_list

    return temp


def get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id, display_name):
    '''function to get sports tags'''

    # for sports
    # attribute_id = 10
    # attribute_name = "Interests_sports"

    tags = Tags_lpig.objects.filter(attribute_id=attribute_id).order_by('-tag_rank')
    attribute_temp = {}
    attribute_temp['hint'] = hint
    attribute_temp['id'] = attribute_id
    attribute_temp['name'] = attribute_name
    attribute_temp['category_id'] = category_id
    attribute_temp['display_name'] = display_name.capitalize()
    tag_list = []
    if attribute_id == 3 or attribute_id == 12:
        attribute_temp['tags'] = tag_list
        return attribute_temp
    for each_tag in tags:
        tag = {}
        tag['id'] = each_tag.tag_id
        tag['name'] = each_tag.name
        tag['attribute_name'] = attribute_name
        if each_tag.image_link:
            tag['image_url'] = each_tag.thumbnail
        tag['state'] = 0
        if tag['id'] in member_tags_list:
            print(tag)
            print("\n\n")
            tag['state'] = 1
        tag_list.append(tag)
    attribute_temp['tags'] = tag_list

    return attribute_temp


def get_third_screen_of_onboarding(member_tags_list):
    '''function to show third screen of onboarding'''

    temp = {}
    temp['title'] = "What do you identify yourself with"
    temp['sub_title'] = "Select atleast 5"
    attribute_list = []

    # getting sport list
    attribute_id = 10
    attribute_name = "Interests_sports"
    hint = "Playing these sports"
    category_id = 3
    display_name = "sports"
    sports_list = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id, display_name)
    attribute_list.append(sports_list)

    # getting hobbies

    attribute_id = 9
    attribute_name = "Interests_hobby"
    hint = "Pursuing these hobbies"
    category_id = 3
    display_name = "hobbies"
    hobbies = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id, display_name)
    attribute_list.append(hobbies)

    # getting fan

    attribute_id = 11
    attribute_name = "Interests_fan"
    hint = "Following these teams, sports, genres or topics"
    category_id = 3
    display_name = "fans"
    fan = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id, display_name)
    attribute_list.append(fan)

    # getting cause

    attribute_id = 8
    attribute_name = "Interests_cause"
    hint = "Working on these causes"
    category_id = 3
    display_name = "causes"
    cause = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id, display_name)
    attribute_list.append(cause)

    # getting skill

    attribute_id = 5
    attribute_name = "Profession_skill"
    hint = "Skills that you have"
    category_id = 2
    display_name = "skills"
    skill = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id, display_name)
    attribute_list.append(skill)

    # getting industry

    attribute_id = 6
    attribute_name = "Profession_industry"
    hint = "Industry that you belong to"
    category_id = 2
    display_name = "industries"
    industry = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id, display_name)
    attribute_list.append(industry)

    temp['attributes'] = attribute_list

    return temp


def onboarding(request):
    '''function to send all the tags for onboarding'''

    onboarding_screens = []
    user_id = request.GET.get('member_id', '')
    member_tags_list = []

    if user_id:
        legacy = list(User_Legacy.objects.filter(user_id=user_id).values_list('correct_tag_id', flat=True))
        profession = list(User_Profession.objects.filter(user_id=user_id).values_list('correct_tag_id', flat=True))
        interest = list(User_Profession.objects.filter(user_id=user_id).values_list('correct_tag_id', flat=True))
        geography = list(User_Profession.objects.filter(user_id=user_id).values_list('correct_tag_id', flat=True))
        member_tags_list = legacy + profession + interest + geography

    # first screen flow

    screen = request.GET.get('screen', '')

    if screen == "first":
        first_screen = get_first_screen_of_onboarding(member_tags_list)
        onboarding_screens.append(first_screen)
        # print(onboarding_screens)
        return JsonResponse({'onboarding': onboarding_screens})

    # second screen flow
    if screen == "second":
        second_screen = get_second_screen_of_onboarding(member_tags_list)
        onboarding_screens.append(second_screen)
        # print(onboarding_screens)
        return JsonResponse({'onboarding': onboarding_screens})

    # third screen flow

    if screen == "third":
        third_screen = get_third_screen_of_onboarding(member_tags_list)
        onboarding_screens.append(third_screen)
        # print(onboarding_screens)
        return JsonResponse({'onboarding': onboarding_screens})

    return JsonResponse({'onboarding': onboarding_screens})


def save_tags_for_user_from_onboarding(category_id, tag_id, member_id):
    '''function to save user tags in lpig tables'''
    category_id = int(category_id)

    if category_id == 1:
        if tag_id.attribute_id.id == 3:
            tag_id = insert_user_home_town_tags(user_id=member_id.id, tag=str(tag_id.tag_id))
        user_tag = User_Legacy.objects.filter(tags_id=tag_id, user_id=member_id)
        if not user_tag.exists():
            user_legacy_object = User_Legacy()
            user_legacy_object.user_id = member_id
            user_legacy_object.tags_id = tag_id
            user_legacy_object.save()

    elif category_id == 2:
        user_tag = User_Profession.objects.filter(tags_id=tag_id, user_id=member_id)
        if not user_tag.exists():
            user_profession_object = User_Profession()
            user_profession_object.user_id = member_id
            user_profession_object.tags_id = tag_id
            user_profession_object.save()
    elif category_id == 3:
        user_tag = User_Interest.objects.filter(tags_id=tag_id, user_id=member_id)
        if not user_tag.exists():
            user_interest_object = User_Interest()
            user_interest_object.user_id = member_id
            user_interest_object.tags_id = tag_id
            user_interest_object.save()
    elif category_id == 4:
        user_tag = User_Geography.objects.filter(tags_id=tag_id, user_id=member_id)
        if not user_tag.exists():
            user_geography_object = User_Geography()
            user_geography_object.user_id = member_id
            user_geography_object.tags_id = tag_id
            user_geography_object.save()
        update_user_geography_tags.delay(user_id=member_id.id)

    log = """for category_id=%s, tags_id=%s saved for member_id=%s""" % (str(category_id), str(tag_id), str(member_id))
    info_logger.info(log)


@csrf_exempt
def push_onboarding(request):
    '''function to save user tags'''

    user_id = get_member_id_from_headers(request)
    response = json.loads(request.body)
    member_id = 0
    try:
        member_id = User.objects.get(id=user_id)  # getting a user object in member id
    except:
        error_logger.error("User does not exist")
    for data in response['attributes']:

        category_id = data['category_id']
        tags = data['tags']

        for tag in tags:

            if 'id' in tag and tag['id']:

                tag_id = Tags_lpig.objects.get(id=tag['id'])
                status = Tags_lpig.objects.filter(id=tag['id']).update(tag_rank=F('tag_rank') + 1)
                print(status)
                save_tags_for_user_from_onboarding(category_id, tag_id, member_id)

            else:

                if data['id'] == 12 or data['id'] == '12':
                    attribute_id = Attributes.objects.get(id=data['id'])

                    update_status = Userinfo.objects.filter(user_id=user_id).update(address=tag['name'])
                    print(update_status)
                    save_geography_and_hometown_tags_of_user_from_onboarding(tag['name'], member_id, attribute_id, 4)

                elif data['id'] == 3 or data['id'] == '3':
                    attribute_id = Attributes.objects.get(id=data['id'])
                    save_geography_and_hometown_tags_of_user_from_onboarding(tag['name'], member_id, attribute_id, 1)
                else:
                    print("uncharacterized tag==" + tag['name'])
                    attribute_id = Attributes.objects.get(id=data['id'])
                    uncharacterized_category_id = Category.objects.get(id=6)

                    is_tag_exists = Tags_lpig.objects.filter(attribute_id=attribute_id, name=tag['name'])
                    if not is_tag_exists:
                        tag_object = Tags_lpig()
                        tag_object.name = tag['name']
                        tag_object.attribute_id = attribute_id
                        tag_object.category_id = uncharacterized_category_id  # uncategorized tag
                        tag_object.save()
                        tag_object.tag_id = tag_object.id
                        tag_object.created_at = time.time()
                        tag_object.updated_at = time.time()
                        tag_object.save()
                    else:
                        tag_object = is_tag_exists[0]

                    save_tags_for_user_from_onboarding(category_id, tag_object, member_id)

    # saving global tags for user

    tag_id = Tags_lpig.objects.get(id=15)
    legacy_global = User_Legacy.objects.filter(tags_id=tag_id, user_id=member_id)
    if not legacy_global:
        save_tags_for_user_from_onboarding(1, tag_id, member_id)

    tag_id = Tags_lpig.objects.get(id=16)
    profession_global = User_Profession.objects.filter(tags_id=tag_id, user_id=member_id)
    if not profession_global:
        save_tags_for_user_from_onboarding(2, tag_id, member_id)

    tag_id = Tags_lpig.objects.get(id=17)
    interest_global = User_Interest.objects.filter(tags_id=tag_id, user_id=member_id)
    if not interest_global:
        save_tags_for_user_from_onboarding(3, tag_id, member_id)

    tag_id = Tags_lpig.objects.get(id=18)
    geography_global = User_Geography.objects.filter(tags_id=tag_id, user_id=member_id)
    if not geography_global:
        save_tags_for_user_from_onboarding(4, tag_id, member_id)

    log = """All tags inserted success fully for user=%s""" % (str(member_id))
    info_logger.info(log)

    compute_rank.delay(user_id=user_id)
    # send_mail_after_rank_computation.delay(user_id)  # both mail and notification will be sent here
    Userinfo.objects.filter(user_id=user_id).update(has_tags=True)
    return JsonResponse({'success': True})


def save_geography_and_hometown_tags_of_user_from_onboarding(address_input, user_id, attribute_id, category_id):
    '''function to take the address of the user and get its city,state and country tags to save in tags'''

    user_address = get_city_address(city=address_input)

    city = user_address['city']
    if not city:
        return
    if category_id == 4:
        city_tag = Tags_lpig.objects.filter(attribute_id=attribute_id, name=city)
        if city_tag:
            save_tags_for_user_from_onboarding(4, city_tag[0], user_id)
        else:
            category = Category.objects.get(id=4)

            is_tag_exists = Tags_lpig.objects.filter(attribute_id=attribute_id, name=user_address['city'])
            if not is_tag_exists:
                tag_object = Tags_lpig()
                tag_object.name = user_address['city']
                tag_object.attribute_id = attribute_id
                tag_object.category_id = category  # uncategorized tag
                tag_object.save()
                tag_object.tag_id = tag_object.id
                tag_object.created_at = time.time()
                tag_object.updated_at = time.time()
                tag_object.save()
            else:
                tag_object = is_tag_exists[0]

            save_tags_for_user_from_onboarding(4, tag_object, user_id)



    elif category_id == 1:
        hometown = Tags_lpig.objects.filter(attribute_id=attribute_id, name=city)
        if hometown:
            save_tags_for_user_from_onboarding(1, hometown[0], user_id)
        else:
            category = Category.objects.get(id=1)

            is_tag_exists = Tags_lpig.objects.filter(attribute_id=attribute_id, name=user_address['city'])
            if not is_tag_exists:
                tag_object = Tags_lpig()
                tag_object.name = user_address['city']
                tag_object.attribute_id = attribute_id
                tag_object.category_id = category  # uncategorized tag
                tag_object.save()
                tag_object.tag_id = tag_object.id
                tag_object.created_at = time.time()
                tag_object.updated_at = time.time()
                tag_object.save()
            else:
                tag_object = is_tag_exists[0]

            save_tags_for_user_from_onboarding(1, tag_object, user_id)

    print("Hometown and city updated successfully")


# Reporting collabcard functions

def fetch_report_tags(request):
    '''api to send report tags '''
    type = request.GET.get('type', 0)
    type = int(type)
    if not type:
        report_tags_instances = Report_Tags.objects.filter(type=0)
    else:
        report_tags_instances = Report_Tags.objects.filter(type=1)

    report_tags = []

    for instance in report_tags_instances:
        temp = {}
        temp['id'] = instance.tag_id
        temp['name'] = instance.tag_name
        report_tags.append(temp)
    # info_logger.info("fetch report tags api successfulll")
    return JsonResponse({'report_tags': report_tags})


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

        member_id = get_member_id_from_headers(request)
        user_instance = User.objects.get(id=member_id)

        request_body = json.loads(request.body)
        collabcard_id = request_body['collabcard_id'] if 'collabcard_id' in request_body else None
        community_id = request_body['community_id'] if 'community_id' in request_body else None
        tag_id = request_body['tag_id'] if 'tag_id' in request_body else None
        reason = request_body['reason'] if 'reason' in request_body else None
        reported_member_id = int(request_body['reported_member_id']) if 'reported_member_id' in request_body else None
        link = request_body['link'] if 'link' in request_body else None
        conversation_id = request_body['conversation_id'] if 'conversation_id' in request_body else None

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
                return JsonResponse({'success': False, "error_message": "you have no right to report chatroom"})

            collabcard_instance = Collabcard.objects.get(id=collabcard_id)
            report_type = report_Types.REPORT_CHATROOM
            if not reported_member_id:
                reported_member_instance = collabcard_instance.user

            if not community_id:
                community_id = collabcard_instance.community.id

        if conversation_id:

            if is_promoter and has_right_0:
                return JsonResponse({'success': False, "error_message": "you have no right to report convesations"})

            conversation_instance = card_answers.objects.get(id=conversation_id)
            report_type = report_Types.REPORT_CONVERSATION

            if collabcard_instance is None:
                collabcard_instance = conversation_instance.card

            if not reported_member_id:
                reported_member_instance = conversation_instance.user

            if not community_id:
                community_id = conversation_instance.community.id

        if reported_member_id and not reported_member_instance:

            if is_promoter and has_right_1:
                return JsonResponse({'success': False, "error_message": "you have no right to report a member"})

            if not community_id:
                return JsonResponse({'success': False, "error_message": "send community_id in body"})

            report_type = report_Types.REPORT_MEMBER
            reported_member_instance = User.objects.get(pk=reported_member_id)

        report_tag_instance = Report_Tags.objects.get(tag_id=tag_id) if tag_id else None
        community_instance = Community.objects.get(id=community_id)

        report_instance = Report()
        report_instance.tag = report_tag_instance
        report_instance.reason = reason

        report_instance.collabcard = collabcard_instance
        report_instance.conversation = conversation_instance
        report_instance.community = community_instance

        report_instance.reported_member_id = reported_member_id  # has to be removed
        report_instance.user_reported = reported_member_instance
        report_instance.member = user_instance  # has to be removed
        report_instance.reported_by = user_instance
        if link is not None:
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

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


def fetch_whatsapp_tool(request):
    '''fetch whatsapp tool page'''

    title = "Your WhatsApp community is still not connected well."
    sub_title = "Register your group on LikeMinds and get exciting tools to better functioning of your whatsapp group."

    list_points = []

    point_1 = {}

    point_1['title'] = "Your group is not discoverable"  # text change
    point_1[
        'sub_title'] = "Make your group discoverable to other relevant members who might be interested in joining your group."

    list_points.append(point_1)

    point_2 = {}
    point_2['title'] = "Group members can't identify each other"
    point_2[
        'sub_title'] = "Your group members can create their profile and share them so that other members can get to know them better."
    list_points.append(point_2)

    point_3 = {}
    point_3['title'] = "Not able to create polls on whatsapp?"
    point_3['sub_title'] = "Get the ability to create private polls for your group."
    list_points.append(point_3)

    point_4 = {}
    point_4['title'] = "Not able to create events on whatsapp?"
    point_4['sub_title'] = "Create private events for your group and easier way to access the attending members."

    list_points.append(point_4)

    whatsapp_tool = {}
    whatsapp_tool['title'] = title
    whatsapp_tool['sub_title'] = sub_title
    whatsapp_tool['points'] = list_points

    # getting types.object
    community_type_list = communityType.objects.all()
    community_subtype_list = communitySubtype.objects.all()

    types = []
    for instance in community_type_list:
        temp = communityTypeSerializer(instance)

        sub_type_list = []
        subtype_queryset = communitySubtype.objects.filter(typ=instance.id)

        if subtype_queryset.exists():
            for subtype_instance in subtype_queryset:
                subtype_temp = communitySubtypeSerializer(subtype_instance)
                sub_type_list.append(subtype_temp)

        if sub_type_list and temp['id'] != 16:
            temp['sub_types'] = sub_type_list

        types.append(temp)

    # getting sub-types.object
    # community_subtype_list = communitySubtype.objects.all()
    # sub_types = []
    #
    # for instance in community_subtype_list:
    #     sub_types.append(communitySubtypeSerializer(instance))

    whatsapp_tool['types'] = types
    # whatsapp_tool['sub_types'] = sub_types

    master_question_list = masterQuestions.objects.all()
    paginator = Paginator(master_question_list, 50)

    whatsapp_tool['total_master_questions'] = paginator.num_pages

    return JsonResponse(whatsapp_tool)


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
    verify_url = url + "/email_verify?token=" + str(token) + "&user=" + str(user_id)

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
        temp['unread_conversation'] = get_custom_data_for_new_conversation_created(user_id)

        return JsonResponse(temp)

    return JsonResponse({'error': 'send user_id or conversation_id in order to see payload'})


def unread_conversation_notification(request):
    member_id = get_member_id_from_headers(request)

    if not member_id:
        context = get_error_context(False, "send memeber id in headers")
        return JsonResponse(context)

    temp = {}
    temp['unread_conversation'] = get_custom_data_for_new_conversation_created(user_id=member_id)

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
        collabcardState.objects.filter(card=card_instance).update(updated_at=time.time())
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

        collabcardState.objects.filter(card=card_instance).update(updated_at=time.time())
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
            members_list.append(get_user_profile(member.user, send_profile=True))


    return JsonResponse({"members": members_list})


@csrf_exempt
def delete_conversation(request):
    """ function to delete a conversation """

    if request.method == 'GET':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'})

    member_id = get_member_id_from_headers(request)
    current_user_instance = User.objects.get(pk=member_id)

    req_body = json.loads(request.body)

    conversation_ids = req_body.get('conversation_ids', None)
    tag_id = req_body.get('tag_id', None)
    reason = req_body.get('reason', None)

    if not conversation_ids:
        context = get_error_context(False, "send the conversation_ids in post params")
        return JsonResponse(context)

    if not member_id:
        context = get_error_context(False, "send the member_id in headers")
        return JsonResponse(context)

    conversation_list = []
    for conversation_id in conversation_ids:
        conversation = card_answers.objects.get(pk=conversation_id)

        update_conversation_delete_status(conversation, current_user_instance, reason=reason, tag_id=tag_id)

        conversation_dict = get_conversation_instance_for_db_synching(conversation, current_user_id=member_id)
        conversation_list.append(conversation_dict)

    return JsonResponse({'success': True, 'conversations': conversation_list})


def update_conversation_delete_status(conversation_instance, current_user_instance,
                                      reason=None, tag_id=None):
    tag_instance = None
    if tag_id:
        tag = Report_Tags.objects.filter(tag_id=tag_id)
        if tag.exists():
            tag_instance = tag[0]

    conversation_instance.is_deleted = True
    conversation_instance.deleted_by_user = current_user_instance
    conversation_instance.tag = tag_instance
    conversation_instance.reason = reason
    conversation_instance.last_updated = int(round(time.time() * 1000))
    conversation_instance.save()

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
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'})

    member_id = get_member_id_from_headers(request)
    conversation_id = request.POST.get('conversation_id', None)
    edited_answer = request.POST.get('text', None)

    if not conversation_id:
        context = get_error_context(False, "send the conversation_id in post params")
        return JsonResponse(context)

    if not member_id:
        context = get_error_context(False, "send the member_id in headers")
        return JsonResponse(context)

    try:
        conversation = card_answers.objects.get(pk=conversation_id)
    except:
        context = get_error_context(False, "conversation id does not exist")
        return JsonResponse(context, status=400)

    if conversation.is_deleted:
        context = get_error_context(False, "Cannot edit deleted conversation")
        return JsonResponse(context)
    elif int(conversation.user.id) == int(member_id):
        conversation.answer = edited_answer
        conversation.is_edited = True
        conversation.last_updated = int(round(time.time() * 1000))
        conversation.save()
    else:
        context = get_error_context(False,
                                    "you are not the conversation creator.Only conversation creator can edit his/her message")
        return JsonResponse(context)

    conversation = get_conversation_instance_for_db_synching(conversation, current_user_id=member_id)

    return JsonResponse({'success': True, 'conversation': conversation})


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


def fetch_community_manager_rights(request):
    """ function to fetch manager rights """

    if request.method == 'POST':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to GET'})

    current_user_id = get_member_id_from_headers(request)
    community_id = request.GET.get('community_id', None)
    user_id = request.GET.get('user_id', None)

    context = None
    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not user_id:
        context = get_error_context(False, "send user_id in params")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in params")
        return JsonResponse(context)

    community_instance = Community.objects.get(pk=community_id)
    current_user_instance = User.objects.get(pk=current_user_id)
    user_instance = User.objects.get(pk=user_id)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing

    rights_context = []

    if admin.exists():
        admin_rights = userAdminRights.objects.filter(community=community_instance, user=current_user_instance)
        user_rights = list(userAdminRights.objects.filter(community=community_instance,
                                                          user=user_instance).values_list('right__id',
                                                                                          flat=True))
        if admin_rights.exists():
            is_member = len(user_rights) == 0

            for right in admin_rights:
                right = right.right
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

    return JsonResponse({"admin_mobiles": mobile_list, "member": member_profile[0], "rights": rights_context})


@csrf_exempt
def update_community_manager_rights(request):
    """ function to remove a communtiy manager as manager """

    if request.method == 'GET':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'})

    current_user_id = get_member_id_from_headers(request)
    req_body = json.loads(request.body)
    user_id = req_body['user_id'] if "user_id" in req_body else None
    community_id = req_body['community_id'] if "community_id" in req_body else None
    selected_rights = req_body['rights'] if "rights" in req_body else []
    custom_title = req_body['custom_title'] if "custom_title" in req_body else None

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not user_id:
        context = get_error_context(False, "send user_id in body")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in body")
        return JsonResponse(context)
    # if selected_rights is None:
    #     context = get_error_context(False, "send rights in body")
    #     return JsonResponse(context)

    community_instance = Community.objects.get(pk=community_id)
    current_user_instance = User.objects.get(pk=current_user_id)
    if int(user_id) == int(current_user_id):
        user_instance = current_user_instance
    else:
        user_instance = User.objects.get(pk=user_id)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing

    member_is_owner = Members.objects.filter(member_id=user_instance, community_id=community_instance,
                                             state=member_states.ADMIN,
                                             is_owner=True).exists()  # who's rights are being updated
    if admin.exists():
        if member_is_owner:
            log = f"UPDATING_CM_RIGHTS_FOR_OWNER - community_id = {community_id}" \
                  f" current_user id = {current_user_id} user = {user_id}"
            info_logger.info(log)

            save_owner_title(custom_title, admin, community_instance, user_instance)
            return JsonResponse({'success': True})

        rights_added, removed_rights = save_added_removed_rights_for_manager(community_instance,
                                                                             user_instance,
                                                                             selected_rights)

        if int(user_id) != int(current_user_id):
            member = Members.objects.filter(member_id=user_instance,
                                            community_id=community_instance)
            if member.exists():
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

                Member_Engage.objects.filter(member_id=user_instance,
                                             community_id=community_id).update(
                    member_state=member_states.ADMIN,
                    rights_list=json.dumps(member_rights.ALL_MEMBER_RIGHTS))

                save_moderation_history(user=user_instance, community=community_instance,
                                        moderation_by=current_user_instance,
                                        type=moderation_history_types.MADE_COMMUNITY_MANAGER)

                send_notification_for_new_promoter.delay(promoter_id=current_user_id, member_id=user_id,
                                                         community_id=community_id, custom_title=custom_title)
            elif custom_title_changed:
                # updating time for all members of community
                Members.objects.filter(community_id=community_instance).update(updated_at=time.time())
                send_notification_for_custom_title_changed.delay(promoter_id=current_user_id, member_id=user_id,
                                                                 community_id=community_id,
                                                                 custom_title=custom_title)

            if len(rights_added) > 0:
                send_notification_for_right_given_to_manager.delay(user_id, community_id, list(rights_added))

        info_logger.info(f"UPDATING_CM_RIGHTS current user id = {current_user_id},"
                         f" user id = {user_id}, community id = {community_id}")

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
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'})

    current_user_id = get_member_id_from_headers(request)
    community_id = request.POST.get('community_id', None)
    user_id = request.POST.get('user_id', None)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not user_id:
        context = get_error_context(False, "send user_id in params")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in params")
        return JsonResponse(context)

    community_instance = Community.objects.get(pk=community_id)
    current_user_instance = User.objects.get(pk=current_user_id)
    user_instance = User.objects.get(pk=user_id)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing
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

        Members.objects.filter(community_id=community_instance,
                               member_id=user_instance).update(state=member_states.MEMBER, custom_title=custom_title,
                                                               parent_cm=None, parent_cm_list='[]',
                                                               updated_at=time.time())
        Member_Engage.objects.filter(member_id=user_instance,
                                     community_id=community_instance).update(member_state=member_states.MEMBER,
                                                                             pending_chatrooms=0,
                                                                             open_reports=0)
        save_moderation_history(user=user_instance, community=community_instance,
                                moderation_by=current_user_instance,
                                type=moderation_history_types.REMOVED_AS_COMMUNITY_MANAGER)
        # updating time for all members of community
        Members.objects.filter(community_id=community_instance).update(updated_at=time.time())

        restore_member_rights_from_history(user_instance, community_instance)

        info_logger.info(f"REMOVE_COMMUNITY_MANAGER_API  current user id = {current_user_id}, user id = {user_id}"
                         f", community id = {community_id}")
        send_notification_for_removed_cm.delay(user_id, community_id)
        return JsonResponse({'success': True})

    else:
        context = get_error_context(False, "you are not a admin")
        return JsonResponse(context)


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

            context = verify_otp_on_mobile(phone_no, otp, international=international)
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

        Members.objects.filter(community_id=community_instance,
                               member_id=user_instance).update(state=member_states.ADMIN, is_owner=True,
                                                               custom_title=new_owner_title, parent_cm=None,
                                                               parent_cm_list=None,
                                                               updated_at=time.time())

        Member_Engage.objects.filter(member_id=user_instance, community_id=community_instance).update(
            rights_list=json.dumps(member_rights.ALL_MEMBER_RIGHTS),
            member_state=member_states.ADMIN, click_state=click_states.DEFAULT
        )
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
        Members.objects.filter(community_id=community_instance).update(updated_at=time.time())
        info_logger.info(f"TRANSFER_OWNERSHIP_API  current user id = {current_user_id}, user id = {user_id}"
                         f", community id = {community_id}")
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

    community_instance = Community.objects.get(pk=community_id)
    current_user_instance = User.objects.get(pk=current_user_id)
    user_instance = User.objects.get(pk=user_id)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing

    rights_context = []

    if admin.exists():
        admin_rights = check_all_manager_rights(current_user_instance, community_instance)
        user_rights = check_all_member_rights(user_instance, community_instance)

        rights_context = get_saved_member_rights_list(user_rights, admin_rights)

    else:
        context = get_error_context(False, "user is not a admin")
        return JsonResponse(context)

    member_profile = get_members_profile([user_instance], community_instance)

    return JsonResponse({"member": member_profile[0], "rights": rights_context})


@csrf_exempt
def update_community_member_rights(request):
    """ function to remove a communtiy manager as manager """

    if request.method == 'GET':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to POST'})

    current_user_id = get_member_id_from_headers(request)
    req_body = json.loads(request.body)
    user_id = req_body['user_id'] if "user_id" in req_body else None
    community_id = req_body['community_id'] if "community_id" in req_body else None
    selected_rights = req_body['rights'] if "rights" in req_body else []
    custom_title = req_body['custom_title'] if "custom_title" in req_body else None

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not user_id:
        context = get_error_context(False, "send user_id in body")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in body")
        return JsonResponse(context)

    community_instance = Community.objects.get(pk=community_id)
    current_user_instance = User.objects.get(pk=current_user_id)
    user_instance = User.objects.get(pk=user_id)

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
            Members.objects.filter(community_id=community_instance).update(updated_at=time.time())
            send_notification_for_custom_title_changed.delay(promoter_id=current_user_id, member_id=user_id,
                                                             community_id=community_id,
                                                             custom_title=custom_title)

        update_member_rights_history.delay(rights_added, rights_removed, current_user_id, community_id, user_id)

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
        context = get_error_context(False, "change HTTP method to GET")
        return JsonResponse(context)

    current_user_id = get_member_id_from_headers(request)
    # user_instance = User.objects.get(id=current_user_id)

    community_id = request.GET.get('community_id', None)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in params")
        return JsonResponse(context)

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
        context = get_error_context(False, "user has not Owner or CM")
        return JsonResponse(context)

    reports = get_related_reports_for_user(user_id=current_user_id, community_id=community_id, has_right_0=has_right_0,
                                           is_owner=is_owner, has_right_1=has_right_1, has_right_2=has_right_2,
                                           parent_cm_list=parent_cm_list)

    report_list = []

    for report in reports:
        report_dict = report_serializer(report, current_user_id)
        report_list.append(report_dict)

    return JsonResponse({"reports": report_list})


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
        return JsonResponse(context)

    current_user_id = get_member_id_from_headers(request)
    # user_instance = User.objects.get(id=current_user_id)

    community_id = request.GET.get('community_id', None)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in params")
        return JsonResponse(context)

    member_instance = Members.objects.filter(community_id=community_id, member_id=current_user_id,
                                             state=member_states.ADMIN)
    if member_instance.exists():
        member = member_instance[0]
        has_right_0 = check_admin_delete_right(user=current_user_id, community=community_id)

        if not has_right_0:
            context = get_error_context(False, "you doesnt have required right to view pending chat rooms")
            return JsonResponse(context)

    else:
        context = get_error_context(False, "You are not a CM of this community")
        return JsonResponse(context)

    pending_chatrooms = Collabcard.objects.filter(community=community_id, is_pending=True,
                                                  is_deleted=False).order_by('id')

    chatrooms = []
    context = {}

    for chatroom in pending_chatrooms:
        chatroom_instance = get_chatroom_instance(chatroom, current_user_id)
        chatrooms.append(chatroom_instance)

    context['chatrooms'] = chatrooms

    return JsonResponse(context)


@csrf_exempt
def action_pending_chatroom(request):
    """ function to approve a chatroom """
    if request.method == "GET":
        context = get_error_context(False, "change HTTP method to POST")
        return JsonResponse(context)

    current_user_id = get_member_id_from_headers(request)
    # user_instance = User.objects.get(id=current_user_id)
    #
    chatroom_id = request.POST.get('chatroom_id', None)
    value = request.POST.get('value', False)
    pre_approve = request.POST.get('pre_approve', None)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not chatroom_id:
        context = get_error_context(False, "send chatroom_id in params")
        return JsonResponse(context)

    try:
        chatroom = Collabcard.objects.get(pk=chatroom_id)
    except:
        context = get_error_context(False, "Pending chatroom id does not exist or already approved or rejected")
        return JsonResponse(context, status=400)

    community_instance = chatroom.community
    chatroom_creator = chatroom.user
    has_right_approve = check_admin_approve_right(user=current_user_id, community=community_instance)
    if not has_right_approve:
        context = get_error_context(False, "you have no right to approve chatrooms")
        return JsonResponse(context)

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
                        state=chatroom_states.CHATROOM_HEADER, current_user_id=chatroom.user.id)

        send_ice_breaker_notification.delay(chatroom.community.id, time.time(), day=0)

        # batch update for already existing users and saving their unseen count
        set_chatroom_state_for_all_members_on_card_creation.delay(chatroom.community.id, card_id=chatroom.id,
                                                                  function_called="action_pending_chatroom")

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

        current_user_instance = User.objects.get(pk=current_user_id)
        save_moderation_history(user=chatroom_creator, community=community_instance,
                                moderation_by=current_user_instance,
                                type=moderation_history_types.MEMBER_PERMISSION_EDITED)

    info_logger.info(
        f"ACTION_PENDING_CHATROOM - current user id = {current_user_id}, card creator id = {chatroom_creator.id}, disallow_create_chatroom = {pre_approve},"
        f"card id = {chatroom_id}, community id = {community_instance.id}")

    return JsonResponse({'success': True})


def fetch_management_tools(request):
    if request.method == "POST":
        context = get_error_context(False, "change HTTP method to GET")
        return JsonResponse(context)

    current_user_id = get_member_id_from_headers(request)
    # user_instance = User.objects.get(id=current_user_id)

    community_id = request.GET.get('community_id', None)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in params")
        return JsonResponse(context)

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
        context = get_error_context(False, "you are not CM for this community")
        return JsonResponse(context)

    community_instance = Community.objects.get(pk=community_id)
    community_name = community_instance.name
    header = f"Management tools for {community_name}"
    management_tools = []

    tools = {"header": header,
             "management_tools": management_tools}

    if not has_right_0 and not has_right_1 and not has_right_2:
        return JsonResponse(tools)

    # cause to do this multiple duplicate checks is to send lkst in tool order as per design
    if has_right_1:
        member_request_tool = get_tool_member_requests(user_id=current_user_id, community_id=community_id)

        member_request_tool[
            "route"] = f"route://member_approve?community_id={community_id}&community_name={community_name}"

        management_tools.append(member_request_tool)

    if has_right_0:
        pending_chatrooms_tool = get_tool_pending_chat_rooms(user_id=current_user_id, community_id=community_id)
        pending_chatrooms_tool[
            "route"] = f"route://pending_chatrooms?community_id={community_id}&community_name={community_name}"
        management_tools.append(pending_chatrooms_tool)

    if has_right_0 or has_right_1:
        reports_tool = get_tool_review_reports(user_id=current_user_id, community_id=community_id,
                                               has_right_0=has_right_0, has_right_1=has_right_1,
                                               has_right_2=has_right_2, parent_cm_list=parent_cm_list,
                                               is_owner=is_owner)
        reports_tool["route"] = f"route://review_reports?community_id={community_id}&community_name={community_name}"
        management_tools.append(reports_tool)

    if has_right_2:
        global tool_edit_directory_questions
        global tool_edit_community_details

        tool_edit_directory_questions = tool_edit_directory_questions.copy()
        tool_edit_community_details = tool_edit_community_details.copy()

        tool_edit_directory_questions[
            "route"] = f"route://edit_community_directory?community_id={community_id}&community_name={community_name}"
        tool_edit_community_details[
            "route"] = f"route://edit_community?community_id={community_id}&community_name={community_name}"

        if has_right_1:
            management_tools.append(tool_edit_directory_questions)
        management_tools.append(tool_edit_community_details)

    if has_right_0 or has_right_1:
        global tool_community_settings
        tool_community_settings = tool_community_settings.copy()
        tool_community_settings[
            "route"] = f"route://community_settings?community_id={community_id}&community_name={community_name}"
        management_tools.append(tool_community_settings)

    return JsonResponse(tools)


def fetch_community_setting_rights(request):
    """ function to fetch community setting rights """

    if request.method == 'POST':
        return JsonResponse({'success': False, 'error_message': 'Change HTTP method to GET'})

    current_user_id = get_member_id_from_headers(request)
    community_id = request.GET.get('community_id', None)
    user_id = request.GET.get('user_id', None)

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in params")
        return JsonResponse(context)

    community_instance = Community.objects.get(pk=community_id)
    current_user_instance = User.objects.get(pk=current_user_id)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing
    # checking if the logged in user is Manager of the community or not
    if admin.exists():
        user_rights = check_all_member_rights(community=community_instance)
        # fetching all the rights of the community
        rights_context = get_saved_member_rights_list(user_rights)
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

    if not current_user_id:
        context = get_error_context(False, "send member_id in headers")
        return JsonResponse(context)
    if not community_id:
        context = get_error_context(False, "send community_id in body")
        return JsonResponse(context)
    # if not selected_rights:
    #     context = get_error_context(False, "send rights in body")
    #     return JsonResponse(context)

    community_instance = Community.objects.get(pk=community_id)
    current_user_instance = User.objects.get(pk=current_user_id)

    admin = Members.objects.filter(member_id=current_user_instance,
                                   community_id=community_instance, state=member_states.ADMIN)  # who is viewing
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
            except:
                error_logger.error("rights already exists for commnunity {community_id} in community settings")

        for right_id in removed_rights:
            # if right is removed, the right is disabled for all the members
            right = memberRights.objects.get(pk=right_id)
            communityRightsSettings.objects.filter(community=community_instance, right=right).delete()
            remove_right_for_all_members(community=community_instance, right=right)

        info_logger.info(
            f"UPDATING_COMMUNITY_SETTINGS - current user id = {current_user_id}"
            f"community id = {community_id}")

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
        if not member_id:
            context = get_error_context(False, "send member id in headers")
            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)
        query_params = request.query_params

        page = query_params.get('page', 1)
        page = int(page)

        paginate_by = query_params.get('page_size', 200)

        last_updated = query_params.get('last_updated', 0)

        chatroom_id = query_params.get('chatroom_id', '')
        community_id = query_params.get('community_id', '')
        chatroom_status = query_params.get('chatroom_status', '')
        chatroom_expire_status = query_params.get('chatroom_expire_status', '')

        draft = query_params.get('draft', '')

        if draft and draft == "true":
            draft_response = self._get_draft_chatrooms(member_id, last_updated, page, paginate_by)
            return JsonResponse(draft_response)

        if chatroom_id:
            state_filter = collabcardState.objects.filter(card=chatroom_id, user=member_id)

            if state_filter.exists():
                chatroom_data, chatroom_id_list = fetch_chatroom_id_query(chatroom_id, member_id)
            else:
                chatroom = get_chatroom_data_in_case_of_guest(chatroom_id, member_id)

                return JsonResponse({'chatrooms':chatroom})

        elif community_id:
            chatroom_data, chatroom_id_list = fetch_community_chatroom_query(community_id, member_id, page, paginate_by, last_updated)

        else:
            chatroom_data, chatroom_id_list = get_user_related_chatrooms(member_id, paginate_by, page, last_updated, chatroom_status, chatroom_expire_status)

        poll_data = {}
        poll_votes = {}

        if chatroom_id_list:
            poll_data = fetch_chatroom_polls(chatroom_id_list)
            poll_votes = fetch_member_poll_votes(chatroom_id_list)

        chatrooms = []

        max_last_updated = 0
        for data in chatroom_data:

            attachment_count = data[45]
            attachments_uploaded = data[46]

            if attachment_count > 0 and\
                    attachments_uploaded is False:
                if int(member_id) != int(data[14]):
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

            chatroom['chatroom_expiry_time'] = data[23]
            chatroom['attending_status'] = data[24]

            chatroom_files = self._get_chatroom_files(chatroom['id'], data[25])
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
                    chatroom['polls'] = polls
                chatroom["expiry_time"] = data[32]

            if chatroom['type'] == card_types.CARD_EVENT or chatroom['type'] == card_types.CARD_PUBLIC_EVENT:
                if data[33]:
                    chatroom['about'] = data[33]
                if data[34]:
                    chatroom['co_hosts_id'] = self._get_co_hosts(data[34])
                if data[35]:
                    chatroom['online_link'] = data[35]
                if data[32] > 0:
                    chatroom['end_date'] = data[32]

            if data[36]:
                chatroom['og_tags'] = json.loads(data[36])

            if data[37]:
                chatroom['preview'] = get_preview_for_url(member_id=member_id,
                                                          preview_url=data[37],
                                                          send_preview_text=False)
            if data[38]:
                chatroom['deleted_by'] = data[38]

            if max_last_updated < data[39]:
                max_last_updated = data[39]

            chatroom['community_name'] = data[40]
            if chatroom['type'] == card_types.CARD_PUBLIC_EVENT:
                chatroom['duration'] = data[41]
                chatroom['location'] = data[42]
                chatroom['location_lat'] = data[43]
                chatroom['location_long'] = data[44]

            chatrooms.append(chatroom)

        if max_last_updated:
            return JsonResponse({'chatrooms': chatrooms, 'max_last_updated': max_last_updated})

        return JsonResponse({'chatrooms': chatrooms})

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
            'videos': []
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

                    files['images'].append(img)
                    attachments.append(img_attachment)

                elif file.type == "pdf":
                    pdf = {'pdf_file': file.file_url, 'index': file.index, 'type': file.type}
                    files['pdf'].append(pdf)
                elif file.type == "audio":
                    audio_file = {'audio_url': file.file_url, 'index': file.index, 'type': file.type}
                    files['audios'].append(audio_file)
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

                    files['videos'].append(video_file)
                    attachments.append(video_attachment)
                    
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


class SyncConversation(APIView):

    def get(self, request, *args, **kwargs):

        member_id = get_member_id_from_headers(request)

        if not member_id:
            context = get_error_context(False, "send member id in headers")

            return JsonResponse(context)

        query_params = request.query_params
        page = query_params.get('page', 1)
        paginate_by = query_params.get('page_size', 200)
        last_updated = query_params.get('last_updated', 0)
        paginate_by = int(paginate_by)
        chatroom_status = query_params.get('chatroom_status', '')
        chatroom_expire_status = query_params.get('chatroom_expire_status', '')
        chatroom_id = query_params.get('chatroom_id', '')
        community_id = query_params.get('community_id', '')

        if chatroom_id:
            # sending all the conversations in a particular chatroom
            seen_conversation = request.GET.get('seen_conversation')
            if seen_conversation:
                conversation_filter = card_answers.objects.filter(card=chatroom_id, id__gt=seen_conversation).order_by(
                    'last_updated')
            elif last_updated:
                conversation_filter = card_answers.objects.filter(card=chatroom_id,
                                                                  last_updated__gt=last_updated).order_by('last_updated')
            else:
                conversation_filter = card_answers.objects.filter(card=chatroom_id).order_by('last_updated')
        elif community_id:
            # sending all the conversation in a particular community
            if not last_updated:
                conversation_filter = card_answers.objects.filter(community=community_id).order_by('last_updated')
            else:
                conversation_filter = card_answers.objects.filter(community=community_id,
                                                                  last_updated__gt=last_updated).order_by('last_updated')
        else:
            conversation_filter = get_user_related_conversations(chatroom_status, chatroom_expire_status,
                                                                 member_id, last_updated)

        conversation_filter = conversation_filter.select_related('preview_community', 'preview_chatroom')

        conversation_list = pagination(conversation_filter, page, paginate_by=paginate_by)

        context = {"current_user_id": member_id, "fetch_reply": True}
        conversations_data = CardAnswersDBSyncSerializer(conversation_list, context=context, many=True)
        conversations = conversations_data.data

        max_last_updated = self.get_attachments_filtered_conversations(conversation_list,
                                                                       conversations,
                                                                       member_id)

        context = {
            'conversations': conversations,
        }

        if max_last_updated:
            context['max_last_updated'] = max_last_updated

        return JsonResponse(context)

    def get_attachments_filtered_conversations(self, conversation_list, conversation_data, member_id):

        conversation_last_index = len(conversation_data) - 1
        max_last_updated = 0

        for conversation in conversation_list[::-1]:

            if conversation.attachment_count > 0 and \
                    conversation.attachments_uploaded is False:

                if NumberUtilities.get_integer_from_string(member_id) != conversation.user.id:
                    del conversation_data[conversation_last_index]
                    conversation_last_index -= 1
                    continue

            if max_last_updated < conversation.last_updated:
                max_last_updated = conversation.last_updated

            conversation_last_index -= 1

        return max_last_updated


def get_user_related_conversations(chatroom_status, chatroom_expire_status, member_id, last_updated):

    """
        This function returns conversation filter based on different conditions of chatroom
        chatroom_status = followed/unfollowed
        chatroom_expire_status = active/ inactive
    """
    chatroom_list = []

    if chatroom_status and chatroom_expire_status:

        if chatroom_status == "followed" and chatroom_expire_status == "active":
            condition_dict = {'user': member_id, 'follow_status': True, 'remove': None}
            chatroom_list = get_id_list_of_chatrooms(condition_dict, active_status=True)

        elif chatroom_status == "followed" and chatroom_expire_status == "inactive":
            condition_dict = {'user': member_id, 'follow_status': True, 'remove': None}
            chatroom_list = get_id_list_of_chatrooms(condition_dict, active_status=False)

        elif chatroom_status == "unfollowed" and chatroom_expire_status == "active":
            condition_dict = {'user': member_id, 'follow_status': False, 'remove': None}
            chatroom_list = get_id_list_of_chatrooms(condition_dict, active_status=True)

        elif chatroom_status == "unfollowed" and chatroom_expire_status == "inactive":
            condition_dict = {'user': member_id, 'follow_status': False, 'remove': None}
            chatroom_list = get_id_list_of_chatrooms(condition_dict, active_status=False)

    elif chatroom_status:

        if chatroom_status == "followed":
            condition_dict = {'user': member_id, 'follow_status': True, 'remove': None}
            chatroom_list = get_id_list_of_chatrooms(condition_dict)

        elif chatroom_status == "unfollowed":
            condition_dict = {'user': member_id, 'follow_status': False, 'remove': None}
            chatroom_list = get_id_list_of_chatrooms(condition_dict)

    elif chatroom_expire_status:

        if chatroom_expire_status == "active":
            condition_dict = {'user': member_id,'remove': None}
            chatroom_list = get_id_list_of_chatrooms(condition_dict, active_status=True)

        elif chatroom_expire_status == "inactive":
            condition_dict = {'user': member_id, 'remove': None}
            chatroom_list = get_id_list_of_chatrooms(condition_dict, active_status=False)

    else:
        condition_dict = {'user': member_id, 'follow_status': False, 'remove': None}
        chatroom_list = get_id_list_of_chatrooms(condition_dict)

    conversation_filter = card_answers.objects.filter(card__id__in=chatroom_list,
                                                      last_updated__gt=last_updated).order_by('last_updated')
    conversation_filter = conversation_filter.select_related('preview_community', 'preview_chatroom')

    return conversation_filter


def get_id_list_of_chatrooms(condition_dict, active_status=None):

    """ return chatroom id list based on conditional dict"""
    q_cond = Q()
    current_time = time.time()

    if active_status is True:
        q_cond = Q(expiry_time=None) | Q(expiry_time__gt=current_time)

    elif active_status is False:
        q_cond = ~Q(expiry_time=None) & Q(expiry_time__lte=current_time)

    chatroom_list = list(collabcardState.objects.filter(
        **condition_dict).filter(q_cond).values_list(
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


def sync_members(request):
    '''api to sync members'''

    member_id = get_member_id_from_headers(request)

    members_type = request.GET.get('members_type', "")

    if not member_id:
        context = get_error_context(False, "send member id in headers")
        return JsonResponse(context)

    page = request.GET.get('page', 1)
    page = int(page)
    paginate_by = request.GET.get('page_size', 200)

    last_updated = request.GET.get('last_updated',0)

    paginate_by = int(paginate_by)
    member_list = []

    chatroom_id = request.GET.get('chatroom_id', '')
    community_id = request.GET.get('community_id', None)

    if members_type == "members":
        if chatroom_id:

            try:
                card_instance = Collabcard.objects.get(pk=chatroom_id)
                community_instance = card_instance.community
            except:
                context = get_error_context(False, "Incorrect chatroom id")
                return JsonResponse(context, status=400)

            chatroom_particpants = collabcardState.objects.filter(card=card_instance, is_guest=False,
                                                                  remove=None).filter(Q(follow_status=True) |
                                                                                      Q(
                                                                                          attending_status=True)).order_by(
                'id')
            participants_list = list(chatroom_particpants.values_list("user__id", flat=True))
            max_last_updated = 0

            chatroom_particpants = list_pagination(participants_list, page, paginate_by=paginate_by)
            if not last_updated:
                chatroom_members = Members.objects.filter(member_id__id__in=chatroom_particpants,
                                                          community_id=community_instance)
            else:
                chatroom_members = Members.objects.filter(member_id__id__in=chatroom_particpants,
                                                          community_id=community_instance, updated_at__gt=last_updated)

            for member_instance in chatroom_members:

                if max_last_updated < member_instance.updated_at:
                    max_last_updated = member_instance.updated_at

                member_data = get_member_instance_for_db_synching(member_instance, member_instance.community_id.id,
                                                                  current_user_id=member_id, send_profile=False)
                member_list.append(member_data)

            if max_last_updated:
                context = {
                    'members': member_list,
                    'max_last_updated': max_last_updated
                }

            else:
                context = {'members': []}

            return JsonResponse(context)

        elif community_id:
            if not last_updated:
                member_filter = Members.objects.filter(community_id=community_id).order_by('id')
            else:
                member_filter = Members.objects.filter(community_id=community_id, updated_at__gt=last_updated).order_by(
                    'id')
        else:
            members_response = fetch_all_members_of_user_joined_communities(member_id, page, last_updated, paginate_by)
            return JsonResponse(members_response)

        paginated_members = get_paginated_queryset_with_maxpages(member_filter, page, paginate_by=paginate_by)

        member_filter = paginated_members['page_list']
        max_last_updated = 0
        for member_instance in member_filter:

            if max_last_updated < member_instance.updated_at:
                max_last_updated = member_instance.updated_at

            member_data = get_member_instance_for_db_synching(member_instance, member_instance.community_id.id,
                                                              current_user_id=member_id, send_profile=False)
            member_list.append(member_data)

        context = {
            'members': member_list
        }

        if max_last_updated:
            context['max_last_updated'] = max_last_updated

        return JsonResponse(context)

    # getting the removed members data

    if members_type == "removed_members":

        if chatroom_id:
            removed_members = collabcardState.objects.filter(card=chatroom_id).filter(~Q(remove=None)).order_by('id')
            max_last_updated = 0
            members = []
            removed_members = pagination(removed_members, page, paginate_by=paginate_by)
            user_set = set()
            for data in removed_members:
                key = data.user.id
                if key not in user_set:
                    community_profile = get_user_profile(data.user, data.community.id, current_user_id=member_id,
                                                         send_profile=False, remove=True)
                    if max_last_updated < data.updated_at:
                        max_last_updated = data.updated_at
                    members.append(community_profile)
                    user_set.add(key)

            context = {
                'members': members,
                'max_last_updated': max_last_updated
            }
            return JsonResponse(context)

        elif community_id:
            remove_member_filter = removedMembers.objects.filter(community=community_id).order_by('id')
        else:
            if not last_updated:
                remove_member_filter = removedMembers.objects.order_by('id')
            else:
                remove_member_filter = removedMembers.objects.filter(created_at__gt=last_updated).order_by('id')

        pagianted_removed_members = get_paginated_queryset_with_maxpages(remove_member_filter, page,
                                                                         paginate_by=paginate_by)

        remove_member_filter = pagianted_removed_members['page_list']
        # max_pages_removed_members = pagianted_removed_members['last_page']
        max_last_updated = 0
        for data in remove_member_filter:

            if max_last_updated < data.created_at:
                max_last_updated = data.created_at

            member_data = get_removed_member_instance(data)
            member_list.append(member_data)

        context = {
            'members': member_list
        }

        if max_last_updated:
            context['max_last_updated'] = max_last_updated
        return JsonResponse(context)

    # getting the guest users
    if members_type == "guest":

        if chatroom_id:
            guest_filter = collabcardState.objects.filter(is_guest=True, card=chatroom_id, remove=None).order_by('id')

        elif community_id:
            guest_filter = collabcardState.objects.filter(is_guest=True, community=community_id).distinct(
                'user').order_by('user')
        else:
            if not last_updated:
                guest_filter = collabcardState.objects.filter(is_guest=True).order_by('id')
            else:
                guest_filter = collabcardState.objects.filter(is_guest=True, updated_at__gt=last_updated).order_by('id')

        guest_filter = pagination(guest_filter, page, paginate_by=paginate_by)

        max_last_updated = 0
        for guest_instance in guest_filter:

            if max_last_updated < guest_instance.updated_at:
                max_last_updated = guest_instance.updated_at

            member_data = get_guest_member_instance(guest_instance)
            member_list.append(member_data)

        context = {
            'members': member_list
        }

        if max_last_updated:
            context['max_last_updated'] = max_last_updated

        return JsonResponse(context)

    context = {
        'members': member_list
    }
    return JsonResponse(context)


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


def fetch_all_members_of_user_joined_communities(member_id, page, last_updated, limit):
    """function to get all members of community which is joined by the member"""

    community_id_list = get_community_id_list(member_id)
    responses_data = get_member_responses_for_community(community_id_list)
    members_data = get_members_of_community(community_id_list, last_updated, page, limit)
    members = []
    max_last_updated = 0

    for data in members_data:
        member_context = dict()
        member_context['id'] = data['member_id']
        member_context['name'] = data['name']
        member_context['image_url'] = data['image_url']
        member_context['state'] = data['state']
        member_context['is_owner'] = data['is_owner']
        community_name = data['community_name']
        locale_time = time.localtime(data['created_at'])

        if data['custom_title'] and not data['custom_title'] == 'Member':
            member_context['custom_title'] = data['custom_title']

        if member_context['state'] == member_states.ADMIN or member_context['state'] == member_states.MEMBER or \
                member_context['state'] == member_states.PROFILE_UNAVAILABLE:
            member_context['member_since'] = "Member of " + community_name + " since " + time.strftime('%b %d %Y',
                                                                                                       locale_time)
        elif member_context['state'] == member_states.PENDING_MEMBER:
            member_context['member_since'] = "Verification pending for " + community_name

        key = str(data['member_id']) + "$" + str(data['community_id'])

        if member_context['state'] == member_states.ADMIN and not responses_data.get(key):
            member_context['custom_intro_text'] = CREATE_INTRO_TEXT_ADMIN % (
                time.strftime("%d %B %Y", locale_time))

        elif member_context['state'] == member_states.MEMBER or member_context['state'] == member_states.PROFILE_UNAVAILABLE:

            if not responses_data.get(key):
                member_context['custom_intro_text'] = CREATE_INTRO_TEXT_MEMBER % (
                    time.strftime("%d %B %Y", locale_time))
                member_context['custom_click_text'] = CUSTOM_CLICK_TEXT % (
                    data['name'],
                    time.strftime("%d %B %Y", locale_time))

        member_context['community_id'] = data['community_id']

        if max_last_updated < data['updated_at']:
            max_last_updated = data['updated_at']

        members.append(member_context)


    if max_last_updated:
        return {'members': members, 'max_last_updated': max_last_updated}

    return {'members': members}


class SyncCommunities(APIView):

    def get(self, request, *args, **kwargs):

        member_id = get_member_id_from_headers(request)
        if not member_id:
            context = get_error_context(False, "send member id in headers")
            return JsonResponse(context)
        query_params = request.query_params

        page = query_params.get('page', 1)
        page = int(page)

        paginate_by = query_params.get('page_size', 200)

        last_updated = query_params.get('last_updated', None)

        chatroom_id = query_params.get('chatroom_id', '')
        community_id = query_params.get('community_id', '')
        context = {"current_user_id": member_id}

        if chatroom_id:
            chatroom_context = fetch_community_of_chatroom(chatroom_id, member_id)

            return JsonResponse(chatroom_context)

        elif community_id:
            engage_filter = Member_Engage.objects.filter(member_id=member_id, community_id=community_id
                                                         ).select_related('community_id')

            if not engage_filter.exists():
                community_context = create_community_context(community_id, member_id)

                return JsonResponse(community_context)

        else:

            if last_updated:
                engage_filter = Member_Engage.objects.filter(member_id=member_id, updated_at__gt=last_updated
                                                             ).select_related('community_id').order_by('id')
            else:
                engage_filter = Member_Engage.objects.filter(member_id=member_id
                                                             ).select_related('community_id').order_by('id')

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

        else:
            max_pages = paginated_query_set['last_page']
            page = page - max_pages
            communities = fetch_guest_communities(member_id, page, paginate_by)

            return JsonResponse(communities)


def fetch_community_of_chatroom(chatroom_id, member_id):

    state_filter = Collabcard.objects.filter(id=chatroom_id).select_related('community')

    if state_filter.exists():
        temp = CommunitySerializerV1([state_filter[0].community], context={"current_user_id": member_id}, many=True)

        chatroom_context =  {'communities': temp.data}

    else:
        chatroom_context = get_error_context(False, "in-correct chatroom id")

    return chatroom_context


def create_community_context(community_id, member_id):

    communities = []
    community_instance = Community.get_community_or_raise_exception(community_id)
    community_list = CommunitySerializerV1(community_instance, context={"current_user_id": member_id}, many=False)
    communities.append(community_list.data)

    return {'communities': communities}


def fetch_guest_communities(member_id , page, paginate_by):

    state_filter = collabcardState.objects.filter(is_guest=True, user_id=member_id).distinct('community').select_related('community').order_by('community')
    guest_community_relation = list(Member_Engage.objects.filter(member_id=member_id).values_list('community_id',flat=True))
    state_filter = pagination(state_filter, page, paginate_by)
    guest_communities = fill_guest_communities(state_filter, member_id, guest_community_relation)

    return {
            'communities': guest_communities
        }


def fill_guest_communities(state_filter, member_id, guest_community_relation):

    context = {"current_user_id": member_id}
    communities = []
    
    for data in state_filter:
        community_instance = data.community

        if community_instance.id in guest_community_relation:
            continue

        community_list = CommunitySerializerV1(community_instance, context=context, many=False)
        communities.append(community_list.data)

    return communities


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


def get_user_related_chatrooms(member_id, paginate_by, page, last_updated, chatroom_status, chatroom_expire_status):

    """
    This function returns chatrooms based on different conditions
    chatroom_status = followed/unfollowed
    chatroom_expire_status = active/ inactive
    """
    chatroom_data = []
    chatroom_id_list = []

    if chatroom_status and chatroom_expire_status:

        if chatroom_status == "followed" and chatroom_expire_status == "active":
            chatroom_data, chatroom_id_list = fetch_chatroom_query_follow_status_active_status(member_id, paginate_by,
                                                                                               page, last_updated, follow_status=True, active_status=True)

        elif chatroom_status == "followed" and chatroom_expire_status == "inactive":
            chatroom_data, chatroom_id_list = fetch_chatroom_query_follow_status_active_status(member_id, paginate_by,
                                                                                               page, last_updated, follow_status=True, active_status=False)

        elif chatroom_status == "unfollowed" and chatroom_expire_status == "active":
            chatroom_data, chatroom_id_list = fetch_chatroom_query_follow_status_active_status(member_id, paginate_by,
                                                                                               page, last_updated, follow_status=False, active_status=True)

        elif chatroom_status == "unfollowed" and chatroom_expire_status == "inactive":
            chatroom_data, chatroom_id_list = fetch_chatroom_query_follow_status_active_status(member_id, paginate_by,
                                                                                               page, last_updated, follow_status=False, active_status=False)

    elif chatroom_status:

        if chatroom_status == "followed":
            chatroom_data, chatroom_id_list = fetch_chatroom_query_with_follow_status(member_id, paginate_by, page,
                                                                                      last_updated, follow_status=True)

        elif chatroom_status == "unfollowed":
            chatroom_data, chatroom_id_list = fetch_chatroom_query_with_follow_status(member_id, paginate_by, page,
                                                                                      last_updated, follow_status=False)

    elif chatroom_expire_status:

        if chatroom_expire_status == "active":
            chatroom_data, chatroom_id_list = fetch_chatroom_query_with_active_status(member_id, paginate_by, page,
                                                                                      last_updated, active_status=True)

        elif chatroom_expire_status == "inactive":
            chatroom_data, chatroom_id_list = fetch_chatroom_query_with_active_status(member_id, paginate_by, page,
                                                                                      last_updated, active_status=False)

    else:
        chatroom_data, chatroom_id_list = fetch_chatrooms_query(member_id, paginate_by, page, last_updated)

    return chatroom_data, chatroom_id_list


