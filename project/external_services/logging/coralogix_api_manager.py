import abc


class CoralogixApiManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'call_logging_api') and
                callable(subclass.call_logging_api) or
                NotImplemented)

    @abc.abstractmethod
    def call_logging_api(self, payload: dict) -> None:
        """
        Make a call to Coralogix server to log given payload
        """
        raise NotImplementedError
