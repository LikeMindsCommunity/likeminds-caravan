from .base import *

DEBUG = False

URL = os.getenv('PRODUCTION_URL')
WEB_URL = os.getenv('PRODUCTION_WEB_URL')

DB_HOST = os.getenv('PRODUCTION_DB_HOST')

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('PRODUCTION_DB_NAME'),
        'USER': os.getenv('PRODUCTION_DB_USER'),
        'PASSWORD': os.getenv('PRODUCTION_DB_PASSWORD'),
        'HOST': os.getenv('PRODUCTION_DB_HOST'),
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
        'TEST': {
            'NAME': "db_test"
        }
    }
}

FIREBASE_CONFIG = {
    'apiKey': os.getenv('FIREBASE_API_KEY'),
    'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN'),
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL'),
    'projectId': os.getenv('FIREBASE_PROJECT_ID'),
    'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET'),
    'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
    'appId': os.getenv('FIREBASE_APP_ID')
}
# variable to check if ther server is beta server

IS_BETA = False

TIME_ZONE = 'Asia/Kolkata'

ALLOWED_HOSTS = [os.getenv("PRODUCTION_ALLOWED_HOST_1"), os.getenv("PRODUCTION_ALLOWED_HOST_2"),
                 os.getenv("PRODUCTION_ALLOWED_HOST_3"), os.getenv("PRODUCTION_ALLOWED_HOST_4"),
                 os.getenv("PRODUCTION_ALLOWED_HOST_5"), os.getenv("PRODUCTION_ALLOWED_HOST_6")]
FCM_SERVER_KEY = os.getenv('PRODUCTION_FCM_SERVER_KEY')

# variable for google sign in oauth client ID
# GOOGLE_OAUTH_CLIENT_ID=os.getenv('PROD_GOOGLE_OAUTH_CLIENT_ID')
# hard coding here for prod unless key it is moved to prod env as above
GOOGLE_OAUTH_CLIENT_ID = "645716458793-rprdna1adps5s7pigsrjasko3ot3ljfl.apps.googleusercontent.com"

AWS_CREDENTIALS = {
    'ACCESS_KEY': os.getenv('AWS_S3_ACCESS_KEY'),
    'SECRET_KEY': os.getenv('AWS_S3_SECRET_KEY')
}

USE_INTERNAL_FILE_LOGGER = False
OMIT_200_OK_FULL_RESPONSE = True

CORALOGIX_LOGGER = {
    'PRIVATE_API_KEY': os.getenv('CORALOGIX_LOGGER_PRIVATE_API_KEY'),
    'APPLICATION_NAME': 'LikeMinds_Prod',
    'SUBSYSTEM_NAME_API': 'Backend_App_Api',
    'SUBSYSTEM_NAME_APP': 'Backend_App_System'
}

S3_BUCKETS = {
    'media_bucket': {
        'arn': 'arn:aws:s3:::prod-likeminds-media',
        'name': 'prod-likeminds-media',
        'region': 'ap-south-1'
    }
}

GHUPSHUP_KEY = "45314393fb4505a15ff19d175d0c92f1"

OTP_TEMPLATE_ID = '5fcfb2806e0eaa3000589d5c'

ADMINS = [
    ('Ketan', 'ketan@likeminds.community'),
    ('Ankit', 'ankit.garg@likeminds.community'),
    ('Shubh', 'shubh.gupta@likeminds.community'),
    ('Mahir', 'mahir.gupta@likeminds.community')
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

WEBHOOK_FAILURE_NOTIFICATION_TEAM_EMAILS = ['product@likeminds.community', 'backend@likeminds.community']

SWARM_BASE_URL = os.getenv('SWARM_BASE_URL')

CH_FORCE_UPDATE_ANDROID_VERSION = os.getenv('CH_FORCE_UPDATE_ANDROID_VERSION')
CH_FORCE_UPDATE_IOS_VERSION = os.getenv('CH_FORCE_UPDATE_IOS_VERSION')
