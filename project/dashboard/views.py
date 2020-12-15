from django.shortcuts import render,redirect
from django.http import HttpResponse

from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import *
from togther.models import card_answers as CardAnswers
from togther.views import update_user_info
from django.views.generic import *
from collabmates_api.views import request_response
from .forms import *
from django.db.models import Q,Max
import time
import csv
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
from collabmates_api.notification import send_notification_for_join_requests, send_notification_to_proposed_admin,send_notification_for_new_collabcard_posted
from django.conf import settings
import json
from django.http.response import JsonResponse
from utility.states import collabcard_states, member_states
from django.views.decorators.csrf import csrf_exempt
from collabmates_api.raw_queries import compute_rank
from utility.pre_creation import pre_create_communities
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from urllib.parse import urlencode,quote
from utility.utils import (get_city_address, update_tag_image,
                           create_or_categorize_tag, update_user_geography_tags,
                           insert_user_home_town_tags, update_hometown_tags_for_all_users,
                           user_onbaord)
from utility.celery_tasks import update_last_unseen_in_engage_on_card_creation

from utility.firebase import (upload_tag_files, upload_user_files,
                              upload_community_files, upload_community_thumbnail,
                              upload_tag_thumbnail)
from django.contrib.auth import authenticate, login

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import logout
from collabmates_api.views import send_email_for_collabcard
url = settings.URL
# uncomment to run it in localhost
url='http://likeminds.community'
error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()
api_url = url + '/api/'


def admin_login(request):

    if request.method == 'GET':

        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin_dashboard')
            else:
                logout(request)

        return render(request,'dashboard/login.html',{})
    else:
        username = request.POST.get("username",'')
        passcode = request.POST.get("passcode",'')

        user = authenticate(username=username, password=passcode)
        # user is not found
        if not user:
            return JsonResponse({'success': False,'raise_error':True})
        # if user is found , login user
        login(request, user)

        # if super user, redirect to admin dashboard
        if request.user.is_superuser:
            return JsonResponse({'success':True,'is_super_user':True})
        # if not super user, redirect to communities
        elif not request.user.is_superuser:
            return JsonResponse({'success':True,'is_super_user':False})
        # else raise validation error
        else:
            return JsonResponse({'success': False,'raise_error':True})


@login_required
def admin_logout(request):
    logout(request)
    return redirect('admin_login')


def dashboard(request):
    '''function to give list of community to edit'''

    if request.user.is_authenticated:
        if not request.user.is_superuser:
            return redirect('signup')
    else:
        return redirect('admin_login')

    select_type=request.GET.get('filter',None)
    dashboard_list=[]
    if select_type == 'pilot_live':
        community_list = Community.objects.filter(hide_community='4').order_by('-updated_at')
    elif select_type == 'pilot_0_interested':
        community_list = Community.objects.filter(hide_community='3').filter(members_count=0).order_by('-updated_at')
    elif select_type == 'pilot_1_interested':
        community_list = Community.objects.filter(hide_community='3').filter(members_count__gte=1).order_by(
            '-updated_at')
    elif select_type == 'user_created':
        community_list = Community.objects.filter(hide_community='0').order_by('-updated_at')
    elif select_type == 'members_count_ascending':
        community_list = Community.objects.order_by('members_count', '-updated_at')
    elif select_type == 'members_count_descending':
        community_list = Community.objects.order_by('-members_count', '-updated_at')
    elif select_type == 'interested_count_ascending':
        community_list = Community.objects.filter(hide_community='3').order_by('members_count', '-updated_at')
    elif select_type == 'interested_count_descending':
        community_list = Community.objects.filter(hide_community='3').order_by('-members_count', '-updated_at')
    else:
        community_list = Community.objects.order_by('-updated_at')

    search_key=request.GET.get('search_key',None)
    if search_key:
        tag_name=Tags_lpig.objects.filter(name__iexact=search_key)
        if tag_name:
            category_id=tag_name[0].category_id.id
            tag_id=tag_name[0].tag_id
            tag=Tags_lpig.objects.get(id=tag_id)
            if category_id == 1:
                community_list = list(Community_Legacy.objects.filter(tags_id=tag).values_list('community_id_id',flat=True))
            elif category_id == 2:
                community_list = list(Community_Profession.objects.filter(tags_id=tag).values_list('community_id_id',flat=True))
            elif category_id == 3:
                community_list = list(Community_Interest.objects.filter(tags_id=tag).values_list('community_id_id',flat=True))
            elif category_id == 4:
                community_list = list(Community_Geography.objects.filter(tags_id=tag).values_list('community_id_id',flat=True))


    page = request.GET.get('page', 1)
    paginator = Paginator(community_list, 20)
    try:
        community_list = paginator.page(page)
    except PageNotAnInteger:
        community_list = paginator.page(1)
    except EmptyPage:
        community_list = paginator.page(paginator.num_pages)

    for i in community_list:
        if isinstance(i,int):
            i=Community.objects.get(id=i)
        community_dic={}
        if i.hide_community == '2':
            continue
        community_dic['id'] = i.id
        community_dic['name'] = i.name
        community_dic['image_url'] = i.image_url if i.image_url else None
        community_dic['purpose'] = i.purpose
        pending_members_count = Members.objects.filter(community_id=i, state=3).count()
        community_dic['pending_member_count'] = pending_members_count
        members_count = Members.objects.filter(community_id=i).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7)).count()
        community_dic['members_count'] = members_count
        community_dic['active_since'] = i.active_since
        community_dic['question_count'] = communityQuestions.objects.filter(community=i).count()
        community_dic['hidden_tags_count'] = get_tags_count(i)
        community_dic['image_link'] = i.image_link
        dashboard_list.append(community_dic)

    #tags_queryset=Tags_lpig.objects.order_by('name')
    tags=[]
    # for tag in tags_queryset:
    #     temp={}
    #     temp['id']=tag.id
    #     temp['name']=tag.name
    #     temp['attribute']=tag.attribute_id.attribute_name
    #     tags.append(temp)

    context={'communities':dashboard_list,
             'community':community_list,
              'tags': tags,
              'select_type':select_type,
             'search_key':search_key,
             'url':url}
    info_logger.info(context)
    return render(request,'dashboard/dashboard.html',context)


