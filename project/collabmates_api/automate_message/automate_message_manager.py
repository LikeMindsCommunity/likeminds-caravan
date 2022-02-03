import abc


class AutomateMessageManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'add_template') and callable(subclass.add_template)) and
                (hasattr(subclass, 'send_custom_message') and callable(subclass.send_custom_message)) or
                NotImplemented)

    @abc.abstractmethod
    def add_template(self) -> dict:
        """
        add templates for automation of messages
        """
        raise NotImplementedError

    @abc.abstractmethod
    def send_custom_message(self) -> dict:
        """
        send custom message to all community members
        """
