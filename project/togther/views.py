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
from django.template.loader import get_template
import traceback
from collabmates_api.raw_queries import  compute_rank
from django.urls import reverse
from utility.utils import (get_city_address, update_tag_image,
                           update_user_geography_tags, create_or_categorize_tag,
                           referal, insert_user_home_town_tags, )
from urllib.parse import urlencode,quote
from utility.tasks import new_member_request
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from user_agents import parse

url = settings.URL

# uncomment to run it in localhost
#
# url='http://localhost:8000'

api_url = url + '/api/'


def index(request):
    '''function to show promotion page'''
    return render(request, 'index.html')


def home(request):
    # users = User.objects.all()
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return render(request, 'home.html', {})

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
        return render(request, 'signup.html',{})

def dashboard(request):
    ''' function to show all communities and filter based on categories '''

    print('reqesut META  >>>>>>>>> ',request.META)
    if request.user.is_authenticated:

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
        onboard,is_iitd = user_onbaord(request)

        # if 'HTTP_USER_AGENT' in request.META:
        #     ua_string = request.META['HTTP_USER_AGENT']
        #     #ua_string="Mozilla/5.0 (Linux; Android 9; Redmi Note 5 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.92 Mobile Safari/537.36"
        #     user_agent = parse(ua_string)
        #     mobile_os=request.user.userinfo.mobile_os
        #     if user_agent.os.family == "Android" and mobile_os:
        #         # user.mobile_os="Android"
        #         # user.save()
        #         base_url = reverse('dashboard')
        #         query_string = urlencode({'member_id': request.user.id})
        #         url = '{}?{}'.format(base_url, query_string)
        #         return redirect(url)


        return render(request, 'dashboard.html',
                      {'usr': user, 'communities': communities, 'my_communities': my_community[:2],
                       "my_communities_count": len(my_community),'onboard':onboard,'is_iitd':True})
    communities = Community.objects.filter(Q(hide_community='0')|Q(hide_community = '4')).order_by('-updated_at')
    for community in communities:
        update_member_count(community.id)




    return render(request, 'dashboard.html', {'communities': communities})


def user_onbaord(request):
    ''' checking if user has gone through on-boarding flow or not'''
    user_legacy = User_Legacy.objects.filter(user_id=request.user)
    user_prof = User_Profession.objects.filter(user_id=request.user)
    user_int = User_Interest.objects.filter(user_id=request.user)
    user_gro = User_Geography.objects.filter(user_id=request.user)

    # if user does not have any tags , user has to do on-boarding
    if user_legacy.exists() and user_prof.exists() and user_int.exists() and user_gro.exists():

        ''' if user comes back in the middle of on-baording flow,
        make sure he continues the on-boarding'''
        #iit_tag = user_legacy.filter(tags_id__id = 6)
        return True, True
    return False,False


