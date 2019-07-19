from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from togther.models import *
from togther.forms import *
from django.contrib.auth.models import User
import json
from django.http.response import JsonResponse
from collabmates_api.serializers import CommunitySerializer
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime 
import time
from .notification import send_follow_notification,send_notification_to_admins,send_notification_for_join_requests,send_notification_for_new_collabcard_posted,send_notification_to_proposed_admin
from django.db.models import Q
import dateutil.relativedelta
from .tasks import send_email_to_nominated_admin
from django.conf import settings
from togther.tasks import send_email_to_proposed_admin
from django.core.paginator import Paginator
from togther.views import set_user_tag, get_user_tag

url  = settings.URL


def communities(request):
    '''function to get all the communities'''

    if request.method == 'GET':
        request = request.GET.dict()
        if 'member_id' in request:
            # get member id and members hidden tag
            user_id = request['member_id']
            user_tag = get_user_tag(user_id)
            if user_tag:
                # if member has a hidden tag
                user_tag = user_tag[0].tag_id
            else:
                # if member does not have a hidden tag
                user_tag = 0
        if 'page' in request:
            # if page number is in request
            page_number = request['page']
        else:
            # set default page number
            page_number = 1
        if 'category_id' in request:
            if request['category_id'] != '':
                # if communites are filtered by category
                category = request['category_id']
                # get category id'''
                category = int(category)
                # get the related communities according to category asked and user hidden tag
                community = get_communities_by_tags(category_tag=category, user_tag=user_tag,page_number = page_number)
                # serialize the communities objects recieved from above function
                community = serialize_community(queryset =community,user_id =user_id)
                # send communities JSON response '''
                return JsonResponse({'communities': community})
            else:
                # if category is not provided, get categories according to the user tag if user has one
                queryset = get_communities_by_tags(user_tag=user_tag,page_number = page_number)
                community = serialize_community(queryset=queryset, user_id=user_id)
                return JsonResponse({'communities': community})

def get_communities_by_tags(user_tag=0, category_tag=0,page_number=1):
    ''' fetching communities based on category tag and user hidden tag '''
    if category_tag != 0 and user_tag != 0:
        ''' if category tag and user tag ,bith are provided
            get communities ,which are the intersection of given category and user hidden tag '''

        # get communities based on category tag
        category_tag = Community_tags.objects.filter(tags_id=category_tag).values('community_id').order_by("-community_id")
        # get communities based on user hidden tag
        user_tag = Community_tags.objects.filter(tags_id=user_tag).values('community_id').order_by("-community_id")
        #intersect both of the querysets
        res = category_tag.intersection(user_tag)
        #paginating the resultant queryset
        queryset = pagination(res, page_number)
        #return result
        return queryset

    if category_tag == 0 and user_tag == 0:
        # if there is not category tag and user does not have a hidden tag too
        # just return him all the communites
        community =  Community_tags.objects.all().values('community_id').order_by("-community_id")
        # paginating the communities
        queryset = pagination(community, page_number)
        return  queryset

    if category_tag == 0:
        # if there is no category tag , then return communites based on user hidden tag
        user_tag = Community_tags.objects.filter(tags_id=user_tag).values('community_id').order_by("-community_id")
        queryset = pagination(user_tag, page_number)
        return queryset

    if user_tag == 0:
        # if there is no user hidden tag , then return communites based on category tag
        category_tag = Community_tags.objects.filter(tags_id=category_tag).values('community_id').order_by("-community_id")
        queryset = pagination(category_tag, page_number)
        return queryset

