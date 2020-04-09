from __future__ import absolute_import, unicode_literals
from celery import shared_task
import json
import logging
import os
import re
import ast
import time
from datetime import datetime
from random import randint
import requests as rqst
import dateutil.relativedelta
import googlemaps
from celery import shared_task
from collabmates_api.serializers import *
from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import F
from django.db.models import Q
from django.http import HttpResponse
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from togther.forms import *
from togther.models import *
from togther.tasks import send_email_to_proposed_admin, send_mail_after_rank_computation
from togther.views import get_nominated_admin_details
from utility.celery_tasks import (save_community_purpose_card,
                                  update_last_unseen_in_engage_on_card_creation,
                                  update_last_unseen_in_engage,
                                  )
from utility.firebase import update_last_answer_id, upload_image_to_firebase, upload_community_thumbnail, \
    upload_community_files
from utility.states import collabcard_states, member_states, question_states,community_states,deleted_members
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
                           is_member_verified,community_default_image,community_default_thumbnail,

                           )

from .notification import (send_follow_notification, send_notification_to_admins,
                           send_notification_for_join_requests,
                           send_notification_for_new_collabcard_posted,
                           send_notification_to_proposed_admin,
                           send_notification_to_proposer,
                           send_notification_to_eligible_member,
                           send_notification_to_all_admins,
                           send_notification_to_tagged_users,
                           send_poll_or_event_notification,
                           send_notification_to_promoter_of_ig_community,
                           send_notification_to_referrer_of_ig_community,
                           send_notification_to_referrer_of_lg_community,
                           ask_approval_notification,
                           send_notification_for_tool_unlocked_for_live_community,
                           send_notification_for_tool_unlocked_for_pilot)
from .raw_queries import compute_rank
from .tasks import send_email_to_nominated_admin, send_email_for_new_collabcard_posted, send_welcome_mail
from django.contrib.auth import login

from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.decorators import api_view, renderer_classes



# CACHE_TTL = getattr(settings, 'CACHE_TTL', cache_timeout)

url = settings.URL
# url='http://localhost:8000'
error_logger = logging.getLogger("error_logger")
info_logger = logging.getLogger("info_logger")


# /api/communities?category_id=&member_id=

############# functions for community api ##########################
def communities(request):
    ''' function to get all the communities '''

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
        if each_community.member_state == 1 or each_community.member_state == 2 or each_community.member_state == 4 or each_community.member_state == 7:
            community['collabcard_unseen'] = each_community.last_unseen_count
        else:
            community['collabcard_unseen'] = 0
        if community['state'] != community_states.DELETED:
            my_community.append(community)

    return JsonResponse({'your_communities': my_community})


############# functions for  community detail screen ##########################

def get_community_card_details(each_community, user_id):
    community = each_community.community_id
    serialized_object = CommunitySerializer(community)
    serialized_object['is_member'] = ''
    new_dict = {}
    new_dict.update(serialized_object)
    is_admin = False
    # community = Community.objects.get(id=new_dict['id'])
    # community_admins = Members.objects.filter(community_id=each_community.community_id.id).filter(member_id=user_id)
    pending_requests = Members.objects.filter(community_id=community).filter(state=3)

    if (each_community.state == 1 or each_community.state == 2):
        new_dict['pending_members_count'] = pending_requests.count()
        is_admin = True
    else:
        new_dict['pending_members_count'] = 0
    new_dict['is_admin'] = is_admin

    # get time stamp
    if str(community.updated_at) == "-9223372036854775808":
        time_text = ""
    else:
        # getting time stamp for the latest card
        time_text = get_time_text(community.updated_at)

    new_dict['updated_at'] = time_text
    # getting the unseen cards
    # getting the total cards of a community
    total_collabcards = Collabcard.objects.filter(community=community).values('id').order_by('-id')
    print(total_collabcards)
    # getting seen collabcards by the user from that community
    seen_collabcard = collabcard_seen.objects.filter(community=community, user=user_id
                                                     ).values('card_id').order_by('-card_id')
    print(seen_collabcard)
    # unseen cards count
    if (total_collabcards.count() - seen_collabcard.count()) <= 0:
        # if zero or less than zero , unseen card count = 0
        new_dict['collabcard_unseen'] = 0
    else:
        new_dict['collabcard_unseen'] = (total_collabcards.count() - seen_collabcard.count())
    # getting unseen card list by getting the difference between total cards and seen cards
    unseen_list = total_collabcards.difference(seen_collabcard).values('id').order_by('-id')
    print(unseen_list)
    if total_collabcards.count() > 0:
        # if community has atleast one card
        if unseen_list.count() != 0:
            # if the unseen cards are present
            # show the latest unseen cards text
            card = Collabcard.objects.get(id=unseen_list.values('id')[0]['id'])

        else:
            # if no unseen cards , show latest card text
            card = Collabcard.objects.get(id=total_collabcards.order_by('id')[0]['id'])
        # show details of the latest card or latest unseen card
        # get json form of card object
        collabcard = CollabcardSerializer(card, user_id, community)

        new_dict['collabcard'] = collabcard

        # get user details who posted the latest card
        user = Userinfo.objects.get(user_id=card.user)
        # get json form of userinfo object
        usr = UserinfoSerializer(user)

        collabcard['member'] = usr

    return new_dict


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


def community(request, community_id):
    ''' Community detail page '''

    community = Community.objects.get(id=community_id)
    member_id = get_member_id_from_headers(request)

    is_promoter = False
    block_leave_community = False
    member_list = Members.objects.filter(community_id=community, member_id=member_id)

    if member_list.exists():

        state = member_list[0].state

        if state == member_states.ADMIN:
            is_promoter = True
            block_leave_community = True
            promoter_id = member_list[0].member_id

        if state == member_states.PENDING_MEMBER:
            block_leave_community = True
    else:
        block_leave_community = True



    serialized_object = CommunitySerializer(community)
    new_dict = {}

    community_state = get_state_of_community(community)
    if member_id and (community_state== community_states.PILOT or community_state == community_states.PILOT_ACTIVE):
        serialized_object['share_url'] = serialized_object['share_url'] + "?ref_id=" + str(member_id)
    elif community_state== community_states.PRIVATE or community_state == community_states.HIDDEN:
        serialized_object['share_url'] = serialized_object['share_url'] + "?cta=share"



    if is_promoter:
        serialized_object['private_link'] = generate_private_link(community_instance=community,
                                                                  promoter_instance=promoter_id)

    # form a dictionary of community objects
    new_dict.update(serialized_object)
    if community:
        community_type = is_IG_community(community)
        if not community_type:
            new_dict['share_text_admin'] = """Hi, I am trying to gather %s community on LikeMinds. It will be good if you can join it.\n""" % (new_dict['name'])
            new_dict['share_text_member'] = """I recently joined %s community on LikeMinds. It will be good if you also join this community.\n""" % (new_dict['name'])
            new_dict['share_text_anonymous'] = """I recently discovered %s community on LikeMinds. You can join this community using this link.\n""" % (new_dict['name'])
        else:
            new_dict['share_text_admin'] = """Hi, I am trying to gather %s community on CollabMates. It will be fun if you can join it.\n""" % (new_dict['name'])
            new_dict['share_text_member'] = """I recently joined %s community on CollabMates. It will be fun if you also join this community.\n""" % (new_dict['name'])
            new_dict['share_text_anonymous'] = """I recently discovered %s community on CollabMates. You can join this community using this link.\n""" % (new_dict['name'])
    new_dict['min_referrer_member'] = eligibility_count

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
        return JsonResponse({'community': new_dict,'leave_community':temp})

    return JsonResponse({'community': new_dict})




def similar_community(request, community_id):
    '''function to return similar communitites'''
    body = request.GET
    user_id = body['member_id']
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
    return JsonResponse({'communities': community})


############# functions for  join community  screen ##########################

# /api/community/264/questions
def join_community(request, community_id):

    '''function to get questions of community'''
    data = communityQuestions.objects.filter(community=community_id).order_by("id")
    community_instance = Community.objects.get(id=community_id)
    community = CommunitySerializer(community_instance)

    reqd_info = []
    first_question = False
    for i in data:
        if not first_question:
            ques = {'question': i.question_title,
                    'question_state': 3,
                    }
            if i.question_state == 1:
                try:
                    ques['dropdown_list'] = json.loads(i.value)
                except:
                    ques['dropdown_list'] = i.value.split("$#")

            first_question = True
        else:

            ques = {'question': i.question_title}
            if i.question_state == 1:
                try:
                    ques['dropdown_list'] = json.loads(i.value)
                except:
                    ques['dropdown_list'] = i.value.split("$#")
                ques['question_state'] = 1
            elif i.question_state == 2:
                try:
                    ques['dropdown_list'] = json.loads(i.value)
                except:
                    ques['dropdown_list'] = i.value.split("$#")
                ques['question_state'] = 2  # multiselect for android only
            elif i.question_state == 0:
                ques['question_state'] = 0  # no limit on answer condition for android

        reqd_info.append(ques)


    return JsonResponse({'questions': reqd_info,'community':community})


# /api/join_community?member_id=&community_id=
@csrf_exempt
def join_community_responses(request):

    '''function to join community'''

    res = json.loads(request.body)
    user_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')

    if 'questions' not in res:
        res['questions'] = None

    community = Community.objects.get(id=community_id)

    is_private=False
    if community.hide_community == '0' or community.hide_community == '1':
        is_private=True

    is_ig=is_IG_community(community)
    is_lg=is_LG_or_LP_community(community)


    user = User.objects.get(id=user_id)

    if 'ref_id' in res:
        ref_id = res['ref_id']
    else:
        ref_id = request.GET.get('ref_id', None)

    if  is_ig or is_lg == None:                                 #if the community is ig community or is_lg hometown community
        print("Inside IG")
        join_ig_communities(request,res,community,user,ref_id)


        if not ref_id:
            # sending mail to nipun and harsh
            new_member_request.delay(member_id=user_id, community_id=community_id, ref_id=None,
                                     form_response=res['questions'])
        else:
            # sending mail to nipun and harsh
            new_member_request.delay(member_id=user_id, community_id=community_id, ref_id=ref_id,
                                     form_response=res['questions'])

        return JsonResponse({'success':True})

    elif is_lg:
        print("LG community")
        join_lg_communities(request, res, community,user,ref_id)

        if not ref_id:
            # sending mail to nipun and harsh
            new_member_request.delay(member_id=user_id, community_id=community_id, ref_id=None,
                                     form_response=res['questions'])
        else:
            # sending mail to nipun and harsh
            new_member_request.delay(member_id=user_id, community_id=community_id, ref_id=ref_id,
                                     form_response=res['questions'])
        return JsonResponse({'success': True})
    elif is_private:
        join_promoter_created_community(res,community,user)
        new_member_request.delay(member_id=user_id, community_id=community_id, ref_id=ref_id,
                                 form_response=res['questions'])

    return JsonResponse({'success': True})


