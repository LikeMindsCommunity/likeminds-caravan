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
                (hasattr(subclass, 'create_user_bot') and callable(subclass.create_user_bot)) and
                (hasattr(subclass, 'update_user_bot') and callable(subclass.update_user_bot)) and
                (hasattr(subclass, 'fetch_user_bot') and callable(subclass.fetch_user_bot)) and
                (hasattr(subclass, 'fetch_user_info') and callable(subclass.fetch_user_info)) and
                (hasattr(subclass, 'whatsapp_subscription') and callable(subclass.whatsapp_subscription)) and
                (hasattr(subclass, 'send_user_otp') and callable(subclass.send_user_otp)) and
                (hasattr(subclass, 'verify_user_otp') and callable(subclass.verify_user_otp)) and
                (hasattr(subclass, 'user_social_login') and callable(subclass.user_social_login)) and
                (hasattr(subclass, 'user_meta') and callable(subclass.user_meta)) or
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
    def login(self, req_body, platform_code, device_id, version_code, api_key: str = None) -> {}:
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

    def fetch_dm_feed(self) -> dict:
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

    @abc.abstractmethod
    def update_user_bot(self, req_body) -> dict:
        """
        Updates a user bot
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_user_bot(self, api_key: str = None, community_id: str = None) -> dict:
        """
        Fetches a user bot
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_user_info(self) -> dict:
        """
        Fetches user info
        """
        raise NotImplementedError

    @abc.abstractmethod
    def whatsapp_subscription(self, req_body: dict) -> dict:
        """
        Manages whatsapp subscription of users
        """
        raise NotImplementedError

    @abc.abstractmethod
    def send_user_otp(self, otp_type: str, mobile_no: str = int, country_code: str = int, email_id: str = None,
                      is_retry: bool = False) -> dict:
        """
        Sends OTP to user
        """
        raise NotImplementedError

    @abc.abstractmethod
    def verify_user_otp(self, otp_type: str, mobile_no: int = None, country_code: int = None, email_id: str = None,
                        otp: str = None) -> dict:
        """
        Verify user OTPs
        """
        raise NotImplementedError

    @abc.abstractmethod
    def user_social_login(self, login_type: str, token: str) -> dict:
        """
        Verify user OTPs
        """
        raise NotImplementedError

    @abc.abstractmethod
    def user_meta(self) -> dict:
        """
        Fetch user meta corresponding to member id
        """
        raise NotImplementedError
