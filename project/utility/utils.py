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
from collabmates_api.notification import send_notification_to_eligible_member

from django.http.response import JsonResponse



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

    print('is digit ', tag_name.isdigit())
    if tag_name.isdigit():
        return

    locations = [tag_name, tag_name.title(), tag_name.lower(), tag_name +' city', tag_name +' district', tag_name +' state', tag_name +' country']

    for loc in locations:

        print(loc)
        request = 'https://en.wikipedia.org/w/api.php?action=query&format=json&formatversion=2&prop=pageimages|pageterms&piprop=thumbnail&pithumbsize=600&titles=' + str(
            loc)
        response = rqst.get(request)
        print("status code",response.status_code)
        if response.status_code == 200:
            response = json.loads(response.content.decode('utf-8'))
            print('loc',response)
        if 'thumbnail' in response['query']['pages'][0]:

            tag_obj = Tags_lpig.objects.get(pk = tag_id)
            file_name = 'media/tags_images/' + tag_name + "__tag.jpeg"
            if not tag_obj.tag_image:

                image_url = response['query']['pages'][0]['thumbnail']['source']
                img_data = rqst.get(image_url).content
                # file_name = '/media/tags_images/' + tag_name + "__tag.jpeg"

                path = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'media/', )
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


def get_city_address(request=None,city=None):

    request = "https://maps.googleapis.com/maps/api/geocode/json?address="+str(city)+"&key=AIzaSyDN10TwCPVMdLEE6vvTiglKHGlkTIYKduc"
    response = rqst.get(request)
    response = response.json()
    country = ''
    city = ''
    district = ''
    state = ''
    postal_code = ''

    for level in response['results'][0]['address_components']:

        for typ in level['types']:

            if typ == 'administrative_area_level_1':

                state = level['long_name']

            elif typ == 'country':
                country = level['long_name']

            elif typ == 'administrative_area_level_2':
                district = level['long_name']

            elif typ == 'locality':
                city = level['long_name']

            elif typ == 'postal_code':
                postal_code = level['long_name']

    # return JsonResponse({'response':response})

    # return JsonResponse({'city':city,'district':district,'state':state,'country':country,'postal_code':postal_code})
    return {'city':city,'district':district,'state':state,'country':country,'postal_code':postal_code}


def create_or_categorize_tag(tag,category,attribute):
    ''' function to create a un-categorized tag '''

    new_tag = tag
    new_tag = new_tag.strip().title()

    # if tag is not a empty string
    if new_tag!='':
        category = Category.objects.filter(Q(name__icontains=category))[0]
        if not attribute == 'district':
            # if attribute is not district (cause currently we dont have a attribute geo_district)

            attribute = Attributes.objects.filter(Q(attribute_name__icontains=attribute))
            if attribute.exists():
                attribute = attribute[0]
                tag = Tags_lpig.objects.filter(name = new_tag,attribute_id =attribute)
                print("here",tag,tag.exists())
                # create a new tag if tag is not present already
                if not tag.exists() :
                    print('create or categorize  ',new_tag)
                    tag = Tags_lpig()
                    tag.name = new_tag
                    tag.category_id = category
                    tag.attribute_id = attribute
                    tag.save()
                    tag.tag_id = tag.id
                    tag.save()

                elif tag.exists():
                    # print('tag is present categorizing the tag',tag)
                    tag = Tags_lpig.objects.get(pk = tag[0].id)
                    print('tag is present categorizing the tag', tag)
                    if tag.attribute_id.id >=17 and tag.attribute_id.id <=20:
                        print("inside")
                        tag.category_id = category
                        tag.attribute_id = attribute
                        tag.save()
                else:
                    tag = tag[0]

                # tag is of category type geography update or create tag image
                if category.name == 'Geography':
                    tag_name, tag_id = new_tag, tag.id
                    update_tag_image.delay(tag_name=tag_name, tag_id=tag_id)
                return tag
            return None
        return None
    return None


@shared_task
def update_user_geography_tags(user_id, typ=''):

    user = User.objects.get(id=user_id)

    # getting all geography tags of the user
    user_tags_list = list(User_Geography.objects.filter(user_id=user).values_list("tags_id",flat=True))
    # save city,district state and country of a particular city tag
    for each_tag in user_tags_list:
        tag = Tags_lpig.objects.get(pk=each_tag)
        tag_name = tag.name

        if tag.id == 15 or tag.id == 16 or tag.id == 17 or tag.id == 18:
            continue

        geography_list = get_city_address(city = tag_name)

        for attr,tag_name in geography_list.items():

            print(">>>>>>>>",tag_name,attr)
            if tag_name == '':
                continue
            # creating or catgorizing a tag with known category and attribute
            tag = create_or_categorize_tag(tag=tag_name,category='Geography',attribute=attr)

            user_geo_tag = User_Geography.objects.filter(tags_id=tag, user_id=user)

            if not user_geo_tag.exists() and tag :
                print("update_user_geography_tags  ", tag)

                user_geo_tag = User_Geography()
                user_geo_tag.tags_id = tag
                user_geo_tag.user_id = user
                user_geo_tag.save()
                print('user_geo_tag === ',user_geo_tag)


