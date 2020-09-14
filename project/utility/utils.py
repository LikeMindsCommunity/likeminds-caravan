# file containing common functions of both android and web
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from bs4 import BeautifulSoup
import requests
from togther.models import *
from django.shortcuts import get_object_or_404
from django.db.models import Q
import requests as rqst
import json
import ast
# from collabmates_api.notification import (send_notification_to_eligible_member,
#                                           send_notification_to_referred_member,
#                                           send_notification_to_referred_member_in_active_community,
#                                           )
from .tasks import *
from .firebase import upload_tag_files
from random import randint
from django.conf import settings
from user_agents import parse
import time
from datetime import datetime,date,timedelta
import dateutil.relativedelta
from .states import *
# cache details
# from django.core.cache import cache
# custom_cache=cache
# cache_timeout=3600

#link to download the android app
android_app_download_link="https://play.google.com/store/apps/details?id=com.collabmates"

ios_app_download_link="https://apps.apple.com/us/app/likeminds-community-chat/id1526635028"


community_default_image = "https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fcommunity%2Fimage_community_default?alt=media"

community_default_thumbnail = "https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fcommunity%2Fimage_community_default_thumbnail?alt=media"

community_default_image_round = "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Fmain_website%2Fgeneric_community_banner.png?alt=media&token=044d32ff-3da7-4d8d-9c83-d3c486b61f7a"

angellist_link = "https://angel.co/company/likeminds-6"
linkedIn_link = "https://www.linkedin.com/company/collabmates/about/"

url=settings.URL

if settings.IS_BETA:

    eligibility_count = 5
    ig_members_count=4

    feedback_community_id = 48640
    feedback_collabcard_id = 644

else:
    eligibility_count = 5
    ig_members_count = 4

    feedback_community_id = 49673
    feedback_collabcard_id = 517

# count for a particular community to show tutorial
tutorial_count=3



#member related functions
def is_member_engage(community,member):

    '''function to check if data is presnt in member engage table or not'''

    is_present=False
    member_data=Member_Engage.objects.filter(community_id=community,member_id=member)
    if member_data:
        is_present=True
    return is_present


def is_member_verified(community,user_instance):

    '''function to check whether the member is verified or not'''

    is_verified=Members.objects.filter(community_id=community,member_id=user_instance).filter(
        Q(state=member_states.ADMIN)|Q(state=member_states.PROFILE_UNAVAILABLE)|
        Q(state=member_states.MEMBER)|Q(state=member_states.KNOWN_NOMINATED_PROMOTER))

    if is_verified.exists():
        return is_verified[0]
    return False

def is_member_promoter(community_id,member_id):

    is_promoter = Members.objects.filter(community_id=community_id,member_id=member_id,state=member_states.ADMIN)

    if is_promoter.exists():

        return is_promoter[0].member_id

    return False

def is_member_pending(community_id, member_id):

    is_pending = Members.objects.filter(community_id=community_id, member_id=member_id, state=member_states.PENDING_MEMBER)

    return is_pending.exists()

def is_member_present(community_id,member_id):

    is_member = Members.objects.filter(community_id=community_id,
                                       member_id=member_id).filter(Q(state=member_states.MEMBER)
                                                                   |Q(state=member_states.KNOWN_NOMINATED_PROMOTER))
    return is_member.exists()


def get_members_count_in_community(community_id):

    '''function to get members count in a community'''

    instance = Members.objects.filter(community_id=community_id).filter(
        Q(state=member_states.ADMIN) | Q(state=member_states.TEMP_ADMIN) |
        Q(state=member_states.MEMBER) | Q(state=member_states.PROFILE_UNAVAILABLE))

    return instance.count()


#community related functions
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




