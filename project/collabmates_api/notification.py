from __future__ import absolute_import, unicode_literals
from celery import shared_task
import psycopg2
from pyfcm import FCMNotification
from django.conf import  settings
import time
from togther.models import (Community_Rank, collabcardState,
                            MemberPollVotes, Collabcard,
                            )
from django.contrib.auth.models import User

from utility.states import *
import re
from django.db.models import Q
from utility.celery_beat_tasks import CeleryBeatTask
# file to store configuration of the system


# database details
db_user=settings.DATABASES['default']['USER']
db_password=settings.DATABASES['default']['PASSWORD']
db_host=settings.DB_HOST
db_port=settings.DATABASES['default']['PORT']
db_database=settings.DATABASES['default']['NAME']


url=settings.URL

#server keys for sending notification
if url == "https://beta.collabmates.com":
    server_key='AAAA5QiC06o:APA91bGK2e3Y9r2g5VXnJIwK7OJ8pliwpXs_cwayEJ2D32Dfn5TcXpiUJDJNw7w-NqSdUH93FrX5xFie8KfpQORigfSuNlDVXxgi1nt9FcB7y5e5f0428jRKX35vti3R-BhxzMc9yrj_'
else:
    server_key = 'AAAAllezPSk:APA91bEYRnVqZGMS_YNTDwu4wJfQfbubN7jQtwvdAyZI6XvoRIjQPii9kj2joizPGJ8GhcoXpcIF5ftsZ-zyBuY9WzqS48b2JCZ51Lv8K9L56gMwBjLsW7tDSfntEqMtAQ9f8f024M5P'



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


def get_token_for_fcm(member_id):

    '''function to get token from user'''
    try:
        conn = get_connection()
        curr = conn.cursor()

        curr.execute("select fcm_token from togther_userinfo where user_id_id=" + str(member_id))
        fcm_token = curr.fetchone()
        if fcm_token:
            return fcm_token[0]

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
        print(sql)
        mobile_os = curr.fetchone()
        if mobile_os:
            print(mobile_os[0])
            if mobile_os[0] == "Android":
                print("Android")
                return True
            elif mobile_os[0] == "iOS":
                print("iOS")
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


@shared_task
def send_follow_notification(card_id,user_id,answer):

    '''function to send notification to followed members'''

    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="select user_id from togther_collabcardstate where card_id=%s and state=%s"
        parameter_list=[card_id, collabcard_follow_state]
        curr.execute(sql,parameter_list)
        member_list=curr.fetchall()
        curr.execute("select name from togther_userinfo where user_id_id=%s",[user_id])
        answerer_name=curr.fetchone()
        curr.close()
        connection.close()
        message={}

        tagged_users_list = re.findall("route://member/"'([0-9]+)', answer)
        answer_text = re.split('>>', answer)[-1]

        user_names="@"+' @'.join(re.findall('(?<=\<\<).+?(?=\|)', answer))

        message['payload']={
            "title":str(answerer_name[0]) + " responded",
            "sub_title":answer_text,
            "route":"route://collabcard?collabcard_id="+str(card_id)
        }
        token_list=[]

        for member in member_list:
            if str(member[0]) != user_id and str(member[0]) not in tagged_users_list:
                fcm_token = get_token_for_fcm(member[0])
                token_list.append(fcm_token)
        send_notification_to_multiple_devices(token_list,message)

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
        token_list=[]
        fcm_token=get_token_for_fcm(user_id)
        token_list.append(fcm_token)

        send_notification_to_multiple_devices(token_list,message)

    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting to PostgreSQL", error)


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
            'sub_title':str(name)+' has requested to join your community',
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
    fcm_token=get_token_for_fcm(member_id)
    token_list=[]
    token_list.append(fcm_token)
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
            'sub_title': "Sorry! your request to join this community has been rejected",
            'route': 'route://member_declined?community_id=' + str(community_id)
        }

    send_notification_to_multiple_devices(token_list,message)



# notifications for new collabcards

