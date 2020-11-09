from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from togther.models import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from togther.forms import *
import requests as rqst
from django.contrib.auth.models import User
import json
from django.db.models import Q
from django.http.response import JsonResponse
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from .tasks import send_mail_after_rank_computation, send_email_to_proposed_admin
from django.core.mail import EmailMultiAlternatives
from collabmates_api.serializers import *
from collabmates_api.views import *
from collabmates_api.static_files import *
import traceback
from collabmates_api.raw_queries import compute_rank
# from collabmates_api.notification import notification_after_compute_rank
from utility.utils import (get_city_address, update_tag_image,
                           update_user_geography_tags, create_or_categorize_tag,
                           insert_user_home_town_tags, user_onbaord,
                           is_request_android, is_request_ios,
                           is_request_pc, android_app_download_link,
                           is_IG_community, ios_app_download_link,is_member_verified,
                           feedback_community_id,decode_option,get_members_count_in_community,
                           )
from utility.encryption import encrypt,decrypt
from utility.firebase import upload_image_to_firebase
from urllib.parse import urlencode, quote,unquote
from collabmates_api.tasks import send_email
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from user_agents import parse
import time
import logging
from utility.states import collabcard_states, member_states, question_states
import ast
from django.contrib.auth import login


url = settings.URL

if not url and settings.IS_BETA:
    url = "https://beta.likeminds.community"

if not url and not settings.IS_BETA:
    url = "https://www.likeminds.community"

# uncomment to run it in localhost
#
#url='http://localhost:8000'

api_url = url + '/api/'
error_logger = logging.getLogger("error_logger")
info_logger = logging.getLogger("info_logger")


def index(request):
    '''function to show promotion page'''

    themeFromURL = request.GET.get('theme', 'light')
    context = {
        'theme': themeFromURL # 'dark', 'gradient'
    }
    return render(request, 'home_landing.html', context)


    # user_agent = parse(request.META['HTTP_USER_AGENT'])
    # os_type = user_agent.os.family

    # if os_type == "Android":
    #     return render(request, 'mobile.html', {'is_beta': settings.IS_BETA})
    # elif os_type == "iOS":
    #     return render(request, 'mobile.html', {'is_beta': settings.IS_BETA})
    # else:
    #     return render(request, 'index.html', {'is_beta': settings.IS_BETA})


def download_the_app(request):
    '''function to download the app'''

    user_agent = parse(request.META['HTTP_USER_AGENT'])
    os_type = user_agent.os.family
    log = """download is clicked for os=%s""" % (str(os_type))
    info_logger.info(log)
    if os_type == "Android":
        return redirect(android_app_download_link)
    elif os_type == "iOS":
        return redirect(ios_app_download_link)
    else:
        return redirect(android_app_download_link)


# def home(request):
#     # users = User.objects.all()
#     if request.user.is_authenticated:
#         return redirect('dashboard')
#     else:
#         return render(request, 'home.html', {})


def signup(request):
    # users = User.objects.all()
    if request.user.is_authenticated:
        try:
            # check if user has user info
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            # if there is no user info for the user who is currently logged in
            # create userinfo for current user
            user = update_user_info(request)

        return redirect('dashboard')
    else:
        return render(request, 'signup.html', {})


def dashboard(request):
    ''' function to show all communities and filter based on categories '''

    if request.user.is_authenticated:

        # if user does not have a email linked to his account, ask for a email
        request_user_email = False
        if not request.user.email and request.user.id != 37 and request.user.id != 176:
            request_user_email = True

        try:
            # check if user has user info
            user = Userinfo.objects.get(user_id=request.user.id)

        except:
            # if there is no user info for the user who is currently logged in
            # create userinfo for current user
            user = update_user_info(request)
        # get users communities
        my_community = get_user_communities(request)
        # getting communities by user hidden tag
        communities = get_communities_by_rank(request)

        # check if user has completed onbarding and is from IIT Delhi
        onboard = user_onbaord(request.user.id)
        return render(request, 'dashboard.html',
                      {'usr': user, 'communities': communities, 'my_communities': my_community[:2],
                       "my_communities_count": len(my_community), 'onboard': onboard, 'is_iitd': True,
                       'request_user_email': request_user_email})

    page = request.GET.get('page', 1)
    communities = Community.objects.filter(Q(hide_community='0') | Q(hide_community='4')).order_by('-updated_at')
    paginator = Paginator(communities, 20)
    queryset = paginator.get_page(page)

    for community in queryset:
        update_member_count(community.id)

    return render(request, 'dashboard.html', {'communities': queryset})


def get_communities_by_rank(request):
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


def get_communities_by_tags(user_tag=0, category_tag=0):
    ''' fetching communities based on category tag and user hidden tag '''
    if category_tag != 0 and user_tag != 0:
        ''' if category tag and user tag ,bith are provided
            get communities ,which are the intersection of given category and user hidden tag '''

        # get communities based on category tag
        category_tag = Community_tags.objects.filter(tags_id=category_tag).values('community_id')
        # get communities based on user hidden tag
        user_tag = Community_tags.objects.filter(tags_id=user_tag).values('community_id')
        # intersect both of the querysets
        res = category_tag.intersection(user_tag).order_by("-community_id").distinct()
        # return result
        return res

    if category_tag == 0 and user_tag == 0:
        # if there is not category tag and user does not have a hidden tag too
        # just return him all the communites
        community = Community_tags.objects.values('community_id').order_by("-community_id").distinct()

        return community

    if category_tag == 0 and user_tag != 0:
        # if there is no category tag , then return communites based on user hidden tag
        user_tag = Community_tags.objects.filter(tags_id=user_tag).values('community_id').order_by(
            "-community_id").distinct()
        return user_tag

    if user_tag == 0 and category_tag != 0:
        # if there is no user hidden tag , then return communites based on category tag
        category_tag = Community_tags.objects.filter(tags_id=category_tag).values('community_id').order_by(
            "-community_id").distinct()

        return category_tag


def get_user_communities(request):
    ''' function to get users communities '''
    communities1 = Members.objects.all().filter(member_id=request.user).filter(
        Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7))

    my_communities = []
    for j in communities1:
        my_communities.append(j.community_id)
    my_community = []
    for j in my_communities:
        my_community.append(j)

    return my_community


def community(request, community_id):


    aj = request.GET.get('aj', False)
    #auto join check functionality

    ios_private_link = ""

    source = request.GET.get('source')
    if aj and is_request_android(request) and not source:

        private_link = "https://" + request.META['HTTP_HOST'] +"/community/"+str(community_id)+"?aj="+str(aj)
        playstore_ref_link = android_app_download_link+"""&referrer=%s"""%(quote(private_link))
        return redirect(playstore_ref_link)

    if aj and is_request_ios(request) and not source:

        ios_deep_link = "Collabmates://" + request.META['HTTP_HOST'] +"/community/"+str(community_id)+"?aj="+str(aj)
        ios_branch_link="""https://collabmates.app.link/q9PKG0YPR8?$deep_link=%s"""%(quote(ios_deep_link))
        print(ios_branch_link)


        return redirect(ios_branch_link)


    # print(aj)
    # print(source)
    #profile = request.GET.get('profile')

    profile_list = []

    #flow for saving the community questions
    state = 0
    user_instance = None
    is_member = False
    mixpanel_event = ""
    user_context = {}
    user_context['current_user_request_date'] = 0
    if request.user.is_authenticated:
        state_data = members_state(request,{'community_id':community_id,'member_id':request.user.id})
        state = state_data['state']
        user_context['current_user_request_date']= state_data['created_at']
        user_instance = request.user
        # if profile:
        #     profile_list = get_member_profile(community_id,user_instance.id)
        is_member = is_member_verified(community_id,request.user)

        mixpanel_event = get_mixpanel_statistics(user_instance.id)

    if state == 0:

        if aj and source:
            params = str(community_id)+"-"+str(aj)+"-"+str(source)

        elif aj:
            params = str(community_id) + "-" + str(aj) + "-private_link"
        else:
            params = community_id
        return redirect('community_questions',params=params)

    community_instance = Community.objects.get(id=community_id)

    context = get_community_context(request,community_instance,user_instance,state,profile_list,is_member,user_context)

    context['ios_private_link'] = ios_private_link

    if mixpanel_event:
        context['mixpanel_event'] = mixpanel_event

    return render(request,'community.html',context)






