import abc


class CommunityManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'fetch_community') and callable(subclass.fetch_community) and
                (hasattr(subclass, 'fetch_chatroom_feed') and callable(subclass.fetch_chatroom_feed)) and
                (hasattr(subclass, 'delete_community') and callable(subclass.delete_community) and
                 (hasattr(subclass, 'fetch_feed_url') and callable(subclass.fetch_feed_url)) and
                 (hasattr(subclass, 'fetch_discoverable_communities') and callable(
                     subclass.fetch_discoverable_communities))) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_community(self, client_type):
        """
        fetches the community from the database
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

    def fetch_discoverable_communities(self, page, page_size):
        """returns communities objects which are discoverable"""

        raise NotImplementedError
