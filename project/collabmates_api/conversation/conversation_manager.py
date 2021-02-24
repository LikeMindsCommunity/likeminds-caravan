import abc
from togther.models import card_answers


class ConversationManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'fetch_conversation') and
                callable(subclass.fetch_conversation) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_conversation(self) -> None:
        """
        fetches the conversation from the database
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_conversation(self, req_body: dict, is_ios: bool,
                            is_user_guest: bool, has_files: bool, **kwargs) -> {}:
        """
        create conversation
        """
        raise NotImplementedError