@shared_task
def send_notification_for_new_collabcard_posted(community_id, collabcard_title,
                                                card_creater_id, card_creater_name, **kwargs):
    '''function to send notification to all members when new collabcard is posted'''
    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="select member_id_id from togther_members where community_id_id=%s and member_id_id !=%s and (state=1 or state=2 or state=4 or state=7)"
        parameter_list=[community_id,card_creater_id]
        curr.execute(sql,parameter_list)
        member_list=curr.fetchall()

        token_list=[]
        for member in member_list:
            token=get_token_for_fcm(member[0])
            token_list.append(token)
        community_name=get_community_name(community_id)
        message={}
        typ = kwargs['type'] if 'type' in kwargs else 0
        if typ == 2:
            sub_title = "Posted an event: "+str(collabcard_title)
        elif typ == 3:
            sub_title = "Posted a poll: "+ str(collabcard_title)
        else:
            sub_title = str(collabcard_title)


        message['payload']={
            'title': str(card_creater_name) + " @ "+str(community_name),
            'sub_title': sub_title,
            'route': 'route://community_collabcard?community_id=' + str(community_id) + '&community_name='+ str(community_name)
        }

        send_notification_to_multiple_devices(token_list,message)

        if typ == 2 or typ == 3:
            task_name = 'poll_with_id_' + str(kwargs['card_id']) if typ == 3 else 'event_with_id_' + str(kwargs['card_id'])
            task_path = 'collabmates_api.notification.poll_expiry_or_event_remainder_notification'
            task_name, task_path = task_name, task_path
            if task_name and task_path:
                celerybeatask = CeleryBeatTask()
                args = [community_name, community_id, typ]

                date_time = int(kwargs['date_time']//1000) if isinstance(kwargs['date_time'], int)\
                                else kwargs['date_time'][:10] if isinstance(kwargs['date_time'], str)\
                                else int(str(kwargs['date_time'])[:10])

                date_time = (date_time-1800) if typ == 2 else date_time
                celerybeatask.get_or_create_new_beat_task(card_creater_id=card_creater_id,
                                                          card_creater_name=card_creater_name,
                                                          args=args, task_name=task_name, task_path=task_path,
                                                          date_time=date_time, interval=False, crontab=True,
                                                          collabcard_title=collabcard_title,
                                                          card_id=kwargs['card_id'])


    except (Exception, psycopg2.Error) as error:

        print("Error while connecting to PostgreSQL", error)



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
        sub_title = member_name + " is attending you event"
        time.sleep(60)
        attending_state = collabcardState.objects.filter(card=card, user=member).filter(Q(state=3) | Q(state=4))
        if not attending_state.exists():
            return
    else:
        sub_title = member_name + " voted on your poll"
    message = {}
    message['payload'] = {
        'title': str(community_name),
        'sub_title': sub_title,
        'route': 'route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(
            community_name)
    }

    token_list = [card_creator_fcm_token]

    send_notification_to_multiple_devices(token_list, message)



@shared_task
def poll_expiry_or_event_remainder_notification(community_name, community_id, typ, **kwargs):

    """ function to send notification to all members when event/poll is going to start/end """
    try:

        if typ == 2:
            token_list = list(collabcardState.objects.filter(card=kwargs['card_id']).filter(
                                 Q(state=3) |
                                 Q(state=4)).values_list('user__userinfo__fcm_token', flat=True))

        else:
            token_list = list(MemberPollVotes.objects.filter(card=kwargs[
                                                                'card_id']).order_by('-id').values_list(
                                                                'user__userinfo__fcm_token', flat=True))
            print("token list ===== ", token_list)


        community_name = community_name

        if typ == 3:
            sub_title = 'your poll ended. Tap to see results'
        else:
            sub_title = 'your event is starting in 30 minutes'

        message = {}
        message['payload'] = {
            'title': str(community_name),
            'sub_title': sub_title,
            'route': 'route://community_collabcard?community_id=' + str(
                      community_id) + '&community_name=' + str(community_name),
        }

        send_notification_to_multiple_devices(token_list, message)

    except:

        print("Error while connecting to PostgreSQL")
