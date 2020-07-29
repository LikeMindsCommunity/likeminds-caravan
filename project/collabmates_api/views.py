from __future__ import absolute_import, unicode_literals
from celery import shared_task
import logging
import os
from datetime import datetime
from urllib.parse import unquote, quote
import googlemaps
import requests as rqst
from celery import shared_task
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import F
from django.db.models import Q
from django.http import HttpResponse
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, render,redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from togther.forms import *
from togther.models import *
from random import randint
# utility functions
from utility.celery_tasks import (save_community_purpose_card,
                                  update_last_unseen_in_engage_on_card_creation,
                                  update_last_unseen_in_engage,update_my_chatrooms_for_users
                                  )
from utility.encryption import encrypt, decrypt
from utility.firebase import update_last_answer_id, upload_image_to_firebase, upload_community_thumbnail, \
    upload_community_files
from utility.states import collabcard_states, member_states, question_states, community_states, deleted_members, \
    card_types, chatroom_states, email_states
from utility.tasks import (mail_triger, new_member_request,
                           member_request_approval_or_denied,
                           send_mail_for_report_abuse,
                           send_mail_for_query_and_feedback
                           )
from utility.utils import (decode_meta_from_url, update_tag_image,
                           get_referred_members_of_a_member,
                           eligibility_count, notify_referred_member,
                           update_member_count,
                           tutorial_count,
    # custom_cache,cache_timeout,
                           get_city_address,
                           update_user_geography_tags, insert_user_home_town_tags, is_IG_community,
                           ig_members_count, is_LG_or_LP_community, feedback_community_id, feedback_collabcard_id,
                           is_member_verified, community_default_image, community_default_thumbnail, is_member_promoter,
                           is_member_present, generate_private_link, generate_random, get_time_text,
                           community_default_image_round, decode_option, get_user_communities_by_rank_web,
                           user_onbaord,get_time_text_for_my_chatrooms,get_members_count_in_community,
                           check_notification_flag

                           )

from .notification import *
from .raw_queries import compute_rank,update_conversation_engage_for_chatrooms
from .serializers import *
from .static_files import *
from .static_text import *
from .members import *
from .tasks import send_email_to_nominated_admin, send_email_for_new_collabcard_posted, send_welcome_mail, \
    send_verification_mail_for_email_sync,send_tagged_user_mail,send_chatroom_owner_mail


# CACHE_TTL = getattr(settings, 'CACHE_TTL', cache_timeout)

url = settings.URL
#url='http://localhost:8000'
error_logger = logging.getLogger("error_logger")
info_logger = logging.getLogger("info_logger")


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
        communities = Community_Rank.objects.filter(member_id=user_id).values('community_id').order_by("-weight").distinct()
    else:
        ''' if no communities are present in Community_Rank send all communities in DESC order of ID  '''
        # get all communities except hidden
        communities = Community.objects.filter(Q(hide_community='0') | Q(hide_community='3') |
                                               Q(hide_community='4')).order_by('-id')
    # paginating the resultant queryset
    queryset = pagination(communities, page_number)
    # return result
    return queryset, is_user_communities.exists()


def pagination(queryset, page_number, paginate_by=10):
    '''function to create pagination and return a query set for page number'''
    paginator = Paginator(queryset, paginate_by)
    max_page = len(paginator.page_range)

    return [] if (max_page < int(page_number) or not queryset.exists()) else paginator.get_page(page_number)


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

    #update pending members in case of multiple promoters
    for member in all_members:

        if member.state == member_states.ADMIN or member.state == member_states.TEMP_ADMIN:
            Member_Engage.objects.filter(community_id=community, member_id=member.member_id
                                         ).update(pending_members=pending_members_count,
                                         updated_at=current_time, member_state=member.state)
        else:
            Member_Engage.objects.filter(community_id=community, member_id=member.member_id
                                         ).update(member_state=member.state)

    info_logger.info("Member Engage Pending Count Updated")


# /api/your_communities/member_id?member_id=
def your_communities(request, user_id):
    '''This function is used to see your communities based on user id'''

    member_id = request.GET.get('member_id')
    current_user_id = get_member_id_from_headers(request)

    page_number = request.GET.get('page', '')
    if str(member_id) != str(user_id):
        member_id = user_id
    my_community = []
    user = User.objects.get(id=member_id)
    communities = Member_Engage.objects.filter(member_id=user).order_by('-updated_at')
    if page_number and not page_number == '0' and not page_number == '':
        communities = pagination(communities, page_number, paginate_by=10)
    for each_community in communities:

        community = CommunitySerializer(each_community.community_id)
        community['pending_members_count'] = each_community.pending_members
        community['updated_at'] = get_time_text(each_community.updated_at)
        if each_community.last_unseen_conversation:
            collabcard = CollabcardSerializer(each_community.last_unseen_conversation, user=member_id)
            user = each_community.last_unseen_conversation.user
            collabcard['member'] = UserinfoSerializer(user.userinfo)
            community['collabcard'] = collabcard

        if each_community.member_referral:
            community['member_referral'] = each_community.member_referral
        if each_community.member_state:
            community['member_state'] = each_community.member_state
        if each_community.member_state == member_states.ADMIN or each_community.member_state == member_states.TEMP_ADMIN or each_community.member_state == member_states.MEMBER or each_community.member_state == member_states.KNOWN_NOMINATED_PROMOTER:
            community['collabcard_unseen'] = each_community.last_unseen_count
        else:
            community['collabcard_unseen'] = 0

        if community['state'] != community_states.DELETED:
            my_community.append(community)

        community['click_state'] = each_community.click_state

    return JsonResponse({'your_communities': my_community})

def my_chatrooms(request):

    '''functions to get chatrooms for users'''

    member_id = get_member_id_from_headers(request)
    page = request.GET.get('page',1)
    if not member_id:
        context = get_error_context(False,"send member id in headers")
        return JsonResponse(context)


    instance_list = conversationEngage.objects.filter(user=member_id).order_by('-updated_at','-id')
    instance_list = pagination(instance_list,page,paginate_by=10)
    my_chatrooms = []
    for instance in instance_list:

        chatroom = {}
        card_instance = instance.card
        draft_instance = instance.draft
        if card_instance:
            chatroom['chatroom'] = get_chatroom_instance(card_instance,member_id)
            chatroom['community'] = CommunitySerializer(card_instance.community)
            chatroom['is_draft'] = False
        elif draft_instance:
            chatroom['chatroom'] = get_draft_chatroom_instance(draft_instance,member_id)
            chatroom['community'] = CommunitySerializer(draft_instance.community)
            chatroom['is_draft'] = True

        last_conversation = instance.last_conversation

        if last_conversation:
            chatroom['last_conversation'] = conversationSerializer(last_conversation)

        chatroom['unseen_conversation_count'] = instance.unseen_count
        chatroom['last_conversation_time'] = get_time_text_for_my_chatrooms(instance.updated_at)

        my_chatrooms.append(chatroom)


    return JsonResponse({"my_chatrooms":my_chatrooms})




######################function for api utility#################################


