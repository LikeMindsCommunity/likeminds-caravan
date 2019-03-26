from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from togther.models import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from togther.forms import * 
import urllib
import requests as rqst
from django.contrib.auth.models import User
import json
from django.http.response import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from collabmates_api.serializers import CommunitySerializer
from categories import Category_list
from django.views.decorators.csrf import csrf_exempt

# your views here.

def communities(request):
    if request.method == 'GET':
        body = request.GET
        if 'member_id' in body:
            user_id = body['member_id']
        response = request.GET.dict()
        if 'category' in response:
            if response['category'] != '':
                category = response['category']
                print(category)
                categories = Category.objects.all()
                communities = []
                for i in categories:
                    if i.category == category:
                        c = Community.objects.get(id = i.community_id.id)
                        communities.append(c)
                community = []
                for i in communities:
                    comm = {'id':i.id,
                        'name':i.name,
                        'about':i.about,
                        'image_url':i.image_url.url,
                        'location':i.location,
                        'members_count':i.members_count,
                        'purpose': i.purpose,
                        }
                    community.append(comm)
                return JsonResponse({'communities': community})
        else:
            queryset = Community.objects.all().order_by('-active_since')
            community = []
            for i in queryset:
                serializer_class = CommunitySerializer(i)
                community.append(serializer_class.data)
            return JsonResponse({'communities': community})
        
    queryset = Community.objects.all().order_by('-active_since')
    community = []
    user = User.objects.get(id = user_id)
    for i in queryset:
        serializer_class = CommunitySerializer(i)
        member = Members.objects.all().filter(community_id = i.id)
        is_member = False
        for m in member:
            if m.member_id == user:
                is_member = True
        comm = serializer_class.data
        print(comm)    
        comm['member_id'] = member_id
        community.append(comm)
    return JsonResponse({'communities': community})

def your_communities(request,user_id):
    member_id = request.GET.get('member_id')
    user = User.objects.get(id = member_id)
    communities = Members.objects.all().filter(member_id = user_id)
    my_communities = []
    print(communities)
    for i in communities:
        my_communities.append(i.community_id)
    my_community =[]
    for i in my_communities:
        members = Members.objects.all().filter(community_id = i.id)
        serializer_class = CommunitySerializer(i)
        comm = serializer_class.data
        for j in members:
            if j.member_id == user:
                comm['is_member'] = True
            else:
                comm['is_member'] = False
        my_community.append(comm)
    return JsonResponse({'your_communities':my_community})

def community(request, community_id):
    queryset = Community.objects.get(id = community_id)
    body = request.GET
    print(body)
    if 'member_id' in body:
        user_id = body['member_id']
    print(user_id)
    member = Members.objects.all().filter(community_id = community_id)
    is_member = False
    user = User.objects.get(id = user_id)
    for m in member:
        if m.member_id == user:
            is_member = True
    serializer_class = CommunitySerializer(queryset)
    community = serializer_class.data
    community['is_member']= is_member
    return JsonResponse({'community': community})

def similar_community(request, community_id):
    body = request.GET
    if 'member_id' in body:
        user_id = body['member_id']
    member = Members.objects.all().filter(community_id = community_id)
    is_member = False
    user = User.objects.get(id = user_id)
    
    community = Community.objects.get(id = community_id)
    queryset = Community.objects.all().order_by('-active_since')
    similar_communities = []
    for i in queryset:
        if i.id != community_id:
            serializer_class = CommunitySerializer(i)
            community = serializer_class.data
            print(community)
            member = Members.objects.all().filter(community_id = community['id'])
            is_member = False
            for m in member:
                if m.member_id == user:
                    is_member = True
            community['is_member']= is_member
            similar_communities.append(community)
    return JsonResponse({'communities': similar_communities})

