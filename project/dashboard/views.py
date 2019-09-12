from django.shortcuts import render,redirect
from django.http import HttpResponse
from togther.models import *
from django.views.generic import *
from .forms import *
from django.db.models import Q
from django.db.models import F
import time
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
from collabmates_api.notification import send_notification_for_join_requests, send_notification_to_proposed_admin
from django.conf import settings
import json
from django.http.response import JsonResponse
import requests as rqst
import os
import re
from django.views.decorators.csrf import csrf_exempt
from collabmates_api.raw_queries import compute_rank
from utility.pre_creation import pre_create_communities
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from urllib.parse import urlencode
from utility.utils import update_tag_image, get_city_address
url = settings.URL

# uncomment to run it in localhost
# url='http://localhost:8000'

api_url = url + '/api/'

def dashboard(request):
  '''function to give list of community to edit'''

  community_list=Community.objects.all().order_by('-created_at', '-active_since')
  dashboard_list=[]

  page = request.GET.get('page', 1)
  paginator = Paginator(community_list, 100)
  try:
      community_list = paginator.page(page)
  except PageNotAnInteger:
      community_list = paginator.page(1)
  except EmptyPage:
      community_list = paginator.page(paginator.num_pages)

  for i in community_list:
      community_dic={}
      if i.hide_community == '2':
          continue
      community_dic['id']=i.id
      community_dic['name']=i.name
      community_dic['image_url']=i.image_url
      community_dic['purpose']=i.purpose
      pending_members_count=Members.objects.filter(community_id=i,state=3).count()
      community_dic['pending_member_count'] = pending_members_count
      members_count = Members.objects.filter(community_id=i).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7)).count()
      community_dic['members_count'] = members_count
      community_dic['active_since']=i.active_since
      community_dic['question_count']=Form_data.objects.filter(community_id=i).count()
      community_dic['hidden_tags_count']=get_tags_count(i)
      dashboard_list.append(community_dic)
  return render(request,'dashboard/dashboard.html',{'communities':dashboard_list,'community':community_list})


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
        old_image_file = community.image_url
        # get the version of the image
        version = re.findall(r'\w*__image__(\d+)', old_image_file.name)
        if version:
            version = int(version[0]) + 1
        else:
            version = 1

        community_form=CommunityForm(request.POST,request.FILES,instance=community)
        admins=Members.objects.filter(community_id=community).filter(Q(state=1)|Q(state=2))
        member_id=0
        purpose=""
        rename = False
        if community_form.is_valid():
            purpose=community_form.cleaned_data['purpose']
            for_string=purpose.split(' ', 1)[0]
            purpose = "Created this community " + for_string.lower() + purpose.split("For", 1)[1]
            # deleting the old file after new file is updated
            # get the new image file
            new_image_file = community_form.cleaned_data['image_url']
            if not old_image_file == new_image_file:
                # if both are not same delete old file
                if os.path.isfile(old_image_file.path):
                    os.remove(old_image_file.path)
                    rename =True
        else:
            print("some error is there")
        if admins:
            for admin in admins:
                member_id=admin.member_id
                break;

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
        community_form.save()

        # renaming the image
        if rename:
            community=Community.objects.get(id=community_id)
            new_name = 'media/'+str(community_id) + '__image__' + str(version) + '.jpg'
            old_path = community.image_url.path
            community.image_url.name = new_name
            os.rename(old_path, community.image_url.path)
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
    community = Community.objects.get(id=community_id)
    Members.objects.filter(community_id=community,member_id=member_id).update(state=4)
    update_member_count(community_id)
    url='/admin_dashboard/all_members/'+str(community_id)
    send_notification_for_join_requests.delay(community_id,True,member_id)
    return redirect(url)


