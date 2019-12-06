from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from togther.models import *
from togther.forms import *
from django.contrib.auth.models import User
import json
from django.http.response import JsonResponse
from collabmates_api.serializers import *
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.db.models import F
import time
from .notification import (send_follow_notification, send_notification_to_admins,
                           send_notification_for_join_requests,
                           send_notification_for_new_collabcard_posted,
                           send_notification_to_proposed_admin,
                           send_notification_to_proposer,
                           send_notification_to_eligible_member,
                           send_notification_to_all_admins)

from django.db.models import Q
import dateutil.relativedelta
from .tasks import send_email_to_nominated_admin, send_email_for_new_collabcard_posted, send_welcome_mail
from django.conf import settings
from togther.tasks import send_email_to_proposed_admin, send_mail_after_rank_computation
from django.core.paginator import Paginator
from togther.views import get_nominated_admin_details
import os
import re
import googlemaps
import logging
from PIL import Image

from utility.utils import (decode_meta_from_url, update_tag_image,
                           referal, get_referred_members_of_a_member,
                           eligibility_count, notify_referred_member,
                           user_onbaord, update_member_count,
                           update_community_tags_to_user,tutorial_count,custom_cache,cache_timeout,
                           get_city_address,
                           update_user_geography_tags, create_or_categorize_tag,
                           insert_user_home_town_tags,user_onbaord)

from utility.tasks import (mail_triger, new_member_request)
from utility.firebase import update_last_answer_id,upload_image_to_firebase,upload_community_thumbnail,upload_community_files
from .raw_queries import compute_rank

CACHE_TTL = getattr(settings, 'CACHE_TTL', cache_timeout)


url  = settings.URL

error_logger = logging.getLogger("error_logger")
info_logger = logging.getLogger("info_logger")
# /api/communities?category_id=&member_id=

############# functions for community api ##########################
def communities(request):

    ''' function to get all the communities '''

    communities_url=request.build_absolute_uri()
    if request.method == 'GET':
        info_logger.info("added")
        request = request.GET.dict()
        if 'member_id' in request:
            # get member id and members hidden tag
            user_id = request['member_id']
            user_tag = 0
        if 'page' in request:
            # if page number is in request
            page_number = request['page']
        else:
            # set default page number
            page_number = 1
        if 'category_id' in request:
            if request['category_id'] != '':
                # if communites are filtered by category
                category = request['category_id']
                # get category id'''
                category = int(category)
                # get the related communities according to category asked and user hidden tag
                community = get_communities_by_tags(category_tag=category, user_tag=user_tag,page_number = page_number,user_id=user_id)
                # serialize the communities objects recieved from above function
                community = serialize_community(queryset =community)
                # send communities JSON response '''
                return JsonResponse({'communities': community})
            else:
                # if category is not provided, get categories according to the user tag if user has one
                #custom_cache.clear()
                print(custom_cache.keys('*'))
                cache_key=communities_url

                if cache_key in custom_cache:
                    community=custom_cache.get(cache_key)
                else:
                    queryset = get_communities_by_tags(user_tag=user_tag,page_number = page_number,user_id=user_id)
                    community = serialize_community(queryset=queryset)
                    custom_cache.set(cache_key,community,timeout=CACHE_TTL)
                info_logger.info(community)
                #custom_cache.clear()
                return JsonResponse({'communities': community})

def get_communities_by_tags(user_tag=0, category_tag=0,page_number=1,user_id=None):
    ''' fetching communities based on category tag and user hidden tag '''

    is_user_tags = Community_Rank.objects.filter(member_id=user_id)

    if is_user_tags:
        if user_id:

            user_tag = Community_Rank.objects.filter(member_id=user_id).values('community_id').order_by(
                    "-weight").distinct()
            queryset = pagination(user_tag, page_number)
            return queryset

    if category_tag != 0 and user_tag != 0:
        ''' if category tag and user tag ,bith are provided
            get communities ,which are the intersection of given category and user hidden tag '''

        # get communities based on category tag
        category_tag = Community_tags.objects.filter(tags_id=category_tag).values('community_id')
        # get communities based on user hidden tag
        user_tag = Community_tags.objects.filter(tags_id=user_tag).values('community_id')
        #intersect both of the querysets
        res = category_tag.intersection(user_tag).order_by("-community_id").distinct()
        #paginating the resultant queryset
        queryset = pagination(res, page_number)
        #return result
        return queryset



    if category_tag == 0 and user_tag == 0:
        # if there is not category tag and user does not have a hidden tag too
        # just return him all the communites
        community =  Community_tags.objects.values('community_id').order_by("-community_id").distinct()
        # paginating the communities
        queryset = pagination(community, page_number)
        return queryset



    if category_tag == 0 and user_tag != 0:
        # if there is no category tag , then return communites based on user hidden tag
        user_tag = Community_Rank.objects.values('community_id').order_by("-weight").distinct()
        queryset = pagination(user_tag, page_number)
        return queryset

    if user_tag == 0 and category_tag != 0:
        # if there is no user hidden tag , then return communites based on category tag
        category_tag = Community_tags.objects.filter(tags_id=category_tag).values('community_id').order_by("-community_id").distinct()
        queryset = pagination(category_tag, page_number)
        return queryset

def serialize_community(queryset):
    ''' this function gives us a dictionary of community/communities objects based on given queryset '''
    communities = []
    for community in queryset:

        try:
            # if the queryset is of type dictionary
            comm = Community.objects.get(id=community['community_id'])
        except:
            # if the queryset if a lazy community object
            try:
                comm = Community.objects.get(id=community.id)
            except:
                comm=Community.objects.get(id=community)
        # check if the community is hidden or not

        if comm.hide_community == '0' or comm.hide_community == '3' or comm.hide_community =='4':
            # if not hidden , pass the community object to serializer or pre-created
            serialized_object = CommunitySerializer(comm)
            new_dict = {}
            # form a dictionary of community objects
            new_dict.update(serialized_object)

            communities.append(new_dict)
        elif comm.hide_community == '1':

            pass

    return communities


def pagination(queryset,page_number,paginate_by=20):

    '''function to create pagination and return a query set for page number'''
    paginator = Paginator(queryset, paginate_by)
    max_page=len(paginator.page_range)

    if max_page < int(page_number):
        return []
    queryset = paginator.get_page(page_number)

    return queryset



############# functions for your communities  api ##########################

def is_member_engage(community,member):

    '''function to check if data is presnt in member engage table or not'''

    is_present=False
    member_data=Member_Engage.objects.filter(community_id=community,member_id=member)
    if member_data:
        is_present=True
    return is_present


def update_pending_member_count_in_engage(community):

    '''function to update the member count in engage'''

    pending__members_count=Members.objects.filter(community_id=community,state=3).count()

    all_members=Members.objects.filter(community_id=community)
    current_time=time.time()
    for member in all_members:
        if member.state == 1 or member.state == 2:
            Member_Engage.objects.filter(community_id=community,member_id=member.member_id).update(
                pending_members=pending__members_count,updated_at=current_time,member_state=member.state)
        else:
            Member_Engage.objects.filter(community_id=community, member_id=member.member_id).update(member_state=member.state)

    info_logger.info("Member Engage Pending Count Updated")


def update_last_unseen_in_engage(user='',community='',is_seen=False):

    '''function to update the unseen  collabcard in engage'''

    total_collabcards = Collabcard.objects.filter(community=community).values('id').order_by('-id')
    seen_collabcard = collabcard_seen.objects.filter(community=community, user=user).values('card_id')

    unseen_count=total_collabcards.count() - seen_collabcard.count()
    if  unseen_count<= 0:
        # if zero or less than zero , unseen card count = 0
        collabcard_unseen = 0
    else:
        collabcard_unseen = (total_collabcards.count() - seen_collabcard.count())

    unseen_list = total_collabcards.difference(seen_collabcard).values('id').order_by('id')
    if total_collabcards.count() > 0:
        # if community has atleast one card
        if unseen_list.count() != 0:
            # if the unseen cards are present
            # show the latest unseen cards text
            card = Collabcard.objects.get(id=unseen_list.values('id')[0]['id'])

        else:
            # if no unseen cards , show latest card text
            card = Collabcard.objects.get(id=total_collabcards[0]['id'])

    current_time=time.time()
    Member_Engage.objects.filter(community_id=community,member_id=user).update(last_unseen_count=collabcard_unseen,
                                                                               last_unseen_conversation=card,
                                                                               updated_at=current_time)

    if is_seen == False:
        Member_Engage.objects.filter(community_id=community).filter(~Q(member_id=user)).update(last_unseen_count=collabcard_unseen,updated_at=current_time)


def update_referral_text_in_engage_table(community_object):

    '''function to update the referal text in member engage table by taking member engage object'''
    # getting the state of member

    engage_communities=Member_Engage.objects.filter(community_id=community_object)

    for each_community in engage_communities:
        community={}
        community['pending_members_count']=each_community.pending_members
        community['member_referral']=""
        member_state = Members.objects.filter(community_id=each_community.community_id.id,
                                              member_id=each_community.member_id.id)
        if member_state:
            state = member_state[0].state
            community_state = each_community.community_id.hide_community
            # if the community is pilot community and member has shown interest

            if community_state == '3' and state == 8:
                diff = eligibility_count - community['pending_members_count']
                if community['pending_members_count'] < (eligibility_count-2):
                    community['member_referral']="""[Pilot] Help this community find a promoter"""
                elif community['pending_members_count'] >= (eligibility_count-2) and  community['pending_members_count'] < (eligibility_count):
                    community['member_referral'] = """You have successfully referred %s. Refer %s and become promoter of this community."""%(community['pending_members_count'],diff)

            # if the community is pilot community and the member is eligible promoter
            elif community_state == '3' and state == 9:
                community['member_referral'] = "You are eligible to become a promoter of this community"

            # if the community is pilot-active and new promoter comes
            elif community_state == '4' and state == 9:
                community['member_referral'] = "You are eligible to become a promoter of this community"

            # if the community becomes a pilot-active community and member approval is pending
            elif (community_state == '4' or community_state == '0' or community_state == '1') and state == 3:
                community['member_referral'] = "Your request is waiting for approval by promoter"

            # if the community becomes a pilot-active community and member request is approved
            # elif community_state == '4' and state == 4:
            #     diff = eligibility_count - community['pending_members_count']
            #     if community['pending_members_count'] == 1:
            #         community['member_referral'] = """You have successfully referred %s member. Please refer %s more to become promoter.""" % (
            #             community['pending_members_count'], diff)
            #     elif community['pending_members_count']:
            #         community[
            #             'member_referral'] = """You have successfully referred %s members. Please refer %s more to become promoter.""" % (
            #             community['pending_members_count'], diff)
            elif community_state == '0' and community['pending_members_count']:
                community['member_referral'] = str(community['pending_members_count']) + " new member requests"

            each_community.member_referral=community['member_referral']
            each_community.member_state=state
            each_community.save()


