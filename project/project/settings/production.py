from .base import *

DEBUG = False

URL = "https://www.likeminds.community"
WEB_URL = "https://web.likeminds.community"

DB_HOST = "collabmatesdatabase.cgx3gr7xnezq.ap-south-1.rds.amazonaws.com"

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': "togther",
        'USER': "nateshr",
        'PASSWORD': "connectNRpostgresql",
        'HOST': "collabmatesdatabase.cgx3gr7xnezq.ap-south-1.rds.amazonaws.com",
        'PORT': '5432',
    }
}

FIREBASE_CONFIG = {
    'apiKey': "AIzaSyCmu_u-n31x2WMQlWAciP5RDXGn2qMuXrg",
    'authDomain':"collabmates-3d601.firebaseapp.com",
    'databaseURL': "https://collabmates-3d601.firebaseio.com",
    'projectId': "collabmates-3d601",
    'storageBucket': "collabmates-3d601.appspot.com",
    'messagingSenderId': "645716458793",
    'appId': "1:645716458793:web:779debf3286d6049"
}

# variable to check if ther server is beta server

IS_BETA = False

TIME_ZONE = 'Asia/Kolkata'

ALLOWED_HOSTS = ["collabmates.com", "13.235.165.26",
                 "www.collabmates.com", "likeminds.community",
                 "www.likeminds.community"]

FCM_SERVER_KEY = "AIzaSyCmu_u-n31x2WMQlWAciP5RDXGn2qMuXrg"

# variable for google sign in oauth client ID
# GOOGLE_OAUTH_CLIENT_ID=os.getenv('PROD_GOOGLE_OAUTH_CLIENT_ID')
# hard coding here for prod unless key it is moved to prod env as above
GOOGLE_OAUTH_CLIENT_ID = "645716458793-rprdna1adps5s7pigsrjasko3ot3ljfl.apps.googleusercontent.com"

AWS_CREDENTIALS = {
    'ACCESS_KEY': "AKIA3HMTDICCWBSGV67Z",
    'SECRET_KEY':  "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"
}

USE_INTERNAL_FILE_LOGGER = False

CORALOGIX_LOGGER = {
    'PRIVATE_API_KEY':"ca80efdf-f108-6cdf-d206-4028c9de2392",
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
        'LOCATION': "redis://lm-redis-prod-001.5pevj6.0001.aps1.cache.amazonaws.com:6379",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

CACHE_CREDENTIALS = {
    'host': "lm-redis-prod-001.5pevj6.0001.aps1.cache.amazonaws.com",
    'port': "6379"
}
