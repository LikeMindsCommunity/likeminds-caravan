from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
load_dotenv()
from django.conf import settings
# from kombu import Exchange, Queue
# set the default Django settings module for the 'celery' program.
# set the default Django settings module for the 'celery' program.

if settings.IS_BETA:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.beta')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.production')

app = Celery('project', backend='amqp', broker=os.getenv('BROKER_URL'))
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
# import collabmates_api.notification.send_morning_pending_request_notification


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


app.conf.beat_schedule = {
    """
    '<task_name>': {
        'task': '<task path>',
        'schedule': crontab(hour=8, minute=0),
        minute="*/10" change to `crontab(minute=0, hour=0)` if you want it to run daily at midnight
    }
    """    
    # 'send_pending_request_notification_at_8am': {
    #     'task': 'collabmates_api.notification.send_morning_pending_request_notification',
    #     'schedule': crontab(hour=8, minute=0),
    # },
    # 'send_uninstall_notification_3am': {
    #     'task': 'cms.utils.find_uninstall_devices',
    #     'schedule': crontab(hour=3, minute=0),
    # },
    # 'new_test_task_for_intro_room': {
    #     'task': 'collabmates_api.tasks.task_to_send_intro_notifications',
    #     'schedule': crontab(hour=20, minute=53),
    # },
    # 'send_daily_emails': {
    #     'task': 'collabmates_api.tasks.send_daily_emails',
    #     'schedule': crontab(hour=10, minute=0),
    # },
    # 'remove_guest_users_sdk': {
    #     'task': 'collabmates_api.tasks.remove_guest_users_sdk',
    #     'schedule': crontab(hour=2, minute=0),
    # },
    # 'international_otp_generate_requests_blocked_task': {
    #     'task': 'collabmates_api.tasks.international_otp_generate_requests_blocked_task',
    #     'schedule': crontab(hour=8, minute=0),
    # },
    'mau_tracking': {
        'task': 'collabmates_api.cron.mau_tracker.track',
        'schedule': crontab(minute='*/1'),
    }
}

app.conf.timezone = 'Asia/Kolkata'

app.conf.enable_utc = False

beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

app.conf.update(
    task_routes={
        'proj.tasks.add': {'queue': 'celery', 'delivery_mode': 'transient'}
    }
)

app.conf.update(
    task_acks_late = True
)

app.conf.update(
    result_persistent=False
)

app.conf.update(
    task_ignore_result=True
)

app.conf.update(
    result_expires=60
)
