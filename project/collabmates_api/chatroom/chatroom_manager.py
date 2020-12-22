import abc


class ChatroomManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'fetch_chatroom') and
                callable(subclass.fetch_chatroom) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_chatroom(self) -> None:
        """
        fetching the chatroom from chatroom id
        """
        raise NotImplementedError
