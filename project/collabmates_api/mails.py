from django.template.loader import get_template
from django.conf import settings

from django.shortcuts import render
# from django.core.mail import EmailMultiAlternatives
import time
# from django.template import Context
from togther.models import *

from project.celery import app

from utility.states import *
from utility.celery_beat_tasks import CeleryBeatTask
from utility.tasks import send_email
from utility.utils import (android_app_download_link, ios_app_download_link, get_user_email,add_relative_time_to_epoch,
                           get_next_day_time,check_notification_flag)
from utility.encryption import encrypt,decrypt

from .static_files import GOOGLE_PLAYSTORE,APPLE_APPSTORE,APP_LOGO
from celery import shared_task
import ast
from datetime import datetime,timedelta

url = settings.URL
is_beta = settings.IS_BETA
# url = 'https://beta.likeminds.community'

import time

@shared_task
def send_feedback_mail_to_webmaster(feedback_id):
    subject = '[Feedback] from likeMinds user'
    feedback_instance = userFeedback.objects.get(id=feedback_id)
    # mail_images = ast.literal_eval(mail_images)
    context = {
        'feedback': feedback_instance
    }
    if feedback_instance.images:
        print(feedback_instance.images)

        context['images'] = ast.literal_eval(feedback_instance.images)
        print(context['images'])

    template = get_template("mails/send_feedback_mail_to_webmaster.html").render(context)

    if is_beta:
        to = ['himanshu@likeminds.community']
    else:
        to = settings.TEAM

    send_email(subject, template, to)
    print(template)




@app.task
@shared_task
def send_8am_level_mails_to_admin_scheduler(community_id, start_time, level=1,day=0,counter=0):

    if day == 0:
        counter = counter + 1
        # start_time = get_next_day_time(start_time,hours=8,minutes=0)
        # start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=0, days=2)
        start_time = add_relative_time_to_epoch(start_time, minutes=2, hours=0, days=0)
        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + "_send_8am_level_mails_to_admin"
        celerybeatask.terminate_task(task_name)
        day = 2
        args = [community_id, start_time, day,level,day,counter]
        task_path = "collabmates_api.mails.send_8am_level_mails_to_admin_scheduler"
        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=start_time, interval=False, crontab=True)
        return

    elif day == 2:
        send_8am_level_mails_to_admin_mailer(community_id, day, level)
        counter = counter + 1
        # start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=0, days=2)
        start_time = add_relative_time_to_epoch(start_time, minutes=2, hours=0, days=0)
        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + "_send_8am_level_mails_to_admin"
        celerybeatask.terminate_task(task_name)
        day = 4
        args = [community_id, start_time, day,level,day,counter]
        task_path = "collabmates_api.mails.send_8am_level_mails_to_admin_scheduler"
        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=start_time, interval=False, crontab=True)
        return

    elif day == 4:
        send_8am_level_mails_to_admin_mailer(community_id, day, level)
        counter = counter + 1
        # start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=0, days=2)
        start_time = add_relative_time_to_epoch(start_time, minutes=2, hours=0, days=0)

        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + "_send_8am_level_mails_to_admin"
        celerybeatask.terminate_task(task_name)
        day = 6
        args = [community_id, start_time, day,level,day,counter]
        task_path = "collabmates_api.mails.send_8am_level_mails_to_admin_scheduler"
        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=start_time, interval=False, crontab=True)
        return

    elif day == 6:
        send_8am_level_mails_to_admin_mailer(community_id, day, level)
        counter = counter + 1
        # start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=0, days=2)
        start_time = add_relative_time_to_epoch(start_time, minutes=2, hours=0, days=0)

        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + "_send_8am_level_mails_to_admin"
        celerybeatask.terminate_task(task_name)
        day = 8
        args = [community_id, start_time, day,level,day,counter]
        task_path = "collabmates_api.mails.send_8am_level_mails_to_admin_scheduler"
        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=start_time, interval=False, crontab=True)
        return


    elif day == 8 and level < 3:
        send_8am_level_mails_to_admin_mailer(community_id, day, level)
        counter = counter + 1
        # start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=0, days=2)
        start_time = add_relative_time_to_epoch(start_time, minutes=2, hours=0, days=0)

        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + "_send_8am_level_mails_to_admin"
        celerybeatask.terminate_task(task_name)
        day = 10
        args = [community_id, start_time, day,level,day,counter]
        task_path = "collabmates_api.mails.send_8am_level_mails_to_admin_scheduler"
        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=start_time, interval=False, crontab=True)
        return

    elif day == 10 and level < 3:
        send_8am_level_mails_to_admin_mailer(community_id, day, level)
        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + "_send_8am_level_mails_to_admin"
        celerybeatask.terminate_task(task_name)
        return



def send_8am_level_mails_to_admin_mailer(community_id, days, level):
    community_instance = Community.objects.get(id=community_id)
    members = Members.objects.filter(community_id=community_id, state=1)

    for member in members:
        if level == 1:
            template = 'mails/level_1_email.html'
            subject = str(member.userinfo.name) + ", reminding you to invite the inner circle!"
        elif level == 2:
            template = 'mails/level_2_email.html'
            subject = str(member.userinfo.name) + ", reminding you to set up your directory!"
        elif level == 3:
            template = 'mails/level_3_email.html'
            subject = str(member.userinfo.name) + ", reminding you to get 10 member profiles in directory!"
        else:
            template = 'mails/level_4_email.html'
            subject = str(member.userinfo.name) + ", let’s get your community off to a great start!"

        notification_list = [
            'send_8am_level_mails_to_admin_mailer'
        ]

        if check_notification_flag(member.member_id.id, notification_list, card_id=None, community_id=None):
            # subject = str(member.userinfo.name) + " is waiting for your response! "
            email_context = {
                'subject': subject,
                'member_name': member.userinfo.name,
                'date_of_unlock':days,
                'community_name': community_instance.name,
                'android_app_download_link': android_app_download_link,
                'ios_app_download_link': ios_app_download_link,
                'playstore_image': GOOGLE_PLAYSTORE,
                'applestore_image': APPLE_APPSTORE,
                'blog_link_1':'http://bit.ly/lmcm_guide',
                'app_image': APP_LOGO,
                'cta_url': url + '/community/' + str(community_id),
                'unsubscribe_url': url + '/unsubscribe_from_email?m=' + encrypt(member.member_id) + '&code=send_8am_level_mails_to_admin_mailer'
            }
            template = get_template(template).render(email_context)
            email = get_user_email(member.member_id)
            to = [email]
            # to = ['himanshu@likeminds.community']
            send_email(subject, template, to)


@shared_task
def send_created_community_email_to_team(context):
    subject = '[New Community] on LikeMinds App'
    context['url'] = url
    template = get_template("mails/send_community_created_mail_to_webmaster.html").render(context)

    if is_beta:
        to = ['himanshu@likeminds.community',]
    else:
        to = settings.TEAM

    print(context,to)

    send_email(subject, template, to)
    # print(template)

@shared_task
def send_report_mail_to_team(subject, report_instance_id):
    report_instance = Report.objects.get(id=report_instance_id)
    context = {
        'report':report_instance,
        'url':url
    }

    template = get_template("mails/send_report_mail_to_team.html").render(context)

    if is_beta:
        to = ['himanshu@likeminds.community',]
    else:
        to = settings.TEAM

    print(subject,context,to)

    send_email(subject, template, to)
    # print(template)