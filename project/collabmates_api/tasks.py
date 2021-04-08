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
from cms.models import MessageTemplate
from project.celery import app
from utility.tasks import send_email
from utility.utils import (android_app_download_link, ios_app_download_link,
                           is_LG_or_LP_community, is_IG_community,angellist_link,linkedIn_link,get_user_email,
                           android_app_download_link,ios_app_download_link,check_notification_flag)
from utility.states import (collabcard_states, member_states, community_states,
                            card_types, chatroom_states, chatroom_actions, member_rights, manager_rights,
                            moderation_history_types, report_Action_Types, report_Types, multi_select_poll_states)
from utility.celery_beat_tasks import CeleryBeatTask
from django.http import JsonResponse
from django.contrib.auth.models import User
from togther.models import Collabcard, userMemberRightsHistory, Members, Community
from utility.encryption import encrypt, decrypt
from .static_files import GOOGLE_PLAYSTORE,APPLE_APPSTORE,APP_LOGO
from .user_moderation_rights import (get_related_reports_for_user, check_admin_delete_right,
                                     check_admin_approve_right, check_admin_edit_community_right)
import json
import requests
from .serializers import CollabcardPollsSerializer
from .notification import get_title_from_collabcard,send_intro_room_evening_notifications
from .static_text import CREATE_CONVERSATION_API_END_POINT, HOURS_24
from utility.mail_category_constants import *
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()
url = settings.URL


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

    setting_category = MAIL_CATEGORY_BETA if settings.IS_BETA else MAIL_CATEGORY_PROD

    categories = [
        setting_category,
        f"{setting_category} - {MAIL_CATEGORY_VERIFY_EMAIL}"
    ]

    to = [email]
    send_email(subject, template, to, categories=categories)


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

                setting_category = MAIL_CATEGORY_BETA if settings.IS_BETA else MAIL_CATEGORY_PROD

                categories = [
                    f"{setting_category} - {MAIL_CATEGORY_USER_ENGAGEMENT} - {MAIL_CATEGORY_TAGGED}",
                    f"{setting_category} - {MAIL_CATEGORY_USER_ENGAGEMENT}",
                    setting_category,
                ]

                send_email(subject, template, to, categories=categories)

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

            setting_category = MAIL_CATEGORY_BETA if settings.IS_BETA else MAIL_CATEGORY_PROD

            categories = [
                f"{setting_category} - {MAIL_CATEGORY_USER_ENGAGEMENT} - {MAIL_CATEGORY_MESSAGE_WAITING}",
                f"{setting_category} - {MAIL_CATEGORY_USER_ENGAGEMENT}",
                setting_category,
            ]

            send_email(subject, template, to, categories=categories)

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
def send_community_confirmation_email_2(user_id, community_id, task_name, *args, **kwargs):
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


@app.task
def send_poll_results_announcement_mail(card_id, task_name):
    """ function to send poll reuslts annoucement mail for users who missed or didn't see the poll results yet """

    card_instance = Collabcard.objects.get(pk=card_id)

    if card_instance.is_deleted or card_instance.is_pending:
        return

    community_instance = card_instance.community
    community_id = community_instance.id
    community_owner = Members.objects.filter(community_id=community_instance,
                                             state=member_states.ADMIN, is_owner=True)

    if community_owner.exists():
        community_owner_instance = community_owner[0].member_id
    else:
        community_owner = Members.objects.filter(community_id=community_instance,
                                                 state=member_states.ADMIN).order_by("id")
        community_owner_instance = community_owner[0].member_id

    community_owner_name = community_owner_instance.userinfo.name

    card_creator = card_instance.user
    card_creator_id = card_creator.id
    card_creator_name = card_creator.userinfo.name

    card_polls = CollabcardPolls.objects.filter(card=card_instance).order_by("id")

    voted_members = set(MemberPollVotes.objects.filter(card=card_id).values_list("user", flat=True))
    followed_members = set(collabcardState.objects.filter(
        card=card_id, mute_status=False, external_follow=True).values_list("user", flat=True))

    final_users_list = voted_members | followed_members

    if card_creator_id not in final_users_list:
        final_users_list.add(card_creator_id)

    is_multi_select = False
    multi_select_text = ""
    if card_instance.multiple_select_no is not None or card_instance.multiple_select_state is not None:
        is_multi_select = True

    if is_multi_select:
        multiple_select_state = card_instance.multiple_select_state
        multiple_select_no = card_instance.multiple_select_no if card_instance.multiple_select_no else 0
        if multiple_select_state == multi_select_poll_states.EXACTLY:
            multi_select_text = f"(Select exactly {multiple_select_no} options)"
        elif multiple_select_state == multi_select_poll_states.AT_LEAST:
            multi_select_text = f"(Select atleast {multiple_select_no} options)"
        elif multiple_select_state == multi_select_poll_states.AT_MAX:
            multi_select_text = f"(Select at most {multiple_select_no} options)"


    polls_list = []
    for poll in card_polls:
        poll_dict = CollabcardPollsSerializer(poll=poll, user=None, card=card_instance)
        polls_list.append(poll_dict)

    for user_id in final_users_list:
        user_instance = User.objects.get(pk=user_id)
        email = get_user_email(user_id)

        notification_name = 'poll_results_announcement_mail'

        first_name = user_instance.userinfo.name.split(" ")[0]
        notification_flag = memberNotificationFlag.objects.filter(code=notification_name, card=card_instance,
                                                                  member=user_instance, flag=True).exists()
        subject = f'{first_name}, results for {card_instance.header}'
        if not notification_flag:
            email_context = {
                'subject': subject,
                'card_instance': card_instance,
                'poll_options': polls_list,
                'member_name': first_name,
                'card_creator_name': card_creator_name,
                'community_owner_name': community_owner_name,
                'community_name': community_instance.name,
                'is_multi_select': is_multi_select,
                'multi_select_text': multi_select_text,
                'android_app_download_link': android_app_download_link,
                'ios_app_download_link': ios_app_download_link,
                'playstore_image': GOOGLE_PLAYSTORE,
                'applestore_image': APPLE_APPSTORE,
                'app_image': APP_LOGO,
                'cta_url': url + '/community/' + str(community_id),
                'unsubscribe_url': url + '/unsubscribe_from_email?m=' + encrypt(
                    user_id) + '&code=poll_results_announcement_mail',
            }
            template = get_template("mails/poll_results_announcement.html").render(email_context)

            to = [email]
            fail_silently = False
            msg = EmailMultiAlternatives(subject,
                                         template,
                                         f"{community_instance.name}<hello@likeminds.community>",
                                         to)
            msg.attach_alternative(template, "text/html")

            setting_category = MAIL_CATEGORY_BETA if settings.IS_BETA else MAIL_CATEGORY_PROD

            categories = [
                f"{setting_category} - {MAIL_CATEGORY_USER_ENGAGEMENT} - {MAIL_CATEGORY_POLL_RESULTS}",
                f"{setting_category} - {MAIL_CATEGORY_USER_ENGAGEMENT}",
                setting_category,
            ]

            msg.categories = categories

            msg.send(fail_silently)

    card_instance.disable_poll_announcement_mail = True
    card_instance.save()

    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)


