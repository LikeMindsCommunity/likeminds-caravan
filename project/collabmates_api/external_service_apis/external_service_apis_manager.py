import abc


class ExternalServiceApisManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'send_email') and callable(subclass.send_email)) and
                (hasattr(subclass, 'send_wa_message') and callable(subclass.send_wa_message)) and
                (hasattr(subclass, 'send_notifications') and callable(subclass.send_notifications))
                or NotImplemented)

    @abc.abstractmethod
    def send_email(self, req_body) -> dict:
        """
        Sends the email
        """
        raise NotImplementedError

    @abc.abstractmethod
    def send_wa_message(self, req_body) -> dict:
        """
        Sends the whatsapp message
        """
        raise NotImplementedError

    @abc.abstractmethod
    def send_notifications(self, req_body) -> dict:
        """
        Sends push notification
        """
        raise NotImplementedError
