from .base import *


DEBUG = False

URL = os.getenv('BETA_URL')

DB_HOST=os.getenv('BETA_DB_HOST')

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('BETA_DB_NAME'),
        'USER': os.getenv('BETA_DB_USER'),
        'PASSWORD':os.getenv('BETA_DB_PASSWORD'),
        'HOST': os.getenv('BETA_DB_HOST'),
        'PORT': '5432',
    }
}


TIME_ZONE = 'Asia/Kolkata'
# CELERY_TIMEZONE = 'Asia/Kolkata'


# variable to check if ther server is beta server
IS_BETA = True


ALLOWED_HOSTS = [os.getenv("BETA_ALLOWED_HOST_1"),os.getenv("BETA_ALLOWED_HOST_2")]

FCM_SERVER_KEY=os.getenv('BETA_FCM_SERVER_KEY')