def community_questions(request,params):


    '''function to get community questions'''


    # if is_request_ios(request):
    #     return redirect("https://apps.apple.com/us/app/likeminds-community-chat/id1526635028?mt=8")



    url_details = {}
    user_directory = False
    chatroom_deleted = None
    if params.find("-") == -1:
        community_id = params
    else:
        params = params.split("-")

        if len(params) == 3:
            community_id = params[0]
            user_directory = True
            url_details['community_id'] = params[0]
            url_details['aj'] = params[1]
            url_details['source'] = params[2]
        elif len(params) == 2:                  #deleted card
            community_id = params[0]
            chatroom_deleted = params[1]
        else:
            return HttpResponse("invalid url")



    question_format = get_community_questions(community_id)
    community_instance = Community.objects.get(id=community_id)
    admin = get_community_creator(community_instance)



    user_instance = None
    state = 0
    analytics = {}
    mixpanel_event = ""
    if request.user.is_authenticated:
        user_instance = request.user
        state = members_state(request,req_dict={'community_id':community_id,'member_id':user_instance.id})

        if state['state'] != 0:
            return redirect('community',community_id=community_id)

        analytics = get_community_join_analytics(user_instance)

        mixpanel_event = get_mixpanel_statistics(user_instance.id)





    if request.method == "GET":
        header = {
            'back': True,
            'title': 'Welcome to LikeMinds!',
            'subTitle': False,
            'background': '_',
            'color': 'F'
        }
        header_showcase = {
            # 'image': 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fmain_website%2Fresponse_header?alt=media',
            'image': 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fmain_website%2Fapp_bar_status_bar.png?alt=media',
            'header': 'You are interested in joining this community:',
            'subHeader': community_instance.name,
            'userImage': request.user.userinfo.image_link if user_instance else PROFILE_DEFAULT
        }


        context = {
                    "data": question_format, 'usr': user_instance, 'header': header,
                    'community': community_instance,
                    'header_showcase': header_showcase,
                    'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                    'facebook_auth_id': settings.SOCIAL_AUTH_FACEBOOK_KEY,
                    'firebase_config': settings.FIREBASE_CONFIG,
                     'user_directory': user_directory,
                     'analytics':analytics

                   }

        members_count = get_members_count_in_community(community_instance)
        context['header_showcase']['subHeader'] = ""
        context['header_showcase']['header'] = admin + " invited you to join this community"
        context['header_showcase']['communityBlock'] = {
            'title': community_instance.name,
            'creator': "Created by " + admin,
            'members':  str(members_count) + " members",
            'imgURL': community_instance.image_link
        }
        if user_directory:
            footer = private_link_app_invite(community_instance, url_details['aj'], admin)
            footer['aj']=url_details['aj']
            context['footer'] = footer

            context['source'] = url_details['source']

            if context['source'] == "private_link":
                ios_private_link = "Collabmates://" + request.META['HTTP_HOST'] + "/community/" + str(
                    community_id) + "?aj=" + str(url_details['aj'])

                context['ios_private_link'] = ios_private_link


        if chatroom_deleted:

            footer = {
                'toast':"Oops Your chatroom is deleted. Don't worry you can still view and participate in other chatrooms after joining the community"
                      }
            context['footer'] = footer



        if mixpanel_event:
            context['mixpanel_event'] = mixpanel_event
        # print(context,"***")

        return render(request, 'response_form.html', context)
    else:
        question_data = request.POST.dict().get("data")
        aj = request.POST.get('aj')
        aj_expired = request.POST.get('aj_expired')
        source = request.POST.get('source')
        #print("source---",source)
        question_data = ast.literal_eval(question_data)
        response_list = []

        for quest_dict in question_data:

            question_dict = {}
            if quest_dict['id'] == 'csrfmiddlewaretoken':
                continue
            elif quest_dict['id'] == 'ref_id':
                continue

            question_dict['id'] = quest_dict['id']
            question_dict['value'] = quest_dict['value']

            response_list.append(question_dict)

        json_dict = {"community_id": community_id, "timestamp": time.time()}
        json_dict['questions'] = response_list
        json_dict['user_id'] = request.user.id

        if state['state'] == 0:
            join_url = api_url + 'v1/join_community'

            params = {'member_id': user_instance.id, 'community_id': community_id}
            if  aj_expired == 'False':
                json_dict['aj'] = int(aj)

            # print("params---",params)
            # print("json dict---",json_dict)

            rqst.post(join_url, params=params, json=json_dict)

        if aj_expired == "" or aj_expired == "True":
            return JsonResponse({'success':True, 'aj_expired':aj_expired})
        elif source == "private_link":
            return JsonResponse({'success': True, 'source': "private_link",'aj_expired':aj_expired})
        else:
            return JsonResponse({'success':True,'source':"members_directory",'aj_expired':aj_expired})



def get_community_context(request,community_instance,user_instance,state,profile_list,is_member,user_context):

    admin_details = get_admins_details(community_instance)

    if community_instance.id == feedback_community_id:
        members = []
    else:
        members = get_member_details(community_instance)

    header = {
        'back': True,
        'title': False,
        'subTitle': False,
        'background': 'Fo05',
        'color': '0'
    }
    header_showcase = {
        'image': community_instance.image_link if community_instance.image_link else community_instance.image_url,
        'header': community_instance.name,
        'subHeader': str(len(members)) + ' Members' if len(members) else ''
    }

    # sending links and context
    android_app_link = ""
    ios_app_download_link = ""
    if is_request_android(request):
        android_app_link = android_app_download_link
    if is_request_ios(request):
        ios_app_download_link = ios_app_download_link

    about_1 = ""
    about_2 = ""
    if community_instance.about:
        about = community_instance.about
        about_1 = about[0:180]
        about_2 = about[180:]


    context = {'usr': user_instance,
               'community': community_instance, 'admins': admin_details,
               'header': header, 'header_showcase': header_showcase,
               'members': members,
               'Nom_mem_state': state,
               'admin_length': len(admin_details),
               'members_length': len(members),
               'android_app_link': android_app_link,
               'share_text': """I recently joined %s community on LikeMinds. It will be fun if you also join this community""" % (
                   community_instance.name),

               'share_url': str(settings.URL) + '/community/' + str(community_instance.id),
               'ios_app_download_link': ios_app_download_link,
               'about_1': about_1,
               'about_2': about_2,

               'community_state': int(community_instance.hide_community),
               'profile_list': profile_list,
               'is_member': is_member,
               'community_id': community_instance.id,
               'user_email': request.user.userinfo.email if request.user.is_authenticated else '',
               'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
               'facebook_auth_id': settings.SOCIAL_AUTH_FACEBOOK_KEY,
               'firebase_config': settings.FIREBASE_CONFIG,
               'current_user_request_date':  user_context['current_user_request_date']
               }

    if state == member_states.PENDING_MEMBER:
        context['footer'] = {
            'toast':"Your request to join the community is pending."
        }





    return context



def get_join_community_context(request, ref_id, aj, validation_error, user, data, community, filled_answers, auto_join):
    aj = request.GET.get('aj')
    header = {
        'back': True,
        'title': 'Welcome to LikeMinds!',
        'subTitle': False,
        'background': '_',
        'color': 'F'
    }
    header_showcase = {
        'image': 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fmain_website%2Fresponse_header?alt=media',
        'header': 'You are interested in joining this community:',
        'subHeader': community.name,
        'userImage': request.user.userinfo.image_link if request.user.is_authenticated else 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fuser%2F222%2Fimg_user_222?alt=media'
    }

    context = {"data": data, 'usr': user, 'header': header,
               'community': community, 'ref_id': ref_id,
               'validation_error': validation_error,
               'filled_answers': filled_answers,
               'aj': aj, 'header_showcase': header_showcase}
    if aj:
        context['auto_join'] = auto_join

    return context


def get_community_join_analytics(user_instance):

    analytics = {}
    community_list = []
    promoter_count = Members.objects.filter(member_id=user_instance.id, state=member_states.ADMIN).count()

    member_filter = Members.objects.filter(member_id=user_instance.id).filter(
        Q(state=member_states.MEMBER) | Q(state=member_states.KNOWN_NOMINATED_PROMOTER))
    community_member_count = member_filter.count()
    for member in member_filter:

        community_list.append(member.community_id.name)

    analytics['community_list'] = community_list
    analytics['community_member_count'] = community_member_count
    analytics['other_community_promoter'] = True if promoter_count > 1 else False

    return analytics





def refer_members(request, community_id):
    if request.user.is_authenticated:

        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

        if request.method == 'GET':

            share_url = url + '/community/' + str(community_id) + "?ref_id=" + str(request.user.id)
            # decoded url for mobile web sharing
            copy_url = share_url
            # encoded url for web sharing
            share_url = quote(share_url)

            community = Community.objects.get(pk=community_id)

            member = Members.objects.filter(community_id=community, member_id=request.user)
            admins = Members.objects.filter(community_id=community).filter(Q(state=1) | Q(state=2)).order_by('id')

            share_text = 'Hi, I have added ' + str(
                community.name) + ' community on LikeMinds. It will be good if you can join this community'

            android = is_request_android(request)
            ios = False
            if is_request_ios(request):
                ios = True
            pc = is_request_pc(request)
            # print(request.META)
            # if admins.exists() and request.user.id == admins[0].member_id.id:
            #     share_text = """Hi, I have initiated %s community on CollabMates. It will be good if you can join this community.\n""" % (community.name)
            #
            # elif member.exists() and member[0].state == 1 or member[0].state == 2 or member[0].state == 4 or member[0].state == 7 :
            #     share_text = """I recently joined %s community on CollabMates. It will be good if you also join this community.\n""" % (community.name)
            #
            # elif member.exists() and member[0].state == 8 or member[0].state == 9 :
            #     share_text = """I recently discovered %s community on CollabMates. You can join this community using this link.\n""" % (community.name)

            # elif member.exists() and member[0].state == 0 :
            #     share_text = 'Hi, I have added '+ str(community.name) +' community on CollabMates. It will be good if you can join this community'
            #
            # elif not member.exists():
            #     share_text = 'Hi, I have added '+ str(community.name) +' community on CollabMates. It will be good if you can join this community'

            form_responses = communityAnswers.objects.filter(community=community_id, member=request.user.id).order_by(
                'id')
            form_answers_list = []

            is_introduction = False

            for form in form_responses:

                temp = {}

                if not is_introduction:
                    temp['is_introduction'] = True
                    temp['answer'] = form.question_answer
                    is_introduction = True
                else:
                    temp['is_introduction'] = False
                    temp['answer'] = form.question_title + " : " + form.question_answer

                form_answers_list.append(temp)

            context = {'share_url': share_url,
                       'community': community,
                       'copy_url': copy_url,
                       'share_text': share_text,
                       'android': android,
                       'ios': ios,
                       'community_id': community_id,
                       'pc': pc,
                       'android_app_download_link': android_app_download_link,
                       'ios_app_download_link': ios_app_download_link,
                       'form_answer_list': form_answers_list,
                       'form_answers_list_length': len(form_answers_list)
                       }

            return render(request, 'referal.html', context)
        else:
            mobile_no_ios = request.POST.get('mobile_no_ios', None)
            if mobile_no_ios:
                user.contact_number = mobile_no_ios
                user.save()
                return JsonResponse({'success': True})

            user_id = request.user.id
            mobile_os = request.POST.get('mobile_os')
            email = request.POST.get('email')
            mobile_no = request.POST.get('mobile_no')
            try:
                user_info = Userinfo.objects.get(user_id=user_id)
                user_info.mobile_os = mobile_os
                user_info.secondary_email = email
                if mobile_no:
                    user_info.contact_number = mobile_no
                else:
                    user_info.contact_number = None
                user_info.save()
            except:
                print("Error in user info")

            return JsonResponse({'success': True})


