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
                            MemberPollVotes, Collabcard,Members,Members,Referal,Community,communityAnswers,
                            Userinfo,communityLevels,communityExpiryCodes,conversationEngage,card_answers,
                            conversationMemberState, memberRights, adminRights, userAdminRights, userMemberRights,
                            moderationHistory, Report, Report_Tags, communityRightsSettings, blockedMembers,userDevices)

from utility.states import (member_states, manager_rights, member_rights, moderation_history_types,
                           )

from utility.utils import *
from utility.celery_beat_tasks import CeleryBeatTask
from project.celery import app
from utility.states import *

import json
from django.shortcuts import get_object_or_404
import traceback

from datetime import datetime,timedelta
from .serializers import get_answer_files, get_collabcard_files
# file to store configuration of the system


# database details
db_user=settings.DATABASES['default']['USER']
db_password=settings.DATABASES['default']['PASSWORD']
db_host=settings.DATABASES['default']['HOST']
db_port=settings.DATABASES['default']['PORT']
db_database=settings.DATABASES['default']['NAME']


url=settings.URL

#server keys for sending notification
server_key=settings.FCM_SERVER_KEY

#notifications for different mobile os versions
def send_test_notification(token_list,message):
    result = ""
    message = {}
    # message['payload']={
    #     'title': 'title',
    #     'sub_title': 'sub_title',
    #     'route': 'route://community?community_id=49016'
    # }
    # message['payload']['sub_title'] = sub_titlee
    push_service = FCMNotification(api_key=server_key)
    result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                  data_message=message['payload'])
    print(result)

    
def send_notification_for_android(token_list,message):
    '''function to send notification to android'''
    # print(token_list,message)
    result=""
    # print("===== sending for android")
    push_service = FCMNotification(api_key=server_key)
    result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                  data_message=message['payload'])

    print(result)
   

def send_notification_for_ios(token_list, message):

    '''function to send notification to android'''



    result = ""
    push_service = FCMNotification(api_key=server_key)

    extra_kwargs = {
        "mutable_content": True
    }

    result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                  message_title=message['payload']['title'],
                                                  message_body=message['payload']['sub_title'],
                                                  data_message=message['payload'],
                                                  extra_kwargs=extra_kwargs)

    print(result)


def get_title_from_collabcard(card):
    ''' To extract the title from a card. '''
    if card.header:
        return card.header
    else:
        return card.title[:30]


def get_devices_of_users(user_id):

    '''function to get all devices of users'''

    devices_filter  = userDevices.objects.filter(user=user_id)
    user_devices = []

    for device in devices_filter:
        temp = {}
        temp['id'] = device.user.id
        temp['fcm_token'] = device.fcm_token
        temp['mobile_os'] = device.mobile_os
        user_devices.append(temp)

    return user_devices



def notification_meta(notification_list,message,calling_notification=""):
    # print(notification_list,message)
    '''function to process notification to send'''

    for data in notification_list:

        if 'id' in data:
            user_id = data['id']
        else:
            continue

        user_devices = get_devices_of_users(user_id)

        for device in user_devices:
            if device['mobile_os'] == "Android":
                token_list = [device['fcm_token']]
                send_notification_for_android(token_list, message)
            elif device['mobile_os'] == 'iOS':
                token_list = [device['fcm_token']]
                if 'message' in data:
                    send_notification_for_ios(token_list, data['message'])
                else:
                    send_notification_for_ios(token_list,message)



    # for data in notification_list:
    #     if data['fcm_token']:
    #         if data['mobile_os'] == "Android":
    #             token_list_android.append(data['fcm_token'])
    #         else:
    #             token_list_ios.append(data['fcm_token'])
    #             #functionalities for iOS flow
    #             if 'message' in data:
    #                 send_notification_for_ios(token_list_ios, data['message'])
    #             else:
    #                 send_notification_for_ios(token_list_ios,message)
    #             token_list_ios = []
    #
    #         #print(data)
    #
    # if token_list_android:
    #     send_notification_for_android(token_list_android,message)

    # if token_list_ios:
    #     send_notification_for_ios(token_list_ios,message)




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
    answer_text = re.sub(r'\|route://member/[0-9]+>>|<<', '', answer)

    tagged_user_names = "@" + ' @'.join(re.findall('(?<=\<\<).+?(?=\|)', answer))
    
    return tagged_users_list, answer_text, tagged_user_names

    # return {"tagged_users_list":tagged_users_list, "answer_text":answer_text, "tagged_user_names":tagged_user_names}


