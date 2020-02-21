from .base import *


DEBUG = False


URL = os.getenv('PROD_URL')

DB_HOST=os.getenv('PROD_DB_HOST')

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('PROD_DB_NAME'),
        'USER': os.getenv('PROD_DB_USER'),
        'PASSWORD':os.getenv('PROD_DB_PASSWORD'),
        'HOST': os.getenv('PROD_DB_HOST'),
        'PORT': '5432',
    }
}


FIREBASE_CONFIG = {
    'apiKey':  os.getenv('FIREBASE_API_KEY'),
    'authDomain':  os.getenv('FIREBASE_AUTH_DOMAIN'),
    'databaseURL':  os.getenv('FIREBASE_DATABASE_URL'),
    'projectId':  os.getenv('FIREBASE_PROJECT_ID'),
    'storageBucket':  os.getenv('FIREBASE_STORAGE_BUCKET'),
    'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
    'appId':  os.getenv('FIREBASE_APP_ID')
  }


# variable to check if ther server is beta server

IS_BETA = False

ALLOWED_HOSTS = [os.getenv("PROD_ALLOWED_HOST_1"),os.getenv("PROD_ALLOWED_HOST_2"),os.getenv("PROD_ALLOWED_HOST_3")]


FCM_SERVER_KEY=os.getenv('PROD_FCM_SERVER_KEY')