def get_admins_details(community):
    '''function to get details of admins'''

    admin_list = Members.objects.filter(community_id=community.id).filter(Q(state=1) | Q(state=2))
    admins = []
    for admin in admin_list:
        temp = {}
        temp['name'] = admin.member_id.userinfo.name
        temp['image_link'] = admin.member_id.userinfo.image_link
        form_response = communityAnswers.objects.filter(member=admin.member_id, community=community).order_by('id')
        if form_response:
            answer = form_response[0].question_answer
            if "$#" in answer:
                answer = answer.replace("$#",",")
            temp['introduction_answer'] = answer

        admins.append(temp)

    return admins


def get_member_details(community, *args):
    '''function to get member details of community'''

    members = []
    # member_list = Members.objects.filter(community_id=community).filer(state=1) | Q(state=2) | Q(state=4))
    
    # tweaking func args to get other states as well
    getMemberStates = [1, 2, 4,9] # default states
    for state in args:
        getMemberStates.append(state)

    member_list = Members.objects.filter(community_id=community).filter(state__in = getMemberStates)
    
    for member in member_list:
        temp = {}
        temp['id'] = member.member_id.id
        temp['name'] = member.member_id.userinfo.name
        temp['image_link'] = member.member_id.userinfo.image_link
        temp['state'] = member.state
        answer = get_introduction_answer(community, member)
        temp['answer'] = answer
        members.append(temp)

    return members




def get_filtered_members(community,filter_list):


    '''function to get filteres members'''

    members=[]
    if not filter_list:
        return []

    for member_id in filter_list:
        if not member_id:
            continue
        member = Members.objects.filter(community_id=community, member_id=member_id)
        if member.exists():
            temp = {}
            temp['id'] = member[0].member_id.id
            temp['name'] = member[0].member_id.userinfo.name
            temp['image_link'] = member[0].member_id.userinfo.image_link
            temp['state'] = member[0].state
            answer = get_introduction_answer(community, member[0])
            temp['answer'] = answer
            members.append(temp)
    return members


def get_members_of_community(request, community):
    ''' function to get admins and members of a community '''

    members = []
    admin_details = []
    all_members = []
    if community.hide_community == '0' or community.hide_community == '1' or community.hide_community == '4':
        all_members = Members.objects.filter(community_id=community.id).filter(
            Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7))

    elif community.hide_community == '3':
        all_members = Members.objects.filter(community_id=community.id).filter(Q(state=8))

    for member in all_members:
        mem = Userinfo.objects.filter(user_id=member.member_id.id)
        if not mem.exists():
            user = update_user_info(request=request, member_id=member.member_id.id)
            print('user ---- ', user)
            # if user.status_code == 200:
            #     user = json.loads(user.content.decode('utf-8'))
            #     print('user ===== ', user)
            mem = Userinfo.objects.filter(user_id=user.user_id.id)

        if member.state == 1 or member.state == 2:
            admin_details.append(mem)
            members.append(mem[0])
        elif member.state == 4 or member.state == 7 or member.state == 8:
            members.append(mem[0])

    return members, admin_details


def get_introduction_answer(community_instance, member_instance):
    '''function to get introduction answer'''
    introduction_answer = ""
    check_intro = communityQuestions.objects.filter(community=community_instance,
                                                    question_state=question_states.INTRODUCTION)
    if check_intro:

        question_id = check_intro[0].id
        introduction_answer_list = communityAnswers.objects.filter(community=community_instance,
                                                                   member=member_instance.member_id,
                                                                   question_id=question_id)
        if introduction_answer_list.exists():
            introduction_answer = introduction_answer_list[0].question_answer
            return introduction_answer

    if not introduction_answer:
        epoch_time = member_instance.created_at
        if epoch_time < 0:
            return ""
        else:
            time_string = "Member since "
            time_string = time_string + time.strftime("%d %b %Y", time.localtime(epoch_time))
            return time_string
    return ""


def members_directory(request, community_id):

    '''function to see members directory'''

    is_member = False
    user_email = ""
    member_state = 0
    mixpanel_event = {}
    if request.user.is_authenticated:

        temp = members_state(request,req_dict={'member_id':request.user.id,'community_id':community_id})
        member_state = temp['state']
        if member_state == member_states.ADMIN or member_state == member_states.MEMBER:
            is_member = True

        community_instance = Community.objects.get(id=community_id)
        user_instance = User.objects.get(id=request.user.id)

        mixpanel_event = get_mixpanel_statistics(user_instance.id)


        user_email = request.user.userinfo.email

    if request.method == 'POST':

        option_data = request.POST.get('data')
        option_data = json.loads(option_data)
        question_id = request.POST.get('question_id')

        member_ids = request.POST.get('member_ids')
        question_ids = request.POST.get('question_ids')
        options = request.POST.get('options')


        member_set = set()

        question_set = set()
        option_set = set()

        questions=[]
        dropdowns=[]

        is_selected = False

        if member_ids:
            member_list = member_ids.split("$")
            for member in member_list:
                if member:
                    if member not in member_set:
                        member_set.add(member)

        if question_ids:
            is_selected = True
            question_list = question_ids.split("$")
            for question in question_list:

                if question not in question_set:
                    questions.append(question)
                    question_set.add(question)

        if question_id not in question_set:
            question_set.add(question_id)
            questions.append(question_id)

        if options:
            option_list = options.split("$")
            for option in option_list:
                if option not in option_set:
                    dropdowns.append(option)
                    option_set.add(option)

        for option in option_data:
            if option not in option_set:
                dropdowns.append(option)
                option_set.add(option)


        # print("member_set---",member_set)
        # print("question_list--",questions)
        # print("dropdowns--",dropdowns)

        filtered_members = get_member_string_for_filters(option_data,question_id)
        if not is_selected:                     #if the first request is comming
            member_string=filtered_members[0]
        else:
            filtered_member_list = filtered_members[1]
            member_string = ""

            for member in filtered_member_list:
                if member in member_set:
                    member_string = member_string+"$"+ member

        if member_string == "$":
            member_string = ""
        
        context = {'members': member_string,'filter':questions,'option_data':dropdowns,
                   'mixpanel_event':mixpanel_event
}
        return JsonResponse(context)

    community_instance = Community.objects.get(pk=community_id)
    filter_list = communityQuestions.objects.filter(community=community_instance).filter(
        Q(question_state=question_states.CHOICE_SINGLE) | Q(question_state=question_states.CHOICE_MULTIPLE))

    # for filter processing
    member_string = request.GET.get('members',None)

    selected_options = request.GET.get('filter', None)
    selected_filters=[]
    if selected_options:
        selected_filters = selected_options.split(",")



    selected_list = request.GET.get('option_data',None)
    if selected_list:
        selected_list = selected_list.split(",")




    # print("member_string",member_string)
    # print("selected filters",selected_filters)
    # print("selected list",selected_list)

    selected = False                #boolean to show clear button
    filters = []



    for filter in filter_list:
        temp = {}
        response_list = get_user_selected_option_list(filter.id,selected_list=selected_list)
        if not response_list:
            continue
        temp['question_id'] = filter.id
        temp['question_title'] = filter.question_title
        temp['values'] = response_list
        if str(filter.id) in selected_filters:
            selected = True
            temp['selected'] = True
        else:
            temp['selected'] = False
        filters.append(temp)

    if member_string == None:
        members = get_member_details(community_instance, 3) # passing 3 for getting unverified members
    else:
        member_split = member_string.split("$")
        members = get_filtered_members(community_instance,member_split)
    header = {
        'back': True,
        'title': 'Members',
        'subTitle': community_instance.name,
        'background': 'Wa',
        'color': 'F'
    }

    context = {
        'members': members,
        'members_length': len(members),
        'community_name': community_instance.name,
        'community_id': community_instance.id,
        'is_member':is_member,
        'header': header,
        'user_email': user_email,
        'filter_list':filters,
        'member_state':member_state,
        'selected':selected,
        'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'facebook_auth_id':settings.SOCIAL_AUTH_FACEBOOK_KEY,
        'firebase_config': settings.FIREBASE_CONFIG,
        'mixpanel_event':mixpanel_event

    }

    return render(request, 'members.html', context)



# def decode_option(value):
#
#
#
#     value = ast.literal_eval(value)
#     value_list = []
#
#     for item in value:
#         value_list.append(item['value'])
#
#     #print(value_list)
#
#     return value_list


def get_user_selected_option_list(question_id,selected_list=None):

    '''function to get user selected options'''
    filter_list = list(questionFilters.objects.filter(question=question_id).values_list('filter',flat=True).distinct())
    response_list = []
    for option in filter_list:
        temp={}
        temp['option'] = option
        if selected_list and option in selected_list:
            temp['is_selected'] = True
        else:
            temp['is_selected'] = False

        response_list.append(temp)
    return response_list