# /api/your_communities/member_id?member_id=
def your_communities(request,user_id):
    '''This function is used to see your communities based on user id'''

    member_id=request.GET.get('member_id')
    page_number = request.GET.get('page','')
    if str(member_id) != str(user_id):
        member_id = user_id
    my_community=[]
    user=User.objects.get(id=member_id)
    communities=Member_Engage.objects.filter(member_id=user).order_by('-updated_at')
    if page_number:
        communities=pagination(communities,page_number,paginate_by=10)
    for each_community in communities:

        community=CommunitySerializer(each_community.community_id)
        community['pending_members_count']=each_community.pending_members
        community['updated_at']=get_time_text(each_community.updated_at)
        community['collabcard_unseen']=each_community.last_unseen_count
        if each_community.last_unseen_conversation:
            collabcard=CollabcardSerializer(each_community.last_unseen_conversation)
            user=each_community.last_unseen_conversation.user
            collabcard['member']=UserinfoSerializer(user.userinfo)
            community['collabcard']=collabcard

        if each_community.member_referral:
            community['member_referral']=each_community.member_referral
        if each_community.member_state:
            community['member_state'] = each_community.member_state
        my_community.append(community)

    return JsonResponse({'your_communities':my_community})



############# functions for  community detail screen ##########################

def get_community_card_details(each_community,user_id):
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
    seen_collabcard = collabcard_seen.objects.filter(community=community, user=user_id).values('card_id').order_by('-card_id')
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
        collabcard = CollabcardSerializer(card,community)

        new_dict['collabcard'] = collabcard

        # get user details who posted the latest card
        user = Userinfo.objects.get(user_id=card.user)
        # get json form of userinfo object
        usr = UserinfoSerializer(user)

        collabcard['member'] = usr

    return new_dict


def community(request, community_id):
    ''' Community detail page '''

    community = Community.objects.get(id=community_id)
    member_id = request.GET.get('member_id',None)
    serialized_object = CommunitySerializer(community)
    new_dict = {}

    if member_id and (community.hide_community == '3' or community.hide_community =='4'):
        serialized_object['share_url'] = serialized_object['share_url']+"?ref_id="+str(member_id)
    elif community.hide_community == '0' or community.hide_community == '1':
        serialized_object['share_url'] = serialized_object['share_url'] + "?cta=share"

    # form a dictionary of community objects
    new_dict.update(serialized_object)

    if community:
        new_dict['share_text_admin']= """Hi, I am trying to gather %s community on CollabMates. It will be good if you can join it.\n"""%(new_dict['name'])
        new_dict['share_text_member']="""I recently joined %s community on CollabMates. It will be good if you also join this community.\n"""%(new_dict['name'])
        new_dict['share_text_anonymous']="""I recently discovered %s community on CollabMates. You can join this community using this link.\n"""%(new_dict['name'])
    new_dict['min_referrer_member'] = eligibility_count
    return JsonResponse({'community': new_dict})


def similar_community(request, community_id):
    '''function to return similar communitites'''
    body = request.GET
    user_id = body['member_id']
    user_tag = 0
    # getting communities based on user hidden tags
    queryset = get_communities_by_tags(user_tag=user_tag,user_id=user_id)[:11]
    community = []
    for comm in queryset:

        
        try:
            comm_object = Community.objects.get(id=comm)
        except:
            # if the queryset is of type dictionary
            comm_object = Community.objects.get(id=comm['community_id'])
        # check if the community is hidden or not

        if comm_object.hide_community == '0' or comm_object.hide_community =='4' and comm_object.id != community_id:
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

    data = Form_data.objects.all().filter(community_id = community_id)
    reqd_info = []
    for i in data:
        ques = {'question':i.data,
                'data_type':i.data_type,
                }
        reqd_info.append(ques)
    return JsonResponse({'questions': reqd_info})


# /api/join_community?member_id=&community_id=
@csrf_exempt
def join_community_responses(request):

    '''function to join community'''
    res = json.loads(request.body)
    user_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')

    community = Community.objects.get(id=community_id)
    user = User.objects.get(id=user_id)

    if 'ref_id' in res:
        ref_id = res['ref_id']
    else:
        ref_id = request.GET.get('ref_id',None)

    info_logger.info("\n")
    info_logger.info("Join Community api")
    info_logger.info("""Community Id=%s"""%(community_id))
    info_logger.info("""Member Id=%s"""%(user_id))
    info_logger.info("""ref_id=%s""",str(ref_id))
    info_logger.info("""Community State=%s"""%str(community.hide_community))

    if ref_id :
        #ref_id = res['ref_id']
        # sending mail to nipun and harsh
        new_member_request.delay(member_id=user_id, commuinity_id=community_id, ref_id=ref_id)
        if community.hide_community == '3' or community.hide_community == '4':
            invited_member = Members.objects.filter(community_id=community,
                                                          member_id=ref_id)
            if invited_member.exists():
                referal(ref_id=ref_id, community_id=community_id, interested_member_id=user_id)
    if not ref_id:
        # sending mail to nipun and harsh
        new_member_request.delay(member_id=user_id, commuinity_id=community_id, ref_id=None)
    # inserting in members table if the member status is pending and inserting it to database with status=3

    # If the member is declined from the community and he applied again
    try:
        current_state=Members.objects.filter(member_id=user,community_id=community).values('state')
        if current_state[0]['state'] == 5:
            Members.objects.filter(member_id=user, community_id=community).update(state=3)

    except:
        # if not
        member = Members.objects.filter(member_id=user,community_id=community)
        if not member.exists():
            member = Members()
            member.member_id = user
            member.community_id = community
            if community.hide_community == '0' or community.hide_community == '1' or community.hide_community =='4':
                member.state = 3  # pending members
                member.save()
            elif community.hide_community == '3':
                member.state = 8
                member.save()
                update_member_count(community_id)
            update_community_tags_to_user(community_id=community_id,user_id=user.id)

    if 'questions' in res:
        info_logger.info(res['questions'])
        for i in res['questions']:
            response = Form_response()
            response.data = i['key']
            response.response = i['value']
            response.user = user.id
            response.community = community.id
            response.save()

    if community.hide_community == '0' or community.hide_community == '1' or community.hide_community =='4':

        # updating updated time of community and pending member count for admins of commnity
        Community.objects.filter(id=community_id).update(updated_at=time.time())

        # if the member is not present in engage table
        if not is_member_engage(community,user):
            engage = Member_Engage()
            engage.community_id = community
            engage.member_id = user
            engage.updated_at = time.time()
            engage.save()
            info_logger.info("""Data Inserted successfully in members engage table where user_id=%s and community_id=%s""" % (
                user_id, community_id))

        update_pending_member_count_in_engage(community)
        # sending notification to admins of the community
        name = user.userinfo.name
        send_notification_to_admins.delay(community_id,name)

    # if the community is the pilot community then filling the engage table
    if community.hide_community == '3':
        # if the user is not refered by anyone
        if not ref_id:
            # if the user data is already there in members engage
            if not is_member_engage(community,user):
                engage=Member_Engage()
                engage.community_id=community
                engage.member_id=user
                engage.updated_at=time.time()
                engage.save()
                info_logger.info("""Data Inserted successfully in members engage table where user_id=%s and community_id=%s"""%(user_id,community_id))
            else:
                info_logger.info("Data already present for user")
        else:
            #if the user refered by someone
            referer=User.objects.get(id=ref_id)
            engage = Member_Engage()
            engage.community_id = community
            engage.member_id = user
            engage.updated_at = time.time()
            engage.save()
            info_logger.info("""Data Inserted successfully in members engage table where user_id=%s and community_id=%s""" % (
                user_id, community_id))
            Member_Engage.objects.filter(community_id=community,member_id=referer).update(pending_members=F('pending_members')+1)
            info_logger.info(
                """Members engage table updated  where ref_id=%s and community_id=%s""" % (
                    user_id, community_id))

    update_referral_text_in_engage_table(community)
    log="""Request for community_id=%s is sent from member_id=%s\n"""%(community_id,user_id)
    info_logger.info(log)
    info_logger.info("\n")
    return JsonResponse({'success':True})


def category_filter(request, category):
    categories = Community_tags.objects.all()
    communities = []
    for cat in categories:
        if cat.category == category:
            c = Community.objects.get(id = cat.community_id.id)
            communities.append(c)
    community = []
    for comm_object in communities:
        serialized_object = CommunitySerializer(comm_object)
        community.append(serialized_object)
    return JsonResponse({'communities': community})


def categories(request):
    ''' function to get all categories  '''

    tags=Tags.objects.all()
    Category_list=[]
    for category in tags:
        category_dict={}
        if category.id == 4 or category.id == 8  or category.id == 13 or category.id == 22 or category.id == 25  or category.id == 28 or category.id == 39 or category.id == 40:
            category_dict['id']=str(category.id)
            category_dict['title']=category.category_name
            Category_list.append(category_dict)


    return JsonResponse ({'category_list': Category_list})


############# functions for  members of community   ##########################

def user(request, user_id):

    '''function to send user object with tags'''

    info = Userinfo.objects.all().filter(user_id = user_id)
    usr = UserinfoSerializer(info[0])

    tags=get_user_lpig_tags(user_id)
    if tags:
        usr['tags']=tags
        return JsonResponse({'user': usr})

    return JsonResponse ({'user': usr})


def members(request, community_id):
    ''' function to get all the mebers of a community including admins and nominated members '''
    community = get_object_or_404(Community, pk = community_id)
    # get members of the community
    member = Members.objects.filter(community_id = community).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7)|Q(state=8)|Q(state=9))
    members = []
    for mem in member:
        user = Userinfo.objects.filter(user_id = mem.member_id)
        if user:
            user = user[0]
            # get user json
            usr = UserinfoSerializer(user)
            usr['member_state'] = mem.state
            members.append(usr)
        else:
            continue
    return JsonResponse ({'members': members})


def admins(request, community_id):
    ''' function to get admins of a community '''
    member_id=request.GET.get('member_id',None)
    admins = Members.objects.filter(community_id = community_id).filter(Q(state=1)|Q(state=2))
    users = []
    for admin in admins:
        user = Userinfo.objects.filter(user_id = admin.member_id.id)
        # get user serialized
        usr = UserinfoSerializer(user[0])
        users.append(usr)
    community = Community.objects.get(pk = community_id)
    referred_members_count=0
    if member_id and community.hide_community == '3':
        ref_members=get_referred_members_of_a_member(community_id,member_id)
        if len(ref_members):
            referred_members_count=len(ref_members)
            return JsonResponse({'members': users,'referred_members_count':referred_members_count})
        else:
            return JsonResponse({'members': users,'referred_members_count':referred_members_count})
    elif member_id:

        print(">>>>>>>>>>> ", member_id)
        referals = get_referred_members_of_a_member(community_id=community_id, member_id=member_id)
        referal_count = len(referals)
        print(referals)
        count = 0
        print("referal count === ", referal_count)

        for mem_id in referals:
            member = Members.objects.filter(member_id=mem_id, community_id=community_id)
            if member.exists():

                if member[0].state == 4:
                    count += 1

        return JsonResponse({'members': users,'referred_members_count':count})
    else:
        return JsonResponse({'members': users})


