from .base import *

DEBUG = False

URL = os.getenv('BETA_URL')
WEB_URL = os.getenv('BETA_WEB_URL')

DB_HOST = os.getenv('BETA_DB_HOST')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('BETA_DB_NAME'),
        'USER': os.getenv('BETA_DB_USER'),
        'PASSWORD': os.getenv('BETA_DB_PASSWORD'),
        'HOST': os.getenv('BETA_DB_HOST'),
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
        'TEST': {
            'NAME': "db_test"
        }
    }
}

TIME_ZONE = 'Asia/Kolkata'

# variable to check for beta server
IS_BETA = True
IS_LOAD_ENV = False

ALLOWED_HOSTS = [os.getenv("BETA_ALLOWED_HOST_2"), os.getenv("BETA_ALLOWED_HOST_3"), os.getenv("BETA_ALLOWED_HOST_ELB")]

FCM_SERVER_KEY = os.getenv('BETA_FCM_SERVER_KEY')

# variable for google sign in oauth client ID
# GOOGLE_OAUTH_CLIENT_ID=os.getenv('BETA_GOOGLE_OAUTH_CLIENT_ID')
# hard coding here for prod unless key it is moved to beta env as above
GOOGLE_OAUTH_CLIENT_ID = "983690302378-vmcfu305q815j0n430t385to742s3epu.apps.googleusercontent.com"

# hard coding here for prod unless key it is moved to beta env
FIREBASE_CONFIG = {
    'apiKey': "AIzaSyBWjDQEiYKdQbQNvoiVvvOn_cbufQzvWuo",
    'authDomain': "collabmates-beta.firebaseapp.com",
    'databaseURL': "https://collabmates-beta.firebaseio.com",
    'projectId': "collabmates-beta",
    'storageBucket': "collabmates-beta.appspot.com",
    'messagingSenderId': "983690302378",
    'appId': "1:983690302378:web:b2fa2c58f2351d5c1b91d3",
    'measurementId': "G-R2PXYC9F4S"
}

AWS_CREDENTIALS = {
    'ACCESS_KEY': os.getenv('AWS_S3_ACCESS_KEY'),
    'SECRET_KEY': os.getenv('AWS_S3_SECRET_KEY')
}

USE_INTERNAL_FILE_LOGGER = False
OMIT_200_OK_FULL_RESPONSE = True

CORALOGIX_LOGGER = {
    'PRIVATE_API_KEY': os.getenv('CORALOGIX_LOGGER_PRIVATE_API_KEY'),
    'APPLICATION_NAME': 'LikeMinds_Beta',
    'SUBSYSTEM_NAME_API': 'Backend_App_Api',
    'SUBSYSTEM_NAME_APP': 'Backend_App_System'
}

S3_BUCKETS = {
    'media_bucket': {
        'arn': 'arn:aws:s3:::beta-likeminds-media',
        'name': 'beta-likeminds-media',
        'region': 'ap-south-1'
    }
}

GHUPSHUP_KEY = "03f92dd7cbf3b983d8c9a4dc7ac485c7"

OTP_TEMPLATE_ID = os.getenv('MSG_91_OTP_TEMPLATE_ID')

ADMINS = [  
            ('Ankit', 'ankit.garg@likeminds.community'),
            ('Shubh', 'shubh.gupta@likeminds.community'),
            ('Mahir', 'mahir.gupta@likeminds.community'),
            ('Ketan', 'ketan@likeminds.community')
         ]

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('CACHE_LOCATION'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

CACHE_CREDENTIALS = {
    'host': os.getenv('CACHE_HOST'),
    'port': os.getenv('CACHE_PORT')
}

CALENDAR_CREDENTIALS = {
    'service_account_email': os.getenv('SERVICE_ACCOUNT_EMAIL'),
    'scopes': [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ],
    'delegated_email': os.getenv('DELEGATED_EMAIL'),

    'key_dict': {
        "type": os.getenv("CALENDER_ACCOUNT_TYPE"),
        "project_id": os.getenv("CALENDER_PROJECT_ID"),
        "private_key_id": os.getenv("CALENDER_PRIVATE_KEY_ID"),
        "private_key": os.getenv("CALENDER_PRIVATE_KEY"),
        "client_email": os.getenv("CALENDER_CLIENT_EMAIL"),
        "client_id": os.getenv("CALENDER_CLIENT_ID"),
        "auth_uri": os.getenv("CALENDER_AUTH_URI"),
        "token_uri": os.getenv("CALENDER_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("CALENDER_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("CALENDER_CLIENT_X509_CERT_URL")
    }
}

WEBHOOK_FAILURE_NOTIFICATION_TEAM_EMAILS = ['backend@likeminds.community']

SWARM_BASE_URL = os.getenv('SWARM_BASE_URL')
KETTLE_BASE_URL = os.getenv('KETTLE_BASE_URL')

CH_FORCE_UPDATE_ANDROID_VERSION = os.getenv('CH_FORCE_UPDATE_ANDROID_VERSION')
CH_FORCE_UPDATE_IOS_VERSION = os.getenv('CH_FORCE_UPDATE_IOS_VERSION')
