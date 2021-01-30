import abc


class SnackbarManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'fetch_snackbar') and
                callable(subclass.fetch_snackbar) and
                hasattr(subclass, 'create_snackbar') and
                callable(subclass.create_snackbar) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_snackbar(self, member_id) -> dict:
        """
        function to fetch the snackbar
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_snackbar(self, snackbar_dict) -> None:
        """
        function to create the snackbar
        """
        raise NotImplementedError