def get_user_lpig_tags(user_id):

    '''function to get user lpig tags'''
    if not user_onbaord(user_id):
        return False
    legacy=User_Legacy.objects.filter(user_id=user_id)
    profession=User_Profession.objects.filter(user_id=user_id)
    interest=User_Interest.objects.filter(user_id=user_id)
    geography=User_Geography.objects.filter(user_id=user_id)

    legacy_list=[]
    profession_list=[]
    interest_list=[]
    geography_list=[]

    cluster_tags=[]
    for each in legacy:
        temp={}
        if each.tags_id.id !=15 and each.tags_id.is_cluster == 0:
            temp['id']=each.tags_id.id
            temp['name']=each.tags_id.name
            if each.tags_id.image_link:
                temp['image_url'] = each.tags_id.image_link
            elif each.tags_id.tag_image:
                temp['image_url'] = url+each.tags_id.tag_image.url
            attribute_id=each.tags_id.attribute_id.id

            if attribute_id is 1:
                temp['attribute_name']="Work"
            elif attribute_id is 2:
                temp['attribute_name'] = "Education"
            elif attribute_id is 3:
                temp['attribute_name'] = "Hometown"
            elif attribute_id is 4:
                temp['attribute_name'] = "Lifestyle"

            # if each.tags_id.is_cluster:
            #     cluster=list(Tags_lpig.objects.filter(cluster_tag_id=each.tags_id.id).values_list('id',flat=True))
            #     cluster_tags=cluster_tags+cluster
            legacy_list.append(temp)

    # legacy_list=get_clustered_tags_for_user(legacy_list,cluster_tags)

    cluster_tags = []
    for each in profession:
        temp={}
        if each.tags_id.id !=16 and each.tags_id.is_cluster == 0:
            temp['id']=each.tags_id.id
            temp['name']=each.tags_id.name
            if each.tags_id.tag_image:
                temp['image_url']=url+each.tags_id.tag_image.url
            attribute_id=each.tags_id.attribute_id.id
            if attribute_id is 5:
                temp['attribute_name']="Skill"
            elif attribute_id is 6:
                temp['attribute_name'] = "Industry"
            elif attribute_id is 7:
                temp['attribute_name'] = "Designation"

            # if each.tags_id.is_cluster:
            #     cluster=list(Tags_lpig.objects.filter(cluster_tag_id=each.tags_id.id).values_list('id',flat=True))
            #     cluster_tags=cluster_tags+cluster
            profession_list.append(temp)

    #profession_list=get_clustered_tags_for_user(profession_list,cluster_tags)


    cluster_tags = []
    for each in interest:
        temp = {}
        if each.tags_id.id != 17 and each.tags_id.is_cluster == 0:
            temp['id'] = each.tags_id.id
            temp['name'] = each.tags_id.name
            if each.tags_id.tag_image:
                temp['image_url']=url+each.tags_id.tag_image.url
            attribute_id=each.tags_id.attribute_id.id
            if attribute_id is 8:
                temp['attribute_name']="Cause"
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


    #interest_list = get_clustered_tags_for_user(interest_list, cluster_tags)

    cluster_tags = []
    for each in geography:
        temp = {}
        if each.tags_id.id != 18 and each.tags_id.is_cluster == 0:
            temp['id'] = each.tags_id.id
            temp['name'] = each.tags_id.name
            if each.tags_id.tag_image:
                temp['image_url']=url+each.tags_id.tag_image.url
            attribute_id=each.tags_id.attribute_id.id
            if attribute_id is 12:
                temp['attribute_name']="City"
            elif attribute_id is 13:
                temp['attribute_name'] = "State"
            elif attribute_id is 14:
                temp['attribute_name'] = "Country"

            # if each.tags_id.is_cluster:
            #     cluster=list(Tags_lpig.objects.filter(cluster_tag_id=each.tags_id.id).values_list('id',flat=True))
            #     cluster_tags=cluster_tags+cluster
            geography_list.append(temp)

    #geography_list = get_clustered_tags_for_user(geography_list, cluster_tags)

    tags={
        'legacy':legacy_list,
        'profession':profession_list,
        'interest':interest_list,
        'geography':geography_list
    }

    #print(tags)
    return tags




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
                elif dict['key'] == 'whatsapp_link' :
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
            group.updated_at=time.time()
            group.created_at=time.time()
            group.save()

            # uploading community image and thumbnail
            image_link = upload_community_files(community_id = group.id,image='https://beta.collabmates.com/media/media/community/default.jpeg',url=True)
            group.image_link = image_link
            group.save()
            upload_community_thumbnail.delay(group.id, 'https://beta.collabmates.com/media/media/community/default.jpeg')

            # create user as a admin for the community as the user is creating the community as a admin
            user = User.objects.get(id = user_id)
            community = Community.objects.get(id = group.id)

            member = Members()
            member.member_id = user
            member.community_id = community
            member.state=1                                  # admin state
            member.created_at=time.time()
            member.save()

            #creating a card while a comunity is created
            card = Collabcard()
            if community.purpose != '':
                card.title = "Created this community "+community.purpose
            else:
                card.title = "Listed our community on CollabMates. This will help us to know each other, have organised discussions and network efficiently."
            card.community = community
            card.user = user
            card.date_epoch =time.time()
            card.save()
            # saving details in firebase
            update_last_answer_id(card.id,"")

            # Community.objects.filter(id=community.id).update(purpose_collabcard = card.id)
            # community.purpose_collabcard = card.id
            # community.save()
            community_id = community.id
            card_id = card.id
            save_community_purpose_card.delay(community_id, card_id)
            print("updated card id >>>>>>>   \n",card.id,"\n")
            # created card will be auto followed by the creator if the card
            follow=follow_collabcard()
            follow.collabcard_id=card
            follow.member_id=user
            follow.save()
            #getting details of the user who is creating the community
            userinfo = Userinfo.objects.get(user_id = user.id)

            # get user serialized json
            usr = UserinfoSerializer(userinfo)
            serialized_object = CommunitySerializer(community)
            new_dict = {}
            new_dict.update(serialized_object)

            ans_text =''

            #saving the questions to be asked while joining a community
            for questions in res['questions']:
                question = Form_data()
                question.data = questions["key"]
                question.community_id = community
                question.save()

            collabcard_share_url=url+'/collabcard/'+str(card.id)

            # forming card dict

            crd = {'id':card.id , 'title':card.title, 'member':usr,'answer_text': ans_text,'share_url':collabcard_share_url}

            #inserting in member_engage table

            engage=Member_Engage()
            engage.member_id=user
            engage.community_id=community
            engage.last_unseen_conversation=card
            engage.updated_at=time.time()
            engage.member_state=1
            engage.save()

            #send_email_to_admin_of_community.delay(CommmunityAdminName=user.name,CommunityName=res['name'],email=user.email)
            return JsonResponse({'success':True, 'community':new_dict, 'collabcard':crd})
    else:
        # if community is created as a member
        member_id = request.GET.get('member_id')
        if request.method == 'POST':
            res = json.loads(request.body)

            # creating new community
            group = Community()
            group.members_count = group.members_count + 1
            group.name = res['name']
            group.updated_at=time.time()
            group.created_at=time.time()
            group.save()

            user = User.objects.get(id=member_id)

            # creating member as temporary promoter
            member = Members()
            member.member_id = user
            member.community_id = group
            member.state=2                              # temperary admin state
            member.created_at=time.time()
            member.save()
            # get community serialized json
            serialized_object = CommunitySerializer(group)
            new_dict = {}
            new_dict.update(serialized_object)

            user_id = request.GET.get('member_id')
            user = Userinfo.objects.get(user_id = user_id)
            #send_email_to_temp_admin_of_community.delay(CommmunityAdminName=user.name,CommunityName=res['name'],email=user.email)
            return JsonResponse({'success':True, 'community':new_dict})
    return HttpResponse("Create Community Api")

@shared_task
def save_community_purpose_card(community_id,card_id):
    print("\n>>>>>>>>>>>>>   card  =====  ", card_id)
    print("\n>>>>>>>>>>>>>   community  =====  ", community_id)
    time.sleep(2)
    community = Community.objects.get(id=community_id)
    community.purpose_collabcard = card_id
    community.save()


# /api/create_collabcard?community_id=300&member_id=21
@csrf_exempt
def create_card(request):
    ''' function to create a card '''

    user_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')
    # image_count = request.GET.get('image_count',0)
    # pdf_count = request.GET.get('pdf_count',0)


    # useer = User.objects.get(id = user_id)
    user = Userinfo.objects.get(user_id = user_id)
    community = Community.objects.get(id = community_id)

    if request.method == 'POST':
        res = json.loads(request.body)
        # creating card
        card = Collabcard()
        card.title = res['title']
        card.community = community
        card.user = user.user_id
        if 'share_link' in res:
            card.share_link=res['share_link']
            og_tags = decode_meta_from_url(res['share_link'])
            card.og_tags=json.dumps(og_tags)
        if 'image_count' in res:
            image_count = res['image_count']
        else:
            image_count = 0
        card.image_count = image_count

        if 'pdf_count' in res:
            pdf_count = res['pdf_count']
        else:
            pdf_count = 0
        card.pdf_count = pdf_count

        card.date_epoch=time.time()
        card.save()
        # if the community does not have a purpose card then a purpose will be created
        # the first card created for a community is the purpose card
        # if its a pilot community making the user promoter and updating community state to pilot active
        info_logger.info(community.purpose_collabcard)
        is_pilot_active=False
        if not community.purpose_collabcard and community.hide_community == '3':
            community.purpose_collabcard=card.id
            community.save()
            join_time = time.time()
            Members.objects.filter(community_id=community, member_id=user.user_id).update(state=1, created_at=join_time)
            # changing community state to 0 (zero) to make it a active community
            community.hide_community = '4'
            community.save()
            is_pilot_active=True


        # sending notification to the user
        send_notification_for_new_collabcard_posted.delay(community_id,res['title'],user_id,user.name)
        send_email_for_collabcard(community,user,card)
        Community.objects.filter(id=community_id).update(updated_at=time.time())

        collabcard = CollabcardSerializer(card, community)

        collabcard['date'] = datetime.today().strftime('%d-%m-%Y')

        # get user object's serialized json
        usr = UserinfoSerializer(user)
        collabcard['member'] = usr

        # card creator auto follows the card
        follow=follow_collabcard()
        follow.collabcard_id=card
        follow.member_id=user.user_id
        follow.save()

        update_last_answer_id(card.id,"")

        if is_member_engage(community,user.user_id):
            if is_pilot_active:
                # updating the last unseen card for community and member who become promoter
                engage=Member_Engage.objects.get(community_id=community,
                                          member_id=user.user_id)
                engage.last_unseen_conversation=card
                engage.updated_at = time.time()
                engage.save()

                #updating the members engage for members who is refered by user
                refered_members=get_referred_members_of_a_member(community_id,user_id)
                for member in refered_members:
                    user_id=User.objects.get(id=member)
                    engage=Member_Engage.objects.get(community_id=community,member_id=user_id)
                    engage.last_unseen_conversation=card
                    engage.last_unseen_count=1
                    engage.updated_at = time.time()
                    engage.save()
                update_pending_member_count_in_engage(community)
            else:
                update_last_unseen_in_engage(user=user.user_id,community=community)
        else:
            engage = Member_Engage()
            engage.member_id = user.user_id
            engage.community_id = community
            engage.last_unseen_conversation = card
            engage.updated_at = time.time()
            engage.save()
        update_referral_text_in_engage_table(community)
        custom_cache.clear()
        return JsonResponse({'success':True,'collabcard':collabcard})
    return JsonResponse({'success':False})


