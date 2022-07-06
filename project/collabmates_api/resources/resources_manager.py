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
                callable(subclass.delete_resource_category)) and
                (hasattr(subclass, 'create_resource_url') and
                callable (subclass.create_resource_url)) and
                (hasattr(subclass, 'update_resource_url') and
                callable (subclass.update_resource_url)) and
                (hasattr(subclass, 'delete_resource_url') and
                callable(subclass.delete_resource_url)) and
                (hasattr(subclass, 'create_resource_file') and
                callable (subclass.create_resource_file)) and
                (hasattr(subclass, 'update_resource_file') and
                callable (subclass.update_resource_file)) and
                (hasattr(subclass, 'delete_resource_file') and
                callable(subclass.delete_resource_file)) and
                (hasattr(subclass, 'create_resource_reference') and
                callable (subclass.create_resource_reference)) and
                (hasattr(subclass, 'fetch_resource_reference') and
                callable (subclass.fetch_resource_reference)) and
                (hasattr(subclass, 'delete_resource_reference') and
                callable(subclass.delete_resource_reference)) and
                (hasattr(subclass, 'update_resource_state') and
                callable (subclass.update_resource_state)) and
                (hasattr(subclass, 'fetch_resource_state') and
                callable(subclass.fetch_resource_state)) or
                NotImplemented)

    @abc.abstractmethod
    def update_resource_settings(self, req_body) -> dict:
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
    def create_resource_category(self, req_body) -> dict:
        """
        to create resource category
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_resource_category(self, page) -> dict:
        """
        to fetch resource category
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_resource_category(self, req_body) -> dict:
        """
        to update resource category
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_resource_category(self, req_body) -> dict:
        """
        to delete resource category
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_resource_url(self, req_body) -> dict:
        """
        to create resource url
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_resource_url(self, req_body) -> dict:
        """
        to update resource url
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_resource_url(self, req_body) -> dict:
        """
        to delete resource url
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_resource_file(self, req_body) -> dict:
        """
        to create resource file
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_resource_file(self, req_body) -> dict:
        """
        to update resource file
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_resource_file(self, req_body) -> dict:
        """
        to delete resource file
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_resource_reference(self, req_body) -> dict:
        """
        to create resource reference
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_resource_reference(self, page) -> dict:
        """
        to fetch resource reference
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_resource_reference(self, req_body) -> dict:
        """
        to delete resource reference
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_resource_state(self, req_body) -> dict:
        """
        to update resource state
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_resource_state(self, req_body) -> dict:
        """
        to fetch resource state
        """
        raise NotImplementedError