def get_error_context(success,error_message):

    '''function to get error context for apis'''

    context={
        'success':success,
        'error_message':error_message
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


def community(request, community_id,req_dict=None):
    ''' Community detail page '''

    community = Community.objects.get(id=community_id)
    member_id = get_member_id_from_headers(request)
    is_promoter = False
    block_leave_community = False
    member_list = Members.objects.filter(community_id=community, member_id=member_id)
    promoter_instance = 0
    if member_list.exists():

        state = member_list[0].state

        if state == member_states.ADMIN:
            is_promoter = True
            promoter_instance = member_list[0].member_id
            block_leave_community = True


        if state == member_states.PENDING_MEMBER:
            block_leave_community = True
    else:
        block_leave_community = True


    if is_promoter:
        serialized_object = CommunitySerializer(community,promoter_id=promoter_instance)
    else:
        serialized_object = CommunitySerializer(community)
    new_dict = {}

    community_state = get_state_of_community(community)

    if member_id and (community_state== community_states.PILOT or community_state == community_states.PILOT_ACTIVE):
        serialized_object['share_url'] = serialized_object['share_url'] + "?ref_id=" + str(member_id)

    elif community_state== community_states.PRIVATE or community_state == community_states.HIDDEN or community_state == community_states.WHATSAPP:
        serialized_object['share_url'] = serialized_object['share_url'] + "?cta=share"


    # form a dictionary of community objects
    new_dict.update(serialized_object)
    # if community:
    #     community_type = is_IG_community(community)
    #     if not community_type:
    #         new_dict['share_text_admin'] = """Hi, I am trying to gather %s community on LikeMinds. It will be good if you can join it.\n""" % (new_dict['name'])
    #         new_dict['share_text_member'] = """I recently joined %s community on LikeMinds. It will be good if you also join this community.\n""" % (new_dict['name'])
    #         new_dict['share_text_anonymous'] = """I recently discovered %s community on LikeMinds. You can join this community using this link.\n""" % (new_dict['name'])
    #     else:
    #         new_dict['share_text_admin'] = """Hi, I am trying to gather %s community on CollabMates. It will be fun if you can join it.\n""" % (new_dict['name'])
    #         new_dict['share_text_member'] = """I recently joined %s community on CollabMates. It will be fun if you also join this community.\n""" % (new_dict['name'])
    #         new_dict['share_text_anonymous'] = """I recently discovered %s community on CollabMates. You can join this community using this link.\n""" % (new_dict['name'])
    #new_dict['min_referrer_member'] = eligibility_count

    if community.id == feedback_community_id:
        new_dict['share_url'] = ""

    #leave community data
    if not block_leave_community:
        temp={}
        leave_community = get_leave_community_text()
        temp['leave_community_title'] = leave_community[0]
        temp['leave_community_sub_title'] = leave_community[1]  #fix
        temp['leave_community_positive_title'] = leave_community[2]
        temp['leave_community_negative_title'] = leave_community[3]
        context = {'community': new_dict,'leave_community':temp}
        if req_dict:
            return context
        return JsonResponse(context)

    if req_dict:
        return new_dict

    return JsonResponse({'community': new_dict})



def similar_community(request, community_id,req_dict=None):
    '''function to return similar communitites'''

    if not req_dict:
        body = request.GET
        user_id = body['member_id']
    else:
        user_id=req_dict['member_id']
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

    member_id = request.GET.get('member_id',None)
    if not member_id:
        member_id = get_member_id_from_headers(request)
    pending_requests=get_pending_members_of_community(community_id,requested_member_id=member_id)
    return JsonResponse({'pending_members': pending_requests})

def admins(request, community_id,req_dict=None):

    ''' function to get admins of a community '''



    member_id = request.GET.get('member_id', None)


    current_user_id = get_member_id_from_headers(request)
    admins = Members.objects.filter(community_id=community_id).filter(Q(state=1) | Q(state=2))
    users = []

    for admin in admins:
        user = Userinfo.objects.filter(user_id=admin.member_id.id)
        # get user serialized
        usr = UserinfoSerializer(user[0])

        if int(community_id) != feedback_community_id:
            form_response = FormResponseSerilaizer(community_id, admin.member_id.id,bl=True,current_user_id=current_user_id)
            if form_response:
                usr['response'] = form_response[0]
                usr['question_answers'] = form_response[1]
        else:
            form_response =[
                {
                    'key':"",
                    'value':"founder of LikeMinds"
                }

            ]
            usr['response'] = form_response
        ref_members = get_referred_members_of_a_member(community_id, admin.member_id.id)
        usr['referred_members_count']=len(ref_members)


        users.append(usr)


    community = Community.objects.get(pk=community_id)
    referred_members_count = 0
    if member_id and community.hide_community == '3':
        ref_members = get_referred_members_of_a_member(community_id, member_id)
        referred_members_count = len(ref_members)
        context = {'members': users, 'referred_members_count': referred_members_count}
    elif member_id:

        #print(">>>>>>>>>>> ", member_id)
        referals = get_referred_members_of_a_member(community_id=community_id, member_id=member_id)
        referal_count = len(referals)
        # print(referals)
        # count = 0
        # print("referal count === ", referal_count)
        #
        # for mem_id in referals:
        #     member = Members.objects.filter(member_id=mem_id, community_id=community_id)
        #     if member.exists():
        #
        #         if member[0].state == 4:
        #             count += 1

        context = {'members': users, 'referred_members_count': referal_count}
    else:
        context = {'members': users}


    if req_dict:
        return context

    return JsonResponse(context)



def community_version_1(request,community_id):

    '''api to club data in community detail screen by calling apis from backend'''
    start_time=time.time()

    response={}
    member_id=get_member_id_from_headers(request)
    headers={'x-member-id':member_id}
    #print(headers)

    #community detail api
    community_url=url+"/api/community/"+str(community_id)
    community_detail_response=rqst.get(community_url,headers=headers)
    if community_detail_response.status_code == 200:
        community_detail_response = community_detail_response.json()
        #print(community_detail_response)

        response['community_api'] = community_detail_response

    #admins api

    admin_url = url + "/api/admins/" + str(community_id)
    admin_response = rqst.get(admin_url, headers=headers,params={'member_id':member_id})
    if admin_response.status_code == 200:
        admin_response = admin_response.json()
        # print(community_detail_response)

        response['admins_api'] = admin_response


    #members api
    member_url = url + "/api/all_members"
    member_response = rqst.get(member_url, headers=headers, params={'community_id': community_id})
    if member_response.status_code == 200:
        member_response = member_response.json()
        # print(community_detail_response)

        response['all-member-api'] = member_response


    #members_state
    member_url = url + "/api/members_state"
    member_state = rqst.get(member_url, headers=headers, params={'community_id': community_id,'member_id':member_id})
    if member_state.status_code == 200:
        member_state = member_state.json()
        state=member_state['state']
        # print(community_detail_response)

        response['member-state-api'] = member_state



    # pending-members
    pending_url = url + "/api/pending_members/"+str(community_id)
    pending_response = rqst.get(pending_url, headers=headers, params={'community_id': community_id, 'member_id': member_id})

    if pending_response.status_code == 200:
        pending_response = pending_response.json()
        # print(community_detail_response)

        response['pending-members-api'] = pending_response

    if member_state['state'] == member_states.ADMIN or member_state['state'] == member_states.MEMBER or member_state['state'] == member_states.KNOWN_NOMINATED_PROMOTER:

        # collabcard url
        collabcard = url + "/api/v1/community_collabcard/" + str(community_id)
        collabcard = rqst.get(collabcard, headers=headers,
                                    params={'community_id': community_id, 'member_id': member_id})

        if collabcard.status_code == 200:
            collabcard = collabcard.json()
            # print(community_detail_response)

            response['v1/collabcard-api'] = collabcard

    else:

        # similar communities
        similar_communities = url + "/api/similar_communities/" + str(community_id)
        similar_communities = rqst.get(similar_communities, headers=headers,
                                    params={'community_id': community_id, 'member_id': member_id})

        if similar_communities.status_code == 200:
            similar_communities = similar_communities.json()
            # print(community_detail_response)

            response['similar_communities'] = similar_communities

    end_time = time.time()

    diff = end_time-start_time

    info_logger.info("community-version-api")
    info_logger.info(diff)
    info_logger.info("\n\n")


    return JsonResponse(response)



def community_version_2(request,community_id):


    start_time = time.time()
    response={}
    member_id=get_member_id_from_headers(request)
    #community_detail_api
    community_detail = community(request,community_id,req_dict=True)
    response['community'] = community_detail

    #admins api
    admins_api=admins(request,community_id,req_dict={'member_id':member_id})
    response['admins-api'] = admins_api

    #all_members api
    all_members_api=get_all_members(request,req_dict={'community_id':community_id})
    response['all_members_api'] = all_members_api

    #member_state api

    member_state=members_state(request,req_dict={'community_id':community_id,'member_id':member_id})
    response['members_state_api'] = member_state

    #pending members api
    pending_members=get_pending_members_of_community(community_id,member_id)
    response['pending_members_api'] = pending_members


    if member_state['state'] == member_states.ADMIN or member_state['state'] == member_states.MEMBER or member_state['state'] == member_states.KNOWN_NOMINATED_PROMOTER:
        #community_collabcard
        community_collabcard=community_cards_version_1(request,community_id,{'member_id':member_id})
        response['community_collabcard_api']=community_collabcard
    else:
        # suggested_communities api
        suggested_community = similar_community(request, community_id, {'member_id': member_id})
        response['similar_communities_api'] = suggested_community

    end_time=time.time()

    info_logger.info("Community Detail version 2")
    diff= end_time-start_time
    info_logger.info(diff)


    return JsonResponse(response)



############# functions for  join community  screen ##########################



def questions(request):

    '''api to send the questions for a particular community'''

    member_id = get_member_id_from_headers(request)

    community_id = request.GET.get('community_id')
    data = communityQuestions.objects.filter(community=community_id).order_by("id")
    community_instance = Community.objects.get(id=community_id)
    community = CommunitySerializer(community_instance)

    created_by = get_community_creator(community_instance)

    community['created_by'] = created_by

    ##private link share flow
    aj = request.GET.get('aj')


    auto_join = private_link_app_invite(community_instance,aj,created_by)


    questions = []

    for question in data:
        serialized_question = CommunityQuestionsSerializer(question)
        if serialized_question['state'] == question_states.INTRODUCTION:
            serialized_question['rank'] = 0
            answers_filter = communityAnswers.objects.filter(question=serialized_question['id'],member=member_id)
            if answers_filter.exists():
                answer_instance = answers_filter[0]
                introduction_answer = answer_instance.question_answer
                serialized_question['previous_answer'] = introduction_answer

        else:
            serialized_question['rank'] = 1

        # if the question is not deleted
        if not question.remove_state:
            questions.append(serialized_question)
    questions = sorted(questions, key=lambda i: i['rank'])

    context = {'questions': questions, 'community': community}

    if aj:
        context.update(auto_join)
    return JsonResponse(context)

def private_link_app_invite(community_instance,unique_code,created_by):

    '''function to send private link for app invite on playstore'''

    expiry_filter = communityExpiryCodes.objects.filter(community=community_instance, unique_code=unique_code)

    auto_join ={
        'toast': """The private invite link has expired. Continue to join the community and wait for admin’s approval. Or, ask %s to resend a private invite link."""%(created_by),
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
            auto_join['toast'] = """This private invite link expires in %s"""%(time_left)


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

    community_instance = Community.objects.get(id=community_id)
    community=community_instance


    community_state = get_state_of_community(community_instance)


    # is_private = False
    # if community_state == community_states.PRIVATE or community_state == community_states.HIDDEN:
    #     is_private = True
    #
    # if is_private:
    info_logger.info("Inside private\n")
    join_promoter_created_community_version_1(res, request)

    return JsonResponse({'success': True})



def join_promoter_created_community_version_1(res,request):

    '''function to join promoter created community'''

    community_id = res['community_id']
    community_instance = Community.objects.get(id=community_id)

    member_id = get_member_id_from_headers(request)
    if not member_id:
        member_id = request.GET.get('member_id', None)
    else:
        res['timestamp'] = res['timestamp'] / 1000  # for android timestamp

    user_instance = User.objects.get(id=member_id)


    if 'questions' in res:

        for question in res['questions']:


            if 'value' not in question or not question['value']:
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

                selected_choices = question['value'].split("$#")
                save_user_selected_options(question_instance, user_instance, community_instance, selected_choices)


    update_hidden_fields_in_questions(user_instance,community_instance)

    #saving data directly
    if 'aj' in res:
        if res['aj']:
            validate_time = is_joining_time_valid(community_instance, res['timestamp'], res['aj'])
            info_logger.info(validate_time)
            if validate_time:
                auto_join_community(community_instance, user_instance)
                set_state_for_onboarding_chatroom(community_instance, user_instance.id, request)
                post_introduction_card_for_community(community_id, member_id, request)

                # saving create community action level3
                update_community_actions(community_instance)

                log = """Auto join community for community_id=%s for user=%s""" % (community_id, member_id)
                info_logger.info(log)
                return


    member_list = Members.objects.filter(member_id=user_instance, community_id=community_instance)

    if member_list:
        member_state = member_list[0].state
        if member_state == member_states.ADMIN:

            #post_purpose_collabcard_for_community(request, community_instance, member_id)
            post_introduction_card_for_community(community_id, member_id, request)

            generate_private_link(community_instance, user_instance)

            Member_Engage.objects.filter(member_id=user_instance, community_id=community_instance).update(
                member_referral="",click_state = click_states.DEFAULT)

            #updating the community level 3 state

            communityLevels.objects.filter(community=community_instance).update(level_click_state=level_click_states.COMMUNITY_JOINED)

        elif member_state == member_states.PROFILE_UNAVAILABLE:

            Members.objects.filter(member_id=user_instance, community_id=community_instance).update(
                state=member_states.MEMBER)

            Member_Engage.objects.filter(member_id=user_instance, community_id=community_instance).update(
                member_state=member_states.MEMBER,click_state=click_states.DEFAULT)
            post_introduction_card_for_community(community_id, member_id, request)
            set_state_for_onboarding_chatroom(community_instance, user_instance.id, request)
        else:

            Members.objects.filter(member_id=user_instance, community_id=community_instance).update(
                state=member_states.PENDING_MEMBER)

            Member_Engage.objects.filter(member_id=user_instance, community_id=community_instance).update(
                member_state=member_states.PENDING_MEMBER)
        update_pending_member_count_in_engage(community_instance)
        return JsonResponse({'success': True})
    else:

        # creating a member instance
        member_instance = Members()
        member_instance.member_id = user_instance
        member_instance.community_id = community_instance
        member_instance.state = member_states.PENDING_MEMBER
        member_instance.created_at = time.time()
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


def auto_join_community(community_instance,user_instance):

    # updating the member instance
    if not is_member_verified(community_instance,user_instance):
        member_instance = Members()
        member_instance.member_id = user_instance
        member_instance.community_id = community_instance
        member_instance.state = member_states.MEMBER
        member_instance.created_at=time.time()
        member_instance.save()
        send_notification_for_join_requests.delay(community_instance.id, True, user_instance.id)

    # updating the member engage instance
    if not is_member_engage(community_instance,user_instance):
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.MEMBER
        engage.save()



def post_introduction_card_for_community(community_id,member_id,request):

    '''fucntion to get introduction card of community'''

    check_intro=communityQuestions.objects.filter(community=community_id,question_state=question_states.INTRODUCTION)
    if check_intro.exists():
        question_id=check_intro[0].id
        introduction_answer_list=communityAnswers.objects.filter(community=community_id,member=member_id,question_id=question_id)
        if introduction_answer_list.exists():
            introduction_answer=introduction_answer_list[0].question_answer
            req_dict = {

                'member_id': member_id,
                'community_id': community_id,
                'title': introduction_answer,
                'type': 1,
                'create_intro': 1
            }
            request.method = "POST"
            create_card(request, req_dict=req_dict)
            return True

    return False

def post_purpose_collabcard_for_community(request,community_instance,member_id):

    '''function to post purpose card for community'''

    introduction_answer=community_instance.purpose
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


def update_hidden_fields_in_questions(user_instance,community_instance):

    '''api to update hidden fields in questions'''
    question_filter = communityQuestions.objects.filter(community=community_instance,is_hidden=True)

    for question_instance in question_filter:



        if question_instance.question_state == question_states.EMAIL_ID:

            answer_instance = communityAnswers()
            answer_instance.question = question_instance
            answer_instance.member = user_instance
            answer_instance.community = community_instance
            answer_instance.question_answer = user_instance.userinfo.email
            answer_instance.question_title = question_instance.question_title
            answer_instance.save()




def creating_collabcard_for_lg_communities(community,user,introduction_answer,ref_id=None):

    '''function to create collabcard for lg community'''

    if ref_id:
        is_present=collabcardTemp.objects.filter(community=community,member=user)
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

            #creating for user
            collabcard_temp_instance=collabcardTemp()
            collabcard_temp_instance.member=user
            collabcard_temp_instance.community=community
            collabcard_temp_instance.title=introduction_answer
            collabcard_temp_instance.show_member=user
            collabcard_temp_instance.created_at=time.time()
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

    instance_list = communityLevels.objects.filter(community=community_instance).order_by('id')
    community_level_filter = instance_list
    for instance in instance_list:

        if instance.level == "Level 2" and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()
                #instance.update(joined_members=F(instance.joined_members)+1)

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                instance.save()

                community_level_filter.filter(level="Level 3").update(title="Set up community directory",
                                                                      sub_title="Help members know each other. Give 10 members a community-specific identity.",
                                                                      state = community_level_states.PENDING)

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

        elif instance.level == "Level 4" and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                promoter_filter.update(actions_required = False)
                instance.save()


def set_levels_on_ctc(community_instance,level):

    '''updating levels based on differet call to actions'''

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
                







def save_user_selected_options(question_instance,user_instance,community_instance,selected_choices):

    '''function to save user selected options in dropdown'''

    #question_instance = communityQuestions.objects.get(id=48562)

    dropdown_list =  decode_option(question_instance.value)

    for choice in selected_choices:

        option = choice.strip()
        if not is_option_present(option,dropdown_list):
            dropdown_list.append(option)
        filter_instance = questionFilters(question=question_instance, filter=option,
                                          member=user_instance, community=community_instance)
        filter_instance.save()

    result = []
    for value in dropdown_list:
        temp={}
        temp['value'] = value
        result.append(temp)

    json_dump = json.dumps(result)
    question_instance.value = json_dump
    question_instance.save()


def is_option_present(option,dropdown_list):

    '''function to check is option present or not'''

    for data in dropdown_list:
        if data.lower() == option.lower():
            return True
    return False




############# functions for  members of community   ##########################

def user(request, user_id):
    '''function to send user object with tags'''

    info = Userinfo.objects.all().filter(user_id=user_id)
    usr = UserinfoSerializer(info[0])

    tags = get_user_lpig_tags(user_id)
    if tags:
        usr['tags'] = tags
        return JsonResponse({'user': usr})

    return JsonResponse({'user': usr})


def members(request, community_id):
    ''' function to get all the mebers of a community including admins and nominated members '''
    community = get_object_or_404(Community, pk=community_id)
    # get members of the community

    current_user_id = get_member_id_from_headers(request)


    if community_id == feedback_community_id:
        # if the community is feedback community sending empty list
        return  JsonResponse({'members': []})


    member = Members.objects.filter(community_id=community).filter(Q(state=1) | Q(state=2) |
                                                                   Q(state=4) | Q(state=7) |
                                                                   Q(state=8) | Q(state=9))
    members = []
    for mem in member:

        if not mem.member_id.userinfo:
            continue
        usr = UserinfoSerializer(mem.member_id.userinfo)
        usr['member_state'] = mem.state
        form_response = FormResponseSerilaizer(community_id, mem.member_id.id,bl=True,current_user_id=current_user_id)
        if form_response:
            usr['response'] = form_response[0]
            usr['question_answers'] = form_response[1]

        members.append(usr)

    context={'members': members}
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

    user_instance = User.objects.get(id=member_id)

    answer_filter = communityAnswers.objects.filter(community=community_instance,member=user_instance)


    #getting the collabcard Id for introduction card
    collabcard_id = 0
    for answer in answer_filter:
        if answer.question.question_state == question_states.INTRODUCTION:

            collabcard_filter = Collabcard.objects.filter(community=community_instance,
                                                          user=user_instance,title=answer.question_answer)

            if collabcard_filter.exists():
                collabcard_id = collabcard_filter[0].id





    delete_filters = questionFilters.objects.filter(member=user_instance,community=community_instance).delete()
    delete_answers = answer_filter.delete()


    info_logger.info(delete_answers)
    info_logger.info(delete_filters)
    info_logger.info("\n")

    if 'questions' in res:

        for question in res['questions']:

            #empty cases handling
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


    update_hidden_fields_in_questions(user_instance,community_instance)
    form_response = FormResponseSerilaizer(community_id,member_id, bl=True, current_user_id=member_id)

    #setting edit status in members table
    Members.objects.filter(community_id=community_instance,member_id=user_instance).update(edit_required=False)

    #posting a introduction collabcard
    if collabcard_id == 0:
        post_introduction_card_for_community(community_instance.id,user_instance.id,request)


    #update level of community
    set_levels_on_ctc(community_instance,"Level 3")


    question_answer=""
    if form_response:
        question_answer = form_response[1]

    if question_answer:
        return JsonResponse({'success': True,'question_answers':question_answer})

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

    member_id=get_member_id_from_headers(request)
    ask_member_id=request.GET.get('ask_member_id',None)


    community_id=request.GET.get('community_id')
    community_instance=Community.objects.get(id=community_id)

    if not ask_member_id:
        contact_number=request.GET.get('contact_number')
        user_instance=User.objects.get(id=member_id)
        Userinfo.objects.filter(user_id=user_instance).update(contact_number=contact_number)
        new_member_request.delay(member_id=member_id, community_id=community_id, ref_id=None,
                                 form_response=None, ph_no=contact_number)
        return JsonResponse({'success': True})

    member_instance=Members.objects.get(member_id=member_id,community_id=community_id)
    member_engage_instance=Member_Engage.objects.get(community_id=community_id,member_id=ask_member_id)

    if member_instance.ask_member_id:                       #if the member ask someone else already for verification
        previous_asked_member=member_instance.ask_member_id
        member_engage_ask_instance=Member_Engage.objects.get(community_id=community_id,member_id=member_instance.ask_member_id)
        if member_engage_ask_instance.pending_members:
            member_engage_ask_instance.pending_members= member_engage_ask_instance.pending_members - 1
            member_engage_ask_instance.save()

        collabcardTemp.objects.filter(show_member=previous_asked_member,member=member_id,community=community_id).delete()
        collabcardTemp.objects.filter(show_member=member_id,member=previous_asked_member,community=community_id).delete()

    member_instance.ask_member_id=ask_member_id
    member_instance.save()

    member_engage_instance.pending_members=member_engage_instance.pending_members + 1
    member_engage_instance.save()

    card_temp_list=collabcardTemp.objects.filter(show_member=member_id,member_id=member_id,community_id=community_id)

    if card_temp_list.exists():
        ask_user_instance=User.objects.get(id=ask_member_id)

        card_temp_instance=collabcardTemp()
        card_temp_instance.show_member=ask_user_instance
        card_temp_instance.member=card_temp_list[0].member
        card_temp_instance.community=card_temp_list[0].community
        card_temp_instance.title = card_temp_list[0].title
        card_temp_instance.created_at = card_temp_list[0].created_at
        card_temp_instance.save()

    # ask_approval_notification(community_id=community_id, community_name=community_instance.name, approver_id=ask_member_id,
    #                           member_name=member_instance.member_id.userinfo.name, community_state=community_instance.hide_community)



    return JsonResponse({'success':True})




@csrf_exempt
def remove_from_member(request):

    '''function to remove member of community'''

    member_id = get_member_id_from_headers(request)

    if not member_id:
        return JsonResponse({'success':False,'error_message':"Send Member Id in header"})

    community_id = request.POST.get('community_id')

    member_ids = request.POST.get('member_ids', False)

    is_promoter = Members.objects.filter(state=member_states.ADMIN, community_id=community_id, member_id=member_id)
    is_promoter = is_promoter.exists()
    if member_ids:
       if is_promoter:

           member_ids = unquote(member_ids)
           member_ids = json.loads(member_ids)


           for member in member_ids:
                member_filter = Members.objects.filter(community_id=community_id,member_id=member)

                if member_filter.exists():
                    member_state = member_filter[0].state
                    if member_state == member_states.MEMBER or member_state == member_states.KNOWN_NOMINATED_PROMOTER:
                        remove_members(community_id,member_filter[0].member_id.id,removed_state=deleted_members.REMOVED)

           return JsonResponse({'success': True})
       else:
           return JsonResponse({'success':False,'error_message':"You are not the promoter of this community"})



    #flow to leave the community
    if not is_promoter and member_ids == False:

        is_member=Members.objects.filter(community_id=community_id,member_id=member_id).filter(
            Q(state=member_states.KNOWN_NOMINATED_PROMOTER)|Q(state=member_states.MEMBER))
        if is_member.exists():
            remove_members(community_id,member_id,removed_state=deleted_members.LEFT)
            return JsonResponse({'success':True})
        else:
            return JsonResponse({'success':False,'error_message':"You are not the member of this community"})

    # else:
    #
    #     context = get_error_context(False,"You are the promoter of this community can't leave this community ")
    #     return JsonResponse(context)

    return JsonResponse({'success':False})


def remove_members(community_id, member_id,removed_state):
    '''function to remove member'''

    try:
        community_instance = Community.objects.get(id=community_id)
        user_instance = User.objects.get(id=member_id)
    except:
        return



    #communityAnswers.objects.filter(community=community_id, member=member_id).delete()

    is_member_left = removedMembers.objects.filter(community=community_id, member=member_id)

    if not is_member_left.exists():

        instance = removedMembers(community=community_instance, member=user_instance,
                                  removed_state=removed_state, created_at=time.time())
        instance.save()
        #saving collabcard state in update status
        update_staus = collabcardState.objects.filter(community=community_id,user=member_id).update(removed_status=instance.id)
        print(update_staus)


    member_removerd = Members.objects.filter(community_id=community_id, member_id=member_id).delete()
    #print(member_removerd)

    engage_removed = Member_Engage.objects.filter(community_id=community_id, member_id=member_id).delete()
    #print(engage_removed)

    profile_removed = communityAnswers.objects.filter(community=community_id, member=member_id).delete()
    #print(profile_removed)

    intro_removed = Collabcard.objects.filter(community=community_id,user=member_id,type=card_types.CARD_INTRO).delete()
    #print(intro_removed)





############# functions for  create flow of card,community and members   ##########################



@csrf_exempt
def create_community_version_1(request):

    '''function to create community for version for whatsapp shifting'''
    member_id=get_member_id_from_headers(request)
    user_instance=User.objects.get(pk=member_id)
    res=json.loads(request.body)
    print(res)

    community_name=""
    purpose=""
    community_type = None
    sub_type = None

    page = 1

    if 'page' in res:
        page = res['page']

    if 'name' in res:
        community_name=res['name']

    if 'purpose' in res:
        purpose=res['purpose']

    if 'type' in res:
        community_type=res['type']

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

        community_instance=Community()
        community_instance.name=community_name
        community_instance.members_count=1
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
        member_instance.created_at = time.time()
        member_instance.save()

        # making the member enage instance for created community
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.ADMIN
        engage.member_referral = "Finish setting up your community"
        engage.click_state = click_states.SET_PURPOSE
        engage.save()

        community_serializer = CommunitySerializer(community_instance,promoter_id=user_instance)
        return JsonResponse({'success':True,'community':community_serializer})



    elif page == 2:


        community_instance = Community.objects.get(id=community_id)
        community_instance.purpose = purpose
        community_instance.save()

        engage_filter = Member_Engage.objects.filter(community_id=community_instance.id,member_id=member_id)
        engage_filter.update(click_state = click_states.DEFAULT)

        create_introduction_question_in_community(community_instance)
        post_purpose_collabcard_for_community(request, community_instance, member_id)


        community_serializer = CommunitySerializer(community_instance, promoter_id=user_instance)
        return JsonResponse({'success': True, 'community': community_serializer})

    elif page == 3:

        try:
            community_instance = Community.objects.get(id=community_id)

            create_community_questions(res)

            #updating the community level click state
            communityLevels.objects.filter(community=community_instance,level="Level 3").update(level_click_state=level_click_states.DIRECTORY_CREATED)

            card_filter = Collabcard.objects.filter(user=user_instance,community=community_instance,type=card_types.CARD_PURPOSE)

            if card_filter.exists():
                post_member_directly_link(card_filter[0], user_instance, community_instance)

        except Exception as e:

            context = get_error_context(False, e)
            return JsonResponse(context)

        community_serializer = CommunitySerializer(community_instance, promoter_id=user_instance)
        return JsonResponse({'success': True, 'community': community_serializer})


def create_community_questions(res):

    '''function to create community questions'''


    community_id = res['community_id']
    community_instance = Community.objects.get(id=community_id)

    if 'questions' in res:
        for question in res['questions']:

            if question['state'] == question_states.INTRODUCTION:
                question_filter = communityQuestions.objects.filter(question_state=question_states.INTRODUCTION,community=community_instance)
                if question_filter.exists():
                    question_instance = question_filter[0]
                    question_instance.community = community_instance
                    question_instance.question_title = question['question_title']
                    question_instance.question_state = question['state']
                    question_instance.value = question['value'] if 'value' in question else None
                    question_instance.optional = question['optional']
                    question_instance.help_text = question['help_text'] if 'help_text' in question else None
                    question_instance.is_hidden = question['is_compulsory'] if 'is_compulsory' in question else False
                    question_instance.save()

            else:
                questions_instance = communityQuestions()
                questions_instance.community = community_instance
                questions_instance.question_title = question['question_title']
                questions_instance.question_state = question['state']
                questions_instance.value = question['value'] if 'value' in question else None
                questions_instance.optional = question['optional']
                questions_instance.help_text = question['help_text'] if 'help_text' in question else None
                questions_instance.is_hidden = question['is_compulsory'] if 'is_compulsory' in question else False
                questions_instance.save()


    #setting the state of community in order to make it editable
    Members.objects.filter(community_id=community_instance,state=member_states.MEMBER).update(edit_required=True)


def create_introduction_question_in_community(community_instance):

    '''function to create introduction question in community'''

    help_text = None
    field_filter = communityField.objects.filter(state=question_states.INTRODUCTION,
                                                 type=community_instance.type,sub_type=community_instance.sub_type)

    if field_filter.exists():
        help_text = field_filter[0].help_text

    value_list = [{"min_chars": "50", "max_chars": "No limit"}]
    questions_instance = communityQuestions()
    questions_instance.community = community_instance
    questions_instance.question_title = "Introduce yourself"
    questions_instance.question_state = question_states.INTRODUCTION
    questions_instance.value = json.dumps(value_list)
    questions_instance.optional = False
    questions_instance.help_text = help_text
    questions_instance.is_hidden = False
    questions_instance.save()

def post_member_directly_link(card_instance,user_instance,community_instance):

    member_directory_link = url + "/members_directory/"+str(community_instance.id)
    conversation = card_answers()
    conversation.answer = """Here is a link to our member directory: %s"""%(member_directory_link)
    conversation.card = card_instance
    conversation.user = user_instance
    conversation.created_at = time.time()
    conversation.save()


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

    context = {'types':types}
    context['onboarding_examples'] = ONBOARDING_EXAMPLES
    return JsonResponse(context)



def get_basic_directory_options(request):

    '''api to get basic diretory options'''

    type_id = request.GET.get('type')
    sub_type_id = request.GET.get('sub_type')

    if not type_id or not sub_type_id :
        context = get_error_context(False,"send type  sub_type  in get params")
        return JsonResponse(context)

    field_filter = communityField.objects.filter(type=type_id,sub_type=sub_type_id).order_by('-rank')

    questions = []
    for field in field_filter:

        # if field.state == question_states.GOOGLE_CITY_FETCH:
        #     continue
        temp  = communityFieldSerializer(field)
        questions.append(temp)

    return JsonResponse({'questions':questions})










def update_community(res):

    '''function to update the community'''

    community_id = res['community_id']

    community_filter = Community.objects.filter(id=community_id)

    #updating community
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


        #deleting previous questions
        delete_status = communityQuestions.objects.filter(community=community_id).delete()
        print("delete status--",delete_status)


        #saving the questions again
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

        #first level
        instance = communityLevels()
        instance.community = community_instance
        instance.level = "Level 1"
        instance.title = "Create onboarding room"
        instance.sub_title = "Break the ice for new members. Tell what this community stands for."
        instance.state = community_level_states.COMPLETE
        instance.image = IMAGE_LEVEL_1
        instance.save()

        #second level
        instance = communityLevels()
        instance.community = community_instance
        instance.level = "Level 2"
        instance.title = "Invite your inner circle"
        instance.sub_title = "Bring 5 trusted people you want to build this community with."
        instance.joined_members = 0
        instance.max_members = 2 if settings.IS_BETA  else 5
        instance.state = community_level_states.PENDING
        instance.image = IMAGE_LEVEL_2
        instance.save()

        #third level
        instance = communityLevels()
        instance.community = community_instance
        instance.level = "Level 3"
        instance.title = "Community Directory"
        instance.state = community_level_states.LOCKED
        instance.joined_members = 0
        instance.max_members = 2 if settings.IS_BETA  else 10
        instance.image = IMAGE_LEVEL_3
        instance.save()

        #fourth level
        instance = communityLevels()
        instance.community = community_instance
        instance.level = "Level 4"
        instance.title = "Growth"
        instance.state = community_level_states.LOCKED
        instance.joined_members = 0
        instance.max_members = 2 if settings.IS_BETA  else 10
        instance.image = IMAGE_LEVEL_4
        instance.save()


@csrf_exempt
def create_card(request,req_dict=None):
    ''' function to create a card '''

    if not req_dict:
        user_id = request.GET.get('member_id')
        community_id = request.GET.get('community_id')
        res = json.loads(request.body)
    else:
        user_id=req_dict['member_id']
        community_id=req_dict['community_id']
        res = req_dict

    context = create_card_internal(user_id,community_id,res)

    if req_dict:
        return context

    return JsonResponse({'success': True, 'collabcard': context['collabcard']})



def create_chatroom_instance(res,community_instance,user_instance):

    '''function to create chatroom instance'''
    card = Collabcard()
    card.title = res['title']
    card.community = community_instance
    card.user = user_instance
    card.type = int(res['type']) if 'type' in res else card_types.CARD_NORMAL
    card.image_count = res['image_count'] if ('image_count' in res) else 0
    card.pdf_count = res['pdf_count'] if ('pdf_count' in res) else 0
    card.date_time = res['date_time'] if ('date_time' in res) else 0
    card.duration = res['duration'] if ('duration' in res) else 0

    # for event card
    card.location = res['location'] if ('location' in res) else None
    card.location_lat = res['location_lat'] if ('location_lat' in res) else None
    card.location_long = res['location_long'] if ('location_long' in res) else None
    card.start_date = res['start_date'] if ('start_date' in res) else 0
    card.end_date = res['end_date'] if ('end_date' in res) else 0
    card.about = res['about'] if ('about' in res) else None
    card.co_hosts = json.dumps(res['co_hosts']) if ('co_hosts' in res) else None
    card.online_link = res['online_link'] if ('online_link' in res) else None

    # for poll card
    card.multiple_select = res['multiple_select'] if ('multiple_select' in res) else False
    card.multiple_select_no = res['multiple_select_no'] if ('multiple_select_no' in res) else 1
    card.multiple_select_state = res['multiple_select_state'] if ('multiple_select_state' in res) else 0

    # for chatroom header
    has_been_named = False
    if 'header' in res:

        card.header = res['header']
        has_been_named = True
        card.has_been_named = has_been_named
    else:

        if len(res['title']) <= 30:
            card.header = card.title[:30]
        else:
            card.header = card.title[:27] + "..."

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

    card.date_epoch = time.time()  # card creation time
    card.save()


    #send notification to new chatroom posted
    if has_been_named:
        send_chatroom_creation_notifications_and_mails(card,user_instance)

    # sending notification to co-hosts
    if card.co_hosts:
        co_hosts = res['co_hosts']

        # making the co_host auto follow the card
        for host in co_hosts:
            req_dict = {
                'member_id': host,
                'collabcard_id': card.id,
                'status': True
            }
            collabcard_follow_internal(req_dict)

        send_notification_to_event_co_hosts.delay(co_hosts, card.id, card.title, user_instance.userinfo.name)

    # saving poll card details
    polls = res['polls'] if 'polls' in res else []
    for poll in polls:
        collabcardpolls_instance = CollabcardPolls()
        collabcardpolls_instance.card = card
        collabcardpolls_instance.text = poll['text']
        collabcardpolls_instance.sub_text = poll['sub_text'] if ('sub_text' in poll) else None
        collabcardpolls_instance.save()


    return card


def create_card_internal(user_id,community_id,res):


    user_instance = User.objects.get(id=user_id)
    userinfo_instance = user_instance.userinfo
    community_instance = Community.objects.get(id=community_id)


    card_instance = create_chatroom_instance(res,community_instance,user_instance)

    #if the community is a ig community
    create_intro=False
    if 'create_intro' in res:
        create_intro=True


    collabcard = CollabcardSerializer(card_instance, user_id, community_instance)

    collabcard['date'] = datetime.today().strftime('%d-%m-%Y')

    # get user object's serialized json
    user_info_serializer = UserinfoSerializer(userinfo_instance)
    collabcard['member'] = user_info_serializer


    if create_intro:
        update_seen_status_for_new_user_in_chatroom(community_instance,user_instance)

    #following the user created chatroom
    func_dict = {
        'member_id': user_id,
        'collabcard_id': card_instance.id,
        'status': True
    }
    collabcard_follow_internal(func_dict)

    update_last_answer_id(card_instance.id, "")

    #creating a chatroom for the collabcard posted
    create_chatroom(card_instance=card_instance,user_instance=user_instance
                        ,state=chatroom_states.CHATROOM_HEADER,current_user_id=user_id)

    update_last_unseen_in_engage_on_card_creation.delay(community_id=community_id)



    #deleting the draft chatroom
    if 'draft_id' in res:
        conversationEngage.objects.filter(draft_id=res['draft_id']).delete()
        draftChatroom.objects.filter(id=res['draft_id']).delete()
        draftPolls.objects.filter(draft=res['draft_id']).delete()

    context = {
        'collabcard':collabcard,
        'card_instance':card_instance
    }

    return context



def send_chatroom_creation_notifications_and_mails(card_instance,user_instance):

    '''function to send mail and notifications for chatroom creations'''
    send_notification_for_new_collabcard_posted.delay(card_instance.community.id, card_instance.title,
                                                      user_instance.id, user_instance.userinfo.name,
                                                      type=card_instance.type,
                                                      date_time=card_instance.end_date if card_instance.type == card_types.CARD_POLL else card_instance.date_time,
                                                      card_id=card_instance.id,
                                                      community_name=card_instance.community.name,
                                                      community_state=card_instance.community.hide_community)

    # if card_instance.type != card_types.CARD_INTRO:  # stopping mail for introduction cards
    #     send_email_for_collabcard(card_instance.community, user_instance.userinfo, card_instance, card_instance.type)

@csrf_exempt
def create_draft_collabcard(request):

    '''function to create draft collabcard'''

    member_id = get_member_id_from_headers(request)
    res = json.loads(request.body)

    community_id = res['community_id']

    community_instance = Community.objects.get(id=community_id)
    user_instance =  User.objects.get(id=member_id)

    typ = int(res['type']) if 'type' in res else card_types.CARD_NORMAL

    if 'draft_id' in res:
        draft_chatroom_filter = draftChatroom.objects.filter(id=res['draft_id'])

        if draft_chatroom_filter.exists():
            card = draft_chatroom_filter[0]

            #deleting the chatrooms
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
    card.duration = res['duration'] if ('duration' in res) else 0

    # for event card
    card.location = res['location'] if ('location' in res) else None
    card.location_lat = res['location_lat'] if ('location_lat' in res) else None
    card.location_long = res['location_long'] if ('location_long' in res) else None
    card.start_date = res['start_date'] if ('start_date' in res) else 0
    card.end_date = res['end_date'] if ('end_date' in res) else 0
    card.about = res['about'] if ('about' in res) else None
    card.co_hosts = json.dumps(res['co_hosts']) if ('co_hosts' in res) else None
    card.online_link = res['online_link'] if ('online_link' in res) else None

    # for poll card
    card.multiple_select = res['multiple_select'] if ('multiple_select' in res) else False
    card.multiple_select_no = res['multiple_select_no'] if ('multiple_select_no' in res) else 1
    card.multiple_select_state = res['multiple_select_state'] if ('multiple_select_state' in res) else 0

    # for chatroom header
    card.header = res['header'] if ('header' in res) else card.title[:30]

    if 'share_link' in res:
        card.share_link = res['share_link']
        og_tags = decode_meta_from_url(res['share_link'])
        card.og_tags = json.dumps(og_tags)

    card.date_epoch = time.time()  # card creation time
    card.save()


    #deleting the existing polls
    draftPolls.objects.filter(draft=card).delete()
    polls = res['polls'] if 'polls' in res else []
    for poll in polls:
        poll_instance = draftPolls()
        poll_instance.draft = card
        poll_instance.text = poll['text']
        poll_instance.sub_text = poll['sub_text'] if ('sub_text' in poll) else None
        poll_instance.save()



    chatroom =  draftChatroomSerializer(card,user_instance)

    engage_filter = conversationEngage.objects.filter(user=user_instance,draft=card)

    if not engage_filter.exists():
        instance = conversationEngage()
        instance.user = user_instance
        instance.draft = card
        instance.created_at = time.time()
        instance.updated_at = time.time()
        instance.save()
    else:
        engage_filter.update(updated_at=time.time())


    return JsonResponse({'success':True,"chatroom":chatroom})

def create_collabcard_state_for_user(card_instance, user_instance, state, community):
    """ create collabcard state for a member for a card """

    state_filter = collabcardState.objects.filter(card=card_instance,user=user_instance)
    if not state_filter.exists():
        collabcard_state_instance = collabcardState()
        collabcard_state_instance.card = card_instance
        collabcard_state_instance.user = user_instance
        collabcard_state_instance.community = community
        collabcard_state_instance.state = state  # user has created the card and he is autofollowing
        collabcard_state_instance.follow_status = True
        collabcard_state_instance.created_at = time.time()
        collabcard_state_instance.updated_at = time.time()
        collabcard_state_instance.save()

def create_chatroom(card_instance,user_instance,state,current_user_id=None,answer=""):

    '''function to create chat-room and perform follow unfollow operations'''
    #handling answer states
    if not answer:

        user_name = user_instance.userinfo.name
        member_ids = [user_instance.id]
        community_profile = get_members_profile(member_ids, card_instance.community.id, current_user_id)
        if community_profile:
            community_profile = community_profile[0]
            user_route = "route://member_profile/" + str(user_instance.id) + "?member=" + quote(str(community_profile))
        else:
            user_route = "route://member_profile/" + str(user_instance.id)
        user_name = "<<" + user_name + "|" + user_route + "&community_id=" + str(card_instance.community.id) + ">>"

        if state == chatroom_states.CHATROOM_HEADER:

            community = CommunitySerializer(card_instance.community)
            community_route = "route://community?community_id="+str(community['id'])
            community_name = "<<"+str(community['name'])+"|"+community_route+">>"
            answer = user_name + " started this chatroom in " + community_name
        elif state == chatroom_states.CHATROOM_FOLLOW:
            answer = user_name + " followed this chatroom"
        elif state == chatroom_states.CHATROOM_UNFOLLOW:
            answer = user_name + " unfollwed this chatroom"
        elif state == chatroom_states.CHATROOM_PURPOSE_EDIT:
            answer = user_name + " edited community purpose"


    instance = card_answers()
    instance.answer = answer
    instance.card = card_instance
    instance.user = user_instance
    instance.state = state
    instance.created_at = time.time()
    instance.save()


def create_chatroom_engagement(card_instance,user_instance,last_conversation=None,unseen_count=0):

    '''function to create and update chatroom engagements '''
    print("hit")
    instance_list = conversationEngage.objects.filter(card=card_instance,user=user_instance)

    if not instance_list.exists():
        instance = conversationEngage()
        instance.card = card_instance
        instance.user = user_instance
        instance.last_conversation = last_conversation
        instance.unseen_count = unseen_count
        instance.created_at = time.time()
        instance.updated_at = time.time()
        instance.save()
    else:
        instance = instance_list[0]
        instance_list.last_conversation = last_conversation
        instance_list.unseen_count = unseen_count
        instance.updated_at = time.time()
        instance.save()


def update_seen_status_for_new_user_in_chatroom(community_instance,user_instance):

    collabcard_filter = Collabcard.objects.filter(community=community_instance).order_by('id')

    for card_instance in collabcard_filter:

        state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)
        if not state_filter.exists():
            collabcard_state_instance = collabcardState()
            collabcard_state_instance.card = card_instance
            collabcard_state_instance.community = community_instance
            collabcard_state_instance.user = user_instance
            collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_SEEN
            collabcard_state_instance.created_at = time.time()
            collabcard_state_instance.updated_at = time.time()
            collabcard_state_instance.save()

    update_last_unseen_in_engage(user=user_instance, community=community_instance,is_seen=False)

    print("updating the seen status")





@csrf_exempt
def chatroom_mute(request):

    '''function to mute and unmute chatroom'''
    chatroom_id = request.POST.get('chatroom_id')

    if not chatroom_id:
        context = get_error_context(False,"send chatroom id as post parameters")
        return JsonResponse(context)

    member_id = get_member_id_from_headers(request)
    if not member_id:
        context = get_error_context(False,"send member id in headers")
        return JsonResponse(context)

    value = request.POST.get('value',False)

    if value == "true":
        collabcardState.objects.filter(card_id=chatroom_id,user=member_id).update(mute_status=True)
    else:
        collabcardState.objects.filter(card_id=chatroom_id, user=member_id).update(mute_status=False)

    return JsonResponse({'success':True})


@csrf_exempt
def chatroom_rename(request):

    chatroom_id = request.POST.get('chatroom_id')
    first_time_rename = request.POST.get('first_time_rename')

    member_id = get_member_id_from_headers(request)

    if not chatroom_id or not member_id:
        context = get_error_context(False,"send params correctly")
        return JsonResponse(context)

    chatroom_name = request.POST.get("header",None)

    collabcard_filter = Collabcard.objects.filter(id=chatroom_id)
    if collabcard_filter.exists():
        collabcard_filter.update(header=chatroom_name)

        if first_time_rename == "true":
            collabcard_filter.update(has_been_named=True)
            card_instance = collabcard_filter[0]
            user_instance = User.objects.get(id=member_id)

            send_chatroom_creation_notifications_and_mails(card_instance,user_instance)

    else:
        context = get_error_context(False, "send correct chatroom id in post params")
        return JsonResponse(context)


    return JsonResponse({"success":True})






@csrf_exempt
def chatroom_delete(request):

    '''api to delete the chatroom '''

    member_id = get_member_id_from_headers(request)
    chatroom_id = request.POST.get('chatroom_id',None)

    draft_id = request.POST.get('draft_id')

    if draft_id:
        draftChatroom.objects.filter(id=draft_id).delete()
        return JsonResponse({'success':True})

    if not chatroom_id:
        context = get_error_context(False,"send the chatroom_id in post params")
        return JsonResponse(context)

    try:
        collabcard_instance = Collabcard.objects.get(id=chatroom_id)
        community_id = collabcard_instance.community.id
        if collabcard_instance.user.id != int(member_id):
            context = get_error_context(False,"You are not the card creator you cannot delete this chatroom")
            return JsonResponse(context)

        create_chatroom_delete_backup(collabcard_instance)

        delete_status=Collabcard.objects.filter(id=chatroom_id).delete()
        info_logger.info(delete_status)
        update_last_unseen_in_engage_on_card_creation.delay(community_id)

    except Exception as e:

        context = get_error_context(False,str(e))
        return JsonResponse(context)



    return JsonResponse({'success':True})


def create_chatroom_delete_backup(card_instance):

    deleted_filter = deletedChatrooms.objects.filter(card_id=card_instance.id)

    if deleted_filter.exists():
        return
    card = deletedChatrooms()
    card.title = card_instance.title
    card.community = card_instance.community
    card.user = card_instance.user
    card.type = card_instance.type
    card.image_count = card_instance.image_count
    card.pdf_count = card_instance.pdf_count
    card.date_time = card_instance.date_time
    card.duration = card_instance.duration

    # for event card
    card.location = card_instance.location
    card.location_lat = card_instance.location_lat
    card.location_long = card_instance.location_long
    card.start_date = card_instance.start_date
    card.end_date = card_instance.end_date
    card.about = card_instance.about
    card.co_hosts = card_instance.co_hosts
    card.online_link = card_instance.online_link

    # for poll card
    card.multiple_select = card_instance.multiple_select
    card.multiple_select_no = card_instance.multiple_select_no
    card.multiple_select_state = card_instance.multiple_select_state

    # for chatroom header
    card.header = card_instance.header


    card.share_link =card_instance.share_link
    card.og_tags = card_instance.og_tags

    card.date_epoch = time.time()  # card creation time
    card.card_id = card_instance.id
    card.save()



#api to deprecate
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
            context = get_error_context(success=False,error_message="Send the correct collabcard id")
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


        #deleting the previous votes
        memberpolls_filter = MemberPollVotes.objects.filter(card=card_instance, user=user_instance)
        memberpolls_filter.delete()


        for poll_id in poll_ids:
            vote_poll(poll_id,card_instance,user_instance,collabcard_id)

        # if not str(member_id) == str(card_instance.user.id):
        #     send_poll_or_event_notification.delay(card_id=collabcard_id, user_id=member_id)


        #autofollowing the collabcard
        function_dict = {
            'member_id': user_instance.id,
            'collabcard_id': card_instance.id,
            'status': True
        }
        collabcard_follow_internal(function_dict)
        return JsonResponse({"success": True})

    return JsonResponse({"success": False})


def vote_poll(poll_id,card_instance,user_instance,collabcard_id):

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
    response={}

    response['online_event'] = {
        'header':"Guidelines for online event url",
        'sub_header':"Use the following guidelines to best use the online event url:",

        'title_1':"What are online events",
        'sub_title_1':"Online events are the events that can be performed via web video conferencing tools. There are plenty of video conferencing tools out there like Zoom, Hangout, Skype etc.",

        'title_2':"Recommended online platforms",
        'sub_title_2':"Recommended tools are those where joining the conference is easier and can handle the number of expected participants joining your event online.",

        'title_3':"Link to online event",
        'sub_title_3':"Make sure that you provide the video conferencing urls and not the event description page from other platforms."
    }


    response['event_privacy'] = {

        'header':"Event Privacy",
        'sub_header':"An event can either be a private or a public event.",

        'title_1':"Private Event",
        'sub_title_1':"Only verified community mambers can see all the details. A non-member trying to access the event information would have to join the community first.",

        'title_2':"Public Event",
        'sub_title_2':"Anyone with the link can see this event. Attending Member’s details would be available only to the users who join the community.",

    }

    response['banner'] = {
        'header':"Guidelines for image files",
        'sub_header':"Use the following guidelines to get the highest quality event image:",

        'title_1':"Dimensions",
        'sub_title_1':"Find at least a 2160 x 1080px (2:1 ratio) image.",

        'title_2':"File Type",
        'sub_title_2':"Pictures with file types JPEG, BMP, PNG, or GIF work best.",

        'title_3' : "File Size",
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

        nominated_admin = res['nominate_member_ids']

        if len(nominated_admin) > 0:
            nominated_admin = nominated_admin[0]

        member_filter = Members.objects.filter(member_id=nominated_admin,community_id=community_id)

        engage_filter = Member_Engage.objects.filter(member_id=nominated_admin,community_id=community_id)

        info_logger.info(res)

        update_status_member = member_filter.update(state=member_states.ADMIN)

        update_status_engage = engage_filter.update(member_state=member_states.ADMIN)

        info_logger.info(update_status_member)

        send_notification_to_new_promoter.delay({'nominated_admin':nominated_admin,'community_id':community_id})

        info_logger.info("----------------add admin api end --------------\n")


    except Exception as e:

        return JsonResponse({'error':e})


    return JsonResponse({'success':True})




def check_member(email, community_id, member_id, nominated_member_name,community_instance):
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
            send_email_to_nominated_admin.delay(NominatedAdmin=nominated_member_name, email=email, ProposedAdmin=ProposedAdmin,
                                                proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                                community_id=community.id)
            return False
    except:
        """ if any error trying fetch the user details , then user is not registered , send an email"""
        send_email_to_nominated_admin.delay(NominatedAdmin=nominated_member_name, email=email, ProposedAdmin=ProposedAdmin,
                                            proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                            community_id=community.id)
        return False

    if user:
        # get the state of the user of the community he is proposed to become a promoter for
        member = Members.objects.filter(community_id=community, member_id=user[0].user_id.id)

        if member and member[0].state == 4:
            # if the user is already a member , give him state 7
            # state 7 is nominted promoter who is already a member of thet community
            Members.objects.filter(community_id=community, member_id=user[0].user_id.id).update(state=member_states.KNOWN_NOMINATED_PROMOTER)
            Member_Engage.objects.filter(community_id=community,member_id=user[0].user_id.id).update(
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



def get_pending_members_of_community(community_id,requested_member_id):

    '''functions to get pending members of the community'''


    info_logger.info("PENDING MEMBERS COUNT CHECK")
    info_logger.info(community_id)
    member_id=requested_member_id
    community = Community.objects.get(id=community_id)
    pend_requests = Members.objects.filter(community_id=community).filter(state=3)

    is_admin = False
    is_member_admin = Members.objects.filter(community_id=community, member_id=member_id, state=1)
    if is_member_admin.exists():
        is_admin = True
    info_logger.info(is_admin)

    is_verified = False
    is_verified_member = Members.objects.filter(community_id=community, member_id=member_id).filter(
        Q(state=1) | Q(state=4))
    if is_verified_member.exists():
        is_verified = True
    pending_requests = []
    is_lg = is_LG_or_LP_community(community)

    for i in pend_requests:
        if is_lg and is_verified:
            if str(i.ask_member_id) == str(member_id):
                # resp = communityAnswers.objects.filter(community=community_id).filter(member=i.member_id.id).order_by('id')
                user = Userinfo.objects.get(user_id=i.member_id.id)
                # serilaizing userinfo object
                usr = UserinfoSerializer(user)
                # user_response = []
                # for j in resp:
                #     # getting the answers of the users who requested to join
                #     # for the questions that have been asked while requestiong to join in a community
                #     response_object = {}
                #     response_object['key'] = j.question_title
                #     response_object['value'] = j.question_answer
                #     user_response.append(response_object)
                response = FormResponseSerilaizer(community_id, i.member_id.id,bl=True,current_user_id=requested_member_id)
                if response:
                    usr['response'] = response[0]
                    usr['question_answers'] = response[1]
                pending_requests.append(usr)
        elif is_admin:
            # resp = communityAnswers.objects.filter(community=community_id).filter(member=i.member_id.id).order_by('id')
            user = Userinfo.objects.get(user_id=i.member_id.id)
            # serilaizing userinfo object
            usr = UserinfoSerializer(user)
            # user_response = []
            # for j in resp:
            #     # getting the answers of the users who requested to join
            #     # for the questions that have been asked while requestiong to join in a community
            #     response_object = {}
            #     response_object['key'] = j.question_title
            #     response_object['value'] = j.question_answer
            #     user_response.append(response_object)
            response = FormResponseSerilaizer(community_id, i.member_id.id, bl=True,current_user_id=requested_member_id)
            if response:
                usr['response'] = response[0]
                usr['question_answers'] = response[1]
            pending_requests.append(usr)

    info_logger.info("PENDING MEMBER REQUEST")

    info_logger.info(pending_requests)
    info_logger.info("\n\n")
    return pending_requests


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
                Members.objects.filter(member_id=member_id, community_id=community).update(state=9)
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
                    Members.objects.filter(member_id=member_id, community_id=community).update(state=9)

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
                    unseen_count = Collabcard.objects.filter(community=community).count()

                    engage = Member_Engage()
                    engage.member_id = nom_admin[0].user_id
                    engage.community_id = community
                    engage.last_unseen_conversation = purpose_card
                    engage.last_unseen_count = unseen_count
                    engage.updated_at = time.time()
                    engage.pending_members = pending_members
                    engage.save()
                    Members.objects.filter(community_id=community, member_id=member_id).update(created_at=time.time())

        if len(promoter) == 1:
            # if the community has only one promoter
            prop_admin = Userinfo.objects.get(user_id=promoter[0].member_id.id)
            # if the promoter is actually a promoter
            if promoter[0].state == 1:
                Members.objects.filter(community_id=community, member_id=member_id).update(state=1)
                Member_Engage.objects.filter(community_id=community, member_id=member_id).update(member_state=1)
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
    update_pending_member_count_in_engage(req_dict['community_id'])
    return  JsonResponse({'success': True})




def approve_or_decline_lg_community(request,req_dict,member_verification):

    '''function to approve and decline request in lg community'''

    if req_dict:


        community_id = req_dict['community_id']
        member_id = req_dict['member_id']
        community = Community.objects.get(id=community_id)
        user=User.objects.get(id=member_id)

        if req_dict['accepted']:

            #if the request is accepted from dashboard


            join_time=time.time()
            Members.objects.filter(member_id=member_id, community_id=community).update(state=member_states.MEMBER,
                                                                                       created_at=join_time)  # aprove state = 4

            pending_members = get_pending_members_of_community(community_id,member_id)
            pending_members_count = len(pending_members)

            update_status = Member_Engage.objects.filter(member_id=member_id,community_id=community).update(
                member_state=member_states.MEMBER,updated_at=time.time(),member_referral="",pending_members=pending_members_count)
            #info_logger.info("update_status",update_status)



            #creating a collabcard
            # introduction_question, introduction_answer = auto_create_collabcard(user, community)
            # print(introduction_answer)
            # req_dict = {
            #
            #     'member_id': member_id,
            #     'community_id': community_id,
            #     'title': introduction_answer,
            #     'type': 1,
            #     'create_intro': 1
            # }
            #
            # request.method="POST"
            # create_card(request,req_dict=req_dict)
            #(community.id,member_id,request)
            # saving the referal detail and sending notifications for refered members
            post_introduction_card_for_community(community_id,member_id,request)

            community.updated_at = time.time()
            community.members_count = community.members_count + 1
            community.save()
            is_live=False
            if community.hide_community == '4':
                is_live=True

            if community.members_count == ig_members_count:
                community.hide_community = '4'
                # send_notification_for_tool_unlocked_for_pilot.delay(community_id=community_id)
                community.save()

            send_notification_for_join_requests.delay(community_id, True, member_id)

            update_last_unseen_in_engage(user=user,community=community)

            #deleting the data from collabcard temp
            member_instance=Members.objects.get(member_id=user,community_id=community)

            #getting pending members who was refered by me
            # pending_members=get_pending_members_of_community(community.id,requested_member_id=member_id)
            # info_logger.info("\n")
            # info_logger.info(pending_members)
            # check=Member_Engage.objects.filter(member_id=user,community_id=community).update(pending_members=len(pending_members),
            #                                                                                  member_referral="")
            # info_logger.info(check)

            if member_instance.ask_member_id:
                collabcardTemp.objects.filter(member=member_instance.ask_member_id, community=community,show_member=user).delete()

            collabcardTemp.objects.filter(member=member_id,community=community).delete()

            if member_verification:
                header_member_id=get_member_id_from_headers(request)
                Members.objects.filter(member_id=member_id, community_id=community).update(approved_member_id=header_member_id)

                pending_members = len(get_pending_members_of_community(community.id, header_member_id))
                print("pending members",pending_members)
                update_status = Member_Engage.objects.filter(member_id=header_member_id, community_id=community).update(
                    pending_members=pending_members,member_referral="")

                print("update_status---",update_status)


                #info_logger.info("update_status",update_status)

                # making the referer promoter if his referal count becomes equal to eligibility count
                header_member_instance=User.objects.get(id=header_member_id)
                referal_instance=Referal(community=community,invited_member=user,member=header_member_instance)
                referal_instance.save()

                referal_list = Referal.objects.filter(member=header_member_instance, community=community)

                if referal_list.exists():

                    referer_instance = referal_list[0].member
                    referal_list = get_referred_members_of_a_member(community_id=community_id,
                                                                    member_id=referer_instance.id)
                    total_referal_count = len(referal_list)

                    if total_referal_count == eligibility_count:
                        admin = Members.objects.filter(community_id=community, member_id=referer_instance)

                        if admin.exists():
                            Members.objects.filter(community_id=community, member_id=referer_instance).update(
                                state=member_states.ADMIN)
                            Member_Engage.objects.filter(member_id=member_id, community_id=community).update(
                                    member_state=member_states.ADMIN)
                    # if is_live:
                    #     send_notification_for_tool_unlocked_for_live_community.delay(referer_id=header_member_id,
                    #                                                                  referal_count=total_referal_count,
                    #                                                                  community_id=community.id,
                    #                                                                  community_name=community.name,
                    #                                                                  community_state=community.hide_community)


        else:
            # change user state to 5
            Members.objects.filter(member_id=member_id, community_id=community).delete() # decline state = 5
            # delete the member engage table record for the user
            Member_Engage.objects.filter(member_id=member_id, community_id=community).delete()
            # delete the responses of user to community questions, if any
            communityAnswers.objects.filter(member=member_id, community=community_id).delete()
            collabcardTemp.objects.filter(member=member_id, community=community).delete()
            if member_verification:
                header_member_id = get_member_id_from_headers(request)
                pending_members = len(get_pending_members_of_community(community.id,header_member_id))
                Member_Engage.objects.filter(member_id=header_member_id, community_id=community).update(
                    pending_members=pending_members)
                Referal.objects.filter(member=header_member_id, community=community).delete()
            send_notification_for_join_requests.delay(community_id, False, member_id)


def approve_or_decline_whatsapp_community(req_dict,request):

    '''function to approve the whatsapp community'''

    if req_dict['accepted'] or req_dict['accepted'] == 'true':

        is_member = is_member_verified(community=req_dict['community_id'], user_instance=req_dict['member_id'])
        
        promoter_name = request.member.userinfo.name
        
        if not is_member:
            Members.objects.filter(member_id=req_dict['member_id'],
                                   community_id=req_dict['community_id']).update(state=member_states.MEMBER,
                                                                                 created_at=time.time())

            Member_Engage.objects.filter(member_id=req_dict['member_id'],
                                         community_id=req_dict['community_id']).update(member_state=member_states.MEMBER,
                                                                                       updated_at=time.time(),click_state=click_states.DEFAULT)

            # updating pending member count
            community = Community.objects.get(id=req_dict['community_id'])
            members_count = community.members_count + 1
            Community.objects.filter(id=req_dict['community_id']).update(members_count=members_count)

            # setting the follow state for purpose collabcard
            set_state_for_onboarding_chatroom(community_instance=community, user_id=req_dict['member_id'],request=request)


            # posting a intro collabcard
            post_introduction_card_for_community(req_dict['community_id'], req_dict['member_id'], request)

            # saving create community action step 4
            update_community_actions(community_instance=community)

            #sending mails and notifications

            #send notification
            send_notification_for_join_requests.delay(req_dict['community_id'], True, req_dict['member_id'],promoter_name)

            # sending email to the user that his request is accepted for this community
            member_request_approval_or_denied.delay(user_id = req_dict['member_id'],community_id = req_dict['community_id'], approved = True)

    else:

        Members.objects.filter(member_id=req_dict['member_id'], community_id=req_dict['community_id']).delete()

            # delete the member engage table record for the user
        Member_Engage.objects.filter(member_id=req_dict['member_id'],community_id = req_dict['community_id']).delete()

        # delete the responses of user to community questions, if any
        communityAnswers.objects.filter(member_id=req_dict['member_id'],community_id = req_dict['community_id']).delete()

        send_notification_for_join_requests.delay(req_dict['community_id'], False, req_dict['member_id'],promoter_name)


def approve_or_decline_private_community(req_dict,request):

    '''function to approve the whatsapp community'''

    if req_dict['accepted'] or req_dict['accepted'] == 'true':

        is_member = is_member_verified(community=req_dict['community_id'], user_instance=req_dict['member_id'])

        if not is_member:
            Members.objects.filter(member_id=req_dict['member_id'],
                                   community_id=req_dict['community_id']).update(state=member_states.MEMBER,
                                                                                 created_at=time.time())

            Member_Engage.objects.filter(member_id=req_dict['member_id'],
                                         community_id=req_dict['community_id']).update(member_state=member_states.MEMBER,
                                                                                       updated_at=time.time(),click_state = click_states.DEFAULT)


            # updating pending member count
            community = Community.objects.get(id=req_dict['community_id'])
            members_count = community.members_count + 1
            Community.objects.filter(id=req_dict['community_id']).update(members_count=members_count)

            # setting the follow state for purpose collabcard
            set_state_for_onboarding_chatroom(community_instance=community, user_id=req_dict['member_id'],request=request)


            # posting a intro collabcard
            post_introduction_card_for_community(req_dict['community_id'], req_dict['member_id'], request)

            #removing guest status from all chatrooms after access
            collabcardState.objects.filter(community=req_dict['community_id'],user=req_dict['member_id']).update(is_guest=False)

            # saving create community action step 4
            update_community_actions(community_instance=community)

            #sending mails and notifications

            #send notification
            send_notification_for_join_requests.delay(req_dict['community_id'], True, req_dict['member_id'])

            # sending email to the user that his request is accepted for this community
            member_request_approval_or_denied.delay(user_id = req_dict['member_id'],community_id = req_dict['community_id'], approved = True)

    else:

        Members.objects.filter(member_id=req_dict['member_id'], community_id=req_dict['community_id']).delete()

            # delete the member engage table record for the user
        Member_Engage.objects.filter(member_id=req_dict['member_id'],community_id = req_dict['community_id']).delete()

        # delete the responses of user to community questions, if any
        communityAnswers.objects.filter(member_id=req_dict['member_id'],community_id = req_dict['community_id']).delete()

        send_notification_for_join_requests.delay(req_dict['community_id'], False, req_dict['member_id'])


def set_state_for_onboarding_chatroom(community_instance,user_id,request):

    '''function to autofollow onboarding chatroom'''
    onboarding_chatroom_instance = Collabcard.objects.filter(community=community_instance,type=card_types.CARD_PURPOSE)
    print("onboarding--",onboarding_chatroom_instance)
    if onboarding_chatroom_instance.exists():
        instance = onboarding_chatroom_instance[0]
        function_dict = {
            'collabcard_id': instance.id,
            'member_id': user_id,
            'status': True
        }
        collabcard_follow_internal(function_dict)
        print("onboarding state set for user")


############# functions for  collabcard flow   ##########################


def send_email_for_collabcard(community, user, card, type):
    '''function to make the format of email to send when a new collabcard is posted'''

    members = Members.objects.filter(community_id=community)

    for member in members:
        if not user.image_link:
            collabcard_card_image = url + user.image_file.url
        else:
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
    if card_filter.exists():
        card_instance = card_filter[0]
    else:

        backup_filter = deletedChatrooms.objects.filter(card_id=card_id)

        if backup_filter.exists():
            community_id = backup_filter[0].community.id
            return redirect("community_questions",params=str(community_id)+"+deleted")
        else:
            return render(request,"__404__.html",{})

    card['type'] = card_instance.type
    if card_instance.type == card_types.CARD_EVENT or card_instance.type == card_types.CARD_PUBLIC_EVENT or card_instance.type == card_types.CARD_POLL:
        page = request.GET.get('page', 1)

        current_user_id = get_member_id_from_headers(request)

        feedback=True
        if card_instance.community.id == feedback_community_id:
            feedback = False

        # coverting current time into epoch time for getting time stamp of answers and card

        answer_id = request.GET.get('answer_id', '')
        user_id = request.GET.get('member_id', '')

        if is_request_web(request) and request.user.is_authenticated:
            current_user_id = request.user.id

            answers = get_chatroom_internal(request,card_instance,current_user_id,page,'','')
        else :
            # get all the answers of the card
            answer = card_answers.objects.filter(card=card_instance).order_by('id')
            answer=pagination(answer,page,paginate_by=3)
            if answer_id:
                answer_id = int(answer_id)
                answer = card_answers.objects.filter(card=card_instance, id__gte=answer_id).filter(~Q(user__id=user_id))
                # answer = pagination(answer, page, paginate_by=10)
                answers = get_answer_data(answer,card_instance.community.id,current_user_id=current_user_id)         #if the feedback is true don't send id in userinfo
                return JsonResponse({'answers': answers})
            else:
                answers = get_answer_data(answer,card_instance.community.id,current_user_id=current_user_id)


        # serializing Collabcard

        if not user_id:
            #handling the web case
            if request.user.is_authenticated and is_request_web(request):
                user_id=request.user.id
                user_instance = User.objects.get(id=user_id)

        card = CollabcardSerializer(card_instance, user_id, card_instance.community)

        user = Userinfo.objects.get(user_id=card_instance.user.id)

        # if request.user.is_authenticated and not get_request_type(request):
        #     # set current user if user in logged in
        #     current_user = User.objects.get(user_id=current_user_id)

        # serializing user object
        usr = UserinfoSerializer(user)
        usr['is_clickable']=feedback

        #when the member is removed
        removed_state = removedMembersSerializer(card_instance.community.id,usr['id'])
        if removed_state != False:
            usr['remove_state'] = removed_state

        # user form response serialzer
        form_response = FormResponseSerilaizer(card_instance.community.id, card_instance.user.id,bl=True,current_user_id=current_user_id)
        if form_response:
            #usr['response'] = form_response[0]
            usr['question_answers'] =form_response[1]
        # get the card image if any
        files = get_collabcard_files(card_id)
        card['images'] = files[0]
        card['member'] = usr
        card['pdf'] = files[1]
        if user_id:
            collabcard_status = get_status_of_collabcard(member_id=user_id, card=card_instance)
            card['state'] = collabcard_status['state']
            card['mute_status'] = collabcard_status['mute_status']
            card['follow_status'] = collabcard_status['follow_status']


        # get tine stamp for card
        time_text = get_time_text(card_instance.date_epoch)
        card['created_at'] = time_text


    #request is made from web
    if request.accepted_renderer.format == 'html':

        web_data = get_collabcard_details_for_web(request,card_instance,card,current_user_id,answers)

        context = web_data[0]
        card_category = web_data[1]

        mixpanel_events = get_event_super_properties_for_mixpanel(user_instance,card_instance.community)

        if mixpanel_events:
            context['mixpanel_event'] = mixpanel_events


        if card_category == "EVENT_CARD":
            return render(request, 'event.html', context)

        if card_category == "POLL_CARD":
            return render(request, 'poll.html', context)

        return render(request, 'chatroom.html', context)

    else:
        return JsonResponse({"collabcard": card, 'answers': answers})



def get_collabcard_details_for_web(request,card_instance,card,current_user_id,answers):

    '''function that contain collabcard details for web'''
    is_logged = False
    current_user = {}

    if request.user.is_authenticated and is_request_web(request):
        # user id from request if user in logged in
        current_user_id = request.user.id
        current_user_instance = Userinfo.objects.get(user_id=current_user_id)
        current_user = UserinfoSerializer(user=current_user_instance)

        collabcard_status = get_status_of_collabcard(member_id=current_user_id, card=card_instance)
        current_user['collabcard_state'] = collabcard_status['state']
        current_user['mute_status'] = collabcard_status['mute_status']
        current_user['follow_status'] = collabcard_status['follow_status']
        is_logged = True

    if type(answers) is list:
        _answers = answers
        answers = {}
        answers['conversations'] = _answers

    #print('in html')
    # check for event card
    # type 2 => private
    # type 6 => public
    if card['type'] in (card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT):
        #print('event card')

        # get community for community name, image, etc
        community = card_instance.community

        member_state = members_state(request,
                                     req_dict={'community_id': card_instance.community.id, 'member_id': current_user_id})

        # set default event banner image
        card['banner_image'] = "https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fmain_website%2Fevent_banner.jpg?alt=media&token=4f6709df-8918-4227-8606-c11607d2d31b"
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
        card['duration'] = card['duration']/1000.0
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
            'facebook_auth_id':settings.SOCIAL_AUTH_FACEBOOK_KEY,
            'firebase_config': settings.FIREBASE_CONFIG
        }

        if is_logged:
            if current_user['collabcard_state'] == 0:
                collabcards_seen_internal(card_instance.community.id, card_instance.id, card['type'], current_user_id)
            context["current_user"] = current_user



        context['redirect_link'] = "/community_questions/"+ str(community.id) + "?event="+ str(card_instance.id) + "&type="+ str(card['type'])



        # print(context)

        return context,"EVENT_CARD"
        #return render(request, 'event.html', context)
    elif card['type'] == card_types.CARD_POLL:
        # print('poll card')

        # get community for community name, image, etc
        community = card_instance.community

        member_state = members_state(request,
                                     req_dict={'community_id': card_instance.community.id, 'member_id': current_user_id})

        if card['polls_count'] > 0:
            card['polls_count_percentage'] = card['polls_count']/100



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
            #"members": members,
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


        context['redirect_link'] = "/community_questions/"+ str(community.id) + "?poll="+ str(card_instance.id)




        #print(context['collabcard']['polls'])
        return context,"POLL_CARD"
    else:
        print('collab card')

        context = get_normal_chatroom_context(request,card_instance)
        return context, "SIMPLE_CARD"
        #return render(request, 'collabcard.html', context)



def get_normal_chatroom_context(request,card_instance):


    is_logged = False
    current_user = None
    current_user_id  = None
    page = request.GET.get('page',1)
    community_instance = card_instance.community

    aj = request.GET.get('aj')
    source_id = request.GET.get('source_id')

    if is_request_web(request) and request.user.is_authenticated:

        is_logged = True
        current_user_id = request.user.id
        current_user_instance = Userinfo.objects.get(user_id=current_user_id)
        current_user = UserinfoSerializer(user=current_user_instance)
        collabcard_status = get_status_of_collabcard(member_id=current_user_id, card=card_instance)
        current_user['collabcard_state'] = collabcard_status['state']
        current_user['mute_status'] = collabcard_status['mute_status']
        current_user['follow_status'] = collabcard_status['follow_status']


    chatroom_dict = get_chatroom_internal(request, card_instance, current_user_id, page, conversation_id=None,
                                     scroll_direction=None)


    has_conversation = card_answers.objects.filter(card=card_instance,user=current_user_id,state=chatroom_states.ANSWER).exists()


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
        'member_state' : member_state,
        'community_block':communityBlock,
        'aj': aj,
        'source_id': source_id,
        'has_conversation':has_conversation
    }

    if aj and source_id:
        context['redirect_link'] = "/collabcard/"+str(card_instance.id)+"?aj="+str(aj)+"&source_id="+str(source_id)
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

    n=int(n)

    day = n // (24 * 3600)

    n = n % (24 * 3600)
    hour = n // 3600

    n %= 3600
    minutes = n // 60

    n %= 60
    seconds = n
    time_text = ""

    #checking day
    if day !=0:
        if day == 1:
            time_text = str(day)+" day "
        else:
            time_text = str(day) + " days "

    if hour != 0:
        if hour == 1:
            time_text = time_text + str(hour) + " hour "
        else:
            time_text = time_text + str(hour) + " hours "



    if minutes != 0:
        if minutes == 1:
            time_text = time_text+ "and " + str(minutes) + " minute "
        else:
            time_text = time_text +  "and " + str(minutes) + " minutes "


    if hour == 0 and minutes != 0:

        if minutes == 1:
            time_text =  str(minutes) + " minute "
        else:
            time_text = str(minutes) + " minutes "

    if hour == 0 and minutes == 0:
        time_text = str(seconds)+" seconds"

    return time_text


@api_view(['GET', 'POST'])
@renderer_classes([JSONRenderer, TemplateHTMLRenderer])
def fetch_chatroom(request):

    '''api to get the chatroom'''

    card_id = request.GET.get('chatroom_id','')
    community_id = None
    if not card_id:
        context = get_error_context(False,"send chat_room_id as a get params")
        return JsonResponse(context)

    conversation_id = request.GET.get('conversation_id')
    scroll_direction = request.GET.get('scroll_direction')



    card_filter = Collabcard.objects.filter(id=card_id)

    if card_filter.exists():
        card_instance = card_filter[0]
    else:
        context={}
        backup_filter = deletedChatrooms.objects.filter(card_id=card_id)

        if backup_filter.exists():
            community_id = backup_filter[0].community.id
        if community_id:
            context['community_id'] = community_id
        return JsonResponse(context)

    page = request.GET.get('page',1)
    current_user_id = get_member_id_from_headers(request)
    current_user = None
    if is_request_web(request) and request.user.is_authenticated:
        current_user_id = request.user.id
        current_user_instance = Userinfo.objects.get(user_id=current_user_id)
        current_user = UserinfoSerializer(user=current_user_instance)

    context = get_chatroom_internal(request,card_instance,current_user_id,page,conversation_id,scroll_direction)


    if str(current_user_id) == str(card_instance.user.id):
        notification_flag = memberNotificationFlag.objects.get(code='mail_card_owner_inactivity',card=card_instance,member_id=current_user_id)
        notification_flag.flag=True
        notification_flag.save()

    if request.accepted_renderer.format == 'html' and conversation_id:
        context['conversations'] = context['conversations']
        context = {
            'answers': context,
            'current_user': current_user
        }
        return render(request, 'components/chat_bubbles.html', context)

    return JsonResponse(context)


def conversation_meta(request):

    '''api to perfrom firebase operations on conversation for real time messaging'''

    conversation_id = request.GET.get('conversation_id')
    chatroom_id = request.GET.get('chatroom_id')
    if not conversation_id or not chatroom_id:
        context = get_error_context(False,"send conversation_id and chatroom_id in post params")
        return JsonResponse(context)

    user_id = get_member_id_from_headers(request)
    if not user_id:
        context = get_error_context(False,"send member_id in headers")
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

    return JsonResponse(context)


@csrf_exempt
def conversation_seen(request,req_dict=None):

    '''api to save conversation id for user'''

    if not req_dict:
        conversation_id = request.POST.get('conversation_id')
        member_id = get_member_id_from_headers(request)
    else:
        conversation_id = req_dict['conversation_id']
        member_id = req_dict['member_id']

    if not conversation_id or not member_id:
        context = get_error_context(False,"send conversation id and member id in headers")
        return context

    try:
        user_instance = User.objects.get(id=member_id)
        conversation_instance = card_answers.objects.get(id=conversation_id)
        card_instance = conversation_instance.card
        conversation_member_filter = conversationMemberState.objects.filter(user=user_instance,card=card_instance)

        #resetting flag when card owner sees the conversation
        if member_id == card_instance.user.id:
            notification_flag = memberNotificationFlag.objects.get(code='mail_card_owner_inactivity',card=card_instance,member=user_instance)

        if not conversation_member_filter.exists():
            conversation_member_instance = conversationMemberState()
            conversation_member_instance.card = card_instance
            conversation_member_instance.conversation = conversation_instance
            conversation_member_instance.user = user_instance
            conversation_member_instance.save()
        else:
            conversation_member_filter.update(conversation=conversation_instance,updated_at=time.time())
    except Exception as e:
        print(e)
        context = get_error_context(False,"send the member id in headers or conversation does'nt exists")
        return JsonResponse(context)

    update_my_chatrooms_for_users(conversation_instance.card.id,member_id)
    return JsonResponse({'success':True})



def get_answer_data(answer_filter,community_id,current_user_id,last_seen=None):
    '''function to get answer for a particular collabcard '''

    answers = []
    for ans in answer_filter:
        user = Userinfo.objects.filter(user_id=ans.user.id)
        usr = UserinfoSerializer(user[0])
        #usr['is_clickable']=feedback

        removed_state = removedMembersSerializer(community_id, usr['id'])

        if removed_state != False:
            usr['remove_state'] = removed_state

        form_response = FormResponseSerilaizer(community_id, ans.user.id,bl=True,current_user_id=current_user_id)
        if form_response:
            #usr['response'] = form_response[0]
            usr['question_answers'] = form_response[1]
        # coverting current time into epoch time

        #time_text = get_time_text(ans.created_at)
        time_text = time.strftime('%H:%M', time.localtime(ans.created_at))

        date = time.strftime('%d %b %Y', time.localtime(ans.created_at))
        attachements = get_answer_files(ans.id)

        context = {
              'id': ans.id,
              'answer': ans.answer,
              'created_at': time_text,
              'member': usr,
              'images': attachements['image'],
              'pdf': attachements['pdf'],
              'date': date,
              'state': ans.state,
        }

        if ans.og_tags:
            context['og_tags'] = json.loads(ans.og_tags)

        if last_seen and last_seen.id == ans.id:
            context['last_seen'] = True

        if 'location' in attachements:
            context['location'] = attachements['location']

        context['answer_bubble'] = get_answer_bubble_context_for_web(ans)



        answers.append(context)
    return answers


def get_answer_bubble_context_for_web(ans):

    '''function to get answer bubble context'''
    answer_bubble=""
    if ans.state == chatroom_states.CHATROOM_GUEST:

        ans = re.findall("""\<<.*?\|""",ans.answer,re.DOTALL)
        user_list = []
        for user in ans:

            user = user.replace("<<","")
            user = user.replace("|","")
            user_list.append(user)

        if len(user_list) == 2:
            answer_bubble = user_list[0] + " joined via a "+ user_list[1]+"'s invite"

    elif ans.state == chatroom_states.CHATROOM_FOLLOW:
        answer_bubble = str(ans.user.userinfo.name) +  " follwed this chatroom"
    elif ans.state == chatroom_states.CHATROOM_UNFOLLOW:
        answer_bubble= str(ans.user.userinfo.name) +  " unfollwed this chatroom"
    elif ans.state == chatroom_states.CHATROOM_PURPOSE_EDIT:
        answer_bubble= str(ans.user.userinfo.name) +  " edited community purpose"
    return answer_bubble







def get_chatroom_actions(card_status,creator):

    '''function to get chatroom actions'''

    if creator and card_status['mute_status']:

        return (chatroom_actions_creator_mute)

    if creator and not card_status['mute_status']:
        return (chatroom_actions_creator_unmute)


    if(card_status['state'] == collabcard_states.COLLABCARD_STATE_FOLLOW or card_status['state'] == collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING) and not card_status['mute_status']:

        return (collabcard_action_user_follow_unmute)


    if(card_status['state'] == collabcard_states.COLLABCARD_STATE_FOLLOW or card_status['state'] == collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING) and  card_status['mute_status']:

        return (collabcard_action_user_follow_mute)


    return (collabcard_action_user_unfollow)


def get_chatroom_internal(request,card_instance,user_id,page,conversation_id,scroll_direction):

    '''internal function to get the chatroom can be used to handle web and android '''

    source_id = request.GET.get('source_id')
    aj = request.GET.get('aj')

    is_guest = False
    context={}

    if aj:
        is_guest = True

    # card = CollabcardSerializer(card_instance, user_id, card_instance.community)
    # card_id = card['id']
    # user = Userinfo.objects.get(user_id=card_instance.user.id)
    # usr = UserinfoSerializer(user)
    # #usr['is_clickable'] = feedback
    #
    # # when the member is removed
    # removed_state = removedMembersSerializer(card_instance.community.id, usr['id'])
    # if removed_state != False:
    #     usr['remove_state'] = removed_state
    #
    # # user form response serialzer
    # form_response = FormResponseSerilaizer(card_instance.community.id, card_instance.user.id, bl=True,
    #                                        current_user_id=user_id)
    # if form_response:
    #     usr['question_answers'] = form_response[1]
    #
    # # get the card image if any
    # files = get_collabcard_files(card_id)
    # card['images'] = files[0]
    # card['member'] = usr
    # card['pdf'] = files[1]
    #
    # card['community_name'] = card_instance.community.name




    #if the chatroom is deleted
    if card_instance.type == card_types.CARD_HIDDEN:
        card = get_chatroom_instance(card_instance,user_id)
        context = {'chatroom': card}
        return context

    # conversations  functionality

    #user has not done the scrolling
    conversations_filter = card_answers.objects.filter(card=card_instance).order_by('id')
    if not conversation_id and not scroll_direction:

        if is_guest:
           context = adding_guest_in_chatroom(request,context,card_instance,aj,source_id,card_instance.community.id,current_user_id=user_id)


        instance_filter = conversationMemberState.objects.filter(user_id=user_id,card = card_instance)
        if not instance_filter.exists():

            conversations = pagination(conversations_filter,page,paginate_by=20)
            conversations = get_answer_data(conversations, card_instance.community.id, current_user_id=user_id)

            placeholder = create_introduction_card_placeholder(card_instance,user_id)
            if placeholder:
                context['placeholder'] = placeholder
        else:
            conversation_instance = instance_filter[0].conversation

            upward_conversation = conversations_filter.filter(id__lte=conversation_instance.id).order_by('-id')[:10]

            downward_conversation = conversations_filter.filter(id__gt=conversation_instance.id)[:10]

            #merging both conversations
            conversations = upward_conversation|downward_conversation
            conversations = conversations.order_by('id')
            conversations = get_answer_data(conversations,card_instance.community.id,
                                            current_user_id=user_id,last_seen=conversation_instance)

    else:

        scroll_direction = int(scroll_direction)
        conversation_id = int(conversation_id)
        if scroll_direction == 0:               #upward scroll
            upward_list = conversations_filter.filter(id__lt=conversation_id).order_by('-id')[:20]
            conversations = reverse_conversations_for_upward_pagination(upward_list)

        elif scroll_direction == 1:           #downward scroll
            conversations = conversations_filter.filter(id__gt=conversation_id)[:20]
        else:
            conversations = conversations_filter

        conversations = get_answer_data(conversations, card_instance.community.id, current_user_id=user_id)



    card = get_chatroom_instance(card_instance, user_id)

    card_status = {
        'state': card['state'],
        'mute_status': card['mute_status'],
        'follow_status': card['follow_status'],
        'is_guest': card['is_guest']
    }

    #sending the chatroom actions
    if user_id and int(user_id) == card_instance.user.id:

        chatroom_actions = get_chatroom_actions(card_status,creator=True)
    else:

        chatroom_actions = get_chatroom_actions(card_status,creator=False)


    save_the_latest_conversation(card_instance, user_id)




    #sending the follow telescope
    latest_conversation = conversations_filter.last()
    card['show_follow_telescope'] = show_follow_telescope(card_status, card_instance, user_id, latest_conversation,conversations)


    context['chatroom'] = card
    context['conversations'] = conversations
    context['chatroom_actions'] =  chatroom_actions

    return context


def save_the_latest_conversation(card_instance,user_id):

    '''function to save the latest seen conversation'''


    latest_card = card_answers.objects.filter(card=card_instance,state=chatroom_states.ANSWER).last()
    print(latest_card)
    #status = is_member_verified(card_instance.community,user_id)
    if True:
        if latest_card:
            user_instance = User.objects.get(id=user_id)
            conversation_member_filter = conversationMemberState.objects.filter(user=user_instance, card=card_instance)
            conversation_instance = latest_card
            if not conversation_member_filter.exists():
                conversation_member_instance = conversationMemberState()
                conversation_member_instance.card = card_instance
                conversation_member_instance.conversation = conversation_instance
                conversation_member_instance.user = user_instance
                conversation_member_instance.save()

                update_conversation_engage_for_chatrooms(card_id=card_instance.id,user_id=user_instance.id,
                                                         last_conversation_id=conversation_instance.id,unseen_count=0)

                # conversation_engage_filter.update(
                #     last_conversation=conversation_instance, unseen_count=0)



            else:
                if conversation_instance.id != conversation_member_filter[0].conversation.id:
                    conversation_member_filter.update(conversation=conversation_instance, updated_at=time.time())

                    update_conversation_engage_for_chatrooms(card_id=card_instance.id, user_id=user_instance.id,
                                                             last_conversation_id=conversation_instance.id,
                                                             unseen_count=0)

                    # conversation_engage_filter.update(
                    #     last_conversation=conversation_instance, unseen_count=0)


def is_chatroom_join_expired(aj,source_id):

    '''function to check weather joining time of chatroom is valid or not'''

    expiry_filter = chatroomExpiryCodes.objects.filter(unique_code=aj,source=source_id)
    if expiry_filter.exists():
        expiry_instance = expiry_filter[0]
        time_stamp = int(time.time())
        expiry_time = int(expiry_instance.created_at)

        if (time_stamp - expiry_time) <= expiry_instance.expire_duration:
            return False

    return True


def adding_guest_in_chatroom(request,context,card_instance,aj,source_id,community_id,current_user_id,guest_header=False):



    context['aj_expired'] = is_chatroom_join_expired(aj, source_id)
    status = is_member_verified(community_id, current_user_id)

    state_filter = collabcardState.objects.filter(card=card_instance,user=current_user_id,is_guest=True)

    if not context['aj_expired'] and not status and not state_filter.exists():
            if guest_header:
                create_guest_header(current_user_id,source_id,card_instance,current_user_id)
                func_dict = {'collabcard_id': card_instance.id, 'member_id': current_user_id, 'status': True, 'is_guest': True}
                collabcard_follow_internal(func_dict)

    else:

        aj_expired_disclaimer = {}
        aj_expired_disclaimer['image_url'] = WARNING_IMAGE
        aj_expired_disclaimer['title'] = "Oops! The private link to participate in this chat room has expired. Join the following community to access this chat room."
        if status:
            #for promoter
            community_serializer =  CommunitySerializer(card_instance.community,status.member_id)
            community_serializer['created_by'] = get_community_creator(card_instance.community)
            aj_expired_disclaimer['community'] = community_serializer
        else:
            community_serializer =  CommunitySerializer(card_instance.community)
            community_serializer['created_by'] = get_community_creator(card_instance.community)
            aj_expired_disclaimer['community'] = community_serializer

        context['aj_expired_disclaimer'] = aj_expired_disclaimer


    return context


def create_guest_header(guest_id,invitee_id,card_instance,current_user_id):

    try:
        guest_instance = User.objects.get(id=guest_id)
        invitee_instance = User.objects.get(id=invitee_id)
    except:
        return



    guest_user_name = get_user_in_route_form(card_instance,guest_instance,current_user_id)

    invitee_user_name =  get_user_in_route_form(card_instance,invitee_instance,current_user_id)

    answer = guest_user_name + " joined via "+invitee_user_name+"'s link"

    cardAnswer_filter = card_answers.objects.filter(card=card_instance,user=guest_instance,state=chatroom_states.CHATROOM_GUEST)
    if not cardAnswer_filter.exists():
        instance = card_answers()
        instance.answer = answer
        instance.card = card_instance
        instance.user = guest_instance
        instance.state = chatroom_states.CHATROOM_GUEST
        instance.created_at = time.time()
        instance.save()


def get_user_in_route_form(card_instance,user_instance,current_user_id):

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

def show_follow_telescope(card_status,card_instance,user_id,latest_conversation,conversations):

    '''function to show follow telescope of user'''

    show = False
    if not card_status['follow_status']:
        show = True

    if card_instance.user.id == user_id:
        show = False

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


    return show


def create_introduction_card_placeholder(card_instance,user_id):

    '''function to create introduction card placeholder'''

    user_filter = User.objects.filter(id=user_id)
    if user_filter.exists():
        user_instance = user_filter[0]
    else:
        return

    if card_instance.type == card_types.CARD_INTRO and card_instance.user.id != user_instance.id:
        placeholder = """Welcome to """+ card_instance.community.name +", "
        user_name = card_instance.user.userinfo.name
        user_route = "route://member_profile/" + str(card_instance.user.id)
        user_name = "<<" + user_name + "|" + user_route + ">>"
        placeholder = placeholder + user_name
        return placeholder




def community_collabcard_invite(request,community_id):

    '''api to send collabcard invite footer'''

    community = Community.objects.get(id=community_id)
    member_id = request.GET.get('member_id')
    member_instance = User.objects.get(id=member_id)
    if is_member_promoter(community_id=community_id,member_id=member_id):
        community_serializer_instance = CommunitySerializer(community,promoter_id=member_instance)
    else:
        community_serializer_instance = CommunitySerializer(community)

    #if the community is a user-created community
    if community_serializer_instance['state'] == community_states.PRIVATE or community_serializer_instance['state'] == community_states.HIDDEN or community_serializer_instance['state'] == community_states.WHATSAPP:
        json_response = {

            'community': community_serializer_instance,

        }
        return JsonResponse(json_response)

    #initializing variables


    community_live_subtitle=""
    invite_prompt={}



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

        community_live_subtitle = compute_community_live_subtitle_for_Ig(community,member_id,number_of_members)
        invite_prompt = get_invite_prompt_for_members(community_id,member_type,member_types,member_id)


    #community live for lg communities
    elif community_serializer_instance['community_type'] == 1:


        user_instance=User.objects.get(id=member_id)

        collabcardTemp_instance_list=collabcardTemp.objects.filter(show_member=user_instance,community_id=community_serializer_instance['id']).order_by('id')

        for instance in collabcardTemp_instance_list:

            card_dict={}
            card_dict['id']=instance.id
            card_dict['title']=instance.title
            user = Userinfo.objects.get(user_id=instance.member)
            # serialize user object
            usr = UserinfoSerializer(user)
            card_dict['created_at'] = get_time_text(instance.created_at)
            card_dict['member'] = usr
            card_dict['images'] = []
            card_dict['pdf'] = []
            card_dict['state'] = instance.state
            card_dict['type'] = 5           #for unverified
            card_list.append(card_dict)

        count_of_verified_members=Members.objects.filter(community_id=community_serializer_instance['id']).filter(Q(state=4)|Q(state=1)).count()
        collabcard_temp_count=collabcardTemp_instance_list.count()
        total_count=count_of_verified_members + collabcard_temp_count


        community_live_subtitle= compute_community_live_subtitle_for_lg(total_count,count_of_verified_members,user_instance,community)

        # invite prompt logic for lg
        member_type="relevant alumnus"
        member_types="relevant alumini"
        invite_prompt = get_invite_prompt_for_members(community_id,member_type,member_types,member_id)

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
            'intro_collabcards':card_list
        }

    else:

        check_member=is_member_verified(community_id,member_id)
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


