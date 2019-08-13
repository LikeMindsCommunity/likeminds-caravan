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


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

app.conf.beat_schedule = {
    'pending_members_mail_at_8_AM': {
        'task': 'collabmates_api.tasks.pending_members_mail',
        # 'schedule': crontab(minute="*/10"),  # change to `crontab(minute=0, hour=0)` if you want it to run daily at midnight
        'schedule':60.0,
    },
}

app.conf.timezone = 'UTC'