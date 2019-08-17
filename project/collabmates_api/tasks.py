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


url  = settings.URL


# @shared_task
# def send_email():
# 	fail_silently=True
# 	subject="Thanks for joining CollabMates! Here's what to expect"
# 	template = get_template("mails/collabcard_posted.html").render()
# 	msg = EmailMultiAlternatives(subject,
# 	                                 template,
# 	                                 "hello@collabmates.com",
# 	                                 [to],
# 	                                 )
# 	msg.attach_alternative(template, "text/html")
# 	return msg.send(fail_silently)

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
                                 "hello@collabmates.com",
                                 [to],
                                 )
    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)

@shared_task
def send_email_to_admin_of_community(CommmunityAdminName,CommunityName,email):
    time.sleep(5)
    fail_silently=True
    to = email
    subject = "Congrats! "+CommunityName+" community is now live"
    template = get_template("mails/create_community_as_admin.html").render({"CommmunityAdminName":CommmunityAdminName,"CommunityName":CommunityName})
    msg = EmailMultiAlternatives(subject,
                                 template,
                                 "hello@collabmates.com",
                                 [to],
                                 )
    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)

@shared_task
def send_email_to_temp_admin_of_community(CommmunityAdminName,CommunityName,email):
    time.sleep(5)
    fail_silently=True
    to = email
    subject = "Congrats! "+CommunityName+" community is now live"
    template = get_template("mails/create_community_as_member.html").render({"CommmunityAdminName":CommmunityAdminName,"CommunityName":CommunityName})
    msg = EmailMultiAlternatives(subject,
                                 template,
                                 "hello@collabmates.com",
                                 [to],
                                 )
    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)


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
    msg = EmailMultiAlternatives(subject,
                                 template,
                                 "hello@collabmates.com",
                                 [to],
                                 )
    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)

@shared_task
def send_email_for_new_collabcard_posted(context):

    '''function to send the email when a new collabcard is posted'''

    to = context['to']
    fail_silently = True
    subject = str(context['collabcard_creater']) + " has started a new Conversation in "+ str(context['community_name'])+ " community"
    template = get_template("mails/collabcard_posted.html").render(context)
    msg = EmailMultiAlternatives(subject,
                                 template,
                                 "hello@collabmates.com",
                                 [to],
                                 )
    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)


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
                    template = get_template("mails/single_pending_member.html").render(
                        {'promoter': admin.member_id.userinfo.name,
                         'promoter_image': admin.member_id.userinfo.image_file.url,
                         'pending_members': pending_members_in_community[0],
                         'pending_member_count': pending_count,
                         'community': admin.community_id,
                         'url':url})
                    subject = str(pending_members_in_community[0].member_id.userinfo.name)+" has requested to join "+str(admin.community_id.name)
                elif pending_count > 1:
                    subject = str(pending_count)+' new members have requested to join '+str(admin.community_id.name)
                    template = get_template("mails/multiple_pending_members_mail.html").render(
                        {'promoter': admin.member_id.userinfo.name,
                         'promoter_image': admin.member_id.userinfo.image_file.url,
                         'pending_members': pending_members_in_community[:4],
                         'pending_member_count': pending_count,
                         'remaining_pending_requests': pending_count-4,
                         'community_name': admin.community_id.name,
                         'url':url})
                print(subject)

                msg = EmailMultiAlternatives(subject,
                                             template,
                                             "hello@collabmates.com",
                                             ['mahesh61437mahe@gmail.com',admin.member_id.userinfo.email],
                                             )
                msg.attach_alternative(template, "text/html")
                msg.send(fail_silently)
    return

