from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from togther.models import *
from togther.forms import *
from django.contrib.auth.models import User
import json
from django.http.response import JsonResponse
from collabmates_api.serializers import *
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime 
import time
from .notification import send_follow_notification,send_notification_to_admins,send_notification_for_join_requests,send_notification_for_new_collabcard_posted,send_notification_to_proposed_admin,send_notification_to_proposer
from django.db.models import Q
import dateutil.relativedelta
from .tasks import send_email_to_nominated_admin,send_email_for_new_collabcard_posted
from django.conf import settings
from togther.tasks import send_email_to_proposed_admin
from django.core.paginator import Paginator
from togther.views import set_user_tag, get_user_tag,get_nominated_admin_details
import os
from .firebase import update_last_answer_id
import re

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
        category_tag = Community_tags.objects.filter(tags_id=category_tag).values('community_id')
        # get communities based on user hidden tag
        user_tag = Community_tags.objects.filter(tags_id=user_tag).values('community_id')
        #intersect both of the querysets
        res = category_tag.intersection(user_tag).order_by("-community_id").distinct()
        #paginating the resultant queryset
        queryset = pagination(res, page_number)
        #return result
        return queryset

    if category_tag == 0 and user_tag == 0:
        # if there is not category tag and user does not have a hidden tag too
        # just return him all the communites
        community =  Community_tags.objects.values('community_id').order_by("-community_id").distinct()
        # paginating the communities
        queryset = pagination(community, page_number)
        return queryset

    if category_tag == 0 and user_tag != 0:
        # if there is no category tag , then return communites based on user hidden tag
        user_tag = Community_tags.objects.filter(tags_id=user_tag).values('community_id').order_by("-community_id").distinct()
        queryset = pagination(user_tag, page_number)
        return queryset

    if user_tag == 0 and category_tag != 0:
        # if there is no user hidden tag , then return communites based on category tag
        category_tag = Community_tags.objects.filter(tags_id=category_tag).values('community_id').order_by("-community_id").distinct()
        queryset = pagination(category_tag, page_number)
        return queryset


def serialize_community(queryset,user_id ):
    ''' this function gives us a dictionary of community/communities objects based on given queryset '''
    communities = []
    for community in queryset:

        try:
            # if the queryset is of type dictionary
            comm = Community.objects.get(id=community['community_id'])
        except:
            # if the queryset if a lazy community object
            comm = Community.objects.get(id=community.id)
        # check if the community is hidden or not

        if comm.hide_community == '0':
            # if not hidden , pass the community object to serializer
            serialized_object = CommunitySerializer(comm)
            new_dict = {}
            # form a dictionary of community objects
            new_dict.update(serialized_object)

            communities.append(new_dict)
        elif comm.hide_community == '1':

            pass

    return communities


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

    # user = User.objects.get(id = member_id)
    # getting communities of the member from member model based on member state
    communities = Members.objects.all().filter(member_id = user_id).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7))
    my_communities = []

    # making a tupple list and sorting communities based on date
    tupple_list=[]
    # sorting communities based on its updated time
    for each_community in communities:
        update_time=Community.objects.filter(id=each_community.community_id.id).values('updated_at')

        if update_time.count() == 0:

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

    for comm in my_communities:
        serialized_object = CommunitySerializer(comm)

        serialized_object['is_member'] = ''
        new_dict = {}
        new_dict.update(serialized_object)
        is_admin = False
        community = Community.objects.get(id = new_dict['id'])
        community_admins = Members.objects.filter(community_id = comm).filter(member_id =user_id)
        pending_requests = Members.objects.filter(community_id = community.id).filter(state = 3)

        if (community_admins[0].state == 1 or community_admins[0].state==2):
            new_dict['pending_members_count'] = pending_requests.count()
            is_admin = True
        else:
            new_dict['pending_members_count'] = 0
        new_dict['is_admin'] = is_admin

        # get time stamp
        if str(comm.updated_at) == "-9223372036854775808":
            time_text = ""
        else:
            # getting time stamp for the latest card
            time_text = get_time_text(comm.updated_at)

        new_dict['updated_at'] = time_text
        # getting the unseen cards
        # getting the total cards of a community
        total_collabcards = Collabcard.objects.filter(community=community).order_by("-id").values('id')
        # getting seen collabcards by the user from that community
        seen_collabcard = collabcard_seen.objects.filter(community=community, user=user_id).order_by("-id").values('card_id')
        # unseen cards count
        if (total_collabcards.count() - seen_collabcard.count()) <= 0:
            # if zero or less than zero , unseen card count = 0
            new_dict['collabcard_unseen'] =0
        else:
            new_dict['collabcard_unseen'] = (total_collabcards.count() - seen_collabcard.count())
        # getting unseen crad list by getting the difference between total cards and seen cards
        unseen_list  = total_collabcards.difference(seen_collabcard).values('id').distinct().order_by("-id")

        if total_collabcards.count()>0:
        # if community has atleast one card
            if unseen_list.count() != 0:
                # if the unseen cards are present
                # show the latest unseen cards text
                card = Collabcard.objects.get(id = unseen_list.values('id')[0]['id'])
            else:
                # if no unseen cards , show latest card text
                card = Collabcard.objects.get(id = total_collabcards.values('id')[0]['id'])
            # show details of the latest card or latest unseen card
            # get json form of card object
            collabcard = CollabcardSerializer(card,community)

            new_dict['collabcard'] = collabcard

            # get user details who posted the latest card
            user = Userinfo.objects.get(user_id = card.user)
            # get json form of userinfo object
            usr = UserinfoSerializer(user)

            collabcard['member'] = usr

        my_community.append(new_dict)
    return JsonResponse({'your_communities':my_community})


