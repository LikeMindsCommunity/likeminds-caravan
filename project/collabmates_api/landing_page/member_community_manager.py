import abc


class MemberCommunityManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'extract_member_communities') and
                callable(subclass.extract_member_communities) or
                NotImplemented)

    @abc.abstractmethod
    def extract_member_communities(self) -> None:
        """Get communities of the member"""
        raise NotImplementedError
