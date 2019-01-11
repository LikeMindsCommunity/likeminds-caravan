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
# Create your views here.

def communities(request):
    communities = Community.objects.all().order_by('-active_since')
    community = []
    for i in communities:
        if i.image_url :
            comm = {'id':i.id,
                'name':i.name,
                'about':i.about,
                'image_url':i.image_url.url,
                'location':i.location,
                'members_count':i.members_count,
                'purpose': i.purpose,
                }
            community.append(comm)
        else:
            comm = {'id':i.id,
                'name':i.name,
                'about':i.about,
                'location':i.location,
                'members_count':i.members_count,
                'purpose': i.purpose,
                }
            community.append(comm)
    return JsonResponse({'communities': community})

def your_communities(request,user_id):
    communities = Members.objects.all().filter(member_id = user_id)
    my_communities = []
    for i in communities:
        my_communities.append(i.community_id)
    my_community =[]
    for i in my_communities:
        if i.image_url :
            comm = {'id':i.id,
                'name':i.name,
                'about':i.about,
                'image_url':i.image_url.url,
                'location':i.location,
                'members_count':i.members_count,
                'purpose': i.purpose,
                }
            my_community.append(comm)
    return JsonResponse({'your_communities':my_community})
