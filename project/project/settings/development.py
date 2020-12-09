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


ALLOWED_HOSTS = [os.getenv("BETA_ALLOWED_HOST_2"), os.getenv("BETA_ALLOWED_HOST_3")]

FCM_SERVER_KEY=os.getenv('BETA_FCM_SERVER_KEY')

# variable for google sign in oauth client ID
# GOOGLE_OAUTH_CLIENT_ID=os.getenv('BETA_GOOGLE_OAUTH_CLIENT_ID')
# hard coding here for prod unless key it is moved to beta env as above
GOOGLE_OAUTH_CLIENT_ID="983690302378-vmcfu305q815j0n430t385to742s3epu.apps.googleusercontent.com"

# hard coding here for prod unless key it is moved to beta env
FIREBASE_CONFIG = {
    'apiKey':  "AIzaSyBWjDQEiYKdQbQNvoiVvvOn_cbufQzvWuo",
    'authDomain':  "collabmates-beta.firebaseapp.com",
    'databaseURL':  "https://collabmates-beta.firebaseio.com",
    'projectId':  "collabmates-beta",
    'storageBucket':  "collabmates-beta.appspot.com",
    'messagingSenderId': "983690302378",
    'appId':  "1:983690302378:web:b2fa2c58f2351d5c1b91d3",
    'measurementId': "G-R2PXYC9F4S"
}

CORALOGIX_LOGGER = {
    'PRIVATE_API_KEY': '546fce97-bd5c-bc35-9952-704ab4db8720',
    'APPLICATION_NAME': 'LikeMinds',
    'SUBSYSTEM_NAME': 'Backend Application',
}

GHUPSHUP_KEY = "03f92dd7cbf3b983d8c9a4dc7ac485c7"


ADMINS = [('mahesh', 'mahesh@likeminds.community')]