def get_member_string_for_filters(option_data,question_id):

    '''function to get member string for  filters'''

    member_set = set()

    member_string = ""
    filter_member_list = []
    for option in option_data:
        question_list = questionFilters.objects.filter(filter=option, question=question_id)

        for member_instance in question_list:
            member_id = str(member_instance.member.id)
            if member_id not in member_set:
                member_string = member_string + "$" + member_id
                member_set.add(member_id)
                filter_member_list.append(member_id)
    return member_string,filter_member_list



def member_profile(request):

    '''function to show member profile'''

    member_id = request.POST.get('data')
    community_id = request.POST.get('community_id')
    member_name=""

    user_instance=User.objects.filter(id=member_id)
    image_link=""

    is_promoter=False
    status = None
    if user_instance.exists():
        member_name = user_instance[0].userinfo.name
        image_link = user_instance[0].userinfo.image_link

        # is_promoter = Members.objects.filter(community_id=community_id, member_id=request.user.id).filter(
        #               state = member_states.ADMIN)
        #
        # is_promoter=is_promoter.exists()
        #

        status = members_state(request,{'community_id':community_id,'member_id':request.user.id})

        if status['state'] == 1:
            is_promoter = True

    if not is_promoter and str(request.user.id) == str(member_id):
        is_promoter = True

    answer_list = get_member_profile(community_id,member_id,is_promoter=is_promoter)

    json_response = {

        'answer_list':answer_list,
        'member_name':member_name,
        'image_link':image_link,
        'member_state': get_member_community_status(status['state']) if status else 0,
        'member_id': request.user.id

        }

    return JsonResponse(json_response)


def update_email(request):

    '''function to update email'''

    email = request.POST.get('email',None)
    if request.user.is_authenticated:
        if email:
            Userinfo.objects.filter(user_id=request.user).update(secondary_email=email)

        return JsonResponse({'success':True})
    return JsonResponse({'success':False})


def get_member_profile(community_id,member_id,is_promoter=False):

    '''function to get member profile'''
    user_answers = communityAnswers.objects.filter(community=community_id, member_id=member_id).order_by('id')
    answer_list = []

    email = ""
    mobile_no = ""
    profile_link = ""

    for answer in user_answers:
        temp = {}
        question_instance = communityQuestions.objects.get(pk=answer.question_id)
        # introduction answer
        if question_instance.question_state == question_states.INTRODUCTION:
            # introduction
            temp['answer'] = answer.question_answer
            temp['rank'] = 4

        elif question_instance.question_state == question_states.EMAIL_ID:
            # email id
            email =  answer.question_answer
            temp['answer_privacy']=answer_privacy(question_instance.value,is_promoter=is_promoter)
            #print(temp['answer_privacy'])
            temp['answer'] = email
            temp['rank'] = 1

        elif question_instance.question_state == question_states.MOBILE_NO:
            # mobile number
            mobile_no = answer.question_answer
            temp['answer_privacy']=answer_privacy(question_instance.value,is_promoter=is_promoter)
            #print(temp['answer_privacy'])
            temp['answer'] = mobile_no
            temp['rank'] = 2

        elif question_instance.question_state == question_states.PROFILE_LINK:
            # profile link
            profile_link = answer.question_answer
            temp['answer_privacy']=answer_privacy(question_instance.value,is_promoter=is_promoter)
            #print(temp['answer_privacy'])
            temp['profile_link'] = profile_link
            temp['answer'] = "Profile link"
            temp['rank'] = 3

        elif question_instance.question_state == question_states.FILE_UPLOAD:
            # question answer
            file_link = answer.question_answer
            temp['file_link'] = file_link
            temp['answer'] = question_instance.question_title + ": " "File Link"
            temp['rank'] = 5
        else:
            response = answer.question_answer
            if "$#" in response:
                response = response.replace("$#",",")
            temp['answer'] = question_instance.question_title + ": " + response
            temp['rank'] = 6
        answer_list.append(temp)
        answer_list = sorted(answer_list, key=lambda i: i['rank'])
        #print(answer_list)
    return answer_list

def answer_privacy(answer,is_promoter=False):

    '''function to check the privacy of answer'''
    if not answer:
        return True
    if is_promoter:
        return True

    value_list = ast.literal_eval(answer)
    privacy = ""
    for value in value_list:
        privacy = value['answer_privacy']

    if privacy == "Public":
        return True
    return False



@login_required
def update_user_info(request, member_id=None, user_email=None):
    if member_id:
        user_id = member_id
    elif request:
        user_id = request.user.id

    user = Userinfo.objects.all().filter(user_id=user_id)
    if not user:
        if member_id:
            member = User.objects.get(pk=user_id)
            social_user = member.social_auth.filter(user_id=user_id).first()


        elif request:
            social_user = request.user.social_auth.filter(user_id=user_id).first()

        if social_user:

            if social_user.provider == 'facebook':
                url = "https://graph.facebook.com/v2.9/" + social_user.extra_data[
                    'id'] + "?fields=name,email,gender,location,picture,link&access_token=" + social_user.extra_data[
                          'access_token']
                response = rqst.get(url)
                data = json.loads(response.text)
                image_url = "http://graph.facebook.com/" + social_user.extra_data[
                    'id'] + "/picture?width=400&height=400"
                print(data)
                usr = User.objects.get(pk=request.user.id)

                try:
                    user = Userinfo.objects.get(user_id=request.user.id)
                    if not usr.email:

                        if user_email:
                            data['email'] = user_email
                            usr.email = user_email
                            usr.save()
                        if not user.email:
                            user.email = user_email
                            user.save()

                except:
                    user = Userinfo()
                    if 'name' in data:
                        user.name = data['name']
                    if 'email' in data:
                        user.email = data['email']
                    if 'location' in data:
                        user.city = data['location']['name']
                    user.image_link = upload_image_to_firebase(image_url, usr.id)
                    user.login_type = 'facebook'
                    user.login_json = data
                    if member_id:
                        user.user_id = member

                    elif request:
                        user.user_id = request.user
                    user.save()
                    print("created userinfo")

                if user_email:
                    return JsonResponse({"success": True})

                return user

            if social_user.provider == 'linkedin-oauth2':
                # accessing Linked In API to get user basic information
                url = 'https://api.linkedin.com/v2/me?projection=(id,firstName,emailAddress,lastName,vanityName,headline,interests,location,picture-url,name,profilePicture(displayImage~:playableStreams))&oauth2_access_token=' + \
                      social_user.extra_data['access_token']
                email_url = 'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))&oauth2_access_token=' + \
                            social_user.extra_data['access_token']
                response = rqst.get(url)
                # getting public details of user from Linked In
                data_main = json.loads(response.text)
                response = rqst.get(email_url)
                email_data = json.loads(response.text)
                # getting specific details from received Json
                user_name = data_main['firstName']['localized']['en_US'] + " " + data_main['lastName']['localized'][
                    'en_US']
                profile_picture = data_main['profilePicture']['displayImage~']['elements'][2]['identifiers'][0][
                    'identifier']
                email = email_data['elements'][0]['handle~']['emailAddress']
                usr = User.objects.get(pk=request.user.id)
                usr1 = Userinfo.objects.get(user_id=request.user.id)

                if not usr.email:
                    if user_email:
                        email = user_email
                        usr.email = user_email
                        usr.save()
                if usr1 and not usr1.email:
                    if user_email:
                        usr1.email = user_email
                        usr1.save()
                # checking if there is any user having details with the email we got from linkedIn
                if not usr1:
                    # if there is no user having th email , create a user info for the user
                    user = Userinfo()
                    user.name = user_name
                    user.email = email
                    user.image_link = upload_image_to_firebase(profile_picture, usr.id)
                    # info.linkedin_link = data['publicProfileUrl']
                    user.login_type = 'linkedIn'
                    user.login_json = [data_main, email_data]
                    if member_id:
                        user.user_id = member
                    elif request:
                        user.user_id = request.user
                    user.save()

                if user_email:
                    return JsonResponse({"success": True})

                return user


@login_required
def accept_admin(request, community_id):
    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

    ''' function to accept promoter invitation or decilne the invitation from web '''
    # getting value attribute which says whether the user accepted or declined it
    accepted = request.GET.get('value', 'true')
    # forming url to call accept admin android api
    accept_url = api_url + 'accept_invitation'
    # preparing the necessary parameters to be passed to accept_admin android api
    params = {'member_id': request.user.id, 'community_id': community_id, 'value': accepted}
    # calling accept_admin android api and passing params
    rqst.post(accept_url, params=params)
    # redirecting to playstore
    return HttpResponseRedirect("https://play.google.com/apps/testing/com.collabmates")


#@login_required
def logout_view(request):
    logout(request)
    return redirect(settings.URL)