@shared_task
def send_notification_to_admins(community_id,name):
    '''function to send notification to community admins'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = "select member_id_id from togther_members where community_id_id= " + str(community_id) + " and (state=1 or state=2)"
        curr.execute(sql)
        admins = curr.fetchall()
        notification_list =  []

        eligible_admin_ids = list(userAdminRights.objects.filter(community=community_id,
                         right__state=manager_rights.MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS).values_list("user__id",
                                                                                                       flat=True))
        for admin in admins:
            temp = {}
            promoter_id = admin[0]
            if promoter_id in eligible_admin_ids:
                notification_details = get_token_for_fcm(promoter_id, True)
                if notification_details:
                    temp['id'] = promoter_id
                    temp['fcm_token'] = notification_details[0]
                    temp['mobile_os'] = notification_details[1]

                notification_list.append(temp)

        community_name = get_community_name(community_id)
        message = {}
        message['payload'] = {
            'title': community_name,
            'sub_title': str(name)+' has requested to join your community',
            'route': 'route://member_approve?'+'community_id=' + str(community_id) + "&" + "community_name=" + str(community_name)
        }

        notification_meta(notification_list, message)

        #send_notification_to_multiple_devices(token_list,message)
        curr.close()
        connection.close()
    except (Exception, psycopg2.Error) as error:

        print ("Error while connecting to PostgreSQL", error)

@shared_task
def send_notification_for_join_requests(community_id,flag,member_id,promoter_name=""):
    '''function to send notification for approval or denial'''
    community_name=get_community_name(community_id)
    temp = {}
    notification_list=[]
    temp['id'] = member_id
    notification_details = get_token_for_fcm(member_id, True)
    temp['fcm_token'] = notification_details[0]
    temp['mobile_os'] = notification_details[1]

    notification_list.append(temp)

    message={}
    if flag:
        if promoter_name != "":
            message['payload']={
                'title':"Membership approved!",
                'sub_title':"Congratulations, " + promoter_name + " has accepted your request to join " + community_name,
                'route':'//route://community_collabcard?community_id='+ str(community_id) +'&community_name=' + str(community_name)
            }
        else:
            message['payload']={
                'title':"Membership approved!",
                'sub_title':"Congratulations, you are now part of the " + community_name + " community",
                'route':'//route://community_collabcard?community_id='+ str(community_id) +'&community_name=' + str(community_name)

            }
        notification_meta(notification_list,message)
    # else:
    #     message['payload'] = {
    #         'title': community_name,
    #         'sub_title': "Your request to join this community has been rejected",
    #         'route': 'route://member_declined?community_id=' + str(community_id)
    #     }

    # notification_meta(notification_list,message)

@shared_task
def send_notification_to_new_promoter(context):

    promoter_id = context['nominated_admin']
    community_id = context['community_id']
    admin_name = context['admin']
    notification_list = []
    try:
        temp = {}
        notification_details = get_token_for_fcm(promoter_id, True)
        if notification_details:
            temp['id'] = promoter_id
            temp['fcm_token'] = notification_details[0]
            temp['mobile_os'] = notification_details[1]

            notification_list.append(temp)
            community_name = get_community_name(community_id)

            message = {}
            message['payload'] = {
                'title': community_name,
                'sub_title': str(admin_name) + " has added you as promoter of the community.",
                'route':'route://community?community_id=' + str(community_id)
            }

            notification_meta(notification_list, message)


    except (Exception, psycopg2.Error) as error:
        traceback.print_exc()
        print("Error while connecting to PostgreSQL", error)




# notifications for new collabcards

@shared_task
def send_notification_for_new_collabcard_posted(community_id, collabcard_title, card_creater_id, card_creater_name,
                                            **kwargs):
    '''function to send notification to all members when new collabcard is posted'''

    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = "select member_id_id, state from togther_members where community_id_id=%s and member_id_id !=%s and (state=1 or state=4 or state=9) "
        parameter_list = [community_id, card_creater_id]
        curr.execute(sql, parameter_list)
        member_list = curr.fetchall()

        card_id = kwargs['card_id']
        card = Collabcard.objects.get(id=card_id)

        notification_list_member = []

        tagged_users_list, collabcard_title, user_names = get_tagged_members_list(collabcard_title)

        blocked_by_user_list = list(blockedMembers.objects.filter(community=community_id,
                                                                  blocked_member=card_creater_id).values_list(
                                                                  "blocked_by__id", flat=True))
        eligible_admin_ids = []
        if card.is_pending:
            eligible_admin_ids = list(userAdminRights.objects.filter(community=community_id,
                                      right__state=manager_rights.MANAGER_RIGHT_DELETE_ROOMS).values_list(
                                      "user__id", flat=True))

        # print(member_list)
        for member in member_list:
            member_id = member[0]
            member_state = member[1]
            if card.is_pending:
                if member_state != member_states.ADMIN:
                    continue
                elif member_id not in eligible_admin_ids:
                    continue

            temp = {}
            temp['id'] = member_id
            notification_details = get_token_for_fcm(member[0], True)
            temp['fcm_token'] = notification_details[0]
            temp['mobile_os'] = notification_details[1]
            if str(member[0]) not in tagged_users_list and int(member[0]) not in blocked_by_user_list:
                notification_list_member.append(temp)

        custom_payload = get_custom_data_for_new_chatroom_created(card)
        
        collabcard_title = get_title_from_collabcard(card)

        community_name = kwargs['community_name']
        message = {}
        typ = kwargs['type'] if 'type' in kwargs else 0

        if card.is_pending:
            title = community_name
            sub_title = str(card_creater_name) + " has created a new chat room " + str(collabcard_title)
            route = 'route://chatroom_detail?chatroom_id=' + str(kwargs['card_id'])
        elif typ == 2:
            title = community_name
            sub_title = str(card_creater_name) + " created a new event: " + str(collabcard_title) + ". Join now!"
            route = 'route://collabcard?collabcard_id='+str(kwargs['card_id'])
        elif typ == 3:
            title = "Time to vote!"
            sub_title = str(card_creater_name) + " started a poll on " + str(collabcard_title) + " in " + community_name
            route = 'route://poll_chatroom?chatroom_id='+str(kwargs['card_id'])
        else:
            title = community_name
            sub_title = str(card_creater_name) + " started a new chatroom: " + str(collabcard_title) + ". Join now!"
            route = 'route://collabcard?collabcard_id='+str(kwargs['card_id'])

        message['payload'] = {
            # 'title': str(card_creater_name) + " @ " + str(community_name),
            'title': title,
            'sub_title': sub_title,
            'route': route
        }
        # message['payload']['unread_new_chatroom'] = {}
        if not card.is_pending:
            if typ not in [2, 3]:
                message['payload']['unread_new_chatroom'] = custom_payload

        notification_meta(notification_list_member, message)

        if not card.is_pending:
            # functionality to send notification to tagged users
            new_title_text = re.sub(r'\|route://member/[0-9]+>>|<<', '', card.title)
            for member_id in tagged_users_list:
                if not str(member_id) == str(card_creater_id):

                    send_notification_to_tagged_users(card_id=kwargs['card_id'],
                                                      answerer_name=card_creater_name,
                                                      answer=new_title_text,
                                                      user_id=member_id, user_names=user_names)


    except (Exception, psycopg2.Error) as error:

        print("Error while connecting to PostgreSQL", error)


def get_custom_data_for_new_chatroom_created(card):

    """ function to get data for custom notification """

    unread_conversation = {}
    chatroom_instance = card
    user_instance = chatroom_instance.user
    unread_conversation['community_name'] = chatroom_instance.community.name
    unread_conversation['chatroom_name'] = get_title_from_collabcard(chatroom_instance)+" (New Chatroom)"
    unread_conversation['chatroom_title'] = chatroom_instance.title
    unread_conversation['chatroom_user_name'] = user_instance.userinfo.name

    collabcard_files = get_collabcard_files(card_id=card.id)
    unread_conversation['images'] = collabcard_files[0]
    unread_conversation['pdf'] = collabcard_files[1]

    chatroom_user_image = user_instance.userinfo.image_link
    unread_conversation['chatroom_user_image'] = chatroom_user_image if chatroom_user_image else ''
    unread_conversation['chatroom_id'] = chatroom_instance.id
    unread_conversation['community_id'] = str(chatroom_instance.community.id)
    unread_conversation['community_image'] = chatroom_instance.community.image_link
    #unread_conversation['notification_id'] = str(chatroom_instance.id)+"_new"
    unread_conversation['route'] = """route://chatroom_new_feed?community_id=%s&community_name=%s"""%(str(chatroom_instance.community.id),str(chatroom_instance.community.name))
    unread_conversation['route_child'] = """route://collabcard?collabcard_id=%s"""%(str(chatroom_instance.id))
    unread_conversation['chatroom_name_ios'] = get_title_from_collabcard(chatroom_instance)

    print(">>>>>>>>>   ", unread_conversation)

    return unread_conversation


@shared_task
def send_follow_notification(card_id,user_id,answer):

    '''function to send notification to followed members who have responded or follow'''


    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="select user_id from togther_collabcardstate where card_id=%s and follow_status = True and remove_id is null and mute_status = False"
        parameter_list=[card_id]
        curr.execute(sql,parameter_list)
        member_list=curr.fetchall()
        curr.execute("select name from togther_userinfo where user_id_id=%s",[user_id])
        answerer_name=curr.fetchone()
        curr.close()
        connection.close()
        message={}

        card = Collabcard.objects.get(id=card_id)
        # tagged_users_list = re.findall("route://member/"'([0-9]+)', answer)
        # answer_text = re.split('>>', answer)[-1]
        #
        # user_names="@"+' @'.join(re.findall('(?<=\<\<).+?(?=\|)', answer))

        tagged_users_list, answer_text, user_names = get_tagged_members_list(answer)

        #in case of images/document, show following in the notification
        if answer_text == "":
            answer_text = '📄 Document'


        #unread_conversation = get_custom_data_for_new_conversation_created(user_id)

        message['payload']={
            "title":str(get_title_from_collabcard(card)),
            "sub_title":str(answerer_name[0])+": "+answer_text,
            "route":"route://collabcard?collabcard_id="+str(card_id)

        }
        # message['payload']={
        #     "title":str(answerer_name[0]) + " responded",
        #     "sub_title":answer_text,
        #     "route":"route://collabcard?collabcard_id="+str(card_id)
        # }

        notification_list=[]

        for member in member_list:
            if str(member[0]) != user_id and str(member[0]) not in tagged_users_list:
                temp={}
                notification_details = get_token_for_fcm(member[0],True)
                temp['id']=member[0]
                temp['fcm_token'] = notification_details[0]
                temp['mobile_os'] = notification_details[1]

                #if the user has a iOS device reqistered
                device_filter = userDevices.objects.filter(user=temp['id'],mobile_os='iOS')
                if device_filter.exists():
                    unread_followed_chatroom = get_custom_data_for_new_conversation_created_ios(temp['id'])
                    message['payload']['unread_followed_chatroom'] = unread_followed_chatroom
                    temp['message'] = message

                notification_list.append(temp)

        notification_meta(notification_list,message,calling_notification="send_follow_notification")



        #functionality to send notification to tagged users
        for member_id in tagged_users_list:
            if not str(member_id) == str(user_id):
                send_notification_to_tagged_users(card_id=card_id, answerer_name=answerer_name[0],
                                                  answer=answer_text,
                                                  user_id=member_id, user_names=user_names,chatroom_created=False)



    except (Exception, psycopg2.Error) as error:
        traceback.print_exc()
        print ("Error while connecting to PostgreSQL", error)


def get_custom_data_for_new_conversation_created(user_id):

    """function to send notification for new conversation posted to followed users"""

    # time.sleep(2)
    followed_chatrooms = conversationEngage.objects.filter(user_id=user_id,draft_id=None).order_by('-updated_at','-id')

    unread_conversation = []

    for conversation in followed_chatrooms:
        temp = {}

        if not conversation.unseen_count:
            continue
       
        state_filter = collabcardState.objects.filter(user=user_id,card=conversation.card)
        if state_filter.exists():
            mute_status = state_filter[0].mute_status
            if mute_status:
                continue

        chatroom_name = get_title_from_collabcard(conversation.card)

        if conversation.unseen_count > 1:
            chatroom_name = chatroom_name+""" (%s messages)"""%(str(conversation.unseen_count))

        temp['community_name'] = conversation.card.community.name
        temp['chatroom_name'] = chatroom_name
        temp['chatroom_title'] = conversation.card.title
        temp['chatroom_user_name'] = conversation.user.userinfo.name
        temp['chatroom_user_image'] = conversation.user.userinfo.image_link
        temp['chatroom_id'] = conversation.card.id

        if conversation.has_files:
            answer_files = get_answer_files(conversation.id)
            temp['images'] = answer_files['image']
            temp['pdf'] = answer_files['pdf']

        temp['notification_id'] = str(conversation.card.id)+"_followed"
        temp['route'] = """route://chatroom_followed_feed?community_id=%s&community_name=%s"""%(str(conversation.card.community.id),str(conversation.card.community.name))
        temp['chatroom_unread_conversation_count'] = conversation.unseen_count
        temp['community_id'] = str(conversation.card.community.id)
        temp['community_image'] = conversation.card.community.image_link
        temp['route_child'] = """route://collabcard?collabcard_id=%s""" % (str(conversation.card.id))

        last_conversation = ""
        last_instance = card_answers.objects.filter(card=conversation.card,state=0).last()
        if last_instance:
            last_conversation = last_instance.answer
            temp['chatroom_last_conversation'] = last_conversation
            temp['chatroom_last_conversation_user_name'] = last_instance.user.userinfo.name
            temp['chatroom_last_conversation_user_image'] = last_instance.user.userinfo.image_link
            temp['chatroom_last_conversation_timestamp'] = last_instance.created_at

        unread_conversation.append(temp)

    print(">>>>>>>>>   ", unread_conversation)

    return unread_conversation


def get_custom_data_for_new_conversation_created_ios(user_id):

    """ function to send custom data in case of ios """

    # time.sleep(2)
    followed_chatrooms = conversationEngage.objects.filter(user_id=user_id,draft_id=None).order_by('-updated_at','-id')

    temp = {}

    if followed_chatrooms.exists():

        conversation = followed_chatrooms[0]
        if not conversation.unseen_count:
            return {}

        chatroom_name = get_title_from_collabcard(conversation.card)

        # if conversation.unseen_count > 1:
        #     chatroom_name = chatroom_name+""" (%s messages)"""%(str(conversation.unseen_count))

        temp['community_name'] = conversation.card.community.name
        temp['chatroom_name'] = chatroom_name
        temp['chatroom_title'] = conversation.card.title
        temp['chatroom_user_name'] = conversation.user.userinfo.name
        temp['chatroom_user_image'] = conversation.user.userinfo.image_link
        temp['chatroom_id'] =  conversation.card.id
        temp['notification_id'] = str(conversation.card.id)+"_followed"

        if conversation.has_files:
            answer_files = get_answer_files(conversation.id)
            temp['images'] = answer_files['image']
            temp['pdf'] = answer_files['pdf']

        temp['route'] = """route://chatroom_followed_feed?community_id=%s&community_name=%s"""%(str(conversation.card.community.id),str(conversation.card.community.name))
        temp['chatroom_unread_conversation_count'] = conversation.unseen_count
        temp['community_id'] = str(conversation.card.community.id)
        temp['community_image'] = conversation.card.community.image_link

        #temp['unseen_conversation_count'] = conversation.unseen_count

        #sending names of unique members who have responded in chatroom

        card_instance  = conversation.card
        temp['last_conversation_unique_names'] = get_last_conversation_unique_names(card_instance,user_id)

        last_conversation = ""
        last_instance = card_answers.objects.filter(card=conversation.card,state=0).last()
        if last_instance:
            last_conversation = last_instance.answer
            temp['chatroom_last_conversation'] = last_conversation
            temp['chatroom_last_conversation_user_name'] = last_instance.user.userinfo.name
            temp['chatroom_last_conversation_user_image'] = last_instance.user.userinfo.image_link
            temp['chatroom_last_conversation_timestamp'] = last_instance.created_at

            temp['route_child'] = """route://collabcard?collabcard_id=%s&last_conversation_id=%s"""%(str(conversation.card.id),str(last_instance.id))
    print(">>>>>>>>>   ", temp)

    return temp


def get_last_conversation_unique_names(card_instance,user_id):

    '''function to get last conversation unique names'''

    name_set = set()
    name_list = []
    conversation_state_filter = conversationMemberState.objects.filter(card=card_instance,user=user_id)
    if conversation_state_filter.exists():
        last_conversation = conversation_state_filter[0].conversation

        answer_filter = card_answers.objects.filter(card=card_instance,state=0,id__gt=last_conversation.id).order_by('-id')
        for answer in answer_filter:

            if answer.user.id == user_id:
                continue
            if answer.user not in name_set:
                name_set.add(answer.user)
                name_list.append(answer.user.userinfo.name)

            if len(name_list) > 4:
                break
    else:
        answer_filter = card_answers.objects.filter(card=card_instance, state=0).order_by(
            '-id')
        for answer in answer_filter:
            if answer.user not in name_set:
                name_set.add(answer.user)
                name_list.append(answer.user.userinfo.name)

            if len(name_list) > 4:
                break

    return name_list



@shared_task
def send_notification_to_tagged_users(card_id,answerer_name,answer,user_id,user_names,chatroom_created = True):

    '''function to send notification to those users who didn't follow the collabcard but tagged in an answer'''

    try:

        message={}

        card = Collabcard.objects.get(id=card_id)



        message['payload']={
            "title":str(answerer_name) + " tagged you!",
            "sub_title":str(get_title_from_collabcard(card))+": "+answer,
            "route":"route://collabcard?collabcard_id="+str(card_id),
        }

        if chatroom_created:
            custom_payload = get_custom_data_for_new_chatroom_created(card)
            message['payload']['unread_new_chatroom'] = custom_payload




        notification_list = []
        temp = {}
        notification_details = get_token_for_fcm(user_id, True)
        temp['id'] = user_id
        temp['fcm_token'] = notification_details[0]
        temp['mobile_os'] = notification_details[1]

        device_filter = userDevices.objects.filter(user=temp['id'], mobile_os='iOS')

        if device_filter.exists() and chatroom_created == False:
            #case for send conversation message
            unread_followed_chatroom = get_custom_data_for_new_conversation_created_ios(user_id)
            message['payload']['unread_followed_chatroom'] = unread_followed_chatroom
            temp['message'] = message

        notification_list.append(temp)

        notification_meta(notification_list, message)


    except (Exception, psycopg2.Error) as error:
        traceback.print_exc()
        print ("Error while connecting to PostgreSQL", error)