#private link generation for chatrooms
def generate_private_link_for_chatroom(card_instance,user_instance):

    '''function to generate private links for chatrooms'''


    chatroom_expire_filter = chatroomExpiryCodes.objects.filter(card=card_instance,source=user_instance).order_by('-id')
    unique_code_list = list(chatroom_expire_filter.values_list('unique_code',flat=True))

    temp = {}

    if not unique_code_list:

        unique_code = generate_random(unique_code_list)
        expireInstance = chatroomExpiryCodes()
        expireInstance.card = card_instance
        expireInstance.source = user_instance
        expireInstance.created_at = time.time()
        expireInstance.unique_code = unique_code
        expireInstance.private_link = url + '/collabcard/' + str(card_instance.id) + "?aj=" + str(
            unique_code) + "&source_id=" + str(user_instance.id)

        expireInstance.expire_duration = 86400
        expireInstance.save()

        temp['private_link'] = expireInstance.private_link
        temp['private_link_created_at'] = get_date_time_from_timestamp(expireInstance.created_at)

        return temp

    else:

        current_time = int(time.time())
        last_created_time = chatroom_expire_filter[0].created_at

        if current_time - last_created_time > (3600*3):
            unique_code = generate_random(unique_code_list)
            expireInstance = chatroomExpiryCodes()
            expireInstance.card = card_instance
            expireInstance.source = user_instance
            expireInstance.created_at = time.time()
            expireInstance.unique_code = unique_code
            expireInstance.private_link = url + '/collabcard/' + str(card_instance.id) + "?aj=" + str(unique_code)+"&source_id="+str(user_instance.id)

            expireInstance.expire_duration = 86400
            expireInstance.save()

            temp['private_link'] = expireInstance.private_link
            temp['private_link_created_at'] = get_date_time_from_timestamp(expireInstance.created_at)

            return temp

    temp['private_link'] = chatroom_expire_filter[0].private_link
    temp['private_link_created_at'] = get_date_time_from_timestamp(chatroom_expire_filter[0].created_at)

    return temp


def get_date_time_from_timestamp(timestamp):

    return time.strftime('%d/%m/%y %H:%M', time.localtime(timestamp))




def decode_option(value):

    if not value:
        return []

    value = ast.literal_eval(value)
    value_list = []

    for item in value:
        value_list.append(item['value'])

    #print(value_list)

    return value_list

#collabcard related functions
def decode_meta_from_url(url):

    '''function to take meta tags from url'''


    is_valid_https=url.find("https://")

    if is_valid_https == -1:
        url="https://"+url



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


def get_time_text_for_my_chatrooms(updated_at):

    current_time = time.time()
    current_date = datetime.fromtimestamp(current_time).date()
    previous_date =  datetime.fromtimestamp(updated_at).date()
    difference = current_date  - previous_date

    if difference.days == 1:
        return "Yesterday"
    elif difference.days > 1:
        return time.strftime('%d/%m/%y', time.localtime(updated_at))
    else:
        return time.strftime('%H:%M', time.localtime(updated_at))




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
    # getting the count of members including admins in a community
    count = Members.objects.filter(community_id=community_id).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7)|Q(state=8)|Q(state=9)).count()
    # updating count
    Community.objects.filter(id=community_id).update(members_count = count)

    return count


@shared_task
def update_tag_image(tag_name, tag_id):

    print('is digit ', tag_name.isdigit())
    if tag_name.isdigit():
        return
    elif tag_name.lower() == 'gurugram':
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
            # file_name = 'media/tags_images/' + tag_name + "__tag.jpeg"
            if not tag_obj.image_link:

                image_url = response['query']['pages'][0]['thumbnail']['source']

                image_link = upload_tag_files(tag_id=tag_id,url=True,image=image_url)

                # img_data = rqst.get(image_url).content
                # # file_name = '/media/tags_images/' + tag_name + "__tag.jpeg"
                #
                # path = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'media/', )
                # to_path = path + file_name
                #
                # print(to_path)
                #
                # if not os.path.isfile(to_path):
                #     with open(to_path,mode = 'wb+') as file :
                #         print('creating file')
                #         file.write(img_data)
                # else:
                #     print('file already exists')

                # tag_obj.image_link = file_name
                tag_obj.image_link = image_link
                tag_obj.updated_at = time.time()
                tag_obj.save()
            return
    return


