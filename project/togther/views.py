from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from togther.models import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from togther.forms import * 
import facebook
import urllib
import requests
from django.contrib.auth.models import User
import json,requests
from django.http.response import JsonResponse



def home(request):
    users = User.objects.all()
    if request.user.is_authenticated: 
        return redirect('dashboard')
    else :
        usr = request.user.username
        print ("here")
        print(request.user.id)
        return render(request, 'home.html', {'users': users})
        


def dashboard(request):
    usr = Userinfo.objects.all().filter(user_id = request.user)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    
        if not usr :
            social_user = request.user.social_auth.filter(user_id = request.user.id).first()
            print(social_user.extra_data['id'])
            if social_user:
                if social_user.provider == 'facebook':
                    url = "https://graph.facebook.com/v2.9/"+social_user.extra_data['id']+"?fields=name,email,location,gender,picture,link&access_token="+social_user.extra_data['access_token']
                    response = requests.get(url)
                    data = json.loads(response.text)
                    print(data)
                    info = Userinfo()
                    info.name = data['name']
                    info.email = data['email'] 
                    gender = 0
                    if data['gender'] == 'male':
                        gender = 1
                    if data['gender'] == 'female':
                        gender = 0
                    info.gender = gender
                    info.city = data['location']['name']
                    info.image_url = data['picture']['data']['url']
                    info.fb_link = data["link"]
                    info.user_id = request.user
                    info.save()

            if social_user.provider == 'linkedin-oauth2':
                url = 'https://api.linkedin.com/v1/people/~:(id,email-address,first-name,last-name,location:(name),picture-url,public-profile-url)?format=json&oauth2_access_token=AQWY8Jq6ozfuocRIPm-KM6fS56UuscZ66StJOkJojMbcfCAqVl0N_d9l72RRS8rhhR2Lqt6dP4H2i8cr8MEOEsYwupNpGowJ0IhLtxg2zCckYo0tZWsvjUqIhBKbU-kz2VK-K4Tk4P96eOIz5pcvWOFzHX4_AeTo_7r5U6vl87F4pidcTPkNPUT4DsZiqubCe7zoOruTcSXVYOM0_VQhDukITgeXa_XfJ6xUkAvPG2FI_SuXD6wXDIJeX4ptDQGSXIc4hJmtaIGYhlPn0ZdHVcgK2x69W9sWh05a395QI8dweE6EVWR2WjYrssJ_uLs3NzejvzxvrPF2e3GWc6wtCYMlDASqAg'
                response = requests.get(url)
                data = json.loads(response.text)
                print(data)
                info = Userinfo()
                info.name = data['firstName']+" "+data['lastName']
                info.email = data['emailAddress'] 
                info.city = data['location']['name']
                info.image_url = data['pictureUrl']
                info.linkedin_link = data['publicProfileUrl']
                info.user_id = request.user
                info.save()

    else:
        user = []
    communities = Community.objects.all()

    if request.method == 'GET':
        response = request.GET.dict()
        print (response)
        if 'data' in response:
            category = response['data']
            categories = Category.objects.all().filter(category = category)
            print (categories)
            communities = []
            for i in categories:
                communities.append({'community':i.community_id})
            print('comm :',communities)
            # return  HttpResponse(json.dumps({'communities':communities}), content_type='application/json')
        else:    
            return render (request, 'dashboard.html', { 'usr': user,'communities' : communities})


def community(request, community_id):
    community = get_object_or_404(Community, pk = community_id)
    admins = Admins.objects.all().filter( community_id_id = community.id)
    admin_details=[]
    print("admin",admins)
    for admin in admins:
        print(admin.id)
        user_details = Userinfo.objects.all().filter( user_id = admin.admin_id )
        admin_details.append(user_details)
    member = Members.objects.all().filter(community_id = community.id)
    is_joined = 0
    print('admin: ',admin_details)
    members = [] 
    for m in member:
        if m.member_id == request.user.id:
            is_joined = 1
        print (m.member_id.id)
        mem = Userinfo.objects.all().filter(user_id = m.member_id.id)
        print(mem)
        if mem:
            members.append(mem[0])
    print (members)
    communities = Community.objects.all()
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else:
        user = []
    return render (request, 'community.html', {'usr':user,'similar_communities':communities , 'community' : community,'admins': admin_details, 'joined':is_joined, 'members':members})   

@login_required
def creategroup(request):
    if request.method == 'POST':
        form = NewGroupForm(request.POST,request.FILES)
        if form.is_valid():
            group = form.save()
            group.members_count = group.members_count + 1
            group.save()
            return redirect('form_data',1)
    return render(request, 'creategroup.html')