@csrf_exempt
def create_admin(request,community_id):
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
            nominated_member_id=res['nominate_member_id']
            try:
                user_data=Userinfo.objects.get(user_id=nominated_member_id)
                res['name']=user_data.name
                res['email_id']=user_data.email
            except:
                print("Error in object")
        if 'name' in res:
            admin.name = res['name']
        if 'email_id' in res:
            try:
                if res['email_id'] == promoter_email:
                    return JsonResponse({'success':True})
            except:
                pass
            admin.email = res['email_id']
        if 'contact_no' in res:
            admin.contact_number = res['contact_no']
        if 'member_id' in res:
            member_id = res['member_id']
        community = Community.objects.get(id = community_id)
        admin.community = community
        admin.member_id = member_id
        admin.save()
        # checking if there is any person with given mail , and make him nominated promoter
        check = check_member(res['email_id'],community_id,res['member_id'],res)
        return JsonResponse({'success':True})
    return HttpResponse('Add Admin Api')


def check_member(email,community_id,member_id,res):
    """ check if the user is already a member of the invited community and make user as nominated promoter
     if he is registered in collabmates and if the user is not registered just send the user a invitation email """
    ProposedAdmin = Userinfo.objects.get(user_id = member_id)
    community = Community.objects.get(id = community_id)
    proposedAdminState = Members.objects.filter(member_id=ProposedAdmin.user_id,community_id = community)
    proposedAdminState = proposedAdminState[0].state
    CommunityName=community.name
    email=email.lower().strip()
    ProposedAdmin=ProposedAdmin.name

    try:
        user = Userinfo.objects.filter(email=email)

        if user:
            """ if the user is present get user details """
            NominatedAdmin_id = user[0].user_id.id
            NominatedAdmin=user[0].name
        else:
            """ if the user is not present just user a email"""
            send_email_to_nominated_admin.delay(NominatedAdmin=res['name'],email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            return False
    except:
        """ if any error trying fetch the user details , then user is not registered , send an email"""
        send_email_to_nominated_admin.delay(NominatedAdmin=res['name'],email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
        return False

    if user:
        # get the state of the user of the community he is proposed to become a promoter for
        member =Members.objects.filter(community_id = community,member_id = user[0].user_id.id)

        if member and member[0].state == 4:
            # if the user is already a member , give him state 7
            # state 7 is nominted promoter who is already a member of thet community
            Members.objects.filter(community_id = community,member_id = user[0].user_id.id).update(state=7)
            # send mail and notification
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )

        elif member and (member[0].state == 6 or member[0].state == 7):
            # if he is nominated again just send hime a remainding mail and notification
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )

        elif member and (member[0].state == 1 or member[0].state == 2):
            return True

        elif member and (member[0].state == 3 or member[0].state == 5):
            Members.objects.filter(community_id = community,member_id = user[0].user_id.id).update(state=6)
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
                                                proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                                community_id=community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id=NominatedAdmin_id, community_id=community.id,
                                                      proposed_admin_name=ProposedAdmin)

        else:
            # if user is not anything to the community and he is nominated as promoter
            # create a member instance , making the user a nominated promoter giving user state = 6
            # state 6 is nominated member who was never involved in that community
            member =Members()
            member.community_id = community
            member.member_id = user[0].user_id
            member.state = 6
            member.save()
            # send mail and notification
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )
        return True
    return False


def pending_members(request,community_id):
    ''' function to get members requested to join in a community '''
    community = Community.objects.get(id = community_id)
    pend_requests=Members.objects.filter(community_id=community).filter(state = 3)
    pending_requests = []
    for i in pend_requests:
        print(i.member_id.id,"  ==  ",type(i))
        resp = Form_response.objects.filter(community = community_id).filter(user = i.member_id.id)
        user = Userinfo.objects.get(user_id = i.member_id.id)
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

def check_for_member_eligibiity(community_id,member_id):

    '''That return count return you the no of people user referred and has become state 4'''
    # function to check if accepted member is a eligible admin or not

    community = Community.objects.get(pk = community_id)

    update = True
    print(">>>>>>>>>>> ",member_id)
    referals = get_referred_members_of_a_member(community_id=community_id, member_id=member_id)
    referal_count = len(referals)
    print(referals)
    return_count = 0
    print("referal count === ",referal_count)
    if referal_count >= eligibility_count:
        # return_count = 0
        for mem_id in referals:
            member = Members.objects.filter(member_id=mem_id,community_id=community_id)
            if member.exists():

                if member[0].state == 4:
                    return_count+=1

        if return_count >= eligibility_count:
            member = Members.objects.filter(member_id=member_id, community_id=community)
            if member[0].state != 1:
                Members.objects.filter(member_id=member_id, community_id=community).update(state=9)
                community_id=community.id
                community_name = community.name
                ref_id=member_id

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
                member = Members.objects.filter(member_id=mem_id,community_id=community_id)
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

def pending_request_count(request,community_id):
    ''' fucntion to get peding members count of a community '''

    no_of_pending_members = Members.objects.filter(community_id = community_id).filter(state = 3).count()
    return JsonResponse({'pending_request_count': no_of_pending_members})


@csrf_exempt
def accept_invitation(request):
    ''' accept promoter request '''
    # getting details of nominated person and the community promoter who proposed this invitation
    member_id=request.GET.get('member_id')
    community_id=request.GET.get('community_id')
    community = Community.objects.get(id=community_id)
    promoter = Members.objects.filter(community_id = community).filter(Q(state=1)|Q(state=2))
    nom_admin = Userinfo.objects.filter(user_id = member_id)
    # ------------------------------------------------------------------------------
    # if only one promoter to a community

    accepted = request.GET.get('value','true')

    if accepted == 'true':
        #saving data for a new member who is nominated and has accept the invitation
        member_state=Members.objects.filter(community_id=community, member_id=member_id).values('state')
        pending_members=Members.objects.filter(community_id=community,state=3).count()
        if member_state:
            state=member_state[0]['state']
            if state == 6:
                if is_member_engage(community,nom_admin[0].user_id) ==  False:
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
                    engage.pending_members=pending_members
                    engage.save()
                    Members.objects.filter(community_id=community, member_id=member_id).update(created_at=time.time())


        if len(promoter) == 1:
            #if the community has only one promoter
            prop_admin = Userinfo.objects.get(user_id=promoter[0].member_id.id)
            # if the promoter is actually a promoter
            if promoter[0].state == 1:
                Members.objects.filter(community_id=community, member_id=member_id).update(state=1)
                Member_Engage.objects.filter(community_id=community, member_id=member_id).update(member_state=1)
                # updating member count of the community
                update_member_count(community.id)
                #sending email to promoter , that user has accepted his request to beacome a promoter
                send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState =1,CommunityName=community.name,community_id = community.id)
                proposer_id = prop_admin.user_id.id
                nom_admin_name = nom_admin[0].name
                send_notification_to_proposer.delay(proposer_id,community_name =community.name,community_id=community.id,proposed_name = nom_admin_name)
                return JsonResponse({'success':True})
            # if the promoter is a temporary promoter
            elif promoter[0].state == 2:
                temp_promoter = Members.objects.filter(community_id = community,state=2)
                Members.objects.filter(community_id = community,member_id=temp_promoter[0].member_id).update(state =4)
                Member_Engage.objects.filter(community_id=community, member_id=temp_promoter[0].member_id).update(member_state=4)

                Members.objects.filter(community_id = community,member_id=member_id).update(state =1)
                Member_Engage.objects.filter(community_id=community, member_id=member_id).update(member_state=1)
                # updating member count of the community
                update_member_count(community.id)
                #sending email to promoter , that user has accepted his request to beacome a promoter
                send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState=2,CommunityName=community.name,community_id = community.id)
                proposer_id = prop_admin.user_id.id
                nom_admin_name = nom_admin[0].name
                send_notification_to_proposer.delay(proposer_id, community_name =community.name,community_id=community.id,proposed_name = nom_admin_name)
                return JsonResponse({'success':True})
        else:
            # if there are more than two admins , sent mail to the promoter who invited this member
            # getting the promoter ID from temp admin model
            promoter_who_proposed = temp_admin.objects.filter(community_id=community,email=nom_admin[0].email)
            # getting the promoter details
            prop_admin = Userinfo.objects.get(user_id=promoter_who_proposed[0].member_id)
            # make th current member a promoter of this community
            Members.objects.filter(community_id=community, member_id=member_id).update(state=1)
            Member_Engage.objects.filter(community_id=community, member_id=member_id).update(
                member_state=1)

            # updating member count of the community
            update_member_count(community.id)
            #sending email to promoter , that user has accepted his request to become a promoter
            send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState=1,CommunityName=community.name,community_id = community.id)
            proposer_id=prop_admin.user_id.id
            nom_admin_name=nom_admin[0].name
            send_notification_to_proposer.delay(proposer_id, community_name =community.name,community_id=community.id,proposed_name = nom_admin_name)
            return JsonResponse({'success':True})
    else:
        # if nominated promoter didn't accept the invitation
        member = Members.objects.filter(community_id=community, member_id=member_id)
        if member[0].state == 6:
            print("member state == 6")
            # deleting his details from temp admin model
            usr = Userinfo.objects.get(user_id = member[0].member_id)
            temp = temp_admin.objects.filter(community_id=community,email= usr.email)
            temp.delete()
            # if he is previously not a member of this community
            # then delete the member from members model
            Members.objects.filter(community_id=community, member_id=member_id).delete()
            Member_Engage.objects.filter(community_id=community, member_id=member_id).delete()

        elif member[0].state == 7:
            print("member state == 7")
            # if he is previously not a member of this community , then make him member again
            Members.objects.filter(community_id=community, member_id=member_id).update(state=4)
            Member_Engage.objects.filter(community_id=community, member_id=member_id).update(state=4)

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


