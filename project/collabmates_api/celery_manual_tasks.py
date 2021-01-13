from __future__ import absolute_import, unicode_literals
from celery import Celery
import os
from django.http.response import JsonResponse
from celery import shared_task

from dotenv import load_dotenv
load_dotenv()

app = Celery('project', backend='amqp', broker=os.getenv('BETA_BROKER_URL'))

def dummy_task(request):
    dummy_celery_task.apply_async()
    return JsonResponse({'success': True})

@shared_task
def dummy_celery_task():
    print("celery task recieved")