@shared_task
def send_notification_to_event_co_hosts(co_hosts,card_id,event_title,event_creater):

    '''function to send notification to co-hosts'''

    notification_list=[]

    card = Collabcard.objects.get(id=card_id)
    
    community_name = str(card.community.name)
    
    for host in co_hosts:
        temp={}
        notification_details = get_token_for_fcm(host,flag=True)
        temp['id'] = host
        temp['fcm_token'] = notification_details[0]
        temp['mobile_os'] = notification_details[1]
        notification_list.append(temp)

    message={}
    # message['payload']={
    #     "title" : event_creater +" made you co-host of this event",
    #     "sub_title" : event_title,
    #     "route":"route://collabcard?collabcard_id="+str(card_id)
    # }
    # <<Harsh>> added you as a host for <<event name>> in <<community_name>>. View details
    message['payload']={
        "title" : "You are a co-host!",
        "sub_title" : event_creater + " added you as a host for "+event_title+" in "+ community_name,
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
       'sub_title': admin_name + "has added you as promoter of the community.",
       'route': 'route://community?community_id=' + str(community_id)
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


@shared_task
def send_notification_to_incomplete_profile(member_id,community_id,community_state,community_name,time_in_hrs):
    '''function to send notification to users who pressed skip when joining link was sent'''
    start_time = time.time()
    start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=time_in_hrs, days=0)
    task_name = str(community_id) + "_" + str(member_id) +"_send_notification_to_incomplete_profile"
    args = [member_id, community_id, community_state, community_name, time_in_hrs]
    task_path = "collabmates_api.notification.send_notification_to_incomplete_profile_scheduled"
    kwargs = {}
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)
    celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                            date_time=start_time, interval=False, crontab=True)

