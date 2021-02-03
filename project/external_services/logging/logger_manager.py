import abc
import logging


class LoggerManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'get_instance') and
                callable(subclass.get_instance) or
                NotImplemented)

    @staticmethod
    def get_instance() -> logging.Logger:
        """
        returns logger instance
        """
        raise NotImplementedError
