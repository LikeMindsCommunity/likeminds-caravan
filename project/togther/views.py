from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from togther.models import *
from django.contrib.auth.decorators import login_required
from togther.forms import * 


# Create your views here.
def home(request):
    users = User.objects.all()
    return render(request, 'home.html', {'users': users})

@login_required
def dashboard(request):
    communities = Community.objects.all()
    users_communities = Members.objects.all().filter(member_id = 1)
    user_communities = []
    for community in users_communities: 
        user_communities.append(Community.objects.all().filter(id = community.id))
    my_communities = Admins.objects.all().filter(admin_id = 1)
    my_community = []
    for community in my_communities:
        my_community.append(Community.objects.all().filter(id = community.id))
    return render (request, 'dashboard.html', {'communities' : communities, 'user_communities': user_communities, 'my_community': my_community})

@login_required
def community(request, community_id):
    community = get_object_or_404(Community, pk = community_id)
    admins = Admins.objects.all().filter( community_id_id = community.id)
    admin_details=[]
    for admin in admins:
        user_details = User.objects.all().filter( id = admin.id )
        admin_details.append(user_details)
    return render (request, 'community.html', {'community' : community,'admins': admin_details})   

@login_required
def creategroup(request):
    if request.method == 'POST':
        form = NewGroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            group.members_count = group.members_count + 1
            category = Category()
            f = form.data.dict()
            print (f)
            print (type(f))
            category.category = f["category"]
            category.community_id_id = group.id
            category.save()
            group.save()
            return redirect('dashboard')
    else:
        form = NewGroupForm()
    return render(request, 'creategroup.html', { 'form': form})

@login_required
def profile(request, user_id):
    info = Userinfo.objects.all().filter(user_id_id = user_id)
    return render(request, 'profile.html', {"info": info})


@login_required
def recieved_requests(request):
    admins_communities = Admins.objects.all().filter(admin_id = 1)
    req = []
    for c in admins_communities :
        r = Requests.objects.all().filter( community_id_id = c.admin_id_id)
        req.append(r)
    return render (request,'requests.html', {'req': req})    

def join_request(request):
    if request.method == "GET":
        user = request.GET.get("user")
        community = request.GET.get("community")
        print (user, community)
        req = Requests()
        req.status = 0
        user_obj = User.objects.filter(id = user)
        community_obj = Community.objects.filter(id=community)
        req.user_id = user_obj[0]
        req.community_id = community_obj[0]
        req.save()

def request_response(request):
    if request.method == "GET":
        id = request.GET.get("id")
        req = Requests.objects.get(id = id)
        val = request.GET.get("value")
        print (type(val))
        if val == '1':
            print ('heloo')
            req.status = 1
            print (req.community_id_id)
            comm = Community.objects.get(id = req.community_id_id)
            print (comm.members_count)
            comm.members_count = comm.members_count + 1
            member = Members()
            member.community_id_id = comm.id
            user = User.objects.get(id = req.user_id_id)
            member.member_id_id = user.id
            print (comm)
            comm.save()
            req.save()
            member.save()
        else:
            print ('adfa')
    return HttpResponse('hi')
        