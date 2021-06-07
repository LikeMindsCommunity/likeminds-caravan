from .base import *

DEBUG = False

URL = os.getenv('DEVELOPMENT_URL')
WEB_URL = os.getenv('DEVELOPMENT_WEB_URL')

DB_HOST = os.getenv('DEVELOPMENT_DB_HOST')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('DEVELOPMENT_DB_NAME'),
        'USER': os.getenv('DEVELOPMENT_DB_USER'),
        'PASSWORD':os.getenv('DEVELOPMENT_DB_PASSWORD'),
        'HOST': os.getenv('DEVELOPMENT_DB_HOST'),
        'PORT': '5432',
        'CONN_MAX_AGE': 600
    }
}

TIME_ZONE = 'Asia/Kolkata'

# variable to check for beta server
IS_BETA = True

ALLOWED_HOSTS = [os.getenv("DEVELOPMENT_ALLOWED_HOST_2"), os.getenv("DEVELOPMENT_ALLOWED_HOST_3")]

FCM_SERVER_KEY = os.getenv('DEVELOPMENT_FCM_SERVER_KEY')

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

AWS_CREDENTIALS = {
    'ACCESS_KEY': os.getenv('AWS_S3_ACCESS_KEY'),
    'SECRET_KEY': os.getenv('AWS_S3_SECRET_KEY')
}

USE_INTERNAL_FILE_LOGGER = True
OMIT_200_OK_FULL_RESPONSE = False

CORALOGIX_LOGGER = {
    'PRIVATE_API_KEY': os.getenv('CORALOGIX_LOGGER_PRIVATE_API_KEY'),
    'APPLICATION_NAME': 'LikeMinds_Development',
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

OTP_TEMPLATE_ID = '5fd9f7f1e96b780fae01acff'

ADMINS = [('mahesh', 'mahesh@likeminds.community')]

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

FCM_CREDENTIALS = {
  "type": os.getenv('FCM_TYPE'),
  "project_id": os.getenv('FCM_PROJECT_ID'),
  "private_key_id": os.getenv('FCM_PRIVATE_KEY_ID'),
  "private_key": os.getenv('FCM_PRIVATE_KEY'),
  "client_email": os.getenv('FCM_CLIENT_EMAIL'),
  "client_id": os.getenv('FCM_CLIENT_ID'),
  "auth_uri": os.getenv('FCM_AUTH_URI'),
  "token_uri": os.getenv('FCM_TOKEN_URI'),
  "auth_provider_x509_cert_url": os.getenv('FCM_AUTH_PROVIDER_X509_CERT_URL'),
  "client_x509_cert_url": os.getenv('FCM_CLIENT_X509_CERT_URL')
}
