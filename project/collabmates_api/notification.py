from __future__ import absolute_import, unicode_literals
from celery import shared_task
import re
import time
from django.http.response import JsonResponse
import psycopg2
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from pyfcm import FCMNotification
from togther.models import (Community_Rank, collabcardState,
                            MemberPollVotes, Collabcard,Members,Members,Referal,Community
                            )
from utility.celery_beat_tasks import CeleryBeatTask
from utility.states import *
import json
from django.shortcuts import get_object_or_404

# file to store configuration of the system


# database details
db_user=settings.DATABASES['default']['USER']
db_password=settings.DATABASES['default']['PASSWORD']
db_host=settings.DB_HOST
db_port=settings.DATABASES['default']['PORT']
db_database=settings.DATABASES['default']['NAME']


url=settings.URL

#server keys for sending notification
server_key=settings.FCM_SERVER_KEY

#notifications for different mobile os versions

def send_notification_for_android(token_list,message):

    '''function to send notification to android'''



    result=""
    push_service = FCMNotification(api_key=server_key)
    result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                  data_message=message['payload'])
    print(result)




def send_notification_for_ios(token_list, message):

    '''function to send notification to android'''



    result = ""
    push_service = FCMNotification(api_key=server_key)
    result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                  message_title=message['payload']['title'],
                                                  message_body=message['payload']['sub_title'],
                                                  data_message=message['payload'])



def notification_meta(notification_list,message):

    '''function to process notification to send'''



    token_list_android=[]
    token_list_ios=[]

    for data in notification_list:

        if data['mobile_os'] == "Android":
            token_list_android.append(data['fcm_token'])
        else:
            token_list_ios.append(data['fcm_token'])
        print(data['user_id'])

    if token_list_android:
        send_notification_for_android(token_list_android,message)

    if token_list_ios:
        send_notification_for_ios(token_list_ios,message)





def get_connection():
    '''function to create a postgres connection'''
    try:
        connection = psycopg2.connect(user=db_user,
                                      password=db_password,
                                      host=db_host,
                                      port=db_port,
                                      database=db_database)
        return connection

    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting  to PostgreSQL", error)


