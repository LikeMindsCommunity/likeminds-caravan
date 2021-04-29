import abc


class UserManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'delete_user') and
                callable(subclass.delete_user) and
                (hasattr(subclass, 'survey_seen') and
                 callable(subclass.survey_seen)) and
                (hasattr(subclass, 'logout') and
                 callable(subclass.logout)) or
                NotImplemented)

    @abc.abstractmethod
    def delete_user(self) -> None:
        """
        deleting the user from database
        """
        raise NotImplementedError

    @abc.abstractmethod
    def survey_seen(self) -> {}:
        """
        save the flag for survey seen
        """
        raise NotImplementedError

    @abc.abstractmethod
    def logout(self, device_id) -> {}:
        """
        logout the user from the app
        """
        raise NotImplementedError