def decline_member(request,community_id,member_id):
    '''function to approve member'''
    community = Community.objects.get(id=community_id)

    Members.objects.filter(community_id=community,member_id=member_id).update(state=5)
    url='/admin_dashboard/all_members/'+str(community_id)
    send_notification_for_join_requests.delay(community_id,False,member_id)

    return redirect(url)


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
    users_list = []
    for i in userinfo:
        user_dic = {}
        user_dic['id'] = i.id
        user_dic['user_id'] = i.user_id.id
        user_dic['name'] = i.name
        user_dic['email'] = i.email
        user_dic['image_url'] = i.image_file
        if i.fcm_token:
            print("has token")
            user_dic['fcm_token'] = 1
        else:
            print("no token")
            user_dic['fcm_token'] = 0
        tags = userinfo_tags.objects.filter(user_id=i.user_id.id)
        tags_count = tags.count()
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
    return render(request, 'dashboard/all_user.html', {'all_user': users_list})


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
        old_image_file = user_info.image_file
        user_info_form=UserForm(request.POST,request.FILES or None,instance=user_info)
        # deleting the old file after new file is updated
        if user_info_form.is_valid():
            # get the new image file
            new_image_file = user_info_form.cleaned_data['image_file']
            if not old_image_file == new_image_file:
                # if both are not same delete old file
                if os.path.isfile(old_image_file.path):
                    # if file is present
                    os.remove(old_image_file.path)
        user_info_form.save()
        # saving with the new name
        user_info = Userinfo.objects.get(user_id = user_id)
        # renaming the image
        new_name ='media/profile_pics/profile_picture_' + str(user_info).replace(" ", "_") + '.jpeg'
        old_path = user_info.image_file.path
        user_info.image_file.name = new_name
        os.rename(old_path, user_info.image_file.path)
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
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin, email=email, ProposedAdmin=ProposedAdmin,
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
                                     "Collabmates<hello@collabmates.com>",
                                     [to],
                                     )
    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)


def all_members(request,community_id):

    '''function to show all members of the community'''

    members_info=Members.objects.filter(community_id=community_id)
    members_list=[]
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

        image_url=Userinfo.objects.filter(user_id=i.member_id).values('image_file')
        image_url=image_url[0]['image_file']
        member['image_file']=image_url
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
        userinfo=Userinfo.objects.filter(email = user.email)
        if userinfo :
            continue

        unregitered_users_list.append(member)

    return render(request,'dashboard/all_members.html',{'member_list':members_list,'unregitered_users_list':unregitered_users_list})


def delete_members(request,community_id,member_id):

    '''function to delete the members'''
    promoter=Members.objects.filter(community_id=community_id)
    promoter_count=0
    for i in promoter:
       if i.state == 1 or i.state == 2:
           promoter_count=promoter_count+1

    state_of_member=Members.objects.filter(community_id=community_id,member_id=member_id).values('state')
    member_state=state_of_member[0]['state']
    if promoter_count == 1 and (member_state==1 or member_state==2):
        return HttpResponse("You cannot Delete the promoter.First make a promoter in order to delete")
    Members.objects.filter(community_id=community_id,member_id=member_id).delete()
    update_member_count(community_id)
    return redirect('admin_dashboard')


def add_questions(request,community_id):

    '''function to add and edit questions'''
    questions=Form_data.objects.filter(community_id=community_id)
    community_name=Community.objects.filter(id=community_id).values('name')
    question_list=[]
    for question in questions:
        question_list.append(question)

    context={
        'question_list':question_list,
        'community_name':community_name[0]['name'],
        'length':len(question_list),
        'community_id':community_id
    }

    question_data=request.GET.get('data',None)
    if question_data is not None:
        question_data=json.loads(question_data)

        for question in question_data:

           if len(question['question']) == 0:
               continue
           if question['update']:
               Form_data.objects.filter(id=question['id']).update(data=question['question'])
           else:
               form_data=Form_data()
               form_data.community_id=Community.objects.get(id=community_id)
               form_data.data=question['question']
               form_data.save()

    return render(request,'dashboard/add_questions.html',context)