def community(request, community_id):
    '''Community detail page'''

    community = Community.objects.get(id=community_id)

    serialized_object = CommunitySerializer(community)
    new_dict = {}
    # form a dictionary of community objects
    new_dict.update(serialized_object)

    if community:

        new_dict['share_text_admin']= """Hi, I have added %s community on CollabMates. It will be good if you can join this community.\n"""%(new_dict['name'])
        new_dict['share_text_member']="""I recently joined %s community on CollabMates. It will be good if you also join this community.\n"""%(new_dict['name'])
        new_dict['share_text_anonymous']="""I recently discovered %s community on CollabMates. You can join this community using this link.\n"""%(new_dict['name'])
    return JsonResponse({'community': new_dict})


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
    community = []
    for comm in queryset:

        # if the queryset is of type dictionary
        comm_object = Community.objects.get(id=comm['community_id'])
        # check if the community is hidden or not

        if comm_object.hide_community == '0' and comm_object.id != community_id:
            # if not hidden , pass the community object to serializer
            serialized_object = CommunitySerializer(c)
            new_dict = {}
            # form a dictionary of community objects
            new_dict.update(serialized_object)


            community.append(new_dict)
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
        # if not
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

    send_notification_to_admins.delay(community_id,userinfo)
    return JsonResponse({'success':True})


def category_filter(request, category):
    categories = Community_tags.objects.all()
    communities = []
    for cat in categories:
        if cat.category == category:
            c = Community.objects.get(id = cat.community_id.id)
            communities.append(c)
    community = []
    for comm_object in communities:
        serialized_object = CommunitySerializer(comm_object)
        community.append(serialized_object)
    return JsonResponse({'communities': community})

def categories(request):
    ''' function to get all categories  '''

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
    usr = UserinfoSerializer(info[0])
    return JsonResponse ({'user': usr})


def members(request, community_id):
    ''' function to get all the mebers of a community including admins and nominated members '''
    community = get_object_or_404(Community, pk = community_id)
    # get members of the community
    member = Members.objects.filter(community_id = community).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7))
    members = []
    for mem in member:
        user = Userinfo.objects.filter(user_id = mem.member_id)
        if user:
            user = user[0]
            # get user json
            usr = UserinfoSerializer(user)
            usr['member_state'] = mem.state
            members.append(usr)
        else:
            continue
    return JsonResponse ({'members': members})


def admins(request, community_id):
    ''' function to get admins of a community '''
    admins = Members.objects.filter(community_id = community_id).filter(Q(state=1)|Q(state=2))
    users = []
    for admin in admins:
        user = Userinfo.objects.filter(user_id = admin.member_id.id)
        # get user serialized
        usr = UserinfoSerializer(user[0])
        users.append(usr)
    return JsonResponse ({'members': users})