#old api support
def join_ig_communities(request,res,community,user,ref_id):

    '''join api for ig communities'''

    member_instance = Members.objects.filter(member_id=user, community_id=community)
    if not member_instance:
        # making a member instance
        member = Members()
        member.member_id = user
        member.community_id = community
        member.state = member_states.MEMBER
        member.created_at=time.time()
        member.save()

        # saving questions
        if 'questions' in res:
            info_logger.info(res['questions'])
            for i in res['questions']:
                response = communityAnswers.objects.filter(question_title=i['key'], member=user, community=community)
                if not response.exists():
                    question_list=communityQuestions.objects.filter(question_title=i['key'])
                    response = communityAnswers()
                    response.question_title = i['key']
                    response.question_answer = i['value']
                    response.member = user
                    response.community = community
                    if question_list:
                        response.question=question_list[0]
                    response.save()
        else:
            res['questions'] = [{}]

        # creating an introduction card
        community_id = community.id
        member_id =user.id
        introduction_question, introduction_answer = auto_create_collabcard(user, community)
        print(introduction_answer)
        req_dict={

            'member_id':member_id,
            'community_id':community_id,
            'title':introduction_answer,
            'type':1,
            'create_intro':1
        }
        create_card(request,req_dict=req_dict)
        #saving the referal detail and sending notifications for refered members

        community.updated_at=time.time()
        community.members_count=community.members_count + 1
        community.save()

        is_live = False
        if community.hide_community == '4':
            is_live = True

        if community.members_count == ig_members_count:
            community.hide_community='4'
            community.save()
            send_notification_for_tool_unlocked_for_pilot.delay(community_id=community.id)

        send_notification_for_join_requests.delay(community_id, True, member_id)
        log="""Community joined for community_id=%s and member_id=%s"""%(community.id,user.id)

        info_logger.info(log)


        if ref_id:
            referer_instance = User.objects.get(pk=ref_id)
            refer = Referal.objects.filter(member=referer_instance,
                                           invited_member=user,
                                           community=community)

            #send notification for joining community
            send_notification_to_referrer_of_ig_community.delay(community_id=community_id, community_name=community.name,
                                                          referrer_id=ref_id,
                                                          member_name=user.userinfo.name,
                                                          community_state=community.hide_community)


            if not refer.exists():
                refer = Referal(member=referer_instance,
                                invited_member=user,
                                community=community)
                refer.save()

            total_referals = get_referred_members_of_a_member(community.id,ref_id)
            total_referal_count = len(total_referals)


            if total_referal_count >= eligibility_count:
                admin = Members.objects.filter(community_id=community, member_id=referer_instance)

                if admin.exists():
                    Members.objects.filter(community_id=community, member_id=referer_instance).update(state=member_states.ADMIN)
                    Member_Engage.objects.filter(member_id=referer_instance, community_id=community).update(
                        member_state=member_states.ADMIN)


            if is_live:
                send_notification_for_tool_unlocked_for_live_community.delay(referer_id=ref_id, referal_count=total_referal_count,
                                                    community_id=community.id,
                                                    community_name=community.name,
                                                    community_state=community.hide_community)



def join_lg_communities(request,res,community,user,ref_id):

    '''function to join lg communities'''

    member_instance = Members.objects.filter(member_id=user, community_id=community)
    if not member_instance:
        # making a member instance
        member = Members()
        member.member_id = user
        member.community_id = community
        member.state = member_states.PENDING_MEMBER
        if ref_id:
            member.ask_member_id=ref_id
        member.created_at = time.time()
        member.save()

        introduction_answer=""
        # saving questions
        if 'questions' in res:
            info_logger.info(res['questions'])
            for i in res['questions']:
                response = communityAnswers.objects.filter(question_title=i['key'], member=user,
                                                           community=community)
                if not response.exists():
                    question_list = communityQuestions.objects.filter(question_title=i['key'])
                    response = communityAnswers()
                    response.question_title = i['key']
                    response.question_answer = i['value']
                    response.member = user
                    response.community = community
                    if question_list:
                        response.question = question_list[0]
                    response.save()

                if not introduction_answer:
                    introduction_answer=i['value']
        else:
            res['questions'] = [{}]

        creating_collabcard_for_lg_communities(community, user, introduction_answer, ref_id=ref_id)


       #creating members engage

        engage = Member_Engage()
        engage.member_id = user
        engage.community_id = community
        engage.updated_at = time.time()
        engage.member_state = member_states.PENDING_MEMBER
        engage.member_referral="Your profile is being verified"
        engage.save()



        #updating the pending members count in engage table if the ref_id member is verified
        if ref_id:

            member_queryset=Member_Engage.objects.filter(community_id=community,member_id=ref_id).filter(
                Q(member_state=member_states.ADMIN)|Q(member_state=member_states.MEMBER))
            is_verified = member_queryset.exists()
            if is_verified:
                member_queryset.update(pending_members=F('pending_members')+1)
            send_notification_to_referrer_of_lg_community(community_id=community.id, community_name=community.name,
                                                          referrer_id=ref_id,
                                                          member_name=user.userinfo.name, community_state=community.hide_community,
                                                          is_verified=is_verified)


        log = """Request in LG community where community_id=%s and member_id=%s""" % (community.id, user.id)
        print(log)



def join_promoter_created_community(res,community,user):

    '''function to join promoter created community'''

    member_instance = Members.objects.filter(member_id=user, community_id=community)
    if not member_instance:
        # making a member instance
        member = Members()
        member.member_id = user
        member.community_id = community
        member.state = member_states.PENDING_MEMBER
        member.created_at = time.time()
        member.save()

        introduction_answer = ""
        # saving questions
        if 'questions' in res:
            info_logger.info(res['questions'])
            for i in res['questions']:
                response = communityAnswers.objects.filter(question_title=i['key'], member=user,
                                                           community=community)
                if not response.exists():
                    question_list = communityQuestions.objects.filter(question_title=i['key'])
                    response = communityAnswers()
                    response.question_title = i['key']
                    response.question_answer = i['value']
                    response.member = user
                    response.community = community
                    if question_list:
                        response.question = question_list[0]
                    response.save()

                if not introduction_answer:
                    introduction_answer = i['value']
        else:
            res['questions'] = [{}]

        engage = Member_Engage()
        engage.member_id = user
        engage.community_id = community
        engage.updated_at = time.time()
        engage.member_state = member_states.PENDING_MEMBER
        engage.save()
        update_pending_member_count_in_engage(community)

        #sending notifications to the admin of the community
        name=user.userinfo.name
        send_notification_to_admins.delay(community.id, name)



def questions(request):

    '''api to send the questions for a particular community'''

    community_id = request.GET.get('community_id')
    data = communityQuestions.objects.filter(community=community_id).order_by("id")
    community_instance = Community.objects.get(id=community_id)
    community = CommunitySerializer(community_instance)


    questions = []

    for question in data:
        serialized_question = CommunityQuestionsSerializer(question)
        questions.append(serialized_question)

    return JsonResponse({'questions': questions, 'community': community})




#version support apis
@csrf_exempt
def join_community_responses_version_1(request):


    info_logger.info("Join community request\n")
    info_logger.info(request.body)
    res = json.loads(request.body)

    info_logger.info("Join community res\n")
    info_logger.info(res)
    info_logger.info("\n")
    community_id = res['community_id']
    print(community_id)
    community_instance = Community.objects.get(id=community_id)
    community=community_instance


    user_id = get_member_id_from_headers(request)
    if not user_id:
        user_id = request.GET.get('member_id', None)

    #for whatsapp community

    community_state = get_state_of_community(community_instance)

    if community_state == community_states.WHATSAPP:
        info_logger.info("whats app communtiy")

        join_whatsapp_community(res,request)
        return JsonResponse({'success': True})

    is_private = False
    if community_state == community_states.PRIVATE or community_state == community_states.HIDDEN:
        is_private = True

    is_ig = is_IG_community(community)
    is_lg = is_LG_or_LP_community(community)

    user = User.objects.get(id=user_id)

    if 'ref_id' in res:
        ref_id = res['ref_id']
    else:
        ref_id = request.GET.get('ref_id', None)

    if is_ig or is_lg == None:  # if the community is ig community or is_lg hometown community
        print("Inside IG")
        join_ig_communities_version_1(request, res, community, user, ref_id)
        if ref_id:
            referer_instance = User.objects.get(pk=ref_id)
            refer = Referal.objects.filter(member=referer_instance,
                                           invited_member=user,
                                           community=community)
            if not refer.exists():
                refer = Referal(member=referer_instance,
                                invited_member=user,
                                community=community)
                refer.save()

            # send notification for joining community
            send_notification_to_referrer_of_ig_community(community_id=community_id, community_name=community.name,
                                                              referrer_id=ref_id,
                                                              member_name=user.userinfo.name,
                                                              community_state=community.hide_community)

            total_referals = Referal.objects.filter(member=referer_instance,
                                                    community=community)

            total_referal_count = total_referals.count()

            # send_notification_for_tool_unlocked.delay(referer_id=ref_id,
            #                                           joined_member_name=user.userinfo.name,
            #                                           referal_count=total_referal_count, community_id=community.id,
            #                                           community_name=community.name)
            if total_referal_count < ig_members_count:
                pass

            if total_referal_count == eligibility_count:
                admin = Members.objects.filter(community_id=community, member_id=referer_instance)

                if admin.exists():
                    Members.objects.filter(community_id=community, member_id=referer_instance).update(
                        state=member_states.ADMIN)
                    Member_Engage.objects.filter(member_id=referer_instance, community_id=community).update(
                        member_state=member_states.ADMIN)

                    send_notification_to_promoter_of_ig_community.delay(community_id=community.id,
                                                                        community_name=community.name, member_id=ref_id)

        if not ref_id:
            # sending mail to nipun and harsh
            new_member_request.delay(member_id=user_id, community_id=community_id, ref_id=None,
                                     form_response=res['questions'])
        else:
            # sending mail to nipun and harsh
            new_member_request.delay(member_id=user_id, community_id=community_id, ref_id=ref_id,
                                     form_response=res['questions'])

        return JsonResponse({'success': True})

    elif is_lg:
        print("LG community")
        join_lg_communities_version_1(request, res, community, user, ref_id)

        if not ref_id:
            # sending mail to nipun and harsh
            new_member_request.delay(member_id=user_id, community_id=community_id, ref_id=None,
                                     form_response=res['questions'])
        else:
            # sending mail to nipun and harsh
            new_member_request.delay(member_id=user_id, community_id=community_id, ref_id=ref_id,
                                     form_response=res['questions'])
        return JsonResponse({'success': True})

    elif is_private:
        info_logger.info("Inside private\n")
        join_promoter_created_community_version_1(res, request)
        new_member_request.delay(member_id=user_id, community_id=community_id, ref_id=ref_id,
                                 form_response=res['questions'])

    return JsonResponse({'success': True})


def join_ig_communities_version_1(request,res,community,user,ref_id):

    '''join api for ig communities'''

    member_instance = Members.objects.filter(member_id=user, community_id=community)
    if not member_instance:
        # making a member instance
        member = Members()
        member.member_id = user
        member.community_id = community
        member.state = member_states.MEMBER
        member.created_at=time.time()
        member.save()

        # saving questions
        if 'questions' in res:
            info_logger.info(res['questions'])

            for question in res['questions']:

                if 'value' not in question:
                    continue
                if not question['value']:
                    continue
                question_instance = communityQuestions.objects.get(id=question['id'])
                answer_instance = communityAnswers()
                answer_instance.question = question_instance
                answer_instance.member = user
                answer_instance.community = community
                answer_instance.question_answer = question['value']
                answer_instance.question_title = question_instance.question_title
                answer_instance.save()
        else:
            res['questions'] = [{}]

        # creating an introduction card
        community_id = community.id
        member_id =user.id
        introduction_question, introduction_answer = auto_create_collabcard(user, community)
        print(introduction_answer)
        req_dict={

            'member_id':member_id,
            'community_id':community_id,
            'title':introduction_answer,
            'type':1,
            'create_intro':1
        }
        create_card(request,req_dict=req_dict)

        #post_introduction_card_for_community(community_id,member_id,request)
        #saving the referal detail and sending notifications for refered members

        community.updated_at=time.time()
        community.members_count=community.members_count + 1
        community.save()

        if community.members_count == ig_members_count:
            community.hide_community='4'
            community.save()
        send_notification_for_join_requests.delay(community_id, True, member_id)
        log="""Community joined for community_id=%s and member_id=%s"""%(community.id,user.id)
        print(log)


