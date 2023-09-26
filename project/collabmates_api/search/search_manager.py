import abc


class SearchManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'search_chatroom') and callable(subclass.search_chatroom)) and
                (hasattr(subclass, 'search_conversation') and callable(subclass.search_conversation)) and
                (hasattr(subclass, 'search_third_party') and callable(subclass.search_third_party)) or
                NotImplemented)

    @abc.abstractmethod
    def search_chatroom(self):
        """
        Search chatrooms by title and header with elastic search
        """
        raise NotImplementedError

    def search_conversation(self, chatroom_id):
        """
        Search conversation by answer text with elastic search
        """

        raise NotImplementedError

    @abc.abstractmethod
    def search_third_party(self):
        """
        Search followed chatrooms by header for third party content sharing with elastic search
        """
        raise NotImplementedError

    @abc.abstractmethod
    def search_member_directory(self, member_state: list = None, order_by: str = None, question_answers_version: str = None):
        """
        Search in member directory by member name or tag with elastic search
        """
        raise NotImplementedError
