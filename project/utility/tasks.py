from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
from togther.models import *
from django.conf import settings
from togther.models import *
from collabmates_api.notification import notification_to_complete_onboarding
from .utils import is_request_android,is_request_ios,is_request_pc, android_app_download_link
import time

url = settings.URL

is_beta=settings.IS_BETA

from threading import Timer

def mail_triger(member_id,request):
    print('member_id === ',member_id)

    android = is_request_android(request)
    ios = is_request_ios(request)
    pc = is_request_pc(request)

    t = Timer(10.0, onboarding_mail_for_new_users,[member_id,android,ios,pc])
    t.start()


def send_email(subject,template,to):
    fail_silently=True
    msg = EmailMultiAlternatives(subject,
                                template,
                                "Collabmates<hello@collabmates.com>",
                                [to],)
    msg.attach_alternative(template, "text/html")
    msg.send(fail_silently)
    return


@shared_task
def onboarding_mail_for_new_users(member_id,android,ios,pc):
    print('member_id ===>>>> ',member_id)

    user = User.objects.get(pk = member_id)
    user_legacy = User_Legacy.objects.filter(user_id=user)
    user_prof = User_Profession.objects.filter(user_id=user)
    user_int = User_Interest.objects.filter(user_id=user)
    user_gro = User_Geography.objects.filter(user_id=user)

    # if user does not have any tags , user has to do on-boarding
    if user_legacy.exists() and user_prof.exists() and user_int.exists() and user_gro.exists():

        ''' if user comes back in the middle of on-baording flow,
        make sure he continues the on-boarding'''
        return
    else:
        fail_silently=True
        if user.email:

            if user.userinfo.fcm_token and not pc:
                link = url
            elif user.userinfo.fcm_token and pc:
                link = url+"/newpage"
            elif pc :
                link = url + "/signup"
            else:
                if android:
                    link = "https://drive.google.com/open?id=1IQjFXjzxlUcMva7afZF_szwoYYaICdnf"
                elif ios:
                    link = url+"/communities"
                else:
                    link = url+"/onboarding"
            to = user.email
            subject="Thanks for joining CollabMates! Here's the next step"
            template = get_template("mails/onboarding_mail.html").render({"name":user.userinfo.name,
                                                                          'subject':subject,'url':link,
                                                                          })
            # msg = EmailMultiAlternatives(subject,
            #                                  template,
            #                                  "Collabmates<hello@collabmates.com>",
            #                                  [to],
            #                                  )
            # msg.attach_alternative(template, "text/html")
            # return msg.send(fail_silently)
            send_email(subject, template, to)
            notification_to_complete_onboarding(member_id) # notification to complete onboarding
            return


@shared_task
def new_member_request(member_id,community_id,form_response,ref_id=None,):

    # time.sleep(5)
    member = User.objects.get(pk=member_id)
    if ref_id:
        ref_person = User.objects.get(pk=ref_id)
        ref_name = ref_person.userinfo.name
    else:
        ref_name = ''

    community = Community.objects.get(pk=community_id )
    community_name = community.name

    member_name = member.userinfo.name
    fail_silently = True
    community_link=url+"/community/"+str(community_id)
    subject = "New Member Request in Community "+ str(community_name)
    if not ref_id:
        if community.hide_community == '3':

            text = str(member_name)+ ' has shown interest in '+str(community_name) + ' community and is not referred by anyone'
        elif community.hide_community == '0' or community.hide_community == '1' or community.hide_community == '4':
            if community.hide_community == '1':
                text = str(member_name)+ ' has request to join '+str(community_name) + ' community (Hidden) and is not referred by anyone'
            else:
                text = str(member_name)+ ' has request to join '+str(community_name) + ' community and is not referred by anyone'
        else:
            text = str(member_name) + ' has request to join ' + str(community_name) + ' community and is not referred by anyone'

    else:
        if community.hide_community == '3':

            text = str(member_name) + ' has shown interest in ' + str(
                community_name) + ' community and is referred by ' + str(ref_name)
        elif community.hide_community == '0' or community.hide_community == '1' or community.hide_community == '4':
            if community.hide_community == '1':
                text = str(member_name) + ' has request to join ' + str(
                    community_name) + ' community (Hidden) and is referred by ' + str(ref_name)
            else:
                text = str(member_name) + ' has request to join ' + str(
                    community_name) + ' community and is referred by ' + str(ref_name)
        else:
            text = str(member_name) + ' has request to join ' + str(
                community_name) + ' community and is referred by ' + str(ref_name)


    res = {}
    for response in form_response:
        res[response['key']] = response['value']

    template = get_template("mails/new_member_request.html").render({"member_name": member_name,"member_id": member_id,'ref_name':ref_name,
                                                                  'subject': subject, 'community_name': community_name, 'community_id': community_id,
                                                                  'text':text,'community_link':community_link,
                                                                  'result':res, 'url': url,})
    
    if url == "https://beta.collabmates.com":
        to_list = ['mahesh61437mahe@gmail.com']

    elif url == "https://www.collabmates.com":
        to_list = ['nipungoyal.iitd@gmail.com','hrshshukl@gmail.com']
    else:
        to_list = ['mahesh61437mahe@gmail.com','rastogi.fresh88@gmail.com']
    msg = EmailMultiAlternatives(subject,
                                 template,
                                 "Collabmates<hello@collabmates.com>",

                                 to_list,
                                 )

    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)

    # send_email(subject, template, to=to_list)


@shared_task
def member_request_approval_or_denied(user_id,community_id,approved):

    user = User.objects.get(pk=user_id)
    community = Community.objects.get(pk=community_id )

    to = user.email
    if approved:
        subject = "Congrats! you are now part of "+community.name+" community"
    else:
        subject = "Sorry! your request to join "+community.name+" has been rejected"

    link_text = ''
    url = settings.URL
    if user.userinfo.fcm_token:
        if approved:
            url = url + "/community/"+str(community_id)
            link_text = 'Start Engaging'
        else:
            link_text = 'Explore Communties'
    else:
        url = android_app_download_link
        link_text = 'Download App'

    template = get_template("mails/member_approval_or_declined.html").render({"user_name": user.userinfo.name,
                                                                  'community_name':community.name,
                                                                  'purpose':community.purpose,
                                                                  'subject': subject, 'url': url,
                                                                  'link_text':link_text,
                                                                  'approved':approved
                                                                  })

    send_email(subject, template, to)
    return

@shared_task
def send_mail_for_report_abuse__on_collabcard(user_name,collabcard_message,report_tag,community_name,community_url,report_reason=None):

    '''function to send a mail when the user report abuse on collabcard'''

    subject=str(user_name)+" reported "+report_tag
    if report_reason:
        text=str(user_name)+" reported "+str(report_tag)+" for collabcard:"+str(collabcard_message)+" in community "+str(community_name)+". The feedback given By user is "+str(report_reason)
    else:
        text = str(user_name) + " reported " + str(report_tag) + " for collabcard:" + str(collabcard_message)+" in community "+str(community_name)
    context={
        'subject':subject,
        'text':text,
        'community_link':community_url
    }
    template = get_template("mails/report_abuse.html").render(context)
    if not is_beta:
        to="nipun@collabmates.com"
    else:
        to="mahesh61437mahe@gmail.com"
    send_email(subject, template, to)
    print("Executed")