def join_lg_communities_version_1(request,res,community,user,ref_id):

    '''function to join lg communities'''

    member_instance = Members.objects.filter(member_id=user, community_id=community)
    if not member_instance:
        # making a member instance
        member = Members()
        member.member_id = user
        member.community_id = community
        member.state = member_states.PENDING_MEMBER
        if ref_id:
            member.ask_member_id=ref_id
        member.created_at = time.time()
        member.save()

        introduction_answer=""
        # saving questions
        if 'questions' in res:

            for question in res['questions']:

                if 'value' not in question:
                    continue
                if not question['value']:
                    continue
                question_instance = communityQuestions.objects.get(id=question['id'])
                answer_instance = communityAnswers()
                answer_instance.question = question_instance
                answer_instance.member = user
                answer_instance.community = community
                answer_instance.question_answer = question['value']
                answer_instance.question_title = question_instance.question_title
                answer_instance.save()

                if not introduction_answer:
                    introduction_answer = question['value']
        else:
            res['questions'] = [{}]

        creating_collabcard_for_lg_communities(community, user, introduction_answer, ref_id=ref_id)


       #creating members engage

        engage = Member_Engage()
        engage.member_id = user
        engage.community_id = community
        engage.updated_at = time.time()
        engage.member_state = member_states.PENDING_MEMBER
        engage.member_referral="Your profile is being verified"
        engage.save()



        #updating the pending members count in engage table if the ref_id member is verified
        member_queryset = Member_Engage.objects.filter(community_id=community, member_id=ref_id).filter(
            Q(member_state=member_states.ADMIN) | Q(member_state=member_states.MEMBER))
        is_verified = member_queryset.exists()
        if is_verified:

            pending_member= len(get_pending_members_of_community(community,ref_id))
            Member_Engage.objects.filter(community_id=community,member_id=ref_id).update(pending_members=pending_member)
            send_notification_to_referrer_of_lg_community(community_id=community.id, community_name=community.name,
                                                      referrer_id=ref_id,
                                                      member_name=user.userinfo.name,
                                                      community_state=community.hide_community,
                                                      is_verified=is_verified)

        log = """Request in LG community where community_id=%s and member_id=%s""" % (community.id, user.id)
        print(log)
    else:
        member_instance.update(state=member_states.PENDING_MEMBER)


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

    #saving data directly
    if 'aj' in res:
        if res['aj']:
            validate_time = is_joining_time_valid(community_instance, res['timestamp'], res['aj'])
            info_logger.info(validate_time)
            if validate_time:
                auto_join_community(community_instance, user_instance)
                post_introduction_card_for_community(community_id, member_id, request)
                log = """Auto join community for community_id=%s for user=%s""" % (community_id, member_id)
                info_logger.info(log)
                return

    member_list = Members.objects.filter(member_id=user_instance, community_id=community_instance)

    if member_list:
        member_state = member_list[0].state
        if member_state == member_states.ADMIN:

            post_introduction_card_for_community(community_id, member_id, request)

            generate_private_link(community_instance, user_instance)

            Member_Engage.objects.filter(member_id=user_instance, community_id=community_instance).update(
                member_referral="")
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
        member_instance.save()

        # creating a member engage instance
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.PENDING_MEMBER
        engage.save()
        update_pending_member_count_in_engage(community_instance)
        send_notification_to_admins.delay(community_id, user_instance.userinfo.name)


def join_whatsapp_community(res,request):

    '''function to join whatsapp community'''

    community_id = res['community_id']
    community_instance = Community.objects.get(id=community_id)

    member_id = get_member_id_from_headers(request)
    if not member_id:
        member_id = request.GET.get('member_id', None)
    else:
        res['timestamp'] = res['timestamp'] / 1000                  #for android timestamp

    user_instance = User.objects.get(id=member_id)

    if 'questions' in res:

        for question in res['questions']:

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


    #saving data directly
    if 'aj' in res:
        if res['aj']:
            validate_time = is_joining_time_valid(community_instance, res['timestamp'],res['aj'])
            info_logger.info(validate_time)
            if validate_time:
                auto_join_community(community_instance,user_instance)
                post_introduction_card_for_community(community_id, member_id, request)
                log="""Auto join community for community_id=%s for user=%s"""%(community_id,member_id)
                info_logger.info(log)
                return



    member_list = Members.objects.filter(member_id=user_instance, community_id=community_instance)


    if member_list:
        member_state = member_list[0].state
        if member_state == member_states.ADMIN:

            post_introduction_card_for_community(community_id,member_id,request)

            generate_private_link(community_instance,user_instance)

            Member_Engage.objects.filter(member_id=user_instance, community_id=community_instance).update(
                member_referral="")
        else:

            Members.objects.filter(member_id=user_instance,community_id=community_instance).update(
                        state=member_states.PENDING_MEMBER)

            Member_Engage.objects.filter(member_id=user_instance,community_id=community_instance).update(
                member_state=member_states.PENDING_MEMBER)
        update_pending_member_count_in_engage(community_instance)
        return JsonResponse({'success': True})
    else:

        #creating a member instance
        member_instance = Members()
        member_instance.member_id = user_instance
        member_instance.community_id = community_instance
        member_instance.state = member_states.PENDING_MEMBER
        member_instance.save()

        #creating a member engage instance
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.PENDING_MEMBER
        engage.save()
        update_pending_member_count_in_engage(community_instance)
        send_notification_to_admins.delay(community_id,user_instance.userinfo.name)


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
    member_instance = Members()
    member_instance.member_id = user_instance
    member_instance.community_id = community_instance
    member_instance.state = member_states.MEMBER
    member_instance.created_at=time.time()
    member_instance.save()

    # updating the member engage instance
    engage = Member_Engage()
    engage.member_id = user_instance
    engage.community_id = community_instance
    engage.updated_at = time.time()
    engage.member_state = member_states.MEMBER
    engage.save()

    send_notification_for_join_requests.delay(community_instance.id,True, user_instance.id)


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
            create_card(request, req_dict=req_dict)
            return True

    return False



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



def generate_private_link(community_instance,promoter_instance):

    '''function to generate private links of community'''

    community_expire_filter = communityExpiryCodes.objects.filter(community=community_instance).order_by('-id')
    unique_code_list = list(community_expire_filter.values_list('unique_code',flat=True))



    if not unique_code_list:

        unique_code = generate_random(unique_code_list)
        expireInstance = communityExpiryCodes()
        expireInstance.community = community_instance
        expireInstance.promoter = promoter_instance
        expireInstance.created_at = time.time()
        expireInstance.unique_code = unique_code
        expireInstance.private_link = url + '/community/' + str(community_instance.id) + "?aj="+ str(unique_code)
        expireInstance.expire_duration = 86400
        expireInstance.save()

        return expireInstance.private_link

    else:

        current_time = int(time.time())
        last_created_time = community_expire_filter[0].created_at

        if current_time - last_created_time > 3600:
            unique_code = generate_random(unique_code_list)
            expireInstance = communityExpiryCodes()
            expireInstance.community = community_instance
            expireInstance.promoter = promoter_instance
            expireInstance.created_at = time.time()
            expireInstance.unique_code = unique_code
            expireInstance.private_link = url + '/community/' + str(community_instance.id) + "?aj=" + str(unique_code)
            expireInstance.expire_duration = 86400
            expireInstance.save()

            return expireInstance.private_link

    return community_expire_filter[0].private_link



def generate_random(unique_code_list):

  '''function to generate a random number'''

  randInt = randint(1,100000)

  return generate_random(unique_code_list) if randInt in unique_code_list else randInt



def category_filter(request, category):
    categories = Community_tags.objects.all()
    communities = []
    for cat in categories:
        if cat.category == category:
            c = Community.objects.get(id=cat.community_id.id)
            communities.append(c)
    community = []
    for comm_object in communities:
        serialized_object = CommunitySerializer(comm_object)
        community.append(serialized_object)
    return JsonResponse({'communities': community})


def categories(request):
    ''' function to get all categories  '''

    tags = Tags.objects.all()
    Category_list = []
    for category in tags:
        category_dict = {}
        if category.id == 4 or category.id == 8 or category.id == 13 or category.id == 22 or category.id == 25 or category.id == 28 or category.id == 39 or category.id == 40:
            category_dict['id'] = str(category.id)
            category_dict['title'] = category.category_name
            Category_list.append(category_dict)

    return JsonResponse({'category_list': Category_list})


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

    return JsonResponse({'members': members})


def admins(request, community_id):
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
        return JsonResponse({'members': users, 'referred_members_count': referred_members_count})
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

        return JsonResponse({'members': users, 'referred_members_count': referal_count})
    else:
        return JsonResponse({'members': users})

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

    form_response = FormResponseSerilaizer(community_id,member_id, bl=True, current_user_id=member_id)

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

    ask_approval_notification(community_id=community_id, community_name=community_instance.name, approver_id=ask_member_id,
                              member_name=member_instance.member_id.userinfo.name, community_state=community_instance.hide_community)



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
           member_ids = member_ids.split(",")

           for member in member_ids:

                member_filter = Members.objects.filter(community_id=community_id,member_id=member)

                if member_filter.exists():
                    member_state = member_filter[0].state

                    if member_state == member_states.MEMBER:
                        remove_members(community_id,member_filter[0].member_id.id,removed_state=deleted_members.REMOVED)

           return JsonResponse({'success': True})

    #flow to leave the community

    if not is_promoter and member_ids == False:
        remove_members(community_id,member_id,removed_state=deleted_members.LEFT)
        return JsonResponse({'success':True})

    return JsonResponse({'success':False})


def remove_members(community_id, member_id,removed_state):
    '''function to remove member'''

    try:
        community_instance = Community.objects.get(id=community_id)
        user_instance = User.objects.get(id=member_id)
    except:
        return


    Member_Engage.objects.filter(community_id=community_id, member_id=member_id).delete()
    #communityAnswers.objects.filter(community=community_id, member=member_id).delete()

    is_member_left = removedMembers.objects.filter(community=community_id, member=member_id)

    if not is_member_left.exists() and community_instance:

        instance = removedMembers(community=community_instance, member=user_instance,
                                  removed_state=removed_state, created_at=time.time())
        instance.save()
        #saving collabcard state in update status
        update_staus = collabcardState.objects.filter(community=community_id,user=member_id).update(removed_status=instance.id)
        print(update_staus)


    Members.objects.filter(community_id=community_id, member_id=member_id).delete()





############# functions for  create flow of card,community and members   ##########################

# /api/create_community?member_id=21&is_admin=true
@csrf_exempt
def create_community(request):
    ''' function create a community '''

    is_admin = request.GET.get('is_admin')
    if is_admin == 'true':
        # if community is created as a admin
        user_id = request.GET.get('member_id')
        if request.method == 'POST':
            res = json.loads(request.body)
            img = request.FILES.dict()
            # creating the community with given credentials
            group = Community()
            group.members_count = group.members_count + 1
            group.name = res['name']
            for dict in res['items']:
                if dict['key'] == 'Purpose of the community':
                    group.purpose = dict['value']
                elif dict['key'] == 'Geography of the community':
                    group.location = dict['value']
                elif dict['key'] == 'About the community (Optional)':
                    group.about = dict['value']
                elif 'image' in img:
                    group.image_url = img['image']
                elif dict['key'] == 'whatsapp_link':
                    group.whatsapp_group_link = dict['whatsapp_link']
                    # saving the categories of the community
                elif dict['key'] == 'Type of community':
                    categories = dict['value']
                    categories = categories.split(", ")
                    group.save()
                    for tags in categories:
                        tags_id = int(tags)
                        tags_object = Tags.objects.get(id=tags_id)
                        community_tags = Community_tags()
                        community_tags.category = tags_object.category_name
                        community_tags.community_id_id = group.id
                        community_tags.tags_id = tags_id
                        community_tags.save()
            group.updated_at = time.time()
            group.created_at = time.time()
            group.save()

            # uploading community image and thumbnail
            image_link = upload_community_files(community_id=group.id,
                                                image='https://beta.likeminds.community/media/media/community/default.jpeg',
                                                url=True)
            group.image_link = image_link
            group.save()
            upload_community_thumbnail.delay(group.id,
                                             'https://beta.likeminds.community/media/media/community/default.jpeg')

            # create user as a admin for the community as the user is creating the community as a admin
            user = User.objects.get(id=user_id)
            community = Community.objects.get(id=group.id)
            # create admin for that community
            member = Members()
            member.member_id = user
            member.community_id = community
            member.state = 1  # admin state
            member.created_at = time.time()
            member.save()

            # creating a card while a comunity is created
            card = Collabcard()
            if community.purpose != '':
                card.title = "Created this community " + community.purpose
            else:
                card.title = "Listed our community on LikeMinds. This will help us to know each other, have organised discussions and network efficiently."
            card.community = community
            card.user = user
            card.date_epoch = time.time()
            card.save()
            # saving details in firebase
            update_last_answer_id(card.id, "")

            # Community.objects.filter(id=community.id).update(purpose_collabcard = card.id)
            # community.purpose_collabcard = card.id
            # community.save()
            community_id = community.id
            card_id = card.id
            save_community_purpose_card.delay(community_id, card_id)
            print("updated card id >>>>>>>   \n", card.id, "\n")
            # created card will be auto followed by the creator if the card
            create_collabcard_state_for_user(card=card, user=user, state=collabcard_states.COLLABCARD_STATE_FOLLOW, community=community)
            # getting details of the user who is creating the community
            userinfo = Userinfo.objects.get(user_id=user.id)

            # get user serialized json
            usr = UserinfoSerializer(userinfo)
            serialized_object = CommunitySerializer(community)
            new_dict = {}
            new_dict.update(serialized_object)

            ans_text = ''

            # saving the questions to be asked while joining a community
            for questions in res['questions']:
                question = communityQuestions()
                question.question_title = questions["key"]
                question.question_state = 0
                question.community = community
                question.value = questions['value']
                question.optional = False
                question.save()

            # forming card dict

            crd = CollabcardSerializer(card, user=user_id)
            crd['member'] = usr
            # inserting in member_engage table
            if not is_member_engage(community, user):
                engage = Member_Engage()
                engage.member_id = user
                engage.community_id = community
                engage.last_unseen_conversation = card
                engage.updated_at = time.time()
                engage.member_state = 1
                engage.save()

            # send_email_to_admin_of_community.delay(CommmunityAdminName=user.name,CommunityName=res['name'],email=user.email)
            return JsonResponse({'success': True, 'community': new_dict, 'collabcard': crd})
    else:
        # if community is created as a member
        member_id = request.GET.get('member_id')
        if request.method == 'POST':
            res = json.loads(request.body)

            # creating new community
            group = Community()
            group.members_count = group.members_count + 1
            group.name = res['name']
            group.updated_at = time.time()
            group.created_at = time.time()
            group.save()

            user = User.objects.get(id=member_id)

            # creating member as temporary promoter
            member = Members()
            member.member_id = user
            member.community_id = group
            member.state = 2  # temperary admin state
            member.created_at = time.time()
            member.save()
            # get community serialized json
            serialized_object = CommunitySerializer(group)
            new_dict = {}
            new_dict.update(serialized_object)

            user_id = request.GET.get('member_id')
            user = Userinfo.objects.get(user_id=user_id)
            # send_email_to_temp_admin_of_community.delay(CommmunityAdminName=user.name,CommunityName=res['name'],email=user.email)
            return JsonResponse({'success': True, 'community': new_dict})
    return HttpResponse("Create Community Api")

