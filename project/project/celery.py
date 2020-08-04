from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.development')

app = Celery('project')

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
    'send_pending_request_notification_at_8am': {
        'task': 'collabmates_api.notification.send_morning_pending_request_notification',
        'schedule': crontab(hour=15, minute=45),
        # minute="*/10" change to `crontab(minute=0, hour=0)` if you want it to run daily at midnight
        # 'schedule':120.0, #for testing purpose
    },
    'send_level_notification_at_8pm': {
        'task': 'collabmates_api.notification.send_morning_pending_request_notification',
        'schedule': crontab(hour=15, minute=59),
        # minute="*/10" change to `crontab(minute=0, hour=0)` if you want it to run daily at midnight
        # 'schedule':120.0, #for testing purpose
    },
    # 'pending_members_mail_at_8_AM': {
    #     'task': 'collabmates_api.tasks.pending_members_mail_new',
    #     'schedule': crontab(hour=8,minute=0),  #  minute="*/10" change to `crontab(minute=0, hour=0)` if you want it to run daily at midnight
    #     #'schedule':120.0, #for testing purpose
    # },
    # 'compute_rank_task_at_3_AM': {
    #     'task': 'collabmates_api.raw_queries.ranking_all_users_and_communities',
    #     'schedule': crontab(hour=3, minute=0),
    #     # minute="*/10" change to `crontab(minute=0, hour=0)` if you want it to run daily at midnight
    #     # 'schedule':120.0, #for testing purpose
    # },
}
app.conf.timezone = 'Asia/Kolkata'

beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'