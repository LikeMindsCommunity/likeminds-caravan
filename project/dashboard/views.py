from django.shortcuts import render,redirect
from django.http import HttpResponse
from togther.models import *
from django.views.generic import *
from .forms import *
# Create your views here.

def dashboard(request):
  '''function to give list of community to edit'''

  community_list=Community.objects.all().order_by('-created_at','-active_since')


  return render(request,'dashboard/dashboard.html',{'communities':community_list})


def update_form(request,community_id):

    if request.method == 'POST':


        community=Community.objects.get(id=community_id)
        community_form=CommunityForm(request.POST,request.FILES,instance=community)
        community_form.save()
        return redirect('dashboard')
    else:
        community=Community.objects.get(id=community_id)
        community_form=CommunityForm(instance=community)


    context={'community_form':community_form,'community':community}
    return render(request,'dashboard/community.html',context)




def community_delete(request,community_id):
    '''function to delete the community'''
    Community.objects.filter(id=community_id).delete()
    return redirect('dashboard')




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
        return redirect('dashboard')
    else:
        community=Community.objects.get(id=community_id)
        admin_form = AdminForm(request.POST)
    context = {'admin_form': admin_form, 'community': community}
    return render(request, 'dashboard/add_admin.html', context)