def get_token_for_fcm(member_id,flag=None):

    '''function to get token from user'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        if not flag:
            curr.execute("select fcm_token from togther_userinfo where user_id_id=" + str(member_id))
            fcm_token = curr.fetchone()
            if fcm_token:
                return fcm_token[0]
        else:
            curr.execute("select fcm_token,mobile_os from togther_userinfo where user_id_id=" + str(member_id))

            notification_details=curr.fetchone()
            if notification_details:
                fcm_token=notification_details[0]
                if  notification_details[1]:
                    mobile_os=notification_details[1]
                else:
                    mobile_os="Android"
                return (fcm_token,mobile_os)

        return None

    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting to PostgreSQL  ", error)

def get_community_name(community_id):
    try:
        conn=get_connection()
        curr=conn.cursor()
        sql = "select name from togther_community where id= " + str(community_id)
        curr.execute(sql)
        community_name = curr.fetchone()[0]
        curr.close()
        conn.close()
        return community_name

    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting to PostgreSQL", error)

def is_mobile_os_android(fcm_token):

    '''function to change whether the mobile os is android or ios'''


    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="select mobile_os from togther_userinfo where fcm_token='"+fcm_token+"'"
        curr.execute(sql)
        #print(sql)
        mobile_os = curr.fetchone()
        if mobile_os:
            #print(mobile_os[0])
            if mobile_os[0] == "Android":
                #print("Android")
                return True
            elif mobile_os[0] == "iOS":
                #print("iOS")
                return False
        else:
            return True

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)



def send_notification_to_multiple_devices(token_list,message):

    '''This function is used to send notifications by checking whether the request is android or ios'''

    for token in token_list:

        mobile_os=is_mobile_os_android(token)
        if mobile_os:
            send_notification(token,message,True)               #if request is android
        else:
            send_notification(token,message,False)              #if request is iOS



# def send_notification_to_multiple_devices(token_list,message):
#
#     '''This function is used to send notifications'''
#     result=""
#
#     push_service = FCMNotification(api_key=server_key)
#     result = push_service.notify_multiple_devices(registration_ids=token_list,data_message=message['payload'])
#     print(result)
#
#     return result



def send_notification(fcm_token,message,is_android):

    '''function to send notification for android as well as iOS'''

    token_list=[]
    token_list.append(fcm_token)
    if not is_android:
        push_service = FCMNotification(api_key=server_key)
        result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                      message_title=message['payload']['title'],
                                                      message_body=message['payload']['sub_title'],
                                                      data_message=message['payload'])
    else:
        push_service = FCMNotification(api_key=server_key)
        result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                      data_message=message['payload'])
    print(result)


def get_tagged_members_list(answer):

    tagged_users_list = re.findall("route://member/"'([0-9]+)', answer)
    answer_text = re.split('>>', answer)[-1]

    tagged_user_names = "@" + ' @'.join(re.findall('(?<=\<\<).+?(?=\|)', answer))
    
    return tagged_users_list, answer_text, tagged_user_names

    # return {"tagged_users_list":tagged_users_list, "answer_text":answer_text, "tagged_user_names":tagged_user_names}


@shared_task
def send_notification_to_admins(community_id,name):
    '''function to send notification to community admins'''
    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="select member_id_id from togther_members where community_id_id= " + str(community_id) + " and (state=1 or state=2)"
        curr.execute(sql)
        admins=curr.fetchall()
        token_list=[]
        for admin in admins:
             fcm_token=get_token_for_fcm(admin[0])
             token_list.append((fcm_token))

        community_name=get_community_name(community_id)
        message={}
        message['payload']={
            'title':community_name,
            'sub_title':str(name)+' has requested to join your community.Please verify',
            'route':'route://member_approve?'+'community_id=' + str(community_id) + "&" + "community_name=" + str(community_name)
        }
        send_notification_to_multiple_devices(token_list,message)
        curr.close()
        connection.close()
    except (Exception, psycopg2.Error) as error:

        print ("Error while connecting to PostgreSQL", error)

@shared_task
def send_notification_for_join_requests(community_id,flag,member_id):
    '''function to send notification for approval or denial'''
    community_name=get_community_name(community_id)
    temp = {}
    notification_list=[]
    temp['user_id'] = member_id
    notification_details = get_token_for_fcm(member_id, True)
    temp['fcm_token'] = notification_details[0]
    temp['mobile_os'] = notification_details[1]

    notification_list.append(temp)

    message={}
    if flag:
        message['payload']={
            'title':community_name,
            'sub_title':"Congrats! you are now part of this community",
            'route':'route://member_approved?community_id='+ str(community_id)
        }
    else:
        message['payload'] = {
            'title': community_name,
            'sub_title': "Your request to join this community has been rejected",
            'route': 'route://member_declined?community_id=' + str(community_id)
        }

    notification_meta(notification_list,message)




# notifications for new collabcards

@shared_task
def send_notification_for_new_collabcard_posted(community_id, collabcard_title, card_creater_id, card_creater_name,
                                            **kwargs):
    '''function to send notification to all members when new collabcard is posted'''

    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = "select member_id_id from togther_members where community_id_id=%s and member_id_id !=%s and (state=1 or state=2 or state=4 or state=7)"
        parameter_list = [community_id, card_creater_id]
        curr.execute(sql, parameter_list)
        member_list = curr.fetchall()

        notification_list = []
        for member in member_list:
            temp = {}
            temp['user_id'] = member[0]
            notification_details = get_token_for_fcm(member[0], True)
            temp['fcm_token'] = notification_details[0]
            temp['mobile_os'] = notification_details[1]
            notification_list.append(temp)

        tagged_users_list, collabcard_title, user_names = get_tagged_members_list(collabcard_title)

        community_name = kwargs['community_name']
        message = {}
        typ = kwargs['type'] if 'type' in kwargs else 0

        if typ == 2:
            sub_title = "Posted an event: " + str(collabcard_title)
        elif typ == 3:
            sub_title = "Posted a poll: " + str(collabcard_title)
        else:
            sub_title = str(collabcard_title)

        message['payload'] = {
            'title': str(card_creater_name) + " @ " + str(community_name),
            'sub_title': sub_title,
            'route': 'route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(
                community_name) + '&community_state=' + str(kwargs['community_state'])
        }

        notification_meta(notification_list, message)

        # functionality to send notification to tagged users
        for member_id in tagged_users_list:
            if not str(member_id) == str(card_creater_id):
                send_notification_to_tagged_users(card_id=kwargs['card_id'], answerer_name=card_creater_name,
                                                  answer=collabcard_title,
                                                  user_id=member_id, user_names=user_names)


        if typ == 2 or typ == 3:
            task_name = 'poll_with_id_' + str(kwargs['card_id']) if typ == 3 else 'event_with_id_' + str(
                kwargs['card_id'])
            task_path = 'collabmates_api.notification.poll_expiry_or_event_remainder_notification'
            task_name, task_path = task_name, task_path
            if task_name and task_path:
                celerybeatask = CeleryBeatTask()
                args = [community_name, community_id, typ]
                print("card id === ", kwargs['card_id'],"   type ===  ",typ)
                print("date time === ",kwargs['date_time'])

                date_time = int(str(kwargs['date_time'])[:10])
                print("date time === ", date_time)
                if typ == 2:
                    date_time = date_time - 1800
                else:
                    date_time = date_time
                print("date time === ", date_time)
                celerybeatask.get_or_create_new_beat_task(card_creater_id=card_creater_id,
                                                          card_creater_name=card_creater_name,
                                                          args=args, task_name=task_name, task_path=task_path,
                                                          date_time=date_time, interval=False, crontab=True,
                                                          collabcard_title=collabcard_title,
                                                          card_id=kwargs['card_id'],
                                                          community_state=kwargs['community_state'])

    except (Exception, psycopg2.Error) as error:

        print("Error while connecting to PostgreSQL", error)



@shared_task
def send_follow_notification(card_id,user_id,answer):

    '''function to send notification to followed members who have responded or follow'''

    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="select user_id from togther_collabcardstate where card_id=%s and state=%s and removed_status is null and mute_status = False"
        parameter_list=[card_id, collabcard_states.COLLABCARD_STATE_FOLLOW]
        curr.execute(sql,parameter_list)
        member_list=curr.fetchall()
        curr.execute("select name from togther_userinfo where user_id_id=%s",[user_id])
        answerer_name=curr.fetchone()
        curr.close()
        connection.close()
        message={}

        # tagged_users_list = re.findall("route://member/"'([0-9]+)', answer)
        # answer_text = re.split('>>', answer)[-1]
        #
        # user_names="@"+' @'.join(re.findall('(?<=\<\<).+?(?=\|)', answer))

        tagged_users_list, answer_text, user_names = get_tagged_members_list(answer)

        message['payload']={
            "title":str(answerer_name[0]) + " responded",
            "sub_title":answer_text,
            "route":"route://collabcard?collabcard_id="+str(card_id)
        }

        notification_list=[]
        for member in member_list:
            if str(member[0]) != user_id and str(member[0]) not in tagged_users_list:
                temp={}
                notification_details = get_token_for_fcm(member[0],True)
                temp['id']=member[0]
                temp['fcm_token']=notification_details[0]
                temp['mobile_os']=notification_details[1]
                notification_list.append(temp)

        notification_meta(notification_list,message)



        #functionality to send notification to tagged users
        for member_id in tagged_users_list:
            if not str(member_id) == str(user_id):
                send_notification_to_tagged_users(card_id=card_id, answerer_name=answerer_name[0],
                                                  answer=answer_text,
                                                  user_id=member_id, user_names=user_names)



    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting to PostgreSQL", error)


@shared_task
def send_notification_to_tagged_users(card_id,answerer_name,answer,user_id,user_names):

    '''function to send notification to those users who didn't follow the collabcard but tagged in an answer'''

    try:

        message={}

        message['payload']={
            "title":str(answerer_name) + " tagged you",
            "sub_title":str(user_names)+" "+answer,
            "route":"route://collabcard?collabcard_id="+str(card_id)
        }
        notification_list = []

        temp = {}
        notification_details = get_token_for_fcm(user_id, True)
        temp['id'] = user_id
        temp['fcm_token'] = notification_details[0]
        temp['mobile_os'] = notification_details[1]
        notification_list.append(temp)

        notification_meta(notification_list, message)


    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting to PostgreSQL", error)



