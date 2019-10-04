
from django.shortcuts import render,redirect
from django.http import HttpResponse
from togther.models import *
from django.views.generic import *
from django.db.models import Q
from django.db.models import F
import time
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import json
from django.http.response import JsonResponse
import requests as rqst
import os
import re
from django.views.decorators.csrf import csrf_exempt

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from urllib.parse import urlencode
url = settings.URL

# uncomment to run it in localhost
# url='http://localhost:8000'

api_url = url + '/api/'

from dashboard.views import dashboard

def login(request):

    if request.method == 'GET':
        username = request.GET.get('user',None)
        password = request.GET.get('pass',None)
        print("user name and pass word === ",username,password)
        if not username and not password:
            return render(request, 'analytics/login.html', {})
        elif username == 'admin' and password == 'collabmates':
            return redirect('/analytics')
        else:
            return render(request, 'analytics/login.html', {})


def logout():
    pass


def dashboard(request):
    '''function to give list of community to edit'''

    community_list=Community.objects.all().order_by('-updated_at', '-active_since')
    dashboard_list=[]

    page = request.GET.get('page', 1)
    paginator = Paginator(community_list, 100)
    try:
        community_list = paginator.page(page)
    except PageNotAnInteger:
        community_list = paginator.page(1)
    except EmptyPage:
        community_list = paginator.page(paginator.num_pages)

    for i in community_list:
        community_dic={}
        if i.hide_community == '2':
            continue
        community_dic['id']=i.id
        community_dic['name']=i.name
        community_dic['image_url']=i.image_url
        community_dic['purpose']=i.purpose
        pending_members_count=Members.objects.filter(community_id=i,state=3).count()
        community_dic['pending_member_count'] = pending_members_count
        members_count = Members.objects.filter(community_id=i).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7)).count()
        community_dic['members_count'] = members_count
        community_dic['active_since']=i.active_since
        community_dic['question_count']=Form_data.objects.filter(community_id=i).count()
        community_dic['hidden_tags_count']=get_tags_count(i)
        dashboard_list.append(community_dic)

    tags = Tags_lpig.objects.all().order_by('name')
    return render(request,'analytics/dashboard.html',{'communities':dashboard_list,
                                                    'community':community_list,
                                                    'tags': tags,})


