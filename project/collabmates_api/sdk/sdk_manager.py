import abc


class SdkManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'fetch_sdk_project') and callable(subclass.fetch_sdk_project)) and
                (hasattr(subclass, 'create_sdk_project') and callable(subclass.create_sdk_project)) and
                (hasattr(subclass, 'edit_sdk_project') and callable(subclass.edit_sdk_project)) and
                (hasattr(subclass, 'delete_sdk_project') and callable(subclass.delete_sdk_project)) and
                (hasattr(subclass, 'initiate_sdk') and callable(subclass.initiate_sdk)) and
                (hasattr(subclass, 'authenticate_sdk') and callable(subclass.authenticate_sdk)) and
                (hasattr(subclass, 'fetch_onboarding_screens') and callable(subclass.fetch_onboarding_screens)) and
                (hasattr(subclass, 'create_onboarding_screen') and callable(subclass.create_onboarding_screen)) and
                (hasattr(subclass, 'edit_onboarding_screen') and callable(subclass.edit_onboarding_screen)) and
                (hasattr(subclass, 'delete_onboarding_screen') and callable(subclass.delete_onboarding_screen)) or
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
    def edit_sdk_project(self, req_body) -> dict:
        """
        edit an existing sdk project
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_sdk_project(self) -> dict:
        """
        deletes an sdk project
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

    @abc.abstractmethod
    def fetch_onboarding_screens(self, req_params) -> dict:
        """
        Fetches onboarding screens of SDK Project
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_onboarding_screen(self, req_body) -> dict:
        """
        Create a new onboarding screen for SDK Project
        """
        raise NotImplementedError

    @abc.abstractmethod
    def edit_onboarding_screen(self, req_body) -> dict:
        """
        Edits an existing screen for SDK Project
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_onboarding_screen(self, req_body) -> dict:
        """
        Deletes an existing screen for SDK Project
        """
        raise NotImplementedError