@csrf_exempt
def create_community_version_1(request):

    '''function to create community for version for whatsapp shifting'''
    member_id=get_member_id_from_headers(request)
    user_instance=User.objects.get(pk=member_id)
    res=json.loads(request.body)
    info_logger.info(res)

    community_name=""
    purpose=""
    community_type = None
    sub_type = None

    if 'name' in res:
        community_name=res['name']

    if 'purpose' in res:
        purpose=res['purpose']

    if 'type' in res:
        community_type=res['type']

    if 'sub_type' in res:
        sub_type = res['sub_type']

    if 'community_id' in res:
        community_serialized_object = update_community(res)
        return JsonResponse({'success':True,'community':community_serialized_object})

    community_state = 0
    if 'state' in res:
        community_state = res['state']

    about = None
    if 'about' in res:
        about = res['about']


    community_instance=Community()
    community_instance.name=community_name
    community_instance.purpose=purpose
    community_instance.members_count=1
    community_instance.about = about
    community_instance.image_link = community_default_image
    community_instance.thumbnail = community_default_thumbnail
    if community_type:
        community_instance.community_type=community_type
    community_instance.created_at=time.time()
    community_instance.updated_at=time.time()
    community_instance.hide_community = community_state    #for whatsapp community
    if sub_type:
        community_instance.sub_type = sub_type    #for whatsapp community
    community_instance.save()

    log = """%s community created in community table"""%(community_name)
    info_logger.info(log)


    #making the member instance for created community
    member_instance=Members()
    member_instance.member_id=user_instance
    member_instance.community_id=community_instance
    member_instance.state=member_states.ADMIN
    member_instance.created_at=time.time()
    member_instance.save()

    #making the member enage instance for created community
    engage = Member_Engage()
    engage.member_id = user_instance
    engage.community_id = community_instance
    engage.updated_at = time.time()
    engage.member_state = member_states.ADMIN
    engage.member_referral = "Finish setting up your community"
    engage.save()


    log = """%s is the promoter of %s"""%(user_instance.userinfo.name,community_instance.name)
    info_logger.info(log)


    for question in res['questions']:

        questions_instance=communityQuestions()
        questions_instance.community=community_instance
        questions_instance.question_title=question['question_title']
        questions_instance.question_state=question['state']
        questions_instance.value = question['value'] if 'value' in question else None
        questions_instance.optional=question['optional']
        questions_instance.help_text = question['help_text'] if 'help_text' in question else None
        questions_instance.save()

    log = """questions added in community questions table"""
    info_logger.info(log)


    # check_data=communityExpire.objects.filter(community=community_instance)
    # if not check_data:
    #     communityExpireInstance=communityExpire()
    #     communityExpireInstance.community=community_instance
    #     communityExpireInstance.duration = 86400                  #for 24 hours saving in community
    #     communityExpireInstance.save()

    communty_serailized_object = CommunitySerializer(community_instance)
    return JsonResponse({'success':True,'community':communty_serailized_object})



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









# /api/create_collabcard?community_id=&member_id=
@csrf_exempt
def create_card(request,req_dict=None):
    ''' function to create a card '''

    if not req_dict:
        user_id = request.GET.get('member_id')
        community_id = request.GET.get('community_id')
    else:

        user_id=req_dict['member_id']
        community_id=req_dict['community_id']

    print(request.method)

    #member_id = get_member_id_from_headers(request)
    user_instance = User.objects.get(id=user_id)
    userinfo_instance = user_instance.userinfo
    community = Community.objects.get(id=community_id)
    community_name = community.name
    community_state = community.hide_community
    if request.method == 'POST':
        if not req_dict:
            res = json.loads(request.body)
        else:
            res=req_dict

        # creating card
        # type=0 normal card, type =1 intro card, type 2 is event card and type 3 is poll card
        typ = int(res['type']) if 'type' in res else 0


        card = Collabcard.objects.filter(community=community, user=user_instance, type=1)
        if card.exists() and typ == 1:
            # if welcome card for user is already existing
            return JsonResponse({'success': False})

        if 'date_time' in res:
            date_time = res['date_time'] if (str(typ) == '2' or str(typ) == '3') else 0
        else:
            date_time=0

        #if the community is a ig community
        create_intro=False
        if 'create_intro' in res:
            create_intro=True

        is_feedback=False
        if int(community_id) == int(feedback_community_id):
            typ=4
            is_feedback=True
        card = Collabcard()
        card.title = res['title']
        card.community = community
        card.user = user_instance
        card.type = typ
        card.image_count = res['image_count'] if ('image_count' in res) else 0
        card.pdf_count = res['pdf_count'] if ('pdf_count' in res) else 0
        card.date_time = date_time
        card.duration = res['duration'] if ('duration' in res) else 0
        card.location = res['location'] if ('location' in res) else None
        card.location_lat = res['location_lat'] if ('location_lat' in res) else None
        card.location_long = res['location_long'] if ('location_long' in res) else None

        if 'share_link' in res:
            card.share_link = res['share_link']
            og_tags = decode_meta_from_url(res['share_link'])
            card.og_tags = json.dumps(og_tags)

        card.date_epoch = time.time()  # card creation time
        card.save()

        polls = res['polls'] if 'polls' in res else []
        for poll in polls:
            collabcardpolls_instance = CollabcardPolls()
            collabcardpolls_instance.card = card
            collabcardpolls_instance.text = poll['text']
            collabcardpolls_instance.save()




        collabcard = CollabcardSerializer(card, user_id, community)

        collabcard['date'] = datetime.today().strftime('%d-%m-%Y')

        # get user object's serialized json
        user_info_serializer = UserinfoSerializer(userinfo_instance)
        collabcard['member'] = user_info_serializer

        if is_feedback:                                      #if the collabcard created in feedback community

            mail_dict={}
            mail_dict['user_name']=user_info_serializer['name']
            mail_dict['email']=user_info_serializer['email']
            mail_dict['collabcard_link']=collabcard['share_url']
            mail_dict['content']=collabcard['title']
            mail_dict['collabcard_id']=collabcard['id']
            mail_dict['url']=url

            send_mail_for_query_and_feedback(mail_dict)          #sending mail to collabmates for posting

            #sending text for pop-up:

            collabcard_feedback_popup={

                'title':"Thanks for writing to us",
                'sub_title':"We may reply privately to your query/feedback via email or feature it in this community depending on its utility for everyone.",
                'action_title':"OK",
                'action':'route://community_collabcard?community_id=' + str(community.id) + '&community_name=' + str(
            community.name) + '&community_state=' + str(community.hide_community)
            }
            return JsonResponse({'success': True, 'collabcard': collabcard,'collabcard_feedback_popup':collabcard_feedback_popup})


        # #saving the state in collabcardState table instead of follow collabcard
        create_collabcard_state_for_user(card=card, user=user_instance,
                                         state=collabcard_states.COLLABCARD_STATE_FOLLOW,
                                         community=community)

        update_last_answer_id(card.id, "")



        if is_member_engage(community, user_instance):

            if create_intro:
                Member_Engage.objects.filter(community_id=community,member_id=user_instance).update(
                    member_state=member_states.MEMBER,
                    last_unseen_conversation=card,
                    member_referral=""
                )



        else:
            engage = Member_Engage()
            engage.member_id = user_instance
            engage.community_id = community
            engage.last_unseen_conversation = card
            engage.updated_at = time.time()
            if create_intro:
                engage.member_state=member_states.MEMBER
            engage.save()
        #update_referral_text_in_engage_table.delay(community_id)
        update_last_unseen_in_engage_on_card_creation.delay(community_id=community_id)




        # custom_cache.clear()

        #sending notification to the user

        send_notification_for_new_collabcard_posted.delay(community_id, res['title'],
                                                          user_id, userinfo_instance.name,
                                                          type=typ, date_time=date_time,
                                                          card_id=card.id,
                                                          community_name=community_name,
                                                          community_state=community_state)

        if typ != 1:  # stopping mail for introduction cards
            send_email_for_collabcard(community, userinfo_instance, card, typ)


        return JsonResponse({'success': True, 'collabcard': collabcard})
    return JsonResponse({'success': False})


def create_collabcard_state_for_user(card, user, state, community):
    """ create collabcard state for a member for a card """

    collabcard_state_instance = collabcardState()
    collabcard_state_instance.card = card
    collabcard_state_instance.user = user
    collabcard_state_instance.community = community
    collabcard_state_instance.state = state  # user has created the card and he is autofollowing
    collabcard_state_instance.created_at = time.time()
    collabcard_state_instance.updated_at = time.time()
    collabcard_state_instance.save()


# /api/add_admin/community_id
@csrf_exempt
def create_admin(request, community_id):
    ''' saving admin details given by user of a community
     when the user is creating a community as a member '''
    if request.method == 'POST':
        res = json.loads(request.body)
        # saving the nominated promoter details
        admin = temp_admin()
        if 'member_id' in res:
            member_id = res['member_id']
            promoter = Userinfo.objects.get(user_id=member_id)
            promoter_email = promoter.email
        if 'nominate_member_id' in res:
            nominated_member_id = res['nominate_member_id']
            try:
                user_data = Userinfo.objects.get(user_id=nominated_member_id)
                res['name'] = user_data.name
                res['email_id'] = user_data.email
            except:
                print("Error in object")
        if 'name' in res:
            admin.name = res['name']
        if 'email_id' in res:
            try:
                if res['email_id'] == promoter_email:
                    return JsonResponse({'success': True})
            except:
                pass
            admin.email = res['email_id']
        if 'contact_no' in res:
            admin.contact_number = res['contact_no']
        if 'member_id' in res:
            member_id = res['member_id']
        community = Community.objects.get(id=community_id)
        admin.community = community
        admin.member_id = member_id
        admin.save()
        # checking if there is any person with given mail , and make him nominated promoter
        check = check_member(res['email_id'], community_id, res['member_id'], res)
        return JsonResponse({'success': True})
    return HttpResponse('Add Admin Api')


