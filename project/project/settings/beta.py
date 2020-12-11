from .base import *

DEBUG = False

URL = os.getenv('BETA_URL')

DB_HOST = os.getenv('BETA_DB_HOST')

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

# variable to check for beta server
IS_BETA = True

ALLOWED_HOSTS = [os.getenv("BETA_ALLOWED_HOST_2"), os.getenv("BETA_ALLOWED_HOST_3")]

FCM_SERVER_KEY = os.getenv('BETA_FCM_SERVER_KEY')

# variable for google sign in oauth client ID
# GOOGLE_OAUTH_CLIENT_ID=os.getenv('BETA_GOOGLE_OAUTH_CLIENT_ID')
# hard coding here for prod unless key it is moved to beta env as above
GOOGLE_OAUTH_CLIENT_ID = "983690302378-vmcfu305q815j0n430t385to742s3epu.apps.googleusercontent.com"

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
    'PRIVATE_API_KEY': os.getenv('CORALOGIX_LOGGER_PRIVATE_API_KEY'),
    'APPLICATION_NAME': 'LikeMinds_Beta',
    'SUBSYSTEM_NAME_API': 'Backend_App_Api',
    'SUBSYSTEM_NAME_APP': 'Backend_App_System'
}

GHUPSHUP_KEY = "03f92dd7cbf3b983d8c9a4dc7ac485c7"

ADMINS = [('mahesh', 'mahesh@likeminds.community')]