@csrf_exempt
def create_community(request):
    ''' function create a community '''

    is_admin = request.GET.get('is_admin')
    if is_admin == 'true':
        # if community is created as a admin
        user_id = request.GET.get('member_id')
        if request.method == 'POST':
            res = json.loads(request.body)
            img = request.FILES.dict()
            # creating the community with given credentials
            group = Community()
            group.members_count = group.members_count + 1
            group.name = res['name']
            for dict in res['items']:
                if dict['key'] == 'Purpose of the community':
                    group.purpose = dict['value']
                elif dict['key'] == 'Geography of the community':
                    group.location = dict['value']
                elif dict['key'] == 'About the community (Optional)':
                    group.about = dict['value']
                elif 'image' in img:
                    group.image_url = img['image']
                elif dict['key'] == 'whatsapp_link' :
                    group.whatsapp_group_link = dict['whatsapp_link']
                    # saving the categories of the community
                elif dict['key'] == 'Type of community':
                    categories = dict['value']
                    categories = categories.split(", ")
                    for tags in categories:
                        tags_id = int(tags)
                        tags_object = Tags.objects.get(id=tags_id)
                        community_tags = Community_tags()
                        community_tags.category = tags_object.category_name
                        community_tags.community_id_id = group.id
                        community_tags.tags_id = tags_id
                        community_tags.save()
            group.updated_at=time.time()
            group.created_at=time.time()
            group.save()

            # create user as a admin for the community as the user is creating the community as a admin
            user = User.objects.get(id = user_id)
            community = Community.objects.get(id = group.id)

            # creating member as promoter
            member = Members()
            member.member_id = user
            member.community_id = community
            member.state=1                                  # admin state
            member.save()

            #creating a card while a comunity is created
            card = Collabcard()
            if community.purpose != '':
                card.title = "Created this community "+community.purpose
            else:
                card.title = "Listed our community on CollabMates. This will help us to know each other, have organised discussions and network efficiently."
            card.community = community
            card.user = user
            card.date_epoch =time.time()
            card.save()
            # saving details in firebase
            update_last_answer_id(card.id,"")

            Community.objects.filter(id=group.id).update(purpose_collabcard = card.id)
            # created card will be auto followed by the creator if the card
            follow=follow_collabcard()
            follow.collabcard_id=card
            follow.member_id=user
            follow.save()
            #getting details of the user who is creating the community
            user = Userinfo.objects.get(user_id = user.id)

            # get user serialized json
            usr = UserinfoSerializer(user)
            serialized_object = CommunitySerializer(community)
            new_dict = {}
            new_dict.update(serialized_object)

            ans_text =''

            #saving the questions to be asked while joining a community
            for questions in res['questions']:
                question = Form_data()
                question.data = questions["key"]
                question.community_id = community
                question.save()

            collabcard_share_url=url+'/collabcard/'+str(card.id)

            # forming card dict

            crd = {'id':card.id , 'title':card.title, 'member':usr,'answer_text': ans_text,'share_url':collabcard_share_url}
            #send_email_to_admin_of_community.delay(CommmunityAdminName=user.name,CommunityName=res['name'],email=user.email)
            return JsonResponse({'success':True, 'community':new_dict, 'collabcard':crd})
    else:
        # if community is created as a member
        member_id = request.GET.get('member_id')
        if request.method == 'POST':
            res = json.loads(request.body)

            # creating new community
            group = Community()
            group.members_count = group.members_count + 1
            group.name = res['name']
            group.updated_at=time.time()
            group.created_at=time.time()
            group.save()

            user = User.objects.get(id=member_id)

            # creating member as temporary promoter
            member = Members()
            member.member_id = user
            member.community_id = group
            member.state=2                              # temperary admin state
            member.save()
            # get community serialized json
            serialized_object = CommunitySerializer(group)
            new_dict = {}
            new_dict.update(serialized_object)

            user_id = request.GET.get('member_id')
            user = Userinfo.objects.get(user_id = user_id)
            #send_email_to_temp_admin_of_community.delay(CommmunityAdminName=user.name,CommunityName=res['name'],email=user.email)
            return JsonResponse({'success':True, 'community':new_dict})
    return HttpResponse("Create Community Api")