def check_member(email, community_id, member_id, res):
    """ check if the user is already a member of the invited community and make user as nominated promoter
     if he is registered in collabmates and if the user is not registered just send the user a invitation email """
    ProposedAdmin = Userinfo.objects.get(user_id=member_id)
    community = Community.objects.get(id=community_id)
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
            send_email_to_nominated_admin.delay(NominatedAdmin=res['name'], email=email, ProposedAdmin=ProposedAdmin,
                                                proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                                community_id=community.id)
            return False
    except:
        """ if any error trying fetch the user details , then user is not registered , send an email"""
        send_email_to_nominated_admin.delay(NominatedAdmin=res['name'], email=email, ProposedAdmin=ProposedAdmin,
                                            proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                            community_id=community.id)
        return False

    if user:
        # get the state of the user of the community he is proposed to become a promoter for
        member = Members.objects.filter(community_id=community, member_id=user[0].user_id.id)

        if member and member[0].state == 4:
            # if the user is already a member , give him state 7
            # state 7 is nominted promoter who is already a member of thet community
            Members.objects.filter(community_id=community, member_id=user[0].user_id.id).update(state=7)
            # send mail and notification
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
                                                proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                                community_id=community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id=NominatedAdmin_id, community_id=community.id,
                                                      proposed_admin_name=ProposedAdmin)

        elif member and (member[0].state == 6 or member[0].state == 7):
            # if he is nominated again just send hime a remainding mail and notification
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
                                                proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                                community_id=community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id=NominatedAdmin_id, community_id=community.id,
                                                      proposed_admin_name=ProposedAdmin)

        elif member and (member[0].state == 1 or member[0].state == 2):
            return True

        elif member and (member[0].state == 3 or member[0].state == 5):
            Members.objects.filter(community_id=community, member_id=user[0].user_id.id).update(state=6)
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
                                                proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                                community_id=community.id)
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
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
                                                proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                                community_id=community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id=NominatedAdmin_id, community_id=community.id,
                                                      proposed_admin_name=ProposedAdmin)
        return True
    return False


def pending_members(request, community_id):

    ''' function to get members requested to join in a community '''

    member_id = request.GET.get('member_id',None)
    if not member_id:
        member_id = get_member_id_from_headers(request)
    pending_requests=get_pending_members_of_community(community_id,requested_member_id=member_id)
    return JsonResponse({'pending_members': pending_requests})


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
                send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name, email=prop_admin.email,
                                                   ProposedAdmin=prop_admin.name, proposedAdminState=1,
                                                   CommunityName=community.name, community_id=community.id)
                proposer_id = prop_admin.user_id.id
                nom_admin_name = nom_admin[0].name
                send_notification_to_proposer.delay(proposer_id, community_name=community.name,
                                                    community_id=community.id, proposed_name=nom_admin_name)
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
                send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name, email=prop_admin.email,
                                                   ProposedAdmin=prop_admin.name, proposedAdminState=2,
                                                   CommunityName=community.name, community_id=community.id)
                proposer_id = prop_admin.user_id.id
                nom_admin_name = nom_admin[0].name
                send_notification_to_proposer.delay(proposer_id, community_name=community.name,
                                                    community_id=community.id, proposed_name=nom_admin_name)
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
            send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name, email=prop_admin.email,
                                               ProposedAdmin=prop_admin.name, proposedAdminState=1,
                                               CommunityName=community.name, community_id=community.id)
            proposer_id = prop_admin.user_id.id
            nom_admin_name = nom_admin[0].name
            send_notification_to_proposer.delay(proposer_id, community_name=community.name, community_id=community.id,
                                                proposed_name=nom_admin_name)
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

    if 'member_id' in res:
        member_id = res['member_id']
    if 'community_id' in res:
        community_id = res['community_id']
    accepted=False
    if 'accepted' in res:
        accepted = res['accepted']
    community = Community.objects.get(id=community_id)
    user = User.objects.get(id=member_id)

    is_lg=is_LG_or_LP_community(community)

    if is_lg:                       #request accepted in case of lg communities
        member_verification=False
        if not req_dict:
            member_verification=True
            req_dict = {
                'member_id': member_id,
                'community_id': community_id,
                'accepted':accepted
            }
        approve_or_decline_lg_community(request,req_dict,member_verification)
        return JsonResponse({'success': True})

    community_state = get_state_of_community(community)

    if community_state == community_states.WHATSAPP:

        req_dict = {
            'member_id': member_id,
            'community_id': community_id,
            'accepted': accepted
        }
        info_logger.info("whatsapp community")
        approve_or_decline_whatsapp_community(req_dict,request)
        update_pending_member_count_in_engage(req_dict['community_id'])
        return  JsonResponse({'success': True})

    if community_state == community_states.PRIVATE or community_state == community_states.HIDDEN:
        req_dict = {
            'member_id': member_id,
            'community_id': community_id,
            'accepted': accepted
        }
        info_logger.info("private_community")
        approve_or_decline_private_community(req_dict, request)
        update_pending_member_count_in_engage(req_dict['community_id'])
        return  JsonResponse({'success': True})



    if accepted or accepted == 'true':
        # if accepted , then make him a member of the community
        join_time = time.time()

        # check if member is already accepted to stop duplicate notifications and false member count
        member_queryset = Members.objects.filter(member_id=member_id, community_id=community).filter(Q(state=1)|Q(state=4))
        if not member_queryset.exists():
            # updating the approve state
            Members.objects.filter(member_id=member_id, community_id=community).update(state=4,
                                                                                       created_at=join_time)  # aprove state = 4
            community = Community.objects.get(id=community_id)
            members_count = community.members_count + 1
            Community.objects.filter(id=community_id).update(members_count=members_count)

            request.method = "POST"
            post_introduction_card_for_community(community_id,member_id,request)


            send_notification_for_join_requests.delay(community_id, True, member_id)
            ## sending email to the user that his request is accepted for this community
            member_request_approval_or_denied.delay(user_id=member_id, community_id=community_id, approved=True)

    else:

        send_notification = res['send_notification'] if 'send_notification' in res else True

        # checking state to stop duplicate notifications and false referal text and pending member count
        state = Members.objects.filter(member_id=member_id, community_id=community)[0].state
        if state == 3 or state == 8:
            # change user state to 5
            Members.objects.filter(member_id=member_id, community_id=community).delete()  # decline state = 5
            # delete the member engage table record for the user
            Member_Engage.objects.filter(member_id=member_id, community_id=community).delete()
            # delete the responses of user to community questions, if any
            communityAnswers.objects.filter(member=member_id, community=community_id).delete()
            # update pending members count of community and referal text of user
            update_pending_member_count_in_engage(community)

            if send_notification or send_notification == 'true':
                send_notification_for_join_requests.delay(community_id, False, member_id)

    return JsonResponse({'success': True})


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



            #creating a collabcard
            introduction_question, introduction_answer = auto_create_collabcard(user, community)
            print(introduction_answer)
            req_dict = {

                'member_id': member_id,
                'community_id': community_id,
                'title': introduction_answer,
                'type': 1,
                'create_intro': 1
            }

            request.method="POST"
            create_card(request,req_dict=req_dict)
            #(community.id,member_id,request)
            # saving the referal detail and sending notifications for refered members

            community.updated_at = time.time()
            community.members_count = community.members_count + 1
            community.save()
            is_live=False
            if community.hide_community == '4':
                is_live=True

            if community.members_count == ig_members_count:
                community.hide_community = '4'
                send_notification_for_tool_unlocked_for_pilot.delay(community_id=community_id)
                community.save()

            send_notification_for_join_requests.delay(community_id, True, member_id)

            update_last_unseen_in_engage(user=user,community=community)

            #deleting the data from collabcard temp
            member_instance=Members.objects.get(member_id=user,community_id=community)

            #getting pending members who was refered by me
            pending_members=get_pending_members_of_community(community.id,requested_member_id=member_id)
            info_logger.info("\n")
            info_logger.info(pending_members)
            check=Member_Engage.objects.filter(member_id=user,community_id=community).update(pending_members=len(pending_members))
            info_logger.info(check)

            if member_instance.ask_member_id:
                collabcardTemp.objects.filter(member=member_instance.ask_member_id, community=community,show_member=user).delete()

            collabcardTemp.objects.filter(member=member_id,community=community).delete()

            if member_verification:
                header_member_id=get_member_id_from_headers(request)
                Members.objects.filter(member_id=member_id, community_id=community).update(approved_member_id=header_member_id)

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
                    if is_live:
                        send_notification_for_tool_unlocked_for_live_community.delay(referer_id=header_member_id,
                                                                                     referal_count=total_referal_count,
                                                                                     community_id=community.id,
                                                                                     community_name=community.name,
                                                                                     community_state=community.hide_community)


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
                pending_members = len(get_pending_members_of_community(community,header_member_id))
                Member_Engage.objects.filter(member_id=header_member_id, community_id=community).update(
                    pending_members=pending_members)
                Referal.objects.filter(member=header_member_id, community=community).delete()
            send_notification_for_join_requests.delay(community_id, False, member_id)



def approve_or_decline_whatsapp_community(req_dict,request):

    '''function to approve the whatsapp community'''

    if req_dict['accepted'] or req_dict['accepted'] == 'true':

        is_member = is_member_verified(community=req_dict['community_id'], user_instance=req_dict['member_id'])

        if not is_member:
            Members.objects.filter(member_id=req_dict['member_id'],
                                   community_id=req_dict['community_id']).update(state=member_states.MEMBER,
                                                                                 created_at=time.time())

            Member_Engage.objects.filter(member_id=req_dict['member_id'],
                                         community_id=req_dict['community_id']).update(member_state=member_states.MEMBER,
                                                                                       updated_at=time.time())

            # updating pending member count
            community = Community.objects.get(id=req_dict['community_id'])
            members_count = community.members_count + 1
            Community.objects.filter(id=req_dict['community_id']).update(members_count=members_count)

            # posting a intro collabcard
            post_introduction_card_for_community(req_dict['community_id'], req_dict['member_id'], request)


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
                                                                                       updated_at=time.time())

            # updating pending member count
            community = Community.objects.get(id=req_dict['community_id'])
            members_count = community.members_count + 1
            Community.objects.filter(id=req_dict['community_id']).update(members_count=members_count)

            # posting a intro collabcard
            post_introduction_card_for_community(req_dict['community_id'], req_dict['member_id'], request)


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


def collabcard(request, card_id):
    ''' function to get card details, answers and images '''
    # get the card object

    cards = Collabcard.objects.get(id=card_id)
    page = request.GET.get('page', 1)

    current_user_id = get_member_id_from_headers(request)

    feedback=True
    if cards.community.id == feedback_community_id:
        feedback = False

    # coverting current time into epoch time for getting time stamp of answers and card

    # get all the answers of the card
    answer = card_answers.objects.filter(card=cards).order_by('id')
    # answer=pagination(answer,page,paginate_by=10)

    answer_id = request.GET.get('answer_id', '')
    user_id = request.GET.get('member_id', '')

    if answer_id:
        answer_id = int(answer_id)

        answer = card_answers.objects.filter(card=cards, id__gte=answer_id).filter(~Q(user__id=user_id))
        # answer = pagination(answer, page, paginate_by=10)
        answers = get_answer_data(answer,feedback,cards.community.id,current_user_id=current_user_id)         #if the feedback is true don't send id in userinfo
        return JsonResponse({'answers': answers})
    else:
        answers = get_answer_data(answer,feedback,cards.community.id,current_user_id=current_user_id)

    # serializing Collabcard
    card = CollabcardSerializer(cards, user_id, cards.community)

    user = Userinfo.objects.get(user_id=cards.user.id)

    # serializing user object
    usr = UserinfoSerializer(user)
    usr['is_clickable']=feedback

    #when the member is removed
    removed_state = removedMembersSerializer(cards.community.id,usr['id'])
    if removed_state != False:
        usr['remove_state'] = removed_state

    # user form response serialzer
    form_response = FormResponseSerilaizer(cards.community.id, cards.user.id,bl=True,current_user_id=current_user_id)
    if form_response:
        usr['response'] = form_response[0]
        usr['question_answers'] =form_response[1]
    # get the card image if any
    files = get_collabcard_files(card_id)
    card['images'] = files[0]
    card['member'] = usr
    card['pdf'] = files[1]
    if user_id:
        card['state'] = get_status_of_collabcard(member_id=user_id, community=cards.community, card=cards)
    # get tine stamp for card
    time_text = get_time_text(cards.date_epoch)
    card['created_at'] = time_text
    return JsonResponse({"collabcard": card, 'answers': answers})


def get_answer_data(answer,feedback,community_id,current_user_id):
    '''function to get answer for a particular collabcard from database database'''
    answers = []

    for ans in answer:
        user = Userinfo.objects.filter(user_id=ans.user.id)
        usr = UserinfoSerializer(user[0])
        usr['is_clickable']=feedback

        removed_state = removedMembersSerializer(community_id, usr['id'])

        if removed_state != False:
            usr['remove_state'] = removed_state

        form_response = FormResponseSerilaizer(community_id, ans.user.id,bl=True,current_user_id=current_user_id)
        if form_response:
            usr['response'] = form_response[0]
            usr['question_answers'] = form_response[1]
        # coverting current time into epoch time

        if str(ans.date_epoch) == "-9223372036854775808":
            time_text = ""
        else:
            time_text = get_time_text(ans.date_epoch)

        attachements = get_answer_files(ans.id)

        answers.append({'id': ans.id, 'answer': ans.answer, 'created_at': time_text, 'member': usr,
                        'images': attachements[0], 'pdf': attachements[1]})
    return answers


