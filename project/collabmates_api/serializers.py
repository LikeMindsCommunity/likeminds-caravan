from django.contrib.auth.models import User, Group
from rest_framework import serializers
from togther.models import *
from django.conf import settings

url  = settings.URL
#
# class CommunitySerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = Community
#         fields = ('id','name', 'purpose', 'image_url' ,'about', 'location')

def CommunitySerializer(community):
    # function to serialize a community object
    return {
        'id': community.id,
        'name': community.name,
        'purpose': community.purpose,
        'image_url': url + community.image_url.url,
        'about': community.about,
        'location': community.location,
    }

def UserinfoSerializer(user):
    # function to serialize a community object
    return {
        'id': user.user_id.id,
        "name": user.name,
        "email": user.email,
        "city": user.city,
        "headline": user.headline,
        "contact_number": user.contact_number,
        "image_url": url +user.image_file.url,
        "about": user.about,
        "fb_link": user.fb_link,
        "linkedin_link": user.linkedin_link,
    }

def CollabcardSerializer(card,community):
    # function to serialize a community object
    return {
    'id' : card.id,
    'title' : card.title,
    'community' : community.id,
    'share_url' : url + '/collabcard/' + str(card.id),
    'answer_text' : card.answer_text,
    'share_link':card.share_link
    }
