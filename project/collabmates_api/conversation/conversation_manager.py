import abc


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
    