def delete_questions(request,question_id):
    '''function to delelte the questions'''
    form_data=Form_data.objects.filter(id=question_id)
    community_id=0
    for i in form_data:
        community_id=i.community_id.id
    Form_data.objects.filter(id=question_id).delete()
    url='/admin_dashboard/add_questions/'+str(community_id)
    return redirect(url)


def analytics(request):
    ''' function to show the analytics '''

    community_count=Community.objects.all().count()
    public_communities=Community.objects.filter(hide_community='0').count()
    private_communities=Community.objects.filter(hide_community='1').count()
    user_count=Userinfo.objects.all().count()
    promoter_member_count=Members.objects.filter(~Q(state=0)).values('member_id').distinct().count()
    working_communitites=Community.objects.filter(Q(hide_community= 2))


    promoter_count=Members.objects.filter(Q(state=1)|Q(state=2)).values('member_id').distinct().count()
    total_promoter_count = Members.objects.filter(Q(state=1)|Q(state=2)).values('member_id').count()
    member_count=Members.objects.filter(state=4).values('member_id').distinct().count()
    total_member_count = Members.objects.filter(state=4).values('member_id').count()
    conversations_count=Collabcard.objects.all().count()
    responses_count=card_answers.objects.all().count()
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
    }
    return render(request,'dashboard/analytics.html',context)


def analytics_community(request,community_id):

    '''function to show analytics of community'''

    collabcard=Collabcard.objects.filter(community_id=community_id)
    collabcard_count=0
    collabcard_answer_count=0

    for each_collabcard in collabcard:
        collabcard_count=collabcard_count+1
        answer_count=card_answers.objects.filter(card_id=each_collabcard.id).count()
        collabcard_answer_count=collabcard_answer_count+answer_count

    context={
        'conversations_count':collabcard_count,
        'answers_count':collabcard_answer_count
    }

    return render(request,'dashboard/community_analytics.html',context)


def is_tag_present(tag,hide_status):
    '''function to check whether the tag is present or not'''
    tags=Tags.objects.filter(category_name=tag)

    if tags:
        return tags[0].id
    else:
        new_tag=Tags()
        new_tag.category_name=tag
        if hide_status:
            new_tag.state=1
        new_tag.save()
        return new_tag.id


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

    compute_rank.delay(community_id=community_id)

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
            Community_Legacy.objects.filter(tags_id = tag,community_id=community).delete()

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


def get_or_create_tag_attributes_list(tags,tag_type):

    ''' function get list of tag id's accroding to given list of strings '''

    tags_list=[]

    if len(tags) == 1 and tags[0]=='':
        return tags_list
    for each_tag in tags:

        tag = Tags_lpig.objects.filter(name = each_tag)
        print("tag ========= ",tag)

        if len(tag)>0:
            tag=tag[0]

        elif len(tag) == 0:
            tag = create_uncategorized_tag(each_tag,tag_type)

        if tag.id not in tags_list:
            tags_list.append(tag.id)
    return tags_list


def create_uncategorized_tag(tag,tag_type):
    ''' function to create a un-categorized tag '''

    new_tag = tag
    new_tag = new_tag.strip().capitalize()
    if new_tag!='':
        category = Category.objects.filter(Q(name__icontains=tag_type))[0]
        attribute = Attributes.objects.filter(Q(attribute_name__icontains=tag_type), Q(attribute_name__icontains='Uncategorized'))[0]
        tag = Tags_lpig.objects.filter(name = new_tag)
        if not tag.exists():
            tag = Tags_lpig()
            tag.name = new_tag
            tag.category_id = category
            tag.attribute_id = attribute
            tag.save()
            tag.tag_id = tag.id
            tag.save()
        else:
            tag = tag[0]
        if tag_type == 'Geography':
            tag_name, tag_id = new_tag, tag.id
            update_tag_image.delay(tag_name=tag_name, tag_id=tag_id)
        return tag
    return None


def delete_hidden_tags(request):

    '''function to delete the hidden tags'''

    tag = request.GET.get('del_uncategorized')
    Tags_lpig.objects.filter(pk=tag).delete()

    return JsonResponse({'success': True})