@app.task
def send_notification_to_incomplete_profile_scheduled(member_id, community_id, community_state, community_name, time_in_hrs):
    

    #check if they created the profile. 
    community_answers = communityAnswers.objects.filter(community_id=community_id,member_id=member_id)

    if community_answers.exists():
        pass

    else:
        notification_list=[]

        notification_details = get_token_for_fcm(member_id,flag=True)

        temp = {
            'id':member_id,
            'fcm_token':notification_details[0],
            'mobile_os':notification_details[1],
        }

        notification_list.append(temp)

        
        message={}
        
        message['payload']={
            "title" : "Complete your profile!",
            "sub_title" : "Get full access to "+ community_name,
            'route':'route://community?community_id=' + str(community_id)
        }
        notification_meta(notification_list,message)

@shared_task
def send_login_dropoff_notification(token,platform_code):
    '''send notification to users who did not login after 2 hour'''


    start_time = time.time()
    start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=2, days=0)
    task_name = str(token) + "_send_login_dropoff_notification"
    args = [token, platform_code]
    task_path = "collabmates_api.notification.send_login_dropoff_notification_scheduled"
    kwargs = {}
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)
    celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                            date_time=start_time, interval=False, crontab=True)


@app.task
def send_login_dropoff_notification_scheduled(token, platform_code):
    user = Userinfo.objects.filter(fcm_token=token)

    if user.exists():
        return
    else:
        temp = {
            'id':None,
            'fcm_token':token,
            'mobile_os':platform_code,
        }
        notification_list = []

        notification_list.append(temp)

        message = {}

        message['payload']={
                "title" : "Finish signing up!",
                "sub_title" : "Click here to sign up and meet like-minded people and have relevant conversations.",
            }
        notification_meta(notification_list,message)


@app.task
def send_morning_pending_request_notification():

    ''' send morning notification at 8 am '''
    print('sending notification')
    Members.objects.filter(community_id=49063,member_id=504).update(state=3)
    members = Members.objects.filter(state=member_states.PENDING_MEMBER)
    communities = []
    for member in members:
        if member.community_id not in communities:
            communities.append(member.community_id)
    
    # communities = Community.objects.filter(pk__in=)
    for community in communities:
        members = Members.objects.filter(community_id=community.id)
        
        pending_members = members.filter(state=member_states.PENDING_MEMBER)
        pending_members_count = pending_members.count()

        if pending_members_count>0:
            promoters = members.filter(state=member_states.ADMIN)
            notification_list = []
            for promoter in promoters:
                notification_details = get_token_for_fcm(promoter.member_id.id,flag=True)
                temp = {
                    'id':promoter.member_id.id,
                    'fcm_token':notification_details[0],
                    'mobile_os':notification_details[1],
                }

                notification_list.append(temp)

            message = {}

            message['payload']={
                    "title" : str(community.name),
                    "sub_title" : str(pending_members_count) + " members are awaiting your approval to join the community.",
                    'route':'route://member_approve?'+'community_id=' + str(community.id) + "&" + "community_name=" + str(community.name)

                }

            if pending_members_count == 1:
                message['payload']['sub_title']= "1 member is awaiting your approval to join the community."

            notification_meta(notification_list,message)


@app.task
def send_evening_level_notification():
    
    ''' send evening notification at 8 pm to ask them to level up'''

    community_levels = communityLevels.objects.filter(state = community_level_states.PENDING)
    for community_level in community_levels:
        members = Members.objects.filter(community_id=community_level.community.id,state=member_states.ADMIN)
        
        notification_list = []
        
        for member in members:
            notification_details = get_token_for_fcm(member.member_id.id,flag=True)
            temp = {
                'id':member.member_id.id,
                'fcm_token':notification_details[0],
                'mobile_os':notification_details[1],
            }

            notification_list.append(temp)

        message = {}

        message['payload']={
                "title" : 'Level up '+str(community_level.community.name),
                "sub_title" : str(community_level.title) + ". " +str(community_level.sub_title),
                'route':'route://community_collabcard?community_id='+str(community_level.community.id) + '&community_name=' + str(community_level.community.name) + '&show_level=true'
            }
        #todo
        notification_meta(notification_list,message)




@shared_task
def send_notification_to_join_drop_off(member_id,community_id,aj,time_in_hrs):

    '''function to send notification to users who opened the private link but did not joint the community'''
    start_time = time.time()
    start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=time_in_hrs, days=0)
    task_name = str(member_id) + "_" + str(community_id) + "_send_notification_to_join_drop_off"
    args = [member_id, community_id, aj, time_in_hrs]
    task_path = "collabmates_api.notification.send_notification_to_join_drop_off_scheduled"
    kwargs = {}
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)
    celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                            date_time=start_time, interval=False, crontab=True)






