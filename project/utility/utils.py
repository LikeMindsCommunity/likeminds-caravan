# file containing common functions of both android and web
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from bs4 import BeautifulSoup
import requests
from togther.models import *
from togther.models import *
from django.shortcuts import get_object_or_404
from django.db.models import Q
import requests as rqst
import json
import os


def decode_meta_from_url(url):

    '''function to take meta tags from url'''

    r = requests.get(url)

    soup = BeautifulSoup(r.text,'html.parser')
    title = soup.find("meta", property="og:title")
    image=soup.find("meta",property="og:image")
    description=soup.find("meta",property="og:description")
    og_tags={}

    try:
        og_tags['title']=title['content']
    except:
        pass

    try:
        og_tags['image'] = image['content']
    except:
        pass

    try:
        og_tags['description'] = description['content']
    except:
        pass
    og_tags['url']=url
    return og_tags


def get_nominated_admin_details(community_id,email):
    '''fetching nominated promoter details from temp admin table'''
    community = get_object_or_404(Community, pk = community_id)
    details = temp_admin.objects.filter(community_id=community,email=email)
    if details:
        '''details are present,return s true'''
        print('details are present')
        return True
    else:
        '''details are not present, returns false'''
        print('details are not present')
        return False


def update_member_count(community_id):
    ''' update members count of a community , when a promoter or member joins a community '''
    community = Community.objects.get(id=community_id)
    # getting the count of members including admins in a community
    count = Members.objects.filter(community_id=community).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7)).count()
    # updating count
    Community.objects.filter(id=community_id).update(members_count = count)
    return count


def set_user_tag(user_id, community_id):
    ''' function to set hidden tag for user '''
    community = Community.objects.get(id=community_id)
    iit_tag = Community_tags.objects.filter(community_id=community, tags_id=41)
    nsit_tag = Community_tags.objects.filter(community_id=community, tags_id=42)
    check = True
    # we have only two hidden tags now
    # if we have more hidden tags this function is gonna change
    if iit_tag:
        tag_id = 41
        check = check_user_tag(user_id=user_id, tag_id=tag_id)
    elif nsit_tag:
        tag_id = 42
        check = check_user_tag(user_id=user_id, tag_id=tag_id)
    if not check:
        user_tag = userinfo_tags()
        user_tag.user_id = user_id
        user_tag.tag_id = tag_id
        user_tag.save()
    return


def get_user_tag(user_id):
    ''' function to get user hidden tag '''
    user_tag = userinfo_tags.objects.all().filter(user_id=user_id)
    return user_tag


@shared_task
def update_tag_image(tag_name, tag_id):
    locations = [tag_name, 'city', 'district', 'state', 'country']
    print('is digit ',tag_name.isdigit())
    if tag_name.isdigit() :
        return
    for loc in locations:
        if loc == tag_name:
            loc = tag_name

        else:
            loc = tag_name + " " + loc
        print(loc)
        request = 'https://en.wikipedia.org/w/api.php?action=query&format=json&formatversion=2&prop=pageimages|pageterms&piprop=thumbnail&pithumbsize=600&titles=' + str(
            loc)
        response = rqst.get(request)
        print("status code",response.status_code)
        if response.status_code == 200:
            response = json.loads(response.content.decode('utf-8'))
        if 'thumbnail' in response['query']['pages'][0]:

            tag_obj = Tags_lpig.objects.get(pk = tag_id)
            file_name = '/media/tags_images/' + tag_name + "__tag.jpeg"
            if not tag_obj.tag_image:

                image_url = response['query']['pages'][0]['thumbnail']['source']
                img_data = rqst.get(image_url).content
                # file_name = '/media/tags_images/' + tag_name + "__tag.jpeg"

                path = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'media', )
                to_path = path + file_name

                print(to_path)

                if not os.path.isfile(to_path):
                    with open(to_path,mode = 'wb+') as file :
                        print('creating file')
                        file.write(img_data)
                else:
                    print('file already exists')

            tag_obj.tag_image = file_name
            tag_obj.save()
            return
    return

