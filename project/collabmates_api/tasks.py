from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
import time
from django.template import Context
from django.conf import settings
from django.db.models import Q
from togther.models import *
from project.celery import app
from utility.tasks import send_email
from utility.utils import (android_app_download_link, ios_app_download_link,
                           is_LG_or_LP_community, is_IG_community,angellist_link,linkedIn_link,get_user_email,
                           android_app_download_link,ios_app_download_link,check_notification_flag)

from utility.celery_beat_tasks import CeleryBeatTask
from django.http import JsonResponse
from django.contrib.auth.models import User
from togther.models import Collabcard
from utility.encryption import encrypt,decrypt
from .static_files import GOOGLE_PLAYSTORE,APPLE_APPSTORE,APP_LOGO
# from datetime import datetime,
# url = 'https://beta.likeminds.community'
url = settings.URL

from .notification import get_title_from_collabcard 
# def send_email(subject,template,to):
#     fail_silently=True
#     msg = EmailMultiAlternatives(subject,
#                                 template,
#                                 "Collabmates<hello@collabmates.com>",
#                                 [to],)
#     msg.attach_alternative(template, "text/html")
#     return msg.send(fail_silently)

@shared_task
def send_email_to_nominated_admin(NominatedAdmin,email,ProposedAdmin,CommunityName,community_id,proposedAdminState):
    time.sleep(5)
    url = settings.URL
    url = url+"/community/"+str(community_id)+"?source=email&cta=accept_admin"
    fail_silently=True
    to = email
    subject =str(ProposedAdmin)+ " has proposed you as a promoter of "+str(CommunityName)+" community"
    if proposedAdminState == 1:
        template = get_template("mails/accept_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id,'url':url})
    elif proposedAdminState == 2:
        template = get_template("mails/accept_temp_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id,'url':url})
    msg = EmailMultiAlternatives(subject,
                                 template,
                                 "LikeMinds<hello@likeminds.community>",
                                 [to],
                                 )
    msg.attach_alternative(template, "text/html")
    # print("printing mag >>> ",msg.send(fail_silently))
    # return
    to = [to]
    send_email(subject, template, to)

@shared_task
def send_email_to_admin_of_community(CommmunityAdminName,CommunityName,email):
    time.sleep(5)
    fail_silently=True
    to = email
    subject = "Congrats! "+CommunityName+" community is now live"
    template = get_template("mails/create_community_as_admin.html").render({"CommmunityAdminName":CommmunityAdminName,"CommunityName":CommunityName})
    # msg = EmailMultiAlternatives(subject,
    #                              template,
    #                              "Collabmates<hello@collabmates.com>",
    #                              [to],
    #                              )
    # msg.attach_alternative(template, "text/html")
    # return msg.send(fail_silently)
    to = [to]
    send_email(subject, template, to)

@shared_task
def send_email_to_temp_admin_of_community(CommmunityAdminName,CommunityName,email):
    time.sleep(5)
    fail_silently=True
    to = email
    subject = "Congrats! "+CommunityName+" community is now live"
    template = get_template("mails/create_community_as_member.html").render({"CommmunityAdminName":CommmunityAdminName,"CommunityName":CommunityName})
    # msg = EmailMultiAlternatives(subject,
    #                              template,
    #                              "Collabmates<hello@collabmates.com>",
    #                              [to],
    #                              )
    # msg.attach_alternative(template, "text/html")
    # return msg.send(fail_silently)
    to = [to]
    send_email(subject, template, to)


@shared_task
def send_email_to_proposed_admin(NominatedAdmin, email, ProposedAdmin, CommunityName, proposedAdminState, community_id):
    time.sleep(5)
    fail_silently = True
    to = email
    subject = str(NominatedAdmin) + " has accepted your invitation to become a promoter for " + str(
        CommunityName) + " community"

    if proposedAdminState == 1:
        template = get_template("mails/accepted_admin_request.html").render(
            {"NominatedAdmin": NominatedAdmin, "email": email, "ProposedAdmin": ProposedAdmin,
             "CommunityName": CommunityName, "community_id": community_id, 'url': url})
    elif proposedAdminState == 2:
        template = get_template("mails/accepted_temp_admin_request.html").render(
            {"NominatedAdmin": NominatedAdmin, "email": email, "ProposedAdmin": ProposedAdmin,
             "CommunityName": CommunityName, "community_id": community_id, 'url': url})
    # msg = EmailMultiAlternatives(subject,
    #                              template,
    #                              "Collabmates<hello@collabmates.com>",
    #                              [to],
    #                              )
    # msg.attach_alternative(template, "text/html")
    # return msg.send(fail_silently)
    to = [to]
    send_email(subject, template, to)

@shared_task
def send_email_for_new_collabcard_posted(context):

    '''function to send the email when a new collabcard is posted'''

    to = context['to']
    fail_silently = True
    context['android_app_download_link'] = android_app_download_link
    context['ios_app_download_link'] = ios_app_download_link
    subject = context['subject']
    template = get_template("mails/collabcard_posted.html").render(context)
    # msg = EmailMultiAlternatives(subject,
    #                              template,
    #                              "Collabmates<hello@collabmates.com>",
    #                              [to],
    #                              )
    # msg.attach_alternative(template, "text/html")
    # return msg.send(fail_silently)
    to = [to]
    send_email(subject, template, to)


@app.task
def pending_members_mail():
    '''24 hour mail'''
    members = Members.objects.select_related('community_id','member_id')
    pending_members = members.filter(state=3)#.distinct('community_id')
    count=1
    for member in pending_members:
        pending_members_in_community = pending_members.filter(community_id=member.community_id)#[:3]
        admins_of_community = members.filter(community_id=member.community_id).filter(Q(state=1)|Q(state=2))
        # print("==== ",member.community_id.id,)

        if pending_members_in_community.exists() and admins_of_community.exists():

            for admin in admins_of_community:
                print("==== ", admin.member_id.id ,'>>>>' ,count)

                to = admin.member_id.email
                fail_silently = True
                pending_count = pending_members_in_community.count()
                # pending_count = 1
                if pending_count == 1:
                    if not admin.member_id.userinfo.image_link:
                        promoter_image=admin.member_id.userinfo.image_file.url
                    else:
                        promoter_image = admin.member_id.userinfo.image_link
                    template = get_template("mails/single_pending_member.html").render(
                        {'promoter': admin.member_id.userinfo.name,
                         'promoter_image': promoter_image,
                         'pending_members': pending_members_in_community[0],
                         'pending_member_count': pending_count,
                         'community': admin.community_id,
                         'community_name': admin.community_id.name,
                         'community_id': admin.community_id.id,
                         'url':url,
                         'android_app_download_link':android_app_download_link,
                         'ios_app_download_link':ios_app_download_link
                         })
                    subject = str(pending_members_in_community[0].member_id.userinfo.name)+" has requested to join "+str(admin.community_id.name)
                elif pending_count > 1:
                    subject = str(pending_count)+' new members have requested to join '+str(admin.community_id.name)
                    template = get_template("mails/multiple_pending_members_mail.html").render(
                        {'promoter': admin.member_id.userinfo.name,
                         'promoter_image': promoter_image,
                         'pending_members': pending_members_in_community[:4],
                         'pending_member_count': pending_count,
                         'remaining_pending_requests': pending_count-4,
                         'community_name': admin.community_id.name,
                         'community_id': admin.community_id.id,
                         'url':url,
                         'android_app_download_link':android_app_download_link,
                         'ios_app_download_link':ios_app_download_link
                         })
                print(subject)
                to = admin.member_id.userinfo.email
                # msg = EmailMultiAlternatives(subject,
                #                              template,
                #                              "Collabmates<hello@collabmates.com>",
                #                              [admin.member_id.userinfo.email],
                #                              )
                # msg.attach_alternative(template, "text/html")
                # msg.send(fail_silently)
                to = [to]
                send_email(subject, template, to)
    return


@app.task
def pending_members_mail_new(request=None):
    '''24 hour mail'''

    communities = Community.objects.all()

    for community in communities:
        all_members = Members.objects.select_related('community_id', 'member_id').filter(community_id=community)
        if all_members.exists():
            pending_members = all_members.filter(state=3)
            if pending_members.exists():
                is_lg = is_LG_or_LP_community(community)
                if is_lg:
                    # print("is ig ====  ",community.id)
                    for member in all_members:

                        is_member_verified = all_members.filter(member_id=member.member_id).filter(state=4)
                        if not is_member_verified.exists():
                            print("member not verified ===  ",member.member_id.id)
                            continue
                        # print("member is verified ===  ", member.member_id.id)
                        pending_members_list = all_members.filter(ask_member_id=member.member_id.id).filter(state=3)
                        if pending_members_list.exists():
                            # print("pending members list === ",pending_members_list)
                            if pending_members_list.count() == 1:
                                send_pending_members_mail_for_one_pending_member(admin=member,
                                                                                 pending_members_list=pending_members)
                            elif pending_members_list.count() > 1:
                                send_pending_members_mail_for_multiple_pending_members(
                                                        admin=member,
                                                        pending_members_list=pending_members_list,
                                                        pending_count=pending_members.count())

                else:
                    # print("community ====  ", community.id)
                    admins_of_community = all_members.filter(Q(state=1) | Q(state=2))
                    if admins_of_community.exists():
                        for admin in admins_of_community:
                            # print("admin ====  ", admin.member_id.id)
                            # print("pending members === ",pending_members)
                            if pending_members.count() == 1:
                                send_pending_members_mail_for_one_pending_member(admin=admin,
                                                                                 pending_members_list=pending_members)
                            elif pending_members.count() > 1:
                                send_pending_members_mail_for_multiple_pending_members(
                                                        admin=admin,
                                                        pending_members_list=pending_members,
                                                        pending_count=pending_members.count())
        time.sleep(1)
        # print("\n")
    return  # JsonResponse({"success":True}) #for testing purpose


def send_pending_members_mail_for_one_pending_member(admin, pending_members_list):
    if not admin.member_id.userinfo.image_link:
        promoter_image = url + admin.member_id.userinfo.image_file.url
    else:
        promoter_image = admin.member_id.userinfo.image_link
    template = get_template("mails/single_pending_member.html").render(
        {'promoter': admin.member_id.userinfo.name,
         'promoter_image': promoter_image,
         'pending_members': pending_members_list[0],
         'pending_member_count': 1,
         'community': admin.community_id,
         'community_name': admin.community_id.name,
         'community_id': admin.community_id.id,
         'url': url,
         'android_app_download_link': android_app_download_link,
         'ios_app_download_link': ios_app_download_link
         })
    subject = str(pending_members_list[0].member_id.userinfo.name) + " has requested to join " + str(
        admin.community_id.name)

    print(subject)
    to = admin.member_id.userinfo.email
    to = [to]
    send_email(subject, template, to)


def send_pending_members_mail_for_multiple_pending_members(admin, pending_members_list, pending_count):
    if not admin.member_id.userinfo.image_link:
        promoter_image = url + admin.member_id.userinfo.image_file.url
    else:
        promoter_image = admin.member_id.userinfo.image_link
    subject = str(pending_count) + ' new members have requested to join ' + str(admin.community_id.name)
    template = get_template("mails/multiple_pending_members_mail.html").render(
        {'promoter': admin.member_id.userinfo.name,
         'promoter_image': promoter_image,
         'pending_members': pending_members_list[:4],
         'pending_member_count': pending_count,
         'remaining_pending_requests': pending_count - 4,
         'community_name': admin.community_id.name,
         'community_id': admin.community_id.id,
         'url': url,
         'android_app_download_link': android_app_download_link,
         'ios_app_download_link': ios_app_download_link
         })
    print(subject)
    to = admin.member_id.userinfo.email
    to = [to]
    send_email(subject, template, to)


@shared_task
def send_welcome_mail(user_id):
    user = User.objects.get(pk = user_id)
    count = 0
    member_communities_list = Members.objects.filter(member_id = user).distinct('community_id')
    for community in member_communities_list:
        if community.community_id.hide_community == '0' or community.community_id.hide_community == '1' or community.community_id.hide_community == '4' :
            if community.state == 1 or community.state == 2 or community.state == 4 or community.state == 7:
                count +=1
    fail_silently=True
    if user.email:
        to = user.email
        subject = "Thanks for downloading LikeMinds App! Here's what to expect"
        if count == 0:

            template = get_template("mails/welcome_mail_zero.html").render({"name":user.userinfo.name})
        else:
            if count == 1:
                text = 'the '+member_communities_list[0].community_id.name+' community'
            if count > 1:
                text = 'your existing communities'

            template = get_template("mails/welcome_mail_non_zero.html").render({"name":user.userinfo.name,'url':url,'text':text})
        # msg = EmailMultiAlternatives(subject,
        #                              template,
        #                              "Collabmates<hello@collabmates.com>",
        #                              [to],
        #                              )
        # msg.attach_alternative(template, "text/html")
        # return msg.send(fail_silently)
        to = [to]
        send_email(subject, template, to)
    else:
        return



@shared_task
def send_verification_mail_for_email_sync(user_name,verification_link,email):

    '''function to send verification mail to user who wants email sync'''

    subject = user_name + ", verify your email"
    context = {
                'user_name':user_name,
                'verification_link':verification_link,
                'android_app_download_link': android_app_download_link,
                'ios_app_download_link': ios_app_download_link,
                'linkedIn_link': linkedIn_link,
                'angellist_link': angellist_link
               }
    template = get_template("mails/verify_email_template.html").render(context)
    #print(context)

    to = [email]
    send_email(subject, template, to)

@shared_task
def send_tagged_user_mail(user_id,card_id,tagged_member_list,time_in_hrs):
    #check last conversation seen
    has_seen = {}
    for member_id in tagged_member_list:
        state = conversationMemberState.objects.filter(card_id=card_id, user_id=member_id)
        if state.exists():
            has_seen[member_id] = state.first().conversation_id
        else:
            has_seen[member_id] = -1

    celerybeatask = CeleryBeatTask()
    kwargs = {}
    task_name = str(user_id) + '_' + str(card_id) + '_send_tagged_user_mail'
    celerybeatask.terminate_task(task_name)
    task_path = 'collabmates_api.tasks.send_tagged_user_mail_scheduled'
    args = [user_id,card_id,tagged_member_list,has_seen]

    date_time = time.time() + (time_in_hrs*60*60)
    # date_time = time.time() + 60

    celerybeatask.create_dynamic_clery_task(args,kwargs,task_name,task_path,
                                            date_time=date_time, interval=False, crontab=True)


@app.task
def send_tagged_user_mail_scheduled(user_id,card_id,tagged_member_list,has_seen):
    userinstance = User.objects.get(pk=user_id)
    card_instance = Collabcard.objects.get(id=card_id)
    has_seen_new = {}
    for member_id in tagged_member_list:
        user_name = userinstance.userinfo.name
        email = get_user_email(member_id)
        member = User.objects.get(pk=member_id)
        member_name = member.userinfo.name

        #check if user has opened the chat
        state = conversationMemberState.objects.filter(card_id=card_id, user_id=member_id)
        if state.exists():
            has_seen_new[member_id] = state.first().conversation_id
        else:
            has_seen_new[member_id] = -1
        print(has_seen,has_seen_new)
        #if email exists and he hasnt seen the chat
        if email and has_seen_new[member_id] == has_seen[member_id]:
            notification_list = [
                'mail_send_tagged_user_mail'
            ]
            if check_notification_flag(member_id,notification_list,card_id=None,community_id=None):
                subject = str(user_name) + " is waiting for your response! "
                email_context = {
                    'subject':subject,
                    'user_name' : user_name,
                    'member_name' : member_name,
                    'community_name' : card_instance.community.name,
                    'card_name' : get_title_from_collabcard(card_instance) ,
                    'profile_pic': userinstance.userinfo.image_link,
                    'android_app_download_link': android_app_download_link,
                    'ios_app_download_link': ios_app_download_link,
                    'playstore_image' : GOOGLE_PLAYSTORE,
                    'applestore_image' : APPLE_APPSTORE,
                    'app_image' : APP_LOGO,
                    'cta_url': url + '/collabcard/' + str(card_id),
                    'unsubscribe_url':url + '/unsubscribe_from_email?m=' + encrypt(member_id) + '&code=mail_send_tagged_user_mail' 
                }
                template = get_template("mails/tagged_email.html").render(email_context)


                # to = ['himanshu@likeminds.community']
                to = [email]

                print(to)
                send_email(subject, template, to)
                print(email_context)

@shared_task
def send_chatroom_owner_mail(user_id,card_id,time_in_hrs):
    state = conversationMemberState.objects.filter(card_id=card_id, user_id=user_id)
    
    if state.exists():
        last_conversation_id = state.first().conversation_id
        message_time = state.first().updated_at
    else:
        last_conversation_id = -1
        message_time = 0

    celerybeatask = CeleryBeatTask()
    kwargs = {}
    task_name = str(card_id) + '_send_chatroom_owner_mail'
    celerybeatask.terminate_task(task_name)
    task_path = 'collabmates_api.tasks.send_chatroom_owner_mail_scheduled'
    args = [user_id, card_id, last_conversation_id,message_time]

    date_time = time.time() + (time_in_hrs*60*60)
    # date_time = time.time() + 60

    celerybeatask.create_dynamic_clery_task(args,kwargs,task_name,task_path,
                                            date_time=date_time, interval=False, crontab=True)
    # print('scheduled')


@app.task
def send_chatroom_owner_mail_scheduled(user_id, card_id, last_conversation_id,message_time ):
    user_instance = User.objects.get(pk=user_id)
    card_instance = Collabcard.objects.get(id=card_id)
    email = get_user_email(user_id)

    state = conversationMemberState.objects.filter(card_id=card_id, user_id=user_id)
    if state.exists():
        new_conversation_id = state.first().conversation_id
    else:
        new_conversation_id = -1
    if new_conversation_id == last_conversation_id:
        notification_list = [
            'mail_send_chatroom_owner_mail'
        ]
        if check_notification_flag(user_id,notification_list,card_id=None,community_id=None):
            number_of_messages = card_answers.objects.filter(card__id=card_id,created_at__gte=message_time).count()
            if number_of_messages == 1:
                subject = str(user_instance.userinfo.name) + ", " + str(number_of_messages) +" message is waiting for you!"
            else:
                subject = str(user_instance.userinfo.name) + ", " + str(number_of_messages) +" messages are waiting for you!"
            email_context = {
                    'subject':subject,
                    'member_name' : user_instance.userinfo.name,
                    'community_name' : card_instance.community.name,
                    'card_name' : get_title_from_collabcard(card_instance),
                    'android_app_download_link': android_app_download_link,
                    'ios_app_download_link': ios_app_download_link,
                    'playstore_image' : GOOGLE_PLAYSTORE,
                    'applestore_image' : APPLE_APPSTORE,
                    'app_image' : APP_LOGO,
                    'cta_url': url + '/collabcard/' + str(card_id),
                    'number_of_messages':number_of_messages,
                    'unsubscribe_url':url + '/unsubscribe_from_email?m=' + encrypt(user_id) + '&code=mail_send_chatroom_owner_mail' ,
                }
            template = get_template("mails/owner_inactive_email.html").render(email_context)

            to = [email]
            # to = ['himanshu@likeminds.community']

            send_email(subject, template, to)
            print(email_context)
            flag = memberNotificationFlag.objects.get(member_id=user_id,code='mail_card_owner_inactivity',card=card_instance)
            flag.flag = False
            flag.save()


@shared_task
def send_community_confirmation_email(user_id, community_id):

    user_instance = User.objects.get(pk=user_id)
    community_instance = Community.objects.get(id=community_id)

    email = get_user_email(user_id)

    notification_list = [
        'mail_has_installed_app'
    ]
    if check_notification_flag(user_id, notification_list, card_id=None, community_id=None):
        subject = user_instance.userinfo.name+', Congratulations, your request has been approved!'
        email_context = {
            'subject': user_instance.userinfo.name+', Congratulations, your request has been approved!',
            'member_name': user_instance.userinfo.name,
            'community_name': community_instance.name,
            'android_app_download_link': android_app_download_link,
            'ios_app_download_link': ios_app_download_link,
            'playstore_image': GOOGLE_PLAYSTORE,
            'applestore_image': APPLE_APPSTORE,
            'app_image': APP_LOGO,
            'cta_url': url + '/community/' + str(community_id),
            'unsubscribe_url': url + '/unsubscribe_from_email?m=' + encrypt(
                user_id) + '&code=mail_has_installed_app',
        }
        template = get_template("mails/community_confirmation_email.html").render(email_context)

        to = [email]
        # to = ['himanshu@likeminds.community']

        send_email(subject, template, to)
        print(email_context)
        celerybeatask = CeleryBeatTask()
        task_name = str(user_id)+"_"+str(community_id) + "_send_community_confirmation_email_2"
        celerybeatask.terminate_task(task_name)
        args = [user_id, community_id,task_name]
        task_path = "collabmates_api.tasks.send_community_confirmation_email_2"

        # date_time = time.time() + 80
        date_time = time.time() + (3*24*60*60)

        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args,kwargs, task_name,task_path,
                                                  date_time=date_time, interval=False, crontab=True)


@app.task
def send_community_confirmation_email_2(user_id, community_id,task_name,*args,**kwargs):
    print("here")
    user_instance = User.objects.get(pk=user_id)
    community_instance = Community.objects.get(id=community_id)

    email = get_user_email(user_id)

    notification_list = [
        'mail_has_installed_app'
    ]

    if check_notification_flag(user_id, notification_list, card_id=None, community_id=None):
        subject = "Hey " + user_instance.userinfo.name + ', you are missing the real action!😬'
        email_context = {
            'subject': "Hey " + user_instance.userinfo.name+', you are missing the real action!😬',
            'member_name': user_instance.userinfo.name,
            'community_name': community_instance.name,
            'android_app_download_link': android_app_download_link,
            'ios_app_download_link': ios_app_download_link,
            'playstore_image': GOOGLE_PLAYSTORE,
            'applestore_image': APPLE_APPSTORE,
            'app_image': APP_LOGO,
            'cta_url': url + '/community/' + str(community_id),
            'unsubscribe_url': url + '/unsubscribe_from_email?m=' + encrypt(
                user_id) + '&code=mail_has_installed_app',
        }
        template = get_template("mails/community_confirmation_email_2.html").render(email_context)

        to = [email]
        # to = ['himanshu@likeminds.community']

        send_email(subject, template, to)
        print(email_context)
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)


