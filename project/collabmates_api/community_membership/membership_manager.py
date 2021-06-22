import abc


class MembershipManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'fetch_community_benefits') and callable(subclass.fetch_community_benefits)) and
                (hasattr(subclass, 'remove_community_membership') and callable(subclass.remove_community_membership)) and
                (hasattr(subclass, 'renew_community_membership') and callable(subclass.renew_community_membership)) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_community_benefits(self, community_ids) -> dict:
        """
        fetches the community from the database
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_community_membership(self, community_id, member_id) -> dict:
        """
        removes member from paid community when subscription is expired
        """
        raise NotImplementedError

    @abc.abstractmethod
    def renew_community_membership(self, community_id) -> dict:
        """
        Restores members data in a a paid community after he renews his membership
        """
        raise NotImplementedError
