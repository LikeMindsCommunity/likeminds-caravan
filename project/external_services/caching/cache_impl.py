from external_services.caching.cache_manager import CacheManager
import redis
from django.conf import settings
from django.core.cache import cache

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()


class CacheImpl(CacheManager):

    @staticmethod
    def set_cache(key, value, timeout=None) -> bool:

        status = False

        try:
            cache.set(key, value, timeout)
            status = True

        except Exception as e:
            error_logger.error(e.args)

        return status

    @staticmethod
    def get_cache(key) -> {}:

        result = {}
        try:

            if key in cache:
                result = cache.get(key)
            
        except Exception as e:
            error_logger.error(e.args)

        return result

    @staticmethod
    def ping_cache():
        redis_connection = redis.Redis(host=settings.CACHE_CREDENTIALS['host'], port=settings.CACHE_CREDENTIALS['port'])
        redis_connection.ping()

    @staticmethod
    def delete_key(key) -> bool:

        status = False
        try:

            if key in cache:
                cache.delete(key)

                status = True

        except Exception as e:
            error_logger.error(e.args)
            status = False

        return status