@shared_task
def send_poll_or_event_notification(card_id, user_id):
    """ send poll/event notification to poll/event card created person, when some one votes/attending """
    card = Collabcard.objects.get(pk=card_id)
    card_creator_fcm_token = card.user.userinfo.fcm_token

    community_name = card.community.name
    community_id = card.community.id

    member = User.objects.get(pk=user_id)
    member_name = member.userinfo.name

    if card.type == 2:
        sub_title = member_name + " is attending your event"
        time.sleep(60)
        attending_state = collabcardState.objects.filter(card=card,
                                                         user=member).filter(Q(state=3) | Q(state=4)).filter(removed_status=None)
        if not attending_state.exists():
            return
    else:
        sub_title = member_name + " voted on your poll"
    message = {}
    message['payload'] = {
        'title': str(community_name),
        'sub_title': sub_title,
        'route': 'route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(
            community_name) + '&community_state=' + str(card.community.hide_community)
    }

    token_list = [card_creator_fcm_token]

    send_notification_to_multiple_devices(token_list, message)



@shared_task
def poll_expiry_or_event_remainder_notification(community_name, community_id, typ, **kwargs):

    """ function to send notification to all members when event/poll is going to start/end """
    print("\ntype === ", typ)
    print(" community-id === ", community_id)
    print("kwargs === ", kwargs,"\n")
    try:
        if typ == 2:
            token_list = list(collabcardState.objects.filter(card=kwargs['card_id']).filter(
                                 Q(state=3) |
                                 Q(state=4)).filter(removed_status=None).values_list('user__userinfo__fcm_token', flat=True))

        else:
            token_list = list(MemberPollVotes.objects.filter(card=kwargs[
                                                                'card_id']).order_by('-id').values_list(
                                                                'user__userinfo__fcm_token', flat=True))
        print("token list ===== ", token_list)

        card_instance = Collabcard.objects.get(pk=kwargs['card_id'])

        user_fcm = card_instance.user.userinfo.fcm_token

        if not user_fcm in token_list:
            token_list.append(user_fcm)


        if typ == 3:
            sub_title = 'Your poll ended. Tap to see results'
        else:
            sub_title = 'Your event is starting in 30 minutes'

        message = {}
        message['payload'] = {
            'title': str(community_name),
            'sub_title': sub_title,
            'route': 'route://community_collabcard?community_id=' + str(
                      community_id) + '&community_name=' + str(community_name) + '&community_state=' + str(kwargs['community_state']),
        }

        send_notification_to_multiple_devices(token_list, message)
        # disable the task , to prevent it from trigerring in future
        beat_task = CeleryBeatTask()
        beat_task.stop_task(task_name=kwargs['task_name'])

    except:
        print("Error while connecting to PostgreSQL")