def get_tags_count(community):

    '''function to get count of tags from dashboard'''

    tags_count = 0

    hidden_legacy_tags = list(Community_Legacy.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_profession_tags = list(Community_Profession.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_interests_tags = list(Community_Interest.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_geography_tags = list(Community_Geography.objects.filter(community_id=community).values_list('tags_id', flat=True))


    for tag in hidden_legacy_tags:
        global_tag = Tags_lpig.objects.get(name='legacy_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_profession_tags:
        global_tag = Tags_lpig.objects.get(name='profession_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_interests_tags:
        global_tag = Tags_lpig.objects.get(name='interest_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_geography_tags:
        global_tag = Tags_lpig.objects.get(name='Global')
        if tag == global_tag.id:
            continue
        tags_count += 1

    return tags_count


def update_form(request,community_id):
    '''function to update form for community and also purpose collabcard'''
    if request.method == 'POST':

        community=Community.objects.get(id=community_id)
        community.updated_at=time.time()


        community_form=CommunityForm(request.POST,request.FILES,instance=community)
        admins=Members.objects.filter(community_id=community).filter(Q(state=1)|Q(state=2))
        member_id=0
        purpose=""

        hide_community=3
        if community_form.is_valid():
            purpose=community_form.cleaned_data['purpose']
            purpose_community = purpose
            for_string=purpose.split(' ', 1)[0]
            purpose = "Created this community " + for_string.lower() + purpose.split("For", 1)[1]
            hide_community=community_form.cleaned_data['hide_community']


            name = community_form.cleaned_data['name']
            about = community_form.cleaned_data['about']
            location = community_form.cleaned_data['location']

            community.name = name
            community.about = about
            community.location = location
            community.purpose = purpose_community
            community.hide_community = hide_community

            #uploading community image to firebase
            image = community_form.cleaned_data['image_url']
            image_link = upload_community_files(community_id=community_id, image=image, url=False)

            # saving image link in community object
            community.image_link = image_link

            # saving community image thumbnail
            upload_community_thumbnail.delay(community_id=community_id,image_url=image_link)

            community.save()


        else:
            print("some error is there")
        if admins:
            for admin in admins:
                member_id=admin.member_id
                break

        if hide_community != '3':
            try:
                collabcard=Collabcard.objects.get(id=community.purpose_collabcard)
                collabcard.title=purpose
                collabcard.save()
            except:
                collabcard=Collabcard()
                collabcard.title = purpose
                collabcard.user = member_id
                collabcard.community_id = community_id
                collabcard.date_epoch = time.time()
                collabcard.save()
                community.purpose_collabcard=collabcard.id
                community.save()
            community.save()
        else:
            community.save()


        return redirect('admin_dashboard')
    else:
        community=Community.objects.get(id=community_id)
        community_form=CommunityForm(instance=community)

    context={'community_form':community_form,'community':community}
    return render(request,'dashboard/community.html',context)


def community_delete(request,community_id):
    '''function to delete the community'''
    community=Community.objects.get(id=community_id)
    community.hide_community='2'
    community.save()
    #deleting the member state
    Members.objects.filter(community_id=community_id).update(state=0)
    return redirect('admin_dashboard')


def deleted_communities(request):

    '''function to show all the deleted communities'''

    community_list=Community.objects.filter(hide_community='2')
    context={
        'community_list':community_list
    }
    return render(request,'dashboard/delete_communities.html',context)


def add_dashboard_admin(request,community_id):

    '''function to add admin'''
    if request.method == 'POST':
        community = Community.objects.get(id=community_id)
        admin_form = AdminForm(request.POST)
        if admin_form.is_valid():
            email_id=admin_form.cleaned_data['email']
            user_id=Userinfo.objects.get(email=email_id)

            member_data=Members.objects.filter(community_id=community,member_id=user_id.user_id)
            if member_data:
                Members.objects.filter(community_id=community_id,member_id=user_id.user_id).update(state=1)
            else:
                m=Members()
                m.community_id=community
                m.member_id=user_id.user_id
                m.state=1
                m.save()
            update_member_count(community_id)
        return redirect('admin_dashboard')
    else:
        community=Community.objects.get(id=community_id)
        admin_form = AdminForm(request.POST)
    context = {'admin_form': admin_form, 'community': community}
    return render(request, 'dashboard/add_admin.html', context)


def update_member_count(community_id):
    community = Community.objects.get(id=community_id)
    count = Members.objects.filter(community_id=community).filter(Q(state=1)|Q(state=2)|Q(state=4))
    community = Community.objects.filter(id=community_id).update(members_count = len(count))
    return


def add_dashboard_member(request,community_id):
    '''function to add members'''

    if request.method == 'POST':
        community = Community.objects.get(id=community_id)
        member_form = MemberForm(request.POST)
        if member_form.is_valid():
            email_id = member_form.cleaned_data['email']
            user_id = Userinfo.objects.get(email=email_id)

            member_data = Members.objects.filter(community_id=community, member_id=user_id.user_id)
            if member_data:
                Members.objects.filter(community_id=community_id, member_id=user_id.user_id).update(state=4)
            else:
                m = Members()
                m.community_id = community
                m.member_id = user_id.user_id
                m.state = 4
                m.save()
            update_member_count(community_id)
        return redirect('admin_dashboard')
    else:
        community = Community.objects.get(id=community_id)
        member_form = MemberForm(request.POST)
    context = {'member_form': member_form, 'community': community}
    return render(request, 'dashboard/add_member.html', context)


def show_pending_members(request,community_id):
    '''function to show pending members'''
    community = Community.objects.get(id=community_id)
    pending_members=Members.objects.filter(community_id=community).filter(state=3)

    context={'pending_members':pending_members,'community_id':community_id}
    return render(request,'dashboard/pending_list.html',context)


def aprove_member(request,community_id,member_id):
    '''function to approve member'''

    status = request.GET.get('status')
    redirect_url = True if request.GET.get('redirect') == 'true' else False
    req_dict = {
        'member_id': member_id,
        'community_id': community_id,
    }
    accepted = ''
    if status == 'approved':
        accepted = True
    else:
        accepted = False
        if status == 'delete':
            req_dict['send_notification'] = False

    req_dict['accepted'] = accepted

    request_response(request, req_dict)
    update_member_count(community_id)

    if not redirect_url:
        url='/admin_dashboard/all_members/'+str(community_id)
    else:
        url='/community/'+str(community_id)

    return redirect(url)


# def decline_member(request,community_id,member_id):
#     '''function to approve member'''
#     community = Community.objects.get(id=community_id)
#
#     Members.objects.filter(community_id=community,member_id=member_id).update(state=5)
#     url='/admin_dashboard/all_members/'+str(community_id)
#     send_notification_for_join_requests.delay(community_id,False,member_id)
#
#     return redirect(url)


def show_tags(request,community_id):
    '''Taging communitites'''
    categories=Community_tags.objects.filter(community_id=community_id).exclude(state=1)
    category_string=""
    for i in categories:
        if i.tags_id == 41 or i.tags_id == 42:
            continue
        category_string=category_string+str(i) + ","
    category_string=category_string[:-1]
    context={
        'category':category_string,
        'community_id':community_id
    }
    return render(request,"dashboard/category.html",context)


def add_tags(request):

    categories=request.GET.get('categories')
    community_id=request.GET.get('community_id')
    categories=categories.split(",")
    already_category=request.GET.get('already_category')
    already_category=already_category.split(",")

    category_list=[]
    community_category=Community_tags.objects.filter(community_id=community_id)

    for category in community_category:

        # do not delete the hidden tags of a community
        if category.tags_id == 41 or category.tags_id ==42:
            continue
        category_list.append(str(category))

    for category in category_list:
        if category not in already_category:
            
            Community_tags.objects.filter(community_id=community_id,category=category).delete()

    for category in categories:

        selected_categories=Community_tags.objects.filter(community_id=community_id,category=category)
        if not selected_categories:
            cat=Community_tags()
            cat.community_id=Community.objects.get(id=community_id)
            cat.category=category
            tags_id=Tags.objects.filter(category_name=category).values('id')
            if len(tags_id) == 0:
                continue
            cat.tags_id=tags_id[0]['id']
            cat.save()
    return JsonResponse({'success':True})


def all_user(request):

    '''dashboard to show all users'''
    userinfo=Userinfo.objects.all().order_by('-user_id')

    page = request.GET.get('page', 1)
    paginator = Paginator(userinfo, 20)
    try:
        userinfo = paginator.page(page)
    except PageNotAnInteger:
        userinfo = paginator.page(1)
    except EmptyPage:
        userinfo = paginator.page(paginator.num_pages)

    users_list = []
    for i in userinfo:
        user_dic = {}
        user_dic['id'] = i.id
        user_dic['user_id'] = i.user_id.id
        user_dic['name'] = i.name
        user_dic['email'] = i.email
        user_dic['image_url'] = i.image_file

        if i.image_link:
            user_dic['image_link'] = i.image_link
        else:
            user_dic['image_link'] = None


        if i.fcm_token:
            #print("has token")
            user_dic['fcm_token'] = 1
            user_dic['color']='green'
        else:
            #print("no token")
            user_dic['fcm_token'] = 0
            user_dic['color'] = 'Red'

        if i.mobile_os :
            if i.mobile_os == 'Android':
                user_dic['os'] = 'Android'

            elif i.mobile_os == 'Both':
                user_dic['os'] = 'Android and iOS Both'
            else:
                user_dic['os'] = 'iOS'

        else:
            user_dic['os'] = 'Web'

        tags = []
        #tags_count = tags.count()
        tags_list=[]
        for t in tags:
            tag = Tags.objects.get(id = t.tag_id)
            tags_list.append(tag.category_name)

        user_tags = get_user_tags_count(i.user_id)

        if user_tags > 0:
            user_dic['tags_count'] = user_tags
        else:
            user_dic['tags_count'] = 0
        user_dic['fb_link'] = i.fb_link
        user_dic['linkedin_link'] = i.linkedin_link

        communities_count = Members.objects.all().filter(member_id=i.user_id).filter(~Q(state=0)).count()
        user_dic['communities_count']=communities_count
        users_list.append(user_dic)
    return render(request, 'dashboard/all_user.html', {'all_user': users_list,'paginator':userinfo})


def get_user_tags_count(user_id):

    tags_count = 0

    hidden_legacy_tags = list(User_Legacy.objects.filter(user_id=user_id).values_list('tags_id', flat=True))
    hidden_profession_tags = list(User_Profession.objects.filter(user_id=user_id).values_list('tags_id', flat=True))
    hidden_interests_tags = list(User_Interest.objects.filter(user_id=user_id).values_list('tags_id', flat=True))
    hidden_geography_tags = list(User_Geography.objects.filter(user_id=user_id).values_list('tags_id', flat=True))


    for tag in hidden_legacy_tags:
        global_tag = Tags_lpig.objects.get(name='legacy_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_profession_tags:
        global_tag = Tags_lpig.objects.get(name='profession_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_interests_tags:
        global_tag = Tags_lpig.objects.get(name='interest_any')
        if tag == global_tag.id:
            continue
        tags_count += 1

    for tag in hidden_geography_tags:
        global_tag = Tags_lpig.objects.get(name='Global')
        if tag == global_tag.id:
            continue
        tags_count += 1

    return tags_count


def update_user(request,user_id):
    if request.method == 'POST':

        user_info = Userinfo.objects.get(user_id = user_id)
        # old_image_file = user_info.image_file
        user_info_form=UserForm(request.POST, request.FILES or None, instance=user_info)
        # deleting the old file after new file is updated
        if user_info_form.is_valid():
            # get the new image file
            name = user_info_form.cleaned_data['name']
            city = user_info_form.cleaned_data['city']
            contact_number = user_info_form.cleaned_data['contact_number']
            interests = user_info_form.cleaned_data['interests']
            fb_link = user_info_form.cleaned_data['fb_link']
            linkedin_link = user_info_form.cleaned_data['linkedin_link']
            fcm_token = user_info_form.cleaned_data['fcm_token']
            login_type = user_info_form.cleaned_data['login_type']

            user_info.name = name
            user_info.city = city
            user_info.contact_number = contact_number
            user_info.interests = interests
            user_info.fb_link = fb_link
            user_info.linkedin_link = linkedin_link
            user_info.fcm_token = fcm_token
            user_info.login_type = login_type

            image = user_info_form.cleaned_data['image_file']
            image_link = upload_user_files(user_id=user_id, image=image, url=False)
            user_info.image_link = image_link
            user_info.save()

        return redirect('all_user')
    else:
        try:
            user_info = Userinfo.objects.filter(user_id = user_id)
            user_info_form = UserForm(instance=user_info[0])
            context = {'user_info_form': user_info_form,'user_info':user_info[0]}
        except Exception as e:

            context={'error':'Some Technical Error'}

    return render(request,'dashboard/update_links.html',context)


def send_invitation(request,community_id):
    '''function to send invite to members'''
    if request.method == 'POST':
        community = Community.objects.get(id=community_id)
       
        send_nominated_email=SendNominatedEmail(request.POST)
        if send_nominated_email.is_valid():
            proposer_name=send_nominated_email.cleaned_data['proposer_name']
            proposed_name=send_nominated_email.cleaned_data['proposed_name']
            proposed_email=send_nominated_email.cleaned_data['proposed_email']
            proposer_email=send_nominated_email.cleaned_data['proposer_email']
            proposed_no=send_nominated_email.cleaned_data['proposed_no']
            proposed_admin = User.objects.filter(email=proposer_email).first()

            admin = temp_admin()
            admin.name = proposed_name
            admin.email = proposed_email
            admin.contact_number = proposed_no
            admin.community = community
            admin.member_id = proposed_admin.id
            admin.save()
            check = check_member(proposed_email,community_id,proposed_admin.id,proposed_name)
            return redirect('admin_dashboard')
    else:
        send_nominated_email=SendNominatedEmail()
        context={'send_email':send_nominated_email}
        return render(request,'dashboard/send_invitation.html',context)


def check_member(email,community_id,member_id,proposed_name):
    ProposedAdmin = User.objects.filter(id = member_id).first()
    community = Community.objects.get(id = community_id)
    CommunityName=community.name
    email=email.lower().strip()
    proposedAdminState = Members.objects.filter(member_id=ProposedAdmin.id,community_id = community)
    proposedAdminState = proposedAdminState[0].state
    ProposedAdmin = Userinfo.objects.get(user_id  = ProposedAdmin.id)
    ProposedAdmin = ProposedAdmin.name
    try:
        user = Userinfo.objects.filter(email=email)

        if user:
            NominatedAdmin=user[0].name
            NominatedAdmin_id = user[0].user_id.id
        else:
            send_email_to_nominated_admin(NominatedAdmin=proposed_name,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            return False
    except:
        send_email_to_nominated_admin(NominatedAdmin=proposed_name,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
        return False
    if user:
        member =Members.objects.filter(community_id = community,member_id = user[0].user_id.id)
        if member and member[0].state == 4:
            Members.objects.filter(community_id = community,member_id = user[0].user_id.id).update(state=7)
            send_email_to_nominated_admin(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )
        elif member and (member[0].state == 6 or member[0].state == 7):
            send_email_to_nominated_admin(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )
            print("member is already a nominated promoter")
        elif member and (member[0].state == 1 or member[0].state == 2):
            return True

        elif member and (member[0].state == 3 or member[0].state == 5):
            Members.objects.filter(community_id = community,member_id = user[0].user_id.id).update(state=6)
            send_email_to_nominated_admin(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
                                                proposedAdminState=proposedAdminState, CommunityName=CommunityName,
                                                community_id=community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id=NominatedAdmin_id, community_id=community.id,
                                                      proposed_admin_name=ProposedAdmin)

        else:
            print("member is created")
            member =Members()
            member.community_id = community
            member.member_id = user[0].user_id
            member.state = 6
            member.save()
            send_email_to_nominated_admin(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )
        return True
    return False


def send_email_to_nominated_admin(NominatedAdmin,email,ProposedAdmin,CommunityName,community_id,proposedAdminState):
    fail_silently=True
    to = email
    url = settings.URL
    url = url + "/community/" + str(community_id) + "?source=email&cta=accept_admin"
    subject =str(ProposedAdmin)+ " has proposed you as promoter of "+str(CommunityName)+" community"
    if proposedAdminState == 1:
        print("proposed admin state  == 1")
        template = get_template("mails/accept_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id,'url':url})
    elif proposedAdminState == 2:
        print("proposed admin state  == 2")
        template = get_template("mails/accept_temp_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id,'url':url})
    msg = EmailMultiAlternatives(subject,
                                     template,
                                     "LikeMinds<hello@likeminds.community>",
                                     [to],
                                     )
    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)


def all_members(request,community_id):

    '''function to show all members of the community'''

    members_info=Members.objects.filter(community_id=community_id).order_by('created_at')
    form_responses=communityAnswers.objects.filter(community=community_id)
    print(form_responses)
    has_questions=False
    if form_responses:
        has_questions=True

    members_list=[]

    fcm_count = 0
    for i in members_info:
        member={}
        member['id']=i.member_id
        if i.state == 1 or i.state == 2:
            member['state']='Promoter'
        elif i.state == 3:
            member['state']='Pending'
        elif i.state == 4:
            member['state']='Member'
        elif i.state == 6:
            member['state']='Nominated Promoter'
        elif i.state == 7:
            member['state']='Nominated Promoter(already a member)'
        elif i.state == 5:
            member['state']='Declined by Promoter'
        elif i.state == 8:
            member['state']='Interested Member'
        elif i.state == 9:
            member['state']='Eligible Promoter'

        userinfo = Userinfo.objects.filter(user_id=i.member_id)
        if not userinfo.exists():
            user = update_user_info(request=None, member_id=i.member_id.id)
        else:
            if userinfo[0].fcm_token:
                fcm_count+=1
        # image_url=Userinfo.objects.filter(user_id=i.member_id).values('image_file')
        # image_url=image_url[0]['image_file']
        # member['image_file']=image_url
        member['community_id']=community_id
        members_list.append(member)

    unregistered_users = temp_admin.objects.filter(community_id=community_id)
    unregitered_users_list = []
    for user in unregistered_users:
        member={}
        member['name'] = user.name
        member['email'] = user.email
        member['contact_number'] = user.contact_number
        member['state'] = 'Unregistred user NOMINATED as promoter'
        userinfo=Userinfo.objects.filter(email=user.email)
        if userinfo:
            continue

        unregitered_users_list.append(member)

    return render(request,'dashboard/all_members.html',{'member_list':members_list,
                                                        'unregitered_users_list':unregitered_users_list,
                                                        'has_questions':has_questions,
                                                        'fcm_count':fcm_count})


def delete_members(request,community_id,member_id):

    '''function to delete the members'''

    promoter_count = Members.objects.filter(community_id=community_id).filter(Q(state=1) | Q(state=2)).count()
    state_of_member = Members.objects.filter(community_id=community_id, member_id=member_id).values('state')
    member_state = state_of_member[0]['state']

    if promoter_count == 1 and (member_state == 1 or member_state == 2):
        return HttpResponse("You cannot Delete the promoter.First make a promoter in order to delete")
    Members.objects.filter(community_id=community_id, member_id=member_id).delete()
    update_member_count(community_id)

    return redirect('admin_dashboard')


def show_member_responses(request,community_id,member_id):

    ''' function to show member responses '''
    form_responses=communityAnswers.objects.filter(member=member_id,community=community_id)
    response_list=[]
    community_instance=Community.objects.get(id=community_id)
    user_instance=User.objects.get(id=member_id)
    for response in form_responses:
        temp={}
        temp['question']=response.question_title
        temp['answer']=response.question_answer
        response_list.append(temp)
    context={
        'response_list':response_list,
        'community_name':community_instance.name,
        'user_name':user_instance.userinfo.name
    }
    print(context)
    return render(request,'dashboard/show_form_response.html',context)

def add_questions(request,community_id):

    '''function to add and edit questions'''
    questions=communityQuestions.objects.filter(community=community_id).order_by('id')

    community_name=Community.objects.filter(id=community_id).values('name')
    question_list=[]
    for question in questions:
        question_list.append(question)

    if request.method == "GET":

        context={
            'question_list':question_list,
            'community_name':community_name[0]['name'],
            'length':len(question_list),
            'community_id':community_id
        }
        return render(request,'dashboard/add_questions.html',context)
    else:

        question_data=request.POST.get('data',None)
        if question_data is not None:
            question_data=json.loads(question_data)

            for question in question_data:

               if len(question['question']) == 0:
                   continue
               if question['update']:
                   communityQuestions.objects.filter(id=question['id']).update(question_title=question['question'])
               else:
                   community = Community.objects.get(id=community_id)
                   if not communityQuestions.objects.filter(community=community,question_title=question['question']).exists():
                       form_data=communityQuestions()
                       form_data.community=community
                       form_data.question_title=question['question']
                       form_data.value="text"
                       form_data.save()

            return JsonResponse({"success": True})
        return JsonResponse({"success": False})


def delete_questions(request,question_id):
    '''function to delelte the questions'''
    form_data=communityQuestions.objects.filter(id=question_id)
    community_id=0
    for i in form_data:
        community_id=i.community.id
    communityQuestions.objects.filter(id=question_id).delete()
    url='/admin_dashboard/add_questions/'+str(community_id)
    return redirect(url)


def add_dropdown_responses(request,question_id):

    '''adding the dropdown reponses'''
    form_data = communityQuestions.objects.get(id=question_id)
    if request.method == "GET":

        # dropdown_list=["Ford", "BMW", "Fiat"]
        # form_data.dropdown_list=json.dumps(dropdown_list)
        # form_data.save()
        dropdown_list=[]
        dropdown_status=0
        if form_data.question_state:
            if form_data.value[0] == '[':
                form_data.value = form_data.value[1:]
            if form_data.value[-1] == ']':
                form_data.value = form_data.value[:-1]

            if '$' in form_data.value:
                dropdown_list=form_data.value.split("$#")
            else:
                dropdown_list=form_data.value.split(",")
            for index, item in enumerate(dropdown_list):
                item = item.strip()
                if item[0] == '"':
                    item = item[1:]
                if item[-1] == '"':
                    item = item[:-1]
                community_state = form_data.community.hide_community
                if community_state:
                    find_index = item.find(":")
                    if find_index != -1:
                        item = item[find_index + 1:-1].strip()
                        if item[0] == '"':
                            item = item[1:-1]
                dropdown_list[index] = item
            dropdown_status=form_data.question_state

        context={
                'dropdown_list':dropdown_list,
                'question_id':question_id,
                'question_name':form_data.question_title,
                'length':len(dropdown_list),
                'dropdown_status': dropdown_status,
                'dropdown_selection_limit':form_data.dropdown_selection_limit
        }
        return render(request,'dashboard/add_questions_dropdown.html',context)
    else:
        option_data=request.POST.get('data')
        option_data=json.loads(option_data)
        dropdown_state=request.POST.get('dropdown_state')
        dropdown_limit=request.POST.get('dropdown_selection_limit')

        # if form_data.community.hide_community == '5':
        #     return JsonResponse({"success": True})

        dropdown_list=[]

        for option in option_data:
            dropdown_list.append(option['option'])
        if dropdown_list:
            if dropdown_list[0][0] == '[':
                dropdown_list[0] = dropdown_list[0][1:]
                dropdown_list[-1] = dropdown_list[-1][:-1]

            # dropdown_list=" $# ".join(dropdown_list)
            ans = []
            for value in dropdown_list:
                temp = {}
                temp['value'] = value
                ans.append(temp)
            dropdown_list = json.dumps(ans)

            form_data.value=dropdown_list
            form_data.question_state=dropdown_state
            form_data.dropdown_selection_limit=dropdown_limit if dropdown_limit else None
            form_data.save()
            return JsonResponse({"success": True})
        else:
            form_data.value=None
            form_data.question_state=0
            form_data.save()
            return JsonResponse({"success":False})
    # print(form_data)


def analytics(request):
    ''' function to show the analytics '''

    community_count=Community.objects.all().count()
    public_communities=Community.objects.filter(Q(hide_community='0')|Q(hide_community ='4')).count()
    private_communities=Community.objects.filter(hide_community='1').count()
    pre_created_communities=Community.objects.filter(hide_community='3').count()

    user_count=Userinfo.objects.all().count()
    promoter_member_count=Members.objects.filter(~Q(state=0)).values('member_id').distinct().count()
    working_communitites=Community.objects.filter(Q(hide_community= 2))


    promoter_count=Members.objects.filter(Q(state=1)|Q(state=2)).values('member_id').distinct().count()
    total_promoter_count = Members.objects.filter(Q(state=1)|Q(state=2)).values('member_id').count()
    member_count=Members.objects.filter(state=4).values('member_id').distinct().count()
    total_member_count = Members.objects.filter(state=4).values('member_id').count()
    conversations_count=Collabcard.objects.all().count()
    responses_count=CardAnswers.objects.all().count()

    pilot_live = Community.objects.filter(hide_community='4').count()
    pilot_0_interested = Community.objects.filter(hide_community='3').filter(members_count=0).count()
    pilot_1_interested = Community.objects.filter(hide_community='3').filter(members_count__gte=1).count()
    user_created = Community.objects.filter(hide_community='0').count()
    all_communities = Community.objects.all().count()


    context={
        'community_count':community_count,
        'public_communities':public_communities,
        'private_communities':private_communities,
        'user_count':user_count,
        'promoter_member_count':promoter_member_count,
        'promoter_count':promoter_count,
        'member_count':member_count,
        'conversations_count':conversations_count,
        'responses_count':responses_count,
        'total_promoter_count': total_promoter_count,
        'total_member_count': total_member_count,
        'pre_created_communities':pre_created_communities,
        'pilot_live':pilot_live,
        'pilot_0_interested': pilot_0_interested,
        'pilot_1_interested': pilot_1_interested,
        'user_created': user_created,
        'all_communities': all_communities,

    }
    return render(request,'dashboard/analytics.html',context)


def analytics_community(request,community_id):

    '''function to show analytics of community'''

    collabcard=Collabcard.objects.filter(community_id=community_id)
    collabcard_count=0
    collabcard_answer_count=0

    for each_collabcard in collabcard:
        collabcard_count=collabcard_count+1
        answer_count=CardAnswers.objects.filter(card_id=each_collabcard.id).count()
        collabcard_answer_count=collabcard_answer_count+answer_count

    context={
        'conversations_count':collabcard_count,
        'answers_count':collabcard_answer_count
    }

    return render(request,'dashboard/community_analytics.html',context)


def hidden_tags(request,community_id):

    '''function to show hidden tags'''

    community = Community.objects.get(pk = community_id)

    legacy_tags = list(Tags_lpig.objects.filter(category_id__id = '1').values_list('name', flat=True))
    profession_tags = list(Tags_lpig.objects.filter(category_id__id = '2').values_list('name', flat=True))
    interests_tags = list(Tags_lpig.objects.filter(category_id__id = '3').values_list('name', flat=True))
    geography_tags = list(Tags_lpig.objects.filter(category_id__id = '4').values_list('name', flat=True))


    # hidden_tags = Community_LPIG.objects.filter(community_id=community_id)

    hidden_legacy_tags = list(Community_Legacy.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_profession_tags = list(Community_Profession.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_interests_tags = list(Community_Interest.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_geography_tags = list(Community_Geography.objects.filter(community_id=community).values_list('tags_id', flat=True))


    hidden_legacy_tag = ''
    hidden_profession_tag = ''
    hidden_interests_tag = ''
    hidden_geography_tag = ''


    for tag in hidden_legacy_tags:
        global_tag = Tags_lpig.objects.get(name='legacy_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_legacy_tag=hidden_legacy_tag+tag_object.name+","
        except:
            pass

    for tag in hidden_profession_tags:
        global_tag = Tags_lpig.objects.get(name='profession_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_profession_tag=hidden_profession_tag+tag_object.name+","
        except:
            pass


    for tag in hidden_interests_tags:
        global_tag = Tags_lpig.objects.get(name='interest_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_interests_tag=hidden_interests_tag+tag_object.name+","
        except:
            pass


    for tag in hidden_geography_tags:
        global_tag = Tags_lpig.objects.get(name='Global')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_geography_tag = hidden_geography_tag+tag_object.name+","
        except:
            pass

    context={
        'legacy_tags':legacy_tags,
        'profession_tags':profession_tags,
        'interests_tags':interests_tags,
        'geography_tags':geography_tags,
        'hidden_legacy_tag':hidden_legacy_tag,
        'hidden_profession_tag': hidden_profession_tag,
        'hidden_interests_tag': hidden_interests_tag,
        'hidden_geography_tag': hidden_geography_tag,
        'community_id':community_id,
        'community_name':community.name
    }

    return render(request,'dashboard/hidden_tags.html',context)


def add_hidden_tags(request):

    '''function to add hidden tags'''

    legacy_tags=request.GET.get('legacy_tags')
    community_id=request.GET.get('community_id')

    profession_tags = request.GET.get('profession_tags')
    interest_tags = request.GET.get('interests_tags')
    grography_tags = request.GET.get('grography_tags')


    legacy_tags = legacy_tags.split(",")
    profession_tags = profession_tags.split(",")
    interest_tags = interest_tags.split(",")
    grography_tags = grography_tags.split(",")


    legacy_tags = get_or_create_tag_attributes_list(legacy_tags, 'Legacy')
    profession_tags = get_or_create_tag_attributes_list(profession_tags, 'Profession')
    interest_tags = get_or_create_tag_attributes_list(interest_tags, 'Interests')
    grography_tags = get_or_create_tag_attributes_list(grography_tags, 'Geography')


    save_community_lpig_tags(community_id= community_id,
                        legacy_tags= legacy_tags ,
                        profession_tags = profession_tags,
                        interest_tags=interest_tags,
                        grography_tags=grography_tags)

    # compute_rank(community_id=community_id)

    return JsonResponse({'success':True})


def save_community_lpig_tags(community_id,legacy_tags,profession_tags,interest_tags,grography_tags):
    ''' fucntion to save tags for a community '''

    community = Community.objects.get(id=community_id)

    try:
        community_tag = Community_LPIG.objects.get(community_id=community)
    except:
        community_tag = Community_LPIG()
        community_tag.community_id = community

    if len(legacy_tags)==0:
        global_legacy_tag = Tags_lpig.objects.get(name='legacy_any')
        legacy_tags.append(global_legacy_tag.id)

    comm_tags_list = list(Community_Legacy.objects.filter(community_id=community).values_list("tags_id",flat=True))

    for each_tag in legacy_tags:
        tag = Tags_lpig.objects.get(pk = each_tag)
        if each_tag in comm_tags_list:

            continue
        elif not each_tag in comm_tags_list:
            community_tag = Community_Legacy()
            community_tag.tags_id = tag
            community_tag.community_id = community
            community_tag.save()

        else:
            pass
    for tag in comm_tags_list:
        if tag not in legacy_tags:
            present_tag = Tags_lpig.objects.get(pk=tag)
            Community_Legacy.objects.filter(tags_id = tag,community_id=community).delete()

    if len(profession_tags)==0:
        global_profession_tag = Tags_lpig.objects.get(name='profession_any')
        profession_tags.append(global_profession_tag.id)

    comm_tags_list = list(Community_Profession.objects.filter(community_id=community).values_list("tags_id", flat=True))
    for each_tag in profession_tags:
        tag = Tags_lpig.objects.get(pk = each_tag)

        if each_tag in comm_tags_list:
            continue
        elif not each_tag in comm_tags_list:
            community_tag = Community_Profession()
            community_tag.tags_id = tag
            community_tag.community_id = community
            community_tag.save()
        else:
            pass
    for tag in comm_tags_list:
        if tag not in profession_tags:
            present_tag = Tags_lpig.objects.get(pk=tag)
            Community_Profession.objects.filter(tags_id = tag,community_id=community).delete()


    if len(interest_tags)==0:
        global_interest_tag = Tags_lpig.objects.get(name='interest_any')
        interest_tags.append(global_interest_tag.id)

    comm_tags_list = list(Community_Interest.objects.filter(community_id=community).values_list("tags_id", flat=True))

    for each_tag in interest_tags:
        tag = Tags_lpig.objects.get(pk = each_tag)

        if each_tag in comm_tags_list:
            continue
        elif not each_tag in comm_tags_list:
            community_tag = Community_Interest()
            community_tag.tags_id = tag
            community_tag.community_id = community
            community_tag.save()
        else:
            pass
    for tag in comm_tags_list:
        if tag not in interest_tags:
            Community_Interest.objects.filter(tags_id = tag,community_id=community).delete()

    if len(grography_tags)==0:
        global_tag = Tags_lpig.objects.get(name='Global')
        grography_tags.append(global_tag.id)

    comm_tags_list = list(Community_Geography.objects.filter(community_id=community).values_list("tags_id", flat=True))

    for each_tag in grography_tags:
        tag = Tags_lpig.objects.get(pk = each_tag)

        if each_tag in comm_tags_list:
            continue
        elif not each_tag in comm_tags_list:
            community_tag = Community_Geography()
            community_tag.tags_id = tag
            community_tag.community_id = community
            community_tag.save()
        else:
            pass

    for tag in comm_tags_list:
        if tag not in grography_tags:
            Community_Geography.objects.filter(tags_id = tag,community_id=community).delete()


# def delete_cluster_related_tags_for_community(cluster_tag_id,community_id,typ):
#     cluster_list = get_cluster_tags(cluster_tag_id)
#     for tag in cluster_list:
#
#         if typ == 'Legacy':
#             tag = Community_Legacy.objects.filter(tags_id=tag, community_id=community_id)
#         elif typ == 'Profession':
#             tag = Community_Profession.objects.filter(tags_id=tag, community_id=community_id)
#         elif typ == 'Interest':
#             tag = Community_Interest.objects.filter(tags_id=tag, community_id=community_id)
#         elif typ == 'Geography':
#             tag = Community_Geography.objects.filter(tags_id=tag, community_id=community_id)
#
#         tag.delete()


def get_or_create_tag_attributes_list(tags,tag_type):

    ''' function get list of tag id's accroding to given list of strings '''

    tags_list=[]

    if len(tags) == 1 and tags[0]=='':
        return tags_list
    for each_tag in tags:
        print('each tag  ===== ',each_tag)
        # attribute = Attributes.objects.filter(Q(attribute_name__icontains=tag_type))[0]
        # tag = Tags_lpig.objects.filter(name = each_tag,attribute_id=attribute)
        tag = Tags_lpig.objects.filter(name = each_tag)

        cluster = False
        if len(tag)>0:
            tag=tag[0]

        elif len(tag) == 0:
            tag = create_uncategorized_tag(each_tag,tag_type)

        if not cluster:
            if tag.id not in tags_list:
                tags_list.append(tag.id)
    return tags_list


# def get_cluster_tags(cluster_tag_id):
#
#     cluster_tags_list = list(Tags_lpig.objects.filter(cluster_tag_id=cluster_tag_id).distinct('name').values_list('id',flat=True))
#     cluster_tags_list.append(cluster_tag_id)
#     return cluster_tags_list


def create_uncategorized_tag(tag,tag_type):
    ''' function to create a un-categorized tag '''
    print(tag)

    new_tag = tag
    new_tag = new_tag.strip().title()
    if new_tag != '':

        category = Category.objects.get(pk=6)
        attribute = Attributes.objects.filter(Q(attribute_name__icontains=tag_type), Q(attribute_name__icontains='Uncategorized'))[0]
        tag = Tags_lpig.objects.filter(name = new_tag)
        if not tag.exists():
            tag = Tags_lpig()
            tag.name = new_tag
            tag.category_id = category
            tag.attribute_id = attribute
            tag.created_at = time.time()
            tag.updated_at = time.time()
            tag.save()
            tag.tag_id = tag.id
            tag.save()
        else:
            tag = tag[0]
        if tag_type == 'Geography':
            if tag and not tag.image_link:
                tag_name, tag_id = new_tag, tag.id
                error_logger.error(" dashboard update tag image at create or get uncategorized tag")
                update_tag_image.delay(tag_name=tag_name, tag_id=tag_id)
        return tag
    return None


def delete_hidden_tags(request):

    '''function to delete the hidden tags'''

    tag = request.GET.get('del_uncategorized')
    Tags_lpig.objects.filter(pk=tag).delete()

    return JsonResponse({'success': True})


def alpha_sign_up_mail(request,user_id):

    '''function to send mail to alpha sign up'''

    user_college=userinfo_tags.objects.filter(user_id=user_id).values('tag_id')
    user_info=Userinfo.objects.filter(user_id=user_id)
    user_name=''
    user_email=''
    for user in user_info:
        user_name=user.name
        user_email=user.email

    if len(user_college) == 0:
        return HttpResponse('Please Provide a tag for user')

    url=''
    college_name=''
    if user_college[0]['tag_id'] == 41:                         #for IIT Delhi
        college_name='IIT Delhi'
        url='https://docs.google.com/forms/d/e/1FAIpQLSes87js8cTiGg0x-Vw9DYrnY1BCZTolba0B1WBvcVSYZSGAwg/viewform'
    elif user_college[0]['tag_id'] == 42:                       #for NSIT College
        college_name='NSIT'
        url='https://docs.google.com/forms/d/e/1FAIpQLSfqN2z1wg6CCJ4ZKH1lxQQgJ8iUWEbtTT0R9NT64zg5f13_ig/viewform'
    else:
        return HttpResponse('Please Provide the tag first')

    context={
        'Name':user_name,
        'college_name':college_name,
        'url':url,
        'email':user_email
    }

    send_mail_for_signup(context,True)
    return HttpResponse('Alpha Mail is Sent')


def testing_sign_up_mail(request,user_id):

    '''function to send tester mail'''
    user_name = ''
    user_email = ''
    user_info=Userinfo.objects.filter(user_id=user_id)
    for user in user_info:
        user_name = user.name
        user_email = user.email

    context = {
        'Name': user_name,
        'url': 'https://play.google.com/apps/testing/com.collabmates',
        'email': user_email
    }

    send_mail_for_signup(context,False)
    return HttpResponse('Tester Mail is Sent')


def send_mail_for_signup(context,flag):

    '''function to send mail both types of mails for tester and users'''

    time.sleep(5)
    fail_silently = True
    to = context['email']

    if flag:             #alpha signup

        template = get_template("mails/alpha_sign_up.html").render(context)
        subject="""Thanks for joining LikeMinds! Here's the next step"""

    else:
        template = get_template("mails/testing_signup.html").render(context)
        subject="""Access to the first version of LikeMinds App"""


    msg = EmailMultiAlternatives(subject,
                                 template,
                                 "LikeMinds<hello@likeminds.community>",
                                 [to],
                                 )
    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)


def send_tester_mail(request):
    '''function to send tester mail to user you don't have the mail'''
    if request.method == 'POST':
        tester_form=Tester_mail_form(request.POST)

        if tester_form.is_valid():
            user_name=tester_form.cleaned_data['name']
            user_email=tester_form.cleaned_data['email']

            context = {
                'Name': user_name,
                'url': 'https://play.google.com/apps/testing/com.collabmates',
                'email': user_email
            }
            send_mail_for_signup(context, False)
        else:
            return HttpResponse('Some technical Error')
        return HttpResponse('Tester Mail is Sent')

    else:
        tester_form=Tester_mail_form(request.POST)
        context={'Tester_mail_form':tester_form}
        return render(request,'dashboard/send_tester_mail.html',context)


def user_communities(request,user_id):
    """ function to get user communities """

    my_communities,count = get_user_communities(user_id)
    communities=[]
    for community in my_communities:
        comm={"name":community.name}

        state=Members.objects.filter(community_id=community.id,member_id=user_id).values('state')

        if state:
            state=state[0]['state']
            if state == 1:
                comm['state'] = 'Promoter'
            elif state == 2:
                comm['state'] = "Temporary Promoter"
            elif state == 3:
                comm['state'] = 'Pending'
            elif state == 4:
                comm['state'] = 'Member'
            elif state == 6:
                comm['state'] = 'Nominated Promoter'
            elif state == 7:
                comm['state'] = 'Nominated Promoter(already a member)'
            elif state == 5:
                comm['state'] = 'Declined by Promoter'
            elif state == 8:
                comm['state'] = 'Interested'
            elif state == 9:
                comm['state'] = 'Eligible Promoter'
        communities.append(comm)

    return render(request,'dashboard/user_communities.html',{"my_communities":communities,'count':count})


def get_user_communities(user_id):
    ''' function to get users communities '''

    communities = Members.objects.all().filter(member_id=user_id).filter(~Q(state=0))

    my_communities = []
    for community in communities:
        my_communities.append(community.community_id)
    my_community = []
    for community in my_communities:
        my_community.append(community)

    return my_community,communities.count()

  
@csrf_exempt
def create_tag(request):
    ''' function to create a tag '''

    if request.method == 'POST':
        category = request.POST.get('category')
        attribute = request.POST.get('attribute')
        new_tag = request.POST.get('new_tag')
        new_tag = new_tag.strip()
        tag_type=request.POST.get('tag_type')
        print(new_tag)
        if tag_type == "normal_tag":
            get_or_create_sub_tags(new_tag, category, attribute)

        else:
            cluster_tag = request.POST.getlist('cluster_tags[]')
            if not cluster_tag:
                error_logger.error("Invalid Input")
                return redirect('create_tag')

            tag=get_or_create_sub_tags(new_tag, category, attribute,cluster=True)
            bl=False
            for cluster in cluster_tag:
                if not bl:
                    # removing the old cluster tag id
                    Tags_lpig.objects.filter(cluster_tag_id=tag.tag_id).update(cluster_tag_id=None)
                    bl=True
                tag_object=Tags_lpig.objects.filter(id=cluster)
                if tag_object:
                    tag_name=tag_object[0].name
                    print(tag_name)
                    Tags_lpig.objects.filter(name=tag_name).update(cluster_tag_id=tag.tag_id)
                else:
                    error_logger.error("Tag not present for clustering")
            print("Inserted Successfully")
        #return redirect('create_tag')
        return JsonResponse({"success":True})

    else:
        categories = Category.objects.filter(~Q(name__icontains = 'ncategorized'))
        legacy_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Legacy'),~Q(attribute_name__icontains = 'uncategorized'))
        profession_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Profession'),~Q(attribute_name__icontains = 'uncategorized'))
        interests_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Interests'),~Q(attribute_name__icontains = 'uncategorized'))
        geography_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Geography'),~Q(attribute_name__icontains = 'uncategorized'))
        global_attributes = Attributes.objects.filter(Q(attribute_name__icontains='Global'),~Q(attribute_name__icontains = 'uncategorized'))

        clusters=Attributes.objects.filter(Q(id=21)|Q(id=22)|Q(id=23)|Q(id=24))
        existing_clusters=Tags_lpig.objects.filter(is_cluster=1)
        all_tags=Tags_lpig.objects.all().order_by('name')
        tag_set=set()
        tags=[]
        cluster_tags=[]
        for tag in all_tags:
            temp={}
            if not tag.name in tag_set and not tag.is_cluster:
                temp['id']=tag.tag_id
                temp['name']=tag.name
                tags.append(temp)
            if tag.is_cluster:
                temp={}
                temp['name']=tag.name
                temp['clusters']=Tags_lpig.objects.filter(cluster_tag_id=tag.tag_id).distinct('name')
                cluster_tags.append(temp)

            tag_set.add(tag.name)
        #print(cluster_tags)
        return render(request, 'dashboard/create_tag.html', {'categories': categories,
                                                     'legacy_attributes': legacy_attributes,
                                                     'profession_attributes': profession_attributes,
                                                     'geography_attributes': geography_attributes,
                                                     'interests_attributes': interests_attributes,
                                                     'global_attributes': global_attributes,'tags':tags,
                                                     'clusters':clusters,'existing_clusters':existing_clusters,
                                                     'clustered_tags':cluster_tags, })

def get_or_create_sub_tags(new_tag,category,attribute,cluster=False):

    ''' function to create sub tags with known category and attribute  '''
    category = Category.objects.get(id=category)
    attribute = Attributes.objects.get(id=attribute)
    try:
        if not cluster:
            tag = Tags_lpig.objects.get(name__iexact=new_tag,attribute_id = attribute)
        else:
            tag = Tags_lpig.objects.get(name__iexact=new_tag)
            tag.attribute_id=attribute
            tag.is_cluster=1
            tag.updated_at = time.time()
            tag.save()
    except:

        tag = Tags_lpig()
        tag.name = new_tag
        tag.category_id = category
        tag.attribute_id = attribute
        tag.save()
        tag.tag_id =tag.id
        tag.created_at = time.time()
        tag.updated_at = time.time()
        tag.save()
        if cluster:
            tag.is_cluster=1
            tag.save()
        if not cluster:
            if category.name == 'Geography' or attribute.id == 3:
                if tag and not tag.image_link:
                    tag_id,tag_name = tag.id,tag.name
                    update_tag_image(tag_id=tag_id,tag_name=tag_name)


    if not cluster:
        if category.name == 'Geography' or attribute.id == 3:

            geography_list = get_city_address(city=new_tag)
            print(new_tag,"  >>>>>  ",geography_list)


            for attr, tag_name in geography_list.items():
                print(attr,tag_name)
                if tag_name == '':
                    continue
                # creating or catgorizing a tag with known category and attribute
                # geography tag is created, create its related tags
                # for example, if gurgaon is created, create Haryana and India as well as state and country
                tag = create_or_categorize_tag(tag=tag_name, category='Geography', attribute=attr)

    return tag


@csrf_exempt
def categorize_tag(request):

    ''' this function categorizez the tag according to given category and attribute '''

    if request.method == 'POST':
        category = request.POST.get('category')
        attribute = request.POST.get('attribute')
        uncategorized = request.POST.get('uncategorized')

        print(category,attribute,uncategorized)

        tag_id=update_uncategorize_tag(uncategorized, category, attribute)
        pre_create_communities.delay(tag_id=tag_id)

        return redirect('categorize_tag')

    else:

        categories = Category.objects.filter(~Q(name__icontains='ncategorized'))

        legacy_uncat = Attributes.objects.filter(Q(attribute_name__icontains='Legacy_unca'))[0]
        profession_uncat = Attributes.objects.filter(Q(attribute_name__icontains='Profession_unca'))[0]
        interests_uncat = Attributes.objects.filter(Q(attribute_name__icontains='Interests_unca'))[0]
        geography_uncat = Attributes.objects.filter(Q(attribute_name__icontains='Geography_unca'))[0]

        print(legacy_uncat.id,profession_uncat.id,interests_uncat.id,geography_uncat.id)

        uncategortized_tags = Tags_lpig.objects.filter(Q(attribute_id = legacy_uncat.id )|
                                                       Q(attribute_id = profession_uncat.id )|
                                                       Q(attribute_id = interests_uncat.id )|
                                                       Q(attribute_id = geography_uncat.id )|
                                                       Q(category_id = 6)).order_by("name")

        categortized_tags = Tags_lpig.objects.filter(~Q(attribute_id=16),~Q(attribute_id=17),
                                                     ~Q(attribute_id=18),~Q(attribute_id=19),
                                                     ~Q(attribute_id=20),~Q(category_id=6)).order_by("name")

        categortized_tags_list = []
        for tag in categortized_tags:
            tag_dict = {}
            tag_dict['id'] = tag.id
            tag_dict['name'] = tag.name
            tag_dict['attr'] = tag.attribute_id.attribute_name

            categortized_tags_list.append(tag_dict)

        un_categortized_tags_list = []
        for tag in uncategortized_tags:
            tag_dict = {}
            tag_dict['id'] = tag.id
            tag_dict['name'] = tag.name
            if tag.attribute_id.id == 17:
                tag_dict['attr'] = 'legacy'
            elif tag.attribute_id.id == 18:
                tag_dict['attr'] = 'profession'
            elif tag.attribute_id.id == 19:
                tag_dict['attr'] = 'interest'
            elif tag.attribute_id.id == 20:
                tag_dict['attr'] = 'geography'
            else:
                tag_dict['attr'] = tag.attribute_id.attribute_name

            un_categortized_tags_list.append(tag_dict)




        legacy_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Legacy')
                                                       ,~Q(attribute_name__icontains = 'uncategorized'))
        profession_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Profession')
                                                           ,~Q(attribute_name__icontains = 'uncategorized'))
        interests_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Interests')
                                                          ,~Q(attribute_name__icontains = 'uncategorized'))
        geography_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Geography')
                                                          ,~Q(attribute_name__icontains = 'uncategorized'))
        global_attributes = Attributes.objects.filter(Q(attribute_name__icontains='Global')
                                                      ,~Q(attribute_name__icontains = 'uncategorized'))

        return render(request, 'dashboard/categorize_tags.html', {'categories': categories,
                                                                  'uncategortized_tags':un_categortized_tags_list,
                                                                  'categortized_tags': categortized_tags_list,
                                                                  'legacy_attributes': legacy_attributes,
                                                                  'profession_attributes': profession_attributes,
                                                                  'geography_attributes': geography_attributes,
                                                                  'interests_attributes': interests_attributes,
                                                                  'global_attributes': global_attributes, })


def update_uncategorize_tag(uncategorized, category, attribute):

    ''' tag is updated here according to category and attribute '''

    category = Category.objects.get(id=category)
    attribute = Attributes.objects.get(id=attribute)
    deleted = False
    tag = Tags_lpig.objects.get(id=uncategorized)
    tags = Tags_lpig.objects.filter(name=tag.name,attribute_id = attribute)
    if tags.exists():
        tag.delete()
        deleted = True
    if not deleted:
        tag.attribute_id = attribute
        tag.category_id = category
        tag.save()

    if attribute.id == 3:
        tag_id = tag.id
        if tag and not tag.image_link:
            tag_name = tag.name
            update_tag_image(tag_id=tag_id, tag_name=tag_name)
        update_hometown_tags_for_all_users.delay(tag_id)

    elif category.name == 'Geography':
        if tag and not tag.image_link:
            tag_id = tag.id
            tag_name = tag.name
            update_tag_image.delay(tag_id=tag_id,tag_name=tag_name)

    return tag.tag_id



def user_tags(request,user_id):
    ''' gives all the user tags  '''
    user = User.objects.get(pk = user_id)

    legacy_tags = list(Tags_lpig.objects.filter(category_id__id = '1').values_list('name', flat=True))
    profession_tags = list(Tags_lpig.objects.filter(category_id__id = '2').values_list('name', flat=True))
    interests_tags = list(Tags_lpig.objects.filter(category_id__id = '3').values_list('name', flat=True))
    geography_tags = list(Tags_lpig.objects.filter(category_id__id = '4').values_list('name', flat=True))


    hidden_legacy_tags = list(User_Legacy.objects.filter(user_id=user).values_list('tags_id', flat=True))
    hidden_profession_tags = list(User_Profession.objects.filter(user_id=user).values_list('tags_id', flat=True))
    hidden_interests_tags = list(User_Interest.objects.filter(user_id=user).values_list('tags_id', flat=True))
    hidden_geography_tags = list(User_Geography.objects.filter(user_id=user).values_list('tags_id', flat=True))


    hidden_legacy_tag = ''
    hidden_profession_tag = ''
    hidden_interests_tag = ''
    hidden_geography_tag = ''


    for tag in hidden_legacy_tags:
        global_tag = Tags_lpig.objects.get(name='legacy_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_legacy_tag=hidden_legacy_tag+tag_object.name+","
        except:
            pass

    for tag in hidden_profession_tags:
        global_tag = Tags_lpig.objects.get(name='profession_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_profession_tag=hidden_profession_tag+tag_object.name+","
        except:
            pass


    for tag in hidden_interests_tags:
        global_tag = Tags_lpig.objects.get(name='interest_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_interests_tag=hidden_interests_tag+tag_object.name+","
        except:
            pass


    for tag in hidden_geography_tags:
        global_tag = Tags_lpig.objects.get(name='Global')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_geography_tag = hidden_geography_tag+tag_object.name+","
        except:
            pass

    context={
        'legacy_tags':legacy_tags,
        'profession_tags':profession_tags,
        'interests_tags':interests_tags,
        'geography_tags':geography_tags,
        'hidden_legacy_tag':hidden_legacy_tag,
        'hidden_profession_tag': hidden_profession_tag,
        'hidden_interests_tag': hidden_interests_tag,
        'hidden_geography_tag': hidden_geography_tag,
        'user_id':user_id,
        'user_name':user.userinfo.name
    }

    return render(request, 'dashboard/user_tags.html', context)


def add_user_tags(request):

    ''' adding or updating or deleting user hidden tags '''

    legacy_tags=request.GET.get('legacy_tags')
    user_id=request.GET.get('user_id')


    profession_tags = request.GET.get('profession_tags')
    interest_tags = request.GET.get('interests_tags')
    grography_tags = request.GET.get('grography_tags')


    legacy_tags = legacy_tags.split(",")
    profession_tags = profession_tags.split(",")
    interest_tags = interest_tags.split(",")
    grography_tags = grography_tags.split(",")

    legacy_tags = get_or_create_tag_attributes_list(legacy_tags, 'Legacy')
    profession_tags = get_or_create_tag_attributes_list(profession_tags, 'Profession')
    interest_tags = get_or_create_tag_attributes_list(interest_tags, 'Interests')
    grography_tags = get_or_create_tag_attributes_list(grography_tags, 'Geography')


    save_user_lpig_tags(user_id= user_id,
                        legacy_tags= legacy_tags ,
                        profession_tags = profession_tags,
                        interest_tags=interest_tags,
                        greography_tags=grography_tags)

    compute_rank.delay(user_id = user_id)
    return JsonResponse({'success':True})


def  save_user_lpig_tags(user_id,legacy_tags,profession_tags,interest_tags,greography_tags):

    ''' function to update or create and delete users L,P,I,G tags '''

    user = User.objects.get(id=user_id)
    global_tag = Tags_lpig.objects.get(name='legacy_any')

    user_tags_list = list(User_Legacy.objects.filter(user_id=user).values_list("tags_id",flat=True))
    # adding global tag to list manually
    legacy_tags.append(str(global_tag.id))

    for each_tag in legacy_tags:
        if each_tag in user_tags_list:
            # if tag is already present in user tags
            # dont have to do anything
            tag = Tags_lpig.objects.get(pk=each_tag)

            # if tag and ((tag.attribute_id.id >= 12 and tag.attribute_id.id <= 15) or tag.attribute_id.id == 3):
            #     print("inside user home town updte tags -------------> ")
            #     tag = insert_user_home_town_tags(user_id=user_id, tag=str(tag.id))
            #     tag_id = tag.id
            #     update_hometown_tags_for_all_users.delay(tag_id)

        elif not each_tag in user_tags_list:

            tag = Tags_lpig.objects.get(pk=each_tag)

            if tag and ((tag.attribute_id.id >=12 and tag.attribute_id.id <=15) or tag.attribute_id.id == 3):
                print("inside user home town updte tags >>>>>>>>>>> ")
                tag = insert_user_home_town_tags(user_id=user_id, tag=str(tag.tag_id))
                tag_id = tag.id
                update_hometown_tags_for_all_users.delay(tag_id)

            tags = User_Legacy.objects.filter(tags_id=tag, user_id=user)
            # if tag is not present
            if not tags.exists():
                # create new tag for user
                user_tag = User_Legacy()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()

        else:
            pass
    # deleting unwanted tags
    for tag in user_tags_list:
        if tag not in legacy_tags:

            tag = User_Legacy.objects.filter(tags_id=tag, user_id=user)

            if tag[0].tags_id.is_cluster == 1:
                delete_cluster_related_tags_for_users(cluster_tag_id=tag[0].tags_id.id, user_id=user, typ='Legacy')

            elif str(tag[0].tags_id.id) != '15':
                tag.delete()

    # profession tags update --------------------------------->

    global_tag = Tags_lpig.objects.get(name='profession_any')
    user_tags_list = list(User_Profession.objects.filter(user_id=user).values_list("tags_id",flat=True))

    profession_tags.append(str(global_tag.id))

    for each_tag in profession_tags:
        if each_tag in user_tags_list:
            # if tag is already present in user tags
            # dont have to do anything
            continue
        elif not each_tag in user_tags_list:
            tag = Tags_lpig.objects.get(pk=each_tag)
            tags = User_Profession.objects.filter(tags_id=tag, user_id=user)

            if not tags.exists():
                # if user does not have that tag
                user_tag = User_Profession()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()

        else:
            pass
    # delete unwanted tags

    for tag in user_tags_list:
        if tag not in profession_tags:

            tag = User_Profession.objects.filter(tags_id=tag, user_id=user)


            if tag[0].tags_id.is_cluster == 1:
                delete_cluster_related_tags_for_users(cluster_tag_id=tag[0].tags_id.id, user_id=user, typ='Profession')


            elif str(tag[0].tags_id.id) != '16':
                tag.delete()

    # interests tags update --------------------------------->

    global_tag = Tags_lpig.objects.get(name='interest_any')
    user_tags_list = list(User_Interest.objects.filter(user_id=user).values_list("tags_id",flat=True))
    interest_tags.append(str(global_tag.id))

    for each_tag in interest_tags:
        if each_tag in user_tags_list:
            # if tag is already present in user tags
            # dont have to do anything
            continue
        elif not each_tag in user_tags_list:
            tag = Tags_lpig.objects.get(pk=each_tag)
            tags = User_Interest.objects.filter(tags_id=tag, user_id=user)

            if not tags.exists():
                # if user does not have that tag
                user_tag = User_Interest()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()
        else:
            pass
    # delete unwanted tags

    for tag in user_tags_list:
        if tag not in interest_tags:

            tag = User_Interest.objects.filter(tags_id=tag, user_id=user)


            if tag[0].tags_id.is_cluster == 1:
                delete_cluster_related_tags_for_users(cluster_tag_id=tag[0].tags_id.id, user_id=user, typ='Interest')


            elif str(tag[0].tags_id.id) != '17':
                tag.delete()

    # geography tags update --------------------------------->

    global_tag = Tags_lpig.objects.get(name='Global')
    user_tags_list = list(User_Geography.objects.filter(user_id=user).values_list("tags_id",flat=True))

    greography_tags.append(str(global_tag.id))
    for each_tag in greography_tags:
        if each_tag in user_tags_list:
            # if tag is already present in user tags
            # dont have to do anything
            continue

        elif not each_tag in user_tags_list:
            # if user does not have that tag
            tag = Tags_lpig.objects.get(pk=each_tag)
            tags = User_Geography.objects.filter(tags_id=tag, user_id=user)

            if not tags.exists():
                # create a tag for user
                user_tag = User_Geography()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()

        else:
            pass
    # delete unwanted tags
    for tag in user_tags_list:
        if tag not in greography_tags:

            tag = User_Geography.objects.filter(tags_id=tag, user_id=user)


            if tag[0].tags_id.is_cluster == 1:
                delete_cluster_related_tags_for_users(cluster_tag_id=tag[0].tags_id.id, user_id=user, typ='Geography')


            elif str(tag[0].tags_id.id) != '18':
                tag.delete()
    # update user geography tags with images and tag related things like state and country
    update_user_geography_tags(user_id=user_id, typ='Geography')


def delete_cluster_related_tags_for_users(cluster_tag_id,user_id,typ):
    cluster_list = get_cluster_tags(cluster_tag_id)
    for tag in cluster_list:

        if typ == 'Legacy':
            tag = User_Legacy.objects.filter(tags_id=tag, user_id=user_id)
        elif typ == 'Profession':
            tag = User_Profession.objects.filter(tags_id=tag, user_id=user_id)
        elif typ == 'Interest':
            tag = User_Interest.objects.filter(tags_id=tag, user_id=user_id)
        elif typ == 'Geography':
            tag = User_Geography.objects.filter(tags_id=tag, user_id=user_id)

        tag.delete()

def map_tags(request):

    ''' fucntion to map a tag to other tag and categorize it  '''

    uncategorized_tag = request.GET.get('uncategorized_tag')
    mapped_tag = request.GET.get('mapped_tag')

    uncategorized_tag = Tags_lpig.objects.get(pk = uncategorized_tag)
    mapped_tag = Tags_lpig.objects.get(pk=mapped_tag)

    # mapping the uncategorized tag to the mapped tag and
    # categorizing it accroding to the mapped tag

    uncategorized_tag.category_id = mapped_tag.category_id
    uncategorized_tag.attribute_id = mapped_tag.attribute_id
    uncategorized_tag.tag_id = mapped_tag.id
    uncategorized_tag.save()

    return JsonResponse({'success': True})


def update_tag(request):

    ''' function to render all the required elements to fornt end to update a tag '''

    if request.method == 'GET':

        updated = request.GET.get('updated',False)
        print(updated)

        categories = Category.objects.filter(~Q(name__icontains='ncategorized'),~Q(name = 'Global'))

        legacy_attributes = Attributes.objects.filter(Q(attribute_name__icontains='Legacy')
                                                      , ~Q(attribute_name__icontains='uncategorized')).order_by('id')
        profession_attributes = Attributes.objects.filter(Q(attribute_name__icontains='Profession')
                                                          , ~Q(attribute_name__icontains='uncategorized')).order_by('id')
        interests_attributes = Attributes.objects.filter(Q(attribute_name__icontains='Interests')
                                                         , ~Q(attribute_name__icontains='uncategorized')).order_by('id')
        geography_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Geography')
                                                          ,~Q(attribute_name__icontains = 'uncategorized')).order_by('id')


        return render(request, 'dashboard/update_tag.html', {'categories': categories,
                                                             'legacy_attributes': legacy_attributes,
                                                             'profession_attributes': profession_attributes,
                                                             'interests_attributes': interests_attributes,
                                                             'geography_attributes': geography_attributes,

                                                             'updated':updated
                                                             })


def get_tags_by_attributes(request,attr_id):

    tags = Tags_lpig.objects.filter(attribute_id=attr_id).order_by('id')
    print("\ntags count === ",tags.count(),"\n")
    tags_list = []

    for tag in tags:
        color = 'green'
        tag_dict = {'tag_id':tag.id,'tag_name':tag.name,'color':'green'}
        print(tag,tag.tag_characterstics,' >> ',tag.image_link,' >> ',not tag.image_link)

        if tag.attribute_id.id == 1 or tag.attribute_id.id == 4 or tag.attribute_id.id == 7 :
            print('\ninside special if\n')
            if not tag.image_link:
                tag_dict['color'] = 'black'
            tags_list.append(tag_dict)
            continue

        elif not tag.tag_characterstics and not tag.image_link:
            print("\n here 1\n")
            tag_dict['color'] = 'black'
            tags_list.append(tag_dict)
            continue

        elif tag.tag_characterstics == 'null' and not tag.image_link:
            print("\n here 2\n")
            tag_dict['color'] = 'black'
            tags_list.append(tag_dict)
            continue

        elif not tag.tag_characterstics and tag.image_link :
            print('\ninside here 1\n')
            tag_dict['color'] = 'red'
            tags_list.append(tag_dict)
            continue

        elif tag.tag_characterstics == 'null' and tag.image_link:
            print('\ninside here 2\n')
            tag_dict['color'] = 'red'
            tags_list.append(tag_dict)
            continue

        elif tag.image_link and not tag.tag_characterstics:
            print('\ninside here 3\n')
            tag_dict['color'] = 'red'
            tags_list.append(tag_dict)
            continue

        elif tag.image_link and tag.tag_characterstics == 'null':
            print('\ninside here 4\n')
            tag_dict['color'] = 'red'
            tags_list.append(tag_dict)
            continue

        tag_chars = json.loads(tag.tag_characterstics)
        dict_length = len(tag_chars)
        count = 0
        for key,value in tag_chars.items():

            print(tag,key, value,value == '')
            if value == '':
                print('for ', key, " ", value, 'is empty')
                color = 'red'
                count+=1

            elif not value:
                print('for ',key," ",value,'is empty')
                color = 'red'
                count += 1


        if count == dict_length and not tag.image_link:
            tag_dict['color'] = 'black'
            tags_list.append(tag_dict)

        elif count != dict_length and not tag.image_link:
            tag_dict['color'] = 'red'
            tags_list.append(tag_dict)

        elif color == 'red':
            tag_dict['color'] = 'red'
            tags_list.append(tag_dict)
        else:
            tags_list.append(tag_dict)

    return JsonResponse({'tags_list':tags_list})


def tag_update_form(request,tag_id):

    ''' function to update tags with forms '''

    tag = Tags_lpig.objects.get(pk=tag_id)
    attr_id = tag.attribute_id.id

    if request.method=="POST":
        characteristics = None
        image = None
        if 'rank_update' in request.POST:
            tag_rank_form = Tag_Rank_Form(request.POST,instance=tag)
            if tag_rank_form.is_valid():
                tag_rank = tag_rank_form.cleaned_data['tag_rank']
                tag.tag_rank = tag_rank
                tag.updated_at = time.time()
                tag.save()
                print("rank update")
                return HttpResponse("Rank Updated")
        # save characteristics and image from form according to attribute given
        if attr_id == 2:
            form = Legacy_Education_Form(request.POST, request.FILES)
            if form.is_valid():
                demonym = form.cleaned_data['demonym']
                short_name = form.cleaned_data['short_name']
                image = form.cleaned_data['image']
                characteristics={'demonym':demonym,'csn':short_name}

        elif attr_id == 3:
            form = Legacy_Hometown_Form(request.POST, request.FILES)
            if form.is_valid():
                demonym = form.cleaned_data['home_demonym']
                image = form.cleaned_data['image']
                characteristics = {'home_demonym': demonym}

        elif attr_id == 5:
            form = Profession_Skill_Form(request.POST, request.FILES)
            if form.is_valid():
                skill_name = form.cleaned_data['skill_name']
                skill_experts = form.cleaned_data['skill_experts']
                image = form.cleaned_data['image']
                characteristics = {'skill_experts': skill_experts,'skill_name':skill_name}

        elif attr_id == 6:
            form = Profession_Industry_Form(request.POST, request.FILES)
            if form.is_valid():
                # demonym = form.cleaned_data['demonym']
                industry_name = form.cleaned_data['industry_name']
                image = form.cleaned_data['image']

                characteristics = {'industry_name': industry_name}


        elif attr_id == 8:
            form = Interests_Cause_Form(request.POST, request.FILES)
            if form.is_valid():
                thing_event = form.cleaned_data['thing_event']
                image = form.cleaned_data['image']
                characteristics = {'thing_event': thing_event}


        elif attr_id == 9:
            form = Interests_Hobby_Form(request.POST, request.FILES)
            if form.is_valid():
                hobbyists = form.cleaned_data['hobbyists']
                hobby_group_used_case = form.cleaned_data['hobby_group_used_case']
                hobby_group_event = form.cleaned_data['hobby_group_event']
                hobby_event = form.cleaned_data['hobby_event']
                hobby_name = form.cleaned_data['hobby_name']
                image = form.cleaned_data['image']
                characteristics = {'hobbyists': hobbyists,
                                   'hobby_group_used_case': hobby_group_used_case,
                                   'hobby_group_event':hobby_group_event,
                                   'hobby_event':hobby_event,
                                   'hobby_name': hobby_name,
                                   }

        elif attr_id == 10:
            form = Interests_Sports_Form(request.POST, request.FILES)
            if form.is_valid():
                sport_players = form.cleaned_data['sport_players']
                sport_usecase = form.cleaned_data['sport_usecase']
                sport_event = form.cleaned_data['sport_event']
                image = form.cleaned_data['image']
                characteristics = {'sport_players': sport_players, 'sport_usecase': sport_usecase,'sport_event':sport_event}

        elif attr_id == 11:
            form = Interests_Fan_Form(request.POST, request.FILES)
            if form.is_valid():
                thing = form.cleaned_data['thing']
                #thing_fan_group_name = form.cleaned_data['thing_fan_group_name']
                thing_fans = form.cleaned_data['thing_fans']
                thing_group_use_case = form.cleaned_data['thing_group_use_case']
                thing_event = form.cleaned_data['thing_event']
                image = form.cleaned_data['image']
                characteristics = {'thing': thing,
                                   #'thing_fan_group_name': thing_fan_group_name,
                                   'thing_fans': thing_fans,
                                   'thing_group_use_case': thing_group_use_case,
                                   'thing_event': thing_event,
                                   }
        elif (attr_id >= 12 and attr_id <= 15):

            form = Geography_Form(request.POST, request.FILES)
            if form.is_valid():
                demonym = form.cleaned_data['demonym']
                image = form.cleaned_data['image']
                characteristics={'demonym':demonym}

        else:
            form = Tag_Form(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data['image']

        if image:
            # tag.tag_image = image
            image_link = upload_tag_files(tag_id=tag.id,image=image,url=False)
            upload_tag_thumbnail.delay(tag_id=tag.id, image_url=image_link)
            tag.image_link = image_link

        tag.tag_characterstics = json.dumps(characteristics)
        tag.updated_at = time.time()
        tag.save()

        base_url = reverse('update_tag')
        query_string = urlencode({'updated':True})
        url = '{}?{}'.format(base_url, query_string)
        correct_tag=tag.tag_id
        pre_create_communities.delay(tag_id=correct_tag)
        return redirect(url)

    else:

        # render form according to attribute given
        #tag_instance=Tags_lpig.objects.get(id=tag_id)
        tag_rank_form=Tag_Rank_Form(instance=tag)


        if attr_id == 2:
            char={}
            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)
                if not char:
                    char = {}
            demonym = None
            short_name = None
            if 'demonym' in char:
                demonym = char['demonym']
            if 'csn' in char:
                short_name = char['csn']
            characteristics = {'demonym': demonym, 'short_name': short_name}

            form = Legacy_Education_Form(characteristics)
        elif attr_id == 3:

            char = {}
            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)
                if not char:
                    char = {}
            demonym = None
            short_name = None
            if 'home_demonym' in char:
                demonym = char['home_demonym']

            characteristics = {'home_demonym': demonym}

            form = Legacy_Hometown_Form(characteristics)
        elif attr_id == 5:

            char = {}
            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)
                if not char:
                    char = {}
            skill_experts = None
            skill_name = None
            if 'skill_experts' in char:
                skill_experts = char['skill_experts']
            if 'skill_name' in char:
                skill_name = char['skill_name']

            characteristics = {'skill_experts': skill_experts,'skill_name':skill_name}

            form = Profession_Skill_Form(characteristics)
        elif attr_id == 6:

            char = {}
            if tag.tag_characterstics:
                print("inside")
                char = json.loads(tag.tag_characterstics)
                if not char:
                    char = {}

            industry_name = None
            if 'industry_name' in char:
                industry_name = char['industry_name']
            characteristics = {'industry_name': industry_name}

            form = Profession_Industry_Form(characteristics)
        elif attr_id == 8:

            char = {}
            thing_event = None
            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)
                if not char:
                    char = {}

            if 'thing_event' in char:
                thing_event = char['thing_event']

            characteristics = {'thing_event': thing_event}

            form = Interests_Cause_Form(characteristics)
        elif attr_id == 9:

            char = {}
            hobbyists = None
            hobby_group_used_case = None
            hobby_group_event = None
            hobby_event = None
            hobby_name = None

            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)
                if not char:
                    char = {}

            if 'hobbyists' in char:
                hobbyists = char['hobbyists']

            if 'hobby_group_used_case' in char:
                hobby_group_used_case = char['hobby_group_used_case']

            if 'hobby_group_event' in char:
                hobby_group_event = char['hobby_group_event']

            if 'hobby_event' in char:
                hobby_event = char['hobby_event']

            # hobby_name
            if 'hobby_name' in char:
                hobby_name = char['hobby_name']
            characteristics = {'hobbyists': hobbyists,
                               'hobby_group_used_case': hobby_group_used_case,
                               'hobby_group_event': hobby_group_event,
                               'hobby_event': hobby_event,
                               'hobby_name':hobby_name,
                               }

            form = Interests_Hobby_Form(characteristics)

        elif attr_id == 10:

            char = {}
            sport_players = None
            sport_usecase = None
            sport_event = None

            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)
                if not char:
                    char = {}

            if 'sport_players' in char:
                sport_players = char['sport_players']

            if 'sport_usecase' in char:
                sport_usecase = char['sport_usecase']

            if 'sport_event' in char:
                sport_event = char['sport_event']


            characteristics = {'sport_players': sport_players, 'sport_usecase': sport_usecase,'sport_event':sport_event}

            form = Interests_Sports_Form(characteristics)

        elif attr_id == 11:

            char = {}
            thing = None
            thing_fan_group_name = None
            thing_fans = None
            thing_group_use_case = None
            thing_event = None

            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)
                if not char:
                    char = {}

            if 'thing' in char:
                thing = char['thing']

            if 'thing_fan_group_name' in char:
                thing_fan_group_name = char['thing_fan_group_name']

            if 'thing_fans' in char:
                thing_fans = char['thing_fans']

            if 'thing_group_use_case' in char:
                thing_group_use_case = char['thing_group_use_case']

            if 'thing_event' in char:
                thing_event = char['thing_event']


            characteristics = {'thing': thing,
                               'thing_fan_group_name': thing_fan_group_name,
                               'thing_fans': thing_fans,
                               'thing_group_use_case': thing_group_use_case,
                               'thing_event': thing_event
                               }

            form = Interests_Fan_Form(characteristics)

        elif (attr_id >= 12 and attr_id <= 15) :

            char = {}
            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)
                if not char:
                    char = {}
            demonym = None
            if 'demonym' in char:
                demonym = char['demonym']

            characteristics = {'demonym': demonym}

            form = Geography_Form(characteristics)

        else:

            form = Tag_Form()

        tag_image = None
        tag_image_link = None
        if tag.tag_image:
            tag_image =tag.tag_image.url
        if tag.image_link:
            tag_image_link = tag.image_link

        return render(request, 'dashboard/update_tag_form.html', {'form':form,
                                                             'tag_name':tag.name,
                                                             'tag_id':tag.id,
                                                             'attr_id':tag.attribute_id.id,
                                                             'tag_image':tag_image,
                                                             'tag_image_link':tag_image_link,
                                                              'tag_rank_form':tag_rank_form
                                                             })


def delete_tags(request):
    ''' function to render all tags to delete page '''

    deleted = request.GET.get('deleted',False)
    alrt = request.GET.get('alrt',False)
    tag_id = request.GET.get('tag_id','')

    tag_name = ''
    if tag_id != '':
        try:
            tag = Tags_lpig.objects.get(pk = tag_id)
            tag_name = tag.name
        except:
            pass
    print("tag anme ======= ",tag_name)
    # get all tags
    tags = Tags_lpig.objects.all()
    return render(request, 'dashboard/delete_tags.html', {'tags': tags,'deleted':deleted,'alrt':alrt,'tag_name':tag_name})


def delete_tags_post(request,tag_id):

    ''' function to delete the any tag and
    communities with that tag and all community related things '''
    tag_deleted = True

    tags = Tags_lpig.objects.filter(id=tag_id)
    tag = tags[0]
    print(">>>>>>>>>>",tag)
    tag_community = None
    user_tags = None
    community_exists =  False
    category_id = tag.category_id.id
    print("cat id",category_id)

    # get the communities and users with the tag which is to be deleted
    if category_id == 1:
        tag_community = Community_Legacy.objects.filter(tags_id = tag)
        user_tags = User_Legacy.objects.filter(tags_id = tag)
        community_exists = True
    elif category_id == 2:
        tag_community = Community_Profession.objects.filter(tags_id = tag)
        user_tags = User_Profession.objects.filter(tags_id = tag)
        community_exists = True

    elif category_id == 3:
        tag_community = Community_Interest.objects.filter(tags_id = tag)
        user_tags = User_Interest.objects.filter(tags_id = tag)
        community_exists = True


    elif category_id == 4:
        tag_community = Community_Geography.objects.filter(tags_id = tag)
        user_tags = User_Geography.objects.filter(tags_id = tag)
        community_exists = True

    elif category_id == 6:
        community_exists = True
        legacy_communities = Community_Legacy.objects.filter(tags_id = tag)
        profession_community = Community_Profession.objects.filter(tags_id = tag)
        interest_community = Community_Interest.objects.filter(tags_id = tag)
        geography_community = Community_Geography.objects.filter(tags_id = tag)

        user_L_tags = User_Legacy.objects.filter(tags_id = tag)
        user_P_tags = User_Profession.objects.filter(tags_id = tag)
        user_I_tags = User_Interest.objects.filter(tags_id = tag)
        user_G_tags = User_Geography.objects.filter(tags_id = tag)

        tag_community = legacy_communities.union(profession_community, interest_community, geography_community)

        user_tags = user_L_tags.union(user_P_tags, user_I_tags, user_G_tags)

    # if any community has this tag
    if community_exists:
        for community in tag_community:
            tag_community_id = community.community_id.id

            community_members_count = Members.objects.filter(community_id=community.community_id).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7)|Q(state=8)|Q(state=9)).count()
            # if community has no members in it
            if community_members_count == 0:
                print("community will be deleted")

                community_purpose_card_id = community.community_id.purpose_collabcard
                try:
                    # delete cards of that community (purpose card)
                    card = Collabcard.objects.filter(id=community_purpose_card_id)  #
                    if card.exists():
                        print("deleting card")
                        card.delete()
                except:
                    print("problem with card")
                # delete the community
                Community.objects.filter(id=tag_community_id).delete()

            # if community has members , dont delete community and
            # any thing related to that community
            elif community_members_count > 0:
                print("community will not be deleted")
                if not tag_deleted:
                    continue
                tag_deleted = False


    tag_community.delete()
    user_tags.delete()
    tags.delete()

    base_url = reverse('delete_tags')
    query_string = urlencode({'deleted': True,'alrt':True,'tag_id':tag_id})
    url = '{}?{}'.format(base_url, query_string)

    return redirect(url)


def rename_tag(request,tag_id = None):

    if not tag_id:
        updated = request.GET.get('updated', False)
        tag_id = request.GET.get('tag_id', '')
        old_name = request.GET.get('old_name', '')

        tag_name = ''
        if tag_id :
            try:
                tag = Tags_lpig.objects.get(pk=tag_id)
                tag_name = tag.name
            except:
                pass
        print("tag name ======= ", tag_name)
        # get all tags
        tags = Tags_lpig.objects.all()
        return render(request, 'dashboard/rename_tag.html',
                      {'tags': tags, 'updated': updated, 'old_name': old_name, 'tag_name': tag_name})

    elif tag_id:
        print('>>>>>> ',tag_id)

        rename_to = request.GET['rename_to']
        print("new name ===== ",rename_to)
        old_name = ''
        if tag_id :
            try:
                tag = Tags_lpig.objects.get(pk=tag_id)
                old_name = tag.name
                tag.name = rename_to
                tag.updated_at = time.time()
                tag.save()
                if tag.attribute_id.id < 17 :
                    correct_tag_id=tag.tag_id
                    pre_create_communities.delay(tag_id=correct_tag_id)

            except:
                pass

        base_url = '/admin_dashboard/rename_tag'
        query_string = urlencode({'updated': True, 'old_name': old_name, 'tag_id': tag_id})
        url = '{}?{}'.format(base_url, query_string)

        return redirect(url)


def search(request):

    ''' function to fetch communities with searched tag '''

    search_key=request.GET.get('value')
    search_qs = Tags_lpig.objects.filter(name__icontains=search_key).distinct()[:20]
    name_list=[]
    for search in search_qs:
        name_list.append(search.name)
    return JsonResponse({'success':True,'tag_list':name_list})


##############  dashboard metrics   ###########

def metrics(request):

    '''This function returns the metrics'''
    return render(request, 'dashboard/metrics.html', {})


def community_metrics(request):

    '''The function created a community metrics'''

    community_list = Community.objects.order_by('-updated_at', '-active_since')
    page = request.GET.get('page', 1)
    paginator = Paginator(community_list, 10)
    try:
        community_list = paginator.page(page)
    except PageNotAnInteger:
        community_list = paginator.page(1)
    except EmptyPage:
        community_list = paginator.page(paginator.num_pages)

    communities=[]

    for community in community_list:
        temp={}
        temp['name']=community.name
        temp['total_members']=community.members_count
        state=community.hide_community
        if state == '0' or state == '4':
            temp['status']="Live"
        elif state == '3':
            temp['status']="Pilot"
        else:
            continue
        temp['tags']=community.id
        temp['created_at']=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(community.created_at))
        temp['last_activity_date']=time.strftime('%Y-%m-%d    %H:%M:%S', time.localtime(community.updated_at))
        temp['collabcard_count']=Collabcard.objects.filter(community_id=community.id).count()
        temp['tags_count']=get_tags_count(community)
        communities.append(temp)

    context={
        'communities':communities,
        'community': community_list
    }

    return render(request, 'dashboard/community_metrics.html', context)


def hidden_tags_for_metrcis(request,community_id):

    '''function to show hidden tags'''

    community = Community.objects.get(pk = community_id)

    legacy_tags = list(Tags_lpig.objects.filter(category_id__id = '1').values_list('name', flat=True))
    profession_tags = list(Tags_lpig.objects.filter(category_id__id = '2').values_list('name', flat=True))
    interests_tags = list(Tags_lpig.objects.filter(category_id__id = '3').values_list('name', flat=True))
    geography_tags = list(Tags_lpig.objects.filter(category_id__id = '4').values_list('name', flat=True))


    # hidden_tags = Community_LPIG.objects.filter(community_id=community_id)

    hidden_legacy_tags = list(Community_Legacy.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_profession_tags = list(Community_Profession.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_interests_tags = list(Community_Interest.objects.filter(community_id=community).values_list('tags_id', flat=True))
    hidden_geography_tags = list(Community_Geography.objects.filter(community_id=community).values_list('tags_id', flat=True))


    hidden_legacy_tag = ''
    hidden_profession_tag = ''
    hidden_interests_tag = ''
    hidden_geography_tag = ''


    for tag in hidden_legacy_tags:
        global_tag = Tags_lpig.objects.get(name='legacy_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_legacy_tag=hidden_legacy_tag+tag_object.name+","
        except:
            pass

    for tag in hidden_profession_tags:
        global_tag = Tags_lpig.objects.get(name='profession_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_profession_tag=hidden_profession_tag+tag_object.name+","
        except:
            pass


    for tag in hidden_interests_tags:
        global_tag = Tags_lpig.objects.get(name='interest_any')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_interests_tag=hidden_interests_tag+tag_object.name+","
        except:
            pass


    for tag in hidden_geography_tags:
        global_tag = Tags_lpig.objects.get(name='Global')
        if tag == global_tag.id:
            continue
        try:
            tag_object = Tags_lpig.objects.get(pk=tag)
            hidden_geography_tag = hidden_geography_tag+tag_object.name+","
        except:
            pass

    context={
        'legacy_tags':legacy_tags,
        'profession_tags':profession_tags,
        'interests_tags':interests_tags,
        'geography_tags':geography_tags,
        'hidden_legacy_tag':hidden_legacy_tag,
        'hidden_profession_tag': hidden_profession_tag,
        'hidden_interests_tag': hidden_interests_tag,
        'hidden_geography_tag': hidden_geography_tag,
        'community_id':community_id,
        'community_name':community.name
    }

    return render(request,'dashboard/tags_metrics.html',context)


def community_metrics_filter(request):
    '''The function created a community metrics'''

    select_type=request.GET.get('filter',None)

    if select_type=='pilot_live':
        community_list = Community.objects.filter(hide_community='4').order_by('-updated_at')
    elif select_type=='pilot_0_interested':
        community_list = Community.objects.filter(hide_community='3').filter(members_count=0).order_by('-updated_at')
    elif select_type=='pilot_1_interested':
        community_list = Community.objects.filter(hide_community='3').filter(members_count__gte=1).order_by('-updated_at')
    elif select_type == 'user_created':
        community_list = Community.objects.filter(hide_community='0').order_by('-updated_at')
    elif select_type == 'members_count_ascending':
        community_list = Community.objects.order_by('members_count','-updated_at')
    elif select_type == 'members_count_descending':
        community_list = Community.objects.order_by( '-members_count','-updated_at')
    elif select_type == 'interested_count_ascending':
        community_list = Community.objects.filter(hide_community='3').order_by('members_count','-updated_at')
    elif select_type == 'interested_count_descending':
        community_list = Community.objects.filter(hide_community='3').order_by( '-members_count','-updated_at')
    else:
        community_list = Community.objects.order_by('-updated_at')

    page = request.GET.get('page', 1)
    paginator = Paginator(community_list, 20)
    try:
        community_list = paginator.page(page)
    except PageNotAnInteger:
        community_list = paginator.page(1)
    except EmptyPage:
        community_list = paginator.page(paginator.num_pages)

    communities = []

    for community in community_list:
        temp = {}
        temp['name'] = community.name
        temp['total_members'] = community.members_count
        state = community.hide_community
        if state == '0' or state == '4':
            temp['status'] = "Live"
        elif state == '3':
            temp['status'] = "Pilot"
            temp['total_members'] =community.members_count
        else:
            continue


        temp['tags'] = community.id
        temp['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(community.created_at))
        temp['last_activity_date'] = time.strftime('%Y-%m-%d    %H:%M:%S', time.localtime(community.updated_at))
        temp['collabcard_count'] = Collabcard.objects.filter(community_id=community.id).count()
        temp['tags_count'] = get_tags_count(community)
        temp['url']=url+"/community/"+str(community.id)


        communities.append(temp)

    context = {
        'communities': communities,
        'community': community_list,
        'select_type':select_type
    }

    return render(request, 'dashboard/community_metrics.html', context)



############# user metrics ################

def user_metrics(request):

    '''The function created a community metrics'''

    userinfo = Userinfo.objects.order_by('-user_id')
    page = request.GET.get('page', 1)
    paginator = Paginator(userinfo, 20)
    try:
        user_list = paginator.page(page)
    except PageNotAnInteger:
        user_list = paginator.page(1)
    except EmptyPage:
        user_list = paginator.page(paginator.num_pages)

    users=[]

    for user in user_list:
        temp={}
        temp['name']=user.name
        member_of=Members.objects.filter(member_id=user.user_id.id)

        if len(member_of) == 1:
            status=member_of[0].community_id.name
        elif len(member_of) == 0:
            status="0"
        else:
            status="csv_file"
        temp['status']=status

        temp['count_of_joined_community']=Members.objects.filter(member_id=user.user_id.id)\
            .filter(Q(state=1)|Q(state=2)|Q(state=4)).count()
        temp['count_of_interested_community'] = Members.objects.filter(member_id=user.user_id.id) \
            .filter(Q(state=8) | Q(state=9)).count()
        temp['refered_count']=Referal.objects.filter(member=user.user_id.id).count()

        referrer=Referal.objects.filter(invited_member=user.user_id.id).order_by('id').first()
        if referrer:
           temp['referrer']=referrer.member.userinfo.name
        else:
            temp['referrer']="NA"

        is_promoter=Members.objects.filter(member_id=user.user_id.id).filter(state=1)
        if is_promoter:
            temp['is_promoter']="Y"
        else:
            temp['is_promoter']="N"

        if user.mobile_os == "Android":
            temp['has_android']="Yes"
        else:
            temp['has_android']="No"

        if user.fcm_token:
            temp['fcm_token']=True
        else:
            temp['fcm_token']=False

        if user.created_at < 0:
            temp['created_at']="NA"
        else:
            temp['created_at']=time.strftime('%Y-%m-%d    %H:%M:%S', time.localtime(user.created_at))
        temp['id']=user.user_id.id
        commmunities = Community_Rank.objects.filter(member_id=user.user_id)

        if commmunities:
            temp['relevance']=True
        else:
            temp['relevance']=False
        temp['onboarding'] = user_onbaord(user.user_id.id)
        users.append(temp)

        legacy=User_Legacy.objects.filter(user_id=user.user_id)
        profession=User_Profession.objects.filter(user_id=user.user_id)


        temp['legacy']=True if legacy else False
        temp['profession']=True if profession else False


    context={
        'users':users,
        'user':user_list
    }
    return render(request, 'dashboard/user_metrics.html', context)



def getfile(request,member_id):
    '''function to create a csv'''
    members=Members.objects.filter(member_id=member_id)
    member_list=[]
    for member in members:

        temp={}
        temp['name']=member.member_id.userinfo.name
        temp['community_name']=member.community_id.name
        state=member.state
        if state:
            if state == 1:
                temp['state'] = 'Promoter'
            elif state == 4:
                temp['state'] = 'Member'
            elif state == 8:
                temp['state'] = 'Interested Member'
            elif state == 9:
                temp['state'] = 'Eligible Promoter'
            else:
                continue
            member_list.append(temp)

    if member_list:
        response = HttpResponse(content_type='text/csv')
        file_name=member_list[0]['name']
        response['Content-Disposition'] = """attachment; filename=%s"""%(file_name)
        writer = csv.writer(response)

        writer.writerow(['UserName', 'Community', 'Status'])

        for member in member_list:
            #print(member)
            writer.writerow([member['name'],member['community_name'], member['state']])
        return response

    return HttpResponse("")


def get_relevant_communities_file(request,member_id):

    '''function to create a csv of relevant communities'''

    commmunities=Community_Rank.objects.filter(member_id=member_id)
    userinfo=Userinfo.objects.get(user_id=member_id)
    community_list=[]
    for community in commmunities:
        temp={}
        temp['name']=community.community_id.name
        community_list.append(temp)
    if community_list:
        response = HttpResponse(content_type='text/csv')
        file_name=str(userinfo.name)+"_relevant_communities"
        response['Content-Disposition'] = """attachment; filename=%s"""%(file_name)
        writer = csv.writer(response)

        writer.writerow(['Communities'])

        for data in community_list:
            #print(member)
            writer.writerow([data['name']])
        return response

    return HttpResponse("No Relevant Commmunities")

def get_relevant_communities_link(request,member_id):

    '''function to get relevant communities for a user'''

    commmunities = Community_Rank.objects.filter(member_id=member_id)
    userinfo = Userinfo.objects.get(user_id=member_id)
    file_name = " Relevant communities for "+str(userinfo.name)
    community_list = []
    for community in commmunities:
        temp = {}
        temp['name'] = community.community_id.name
        temp['url']=url+'/community/'+str(community.community_id.id)
        community_list.append(temp)
    return render(request,'dashboard/relevant_communities.html',{'name':file_name,'community_list':community_list})


def onboarding_metrics(request):

    '''The function created a community metrics'''

    userinfo = Userinfo.objects.order_by('-user_id')
    page = request.GET.get('page', 1)
    paginator = Paginator(userinfo, 20)
    try:
        user_list = paginator.page(page)
    except PageNotAnInteger:
        user_list = paginator.page(1)
    except EmptyPage:
        user_list = paginator.page(paginator.num_pages)

    users=[]

    for user in user_list:
        temp={}
        temp['name']=user.name

        if user.fcm_token:
            temp['fcm_token']=True
        else:
            temp['fcm_token']=False

        # temp['id']=user.user_id.id
        temp['onboarding'] = user_onbaord(user.user_id.id)
        users.append(temp)



    context={
        'users':users,
        'user':user_list
    }
    return render(request, 'dashboard/onboarding_metrics.html', context)


def map_all_tags(request):
    ''' fucntion to map a tag to other tag and categorize it  '''

    if request.method == 'GET':
        tags = Tags_lpig.objects.filter(~Q(attribute_id=16),~Q(attribute_id=17),
                                        ~Q(attribute_id=18),~Q(attribute_id=19),
                                        ~Q(attribute_id=20),~Q(category_id=6))
        return render(request, 'dashboard/map_all_tag.html', {'tags':tags})
    else:
        selected_tag = request.POST.get('selected_tag')
        map_tag_to = request.POST.get('map_tag_to')
        categorized_tag = Tags_lpig.objects.get(pk = selected_tag)
        mapped_tag = Tags_lpig.objects.get(pk=map_tag_to)

        # mapping the uncategorized tag to the mapped tag and
        # categorizing it accroding to the mapped tag

        categorized_tag.category_id = mapped_tag.category_id
        categorized_tag.attribute_id = mapped_tag.attribute_id
        categorized_tag.tag_id = mapped_tag.id
        categorize_tag.updated_at = time.time()
        categorized_tag.save()

        category=mapped_tag.category_id.id
        tag_id=selected_tag
        correct_tag_id=map_tag_to



        if category is 1:
            User_Legacy.objects.filter(tags_id=tag_id).update(correct_tag_id=correct_tag_id)
            Community_Legacy.objects.filter(tags_id=tag_id).update(correct_tag_id=correct_tag_id)
        elif category is 2:
            User_Profession.objects.filter(tags_id=tag_id).update(correct_tag_id=correct_tag_id)
            Community_Profession.objects.filter(tags_id=tag_id).update(correct_tag_id=correct_tag_id)
        elif category is 3:
            User_Interest.objects.filter(tags_id=tag_id).update(correct_tag_id=correct_tag_id)
            Community_Interest.objects.filter(tags_id=tag_id).update(correct_tag_id=correct_tag_id)
        elif category is 4:
            User_Geography.objects.filter(tags_id=tag_id).update(correct_tag_id=correct_tag_id)
            Community_Geography.objects.filter(tags_id=tag_id).update(correct_tag_id=correct_tag_id)

        #
        # print()


        return JsonResponse({'success': True})



def create_user_update(request):

    '''function to create user update for user'''

    # post method for inserting versions

    if request.method != 'GET':

        version= request.POST.get('version')
        version_dropdown= request.POST.get('version_dropdown')
        title=request.POST.get('title')
        message= request.POST.get('message')
        cta_text= request.POST.get('cta_text')
        cta_route= request.POST.get('cta_route')
        cancel_dropdown= request.POST.get('cancel_dropdown')

        #creating the route link
        cta_link=quote(cta_route)
        cta="""route://browser?link=%s"""%(cta_link)
        route="""route://dialog?title=%s&message=%s&cta_text=%s&cta=%s&cancelable=%s"""%(title,message,cta_text,cta,cancel_dropdown)


        version_no=App_Update_Info.objects.filter(version_code=version)
        if not version_no.exists():
            update=App_Update_Info()
            update.version_code=version
            update.android_route=route
            update.created_at=time.time()
            update.save()

        if version_dropdown == 'less_than_equal_to':
            App_Update_Info.objects.filter(version_code__lte=version).update(android_route=route)
        elif version_dropdown == 'less_than':
            App_Update_Info.objects.filter(version_code__lt=version).update(android_route=route)
        elif version_dropdown == 'equal_to':
            App_Update_Info.objects.filter(version_code=version).update(android_route=route)



        return JsonResponse({'success':True})



    else:

        max=App_Update_Info.objects.aggregate(Max('version_code'))
        latest_version=max['version_code__max']
        return render(request,'dashboard/app_update.html',{'latest_version':latest_version})


def disable_introduction_state(request,community_id):

    '''function to disable or enable the introduction text'''

    state=Community.objects.filter(id=community_id).update(introduction_text_state=1)

    return redirect('admin_dashboard')


def enable_introduction_state(request,community_id):

    '''function to disable or enable the introduction text'''

    state=Community.objects.filter(id=community_id).update(introduction_text_state=0)

    return redirect('admin_dashboard')


def add_report_tags(request):

    '''function to add report tags'''

    if request.method == 'GET':

        typ = request.GET.get('type',0)

        report_tags = Report_Tags.objects.filter(type=typ).order_by('id')
        context = {'report_tags':report_tags,
                   'length':report_tags.count(),
                   'type':typ}
        return render(request, 'dashboard/add_report_tags.html', context)
    else:
        option_data = request.POST.get('data')
        option_data = json.loads(option_data)

        for data in option_data:
            if data['update']:
                tag = Report_Tags.objects.get(pk=data['id'])
                tag.tag_name = data['tag_name']
                tag.save()
            else:
                tag = Report_Tags.objects.filter(tag_name__iexact=data['tag_name'],type=data['type'])
                if not tag.exists():
                    tag = Report_Tags()
                    tag.tag_name = data['tag_name']
                    tag.type = data['type']
                    tag.save()
                    tag.tag_id = tag.id
                    tag.save()
        return JsonResponse({"success": True})


def delete_report_tags(request,tag_id):
    '''function to delelte the questions'''
    Report_Tags.objects.filter(id=tag_id).delete()
    # report_tags = Report_Tags.objects.all()
    # return render(request, 'dashboard/add_report_tags.html', {'report_tags': report_tags,
    #                                                           'length': report_tags.count()})
    return redirect(reverse(add_report_tags))


def delete_collabcard(request):
    """ function to delete collabcard and related objects """
    if request.method == 'GET':
        context = {}
        return render(request, 'dashboard/delete_collabcard.html', context)
    else:
        card_id = request.POST.get('card_id')
        action = request.POST.get('action')

        card = Collabcard.objects.filter(pk=card_id)

        if not card.exists():
            return JsonResponse({"success": False, 'raise_error': True})

        elif action == 'show':
            card = card[0]

            return JsonResponse({"success": True, 'raise_error': False,
                                    'show_card': True, 'card_text': card.title,
                                    'community_name': card.community.name,
                                    })

        else:
            card = card[0]
            community_id = card.community.id

            # get all collabcard related objects
            card_attachments = Card_Attachment.objects.filter(collabcard=card)
            card_answers = CardAnswers.objects.filter(card=card)
            card_reports = Report.objects.filter(collabcard=card)

            # deleting all collabcard related objects
            card_attachments.delete()
            card_answers.delete()
            card_reports.delete()
            # delete collabcard
            card.delete()

            update_last_unseen_in_engage_on_card_creation.delay(community_id)


        return JsonResponse({"success": True, 'raise_error': False})


def approve_collabcard_for_feedback_community(request,card_id):

    '''function to approve the collabcard for feedback community'''

    card_instance=Collabcard.objects.get(id=card_id)
    community_instance=Community.objects.get(id=card_instance.community_id)
    user_instance=User.objects.get(id=card_instance.user_id)
    #saving state for card creater
    is_state=collabcardState.objects.filter(card=card_instance,user=user_instance)
    if not is_state.exists():
        collabcard_state_instance = collabcardState()
        collabcard_state_instance.card = card_instance
        collabcard_state_instance.user = user_instance
        collabcard_state_instance.community = community_instance
        collabcard_state_instance.state = collabcard_states.COLLABCARD_STATE_FOLLOW  # user has created the card and he is autofollowing
        collabcard_state_instance.created_at = time.time()
        collabcard_state_instance.updated_at = time.time()
        collabcard_state_instance.save()

    card_instance.type=0                #posted state
    card_instance.save()

    update_last_unseen_in_engage_on_card_creation(community_instance.id)

    typ=0



    send_notification_for_new_collabcard_posted.delay(community_instance.id, card_instance.title,
                                                      user_instance.id, user_instance.userinfo.name,
                                                      type=typ, date_time=card_instance.date_time,
                                                      card_id=card_instance.id,
                                                      community_name=community_instance.name,
                                                      community_state=community_instance.hide_community)


    send_email_for_collabcard(community_instance, user_instance.userinfo, card_instance, typ)

    return HttpResponse("Collabcard Posted")