def join_community(request, community_id, ref_id, aj=False, member_state=None):


    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

    '''function to join community'''
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []

    member_id = request.user.id
    # calling similar communities api
    # similar_communitites_url = api_url + 'similar_communities/' + str(community_id)
    # res = rqst.get(similar_communitites_url, params={'member_id': member_id})
    # similar_communitites = json.loads(res.content)
    # similar_communities = similar_communitites['communities'][:10]
    similar_communities = []

    join_url = api_url + 'v1/join_community'

    community = Community.objects.get(id=community_id)
    validation_error = False
    if request.method == "POST":

        # question_data = request.POST.dict()

        # for key, value in question_data.items():
        #     if not key[-1] == ']':
        #         question_data = key+"="+value
        #     else:
        #         question_data = key
        #     break

        question_data = request.POST.dict().get("data")

        question_data = ast.literal_eval(question_data)
        response_list = []

        for quest_dict in question_data:

            question_dict = {}
            if quest_dict['id'] == 'csrfmiddlewaretoken':
                continue
            elif quest_dict['id'] == 'ref_id':
                continue

            question_dict['id'] = quest_dict['id']
            question_dict['value'] = quest_dict['value']

            response_list.append(question_dict)

        json_dict = {"community_id": community_id, "timestamp": time.time(),'aj':aj}
        json_dict['questions'] = response_list
        json_dict['user_id'] = request.user.id

        #print(">>>>  ",json_dict)
        info_logger.info(json_dict)

        if (member_state == 0 or member_state == 5) and member_state is not None:
            params = {'member_id': member_id, 'community_id': community_id, 'ref_id': ref_id}
            rqst.post(join_url, params=params, json=json_dict)
        # return false to show thank you page the user has now answered the questions
        return False, validation_error, user, similar_communities, community, [],{}

    else:
        question_format = get_community_questions(community_id)
        community_creator = get_community_creator(community)
        auto_join = {}
        if community_creator:
            created_by = community_creator
            auto_join = private_link_app_invite(community, aj, created_by)
        if not question_format:
            json_dict = {'user_id': request.user.id}
            params = {'member_id': member_id, 'community_id': community_id}
            rqst.post(join_url, params=params, json=json_dict)
            # return false to show thank you page as there are no questions for this community

            return False, validation_error, user, similar_communities, community, [],auto_join
        else:
            # return true to take the user to questions page
            return True, validation_error, user, question_format, community, [], auto_join


def get_community_questions(community_id):
    questions = communityQuestions.objects.filter(community=community_id,is_hidden=False).order_by('-rank', 'id')
    question_format = []
    dropdown_list = []
    for each_question in questions:
        temp = {}
        if each_question.question_state:
            temp['question_state'] = each_question.question_state

            if temp['question_state'] == question_states.INTRODUCTION:
                if each_question.value:
                    item = ast.literal_eval(each_question.value)[0]
                    temp['min_chars'] = int(item['min_chars'])
                    if item['max_chars'] != "No limit":
                        temp['max_chars'] = int(item['max_chars'])
                    else:
                        # temp['max_chars'] = 10000
                        temp['no_limit'] = True
                temp['data'] = each_question.question_title

            elif temp['question_state'] == question_states.PROFILE_LINK:
                if each_question.value:
                    item = ast.literal_eval(each_question.value)[0]
                    temp['profile_platform'] = item['profile_platform'].lower()
                temp['data'] = each_question.question_title


            if temp['question_state'] == 6:
                if each_question.value:
                    item = ast.literal_eval(each_question.value)[0]['date_time']
                    if item.lower() == "yyyy":
                        date_format = 'year'
                    elif item.lower() == "mm yyyy":
                        date_format = 'month'
                        temp["month_format"] = "normal"
                    elif item.lower() == "mmm yyyy":
                        date_format = 'month'
                        temp["month_format"] = "full"
                    elif item.lower() == "dd mmm yyyy":
                        date_format = 'date'
                        temp["date_format_full"] = "full"
                    else:
                        date_format = 'date'
                        temp["date_format_full"] = "normal"

                    temp["date_format"]=date_format


            if temp['question_state'] == 1 or temp['question_state'] == 2:


                dropdown_options = json.loads(each_question.value) if each_question.value else []

                dropdown_list = []

                for option in dropdown_options:
                    dropdown_list.append((option['value']))

                # dropdown_list.sort()


                if 'Other' not in dropdown_list:
                    temp['dropdown_list'] = dropdown_list
                    temp['allowed_addition'] = False
                    if not each_question.help_text:
                        if len(dropdown_list) > 1:
                            temp['help_text'] = "Select from options"
                        else:
                            temp['help_text'] = "Select from option"
                else:
                    dropdown_list.remove('Other')
                    temp['allowed_addition'] = True
                    temp['dropdown_list'] = dropdown_list
                    if not each_question.help_text:
                        if len(dropdown_list) > 1:
                            if temp['question_state'] == 1:
                                temp['help_text'] = "Select from options or add a new option"
                            else:
                                temp['help_text'] = "Select from options or add new options"
                        else:
                            if temp['question_state'] == 1:
                                temp['help_text'] = "Add a new option"
                            else:
                                temp['help_text'] = "Add new options"

            temp['data'] = each_question.question_title
        else:
            temp['question_state'] = each_question.question_state
            temp['dropdown_list'] = []
            temp['data'] = each_question.question_title
        # temp['data_type'] = each_question.data_type
        temp['id'] = each_question.id
        if each_question.dropdown_selection_limit:
            temp['max_selections'] = each_question.dropdown_selection_limit
        temp['optional'] = each_question.optional

        if each_question.help_text:
            temp['help_text'] = each_question.help_text

        if each_question.question_state == question_states.INTRODUCTION:
            temp['rank'] = 0
        else:
            temp['rank'] = 1


        question_format.append(temp)

    #print(question_format)
    question_format = sorted(question_format, key=lambda i: i['rank'])
    return question_format


def thankyou(request):
    email = request.GET.get("mail")
    print("email = = ", email)

    if email:
        mail = get_notified()
        mail.email = email
        mail.save()
        send_email(email)

    return render(request, 'thankyou2.html')


def send_email(email):
    ''' function to send email to user to be notified '''
    fail_silently = True
    to = 'nipungoyal.iitd@gmail.com'
    subject = email + " wants to be Notified"
    msg = EmailMultiAlternatives(subject,
                                 email,
                                 "LikeMinds<hello@likeminds.community>",
                                 [to, 'harsh.shukla@collabmates.com'],
                                 )
    if email:
        return msg.send(fail_silently)


def privacy(request):
    header = {
        'back': True,
        'title': "Privacy Policy",
        'backLink': "/",
        'subTitle': False,
        'background': '0',
        'color': 'F'
    }
    return render(request, 'privacy.html', {'header': header})


def terms(request):
    header = {
        'back': True,
        'title': "Terms",
        'backLink': "/",
        'subTitle': False,
        'background': '0',
        'color': 'F'
    }
    return render(request, 'terms.html', {'header': header})


def collabcard(request, card_id):
    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

    '''function to get data of collabcard'''

    collabcard_url = api_url + 'collabcard/' + str(card_id)
    collabcard = rqst.get(collabcard_url)
    collabcard_dict = json.loads(collabcard.content)

    request_user_email = False

    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)

            if not request.user.email:
                request_user_email = True
        except:
            user, request_user_email = update_user_info(request)
        if user.image_link:
            user_image = user.image_link
    else:
        user_image = ''

    answers = collabcard_dict['answers']
    # getting answer text of the collabcard
    if len(answers) == 0:
        answer_text = 'Be the first to respond'
    else:
        answer_text = collabcard_dict['collabcard']['answer_text']

    try:
        if 'og_tags' in collabcard_dict['collabcard']:
            og_image = collabcard_dict['collabcard']['og_tags']['image']
        else:
            og_image = None
    except:
        og_image = None

    community = Community.objects.get(pk=collabcard_dict['collabcard']['community_id'])

    is_member = False
    if request.user.is_authenticated:
        member = Members.objects.filter(community_id=community, member_id_id=request.user)
        if member.exists():
            if member[0].state == 1 or member[0].state == 2 or member[0].state == 4 or member[0].state == 7:
                is_member = True

    context = {'card': collabcard_dict['collabcard']['title'],
               'creator': collabcard_dict['collabcard']['member']['name'],
               'image_url': collabcard_dict['collabcard']['member']['image_url'],
               'collabcard_id': collabcard_dict['collabcard']['id'],
               'answer_text': answer_text,
               'answers': collabcard_dict['answers'],
               'card_id': card_id,
               'user_image_url': user_image,
               'share_link': collabcard_dict['collabcard']['share_link'],
               'share_link_image': og_image,
               'community_id': collabcard_dict['collabcard']['community_id'],
               'community_name': community.name,
               'created_at': collabcard_dict['collabcard']['created_at'],
               'answers_count': len(collabcard_dict['answers']),
               'is_member': is_member,
               'request_user_email': request_user_email,

               }
    print(context)
    return render(request, 'card.html', context)


@login_required
def view_answers(request, card_id):
    '''function to show the answers on web'''
    collabcard_url = api_url + 'collabcard/' + str(card_id)
    collabcard = rqst.get(collabcard_url)
    try:
        collabcard_dict = json.loads(collabcard.content)
    except ValueError:
        print('Json Decode error')

    context = {'card': collabcard_dict['collabcard']['title'],
               'creator': collabcard_dict['collabcard']['member']['name'],
               'user_image_url': collabcard_dict['collabcard']['member']['image_url'],
               'answers': collabcard_dict['answers'],
               'card_id': card_id,

               }
    return render(request, 'answers.html', context)


def create_message(request):
    '''function to create a message to show'''

    member_id = request.GET.get('member_id')
    user_info = Userinfo.objects.get(user_id=member_id)
    user = UserinfoSerializer(user_info)
    collabcard_id = request.GET.get('collabcard_id')
    params = {
        'member_id': member_id,
        'collabcard_id': collabcard_id
    }
    msg = request.GET.get('message')

    json_body = {
        'title': msg
    }
    link = api_url + 'create_answer'
    create_answer = rqst.post(link, params=params, json=json_body)
    return JsonResponse({'success': True, 'msg': msg, 'image_url': user['image_url'], 'name': user['name']})


def get_nominated_admin_details(community_id, email):
    '''fetching nominated promoter details from temp admin table'''
    community = get_object_or_404(Community, pk=community_id)
    details = temp_admin.objects.filter(community_id=community, email=email)
    if details:
        '''details are present,return s true'''
        # print('details are present')
        return True
    else:
        '''details are not present, returns false'''
        # print('details are not present')
        return False


