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
	context={"subject":"Greetings from collabmates"}
	t = get_template("mails/welcome_mail_zero.html").render()
	msg = EmailMultiAlternatives("Greetings from collabmates",
	                                 t,
	                                 "hello@collabmates.com",
	                                 ['mahesh61437mahe@gmail.com'],
	                                 )
	msg.attach_alternative(t, "text/html")
	return msg.send(fail_silently)

@shared_task
def send_email_to_nominated_admin(NominatedAdmin,email,ProposedAdmin,CommunityName,community_id):
	time.sleep(5)
	fail_silently=True
	to = email
	context={"subject":"Greetings from collabmates"}
	t = get_template("mails/accept_admin_request.html").render({"NominatedAdmin":NominatedAdmin,"email":email,"ProposedAdmin":ProposedAdmin,"CommunityName":CommunityName,"community_id":community_id})
	msg = EmailMultiAlternatives("Greetings from collabmates",
	                                 t,
	                                 "hello@collabmates.com",
	                                 [to],
	                                 )
	msg.attach_alternative(t, "text/html")
	return msg.send(fail_silently)