def serialize_community(queryset,user_id ):
    ''' this function gives us a dictionary of community/communities objects based on given queryset '''
    community = []
    for i in queryset:

        try:
            # if the queryset is of type dictionary
            c = Community.objects.get(id=i['community_id'])
        except:
            # if the queryset if a lazy community object
            c = Community.objects.get(id=i.id)
        # check if the community is hidden or not

        if c.hide_community == '0':
            # if not hidden , pass the community object to serializer
            serializer_class = CommunitySerializer(c)
            new_dict = {}
            # form a dictionary of community objects
            new_dict.update(serializer_class.data)

            # appending all other necessary details of community
            if new_dict['image_url']:
                new_dict['image_url'] = url + new_dict['image_url']
            else:
                new_dict[
                    'image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'

            member = Members.objects.all().filter(community_id=c.id)
            is_member = False
            for m in member:
                if m.member_id == user_id:
                    is_member = True

            new_dict['is_member'] = is_member
            new_dict['share_url'] = url + '/community/' + str(new_dict['id'])
            new_dict['date'] = c.active_since
            new_dict['members_count'] = update_member_count(c.id)
            community.append(new_dict)
    # return dictionary
    return community


def pagination(queryset,page_number):

    '''function to create pagination and return a query set for page number'''

    paginator = Paginator(queryset, 20)
    max_page=len(paginator.page_range)

    if max_page < int(page_number):
        return []
    queryset = paginator.get_page(page_number)

    return queryset


def your_communities(request,user_id):
    '''This function is used to see your communities based on user id'''

    member_id=request.GET.get('member_id')

    user = User.objects.get(id = member_id)
    communities = Members.objects.all().filter(member_id = user_id).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7))
    my_communities = []

    # making a tupple list and sorting communities based on date
    tupple_list=[]
    for each_community in communities:
        update_time=Community.objects.filter(id=each_community.community_id.id).values('updated_at')

        if len(update_time) == 0:

            update_time=-9223372036854775808
        else:
            update_time=update_time[0]['updated_at']
        x=(each_community.community_id,update_time)
        tupple_list.append(x)

    result = sorted(tupple_list, key= lambda x:x[1],reverse=True)

    for each_community in result:

        if str(member_id) != str(user_id):
            if each_community[0].hide_community == '0':
                my_communities.append(each_community[0])

        else:
            member_id=user_id
            if each_community[0].hide_community == '2':
                continue
            my_communities.append(each_community[0])
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
            new_dict['image_url'] = url+new_dict['image_url']
        else:
            new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
        new_dict['share_url']= url+str(new_dict['id'])

        is_admin = False
        community = Community.objects.get(id = new_dict['id'])
        community_admins = Members.objects.filter(community_id = i).filter(member_id =user_id)
        pending_requests = Members.objects.filter(community_id = community.id).filter(state = 3)

        if (community_admins[0].state == 1 or community_admins[0].state==2):
            new_dict['pending_members_count'] = len(pending_requests)
            is_admin = True
        else:
            new_dict['pending_members_count'] = 0
        new_dict['is_admin'] = is_admin
        total_collabcards = Collabcard.objects.filter(community=community)
        seen_collabcard = collabcard_seen.objects.filter(community=community, user=user_id)

        if (len(total_collabcards) - len(seen_collabcard)) < 0:
            new_dict['collabcard_unseen'] =0
        else:
            new_dict['collabcard_unseen'] = (len(total_collabcards) - len(seen_collabcard))

        unseen_list=[]
        total_list=[]
        seen_list=[]
        for j in total_collabcards:
            total_list.append(j.id)

        for j in seen_collabcard:
            seen_list.append(j.card_id)

        for j in total_list:
            if j not in seen_list:
                unseen_list.append(j)

        total_list=sorted(total_list)
        unseen_list = sorted(unseen_list)
        if len(total_collabcards)>0:

            if len(unseen_list) != 0:
                card = Collabcard.objects.get(id = unseen_list[0])
            else:
                card = Collabcard.objects.get(id = total_list[-1:][0])

            collabcard = {}
            collabcard['id'] = card.id
            collabcard['title'] = card.title
            collabcard['community'] = community.id
            collabcard['share_url'] = url+'/collabcard/'+str(card.id)
            collabcard['answer_text'] = ''
            new_dict['collabcard'] = collabcard

            if str(i.updated_at) == "-9223372036854775808":
                time_text=""
            else:
                time =datetime.now()
                time =str(time)
                target_timestamp =datetime.strptime(time.strip(' \t\r\n'), "%Y-%m-%d %H:%M:%S.%f").strftime('%s') 
                time_text = get_time_text(i.updated_at,target_timestamp)

            new_dict['updated_at'] = time_text
            usr = {}
            user = Userinfo.objects.get(user_id = card.user)
            usr['id'] = user.user_id.id
            usr["name"] = user.name
            usr["email"] = user.email
            usr["city"] = user.city
            usr["headline"] = user.headline
            usr["contact_number"] = user.contact_number
            usr["image_url"] = url+user.image_file.url
            usr["about"] = user.about
            usr["fb_link"] = user.fb_link
            usr["linkedin_link"] = user.linkedin_link
            collabcard['member'] = usr


        my_community.append(new_dict)
    return JsonResponse({'your_communities':my_community})


def community(request, community_id):
    '''Community detail page'''
    queryset = Community.objects.filter(id = community_id)
    body = request.GET

    if 'member_id' in body:
        user_id = body['member_id']
    # getting communities serialaized data
    community = serialize_community(queryset=queryset, user_id=user_id)
    return JsonResponse({'community': community[0]})


def similar_community(request, community_id):
    '''function to return similar communitites'''
    body = request.GET
    user_id = body['member_id']
    user_tag = get_user_tag(user_id)

    if user_tag:
        user_tag = user_tag[0].tag_id
    else:
        user_tag = 0
    # getting communities based on user hidden tags
    queryset = get_communities_by_tags(user_tag=user_tag)[:11]
    community = serialize_community(queryset=queryset, user_id=user_id)
    return JsonResponse({'communities': community})