def text_for_community_live_subtitile(total_count,intro_collabcard_list,verified_members_list):

    '''function to return intro collabcard and verified list in case of lg communities'''

    diff = total_count - len(intro_collabcard_list)

    if diff > 0:
        intro_name_list=[]
        members_list=[]
        for instance in intro_collabcard_list:

            intro_name_list.append(instance.member.userinfo.name)

        verified_member_name_list=[]

        for member in verified_members_list:
            verified_member_name_list.append(member.member_id.userinfo.name)


        for num in range(diff):
            members_list.append(verified_member_name_list[num])

        total_list=intro_name_list+members_list

        return total_list
    else:

        intro_name_list = []
        members_list = []
        for instance in intro_collabcard_list:
            intro_name_list.append(instance.member.userinfo.name)
        return intro_name_list


def compute_community_live_subtitle_for_lg(total_count,count_of_verified_members,user_instance,community):

    verfied_status=is_member_verified(community,user_instance)
    member_id=user_instance
    community_id=community.id
    member_type="relevant alumnus"
    member_types="relevant alumni"

    community_live_subtitle=""
    if verfied_status:
        #if member is verified
        if total_count == 1:
           community_live_subtitle="""Awesome, you have taken the first step! Be the spark to ignite this community by inviting other %s from your network."""%(member_types)

        elif total_count == 2:


            intro_collabcard_list=collabcardTemp.objects.filter(show_member=user_instance,community_id=community_id)
            verified_members_list = Members.objects.filter(community_id=community_id).filter(Q(state=1)|Q(state=4))

            total_list=text_for_community_live_subtitile(total_count,intro_collabcard_list,verified_members_list)

            ans_list=[]

            for data in total_list:

                if data == user_instance.userinfo.name:
                    continue
                ans_list.append(data)
            if ans_list:
                community_live_subtitle = """Superb, you and %s are now together for your shared interest! Invite 2 other %s and let them join you in this community.""" % (
                ans_list[0], member_types)


        elif total_count == 3:
            intro_collabcard_list = collabcardTemp.objects.filter(show_member=user_instance, community_id=community_id)
            verified_members_list = Members.objects.filter(community_id=community_id).filter(Q(state=1)|Q(state=4))

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
                    other_member_list[0], other_member_list[1],other_member_list[2])

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
            community_live_subtitle="1 last step pending! Since this is an exclusive community, you need to verify atleast 3 other members to initiate the community"

        elif total_count > 4 and count_of_verified_members == 2:
            community_live_subtitle="1 last step pending! Since this is an exclusive community, you need to verify atleast 2 other members to initiate the community"

        elif total_count > 4 and count_of_verified_members == 3:
            community_live_subtitle = "1 last step pending! Since this is an exclusive community, you need to verify atleast 1 member to initiate the community"




    else:
        # member is not verified
        if total_count == 1:
           community_live_subtitle="""Awesome, you have taken the first step! Be the spark to ignite this community by inviting other %s from your network."""%(member_types)


        elif total_count == 2:
            intro_collabcard_list = collabcardTemp.objects.filter(show_member=user_instance, community_id=community_id)
            verified_members_list = Members.objects.filter(community_id=community_id).filter(Q(state=1)|Q(state=4))

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
            verified_members_list = Members.objects.filter(community_id=community_id).filter(Q(state=1)|Q(state=4))

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
                    other_member_list[0],other_member_list[1],other_member_list[2])


        elif total_count > 4 and count_of_verified_members == 1:
            community_live_subtitle="Your profile isn't verified yet. Since this is an exclusive community, your profile needs to be verified in order to initiate the community"
        elif total_count > 4 and count_of_verified_members == 2:
            community_live_subtitle="Your profile isn't verified yet. Since this is an exclusive community, your profile needs to be verified in order to initiate the community"
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
           community_live_subtitle="Your profile isn't verified yet. Since this is an exclusive community, your profile needs to be verified in order to initiate the community"


        elif total_count > 0  and count_of_verified_members == 0:
            community_live_subtitle="Your profile isn't verified yet. Since this is an exclusive community, your profile needs to be verified in order to initiate the community"
    return community_live_subtitle


