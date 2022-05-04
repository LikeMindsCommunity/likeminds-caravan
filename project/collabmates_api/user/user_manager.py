import abc


class UserManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'delete_user') and callable(subclass.delete_user)) and
                (hasattr(subclass, 'survey_seen') and callable(subclass.survey_seen)) and
                (hasattr(subclass, 'logout') and callable(subclass.logout)) and
                (hasattr(subclass, 'remove_profile') and callable(subclass.remove_profile)) and
                (hasattr(subclass, 'login') and callable(subclass.login)) and
                (hasattr(subclass, 'fetch_all_users') and callable(subclass.fetch_all_users)) and
                (hasattr(subclass, 'fetch_app_access') and callable(subclass.fetch_app_access)) and
                (hasattr(subclass, 'fetch_dm_home') and callable(subclass.fetch_dm_home)) and
                (hasattr(subclass, 'update_dm_tutorial') and callable(subclass.update_dm_tutorial)) and
                (hasattr(subclass, 'fetch_dm_feed') and callable(subclass.fetch_dm_feed)) and
                (hasattr(subclass, 'create_user_bot') and callable(subclass.create_user_bot)) or
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

    @abc.abstractmethod
    def remove_profile(self) -> {}:
        """
        remove the profile of user permanently from LikeMinds
        """
        raise NotImplementedError

    @abc.abstractmethod
    def login(self, req_body, platform_code, device_id, version_code) -> {}:
        """
        login the user into our system
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_app_access(self) -> dict:
        """
        fetch user's approval pending and subscription expired communities
        """
        raise NotImplementedError

    @staticmethod
    def fetch_user_verified_mobile_numbers(user_id_list) -> dict:
        """
        fetch users verified mobile numbers list
        """
        raise NotImplementedError

    @staticmethod
    def fetch_user_verified_emails(user_id_list) -> dict:
        """
        fetch users verified email ids list
        """
        raise NotImplementedError

    def fetch_dm_home(self) -> dict:
        """
        Get whether DM Messages are clicked or not
        """
        raise NotImplementedError

    def update_dm_tutorial(self, req_body) -> dict:
        """
        Update Direct Message Tutorial Table on member_id
        """
        raise NotImplementedError

    def fetch_dm_feed(self, community_id: str) -> dict:
        """
        Check whether the Direct Message Right Enabled or not
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_all_users(self, page, user_ids) -> dict:
        """
        returns all the users corresponding to given user_ids
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_user_bot(self, req_body) -> dict:
        """
        Creates a user bot
        """
        raise NotImplementedError


