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
from django.http import HttpResponseRedirect
from django.urls import reverse
from .tasks import *
from django.db.models import Q
from django.conf import settings

url  = settings.URL

def home(request):
    users = User.objects.all()
    if request.user.is_authenticated: 
        return redirect('dashboard')
    else :
        return render(request, 'home.html', {'users': users})
        

def dashboard(request):
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
        print("user == ", user)
        social_user = request.user.social_auth.filter(user_id = request.user.id).first()
        created =False
        if not user :
            social_user = request.user.social_auth.filter(user_id = request.user.id).first()
            if social_user:
                if social_user.provider == 'facebook':
                    url = "https://graph.facebook.com/v2.9/"+social_user.extra_data['id']+"?fields=name,email,gender,location,picture,link&access_token="+social_user.extra_data['access_token']
                    response = rqst.get(url)
                    image_url = "http://graph.facebook.com/"+social_user.extra_data['id']+"/picture?width=400&height=400"
                    data = json.loads(response.text)
                    print(data)
                    core_user = User.objects.all().filter(email = data['email']).first()
                    print("django user == ",core_user)
                    if core_user:
                        user = Userinfo.objects.all().filter(user_id = core_user)
                        print("userinfo== ",user)
                        if not user:
                            user = Userinfo()
                            if 'name' in data:
                                user.name = data['name']
                            if 'email' in data:
                                user.email = data['email'] 
                            if 'location' in data:
                                user.city = data['location']['name']
                            user.image_url = image_url
                            user.user_id = core_user
                            user.save()
                            print("created userinfo")
                            created =True
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
        print("user ================================  ",user)
        if created:
            print("created")
            user_id = user.id
            print(user.id)
            usr =user
        else:
            print("user info already exists")
            print(user)
            user_id = user[0].id
            usr=user[0]
        communities1 = Members.objects.all().filter(member_id = user_id)
        my_communities = []
        for j in communities1:
                my_communities.append(j.community_id)
        my_community =[]
        for j in my_communities:
            my_community.append(j)
        communities = Community.objects.all().order_by('-active_since')
        print("usr at last  ======== ",usr)
        return render (request, 'dashboard.html', { 'usr': usr, 'communities' : communities, 'my_communities':my_community[:2], "my_communities_count": len(my_community) })
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
                        'image_url':url+i.image_url.url,
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
                        'image_url':url+i.image_url.url,
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
    #-----accept admin APi part---------------
    res= request.GET.dict()
    if 'source' in res:
        source =res['source']
        print(source)
    else:
        source = ''
    if 'cta' in res:
        cta = res['cta']
    else:
        cta =''
    community = get_object_or_404(Community, pk = community_id)
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id = request.user)
        if not user:
            created,email = update_user_info(request)
            if not created:
                core_user = User.objects.all().filter(email = email).first()
                user = Userinfo.objects.all().filter(user_id = core_user)
            else:
                user = Userinfo.objects.all().filter(user_id = request.user)
            print("user info created")
        print("cur sess mail",user[0].email)
        core_user = User.objects.all().filter(email = user[0].email).first()
        print("core user == ",core_user.email)
        Nominated_mem = Members.objects.filter(member_id=core_user.id,community_id=community)
        try:
            print("try block Nominated_mem")
            if Nominated_mem:
                Nom_mem_state=Nominated_mem[0].state
            else:
                try:
                    print("get details from temp admin")
                    check=get_nominated_admin_details(request,member_id=core_user.id,community_id=community.id,email=core_user.email)
                    print("get nominated admin details",check)
                    if check:
                        print("creating member")
                        member=Members()
                        member.member_id=core_user
                        member.community_id = community
                        member.state = 6
                        member.save()
                        Nom_mem_state = 6
                    else:
                        Nom_mem_state = 0
                except:
                    Nom_mem_state = 0
        except:
            print("except block Nominated_mem")
            Nom_mem_state = 0
    elif not request.user.is_authenticated and source == 'email':
        print("not authenticated block Nominated_mem and source is email")
        Nom_mem_state= 0
    elif not request.user.is_authenticated:
        print("not authenticated block Nominated_mem")
        Nom_mem_state= 0
    elif source=='email':
        print("source block Nominated_mem")
        Nom_mem_state= 0
    else:
        Nom_mem_state= 0
    #------------------------------------------
    all_members=Members.objects.filter(community_id=community.id)
    print("nom mem state == ",Nom_mem_state)
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
        elif request.user.is_authenticated:
            if core_user.id == member.member_id.id and member.state == 3:
                is_joined=0
            else:
                is_joined=-1
        else:
            is_joined=-1
    user=[]
    communities=Community.objects.all()
    if request.user.is_authenticated:
        user = Userinfo.objects.all().filter(user_id=core_user.id)
    else:
        user = []
    print("last")
    return render (request, 'community.html', {'usr':user,'similar_communities':communities , 'community' : community,'admins': admin_details, 'is_joined':is_joined, 'members':members,'source':source,'cta':cta,'Nom_mem_state':Nom_mem_state,'admin_length':len(admin_details)})

