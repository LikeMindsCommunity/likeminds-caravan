import abc


class CommunityManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'fetch_community') and
                callable(subclass.fetch_community) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_community(self, client_type):
        """
        fetches the community from the database
        """
        raise NotImplementedError

