import abc


class UriTagsManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
                hasattr(subclass, 'get_tags_from_uri') and callable(subclass.get_tags_from_uri) or
                NotImplemented
        )

    @abc.abstractmethod
    def get_tags_from_uri(self) -> dict:
        """
        returns tags dictionary for a uri
        """
        raise NotImplementedError