@app.task
def send_notification_to_join_drop_off_scheduled(member_id, community_id, aj, time_in_hrs):
    #check if they created the profile. 
    member = Members.objects.filter(community_id=community_id,member_id=member_id)
    
    if member.exists():
        pass

    else:
        user_instance = User.objects.get(pk=member_id)
        member_name = user_instance.userinfo.name
        community_instance = Community.objects.get(id=community_id)
        community_name = community_instance.name
        
        notification_list=[]

        notification_details = get_token_for_fcm(member_id,flag=True)

        temp = {
            'id':member_id,
            'fcm_token':notification_details[0],
            'mobile_os':notification_details[1],
        }

        notification_list.append(temp)

        
        message={}
        if aj == "":
            message['payload']={
                "title" : str(community_name),
                "sub_title" : "Apply to join this community and meet like-minded people. ",
                'route':'route://community?community_id=' + str(community_id)
            }
            notification_meta(notification_list,message)
        
        else:
            message['payload']={
                "title" : str(community_name),
                "sub_title" : "Don't miss relevant conversations. Click here to join and meet like-minded people. ",
                'route':'route://community?community_id=' + str(community_id) + '&aj=' + str(aj)
            }
            notification_meta(notification_list,message)
    
            expiry_instance = communityExpiryCodes.objects.filter(community=community_instance, unique_code=aj)
            
            if expiry_instance.exists():
                time_to_sleep = expiry_instance[0].created_at + expiry_instance[0].expire_duration - int(time.time()) - 30*60
                start_time = expiry_instance[0].created_at + expiry_instance[0].expire_duration - 30*60
            else:
                time_to_sleep = -1

            if time_to_sleep > 0:
                task_name = str(member_id) + "_" + str(community_id) + "_send_notification_to_join_drop_off"
                expiry_time = expiry_instance[0].created_at + expiry_instance[0].expire_duration
                args = [member_id, community_id, aj, expiry_time,notification_list]
                task_path = "collabmates_api.notification.send_notification_to_join_drop_off_scheduled_2"
                kwargs = {}
                celerybeatask = CeleryBeatTask()
                celerybeatask.terminate_task(task_name)
                celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                        date_time=start_time, interval=False, crontab=True)
                # time.sleep(time_to_sleep)

@app.task
def send_notification_to_join_drop_off_scheduled_2(member_id, community_id, aj, time_in_hrs,notification_list):
    member = Members.objects.filter(community_id=community_id,member_id=member_id)
    message = {}
    # member_name = user_instance.userinfo.name
    community_instance = Community.objects.get(id=community_id)
    community_name = community_instance.name


    if member.exists():
        return
    message['payload']={
        "title" : 'Invitation link about to expire!',
        "sub_title" : "Don't miss relevant conversations in "+ str(community_name) +". Click here to join and meet like-minded people.",
        'route':'route://community?community_id=' + str(community_id)
    }

    notification_meta(notification_list,message)

    # send notification after 6 hours when of expiry
    # time_to_sleep += 30*60 + 6*60*60
    # time.sleep(time_to_sleep)
    start_time = time.time()
    task_name = str(member_id) + "_" + str(community_id) + "_send_notification_to_join_drop_off"
    args = [member_id, community_id, aj]
    task_path = "collabmates_api.notification.send_notification_to_join_drop_off_scheduled_3"
    kwargs = {}
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)
    celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                            date_time=start_time, interval=False, crontab=True)
    #
    #send notification after 6 hours after link expire
    start_time = add_relative_time_to_epoch(start_time, minutes=30, hours=6, days=0)

@app.task
def send_notification_to_join_drop_off_scheduled_3(member_id, community_id, aj):
    member = Members.objects.filter(community_id=community_id,member_id=member_id)

    community_instance = Community.objects.get(id=community_id)
    community_name = community_instance.name

    expiry_instance = communityExpiryCodes.objects.filter(community=community_instance, unique_code=aj)
    member_name = expiry_instance.promoter.userinfo.name
    if member.exists():
        return

    notification_list=[]

    notification_details = get_token_for_fcm(expiry_instance[0].promoter.id,flag=True)

    temp = {
        'id':expiry_instance[0].promoter.id,
        'fcm_token':notification_details[0],
        'mobile_os':notification_details[1],
    }

    notification_list.append(temp)

    message = {}

    message['payload']={
        "title" : member_name + 'may need new invitation!',
        "sub_title" : "Your private invitation for joining "+ str(community_name) +"has expired. Please resend them invite link.",
        'route':'route://community?community_id=' + str(community_id)
    }

    notification_meta(notification_list,message)


@app.task
@shared_task
def send_notification_for_directory_creation(community_id,start_time,day=0):


    #add update profile notification as well
    # return

    community_instance = Community.objects.get(id=community_id)
    community_name = community_instance.name

    members = Members.objects.filter(community_id=community_id, state__in=[1,4,9],edit_required=True)

    message = {}

    message['payload'] = {
        "title": str(community_name),
        "sub_title": "",
        'route': '//route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(community_instance.name)
    }

    if day == 0 and members.exists():
        # get tomorrow 9 am
        # start_time = datetime.fromtimestamp(start_time)
        start_time = datetime.fromtimestamp(start_time+(24*60*60))
        start_time = start_time.replace(hour=9,minute=0)+ timedelta(days=3)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        celerybeatask = CeleryBeatTask()
        task_name =  str(community_id) + str(start_time) + "_3_send_notification_for_directory_creation"
        day = 3
        args = [community_id, date_time,day]
        task_path = "collabmates_api.notification.send_notification_for_directory_creation"
        kwargs = {}


        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                        date_time=date_time, interval=False, crontab=True)
        return

    elif day == 3 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9,minute=0)+ timedelta(days=2)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        task_name =  str(community_id) + str(start_time)  + "_3_send_notification_for_directory_creation"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        task_name =  str(community_id) + str(start_time) + "_5_send_notification_for_directory_creation"
        day = 5
        args = [community_id, date_time,day]
        task_path = "collabmates_api.notification.send_notification_for_directory_creation"
        kwargs = {}
        for member in members:
            member_name = member.member_id.userinfo.name
            notification_list = []
            notification_details = get_token_for_fcm(member.member_id.id, flag=True)
            temp = {
                'id': member.member_id.id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1],
            }
            message['payload']['sub_title'] = str(member_name) + ", we are reminding you to complete your directory profile. Without an updated profile, you won’t have seamless access to the community. "
            message['payload']['route'] = "route://member_profile?member_id="+ str(member.member_id.id) +"&community_id="+ str(community_id) + '&edit=true'
            notification_list.append(temp)
            notification_meta(notification_list, message)
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return

    elif day == 5 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9,minute=0)+ timedelta(days=2)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        task_name =  str(community_id) + str(start_time) + "_5_send_notification_for_directory_creation"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        task_name =  str(community_id) + str(start_time) + "_7_send_notification_for_directory_creation"
        day = 7
        args = [community_id, date_time,day]
        task_path = "collabmates_api.notification.send_notification_for_directory_creation"
        kwargs = {}
        for member in members:
            member_name = member.member_id.userinfo.name
            notification_list = []
            notification_details = get_token_for_fcm(member.member_id.id, flag=True)
            temp = {
                'id': member.member_id.id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1],
            }
            message['payload']['sub_title'] = str(member_name) + ", please update your profile now to take full advantage of our networking features. This is mandatory for all the members. "
            message['payload']['route'] = "route://member_profile?member_id="+ str(member.member_id.id) +"&community_id="+ str(community_id) + '&edit=true'
            notification_list.append(temp)
            notification_meta(notification_list, message)
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return

    elif day == 7 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9,minute=0)+ timedelta(days=8)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        task_name =  str(community_id) + str(start_time) + "_7_send_notification_for_directory_creation"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        task_name =   str(community_id) + str(start_time) + "_15_send_notification_for_directory_creation"
        day = 15
        args = [community_id, date_time,day]
        task_path = "collabmates_api.notification.send_notification_for_directory_creation"
        kwargs = {}
        for member in members:
            member_name = member.member_id.userinfo.name
            notification_list = []
            notification_details = get_token_for_fcm(member.member_id.id, flag=True)
            temp = {
                'id': member.member_id.id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1],
            }
            message['payload']['sub_title'] = str(member_name) + ", it has been over 15 days you joined us. Please update your profile now to take full advantage of LikeMinds and connect with others."
            message['payload']['route'] = "route://member_profile?member_id="+ str(member.member_id.id) +"&community_id="+ str(community_id) + '&edit=true'
            notification_list.append(temp)
            notification_meta(notification_list, message)
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return

    elif day == 15 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9,minute=0)+ timedelta(days=15)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        task_name =  str(community_id) + str(start_time) + "_15_send_notification_for_directory_creation"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        task_name =  str(community_id) + str(start_time) + "_30_send_notification_for_directory_creation"
        day = 30
        args = [community_id, date_time,day]
        task_path = "collabmates_api.notification.send_notification_for_directory_creation"
        kwargs = {}
        for member in members:
            member_name = member.member_id.userinfo.name
            notification_list = []
            notification_details = get_token_for_fcm(member.member_id.id, flag=True)
            temp = {
                'id': member.member_id.id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1],
            }
            message['payload']['sub_title'] = str(member_name) + ", it has been over 30 days you joined us. Please update your profile and improve your chances of connecting with like-minded folks."
            message['payload']['route'] = "route://member_profile?member_id="+ str(member.member_id.id) +"&community_id="+ str(community_id) + '&edit=true'
            notification_list.append(temp)
            notification_meta(notification_list, message)
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return


