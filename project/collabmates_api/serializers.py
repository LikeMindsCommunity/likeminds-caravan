from django.contrib.auth.models import User, Group
from rest_framework import serializers
from togther.models import *
from django.conf import settings
from django.db.models import Q
import  json
url  = settings.URL

#
# class CommunitySerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = Community
#         fields = ('id','name', 'purpose', 'image_url' ,'about', 'location')

def CommunitySerializer(community):
    # function to serialize a community object
    new_dict =  {
        'id': community.id,
        'name': community.name,
        'purpose': community.purpose,
        'about': community.about,
        'location': community.location,
    }
    if community.image_link:
        new_dict['image_url']=community.image_link
    elif community.image_url:
        new_dict['image_url'] = community.image_url.url
    else:
        new_dict['image_url'] = '/media/media/community/default.jpeg'


    if new_dict['image_url'] == "/media/https%3A/upload.wikimedia.org/wikipedia/en/0/09/Community_title.jpg":
        new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
    elif not community.image_link:
        new_dict['image_url'] = url + new_dict['image_url']
    new_dict['is_member'] = ''
    new_dict['share_url'] = url + '/community/' + str(new_dict['id'])
    new_dict['date'] = community.active_since
    new_dict['members_count'] = get_member_count(community)
    new_dict['state']=int(community.hide_community)
    return new_dict

def UserinfoSerializer(user):
    # function to serialize a community object
    userinfo= {
        'id': user.user_id.id,
        "name": user.name,
        "email": user.email,
        "city": user.city,
        "headline": user.headline,
        "contact_number": user.contact_number,
        "about": user.about,
        "fb_link": user.fb_link,
        "linkedin_link": user.linkedin_link,
    }

    if not user.image_link:
        userinfo['image_url'] = url + user.image_file.url
    else:
        userinfo['image_url']=user.image_link
    return userinfo

def CollabcardSerializer(card,community=None):
    # function to serialize a community object
    collabcard={
        'id': card.id,
        'title': card.title,
        'community_id': card.community_id,
        'share_url': url + '/collabcard/' + str(card.id),
        'answer_text': card.answer_text,
        'share_link': card.share_link,
        'image_count':card.image_count,
        'pdf_count': card.pdf_count,
    }
    if card.og_tags:
        og_tags=json.loads(card.og_tags)
        collabcard['og_tags']=og_tags

    return collabcard


def get_member_count(community):
    return Members.objects.filter(community_id=community).filter(
        Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7) | Q(state = 8)).count()