def get_city_address(request=None,city=None):

    tag_name = None
    if city:
        tag_name = city.lower()
        
    if str(city).isdigit():
        tag = Tags_lpig.objects.get(pk=city)
        tag_name = tag.name.lower()

    country = ''
    city = ''
    district = ''
    state = ''
    pincode = ''

    updated = False

    if tag_name:

        location_info = Location_Info.objects.filter(tag_name = tag_name)
        if location_info.exists():

            location_info = location_info[0]
            city = location_info.city if location_info.city else ''
            district = location_info.district if location_info.district else ''
            state = location_info.state if location_info.state else ''
            country = location_info.country if location_info.country else ''
            pincode = location_info.pincode if location_info.city else ''

        else:
            request = "https://maps.googleapis.com/maps/api/geocode/json?address="+str(tag_name)+"&key="+str(settings.GOOGLE_API_KEY)
            response = rqst.get(request)
            response = response.json()

            updated = True

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
                        pincode = level['long_name']

        if updated:

            location_info = Location_Info()

            location_info.tag_name = tag_name
            location_info.city = city
            location_info.district = district
            location_info.state = state
            location_info.country = country
            location_info.pincode = pincode

            location_info.save()

    # return JsonResponse({'response':response})

    # return JsonResponse({'city':city,'district':district,'state':state,'country':country,'postal_code':pincode})
    return {'city':city,'district':district,'state':state,'country':country,'postal_code':pincode}


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
                    tag.created_at = time.time()
                    tag.updated_at = time.time()
                    tag.tag_id = tag.id
                    tag.save()

                    # tag is of category type geography update or create tag image
                    if category.name == 'Geography' or attribute.id == 3:
                        if tag and not tag.image_link:
                            tag_name, tag_id = new_tag, tag.id
                            print("utils update tag image at create or categorize tags")
                            update_tag_image.delay(tag_name=tag_name, tag_id=tag_id)

                elif tag.exists():
                    # print('tag is present categorizing the tag',tag)
                    tag = Tags_lpig.objects.get(pk = tag[0].id)
                    print('tag is present categorizing the tag', tag)
                    if tag.attribute_id.id >=17 and tag.attribute_id.id <=20:
                        print("inside")
                        tag.category_id = category
                        tag.attribute_id = attribute
                        tag.updated_at = time.time()
                        tag.save()

                    if category.name == 'Geography' or attribute.id == 3:
                        if tag and not tag.image_link:
                            tag_name, tag_id = new_tag, tag.id
                            print("utils update tag image at create or categorize tags")
                            update_tag_image.delay(tag_name=tag_name, tag_id=tag_id)
                else:
                    tag = tag[0]

                    # tag is of category type geography update or create tag image
                    if category.name == 'Geography' or attribute.id == 3:
                        if tag and not tag.image_link:
                            tag_name, tag_id = new_tag, tag.id
                            print("utils update tag image at create or categorize tags")
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

        if tag.id == 15 or tag.id == 16 or tag.id == 17 or tag.id == 18 or tag.category_id == 6:
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

#
# def referal(ref_id, community_id, interested_member_id):
#
#
#     community = get_object_or_404(Community, pk=community_id)
#
#     # invited member and intrested member are same person
#     invited_member = User.objects.get(pk=interested_member_id)
#
#     interested_member = Members.objects.filter(community_id=community,
#                                                member_id=invited_member)
#     if not interested_member.exists():
#         if community.hide_community == '3':
#             interested_member = Members(community_id=community,
#                                         member_id=invited_member,
#                                         state=8)
#             interested_member.save()
#             update_member_count(community_id)
#             update_community_tags_to_user(community_id=community_id,user_id=invited_member.id)
#
#     referred_member = User.objects.get(pk=ref_id) if (ref_id != '' and ref_id) else False
#     if referred_member:
#
#         refer = Referal.objects.filter(member=referred_member,
#                                        invited_member=invited_member,
#                                        community=community)
#         if not refer.exists():
#             refer = Referal(member=referred_member
#                             , invited_member=invited_member
#                             , community=community)
#             refer.save()
#
#         joined_member_name, community_name = invited_member.userinfo.name, community.name
#
#         if community.hide_community == '3':
#
#             total_referals = Referal.objects.filter(member=referred_member,
#                                                     community=community)
#             if total_referals.count() < eligibility_count:
#
#                 notify_referred_member.delay(referred_member_id=ref_id,
#                                                 joined_member_name=joined_member_name,
#                                                 community_name=community.name,
#                                                 community_id=community_id)
#
#             if total_referals.count() >= eligibility_count:
#                 admin = Members.objects.filter(community_id=community, member_id=referred_member)
#
#                 if admin.exists():
#                     Members.objects.filter(community_id=community, member_id=referred_member).update(state=9)
#
#                 elif not admin.exists():
#                     admin = Members(community_id=community, member_id=referred_member, state=9)
#                     admin.save()
#
#                 community_name = community.name
#
#                 send_notification_to_eligible_member.delay(eligible_member_id= ref_id,
#                                                            community_name = community_name,
#                                                            community_id=community_id,
#
#                                                            )
#
#             # for interested_member in total_referals:
#             #     Members.objects.filter(community_id=community,
#             #                            member_id=interested_member.invited_member).update(state=3)
#     return

