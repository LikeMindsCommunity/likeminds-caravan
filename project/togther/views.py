from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from togther.models import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from togther.forms import * 
import urllib
import requests as rqst
from django.contrib.auth.models import User
import json
from django.http.response import JsonResponse
from django.db.models import Q
from django.core.mail import send_mail

def home(request):
    users = User.objects.all()
    if request.user.is_authenticated: 
        return redirect('dashboard')
    else :
        return render(request, 'home.html', {'users': users})
        

def dashboard(request):  
    if request.user.is_authenticated:
        usr = Userinfo.objects.all().filter(user_id = request.user)
        user = Userinfo.objects.all().filter(user_id = request.user)
        social_user = request.user.social_auth.filter(user_id = request.user.id).first()
        token = social_user.extra_data['access_token']
        print('token',token)
        if not usr :
            social_user = request.user.social_auth.filter(user_id = request.user.id).first()
            print(social_user.extra_data['id'])
            if social_user:
                if social_user.provider == 'facebook':
                    url = "https://graph.facebook.com/v2.9/"+social_user.extra_data['id']+"?fields=name,email,gender,location,picture,link&access_token="+social_user.extra_data['access_token']
                    print(url)
                    response = rqst.get(url)
                    data = json.loads(response.text)
                    usr1 = Userinfo.objects.all().filter(email = data['email'])
                    if not usr1:
                        info = Userinfo()
                        if 'name' in data:
                            info.name = data['name']
                        if 'email' in data:
                            info.email = data['email'] 
                        if 'location' in data:
                            info.city = data['location']['name']
                        info.image_url = data['picture']['data']['url']
                        info.user_id = request.user
                        info.save()
                    else:
                        if 'link' in data:
                            usr1.fb_link = data['link']

            if social_user.provider == 'linkedin-oauth2':
                url = 'https://api.linkedin.com/v1/people/~:(id,email-address,first-name,last-name,headline,interests,location:(name),picture-url,public-profile-url,positions:(id,title,start-date,end-date,company,summary),educations:(id,school-name,field-of-study,start-date,end-date,degree))?format=json&oauth2_access_token='+social_user.extra_data['access_token']
                print(url)
                response = rqst.get(url)
                data = json.loads(response.text)
                print(data)
                info = Userinfo()
                usr1 = Userinfo.objects.all().filter(email = data['email'])
                if not usr1:
                    info.name = data['firstName']+" "+data['lastName']
                    info.email = data['emailAddress'] 
                    info.city = data['location']['name']
                    info.image_url = data['pictureUrl']
                    info.linkedin_link = data['publicProfileUrl']
                    info.user_id = request.user
                    info.save()
                else:
                    usr1.linkedin_link = data['publicProfileUrl']
    else:
        user = []
    communities = Community.objects.all().order_by('-active_since')
    if request.method == 'GET':
        response = request.GET.dict()
        print (response)
        if 'data' in response:
            if response['data'] != '':
                category = response['data']
                print(category)
                categories = Category.objects.all()
                communities = []
                for i in categories:
                    print(i, i.community_id)
                    if i.category == category:
                        c = Community.objects.get(id = i.community_id.id)
                        communities.append(c)
                community = []
                for i in communities:
                    comm = {'id':i.id,
                        'name':i.name,
                        'about':i.about,
                        'image_url':'https://beta.collabmates.com/'+i.image_url.url,
                        'location':i.location,
                        'members_count':i.members_count,
                        'purpose': i.purpose,
                        }
                    community.append(comm)
                print('comm :',community)
                return JsonResponse({'communities': community})
            else:
                communities = []
                community = Community.objects.all()
                for i in community:
                    comm = {'id':i.id,
                        'name':i.name,
                        'about':i.about,
                        'image_url':'https://beta.collabmates.com/'+i.image_url.url,
                        'location':i.location,
                        'members_count':i.members_count,
                        }
                    communities.append(comm)
                return JsonResponse({'communities': communities})
        user_id = request.user.id
        communities1 = Members.objects.all().filter(member_id = user_id)
        my_communities = []
        for j in communities1:
            my_communities.append(j.community_id)
        my_community =[]
        for j in my_communities:
            my_community.append(j)
    return render (request, 'dashboard.html', { 'usr': user,'communities' : communities, 'my_communities':my_community[:2], "my_communities_count": len(my_community) })