@app.task
@shared_task
def send_ice_breaker_notification(community_id,start_time,day=0):

    community_instance = Community.objects.get(id=community_id)

    members = Members.objects.filter(community_id=community_id, state=1)
    collabcards = Collabcard.objects.filter(community = community_instance)
    message = {}
    for member in members:

        notification_list = []
        notification_details = get_token_for_fcm(member.member_id.id, flag=True)
        temp = {
            'id': member.member_id.id,
            'fcm_token': notification_details[0],
            'mobile_os': notification_details[1],
        }
        notification_list.append(temp)
        message['payload'] = {
            "title": str(community_instance.name),
            "sub_title": "",
            'route':'//route://community_collabcard?community_id='+ str(community_id) +'&community_name=' + str(community_instance.name)
        }
        if day == 3:
            message['payload']['sub_title'] = "Hey " + get_first_name_from_name(member.member_id.userinfo.name) + ", looks like your community is having a dull moment! Start a conversation on something your community would like to discuss."
            notification_meta(notification_list, message)

        elif day == 4:
            message['payload']['sub_title'] = "Hey " + get_first_name_from_name(member.member_id.userinfo.name) + ", it has been 4 days that someone said anything in your community. Don’t let the ball drop, start a conversation now!"
            notification_meta(notification_list, message)

        elif day == 7:
            message['payload']['sub_title'] = "Hey " + get_first_name_from_name(member.member_id.userinfo.name) + ",looks like your community is having a dull moment! Start a conversation on something your community would like to discuss."
            notification_meta(notification_list, message)

        elif day == 9:
            message['payload']['sub_title'] = "Hey " + get_first_name_from_name(member.member_id.userinfo.name) + ", it has been 9 days that someone said anything in your community. Don’t let the ball drop, start a conversation now!"
            notification_meta(notification_list, message)



    if day == 0 and members.exists():
        # get tomorrow 11 am
        # start_time = datetime.fromtimestamp(start_time+30)
        start_time = datetime.fromtimestamp(start_time+(24*60*60))
        start_time = start_time.replace(hour=11,minute=0)+ timedelta(days=3)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()

        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + "send_ice_breaker_notification"

        #delete if task exists before
        celerybeatask.terminate_task(task_name)
        day = 3
        args = [community_id, date_time,day]
        task_path = "collabmates_api.notification.send_ice_breaker_notification"
        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                        date_time=date_time, interval=False, crontab=True)
        return

    elif day == 3 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9,minute=0)+ timedelta(days=1)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()

        task_name =  str(community_id) + "send_ice_breaker_notification"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        day = 4
        args = [community_id, date_time,day]
        task_path = "collabmates_api.notification.send_ice_breaker_notification"
        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return

    elif day == 4 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9,minute=0)+ timedelta(days=2)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        task_name =  str(community_id) + "send_ice_breaker_notification"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        day = 7
        args = [community_id, date_time,day]
        task_path = "collabmates_api.notification.send_ice_breaker_notification"
        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return

    elif day == 7 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9,minute=0)+ timedelta(days=8)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        task_name =  str(community_id) + "send_ice_breaker_notification"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        day = 9
        args = [community_id, date_time,day]
        task_path = "collabmates_api.notification.send_ice_breaker_notification"
        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return

# @shared_task
# def private_link_about_to_expire_notification(member_id,community_id,aj):

#     '''function to send notification to users 30 minutes before the link expires'''

#     #check if they created the profile. 
#     member = Members.objects.filter(community_id=community_id,member_id=member_id)
    
#     if member.exists():
#         pass

#     else:
#         community = Community.objects.filter(id=community_id)
#         if community.exists():
#             community_name = community[0].name
#         else:
#             return

#         notification_list=[]

#         notification_details = get_token_for_fcm(member_id,flag=True)

#         temp = {
#             'id':member_id,
#             'fcm_token':notification_details[0],
#             'mobile_os':notification_details[1],
#         }

#         notification_list.append(temp)

        
#         message={}
        
#         message['payload']={
#             "title" : 'Invitation link about to expire!',
#             "sub_title" : "Don't miss relevant conversations in " + str(community_name)+". Click here to join and meet like-minded people.",
#             'route':'route://community_collabcard?community_id=' + str(community_id) + '&aj=' + str(aj)
#         }

#         notification_meta(notification_list,message)

@shared_task
def schedule_poll_end_notification(community_name, community_id, typ, date_time, card_id):
    task_name = str(card_id) + "_poll_expiry_or_event_remainder_notification"
    print("date---time>>>", date_time)
    date_time = date_time/1000
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)
    # celerybeatask = CeleryBeatTask()
    args = [community_name, community_id, typ,card_id,task_name]
    # date_time = time.time() + 60
    task_path = "collabmates_api.notification.poll_expiry_or_event_remainder_notification"
    kwargs = {}
    celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                            date_time=date_time, interval=False, crontab=True)

    # if typ == 3:
    #     task_name = str(card_id) + "_poll_results_announcement_after_6_hours"
    #     task_path = "collabmates_api.tasks.send_poll_results_announcement_mail"
    #     celerybeatask.terminate_task(task_name)
    #
    #     args = [card_id, task_name]
    #     date_time = date_time + 300  # + 21600  # date time + 6 hours . change the value for testing
    #     celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
    #                                             date_time=date_time, interval=False, crontab=True)


