from .base import *

DEBUG = False

URL = os.getenv('PROD_URL')
WEB_URL = os.getenv('PROD_WEB_URL')

DB_HOST = os.getenv('PROD_DB_HOST')

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('PROD_DB_NAME'),
        'USER': os.getenv('PROD_DB_USER'),
        'PASSWORD': os.getenv('PROD_DB_PASSWORD'),
        'HOST': os.getenv('PROD_DB_HOST'),
        'PORT': '5432',
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

ALLOWED_HOSTS = [os.getenv("PROD_ALLOWED_HOST_1"), os.getenv("PROD_ALLOWED_HOST_2"),
                 os.getenv("PROD_ALLOWED_HOST_3"), os.getenv("PROD_ALLOWED_HOST_4"),
                 os.getenv("PROD_ALLOWED_HOST_5")]

FCM_SERVER_KEY = os.getenv('PROD_FCM_SERVER_KEY')

# variable for google sign in oauth client ID
# GOOGLE_OAUTH_CLIENT_ID=os.getenv('PROD_GOOGLE_OAUTH_CLIENT_ID')
# hard coding here for prod unless key it is moved to prod env as above
GOOGLE_OAUTH_CLIENT_ID = "645716458793-rprdna1adps5s7pigsrjasko3ot3ljfl.apps.googleusercontent.com"

AWS_CREDENTIALS = {
    'ACCESS_KEY': os.getenv('AWS_S3_ACCESS_KEY'),
    'SECRET_KEY': os.getenv('AWS_S3_SECRET_KEY')
}

USE_INTERNAL_FILE_LOGGER = False

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
    ('mahesh', 'mahesh@likeminds.community'),
    ('Priyanshu', 'priyanshu@likeminds.community'),
    ('Ketan', 'ketan@likeminds.community'),
    ('Himanshu', 'himanshu@likeminds.community')
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