def referal(ref_id, community_id, interested_member_id):

    eligilibility_count = 3

    community = get_object_or_404(Community, pk=community_id)

    # invited member and intrested member are same person
    invited_member = User.objects.get(pk=interested_member_id)

    interested_member = Members.objects.filter(community_id=community,
                                               member_id=invited_member)
    if not interested_member.exists():
        interested_member = Members(community_id=community,
                                    member_id=invited_member,
                                    state=8)
        interested_member.save()

    referred_member = User.objects.get(pk=ref_id) if (ref_id != '' and ref_id) else False
    if referred_member:
        refer = Referal.objects.filter(member=referred_member,
                                       invited_member=invited_member,
                                       community=community)
        if not refer.exists():
            refer = Referal(member=referred_member
                            , invited_member=invited_member
                            , community=community)
            refer.save()

        total_referals = Referal.objects.filter(member=referred_member,
                                                community=community)

        if total_referals.count() >= eligilibility_count:
            admin = Members.objects.filter(community_id=community, member_id=referred_member)

            if admin.exists():
                Members.objects.filter(community_id=community, member_id=referred_member).update(state=9)

            elif not admin.exists():
                admin = Members(community_id=community, member_id=referred_member, state=9)
                admin.save()

            send_notification_to_eligible_member.delay(eligible_member_id=referred_member.id, community_name = community.name, community_id=community_id)

            # for interested_member in total_referals:
            #     Members.objects.filter(community_id=community,
            #                            member_id=interested_member.invited_member).update(state=3)
    return


def get_referred_members_of_a_member(community_id,member_id):

    community = get_object_or_404(Community, pk=community_id)
    referred_member = User.objects.get(pk=member_id)

    member_list=[]
    total_referals = Referal.objects.filter(member=referred_member, community=community)

    if total_referals.exists():
        for interested_member in total_referals:
            member_list.append(interested_member.invited_member.id)

    return member_list


def insert_user_home_town_tags(user_id,tag):
    ''' function to update user home town tag and
     add home town related state and country tags '''

    new_tag = tag
    new_tag = new_tag.strip().title()

    category = Category.objects.filter(Q(name__icontains='legacy'))[0]
    attribute = Attributes.objects.filter(Q(attribute_name__icontains='hometown'))[0]
    print('attribute  ',attribute,attribute.id)
    # if tag_id is present, get tag
    if tag.isdigit():
        tag = Tags_lpig.objects.get(pk=tag)
        tags = Tags_lpig.objects.filter(name = tag.name,attribute_id = attribute)
        print("\ntag id === ",tag)
        print(tags)
        # print("tag === >?>> ",tags[0],tags[0].attribute_id.id,type(tags[0].attribute_id.id))
        if tags.exists():
            print("already existing tag\n")
            tag = tags[0]
            new_tag = tags[0].name
            new_tag = new_tag.strip().title()
        else:
            print("creating new tag here")
            tag = Tags_lpig.objects.get(pk=tag)
            new_tag = tag.name.strip().title()
            tag = Tags_lpig()
            tag.name = new_tag
            tag.category_id = category
            tag.attribute_id = attribute
            tag.save()
            tag.tag_id = tag.id
            tag.save()

    else:
        # if tag is a string (which means its a new tag), create new tag
        tag = Tags_lpig()
        tag.name = new_tag
        tag.category_id = category
        tag.attribute_id = attribute
        tag.save()
        tag.tag_id = tag.id
        tag.save()
    create_user_hometown_tag_and_related_tags.delay(user_id=user_id, tag_id=tag.id, new_tag=new_tag)
    return tag


@shared_task
def create_user_hometown_tag_and_related_tags(user_id,tag_id,new_tag):
    tag = Tags_lpig.objects.get(pk=tag_id)
    user = User.objects.get(pk=user_id)
    user_tag = User_Legacy.objects.filter(tags_id=tag,user_id=user)

    if not user_tag.exists():
        # create user legacy tag as home town
        user_tag = User_Legacy()
        user_tag.tags_id = tag
        user_tag.user_id = user
        user_tag.save()
        tag_name, tag_id = tag.name, tag.id
        update_tag_image.delay(tag_name, tag_id)
    # adding other related geography tags for the user such as state and country
    geography_list = get_city_address(city=new_tag)

    for attr, tag_name in geography_list.items():

        if tag_name == '':
            continue
        if attr == 'city':
            continue
        # creating or categorizing a tag with known category and attribute
        # geography tag is created, create its related tags
        # for example, if gurgaon is created, create Haryana and India as well as state and country
        tag = create_or_categorize_tag(tag=tag_name, category='Geography', attribute=attr)

        user_geo_tag = User_Geography.objects.filter(tags_id=tag, user_id=user)
        user_legacy_home_town_tag = User_Legacy.objects.filter(tags_id=tag, user_id=user)

        # saving tag related state and country in user geography and user home town
        if not user_geo_tag.exists() and tag:
            user_geo_tag = User_Geography()
            user_geo_tag.tags_id = tag
            user_geo_tag.user_id = user
            user_geo_tag.save()
            print('user_geo_tag === ', user_geo_tag)

        if not user_legacy_home_town_tag.exists() and tag:
            user_home_town_tag = User_Legacy()
            user_home_town_tag.tags_id = tag
            user_home_town_tag.user_id = user
            user_home_town_tag.save()
            print('user_leg_tag === ', user_home_town_tag)

        # finally update all user geography tags to
        # get related things for all tags like state and country
        # with images
        update_user_geography_tags.delay(user_id=user_id, typ='Geography')
    return


@shared_task
def update_hometown_tags_for_all_users(tag_id):
    user_list_with_newly_categorized_tag = User_Legacy.objects.filter(tags_id=tag_id)
    for tag in user_list_with_newly_categorized_tag:
        user_id, tag_id = tag.user_id.id, str(tag.tags_id.id)
        insert_user_home_town_tags(user_id=user_id, tag=tag_id)