def compute_community_live_subtitle_for_Ig(community_instance,member_id,members_count):

    '''function to get community_live  subtitle for IG communities'''

    community_name = community_instance.name
    member_types = community_name.split("of")[0].strip()
    member_type = member_types
    if member_types[-1] == "s":
        member_type = member_types[0:-1]

    member_types = member_types.lower()
    member_type = member_type.lower()

    #members_count = get_members_count_in_community(community_instance)

    if members_count == 1:
        community_live_subtitle = """Awesome, you have taken the first step! Be the spark to ignite this community by inviting other %s from your network.""" % (
            member_types)
    elif members_count == 2:

        member_filter = Members.objects.filter(community_id=community_instance).filter(~Q(member_id=member_id))
        member_name = member_filter[0].member_id.userinfo.name
        community_live_subtitle = """Superb, you and %s are now together for your shared interest! Invite 2 other %s and let them join you in this community.""" % (
            member_name, member_types)

    elif members_count == 3:

        member_filter =  Members.objects.filter(community=community_instance).filter(~Q(member_id=member_id)).order_by('-id')
        member_name1 = member_filter[0].member_id.userinfo.name
        member_name2 = member_filter[1].member_id.userinfo.name

        community_live_subtitle = """You, %s  and %s  make a great group! Make it a community by inviting 1 more %s.""" % (
            member_name1, member_name2, member_type)
    else:
        members_left = ig_members_count - members_count
        community_live_subtitle = """Every community needs its members to make purposeful conversations. Invite %s or more members to start conversations.""" %(members_left)

    return community_live_subtitle


