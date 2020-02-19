from .base import *

DEBUG = True

URL = "https://beta.collabmates.com"

DB_HOST="13.235.187.102"

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'prod_dump',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': '13.235.187.102',
        'PORT': '5432',
    }
}


TIME_ZONE = 'Asia/Kolkata'
# CELERY_TIMEZONE = 'Asia/Kolkata'


# variable to check if ther server is beta server
IS_BETA = True