@app.task
def poll_expiry_or_event_remainder_notification(community_name, community_id, typ, card_id,task_name,**kwargs):

    """ function to send notification to all members when event/poll is going to start/end """
    print("\ntype === ", typ)
    print(" community-id === ", community_id)
    print("kwargs === ", kwargs,"\n")
    try:
        card_instance = Collabcard.objects.get(pk=card_id)
        card_owner = card_instance.user
        owner_flag = False
        card_title = get_title_from_collabcard(card_instance)
        if typ == 2:
            collabcardstates = collabcardState.objects.filter(card=card_id).filter(Q(state=3) | Q(state=4)).filter(removed_status=None)
            notification_list = []
            for ccs in collabcardstates:
                if card_owner.id == ccs.user.id:
                    owner_flag = True
                notification_details = get_token_for_fcm(ccs.user.id, flag=True)
                temp = {
                    'id': ccs.user.id,
                    'fcm_token': notification_details[0],
                    'mobile_os': notification_details[1],
                }

                notification_list.append(temp)


        else:
            members = MemberPollVotes.objects.filter(card=card_id).order_by('-id')
            notification_list = []
            for member in members:
                if card_owner.id == member.user.id:
                    owner_flag = True
                notification_details = get_token_for_fcm(member.user.id,flag=True)
                temp = {
                    'id': member.user.id,
                    'fcm_token':notification_details[0],
                    'mobile_os':notification_details[1],
                }

                notification_list.append(temp)
        # print("token list ===== ", token_list)

        #if card owner did not vote, add him to notification list
        if owner_flag == False:
            notification_details = get_token_for_fcm(card_owner.id, flag=True)
            temp = {
                'id': card_owner.id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1],
            }
            notification_list.append(temp)

        # if not user_fcm in token_list:
        #     token_list.append(user_fcm)


        if typ == 3:
            sub_title = 'Your poll ended. Tap to see results'
            route = 'route://poll_chatroom?chatroom_id=' + str(card_id) + '&poll_end=true'
        else:
            sub_title = 'Your event is starting in 30 minutes'
            route = 'route://collabcard?collabcard_id=' + str(card_id)

        message = {}
        message['payload'] = {
            'title': str(card_title),
            'sub_title': sub_title,
            'route': route
        }
        # print(message)
        notification_meta(notification_list, message)
        # disable the task , to prevent it from trigerring in future
        beat_task = CeleryBeatTask()
        beat_task.terminate_task(task_name=task_name)

    except:
        print("Error while connecting to PostgreSQL")






@app.task
def send_notification_to_inactive_chatroom_users():

    current_time = time.time()

    inactive_chatrooms = collabcardState.objects.filter(follow_status=True,
                                                        remove=None).filter(~Q(expiry_time=None) & Q(
        expiry_time__lt=current_time)).filter(created_at__gt = 1603604997)

    user_set = set()
    user_list = []
    for data in inactive_chatrooms:


        if data.card.type == card_types.CARD_PURPOSE and not is_member_promoter(data.card.community,data.card.user):
            continue

        key = str(data.user.id)+"--"+str(data.card.id)
        if key not in user_set:
            temp = {}
            user_instance = data.user
            card_instance = data.card
            notification_filter = memberNotificationFlag.objects.filter(member=user_instance,
                                                                        card=card_instance,
                                                                        code='chat_room_becoming_inactive'
                                                                        )
            if notification_filter.exists():
                if data.expiry_time > notification_filter[0].updated_at:
                    temp['user_id'] = user_instance.id
                    temp['user_name'] = user_instance.userinfo.name
                    temp['chatroom_id'] = card_instance.id
                    temp['chatroom_name'] = get_title_from_collabcard(card_instance)
                    notification_filter.update(updated_at=current_time)

                    user_list.append(temp)
            else:
                instance = memberNotificationFlag()
                instance.member = user_instance
                instance.card = card_instance
                instance.updated_at = current_time
                instance.created_at = current_time
                instance.community = data.community
                instance.flag = True
                instance.code = 'chat_room_becoming_inactive'
                instance.save()
                temp['user_id'] = user_instance.id
                temp['user_name'] = user_instance.userinfo.name
                temp['chatroom_id'] = card_instance.id
                temp['chatroom_name'] = get_title_from_collabcard(card_instance)

                user_list.append(temp)

            user_set.add(key)

    end_time = time.time()
    diff = end_time - current_time
    print(diff)

    send_inactive_notification_utils(user_list)




def send_inactive_notification_utils(user_list):


    for data in user_list:
        notification_list = []
        notification_details = get_token_for_fcm(data['user_id'], flag=True)
        temp = {
            'id': data['user_id'],
            'fcm_token': notification_details[0],
            'mobile_os': notification_details[1]
        }
        notification_list.append(temp)

        user_name = data['user_name']
        if user_name:
            split_name = user_name.split(" ")
            if split_name and split_name[0]:
                user_name = split_name[0]

        sub_title = """Hey %s, this chat room has been moved to inactive chat rooms since there has been no new activity here in the last 24 hours since you opened it. You may want to mark it as active for yourself if you intend to respond further in it. Else if anyone else responds in the future, it will become active again."""%(user_name)
        message = {}
        message['payload'] = {
            'title': data['chatroom_name'],
            'sub_title': sub_title,
            'route': f"route://inactive_chatroom?chatroom_id={data['chatroom_id']}"
        }

        notification_meta(notification_list,message)

    print("Notification Sent")



# x=CeleryBeatTask()
# x.terminate_task("send_notification_to_inactive_chatroom_users")
# x.terminate_task("run_after_10_sec")


@shared_task
def send_notification_for_new_promoter(promoter_id, member_id, community_id, custom_title=None):
    community_instance = Community.objects.get(pk=community_id)
    promoter_instance = User.objects.get(pk=promoter_id)
    member_instance = User.objects.get(pk=member_id)
    community_name = community_instance.name
    promoter_name = promoter_instance.userinfo.name

    member_fcm_token = member_instance.userinfo.fcm_token
    member_mobile_os = member_instance.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": member_id,
        'fcm_token': member_fcm_token,
        'mobile_os': member_mobile_os,
    }
    notification_list.append(user_details)

    message['payload'] = {
        "title": community_name,
        "sub_title": f"{promoter_name} has added you as {custom_title} of the community.",
        'route': f'route://member_profile/{member_id}?community_id={community_id}&member_id={member_id}'
    }

    notification_meta(notification_list, message)


@shared_task
def send_notification_for_custom_title_changed(promoter_id, member_id, community_id, custom_title):
    community_instance = Community.objects.get(pk=community_id)
    promoter_instance = User.objects.get(pk=promoter_id)
    member_instance = User.objects.get(pk=member_id)
    community_name = community_instance.name
    promoter_name = promoter_instance.userinfo.name

    member_fcm_token = member_instance.userinfo.fcm_token
    member_mobile_os = member_instance.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": member_id,
        'fcm_token': member_fcm_token,
        'mobile_os': member_mobile_os,
    }
    notification_list.append(user_details)

    if custom_title is None:
        custom_title = "Community Manager"

    message['payload'] = {
        "title": community_name,
        "sub_title": f"{promoter_name} has made you {custom_title} of the community.",
        'route': f'route://member_profile/{member_id}?community_id={community_id}&member_id={member_id}'
    }

    notification_meta(notification_list, message)


@shared_task
def send_notification_for_ownership_transfered(prev_owner_id, new_owner_id, community_id):
    community_instance = Community.objects.get(pk=community_id)
    pre_owner = User.objects.get(pk=prev_owner_id)
    new_owner = User.objects.get(pk=new_owner_id)
    community_name = community_instance.name
    prev_owner_name = pre_owner.userinfo.name

    new_owner_fcm_token = new_owner.userinfo.fcm_token
    new_owner_mobile_os = new_owner.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": new_owner_id,
        'fcm_token': new_owner_fcm_token,
        'mobile_os': new_owner_mobile_os,
    }
    notification_list.append(user_details)

    message['payload'] = {
        "title": community_name,
        "sub_title": f"{prev_owner_name} has transferred the ownership of the community to you.",
        'route': f'route://member_profile/{new_owner_id}?community_id={community_id}&member_id={new_owner_id}'
    }

    notification_meta(notification_list, message)


