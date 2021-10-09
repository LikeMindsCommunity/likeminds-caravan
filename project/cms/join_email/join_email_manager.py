import abc


class JoinEmailManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'add_join_email') and callable(subclass.add_join_email)) or
                NotImplemented)

    @abc.abstractmethod
    def add_join_email(self, req_body) -> dict:
        """
        adds a join email
        """
        raise NotImplementedError
