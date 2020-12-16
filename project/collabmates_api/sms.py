from django.conf import settings
import requests
import urllib, requests, json
from celery import shared_task

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.utils import *
from utility.celery_beat_tasks import CeleryBeatTask
from project.celery import app
from .utilities.constants import *


gupshup_id = settings.GUPSHUP_ID
msg91_auth_key = settings.MSG91_AUTH_KEY
gupshup_pass = settings.GUPSHUP_PASS
OTP_TEMPLATE_ID = settings.OTP_TEMPLATE_ID
info_logger = LoggingWrapper.get_instance()


def send_sms(number, msg):
    msg = urllib.parse.quote(msg)

    generated_url = SMSGUPSHUP_SMS_URI.format(number, msg, gupshup_id, gupshup_pass)
    info_logger.info(generated_url)
    key = settings.GHUPSHUP_KEY
    context = {}
    success = False

    response = requests.get(generated_url)

    if response.status_code == 200:
        success = True
        response = response.text
        response_list = response.split("|")
        if response_list[0].strip() == "error":
            success = False

    context['success'] = success
    if not success:
        context['error_message'] = response

    return context


@shared_task
def send_community_confirmation_sms(phone_no, community_name, new_user_name, user_id):
    download_url = 'bit.ly/lmsdownload'
    msg = COMMUNITY_JOIN_SMS_1.format(new_user_name, community_name, download_url)

    notification_list = [
        'mail_has_installed_app'
    ]
    if check_notification_flag(user_id, notification_list, card_id=None, community_id=None):
        celerybeatask = CeleryBeatTask()
        task_name = str(user_id) + "_send_community_confirmation_sms"
        celerybeatask.terminate_task(task_name)
        args = [phone_no, community_name, new_user_name, user_id, task_name]
        task_path = "collabmates_api.sms.send_community_confirmation_sms_2"

        # date_time = time.time() + 80
        date_time = time.time() + (3 * 24 * 60 * 60)

        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)


@app.task
@shared_task
def send_community_confirmation_sms_2(phone_no, community_name, new_user_name, user_id, task_name):
    download_url = 'bit.ly/lmsdownload'
    msg = COMMUNITY_JOIN_SMS_2.format(new_user_name, community_name, download_url)

    notification_list = [
        'mail_has_installed_app'
    ]
    if check_notification_flag(user_id, notification_list, card_id=None, community_id=None):
        print(send_sms(phone_no, msg))
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)


def send_retry_otp(phone_no):
    """ Send otp from msg91 - retry case"""
    template_id = OTP_TEMPLATE_ID
    url = MSG91_SENDOTP_URI % (msg91_auth_key, template_id, phone_no)

    r = requests.get(url)
    context = {}
    result = json.loads(r.text)

    context = {}
    if result['type'] == 'success':
        context['success'] = True
        info_logger.info("MSG91 mobile generate otp success")
    else:
        info_logger.info("MSG91 mobile generate otp fail")
        context['success'] = False
        context['error_message'] = result['message']
    return context


def verify_retry_otp(phone_no, otp):
    ''' Verify otp from msg91 '''
    url = MSG91_VERIFYOTP_URI % (msg91_auth_key, str(phone_no), str(otp))

    r = requests.get(url)
    result = json.loads(r.text)
    context = {}
    if result['type'] == 'success':
        context['success'] = True
        info_logger.info("MSG91 mobile generate otp success")
    else:
        info_logger.info("MSG91 mobile generate otp fail")
        context['success'] = False
        context['error_message'] = result['message']

    return context