def add_location_tags(location,community_id):

    '''function to add location tags for a communities'''

    location_list=location.split(",")

    for data in location_list:
        if data:
            tag_id=is_tag_present(data,True)
            is_present=Community_tags.objects.filter(community_id=community_id,tags_id=tag_id)
            community = Community.objects.get(id=community_id)
            if not is_present:
                community_tags_object = Community_tags()
                community_tags_object.category = data
                community_tags_object.community_id = community
                community_tags_object.state='1'
                community_tags_object.tags_id = tag_id
                community_tags_object.save()

    print('location Inserted Successfully')


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
        subject="""Thanks for joining CollabMates! Here's the next step"""

    else:
        template = get_template("mails/testing_signup.html").render(context)
        subject="""Access to the first version of CollabMates App"""


    msg = EmailMultiAlternatives(subject,
                                 template,
                                 "Collabmates<hello@collabmates.com>",
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
        mem_state_url = api_url + 'members_state'
        params = {'member_id': user_id,"community_id" : community.id}
        response = rqst.get(mem_state_url,params=params)
        if response.status_code == 200:
            state = json.loads(response.content.decode('utf-8'))['state']
            if state:
                if state ==1:
                    comm['state'] = 'Promoter'
                elif state ==2:
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
        new_tag = new_tag.strip().capitalize()

        get_or_create_sub_tags(new_tag, category, attribute)

        return redirect('create_tag')

    else:
        categories = Category.objects.filter(~Q(name__icontains = 'ncategorized'))
        legacy_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Legacy'),~Q(attribute_name__icontains = 'uncategorized'))
        profession_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Profession'),~Q(attribute_name__icontains = 'uncategorized'))
        interests_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Interests'),~Q(attribute_name__icontains = 'uncategorized'))
        geography_attributes  = Attributes.objects.filter(Q(attribute_name__icontains = 'Geography'),~Q(attribute_name__icontains = 'uncategorized'))
        global_attributes = Attributes.objects.filter(Q(attribute_name__icontains='Global'),~Q(attribute_name__icontains = 'uncategorized'))

        return render(request, 'dashboard/create_tag.html', {'categories': categories,
                                                     'legacy_attributes': legacy_attributes,
                                                     'profession_attributes': profession_attributes,
                                                     'geography_attributes': geography_attributes,
                                                     'interests_attributes': interests_attributes,
                                                     'global_attributes': global_attributes, })


def get_or_create_sub_tags(new_tag,category,attribute):

    ''' function to create sub tags with known category and attribute  '''

    try:
        tag = Tags_lpig.objects.get(name=new_tag)
    except:
        category = Category.objects.get(id = category)
        attribute = Attributes.objects.get(id = attribute)
        tag = Tags_lpig()
        tag.name = new_tag
        tag.category_id = category
        tag.attribute_id = attribute
        tag.save()
        tag.tag_id =tag.id
        tag.save()
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
                                                       Q(attribute_id = geography_uncat.id ))

        categortized_tags = Tags_lpig.objects.filter(~Q(attribute_id__id = legacy_uncat.id )|
                                                     ~Q(attribute_id__id = profession_uncat.id)|
                                                     ~Q(attribute_id__id = interests_uncat.id)|
                                                     ~Q(attribute_id__id = geography_uncat.id)).order_by("name")


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
                                                                  'uncategortized_tags':uncategortized_tags,
                                                                  'categortized_tags': categortized_tags,
                                                                  'legacy_attributes': legacy_attributes,
                                                                  'profession_attributes': profession_attributes,
                                                                  'geography_attributes': geography_attributes,
                                                                  'interests_attributes': interests_attributes,
                                                                  'global_attributes': global_attributes, })


def update_uncategorize_tag(uncategorized, category, attribute):

    ''' tag is updated here according to category and attribute '''

    category = Category.objects.get(id=category)
    attribute = Attributes.objects.get(id=attribute)

    tag = Tags_lpig.objects.get(id  = uncategorized)
    tag.attribute_id = attribute
    tag.category_id = category
    tag.save()
    return tag.id


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


