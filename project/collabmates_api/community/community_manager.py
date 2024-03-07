import abc


class CommunityManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
                    (
                            hasattr(subclass, 'create_community') and
                            callable(subclass.create_community)
                    ) and
                    (
                            hasattr(subclass, 'fetch_community') and
                            callable(subclass.fetch_community)
                    ) and
                    (
                            hasattr(subclass, 'get_community_members') and
                            callable(subclass.get_community_members)
                    ) and
                    (
                            hasattr(subclass, 'fetch_all_communities') and
                            callable(subclass.fetch_all_communities)
                    ) and
                    (
                            hasattr(subclass, 'fetch_chatroom_feed') and
                            callable(subclass.fetch_chatroom_feed)
                    ) and
                    (
                            hasattr(subclass, 'delete_community') and
                            callable(subclass.delete_community)
                    ) and
                    (
                            hasattr(subclass, 'fetch_feed_url') and
                            callable(subclass.fetch_feed_url)
                    ) and
                    (
                            hasattr(subclass, 'fetch_feed_url') and
                            callable(subclass.fetch_feed_url_for_cm_onboarding)
                    ) and
                    (
                            hasattr(subclass, 'fetch_otl_url') and
                            callable(subclass.fetch_otl_url)
                    ) and
                    (
                            hasattr(subclass, 'fetch_discoverable_communities') and
                            callable(subclass.fetch_discoverable_communities)
                    ) and
                    (
                            hasattr(subclass, 'fetch_content_download_settings') and
                            callable(subclass.fetch_content_download_settings)
                    ) and
                    (
                            hasattr(subclass, 'update_content_download_settings') and
                            callable(subclass.update_content_download_settings)
                    ) and
                    (
                            hasattr(subclass, 'fetch_community_settings') and
                            callable(subclass.fetch_community_settings)
                    ) and
                    (
                            hasattr(subclass, 'update_community_settings') and
                            callable(subclass.update_community_settings)
                    ) and
                    (
                            hasattr(subclass, 'fetch_community_toasts_v1') and
                            callable(subclass.fetch_community_toasts_v1)
                    ) and
                    (
                            hasattr(subclass, 'update_community_toast_v1') and
                            callable(subclass.update_community_toast_v1)
                    ) and
                    (
                            hasattr(subclass, 'add_join_email') and
                            callable(subclass.add_join_email)
                    ) and
                    (
                            hasattr(subclass, 'fetch_join_email') and
                            callable(subclass.fetch_join_email)
                    ) and
                    (
                            hasattr(subclass, 'fetch_payment_page_url') and
                            callable(subclass.fetch_payment_page_url)
                    ) and
                    (
                            hasattr(subclass, 'fetch_get_started') and
                            callable(subclass.fetch_get_started)
                    ) and
                    (
                            hasattr(subclass, 'send_invite') and
                            callable(subclass.send_invite)
                    ) and
                    (
                            hasattr(subclass, 'edit_questions') and
                            callable(subclass.edit_questions)
                    ) and
                    (
                            hasattr(subclass, 'fetch_community_questions') and
                            callable(subclass.fetch_community_questions)
                    ) and
                    (
                            hasattr(subclass, 'fetch_community_branding_info') and
                            callable(subclass.fetch_community_branding_info)
                    ) and
                    (
                            hasattr(subclass, 'fetch_community_id_from_domain') and
                            callable(subclass.fetch_community_id_from_domain)
                    ) and
                    (
                            hasattr(subclass, 'update_community_dm_settings') and
                            callable(subclass.update_community_dm_settings)
                    ) and
                    (
                            hasattr(subclass, 'fetch_community_dm_settings') and
                            callable(subclass.fetch_community_dm_settings)
                    ) and
                    (
                            hasattr(subclass, 'fetch_community_dm_right') and
                            callable(subclass.fetch_community_dm_right)
                    ) and
                    (
                            hasattr(subclass, 'fetch_community_id_from_domain') and
                            callable(subclass.fetch_community_id_from_domain)
                    ) and
                    (
                            hasattr(subclass, 'edit_community') and
                            callable(subclass.edit_community)
                    ) and
                    (
                            hasattr(subclass, 'add_community_member') and
                            callable(subclass.add_community_member)
                    ) and
                    (
                            hasattr(subclass, 'update_community_member') and
                            callable(subclass.update_community_member)
                    ) and
                    (
                            hasattr(subclass, 'update_community_noti_settings') and
                            callable(subclass.update_community_noti_settings)
                    ) and
                    (
                            hasattr(subclass, 'fetch_community_noti_settings') and
                            callable(subclass.fetch_community_noti_settings)
                    ) and
                    (
                            hasattr(subclass, 'fetch_feed_notification_settings') and
                            callable(subclass.fetch_feed_notification_settings)
                    ) and
                    (
                            hasattr(subclass, 'update_feed_notification_settings') and
                            callable(subclass.update_feed_notification_settings)
                    ) and
                    (
                            hasattr(subclass, 'fetch_users_meta_info') and
                            callable(subclass.fetch_users_meta_info)
                    ) and 
                    (
                            hasattr(subclass, 'fetch_community_removal_reports') and
                            callable(subclass.fetch_community_removal_reports)
                    ) or
                    NotImplemented
        )

    @abc.abstractmethod
    def create_community(self, req_body) -> {}:
        """
        creates new community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_community(self, client_type, platform_code: str, version_code: int):
        """
        fetches the community from the database
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_community_members(self) -> list:
        """
         returns list of all community members
        """
        raise NotImplementedError

    def fetch_all_communities(self, page):
        """
        Fetches all the communities from the database order by latest
        """
        raise NotImplementedError

    def fetch_chatroom_feed(self, size):
        """fetched the chatrooms of the community"""

        raise NotImplementedError

    def delete_community(self):
        """deletes the community from the system"""

        raise NotImplementedError

    def approve_or_decline_community(self, req_body):
        """approves or declines community"""

        raise NotImplementedError

    def fetch_feed_url(self):
        """returns community feed url as a branch link"""

        raise NotImplementedError

    def fetch_feed_url_for_cm_onboarding(self):
        """returns community feed url for cm onboarding as a branch link"""

        raise NotImplementedError

    def fetch_otl_url(self, payment_id, shared_by_id):
        """returns community otl url as a branch link"""

        raise NotImplementedError

    def fetch_discoverable_communities(self, page, page_size):
        """returns communities objects which are discoverable"""

        raise NotImplementedError

    def join_community(self, req_body):
        """make a user either a pending member or a member in community"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_members_meta(self, member_ids, search_name: str = None, page: int = None, page_size: int = None, order_by_name: bool = None):
        """returns list of members to create secret chatrooms"""

        raise NotImplementedError
    
    def fetch_members_meta_v2(self, member_ids, page, page_size, search_name):
        """returns members meta data of given community or member_ids"""

        raise NotImplementedError


    def fetch_content_download_settings(self):
        """returns List of Content Download Settings for a community"""

        raise NotImplementedError

    def update_content_download_settings(self, content_download_settings_list):
        """returns boolean whether the update of settings is a success or a failure"""

        raise NotImplementedError

    def fetch_community_settings(self):
        """returns list of settings for a community"""

        raise NotImplementedError

    def update_community_settings(self, community_settings_list):
        """updates list of settings for a community"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_community_toasts_v1(self):
        """fetches community toasts against user for community"""

        raise NotImplementedError

    @abc.abstractmethod
    def update_community_toast_v1(self, toast_id):
        """updates community toasts against user for community"""

        raise NotImplementedError

    @abc.abstractmethod
    def add_join_email(self, req_body):
        """ add join email for a community """

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_join_email(self):
        """ fetches join email for a community"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_payment_page_url(self, payment_page_id):
        """ fetches branch link for payment pages"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_get_started(self) -> {}:
        """ fetches get started for community"""

        raise NotImplementedError

    @abc.abstractmethod
    def send_invite(self, req_body) -> {}:
        """ Send email or whatsapp invite """

        raise NotImplementedError

    @abc.abstractmethod
    def edit_questions(self, req_body) -> {}:
        """ Create, update or delete community questions """

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_community_questions(self, req_body) -> {}:
        """ Fetches community questions """

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_community_branding_info(self, req_body) -> {}:
        """ Fetches community branding info """

        raise NotImplementedError
    
    @abc.abstractmethod
    def fetch_community_id_from_domain(self, req_body) -> dict:
        """ Fetches community id from doamin """
        
        raise NotImplementedError

    @abc.abstractmethod
    def update_community_dm_settings(self, req_body, api_revamp_v1_check=False) -> {}:
        """ Updates community DM settings in db """

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_community_dm_settings(self, api_revamp_v1_check=False) -> {}:
        """ Fetches community DM settings from db """

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_community_dm_right(self, req_body) -> {}:
        """ Fetches community DM rights from cohorts """

        raise NotImplementedError

    @abc.abstractmethod
    def edit_community(self, req_body) -> dict:
        """
        edit community object
        """

        raise NotImplementedError

    @abc.abstractmethod
    def add_community_member(self, req_body: dict) -> {}:
        """ Add member to community using SDK dashboard"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_community_noti_settings(self, api_revamp_v1_check=False) -> {}:
        """Fetches notification settings of community"""

        raise NotImplementedError

    @abc.abstractmethod
    def update_community_noti_settings(self, req_body: dict) -> {}:
        """Updates notification settings of community"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_feed_notification_settings(self, api_revamp_v1_check=False) -> {}:
        """Fetches feed notification settings of community"""

        raise NotImplementedError

    @abc.abstractmethod
    def update_feed_notification_settings(self, notification_settings: list) -> {}:
        """Updates feed notification settings of community"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_users_meta_info(self, member_ids: list) -> dict:
        """
        Fetches users meta info
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_community_removal_reports(self) -> dict:
        """
        Fetches community removal reports
        """
        raise NotImplementedError
    
    @abc.abstractmethod
    def fetch_community_configurations(self, configuration_types=None) -> dict:
        """
        Fetches community configurations
        """
        raise NotImplementedError
    
    @abc.abstractmethod
    def update_community_configurations(self, req_body: dict = None) -> dict:
        """
        Updates community configurations
        """
        raise NotImplementedError
