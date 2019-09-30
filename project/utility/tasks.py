from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
import time
from django.template import Context
from django.conf import settings
from django.db.models import Q
from togther.models import *
from project.celery import app


url  = settings.URL


from threading import Timer

@shared_task
def hello():
    # print("hello, world")
    t = Timer(30.0, send_email)
    t.start()


@shared_task
def send_email():
    for i in range(10):
        print(i)