def join_community(request, community_id):

    '''function to get questions of community'''

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

    '''function to join community'''
    res = json.loads(request.body)
    user_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')
    user = User.objects.get(id = user_id)
    community = Community.objects.get(id = community_id)

    userinfo = Userinfo.objects.get(user_id=user_id)

    #inserting in members table if the member status is pending and inserting it to database with status=3

    #If the member is declined from the community and he applied again
    try:
        current_state=Members.objects.filter(member_id=user,community_id=community).values('state')
        if current_state[0]['state'] == 5:
            Members.objects.filter(member_id=user, community_id=community).update(state=3)
    except:
        member = Members()
        member.member_id = user
        member.community_id = community
        member.state = 3  # pending members
        member.save()

    if 'questions' in res:
        for i in res['questions']:
            response = Form_response()
            response.data = i['key']
            response.response = i['value']
            response.user = user.id
            response.community = community.id
            response.save()
    Community.objects.filter(id=community_id).update(updated_at=time.time())

    send_notification_to_admins(community_id,userinfo)

    return JsonResponse({'success':True})


def category_filter(request, category):
    categories = Community_tags.objects.all()
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


    tags=Tags.objects.all()
    Category_list=[]
    for category in tags:
        category_dict={}
        if category.id == 4 or category.id == 8 or  category.id == 11 or category.id == 13 or category.id == 22 or category.id == 25  or category.id == 28 or category.id == 39:
            category_dict['id']=str(category.id)
            category_dict['title']=category.category_name
            Category_list.append(category_dict)


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
        user["image_url"] = url+i.image_file.url
        user["about"] = i.about
        user["fb_link"] = i.fb_link
        user["linkedin_link"] = i.linkedin_link
    return JsonResponse ({'user': user})

def members(request, community_id):
    community = get_object_or_404(Community, pk = community_id)
    member = Members.objects.filter(community_id = community).filter(Q(state=1)|Q(state=2)|Q(state=4))
    members = []
    for i in member:
        user = Userinfo.objects.filter(user_id = i.member_id)
        if user:
            user = user[0]
        else:
            continue
        usr = {}
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number
        usr["image_url"] = url+user.image_file.url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        members.append(usr)
    return JsonResponse ({'members': members})

def admins(request, community_id):
    admins = Members.objects.filter(community_id = community_id).filter(Q(state=1)|Q(state=2))
    users = []
    for admin in admins:
        user = Userinfo.objects.filter(user_id = admin.member_id.id)
        usr={}
        usr = {}
        usr['id'] = user[0].user_id.id
        usr["name"] = user[0].name
        usr["email"] = user[0].email
        usr["city"] = user[0].city
        usr["headline"] = user[0].headline
        usr["contact_number"] = user[0].contact_number
        usr["image_url"] = url+user[0].image_file.url
        usr["about"] = user[0].about
        usr["fb_link"] = user[0].fb_link
        usr["linkedin_link"] = user[0].linkedin_link
        users.append(usr)
    return JsonResponse ({'members': users})