def get_invite_prompt_for_members(community_id,member_type,member_types,member_id):


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
        temp['unlock_sub_title'] = "To start a conversation, invite %s more member to this community and make this community live." % (
            members_left)
        temp['community_live_title'] = "more member required"
    else:
        temp['unlock_sub_title'] = "To start a conversation, invite %s more members to this community and make this community live." % (
            members_left)
        temp['community_live_title'] = "more members required"

    temp['unlock_action_title'] = "OK, INVITE NOW"
    temp['unlock_action'] = """route://community?community_id=%s&share=true&source=community_live_unlock"""

    return temp



def community_cards_version_1(request,community_id,req_dict=None):

    '''Version 1 community cards for ig communities'''

    community = Community.objects.get(id=community_id)

    if req_dict:
        member_id=req_dict['member_id']
        size=10
    else:
        member_id = request.GET.get('member_id')
        size = request.GET.get('size', '')

    current_user_id = get_member_id_from_headers(request)


    if size:
        size = int(size)
        collabcard_instance_list = Collabcard.objects.filter(community=community_id).order_by('id')[:size]
        size = Collabcard.objects.filter(community=community_id).count()
    else:
        collabcard_instance_list = Collabcard.objects.filter(community=community_id).order_by('id')
        size = collabcard_instance_list.count()
    card_list = []

    for card_instance in collabcard_instance_list:

        user = Userinfo.objects.get(user_id=card_instance.user)
        # serialize user object
        usr = UserinfoSerializer(user)
        # form responses of user
        form_response = FormResponseSerilaizer(card_instance.community.id, card_instance.user.id,bl=True,current_user_id=current_user_id)
        if form_response:
            usr['response'] = form_response[0]
            usr['question_answers'] =form_response[1]
        # get card images --------------------------------------------------------
        files = get_collabcard_files(card_instance)
        # -----------------------------------------------------------------------
        # share_url = url+'/collabcard/'+str(card.id)

        time_text = '' if str(card_instance.date_epoch) == "-9223372036854775808" else get_time_text(
            card_instance.date_epoch)
        card_dict = CollabcardSerializer(card_instance, member_id, card_instance.community)

        collabcard_status = get_status_of_collabcard(member_id=member_id,
                                                     card=card_instance)
        card_dict['state'] = collabcard_status['state']
        card_dict['mute_status'] = collabcard_status['mute_status']
        card_dict['follow_status'] = collabcard_status['follow_status']

        card_dict['created_at'] = time_text
        card_dict['member'] = usr
        card_dict['images'] = files[0]
        card_dict['pdf'] = files[1]
        card_list.append(card_dict)

    json_response = {
        'collabcards': card_list,
        'size': size,
    }

    if req_dict:
        return json_response

    return JsonResponse(json_response)