def get_collabcard_files(card_id):
    '''function to return pdf and image files of a collabcard'''

    files = Card_Attachment.objects.filter(collabcard=card_id)
    img_list = []
    pdf = []
    for file in files:
        if file.type == 'image':
            if file.file_url:
                img = {'image_url': file.file_url}
            else:
                img = {'image_url': url + file.attachment.url}
            img_list.append(img)
        elif file.type == 'pdf':
            if file.file_url:
                pdf_url = {'pdf_file': file.file_url}
            else:
                pdf_url = {'pdf_file': url + file.attachment.url}
            pdf.append(pdf_url)
    return (img_list, pdf)


def get_answer_files(answer_id):
    '''function to return pdf and image files of a collabcard'''

    files = Answer_Attachment.objects.filter(answer=answer_id)
    img_list = []
    pdf = []
    for file in files:
        if file.type == 'image':
            if file.file_url:
                img = {'image_url': file.file_url}
                img_list.append(img)
        elif file.type == 'pdf':
            if file.file_url:
                pdf_url = {'pdf_file': file.file_url}
                pdf.append(pdf_url)
    return (img_list, pdf)


def get_time_text(created_time):
    """ function to get time stamp """

    # get current time and convert it into epoch time
    present_time = str(datetime.now())
    current_time = datetime.strptime(present_time.strip(' \t\r\n'), "%Y-%m-%d %H:%M:%S.%f").strftime('%s')
    created = datetime.fromtimestamp(created_time)
    current = datetime.fromtimestamp(int(current_time))
    difference = dateutil.relativedelta.relativedelta(current, created)
    # print("diffrence ======== ",difference)
    if difference.years:
        # if difference is more than one week return created date
        return time.strftime('%d/%m/%Y', time.localtime(created_time))
    elif difference.months:
        # if difference is more than one week return created date
        return time.strftime('%d/%m/%Y', time.localtime(created_time))
    elif difference.days:
        # if difference is in days
        if difference.days == 1:
            return str(difference.days) + " day ago"

        elif difference.days < 7:
            return str(difference.days) + " days ago"

        elif difference.days == 7:
            return "1 week ago"
        # if difference is more than one week return created date
        return time.strftime('%d/%m/%Y', time.localtime(created_time))

    elif difference.hours:
        # if difference is in hours
        if difference.hours == 1:
            return str(difference.hours) + " hour ago"

        return str(difference.hours) + " hours ago"
    elif difference.minutes:
        # if difference is in hours
        if difference.minutes == 1:
            return str(difference.minutes) + " min ago"

        return str(difference.minutes) + " mins ago"
    else:
        # if difference is in seconds
        return "Just Now"


def community_cards(request, community_id):
    ''' function get all the cards in a community '''

    community = Community.objects.get(id=community_id)
    member_id = request.GET.get('member_id')

    current_user_id = get_member_id_from_headers(request)

    # user_instance=User.objects.get(id=member_id)

    # is_tour=request.GET.get('is_tour',False)

    # if the community is pilot community and android tour is given
    if community.hide_community == '3':
        card_list = get_cards_for_demo(community_id, member_id)
        return JsonResponse({'collabcards': card_list})

    size = request.GET.get('size', '')
    if size:
        size = int(size)
        cards = Collabcard.objects.filter(community=community_id).order_by('id')[:size]
        size = Collabcard.objects.filter(community=community_id).count()
    else:
        cards = Collabcard.objects.filter(community=community_id).order_by('id')
        size = cards.count()

    # collabcard_url=request.build_absolute_uri()
    # if collabcard_url in custom_cache:
    #     card_list=custom_cache.get(collabcard_url)
    # else:
    if True:
        card_list = []
        for card in cards:
            user = Userinfo.objects.get(user_id=card.user)
            # serialize user object
            usr = UserinfoSerializer(user)
            # form responses of user
            form_response = FormResponseSerilaizer(card.community.id, card.user.id,bl=True,current_user_id=current_user_id)
            if form_response:
                usr['response'] = form_response[0]
                usr['question_answers'] = form_response[1]
            # get card images --------------------------------------------------------
            files = get_collabcard_files(card)
            # -----------------------------------------------------------------------
            # share_url = url+'/collabcard/'+str(card.id)

            time_text = '' if str(card.date_epoch) == "-9223372036854775808" else get_time_text(card.date_epoch)
            card_dict = CollabcardSerializer(card, member_id, card.community)
            card_dict['state'] = get_status_of_collabcard(member_id, community, card)
            card_dict['created_at'] = time_text
            card_dict['member'] = usr
            card_dict['images'] = files[0]
            card_dict['pdf'] = files[1]
            card_list.append(card_dict)
        # custom_cache.set(collabcard_url,card_list,timeout=CACHE_TTL)
    # card_list=list(Collabcard.objects.filter(community_id=community).values_list("id",flat=True))
    # print(card_list)
    return JsonResponse({'collabcards': card_list, 'size': size})