# 
# @shared_task
# def notify_referred_member(referred_member_id,joined_member_name,community_name,community_id):
# 
#     community = get_object_or_404(Community, pk=community_id)
# 
#     referal_count = get_referred_members_of_a_member(community_id=community_id,member_id=referred_member_id)
# 
#     referal_count = len(referal_count)
# 
#     if community.hide_community == '3':
#         print('send_notification_to_referred_member')
#         send_notification_to_referred_member(referred_member_id=referred_member_id,
#                                              joined_member_name=joined_member_name,
#                                              community_name=community_name,
#                                              community_id=community_id,
#                                              referal_count=referal_count,
#                                              )
# 
#     elif community.hide_community == '0' or community.hide_community == '4':
#         print('send_notification_to_referred_member_in_active community')
# 
#         print(">>>>>>>>>>> ", referred_member_id)
#         referals = get_referred_members_of_a_member(community_id=community_id, member_id=referred_member_id)
#         referal_count = len(referals)
#         print(referals)
#         count = 0
#         print("referal count === ", referal_count)
# 
#         for mem_id in referals:
#             member = Members.objects.filter(member_id=mem_id, community_id=community_id)
#             if member.exists():
# 
#                 if member[0].state == 4:
#                     count += 1
#         print('count ==== ',count)
#         if count < eligibility_count:
#             print('semnding notification')
#             send_notification_to_referred_member_in_active_community(referred_member_id=referred_member_id,
#                                                                      joined_member_name=joined_member_name,
#                                                                      community_name=community_name,
#                                                                      community_id=community_id,
#                                                                      referal_count=referal_count,
#                                                                      )


def get_referred_members_of_a_member(community_id,member_id):

    community = get_object_or_404(Community, pk=community_id)
    referred_member = User.objects.get(pk=member_id)

    member_list=[]
    total_referals = Referal.objects.filter(member=referred_member, community=community)

    if total_referals.exists():
        for interested_member in total_referals:
            mem_id=interested_member.invited_member.id
            member = Members.objects.filter(member_id=mem_id, community_id=community_id)
            if member.exists():
                if member[0].state == 4:
                    member_list.append(member[0].member_id.id)

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
            if tag and not tag.image_link:
                tag_id = tag.id
                update_tag_image.delay(tag_name=new_tag, tag_id=tag_id)
        else:
            #tag = Tags_lpig.objects.get(pk=tag)
            if tag.attribute_id.id == 12:
                print("creating new tag here")
                new_tag = tag.name.strip().title()
                tag = Tags_lpig()
                tag.name = new_tag
                tag.category_id = category
                tag.attribute_id = attribute
                tag.save()
                tag.tag_id = tag.id
                tag.created_at = time.time()
                tag.updated_at = time.time()
                tag.save()
                if tag and not tag.image_link:
                    tag_id = tag.id
                    update_tag_image.delay(tag_name=new_tag, tag_id=tag_id)

    else:
        # if tag is a string (which means its a new tag), create new tag
        tag = Tags_lpig()
        tag.name = new_tag
        tag.category_id = category
        tag.attribute_id = attribute
        tag.save()
        tag.tag_id = tag.id
        tag.created_at = time.time()
        tag.updated_at = time.time()
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
        if tag and not tag.image_link:
            tag_name, tag_id = new_tag, tag.id
            print("utils update tag image at create user hometown tags")
            update_tag_image.delay(tag_name=tag_name, tag_id=tag_id)
    # adding other related geography tags for the user such as state and country
    geography_list = get_city_address(city=new_tag)

    for attr, tag_name in geography_list.items():

        if tag_name == '':
            continue

        # creating or categorizing a tag with known category and attribute
        # geography tag is created, create its related tags
        # for example, if gurgaon is created, create Haryana and India as well as state and country
        tag = create_or_categorize_tag(tag=tag_name, category='Geography', attribute=attr)

        if attr == 'city':
            continue

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
        user_id, tag_id = tag.user_id.id, str(tag_id)
        insert_user_home_town_tags(user_id=user_id, tag=tag_id)



def user_onbaord(member_id):
    ''' checking if user has gone through on-boarding flow or not'''
    user_legacy = User_Legacy.objects.filter(user_id=member_id)
    user_prof = User_Profession.objects.filter(user_id=member_id)
    user_int = User_Interest.objects.filter(user_id=member_id)
    user_gro = User_Geography.objects.filter(user_id=member_id)

    # if user does not have any tags , user has to do on-boarding

    if user_legacy.exists() and user_prof.exists() and user_int.exists() and user_gro.exists():
        if (len(user_legacy) == 1 and user_legacy[0].tags_id.tag_id == 15) or (len(user_prof) == 1 and user_prof[0].tags_id.tag_id ==16) or (len(user_int) == 1 and user_int[0].tags_id.tag_id == 17) or (len(user_gro) == 1 and user_gro[0].tags_id.tag_id == 18):
            return False
        return True
    else:
        return False