def save_user_lpig_tags(user_id,legacy_tags,profession_tags,interest_tags,greography_tags):

    ''' function to update or create and delete users L,P,I,G tags '''

    user = User.objects.get(id=user_id)
    global_tag = Tags_lpig.objects.get(name='legacy_any')

    user_tags_list = list(User_Legacy.objects.filter(user_id=user).values_list("tags_id",flat=True))
    # adding global tag to list manually
    legacy_tags.append(str(global_tag.id))

    for each_tag in legacy_tags:
        if each_tag in user_tags_list:
            continue
        elif not each_tag in user_tags_list:


            tag = Tags_lpig.objects.get(pk=each_tag)
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

            if str(tag[0].tags_id.id) != '15':
                tag.delete()

    # profession tags update --------------------------------->

    global_tag = Tags_lpig.objects.get(name='profession_any')
    user_tags_list = list(User_Profession.objects.filter(user_id=user).values_list("tags_id",flat=True))

    profession_tags.append(str(global_tag.id))

    for each_tag in profession_tags:
        if each_tag in user_tags_list:
            continue
        elif not each_tag in user_tags_list:
            tag = Tags_lpig.objects.get(pk=each_tag)
            tags = User_Profession.objects.filter(tags_id=tag, user_id=user)

            if not tags.exists():
                user_tag = User_Profession()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()

        else:
            pass

    for tag in user_tags_list:
        if tag not in profession_tags:

            tag = User_Profession.objects.filter(tags_id=tag, user_id=user)

            if str(tag[0].tags_id.id) != '16':
                tag.delete()

    # interests tags update --------------------------------->

    global_tag = Tags_lpig.objects.get(name='interest_any')
    user_tags_list = list(User_Interest.objects.filter(user_id=user).values_list("tags_id",flat=True))
    interest_tags.append(str(global_tag.id))

    for each_tag in interest_tags:
        if each_tag in user_tags_list:

            continue
        elif not each_tag in user_tags_list:
            tag = Tags_lpig.objects.get(pk=each_tag)
            tags = User_Interest.objects.filter(tags_id=tag, user_id=user)

            if not tags.exists():
                user_tag = User_Interest()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()
        else:
            pass

    for tag in user_tags_list:
        if tag not in interest_tags:

            tag = User_Interest.objects.filter(tags_id=tag, user_id=user)

            if str(tag[0].tags_id.id) != '17':
                tag.delete()

    # geography tags update --------------------------------->

    global_tag = Tags_lpig.objects.get(name='Global')
    user_tags_list = list(User_Geography.objects.filter(user_id=user).values_list("tags_id",flat=True))

    greography_tags.append(str(global_tag.id))
    for each_tag in greography_tags:
        if each_tag in user_tags_list:

            continue
        elif not each_tag in user_tags_list:
            tag = Tags_lpig.objects.get(pk=each_tag)
            tags = User_Geography.objects.filter(tags_id=tag, user_id=user)

            if not tags.exists():
                user_tag = User_Geography()
                user_tag.tags_id = tag
                user_tag.user_id = user
                user_tag.save()

        else:
            pass

    for tag in user_tags_list:
        if tag not in greography_tags:

            tag = User_Geography.objects.filter(tags_id=tag, user_id=user)

            if str(tag[0].tags_id.id) != '18':
                tag.delete()
    update_user_geography_tags(user_id=user_id, typ='Geography')