def get_communities_by_rank(request):
    ''' function to get communities based on rank '''
    communities_list = []
    communities = Community_Rank.objects.filter(member_id = request.user).order_by('-weight').values_list('community_id', flat=True).distinct()
    for community in communities:
        comm = Community.objects.get(pk = community)
        # check if community is hidden or not
        if comm.hide_community == '0' or comm.hide_community == '3'  or comm.hide_community =='4':
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

    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

    community = get_object_or_404(Community, pk=community_id)

    # ----- accept admin APi part ---------------
    res = request.GET.dict()

    source = request.GET.get('source', '')

    # --------- referal part ----------------------
    ref_id = request.GET.get('ref_id', '')

    cta = ''
    if 'cta' in res:
        cta = res['cta']
        cta_split = cta.split("_")
        cta  = cta_split[0]
        if len(cta_split) == 2:
            ref_id = cta_split[1]
        # -------------------- auto join functionality ---------------------------------
        if cta == 'join' and request.user.is_authenticated:
            member = Members.objects.filter(member_id=request.user, community_id = community)
            member_state = member[0].state if member.exists() else 0

            questions, user, data, community = join_community(request, community_id,ref_id)
            if questions:
                if member_state == 0 or member_state == 5:
                    return render(request, 'response_form.html', {"data": data, 'usr': user, 'community': community,'ref_id':ref_id})
            else:

                if community.hide_community == '3':
                    if ref_id != '':
                        base_url = reverse('refer_members', kwargs={'community_id': community_id})
                        query_string = urlencode({'ref_id': ref_id})
                        url = '{}?{}'.format(base_url, query_string)
                        return redirect(url)
                    return redirect('refer_members',community_id=community.id)

                onboard = False
                user_legacy = User_Legacy.objects.filter(user_id = request.user)
                user_profession = User_Profession.objects.filter(user_id = request.user)
                user_interests = User_Interest.objects.filter(user_id = request.user)
                user_geography = User_Geography.objects.filter(user_id = request.user)

                if user_legacy.exists() and user_profession.exists() and user_interests.exists() and user_geography.exists():
                    onboard = True

                return render(request, 'thankyou.html',
                              {'usr': user,
                               'similar_communities': data,
                               'community': community,
                               'onboard':onboard})
        elif cta == 'share':
            cta = 'join'

    else:
        cta = ''
    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

        member = Members.objects.filter(member_id=request.user, community_id=community)
        try:
            if member:
                member_state = member[0].state
            else:
                try:
                    check = get_nominated_admin_details(email=request.user.email, community_id=community.id)
                    if check:
                        member = Members()
                        member.member_id = request.user
                        member.community_id = community
                        member.state = 6
                        member.save()
                        member_state = 6
                    else:
                        member_state = 0
                except:
                    member_state = 0
        except:
            member_state = 0

    elif not request.user.is_authenticated and source == 'email':
        member_state = 0

    elif not request.user.is_authenticated:
        member_state = 0

    elif source == 'email':
        member_state = 0

    else:
        member_state = 0
    # ------------------------------------------------------------------
    members, admin_details = get_members_of_community(request=request,community=community)
    # if user is not authenticated, give some communities as similar communities
    communities=Community.objects.filter(Q(hide_community='0')|Q(hide_community = '4'))[:10]

    if request.user.is_authenticated:
        # calling similar communities api
        similar_comm_url = api_url + 'similar_communities/'+str(community.id)
        params = {'member_id': request.user.id}
        response = rqst.get(similar_comm_url,params=params)

        if response.status_code == 200:
            communities = json.loads(response.content.decode('utf-8'))['communities'][:10]

        user = Userinfo.objects.all().filter(user_id=request.user.id)
    else:
        user = []

    return render(request, 'community.html', {'usr': user, 'similar_communities': communities,
                                              'community': community, 'admins': admin_details,
                                              'members': members, 'source': source,
                                              'cta': cta, 'Nom_mem_state': member_state,
                                              'admin_length': len(admin_details),
                                              'members_length': len(members),
                                              'similar_community_length':len(communities),
                                              'ref_id':ref_id,})


def refer_members(request,community_id):

    ref_id = request.GET.get('ref_id',None)

    if request.user.is_authenticated:

        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

        interested_member_id = request.user.id

        referal(ref_id=ref_id, community_id=community_id, interested_member_id =interested_member_id)

        share_url = url + '/community/' + str(community_id)+"?ref_id="+str(request.user.id)
        # decoded url for mobile web sharing
        copy_url=share_url
        # encoded url for web sharing
        share_url=quote(share_url)

        community = Community.objects.get(pk = community_id)

        member = Members.objects.filter(community_id=community,member_id=request.user)
        admins = Members.objects.filter(community_id=community).filter(Q(state=1) | Q(state=2)).order_by('id')

        share_text = 'Hi, I have added '+ str(community.name) +' community on CollabMates. It will be good if you can join this community'


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


        return  render(request,'referal.html',{'share_url':share_url,'community':community,'copy_url':copy_url,'share_text':share_text})


def get_members_of_community(request,community):
    ''' function to get admins and members of a community '''

    members = []
    admin_details = []
    all_members = []
    if community.hide_community == '0' or community.hide_community == '1'  or community.hide_community =='4':
        all_members = Members.objects.filter(community_id=community.id).filter(Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7))

    elif community.hide_community == '3':
        all_members = Members.objects.filter(community_id=community.id).filter(Q(state=8))

    for member in all_members:
        mem = Userinfo.objects.filter(user_id=member.member_id.id)
        if not mem.exists():
            user = update_user_info(request=request,member_id=member.member_id.id)
            print('user ---- ',user)
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