def user_onbaord_new(user_instance):
    ''' checking if user has gone through on-boarding flow or not'''
    user_legacy = User_Legacy.objects.filter(user_id=user_instance).select_related('tags_id')
    user_profession = User_Profession.objects.filter(user_id=user_instance).select_related('tags_id')
    user_interest = User_Interest.objects.filter(user_id=user_instance).select_related('tags_id')
    user_geography = User_Geography.objects.filter(user_id=user_instance).select_related('tags_id')

    # if user does not have any tags , user has to do on-boarding

    first_condition = (user_legacy.exists() and user_geography.exists()) and (user_profession.exists() or user_interest.exists())

    second_condition = (legacy_exists(user_legacy) and geography_exists(user_geography)) and (interest_exists(user_interest) or profession_exists(user_profession))
    # print("first condition === ", first_condition)
    #
    # print("second_condition === ", second_condition)

    if first_condition:
        if second_condition:
            return True
        return False
    else:
        return False

def legacy_exists(user_legacy):

    condition = not (user_legacy.count() == 1 and user_legacy[0].tags_id.tag_id == 15)
    # print("legacy_exists === ",condition)
    return condition

def profession_exists(user_profession):
    condition = not (user_profession.count() == 1 and user_profession[0].tags_id.tag_id == 16)
    # print("profession_exists === ", condition)
    return condition

def interest_exists(user_interest):
    condition = not (user_interest.count() == 1 and user_interest[0].tags_id.tag_id == 17)
    # print("interest_exists === ", condition)
    return condition

def geography_exists(user_geography):
    condition = not (user_geography.count() == 1 and user_geography[0].tags_id.tag_id == 18)
    # print("geography_exists === ", condition)
    return condition


def update_community_tags_to_user(user_id,community_id):

    '''function to update the tags of the user if he joins a particular community'''

    user = User.objects.get(pk=user_id)
    community = Community.objects.get(pk=community_id)

    community_legacy_tags = Community_Legacy.objects.filter(community_id=community)

    for tag in community_legacy_tags:

        user_tag = User_Legacy.objects.filter(tags_id=tag.tags_id, user_id=user)
        if not user_tag.exists():
            user_tag = User_Legacy()
            user_tag.user_id = user
            user_tag.tags_id = tag.tags_id
            user_tag.save()

    community_profession_tags = Community_Profession.objects.filter(community_id=community)

    for tag in community_profession_tags:

        user_tag = User_Profession.objects.filter(tags_id=tag.tags_id, user_id=user)
        if not user_tag.exists():
            user_tag = User_Profession()
            user_tag.user_id = user
            user_tag.tags_id = tag.tags_id
            user_tag.save()

    community_interest_tags = Community_Interest.objects.filter(community_id=community)

    for tag in community_interest_tags:

        user_tag = User_Interest.objects.filter(tags_id=tag.tags_id, user_id=user)
        if not user_tag.exists():
            user_tag = User_Interest()
            user_tag.user_id = user
            user_tag.tags_id = tag.tags_id
            user_tag.save()

    community_geography_tags = Community_Geography.objects.filter(community_id=community)
    for tag in community_geography_tags:
        user_tag = User_Geography.objects.filter(tags_id=tag.tags_id, user_id=user)
        if not user_tag.exists():
            user_tag = User_Geography()
            user_tag.user_id = user
            user_tag.tags_id = tag.tags_id
            user_tag.save()

    return


# <<<< -------- Function to know device of user -------------------------- >>>>>
def is_request_android(request):

    '''function to check whether the user agent is android or not'''

    if 'HTTP_USER_AGENT' in request.META:
        ua_string = request.META['HTTP_USER_AGENT']
        user_agent = parse(ua_string)
        if user_agent.os.family == "Android" and not user_agent.is_pc:
            return True
        else:
            return False
    return False


def is_request_ios(request):

    '''function to check whether the user agent is android or not'''

    if 'HTTP_USER_AGENT' in request.META:
        ua_string = request.META['HTTP_USER_AGENT']
        user_agent = parse(ua_string)
        if user_agent.os.family == "iOS" and not user_agent.is_pc:
            return True
        else:
            return False
    return False