def update_member_count(community_id):
    ''' update members count of a community , when a promoter or member joins a community '''
    # getting the count of members including admins in a community
    count = Members.objects.filter(community_id=community_id).filter(
        Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7) | Q(state=8) | Q(state=9)).count()
    # updating count
    Community.objects.filter(id=community_id).update(members_count=count)

    return count


def pending_list(request, community_id):
    ''' function to show pending list in html '''

    # if request.user.is_authenticated:
    #     try:
    #         user = Userinfo.objects.get(user_id=request.user.id)
    #     except:
    #         user = update_user_info(request)
    #
    # link = api_url + 'pending_members/' + str(community_id)
    #
    # link = link if not request.user.is_authenticated else link + "?member_id=" + str(request.user.id)
    #
    # res = rqst.get(link)
    # user_image_url = ""
    # is_promoter = 'false'
    # request_user_email = False
    # if request.user.is_authenticated:
    #     try:
    #         userinfo = Userinfo.objects.get(user_id=request.user.id)
    #     except:
    #         user, request_user_email = update_user_info(request)
    #     userinfo=Userinfo.objects.get(user_id=request.user.id)
    #     if not userinfo.image_link:
    #         user_image_url = url + userinfo.image_file.url
    #     else:
    #         user_image_url = userinfo.image_link
    #     link = api_url + 'members_state?member_id=' + str(request.user.id) + '&community_id=' + str(community_id)
    #     state = rqst.get(link)
    #     try:
    #         state = json.loads(state.content)
    #         if state['state'] == 1 or state['state'] == 2:
    #             is_promoter = 'true'
    #     except Exception as e:
    #         traceback.print_exc()
    # pending_list = []
    # error = False
    # try:
    #     pending_list = json.loads(res.content)['pending_members']
    # except Exception as e:
    #     error = True
    #     traceback.print_exc()

    community_instance = Community.objects.get(id=community_id)

    all_members = get_member_details(community_instance,3)
    members = []
    is_promoter = False
    for member in all_members:
        if member['state'] == member_states.PENDING_MEMBER:
            #member['answer'] = ""
            members.append(member)
        elif member['state'] == member_states.ADMIN and request.user.id == member['id']:
            is_promoter = True


    header = {
        'back': True,
        'title': 'Members',
        'subTitle': community_instance.name,
        'background': 'Wa',
        'color': 'F'
    }

    context = {
        'header' : header,
        'members' : members,
        'community_id':community_instance.id,
        'is_member' : is_promoter,
        'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'facebook_auth_id': settings.SOCIAL_AUTH_FACEBOOK_KEY,
        'firebase_config': settings.FIREBASE_CONFIG,
        'length' : len(members)

    }
    #print(context)

    return render(request,'pending_page.html', context)

def questions_responses(request):
    '''function to get responses of the particular user to show'''
    member_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')
    userinfo = Userinfo.objects.get(user_id=member_id)
    form_response = communityAnswers.objects.filter(member=member_id, community=community_id).order_by('-id')
    response_list = []
    for data in form_response:
        response = {}
        response['question'] = data.question_title
        response['answer'] = data.question_answer
        response_list.append(response)
    if not userinfo.image_link:
        image = url + userinfo.image_file.url
    else:
        image = userinfo.image_link
    context = {
        'image_url': image,
        'response_list': response_list
    }
    return JsonResponse(context)


def get_or_create_tag(tag_name, tag_type):
    '''function to check whether the tag is existing tag or a new tag and
     if its new create it as un-categorized'''

    if len(tag_name) is 0:
        print('empty list')
        return 0

    try:
        tag_id = int(tag_name)
        return tag_id
    except:
        tag_name = tag_name.strip()
        try:
            tag = Tags_lpig.objects.get(name=tag_name)
        except:
            category = Category.objects.get(pk=6)
            attribute = Attributes.objects.filter(Q(attribute_name__icontains=tag_type),
                                                  Q(attribute_name__icontains='Uncategorized'))[0]
            tag = Tags_lpig()
            tag.name = tag_name
            tag.category_id = category
            tag.attribute_id = attribute
            tag.save()
            tag.tag_id = tag.id
            tag.created_at = time.time()
            tag.updated_at = time.time()
            tag.save()
        return tag.id


def fill_cluster_tags_in_tags_list(tag_list, typ):
    '''function to fill cluster tags in tags list'''
    clusted_tags = []
    for each_tag in tag_list:
        tag = Tags_lpig.objects.get(pk=each_tag)
        if tag.cluster_tag_id:
            # tag_list.remove(each_tag)
            # if typ == "Legacy":
            #     clusted_tags=list(Tags_lpig.objects.filter(tag_id=tag.cluster_tag_id).values_list('id',flat=True))
            # elif typ == "Profession":
            #     clusted_tags=list(Tags_lpig.objects.filter(tag_id=tag.cluster_tag_id).values_list('id',flat=True))
            # elif typ == "Interest":
            #     clusted_tags=list(Tags_lpig.objects.filter(tag_id=tag.cluster_tag_id).values_list('id',flat=True))
            # elif typ == "Geography":
            #     clusted_tags=list(Tags_lpig.objects.filter(tag_id=tag.cluster_tag_id).values_list('id',flat=True))
            temp = Tags_lpig.objects.filter(tag_id=tag.cluster_tag_id)
            if temp:
                clusted_tags.append(temp[0].tag_id)
    if not clusted_tags:
        return tag_list
    else:
        tag_list = tag_list + clusted_tags
        return tag_list


def insert_tags_for_user(user_id, tag_list, typ):
    '''function to insert tags for user'''

    user = User.objects.get(id=user_id)

    '''updating the list based on type'''

    if typ == "Legacy":
        user_tags_list = list(User_Legacy.objects.filter(user_id=user).values_list("tags_id", flat=True))
        tag_list = fill_cluster_tags_in_tags_list(tag_list, "Legacy")
        info_logger.info("""Tag_type=%s,Tag_list=%s""" % (typ, str(tag_list)))

        for each_tag in tag_list:
            if each_tag in user_tags_list:
                continue
            elif not each_tag in user_tags_list:
                tag = Tags_lpig.objects.get(pk=each_tag)
                user_tag = User_Legacy()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()

            else:
                pass
        for tag in user_tags_list:
            if tag not in tag_list:
                tag = User_Legacy.objects.filter(tags_id=tag, user_id=user)

                if str(tag[0].tags_id.id) != '15':
                    tag.delete()

    if typ == "Profession":

        user_tags_list = list(User_Profession.objects.filter(user_id=user).values_list("tags_id", flat=True))
        tag_list = fill_cluster_tags_in_tags_list(tag_list, "Profession")
        info_logger.info("""Tag_type=%s,Tag_list=%s""" % (typ, str(tag_list)))

        for each_tag in tag_list:
            if each_tag in user_tags_list:
                continue
            elif not each_tag in user_tags_list:
                tag = Tags_lpig.objects.get(pk=each_tag)

                user_tag = User_Profession()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()

            else:
                pass
        for tag in user_tags_list:
            if tag not in tag_list:
                tag = User_Profession.objects.filter(tags_id=tag, user_id=user)

                if str(tag[0].tags_id.id) != '16':
                    tag.delete()

    if typ == "Interests":

        user_tags_list = list(User_Interest.objects.filter(user_id=user).values_list("tags_id", flat=True))
        tag_list = fill_cluster_tags_in_tags_list(tag_list, "Interest")
        info_logger.info("""Tag_type=%s,Tag_list=%s""" % (typ, str(tag_list)))

        for each_tag in tag_list:
            if each_tag in user_tags_list:

                continue
            elif not each_tag in user_tags_list:
                tag = Tags_lpig.objects.get(pk=each_tag)
                user_tag = User_Interest()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()
            else:
                pass
        for tag in user_tags_list:
            if tag not in tag_list:
                tag = User_Interest.objects.filter(tags_id=tag, user_id=user)

                if str(tag[0].tags_id.id) != '17':
                    tag.delete()

    if typ == "Geography":

        user_tags_list = list(User_Geography.objects.filter(user_id=user).values_list("tags_id", flat=True))
        tag_list = fill_cluster_tags_in_tags_list(tag_list, "Geography")
        info_logger.info("""Tag_type=%s,Tag_list=%s""" % (typ, str(tag_list)))

        for each_tag in tag_list:
            if each_tag in user_tags_list:

                continue
            elif not each_tag in user_tags_list:
                tag = Tags_lpig.objects.get(pk=each_tag)
                user_tag = User_Geography()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()

            else:
                pass
        for tag in user_tags_list:
            if tag not in tag_list:
                tag = User_Geography.objects.filter(tags_id=tag, user_id=user)

                if str(tag[0].tags_id.id) != '18':
                    tag.delete()

        # update_user_geography_tags.delay(user_id=user.id)


def get_user_tags_from_list(tag_list, type):
    '''function to get user_tags from list from front end'''

    type_list = []
    for tag in tag_list:
        tags_id = get_or_create_tag(tag, type)
        type_list.append(tags_id)

    if type == "Legacy":
        type_list.append(15)
    if type == "Profession":
        type_list.append(16)
    if type == "Interests":
        type_list.append(17)
    if type == "Geography":
        type_list.append(18)
    return type_list


