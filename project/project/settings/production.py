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