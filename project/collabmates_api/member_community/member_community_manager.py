import abc


class MemberCommunityManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'extract_member_communities') and callable(subclass.extract_member_communities)) and
                (hasattr(subclass, 'community_member_state') and callable(subclass.community_member_state)) and
                (hasattr(subclass, 'fetch_feed') and callable(subclass.fetch_feed)) and
                (hasattr(subclass, 'fetch_feed_v3') and callable(subclass.fetch_feed_v3)) and
                (hasattr(subclass, 'fetch_home_communities') and callable(subclass.fetch_home_communities)) and
                (hasattr(subclass, 'fetch_feed_meta') and callable(subclass.fetch_feed_meta)) and
                (hasattr(subclass, 'fetch_feed_web') and callable(subclass.fetch_feed_web)) and
                (hasattr(subclass, 'fetch_chatroom_home') and callable(subclass.fetch_chatroom_home)) and
                (hasattr(subclass, 'pending_onboarding_communities') and callable(
                    subclass.pending_onboarding_communities)) and
                (hasattr(subclass, 'completed_onboarding_communites') and callable(
                    subclass.completed_onboarding_communites)) and
                (hasattr(subclass, 'fetch_deleted_communities') and callable(
                    subclass.fetch_deleted_communities)) and
                (hasattr(subclass, 'fetch_members_detail') and callable(subclass.fetch_members_detail)) and
                (hasattr(subclass, 'show_dm') and callable(subclass.show_dm)) and
                (hasattr(subclass, 'fetch_member_profile') and callable(subclass.fetch_member_profile)) and
                (hasattr(subclass, 'edit_member_profile') and callable(subclass.edit_member_profile)) and
                (hasattr(subclass, 'request_dm_limit') and callable(subclass.request_dm_limit)) and
                (hasattr(subclass, 'fetch_dm_chatrooms') and callable(subclass.fetch_dm_chatrooms)) and
                (hasattr(subclass, 'join_community_sdk') and callable(subclass.join_community_sdk)) and
                (hasattr(subclass, 'member_can_dm') and callable(subclass.member_can_dm)) and
                (hasattr(subclass, 'unsubscribe_email_notifications') and
                 callable(subclass.unsubscribe_email_notifications)) and
                (hasattr(subclass, 'fetch_member_access') and callable(subclass.fetch_member_access)) and
                (hasattr(subclass, 'fetch_post_feed') and callable(subclass.fetch_post_feed)) and
                (hasattr(subclass, 'fetch_excluded_chatrooms_for_user') and callable(
                    subclass.fetch_excluded_chatrooms_for_user)) and
                (hasattr(subclass, 'fetch_user_chatroom_status') and callable(
                    subclass.fetch_user_chatroom_status)) or
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
    def fetch_feed(self, pin_status, order_type, chatroom_id=None, scroll_direction=None, api_version="", page=1) -> {}:
        """
        fetches the chatrooms of community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_feed_v3(self, pin_status, order_type, page: int = None, page_size: int = None) -> {}:
        """
        fetches the chatrooms of community for explore
        """
        raise NotImplementedError

    def fetch_home_communities(self, page, show_dm=False, is_cm=False, is_paid=False) -> {}:
        """
        fetches the home communities of member
        """
        raise NotImplementedError

    def fetch_feed_meta(self) -> {}:
        """
        fetched the feed meta to show on the top of community feed screen
        """
        raise NotImplementedError

    def fetch_feed_web(self, pin_status, order_type, chatroom_id=None, scroll_direction=None, api_version="",
                       page=1) -> {}:
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

    def fetch_deleted_communities(self) -> {}:
        """returns the list of deleted communities for which earlier user is part of"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_members_detail(self, page, page_size) -> dict:
        """
        Get member details of community
        """
        raise NotImplementedError

    def show_dm(self, req_body) -> {}:
        """returns whether to show the message icons on client side for CM or Member"""

        raise NotImplementedError

    def fetch_member_profile(self, member_id: str) -> {}:
        """returns member profile"""

        raise NotImplementedError

    def edit_member_profile(self, req_body: dict) -> {}:
        """Edits member profile"""

        raise NotImplementedError

    def request_dm_limit(self, member_id: str) -> {}:
        """Returns DM limit connection request meta for user"""

        raise NotImplementedError

    def fetch_dm_chatrooms(self, page: int) -> {}:
        """Returns list of DM chatrooms user is part of"""

        raise NotImplementedError

    def member_can_dm(self, req_body: dict) -> {}:
        """Returns whether member can DM other member or not"""

        raise NotImplementedError

    def join_community_sdk(self, req_body: dict) -> {}:
        """Member joins a community in SDK"""

        raise NotImplementedError

    def unsubscribe_email_notifications(self, code_flags: dict) -> {}:
        """Updates unsubscribe table according to whether notification send or not"""

        raise NotImplementedError

    def fetch_member_access(self, access_type: str) -> {}:
        """Fetches a user access for given access_type"""

        raise NotImplementedError

    def fetch_post_feed(self, order_type: int = 0, pinned:bool = False, page: int = 1, page_size: int = 10,
                        chatroom_ids: list = None):
        """Fetches the post feed data"""

        raise NotImplementedError

    def fetch_excluded_chatrooms_for_user(self):
        """Fetches the list of excluded chatroom ids for a user"""

        raise NotImplementedError

    def fetch_user_chatroom_status(self, user_id: str = None, chatroom_types: list = None, page: int = None,
                                   page_size: int = None) -> dict:
        """Fetches user chatroom joining status"""

        raise NotImplementedError
