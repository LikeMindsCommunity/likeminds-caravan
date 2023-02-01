import abc
from typing import Union
from django.db.models import QuerySet


class ChatroomManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
                    (
                            hasattr(subclass, 'fetch_chatroom') and
                            callable(subclass.fetch_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'fetch_all_chatroom') and
                            callable(subclass.fetch_all_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'create_chatroom') and
                            callable(subclass.create_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'get_chatroom_participants') and
                            callable(subclass.get_chatroom_participants)
                    ) and
                    (
                            hasattr(subclass, 'pin_or_unpin_chatroom') and
                            callable(subclass.pin_or_unpin_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'leave_secret_chatroom') and
                            callable(subclass.leave_secret_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'add_secret_chatroom_participant') and
                            callable(subclass.add_secret_chatroom_participant)
                    ) and
                    (
                            hasattr(subclass, 'get_tagging_list') and
                            callable(subclass.get_tagging_list)
                    ) and
                    (
                            hasattr(subclass, 'edit_chatroom') and
                            callable(subclass.edit_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'follow_chatroom_automatically_for_all_members_of_community') and
                            callable(subclass.follow_chatroom_automatically_for_all_members_of_community)
                    ) and
                    (
                            hasattr(subclass, 'fetch_participants_of_secret_chatroom') and
                            callable(subclass.fetch_participants_of_secret_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'create_event') and
                            callable(subclass.create_event)
                    ) and
                    (
                            hasattr(subclass, 'update_event') and
                            callable(subclass.update_event)
                    ) and
                    (
                            hasattr(subclass, 'add_or_update_instructor') and
                            callable(subclass.add_or_update_instructor)
                    ) and
                    (
                            hasattr(subclass, 'add_or_update_highlights') and
                            callable(subclass.add_or_update_highlights)
                    ) and
                    (
                            hasattr(subclass, 'add_or_update_member_testimonials') and
                            callable(subclass.add_or_update_member_testimonials)
                    ) and
                    (
                            hasattr(subclass, 'add_or_update_event_faq') and
                            callable(subclass.add_or_update_event_faq)
                    ) and
                    (
                            hasattr(subclass, 'update_last_seen_event') and
                            callable(subclass.update_last_seen_event)
                    ) and
                    (
                            hasattr(subclass, 'fetch_unseen_count_in_event') and
                            callable(subclass.fetch_unseen_count_in_event)
                    ) and
                    (
                            hasattr(subclass, 'fetch_link_for_event') and
                            callable(subclass.fetch_link_for_event)
                    ) and
                    (
                            hasattr(subclass, 'fetch_user_all_events') and
                            callable(subclass.fetch_user_all_events)
                    ) and
                    (
                            hasattr(subclass, 'fetch_user_all_events_meta') and
                            callable(subclass.fetch_user_all_events_meta)
                    ) and
                    (
                            hasattr(subclass, 'attend_event') and
                            callable(subclass.attend_event)
                    ) and
                    (
                            hasattr(subclass, 'set_event_attended') and
                            callable(subclass.set_event_attended)
                    ) and
                    (
                            hasattr(subclass, 'toggle_member_message_post') and
                            callable(subclass.toggle_member_message_post)
                    ) and
                    (
                            hasattr(subclass, 'fetch_chatroom_settings') and
                            callable(subclass.fetch_chatroom_settings)
                    ) and
                    (
                            hasattr(subclass, 'add_members_to_chatroom') and
                            callable(subclass.add_members_to_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'update_files') and
                            callable(subclass.update_files)
                    ) and
                    (
                            hasattr(subclass, 'fetch_event_link_for_dashboard') and
                            callable(subclass.fetch_event_link_for_dashboard)
                    ) and
                    (
                            hasattr(subclass, 'update_access_without_subscription') and
                            callable(subclass.update_access_without_subscription)
                    ) and
                    (
                            hasattr(subclass, 'fetch_access_for_chatroom') and
                            callable(subclass.fetch_access_for_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'remove_cohort_from_chatroom') and
                            callable(subclass.remove_cohort_from_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'add_cohort_to_chatroom') and
                            callable(subclass.add_cohort_to_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'fetch_chatroom_participants') and
                            callable(subclass.fetch_chatroom_participants)
                    ) and
                    (
                            hasattr(subclass, 'publish_event_webflow') and
                            callable(subclass.publish_event_webflow)
                    ) and
                    (
                            hasattr(subclass, 'change_chatroom_type') and
                            callable(subclass.change_chatroom_type)
                    ) and
                    (
                            hasattr(subclass, 'create_dm_chatroom') and
                            callable(subclass.create_dm_chatroom)
                    ) and
                    (
                            hasattr(subclass, 'block_member') and
                            callable(subclass.block_member)
                    ) and
                    (
                            hasattr(subclass, 'request_dm') and
                            callable(subclass.request_dm)
                    ) and
                    (
                            hasattr(subclass, 'scheduled_chatroom_follow') and
                            callable(subclass.scheduled_chatroom_follow)
                    ) and
                    (
                            hasattr(subclass, 'fetch_chatroom_noti_settings') and
                            callable(subclass.fetch_chatroom_noti_settings)
                    ) and
                    (
                            hasattr(subclass, 'update_chatroom_noti_settings') and
                            callable(subclass.update_chatroom_noti_settings)
                    ) and
                    (
                            hasattr(subclass, 'remove_chatroom_participant') and
                            callable(subclass.remove_chatroom_participant)
                    ) and
                    (
                            hasattr(subclass, 'get_chatroom_participants_list') and
                            callable(subclass.get_chatroom_participants_list)
                    ) or
                    NotImplemented
        )

    @abc.abstractmethod
    def fetch_chatroom(self, is_internal=False) -> dict:
        """
        fetching the chatroom from chatroom id
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_all_chatroom(self, page: int = 1, chatroom_type: int = -1) -> dict:
        """
        Fetch all chatrooms in community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_chatroom(self, req_body: dict) -> dict:
        """
        create chatroom
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_chatroom_participants(self, filter_dict: dict) -> QuerySet:
        """
        returns chatroom participants list with given filter
        """
        raise NotImplementedError

    @abc.abstractmethod
    def pin_or_unpin_chatroom(self, req_body: dict) -> dict:
        """
        make chatroom pin or unpin
        """
        raise NotImplementedError

    @abc.abstractmethod
    def leave_secret_chatroom(self, member_id: Union[int, str] = None) -> None:
        """
        to leave or remove a participant from secret chatroom
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_secret_chatroom_participant(self, req_body: dict) -> dict:
        """
        to add a participant in secret chatroom
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_tagging_list(self) -> dict:
        """return the tagging list of users in chatroom"""

        raise NotImplementedError

    @abc.abstractmethod
    def follow_chatroom_automatically_for_all_members_of_community(self, member_id, request_body) -> dict:
        """
        to auto follow a chatroom
        """

        raise NotImplementedError

    @abc.abstractmethod
    def edit_chatroom(self, req_body) -> dict:
        """edit the chatroom for first message action"""

        raise NotImplementedError

    def create_introduction_card_in_community(self, community_instance, user_instance, req_body, member_state,
                                              master_intro_instance):
        """create the introduction card of community"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_participants_of_secret_chatroom(self, participant_name: str = None, page: int = None,
                                              page_size: int = None):
        """returns list of participants of secret chatrooms"""

        raise NotImplementedError

    @abc.abstractmethod
    def create_event(self, req_body: dict) -> dict:
        """
        create event chatroom
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_or_update_instructor(self, req_body: dict) -> dict:
        """
        adding instructor in event
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_or_update_highlights(self, req_body: dict) -> dict:
        """
        adding highlights in event
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_or_update_member_testimonials(self, req_body: dict) -> dict:
        """
        adding member testimonials in event
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_or_update_event_faq(self, req_body: dict) -> dict:
        """
        adding FAQ in event
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_last_seen_event(self) -> dict:
        """
        adding last seen event on platform
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_unseen_count_in_event(self) -> dict:
        """
        fetch unseen count in event
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_link_for_event(self) -> dict:
        """
        fetch online link for event
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_user_all_events(self, page, attending_status, has_content, past_events=False, community_id=None) -> dict:
        """
        fetch attending events of user
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_user_all_events_meta(self, past_events=False, community_id=None) -> dict:
        """
        fetch meta data for attending events of user
        """
        raise NotImplementedError

    @abc.abstractmethod
    def attend_event(self, status) -> dict:
        """
        function to attend event
        """

        raise NotImplementedError

    @abc.abstractmethod
    def update_event(self, req_body) -> dict:
        """
        function to update event
        """

        raise NotImplementedError

    @abc.abstractmethod
    def set_event_attended(self) -> dict:
        """
        function to set user attended event
        """

        raise NotImplementedError

    @abc.abstractmethod
    def toggle_member_message_post(self, value) -> dict:
        """
        function to allow members to send message in chatroom
        """

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_chatroom_settings(self) -> dict:
        """
        function to fetch chatroom settings
        """

        raise NotImplementedError

    @abc.abstractmethod
    def add_members_to_chatroom(self, chatroom_participants) -> dict:
        """
        function to add members to the chatroom
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_files(self, req_body) -> dict:
        """
        function to update the files in chatroom
        """

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_event_link_for_dashboard(self) -> dict:
        """
        returns the online links for event dashboard
        """

        raise NotImplementedError

    @abc.abstractmethod
    def update_access_without_subscription(self, value) -> dict:
        """
        updates without subscription access value
        """

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_access_for_chatroom(self) -> dict:
        """
        returns access, remove_state and community object for a chatroom
        """

        raise NotImplementedError

    @abc.abstractmethod
    def remove_cohort_from_chatroom(self, request_body) -> dict:
        """
        function to remove cohort from the chatroom
        """

        raise NotImplementedError

    @abc.abstractmethod
    def add_cohort_to_chatroom(self, request_body) -> dict:
        """
        function to add cohorts to the chatroom
        """

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_chatroom_participants(self, participant_name: str = None, page: int = None, page_size: int = None):
        """
        function to fetch chatroom participants meta data
        """

        raise NotImplementedError

    @abc.abstractmethod
    def publish_event_webflow(self, req_body) -> dict:
        """
        Publishes the events in webflow
        """

        raise NotImplementedError

    @abc.abstractmethod
    def change_chatroom_type(self, req_body) -> dict:
        """
        Changes chatroom type(secret/open)
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get_change_chatroom_type_status(self) -> dict:
        """
        Get chatroom type(secret/open) change status
        """

        raise NotImplementedError

    @abc.abstractmethod
    def create_dm_chatroom(self, req_body) -> dict:
        """
        Creates a DM chatroom
        """

        raise NotImplementedError

    @abc.abstractmethod
    def block_member(self, req_body) -> dict:
        """
        Block/Unblock member in chatroom
        """

        raise NotImplementedError

    @abc.abstractmethod
    def request_dm(self, req_body) -> dict:
        """
        Initiate, accept ot reject a connection request in DM chatroom
        """

        raise NotImplementedError

    @abc.abstractmethod
    def scheduled_chatroom_follow(self, req_body) -> dict:
        """
        Follow chatroom for a user async
        """

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_chatroom_noti_settings(self) -> {}:
        """Fetches notification settings of chatroom"""

        raise NotImplementedError

    @abc.abstractmethod
    def update_chatroom_noti_settings(self, noti_state, is_noti_paused, pause_noti_for) -> {}:
        """Updates notification settings of chatroom"""

        raise NotImplementedError

    @abc.abstractmethod
    def remove_chatroom_participant(self, removed_members_list: list = None) -> {}:
        """Removes a participant from chatroom"""

        raise NotImplementedError

    @abc.abstractmethod
    def get_chatroom_participants_list(self) -> list:
        """
        returns chatroom participants list
        """
        raise NotImplementedError