@csrf_exempt
def request_response(request,req_dict=None):
    ''' function to approve or decline a members who requested to join '''
    if not req_dict:
        res = json.loads(request.body)
    else:
        res=req_dict
    if 'member_id' in res:
        member_id = res['member_id']
    if 'community_id' in res:
        community_id = res['community_id']
    if 'accepted' in res:
        accepted = res['accepted']
    community = Community.objects.get(id = community_id)
    user = User.objects.get(id= member_id)
    if accepted == True :
        # if accepted , then make him a member of the community
        #updating the approve state
        join_time=time.time()
        Members.objects.filter(member_id=member_id,community_id=community).update(state=4,created_at=join_time)  # aprove state = 4
        community = Community.objects.get(id = community_id)
        members_count = community.members_count+1
        Community.objects.filter(id = community_id).update(members_count=members_count)

        # inserting data in member engage
        purpose_card = Collabcard.objects.get(id=community.purpose_collabcard)

        unseen_count=Collabcard.objects.filter(community=community).count()
        count = check_for_member_eligibiity(community_id, member_id)
        if not is_member_engage(community, user.id):
            engage = Member_Engage()
            engage.member_id = user
            engage.community_id = community
            engage.last_unseen_conversation = purpose_card
            engage.last_unseen_count=unseen_count
            engage.updated_at = time.time()
            engage.save()
            update_pending_member_count_in_engage(community)
            update_referral_text_in_engage_table(community)
        else:
            # if the community is created by user than updating the user details
            if community.hide_community == '0' or community.hide_community == '1':
                engage=Member_Engage.objects.get(community_id=community,member_id=user)
                engage.last_unseen_conversation = purpose_card
                engage.last_unseen_count = unseen_count
                engage.updated_at = time.time()
                engage.save()
                update_pending_member_count_in_engage(community)
                update_referral_text_in_engage_table(community)

        # send notification
        send_notification_for_join_requests.delay(community_id,True,member_id)

        if not req_dict:
            notify_referred_member_after_join(joined_member_id=member_id,
                                              joined_member_name=user.userinfo.name,
                                              community_name=community.name, community_id=community_id)

    else:
        # if rejected , change user state to 5
        Members.objects.filter(member_id=member_id,community_id=community).update(state=5)  # decline state = 5
        Member_Engage.objects.filter(member_id=member_id, community_id=community).delete()
        # and also send notification
        send_notification_for_join_requests.delay(community_id, False, member_id)
        Form_response.objects.filter(user=member_id,community=community_id).delete()


    return JsonResponse({'success': True})



############# functions for  collabcard flow   ##########################


def send_email_for_collabcard(community,user,card):

    '''function to make the format of email to send when a new collabcard is posted'''


    members=Members.objects.filter(community_id=community)
    college_tag=Community_tags.objects.filter(community_id=community).filter(Q(tags_id=41)|Q(tags_id=42))
    form_link=url
    for tag in college_tag:
        if tag.tags_id == 41:
            form_link='https://docs.google.com/forms/d/e/1FAIpQLSes87js8cTiGg0x-Vw9DYrnY1BCZTolba0B1WBvcVSYZSGAwg/viewform'
        elif tag.tags_id == 42:
            form_link='https://docs.google.com/forms/d/e/1FAIpQLSfqN2z1wg6CCJ4ZKH1lxQQgJ8iUWEbtTT0R9NT64zg5f13_ig/viewform'

    for member in members:
        if not user.image_link:
            collabcard_card_image=url+user.image_file.url
        else:
            collabcard_card_image=user.image_link
        context = {
            'community_name': community.name,
            'collabcard_creater': user.name,
            'collabcard_creater_image':collabcard_card_image,
            'creater_header': user.headline,
            'url':  url + '/collabcard/' + str(card.id),
            'form_link':form_link
        }

        if member.member_id.id == user.user_id.id:
            continue
        if member.state == 1 or member.state == 2 or member.state == 4:
            userinfo=Userinfo.objects.get(user_id=member.member_id)
            if not userinfo.image_link:
                reciever_image=url+userinfo.image_file.url
            else:
                reciever_image=userinfo.image_link
            context['reciever']=userinfo.name
            context['reciever_image']=reciever_image
            context['to']=userinfo.email
            #print(context)
            send_email_for_new_collabcard_posted.delay(context)



def collabcard(request, card_id):
    ''' function to get card details, answers and images '''
    # get the card object

    cards = Collabcard.objects.get(id = card_id)
    page=request.GET.get('page',1)


    # coverting current time into epoch time for getting time stamp of answers and card

    # get all the answers of the card
    answer = card_answers.objects.filter(card = cards)
    answer=pagination(answer,page,paginate_by=10)

    answer_id=request.GET.get('answer_id','')
    user_id = request.GET.get('member_id', '')

    if answer_id:
        answer_id=int(answer_id)

        answer=card_answers.objects.filter(card=cards,id__gte=answer_id).filter(~Q(user__id = user_id))
        answer = pagination(answer, page, paginate_by=10)
        answers=get_answer_data(answer)
        return JsonResponse({'answers': answers})
    else:
        answers=get_answer_data(answer)

    user = Userinfo.objects.get(user_id = cards.user.id)
    # serializing user object
    usr = UserinfoSerializer(user)
    # get the card image if any

    files= get_collabcard_files(card_id)
    card=CollabcardSerializer(cards,cards.community)
    card['images']=files[0]
    card['member']=usr
    card['pdf']=files[1]
    if user_id:
        card['state']= get_status_of_collabcard(member_id = user_id,community = cards.community,card = cards )
    # get tine stamp for card
    time_text = get_time_text(cards.date_epoch)
    card['created_at'] = time_text
    return JsonResponse({"collabcard": card, 'answers':answers})
  

def get_answer_data(answer):

    '''function to get answer for a particular collabcard from database database'''
    answers = []
    for ans in answer:
        user = Userinfo.objects.filter(user_id=ans.user.id)
        usr = UserinfoSerializer(user[0])
        # coverting current time into epoch time

        if str(ans.date_epoch) == "-9223372036854775808":
            time_text = ""
        else:
            time_text = get_time_text(ans.date_epoch)

        attachements = get_answer_files(ans.id)

        answers.append({'id': ans.id, 'answer': ans.answer, 'created_at': time_text, 'member': usr,
                        'images':attachements[0], 'pdf':attachements[1]})
    return answers


def get_collabcard_files(card_id):

    '''function to return pdf and image files of a collabcard'''

    files = Card_Attachment.objects.filter(collabcard=card_id)
    img_list=[]
    pdf=[]
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
    return (img_list,pdf)


def get_answer_files(answer_id):

    '''function to return pdf and image files of a collabcard'''

    files = Answer_Attachment.objects.filter(answer=answer_id)
    img_list=[]
    pdf=[]
    for file in files:
        if file.type == 'image':
            if file.file_url:
                img = {'image_url': file.file_url}
                img_list.append(img)
        elif file.type == 'pdf':
            if file.file_url:
                pdf_url = {'pdf_file': file.file_url}
                pdf.append(pdf_url)
    return (img_list,pdf)


def get_time_text(created_time):
    """ function to get time stamp """

    # get current time and convert it into epoch time
    present_time = str(datetime.now())
    current_time = datetime.strptime(present_time.strip(' \t\r\n'), "%Y-%m-%d %H:%M:%S.%f").strftime('%s')
    created = datetime.fromtimestamp(created_time)
    current = datetime.fromtimestamp(int(current_time))
    difference = dateutil.relativedelta.relativedelta (current, created)
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
            return str(difference.days)+" day ago"

        elif difference.days < 7 :
            return str(difference.days)+" days ago"

        elif difference.days == 7:
            return "1 week ago"
        # if difference is more than one week return created date
        return time.strftime('%d/%m/%Y', time.localtime(created_time))

    elif difference.hours:
        # if difference is in hours
        if difference.hours == 1:
            return str(difference.hours)+" hour ago"

        return str(difference.hours)+" hours ago"
    elif difference.minutes:
        # if difference is in hours
        if difference.minutes ==1:
            return str(difference.minutes)+" min ago"

        return str(difference.minutes)+" mins ago"
    else:
        # if difference is in seconds
        return "Just Now"


def community_cards(request, community_id):
    ''' function get all the cards in a community '''

    community = Community.objects.get(id = community_id)
    member_id=request.GET.get('member_id')


    #is_tour=request.GET.get('is_tour',False)

    # if the community is pilot community and android tour is given
    if community.hide_community == '3':
        card_list=get_cards_for_demo(community_id,member_id)
        return JsonResponse({'collabcards': card_list})

    size=request.GET.get('size','')
    if size:
        size=int(size)
        cards = Collabcard.objects.filter(community = community_id).order_by('id')[:size]
    else:
        cards = Collabcard.objects.filter(community = community_id).order_by('id')

    collabcard_url=request.build_absolute_uri()
    if collabcard_url in custom_cache:
        card_list=custom_cache.get(collabcard_url)
    else:
        card_list = []
        for card in cards:
            user = Userinfo.objects.get(user_id = card.user)
            # serialize user object
            usr = UserinfoSerializer(user)
            # get card images --------------------------------------------------------
            files=get_collabcard_files(card)
            # -----------------------------------------------------------------------
            share_url = url+'/collabcard/'+str(card.id)

            # get time stamp
            if str(card.date_epoch) == "-9223372036854775808":
                # if there is no time stamp , return nothing
                time_text=""
            else:
                # get time stamp
                time_text = get_time_text(card.date_epoch)
            card_dict = CollabcardSerializer(card, card.community)
            card_dict['state'] = get_status_of_collabcard(member_id,community,card)
            card_dict['created_at'] = time_text
            card_dict['member'] = usr
            card_dict['images'] = files[0]
            card_dict['pdf'] = files[1]
            card_list.append(card_dict)
        custom_cache.set(collabcard_url,card_list,timeout=CACHE_TTL)
    return JsonResponse ({'collabcards': card_list})


def get_cards_for_demo(community_id,member_id):

    '''function to get demo cards for pilot community'''
    card_list = []
    userinfo_objects = Userinfo.objects.get(user_id=member_id)
    community=Community.objects.get(id=community_id)
    name = userinfo_objects.name
    first_name = name.split(' ', 1)[0]
    community_purpose = community.purpose
    if community_purpose:
        community_purpose = community_purpose[0].lower() + community_purpose[1:]
    # sample card
    sample_card = {}
    sample_card['id']="first_conversation"
    sample_card['title'] = """Welcome %s, I'll be initiating this community %s""" % (first_name, community_purpose)
    sample_card['community_id'] = community_id
    sample_card['member'] = {
        'name': "Initial Promoter"
    }
    sample_card['created_at'] = get_time_text(time.time())
    sample_card['answer_text']="Second Promoter & 3 others responded"
    answers=[]

    temp={}

    test=str(community.about)
    x = test.find("Anytime")
    display_string = ""
    for index in range(x, len(test)):
        display_string = display_string + test[index]
        if test[index] == '.':
            break
    temp['id']="first_conversation_1"
    temp['answer']=display_string
    temp['created_at']=get_time_text(time.time())
    temp['member']={
        'name':"Second Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id']="first_conversation_2"
    temp['answer'] = """Interested members can respond by simply chatting with you and each other on your conversation card."""
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Third Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id']="first_conversation_3"
    temp['answer'] = """Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card."""
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Fourth Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id']="first_conversation_4"
    temp['answer'] = """Others would simply swipe through the conversation card and move to the next conversation"""
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Initial Promoter"
    }
    answers.append(temp)
    sample_card['answers']=answers

    card_list.append(sample_card)

    # purpose info card