@shared_task
def send_notification_for_removed_member(admin_id, removed_user_id, community_id):
    community_instance = Community.objects.get(pk=community_id)
    admin = User.objects.get(pk=admin_id)
    removed_user = User.objects.get(pk=removed_user_id)
    community_name = community_instance.name
    admin_name = admin.userinfo.name

    removed_user_fcm_token = removed_user.userinfo.fcm_token
    removed_user_mobile_os = removed_user.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": removed_user_id,
        'fcm_token': removed_user_fcm_token,
        'mobile_os': removed_user_mobile_os,
    }
    notification_list.append(user_details)

    message['payload'] = {
        "title": "LikeMinds",
        "sub_title": f"{admin_name} has removed you from the {community_name}. Click here to know the reasons.",
        'route': '//route://community_collabcard?community_id='
    }

    # notification_meta(notification_list, message)


@shared_task
def send_notification_for_right_given_to_member(user_id, community_id, rights_added):
    community_instance = Community.objects.get(pk=community_id)
    user_instance = User.objects.get(pk=user_id)
    community_name = community_instance.name

    user_fcm_token = user_instance.userinfo.fcm_token
    user_mobile_os = user_instance.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": user_id,
        'fcm_token': user_fcm_token,
        'mobile_os': user_mobile_os,
    }
    notification_list.append(user_details)

    for right_id in rights_added:
        right = memberRights.objects.get(pk=right_id)
        right_title = str(right.title).lower()
        card_type = 0
        if right.state == member_rights.MEMBER_RIGHT_CREATE_ROOMS:
            card_type = 0
        elif right.state == member_rights.MEMBER_RIGHT_CREATE_POLL:
            card_type = 3
        elif right.state == member_rights.MEMBER_RIGHT_CREATE_EVENT:
            card_type = 2

        route = f"route://create_chatroom?community_id={community_id}&community_name={community_name}&type={card_type}"
        sub_title = f"The Community Manager has reactivated your privilege to {right_title}"

        if right.state == member_rights.MEMBER_RIGHT_RESPOND_IN_ROOM:
            sub_title = f"The Community Manager has reactivated your privilege to respond inside chat rooms."
            route = f"route://community_collabcard?community_id={community_id}&community_name={community_name}"
        elif right.state == member_rights.MEMBER_RIGHT_INVITE_PRIVATE_LINK:
            sub_title = f"You have earned the privilege to invite new members to the community via private links!"
            route = f"route://community?community_id={community_id}&share=true"

        message['payload'] = {
            "title": community_name,
            "sub_title": sub_title,
            'route': route
        }

        notification_meta(notification_list, message)


@shared_task
def send_notification_for_pending_chatroom_approved_or_rejected(card_id, is_approved=False):
    card_instance = Collabcard.objects.get(pk=card_id)
    chatroom_title = card_instance.header
    card_creator = card_instance.user
    community_name = card_instance.community.name
    card_creator_first_name = card_creator.userinfo.name.split(" ")[0]
    user_fcm_token = card_creator.userinfo.fcm_token
    user_mobile_os = card_creator.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": card_creator.id,
        'fcm_token': user_fcm_token,
        'mobile_os': user_mobile_os,
    }
    notification_list.append(user_details)

    if is_approved:
        sub_title = f"Hurray! {card_creator_first_name}, your chat room ‘{chatroom_title}’ has been approved."
        route = f" route://chatroom_detail?chatroom_id=={card_id}"
    else:
        sub_title = f"{card_creator_first_name}, we are sorry to inform you that your chat room ‘{chatroom_title}’ was not approved."
        route = "route://main"

    message['payload'] = {
        "title": community_name,
        "sub_title": sub_title,
        'route': route
    }

    notification_meta(notification_list, message)


@shared_task
def send_notification_for_reports(report_id, community_id, reported_by_user_id,
                                  card_id=None, conversation_id=None, reported_on_user_id=None,
                                  report_type=None, reason=None, tag_id=None):

    reported_by_user = User.objects.get(pk=reported_by_user_id)
    reported_by_user_name = reported_by_user.userinfo.name
    community_instance = Community.objects.get(pk=community_id)
    community_name = community_instance.name

    sub_title_prefix = ""
    reported_on_user = None
    print("report_type >>>>>   ", report_type)
    if report_type == 0:
        reported_on_user = User.objects.get(pk=reported_on_user_id)
        sub_title_prefix = reported_on_user.userinfo.name

    elif report_type == 1:
        card_instance = Collabcard.objects.get(pk=card_id)
        reported_on_user = card_instance.user
        sub_title_prefix = card_instance.header

    elif report_type == 2:
        conversation_instance = card_answers.objects.get(pk=conversation_id)
        reported_on_user = conversation_instance.user
        chatroom_name = conversation_instance.card.header
        sub_title_prefix = f"A message in ‘{chatroom_name}'"

    if tag_id:
        report = Report_Tags.objects.get(tag_id=tag_id)
        reason = report.tag_name

    sub_title = f"{sub_title_prefix} was reported by {reported_by_user_name} citing the reason: '{reason}’."
    route = f"route://review_reports?community_id={community_id}&community_name={community_name}&report_id={report_id}"

    message = {}
    notification_list = []
    message['payload'] = {
        "title": community_name,
        "sub_title": sub_title,
        'route': route
    }

    is_promoter = False
    parent_cm_list = []

    if reported_on_user:
        member_instance = Members.objects.filter(community_id=community_instance, member_id=reported_on_user)
        if member_instance.exists():
            member_instance = member_instance[0]
            if member_instance.is_owner:
                return
            elif member_instance.state == member_states.ADMIN:
                is_promoter = True
                parent_cm_list = json.loads(member_instance.parent_cm_list) if member_instance.parent_cm_list else []
                parent_cm_list = set(parent_cm_list)

    if report_type == 0:
        admin_ids = list(userAdminRights.objects.filter(community=community_instance,
                         right__state=manager_rights.MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS).values_list("user__id",
                                                                                  flat=True))
        admin_ids = set(admin_ids)
    else:
        admin_ids = list(userAdminRights.objects.filter(community=community_instance,
                        right__state=manager_rights.MANAGER_RIGHT_DELETE_ROOMS).values_list("user__id", flat=True))
        admin_ids = set(admin_ids)

    admin_ids = {str(admin_id) for admin_id in admin_ids}

    if is_promoter:
        admin_ids = list(admin_ids & parent_cm_list)
    else:
        admin_ids = list(admin_ids)

    users = User.objects.filter(id__in=admin_ids)

    for user in users:
        user_details = {
            "id": user.id,
            'fcm_token': user.userinfo.fcm_token,
            'mobile_os': user.userinfo.mobile_os,
        }

        notification_list.append(user_details)

    if report_type in [0, 1]:  # will remove check after implementing conversation delete
        notification_meta(notification_list, message)


@shared_task
def send_notification_for_chatroom_deleted(deleted_by_user_id, card_id, community_id):

    deleted_by_user = User.objects.get(pk=deleted_by_user_id)
    deleted_by_user_name = deleted_by_user.userinfo.name
    community_instance = Community.objects.get(pk=community_id)
    community_name = community_instance.name

    card_instance = Collabcard.objects.get(pk=card_id)
    card_name = card_instance.header
    sub_title = f"The Community Manager has deleted {card_name}. Click here to know the reasons."
    route = ""

    message = {}
    notification_list = []
    message['payload'] = {
        "title": community_name,
        "sub_title": sub_title,
        'route': route
    }

    following_member_ids = list(conversationEngage.objects.filter(card=card_instance).values_list("user__id", flat=True))

    users = User.objects.filter(id__in=following_member_ids)

    for user in users:
        user_details = {
            "id": user.id,
            'fcm_token': user.userinfo.fcm_token,
            'mobile_os': user.userinfo.mobile_os,
        }

        notification_list.append(user_details)

    # notification_meta(notification_list, message)



