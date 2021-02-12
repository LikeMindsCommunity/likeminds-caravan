import abc


class MixpanelManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'track_notification') and
                callable(subclass.track_notification) or
                NotImplemented)

    @abc.abstractmethod
    def track_notification(self, distinct_id, properties) -> None:
        """
        To track the notification details
        to whom the notification is sent to
        """
        raise NotImplementedError
