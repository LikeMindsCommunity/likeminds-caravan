import abc


class SdkManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'create_sdk') and callable(subclass.create_sdk)) and
                (hasattr(subclass, 'initiate_sdk') and callable(subclass.initiate_sdk)) or
                NotImplemented)

    @abc.abstractmethod
    def create_sdk(self, req_body) -> dict:
        """
        create new sdk project
        """
        raise NotImplementedError

    @abc.abstractmethod
    def initiate_sdk(self, req_body) -> dict:
        """
        initiate a sdk project
        """
        raise NotImplementedError
