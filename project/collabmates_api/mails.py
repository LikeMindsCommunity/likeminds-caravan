from celery import shared_task
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
import time
from django.template import Context
from django.conf import settings
from utility.tasks import send_email

@shared_task
def send_feedback_mail_to_webmaster(feedback):
    subject = 'Feedback from user'
    context = {
        'feedback': feedback,
    }
    template = get_template("mails/send_feedback_mail_to_webmaster.html").render(context)
    to = settings.TEAM
    send_email(subject, template, to)
    # print(template)