###################### sample card end ################
    purpose_card = {}
    purpose_card['id']="second_conversation"
    purpose_card['title'] = """%s, this community is currently a pilot as it doesn't actually have any of us (promoters). Help this community find us and enable interactions between members""" % (
        first_name)
    purpose_card['community_id'] = community_id
    purpose_card['member'] = {
        'name': "Initial Promoter"
    }
    purpose_card['created_at'] = "Just Now"
    purpose_card['answer_text'] = "Second Promoter & 3 others responded"
    answers = []

    temp = {}
    temp['id']="second_conversation_1"
    temp['answer'] = """Promoters are responsible to approve new member requests in the community and drive conversations between members."""
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Second Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id'] = "second_conversation_2"
    temp['answer'] = """Anyone can become a promoter and initiate this community by referring %s new members to the community."""%(eligibility_count)
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Third Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id'] = "second_conversation_3"
    temp['answer'] = """%s, please refer someone who you consider fit to become a promoter"""%(str(first_name))
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Fourth Promoter"
    }
    answers.append(temp)

    temp = {}
    temp['id'] = "second_conversation_4"
    refered_members=get_referred_members_of_a_member(community_id,member_id)
    diff=(eligibility_count-len(refered_members))
    temp['answer'] = """Alternatively, you can refer %s more members and become promoter of this community."""%(str(diff))
    temp['created_at'] = get_time_text(time.time())
    temp['member'] = {
        'name': "Initial Promoter"
    }
    answers.append(temp)
    purpose_card['answers']=answers
    card_list.append(purpose_card)

    # referal card

    referal_card = {}
    referal_card['member'] = {
        'id':member_id,
        'name': name
    }
    referal_card['id']="third_conversation"
    referal_card['title'] = """Just discovered this community which is %s""" % (community_purpose)
    referal_card['created_at'] = "Just Now"
    referal_card['share_url']=url+"/community/"+str(community_id)+"?ref_id="+str(member_id)
    card_list.append(referal_card)
    referal_card['answers']=[]
    return card_list

def get_status_of_collabcard(member_id,community,card):
    '''function to get the state of collabcard'''
    state=0
    member_id=User.objects.get(id=member_id)

    seen_status=collabcard_seen.objects.filter(card=card,community=community,user=member_id)
    if seen_status:
        state=1
        follow=follow_collabcard.objects.filter(collabcard_id=card,member_id=member_id)
        if follow:
            state=2

    return state


@csrf_exempt
def create_answer(request):
    '''function to post answer on collabcard'''
    body = request.GET
    if 'member_id' in body:
        user_id = body['member_id']
    user = User.objects.get(id = user_id)
    if'collabcard_id' in body:
        card_id = body['collabcard_id']
    card = Collabcard.objects.get(id = card_id)

    if request.method == 'POST':
        res = json.loads(request.body)
        ans = card_answers()
        ans.answer =  res['title']
        ans.card = card
        ans.user = user
        ans.date_epoch=time.time()
        ans.save()
        update_last_answer_id(card_id,ans.id)


        #auto following the collabcard if answer is created
        is_present=is_collabcard_already_followed(card,user)
        if  is_present == False:
            follow = follow_collabcard()
            follow.collabcard_id = card
            follow.member_id = user
            follow.save()

        send_follow_notification.delay(card_id=card_id,user_id=user_id,answer=res['title'])

        #calling update_answer_text 
        update_answer_text(card_id)

        return JsonResponse({'success':True})


def update_answer_text(card_id):
        '''function for updating the answer_text feild in collab card model'''
        ans_text=''
        card = Collabcard.objects.get(id = card_id)
        card_ans = card_answers.objects.filter(card = card)
        # if only one answer is present fro a collab card
        if len(card_ans) == 1:
            # get the name of the user who answered
            username = Userinfo.objects.get(user_id = card_ans[0].user_id)
            #format the answer text string as "username answered"
            ans_text = username.name + " responded"
            # update the answer_text feild in collabcard
            Collabcard.objects.filter(id=card_id).update(answer_text=ans_text) 
        # if there is more than one answer
        else:
            #get the user id's of the users who have answered
            user_list =[]
            for ans in card_ans:
                # save it in a list without duplicates
                if ans.user_id not in user_list:
                    user_list.append(ans.user_id)
            count = 1
            #check if only two different users have answered
            #not more than two different users should have answered
            if len(user_list)==2:
                for ID in user_list:
                    username = Userinfo.objects.get(user_id = ID)
                    ans_text += username.name
                    if count !=0:
                        ans_text += " and "
                        count-=1
                ans_text+=" responded"
                Collabcard.objects.filter(id=card_id).update(answer_text=ans_text)

            # if more than two different users have answered
            if len(user_list) >= 3:
                for ID in user_list:
                    username = Userinfo.objects.get(user_id = ID)
                    ans_text += username.name
                    break

                ans_text+= " & "+str(len(user_list)-1) + " others responded"
                Collabcard.objects.filter(id=card_id).update(answer_text=ans_text)

@csrf_exempt
def collabcard_follow(request):
    '''Api to follow collabcard by members Post API'''
    collabcard_id=request.GET.get('collabcard_id','')
    member_id=request.GET.get('member_id','')
    status=request.GET.get('value','true')

    if status != 'true':
        status=False



    collabcard=Collabcard.objects.get(id=collabcard_id)
    member_id=User.objects.get(id=member_id)
    is_present = is_collabcard_already_followed(collabcard, member_id)

    if is_present == False:
        follow=follow_collabcard()
        follow.collabcard_id=collabcard
        follow.member_id=member_id
        follow.save()
    else:
        '''Deleting the collabcard '''
        if status == False:
            follow_collabcard.objects.filter(collabcard_id=collabcard,member_id=member_id).delete()
    custom_cache.clear()
    return JsonResponse({'success':True})


def is_collabcard_already_followed(collabcard,member_id):

    '''function to check whether the person already followed the collabcard or not'''

    is_present=False
    follow_data=follow_collabcard.objects.filter(collabcard_id=collabcard,member_id=member_id)

    if follow_data:
        is_present=True

    return is_present


@csrf_exempt
def collabcards_seen(request):
    '''This functions stores the details of members who have seen the card'''
    params = request.GET
    if 'community_id' in params:
        community_id = params['community_id']
    if 'collabcard_id' in params:
        card_id = params['collabcard_id']
    if 'member_id' in params:
        user_id = params['member_id']

    community = Community.objects.get(id = community_id)
    user = User.objects.get(id = user_id)
    card = Collabcard.objects.get(id = card_id)

    seen_card = collabcard_seen.objects.filter(community = community,user=user,card=card)
    if not seen_card:
        # if the card has not yet been seen by the user, update the database
       collab_seen=collabcard_seen()
       collab_seen.card=card
       collab_seen.user=user
       collab_seen.community=community
       collab_seen.save()
    update_last_unseen_in_engage(user=user,community=community,is_seen=True)
    custom_cache.clear()
    return JsonResponse({'success': True})



def decode_url(request):
    '''function to send og tags of the link'''

    url=request.GET.get('url')

    og_tags=decode_meta_from_url(url)

    return JsonResponse({'og_tags':og_tags})

def member_activity(request):

    '''function to check whether the member created the collabcard or not'''

    state=0
    community_id=request.GET.get('community_id')
    user_id=request.GET.get('member_id')

    community=Community.objects.get(pk=community_id)
    member=User.objects.get(pk=user_id)

    status=Collabcard.objects.filter(community=community,user=member)

    if status:
        state=1
    # if state == 1:
    #state=community.introduction_text_state
    if state:
        return JsonResponse({'state':state,'tutorial_count':tutorial_count})

    if state == 0:

       form_response=Form_response.objects.filter(user=member.id,community=community.id).order_by('id')
       if form_response.exists():
        introduction_question=form_response[0].data
        introduction_answer=form_response[0].response
        return JsonResponse({'state':state,'introduction_question':introduction_question,'introduction_answer':introduction_answer,'tutorial_count':tutorial_count})
    return JsonResponse({'state': state})


############# upload files flow   ##########################

@csrf_exempt
def image_upload(request):
    ''' function to upload community images '''
    body = request.GET
    if request.method =='POST':
        # if 'member_id' in body:
        #     user_id = body['member_id']
        #     user = User.objects.get(id = user_id)
        new_image = request.FILES['file']
        if 'community_id' in body:
             # if image to be updated in community
            community_id = body['community_id']
            community = Community.objects.get(id = community_id)
            old_image_file = community.image_url

            # # deleting the old file after new file is updated
            # # get the new image file
            version =  re.findall(r'\w*__image__(\d+)',old_image_file.name)
            if version:
                version = int(version[0])+1
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
            collabcard = Collabcard.objects.get(id = collabcard_id)

            card_image = Card_Attachment.objects.filter(collabcard = collabcard).order_by('-id')
            if card_image:
                old_image_file=card_image[0].attachment
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
                card_image.type='Image'
                card_image.save()
        return JsonResponse({'success':True})


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
            community.image_link=body['url']
            upload_community_thumbnail.delay(community_id,body['url'])
            community.save()
        elif 'collabcard_id' in body:
            attachment_type = body['type']
            collabcard_id = body['collabcard_id']
            collabcard = Collabcard.objects.get(id=collabcard_id)

            file = Card_Attachment()
            file.collabcard = collabcard
            file.type = attachment_type
            file.file_url=body['url']
            file.save()

        elif 'answer_id' in body:
            attachment_type = body['type']
            answer_id = body['answer_id']
            answer_obj = card_answers.objects.get(id=answer_id)

            file = Answer_Attachment()
            file.answer = answer_obj
            file.type = attachment_type
            file.file_url=body['url']
            file.save()

        return JsonResponse({'success': True})
    return JsonResponse({'success': False})



############# functions for  login flow   ##########################


@csrf_exempt
def login(request):
    ''' function to login a user '''

    if request.method == 'POST':
        res = json.loads(request.body)
        dic_form=res
        json_to_save=json.dumps(dic_form)
        login_type=request.GET.get('type')
        # if user is logging in from facebook
        if login_type == 'facebook':
            email=res['email']
            # converting email to lower case and removing unwanted space
            email=email.lower().strip()
            user =User.objects.filter(email=email)

            if not user:
                # creating a user if no user is associated with that email
                usr = User()
                usr.username = res['name']
                usr.email = res['email']
                usr.save()
                # if there is no user then user will not have userinfo too
                # creating user info
                userinfo = Userinfo()
                userinfo.user_id = usr
                userinfo.email = res['email']
                userinfo.name = res['name']
                userinfo.image_link = upload_image_to_firebase(res['picture']['data']['url'],usr.id)
                if 'link' in res:
                    userinfo.fb_link = res['link']
                if 'location' in res:
                    userinfo.city = res['location']['name']
                userinfo.login_type='facebook'
                userinfo.login_json=json_to_save
                userinfo.created_at = time.time()
                userinfo.save()
                mail_triger(str(usr.id)) # both mail and notification will be sent here
        else:
            # if user is logging in with linkedIn
            user_name=res['firstName']['localized']['en_US'] + " " + res['lastName']['localized']['en_US']
            profile_picture=res['profilePicture']['displayImage~']['elements'][2]['identifiers'][0]['identifier']
            email=res['email']['elements'][0]['handle~']['emailAddress']
            userinfo = Userinfo.objects.filter(email=email)
            # create user and userinfo if there is no user with this email
            if not userinfo:
                userinfo=Userinfo()
                usr=User()
                usr.username=user_name
                usr.email = email
                usr.save()
                userinfo.user_id=usr
                userinfo.email=email
                userinfo.name=user_name
                userinfo.image_link=upload_image_to_firebase(profile_picture,usr.id)
                userinfo.login_type='linkedIn'
                userinfo.login_json=json_to_save
                userinfo.created_at = time.time()
                userinfo.save()
                mail_triger(str(usr.id)) # both mail and notification will be sent here

        userinfo=Userinfo.objects.filter(email=email)
        # get serialized user object
        usr = UserinfoSerializer(userinfo[0])
        has_tags=user_onbaord(usr['id'])
        tags = get_user_lpig_tags(usr['id'])

        if tags:
            usr['tags']=tags
            return JsonResponse({'user': usr, 'has_tags': has_tags})
        return JsonResponse ({'user': usr,'has_tags':has_tags})

    return HttpResponse('Login Api')