@login_required
def update_user_info(request,member_id=None):
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
                usr = User.objects.get(pk = user_id)
                if not usr.email:
                    usr.email = data['email']
                    usr.save()
                try:
                    user = Userinfo.objects.get(user_id=user_id)
                except:
                    user = Userinfo()
                    if 'name' in data:
                        user.name = data['name']
                    if 'email' in data:
                        user.email = data['email']
                    if 'location' in data:
                        user.city = data['location']['name']
                    user.image_url = image_url
                    user.login_type = 'facebook'
                    user.login_json = data
                    if member_id:
                        user.user_id = member

                    elif request:
                        user.user_id = request.user
                    user.save()
                    print("created userinfo")

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
                usr = User.objects.get(pk=user_id)
                if not usr.email:
                    usr.email = email
                    usr.save()
                # checking if there is any user having details with the email we got from linkedIn
                usr1 = Userinfo.objects.all().filter(email=email)
                if not usr1:
                    # if there is no user having th email , create a user info for the user
                    user = Userinfo()
                    user.name = user_name
                    user.email = email
                    user.image_url = profile_picture
                    # info.linkedin_link = data['publicProfileUrl']
                    user.login_type = 'linkedIn'
                    user.login_json = [data_main, email_data]
                    if member_id:
                        user.user_id = member
                    elif request:
                        user.user_id = request.user
                    user.save()

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


@login_required
def creategroup(request):
    print(request)
    if request.method == 'POST':
        res = request.POST.dict()
        img = request.FILES.dict()
        print(img)
        group = Community()
        group.members_count = group.members_count + 1
        group.name = res['name']
        group.about = res['about']
        group.purpose = res['purpose']
        group.location = res['location']
        if 'image' in img:
            print('yeah')
            group.image_url = img['image']
        if 'whatsapp_link' in res:
            group.whatsapp_group_link = res['whatsapp_link']
        group.save()

        categories = request.POST.getlist('category')
        for i in categories:
            category = Community_tags()
            category.category = i
            category.community_id_id = group.id
            category.save()

        admin = Admins()
        admin.admin_id = request.user
        community = Community.objects.get(id=group.id)
        admin.community_id = community
        admin.save()
        member = Members()
        member.member_id = request.user
        member.community_id = community
        member.save()
        return redirect('form_data', community_id=group.id)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []
    return render(request, 'creategroup.html', {'usr': user})


@login_required
def profile(request, user_id):
    info = Userinfo.objects.get(user_id=request.user)
    if request.method == 'GET':
        res = request.GET.dict()
        print(res)
        if 'name' in res:
            if (res['name'] == 'headline'):
                info.headline = res['headline']
                info.save()
            if (res['name'] == 'summary'):
                info.about = res['summary']
                info.save()
            if (res['name'] == 'experience'):
                info.headline = res['headline']
                info.fb_link = res['fb_link']
                info.linkedin_link = res['linkedin']
                info.save()
            if (res['name'] == 'education'):
                info.headline = res['headline']
                info.fb_link = res['fb_link']
                info.linkedin_link = res['linkedin']
                info.save()
            if (res['name'] == 'interests'):
                info.interests = res['interests']
                info.save()
            if (res['name'] == 'add_education'):
                edu = Education()
                edu.user_id = info
                edu.degree = res['degree']
                edu.instituion = res['institution']
                edu.from_year = res['from']
                edu.to_year = res['to']
                edu.description = res['description']
                edu.save()
            if (res['name'] == 'add_experience'):
                exp = Experience()
                exp.user_id = info
                exp.company = res['company']
                exp.title = res['title']
                exp.from_year = res['from']
                exp.to_year = res['to']
                exp.description = res['description']
                exp.save()
            return JsonResponse({'status': 'ok'})
    info = Userinfo.objects.all().filter(user_id=user_id)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []
    communities = Members.objects.all().filter(member_id=user_id)
    my_communities = []
    for i in communities:
        my_communities.append(i.community_id)
    experiences = Experience.objects.all().filter(user_id=info[0])
    educations = Education.objects.all().filter(user_id=info[0])
    print(':', my_communities)

    return render(request, 'profile.html',
                  {'usr': user, "info": info, "my_communities": my_communities, "experience": experiences,
                   "education": educations})


@login_required
def recieved_requests(request):
    admins_communities = Admins.objects.all().filter(admin_id=1)
    req = []
    # data = Form_response.objects.all().filter(user_id = request.user.id)
    for c in admins_communities:
        r = Requests.objects.all().filter(community_id_id=c.admin_id_id)
        req.append(r)
    return render(request, 'requests.html', {'req': req})


