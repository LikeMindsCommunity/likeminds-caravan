import abc


class WebhookManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'add_or_update_webhook') and callable(subclass.add_or_update_webhook)) and
                (hasattr(subclass, 'fetch_webhook') and callable(subclass.fetch_webhook)) and
                (hasattr(subclass, 'delete_webhook') and callable(subclass.delete_webhook)) or
                NotImplemented)

    @abc.abstractmethod
    def add_or_update_webhook(self) -> dict:
        """
        add webhook for community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_webhook(self) -> dict:
        """
        fetch webhook for community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_webhook(self) -> dict:
        """
        delete webhook for community
        """
        raise NotImplementedError
