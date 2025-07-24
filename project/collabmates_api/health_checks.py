import psycopg2
import redis
from elasticsearch import Elasticsearch
from django.conf import settings

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()

def check_postgres():
    try:
        conn = psycopg2.connect(
            dbname=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            host=settings.DATABASES['default']['HOST'],
            port=settings.DATABASES['default']['PORT'],
            connect_timeout=3
        )
        conn.close()
        info_logger.info("--> PostgreSQL is reachable.")
    except Exception as e:
        error_logger.error(f" PostgreSQL connection FAILED: {e}")

def check_redis():
    try:
        r = redis.StrictRedis.from_url(settings.CACHES['default']['LOCATION'])
        r.ping()
        info_logger.info("--> Redis is reachable.")
    except Exception as e:
        error_logger.error(f" Redis connection FAILED: {e}")

def check_elasticsearch():
    try:
        es = Elasticsearch(settings.ELASTICSEARCH_DSL['default']['hosts'])
        if es.ping():
            info_logger.info("--> Elasticsearch is reachable.")
        else:
            error_logger.error("Elasticsearch ping FAILED.")
    except Exception as e:
        error_logger.error(f" Elasticsearch connection FAILED: {e}")
