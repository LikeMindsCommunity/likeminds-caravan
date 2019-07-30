from .base import *

DEBUG = False

URL = "https://www.collabmates.com"

DB_HOST="collabmatesdatabase.cgx3gr7xnezq.ap-south-1.rds.amazonaws.com"

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'togther',
        'USER': 'nateshr',
        'PASSWORD': 'connectNRpostgresql',
        'HOST': 'collabmatesdatabase.cgx3gr7xnezq.ap-south-1.rds.amazonaws.com',
        'PORT': '5432',
    }
}


FIREBASE_CONFIG = {
    'apiKey': "AIzaSyCmu_u-n31x2WMQlWAciP5RDXGn2qMuXrg",
    'authDomain': "collabmates-3d601.firebaseapp.com",
    'databaseURL': "https://collabmates-3d601.firebaseio.com",
    'projectId': "collabmates-3d601",
    'storageBucket': "collabmates-3d601.appspot.com",
    'messagingSenderId': "645716458793",
    'appId': "1:645716458793:web:779debf3286d6049"
  };