def notify_referred_member_after_join(joined_member_id,joined_member_name,community_name,community_id):

    community = get_object_or_404(Community, pk=community_id)
    refer = Referal.objects.filter(invited_member=joined_member_id,
                                   community=community)
    if refer.exists():

        referred_member_id = refer[0].member.id


        notify_referred_member.delay(referred_member_id=referred_member_id,
                                 joined_member_name=joined_member_name,
                                 community_name=community_name,
                                 community_id=community_id)

def members_state(request):
    '''This function gives the state of user.Get Api'''

    member_id=request.GET.get('member_id')
    community_id=request.GET.get('community_id')
    collabcard_id = request.GET.get('collabcard_id')
    # if not collabcard_id.isdigit():
    #     return JsonResponse({'state':0})
    if collabcard_id and not community_id:
        card = Collabcard.objects.get(pk = collabcard_id)
        community_id = card.community.id
    state=0
    query_set=Members.objects.filter(member_id=member_id,community_id=community_id)
    for data in query_set:
        if data.state != None:
            state=data.state
    if state == 0:
        '''checking if user DETAILS EXIST in temp admin table in case he is a newly registered user'''
        user = Userinfo.objects.get(user_id = member_id)
        community = get_object_or_404(Community, pk=community_id)
        check = get_nominated_admin_details(community_id=community_id,email=user.email)
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

    return JsonResponse({'state':state})


@csrf_exempt
def push(request):
    '''This function is used to insert fcm token to the database in order to generate notifications from database'''

    member_id=request.GET.get('member_id','')
    token=request.GET.get('token','')
    print('member_id ===>>> ',member_id)
    if member_id:
        is_member=Userinfo.objects.filter(user_id=member_id)
    else:
        is_member=None
    success=False
    if is_member:
        success=True
        if not is_member[0].fcm_token:
            send_welcome_mail.delay(member_id)
        fcm_token=Userinfo.objects.filter(user_id=member_id).update(fcm_token=token)

    return JsonResponse({'success':success})


def config(request):

    '''function to update the version number of android for a user profile'''
    headers=request.META
    if 'HTTP_X_MEMBER_ID' in headers and 'HTTP_X_VERSION_CODE' in headers:
        member_id=headers['HTTP_X_MEMBER_ID']
        version_code=headers['HTTP_X_VERSION_CODE']

        Userinfo.objects.filter(user_id=member_id).update(version_code=version_code)
        log="""Version code updated for user %s"""%(str(member_id))
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
        #return JsonResponse({'success': True,'route':route})

        version_no=App_Update_Info.objects.filter(version_code=version_code)
        version_update=False
        if version_no:
            route=version_no[0].android_route
            version_update=True



    ingest_your_communities=request.GET.get('ingest_your_communities',False)
    info_logger.info(ingest_your_communities)
    if ingest_your_communities:
        update_communities_in_member_engage_table.delay(member_id)
        log="""Updated successfull for user=%s"""%(member_id)
        info_logger.info(log)
        if version_update:
            return JsonResponse({'success':True})                   #route:route
        else:
            return JsonResponse({'success': True})
    #error_logger.error("headers are not comming correctly")

    if version_update:
        return JsonResponse({'success': True})                      #route:route
    else:
        return JsonResponse({'success': True})

@shared_task
def update_communities_in_member_engage_table(member_id):

    '''function to update the user communities in engage table'''

    all_members=Members.objects.filter(member_id=member_id)
    c=0
    for member in all_members:
        community_id=member.community_id
        if community_id.hide_community == '3':
            community =Community.objects.get(id=community_id.id)
            user=User.objects.get(id=member_id)
            if not is_member_engage(community,user):
                engage=Member_Engage()
                engage.community_id=community
                engage.member_id=user
                engage.updated_at=time.time()
                pending_count= get_referred_members_of_a_member(community.id,member_id)
                engage.pending_members=len(pending_count)
                engage.save()
                info_logger.info("Communities")
                info_logger.info(community)
                c=c+1
            update_referral_text_in_engage_table(community)
    info_logger.info(c)


############# functions edit community    ##########################

@csrf_exempt
def edit_community(request):

    '''function to edit the community'''

    community_id=request.GET.get('community_id')

    json_body=json.loads(request.body)

    key=json_body['key']

    if key == 'purpose':
        value = json_body['value']
        purpose_collabcard=Community.objects.filter(id=community_id).values('purpose_collabcard')
        purpose_collabcard=purpose_collabcard[0]['purpose_collabcard']
        Collabcard.objects.filter(id=purpose_collabcard).update(title=value)
        Community.objects.filter(id=community_id).update(purpose=value)

    elif key == 'questions':
        questions=json_body['questions']
        edit_questions(questions,community_id)
    else:
        value = json_body['value']
        Community.objects.filter(id=community_id).update(**{key: value})

    community=Community.objects.get(id=community_id)

    serialized_object = CommunitySerializer(community)
    new_dict = {}
    new_dict.update(serialized_object)

    return JsonResponse({'success': True,'community':new_dict})


def edit_questions(questions,community_id):

    '''function to edit questions of community'''

    community_object=Community.objects.get(id=community_id)
    Form_data.objects.filter(community_id=community_object).delete()
    print('Previous Questions Deleted')

    for question in questions:
    # if any new question is added -- Insert functionality
        question_object=Form_data()
        question_object.data=question['key']
        question_object.community_id=community_object
        question_object.save()

    print('questions updated successfully')


############# functions to update user location and city    ##########################

@csrf_exempt
def update_location(request):
    ''' function to update user location lat and long co-ordinates '''

    user_id = request.GET.get('member_id')
    latitude = request.GET.get('latitude')
    longitude = request.GET.get('longitude')
    userinfo = Userinfo.objects.get(user_id__id =user_id)

    if not userinfo.latitude and not userinfo.longitude:
        userinfo.latitude = latitude
        userinfo.longitude = longitude
        userinfo.save()
        all_location_tags = get_user_location(request, userinfo.user_id, 'all')
        city = all_location_tags['city']
        userinfo.city = city
        userinfo.address = all_location_tags['address']
        userinfo.save()

        update_user_city_tag.delay( userinfo.user_id.id, all_location_tags)
        return JsonResponse({'success': True})

    return JsonResponse({'success':False})


@shared_task
def update_user_city_tag(user_id,location):
    ''' function to update city tag for user '''
    user  = User.objects.get(pk=user_id)
    global_tag = Tags_lpig.objects.get(name='Global')
    user_tags_list = list(User_Geography.objects.filter(user_id=user).values_list("tags_id",flat=True))

    for attr,loc_tag in location.items():

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
        user_tags_list = list(User_Geography.objects.filter(user_id=user).values_list("tags_id",flat=True))

        if global_tag.id not in user_tags_list:
            user_tag = User_Geography()
            user_tag.tags_id = global_tag
            user_tag.user_id = user
            user_tag.save()
    return


@shared_task
def get_or_create_lpig_tags(tag,category,attr):
    ''' function to create new tags '''
    cat = category

    try:
        tag = Tags_lpig.objects.get(name=tag)

    except:

        attribute = category+"_uncat"
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
        tag.save()
        tag.tag_id = tag.id
        tag.save()

    finally:
        if cat == 'Geography':
            tag_name,tag_id = tag.name,tag.id
            print("collabmates api update tag image at create or get lpig tags")
            update_tag_image.delay(tag_name=tag_name, tag_id=tag_id)

    return tag


def get_user_location(request,user_id,type=None):
    ''' function to fetch user location '''

    flag = True
    if not type:
        type = request.GET.get('type','')
        flag = False
    userinfo = Userinfo.objects.get(user_id=user_id)

    gmaps = googlemaps.Client(key='AIzaSyDN10TwCPVMdLEE6vvTiglKHGlkTIYKduc')
    location_response = gmaps.reverse_geocode((userinfo.latitude,userinfo.longitude))


    addr=location_response[1]['formatted_address']
    address=addr.split(',')
    if type and type == 'address':
        response = {'location':addr}

    elif type and type == 'country':
        country = address[-1].strip()
        print("country ==== ",country)
        response = {'location': country}

    elif type and type == 'state':
        state = address[-2][:-7].strip()
        print('state ===== ', state)
        response = {'location':state}

    elif type and type == 'pincode':
        pincode = address[-2][-6:].strip()
        print("pincode === ",pincode)
        response = {'location': address}

    elif type and type == 'city':

        city = address[-3].strip()
        print("city ==== ",city)
        response = {'location': city}

    elif type and type == 'all':

        # return list [city,state,country,pincode]

        response = {}
        response['city']  = address[-3].strip()
        response['pincode'] = address[-2][-6:].strip()
        response['state'] = address[-2][:-7].strip()
        response['country'] = address[-1].strip()
        response['address'] = addr

        if flag:
            return response


    return JsonResponse(response,safe=False)


def all_members(request):
    '''function to send all user data '''
    page=request.GET.get('page')
    community_id=request.GET.get('community_id')
    query_set=Userinfo.objects.all().order_by("name")
    user_data=[]
    for user in query_set:

        user_object=UserinfoSerializer(user)
        state=Members.objects.filter(community_id=community_id,member_id_id=user.user_id).values('state')
        if state:
            state=state[0]['state']
        else:
            state=0
        user_object['state']=state
        user_data.append(user_object)
    user_data = sorted(user_data, key=lambda i: i['state'],reverse=True)

    return JsonResponse({'members':user_data[20*(int(page)-1):20*int(page)]})