@csrf_exempt
def create_card(request):
    ''' function to create a card '''

    user_id = request.GET.get('member_id')
    community_id = request.GET.get('community_id')

    # useer = User.objects.get(id = user_id)
    user = Userinfo.objects.get(user_id = user_id)
    community = Community.objects.get(id = community_id)
    if request.method == 'POST':
        res = json.loads(request.body)
        # creating card
        card = Collabcard()
        card.title = res['title']
        card.community = community
        card.user = user.user_id
        if 'share_link' in res:
            card.share_link=res['share_link']
        card.date_epoch=time.time()
        card.save()
        # if the community does not have a purpose card then a purpose will be created
        # the first card created for a community is the purpose card
        if not community.purpose_collabcard:
            Community.objects.filter(id=community_id).update(purpose_collabcard  = card.id)

        # sending notification to the user
        send_notification_for_new_collabcard_posted.delay(community_id,res['title'],user_id,user.name)
        send_email_for_collabcard(community,user,card)
        Community.objects.filter(id=community_id).update(updated_at=time.time())

        collabcard = CollabcardSerializer(card, community)

        collabcard['date'] = datetime.today().strftime('%d-%m-%Y')

        # get user object's serialized json
        usr = UserinfoSerializer(user)
        collabcard['member'] = usr

        # card creator auto follows the card
        follow=follow_collabcard()
        follow.collabcard_id=card
        follow.member_id=user.user_id
        follow.save()

        update_last_answer_id(card.id,"")
        return JsonResponse({'success':True,'collabcard':collabcard})
    return JsonResponse()

def send_email_for_collabcard(community,user,card):

    '''function to make the format of email to send when a new collabcard is posted'''


    members=Members.objects.filter(community_id=community)
    college_tag=Community_tags.objects.filter(community_id=community).filter(Q(tags_id=41)|Q(tags_id=42))
    form_link=url
    for tag in college_tag:
        if tag.tags_id == 41:
            form_link='https://docs.google.com/forms/d/e/1FAIpQLSes87js8cTiGg0x-Vw9DYrnY1BCZTolba0B1WBvcVSYZSGAwg/viewform'
        elif tag.tags_id == 42:
            form_link='https://docs.google.com/forms/d/e/1FAIpQLSfqN2z1wg6CCJ4ZKH1lxQQgJ8iUWEbtTT0R9NT64zg5f13_ig/viewform'


    for member in members:
        context = {
            'community_name': community.name,
            'collabcard_creater': user.name,
            'collabcard_creater_image':url+user.image_file.url,
            'creater_header': user.headline,
            'url':  url + '/collabcard/' + str(card.id),
            'form_link':form_link
        }

        if member.member_id.id == user.user_id.id:
            continue
        if member.state == 1 or member.state == 2 or member.state == 4:
            userinfo=Userinfo.objects.get(user_id=member.member_id)
            context['reciever']=userinfo.name
            context['reciever_image']=url+userinfo.image_file.url
            context['to']=userinfo.email
            #print(context)
            send_email_for_new_collabcard_posted.delay(context)






def collabcard(request, card_id):
    ''' function to get card details, answers and images '''
    # get the card object

    cards = Collabcard.objects.get(id = card_id)

    # coverting current time into epoch time for getting time stamp of answers and card

    # get all the answers of the card
    answer = card_answers.objects.filter(card = cards)

    answer_id=request.GET.get('answer_id','')

    if answer_id:
        answer_id=int(answer_id)
        answer=card_answers.objects.filter(card=cards,id__gt=answer_id)
        answers=get_answer_data(answer)
        return JsonResponse({'answers': answers})
    else:
        answers=get_answer_data(answer)

    user = Userinfo.objects.get(user_id = cards.user.id)
    # serializing user object
    usr = UserinfoSerializer(user)
    # get the card image if any

    files= get_collabcard_files(card_id)
    card=CollabcardSerializer(cards,cards.community)
    card['images']=files[0]
    card['member']=usr
    card['pdf']=files[1]
    # get tine stamp for card
    time_text = get_time_text(cards.date_epoch)
    card['created_at'] = time_text
    return JsonResponse({"collabcard": card, 'answers':answers})
  


def get_answer_data(answer):

    '''function to get answer for a particular collabcard from database database'''
    answers = []
    for ans in answer:
        user = Userinfo.objects.filter(user_id=ans.user.id)
        usr = UserinfoSerializer(user[0])
        # coverting current time into epoch time

        if str(ans.date_epoch) == "-9223372036854775808":
            time_text = ""
        else:
            time_text = get_time_text(ans.date_epoch)

        answers.append({'id': ans.id, 'answer': ans.answer, 'created_at': time_text, 'member': usr})
    return answers