def community_collabcard_invite(request,community_id):

    '''api to send collabcard invite footer'''

    community = Community.objects.get(id=community_id)
    member_id = request.GET.get('member_id')

    community_serializer_instance = CommunitySerializer(community)

    #if the community is a user-created community
    if community_serializer_instance['state'] == 0 or community_serializer_instance['state'] == 1 or community_serializer_instance['state'] == 5:
        json_response = {

            'community': community_serializer_instance,

        }
        return JsonResponse(json_response)

    #initializing variables


    community_live_subtitle=""
    invite_prompt={}



    number_of_members = community.members_count
    members_left = ig_members_count - number_of_members
    card_list = []

    # prompt for invite  for ig and lg community

    unlock_title = "Invite members"
    if members_left == 1:
        unlock_sub_title = "To start a conversation, invite %s more member to this community and make this community live." % (
            members_left)
        community_live_title = "more member required"
    else:
        unlock_sub_title = "To start a conversation, invite %s more members to this community and make this community live." % (
            members_left)
        community_live_title = "more members required"

    unlock_action_title = "OK, INVITE NOW"
    unlock_action = """route://community?community_id=%s&share=true&source=community_live_unlock"""


    # community live for ig communities
    if community_serializer_instance['community_type'] == 0:
        community_name = community.name
        member_types = community_name.split("of")[0].strip()
        member_type = member_types
        if member_types[-1] == "s":
            member_type = member_types[0:-1]

        member_types = member_types.lower()
        member_type = member_type.lower()

        # community live sub_title logic

        community_live_subtitle = """Every community needs its members to make purposeful conversations. Invite %s or more members to start conversations.""" % (
            members_left)
        if number_of_members == 1:
            community_live_subtitle = """Awesome, you have taken the first step! Be the spark to ignite this community by inviting other %s from your network.""" % (
                member_types)
        elif number_of_members == 2:

            member_list = Members.objects.filter(community_id=community_id)
            print(member_list)
            member_name = ""
            for member in member_list:
                if member_id == str(member.member_id.id):
                    continue
                if member.state == 4:
                    member_name = member.member_id.userinfo.name
            community_live_subtitle = """Superb, you and %s are now together for your shared interest! Invite 2 other %s and let them join you in this community.""" % (
            member_name, member_types)

        elif number_of_members == 3:

            member_list = Members.objects.filter(community_id=community_id).order_by('-id')
            other_member_list = []
            for member in member_list:
                if member_id == str(member.member_id.id):
                    continue
                member_name = member.member_id.userinfo.name
                if member.state == 4:
                    other_member_list.append(member_name)
            if other_member_list:
                community_live_subtitle = """You, %s  and %s  make a great group! Make it a community by inviting 1 more %s.""" % (
                other_member_list[0], other_member_list[1], member_type)

        # invite prompt logic
        invite_prompt = {}

        ref_members = get_referred_members_of_a_member(community_id, member_id)
        ref_members_count = len(ref_members)

        if ref_members_count == 0:
            invite_prompt['title'] = """Know any %s?""" % (member_type)
            invite_prompt['sub_title'] = """Invite a new member here and unlock a tool"""
            invite_prompt['action_title'] = """Invite"""
            invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (community_id)
        elif ref_members_count == 1:
            invite_prompt['title'] = """Unlock a new tool"""
            invite_prompt['sub_title'] = """By inviting 2 more members to this community"""
            invite_prompt['action_title'] = """Invite"""
            invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (community_id)
        elif ref_members_count == 2:
            invite_prompt['title'] = """Unlock a new tool"""
            invite_prompt['sub_title'] = """By inviting 1 more member to this community"""
            invite_prompt['action_title'] = """Invite"""
            invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (community_id)
        elif ref_members_count == 3:
            invite_prompt['title'] = """Become a promoter"""
            invite_prompt['sub_title'] = """Get recognised by inviting 2 more members"""
            invite_prompt['action_title'] = """Invite"""
            invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (community_id)
        elif ref_members_count == 4:
            invite_prompt['title'] = """Become a promoter"""
            invite_prompt['sub_title'] = """Get recognised by inviting 1 more member"""
            invite_prompt['action_title'] = """Invite"""
            invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (community_id)
        else:
            invite_prompt['title'] = """Promote your community"""
            invite_prompt['sub_title'] = """Let other %s discover this community""" % (member_types)
            invite_prompt['action_title'] = """Invite"""
            invite_prompt['action'] = """route://community?community_id=%s&share=true&source=invite_prompt""" % (community_id)



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



    if members_left > 0:

        community_live = {
            'members_left': members_left,
            'title': community_live_title,
            'sub_title': community_live_subtitle,
            'action_title': "Invite Friends",
            'action': """route://community?community_id=%s&share=true&source=community_live""" % (community_id),

            'unlock_title': unlock_title,
            'unlock_sub_title': unlock_sub_title,
            'unlock_action_title': unlock_action_title,
            'unlock_action': unlock_action

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

    '''function to return intro collabcard and verified list'''

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





def community_cards_version_1(request,community_id):

    '''Version 1 community cards for ig communities'''

    community = Community.objects.get(id=community_id)
    member_id = request.GET.get('member_id')

    current_user_id = get_member_id_from_headers(request)

    size = request.GET.get('size', '')
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
        card_dict['state'] = get_status_of_collabcard(member_id, community, card_instance)
        card_dict['created_at'] = time_text
        card_dict['member'] = usr
        card_dict['images'] = files[0]
        card_dict['pdf'] = files[1]
        card_list.append(card_dict)

    json_response = {
        'collabcards': card_list,
        'size': size,
    }
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


def get_status_of_collabcard(member_id, community, card):
    '''function to get the state of collabcard'''
    state = 0
    member_id = User.objects.get(id=member_id)
    collabcard_state = collabcardState.objects.filter(card=card, user=member_id)

    if collabcard_state:
        state = collabcard_state[0].state
        return state
    return state


# /api/create_answer?collabcard_id=&member_id=
@csrf_exempt
def create_answer(request):
    '''function to post answer on collabcard'''
    body = request.GET
    if 'member_id' in body:
        user_id = body['member_id']
    user = User.objects.get(id=user_id)
    if 'collabcard_id' in body:
        card_id = body['collabcard_id']
    card = Collabcard.objects.get(id=card_id)

    if request.method == 'POST':
        res = json.loads(request.body)
        ans = card_answers()
        ans.answer = res['title']
        ans.card = card
        ans.user = user
        ans.date_epoch = time.time()
        ans.save()
        update_last_answer_id(card_id, ans.id)

        # auto following the collabcard if answer is created
        function_dict = {
            'member_id': user_id,
            'collabcard_id': card_id,
            'status': True
        }
        collabcard_follow(request, function_dict)

        send_follow_notification.delay(card_id=card_id, user_id=user_id, answer=res['title'])

        # calling update_answer_text
        if card.type == 0 or card.type == 1:
            print("type === ", card.type)
            update_answer_text(card_id)

        return JsonResponse({'success': True,'id':ans.id})

    return JsonResponse({'success': False})


def _send_notification_to_tagged_users(card_id, answerer_name, answer, user_id):
    tagged_users = re.findall("route://member/"'([0-9]+)', answer)
    answer_text = re.split('>>', answer)[-1]
    send_follow_notification.delay(card_id=card_id, user_id=user_id, answer=answer, tagged_users_list=tagged_users)
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

    if not function_dict:
        collabcard_id = request.GET.get('collabcard_id', '')
        member_id = request.GET.get('member_id', '')
        status = request.GET.get('value', 'true')

        if status != 'true':
            status = False
        else:
            status = True
    else:
        collabcard_id = function_dict['collabcard_id']
        member_id = function_dict['member_id']
        status = function_dict['status']

    collabcard = Collabcard.objects.get(id=collabcard_id)
    community_instance = collabcard.community
    user_instance = User.objects.get(id=member_id)

    if collabcard.type == 2 and status:  # the collabcard is the event card

        collabcard_state_instance = collabcardState.objects.get(card=collabcard, user=user_instance)

        # when the user is not attending but following the collabcard
        if collabcard_state_instance.state == 1:

            collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_UNATTEND_FOLLOWING
            collabcard_state_instance.updated_at = time.time()
            collabcard_state_instance.save()
        # when the user is attending and following the collabcard
        elif collabcard_state_instance.state == collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING:

            collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING
            collabcard_state_instance.updated_at = time.time()
            collabcard_state_instance.save()
        return JsonResponse({'success': True})

    elif collabcard.type == 2 and not status:
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
        return JsonResponse({'success': True})

    is_present = collabcardState.objects.filter(card=collabcard, user=user_instance)
    if not is_present:
        collabcard_state_instance = collabcardState()
        collabcard_state_instance.card = collabcard
        collabcard_state_instance.community = community_instance
        collabcard_state_instance.user = user_instance
        collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_FOLLOW
        collabcard_state_instance.created_at = time.time()
        collabcard_state_instance.updated_at = time.time()
        collabcard_state_instance.save()
    else:

        if status:
            collabcardState.objects.filter(card=collabcard, user=user_instance).update(state=collabcard_states.COLLABCARD_STATE_FOLLOW,
                                                                                       updated_at=time.time())
        else:
            collabcardState.objects.filter(card=collabcard, user=user_instance).update(state=collabcard_states.COLLABCARD_STATE_SEEN,
                                                                                       updated_at=time.time())

    # custom_cache.clear()
    return JsonResponse({'success': True})


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

    if str(collabcard_type) == str(5):                        #unverifeid collabcard
        collabcardTemp.objects.filter(id=card_id).update(state=1)
        return JsonResponse({'success': True})


    community = Community.objects.get(id=community_id)
    user_instance = User.objects.get(id=user_id)
    card_instance = Collabcard.objects.get(id=card_id)

    # saving the state in collabcard state table if it is not present
    is_present = collabcardState.objects.filter(card=card_instance, user=user_instance)
    if not is_present:
        collabcard_state_instance = collabcardState()
        collabcard_state_instance.card = card_instance
        collabcard_state_instance.community = community
        collabcard_state_instance.user = user_instance
        collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_SEEN
        collabcard_state_instance.created_at = time.time()
        collabcard_state_instance.updated_at = time.time()
        collabcard_state_instance.save()

    update_last_unseen_in_engage(user=user_instance, community=community,is_seen=False)
    # custom_cache.clear()
    return JsonResponse({'success': True})


@csrf_exempt
def collabcard_attend(request):
    '''attending a event on a event card'''

    member_id = get_member_id_from_headers(request)
    collabcard_id = request.GET.get('collabcard_id')
    status = request.GET.get('value', 'true')
    collabcard_instance = Collabcard.objects.get(id=collabcard_id)
    user_instance = User.objects.get(id=member_id)

    if status != 'true':
        status = False
    else:
        status = True

    if status:

        # if the user clicks on attend but not following collabcard
        collabcard_state_instance = collabcardState.objects.get(card=collabcard_instance, user=user_instance)
        if collabcard_state_instance.state == collabcard_states.COLLABCARD_STATE_SEEN:
            collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING
            collabcard_state_instance.updated_at = time.time()
            collabcard_state_instance.save()

        elif collabcard_state_instance.state == collabcard_states.COLLABCARD_STATE_UNATTEND_FOLLOWING:
            # if the user clicks on attend and following collabcard
            collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING
            collabcard_state_instance.updated_at = time.time()
            collabcard_state_instance.save()
    else:
        collabcard_state_instance = collabcardState.objects.get(card=collabcard_instance, user=user_instance)

        if collabcard_state_instance.state == collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING:
            collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_SEEN
            collabcard_state_instance.updated_at = time.time()
            collabcard_state_instance.save()

        elif collabcard_state_instance.state == collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING:
            # if the user clicks on attend and following collabcard

            collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_UNATTEND_FOLLOWING
            collabcard_state_instance.updated_at = time.time()
            collabcard_state_instance.save()

    update_event_answer_text(collabcard_id)  # function to update the text when a user attends an event
    if not str(member_id) == str(collabcard_instance.user.id) and status:
        send_poll_or_event_notification.delay(card_id=collabcard_id, user_id=member_id)

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
        card_dict['state'] = get_status_of_collabcard(member_id, card_instance.community, card_instance)
        card_dict['created_at'] = time_text
        card_dict['member'] = usr
        card_dict['images'] = files[0]
        card_dict['pdf'] = files[1]
        card_list.append(card_dict)

    if community_instance:
        community=CommunitySerializer(community_instance)
        return JsonResponse({'collabcards': card_list,'community':community})

    return JsonResponse({'collabcards': card_list})


############# upload files flow   ##########################

@csrf_exempt
def image_upload(request):
    ''' function to upload community images '''
    body = request.GET
    if request.method == 'POST':
        # if 'member_id' in body:
        #     user_id = body['member_id']
        #     user = User.objects.get(id = user_id)
        new_image = request.FILES['file']
        if 'community_id' in body:
            # if image to be updated in community
            community_id = body['community_id']
            community = Community.objects.get(id=community_id)
            old_image_file = community.image_url

            # # deleting the old file after new file is updated
            # # get the new image file
            version = re.findall(r'\w*__image__(\d+)', old_image_file.name)
            if version:
                version = int(version[0]) + 1
            else:
                version = 1
            new_image.name = str(community_id) + '__image__' + str(version) + '.jpg'

            if not old_image_file == new_image:
                #     # if both are not same delete old file
                if os.path.isfile(old_image_file.path):
                    os.remove(old_image_file.path)

                community.image_url = new_image
                community.save()

        elif 'collabcard_id' in body:

            # if image to be updated in collabcard
            collabcard_id = body['collabcard_id']
            collabcard = Collabcard.objects.get(id=collabcard_id)

            card_image = Card_Attachment.objects.filter(collabcard=collabcard).order_by('-id')
            if card_image:
                old_image_file = card_image[0].attachment
                if os.path.isfile(old_image_file.path):
                    version = re.findall(r'\w*__image__(\d+)', old_image_file.name)
                    if version:
                        version = int(version[0]) + 1
                    else:
                        version = 1
                    new_image.name = str(collabcard_id) + '__image__' + str(version) + '.jpg'
                    card_image = Card_Attachment()
                    card_image.collabcard = collabcard
                    card_image.attachment = new_image
                    card_image.type = 'Image'
                    card_image.save()

            else:
                card_image = Card_Attachment()
                new_image.name = str(collabcard_id) + '__image__' + str(0) + '.jpg'
                card_image.collabcard = collabcard
                card_image.attachment = new_image
                card_image.type = 'Image'
                card_image.save()
        return JsonResponse({'success': True})


@csrf_exempt
def upload_attachment(request):
    '''function to upload attachments'''
    body = request.GET
    if request.method == 'POST':
        attachment = request.FILES['file']
        if 'community_id' in body:
            # if image to be updated in community
            community_id = body['community_id']
            community = Community.objects.get(id=community_id)
            old_image_file = community.image_url
            # deleting the old file after new file is updated
            # get the new image file
            if not old_image_file == attachment:
                # if both are not same delete old file
                if os.path.isfile(old_image_file.path):
                    os.remove(old_image_file.path)

            community.image_url = attachment
            community.save()
        elif 'collabcard_id' in body:
            attachment_type = body['type']
            collabcard_id = body['collabcard_id']
            collabcard = Collabcard.objects.get(id=collabcard_id)

            file = Card_Attachment()
            file.attachment = attachment
            file.collabcard = collabcard
            file.type = attachment_type
            file.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@csrf_exempt
def upload_files(request):
    '''function to upload files'''

    body = request.GET
    if request.method == 'POST':

        if 'community_id' in body:
            # if image to be updated in community
            community_id = body['community_id']
            community = Community.objects.get(id=community_id)
            community.image_link = body['url']
            upload_community_thumbnail.delay(community_id, body['url'])
            community.save()
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
            answer_obj = card_answers.objects.get(id=answer_id)

            file = Answer_Attachment()
            file.answer = answer_obj
            file.type = attachment_type
            file.file_url = body['url']
            file.save()

        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


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
        else:
            create_member_for_feedback_community(userinfo.user_id)
            return JsonResponse({'user': usr, 'has_tags': has_tags})

    return HttpResponse('Login Api')

@csrf_exempt
def login_authenticate_version_1(request):
    ''' function to login a user '''

    if request.method == 'POST':
        res = json.loads(request.body)

        login_type = res['type']
        if login_type == "google":
            if 'google_id_token' in res:
                google_id_token = res['google_id_token']
                context = login_with_google(google_id_token,request)
                info_logger.info(context)
                return JsonResponse(context)
            return JsonResponse({'success':False,'error_message':"send google id token in body"})



        dic_form = res['login_json']
        json_to_save = json.dumps(dic_form)
        # if user is logging in from facebook
        created = False
        if login_type == 'facebook':
            res = res['login_json']
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

            res = res['login_json']
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
        else:
            create_member_for_feedback_community(userinfo.user_id)
            return JsonResponse({'user': usr, 'has_tags': has_tags})

    return HttpResponse('Login Api')


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


def create_member_for_feedback_community(user_instance):

    '''function to make user directly a member of feedback community'''

    is_member=Members.objects.filter(community_id=feedback_community_id,member_id=user_instance)

    community_instance = Community.objects.get(id=feedback_community_id)

    if not is_member.exists():                                                #not is_member.exists()
        member_instance=Members()
        member_instance.member_id=user_instance
        member_instance.community_id=community_instance
        member_instance.state=member_states.MEMBER
        member_instance.created_at=time.time()
        member_instance.save()


    if not is_member_engage(community_instance,user_instance):          #not is_member_engage(community_instance,user_instance)

        card_instance=Collabcard.objects.get(id=feedback_collabcard_id)
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.last_unseen_conversation = card_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.MEMBER
        engage.save()


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
    context ={'success':False,'error_message':"please give permission to use your google account"}

    is_request_web = False

    platform_code = get_platform_code_from_headers(request)
    
    if not platform_code:
        is_request_web = True

    if 'email' in res:
        email = res['email']
        email = email.lower().strip()
        user = User.objects.filter(email=email)

        if not user.exists():
            # creating a user if no user is associated with that email
            res['id'] = res['azp']

            user = create_user(user_name=res['name'], email=res['email'], id=res['id'])

            if 'picture' in res:
                image_link = upload_image_to_firebase(res['picture'], user.id)
            else:
                image_link = 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'

            userinfo = create_userinfo(user=user, email=res['email'], user_name=res['name'],
                                       profile_picture=image_link, login_type=login_type,
                                       json_to_save=json_to_save
                                       )
            created = True
            mail_triger(str(user.id), request)  # both mail and notification will be sent here

        if not created:
            userinfo = user[0].userinfo



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

        else:
            create_member_for_feedback_community(userinfo.user_id)


        if is_request_web:

            login(request,user=userinfo.user_id,backend="django.contrib.auth.backends.ModelBackend")

        context = {'user': usr, 'has_tags': has_tags}

    return context




def notify_referred_member_after_join(joined_member_id, joined_member_name, community_name, community_id):
    community = get_object_or_404(Community, pk=community_id)
    refer = Referal.objects.filter(invited_member=joined_member_id,
                                   community=community)
    if refer.exists():
        referred_member_id = refer[0].member.id

        notify_referred_member.delay(referred_member_id=referred_member_id,
                                     joined_member_name=joined_member_name,
                                     community_name=community_name,
                                     community_id=community_id)


def get_state_of_community(community):

    if community.hide_community:
        return int(community.hide_community)
    return 0

def members_state(request):
    '''This function gives the state of user.Get Api'''

    member_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')
    collabcard_id = request.GET.get('collabcard_id')
    # if not collabcard_id.isdigit():
    #     return JsonResponse({'state':0})
    if collabcard_id and not community_id:
        card = Collabcard.objects.get(pk=collabcard_id)
        community_id = card.community.id

    state = 0
    tool_state = 0
    query_set = Members.objects.filter(member_id=member_id, community_id=community_id)
    community_instance=Community.objects.get(id=community_id)

    community_state = get_state_of_community(community_instance)

    is_tool_state = False

    if community_state == community_states.PRIVATE or community_state == community_states.PILOT_ACTIVE or community_state ==  community_states.WHATSAPP:
        is_tool_state = True

    user_email = ""
    ref_members=[]
    for data in query_set:
        is_member = False
        tool_state = 0
        state = data.state

        if state == member_states.ADMIN or state == 2 or state == member_states.MEMBER or state == 7:
            is_member = True

        if state == member_states.PENDING_MEMBER:
            user_email = data.member_id.userinfo.email

        if is_member and is_tool_state:
            tool_state = 1

        ref_members = get_referred_members_of_a_member(community_id, member_id)

    if state == 0:
        '''checking if user DETAILS EXIST in temp admin table in case he is a newly registered user'''
        user = Userinfo.objects.get(user_id=member_id)
        community = get_object_or_404(Community, pk=community_id)
        check = get_nominated_admin_details(community_id=community_id, email=user.email)
        if check:
            '''creating a new row in members table making current
            user a nominated promoter of this community,if he is a newly
            registered user and his details are present in temp admin table'''
            member = Members()
            member.member_id = user.user_id
            member.community_id = community
            member.state = 6
            member.save()
            state = 6
        else:
            state = 0
    referred_members_count=len(ref_members)
    tool_unlock_sub_title=""
    if referred_members_count == 0:
        tool_unlock_sub_title="Some features might be available only for active members of the community. Invite a new member and unlock a tool"
    elif referred_members_count == 1:
        tool_unlock_sub_title="Some features might be available only for active members of the community. Invite 2 more members and unlock this tool"
    elif referred_members_count == 2:
        tool_unlock_sub_title="Some features might be available only for active members of the community. Invite 1 more member and unlock this tool"



    diff=eligibility_count-referred_members_count

    #sending pop-up for lg community
    community_instance=Community.objects.get(id=community_id)
    unlock_title="Can’t Engage Yet"
    unlock_sub_title="Your verification for joining this closed group is still pending. Engaging is not open for non verified members. Verify your credentials."
    unlock_action_title="REQUEST COMMUNITY MEMBERS"
    unlock_action="""route://member_ask?community_id=%s&community_name=%s"""%(community_instance.id,community_instance.name)

    if diff <= 0:
        json_response = {'state': state,
                         'tool_state': tool_state,
                         'referred_members_count': referred_members_count,
                         'tool_unlock_title': "Unlock Feature",
                         'tool_unlock_sub_title': tool_unlock_sub_title,
                         'tool_unlock_action_title': "OK, INVITE NOW",
                         'tool_unlock_action': """route://community?community_id=%s&share=true&source=tool_unlock""" % (community_id),
                         'unlock_title':unlock_title,
                         'unlock_sub_title':unlock_sub_title,
                         'unlock_action':unlock_action,
                         'unlock_action_title':unlock_action_title
                         }
    else:

        if diff == 1:
            tool_title = """Invite friends to unlock features.If you invite %s friend, You will be highlighted as a promoter of this community.""" % (
            diff)
        else:
            tool_title = """Invite friends to unlock features.If you invite %s friends, You will be highlighted as a promoter of this community.""" % (
                diff)

        json_response={'state': state,
                   'tool_state': tool_state,
                   'referred_members_count':referred_members_count,
                   'tool_title':tool_title,
                   'tool_unlock_title':"Unlock Feature",
                   'tool_unlock_sub_title':tool_unlock_sub_title,
                   'tool_unlock_action_title':"OK, INVITE NOW",
                   'tool_unlock_action':"""route://community?community_id=%s&share=true&source=tool_unlock""" % (community_id),
                   'unlock_title': unlock_title,
                   'unlock_sub_title': unlock_sub_title,
                   'unlock_action': unlock_action,
                   'unlock_action_title':unlock_action_title

                   }


    if state == member_states.PENDING_MEMBER:
        json_response['member_direction_lock'] = get_data_for_filter_pop_ups(email=user_email)
    return JsonResponse(json_response)





@csrf_exempt
def push(request):
    '''This function is used to insert fcm token to the database in order to generate notifications from database'''

    member_id = request.GET.get('member_id', '')
    token = request.GET.get('token', '')
    print('member_id ===>>> ', member_id)
    if member_id:
        is_member = Userinfo.objects.filter(user_id=member_id)
    else:
        is_member = None
    success = False
    if is_member:
        success = True
        if not is_member[0].fcm_token:
            send_welcome_mail.delay(member_id)
        fcm_token = Userinfo.objects.filter(user_id=member_id).update(fcm_token=token)

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

    json_body = json.loads(request.body)

    key = json_body['key']

    if key == 'purpose':
        value = json_body['value']
        purpose_collabcard = Community.objects.filter(id=community_id).values('purpose_collabcard')
        purpose_collabcard = purpose_collabcard[0]['purpose_collabcard']
        Collabcard.objects.filter(id=purpose_collabcard).update(title=value)
        Community.objects.filter(id=community_id).update(purpose=value)

    elif key == 'questions':
        questions = json_body['questions']
        edit_questions(questions, community_id)
    else:
        value = json_body['value']
        Community.objects.filter(id=community_id).update(**{key: value})

    community = Community.objects.get(id=community_id)

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

@api_view(['GET', 'POST'])
@renderer_classes([JSONRenderer, TemplateHTMLRenderer])
def all_members(request):
    print('in all members')
    '''function to send all members of community '''
    page = request.GET.get('page',1)
    community_id = request.GET.get('community_id')





    current_user_id = get_member_id_from_headers(request)

    #functionality for user filteration based on options
    is_filter = request.GET.get('is_filter',False)


    if is_filter == 'true':
        is_filter = True
        member_list = Members.objects.filter(community_id=community_id).filter(
            Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) | Q(
                state=member_states.KNOWN_NOMINATED_PROMOTER) | Q(state=member_states.PENDING_MEMBER)).order_by('id')
        member_list = pagination(member_list, page, paginate_by=20)
        filter_list = request.GET.get('filter', None)


        if filter_list:
            filter_list = json.loads(filter_list)
            info_logger.info(filter_list)
            # filter_list =[{'question_id': '48219', 'value': 'Not Bowler'}, {'question_id': '48220', 'value': 'Middle order'}, {'question_id': '48219', 'value': 'Fast bowler'}, {'question_id': '48220', 'value': 'Tail hander'}]
            member_set = get_filtered_users(filter_list, member_list)
            members = get_member_instances(member_list, current_user_id, community_id, is_filter=is_filter,
                                           member_set=member_set)
        else:
            is_filter = False
            member_list = Members.objects.filter(community_id=community_id).filter(
                Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) | Q(
                    state=member_states.KNOWN_NOMINATED_PROMOTER)).order_by('id')
            member_list = pagination(member_list, page, paginate_by=20)
            members = get_member_instances(member_list, current_user_id, community_id)


    else:
        is_filter = False
        member_list = Members.objects.filter(community_id=community_id).filter(
            Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) | Q(
                state=member_states.KNOWN_NOMINATED_PROMOTER)).order_by('id')
        member_list = pagination(member_list, page, paginate_by=20)
        members = get_member_instances(member_list, current_user_id, community_id)


    if request.accepted_renderer.format == 'html':
        print('in html')
        return render(request, 'filtered_members.html', {'members':members})
    else:
        return JsonResponse({'members':members})