@csrf_exempt
def create_community(request):
    is_admin = request.GET.get('is_admin')
    if is_admin == 'true':
        user_id = request.GET.get('member_id')
        print(user_id)
        if request.method == 'POST':
            res = json.loads(request.body)
            img = request.FILES.dict()
            # creating the community with given credentials
            group = Community()
            group.members_count = group.members_count + 1
            group.name = res['name']
            for i in res['items']:
                if i['key'] == 'Purpose of the community':
                    group.purpose = i['value']
                if i['key'] == 'Geography of the community':
                    group.location = i['value']
                if i['key'] == 'About the community (Optional)':
                    group.about = i['value'] 
                if 'image' in img:
                    group.image_url = img['image']
                if i['key'] == 'whatsapp_link' :
                    group.whatsapp_group_link = i['whatsapp_link']
            group.updated_at=time.time()
            group.created_at=time.time()
            group.save()
            #saving the category of the community
            for i in res['items']:
                if i['key'] == 'Type of community' :
                    categories = i['value']
                    categories = categories.split(", ")
                    for tags in categories:
                        tags_id=int(tags)
                        tags_object=Tags.objects.get(id=tags_id)
                        community_tags=Community_tags()
                        community_tags.category=tags_object.category_name
                        community_tags.community_id_id=group.id
                        community_tags.tags_id=tags_id
                        community_tags.save()

            # create user as a admin for the community as the user is creating the community as a admin
            print(group)
            user = User.objects.get(id = user_id)
            community = Community.objects.get(id = group.id)
            member = Members()
            member.member_id = user
            member.community_id = community
            member.state=1                                  # admin state
            member.save()
            #creating a card while a comunity is created
            card = Collabcard()
            print(community)
            if community.purpose != '':
                card.title = "Created this community "+community.purpose
            else:
                card.title = "Listed our community on CollabMates. This will help us to know each other, have organised discussions and network efficiently."
            card.community = community
            card.user = user
            card.date_epoch =time.time()
            card.save()
            Community.objects.filter(id=group.id).update(purpose_collabcard = card.id)
            follow=follow_collabcard()
            follow.collabcard_id=card
            follow.member_id=user
            follow.save()
            #getting details of the user who is creating the community
            user = Userinfo.objects.get(user_id = user.id)
            usr = {}
            usr['id'] = user.user_id.id
            usr["name"] = user.name
            usr["email"] = user.email
            usr["city"] = user.city
            usr["headline"] = user.headline
            usr["contact_number"] = user.contact_number
            usr["image_url"] = url+user.image_file.url
            usr["about"] = user.about
            usr["fb_link"] = user.fb_link
            usr["linkedin_link"] = user.linkedin_link
            serializer_class = CommunitySerializer(community)
            new_dict = {}
            new_dict.update(serializer_class.data)
            if new_dict['image_url']:
                new_dict['image_url'] = url+new_dict['image_url']
            else:
                new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
            new_dict['share_url']= url+'/community/'+str(new_dict['id'])
            #new_dict['date'] = community['active_since']
            ans_text =''
            #saving the questions to be asked while joining a community
            for questions in res['questions']:
                question = Form_data()
                question.data = questions["key"]
                question.community_id = community
                question.save()
            collabcard_share_url=url+'/collabcard/'+str(card.id)
            crd = {'id':card.id , 'title':card.title, 'member':usr,'answer_text': ans_text,'share_url':collabcard_share_url}
            print(crd)
            #send_email_to_admin_of_community.delay(CommmunityAdminName=user.name,CommunityName=res['name'],email=user.email)
            return JsonResponse({'success':True, 'community':new_dict, 'collabcard':crd})
    else:
        member_id = request.GET.get('member_id')
        if request.method == 'POST':
            res = json.loads(request.body)
            print(res)
            group = Community()
            group.members_count = group.members_count + 1
            group.name = res['name']
            group.updated_at=time.time()
            group.created_at=time.time()
            group.save()
            community = Community.objects.get(id = group.id)
            user = User.objects.get(id=member_id)
            member = Members()
            member.member_id = user
            member.community_id = community
            member.state=2                              # temperary admin state
            member.save()
            serializer_class = CommunitySerializer(community)
            new_dict = {}
            new_dict.update(serializer_class.data)
            if new_dict['image_url']:
                new_dict['image_url'] = url+new_dict['image_url']
            else:
                new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
            new_dict['share_url']= url+'/community/'+str(new_dict['id'])
            user_id = request.GET.get('member_id')
            user = User.objects.get(id = user_id)
            user = Userinfo.objects.get(user_id = user.id)
            #send_email_to_temp_admin_of_community.delay(CommmunityAdminName=user.name,CommunityName=res['name'],email=user.email)
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
        card.date_epoch=time.time()
        card.save()
        # if the community does not have a purpose card then a purpose will be created
        # the first card created for a community is the purpose card
        if not community.purpose_collabcard:
            Community.objects.filter(id=community_id).update(purpose_collabcard  = card.id)
        send_notification_for_new_collabcard_posted(community_id,res['title'],user_id,user.name)
        Community.objects.filter(id=community_id).update(updated_at=time.time())
        collabcard = {}
        collabcard['id'] = card.id
        collabcard['title'] = card.title
        collabcard['community'] = community.id
        collabcard['share_url'] = url+'/collabcard/'+str(card.id)
        collabcard['answer_text'] = ''
        new_dict = {}
        new_dict = collabcard
        new_dict['date'] = datetime.today().strftime('%Y-%m-%d')
        usr = {}
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number
        usr["image_url"] = url+user.image_file.url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        collabcard['member'] = usr
        follow=follow_collabcard()
        follow.collabcard_id=card
        follow.member_id=useer
        follow.save()
        return JsonResponse({'success':True,'collabcard':new_dict})
    return JsonResponse()

def collabcard(request, card_id):
    cards = Collabcard.objects.get(id = card_id)
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
        usr["image_url"] = url+user.image_file.url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        # coverting current time into epoch time

        if str(i.date_epoch) == "-9223372036854775808":
            time_text=""
        else:
            time =datetime.now()
            time =str(time)
            target_timestamp =datetime.strptime(time.strip(' \t\r\n'), "%Y-%m-%d %H:%M:%S.%f").strftime('%s') 
            time_text = get_time_text(i.date_epoch,target_timestamp)
        
        answers.append({'id':i.id,'answer':i.answer,'created_at':time_text ,'member': usr})
    user = Userinfo.objects.get(user_id = cards.user.id)
    usr = {}
    usr['id'] = user.user_id.id
    usr["name"] = user.name
    usr["email"] = user.email
    usr["city"] = user.city
    usr["headline"] = user.headline
    usr["contact_number"] = user.contact_number
    usr["image_url"] = url+user.image_file.url
    usr["about"] = user.about
    usr["fb_link"] = user.fb_link
    usr["linkedin_link"] = user.linkedin_link
    images = card_images.objects.filter(collabcard = card_id)
    img_list = []
    for j in images:
        img = {'image_url': url+j.image_url.url}
        img_list.append(img)
    card = {'id': cards.id, 'title':cards.title, 'member':usr,'community' :cards.community.id,'images':img_list }
    card['share_url'] = url+'/collabcard/'+str(cards.id)
    card['answer_text']= cards.answer_text

    # coverting current time into epoch time
    time =datetime.now()
    time =str(time)
    target_timestamp =datetime.strptime(time.strip(' \t\r\n'), "%Y-%m-%d %H:%M:%S.%f").strftime('%s') 

    time_text = get_time_text(cards.date_epoch,target_timestamp)
    card['created_at'] = time_text
    return JsonResponse({"collabcard": card, 'answers':answers})