def update_user_geography_tags(user_id, typ=''):

    user = User.objects.get(id=user_id)
    print("inside function")
    user_tags_list = []
    if typ == 'Geography':
        user_tags_list = list(User_Geography.objects.filter(user_id=user).values_list("tags_id",flat=True))
    elif typ == 'Legacy':
        user_tags_list = list(User_Legacy.objects.filter(user_id=user, tags_id__attribute_id=3).values_list("tags_id",flat=True))

    # save city,district state and country of a particular city tag
    for each_tag in user_tags_list:
        tag = Tags_lpig.objects.get(pk=each_tag)
        tag_name = tag.name
        if tag.id == 15 or tag.id == 16 or tag.id == 17 or tag.id == 18:
            continue
        print('tag_name',tag_name)
        geography_list = get_city_address(city = tag_name)
        print('geography_list ====',geography_list,type(geography_list))


        for attr,tag_name in geography_list.items():

            print(">>>>>>>>",tag_name)
            if tag_name == '':
                continue
            tag = Tags_lpig.objects.filter(name=tag_name)
            print("tag <<<<<<<  ",tag,tag.exists())
            if not tag.exists():
                if typ == 'Geography':
                    tag = create_categorized_tag(tag=tag_name,category='Geography',attribute=attr)
                    print('created tag ====== ',tag)
                elif typ == 'Legacy':
                    tag = create_categorized_tag(tag=tag_name,category='Legacy',attribute=attr)
                    #print('created tag ====== ',tag)
            else:
                tag = tag[0]


            if typ == 'Geography':
                user_geo_tag = User_Geography.objects.filter(tags_id=tag, user_id=user)

                if not user_geo_tag.exists():
                    user_geo_tag = User_Geography()
                    user_geo_tag.tags_id = tag
                    user_geo_tag.user_id = user
                    user_geo_tag.save()
                print('user_geo_tag === ',user_geo_tag)
            elif typ == 'Legacy':
                user_legacy_tag = User_Legacy.objects.filter(tags_id=tag, user_id=user)
                if not user_legacy_tag.exists():
                    user_tag = User_Legacy()
                    user_tag.tags_id = tag
                    user_tag.user_id = user
                    user_tag.save()


def create_categorized_tag(tag,category,attribute):
    ''' function to create a un-categorized tag '''

    new_tag = tag
    new_tag = new_tag.strip().capitalize()
    if new_tag!='':
        category = Category.objects.filter(Q(name__icontains=category))[0]
        if not (category == 'Geography' and attribute == 'district'):

            attribute = Attributes.objects.filter(Q(attribute_name__icontains=attribute))[0]
            tag = Tags_lpig.objects.filter(name = new_tag)
            if not tag.exists():
                tag = Tags_lpig()
                tag.name = new_tag
                tag.category_id = category
                tag.attribute_id = attribute
                tag.save()
                tag.tag_id = tag.id
                tag.save()
            else:
                tag = tag[0]
            if category == 'Geography':
                tag_name, tag_id = new_tag, tag.id
                update_tag_image.delay(tag_name=tag_name, tag_id=tag_id)
            return tag
    return None


