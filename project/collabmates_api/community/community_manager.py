import abc


class CommunityManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'fetch_community') and callable(subclass.fetch_community)) and
                (hasattr(subclass, 'fetch_all_communities') and callable(subclass.fetch_all_communities)) and
                (hasattr(subclass, 'fetch_chatroom_feed') and callable(subclass.fetch_chatroom_feed)) and
                (hasattr(subclass, 'delete_community') and callable(subclass.delete_community)) and
                (hasattr(subclass, 'fetch_feed_url') and callable(subclass.fetch_feed_url)) and
                (hasattr(subclass, 'fetch_otl_url') and callable(subclass.fetch_otl_url)) and
                (hasattr(subclass, 'fetch_discoverable_communities') and callable(subclass.fetch_discoverable_communities)) and
                (hasattr(subclass, 'fetch_content_download_settings') and callable(subclass.fetch_content_download_settings)) and
                (hasattr(subclass, 'update_content_download_settings') and callable(subclass.update_content_download_settings)) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_community(self, client_type):
        """
        fetches the community from the database
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
    def fetch_members_meta(self, community_id):
        """returns list of members to create secret chatrooms"""

        raise NotImplementedError

    def fetch_content_download_settings(self):
        """returns List of Content Download Settings for a community"""

        raise NotImplementedError

    def update_content_download_settings(self, content_download_settings_list):
        """returns boolean whether the update of settings is a success or a failure"""

        raise NotImplementedError
