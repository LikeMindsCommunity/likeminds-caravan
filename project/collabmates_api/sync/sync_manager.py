import abc


class SyncManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'sync_chatrooms') and callable(subclass.fetch_sdk_project)) and
                (hasattr(subclass, 'sync_conversations') and callable(subclass.fetch_sdk_project)) or
                NotImplemented)

    @abc.abstractmethod
    def sync_chatrooms(self, page: int = None, page_size: int = None, min_timestamp: int = None,
                       max_timestamp: int = None, chatroom_type: list = None) -> dict:
        """
        Sync chatrooms data for local db
        """
        raise NotImplementedError

    @abc.abstractmethod
    def sync_conversations(self, chatroom_id: int = None, page: int = None, page_size: int = None,
                           min_timestamp: int = None, max_timestamp: int = None) -> dict:
        """
        Sync conversations data for local db
        """
        raise NotImplementedError