def get_time_text(created_time,current_time ):

    dt1 = datetime.fromtimestamp(created_time)
    dt2 = datetime.fromtimestamp(int(current_time))
    rd = dateutil.relativedelta.relativedelta (dt2, dt1)

    if rd.days :
        if rd.days == 1:
            return str(rd.days)+" day ago"
        if rd.days < 7 :
            return str(rd.days)+" days ago"
        elif rd.days == 7:
            return "1 week ago"
        return time.strftime('%d/%m/%Y', time.localtime(created_time))
    elif rd.hours:
        if rd.hours == 1:
            return str(rd.hours)+" hour ago"
        return str(rd.hours)+" hours ago"
    elif rd.minutes:
        if rd.minutes ==1:
            return str(rd.minutes)+" min ago"
        return str(rd.minutes)+" mins ago"
    else:
        return "Just Now"

def community_cards(request, community_id):
    community = Community.objects.get(id = community_id)
    cards = Collabcard.objects.filter(community = community_id).order_by('id')
    member_id=request.GET.get('member_id')

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
        usr["image_url"] = url+user.image_file.url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        images = card_images.objects.filter(collabcard = i)
        img_list = []
        for j in images:
            img = {'image_url': url+j.image_url.url}
            img_list.append(img)
        share_url = url+'/collabcard/'+str(i.id)
        if str(i.date_epoch) == "-9223372036854775808":
            time_text=""
        else:
            time =datetime.now()
            time =str(time)
            target_timestamp =datetime.strptime(time.strip(' \t\r\n'), "%Y-%m-%d %H:%M:%S.%f").strftime('%s') 
            time_text = get_time_text(i.date_epoch,target_timestamp)
        ans_text = i.answer_text
        card_dict={'id': i.id,
                   'title': i.title,
                   'member':usr,
                   'images':img_list,
                   'share_url' : share_url,
                   'answer_text': ans_text ,
                   'created_at':time_text,
                   'state':get_status_of_collabcard(member_id,community,i)
                   }
        card.append(card_dict)
    return JsonResponse ({'collabcards': card})

def get_status_of_collabcard(member_id,community,card):
    '''function to get the state of collabcard'''
    state=0
    member_id=User.objects.get(id=member_id)

    seen_status=collabcard_seen.objects.filter(card=card,community=community,user=member_id)
    if seen_status:
        state=1
        follow=follow_collabcard.objects.filter(collabcard_id=card,member_id=member_id)
        if follow:
            state=2

    return state

@csrf_exempt
def create_answer(request):
    '''function to post answer on collabcard'''
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
        ans.date_epoch=time.time()
        ans.save()


        #auto following the collabcard if answer is created
        is_present=is_collabcard_already_followed(card,user)
        if  is_present == False:
            follow = follow_collabcard()
            follow.collabcard_id = card
            follow.member_id = user
            follow.save()

        send_follow_notification(card,user,res['title'])

        #calling update_answer_text 
        update_answer_text(card_id)

        return JsonResponse({'success':True})

def update_answer_text(card_id):
        '''function for updating the answer_text feild in collab card model'''
        ans_text=''
        card = Collabcard.objects.get(id = card_id)
        card_ans = card_answers.objects.filter(card = card)
        # if only one answer is present fro a collab card
        if len(card_ans) == 1:
            # get the name of the user who answered
            username = Userinfo.objects.get(user_id = card_ans[0].user_id)
            #format the answer text string as "username answered"
            ans_text = username.name + " responded"
            # update the answer_text feild in collabcard
            Collabcard.objects.filter(id=card_id).update(answer_text=ans_text) 
        # if there is more than one answer
        else:
            #get the user id's of the users who have answered
            user_list =[]
            for ans in card_ans:
                # save it in a list without duplicates
                if ans.user_id not in user_list:
                    user_list.append(ans.user_id)
            count = 1
            #check if only two different users have answered
            #not more than two different users should have answered
            if len(user_list)==2:
                for ID in user_list:
                    username = Userinfo.objects.get(user_id = ID)
                    ans_text += username.name
                    if count !=0:
                        ans_text += " and "
                        count-=1
                ans_text+=" responded"
                Collabcard.objects.filter(id=card_id).update(answer_text=ans_text)




            # if more than two different users have answered
            if len(user_list) >= 3:
                for ID in user_list:
                    username = Userinfo.objects.get(user_id = ID)
                    ans_text += username.name
                    break


                ans_text+= " & "+str(len(user_list)-1) + " others responded"
                Collabcard.objects.filter(id=card_id).update(answer_text=ans_text)
        