def get_user_legacy_tags(user_id):
    user_legacy = list(User_Legacy.objects.filter(user_id=user_id).values_list('tags_id', flat=True))
    user_geo = list(User_Geography.objects.filter(user_id=user_id).values_list('tags_id', flat=True))
    user_legacy_education = []
    user_legacy_work = []
    user_legacy_hometown = []
    user_geography = []

    if user_legacy:

        for tag_id in user_legacy:
            tag = Tags_lpig.objects.get(pk=tag_id)

            if tag.category_id.id == 1 and tag.attribute_id.id == 1:
                user_legacy_work.append(tag)

            elif tag.category_id.id == 1 and tag.attribute_id.id == 2:
                user_legacy_education.append(tag)


            elif tag.category_id.id == 1 and tag.attribute_id.id == 3:
                user_legacy_hometown.append(tag)

    if user_geo:

        for tag_id in user_geo:
            tag = Tags_lpig.objects.get(pk=tag_id)

            if tag.category_id.id == 4 and tag.attribute_id.id == 12 or tag.attribute_id.id == 13 or tag.attribute_id.id == 14:
                user_geography.append(tag)

    return user_legacy_work, user_legacy_education, user_legacy_hometown, user_geography


def get_user_profession_tags(user_id):
    user_profession = list(User_Profession.objects.filter(user_id=user_id).values_list('tags_id', flat=True))

    user_profession_industry = []
    user_profession_skill = []
    user_profession_designation = []

    if user_profession:

        for tag_id in user_profession:
            tag = Tags_lpig.objects.get(pk=tag_id)

            if tag.category_id.id == 2 and tag.attribute_id.id == 5:
                user_profession_skill.append(tag)

            elif tag.category_id.id == 2 and tag.attribute_id.id == 6:
                user_profession_industry.append(tag)

            elif tag.category_id.id == 2 and tag.attribute_id.id == 7:
                user_profession_designation.append(tag)

    return user_profession_industry, user_profession_skill, user_profession_designation


def get_user_interest_tags(user_id):
    user_interests = list(User_Interest.objects.filter(user_id=user_id).values_list('tags_id', flat=True))

    user_interest_hobby = []
    user_interest_sports = []
    user_interest_fan = []
    user_interest_cause = []

    if user_interests:

        for tag_id in user_interests:
            tag = Tags_lpig.objects.get(pk=tag_id)

            if tag.category_id.id == 3 and tag.attribute_id.id == 9:
                user_interest_hobby.append(tag)

            elif tag.category_id.id == 3 and tag.attribute_id.id == 10:
                user_interest_sports.append(tag)


            elif tag.category_id.id == 3 and tag.attribute_id.id == 11:
                user_interest_fan.append(tag)

            elif tag.category_id.id == 3 and tag.attribute_id.id == 8:
                user_interest_cause.append(tag)

    return user_interest_hobby, user_interest_sports, user_interest_fan, user_interest_cause


def get_community_legacy_tags(community_id):
    community_legacy = list(
        Community_Legacy.objects.filter(community_id=community_id).values_list('tags_id', flat=True))
    community_geo = list(
        Community_Geography.objects.filter(community_id=community_id).values_list('tags_id', flat=True))

    community_legacy_education = []
    community_legacy_work = []
    community_legacy_hometown = []
    community_geography = []

    if community_legacy:

        for tag_id in community_legacy:
            tag = Tags_lpig.objects.get(pk=tag_id)

            if tag.category_id.id == 1 and tag.attribute_id.id == 1:
                community_legacy_work.append(tag)

            elif tag.category_id.id == 1 and tag.attribute_id.id == 2:
                community_legacy_education.append(tag)


            elif tag.category_id.id == 1 and tag.attribute_id.id == 3:
                community_legacy_hometown.append(tag)

    if community_geo:

        for tag_id in community_geo:
            tag = Tags_lpig.objects.get(pk=tag_id)

            if tag.category_id.id == 4 and tag.attribute_id.id == 12:
                community_geography.append(tag)

    return community_legacy_work, community_legacy_education, community_legacy_hometown, community_geography


def get_community_profession_tags(community_id):
    community_profession = list(
        Community_Profession.objects.filter(community_id=community_id).values_list('tags_id', flat=True))

    community_profession_industry = []
    community_profession_skill = []
    community_profession_designation = []

    if community_profession:

        for tag_id in community_profession:
            tag = Tags_lpig.objects.get(pk=tag_id)

            if tag.category_id.id == 2 and tag.attribute_id.id == 5:
                community_profession_skill.append(tag)

            elif tag.category_id.id == 2 and tag.attribute_id.id == 6:
                community_profession_industry.append(tag)

            elif tag.category_id.id == 2 and tag.attribute_id.id == 7:
                community_profession_designation.append(tag)

    return community_profession_industry, community_profession_skill, community_profession_designation


def get_community_interest_tags(community_id):
    community_interests = list(
        Community_Interest.objects.filter(community_id=community_id).values_list('tags_id', flat=True))

    community_interest_hobby = []
    community_interest_sports = []
    community_interest_fan = []
    community_interest_cause = []

    if community_interests:

        for tag_id in community_interests:
            tag = Tags_lpig.objects.get(pk=tag_id)

            if tag.category_id.id == 3 and tag.attribute_id.id == 9:
                community_interest_hobby.append(tag)

            elif tag.category_id.id == 3 and tag.attribute_id.id == 10:
                community_interest_sports.append(tag)


            elif tag.category_id.id == 3 and tag.attribute_id.id == 11:
                community_interest_fan.append(tag)

            elif tag.category_id.id == 3 and tag.attribute_id.id == 8:
                community_interest_cause.append(tag)

    return community_interest_hobby, community_interest_sports, community_interest_fan, community_interest_cause


# onboarding flow

def onboarding(request):
    '''function to show the legacy'''

    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

    if request.method == 'GET':

        community_id = request.GET.get('community_id', None)
        member_id = request.GET.get('member_id', None)
        autheticate = request.GET.get('authenticate', False)
        print(autheticate)
        if autheticate == "true" or autheticate == "True":
            autheticate = True
        else:
            autheticate = False

        if community_id:
            legacy_work, legacy_education, legacy_hometown, geography = get_community_legacy_tags(
                community_id)
        elif member_id and autheticate:
            legacy_work, legacy_education, legacy_hometown, geography = get_user_legacy_tags(
                member_id)
        elif not member_id:
            legacy_work, legacy_education, legacy_hometown, geography = get_user_legacy_tags(request.user.id)
        else:
            legacy_work = []
            legacy_education = []
            legacy_hometown = []
            geography = []

        android = False
        ios = False
        if is_request_android(request) and member_id and autheticate:
            android = True

        if is_request_ios(request) and member_id and autheticate:
            ios = True

        education_tags = Tags_lpig.objects.filter(attribute_id=2, is_cluster=0).order_by('name')
        work_tags = Tags_lpig.objects.filter(attribute_id=1, is_cluster=0).order_by('name')
        hometown_tags = Tags_lpig.objects.filter(attribute_id=3, is_cluster=0).order_by('name')
        geography_tags = Tags_lpig.objects.filter(attribute_id=12, is_cluster=0).order_by('name')
        context = {
            'legacy_education': education_tags,
            'legacy_work': work_tags,
            'legacy_hometown': hometown_tags,
            'geography': geography_tags,
            'community_legacy_work': legacy_work,
            'community_legacy_education': legacy_education,
            'community_legacy_hometown': legacy_hometown,
            'community_geography': geography,
            'community_id': community_id,
            'member_id': member_id,
            'android': android,
            'ios': ios,
        }

        return render(request, 'onboarding.html', context)
    else:

        user_id = request.POST.get('member_id', None)
        if not user_id:
            user_id = request.user.id

        legacy_education = request.POST.getlist('legacy_education[]')
        # legacy_work = request.POST.getlist('legacy_work[]')
        legacy_hometown = request.POST.getlist('legacy_hometown[]')
        geography = request.POST.getlist('loc[]')

        if not legacy_education:
            return JsonResponse({'legacy_error': True})
        elif not geography:
            return JsonResponse({'geo_error': True})

        legacy_li = legacy_education + legacy_hometown  # + legacy_work

        type_list = get_user_tags_from_list(legacy_li, "Legacy")
        insert_tags_for_user(user_id, type_list, "Legacy")
        type_list = get_user_tags_from_list(geography, "Geography")
        insert_tags_for_user(user_id, type_list, "Geography")

        # for tag in legacy_hometown:
        #     insert_user_home_town_tags(user_id = user_id, tag=tag)

        return JsonResponse({'success': True})


def onboarding_profession(request):
    '''onboarding for profession'''

    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

    if request.method == 'GET':

        community_id = request.GET.get('community_id', None)
        member_id = request.GET.get('member_id', None)
        autheticate = request.GET.get('authenticate', False)
        if autheticate == "true" or autheticate == "True":
            autheticate = True
        else:
            autheticate = False

        if community_id:

            profession_industry, profession_skill, profession_designation = get_community_profession_tags(community_id)
        elif member_id and autheticate:
            profession_industry, profession_skill, profession_designation = get_user_profession_tags(member_id)
        elif not member_id:
            profession_industry, profession_skill, profession_designation = get_user_profession_tags(request.user.id)
        else:
            profession_industry = []
            profession_skill = []
            profession_designation = []

        android = False
        ios = False
        if is_request_android(request) and member_id and autheticate:
            android = True

        if is_request_ios(request) and member_id and autheticate:
            ios = True

        industry_tags = Tags_lpig.objects.filter(attribute_id=6, is_cluster=0).order_by('name')
        skill_tags = Tags_lpig.objects.filter(attribute_id=5, is_cluster=0).order_by('name')
        designation_tags = Tags_lpig.objects.filter(attribute_id=7, is_cluster=0).order_by('name')
        context = {
            'profession_industry': industry_tags,
            'profession_skill': skill_tags,
            'profession_designation': designation_tags,
            'community_profession_industry': profession_industry,
            'community_profession_skill': profession_skill,
            'community_profession_designation': profession_designation,
            'community_id': community_id,
            'user_id': member_id,
            'android': android,
            'member_id': member_id,
            'ios': ios,
        }

        return render(request, 'onboarding_profession.html', context)
    else:

        user_id = request.POST.get('member_id', None)
        if not user_id:
            user_id = request.user.id

        profession_industry = request.POST.getlist('profession_industry[]')
        profession_skill = request.POST.getlist('profession_skill[]')
        # profession_designation = request.POST.getlist('profession_designation[]')
        if not profession_industry:
            return JsonResponse({'industry_error': True})
        elif not profession_skill:
            return JsonResponse({'skill_error': True})

        profession_list = profession_industry + profession_skill

        type_list = get_user_tags_from_list(profession_list, "Profession")
        insert_tags_for_user(user_id, type_list, "Profession")

        return JsonResponse({'success': True})