def get_cards_for_demo(community_id, member_id):
    '''function to get demo cards for pilot community'''
    card_list = []
    userinfo_objects = Userinfo.objects.get(user_id=member_id)
    community = Community.objects.get(id=community_id)
    name = userinfo_objects.name
    first_name = name.split(' ', 1)[0]
    community_purpose = community.purpose
    if community_purpose:
        community_purpose = community_purpose[0].lower() + community_purpose[1:]
    # sample card
    sample_card = {}
    sample_card['id'] = "first_conversation"
    sample_card['title'] = """Welcome %s, I'll be initiating this community %s""" % (first_name, community_purpose)
    sample_card['community_id'] = community_id
    sample_card['member'] = {
        'name': "Initial Promoter"
    }
    sample_card['created_at'] = get_time_text(time.time())
    sample_card['answer_text'] = "Second Promoter & 3 others responded"
    sample_card['type'] = 0
    answers = []

    temp = {}

    test = str(community.about)
    x = test.find("Anytime")
    display_string = ""
    for index in range(x, len(test)):
        display_string = display_string + test[index]
        if test[index] == '.':
            break
    temp['id'] = "first_conversation_1"
    temp['answer'] = display_string
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Second Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id'] = "first_conversation_2"
    temp[
        'answer'] = """Interested members can respond by simply chatting with you and each other on your conversation card."""
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Third Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id'] = "first_conversation_3"
    temp[
        'answer'] = """Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card."""
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Fourth Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id'] = "first_conversation_4"
    temp['answer'] = """Others would simply swipe through the conversation card and move to the next conversation"""
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Initial Promoter"
    }
    answers.append(temp)
    sample_card['answers'] = answers

    card_list.append(sample_card)

    # purpose info card
    ###################### sample card end ################
    purpose_card = {}
    purpose_card['id'] = "second_conversation"
    purpose_card[
        'title'] = """%s, this community is currently a pilot as it doesn't actually have any of us (promoters). Help this community find us and enable interactions between members""" % (
        first_name)
    purpose_card['community_id'] = community_id
    purpose_card['member'] = {
        'name': "Initial Promoter"
    }
    purpose_card['created_at'] = "Just Now"
    purpose_card['answer_text'] = "Second Promoter & 3 others responded"
    purpose_card['type'] = 0
    answers = []

    temp = {}
    temp['id'] = "second_conversation_1"
    temp[
        'answer'] = """Promoters are responsible to approve new member requests in the community and drive conversations between members."""
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Second Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id'] = "second_conversation_2"
    temp[
        'answer'] = """Anyone can become a promoter and initiate this community by referring %s new members to the community.""" % (
        eligibility_count)
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Third Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id'] = "second_conversation_3"
    temp['answer'] = """%s, please refer someone who you consider fit to become a promoter""" % (str(first_name))
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Fourth Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id'] = "second_conversation_4"
    refered_members = get_referred_members_of_a_member(community_id, member_id)
    diff = (eligibility_count - len(refered_members))
    temp['answer'] = """Alternatively, you can refer %s  members and become promoter of this community.""" % (str(diff))
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Initial Promoter"
    }
    answers.append(temp)
    purpose_card['answers'] = answers
    card_list.append(purpose_card)

    # referal card

    referal_card = {}
    referal_card['member'] = {
        'id': member_id,
        'name': name
    }
    referal_card['id'] = "third_conversation"
    referal_card['title'] = """Just discovered this community which is %s""" % (community_purpose)
    referal_card['created_at'] = "Just Now"
    referal_card['type'] = 0
    referal_card['share_url'] = url + "/community/" + str(community_id) + "?ref_id=" + str(member_id)
    card_list.append(referal_card)
    referal_card['answers'] = []
    return card_list




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
    except :
        context = get_error_context(False,"Send params correctly")
        return JsonResponse(context)

    res = json.loads(request.body)
    ans = card_answers()
    ans.answer = res['title']
    ans.card = card_instance
    ans.user = user_instance
    ans.created_at = time.time()
    ans.save()

    update_last_answer_id(card_id, ans.id)
    # auto following the collabcard if answer is created
    function_dict = {
        'member_id': user_id,
            'collabcard_id': card_id,
            'status': True
        }
    collabcard_follow_internal(function_dict)


    #sending the tagged member list
    auto_follow_chatrooms_in_case_of_tagging(request, res['title'], card_id)

    send_follow_notification(card_id=card_id, user_id=user_id, answer=res['title'])

    #     # calling update_answer_text
    # if card.type == card_types.CARD_NORMAL or card.type == card_types.CARD_INTRO:
    #     print("type === ", card.type)
    #     update_answer_text(card_id)


    #updating the conversationEngage table
    conversation_seen(request,{'member_id':user_id,'conversation_id':ans.id})
    update_my_chatrooms_for_users(chatroom_id=card_id)

    return JsonResponse({'success': True,'id':ans.id})


@csrf_exempt
def create_conversation(request):

    '''api to create the conversation'''

    member_id = get_member_id_from_headers(request)

    if not member_id:
        context = get_error_context(False,"send member id in headers")
        return JsonResponse(context)

    res = json.loads(request.body)


    is_guest = False

    if 'aj' in res and 'source_id' in res:
        if res['aj'] and res['source_id']:
            is_guest = True


    card_instance = Collabcard.objects.get(id=res['chatroom_id'])
    user_instance = User.objects.get(id=member_id)

    current_state = members_state(request,{'community_id':card_instance.community.id,'member_id':user_instance.id})

    if is_guest and (current_state['state'] == 0 or current_state['state'] == member_states.PENDING_MEMBER):
        context = {}
        context = adding_guest_in_chatroom(request, context, card_instance, res['aj'], res['source_id'], card_instance.community.id, member_id,guest_header=True)



    ans = card_answers()
    ans.answer = res['text']
    ans.card = card_instance
    ans.user = user_instance
    ans.created_at = time.time()
    ans.save()


    #saving the og tags if present
    if 'og_tags' in res:
        ans.og_tags = json.dumps(res['og_tags'])
        ans.save()
    elif 'share_link' in res:
        ans.og_tags = json.dumps(decode_meta_from_url(res['share_link']))
        ans.save()

    update_last_answer_id(card_instance.id, ans.id)

    # auto following the collabcard if answer is created
    if current_state['state'] == member_states.ADMIN or current_state['state'] == member_states.MEMBER or current_state['state'] == member_states.PROFILE_UNAVAILABLE:
        function_dict = {
            'member_id': member_id,
            'collabcard_id': card_instance.id,
            'status': True
        }
        collabcard_follow_internal(function_dict)

    # sending the tagged member list
    auto_follow_chatrooms_in_case_of_tagging(request, res['text'], card_instance.id)

    user_id  = str(user_instance.id)
    send_follow_notification.delay(card_id=card_instance.id, user_id=user_id, answer=res['text'])

    #send tagged users mail if they didnt check chat in last 24 hours
    tagged_members = get_tagged_members_list(res['text'])

    tagged_member_list = tagged_members[0]
    if len(tagged_member_list)>0:
        send_tagged_user_mail.delay(user_instance.id,card_instance.id,tagged_member_list,time_in_hrs=24)

    notification_list = [
        'mail_card_owner_inactivity'
    ]
    
    #check if sender is not the owner and  notification flag is true
    if check_notification_flag(card_instance.user.id,notification_list,card_id=card_instance.id,community_id=None) and str(member_id) != str(card_instance.user.id):
        send_chatroom_owner_mail.delay(card_instance.user.id,card_instance.id,ans.created_at,time_in_hrs=12)


    # # updating the conversationEngage table
    conversation_seen(request, {'member_id': user_instance.id, 'conversation_id': ans.id})
    update_my_chatrooms_for_users.delay(chatroom_id=card_instance.id)

    return JsonResponse({'success': True, 'id': ans.id})






def auto_follow_chatrooms_in_case_of_tagging(request,conversation,card_id):

    '''function to follow tagged chatrooms'''

    tagged_members = get_tagged_members_list(conversation)

    tagged_member_list = tagged_members[0]

    for user_id in tagged_member_list:

        function_dict = {
            'member_id': user_id,
            'collabcard_id': card_id,
            'status': True
        }
        print(function_dict)
        collabcard_follow_internal(function_dict)




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
    '''Api to follow collabcard by members Post API'''
    explicit_call = False                       #variable to distinguish whether the collabcard is followed by external call or internal call

    current_member_id = get_member_id_from_headers(request)

    if is_request_web(request) and request.user.is_authenticated:
        current_member_id = request.user.id


    collabcard_id = request.GET.get('collabcard_id', '')
    member_id = request.GET.get('member_id', '')
    status = request.GET.get('value', 'true')

    if status != 'true':
        status = False              #unfollowed
    else:
        status = True               #followed
        explicit_call = True



    collabcard = Collabcard.objects.get(id=collabcard_id)

    community_instance = collabcard.community
    user_instance = User.objects.get(id=member_id)

    #user cant unfollow hit own collabcard
    if not status and collabcard.user.id == user_instance.id:
        return JsonResponse({'success':True})


    is_guest = False

    aj = request.GET.get('aj')
    source_id = request.GET.get('source_id')
    member_state = members_state(request, {'community_id':community_instance.id,'member_id':user_instance.id})

    #user is a guest in chatroom
    if aj and source_id and (member_state['state'] == 0 or member_state['state'] == member_states.PENDING_MEMBER):

        context = {}
        context = adding_guest_in_chatroom(request, context, collabcard, aj, source_id, community_instance.id, current_member_id,guest_header=True)

        return JsonResponse(context)



    collabcard_state_filter = collabcardState.objects.filter(card=collabcard, user=user_instance)
    if not collabcard_state_filter.exists():
        collabcard_state_instance = collabcardState()
        collabcard_state_instance.card = collabcard
        collabcard_state_instance.community = community_instance
        collabcard_state_instance.user = user_instance
        collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_FOLLOW
        collabcard_state_instance.created_at = time.time()
        collabcard_state_instance.updated_at = time.time()
        collabcard_state_instance.follow_status = status
        collabcard_state_instance.is_guest = is_guest
        collabcard_state_instance.save()

        if status:

            create_chatroom(card_instance=collabcard, user_instance=user_instance,
                            state=chatroom_states.CHATROOM_FOLLOW, current_user_id=current_member_id)

            create_chatroom_engagement(card_instance=collabcard,user_instance=user_instance)

    else:
        follow_status = collabcard_state_filter[0].follow_status
        if status and collabcard_state_filter[0].follow_status:
            return JsonResponse({'success': True})

        if not status and not collabcard_state_filter[0].follow_status:
            return JsonResponse({'success': True})


        if status:

            state = collabcard_states.COLLABCARD_STATE_FOLLOW
            if collabcard_state_filter[0].card.type == card_types.CARD_EVENT or collabcard_state_filter[0].card.type == card_types.CARD_PUBLIC_EVENT:
                collabcard_state_filter.update(follow_status = status,updated_at=time.time())
            else:
                collabcard_state_filter.update(state=state, follow_status = status,updated_at=time.time())

            create_chatroom(card_instance=collabcard, user_instance=user_instance,
                            state=chatroom_states.CHATROOM_FOLLOW, current_user_id=current_member_id)

            create_chatroom_engagement(card_instance=collabcard, user_instance=user_instance)

        else:
            collabcard_state_filter.update(state=collabcard_states.COLLABCARD_STATE_SEEN,follow_status = status,
                                                                                   updated_at=time.time())

            #deleting the conversation engage
            delete_status = conversationEngage.objects.filter(card=collabcard,user=user_instance).delete()
            print(delete_status)

            create_chatroom(card_instance=collabcard, user_instance=user_instance,
                            state=chatroom_states.CHATROOM_UNFOLLOW, current_user_id=current_member_id)



    # custom_cache.clear()
    update_my_chatrooms_for_users(chatroom_id=collabcard.id,user_id=current_member_id)
    return JsonResponse({'success': True})


def collabcard_follow_internal(func_dict,state=collabcard_states.COLLABCARD_STATE_FOLLOW):

    '''folowing collabcard internally'''

    card_id = func_dict['collabcard_id']
    member_id = func_dict['member_id']
    status = func_dict['status']
    is_guest = False
    if 'is_guest' in func_dict:
        is_guest = func_dict['is_guest']

    try:
        card_instance = Collabcard.objects.get(id=card_id)
        user_instance = User.objects.get(id=member_id)
    except:
        return

    collabcard_state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)

    if collabcard_state_filter.exists():
        collabcard_state_filter.update(follow_status=status,state=state,is_guest=is_guest)

    else:
        collabcard_state_instance = collabcardState()
        collabcard_state_instance.card = card_instance
        collabcard_state_instance.community = card_instance.community
        collabcard_state_instance.user = user_instance
        collabcard_state_instance.state = state
        collabcard_state_instance.created_at = time.time()
        collabcard_state_instance.updated_at = time.time()
        collabcard_state_instance.follow_status = status
        collabcard_state_instance.is_guest = is_guest
        collabcard_state_instance.save()

    print("collabcard follow internal hit")
    if status:
        create_chatroom_engagement(card_instance=card_instance, user_instance=user_instance)

    update_my_chatrooms_for_users(chatroom_id=card_instance.id, user_id=member_id)






def set_state_for_event_cards(collabcard,community_instance,user_instance,status,explicit_call,current_member_id):

    '''function to set states in case of event cards'''

    if (collabcard.type == card_types.CARD_EVENT or collabcard.type == card_types.CARD_PUBLIC_EVENT):

        if status:  # the collabcard is the event card and followed
            try:
                collabcard_state_instance = collabcardState.objects.get(card=collabcard, user=user_instance)
            except:
                # for autofollowing the co-host
                collabcard_state_instance = collabcardState()
                collabcard_state_instance.card = collabcard
                collabcard_state_instance.community = community_instance
                collabcard_state_instance.user = user_instance
                collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_FOLLOW
                collabcard_state_instance.created_at = time.time()
                collabcard_state_instance.updated_at = time.time()
                collabcard_state_instance.save()

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
        return {'success':True}
    else:
        return {'success': False}


@csrf_exempt
def collabcards_seen(request):
    '''This functions stores the details of members who have seen the card'''

    params = request.GET
    community_id = None
    card_id = None
    collabcard_type=None
    user_id = None
    if 'community_id' in params:
        community_id = params['community_id']
    if 'collabcard_id' in params:
        card_id = params['collabcard_id']
    if 'member_id' in params:
        user_id = params['member_id']
    if 'collabcard_type' in params:
        collabcard_type=params['collabcard_type']

    collabcards_seen_internal(community_id, card_id, collabcard_type, user_id)

    return JsonResponse({'success': True})

def collabcards_seen_internal(community_id, card_id, collabcard_type, user_id):
    '''This internal functions stores the details of members who have seen the card'''

    if str(collabcard_type) == str(5):                        #unverifeid collabcard
        collabcardTemp.objects.filter(id=card_id).update(state=1)
        return JsonResponse({'success': True})


    community = Community.objects.get(id=community_id)
    user_instance = User.objects.get(id=user_id)
    card_instance = Collabcard.objects.get(id=card_id)

    # saving the state in collabcard state table if it is not present
    is_present = collabcardState.objects.filter(card=card_instance, user=user_instance)
    if not is_present.exists():
        collabcard_state_instance = collabcardState()
        collabcard_state_instance.card = card_instance
        collabcard_state_instance.community = community
        collabcard_state_instance.user = user_instance
        collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_SEEN
        collabcard_state_instance.created_at = time.time()
        collabcard_state_instance.updated_at = time.time()
        collabcard_state_instance.save()
    else:
        state_instance = is_present[0]
        if state_instance.state == 0:
            if state_instance.follow_status:
                state_instance.state = collabcard_states.COLLABCARD_STATE_FOLLOW
            else:
                state_instance.state = collabcard_states.COLLABCARD_STATE_SEEN
            state_instance.save()


    update_last_unseen_in_engage(user=user_instance, community=community,is_seen=False)


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

    #event attending
    if status:

       try:
           state_instance = collabcardState.objects.get(card=card_instance, user=user_instance)
           state_instance.state = collabcard_states.COLLABCARD_STATE_ATTENDING
           state_instance.save()

       except:
           collabcard_state_instance = collabcardState()
           collabcard_state_instance.card = card_instance
           collabcard_state_instance.community = card_instance.community
           collabcard_state_instance.user = user_instance
           collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_ATTENDING
           collabcard_state_instance.created_at = time.time()
           collabcard_state_instance.updated_at = time.time()
           collabcard_state_instance.save()

       func_dict = {'member_id': member_id, 'collabcard_id': card_instance.id, 'status': True}
       collabcard_follow_internal(func_dict,state=collabcard_states.COLLABCARD_STATE_ATTENDING)


    else:

        state = collabcard_states.COLLABCARD_STATE_SEEN
        try:
            state_instance = collabcardState.objects.get(card=card_instance, user=user_instance)

            if state_instance.follow_status:
                state_instance.state = collabcard_states.COLLABCARD_STATE_FOLLOW
                state = collabcard_states.COLLABCARD_STATE_FOLLOW
            else:
                state_instance.state=collabcard_states.COLLABCARD_STATE_SEEN
                state = collabcard_states.COLLABCARD_STATE_SEEN
            state_instance.save()

        except:
            collabcard_state_instance = collabcardState()
            collabcard_state_instance.card = card_instance
            collabcard_state_instance.community = card_instance.community
            collabcard_state_instance.user = user_instance
            collabcard_state_instance.state = state
            collabcard_state_instance.created_at = time.time()
            collabcard_state_instance.updated_at = time.time()
            collabcard_state_instance.save()


    update_event_answer_text(collabcard_id)  # function to update the text when a user attends an event



    # if not str(member_id) == str(card_instance.user.id) and status:
        # send_poll_or_event_notification.delay(card_id=collabcard_id, user_id=member_id)

    return JsonResponse({'success': True})


def update_event_answer_text(card_id):
    '''function to update the answer text of card when an event is created'''

    collabcard_instance = Collabcard.objects.get(id=card_id)

    if collabcard_instance.type == 2:

        # getting the number of people interestes in event
        event_list_members = collabcardState.objects.filter(card=collabcard_instance).filter(
            Q(state=collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING) | Q(state=collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING)).order_by('id')
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

    status = Collabcard.objects.filter(community=community, user=member)

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
        Collabcard.objects.filter(community=community_instance).filter(~Q(type=4)).order_by('id').values_list('id', flat=True))
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
    print("collabcardid----",collabcard_ids)


    #for whatsapp community
    if not collabcard_ids:
        return JsonResponse({'collabcards': []})
    else:
        collabcard_ids = collabcard_ids.split(",")

    member_id = get_member_id_from_headers(request)
    community_instance = None
    feed_back=True
    card_list = []
    for card_id in collabcard_ids:
        card_instance = Collabcard.objects.get(id=card_id)
        user = Userinfo.objects.get(user_id=card_instance.user)
        # serialize user object
        if card_instance.community.id == feedback_community_id:
            feed_back=False
        usr = UserinfoSerializer(user)

        usr['is_clickable']=feed_back
        removed_state = removedMembersSerializer(card_instance.community.id, usr['id'])

        if removed_state != False:
            usr['remove_state'] = removed_state


        # user form response serialzer
        form_response = FormResponseSerilaizer(card_instance.community.id, card_instance.user.id,bl=True,current_user_id=member_id)

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
        community_instance=card_instance.community
        card_dict = CollabcardSerializer(card_instance, member_id, card_instance.community)

        collabard_status = get_status_of_collabcard(member_id, card_instance)

        card_dict['state'] = collabard_status['state']
        card_dict['mute_status'] = collabard_status['mute_status']
        card_dict['follow_status'] = collabard_status['follow_status']

        card_dict['created_at'] = time_text
        card_dict['member'] = usr
        card_dict['images'] = files[0]
        card_dict['pdf'] = files[1]
        card_list.append(card_dict)

    if community_instance:
        community=CommunitySerializer(community_instance)
        return JsonResponse({'collabcards': card_list,'community':community})

    return JsonResponse({'collabcards': card_list})


def get_last_conversation(conversation_filter,member_id,chatroom_id):

    '''function to get last conversation and last unseen conversation'''

    has_seen = conversationMemberState.objects.filter(card_id=chatroom_id, user_id=member_id)

    if has_seen.exists():
        conversation_id = has_seen[0].conversation.id
        next_conversation = card_answers.objects.filter(id__gt=conversation_id,card=chatroom_id,state=chatroom_states.ANSWER)
        unseen_count = next_conversation.count()

        if not next_conversation:

            conversation = conversationSerializer(has_seen[0].conversation)
        else:
            conversation = conversationSerializer(next_conversation[0])

        conversation_files = get_answer_files(conversation['id'])

        if 'location' in conversation_files:
            conversation['location'] = conversation_files['location']
        conversation['images'] = conversation_files['image']
        conversation['pdf'] = conversation_files['pdf']

        return (conversation,unseen_count)
    elif conversation_filter.exists():
        conversation = conversationSerializer(conversation_filter[0])
        unseen_count = conversation_filter.count()
        conversation_files = get_answer_files(conversation['id'])

        if 'location' in conversation_files:
            conversation['location'] = conversation_files['location']
        conversation['images'] = conversation_files['image']
        conversation['pdf'] = conversation_files['pdf']

        return (conversation,unseen_count)
    else:
        return (None,0)

def get_member_images_of_chatroom(conversation_filter):

    '''function to give member images of chatrooms'''
    unique_members = set()
    member_images = []
    for conversation in conversation_filter:

        if conversation.user.id not in unique_members:
            member_images.append(conversation.user.userinfo.image_link)
            unique_members.add(conversation.user.id)

    return member_images[:6]

def get_chatrooms(chatroom_list,member_id):

    '''function to get chatrooms'''

    chatrooms = []

    for card_instance in chatroom_list:
        chatroom_instance = get_chatroom_instance(card_instance, member_id)
        conversation_filter = card_answers.objects.filter(card=card_instance.id,
                                                          state=chatroom_states.ANSWER).order_by('id')
        chatroom_instance['total_response_count'] = conversation_filter.count()
        chatroom_instance['members_images'] = get_member_images_of_chatroom(conversation_filter)
        chatrooms.append(chatroom_instance)

    return chatrooms



def fetch_chatroom_feed(request):

    '''api to fetch chatroom feed'''

    community_id = request.GET.get('community_id')
    page = request.GET.get('page',1)

    chatroom_id = request.GET.get('chatroom_id')
    scroll_direction  = request.GET.get('scroll_direction')

    member_id = get_member_id_from_headers(request)

    chatroom_filter = Collabcard.objects.filter(community=community_id).order_by('id')

    chatrooms = []
    context = {}

    if not chatroom_id and not scroll_direction:

        last_seen = collabcardState.objects.filter(community=community_id,user = member_id).filter(~Q(state=0)).order_by('-card_id')
        if not last_seen.exists():
            chatroom_list = pagination(chatroom_filter,page,paginate_by=5)
            chatrooms = get_chatrooms(chatroom_list,member_id)
        else:
            last_seen = last_seen[0]
            upward = chatroom_filter.filter(id__lte=last_seen.card.id).order_by('-id')[:3]
            downward = chatroom_filter.filter(id__gt=last_seen.card.id)[:3]
            # upward = Collabcard.objects.filter(id__lt=last_seen.card.id,community=community_id).order_by('id')[:3]
            # downward = Collabcard.objects.filter(id__gt=last_seen.card.id,community=community_id).order_by('id')[:3]
            chatroom_filter = upward | downward
            chatroom_list = chatroom_filter.order_by('id')
            chatrooms = get_chatrooms(chatroom_list,member_id)

        context['header'] = chatroom_feed_header(community_id,member_id)

    else:
        scroll_direction = int(scroll_direction)
        if scroll_direction == 0:                                   #upward scroll

            upward = chatroom_filter.filter(id__lt=chatroom_id).order_by('-id')[:5]
            upward = reverse_conversations_for_upward_pagination(upward)
            #print(upward)
            chatrooms = get_chatrooms(upward,member_id)

        elif scroll_direction == 1:                                 #downward scroll

            downward = chatroom_filter.filter(id__gt=chatroom_id).order_by('id')[:5]
            chatrooms = get_chatrooms(downward,member_id)


    context['chatrooms'] = chatrooms
    return JsonResponse(context)




def chatroom_feed_header(community_id,member_id):

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

    #sorting member names in ascending order
    member_names.sort()

    header = {
        'community_name':community_instance.name,
        'member_names':member_names[:10]
    }
    return header
    # sending member_names







############# upload files flow   ##########################


