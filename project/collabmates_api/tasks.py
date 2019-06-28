from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
import time
from django.template import Context
@shared_task
def send_email():
	time.sleep(300)
	fail_silently=True
	subject="Thanks for joining CollabMates! Here's what to expect"
	template = get_template("mails/welcome_mail_zero.html").render()
	msg = EmailMultiAlternatives(subject,
	                                 template,
	                                 "hello@collabmates.com",
	                                 [to],
	                                 )
	msg.attach_alternative(template, "text/html")
	return msg.send(fail_silently)

@shared_task
def send_email_to_nominated_admin(NominatedAdmin,email,ProposedAdmin,CommunityName,community_id):
	time.sleep(5)
	fail_silently=True
	to = email
	subject =str(ProposedAdmin)+ " has proposed you as a promoter of "+str(CommunityName)+" community"
	template = get_template("mails/accept_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id})
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