@csrf_exempt
def login(request):

    if request.method == 'POST':
        res = json.loads(request.body)
        dic_form=res
        json_to_save=json.dumps(dic_form)
        login_type=request.GET.get('type')
        if login_type == 'facebook':
            email=res['email']
            email=email.lower().strip()
            user =User.objects.filter(email=email)
            if not user:
                usr = User()
                usr.username = res['name']
                usr.email = res['email']
                usr.save()
            userinfo = Userinfo.objects.all().filter(email = res['email'])
            if not userinfo:
                userinfo = Userinfo()
                userinfo.user_id = usr
                userinfo.email = res['email']
                userinfo.name = res['name']
                userinfo.image_url = res['picture']['data']['url']
                if 'link' in res:
                    userinfo.fb_link = res['link']
                if 'location' in res:
                    userinfo.city = res['location']['name']
                userinfo.login_type='facebook'
                userinfo.login_json=json_to_save
                userinfo.save()
        else:
            user_name=res['firstName']['localized']['en_US'] + " " + res['lastName']['localized']['en_US']
            profile_picture=res['profilePicture']['displayImage~']['elements'][2]['identifiers'][0]['identifier']
            email=res['email']['elements'][0]['handle~']['emailAddress']
            userinfo = Userinfo.objects.filter(email=email)

            if not userinfo:
                userinfo=Userinfo()
                usr=User()
                usr.username=user_name
                usr.email = email
                usr.save()
                userinfo.user_id=usr
                userinfo.email=email
                userinfo.name=user_name
                userinfo.image_url=profile_picture
                userinfo.login_type='linkedIn'
                userinfo.login_json=json_to_save
                userinfo.save()

        userinfo=Userinfo.objects.filter(email=email)
        usr = {}
        usr['id'] = userinfo[0].user_id.id
        usr["name"] = userinfo[0].name
        usr["email"] = userinfo[0].email
        usr["city"] = userinfo[0].city
        usr["headline"] = userinfo[0].headline
        usr["contact_number"] = userinfo[0].contact_number
        usr["image_url"] = url+userinfo[0].image_file.url
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
def create_admin(request,community_id):
    # saving admin details given by creator of a community
    # when the creator is creating a community as a member
    if request.method == 'POST':
        res = json.loads(request.body)
        admin = temp_admin()
        if 'name' in res:
            admin.name = res['name']
        if 'email_id' in res:
            admin.email = res['email_id']
        if 'contact_no' in res:
            admin.contact_number = res['contact_no']
        if 'member_id' in res:
            member_id = res['member_id']
        #member = Members.objects.get(id = member_id)
        community = Community.objects.get(id = community_id)
        admin.community = community
        admin.member_id = member_id
        admin.save()
        check = check_member(res['email_id'],community_id,res['member_id'],res)
        return JsonResponse({'success':True})
    return HttpResponse('Add Admin Api')

def check_member(email,community_id,member_id,res):
    ProposedAdmin = Userinfo.objects.get(user_id = member_id)
    community = Community.objects.get(id = community_id)
    proposedAdminState = Members.objects.filter(member_id=ProposedAdmin.user_id,community_id = community)
    proposedAdminState = proposedAdminState[0].state
    CommunityName=community.name
    email=email.lower().strip()
    ProposedAdmin=ProposedAdmin.name

    try:
        user = Userinfo.objects.filter(email=email)

        if user:
            print("user is present")
            NominatedAdmin_id = user[0].user_id.id
            NominatedAdmin=user[0].name
        else:
            print("user is not present")
            send_email_to_nominated_admin.delay(NominatedAdmin=res['name'],email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            return False
    except:
        print("except block email")
        send_email_to_nominated_admin.delay(NominatedAdmin=res['name'],email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
        return False
    if user:
        member =Members.objects.filter(community_id = community,member_id = user[0].user_id.id)
        print("member  == ",member)
        if member and member[0].state == 4:
            print("member is meber")
            Members.objects.filter(community_id = community,member_id = user[0].user_id.id).update(state=7)
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )
        elif member and (member[0].state == 6 or member[0].state == 7):
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )
            print("member is already nominated")
        else:
            print("member is created")
            member =Members()
            member.community_id = community
            member.member_id = user[0].user_id
            member.state = 6
            member.save()
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )
        return True
    return False


