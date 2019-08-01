from django.shortcuts import render,redirect
from django.http import HttpResponse
from togther.models import *
from django.views.generic import *
from .forms import *
from django.db.models import Q
import time
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
# Create your views here.
from collabmates_api.notification import send_notification_for_join_requests,send_notification_to_proposed_admin
from django.conf import settings
import json
from django.http.response import JsonResponse
import requests as rqst
import os
import re

url = settings.URL

# uncomment to run it in localhost
# url='http://localhost:8000'

api_url = url + '/api/'

def dashboard(request):
  '''function to give list of community to edit'''

  community_list=Community.objects.all().order_by('-created_at','-active_since')
  dashboard_list=[]
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
      community_dic['active_since']=i.active_since
      community_dic['question_count']=Form_data.objects.filter(community_id=i).count()
      tags_count=get_tags_count(i)
      community_dic['tags_count']=tags_count['tags_count']
      community_dic['hidden_tags_count']=tags_count['hidden_tags_count']
      dashboard_list.append(community_dic)

  return render(request,'dashboard/dashboard.html',{'communities':dashboard_list})

def get_tags_count(community):

    '''function to get count of tags from dashboard'''

    tags_count=0
    hidden_tags_count=0
    community_tags=Community_tags.objects.filter(community_id=community)

    for tag in community_tags:

        if tag.tags_id == 41 or tag.tags_id == 42:
            hidden_tags_count=hidden_tags_count+1
            continue
        tags_count=tags_count+1

    tags={}
    tags['tags_count']=tags_count
    tags['hidden_tags_count']=hidden_tags_count
    return tags


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

        community=Community.objects.get(id=community_id)
        old_image_file = community.image_url
        # deleting the old file after new file is updated
        # get the new image file

        new_image_file = community_form.cleaned_data['image_url']

        new_image_file.name = str(community_id) + '__image__' + str(version) + '.jpg'
        if not old_image_file == new_image_file:
            # if both are not same delete old file
            if os.path.isfile(old_image_file.path):
                os.remove(old_image_file.path)
            community.image_url = new_image_file
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
    categories=Community_tags.objects.filter(community_id=community_id)
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


def user_tags(request,user_id):
    ''' gives all the user tags  '''
    tags = userinfo_tags.objects.filter(user_id= user_id)
    tags_list = []
    for i in tags:
        tag_name = Tags.objects.get(id = i.tag_id)
        tags_list.append(tag_name.category_name)
    # making a single string of all user tags
    tags = ','.join(tags_list)
    context={'tags': tags,'user_id':user_id}
    return render(request, 'dashboard/user_tags.html', context)

def add_user_tags(request):
    ''' adding or updating or deleting user hidden tags '''
    tags=request.GET.get('tags')
    user_id=request.GET.get('user_id')
    tags=tags.split(",")
    already_tags=request.GET.get('already_tags')
    already_tags=already_tags.split(",")
    # get all of the user tags
    user_tags_list = []
    user_tags = userinfo_tags.objects.filter(user_id=user_id)
    # making a list of it
    for tag in user_tags:
        tag_name = Tags.objects.get(id=tag.tag_id)
        user_tags_list.append(tag_name)
    flag = True
    for tag in tags:
        if tag == '0' :
            # if selected none just delete all of them
            userinfo_tags.objects.filter(user_id=user_id).delete()
            flag = False
        if tag not in already_tags:
            # if updated , delete the old ones which are not in the new list
            userinfo_tags.objects.filter(user_id=user_id).delete()
    if flag:
        for tag in tags:
            # create new tags for user which are now given
            selected_tags = userinfo_tags.objects.filter(user_id=user_id,tag_id = tag)
            print(selected_tags)
            if not selected_tags:
                user_tag = userinfo_tags()
                user_tag.user_id = user_id
                user_tag.tag_id = tag
                user_tag.save()

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
        tags = ','.join(tags_list)
        user_dic['tags'] = tags
        user_dic['tags_count'] = tags_count
        user_dic['fb_link'] = i.fb_link
        user_dic['linkedin_link'] = i.linkedin_link

        communities_count = Members.objects.all().filter(member_id=i.user_id).filter(~Q(state=0)).count()
        user_dic['communities_count']=communities_count
        users_list.append(user_dic)
    return render(request, 'dashboard/all_user.html', {'all_user': users_list})


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
        old_image_file = user_info.image_file
        new_image_file = user_info_form.cleaned_data['image_file']
        new_image_file.name ='profile_picture_' + str(user_info).replace(" ", "_") + '.jpeg'

        if not old_image_file == new_image_file:
            # if both are not same delete old file
            if os.path.isfile(old_image_file.path):
                os.remove(old_image_file.path)
            user_info.image_file = new_image_file
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
                                     "hello@collabmates.com",
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
    '''function to show the analytics'''
    community_count=Community.objects.all().count()
    public_communities=Community.objects.filter(hide_community='0').count()
    private_communities=Community.objects.filter(hide_community='1').count()
    user_count=Userinfo.objects.all().count()
    promoter_member_count=Members.objects.filter(~Q(state=0)).values('member_id').distinct().count()

    working_communitites=Community.objects.filter(Q(hide_community= 2))


    promoter_count=Members.objects.filter(Q(state=1)|Q(state=2)).values('member_id').distinct().count()
    member_count=Members.objects.filter(state=4).values('member_id').distinct().count()
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
        'responses_count':responses_count
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


def hidden_tags(request,community_id):

    '''function to show hidden tags'''

    hidden_tags=Community_tags.objects.filter(community_id=community_id).filter(Q(tags_id=41)|Q(tags_id=42))

    hidden_tag=''
    for tag in hidden_tags:
        hidden_tag=hidden_tag+tag.category
    context={
        'hidden_tags':hidden_tag,
        'community_id':community_id
    }

    return render(request,'dashboard/hidden_tags.html',context)



def add_hidden_tags(request):

    '''function to add hidden tags'''
    hidden_tag_id=request.GET.get('hidden_tag_id')
    community_id=request.GET.get('community_id')
    tag_id=int(hidden_tag_id)

    if tag_id == 0:
        query=Community_tags.objects.filter(community_id=community_id).filter(Q(tags_id=41)|Q(tags_id=42)).delete()
        return JsonResponse({'success':'Tags Deleted'})

    tag_name=Tags.objects.filter(id=tag_id).values('category_name')
    tag_name=tag_name[0]['category_name']
    is_tag_present=Community_tags.objects.filter(community_id=community_id).filter(Q(tags_id=41)|Q(tags_id=42))

    if is_tag_present:
        for tag in is_tag_present:
            Community_tags.objects.filter(id=tag.id).update(tags_id=tag_id,category=tag_name)
    community=Community.objects.get(id=community_id)
    if not is_tag_present:
        community_tags_object=Community_tags()
        community_tags_object.category=tag_name
        community_tags_object.community_id=community
        community_tags_object.tags_id=tag_id
        community_tags_object.save()
        print('New Data Inserted')





    return JsonResponse({'success':True})



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
                                 "hello@collabmates.com",
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