def map_tags(request):

    ''' fucntion to map a tag to other tag and categorize it  '''

    uncategorized_tag = request.GET.get('uncategorized_tag')
    mapped_tag = request.GET.get('mapped_tag')

    uncategorized_tag = Tags_lpig.objects.get(pk = uncategorized_tag)
    mapped_tag = Tags_lpig.objects.get(pk=mapped_tag)

    uncategorized_tag.category_id = mapped_tag.category_id
    uncategorized_tag.attribute_id = mapped_tag.attribute_id
    uncategorized_tag.tag_id = mapped_tag.id
    uncategorized_tag.save()

    compute_rank.delay()
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


        legacy_work=Tags_lpig.objects.filter(attribute_id=1).order_by('id')
        legacy_education = Tags_lpig.objects.filter(attribute_id=2).order_by('id')
        legacy_hometown=Tags_lpig.objects.filter(attribute_id=3).order_by('id')
        legacy_life_style = Tags_lpig.objects.filter(attribute_id=4).order_by('id')

        profession_skill = Tags_lpig.objects.filter(attribute_id=5).order_by('id')
        profession_industry = Tags_lpig.objects.filter(attribute_id=6).order_by('id')
        profession_designation = Tags_lpig.objects.filter(attribute_id=7).order_by('id')

        interest_cause = Tags_lpig.objects.filter(attribute_id=8).order_by('id')
        interest_hobby = Tags_lpig.objects.filter(attribute_id=9).order_by('id')
        interest_sports = Tags_lpig.objects.filter(attribute_id=10).order_by('id')
        interest_fan = Tags_lpig.objects.filter(attribute_id=11).order_by('id')

        geography_city = Tags_lpig.objects.filter(attribute_id=12).order_by('id')
        geography_state = Tags_lpig.objects.filter(attribute_id=13).order_by('id')
        geography_country = Tags_lpig.objects.filter(attribute_id=14).order_by('id')
        geography_pincode = Tags_lpig.objects.filter(attribute_id=15).order_by('id')

        return render(request, 'dashboard/update_tag.html', {'categories': categories,
                                                             'legacy_attributes': legacy_attributes,
                                                             'profession_attributes': profession_attributes,
                                                             'interests_attributes': interests_attributes,
                                                             'geography_attributes': geography_attributes,

                                                             'interest_hobby': interest_hobby,
                                                             'interest_sports': interest_sports,
                                                             'interest_fan': interest_fan,
                                                             'interest_cause': interest_cause,

                                                             'profession_industry': profession_industry,
                                                             'profession_skill': profession_skill,
                                                             'profession_designation': profession_designation,

                                                             'legacy_education': legacy_education,
                                                             'legacy_work': legacy_work,
                                                             'legacy_hometown': legacy_hometown,
                                                             'legacy_life_style':legacy_life_style,

                                                             'geography_state': geography_state,
                                                             'geography_country': geography_country,
                                                             'geography_pincode': geography_pincode,
                                                             'geography_city': geography_city,

                                                             'updated':updated
                                                             })