def onboarding_interest(request):
    '''onboarding for profession'''

    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

    if request.method == 'GET':

        community_id = request.GET.get('community_id', None)
        member_id = request.GET.get('member_id', None)
        autheticate = request.GET.get('authenticate', False)
        if autheticate == "true" or autheticate == "True":
            autheticate = True
        else:
            autheticate = False

        if community_id:

            interest_hobby, interest_sports, interest_fan, interest_cause = get_community_interest_tags(community_id)
        elif member_id and autheticate:
            interest_hobby, interest_sports, interest_fan, interest_cause = get_user_interest_tags(member_id)
        elif not member_id:
            interest_hobby, interest_sports, interest_fan, interest_cause = get_user_interest_tags(request.user.id)
        else:
            interest_hobby = []
            interest_sports = []
            interest_fan = []
            interest_cause = []

        android = False
        ios = False
        if is_request_android(request) and member_id and autheticate:
            android = True
            try:
                user_info = Userinfo.objects.get(user_id=member_id)
                user_info.mobile_os = "Android"
                user_info.secondary_email = user_info.email
                user_info.save()


            except:
                print("Error in getting user info object")

        if is_request_ios(request) and member_id and autheticate:
            ios = True

            try:
                user_info = Userinfo.objects.get(user_id=member_id)
                user_info.mobile_os = "iOS"
                user_info.secondary_email = user_info.email
                user_info.save()


            except:
                print("Error in getting user info object")

        hobby_tags = Tags_lpig.objects.filter(attribute_id=9, is_cluster=0).order_by('name')
        sports_tags = Tags_lpig.objects.filter(attribute_id=10, is_cluster=0).order_by('name')
        fan_tags = Tags_lpig.objects.filter(attribute_id=11, is_cluster=0).order_by('name')
        cause_tags = Tags_lpig.objects.filter(attribute_id=8, is_cluster=0).order_by('name')

        context = {
            'interest_hobby': hobby_tags,
            'interest_sports': sports_tags,
            'interest_fan': fan_tags,
            'interest_cause': cause_tags,
            'community_interest_hobby': interest_hobby,
            'community_interest_sports': interest_sports,
            'community_interest_fan': interest_fan,
            'community_interest_cause': interest_cause,
            'android': android,
            'member_id': member_id,
            'autheticate': autheticate,
            'ios': ios,
        }

        return render(request, 'interest_onboarding.html', context)

    else:
        # user_id = request.user.id

        user_id = request.POST.get('member_id', None)
        if not user_id:
            user_id = request.user.id
        member_id = request.POST.get('member_id', None)
        autheticate = request.POST.get('autheticate', False)
        if autheticate == "true" or autheticate == "True":
            autheticate = True
        else:
            autheticate = False
        print("authenticate === ", autheticate)

        interest_hobby = request.POST.getlist('interest_hobby[]')
        interest_sports = request.POST.getlist('interest_sports[]')
        interest_fan = request.POST.getlist('interest_fan[]')
        interest_cause = request.POST.getlist('interest_cause[]')

        if not interest_hobby and not interest_sports and not interest_fan and not interest_cause:
            return JsonResponse({'interest_error': True})

        interest_list = interest_hobby + interest_sports + interest_fan + interest_cause

        type_list = get_user_tags_from_list(interest_list, "Interests")
        insert_tags_for_user(user_id, type_list, "Interests")
        compute_rank.delay(user_id=user_id)
        time.sleep(3)
        print("authenticate === ", autheticate)
        print(member_id)
        print(is_request_android(request))

        # if is_request_android(request) and member_id and autheticate:
            # sending notificaton after rank compuatation
            # sending notificaton after rank compuatation
            # notification_after_compute_rank.delay(user_id=member_id)

        return JsonResponse({'user_agent': False})


def access_page(request):
    '''function to create an early access page and save early respose'''

    # print('>>>>>>>>>>>    ',request.META)
    if request.method == "GET":
        return render(request, 'access_page.html', {})
    else:
        user_id = request.user.id
        mobile_os = request.POST.get('mobile_os')
        email = request.POST.get('email')
        mobile_no = request.POST.get('mobile_no')
        try:
            user_info = Userinfo.objects.get(user_id=user_id)
            user_info.mobile_os = mobile_os
            user_info.secondary_email = email
            if mobile_no:
                user_info.contact_number = mobile_no
            else:
                user_info.contact_number = None
            user_info.save()

            # send_mail_after_rank_computation.delay(user_id=user_id)
            send_mail_after_rank_computation.delay(user_id=user_id)

        except:

            print("error in userinfo")

    return JsonResponse({'success': True, 'mobile_os': mobile_os})


def alpha_page(request):
    '''function to show the alpha  page based on prefereces to discover relevant communities'''

    user_legacy = User_LPIG.objects.filter(member_id=request.user).values('legacy')
    context = {}
    if user_legacy:
        legacy = user_legacy[0]['legacy']
        if "6" in legacy:
            context['college'] = "IIT DELHI"
            context['mobile_os'] = request.user.userinfo.mobile_os
        else:
            context['college'] = ""
    return render(request, 'alpha_page.html', context)



def linked_in_authentication(request):

    code = request.GET.get('code',None)
    state = request.GET.get('state')
    if not code:
        return HttpResponse("unable to login try again")

    #url = "http://" + request.META['HTTP_HOST']  # for local
    url = "https://"+request.META['HTTP_HOST']

    redirect_url = url + state

    link="https://www.linkedin.com/oauth/v2/accessToken"
    redirect_uri = url+"/oauth/complete/linkedin-oauth2/"

    info_logger.info(redirect_uri)

    params={
      'client_id':settings.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY,
      'client_secret': settings.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET,
      'grant_type':'authorization_code',
      'redirect_uri':redirect_uri,
      'code':code

    }
    ans=rqst.post(link, params=params)
    response = ans.json()
    info_logger.info(response)

    if 'access_token' not in response:
        return  HttpResponse("Try after sometime!!!!!")

    token = response['access_token']
    #print(token)

    #print(dis.json())

    #getting the user data
    user_url = 'https://api.linkedin.com/v2/me?projection=(id,firstName,emailAddress,lastName,vanityName,headline,interests,location,picture-url,name,profilePicture(displayImage~:playableStreams))&oauth2_access_token=' + \
          response['access_token']
    email_url = 'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))&oauth2_access_token=' + \
                response['access_token']
    resp = rqst.get(user_url)
    # getting public details of user from Linked In
    data_main = json.loads(resp.text)
    resp = rqst.get(email_url)
    email_data = json.loads(resp.text)

    data_main['email'] = email_data
    login_url = url + "/api/v1/login"
    response = rqst.post(login_url,json={"type": "linkedIn", "login_json": data_main})
    login_response = response.json()
    info_logger.info(response)
    if 'user' in login_response:
        user = User.objects.get(id=login_response['user']['id'])
        login(request, user=user, backend="django.contrib.auth.backends.ModelBackend")
    # context = {'b': data_main}
    #
    # data_main = urlencode(context)
    #
    # #print(ans)
    # #print(data_main)
    # #data_main = quote(data_main,encoding='utf-8')
    # redirect_url = redirect_url + "?json="+str(data_main)
    info_logger.info(request.user.is_authenticated)
    return redirect(redirect_url)




def community_wise_details(request):
    if request.method == 'POST':
        community_id = request.POST.get('community_id',None)
        password = request.POST.get('pass',None)
        if community_id and password:
            if password == 'TheTarun@1110':
                members = Members.objects.filter(community_id = community_id)
                crs = Collabcard.objects.filter(community = community_id).order_by('date_epoch')
                answers = card_answers.objects.filter(card__community = community_id)
                result = []
                for m in members:
                    record = {}
                    record['name'] = m.member_id.userinfo.name
                    record['cr_created'] = crs.filter(user = m.member_id).count()
                    record['answers'] = answers.filter(user = m.member_id).count()
                    result.append(record)
                result_c = []
                for cr in crs:
                    record_c = {}
                    record_c['name'] = cr.header
                    mem = []
                    for m in members:
                        cms = conversationMemberState.objects.filter(card_id=cr.id, user_id=m.member_id)
                        print()
                        if cms.exists():
                            mem.append(cms)
                    record_c['member'] = mem
                    result_c.append(record_c)

                    # cms = conversationMemberState.objects.filter(card_id=card_id, user_id=member_id)
                context = {
                    'result':result,
                    'crs':crs,
                    'result_c':result_c,
                }
            else:
                context = {}
        else:
            context = {}
    else:
        context = {}
    return render(request, 'cms/community_wise_details.html', context)


def unsubscribe_from_email(request):
    user_hash = request.GET.get('m',None)
    email = request.GET.get('code',None)
    user_id = decrypt(user_hash)
    user = User.objects.get(id=user_id)
    notification_list = []
    notification_list.append(email)
    
    flag_instance, created = memberNotificationFlag.objects.get_or_create(code=email,member=user)
    flag_instance.flag = False
    flag_instance.save()
    context = {
        'user':user,
        'flag':flag_instance.flag,
    }
    return render(request,'cms/unsubscribe_from_email.html',context)