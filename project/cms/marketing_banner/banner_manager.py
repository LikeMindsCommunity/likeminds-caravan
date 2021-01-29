import abc


class BannerManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (((hasattr(subclass, 'fetch_banner') and callable(subclass.fetch_banner)) and
                (hasattr(subclass, 'fetch_banner_for_cms') and callable(subclass.fetch_banner_for_cms)) and
                (hasattr(subclass, 'create_or_update_banner') and callable(subclass.create_or_update_banner)) and
                (hasattr(subclass, 'remove_banner') and callable(subclass.remove_banner)) and
                (hasattr(subclass, 'check_banner') and callable(subclass.check_banner))) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_banner(self) -> dict:
        """
        fetching the banners for user
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_banner_for_cms(self) -> dict:
        """
        fetching the banners for cms
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_or_update_banner(self, req_body) -> dict:
        """
        creating or updating the banners for cms
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_banner(self, banner_id) -> dict:
        """
        deleting the banners for cms
        """
        raise NotImplementedError

    @abc.abstractmethod
    def check_banner(self, start_time, end_time) -> dict:
        """
        checking and returning the banners in given time interval
        """
        raise NotImplementedError
