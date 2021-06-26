import abc
from typing import Union


class ChatroomManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'fetch_chatroom') and callable(subclass.fetch_chatroom)) and
                (hasattr(subclass, 'create_chatroom') and callable(subclass.create_chatroom)) and
                (hasattr(subclass, 'set_chatroom_active_or_inactive') and
                 callable(subclass.set_chatroom_active_or_inactive)) and
                (hasattr(subclass, 'pin_or_unpin_chatroom') and
                 callable(subclass.pin_or_unpin_chatroom)) and
                (hasattr(subclass, 'leave_secret_chatroom') and
                 callable(subclass.leave_secret_chatroom)) and
                (hasattr(subclass, 'add_secret_chatroom_participant') and
                 callable(subclass.add_secret_chatroom_participant)) and
                (hasattr(subclass, 'get_tagging_list') and
                 callable(subclass.get_tagging_list)) and
                (hasattr(subclass, 'edit_chatroom') and
                 callable(subclass.edit_chatroom)) and
                (hasattr(subclass, 'follow_chatroom_automatically_for_all_members_of_community') and
                 callable(subclass.follow_chatroom_automatically_for_all_members_of_community)) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_chatroom(self) -> dict:
        """
        fetching the chatroom from chatroom id
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_chatroom(self, req_body: dict) -> dict:
        """
        create chatroom
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_chatroom_active_or_inactive(self, req_body: dict) -> dict:
        """
        make chatroom active or in-active
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
    def follow_chatroom_automatically_for_all_members_of_community(self, member_id, chatroom_id) -> dict:
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
