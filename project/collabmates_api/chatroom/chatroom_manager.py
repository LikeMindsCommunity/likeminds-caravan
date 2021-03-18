import abc


class ChatroomManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'fetch_chatroom') and callable(subclass.fetch_chatroom)) and
                (hasattr(subclass, 'create_chatroom') and callable(subclass.create_chatroom)) and
                (hasattr(subclass, 'set_chatroom_active_or_inactive') and
                 callable(subclass.set_chatroom_active_or_inactive))and
                (hasattr(subclass, 'pin_or_unpin_chatroom') and
                 callable(subclass.pin_or_unpin_chatroom)) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_chatroom(self) -> dict:
        """
        fetching the chatroom from chatroom id
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_chatroom(self, req_body: dict) -> dict:
        """
        create chatroom
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_chatroom_active_or_inactive(self, req_body: dict) -> dict:
        """
        make chatroom active or in-active
        """
        raise NotImplementedError

    @abc.abstractmethod
    def pin_or_unpin_chatroom(self, req_body: dict) -> dict:
        """
        make chatroom pin or unpin
        """
        raise NotImplementedError