@csrf_exempt
def upload_files(request):
    '''function to upload files'''
    body = request.GET
    member_id=get_member_id_from_headers(request)
    if request.user.is_authenticated and is_request_web(request):
        current_member_id = request.user.id

    if 'community_id' in body:
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

    elif 'collabcard_id' in body:
        attachment_type = body['type']
        collabcard_id = body['collabcard_id']
        collabcard = Collabcard.objects.get(id=collabcard_id)

        file = Card_Attachment()
        file.collabcard = collabcard
        file.type = attachment_type
        file.file_url = body['url']
        file.save()

    elif 'answer_id' in body:
        attachment_type = body['type']
        answer_id = body['answer_id']
        answer_instance = card_answers.objects.get(id=answer_id)
        file = answerAttachment()
        file.answer = answer_instance
        file.type = attachment_type
        file.file_url = body['url'] if 'url' in body else None
        file.location_name = body['location_name'] if 'location_name' in body else None
        file.location_lat = body['location_lat'] if 'location_lat' in body else None
        file.location_long = body['location_long'] if 'location_long' in body else None
        file.save()
    elif 'poll_id' in body:

        try:
            instance = CollabcardPolls.objects.get(id=body['poll_id'])
            instance.image_url = body['url']
            instance.save()
        except:
            return JsonResponse({'success': False, 'error_message': "Send valid poll id"})
    elif 'draft_id' in body:
        attachment_type = body['type']
        draft_id = body['draft_id']
        draft_instance = draftChatroom.objects.get(id=draft_id)

        instance = draftChatroomFiles()
        instance.draft= draft_instance
        instance.file_url = body['url']
        instance.type = attachment_type
        instance.save()

    elif 'draft_poll_id' in body:

        try:
            instance = draftPolls.objects.get(id=body['draft_poll_id'])
            instance.image_url = body['url']
            instance.save()
        except:
            return JsonResponse({'success': False, 'error_message': "Send valid draft poll id"})

    return JsonResponse({'success': True})



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

        login_type = request.GET.get('type',None)
        if login_type and login_type == "google":
            google_id_token = request.GET.get('google_id_token',None)
            context = login_with_google(google_id_token,request)
            info_logger.info(context)
            return JsonResponse(context)


        res = json.loads(request.body)
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

            print("res ==== ",res)
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
        #print(res)
        login_type = res['type']
        if login_type == "google":
            if 'google_id_token' in res:
                google_id_token = res['google_id_token']
                context = login_with_google(google_id_token,request)
                info_logger.info(context)
                return JsonResponse(context)
            return JsonResponse({'success':False,'error_message':"send google id token in body"})

        elif login_type == 'facebook':

            dic_form = res['login_json']
            json_to_save = json.dumps(dic_form)

            context = login_with_facebook(request,res,json_to_save)
            #context = {}
            return JsonResponse(context)

        elif login_type == 'linkedIn':

            dic_form = res['login_json']
            json_to_save = json.dumps(dic_form)

            context = login_with_linkedin(request, res, json_to_save)
            return JsonResponse(context)

        elif login_type == "apple":

            dic_form = res['login_json']
            json_to_save = json.dumps(dic_form)

            context = login_with_apple(request,res,json_to_save)
            return JsonResponse(context)

        elif login_type == "custom":

           context = custom_login(request,res,login_type="custom")
           return JsonResponse(context)
    else:
        context = get_error_context(False,"Send a post request")
        return JsonResponse(context)


def create_user(user_name, email, id, apple_id=False):
    ''' function to create Auth-User of a user '''

    user_name = user_name + "_" + id

    user = User.objects.filter(email=email)
    if apple_id and not user.exists():
        user = User.objects.filter(username=user_name)

    if not user.exists():

        user = User()
        user.username = user_name
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
        userinfo.email = email
        userinfo.name = user_name
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

    params={'id_token':google_id_token}
    response = rqst.get("https://oauth2.googleapis.com/tokeninfo",params=params)

    response = response.text
    json_to_save = json.dumps(response)
    google_json = json.loads(response)
    x = (json_to_save,google_json)
    return x

def login_with_google(google_id_token,request,login_type="google"):

    '''function to login with google'''

    google_json = fetch_google_auth_data(google_id_token)
    json_to_save = google_json[0]
    res = google_json[1]
    info_logger.info(res)
    created = False
    #context ={'success':False,'error_message':"please give permission to use your google account"}
    context = get_error_context(False,"please give permission to use your google account")

    if 'email' in res:
        email = res['email']
        email = email.lower().strip()

        user = get_user_from_email(email)           #getting the user instance from email if it is present

        if not user:
            # creating a user if no user is associated with that email
            res['id'] = res['azp']

            user = create_user(user_name=res['name'], email=res['email'], id=res['email'])

            if 'picture' in res:
                image_link = upload_image_to_firebase(res['picture'], user.id)
            else:
                image_link = 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'

            userinfo = create_userinfo(user=user, email=res['email'], user_name=res['name'],
                                       profile_picture=image_link, login_type=login_type,
                                       json_to_save=json_to_save
                                       )

            mobile_no = res['mobile_no'] if 'mobile_no' in res else None
            save_user_primary_email(user,res['email'],mobile_no=mobile_no,verified=True)
            #mail_triger(str(user.id), request)  # both mail and notification will be sent here


        else:
            userinfo = user.userinfo



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




        if is_request_web(request):
            login(request,user=userinfo.user_id,backend="django.contrib.auth.backends.ModelBackend")

        access = is_user_community_part(usr['id'])
        context = {'user': usr, 'has_tags': has_tags,'access':access}

    return context

def login_with_facebook(request,res,json_to_save,login_type="facebook"):

    '''function to login with facebook'''

    res = res['login_json']
    email = res['email']
    # converting email to lower case and removing unwanted space
    email = email.lower().strip()
    user = get_user_from_email(email)

    if not user:
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
        mobile_no = res['mobile_no'] if 'mobile_no' in res else None
        save_user_primary_email(user, res['email'], mobile_no=mobile_no, verified=True)
        mail_triger(str(user.id), request)  # both mail and notification will be sent here
    else:
        userinfo = user.userinfo

        # get serialized user object

    usr = UserinfoSerializer(userinfo)
    # see if user has tags or not
    has_tags = userinfo.has_tags

    # saving the OS type of user (Android,iOS,WEB)
    request_type = get_request_type(request)
    if request_type:
        Userinfo.objects.filter(user_id=usr['id']).update(mobile_os=request_type)

    #login in when the request is web
    if is_request_web(request):
        login(request, user=userinfo.user_id, backend="django.contrib.auth.backends.ModelBackend")

    # User asscoaited tags if any present
    if has_tags:
        tags = get_user_lpig_tags(usr['id'])
        usr['tags'] = tags


    access = is_user_community_part(usr['id'])
    context = {'user': usr, 'has_tags': has_tags, 'access': access}
    return context

def login_with_linkedin(request,res,json_to_save,login_type="linkedIn"):

    '''login with linkedIn '''
    res = res['login_json']
    # if user is logging in with linkedIn
    email = res['email']['elements'][0]['handle~']['emailAddress']

    user = get_user_from_email(email)

    if not user:

        user_name = res['firstName']['localized']['en_US'] + " " + res['lastName']['localized']['en_US']
        user = create_user(user_name=user_name, email=email, id=res['id'])

        if 'profilePicture' in res:
            profile_picture = upload_image_to_firebase(
                res['profilePicture']['displayImage~']['elements'][2]['identifiers'][0]['identifier'], user.id)
        else:
            profile_picture = 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'

        userinfo = create_userinfo(user=user, email=email, user_name=user_name,
                                   profile_picture=profile_picture, login_type=login_type,
                                   json_to_save=json_to_save)
        mobile_no = res['mobile_no'] if 'mobile_no' in res else None
        save_user_primary_email(user, res['email'], mobile_no=mobile_no, verified=True)
        #mail_triger(str(user.id), request)  # both mail and notification will be sent here

    else:
        userinfo = user.userinfo

    usr = UserinfoSerializer(userinfo)
    # see if user has tags or not
    has_tags = userinfo.has_tags

    # saving the OS type of user (Android,iOS,WEB)
    request_type = get_request_type(request)
    if request_type:
        Userinfo.objects.filter(user_id=usr['id']).update(mobile_os=request_type)

    if has_tags:
        tags = get_user_lpig_tags(usr['id'])
        usr['tags'] = tags


    access = is_user_community_part(usr['id'])
    context = {'user': usr, 'has_tags': has_tags, 'access': access}
    #print(context)
    return context

def login_with_apple(request,res,json_to_save,login_type="apple"):

    '''function to login with apple'''
    # if user is logging in with Apple
    res = res['login_json']
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
        mobile_no = res['mobile_no'] if 'mobile_no' in res else None
        save_user_primary_email(user, res['email'], mobile_no=mobile_no, verified=True)
       # mail_triger(str(user.id), request)  # both mail and notification will be sent here

    else:
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

    access = is_user_community_part(usr['id'])
    context = {'user': usr, 'has_tags': has_tags, 'access': access}
    return context

def custom_login(request,res,login_type="custom"):

    context = {}
    mobile_no=res['mobile_no']
    country_code = res['country_code']
    mobile_no = int(str(country_code) + str(mobile_no))

    user_instance = None

    profile = res['user']

    name = profile['name']
    email = profile['email'] if 'email' in profile else ''
    email_exists = get_user_from_email(email)

    if email_exists:
        context['user'] = UserinfoSerializer(email_exists.userinfo)
        context['has_tags'] = email_exists.userinfo.has_tags
        context['access'] = is_user_community_part(context['user']['id'])
        context['email_exists'] = True

        return context

    image_url = profile['image_url'] if 'image_url' in profile else PROFILE_DEFAULT

    user_instance = create_custom_user(name,mobile_no,email,image_url,login_type)

    usr = UserinfoSerializer(user_instance.userinfo)
    # see if user has tags or not
    has_tags = user_instance.userinfo.has_tags

    # saving the OS type of user (Android,iOS,WEB)
    request_type = get_request_type(request)
    if request_type:
        Userinfo.objects.filter(user_id=user_instance.id).update(mobile_os=request_type)


    context['user'] = usr
    context['has_tags'] = has_tags
    context['access'] =  is_user_community_part(usr['id'])
    context['email_exists'] = True if email_exists else False


    return context


def create_custom_user(name,mobile_no,email,image_url,login_type):

    has_mobile_no = userEmails.objects.filter(mobile_no=mobile_no)
    user_name = name + "_"+str(mobile_no)

    if not has_mobile_no.exists():

        # creating user instance
        user_instance = User()
        user_instance.username = user_name
        user_instance.save()

        #creating userinfo instance

        userinfo_instance = Userinfo()
        userinfo_instance.name = name
        userinfo_instance.email = email
        userinfo_instance.image_link = image_url
        userinfo_instance.login_type = login_type
        userinfo_instance.login_json = None
        userinfo_instance.created_at = time.time()
        userinfo_instance.user_id = user_instance
        userinfo_instance.save()

        #creating user email
        save_user_primary_email(user_instance,email,mobile_no,email_states.NON_PRIMARY)


        #send verification mail for email
        verification_details = generate_tokens_for_email(user_instance, email, email_state=email_states.NON_PRIMARY)

        # sending a email from template
        send_verification_mail_for_email_sync(user_name=user_instance.userinfo.name,
                                                    verification_link=verification_details['verify_url'], email=email)


        return user_instance

    return has_mobile_no[0].user


def generate_otp(request):

    user_id = settings.GHUPSHAP_USER_ID
    password = settings.GHUPSHAP_PASSWORD

    mobile_no = request.GET.get('mobile_no')
    country_code = request.GET.get('country_code')

    mobile_no = str(country_code) + str(mobile_no)

    email = request.GET.get('email')

    msg = """Your%20OTP%20code%20is%20%25code%25"""
    generate_url = """http://enterprise.smsgupshup.com/GatewayAPI/rest?userid=%s&password=%s&method=TWO_FACTOR_AUTH&v=1.1&phone_no=%s&msg=%s&format=text&otpCodeLength=4&otpCodeType=NUMERIC"""%(str(user_id),str(password),mobile_no,msg)
    response = rqst.get(generate_url)


    # if email:
    #     generate_url = """http://enterprise.smsgupshup.com/GatewayAPI/rest?userid=%s&password=%s&method=TWO_FACTOR_AUTH&v=1.1&email=%s&msg=%s&format=text&otpCodeLength=4&otpCodeType=NUMERIC""" % (
    #     str(user_id), str(password), email, msg)
    #     response = rqst.get(generate_url)
    #     print(response.content)

    return JsonResponse({'success':True})


def verify_otp(request):


    mobile_no = request.GET.get('mobile_no')
    country_code = request.GET.get('country_code')

    mobile_no = str(country_code) + str(mobile_no)

    otp = request.GET.get('otp')
    email_id = request.GET.get('email_id')

    user_id = settings.GHUPSHAP_USER_ID
    password = settings.GHUPSHAP_PASSWORD

    verify_url = """http://enterprise.smsgupshup.com/GatewayAPI/rest?userid=%s&password=%s&method=TWO_FACTOR_AUTH&v=1.1&phone_no=%s&otp_code=%s"""%(str(user_id),str(password),str(mobile_no),str(otp))
    response = rqst.get(verify_url)

    success = False

    if response.status_code == 200:
        success = True
        response = response.text
        response_list = response.split("|")
        if response_list[0].strip() == "error":
            success = False


    context = {}
    context['success'] = success
    if not success:
        context['error_message'] = response
    context['profile_exists'] = userEmails.objects.filter(mobile_no=mobile_no).exists()

    return JsonResponse(context)



def save_user_primary_email(user_instance,email,mobile_no=None,verified=False,email_state=email_states.PRIMARY):

    '''function to save primary email of user for communications'''

    user_email_instance = userEmails()
    user_email_instance.user = user_instance
    user_email_instance.email_state = email_state
    user_email_instance.email = email
    user_email_instance.mobile_no = mobile_no
    user_email_instance.verified = verified
    user_email_instance.save()

def get_user_from_email(email):

    '''function to get user instance from email'''
    if not email:
        return None

    user = None
    user_emails = userEmails.objects.filter(email=email)
    if user_emails.exists():
        instance = user_emails[0]
        user = instance.user
    else:
        user = User.objects.filter(email=email)
        if user.exists():
            user = user[0]

    return user


def is_user_community_part(user_id):

    '''function to tell whether the user is a part of any community or nor'''

    members_filter = Members.objects.filter(member_id=user_id).filter(
        Q(state=member_states.ADMIN)|Q(state=member_states.TEMP_ADMIN)|
        Q(state=member_states.MEMBER)|Q(state=member_states.KNOWN_NOMINATED_PROMOTER)|Q(state=member_states.PROFILE_UNAVAILABLE))

    return members_filter.exists()

def limit_access(request):

    '''function to limit the access of app and sending details on web screen'''

    member_id = get_member_id_from_headers(request)
    try:
        user_instance = User.objects.get(id=member_id)
    except:
        return {}
    context ={}

    context['header_image'] = LIMIT_ACCESS_HEADER_IMAGE
    context['image'] = LIMIT_ACCESS_IMAGE
    context['title'] = "You are on the waiting list!"
    context['sub_title'] = "Your application to join this community has been submitted. You will have access to your community and other awesome features on this app as soon as you are approved."

    members_filter =  Members.objects.filter(member_id=member_id).filter(state=member_states.PENDING_MEMBER)

    community_list = []
    for member in members_filter:
        community_instance = member.community_id
        community = CommunitySerializer(community_instance)

        community_creator = get_community_creator(community_instance)
        if community_creator:
            community['created_by'] = community_creator

        community_list.append(community)

    context['communities'] = community_list

    access = is_user_community_part(member_id)
    context['access'] = access


    if not community_list:
        context['title'] = "Important Message"

        platform_code = get_platform_code_from_headers(request)

        if platform_code == "an":

            context['sub_title'] = """Access to this app is restricted to invited members only. The login credentials you used (<font color='#00897b'>%s</font>) seems to be missing from our list of invited members.
    
    If you are a community builder and you wish to receive an invite, do fill out the following form:"""%(user_instance.userinfo.email)

        else:

            context['sub_title'] = """Access to this app is restricted to invited members only. The login credentials you used (%s) seems to be missing from our list of invited members.

            If you are a community builder and you wish to receive an invite, do fill out the following form:""" % (
                user_instance.userinfo.email)


    return JsonResponse(context)

def get_community_creator(community_instance):

    '''function to get the creator of community'''
    member_filter = Members.objects.filter(community_id=community_instance,state=member_states.ADMIN).order_by('id')
    created_by=""
    if member_filter.exists():
        promoter_instance = member_filter[0].member_id
        created_by = promoter_instance.userinfo.name

    return created_by

@csrf_exempt
def skip_community(request):

    '''api to skip the community'''
    member_id = get_member_id_from_headers(request)
    community_id = request.POST.get('community_id')

    #adding the members data
    member_filter = Members.objects.filter(member_id=member_id,community_id=community_id)
    user_instance = User.objects.get(id=member_id)
    community_instance = Community.objects.get(id=community_id)

    if not member_filter.exists():
        member_instance = Members()
        member_instance.member_id = user_instance
        member_instance.community_id = community_instance
        member_instance.state = member_states.PROFILE_UNAVAILABLE
        member_instance.created_at=time.time()
        member_instance.save()

    if not is_member_engage(community_id,member_id):
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.PROFILE_UNAVAILABLE
        engage.click_state = click_states.SKIP_COMMUNITY
        engage.save()
        
    set_state_for_onboarding_chatroom(community_instance,user_instance.id,request)

    #sleeping for 2 hours to remind user to complete profile via notification
    try:
        community_instance = Community.obejcts.get(id=community_id)
        community_state = get_state_of_community(community_instance)
        send_notification_to_incomplete_profile.delay(user_id,community_id,community_state,community_name,time_in_s=7200)
    except:
        print("some error occured")
    #updating the member joined level
    set_levels_on_ctc(community_instance,"Level 2")
    return JsonResponse({'success':True})


def get_state_of_community(community):

    if community.hide_community:
        return int(community.hide_community)
    return 0



def members_state(request,req_dict=None):

    '''This function gives the state of user.Get Api'''

    if not req_dict:
        member_id = request.GET.get('member_id')
        community_id = request.GET.get('community_id')
        collabcard_id = request.GET.get('collabcard_id')

        if collabcard_id and not community_id:
            card = Collabcard.objects.get(pk=collabcard_id)
            community_id = card.community.id

    else:
        member_id=req_dict['member_id']
        community_id = req_dict['community_id']
    # if not collabcard_id.isdigit():
    #     return JsonResponse({'state':0})


    state = 0
    tool_state = 0
    query_set = Members.objects.filter(member_id=member_id, community_id=community_id)
    community_instance=Community.objects.get(id=community_id)

    community_state = get_state_of_community(community_instance)

    is_tool_state = False

    if community_state == community_states.PRIVATE or community_state == community_states.PILOT_ACTIVE or community_state ==  community_states.WHATSAPP or community_state == community_states.HIDDEN:
        is_tool_state = True

    user_email = ""
    ref_members=[]
    edit_required = False
    actions_required = False
    created_at = 0

    if query_set.exists():
        data = query_set[0]
        is_member = False
        tool_state = 0
        state = data.state

        if data.created_at > 0:
            created_at =  time.strftime('%A, %b %d', time.localtime(data.created_at))


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




    json_response = {
                   'state': state,
                   'tool_state': 1,
                   'edit_required': edit_required,
                   'created_at': created_at
                   }


    if state == member_states.PENDING_MEMBER:
        json_response['member_direction_lock'] = get_data_for_filter_pop_ups(email=user_email)

    if state == member_states.ADMIN and (community_state == community_states.PRIVATE or community_state ==  community_states.WHATSAPP or community_state == community_states.HIDDEN):
        if actions_required:
            promoter_name = query_set[0].member_id.userinfo.name
            json_response['community_levels'] = get_create_community_actions(community_id,promoter_name)


    json_response['member'] = get_user_profile(member_id,community_id)
    json_response['member']['state'] = state

    if req_dict:
        return json_response
    return JsonResponse(json_response)


def get_create_community_actions(community_id,promoter_name):

    level_filter = communityLevels.objects.filter(community=community_id).order_by('id')

    actions = {}
    levels =  []

    actions['header'] = """Welcome to your community, %s"""%(promoter_name)
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
    context={}

    member_id=get_member_id_from_headers(request)
    if not member_id:
        context['success'] = False
        context['error_message'] = "Send member id in headers"
        return JsonResponse(context)


    community_id = request.POST.get('community_id',None)
    if not community_id:
        context['success'] = False
        context['error_message'] = "Send community_id as post params"
        return JsonResponse(context)

    type = request.POST.get('type',None)
    if not type:
        context['success'] = False
        context['error_message'] = "Send type as post params"
        return JsonResponse(context)


    is_promoter = is_member_promoter(community_id=community_id,member_id=member_id)

    if type == "community_actions" and is_promoter:
        Members.objects.filter(community_id=community_id,member_id=member_id).update(actions_required=False)
        context['success'] = True
        return JsonResponse(context)

    #handling false case
    context['success'] = False
    return JsonResponse(context)


@csrf_exempt
def push(request):
    '''This function is used to insert fcm token to the database in order to generate notifications from database'''

    member_id = request.GET.get('member_id', '')
    token = request.GET.get('token', '')
    if member_id:
        is_member = Userinfo.objects.filter(user_id=member_id)
    else:
        is_member = None

    info_logger.info("Push Notification hit without member id")
    success = False
    if is_member:

        success = True
        # if not is_member[0].fcm_token:
        #     send_welcome_mail.delay(member_id)
        fcm_token = Userinfo.objects.filter(user_id=member_id).update(fcm_token=token)

        info_logger.info("Push Notification hit with member id")
        info_logger.info(member_id)
        info_logger.info(token)
        info_logger.info(fcm_token)


    return JsonResponse({'success': success})


