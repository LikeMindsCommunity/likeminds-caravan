import abc


class CacheManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'set_cache') and
                callable(subclass.set_cache) and
                hasattr(subclass, 'get_cache') and
                callable(subclass.get_cache) and
                hasattr(subclass, 'ping_cache') and
                callable(subclass.ping_cache)
                or
                NotImplemented)

    @staticmethod
    def set_cache(key, value, timeout=None) -> bool:
        """
        sets up a cache
        """
        raise NotImplementedError

    @staticmethod
    def get_cache(key) -> {}:
        """
        gets the result from the cache
        """
        raise NotImplementedError

    @staticmethod
    def ping_cache() -> None:
        """
        pings the cache if the connection to redis is successful
        """
        raise NotImplementedError