def pending_members(request,community_id):
    community = Community.objects.get(id = community_id)
    pend_requests=Members.objects.filter(community_id=community).filter(state = 3)
    pending_requests = []
    for i in pend_requests:
        print(i.member_id.id,"  ==  ",type(i))
        resp = Form_response.objects.filter(community = community_id).filter(user = i.member_id.id)
        user = Userinfo.objects.get(user_id = i.member_id.id)
        usr = {}
        usr['id'] = user.user_id.id
        usr["name"] = user.name
        usr["email"] = user.email
        usr["city"] = user.city
        usr["headline"] = user.headline
        usr["contact_number"] = user.contact_number       
        usr["image_url"] = url+user.image_file.url
        usr["about"] = user.about
        usr["fb_link"] = user.fb_link
        usr["linkedin_link"] = user.linkedin_link
        user_response = []
        for j in resp:
            response_object = {}
            response_object['key'] = j.data
            response_object['value'] = j.response
            user_response.append(response_object)
        usr['response'] = user_response
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
    if accepted == True :
        #updating the approve state
        Members.objects.filter(member_id=member_id,community_id=community).update(state=4)  # aprove state = 4
        community = Community.objects.get(id = community_id)
        set_user_tag(user.id, community_id)
        members_count = community.members_count+1
        Community.objects.filter(id = community_id).update(members_count=members_count)
        send_notification_for_join_requests(community_id,True,member_id)
    else:
        Members.objects.filter(member_id=member_id,community_id=community).update(state=5)  # decline state = 5
        send_notification_for_join_requests(community_id, False, member_id)
    return JsonResponse({'success': True})


def pending_request_count(request,community_id):
    no_of_pending_members = Members.objects.filter(community_id = community_id).filter(state = 3)
    return JsonResponse({'pending_request_count': len(no_of_pending_members)})

@csrf_exempt
def collabcards_seen(request):
    '''This functions stores the details of members who have seen the card'''
    params = request.GET
    if 'community_id' in params:
        community_id = params['community_id']
    if 'collabcard_id' in params:
        card_id = params['collabcard_id']
    if 'member_id' in params:
        user_id = params['member_id']

    community = Community.objects.get(id = community_id)
    user = User.objects.get(id = user_id)
    card = Collabcard.objects.get(id = card_id)

    seen_card = collabcard_seen.objects.filter(community = community,user=user,card=card)
    if not seen_card:
       collab_seen=collabcard_seen()
       collab_seen.card=card
       collab_seen.user=user
       collab_seen.community=community
       collab_seen.save()

    return JsonResponse({'success': True})


def members_state(request):
    '''This function gives the state of user.Get Api'''

    member_id=request.GET.get('member_id')
    community_id=request.GET.get('community_id')
    state=0
    query_set=Members.objects.filter(member_id=member_id,community_id=community_id)
    for data in query_set:
        if data.state != None:
            state=data.state
    if state == 0:
        '''checking if user DETAILS EXIST in temp admin table in case he is a newly registered user'''
        user = Userinfo.objects.get(user_id = member_id)
        community = get_object_or_404(Community, pk=community_id)
        check = get_nominated_admin_details(community_id=community_id,email=user.email)
        if check:
            '''creating a new row in members table making current
            user a nominated promoter of this community,if he is a newly
            registered user and his details are present in temp admin table'''
            member = Members()
            member.member_id = user.user_id
            member.community_id = community
            member.state = 6
            member.save()
            state = 6
        else:
            state = 0

    return JsonResponse({'state':state})

def get_nominated_admin_details(community_id,email):
    '''fetching nominated promoter details from temp admin table'''
    community = get_object_or_404(Community, pk = community_id)
    details = temp_admin.objects.filter(community_id=community,email=email)
    if details:
        '''details are present,return s true'''
        print('details are present')
        return True
    else:
        '''details are not present, returns false'''
        print('details are not present')
        return False


@csrf_exempt
def push(request):
    '''This function is used to insert fcm token to the database in order to generate notifications from database'''
    member_id=request.GET.get('member_id','')
    token=request.GET.get('token','')

    is_member=Userinfo.objects.filter(user_id=member_id)
    print(is_member)
    success=False
    if is_member:
        success=True
        fcm_token=Userinfo.objects.filter(user_id=member_id).update(fcm_token=token)

    return JsonResponse({'success':success})


@csrf_exempt
def collabcard_follow(request):
    '''Api to follow collabcard by members Post API'''
    collabcard_id=request.GET.get('collabcard_id','')
    member_id=request.GET.get('member_id','')
    status=request.GET.get('value','true')

    if status != 'true':
        status=False



    collabcard=Collabcard.objects.get(id=collabcard_id)
    member_id=User.objects.get(id=member_id)
    is_present = is_collabcard_already_followed(collabcard, member_id)

    if is_present == False:
        follow=follow_collabcard()
        follow.collabcard_id=collabcard
        follow.member_id=member_id
        follow.save()
    else:
        '''Deleting the collabcard '''
        if status == False:
            follow_collabcard.objects.filter(collabcard_id=collabcard,member_id=member_id).delete()

    return JsonResponse({'success':True})


def is_collabcard_already_followed(collabcard,member_id):

    '''function to check whether the person already followed the collabcard or not'''

    is_present=False
    follow_data=follow_collabcard.objects.filter(collabcard_id=collabcard,member_id=member_id)

    if follow_data:
        is_present=True

    return is_present