def is_request_pc(request):
    '''function to check if request is pc or not'''
    if 'HTTP_USER_AGENT' in request.META:
        ua_string = request.META['HTTP_USER_AGENT']
        user_agent = parse(ua_string)
        if user_agent.is_pc:
            return True
        else:
            return False
    return False



def is_IG_community(community):

    '''function to check if the community is IG community or not'''

    communities_interest=Community_Interest.objects.filter(community_id=community)

    for interest in communities_interest:
        tag_id=interest.tags_id.id
        if tag_id != 17:
            return True

    return False


def is_LG_or_LP_community(community):

    '''function to check if the community is LG community or not and excluding hometown communities'''

    communities_legacy=Community_Legacy.objects.filter(community_id=community)

    is_hometown=is_legacy_home_town(communities_legacy)

    if not is_hometown:

        for legacy in communities_legacy:
            tag_id = legacy.tags_id.id
            if tag_id != 15:
                return True

        return False
    return False

def is_legacy_home_town(communities_legacy):

    '''function to check whether the community is legacy hometown or not'''

    for legacy in communities_legacy:
        attribute_id=legacy.tags_id.attribute_id.id
        if attribute_id == 3 or attribute_id == 13 or attribute_id == 14 :
            return True
    return False


def get_user_communities_by_rank_web(request):
    ''' function to get communities based on rank '''
    communities_list = []
    communities = Community_Rank.objects.filter(member_id=request.user).order_by('-weight').values_list('community_id',
                                                                                                        flat=True).distinct()
    for community in communities:
        comm = Community.objects.get(pk=community)
        # check if community is hidden or not
        if comm.hide_community == '0' or comm.hide_community == '3' or comm.hide_community == '4':
            communities_list.append(comm)
    return communities_list

def get_user_email(member_id):
    member = User.objects.get(pk=member_id)
    if member.userinfo.email:
        return member.userinfo.email
    else:
        emails = userEmails.objects.filter(user_id=member_id)
        if emails.exists():
            if emails.first().email != "":
                return emails.first().email
        else:
            return None
    
def check_notification_flag(member_id,notification_list,card_id=None,community_id=None):

    ''' 
    functiont check if we can send notitfications to users 
    send member_id, card id for card specific flags, 
    send member_id, community id for community specific flags
    send member_id for member specific flags
    '''

    member = User.objects.get(pk=member_id)
    flag = True

    for notification in notification_list:
        if card_id == None and community_id == None:
            p, created = memberNotificationFlag.objects.get_or_create(code=notification,member=member)

        elif card_id != None and community_id == None:
            card = Collabcard.objects.get(pk=card_id)
            p, created = memberNotificationFlag.objects.get_or_create(code=notification,card=card,member=member)

        elif community_id != None and card_id == None:
            community = Community.objects.get(pk=card_id)
            p, created = memberNotificationFlag.objects.get_or_create(code=notification,community=community,member=member)
        
        if p.flag == False:
            flag = False
            break

    return flag


def create_notification_flag(member_id, notification_list, card_id=None, community_id=None, flag=None):
    '''
    function to add notification flag
    '''

    member = User.objects.get(pk=member_id)

    for notification in notification_list:
        if card_id == None and community_id == None:
            p, created = memberNotificationFlag.objects.get_or_create(code=notification, member=member,flag=flag)

        elif card_id != None and community_id == None:
            card = Collabcard.objects.get(pk=card_id)
            p, created = memberNotificationFlag.objects.get_or_create(code=notification, card=card, member=member,flag=flag)

        elif community_id != None and card_id == None:
            community = Community.objects.get(pk=card_id)
            p, created = memberNotificationFlag.objects.get_or_create(code=notification, community=community,
                                                                      member=member,flag=flag)


def add_relative_time_to_epoch(epoch_time, minutes=0, hours=0, days=0):
    epoch_time = datetime.fromtimestamp(epoch_time)
    epoch_time = epoch_time + timedelta(hours=hours,minutes=minutes,days=days)
    epoch_time = epoch_time.timestamp()
    return epoch_time

def get_next_day_time(epoch_time,minutes=0,hours=0):
    epoch_time = datetime.fromtimestamp(epoch_time + (24 * 60 * 60))
    epoch_time = epoch_time.replace(hour=hours,minute=minutes)
    epoch_time = epoch_time.timestamp()
    return epoch_time