def invite_members(request):
    ''' function to get members requested to join in a community '''

    member_id = request.GET.get('member_id',None)
    community_id = request.GET.get('community_id',None)

    pend_requests = get_referred_members_of_a_member(community_id, member_id)

    pending_requests = []
    for i in pend_requests:
        user_id = i
        resp = Form_response.objects.filter(community = community_id).filter(user = user_id)
        user = Userinfo.objects.get(user_id = user_id)
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
    res=json.loads(request.body)
    community_id=res['community_id']
    member_id=res['member_id']
    value=res['value']
    all_members=Members.objects.filter(community_id=community_id)
    community = Community.objects.get(id=community_id)
    if value:

        if 'member_ids' not in res or not res['member_ids']:
            Members.objects.filter(community_id=community_id,member_id=member_id).update(state=1,created_at=time.time())
            user = User.objects.get(pk=member_id)
            name  = user.userinfo.name
            send_notification_to_all_admins.delay(community_id, name, member_id)
            return JsonResponse({'success': True})

        refered_id=res['member_ids']
        for member in all_members:
            if str(member.member_id.id) == str(member_id):
                continue
            if str(member.member_id.id) in refered_id:
                req_dict={
                    'accepted':True,
                    'member_id':member.member_id.id,
                    'community_id':community_id
                }
                request_response(request,req_dict)
            else:
                Members.objects.filter(community_id=community_id,member_id=member.member_id.id).update(state=3)


    #update member engage table enteries
    update_pending_member_count_in_engage(community)
    update_referral_text_in_engage_table(community)
    update_member_count(community_id)
    return JsonResponse({'success':True})


def get_profile(request):

    '''api to send user object'''

    member_id=request.GET.get('member_id')

    try:
        user=Userinfo.objects.get(user_id=member_id)
        usr = UserinfoSerializer(user)
        tags = get_user_lpig_tags(usr['id'])
        if tags:
            usr['tags']=tags
            return JsonResponse({'user': usr})
        return JsonResponse({'user': usr})
    except:
        print("userinfo object does not exist")

    return JsonResponse({'user': []})


def get_member_id_from_headers(request):

    '''function to get member id from headers'''

    headers = request.META
    member_id=0
    if 'HTTP_X_MEMBER_ID' in headers and 'HTTP_X_VERSION_CODE' in headers:
        member_id = headers['HTTP_X_MEMBER_ID']
    return member_id


################ functions for getting and setting of tags ##########################################


def get_second_screen_of_onboarding(member_tags_list):

    '''function to take college of a user'''

    temp = {}
    temp['title'] = "Enter your schools/colleges"
    temp['sub_title'] = "Discover relevant alumni communities"
    attribute_list=[]
    attribute_id = 2
    category_id=1
    attribute_name = "Legacy_education"
    hint = "Your Schools/Colleges"
    display_name="Education"
    college_list = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint,category_id,display_name)
    attribute_list.append(college_list)
    temp['attributes'] = attribute_list

    return temp

def get_first_screen_of_onboarding(member_tags_list):

    '''function to get secong screen of onboarding'''

    temp = {}
    temp['title'] = "Mention your neighbourhood"
    temp['sub_title'] = "Discover relevant local communities"
    attribute_list=[]

    attribute_id = 12
    attribute_name = "Geography_city"
    hint="Your society/locality/city"
    category_id=4
    display_name="city"
    city_list=get_tag_attributes(member_tags_list,attribute_id,attribute_name,hint,category_id,display_name)
    attribute_list.append(city_list)


    attribute_id = 3
    attribute_name = "Legacy_hometown"
    hint="+ Add hometown"
    category_id=1
    display_name="hometown"
    hometown_list=get_tag_attributes(member_tags_list,attribute_id,attribute_name,hint,category_id,display_name)
    attribute_list.append(hometown_list)
    temp['attributes'] = attribute_list

    return temp

def get_tag_attributes(member_tags_list,attribute_id,attribute_name,hint,category_id,display_name):

    '''function to get sports tags'''

    # for sports
    # attribute_id = 10
    # attribute_name = "Interests_sports"

    tags = Tags_lpig.objects.filter(attribute_id=attribute_id)
    attribute_temp = {}
    attribute_temp['hint'] = hint
    attribute_temp['id'] = attribute_id
    attribute_temp['name'] = attribute_name
    attribute_temp['category_id']=category_id
    attribute_temp['display_name']=display_name.capitalize()
    tag_list = []
    for each_tag in tags:
        tag = {}
        tag['id'] = each_tag.tag_id
        tag['name'] = each_tag.name
        tag['attribute_name'] = attribute_name
        if each_tag.image_link:
            tag['image_url'] = each_tag.image_link
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
    hint="Playing these sports"
    category_id=3
    display_name="sport"
    sports_list=get_tag_attributes(member_tags_list,attribute_id,attribute_name,hint,category_id,display_name)
    attribute_list.append(sports_list)


    # getting hobbies

    attribute_id = 9
    attribute_name = "Interests_hobby"
    hint = "Pursuing these hobbies"
    category_id=3
    display_name="hobby"
    hobbies = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint,category_id,display_name)
    attribute_list.append(hobbies)

    # getting fan

    attribute_id = 11
    attribute_name = "Interests_fan"
    hint = "Following these teams, sports, genres or topics"
    category_id = 3
    display_name="fan"
    fan = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint, category_id,display_name)
    attribute_list.append(fan)

    # getting cause

    attribute_id = 8
    attribute_name = "Interests_cause"
    hint = "Working on these causes"
    category_id=3
    display_name="cause"
    cause = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint,category_id,display_name)
    attribute_list.append(cause)

    #getting skill

    attribute_id = 5
    attribute_name = "Profession_skill"
    hint = "Skills that you have"
    category_id=2
    display_name="skill"
    skill = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint,category_id,display_name)
    attribute_list.append(skill)


    #getting industry

    attribute_id = 6
    attribute_name = "Profession_industry"
    hint = "Industry that you belong to"
    category_id=2
    display_name="industry"
    industry = get_tag_attributes(member_tags_list, attribute_id, attribute_name, hint,category_id,display_name)
    attribute_list.append(industry)



    temp['attributes']=attribute_list

    return temp


def onboarding(request):

    '''function to send all the tags for onboarding'''

    onboarding_screens=[]
    user_id=request.GET.get('member_id','')
    member_tags_list=[]

    if user_id:
        legacy = list(User_Legacy.objects.filter(user_id=user_id).values_list('correct_tag_id',flat=True))
        profession = list(User_Profession.objects.filter(user_id=user_id).values_list('correct_tag_id',flat=True))
        interest = list(User_Profession.objects.filter(user_id=user_id).values_list('correct_tag_id',flat=True))
        geography =list(User_Profession.objects.filter(user_id=user_id).values_list('correct_tag_id',flat=True))
        member_tags_list=legacy+profession+interest+geography


    # first screen flow

    screen=request.GET.get('screen','')

    if screen == "first":
        first_screen=get_first_screen_of_onboarding(member_tags_list)
        onboarding_screens.append(first_screen)
        #print(onboarding_screens)
        return JsonResponse({'onboarding': onboarding_screens})

    # second screen flow
    if screen == "second":
        second_screen=get_second_screen_of_onboarding(member_tags_list)
        onboarding_screens.append(second_screen)
        #print(onboarding_screens)
        return JsonResponse({'onboarding': onboarding_screens})

    # third screen flow

    if screen == "third":
        third_screen=get_third_screen_of_onboarding(member_tags_list)
        onboarding_screens.append(third_screen)
        #print(onboarding_screens)
        return JsonResponse({'onboarding': onboarding_screens})

    return JsonResponse({'onboarding':onboarding_screens})


def save_tags_for_user_from_onboarding(category_id,tag_id,member_id):

    '''function to save user tags in lpig tables'''
    category_id=int(category_id)
    if category_id == 1:
        if tag_id.attribute_id.id == 3:
            tag_id = insert_user_home_town_tags(user_id=member_id.id,tag=str(tag_id.tag_id))
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

    log="""for category_id=%s, tags_id=%s saved for member_id=%s"""%(str(category_id),str(tag_id),str(member_id))
    info_logger.info(log)


@csrf_exempt
def push_onboarding(request):

    '''function to save user tags'''

    user_id=get_member_id_from_headers(request)
    response = json.loads(request.body)
    member_id=0
    try:
        member_id=User.objects.get(id=user_id)   #getting a user object in member id
    except:
        error_logger.error("User does not exist")
    for data in response['attributes']:

        category_id=data['category_id']
        tags=data['tags']

        for tag in tags:

           if 'id' in tag and tag['id']:
              tag_id=Tags_lpig.objects.get(id=tag['id'])
              save_tags_for_user_from_onboarding(category_id,tag_id,member_id)
           else:
               attribute_id=Attributes.objects.get(id=data['id'])
               if attribute_id.id == 12:
                   update_status=Userinfo.objects.filter(user_id=user_id).update(address=tag['name'])
                   print(update_status)
                   save_geography_and_hometown_tags_of_user_from_onboarding(tag['name'],member_id,attribute_id,4)

               elif attribute_id.id == 3:
                   save_geography_and_hometown_tags_of_user_from_onboarding(tag['name'],member_id,attribute_id,1)
               else:
                   uncharacterized_category_id=Category.objects.get(id=6)
                   tag_object=Tags_lpig()
                   tag_object.name=tag['name']
                   tag_object.attribute_id=attribute_id
                   tag_object.category_id=uncharacterized_category_id      # uncategorized tag
                   tag_object.save()
                   tag_object.tag_id=tag_object.id
                   tag_object.save()
                   save_tags_for_user_from_onboarding(category_id,tag_object,member_id)


    #saving global tags for user

    tag_id = Tags_lpig.objects.get(id=15)
    legacy_global=User_Legacy.objects.filter(tags_id=tag_id,user_id=member_id)
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

    log="""All tags inserted success fully for user=%s"""%(str(member_id))
    info_logger.info(log)

    compute_rank.delay(user_id=user_id)
    send_mail_after_rank_computation.delay(user_id) # both mail and notification will be sent here

    return JsonResponse({'success':True})

def save_geography_and_hometown_tags_of_user_from_onboarding(address_input,user_id,attribute_id,category_id):

    '''function to take the address of the user and get its city,state and country tags to save in tags'''

    user_address=get_city_address(city=address_input)

    city=user_address['city']
    if category_id == 4:
        city_tag=Tags_lpig.objects.filter(attribute_id=attribute_id,name=city)
        if city_tag:
            save_tags_for_user_from_onboarding(4,city_tag[0],user_id)
        else:
            category=Category.objects.get(id=4)
            tag_object = Tags_lpig()
            tag_object.name = user_address['city']
            tag_object.attribute_id = attribute_id
            tag_object.category_id = category                   # uncategorized tag
            tag_object.save()
            tag_object.tag_id = tag_object.id
            tag_object.save()
            save_tags_for_user_from_onboarding(4, tag_object, user_id)

    elif category_id == 1:
        hometown=Tags_lpig.objects.filter(attribute_id=attribute_id,name=city)
        if hometown:
            save_tags_for_user_from_onboarding(1, hometown[0], user_id)
        else:
            category = Category.objects.get(id=1)
            tag_object = Tags_lpig()
            tag_object.name = user_address['city']
            tag_object.attribute_id = attribute_id
            tag_object.category_id = category  # uncategorized tag
            tag_object.save()
            tag_object.tag_id = tag_object.id
            tag_object.save()
            save_tags_for_user_from_onboarding(1, tag_object, user_id)

    print("Hometown and city updated successfully")







