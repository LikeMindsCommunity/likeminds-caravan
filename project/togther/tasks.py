from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
import time
from django.template import Context
from django.conf import settings
from togther.models import *
from utility.tasks import send_email
url  = settings.URL
from collabmates_api.notification import notification_after_compute_rank
from utility.utils import android_app_download_link,ios_app_download_link

# def send_email(subject,template,to):
#     fail_silently=True
#     msg = EmailMultiAlternatives(subject,
#                                 template,
#                                 "Collabmates<hello@collabmates.com>",
#                                 [to],)
#     msg.attach_alternative(template, "text/html")
#     return msg.send(fail_silently)


@shared_task
def send_email_to_proposed_admin(NominatedAdmin,email,ProposedAdmin,CommunityName,proposedAdminState,community_id):
    time.sleep(5)
    fail_silently=True
    to = email
    subject =str(NominatedAdmin)+ " has accepted your invitation to become a promoter for "+str(CommunityName)+" community"
    
    if proposedAdminState == 1:
        template = get_template("mails/accepted_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id,'url':url})
    elif proposedAdminState == 2:
        template = get_template("mails/accepted_temp_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id,'url':url})
    # msg = EmailMultiAlternatives(subject,
    #                                  template,
    #                                  "hello@collabmates.com",
    #                                  [to],
    #                                  )
    # msg.attach_alternative(template, "text/html")
    # return msg.send(fail_silently)
    to = [to]
    send_email(subject, template, to)



@shared_task
def send_mail_after_rank_computation(user_id):

    user  = Userinfo.objects.get(user_id = user_id)
    user_name = user.name
    user_email = user.email
    android = True if user.mobile_os == 'Android' or user.mobile_os == 'Both' else False

    fail_silently=True
    to = user_email

    if android:
        subject = 'Access to the first version of LikeMinds App'
        template = get_template("mails/android_apk.html").render({"name":user_name,
                                                                  'android_app_download_link':android_app_download_link,'ios_app_download_link':ios_app_download_link})
    else:
        subject = 'Access to the first version of LikeMinds App'
        template = get_template("mails/ios_users.html").render({"name":user_name,'url':url,
                                                                'android_app_download_link':android_app_download_link,
                                                                'ios_app_download_link':ios_app_download_link})
    # msg = EmailMultiAlternatives(subject,
    #                              template,
    #                              "Collabmates<hello@collabmates.com>",
    #                              [to],
    #                              )
    # msg.attach_alternative(template, "text/html")
    count = 0
    while True:
        communities = Community_Rank.objects.filter(member_id = user_id)
        if communities.exists():
            # send_email(subject, template, to)
            notification_after_compute_rank(user_id=user_id)
            return
        elif count == 30:
            return
        else:
            count += 1
            time.sleep(30)


@shared_task
def send_chatroom_owner_mail():
    pass