@shared_task
def update_pending_chatrooms_and_report_count(community_id):
    """ function to update pending chatrooms and open reports count count for all promoters in community """
    community = Community.objects.get(pk=community_id)

    update_pending_chatroom_count_for_promoters(community)
    update_report_count_for_all_promoters(community)


@shared_task
def update_pending_chatroom_count_for_promoters(community_id):
    """ function to update pending chatrooms count for all promoters in community """

    if not isinstance(community_id, Community):
        community = Community.objects.get(pk=community_id)
    else:
        community = community_id
    user_list = get_users_with_right(community, manager_rights.MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS)

    pending_chatrooms = Collabcard.objects\
        .filter(community=community_id, is_pending=True, is_deleted=False)\
        .filter(Q(attachment_count=0) | Q(attachments_uploaded=True))\
        .count()

    Member_Engage.objects.filter(member_id__in=user_list,
                                 community_id=community).update(pending_chatrooms=pending_chatrooms,
                                                                updated_at=time.time())

    member_state_list = [member_states.MEMBER, member_states.KNOWN_NOMINATED_PROMOTER, member_states.PROFILE_UNAVAILABLE]
    Member_Engage.objects.filter(community_id=community,
                                 member_state__in=member_state_list).update(pending_chatrooms=0,
                                                                            open_reports=0,
                                                                            updated_at=time.time())


def get_users_with_right(community, right_state):
    user_list = list(userAdminRights.objects.filter(community=community,
                                                    right__state=right_state).distinct("user").values_list("user__id"))
    return user_list


@shared_task
def update_report_count_for_all_promoters(community_id=None, report_id=None):
    """ function to update open reports count for all promoters in community """

    if community_id is None and report_id is None:
        return

    if community_id is None:
        report_instance = Report.objects.get(pk=report_id)
        community = report_instance.community

    elif not isinstance(community_id, Community):
        community = Community.objects.get(pk=community_id)
    else:
        community = community_id

    promoters = Members.objects.filter(community_id=community, state=member_states.ADMIN)
    for promoter in promoters:
        is_owner = promoter.is_owner
        parent_cm_list = json.loads(promoter.parent_cm_list) if promoter.parent_cm_list else []

        update_report_count_in_member_engage(promoter.member_id, community,
                                             is_owner=is_owner, parent_cm_list=parent_cm_list)


def update_report_count_in_member_engage(user, community, is_owner=False, parent_cm_list=None):

    if parent_cm_list is None:
        parent_cm_list = []

    has_right_0 = check_admin_delete_right(user=user, community=community)
    has_right_1 = check_admin_approve_right(user=user, community=community)
    has_right_2 = check_admin_edit_community_right(user=user, community=community)

    if not has_right_0 and not has_right_1 and has_right_2:
        report_count = 0
    else:
        report_count = get_related_reports_for_user(user_id=user, community_id=community, has_right_0=has_right_0,
                                                    is_owner=is_owner, has_right_1=has_right_1, has_right_2=has_right_2,
                                                    parent_cm_list=parent_cm_list, return_reports_count=True)

    Member_Engage.objects.filter(member_id=user,
                                 community_id=community).update(open_reports=report_count,
                                                                updated_at=time.time())


def request_api(method, api_url, headers, payload):
    response = requests.request(method, api_url, headers=headers, data=json.dumps(payload))

    return response


@app.task
def task_to_send_intro_notifications():
    # print("chal ja bhai")
    send_intro_room_evening_notifications()