def get_tags_count(community):

    '''function to get count of tags from dashboard'''

    tags_count = 0

    hidden_legacy_tags = list(Community_Legacy.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_profession_tags = list(Community_Profession.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_interests_tags = list(Community_Interest.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_geography_tags = list(Community_Geography.objects.filter(community_id=community).values_list('tags_id', flat=True))


    for tag in hidden_legacy_tags:
        global_tag = Tags_lpig.objects.get(name='legacy_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_profession_tags:
        global_tag = Tags_lpig.objects.get(name='profession_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_interests_tags:
        global_tag = Tags_lpig.objects.get(name='interest_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_geography_tags:
        global_tag = Tags_lpig.objects.get(name='Global')
        if tag == global_tag.id:
            continue
        tags_count += 1

    return tags_count


def all_user(request):

    '''dashboard to show all users'''
    userinfo=Userinfo.objects.all().order_by('-user_id')

    users_list = []
    for i in userinfo:
        user_dic = {}
        user_dic['id'] = i.id
        user_dic['user_id'] = i.user_id.id
        user_dic['name'] = i.name
        user_dic['email'] = i.email
        user_dic['image_url'] = i.image_file
        if i.fcm_token:
            print("has token")
            user_dic['fcm_token'] = 1
        else:
            print("no token")
            user_dic['fcm_token'] = 0
        tags = userinfo_tags.objects.filter(user_id=i.user_id.id)
        tags_count = tags.count()
        tags_list=[]
        for t in tags:
            tag = Tags.objects.get(id = t.tag_id)
            tags_list.append(tag.category_name)

        user_tags = get_user_tags_count(i.user_id)

        if user_tags > 0:
            user_dic['tags_count'] = user_tags
        else:
            user_dic['tags_count'] = 0
        user_dic['fb_link'] = i.fb_link
        user_dic['linkedin_link'] = i.linkedin_link

        communities_count = Members.objects.all().filter(member_id=i.user_id).filter(~Q(state=0)).count()
        user_dic['communities_count']=communities_count
        users_list.append(user_dic)
    return render(request, 'analytics/all_user.html', {'all_user': users_list})


def get_user_tags_count(user_id):

    tags_count = 0

    hidden_legacy_tags = list(User_Legacy.objects.filter(user_id=user_id).values_list('tags_id', flat=True))
    hidden_profession_tags = list(User_Profession.objects.filter(user_id=user_id).values_list('tags_id', flat=True))
    hidden_interests_tags = list(User_Interest.objects.filter(user_id=user_id).values_list('tags_id', flat=True))
    hidden_geography_tags = list(User_Geography.objects.filter(user_id=user_id).values_list('tags_id', flat=True))


    for tag in hidden_legacy_tags:
        global_tag = Tags_lpig.objects.get(name='legacy_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_profession_tags:
        global_tag = Tags_lpig.objects.get(name='profession_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_interests_tags:
        global_tag = Tags_lpig.objects.get(name='interest_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_geography_tags:
        global_tag = Tags_lpig.objects.get(name='Global')
        if tag == global_tag.id:
            continue
        tags_count += 1

    return tags_count


def all_members(request,community_id):

    '''function to show all members of the community'''

    members_info=Members.objects.filter(community_id=community_id)
    members_list=[]
    for i in members_info:
        member={}
        member['id']=i.member_id
        if i.state == 1 or i.state == 2:
            member['state']='Promoter'
        elif i.state == 3:
            member['state']='Pending'
        elif i.state == 4:
            member['state']='Member'
        elif i.state == 6:
            member['state']='Nominated Promoter'
        elif i.state == 7:
            member['state']='Nominated Promoter(already a member)'
        elif i.state == 5:
            member['state']='Declined by Promoter'

        userinfo = Userinfo.objects.filter(user_id=i.member_id)
        if not userinfo.exists():
            user = update_user_info(request=request, member_id=i.member_id)

        image_url=Userinfo.objects.filter(user_id=i.member_id).values('image_file')
        image_url=image_url[0]['image_file']
        member['image_file']=image_url
        member['community_id']=community_id
        members_list.append(member)

    unregistered_users = temp_admin.objects.filter(community_id=community_id)
    unregitered_users_list = []
    for user in unregistered_users:
        member={}
        member['name'] = user.name
        member['email'] = user.email
        member['contact_number'] = user.contact_number
        member['state'] = 'Unregistred user NOMINATED as promoter'
        userinfo=Userinfo.objects.filter(email = user.email)
        if userinfo :
            continue

        unregitered_users_list.append(member)

    return render(request,'analytics/all_members.html',{'member_list':members_list,'unregitered_users_list':unregitered_users_list})


def analytics(request):
    ''' function to show the analytics '''

    community_count=Community.objects.all().count()
    public_communities=Community.objects.filter(Q(hide_community='0')|Q(hide_community ='4')).count()
    private_communities=Community.objects.filter(hide_community='1').count()
    pre_created_communities=Community.objects.filter(hide_community='3').count()

    user_count=Userinfo.objects.all().count()
    promoter_member_count=Members.objects.filter(~Q(state=0)).values('member_id').distinct().count()
    working_communitites=Community.objects.filter(Q(hide_community= 2))


    promoter_count=Members.objects.filter(Q(state=1)|Q(state=2)).values('member_id').distinct().count()
    total_promoter_count = Members.objects.filter(Q(state=1)|Q(state=2)).values('member_id').count()
    member_count=Members.objects.filter(state=4).values('member_id').distinct().count()
    total_member_count = Members.objects.filter(state=4).values('member_id').count()
    conversations_count=Collabcard.objects.all().count()
    responses_count=card_answers.objects.all().count()


    context={
        'community_count':community_count,
        'public_communities':public_communities,
        'private_communities':private_communities,
        'user_count':user_count,
        'promoter_member_count':promoter_member_count,
        'promoter_count':promoter_count,
        'member_count':member_count,
        'conversations_count':conversations_count,
        'responses_count':responses_count,
        'total_promoter_count': total_promoter_count,
        'total_member_count': total_member_count,
        'pre_created_communities':pre_created_communities
    }
    return render(request,'analytics/analytics.html',context)


def hidden_tags(request,community_id):

    '''function to show hidden tags'''

    community = Community.objects.get(pk = community_id)

    legacy_tags = list(Tags_lpig.objects.filter(category_id__id = '1').values_list('name', flat=True))
    profession_tags = list(Tags_lpig.objects.filter(category_id__id = '2').values_list('name', flat=True))
    interests_tags = list(Tags_lpig.objects.filter(category_id__id = '3').values_list('name', flat=True))
    geography_tags = list(Tags_lpig.objects.filter(category_id__id = '4').values_list('name', flat=True))


    # hidden_tags = Community_LPIG.objects.filter(community_id=community_id)

    hidden_legacy_tags = list(Community_Legacy.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_profession_tags = list(Community_Profession.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_interests_tags = list(Community_Interest.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_geography_tags = list(Community_Geography.objects.filter(community_id=community).values_list('tags_id', flat=True))


    hidden_legacy_tag = ''
    hidden_profession_tag = ''
    hidden_interests_tag = ''
    hidden_geography_tag = ''


    for tag in hidden_legacy_tags:
        global_tag = Tags_lpig.objects.get(name='legacy_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_legacy_tag=hidden_legacy_tag+tag_object.name+","
        except:
            pass

    for tag in hidden_profession_tags:
        global_tag = Tags_lpig.objects.get(name='profession_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_profession_tag=hidden_profession_tag+tag_object.name+","
        except:
            pass


    for tag in hidden_interests_tags:
        global_tag = Tags_lpig.objects.get(name='interest_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_interests_tag=hidden_interests_tag+tag_object.name+","
        except:
            pass


    for tag in hidden_geography_tags:
        global_tag = Tags_lpig.objects.get(name='Global')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_geography_tag = hidden_geography_tag+tag_object.name+","
        except:
            pass

    context={
        'legacy_tags':legacy_tags,
        'profession_tags':profession_tags,
        'interests_tags':interests_tags,
        'geography_tags':geography_tags,
        'hidden_legacy_tag':hidden_legacy_tag,
        'hidden_profession_tag': hidden_profession_tag,
        'hidden_interests_tag': hidden_interests_tag,
        'hidden_geography_tag': hidden_geography_tag,
        'community_id':community_id,
        'community_name':community.name
    }

    return render(request,'analytics/hidden_tags.html',context)

def search(request,tag_ids):

    ''' function to fetch communities with searched tag '''

    print("\n inside search    =====   ",type(tag_ids),tag_ids)
    tag = Tags_lpig.objects.get(pk = tag_ids)

    community_list = []

    if tag.category_id.id == 1:
        community_list = Community_Legacy.objects.filter(tags_id = tag).values_list('community_id', flat=True)

    elif tag.category_id.id == 2:
        community_list = Community_Profession.objects.filter(tags_id = tag).values_list('community_id', flat=True)

    elif tag.category_id.id == 3:
        community_list = Community_Interest.objects.filter(tags_id = tag).values_list('community_id', flat=True)

    elif tag.category_id.id == 4:
        community_list = Community_Geography.objects.filter(tags_id = tag).values_list('community_id', flat=True)

    dashboard_list = []

    page = request.GET.get('page', 1)
    paginator = Paginator(community_list, 100)
    try:
        community_list = paginator.page(page)
    except PageNotAnInteger:
        community_list = paginator.page(1)
    except EmptyPage:
        community_list = paginator.page(paginator.num_pages)

    for i in community_list:
        print(i)
        community = Community.objects.get(pk = i)
        community_dic = {}
        if community.hide_community == '2':
            continue
        community_dic['id'] = community.id
        community_dic['name'] = community.name
        community_dic['image_url'] = community.image_url
        community_dic['purpose'] = community.purpose
        pending_members_count = Members.objects.filter(community_id=community, state=3).count()
        community_dic['pending_member_count'] = pending_members_count
        members_count = Members.objects.filter(community_id=community).filter(
            Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7)).count()
        community_dic['members_count'] = members_count
        community_dic['active_since'] = community.active_since
        community_dic['question_count'] = Form_data.objects.filter(community_id=community).count()
        community_dic['hidden_tags_count'] = get_tags_count(community)
        dashboard_list.append(community_dic)

    tags = Tags_lpig.objects.all()
    return render(request, 'analytics/search_results.html', {'communities': dashboard_list,
                                                        'community': community_list,
                                                        'tags': tags,'communities_length':len(dashboard_list) })


def user_tags(request,user_id):
    ''' gives all the user tags  '''
    user = User.objects.get(pk = user_id)

    legacy_tags = list(Tags_lpig.objects.filter(category_id__id = '1').values_list('name', flat=True))
    profession_tags = list(Tags_lpig.objects.filter(category_id__id = '2').values_list('name', flat=True))
    interests_tags = list(Tags_lpig.objects.filter(category_id__id = '3').values_list('name', flat=True))
    geography_tags = list(Tags_lpig.objects.filter(category_id__id = '4').values_list('name', flat=True))


    hidden_legacy_tags = list(User_Legacy.objects.filter(user_id=user).values_list('tags_id', flat=True))
    hidden_profession_tags = list(User_Profession.objects.filter(user_id=user).values_list('tags_id', flat=True))
    hidden_interests_tags = list(User_Interest.objects.filter(user_id=user).values_list('tags_id', flat=True))
    hidden_geography_tags = list(User_Geography.objects.filter(user_id=user).values_list('tags_id', flat=True))


    hidden_legacy_tag = ''
    hidden_profession_tag = ''
    hidden_interests_tag = ''
    hidden_geography_tag = ''


    for tag in hidden_legacy_tags:
        global_tag = Tags_lpig.objects.get(name='legacy_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_legacy_tag=hidden_legacy_tag+tag_object.name+","
        except:
            pass

    for tag in hidden_profession_tags:
        global_tag = Tags_lpig.objects.get(name='profession_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_profession_tag=hidden_profession_tag+tag_object.name+","
        except:
            pass


    for tag in hidden_interests_tags:
        global_tag = Tags_lpig.objects.get(name='interest_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_interests_tag=hidden_interests_tag+tag_object.name+","
        except:
            pass


    for tag in hidden_geography_tags:
        global_tag = Tags_lpig.objects.get(name='Global')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_geography_tag = hidden_geography_tag+tag_object.name+","
        except:
            pass

    context={
        'legacy_tags':legacy_tags,
        'profession_tags':profession_tags,
        'interests_tags':interests_tags,
        'geography_tags':geography_tags,
        'hidden_legacy_tag':hidden_legacy_tag,
        'hidden_profession_tag': hidden_profession_tag,
        'hidden_interests_tag': hidden_interests_tag,
        'hidden_geography_tag': hidden_geography_tag,
        'user_id':user_id,
        'user_name':user.userinfo.name
    }

    return render(request, 'analytics/user_tags.html', context)


def user_communities(request,user_id):
    """ function to get user communities """

    my_communities,count = get_user_communities(user_id)
    communities=[]
    for community in my_communities:
        comm={"name":community.name}
        mem_state_url = api_url + 'members_state'
        params = {'member_id': user_id,"community_id" : community.id}
        response = rqst.get(mem_state_url,params=params)
        if response.status_code == 200:
            state = json.loads(response.content.decode('utf-8'))['state']
            if state:
                if state ==1:
                    comm['state'] = 'Promoter'
                elif state ==2:
                    comm['state'] = "Temporary Promoter"
                elif state == 3:
                    comm['state'] = 'Pending'
                elif state == 4:
                    comm['state'] = 'Member'
                elif state == 6:
                    comm['state'] = 'Nominated Promoter'
                elif state == 7:
                    comm['state'] = 'Nominated Promoter(already a member)'
                elif state == 5:
                    comm['state'] = 'Declined by Promoter'
        communities.append(comm)

    return render(request,'analytics/user_communities.html',{"my_communities":communities,'count':count})

def get_user_communities(user_id):
    ''' function to get users communities '''

    communities = Members.objects.all().filter(member_id=user_id).filter(~Q(state=0))

    my_communities = []
    for community in communities:
        my_communities.append(community.community_id)
    my_community = []
    for community in my_communities:
        my_community.append(community)

    return my_community,communities.count()


def analytics_community(request,community_id):

    '''function to show analytics of community'''

    collabcard=Collabcard.objects.filter(community_id=community_id)
    collabcard_count=0
    collabcard_answer_count=0

    for each_collabcard in collabcard:
        collabcard_count=collabcard_count+1
        answer_count=card_answers.objects.filter(card_id=each_collabcard.id).count()
        collabcard_answer_count=collabcard_answer_count+answer_count

    context={
        'conversations_count':collabcard_count,
        'answers_count':collabcard_answer_count
    }

    return render(request,'analytics/community_analytics.html',context)


def user_invited_members(request,user_id):
     user  = User.objects.get(pk=user_id)

     referals = Refer.objects.filter(member=user).distinct('community__id').order_by('community__id')
     community_list = []
     members=[]
     previous_community_id = None
     for referal in referals:
         comm = {}
         if referal.community.id != previous_community_id:
             previous_community_id = referal.community.id
             members=[]

         comm['community_name'] = referal.community.name
         if referal.community.id == previous_community_id:

            members.append(referal.invited_member.name)


     return render(request, 'analytics/user_invited_members.html', {})