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
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

def dashboard(request):
  '''function to give list of community to edit'''

  community_list=Community.objects.all().order_by('-created_at','-active_since')


  return render(request,'dashboard/dashboard.html',{'communities':community_list})


def update_form(request,community_id):
    '''function to update form for community'''
    if request.method == 'POST':


        community=Community.objects.get(id=community_id)
        community_form=CommunityForm(request.POST,request.FILES,instance=community)
        community_form.save()
        purpose=community_form.cleaned_data['purpose']
        community_form.save()
        admins=Members.objects.filter(community_id=community).filter(Q(state=1)|Q(state=2))
        for_string=purpose.split(' ', 1)[0]
        member_id=0
        if admins:
            for admin in admins:
                member_id=admin.member_id
                break;
        exist=Collabcard.objects.filter(community_id=community,title=purpose)
        if not exist:
            collabcard=Collabcard()
            purpose="Created this community " + for_string.lower() + purpose.split("For",1)[1]
            collabcard.title=purpose
            collabcard.user=member_id
            collabcard.community_id=community_id
            collabcard.date_epoch=time.time()
            collabcard.save()
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
    return redirect(url)

def decline_member(request,community_id,member_id):
    '''function to approve member'''
    community = Community.objects.get(id=community_id)

    Members.objects.filter(community_id=community,member_id=member_id).update(state=5)
    url='/admin_dashboard/show_pending_member/'+str(community_id)
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
        user_info_form=UserForm(request.POST,instance=user_info)
        user_info_form.save()
        return redirect('all_user')
    else:
        context={}
        try:
            user_info = Userinfo.objects.get(email=email)
            user_info_form = UserForm(instance=user_info)
            context = {'user_info_form': user_info_form}
        except:
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

            send_email_to_nominated_admin(proposed_name,proposed_email,proposer_name,community.name,community_id)
            return redirect('admin_dashboard')
    else:
        send_nominated_email=SendNominatedEmail()
        context={'send_email':send_nominated_email}
        return render(request,'dashboard/send_invitation.html',context)




def send_email_to_nominated_admin(NominatedAdmin,email,ProposedAdmin,CommunityName,community_id):
	fail_silently=True
	to = email
	subject =str(ProposedAdmin)+ " has proposed you as promoter of "+str(CommunityName)+" community"
	template = get_template("mails/accept_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id})
	msg = EmailMultiAlternatives(subject,
	                                 template,
	                                 "hello@collabmates.com",
	                                 [to],
	                                 )
	msg.attach_alternative(template, "text/html")
	return msg.send(fail_silently)