def get_collabcard_files(card_id):

    '''function to return pdf and image files of a collabcard'''

    files = Card_Attachment.objects.filter(collabcard=card_id)
    img_list=[]
    pdf=[]
    for file in files:
        if file.type == 'Image':
            img = {'image_url': url + file.attachment.url}
            img_list.append(img)
        elif file.type == 'Pdf':
            pdf_url = {'pdf_file': url + file.attachment.url}
            pdf.append(pdf_url)
    return (img_list,pdf)


def get_time_text(created_time):
    """ function to get time stamp """

    # get current time and convert it into epoch time
    present_time = str(datetime.now())
    current_time = datetime.strptime(present_time.strip(' \t\r\n'), "%Y-%m-%d %H:%M:%S.%f").strftime('%s')
    created = datetime.fromtimestamp(created_time)
    current = datetime.fromtimestamp(int(current_time))
    difference = dateutil.relativedelta.relativedelta (current, created)

    if difference.days :
        # if difference is in days
        if difference.days == 1:
            return str(difference.days)+" day ago"

        elif difference.days < 7 :
            return str(difference.days)+" days ago"

        elif difference.days == 7:
            return "1 week ago"
        # if difference is more than one week return created date
        return time.strftime('%d/%m/%Y', time.localtime(created_time))
    elif difference.hours:
        # if difference is in hours
        if difference.hours == 1:
            return str(difference.hours)+" hour ago"

        return str(difference.hours)+" hours ago"
    elif difference.minutes:
        # if difference is in hours
        if difference.minutes ==1:
            return str(difference.minutes)+" min ago"

        return str(difference.minutes)+" mins ago"
    else:
        # if difference is in seconds
        return "Just Now"

def community_cards(request, community_id):
    ''' function get all the cards in a community '''

    community = Community.objects.get(id = community_id)
    cards = Collabcard.objects.filter(community = community_id).order_by('id')
    member_id=request.GET.get('member_id')

    card_list = []
    for card in cards:
        user = Userinfo.objects.get(user_id = card.user)
        # serialize user object
        usr = UserinfoSerializer(user)
        # get card images --------------------------------------------------------

        files=get_collabcard_files(card)


        # -----------------------------------------------------------------------
        share_url = url+'/collabcard/'+str(card.id)

        # get time stamp
        if str(card.date_epoch) == "-9223372036854775808":
            # if there is no time stamp , return nothing
            time_text=""
        else:
            # get time stamp
            time_text = get_time_text(card.date_epoch)
        ans_text = card.answer_text
        card_dict={'id': card.id,
                   'title': card.title,
                   'member':usr,
                   'images':files[0],
                   'pdf':files[1],
                   'share_url' : share_url,
                   'answer_text': ans_text ,
                   'created_at':time_text,
                   'state':get_status_of_collabcard(member_id,community,card),
                   'share_link':card.share_link
                   }
        card_list.append(card_dict)
    return JsonResponse ({'collabcards': card_list})

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
        update_last_answer_id(card_id,ans.id)


        #auto following the collabcard if answer is created
        is_present=is_collabcard_already_followed(card,user)
        if  is_present == False:
            follow = follow_collabcard()
            follow.collabcard_id = card
            follow.member_id = user
            follow.save()

        send_follow_notification.delay(card_id=card_id,user_id=user_id,answer=res['title'])

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
    ''' function to login a user '''

    if request.method == 'POST':
        res = json.loads(request.body)
        dic_form=res
        json_to_save=json.dumps(dic_form)
        login_type=request.GET.get('type')
        # if user is logging in from facebook
        if login_type == 'facebook':
            email=res['email']
            # converting email to lower case and removing unwanted space
            email=email.lower().strip()
            user =User.objects.filter(email=email)

            if not user:
                # creating a user if no user is associated with that email
                usr = User()
                usr.username = res['name']
                usr.email = res['email']
                usr.save()
                # if there is no user then user will not have userinfo too
                # creating user info
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
            # if user is logging in with linkedIn
            user_name=res['firstName']['localized']['en_US'] + " " + res['lastName']['localized']['en_US']
            profile_picture=res['profilePicture']['displayImage~']['elements'][2]['identifiers'][0]['identifier']
            email=res['email']['elements'][0]['handle~']['emailAddress']
            userinfo = Userinfo.objects.filter(email=email)
            # create user and userinfo if there is no user with this email
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
        # get serialized user object
        usr = UserinfoSerializer(userinfo[0])
        return JsonResponse ({'user': usr})

    return HttpResponse('Login Api')

