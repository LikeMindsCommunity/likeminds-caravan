import abc


class OptionsManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'create_option') and callable(subclass.create_option)) and
                (hasattr(subclass, 'fetch_option') and callable(subclass.fetch_option)) or
                NotImplemented)

    @abc.abstractmethod
    def create_option(self, req_body) -> dict:
        """
        creates or updates a option
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_option(self, slug) -> dict:
        """
        returns option value
        """
        raise NotImplementedError