@login_required
def profile(request, user_id):
    info = Userinfo.objects.all().filter(user_id = user_id)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    communities = Members.objects.all().filter(member_id = user_id)
    my_communities = []
    for i in communities:
        my_communities.append(i.community_id)
    experiences = Experience.objects.all().filter(user_id = info[0].id)
    educations = Education.objects.all().filter(user_id = info[0].id)
    return render(request, 'profile.html', {'usr':user,"info": info,"my_communities":my_communities,"experience":experiences, "education": educations})


@login_required
def recieved_requests(request):
    admins_communities = Admins.objects.all().filter(admin_id = 1)
    req = []
    # data = Form_response.objects.all().filter(user_id = request.user.id)
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
        
@login_required
def edit_profile(request, user_id):
    if request.method == 'POST':
        form = NewProfileForm(request.POST, request.FILES)
        usr = Userinfo.objects.all().filter( user_id_id = request.user.id)
        if usr:
            usr.delete()
        if form.is_valid():
            print (user_id)
            userinfo = form.save(commit = False)
            userinfo.user_id = request.user
            userinfo.profile_completed = 1
            userinfo.save()
            return redirect('profile', user_id = request.user.id)
    else:
        usr = Userinfo.objects.all().filter(user_id_id = user_id)
        
        if not usr:
            form = NewProfileForm()
        else:
            usr = usr[0]
            form = NewProfileForm(initial = {'name':usr.name, 'city':usr.city, 'image_url': usr.image_url ,'college':usr.college, 'contact_number':usr.contact_number, 'experience':usr.experience, 'gender':usr.gender, 'interests':usr.interests, 'fb_link':usr.fb_link,'linkedin_link':usr.linkedin_link})
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    return render(request, 'editprofile.html', { 'usr':user,'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def join_community(request, community_id):
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    data = Form_data.objects.all().filter(community_id = community_id)
    if request.method == "POST":
        return render(request,'thankyou.html',{'usr':user})
    else: 
        return render(request,'response_form.html',{"data":data, 'usr':user})
    
    return redirect('dashboard')

@login_required
def form_data(request, community_id):
    print (community_id)
    if request.method == "POST":
        print (request.POST.dict())
        res = request.POST.dict()
        community = Community.objects.all().filter(id = community_id)
        community[0].whatsapp_group_link = res['whatsapp_link']
        if 'college' in res:
            mForm_data = Form_data()
            mForm_data.data = res['college']
            mForm_data.community_id = community[0]
            mForm_data.save()
        if 'contact' in res:
            mForm_data = Form_data()
            mForm_data.data = res['contact']
            mForm_data.community_id = community[0]
            mForm_data.data_type = text
            mForm_data.save()
        if 'experience' in res:
            mForm_data = Form_data()
            mForm_data.data = res['experience']
            mForm_data.community_id = community[0]
            mForm_data.save()
        if 'interests' in res:
            mForm_data = Form_data()
            mForm_data.data = res['interests']
            mForm_data.community_id = community[0]
            mForm_data.save()
        if 'question_1' in res:
            mForm_data = Form_data()
            mForm_data.data = res['question_1']
            mForm_data.community_id = community[0]
            mForm_data.save()
        if 'question_2' in res:
            mForm_data = Form_data()
            mForm_data.data = res['question_2']
            mForm_data.community_id = community[0]
            mForm_data.save()
    else:
        return render(request,'form_data.html')
    return redirect('community', community_id)

def thankyou(request):
    return render('thankyou.html')

def my_communities(request, user_id):
    communities = Members.objects.all().filter(member_id = user_id)
    my_communities = []
    for i in communities:
        my_communities.append(i.community_id)
    
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    return render(request,'my_community.html',{'usr':user,'my_communities':my_communities})

def communities_as_admin(request, user_id):
    communities = Admins.objects.all()
    admins_communities = []
    for i in communities:
        admins_communities.append(i.community_id)
    
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    return render(request,'communities_as_admin.html',{'usr':user,'admins_communities':admins_communities})

def members_list(request, community_id):
    member_list = Members.objects.all().filter(community_id = community_id)
    members = []
    for i in member_list:
        user = Userinfo.objects.all().filter(user_id = i.member_id)
        if user:
            members.append(user[0])

    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    community = Community.objects.all().filter(id = community_id)
    return render(request,'members.html' ,{'usr':user,'members':members, 'community':community})