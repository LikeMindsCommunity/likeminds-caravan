import abc


class LoggerManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'get_instance') and
                callable(subclass.get_instance) or
                NotImplemented)

    @abc.abstractmethod
    def get_instance(self) -> None:
        """
        returns logger instance
        """
        raise NotImplementedError