def tag_update_form(request,tag_id):

    ''' function to update tags with forms '''

    tag = Tags_lpig.objects.get(pk=tag_id)
    attr_id = tag.attribute_id.id

    if request.method=="POST":
        characteristics = None
        image = None
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

        # elif attr_id == 6:
        #     form = Profession_Industry_Form(request.POST, request.FILES)
        #     if form.is_valid():
        #         demonym = form.cleaned_data['demonym']
        #         short_name = form.cleaned_data['short_name']
        #         image = form.cleaned_data['image']
        #
        #         characteristics = {'demonym': demonym, 'csn': short_name}


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
                image = form.cleaned_data['image']
                characteristics = {'hobbyists': hobbyists,
                                   'hobby_group_used_case': hobby_group_used_case,
                                   'hobby_group_event':hobby_group_event,
                                   'hobby_event':hobby_event,
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
            tag.tag_image = image
        tag.tag_characterstics = json.dumps(characteristics)
        tag.save()

        base_url = reverse('update_tag')  # 1 /products/
        query_string = urlencode({'updated':True})  # 2 category=42
        url = '{}?{}'.format(base_url, query_string)
        pre_create_communities.delay(tag_id=tag_id)
        return redirect(url)

    else:

        # render form according to attribute given

        if attr_id == 2:
            char={}
            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)
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
            demonym = None
            short_name = None
            if 'home_demonym' in char:
                demonym = char['home_demonym']

            characteristics = {'demonym': demonym}

            form = Legacy_Hometown_Form(characteristics)
        elif attr_id == 5:

            char = {}
            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)
            skill_experts = None
            if 'skill_experts' in char:
                skill_experts = char['skill_experts']

            characteristics = {'skill_experts': skill_experts}

            form = Profession_Skill_Form(characteristics)
        # elif attr_id == 6:
        #
        #     char = {}
        #     if tag.tag_characterstics:
        #         char = json.loads(tag.tag_characterstics)
        #     demonym = None
        #     short_name = None
        #
        #     if 'demonym' in char:
        #         demonym = char['demonym']
        #     if 'csn' in char:
        #         short_name = char['csn']
        #     characteristics = {'demonym': demonym, 'short_name': short_name}
        #
        #     form = Profession_Industry_Form(characteristics)
        elif attr_id == 8:

            char = {}
            thing_event = None
            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)

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

            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)

            if 'hobbyists' in char:
                hobbyists = char['hobbyists']

            if 'hobby_group_used_case' in char:
                hobby_group_used_case = char['hobby_group_used_case']

            if 'hobby_group_event' in char:
                hobby_group_event = char['hobby_group_event']

            if 'hobby_event' in char:
                hobby_event = char['hobby_event']

            characteristics = {'hobbyists': hobbyists,
                               'hobby_group_used_case': hobby_group_used_case,
                               'hobby_group_event': hobby_group_event,
                               'hobby_event': hobby_event
                               }

            form = Interests_Hobby_Form(characteristics)

        elif attr_id == 10:

            char = {}
            sport_players = None
            sport_usecase = None
            sport_event = None

            if tag.tag_characterstics:
                char = json.loads(tag.tag_characterstics)

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
            demonym = None
            if 'demonym' in char:
                demonym = char['demonym']

            characteristics = {'demonym': demonym}

            form = Geography_Form(characteristics)

        else:

            form = Tag_Form()

        tag_image = None
        if tag.tag_image:
            tag_image =tag.tag_image.url

        return render(request, 'dashboard/update_tag_form.html', {'form':form,
                                                             'tag_name':tag.name,
                                                             'tag_id':tag.id,
                                                             'attr_id':tag.attribute_id.id,
                                                             'tag_image':tag_image
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
    tags = Tags_lpig.objects.all()
    return render(request, 'dashboard/delete_tags.html', {'tags': tags,'deleted':deleted,'alrt':alrt,'tag_name':tag_name})


def delete_tags_post(request,tag_id):

    ''' function to delete the any tag and
    communities with that tag and all community related things '''
    tag_deleted = True

    # print(request.POST)
    # tag = request.POST.get('del_tag')
    # print("tag =========== ",tag)
    tags = Tags_lpig.objects.filter(id=tag_id)
    tag = tags[0]
    print(">>>>>>>>>>",tag)
    tag_community = None
    user_tags = None
    category_id = tag.category_id.id
    print("cat id",category_id)

    if category_id == 1:
        tag_community = Community_Legacy.objects.filter(tags_id = tag)
        user_tags = User_Legacy.objects.filter(tags_id = tag)
    elif category_id == 2:
        tag_community = Community_Profession.objects.filter(tags_id = tag)
        user_tags = User_Profession.objects.filter(tags_id = tag)

    elif category_id == 3:
        tag_community = Community_Interest.objects.filter(tags_id = tag)
        user_tags = User_Interest.objects.filter(tags_id = tag)

    elif category_id == 4:
        tag_community = Community_Geography.objects.filter(tags_id = tag)
        user_tags = User_Geography.objects.filter(tags_id = tag)

    print(tag_community.exists())
    print(tag_community)

    if tag_community.exists():
        for community in tag_community:
            tag_community_id = community.community_id.id
            print("community id ====== ",tag_community_id)

            community_members_count = Members.objects.filter(community_id=community.community_id).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7)).count()
            print("members count ==== ",community_members_count)
            if community_members_count == 0:
                print("community will be deleted")

                community_purpose_card_id = community.community_id.purpose_collabcard
                try:
                    card = Collabcard.objects.filter(id=community_purpose_card_id)  #
                    if card.exists():
                        print(card)
                        card.delete()
                except:
                    print("problem with card")

                Community.objects.filter(id=tag_community_id).delete()

            elif community_members_count > 0:
                if not tag_deleted:
                    continue
                tag_deleted = False


    if tag_deleted:
        user_tags.delete()
        tags.delete()

    base_url = reverse('delete_tags')  # 1 /products/
    query_string = urlencode({'deleted': tag_deleted,'alrt':True,'tag_id':tag_id})  # 2 category=42
    url = '{}?{}'.format(base_url, query_string)

    return redirect(url)



