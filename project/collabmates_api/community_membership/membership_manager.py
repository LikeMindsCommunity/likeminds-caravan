import abc


class MembershipManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'fetch_community_benefits') and callable(subclass.fetch_community_benefits)) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_community_benefits(self, community_ids) -> dict:
        """
        fetches the community from the database
        """
        raise NotImplementedError
