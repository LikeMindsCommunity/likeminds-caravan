import abc


class SyncManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'sync_chatrooms') and callable(subclass.fetch_sdk_project)) and
                (hasattr(subclass, 'sync_channel_detail') and callable(subclass.sync_channel_detail)) and
                (hasattr(subclass, 'sync_conversations') and callable(subclass.fetch_sdk_project)) or
                NotImplemented)

    @abc.abstractmethod
    def sync_chatrooms(self, page: int = None, page_size: int = None, min_timestamp: int = None,
                       max_timestamp: int = None, chatroom_type: list = None, is_local_db: bool = True,
                       included_conversation_states: list = None, chatroom_id: str = None) -> dict:
        """
        Sync chatrooms data for local db
        """
        raise NotImplementedError

    @abc.abstractmethod
    def sync_channel_detail(self, channel_id: str, channel_action_types: list) -> dict:
        """
        Get channel detail data corresponding to a user
        """
        raise NotImplementedError

    @abc.abstractmethod
    def sync_conversations(self, chatroom_id: int = None, page: int = None, page_size: int = None,
                           min_timestamp: int = None, max_timestamp: int = None, is_local_db: bool = True,
                           conversation_id: str = None, excluded_conversation_states: list = None,
                           order_by: str = "") -> dict:
        """
        Sync conversations data for local db
        """
        raise NotImplementedError