@shared_task
def send_notification_to_event_co_hosts(co_hosts,card_id,event_title,event_creater):

    '''function to send notification to co-hosts'''

    notification_list=[]

    for host in co_hosts:
        temp={}
        notification_details = get_token_for_fcm(host,flag=True)
        temp['id'] = host
        temp['fcm_token'] = notification_details[0]
        temp['mobile_os'] = notification_details[1]
        notification_list.append(temp)

    message={}
    message['payload']={
        "title" : event_creater +" made you co-host of this event",
        "sub_title" : event_title,
        "route":"route://collabcard?collabcard_id="+str(card_id)
    }
    # print(notification_list)
    # print(message)
    notification_meta(notification_list,message)





@shared_task
def send_notification_to_proposed_admin(nominated_admin_id,community_id,proposed_admin_name):
    '''function to send notification to proposed admin'''

    fcm_token=get_token_for_fcm(nominated_admin_id)

    if fcm_token:
        token_list=[]
        token_list.append(fcm_token)
        community_name = get_community_name(community_id)
        message = {}
        message['payload'] = {
            'title': str(community_name),
            'sub_title': str(proposed_admin_name) + " has nominated you as a promoter of this community ",
            'route': 'route://community?community_id=' + str(community_id)
        }

        send_notification_to_multiple_devices(token_list, message)


