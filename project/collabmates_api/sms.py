from django.conf import settings
import requests
import urllib
from celery import shared_task
from utility.utils import *
from utility.celery_beat_tasks import CeleryBeatTask
from project.celery import app


gupshup_id = settings.GUPSHUP_ID
gupshup_pass = settings.GUPSHUP_PASS

def send_sms(number,msg):

    msg = urllib.parse.quote(msg)

    generated_url  = 'http://enterprise.smsgupshup.com/GatewayAPI/rest?method=SendMessage&send_to={0}&msg={1}&msg_type=TEXT&userid={2}&auth_scheme=plain&password={3}&v=1.1&format=text'.format(number,msg,gupshup_id,gupshup_pass)
    print(generated_url)
    key = settings.GHUPSHUP_KEY
    context = {}
    success = False

    # generate_url = """http://enterprise.smsgupshup.com/apps/TwoFactorAuth/incoming.php?phone=%s&key=%s""" % (
    #     phone_no, key)
    response = requests.get(generated_url)
    print(response.content)

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
def send_community_confirmation_sms(phone_no,community_name,new_user_name,user_id):
    download_url = 'bit.ly/lmsdownload'
    msg = '''Congratulations, {0}! Your request to join {1} has been approved.

The next step for you is to download the LikeMinds app. The app allows you to get real-time notifications, join other chatrooms, start your own chatroom, attend events, and much more. 

Download app : {2}'''.format(new_user_name,community_name,download_url)

    notification_list = [
        'mail_has_installed_app'
    ]
    if check_notification_flag(user_id, notification_list, card_id=None, community_id=None):
        print(send_sms(phone_no, msg))
        celerybeatask = CeleryBeatTask()
        task_name = str(user_id) + "_send_community_confirmation_sms"
        celerybeatask.terminate_task(task_name)
        args = [phone_no,community_name,new_user_name,user_id,task_name]
        task_path = "collabmates_api.sms.send_community_confirmation_sms_2"

        # date_time = time.time() + 80
        date_time = time.time() + (3 * 24 * 60 * 60)

        kwargs = {}
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)

@app.task
@shared_task
def send_community_confirmation_sms_2(phone_no,community_name,new_user_name,user_id,task_name):
    download_url = 'bit.ly/lmsdownload'
    msg = '''Hi {0}! It’s been 3 days since you’ve been approved to join {1}. Download the LikeMinds app to get real-time notifications, join other relevant chatrooms, start your own chatroom, attend events, and much more. 

Download app : {2}'''.format(new_user_name,community_name,download_url)

    notification_list = [
        'mail_has_installed_app'
    ]
    if check_notification_flag(user_id, notification_list, card_id=None, community_id=None):
        print(send_sms(phone_no, msg))
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)

