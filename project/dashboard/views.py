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
from collabmates_api.notification import send_notification_for_join_requests
from django.conf import settings
url  = settings.URL

def dashboard(request):
  '''function to give list of community to edit'''

  community_list=Community.objects.all().order_by('-created_at','-active_since')



  return render(request,'dashboard/dashboard.html',{'communities':community_list})


def update_form(request,community_id):
    '''function to update form for community and also purpose collabcard'''
    if request.method == 'POST':


        community=Community.objects.get(id=community_id)
        community_form=CommunityForm(request.POST,request.FILES,instance=community)
        admins=Members.objects.filter(community_id=community).filter(Q(state=1)|Q(state=2))
        member_id=0
        purpose=""
        if community_form.is_valid():
            purpose=community_form.cleaned_data['purpose']
            for_string=purpose.split(' ', 1)[0]
            purpose = "Created this community " + for_string.lower() + purpose.split("For", 1)[1]
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

        return redirect('admin_dashboard')
    else:
        community=Community.objects.get(id=community_id)
        community_form=CommunityForm(instance=community)

    context={'community_form':community_form,'community':community}
    return render(request,'dashboard/community.html',context)


def community_delete(request,community_id):
    '''function to delete the community'''
    Community.objects.filter(id=community_id).delete()
    return redirect('admin_dashboard')


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
    print("length == ",len(count))
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
    url='/admin_dashboard/show_pending_member/'+str(community_id)
    send_notification_for_join_requests(community_id,True,member_id)
    return redirect(url)

def decline_member(request,community_id,member_id):
    '''function to approve member'''
    community = Community.objects.get(id=community_id)

    Members.objects.filter(community_id=community,member_id=member_id).update(state=5)
    url='/admin_dashboard/show_pending_member/'+str(community_id)
    send_notification_for_join_requests(community_id,False,member_id)

    return redirect(url)


def show_tags(request,community_id):
    '''Taging communitites'''
    print(community_id)
    categories=Category.objects.filter(community_id=community_id)
    category_string=""
    for i in categories:
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
    community_category=Category.objects.filter(community_id=community_id)

    for category in community_category:
        category_list.append(str(category))

    for category in category_list:
        if category not in already_category:
            Category.objects.filter(community_id=community_id,category=category).delete()

    for category in categories:

        selected_categories=Category.objects.filter(community_id=community_id,category=category)
        if not selected_categories:
            cat=Category()
            cat.community_id=Community.objects.get(id=community_id)
            cat.category=category
            cat.save()


    return redirect('admin_dashboard')

def all_user(request):

    '''dashboard to show all users'''
    userinfo=Userinfo.objects.all()

    return render(request, 'dashboard/all_user.html', {'all_user': userinfo})


def update_user(request,email):

    if request.method == 'POST':

        user_info = Userinfo.objects.get(email=email)
        user_info_form=UserForm(request.POST,request.FILES or None,instance=user_info)
        user_info_form.save()
        return redirect('all_user')
    else:
        context={}
        try:
            user_info = Userinfo.objects.get(email=email)
            user_info_form = UserForm(instance=user_info)
            context = {'user_info_form': user_info_form,'user_info':user_info}
        except Exception as e:
            print(e)
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
            print("proposed name  == ",proposed_name)
            print("proposed email  == ",proposed_email)
            print("proposed no  == ",proposed_no)
            print("proposer name  == ",proposer_name)
            print("proposer email  == ",proposer_email)
            proposed_admin = User.objects.filter(email=proposer_email).first()
            print("proposer check  == ",proposed_admin)
            print("proposer id  == ",proposed_admin.id)
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

def check_community_admin(community_id,proposed_admin_id):
    community = Community.objects.filter(id= community_id)
    promoter_id = User.objects.get(id = proposed_admin_id)
    promoter = Members.objects.filter(community_id =  community,member_id = promoter_id)


def check_member(email,community_id,member_id,proposed_name):
    ProposedAdmin = User.objects.filter(id = member_id).first()
    print("proposed admin == ",ProposedAdmin)
    community = Community.objects.get(id = community_id)
    print("community == ",community.id)
    CommunityName=community.name
    email=email.lower().strip()
    proposedAdminState = Members.objects.filter(member_id=ProposedAdmin.id,community_id = community)
    print("proposed adminn state == ",proposedAdminState,"    ",proposedAdminState[0].state)
    proposedAdminState = proposedAdminState[0].state
    ProposedAdmin = Userinfo.objects.get(user_id  = ProposedAdmin.id)
    ProposedAdmin = ProposedAdmin.name
    try:
        user = Userinfo.objects.filter(email=email)

        if user:
            print("user is present")
            NominatedAdmin=user[0].name
        else:
            print("user is not present")
            send_email_to_nominated_admin(NominatedAdmin=proposed_name,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            return False
    except:
        print("except block email")
        send_email_to_nominated_admin(NominatedAdmin=proposed_name,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
        return False
    if user:
        member =Members.objects.filter(community_id = community,member_id = user[0].user_id.id)
        if member and member[0].state == 4:
            print("already a member")
            Members.objects.filter(community_id = community,member_id = user[0].user_id.id).update(state=6)
            send_email_to_nominated_admin(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
        elif member and member[0].state == 6:
            print("member is already a nominated promoter")
        else:
            print("member is created")
            member =Members()
            member.community_id = community
            member.member_id = user[0].user_id
            member.state = 6
            member.save()
            send_email_to_nominated_admin(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)

        return True
    return False


def send_email_to_nominated_admin(NominatedAdmin,email,ProposedAdmin,CommunityName,community_id,proposedAdminState):
    fail_silently=True
    to = email
    url = settings.URL
    url = url + "/community/" + str(community_id) + "/?source=email&cta=accept_admin"
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