@shared_task
def send_notification_to_proposer(proposer_id,community_name,community_id,proposed_name):

    '''function to send notification if the proposed admin accepts invitation'''

    fcm_token=get_token_for_fcm(proposer_id)

    if fcm_token:
        token_list=[]
        token_list.append(fcm_token)

        message={}
        message['payload']={
            'title':str(community_name),
            'sub_title':str(proposed_name) + " is now a promoter of the community",
            'route':'route://community?community_id=' + str(community_id)
        }

        send_notification_to_multiple_devices(token_list, message)
    else:
        print('No FCM token to send message')


@shared_task
def send_notification_to_eligible_member(eligible_member_id,community_name,community_id):

    '''function to send notification to eligible promoter
     after he becomes eligible to become admin to a community'''

    fcm_token=get_token_for_fcm(eligible_member_id)
    if fcm_token:
        token_list=[]
        token_list.append(fcm_token)

        message={}
        message['payload']={
            'title':str(community_name),
            'sub_title':"You are now eligible to become a promoter of this community",
            'route':'route://community?community_id=' + str(community_id)
        }
        send_notification_to_multiple_devices(token_list, message)
    else:
        print('No FCM token to send message')


@shared_task
def send_notification_to_referred_member(referred_member_id,joined_member_name,community_name,community_id,referal_count):

    '''function to send notification to referred member(who is referring)'''
    fcm_token=get_token_for_fcm(referred_member_id)

    if fcm_token:
        token_list=[]
        token_list.append(fcm_token)
        if referal_count == 1:

            sub_title =  str(joined_member_name) + " has shown interest to join. You have referred "+ str(referal_count) +" member to the community"
        elif referal_count > 1:
            sub_title =  str(joined_member_name) + " has shown interest to join. You have referred "+ str(referal_count) +" members to the community"

        message={}
        message['payload']={
            'title':str(community_name),
            'sub_title':sub_title,
            'route':'route://community?community_id=' + str(community_id)
        }
        send_notification_to_multiple_devices(token_list, message)
    else:
        print('No FCM token to send message')


@shared_task
def send_notification_to_referred_member_in_active_community(referred_member_id,joined_member_name,community_name,community_id,referal_count):

    '''function to send notification to referred member(who is referring)'''
    fcm_token=get_token_for_fcm(referred_member_id)

    if fcm_token:
        token_list=[]
        token_list.append(fcm_token)
        if referal_count == 1:
            sub_title =  str(joined_member_name) + " has joined this community. You have referred "+ str(referal_count) +" member to the community"
        elif referal_count > 1:
            sub_title =  str(joined_member_name) + " has joined this community. You have referred "+ str(referal_count) +" members to the community"

        message={}
        message['payload']={
            'title':str(community_name),
            'sub_title':sub_title,
            'route':'route://community?community_id=' + str(community_id)
        }
        send_notification_to_multiple_devices(token_list, message)
    else:
        print('No FCM token to send message')


@shared_task
def send_notification_to_all_admins(community_id,name,current_promoter_id):
    '''function to send notification to community admins'''
    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="select member_id_id from togther_members where community_id_id= " + str(community_id) + " and (state=1 or state=2)"
        curr.execute(sql)
        admins=curr.fetchall()
        token_list=[]
        for admin in admins:
            if str(current_promoter_id) != str(admin[0]):
                fcm_token=get_token_for_fcm(admin[0])
                token_list.append((fcm_token))

        community_name=get_community_name(community_id)
        message={}
        message['payload']={
            'title':community_name,
            'sub_title':str(name)+' is also a promoter now',
            'route':'route://community?community_id=' + str(community_id)
        }
        send_notification_to_multiple_devices(token_list,message)
        curr.close()
        connection.close()
    except (Exception, psycopg2.Error) as error:

        print ("Error while connecting to PostgreSQL", error)





