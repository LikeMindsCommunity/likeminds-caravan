import abc


class UserManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'delete_user') and
                callable(subclass.delete_user) or
                NotImplemented)

    @abc.abstractmethod
    def delete_user(self) -> None:
        """
        deleting the user from database
        """
        raise NotImplementedError
