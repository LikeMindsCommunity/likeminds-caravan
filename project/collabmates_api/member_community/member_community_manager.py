import abc


class MemberCommunityManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'extract_member_communities') and callable(subclass.extract_member_communities)) and
                (hasattr(subclass, 'community_member_state') and callable(subclass.community_member_state)) and
                (hasattr(subclass, 'fetch_feed') and callable(subclass.fetch_feed)) and
                (hasattr(subclass, 'fetch_home_communities') and callable(subclass.fetch_home_communities)) and
                (hasattr(subclass, 'fetch_feed_meta') and callable(subclass.fetch_feed_meta)) and
                (hasattr(subclass, 'fetch_feed_web') and callable(subclass.fetch_feed_web)) and
                (hasattr(subclass, 'fetch_chatroom_home') and callable(subclass.fetch_chatroom_home)) or
                NotImplemented)

    @abc.abstractmethod
    def extract_member_communities(self) -> None:
        """
        Get communities of the member
        """
        raise NotImplementedError

    @abc.abstractmethod
    def community_member_state(self) -> int:
        """
        returns member state in community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_feed(self, pin_status, chatroom_id=None, scroll_direction=None) -> {}:
        """
        fetches the chatrooms of community
        """
        raise NotImplementedError

    def fetch_home_communities(self, page) -> {}:
        """
        fetches the home communities of member
        """
        raise NotImplementedError

    def fetch_feed_meta(self) -> {}:
        """
        fetched the feed meta to show on the top of community feed screen
        """
        raise NotImplementedError

    def fetch_feed_web(self, pin_status, chatroom_id=None, scroll_direction=None) -> {}:
        """
        fetched the feed data for web
        """
        raise NotImplementedError

    def fetch_chatroom_home(self, chatroom_id) -> {}:
        """
        fetches the chatroom home data for particular id
        """
        raise NotImplementedError

    def pending_onboarding_communities(self, page_no, paginate_by) -> {}:

        """
        fetches all the communities in which onboarding is pending
        """

        raise NotImplementedError

    def completed_onboarding_communites(self) -> {}:

        """set the onboarding flag to true for user who have completed the onboarding"""

        raise NotImplementedError