@shared_task
def notification_after_compute_rank(user_id):

    '''function to send notification to referred member(who is referring)'''
    time.sleep(30)
    fcm_token=get_token_for_fcm(user_id)

    if fcm_token:
        token_list=[]
        token_list.append(fcm_token)
        #
        # user = User.objects.get(pk = user_id)
        # user_name = user.userinfo.name

        sub_title = "Discover and join relevant communities based on your profile"

        message={}
        message['payload']={
            'title':'Discover communities',
            'sub_title':sub_title,
            'route':'route://main'
        }

        count = 0
        while True:
            communities = Community_Rank.objects.filter(member_id=user_id)
            if communities.exists():
                return send_notification_to_multiple_devices(token_list, message)
            elif count == 30:
                return
            else:
                count += 1
                time.sleep(60)

    else:
        print('No FCM token to send message')

@shared_task
def notification_to_complete_onboarding(user_id):

    '''function to send notification when the user has not completed onboarding in 5 minutes'''

    fcm_token = get_token_for_fcm(user_id)

    if fcm_token:
        token_list = []
        token_list.append(fcm_token)
        message = {}
        message['payload'] = {
            'title': 'Complete your registration',
            'sub_title': """and discover relevant communities""",
            'route': 'route://main'
        }

        send_notification_to_multiple_devices(token_list,message)
        print("notification send when user has not completed onbaording in 5 minutes")




def send_poll_notification_manually(request):
    body = json.loads(request.body)

    community_id = body['community_id']
    community = Community.objects.get(pk=community_id)
    community_name = community.name
    community_state = community.hide_community
    card_id = body['card_id']

    card = Collabcard.objects.get(pk = card_id)
    typ = card.type

    poll_expiry_or_event_remainder_notification(community_name, community_id, typ,
                                                community_state=community_state, card_id=card_id)
    return JsonResponse({'success':True})
#toots unlocked



@shared_task
def send_notification_for_tool_unlocked_for_live_community(referer_id,referal_count, community_id, community_name,community_state):

    '''function to send notification for tool unlocked'''

    sub_title = ""
    route = 'route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(
            community_name) + '&community_state=' + str(community_state)
    print("refererid--",referer_id)

    if referal_count == 1:
        sub_title = "Event tool unlocked. You have successfully referred 1 member"
        notification_list = []
        temp = {}
        temp['user_id'] = referer_id
        notification_details = get_token_for_fcm(referer_id, True)
        temp['fcm_token'] = notification_details[0]
        temp['mobile_os'] = notification_details[1]
        notification_list.append(temp)

        message = {}
        message['payload'] = {
            'title': community_name,
            'sub_title': sub_title,
            'route': route
        }

        notification_meta(notification_list, message)

    elif referal_count == 3:
        sub_title = "Pool tool unlocked. You have successfully referred 3 member."
        notification_list = []
        temp = {}
        temp['user_id'] = referer_id
        notification_details = get_token_for_fcm(referer_id, True)
        temp['fcm_token'] = notification_details[0]
        temp['mobile_os'] = notification_details[1]
        notification_list.append(temp)

        message = {}
        message['payload'] = {
            'title': community_name,
            'sub_title': sub_title,
            'route': route
        }
        notification_meta(notification_list, message)

    elif referal_count == 5:
        sub_title = " Congrats. You are now promoter of this community."
        notification_list = []
        temp = {}
        temp['user_id'] = referer_id
        notification_details = get_token_for_fcm(referer_id, True)
        temp['fcm_token'] = notification_details[0]
        temp['mobile_os'] = notification_details[1]
        notification_list.append(temp)

        message = {}
        message['payload'] = {
            'title': community_name,
            'sub_title': sub_title,
            'route': route
        }
        notification_meta(notification_list, message)



