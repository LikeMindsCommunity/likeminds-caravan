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
from django.conf import settings
from django.core.mail import send_mail
from collabmates_api.serializers import CommunitySerializer
from categories import Category_list
from django.views.decorators.csrf import csrf_exempt

# your views here.

def communities(request):
    if request.method == 'GET':
        body = request.GET
        if 'member_id' in body:
            user_id = body['member_id']
        response = request.GET.dict()
        if 'category_id' in response:
            print(response['category_id'])
            if response['category_id'] != '':
                category = response['category_id']
                category_objects = Category.objects.all()
                for i in Category_list:
                    if i['id'] == category:
                        cat = i['title'] 
                communities = []
                for i in category_objects:
                    if i.category == cat:
                        c = Community.objects.get(id = i.community_id.id)
                        communities.append(c)
                community = []
                for i in communities:
                    serializer_class = CommunitySerializer(i)
                    new_dict = {}
                    new_dict.update(serializer_class.data)
                    if new_dict['image_url']:
                        new_dict['image_url'] = 'https://beta.collabmates.com'+new_dict['image_url']
                    else:
                        new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
                    new_dict['share_url']= 'https://beta.collabmates.com/community/'+str(new_dict['id'])
                    new_dict['date'] = i.active_since
                    community.append(new_dict)
                return JsonResponse({'communities': community})
            else:
                queryset = Community.objects.all().order_by('-active_since')
                community = []
                for i in queryset:
                    serializer_class = CommunitySerializer(i)
                    new_dict = {}
                    new_dict.update(serializer_class.data)
                    if new_dict['image_url']:
                        new_dict['image_url'] = 'https://beta.collabmates.com'+new_dict['image_url']
                    else:
                        new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
                    member = Members.objects.all().filter(community_id = i.id)
                    is_member = False
                    for m in member:
                        if m.member_id == user_id:
                            is_member = True
                    new_dict['is_member'] = is_member
                    new_dict['share_url']= 'https://beta.collabmates.com/community/'+str(new_dict['id'])
                    new_dict['date'] = i.active_since
                    community.append(new_dict)
                return JsonResponse({'communities': community})
        else:
            queryset = Community.objects.all().order_by('-active_since')
            community = []
            for i in queryset:
                serializer_class = CommunitySerializer(i)
                new_dict = {}
                new_dict.update(serializer_class.data)
                if new_dict['image_url']:
                    new_dict['image_url'] = 'https://beta.collabmates.com'+new_dict['image_url']
                else:
                    new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
                member = Members.objects.all().filter(community_id = i.id)
                is_member = False
                for m in member:
                    if m.member_id == user_id:
                        is_member = True
                    new_dict['is_member'] = is_member
                new_dict['share_url']= 'https://beta.collabmates.com/community/'+str(new_dict['id'])
                new_dict['date'] = i.active_since
                community.append(new_dict)
            return JsonResponse({'communities': community})
        
    queryset = Community.objects.all().order_by('-active_since')
    community = []
    user = User.objects.get(id = user_id)
    for i in queryset:
        serializer_class = CommunitySerializer(i)
        member = Members.objects.all().filter(community_id = i.id)
        is_member = False
        for m in member:
            if m.member_id == user_id:
                is_member = True
        comm = serializer_class.data
        print(comm)    
        comm['member_id'] = user_id
        new_dict['share_url']= 'https://beta.collabmates.com/community/'+str(new_dict['id'])
        community.append(comm)
    return HttpResponse({'communities': community})

def your_communities(request,user_id):
    member_id = request.GET.get('member_id')
    user = User.objects.get(id = member_id)
    communities = Members.objects.all().filter(member_id = user_id)
    my_communities = []
    for i in communities:
        my_communities.append(i.community_id)
    my_community =[]
    for i in my_communities:
        members = Members.objects.all().filter(community_id = i.id)
        serializer_class = CommunitySerializer(i)
        comm = serializer_class.data
        for j in members:
            if j.member_id == user:
                comm['is_member'] = True
            else:
                comm['is_member'] = False
        new_dict = {}
        new_dict.update(serializer_class.data)
        if new_dict['image_url']:
            new_dict['image_url'] = 'https://beta.collabmates.com'+new_dict['image_url']
        else:
            new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
        new_dict['share_url']= 'https://beta.collabmates.com/community/'+str(new_dict['id'])
        community = Community.objects.get(id = new_dict['id'])
        requests = Requests.objects.filter(community = community).filter(status = 0)
        new_dict['pending_members_count'] = len(requests)
        card = Collabcard.objects.all().filter(community = community)
        if card:
            new_dict['collabcard_text'] = card[0].title
        new_dict['date'] = i.active_since
        my_community.append(new_dict)
    return JsonResponse({'your_communities':my_community})

