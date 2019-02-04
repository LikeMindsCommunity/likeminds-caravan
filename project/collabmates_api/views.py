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
# your views here.

def communities(request):
    queryset = Community.objects.all().order_by('-active_since')
    community = []
    for i in queryset:
        serializer_class = CommunitySerializer(i)
        community.append(serializer_class.data)
    return JsonResponse({'communities': community})

def your_communities(request,user_id):
    communities = Members.objects.all().filter(member_id = user_id)
    my_communities = []
    for i in communities:
        my_communities.append(i.community_id)
    my_community =[]
    for i in my_communities:
        serializer_class = CommunitySerializer(i)
        my_community.append(serializer_class.data)
    return JsonResponse({'your_communities':my_community})

def community(request, community_id):
    queryset = Community.objects.get(id = community_id)
    serializer_class = CommunitySerializer(queryset)
    return JsonResponse({'communities': serializer_class.data})

def similar_community(request, community_id):
    community = Community.objects.get(id = community_id)
    queryset = Community.objects.all().order_by('-active_since')
    similar_communities = []
    for i in queryset:
        if i.id != community_id:
            serializer_class = CommunitySerializer(i)
            similar_communities.append(serializer_class.data)
    return JsonResponse({'similar_communities': similar_communities})

def join_community(request, community_id):
    data = Form_data.objects.all().filter(community_id = community_id)
    reqd_info = []
    for i in data:
        ques = {'data':i.data,
                'data_type':i.data_type,
                }
        reqd_info.append(ques)
    return JsonResponse({'data': reqd_info})

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
    member = Members.objects.all().filter(community_id = community_id)
    members = []
    for i in member:
        members.append({"member_id": i.member_id.id})
    print (members)
    return JsonResponse ({'members': members})