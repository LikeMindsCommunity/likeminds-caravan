from .base import *

DEBUG = True

URL = "https://beta.collabmates.com"

DB_HOST="13.235.187.102"

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'development',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

FIREBASE_CONFIG = {
  'apiKey': "AIzaSyBNQa1N9u_UuLOW6IwapYzsmPVTqQwOy2E",
  'authDomain': "charealtime.firebaseapp.com",
  'databaseURL': "https://charealtime.firebaseio.com",
  'projectId': "charealtime",
  'storageBucket': "charealtime.appspot.com",
  'messagingSenderId': "746515926836",
  'appId': "1:746515926836:web:c2a732a40f5882f1"
};

TIME_ZONE = 'Asia/Kolkata'
# CELERY_TIMEZONE = 'Asia/Kolkata'