def community(request, community_id):
    queryset = Community.objects.get(id = community_id)
    body = request.GET
    print(body)
    if 'member_id' in body:
        user_id = body['member_id']
    print(user_id)
    member = Members.objects.all().filter(community_id = community_id)
    is_member = False
    user = User.objects.get(id = user_id)
    for m in member:
        if m.member_id == user:
            is_member = True
    serializer_class = CommunitySerializer(queryset)
    community = serializer_class.data
    if community['image_url']:
        community['image_url'] = 'https://beta.collabmates.com'+community['image_url']
    else:
        community['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
    community['is_member']= is_member
    community['share_url']= 'https://beta.collabmates.com/community/'+str(community['id'])
    new_dict['date'] = i.active_since
    return JsonResponse({'community': community})

def similar_community(request, community_id):
    body = request.GET
    if 'member_id' in body:
        user_id = body['member_id']
    member = Members.objects.all().filter(community_id = community_id)
    is_member = False
    user = User.objects.get(id = user_id)
    for m in member:
        if m.member_id == user:
            is_member = True
    community = Community.objects.get(id = community_id)
    queryset = Community.objects.all().order_by('-active_since')[:10]
    similar_communities = []
    for i in queryset:
        if i.id != community_id:
            serializer_class = CommunitySerializer(i)
            community = serializer_class.data
        new_dict = {}
        new_dict.update(serializer_class.data)
        if new_dict['image_url']:
            new_dict['image_url'] = 'https://beta.collabmates.com'+new_dict['image_url']
        else:
            new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
        new_dict['share_url']= 'https://beta.collabmates.com/community/'+str(new_dict['id'])
        new_dict['is_member'] = is_member
        new_dict['date'] = i.active_since
        similar_communities.append(new_dict)
    return JsonResponse({'communities': similar_communities})

def join_community(request, community_id):
    data = Form_data.objects.all().filter(community_id = community_id)
    reqd_info = []
    for i in data:
        ques = {'question':i.data,
                'data_type':i.data_type,
                }
        reqd_info.append(ques)
    return JsonResponse({'questions': reqd_info})

@csrf_exempt
def join_community_responses(request):
    res = json.loads(request.body)
    user_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')
    print(user_id, community_id)
    user = User.objects.get(id = user_id)
    userinfo = Userinfo.objects.get(user_id = user)
    community = Community.objects.get(id = community_id)
    response = Form_response()
    req = Requests()
    req.user_id = user
    req.user_info = userinfo
    req.community = community
    req.save()
    if 'questions' in res:
        for i in res['questions']: 
            response.data = i['key']
            response.response = i['value']
            response.user = user.id
            response.community = community.id
            response.save()
    return JsonResponse({'success':True})


def category_filter(request, category):
    categories = Category.objects.all()
    communities = []
    for i in categories:
        if i.category == category:
            c = Community.objects.get(id = i.community_id.id)
            communities.append(c)
    community = []
    for i in communities:
        serializer_class = CommunitySerializer(i)
        community.append(serializer_class.data)
    return JsonResponse({'communities': community})

def categories(request):
    return JsonResponse ({'category_list': Category_list})

def user(request, user_id):
    info = Userinfo.objects.all().filter(user_id = user_id)
    user = {}
    print (info)
    for i in info:
        user['id'] = i.user_id.id
        user["name"] = i.name
        user["email"] = i.email
        user["city"] = i.city
        user["headline"] = i.headline
        user["contact_number"] = i.contact_number
        user["image_url"] = i.image_url
        user["about"] = i.about
        user["fb_link"] = i.fb_link
        user["linkedin_link"] = i.linkedin_link
    return JsonResponse ({'user': user})

def members(request, community_id):
    community = get_object_or_404(Community, pk = community_id)
    print(community)
    member = Members.objects.all().filter(community_id = community)
    print(member)
    members = []
    for i in member:
        user = Userinfo.objects.get(user_id = i.member_id)
        usr = {}
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number
        usr["image_url"] = user.image_url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        members.append(usr)
    print (members)
    return JsonResponse ({'members': members})

def admins(request, community_id):
    admins = Admins.objects.all().filter(community_id = community_id)
    users = []
    for i in admins:
        user = Userinfo.objects.filter(user_id = i.admin_id)
        print(user)
        usr = {}
        usr['id'] = user[0].user_id.id
        usr["name"] = user[0].name
        usr["email"] = user[0].email
        usr["city"] = user[0].city
        usr["headline"] = user[0].headline
        usr["contact_number"] = user[0].contact_number
        usr["image_url"] = user[0].image_url
        usr["about"] = user[0].about
        usr["fb_link"] = user[0].fb_link
        usr["linkedin_link"] = user[0].linkedin_link
        users.append(usr)
    return JsonResponse ({'members': users})

@csrf_exempt
def create_community(request):
    is_admin = request.GET.get('is_admin')
    print(is_admin)
    if is_admin == 'true':
        user_id = request.GET.get('member_id')
        print(user_id)
        if request.method == 'POST':
            res = json.loads(request.body)
            img = request.FILES.dict()
            print(res)
            group = Community()
            group.members_count = group.members_count + 1
            group.name = res['name']
            for i in res['items']:
                if i['key'] == 'Purpose of the community':
                    group.purpose = i['value']
                if i['key'] == 'Geography of the community':
                    group.location = i['value']
                if i['key'] == 'About the community':
                    group.about = i['value'] 
                if 'image' in img:
                    group.image_url = img['image']
                if i['key'] == 'whatsapp_link' :
                    group.whatsapp_group_link = i['whatsapp_link']
            group.save()
            for i in res['items']:
                if i['key'] == 'Type of community' :
                    categories = i['value']
                    categories = categories.split(",")
                    for j in categories:
                        category = Category()
                        category.category = j
                        category.community_id_id = group.id
                        category.save()
            admin = Admins()
            print(group)
            user = User.objects.get(id = user_id)
            admin.admin_id = user
            community = Community.objects.get(id = group.id)
            admin.community_id = community
            admin.save()
            member = Members()
            member.member_id = user
            member.community_id = community
            member.save()
            card = Collabcard()
            print(community)
            if community.purpose != '':
                card.title = "Created this community "+community.purpose
            else:
                card.title = "Listed our community on CollabMates. This will help us to know each other, have organised discussions and network efficiently."
            card.community = community
            card.user = user
            card.save()
            user = Userinfo.objects.get(user_id = user.id)
            usr = {}
            usr['id'] = user.user_id.id
            usr["name"] = user.name
            usr["email"] = user.email
            usr["city"] = user.city
            usr["headline"] = user.headline
            usr["contact_number"] = user.contact_number
            usr["image_url"] = user.image_url
            usr["about"] = user.about
            usr["fb_link"] = user.fb_link
            usr["linkedin_link"] = user.linkedin_link
            serializer_class = CommunitySerializer(community)
            new_dict = {}
            new_dict.update(serializer_class.data)
            if new_dict['image_url']:
                new_dict['image_url'] = 'https://beta.collabmates.com'+new_dict['image_url']
            else:
                new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
            new_dict['share_url']= 'https://beta.collabmates.com/community/'+str(new_dict['id'])
            #new_dict['date'] = community['active_since']
            crd = {'id':card.id , 'title':card.title, 'member':usr, 'answer_text': '' }
            return JsonResponse({'success':True, 'community':new_dict, 'collabcard':crd})
    else:
        member_id = request.GET.get('member_id')
        if request.method == 'POST':
            res = json.loads(request.body)
            print(res)
            group = Community()
            group.members_count = group.members_count + 1
            group.name = res['name']
            group.save()
            community = Community.objects.get(id = group.id)
            serializer_class = CommunitySerializer(community)
            new_dict = {}
            new_dict.update(serializer_class.data)
            if new_dict['image_url']:
                new_dict['image_url'] = 'https://beta.collabmates.com'+new_dict['image_url']
            else:
                new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
            new_dict['share_url']= 'https://beta.collabmates.com/community/'+str(new_dict['id'])
            
        return JsonResponse({'success':True, 'community':new_dict})
    return HttpResponse("Create Community Api")

@csrf_exempt
def create_card(request):
    user_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')
    print (user_id, community_id)
    useer = User.objects.get(id = user_id)
    user = Userinfo.objects.get(user_id = user_id)
    community = Community.objects.get(id = community_id)
    if request.method == 'POST':
        res = json.loads(request.body)
        card = Collabcard()
        card.title = res['title']
        card.community = community
        card.user = useer
        card.save()
        collabcard = {}
        collabcard['id'] = card.id
        collabcard['title'] = card.title
        collabcard['community'] = community.id
        collabcard['share_url'] = 'https://beta.collabamtes.com/collabcard/'+str(card.id)
        collabcard['answer_text'] = ''
        new_dict = {}
        new_dict = collabcard
        new_dict['date'] = ''
        usr = {}
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number
        usr["image_url"] = user.image_url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        collabcard['member'] = usr
        return JsonResponse({'success':True, 'collabcard':new_dict})
    return JsonResponse()

def collabcard(request, card_id):
    cards = Collabcard.objects.get(id = card_id)
    print(cards)
    answer = card_answers.objects.filter(card = cards)
    answers = []
    for i in answer:
        usr = {}
        user = Userinfo.objects.get(user_id = i.user.id)
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number
        usr["image_url"] = user.image_url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        answers.append({'id':i.id,'answer':i.answer, 'member': usr})
    user = Userinfo.objects.get(user_id = cards.user.id)
    usr = {}
    usr['id'] = user.user_id.id
    usr["name"] = user.name
    usr["email"] = user.email
    usr["city"] = user.city
    usr["headline"] = user.headline
    usr["contact_number"] = user.contact_number
    usr["image_url"] = user.image_url
    usr["about"] = user.about
    usr["fb_link"] = user.fb_link
    usr["linkedin_link"] = user.linkedin_link
    images = card_images.objects.filter(collabcard = card_id)
    img_list = []
    for j in images:
        img = {'image_url': 'https://beta.collabmates.com'+j.image_url.url}
        img_list.append(img)
    card = {'id': cards.id, 'title':cards.title, 'member':usr,'community' :cards.community.id,'images':img_list }
    card['share_url'] = 'https://beta.collabamtes.com/collabcard/'+str(cards.id)
    ans_text = ''
    count = 0
    for i in range(len(answer) -1, -1, -1):
        if i < len(answer) -2 :
            count = len(answer) - 2
            break
        userinfo = Userinfo.objects.get(user_id = answer[i].user)
        ans_text = ans_text+userinfo.name+", "
    if len(answer) >0 :
        ans_text = ans_text[:-2]
        if count > 0:
            ans_text = ans_text + ' & ' + str(count) + ' other'
        ans_text = ans_text+' answered'
    card['answet_text']= ans_text
    card['date'] = ''
    return JsonResponse({"collabcard": card, 'answers':answers})

def community_cards(request, community_id):
    user_id = request.GET.get('member_id')
    cards = Collabcard.objects.filter(community = community_id).order_by('-id')
    card = []
    for i in cards:
        user = Userinfo.objects.get(user_id = i.user)
        usr = {}
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number
        usr["image_url"] = user.image_url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        images = card_images.objects.filter(collabcard = i)
        img_list = []
        for j in images:
            img = {'image_url': 'https://beta.collabmates.com'+j.image_url.url}
            img_list.append(img)
        share_url = 'https://beta.collabamtes.com/collabcard/'+str(i.id)
        ans_text = ''
        count = 0
        answer = card_answers.objects.filter(card = i)
        for j in range(len(answer) -1, -1, -1):
            if j < len(answer) -  2:
                count = len(answer) - 2
                break
            userinfo = Userinfo.objects.get(user_id = answer[j].user)
            ans_text = ans_text+userinfo.name+", "
        if len(answer) >0 :
            ans_text = ans_text[:-2]
            if count > 0:
                ans_text = ans_text + ' & ' + str(count) + ' other'
            ans_text = ans_text+' answered'
        card.append({'id': i.id, 'title': i.title, 'member':usr,'images':img_list,'share_url' : share_url,  'answer_text': ans_text ,'date':''})
    return JsonResponse ({'collabcards': card})
@csrf_exempt
def create_answer(request):
    body = request.GET
    if 'member_id' in body:
        user_id = body['member_id']
    user = User.objects.get(id = user_id)
    if'collabcard_id' in body:
        card_id = body['collabcard_id']
    card = Collabcard.objects.get(id = card_id)
    if request.method == 'POST':
        res = json.loads(request.body)
        ans = card_answers()
        ans.answer =  res['title']
        ans.card = card
        ans.user = user
        ans.save()
        return JsonResponse({'success':True})

@csrf_exempt
def login(request):
    if request.method == 'POST':
        res = json.loads(request.body)
        user = Userinfo.objects.filter(email = res['email'])
        if user :
            userinfo = Userinfo.objects.all().filter(email = res['email'])
        else :
            userinfo = Userinfo.objects.all().filter(email = res['email'])
            if not userinfo:
                userinfo = Userinfo()
                usr = User()
                usr.username = res['name']
                usr.save()
                userinfo.user_id = usr
                userinfo.email = res['email']
                userinfo.name = res['name']
                userinfo.image_url = res['picture']['data']['url']
                if 'link' in res:
                    userinfo.fb_link = res['link']
                if 'location' in res:
                    userinfo.city = res['location']['name']
                userinfo.save()
        
        usr = {}
        usr['id'] = userinfo[0].user_id.id
        usr["name"] = userinfo[0].name
        usr["email"] = userinfo[0].email
        usr["city"] = userinfo[0].city
        usr["headline"] = userinfo[0].headline
        usr["contact_number"] = userinfo[0].contact_number
        usr["image_url"] = userinfo[0].image_url
        usr["about"] = userinfo[0].about
        usr["fb_link"] = userinfo[0].fb_link
        usr["linkedin_link"] = userinfo[0].linkedin_link
        return JsonResponse ({'user': usr})
    return HttpResponse('Login Api')

@csrf_exempt
def image_upload(request):
    body = request.GET
    if request.method =='POST':
        if 'member_id' in body:
            user_id = body['member_id']
        # user = User.objects.get(id = user_id)
        res = request.FILES['file']
        image_url = res
        if 'community_id' in body:
            community_id = body['community_id']
            community = Community.objects.get(id = community_id)
            community.image_url = image_url
            community.save()
        if 'collabcard_id' in body:
            collabcard_id = body['collabcard_id']
            collabcard = Collabcard.objects.get(id = collabcard_id)
            card_image = card_images()
            card_image.image_url = image_url
            card_image.collabcard = collabcard
            card_image.save()
        return JsonResponse({'success':True})

@csrf_exempt
def create_admin(request):
    params = request.GET
    if ['community_id'] in params:
        community_id = params['community_id']
    if request.method == 'POST':
        res = json.loads(request.body)
        admin = temp_admin()
        if 'name' in res:
            admin.name = res['name']
        if 'email' in res:
            admin.email = res['email']
        if 'contact_number' in res:
            admin.contact_number = res['contact_number']
        community = Community.objects.get(id = community_id)
        admin.community = community
        admin.save()
        return JsonResponse({'success':True})
    return HttpResponse('Add Admin Api')

def pending_members(request,community_id):
    community = Community.objects.get(id = community_id)
    requests = Requests.objects.filter(community = community).filter(status = 0)
    pending_requests = []
    for i in requests:
        resp = Form_response.objects.filter(community = community_id).filter(user = i.user_id.id)
        user = i.user_info
        usr = {}
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number
        usr["image_url"] = user.image_url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        user_response = []
        for j in resp:
            response_object = {}
            response_object['key'] = j.data
            response_object['value'] = j.response
            user_response.append(response_object)
        usr['user_respone'] = user_response
        pending_requests.append(usr)
    return JsonResponse({'pending_members': pending_requests})

@csrf_exempt
def request_response(request):
    res = json.loads(request.body)
    if 'member_id' in res:
        member_id = res['member_id']
    if 'community_id' in res:
        community_id = res['community_id']
    if 'accepted' in res:
        accepted = res['accepted']
    community = Community.objects.get(id = community_id)
    user = User.objects.get(id= member_id)
    req = Requests.objects.filter(community = community).filter(user_id = user)
    req = req[0]
    print(req.id)
    if accepted == True :
        req.status = 1
        req.save()
        member = Members()
        member.member_id = req.user_id
        member.community_id = req.community
        member.save()
        community = Community.objects.get(id = community_id)
        community.members_count = community.members_count+1
    else:
        req.status = 0
    return JsonResponse({'success': True})


def pending_request_count(request,community_id):
    community = Community.objects.get(id = community_id)
    requests = Requests.objects.filter(community = community).filter(status = 0)
    return JsonResponse({'pending_request_count': len(requests)})