def join_community(request, community_id):
    data = Form_data.objects.all().filter(community_id = community_id)
    reqd_info = []
    for i in data:
        ques = {'question':i.data,
                'data_type':i.data_type,
                }
        reqd_info.append(ques)
    return JsonResponse({'questions': reqd_info})

@csrf_exempt
def join_community_responses(request):
    res = json.loads(request.body)
    user_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')
    print(user_id, community_id)
    user = User.objects.get(id = user_id)
    community = Community.objects.get(id = community_id)
    response = Form_response()
    for i in res['questions']: 
        response.data = i['key']
        response.response = i['value']
        response.user = user.id
        response.community = community.id
        response.save()
    member = Members()
    member.member_id = user
    member.community_id = community
    member.save()
    return JsonResponse({'success':True})

def category_filter(request, category):
    categories = Category.objects.all()
    communities = []
    for i in categories:
        if i.category == category:
            c = Community.objects.get(id = i.community_id.id)
            communities.append(c)
    community = []
    for i in communities:
        serializer_class = CommunitySerializer(i)
        community.append(serializer_class.data)
    return JsonResponse({'communities': community})

def categories(request):
    return JsonResponse ({'category_list': Category_list})

def user(request, user_id):
    info = Userinfo.objects.all().filter(user_id = user_id)
    user = {}
    print (info)
    for i in info:
        user['id'] = i.user_id.id
        user["name"] = i.name
        user["email"] = i.email
        user["city"] = i.city
        user["headline"] = i.headline
        user["contact_number"] = i.contact_number
        user["image_url"] = i.image_url
        user["about"] = i.about
        user["fb_link"] = i.fb_link
        user["linkedin_link"] = i.linkedin_link
    return JsonResponse ({'user': user})

def members(request, community_id):
    community = get_object_or_404(Community, pk = community_id)
    print(community)
    member = Members.objects.all().filter(community_id = community)
    print(member)
    members = []
    for i in member:
        user = Userinfo.objects.get(user_id = i.member_id)
        usr = {}
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number
        usr["image_url"] = user.image_url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        members.append(usr)
    print (members)
    return JsonResponse ({'members': members})

def admins(request, community_id):
    admins = Admins.objects.all().filter(community_id = community_id)
    users = []
    for i in admins:
        user = Userinfo.objects .filter(user_id = i.admin_id)
        print(user)
        usr = {}
        usr['id'] = user[0].user_id.id
        usr["name"] = user[0].name
        usr["email"] = user[0].email
        usr["city"] = user[0].city
        usr["headline"] = user[0].headline
        usr["contact_number"] = user[0].contact_number
        usr["image_url"] = user[0].image_url
        usr["about"] = user[0].about
        usr["fb_link"] = user[0].fb_link
        usr["linkedin_link"] = user[0].linkedin_link
        users.append(usr)
    return JsonResponse ({'members': users})
@csrf_exempt
def create_community(request):
    print (request)
    params = request.GET
    print(params)
    if 'member_id' in params:
        user_id = params['member_id']
        print(user_id)
    if request.method == 'POST':
        res = json.loads(request.body)
        img = request.FILES.dict()
        print(res)
        group = Community()
        group.members_count = group.members_count + 1
        group.name = res['name']
        print(type(res['items']))
        for i in res['items']:
            if i['key'] == 'Purpose of the community':
                group.purpose = i['value']
            if i['key'] == 'Geography of the community':
                group.location = i['value']
            if i['key'] == 'about':
                group.about = i['value'] 
            if 'image' in img:
                group.image_url = img['image']
            if i['key'] == 'whatsapp_link' :
                group.whatsapp_group_link = i['whatsapp_link']
            if i['key'] == 'categories' :
                categories = res(['items'])
                for i in categories:
                    category = Category()
                    category.category = i
                    category.community_id_id = group.id
                    category.save()
        group.save()
        

        admin = Admins()
        user = User.objects.get(id = user_id)
        admin.admin_id = user
        community = Community.objects.get(id = group.id)
        admin.community_id = community
        admin.save()
        member = Members()
        member.member_id = user
        member.community_id = community
        member.save()
        return JsonResponse({'success':True})
    return JsonResponse({'success':True, 'community_id':community.id})