def get_member_instances(member_list,current_user_id,community_id,is_filter=False,member_set=None):

    members = []

    for member in member_list:
        member_id = member.member_id.id
        userinfo_serialized_object = UserinfoSerializer(member.member_id.userinfo)
        userinfo_serialized_object['state'] = member.state

        form_response = FormResponseSerilaizer(community_id,member_id , bl=True,
                                               current_user_id=current_user_id)

        if form_response:
            userinfo_serialized_object['response'] = form_response[0]
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


@csrf_exempt
def accept_promotership(request):
    '''function to accept the promotership'''

    res = json.loads(request.body)
    community_id = res['community_id']
    member_id = res['member_id']
    value = res['value']
    all_members = Members.objects.filter(community_id=community_id)
    community = Community.objects.get(id=community_id)
    if value == 'true' or value:

        if 'member_ids' not in res or not res['member_ids']:
            Members.objects.filter(community_id=community_id, member_id=member_id).update(state=1,
                                                                                          created_at=time.time())
            user = User.objects.get(pk=member_id)
            name = user.userinfo.name
            send_notification_to_all_admins.delay(community_id, name, member_id)
            return JsonResponse({'success': True})

        refered_id = res['member_ids']
        for member in all_members:

            if str(member.member_id.id) == str(member_id):
                continue

            elif (str(member.member_id.id) in refered_id) or (int(member.member_id.id) in refered_id):
                req_dict = {
                    'accepted': True,
                    'member_id': member.member_id.id,
                    'community_id': community_id,
                    'send_notification': False,
                }
                request_response(request, req_dict)
            else:
                Members.objects.filter(community_id=community_id, member_id=member.member_id.id).update(state=3)

    # update member engage table enteries
    update_pending_member_count_in_engage(community)
    #update_referral_text_in_engage_table.delay(community_id)
    update_member_count(community_id)
    return JsonResponse({'success': True})


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


def get_member_id_from_headers(request):
    '''function to get member id from headers'''
    headers = request.META

    member_id = 0
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
    send_mail_after_rank_computation.delay(user_id)  # both mail and notification will be sent here
    Userinfo.objects.filter(user_id=user_id).update(has_tags=True)
    return JsonResponse({'success': True})


def save_geography_and_hometown_tags_of_user_from_onboarding(address_input, user_id, attribute_id, category_id):
    '''function to take the address of the user and get its city,state and country tags to save in tags'''

    user_address = get_city_address(city=address_input)

    city = user_address['city']
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
        report_tags_instance = Report_Tags.objects.get(id=tag_id) if tag_id else None

        reason = request_body['reason'] if 'reason' in request_body else None
        reported_member_id = int(request_body['reported_member_id']) if 'reported_member_id' in request_body else None

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
        report_instance.save()

        community_url = url + "/community/" + str(collabcard_instance.community.id)
        try:
            if reported_member_id:
                reported_user_instance = User.objects.get(pk=reported_member_id)
                reported_user_name = reported_user_instance.userinfo.name
            else:
                reported_user_name = None
            send_mail_for_report_abuse.delay(user_instance.userinfo.name, collabcard_instance.title,
                                                            report_tags_instance.tag_name,
                                                            collabcard_instance.community.name,
                                                            community_url, reported_user_name, reason)
        except Exception as e:
            log = """Unmatched object for user_id=%s""" % (request_body['reported_member_id'])
            info_logger.info(log)
            info_logger.info(e)
        info_logger.info("push report api successfull")
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


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

        if not str(member_id) == str(card_instance.user.id):
            send_poll_or_event_notification.delay(card_id=collabcard_id, user_id=member_id)

        return JsonResponse({"success": True})

    return JsonResponse({"success": False})


def update_poll_card_text(card_id):
    """ function to update the answer text of card when someone polls in the card """

    total_polls = MemberPollVotes.objects.filter(card=card_id).order_by('-id')

    card = Collabcard.objects.get(pk=card_id)
    poll_text = ''
    total_polls_count = total_polls.count()

    if total_polls_count <= 0:
        card.answer_text = poll_text
        card.save()
        return

    elif total_polls_count == 1:
        user_names = total_polls[0].user.userinfo.name

    elif total_polls_count == 2:
        user_names = total_polls[0].user.userinfo.name + " and " + total_polls[1].user.userinfo.name

    else:
        user_names = total_polls[0].user.userinfo.name + ", " + total_polls[1].user.userinfo.name + " & " + str(
            total_polls_count - 2) + " others"

    poll_text += user_names + " voted on this poll"

    card.answer_text = poll_text
    card.polls_count = total_polls_count
    card.save()

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