@login_required
def check_requests(request):
    if request.method == 'GET':
        res = request.GET.dict()
        print(res)
        if 'status' in res:
            req = Requests.objects.get(id=int(res['id']))
            comm = Community.objects.get(id=req.community.id)
            print(req)
            if res['status'] == '1':
                req.status = 1
                req.save()
                print(req.status)
                mem = Members()
                mem.member_id = req.user_id
                mem.community_id = req.community
                mem.save()
                comm.members_count = comm.members_count + 1
                comm.save()
                email = req.user_info.email
                print(email)
                send_mail('Collabmates: Group Joining', 'Your request has been approved by the admin.',
                          'Collabmates<hello@collabmates.com>', [email], fail_silently=False)
            else:
                req.status = -1
                req.save()
                email = req.user_info.email
                print(email)
                send_mail('Collabmates: Group Joining', 'Your request has been Rejected by the admin.',
                          'Collabmates<hello@collabmates.com>', [email], fail_silently=False)
            return JsonResponse({'status': 'OK'})
    admins_communities = Admins.objects.all().filter(admin_id=request.user)
    print(admins_communities)
    rqsts = []
    requests = Requests.objects.all()
    for i in requests:
        if i.status != -1:
            for j in admins_communities:
                print((j.community_id.id))
                if i.community.id == j.community_id.id:
                    rqsts.append(i)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []
    print(rqsts)
    return render(request, 'requests.html', {'usr': user, 'admins_communities': admins_communities, 'req': rqsts})


def request_response(request):
    if request.method == "GET":
        id = request.GET.get("id")
        req = Requests.objects.get(id=id)
        val = request.GET.get("value")
        print(type(val))
        if val == '1':
            print('heloo')
            req.status = 1
            print(req.community_id_id)
            comm = Community.objects.get(id=req.community_id_id)
            print(comm.members_count)
            comm.members_count = comm.members_count + 1
            member = Members()
            member.community_id_id = comm.id
            user = User.objects.get(id=req.user_id_id)
            member.member_id_id = user.id
            print(comm)
            comm.save()
            req.save()
            member.save()
        else:
            print('adfa')
    return HttpResponse('hi')


