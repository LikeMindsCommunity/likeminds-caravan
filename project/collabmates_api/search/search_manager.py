import abc


class SearchManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'search_chatroom') and callable(subclass.search_chatroom) and
                (hasattr(subclass, 'search_conversation') and callable(subclass.search_conversation)) or
                NotImplemented)

    @abc.abstractmethod
    def search_chatroom(self):
        """
        Search chatrooms by title and header with elastic search
        """
        raise NotImplementedError

    def search_conversation(self):
        """
        Search conversation by answer text with elastic search
        """

        raise NotImplementedError
