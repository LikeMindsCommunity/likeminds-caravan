import abc


class SdkManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'fetch_sdk_project') and callable(subclass.fetch_sdk_project)) and
                (hasattr(subclass, 'create_sdk_project') and callable(subclass.create_sdk_project)) and
                (hasattr(subclass, 'initiate_sdk') and callable(subclass.initiate_sdk)) and
                (hasattr(subclass, 'authenticate_sdk') and callable(subclass.authenticate_sdk)) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_sdk_project(self, req_params) -> dict:
        """
        fetches sdk projects
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_sdk_project(self, req_body) -> dict:
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

    @abc.abstractmethod
    def authenticate_sdk(self) -> dict:
        """
        Authenticate the SDK
        """
        raise NotImplementedError