@login_required
def edit_profile(request, user_id):
    if request.method == 'POST':
        form = NewProfileForm(request.POST, request.FILES)
        usr = Userinfo.objects.all().filter(user_id_id=request.user.id)
        if usr:
            usr.delete()
        if form.is_valid():
            print(user_id)
            userinfo = form.save(commit=False)
            userinfo.user_id = request.user
            userinfo.profile_completed = 1
            userinfo.save()
            return redirect('profile', user_id=request.user.id)
    else:
        usr = Userinfo.objects.all().filter(user_id_id=user_id)

        if not usr:
            form = NewProfileForm()
        else:
            usr = usr[0]
            form = NewProfileForm(
                initial={'name': usr.name, 'city': usr.city, 'image_url': usr.image_url, 'college': usr.college,
                         'contact_number': usr.contact_number, 'experience': usr.experience, 'gender': usr.gender,
                         'interests': usr.interests, 'fb_link': usr.fb_link, 'linkedin_link': usr.linkedin_link})
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []
    return render(request, 'editprofile.html', {'usr': user, 'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('signup')


@login_required
def join_community(request, community_id,ref_id):

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
    similar_communitites_url = api_url + 'similar_communities/' + str(community_id)
    res = rqst.get(similar_communitites_url, params={'member_id': member_id})
    similar_communitites = json.loads(res.content)
    similar_communities = similar_communitites['communities'][:10]

    join_url = api_url + 'join_community'

    community = Community.objects.get(id=community_id)

    if request.method == "POST":

        question_data = request.POST.dict()
        print(question_data)
        response_list = []

        for key, value in question_data.items():
            question_dict = {}
            if key == 'csrfmiddlewaretoken':
                continue
            elif key == 'ref_id':
                continue
            question_dict['key'] = key
            question_dict['value'] = value
            response_list.append(question_dict)

        json_dict = {}
        json_dict['questions'] = response_list

        params = {'member_id': member_id, 'community_id': community_id,'ref_id':ref_id}
        rqst.post(join_url, params=params, json=json_dict)
        # return false to show thank you page the user has now answered the questions
        return False, user, similar_communities, community

    else:
        data = Form_data.objects.all().filter(community_id=community_id)

        if not data:
            params = {'member_id': member_id, 'community_id': community_id}
            rqst.post(join_url, params=params, json={})
            # return false to show thank you page as there are no questions for this community
            return False, user, similar_communities, community
        else:
            # return true to take the user to questions page
            return True, user, data, community


@login_required
def form_data(request, community_id):
    print(community_id)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []
    if request.method == "POST":
        print(request.POST.dict())
        res = request.POST.dict()
        community = Community.objects.all().filter(id=community_id)
        if 'college' in res:
            mForm_data = Form_data()
            mForm_data.data = 'College'
            mForm_data.community_id = community[0]
            mForm_data.data_type = 'text'
            mForm_data.save()
        if 'contact' in res:
            mForm_data = Form_data()
            mForm_data.data = 'Contact'
            mForm_data.community_id = community[0]
            mForm_data.data_type = 'text'
            mForm_data.save()
        if 'experience' in res:
            mForm_data = Form_data()
            mForm_data.data = 'Experience'
            mForm_data.community_id = community[0]
            mForm_data.data_type = 'text'
            mForm_data.save()
        if 'interests' in res:
            mForm_data = Form_data()
            mForm_data.data = 'Interests'
            mForm_data.community_id = community[0]
            mForm_data.data_type = 'text'
            mForm_data.save()
        count = 1
        q = 'question_'
        i = q + str(count)
        print(i)
        while (1):
            if i in res and res[i] != '':
                print(i)
                mForm_data = Form_data()
                mForm_data.data = res[i]
                mForm_data.community_id = community[0]
                mForm_data.data_type = res['response' + str(count)]
                mForm_data.save()
            else:
                break
            count = count + 1
            i = q + str(count)
    else:
        return render(request, 'form_data.html', {'usr': user})

    return redirect('comunity', community_id)


def thankyou(request):
    email = request.GET.get("mail")
    print("email = = ", email)
    mail = get_notified()
    mail.email = email
    mail.save()

    send_email(email)
    return render(request, 'thankyou2.html')


def send_email(email):
    ''' function to send email to user to be notified '''
    fail_silently = True
    to = email
    subject = email + " wants to be Notified"
    msg = EmailMultiAlternatives(subject,
                                 email,
                                 "Collabmates<hello@collabmates.com>",
                                 ['nipungoyal.iitd@gmail.com'],
                                 )
    return msg.send(fail_silently)


def my_communities(request, user_id):
    communities = Members.objects.all().filter(member_id=user_id)
    my_communities = []
    for i in communities:
        my_communities.append(i.community_id)

    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []
    return render(request, 'my_community.html', {'usr': user, 'my_communities': my_communities})


def communities_as_admin(request, user_id):
    communities = Admins.objects.all().filter(admin_id=user_id)
    admins_communities = []
    for i in communities:
        admins_communities.append(i.community_id)

    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []
    return render(request, 'communities_as_admin.html', {'usr': user, 'admins_communities': admins_communities})


def members_list(request, community_id):
    member_list = Members.objects.all().filter(community_id=community_id)
    members = []
    for i in member_list:
        user = Userinfo.objects.all().filter(user_id=i.member_id)
        if user:
            members.append(user[0])

    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []
    community = Community.objects.all().filter(id=community_id)
    return render(request, 'members.html', {'usr': user, 'members': members, 'community': community})


def user_response(request, community_id, user_id):
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []
    responses = Form_response.objects.all().filter(user=user_id, community=community_id)
    return render(request, 'user_response.html', {'usr': user, 'responses': responses})


def privacy(request):
    return render(request, 'privacy.html')


def terms(request):
    return render(request, 'terms.html')


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
    try:
        user=Userinfo.objects.get(user_id=request.user.id)
        user_image=user.image_file.url
    except:
        user_image=''

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
        member = Members.objects.filter(community_id = community,member_id_id = request.user)
        if member.exists():
            if member[0].state == 1 or member[0].state == 2 or member[0].state == 4 or member[0].state == 7:
                is_member = True


    context = {'card': collabcard_dict['collabcard']['title'],
               'creator': collabcard_dict['collabcard']['member']['name'],
               'image_url': collabcard_dict['collabcard']['member']['image_url'],
               'collabcard_id': collabcard_dict['collabcard']['id'],
               'answer_text': answer_text,
               'answers':collabcard_dict['answers'],
               'card_id':card_id,
               'user_image_url':user_image,
               'share_link': collabcard_dict['collabcard']['share_link'],
               'share_link_image':og_image,
               'community_id': collabcard_dict['collabcard']['community_id'],
               'community_name': community.name,
               'created_at':collabcard_dict['collabcard']['created_at'],
               'answers_count': len(collabcard_dict['answers']),
               'is_member':is_member,

               }
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
    member_id=request.GET.get('member_id')
    user_info=Userinfo.objects.get(user_id=member_id)
    user=UserinfoSerializer(user_info)
    collabcard_id=request.GET.get('collabcard_id')
    params={
        'member_id':member_id,
        'collabcard_id':collabcard_id
    }
    msg=request.GET.get('message')

    json_body={
        'title':msg
    }
    link=api_url+'create_answer'
    create_answer=rqst.post(link,params=params,json=json_body)
    return JsonResponse({'success':True,'msg':msg,'image_url':user['image_url'],'name':user['name']})


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


def check_user_tag(user_id, tag_id):
    ''' fucntion to check if user has a hidden tag already
     prevent user from having same tag twice'''
    user_tag = userinfo_tags.objects.filter(user_id=user_id, tag_id=tag_id)
    if user_tag:
        return True
    else:
        return False


def get_user_tag(user_id):
    ''' function to get user hidden tag '''
    user_tag = userinfo_tags.objects.all().filter(user_id=user_id)
    return user_tag


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


def pending_list(request,community_id):

    '''function to show pending list in html'''


    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

    link=api_url+'pending_members/'+str(community_id)

    res = rqst.get(link)
    user_image_url=""
    is_promoter = 'false'
    if request.user.is_authenticated:
        try:
            userinfo = Userinfo.objects.get(user_id=request.user.id)
        except:
            userinfo = update_user_info(request)

        # userinfo=Userinfo.objects.get(user_id=request.user.id)
        user_image_url=userinfo.image_file.url
        link=api_url+'members_state?member_id='+str(request.user.id)+'&community_id='+str(community_id)
        state=rqst.get(link)
        try:
            state=json.loads(state.content)
            if state['state'] == 1 or state['state'] == 2:
                is_promoter='true'
        except Exception as e:
            traceback.print_exc()
    pending_list=[]
    error=False
    try:
        pending_list = json.loads(res.content)['pending_members']
    except Exception as e:
        error=True
        traceback.print_exc()


    context={
        'pending_list':pending_list,
        'community_id':community_id,
        'user_image_url':url+user_image_url,
        'is_promoter':is_promoter,
        'list_length':len(pending_list),
        'error':error
    }
    return render(request,'pending_list.html',context)


def questions_responses(request):

    '''function to get responses of the particular user to show'''
    member_id=request.GET.get('member_id')
    community_id=request.GET.get('community_id')
    userinfo=Userinfo.objects.get(user_id=member_id)
    form_response=Form_response.objects.filter(user=member_id,community=community_id)
    response_list=[]
    for data in form_response:
        response={}
        response['question']=data.data
        response['answer']=data.response
        response_list.append(response)
    context={
        'image_url':url+userinfo.image_file.url,
        'response_list':response_list
    }
    return JsonResponse(context)


def get_or_create_tag(tag_name,tag_type):

    '''function to check whether the tag is existing tag or a new tag and
     if its new create it as un-categorized'''

    if len(tag_name) is 0:
        print('empty list')
        return 0

    try:
        tag_id=int(tag_name)
        return tag_id
    except:
        tag_name = tag_name.strip().title()
        try:
            tag = Tags_lpig.objects.get(name = tag_name)
        except:
            category = Category.objects.filter(Q(name__icontains=tag_type))[0]
            attribute = Attributes.objects.filter(Q(attribute_name__icontains=tag_type), Q(attribute_name__icontains='Uncategorized'))[0]
            tag = Tags_lpig()
            tag.name = tag_name
            tag.category_id = category
            tag.attribute_id = attribute
            tag.save()
            tag.tag_id = tag.id
            tag.save()
        return tag.id


def insert_tags_for_user(user_id,tag_list,typ):

    '''function to insert tags for user'''

    user=User.objects.get(id=user_id)

    print('insert function ========== ',tag_list,type(tag_list))

    '''updating the list based on type'''

    if typ == "Legacy":
        user_tags_list = list(User_Legacy.objects.filter(user_id=user).values_list("tags_id", flat=True))

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


def get_user_tags_from_list(tag_list,type):

    '''function to get user_tags from list from front end'''

    type_list=[]
    for tag in tag_list:
        tags_id=get_or_create_tag(tag,type)
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

            if tag.category_id.id == 4 and tag.attribute_id.id == 12:
                user_geography.append(tag)


    return user_legacy_work,user_legacy_education,user_legacy_hometown,user_geography


def get_user_profession_tags(user_id):

    user_profession = list(User_Profession.objects.filter(user_id = user_id).values_list('tags_id', flat=True))

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


    return user_profession_industry,user_profession_skill,user_profession_designation


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


    return user_interest_hobby,user_interest_sports,user_interest_fan,user_interest_cause


def get_community_legacy_tags(community_id):

    community_legacy = list(Community_Legacy.objects.filter(community_id=community_id).values_list('tags_id', flat=True))
    community_geo = list(Community_Geography.objects.filter(community_id=community_id).values_list('tags_id', flat=True))

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


    return community_legacy_work,community_legacy_education,community_legacy_hometown,community_geography


def get_community_profession_tags(community_id):

    community_profession = list(Community_Profession.objects.filter(community_id=community_id).values_list('tags_id', flat=True))

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


    return community_profession_industry,community_profession_skill,community_profession_designation


def get_community_interest_tags(community_id):

    community_interests = list(Community_Interest.objects.filter(community_id=community_id).values_list('tags_id', flat=True))

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


    return community_interest_hobby,community_interest_sports,community_interest_fan,community_interest_cause


# onboarding flow

def onboarding(request):

    '''function to show the legacy'''

    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

    if request.method == 'GET':

        community_id = request.GET.get('community_id',None)
        member_id = request.GET.get('member_id', None)
        if community_id:
            legacy_work, legacy_education, legacy_hometown, geography = get_community_legacy_tags(
                community_id)
        elif member_id:
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

        if is_request_android(request) and member_id:
            android = True


        education_tags = Tags_lpig.objects.filter(attribute_id=2).order_by('name')
        work_tags = Tags_lpig.objects.filter(attribute_id=1).order_by('name')
        hometown_tags = Tags_lpig.objects.filter(attribute_id=3).order_by('name')
        geography_tags = Tags_lpig.objects.filter(attribute_id=12).order_by('name')
        context={
            'legacy_education':education_tags,
            'legacy_work':work_tags,
            'legacy_hometown':hometown_tags,
            'geography':geography_tags,
            'community_legacy_work':legacy_work,
            'community_legacy_education':legacy_education,
            'community_legacy_hometown':legacy_hometown,
            'community_geography':geography,
            'community_id':community_id,
            'member_id': member_id,
            'android':android,
        }

        return render(request,'onboarding.html',context)
    else:

        user_id = request.POST.get('member_id', None)
        if not user_id:
            user_id=request.user.id

        legacy_education =request.POST.getlist('legacy_education[]')
        # legacy_work = request.POST.getlist('legacy_work[]')
        legacy_hometown = request.POST.getlist('legacy_hometown[]')
        geography=request.POST.getlist('loc[]')

        legacy_li = legacy_education + legacy_hometown   # + legacy_work

        type_list=get_user_tags_from_list(legacy_li,"Legacy")
        insert_tags_for_user(user_id,type_list,"Legacy")


        type_list=get_user_tags_from_list(geography,"Geography")
        insert_tags_for_user(user_id, type_list, "Geography")

        # for tag in legacy_hometown:
        #     insert_user_home_town_tags(user_id = user_id, tag=tag)

        return JsonResponse({'success':True})


def onboarding_profession(request):

    '''onboarding for profession'''

    if request.user.is_authenticated:
        try:
            user = Userinfo.objects.get(user_id=request.user.id)
        except:
            user = update_user_info(request)

    if request.method == 'GET':

        community_id = request.GET.get('community_id',None)
        member_id = request.GET.get('member_id', None)
        if community_id:

            profession_industry,profession_skill,profession_designation = get_community_profession_tags(community_id)
        elif member_id:
            profession_industry,profession_skill,profession_designation = get_user_profession_tags(member_id)
        elif not member_id:
            profession_industry,profession_skill,profession_designation = get_user_profession_tags(request.user.id)
        else:
            profession_industry = []
            profession_skill = []
            profession_designation = []

        android = False
        if is_request_android(request) and member_id:
            android = True

        industry_tags = Tags_lpig.objects.filter(attribute_id=6).order_by('name')
        skill_tags = Tags_lpig.objects.filter(attribute_id=5).order_by('name')
        designation_tags = Tags_lpig.objects.filter(attribute_id=7).order_by('name')
        context = {
            'profession_industry': industry_tags,
            'profession_skill': skill_tags,
            'profession_designation': designation_tags,
            'community_profession_industry': profession_industry,
            'community_profession_skill': profession_skill,
            'community_profession_designation': profession_designation,
            'community_id': community_id,
            'user_id' : member_id,
            'android': android,
        }

        return render(request, 'onboarding_profession.html', context)
    else:
        # user_id = request.user.id
        # print("post profession user id  ===== ",user_id)
        # user_id = request.POST.get('member_id', None)
        # print("post profession user id  ===== ",user_id)

        user_id = request.POST.get('member_id', None)
        if not user_id:
            user_id = request.user.id

        profession_industry = request.POST.getlist('profession_industry[]')
        profession_skill = request.POST.getlist('profession_skill[]')
        #profession_designation = request.POST.getlist('profession_designation[]')

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

        community_id = request.GET.get('community_id',None)
        member_id = request.GET.get('member_id', None)
        if community_id:

            interest_hobby, interest_sports, interest_fan, interest_cause = get_community_interest_tags(community_id)
        elif member_id:
            interest_hobby, interest_sports, interest_fan, interest_cause = get_user_interest_tags(member_id)
        elif not member_id:
            interest_hobby, interest_sports, interest_fan, interest_cause = get_user_interest_tags(request.user.id)
        else:
            interest_hobby = []
            interest_sports = []
            interest_fan = []
            interest_cause = []

        android = False

        if is_request_android(request) and member_id:
            android = True

        hobby_tags = Tags_lpig.objects.filter(attribute_id=9).order_by('name')
        sports_tags = Tags_lpig.objects.filter(attribute_id=10).order_by('name')
        fan_tags = Tags_lpig.objects.filter(attribute_id=11).order_by('name')
        cause_tags = Tags_lpig.objects.filter(attribute_id=8).order_by('name')

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
        }

        return render(request, 'interest_onboarding.html', context)

    else:
        # user_id = request.user.id

        user_id = request.POST.get('member_id', None)
        if not user_id:
            user_id = request.user.id

        interest_hobby = request.POST.getlist('interest_hobby[]')
        interest_sports = request.POST.getlist('interest_sports[]')
        interest_fan = request.POST.getlist('interest_fan[]')
        interest_cause = request.POST.getlist('interest_cause[]')

        interest_list = interest_hobby + interest_sports + interest_fan + interest_cause

        type_list = get_user_tags_from_list(interest_list, "Interests")
        insert_tags_for_user(user_id, type_list, "Interests")
        compute_rank(user_id=user_id)
        # if is_request_android(request):
        #     return JsonResponse({'user_agent': True})
        return JsonResponse({'user_agent': False})


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


def access_page(request):

    '''function to create an early access page and save early respose'''

    print('>>>>>>>>>>>    ',request.META)
    if request.method == "GET":
         return render(request,'access_page.html',{})
    else:
        user_id=request.user.id
        mobile_os=request.POST.get('mobile_os')
        email=request.POST.get('email')
        mobile_no=request.POST.get('mobile_no')
        platform_type=""
        try:
            user_info=Userinfo.objects.get(user_id=user_id)
            user_info.mobile_os=mobile_os
            user_info.secondary_email=email
            if mobile_no:
                user_info.contact_number= mobile_no
            else:
                user_info.contact_number = None
            user_info.save()

            if is_request_android(request):
                platform_type="Android"

            # send_mail_after_rank_computation.delay(user_id=user_id)
            send_mail_after_rank_computation.delay(user_id=user_id)

        except:

            print("error in userinfo")



    return JsonResponse({'success': True,'mobile_os':mobile_os,'platform_type':platform_type})


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
            context['college']=""
    return render(request,'alpha_page.html',context)