@csrf_exempt
def image_upload(request):
    ''' function to upload community images '''
    body = request.GET
    if request.method =='POST':
        # if 'member_id' in body:
        #     user_id = body['member_id']
        #     user = User.objects.get(id = user_id)
        new_image = request.FILES['file']
        if 'community_id' in body:
             # if image to be updated in community
            community_id = body['community_id']
            community = Community.objects.get(id = community_id)
            old_image_file = community.image_url

            # # deleting the old file after new file is updated
            # # get the new image file
            version =  re.findall(r'\w*__image__(\d+)',old_image_file.name)
            if version:
                version = int(version[0])+1
            else:
                version = 1
            new_image.name = str(community_id) + '__image__' + str(version) + '.jpg'

            if not old_image_file == new_image:
                #     # if both are not same delete old file
                if os.path.isfile(old_image_file.path):
                    os.remove(old_image_file.path)

                community.image_url = new_image
                community.save()

        elif 'collabcard_id' in body:

            # if image to be updated in collabcard
            collabcard_id = body['collabcard_id']
            collabcard = Collabcard.objects.get(id = collabcard_id)
            try:
                # delete old image of the card if exists
                card_image = Card_Attachment.objects.get(collabcard = collabcard)
                # deletes the associated file too
                card_image.attachment.delete(save=True)

            except:
                # else create a new card image
                card_image = Card_Attachment()
                card_image.collabcard = collabcard
            card_image.attachment = new_image
            card_image.type='Image'
            card_image.save()
        return JsonResponse({'success':True})


@csrf_exempt
def upload_attachment(request):
    '''function to upload attachments'''
    body=request.GET
    if request.method == 'POST':
        attachment=request.FILES['file']
        if 'community_id' in body:
            # if image to be updated in community
            community_id = body['community_id']
            community = Community.objects.get(id=community_id)
            old_image_file = community.image_url
            # deleting the old file after new file is updated
            # get the new image file
            if not old_image_file == attachment:
                # if both are not same delete old file
                if os.path.isfile(old_image_file.path):
                    os.remove(old_image_file.path)

            community.image_url = attachment
            community.save()
        elif 'collabcard_id' in body:
            attachment_type=body['type']
            collabcard_id = body['collabcard_id']
            collabcard = Collabcard.objects.get(id = collabcard_id)

            file=Card_Attachment()
            file.attachment=attachment
            file.collabcard=collabcard
            file.type=attachment_type
            file.save()
        return JsonResponse({'success':True})
    return JsonResponse({'success': False})



@csrf_exempt
def create_admin(request,community_id):
    ''' saving admin details given by user of a community
     when the user is creating a community as a member '''
    if request.method == 'POST':
        res = json.loads(request.body)
        # saving the nominated promoter details
        admin = temp_admin()
        if 'name' in res:
            admin.name = res['name']
        if 'email_id' in res:
            admin.email = res['email_id']
        if 'contact_no' in res:
            admin.contact_number = res['contact_no']
        if 'member_id' in res:
            member_id = res['member_id']
        community = Community.objects.get(id = community_id)
        admin.community = community
        admin.member_id = member_id
        admin.save()
        # checking if there is any person with given mail , and make him nominated promoter
        check = check_member(res['email_id'],community_id,res['member_id'],res)
        return JsonResponse({'success':True})
    return HttpResponse('Add Admin Api')

