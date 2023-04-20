from django.template.loader import get_template
from django.conf import settings

from django.shortcuts import render
# from django.core.mail import EmailMultiAlternatives
import time
# from django.template import Context
from external_services.email.email_wrapper import MailHelper
from togther.models import *

from project.celery import app

from utility.states import *
from utility.celery_beat_tasks import CeleryBeatTask
from utility.tasks import send_email
from utility.utils import (android_app_download_link, ios_app_download_link, get_user_email,add_relative_time_to_epoch,
                           get_next_day_time,check_notification_flag)
from utility.encryption import encrypt, decrypt

from .static_files import GOOGLE_PLAYSTORE, APPLE_APPSTORE, APP_LOGO
from celery import shared_task
import json
from utility.mail_category_constants import *
from datetime import datetime, timedelta

url = settings.URL
is_beta = settings.IS_BETA


@shared_task
def send_feedback_mail_to_webmaster(feedback_id):

    subject = '[Feedback] from likeMinds user'
    feedback_instance = userFeedback.objects.get(id=feedback_id)
    user_id = feedback_instance.user_id
    mobile_filter = ModelUtilities.get_model_filter(userMobiles, {'user_id': user_id, 'state': 1})
    email_filter = ModelUtilities.get_model_filter(userEmails, {'user_id': user_id, 'email_state': 1})
    user_filter = ModelUtilities.get_model_filter(Userinfo, {'user_id_id': user_id})
    user_mobiles_context = []
    user_emails_context = []

    for instance in email_filter:
        user_emails_context.append(instance.email)

    for mobile_instance in mobile_filter:
        mobile = dict()
        mobile['country_code'] = mobile_instance.country_code
        mobile['mobile_no'] = mobile_instance.mobile_no
        user_mobiles_context.append(mobile)

    user_info_context = {
        'user_id': user_id,
        'name': user_filter.first().name
    }

    context = {
        'feedback': feedback_instance,
        'user_info_context': user_info_context,
        'user_mobiles_context': user_mobiles_context,
        'user_emails_context': user_emails_context
    }
    reply_to = None

    if len(user_emails_context) > 0:
        reply_to = user_emails_context

    if feedback_instance.images:
        context['images'] = json.loads(feedback_instance.images)
    template = get_template("mails/send_feedback_mail_to_webmaster.html").render(context)

    if is_beta:
        to = ['himanshu@likeminds.community']
    else:
        to = settings.TEAM

    categories = MailHelper.get_email_category_list_using_category_subcategory(EmailCategories.APP_LEVEL,
                                                                               EmailSubCategories.FEEDBACK)

    send_email(subject=subject, template=template, to_mails_list=to, reply_to=reply_to, categories=categories)


@shared_task
def send_created_community_email_to_team(context):
    subject = '[New Community] on LikeMinds App'
    context['url'] = url
    template = get_template("mails/send_community_created_mail_to_webmaster.html").render(context)

    if is_beta:
        to = ['himanshu@likeminds.community', ]
    else:
        to = settings.TEAM

    categories = MailHelper.get_email_category_list_using_category_subcategory(EmailCategories.APP_LEVEL,
                                                                               EmailSubCategories.NEW_COMMUNITY)

    send_email(subject, template, to, categories=categories)


@shared_task
def send_report_mail_to_team(subject, report_instance_id):
    report_instance = Report.objects.get(id=report_instance_id)
    context = {
        'report':report_instance,
        'url':url
    }

    template = get_template("mails/send_report_mail_to_team.html").render(context)

    if is_beta:
        to = ['himanshu@likeminds.community',
              'growth@likeminds.community',
              "nipun@likeminds.community",
              'mahesh@likeminds.community']
    else:
        to = settings.TEAM

    print(subject, context, to)

    send_email(subject, template, to)
    # print(template)
