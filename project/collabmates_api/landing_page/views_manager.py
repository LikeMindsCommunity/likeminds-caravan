import abc

from django.http import JsonResponse


class ViewsManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'get_member_communities') and
                callable(subclass.get_member_communities) or
                NotImplemented)

    @abc.abstractmethod
    def get_member_communities(self, user_id: int) -> JsonResponse:
        """
        Get communities of the member
        """
        raise NotImplementedError