@csrf_exempt
def accept_invitation(request):
    ''' accept promoter request '''
    # getting details of nominated person and the community promoter who proposed this invitation
    member_id=request.GET.get('member_id')
    community_id=request.GET.get('community_id')
    community = Community.objects.get(id=community_id)
    promoter = Members.objects.filter(community_id = community).filter(Q(state=1)|Q(state=2))
    nom_admin = Userinfo.objects.all().filter(user_id = member_id)
    # ------------------------------------------------------------------------------
    # if only one promoter to a community

    accepted = request.GET.get('value','true')

    if accepted == 'true':
        if len(promoter) == 1:
            #if the community has only one promoter
            prop_admin = Userinfo.objects.get(user_id=promoter[0].member_id.id)
            # if the promoter is actually a promoter
            if promoter[0].state == 1:
                Members.objects.filter(community_id=community, member_id=member_id).update(state=1)
                # updating member count of the community
                update_member_count(community.id)
                # set user hidden tag
                set_user_tag(member_id, community.id)
                # sending email to promoter , that user has accepted his request to beacome a promoter
                send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState =1,CommunityName=community.name,community_id = community.id)
                return JsonResponse({'success':True})
            # if the promoter is a temporary promoter
            elif promoter[0].state == 2:
                temp_promoter = Members.objects.filter(community_id = community,state=2)
                Members.objects.filter(community_id = community,member_id=temp_promoter[0].member_id).update(state =4)
                Members.objects.filter(community_id = community,member_id=member_id).update(state =1)
                # updating member count of the community
                update_member_count(community.id)
                # set user hidden tag
                set_user_tag(member_id, community.id)
                # sending email to promoter , that user has accepted his request to beacome a promoter
                send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState=2,CommunityName=community.name,community_id = community.id)
                return JsonResponse({'success':True})
        else:
            # if there are more than two admins , sent mail to the promoter who invited this member
            # getting the promoter ID from temp admin model
            promoter_who_proposed = temp_admin.objects.filter(community_id=community,email=nom_admin[0].email)
            # getting the promoter details
            prop_admin = Userinfo.objects.get(user_id=promoter_who_proposed[0].member_id)
            # make th current member a promoter of this community
            Members.objects.filter(community_id=community, member_id=member_id).update(state=1)
            # updating member count of the community
            update_member_count(community.id)
            # set user hidden tag
            set_user_tag(member_id, community.id)
            # sending email to promoter , that user has accepted his request to become a promoter
            send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState=1,CommunityName=community.name,community_id = community.id)
            return JsonResponse({'success':True})
    else:
        # if nominated promoter didn't accept the invitation
        member = Members.objects.filter(community_id=community, member_id=member_id)
        if member[0].state == 6:
            print("member state == 6")
            # deleting his details from temp admin model
            usr = Userinfo.objects.get(user_id = member[0].member_id)
            temp = temp_admin.objects.filter(community_id=community,email= usr.email)
            temp.delete()
            # if he is previously not a member of this community
            # then delete the member from members model
            Members.objects.filter(community_id=community, member_id=member_id).delete()
        elif member[0].state == 7:
            print("member state == 7")
            # if he is previously not a member of this community , then make him member again
            Members.objects.filter(community_id=community, member_id=member_id).update(state=4)
        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


def update_member_count(community_id):
    ''' update members count of a community , when a promoter or member joins a community '''
    community = Community.objects.get(id=community_id)
    # getting the count of members including admins in a community
    count = Members.objects.filter(community_id=community).filter(Q(state=1)|Q(state=2)|Q(state=4))
    # updating count
    Community.objects.filter(id=community_id).update(members_count = len(count))
    return len(count)

@csrf_exempt
def edit_community(request):

    '''function to edit the community'''

    community_id=request.GET.get('community_id')

    json_body=json.loads(request.body)

    key=json_body['key']

    if key == 'purpose':
        value = json_body['value']
        purpose_collabcard=Community.objects.filter(id=community_id).values('purpose_collabcard')
        purpose_collabcard=purpose_collabcard[0]['purpose_collabcard']
        Collabcard.objects.filter(id=purpose_collabcard).update(title=value)
        Community.objects.filter(id=community_id).update(purpose=value)

    elif key == 'questions':
        questions=json_body['questions']
        edit_questions(questions,community_id)
    else:
        value = json_body['value']
        Community.objects.filter(id=community_id).update(**{key: value})

    community=Community.objects.get(id=community_id)

    serializer_class = CommunitySerializer(community)
    new_dict = {}
    new_dict.update(serializer_class.data)

    return JsonResponse({'success': True,'community':new_dict})




def edit_questions(questions,community_id):

    '''function to edit questions of community'''

    community_object=Community.objects.get(id=community_id)
    Form_data.objects.filter(community_id=community_object).delete()
    print('Previous Questions Deleted')

    for question in questions:
    # if any new question is added -- Insert functionality
        question_object=Form_data()
        question_object.data=question['key']
        question_object.community_id=community_object
        question_object.save()

    print('questions updated successfully')