def community(request, community_id):
    community = get_object_or_404(Community, pk = community_id)
    all_members=Members.objects.filter(community_id=community.id)

    members=[]
    admin_details=[]
    is_joined=-1
    for member in all_members:
        mem = Userinfo.objects.all().filter(user_id=member.member_id.id)
        if member.state == 1 or member.state == 2 :
            admin_details.append(mem)
            members.append(mem[0])

        elif member.state == 4 :
            members.append(mem[0])


        elif request.user.id == member.member_id.id and member.state == 3:
            is_joined=0

    user=[]
    communities=Community.objects.all()
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=request.user)
    else:
        user = []

    return render (request, 'community.html', {'usr':user,'similar_communities':communities , 'community' : community,'admins': admin_details, 'is_joined':is_joined, 'members':members})
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
            category = Category()
            category.category = i
            category.community_id_id = group.id
            category.save()

        admin = Admins()
        admin.admin_id = request.user
        community = Community.objects.get(id = group.id)
        admin.community_id = community
        admin.save()
        member = Members()
        member.member_id = request.user
        member.community_id = community
        member.save()
        return redirect('form_data', community_id = group.id)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else:
        user = []
    return render(request, 'creategroup.html', { 'usr':user})

@login_required
def profile(request, user_id):
    info = Userinfo.objects.get(user_id = request.user)
    if request.method == 'GET':
        res = request.GET.dict()
        print(res)
        if 'name' in res:
            if(res['name'] == 'headline'):
                info.headline = res['headline']
                info.save()
            if(res['name'] == 'summary'):
                info.about = res['summary']
                info.save()
            if(res['name'] == 'experience'):
                info.headline = res['headline']
                info.fb_link = res['fb_link']
                info.linkedin_link = res['linkedin']
                info.save()
            if(res['name'] == 'education'):
                info.headline = res['headline']
                info.fb_link = res['fb_link']
                info.linkedin_link = res['linkedin']
                info.save()
            if(res['name'] == 'interests'):
                info.interests = res['interests']
                info.save()
            if(res['name'] == 'add_education'):
                edu = Education()
                edu.user_id = info
                edu.degree = res['degree']
                edu.instituion = res['institution']
                edu.from_year = res['from']
                edu.to_year = res['to']
                edu.description = res['description']
                edu.save()
            if(res['name'] == 'add_experience'):
                exp = Experience()
                exp.user_id = info
                exp.company = res['company']
                exp.title = res['title']
                exp.from_year = res['from']
                exp.to_year = res['to']
                exp.description = res['description']
                exp.save()
            return JsonResponse({'status':'ok'})
    info = Userinfo.objects.all().filter(user_id = user_id)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    communities = Members.objects.all().filter(member_id = user_id)
    my_communities = []
    for i in communities:
        my_communities.append(i.community_id)
    experiences = Experience.objects.all().filter(user_id = info[0])
    educations = Education.objects.all().filter(user_id = info[0])
    print(':',my_communities)
   
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
@login_required
def requests(request):

    if request.method == 'GET':
        res = request.GET.dict()
        print(res)
        if 'status' in res:
            req = Requests.objects.get(id = int(res['id']))
            comm = Community.objects.get(id = req.community.id)
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
                send_mail('Collabmates: Group Joining', 'Your request has been approved by the admin.', 'hello@collabmates.com', [email], fail_silently=False)
            else:
                req.status = -1
                req.save()
                email = req.user_info.email
                print(email)
                send_mail('Collabmates: Group Joining', 'Your request has been Rejected by the admin.', 'hello@collabmates.com', [email], fail_silently=False)
            return JsonResponse({'status':'OK'})
    admins_communities = Admins.objects.all().filter(admin_id = request.user)
    print(admins_communities)
    rqsts = []
    requests = Requests.objects.all()
    for i in requests:
        if i.status != -1 :
            for j in admins_communities:
                print((j.community_id.id))
                if i.community.id == j.community_id.id  :
                    rqsts.append(i)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    print(rqsts)
    return render(request,'requests.html',{'usr':user,'admins_communities':admins_communities, 'req':rqsts})
    

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
    return redirect('dashboard')

