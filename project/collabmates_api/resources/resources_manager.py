import abc


class ResourceManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'update_resource_settings') and
                callable(subclass.update_resource_settings)) and
                (hasattr(subclass, 'fetch_resource_settings') and
                callable(subclass.fetch_resource_settings)) and
                (hasattr(subclass, 'create_resource_category') and
                callable (subclass.create_resource_category)) and
                (hasattr(subclass, 'fetch_resource_category') and
                callable (subclass.fetch_resource_category)) and
                (hasattr(subclass, 'update_resource_category') and
                callable (subclass.update_resource_category)) and
                (hasattr(subclass, 'delete_resource_category') and
                callable(subclass.delete_resource_category)) or
                NotImplemented)

    @abc.abstractmethod
    def update_resource_settings(self) -> dict:
        """
        to update resource settings
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_resource_settings(self) -> dict:
        """
        to fetch resource settings
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_resource_category(self) -> dict:
        """
        to create resource category
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_resource_category(self) -> dict:
        """
        to fetch resource category
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_resource_category(self) -> dict:
        """
        to update resource category
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_resource_category(self) -> dict:
        """
        to delete resource category
        """
        raise NotImplementedError