def check_member(email,community_id,member_id,res):
    """ check if the user is already a member of the invited community and make user as nominated promoter
     if he is registered in collabmates and if the user is not registered just send the user a invitation email """
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
            """ if the user is present get user details """
            NominatedAdmin_id = user[0].user_id.id
            NominatedAdmin=user[0].name
        else:
            """ if the user is not present just user a email"""
            send_email_to_nominated_admin.delay(NominatedAdmin=res['name'],email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            return False
    except:
        """ if any error trying fetch the user details , then user is not registered , send an email"""
        send_email_to_nominated_admin.delay(NominatedAdmin=res['name'],email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
        return False

    if user:
        # get the state of the user of the community he is proposed to become a promoter for
        member =Members.objects.filter(community_id = community,member_id = user[0].user_id.id)

        if member and member[0].state == 4:
            # if the user is already a member , give him state 7
            # state 7 is nominted promoter who is already a member of thet community
            Members.objects.filter(community_id = community,member_id = user[0].user_id.id).update(state=7)
            # send mail and notification
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )

        elif member and (member[0].state == 6 or member[0].state == 7):
            # if he is nominated again just send hime a remainding mail and notification
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )

        else:
            # if user is not anything to the community and he is nominated as promoter
            # create a member instance , making the user a nominated promoter giving user state = 6
            # state 6 is nominated member who was never involved in that community
            member =Members()
            member.community_id = community
            member.member_id = user[0].user_id
            member.state = 6
            member.save()
            # send mail and notification
            send_email_to_nominated_admin.delay(NominatedAdmin=NominatedAdmin,email=email,ProposedAdmin=ProposedAdmin,proposedAdminState = proposedAdminState,CommunityName=CommunityName,community_id =community.id)
            send_notification_to_proposed_admin.delay(nominated_admin_id = NominatedAdmin_id, community_id= community.id, proposed_admin_name=ProposedAdmin )
        return True
    return False


def pending_members(request,community_id):
    ''' function to get members requested to join in a community '''
    community = Community.objects.get(id = community_id)
    pend_requests=Members.objects.filter(community_id=community).filter(state = 3)
    pending_requests = []
    for i in pend_requests:
        print(i.member_id.id,"  ==  ",type(i))
        resp = Form_response.objects.filter(community = community_id).filter(user = i.member_id.id)
        user = Userinfo.objects.get(user_id = i.member_id.id)
        # serilaizing userinfo object
        usr = UserinfoSerializer(user)
        user_response = []
        for j in resp:
            # getting the answers of the users who requested to join
            # for the questions that have been asked while requestiong to join in a community
            response_object = {}
            response_object['key'] = j.data
            response_object['value'] = j.response
            user_response.append(response_object)
        usr['response'] = user_response
        pending_requests.append(usr)
    return JsonResponse({'pending_members': pending_requests})

@csrf_exempt
def request_response(request):
    ''' function to approve or decline a members who requested to join '''
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
        # if accepted , then make him a member of the community
        #updating the approve state
        Members.objects.filter(member_id=member_id,community_id=community).update(state=4)  # aprove state = 4
        community = Community.objects.get(id = community_id)
        set_user_tag(user.id, community_id)
        members_count = community.members_count+1
        Community.objects.filter(id = community_id).update(members_count=members_count)
        # send notification
        send_notification_for_join_requests.delay(community_id,True,member_id)
    else:
        # if rejected , chaange user state to 5
        Members.objects.filter(member_id=member_id,community_id=community).update(state=5)  # decline state = 5
        # and also send notification
        send_notification_for_join_requests.delay(community_id, False, member_id)
    return JsonResponse({'success': True})


def pending_request_count(request,community_id):
    ''' fucntion to get peding members count of a community '''

    no_of_pending_members = Members.objects.filter(community_id = community_id).filter(state = 3).count()
    return JsonResponse({'pending_request_count': no_of_pending_members})

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
        # if the card has not yet been seen by the user, update the database
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
                #sending email to promoter , that user has accepted his request to beacome a promoter
                send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState =1,CommunityName=community.name,community_id = community.id)
                send_notification_to_proposer.delay(prop_admin,community,nom_admin[0].name)
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
                #sending email to promoter , that user has accepted his request to beacome a promoter
                send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState=2,CommunityName=community.name,community_id = community.id)
                send_notification_to_proposer.delay(prop_admin, community,nom_admin[0].name)
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
            #sending email to promoter , that user has accepted his request to become a promoter
            send_email_to_proposed_admin.delay(NominatedAdmin=nom_admin[0].name,email=prop_admin.email,ProposedAdmin=prop_admin.name,proposedAdminState=1,CommunityName=community.name,community_id = community.id)
            send_notification_to_proposer.delay(prop_admin, community,nom_admin[0].name)
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
    count = Members.objects.filter(community_id=community).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7)).count()
    # updating count
    Community.objects.filter(id=community_id).update(members_count = count)
    return

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

    serialized_object = CommunitySerializer(community)
    new_dict = {}
    new_dict.update(serialized_object)

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


def send_mail_and_notification():

    pass
