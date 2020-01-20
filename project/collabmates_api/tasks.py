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
from utility.utils import android_app_download_link,ios_app_download_link

url  = settings.URL


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
                                 "Collabmates<hello@collabmates.com>",
                                 [to],
                                 )
    msg.attach_alternative(template, "text/html")
    # print("printing mag >>> ",msg.send(fail_silently))
    # return
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
    send_email(subject, template, to)

@shared_task
def send_email_for_new_collabcard_posted(context):

    '''function to send the email when a new collabcard is posted'''

    to = context['to']
    fail_silently = True
    context['android_app_download_link'] = android_app_download_link
    context['ios_app_download_link'] = ios_app_download_link
    subject = str(context['collabcard_creater']) + " has started a new Conversation in "+ str(context['community_name'])+ " community"
    template = get_template("mails/collabcard_posted.html").render(context)
    # msg = EmailMultiAlternatives(subject,
    #                              template,
    #                              "Collabmates<hello@collabmates.com>",
    #                              [to],
    #                              )
    # msg.attach_alternative(template, "text/html")
    # return msg.send(fail_silently)
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
                send_email(subject, template, to)
    return


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
        subject = "Thanks for downloading CollabMates App! Here's what to expect"
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
        send_email(subject, template, to)
    else:
        return


