import abc


class WebhookManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'fetch_webhook') and callable(subclass.fetch_webhook)) and
                (hasattr(subclass, 'add_webhook') and callable(subclass.add_webhook)) and
                (hasattr(subclass, 'update_webhook') and callable (subclass.update_webhook)) and
                (hasattr(subclass, 'delete_webhook') and callable(subclass.delete_webhook)) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_webhook(self) -> dict:
        """
        fetch webhook for community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_webhook(self) -> dict:
        """
        add webhook for community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_webhook(self, webhook_url:str = None, is_active:bool = None) -> dict:
        """
        update webhook for community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_webhook(self) -> dict:
        """
        delete webhook for community
        """
        raise NotImplementedError