def update_user_info(request):
    user = Userinfo.objects.all().filter(user_id = request.user)
    social_user = request.user.social_auth.filter(user_id = request.user.id).first()
    created =False
    if not user :
        social_user = request.user.social_auth.filter(user_id = request.user.id).first()
        if social_user:
            if social_user.provider == 'facebook':
                url = "https://graph.facebook.com/v2.9/"+social_user.extra_data['id']+"?fields=name,email,gender,location,picture,link&access_token="+social_user.extra_data['access_token']
                response = rqst.get(url)
                data = json.loads(response.text)
                image_url = "http://graph.facebook.com/"+social_user.extra_data['id']+"/picture?width=400&height=400"
                print(data)
                core_user = User.objects.all().filter(email = data['email']).first()
                print("django user == ",core_user)
                if core_user:
                    user = Userinfo.objects.all().filter(user_id = core_user)
                    print("userinfo== ",user)
                    if not user:
                        user = Userinfo()
                        if 'name' in data:
                            user.name = data['name']
                        if 'email' in data:
                            user.email = data['email'] 
                        if 'location' in data:
                            user.city = data['location']['name']
                        user.image_url = image_url
                        user.user_id = core_user
                        user.save()
                        print("created userinfo")
                        created =True
            return created,data['email']

def get_nominated_admin_details(request,member_id,community_id,email):
    print("fetching non admin details from DB")
    user = Userinfo.objects.all().filter(user_id = request.user)
    print("cur sess mail",user[0].email)
    core_user = User.objects.all().filter(email = user[0].email).first()
    print("core user email == ",core_user.email)
    print("core user id == ",core_user.id)
    community = get_object_or_404(Community, pk = community_id)
    print("community == ",community)
    details = temp_admin.objects.filter(community_id=community,email=core_user.email)
    print("details == ",details)
    if details:
        print("details are present")
        return True
    else:
        print("details are not present")
        return False


def accept_admin(request,community_id,cta=''):
    community = Community.objects.get(id=community_id)
    member = Members.objects.filter(community_id = community).filter(Q(state=1)|Q(state=2))
    core_user = User.objects.all().filter(email = request.user.email).first()
    print("core user == ",core_user.email)
    prop_admin = Userinfo.objects.get(user_id = member[0].member_id.id)
    print("prop_admin name == ",prop_admin.name)
    print("prop admin email == ",prop_admin.email)
    nom_admin = Userinfo.objects.all().filter(user_id = core_user.id)
    print("nom_admin == ",nom_admin[0].name)
    print("nom_admin  == ",nom_admin[0].email)
    cur_sess_user_id = core_user.id

    print("\n\nNomnatedAdmin  == ", nom_admin[0].name)
    print(" to email == ",prop_admin.email)
    print("proposed admin name == ",prop_admin.name)

    if len(member) == 1:
        if member[0].state == 1:
            print(nom_admin[0].name)
            print("email to proposed admin for single admin")
            send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState =1,CommunityName=community.name,community_id = community.id)
            Members.objects.filter(community_id = community,member_id=core_user.id).update(state =1)
        if member[0].state == 2:
            print("email to temp admin")
            temp_admin = Members.objects.filter(community_id = community,state=2)
            Members.objects.filter(community_id = community,member_id=temp_admin[0].member_id).update(state =4)
            Members.objects.filter(community_id = community,member_id=core_user.id).update(state =1)
            send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState=2,CommunityName=community.name,community_id = community.id)
    else:
        send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState=1,CommunityName=community.name,community_id = community.id)
        Members.objects.filter(community_id = community,member_id=core_user.id).update(state =1)
    return HttpResponseRedirect("https://play.google.com/apps/testing/com.collabmates")

def check_admins(community_id):
    community = Community.objects.get(id=community_id)
    member = Members.objects.filter(community_id = community).filter(Q(state=1)|Q(state=2))
    print("member state == ",member[0].state)
    if len(member) == 1:
        if member[0].state == 2:
            cta = 'accept_invitation_temp_admin'
        elif member[0].state == 1:
            cta = 'accept_invitation_admin'
    else:
        cta = 'accept_invitation_admin'
    return cta

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