def config(request):
    '''function to update the version number of android for a user profile'''
    headers = request.META
    if 'HTTP_X_MEMBER_ID' in headers and 'HTTP_X_VERSION_CODE' in headers:
        member_id = headers['HTTP_X_MEMBER_ID']
        version_code = headers['HTTP_X_VERSION_CODE']

        Userinfo.objects.filter(user_id=member_id).update(version_code=version_code)
        log = """Version code updated for user %s""" % (str(member_id))
        info_logger.info(log)
        # title="App Update"
        # message="Update to latest version 2.2.1"
        # cta_text="Update"
        # cancelable=True
        # cta_link="""https://play.google.com/apps/testing/com.collabmates"""
        # cta_link=quote(cta_link)
        # cta="""route://browser?link=%s"""%(cta_link)
        # route="""route://dialog?title=%s&message=%s&cta_text=%s&cta=%s&cancelable=%s"""%(title,message,cta_text,cta,cancelable)
        # info_logger.info(route)
        # return JsonResponse({'success': True,'route':route})

        version_no = App_Update_Info.objects.filter(version_code=version_code)
        version_update = False
        if version_no:
            route = version_no[0].android_route
            version_update = True

    ingest_your_communities = request.GET.get('ingest_your_communities', False)
    info_logger.info(ingest_your_communities)
    # if ingest_your_communities:
    #     update_communities_in_member_engage_table.delay(member_id)
    #     log = """Updated successfull for user=%s""" % (member_id)
    #     info_logger.info(log)
    #     if version_update:
    #         return JsonResponse({'success': True})  # route:route
    #     else:
    #         return JsonResponse({'success': True})
    # error_logger.error("headers are not comming correctly")

    if version_update:
        return JsonResponse({'success': True})  # route:route
    else:
        return JsonResponse({'success': True})


############# functions edit community    ##########################

@csrf_exempt
def edit_community(request):
    '''function to edit the community'''

    community_id = request.GET.get('community_id')
    member_id = get_member_id_from_headers(request)
    community = Community.objects.get(id=community_id)


    if not member_id:
        return JsonResponse({'success':False,'error_message':"Send member id in headers"})
    else:
        member_instance = User.objects.get(id=member_id)

    json_body = json.loads(request.body)

    key = json_body['key']

    if key == 'purpose':
        value = json_body['value']
        edit_community_purpose_collabcard(community_instance=community, member_instance=member_instance, purpose=value)
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



    #saving the updating details for history

    instance = communityUpdate()
    instance.updated_field = key
    instance.updated_time = time.time()
    instance.updated_member = member_instance
    instance.community = community
    instance.save()

    serialized_object = CommunitySerializer(community)
    new_dict = {}
    new_dict.update(serialized_object)

    return JsonResponse({'success': True, 'community': new_dict})


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
        return JsonResponse({'success':False,'error_message':"Send member id in headers"})

    user_instance = User.objects.get(pk=member_id)
    res = json.loads(request.body)

    # error messages

    if 'community_id' not in res:
        return JsonResponse({'success': False, 'error_message': "send community id in request body"})

    if 'questions' not in res:
        return JsonResponse({'success': False, 'error_message': "send questions list"})

    questions_list = res['questions']
    community_instance = Community.objects.get(id=res['community_id'])

    current_questionId_set = set(communityQuestions.objects.filter(community=community_instance).values_list('id',flat=True))
    latest_questionId_set  = set()

    major_change = False
    for question in questions_list:

        if 'id' in question:
            question_instance =communityQuestions.objects.get(pk=question['id'])

            #checking current question for major change
            if question_instance.question_state != question['state']:
                major_change = True

            elif question_instance.value != question['value']:
                major_change = True

            elif (question_instance.optional is True and question['optional'] is False):
                major_change = True



            latest_questionId_set.add(question['id'])

            #updating the question instance
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

        #set is not an empty set major change

        if len(diff) > 0:
            major_change = True
            #updating the removed_state to True if the question is deleted
            communityQuestions.objects.filter(pk__in=diff).update(remove_state=True)

    #updating members state table for editing
    if major_change:
        Members.objects.filter(community_id=community_instance).update(edit_required=True)

    return JsonResponse({'success':True})


def edit_community_purpose_collabcard(community_instance,member_instance,purpose):

    '''function to update the purpose collabcard of community'''
    user_instance = member_instance
    collabcard_filter = Collabcard.objects.filter(community=community_instance,type=card_types.CARD_PURPOSE)

    update_status = collabcard_filter.update(title=purpose,updated_member=user_instance,updated_time=time.time())

    if collabcard_filter.exists():
        card_instance = collabcard_filter[0]
        create_chatroom(card_instance=card_instance,user_instance=user_instance,
                        state=chatroom_states.CHATROOM_PURPOSE_EDIT)
    log="""purpose card updated for community=%s by user=%s"""%(str(community_instance.id),str(member_instance.id))
    info_logger.info(log)
    info_logger.info(update_status)

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
    #print('in all members')
    '''function to send all members of community '''

    context = get_all_members(request)

    if request.accepted_renderer.format == 'html':
        print('in html')
        return render(request, 'filtered_members.html',context)
    else:
        return JsonResponse(context)


def get_all_members(request, req_dict=None):
    '''function to get all members of the community'''

    page = request.GET.get('page', 1)

    if not req_dict:
        community_id = request.GET.get('community_id')
        collabcard_id = request.GET.get('collabcard_id', None)


    else:
        community_id = req_dict['community_id']
        collabcard_id = req_dict['collabcard_id'] if 'collabcard_id' in req_dict else None



    current_user_id = get_member_id_from_headers(request)

    community_instance = Community.objects.get(id=community_id)


    # functionality for user filteration based on options
    context = {}

    if collabcard_id and is_request_web(request):
        members = get_members_data_for_collabcard(collabcard_id, community_id, current_user_id,page_no=page)
        # print(members)
        context = {'members': members['members']}
        return context

    is_filter = request.GET.get('is_filter', False)

    if is_filter == 'true':
        is_filter = True
        member_list = Members.objects.filter(community_id=community_id).filter(
            Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) | Q(
                state=member_states.PROFILE_UNAVAILABLE) | Q(state=member_states.PENDING_MEMBER)).order_by('id')
        member_list = pagination(member_list, page, paginate_by=10)
        filter_list = request.GET.get('filter', None)

        if filter_list:
            filter_list = json.loads(filter_list)
            #info_logger.info(filter_list)
            member_set = get_filtered_users(filter_list, member_list)
            members = get_member_instances(member_list, current_user_id, community_id, is_filter=is_filter,
                                           member_set=member_set)
            if collabcard_id:
                card_members = get_members_data_for_collabcard(collabcard_id, community_id, current_user_id, page_no = page)
                members = get_collabcard_participants(members,card_members['participants'])

        else:
            # is_filter = False
                member_list = Members.objects.filter(community_id=community_id).filter(
                    Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) | Q(
                        state=member_states.PROFILE_UNAVAILABLE) | Q(state=member_states.PENDING_MEMBER)).order_by(
                    'id')
                member_list = pagination(member_list, page, paginate_by=10)
                members = get_member_instances(member_list, current_user_id, community_id)

                if collabcard_id:
                    card_members = get_members_data_for_collabcard(collabcard_id, community_id, current_user_id, page_no = page)
                    members = get_collabcard_participants(members, card_members['participants'],guest=True)

    else:
        # is_filter = False
        member_list = Members.objects.filter(community_id=community_id).filter(
            Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) | Q(
                state=member_states.PROFILE_UNAVAILABLE)).order_by('id')
        member_list = pagination(member_list, page, paginate_by=10)
        members = get_member_instances(member_list, current_user_id, community_id)

    promoter_instance = is_member_promoter(community_instance,current_user_id)

    community = CommunitySerializer(community_instance,promoter_id=promoter_instance)
    context = {'members': members,'community':community}
    return context


def get_member_instances(member_list,current_user_id,community_id,is_filter=False,member_set=None):

    '''function to get members instances from members table'''

    members = []

    for member in member_list:
        member_id = member.member_id.id
        userinfo_serialized_object = UserinfoSerializer(member.member_id.userinfo)
        userinfo_serialized_object['state'] = member.state

        form_response = FormResponseSerilaizer(community_id,member_id , bl=True,
                                               current_user_id=current_user_id)

        if form_response:
            #userinfo_serialized_object['response'] = form_response[0]
            userinfo_serialized_object['question_answers'] = form_response[1]

        if not is_filter:
            members.append(userinfo_serialized_object)
            #pass
        else:
            if member_id in member_set:
                members.append(userinfo_serialized_object)
                #members.append(member_id)

    return members



def get_filtered_users(filter_list,member_list):

    '''function to get filtered users'''



    member_set = set()

    for data in member_list:
        member_set.add(data.member_id.id)

    filter_map={}
    for data in filter_list:
        key_list = []
        question_id = data['question_id']
        if question_id in filter_map:

            key_list = filter_map[question_id]
            key_list.append(data['value'])
            filter_map[question_id] = key_list
        else:
            key_list.append(data['value'])
            filter_map[question_id] = key_list


    distinct_members = {}

    for key,value in filter_map.items():

        question_id = key
        question_set = set()
        for option in value:

            question_filters = questionFilters.objects.filter(filter=option,
                                                              question=question_id)
            for instance in question_filters:
                question_set.add(instance.member.id)
        distinct_members[question_id] = question_set


    for key,value  in distinct_members.items():

       member_set = intersect_sets(member_set,value)





    return member_set


def get_members_data_for_collabcard(card_id,community_id,current_user_id,page_no=1):


    #card_instance = Collabcard.objects.get(id=card_id)

    state_list = [collabcard_states.COLLABCARD_STATE_FOLLOW, collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING,
                  collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING]

    collabcard_state_list = collabcardState.objects.filter(card=card_id).filter(
        state__in=state_list).filter(removed_status=None).order_by('-user_id')



    collabcard_state_list = pagination(collabcard_state_list,page_no,paginate_by=10)
    members = []
    collabcard_participants = []
    for instance in collabcard_state_list:

        user_instance = instance.user

        userinfo_serialized_object = UserinfoSerializer(user_instance.userinfo)
        userinfo_serialized_object['collabcard_state'] = instance.state
        userinfo_serialized_object['is_guest'] = instance.is_guest



        form_response = FormResponseSerilaizer(community_id, user_instance.id, bl=True,
                                               current_user_id=current_user_id)

        if form_response:
            #userinfo_serialized_object['response'] = form_response[0]
            userinfo_serialized_object['question_answers'] = form_response[1]

        members.append(userinfo_serialized_object)

        #sending state also for conserving filter
        temp={}
        temp['user_id'] = user_instance.id
        temp['collabcard_state'] = instance.state
        temp['is_guest'] = instance.is_guest
        temp['member'] = userinfo_serialized_object


        collabcard_participants.append(temp)

    return {'members':members,'participants':collabcard_participants}


def get_collabcard_participants(all_members,collabcard_members,guest=False):

    collabcard_participants = []
    for member in all_members:
        for participant in collabcard_members:
            if member['id'] == participant['user_id']:
                member['collabcard_state'] = participant['collabcard_state']
                collabcard_participants.append(member)


    #sending guest data also
    #print(collabcard_members)
    if guest:
        for data in collabcard_members:

            if data['is_guest']:
                data['member']['state'] = 0
                collabcard_participants.append(data['member'])

    return collabcard_participants


def get_tagging_list(request):

    '''api to get tag list of members'''

    community_id = request.GET.get('community_id')
    chatroom_id = request.GET.get('chatroom_id')


    tagging_list = get_tagging_list_internal(community_id,chatroom_id)



    return JsonResponse({'members':tagging_list})





#functionality for filters

def fetch_filters(request):

    '''api to get all the filtered data'''

    community_id = request.GET.get('community_id')

    member_id = get_member_id_from_headers(request)

    if not member_id:
        return JsonResponse({'success':False,'error_message':"Member id is not coming in header"})

    send_empty_list = False

    member_list = Members.objects.filter(community_id=community_id,member_id=member_id)
    if member_list.exists():

        member_state = member_list[0].state
        if member_state == member_states.PENDING_MEMBER:
            send_empty_list=True

    else:
        send_empty_list = True



    if send_empty_list:
        return JsonResponse({'questions': []})


    community_options = communityAnswers.objects.filter(community_id=community_id)

    question_set = set()
    #print("options===",community_options)

    option_list=[]
    for data in community_options:

        question_instance = data.question

        serialized_instance = CommunityQuestionsSerializer(question_instance)

        if serialized_instance['state'] == question_states.CHOICE_SINGLE or serialized_instance['state'] == question_states.CHOICE_MULTIPLE:




            if serialized_instance['id'] not in question_set:
                serialized_instance['value'] = get_user_selected_option_list(serialized_instance['id'])
                question_set.add(serialized_instance['id'])
                option_list.append(serialized_instance)

    return JsonResponse({'questions':option_list})


def get_user_selected_option_list(question_id):

    '''function to get user selected options'''
    filter_list = list(questionFilters.objects.filter(question=question_id).values_list('filter',flat=True).distinct())
    values=""
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

    Userinfo.objects.filter(user_id=member_id).update(secondary_email = email)


    return JsonResponse({'success':True})


def get_data_for_filter_pop_ups(email):

    '''function to get data for filtered pop-ups'''

    member_direction_lock={}

    member_direction_lock['member_directory_lock_title'] = "Member profile not accessible"
    member_direction_lock['member_directory_lock_sub_title'] ="""Your account is pending for approval from the admin. Once the admin approves, you would be able to view the full communtity profile of the user.

Once verified, we will send an email on: """+str(email)
    member_direction_lock['member_directory_lock_negative_title'] = "DISMISS"
    member_direction_lock['member_directory_lock_positive_title'] = "Change EMAIL ID"

    #member_directory_lock_negative_action,member_directory_lock_positive_action

    member_direction_lock['member_directory_lock_email_title'] = "Change Email ID"
    member_direction_lock['member_directory_lock_email_sub_title'] = "Update your email ID below for further communications."
    member_direction_lock['member_directory_lock_email_negative_title'] = "DISMISS"
    member_direction_lock['member_directory_lock_email_positive_title'] = "SUBMIT"

    #member_directory_lock_email_positive_action,member_directory_lock_email_negative_action

    return member_direction_lock


def intersect_sets(set1,set2):

    return set1.intersection(set2)

def invite_members(request):
    ''' function to get members requested to join in a community '''

    member_id = request.GET.get('member_id', None)
    community_id = request.GET.get('community_id', None)

    pend_requests = get_referred_members_of_a_member(community_id, member_id)

    pending_requests = []
    for i in pend_requests:
        user_id = i
        resp = Form_response.objects.filter(community=community_id).filter(user=user_id)
        user = Userinfo.objects.get(user_id=user_id)
        # serilaizing userinfo object
        usr = UserinfoSerializer(user)
        user_response = []
        for j in resp:
            # getting the answers of the users who requested to join
            # for the questions that have been asked while requestiong to join in a community
            response_object = {}
            response_object['key'] = j.data
            response_object['value'] = j.response
            user_response.append(response_object)
        usr['response'] = user_response
        pending_requests.append(usr)
    return JsonResponse({'pending_members': pending_requests})




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



#getting data from headers

def get_member_id_from_headers(request):
    '''function to get member id from headers'''
    headers = request.META

    member_id = None
    if 'HTTP_X_MEMBER_ID' in headers and 'HTTP_X_VERSION_CODE' in headers:
        member_id = headers['HTTP_X_MEMBER_ID']
    elif 'HTTP_X_MEMBER_ID' in headers:
        member_id = headers['HTTP_X_MEMBER_ID']

    return member_id



def get_platform_code_from_headers(request):

    headers = request.META

    platform_code = 0
    if 'HTTP_X_PLATFORM_CODE' in headers:
        platform_code = headers['HTTP_X_PLATFORM_CODE']

    return platform_code


def is_request_web(request):

    '''function to tell if the request is web or not'''

    platform_code = get_platform_code_from_headers(request)
    if platform_code == 0:
        return True

    return False

def check_android_request(request):

    '''function to check whether the request is android or not'''
    headers = request.META

    platform_code = 0
    if 'HTTP_X_PLATFORM_CODE' in headers:
        platform_code = headers['HTTP_X_PLATFORM_CODE']
        if platform_code == "an":
            return True

    return False


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
    #send_mail_after_rank_computation.delay(user_id)  # both mail and notification will be sent here
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
    info_logger.info("fetch report tags api successfulll")
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

        report_instance.save()

        community_url = url + "/community/" + str(collabcard_instance.community.id)
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



def fetch_whatsapp_tool(request):

    '''fetch whatsapp tool page'''

    title="Your WhatsApp community is still not connected well."
    sub_title="Register your group on LikeMinds and get exciting tools to better functioning of your whatsapp group."

    list_points=[]

    point_1={}

    point_1['title'] = "Your group is not discoverable"    #text change
    point_1['sub_title'] = "Make your group discoverable to other relevant members who might be interested in joining your group."

    list_points.append(point_1)


    point_2 = {}
    point_2['title'] = "Group members can't identify each other"
    point_2['sub_title'] = "Your group members can create their profile and share them so that other members can get to know them better."
    list_points.append(point_2)

    point_3={}
    point_3['title']="Not able to create polls on whatsapp?"
    point_3['sub_title'] = "Get the ability to create private polls for your group."
    list_points.append(point_3)

    point_4={}
    point_4['title']="Not able to create events on whatsapp?"
    point_4['sub_title']="Create private events for your group and easier way to access the attending members."

    list_points.append(point_4)

    whatsapp_tool={}
    whatsapp_tool['title']=title
    whatsapp_tool['sub_title']=sub_title
    whatsapp_tool['points']=list_points


    #getting types.object
    community_type_list=communityType.objects.all()
    community_subtype_list = communitySubtype.objects.all()

    types=[]
    for instance in community_type_list:
        temp = communityTypeSerializer(instance)


        sub_type_list = []
        subtype_queryset = communitySubtype.objects.filter(typ=instance.id)

        if subtype_queryset.exists() :
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
    #whatsapp_tool['sub_types'] = sub_types

    master_question_list = masterQuestions.objects.all()
    paginator = Paginator(master_question_list, 50)


    whatsapp_tool['total_master_questions'] = paginator.num_pages



    return JsonResponse(whatsapp_tool)


def fetch_master_questions(request):
    # getting master Questions

    page=request.GET.get('page',1)
    master_question_list = masterQuestions.objects.all().order_by('id')
    master_question_list=pagination(master_question_list,page_number=page,paginate_by=50)
    master_questions = []
    for instance in master_question_list:
        master_questions.append(masterQuestionSerializer(instance))

    return JsonResponse({
        'master_questions':master_questions
    })



#email address verification for syncing new email accounts

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

    email = request.POST.get('email_id',None)
    email_state = request.POST.get('email_state',0)
    if not email:
        context = get_error_context(False,"send a email id in post params")
        return JsonResponse(context)

    verification_details = generate_tokens_for_email(user_instance,email,email_state=email_state)

    #sending a email from template
    send_verification_mail_for_email_sync.delay(user_name=user_instance.userinfo.name,
                                          verification_link=verification_details['verify_url'],email=email)

    return JsonResponse({'success':True})




def generating_verification_link_for_email(token_list,user_id):

    '''function to generate verification link for email and saving the email'''


    token = generate_random(token_list)
    #print(token)
    encrpt_number = encrypt(token)
    user_id = encrypt(user_id)
    #print(user_id)
    verify_url = url + "/email_verify?token="+encrpt_number+"&user="+user_id

    temp={'verify_url':verify_url,'token':token}

    return temp

def generate_tokens_for_email(user_instance,email,email_state=0):

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


        decoded_token = decrypt(token)
        decoded_user = decrypt(user)

        #getting the user instance
        try:
            user_instance = User.objects.get(id=decoded_user)
        except:
            context = get_error_context(False, "User does not exists")
            return HttpResponse(context)

        info_logger.info("Email Verify")
        info_logger.info(decoded_token)
        info_logger.info(decoded_user)
        info_logger.info("\n")

        instance_list = emailTokens.objects.filter(token=decoded_token,user=user_instance)


        if instance_list.exists():
            instance = instance_list[0]
            #print(instance)

            context = {
                'verification': True,
                'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                'facebook_auth_id':settings.SOCIAL_AUTH_FACEBOOK_KEY,
                'firebase_config': settings.FIREBASE_CONFIG
            }

            #if the link is verified
            if (current_time - instance.created_at) <= instance.expire_time:

                email_state = instance.email_state

                if email_state == email_states.PRIMARY:
                    userEmails.objects.filter(user = user_instance).update(email_state = email_states.NON_PRIMARY)

                user_email_list = userEmails.objects.filter(email=instance.email,user=user_instance)

                if not user_email_list.exists():
                    user_email_instance = userEmails()
                    user_email_instance.user = user_instance
                    user_email_instance.email_state = email_state
                    user_email_instance.email = instance.email
                    user_email_instance.save()

                else:
                    user_email_list.update(user=user_instance,email_state=email_state,email=instance.email,verified=True)


                return render(request, 'email_verify_landing.html', context)


            else:
                context['verification'] = False

                return render(request, 'email_verify_landing.html', context)





    return render(request, 'email_verify_landing.html', {'verification':False})




###############################mixpanel events########################################


def get_member_community_status(state):

    member = ""
    if state == 0:
        member = "Guest"
    elif state == 1:
        member = "Promoter"
    elif state == 3:
        member = "Pending Member"
    elif state == 4:
        member = "Member"
    elif state == 7:
        member = "Nominated Promoter"

    return member



def get_event_super_properties_for_mixpanel(user_instance,community_instance):

    '''function to get event super properties for mixpanel'''

    if not user_instance or not community_instance:
        return {}

    context = {}
    user_profile = user_instance.userinfo
    context['name'] = user_profile.name
    context['email'] = user_profile.email
    context['user_unique_id'] = user_instance.id
    context['first_login_date'] = 0 if user_profile.created_at < 0 else time.strftime('%A, %b %d', time.localtime(user_profile.created_at))

    state_data = Members.objects.filter(community_id=community_instance.id,member_id=user_instance.id)
    state = 0
    if state_data.exists():
        state = state_data[0].state

    context['user_community_state'] = get_member_community_status(state)

    followed_count = collabcardState.objects.filter(follow_status=True,user=user_instance).count()
    context['No_of_Chatrooms_Followed'] = followed_count

    communities_count = Members.objects.filter(member_id=user_instance.id).filter(
        Q(state=member_states.MEMBER)|Q(state=member_states.ADMIN)|Q(
            state=member_states.KNOWN_NOMINATED_PROMOTER)).count()
    context['No_of_community_member'] = communities_count


    distinct_cr_count = card_answers.objects.filter(user=user_instance).distinct('card_id').count()
    context['No_of_unique_cr_responded'] = distinct_cr_count


    if settings.IS_BETA:
        context['token'] = "eb1e03c8be370040278bff61a4857608"
    else:
        context['token'] = "7907eb37f46b1ac2908d3881e633a85e"

    return context