@login_required
def join_community(request, community_id):
    print( community_id)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []

    if request.method == "POST":
        res = request.POST.dict()

        for i in res:
            response = Form_response()
            if i != 'csrfmiddlewaretoken' :
                print(i)
                response.data = i
                response.response = res[i]
                response.user = request.user.id
                response.community = community_id
                response.save()
        
        req = Requests()
        req.user_id = request.user
        req.user_info = user[0]
        comm = Community.objects.all().filter(id = community_id)
        req.community = comm[0]
        req.save()



        admin = Admins.objects.all().filter(community_id = community_id)
        u_info = Userinfo.objects.get(user_id = admin[0].admin_id)
        communities = Community.objects.all()

        return render(request, 'thankyou.html', {'usr':user, 'similar_communities':communities})
        
    else:
        data = Form_data.objects.all().filter(community_id = community_id)
        print('data:',data)
        if not data:
            communities = Community.objects.all()
            return render(request, 'thankyou.html', {'usr':user, 'similar_communities':communities}) 
        else:
            community = Community.objects.get(id = community_id)
            return render(request,'response_form.html',{"data":data, 'usr':user, 'community':community})
    

@login_required
def form_data(request, community_id):
    print (community_id)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    if request.method == "POST":
        print (request.POST.dict())
        res = request.POST.dict()
        community = Community.objects.all().filter(id = community_id)
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
        i = q+str(count)
        print(i)
        while(1):
            if i in res and res[i]!= '' :
                print(i)
                mForm_data = Form_data()
                mForm_data.data = res[i]
                mForm_data.community_id = community[0]
                mForm_data.data_type = res['response'+str(count)]
                mForm_data.save()
            else:
                break
            count=count+1
            i = q+str(count)
    else:
        return render(request,'form_data.html', {'usr':user})
    
    return redirect('community', community_id)


def thankyou(request):
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    communities = Community.objects.all()
    return render(request, 'thankyou.html', {'usr':user, 'similar_communities':communities})

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
    communities = Admins.objects.all().filter(admin_id = user_id)
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


def user_response(request, community_id, user_id):
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    responses = Form_response.objects.all().filter(user = user_id, community = community_id)
    return render(request,'user_response.html' ,{'usr':user, 'responses':responses})

def privacy(request):
    return render(request,'privacy.html')

def terms(request):
    return render(request,'terms.html')

def collabcard(request, card_id):
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
    else :
        user = []
    card = Collabcard.objects.get(id = card_id)
    creator = Userinfo.objects.get(user_id = card.user)
    community = card.community
    print(user)
    return render(request,'card.html' ,{'usr':user, 'card':card, 'creator': creator, 'community': community})

@login_required 
def view_answers(request, card_id):
    cards = Collabcard.objects.get(id = card_id)
    answer = card_answers.objects.filter(card = cards)
    userinfo = Userinfo.objects.get(user_id = cards.user)
    answers = []
    for i in answer:
        creator = Userinfo.objects.get(user_id = i.user.id)
        answers.append({'answer':answer ,'creator':creator})
    return render(request, 'answers.html',{'answers': answers, 'user':userinfo})