@shared_task
def send_notification_for_tool_unlocked_for_pilot(community_id):
    '''function to send notification when the community is pilot and becomes live'''

    members_list=Members.objects.filter(community_id=community_id).filter(Q(state=member_states.ADMIN)|Q(state=member_states.MEMBER))
    community_instance=Community.objects.get(id=community_id)
    print("Send Notification for tool unlocked")
    for member in members_list:

        referal_count=get_referred_members_of_a_member(community_id,member.member_id.id)
        referal_count=len(referal_count)

        if referal_count >= 3:

            send_notification_for_tool_unlocked_for_live_community(referer_id=member.member_id.id,
                                                               referal_count=1,community_id=community_id,
                                                               community_name=community_instance.name,
                                                               community_state=community_instance.hide_community
                                                               )

            send_notification_for_tool_unlocked_for_live_community(referer_id=member.member_id.id,
                                                                   referal_count=3,
                                                                   community_id=community_id,
                                                                   community_name=community_instance.name,
                                                                   community_state=community_instance.hide_community
                                                                   )
        elif referal_count >= 1:


            send_notification_for_tool_unlocked_for_live_community(referer_id=member.member_id.id,
                                                                   referal_count=1, community_id=community_id,
                                                                   community_name=community_instance.name,
                                                                   community_state=community_instance.hide_community
                                                                   )


#Ig notifications


@shared_task
def send_notification_to_promoter_of_ig_community(community_id,community_name,member_id):

   '''function to send notification for the promoter of IG communities'''

   notification_list = []

   temp = {}
   temp['user_id'] = member_id
   notification_details = get_token_for_fcm(member_id, True)
   temp['fcm_token'] = notification_details[0]
   temp['mobile_os'] = notification_details[1]

   notification_list.append(temp)

   message = {}
   message['payload'] = {
       'title': str(community_name),
       'sub_title': "You are now promoter of this community.",
       'route': 'route://community?community_id=' + str(community_id)
   }


   notification_meta(notification_list, message)




@shared_task
def send_notification_to_referrer_of_ig_community(community_id,community_name,referrer_id,
                                                  member_name,community_state):

    '''function to send notification to the referrer of ig community'''

    notification_list = []

    temp = {}
    temp['user_id'] = referrer_id
    notification_details = get_token_for_fcm(referrer_id, True)
    temp['fcm_token'] = notification_details[0]
    temp['mobile_os'] = notification_details[1]

    notification_list.append(temp)

    message = {}
    message['payload'] = {
        'title': str(community_name),
        'sub_title': """%s just joined this community."""%(member_name),
        'route':'route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(
            community_name) + '&community_state=' + str(community_state)
    }

    notification_meta(notification_list, message)






#LG notifications
@shared_task
def send_notification_to_referrer_of_lg_community(community_id,community_name,referrer_id,
                                                  member_name,community_state,is_verified=False):

    '''function to send notification to the referrer of ig community'''

    notification_list = []

    temp = {}
    temp['user_id'] = referrer_id
    notification_details = get_token_for_fcm(referrer_id, True)
    temp['fcm_token'] = notification_details[0]
    temp['mobile_os'] = notification_details[1]

    notification_list.append(temp)
    if not is_verified:
        sub_title="""%s has shown interest to join."""%(member_name)
    else:
        sub_title = """%s has shown interest to join. Please verify""" % (member_name)

    message = {}
    message['payload'] = {
        'title': str(community_name),
        'sub_title': sub_title,
        'route':'route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(
            community_name) + '&community_state=' + str(community_state)
    }

    notification_meta(notification_list, message)




@shared_task
def ask_approval_notification(community_id,community_name,approver_id,
                                                  member_name,community_state):

    '''function to send notification for ask approval'''

    notification_list = []

    temp = {}
    temp['user_id'] = approver_id
    notification_details = get_token_for_fcm(approver_id, True)
    temp['fcm_token'] = notification_details[0]
    temp['mobile_os'] = notification_details[1]

    notification_list.append(temp)

    message = {}
    message['payload'] = {
        'title': str(community_name),
        'sub_title': """%s has requested to join your community."""%(member_name),
        'route':'route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(
            community_name) + '&community_state=' + str(community_state)
    }

    notification_meta(notification_list, message)




#utility functions
def get_referred_members_of_a_member(community_id,member_id):

    community = get_object_or_404(Community, pk=community_id)
    referred_member = User.objects.get(pk=member_id)

    member_list=[]
    total_referals = Referal.objects.filter(member=referred_member, community=community)

    if total_referals.exists():
        for interested_member in total_referals:
            mem_id=interested_member.invited_member.id
            member = Members.objects.filter(member_id=mem_id, community_id=community_id)
            if member.exists():
                if member[0].state == 4:
                    member_list.append(member[0].member_id.id)

    return member_list