@csrf_exempt
def create_card(request):
    user_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')
    print (user_id, community_id)
    user = User.objects.get(id = user_id)
    community = Community.objects.get(id = community_id)
    if request.method == 'POST':
        res = json.loads(request.body)
        card = Collabcard()
        card.title = res['title']
        card.community = community
        card.user = user
        card.save()
        return JsonResponse({'success':True})
    return JsonResponse()

def collabcard(request, card_id):
    cards = Collabcard.objects.get(id = card_id)
    print(cards)
    answer = card_answers.objects.filter(card = cards)
    answers = []
    for i in answer:
        usr = {}
        user = Userinfo.objects.get(user_id = i.user.id)
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number
        usr["image_url"] = user.image_url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        answers.append({'id':i.id,'answer':i.answer, 'member': usr})
    user = Userinfo.objects.get(user_id = cards.user.id)
    usr = {}
    usr['id'] = user.user_id.id
    usr["name"] = user.name
    usr["email"] = user.email
    usr["city"] = user.city
    usr["headline"] = user.headline
    usr["contact_number"] = user.contact_number
    usr["image_url"] = user.image_url
    usr["about"] = user.about
    usr["fb_link"] = user.fb_link
    usr["linkedin_link"] = user.linkedin_link
    card = {'id': cards.id, 'title':cards.title, 'member':usr,'community' :cards.community.id}
    return JsonResponse({"collabcard": card, 'answers':answers})

def community_cards(request, community_id):
    user_id = request.GET.get('member_id')
    cards = Collabcard.objects.filter(community = community_id)
    card = []
    for i in cards:
        user = Userinfo.objects.get(user_id = i.user)
        usr = {}
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number
        usr["image_url"] = user.image_url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
    
        card.append({'id': i.id, 'title': i.title, 'member':usr })
    return JsonResponse ({'collabcards': card})
@csrf_exempt
def create_answer(request):
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
        ans.save()
        return JsonResponse({'success':True})
@csrf_exempt
def login(request):
    if request.method == 'POST':
        res = json.loads(request.body)
        print(res)
        user = Userinfo.objects.filter(email = res['email'])
        if user :
            userinfo = Userinfo.objects.all().filter(email = res['email'])
        else :
            userinfo = Userinfo.objects.all().filter(email = res['email'])
            if not userinfo:
                userinfo = Userinfo()
                usr = User()
                usr.username = res['name']
                usr.save()
                userinfo.user_id = usr
                userinfo.email = res['email']
                userinfo.name = res['name']
                userinfo.image_url = res['picture']['data']['url']
                if 'link' in res:
                    userinfo.fb_link = res['link']
                if 'location' in res:
                    userinfo.city = res['location']['name']
                userinfo.save()
        
        usr = {}
        print(userinfo)
        usr['id'] = userinfo[0].user_id.id
        usr["name"] = userinfo[0].name
        usr["email"] = userinfo[0].email
        usr["city"] = userinfo[0].city
        usr["headline"] = userinfo[0].headline
        usr["contact_number"] = userinfo[0].contact_number
        usr["image_url"] = userinfo[0].image_url
        usr["about"] = userinfo[0].about
        usr["fb_link"] = userinfo[0].fb_link
        usr["linkedin_link"] = userinfo[0].linkedin_link
        return JsonResponse ({'user': usr})
    return HttpResponse('Login Api')

def image_upload(request,community_id):
    body = request.GET
    if 'member_id' in body:
        user_id = body['member_id']
    user = User.objects.get(id = user_id)
    res = json.loads(request.body)
    image_url = res['image']
    community = Community.objects.get(id = community_id)
    community.image_url = image_url
    community.save()
    return JsonResponse({'success':True})