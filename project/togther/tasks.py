from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
import time
from django.template import Context

@shared_task
def send_email_to_proposed_admin(NominatedAdmin,email,ProposedAdmin,CommunityName,proposedAdminState,community_id):
    time.sleep(5)
    fail_silently=True
    to = email
    subject =str(NominatedAdmin)+ " has accepted your invitation to become a promoter for "+str(CommunityName)+" community"
    
    if proposedAdminState == 1:
        template = get_template("mails/accepted_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id})
    elif proposedAdminState == 2:
        template = get_template("mails/accepted_temp_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id})
    msg = EmailMultiAlternatives(subject,
                                     template,
                                     "hello@collabmates.com",
                                     [to,'mahesh61437mahe@gmail.com'],
                                     )
    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)