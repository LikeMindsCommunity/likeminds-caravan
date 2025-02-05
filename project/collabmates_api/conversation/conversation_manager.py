import abc


class ConversationManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'fetch_conversation') and callable(subclass.fetch_conversation)) and
                (hasattr(subclass, 'create_conversation') and callable(subclass.create_conversation)) and
                (hasattr(subclass, 'create_conversation_v1') and callable(subclass.create_conversation_v1)) and
                (hasattr(subclass, 'add_poll') and callable(subclass.add_poll)) and
                (hasattr(subclass, 'submit_poll') and callable(subclass.submit_poll)) and
                (hasattr(subclass, 'poll_users') and callable(subclass.poll_users)) and
                (hasattr(subclass, 'add_reaction') and callable(subclass.add_reaction)) and
                (hasattr(subclass, 'remove_reaction') and callable(subclass.remove_reaction)) and
                (hasattr(subclass, 'set_chatroom_topic') and callable(subclass.set_chatroom_topic)) and
                (hasattr(subclass, 'attend_event') and callable(subclass.attend_event)) and
                (hasattr(subclass, 'set_event_attended') and callable(subclass.set_event_attended)) and
                (hasattr(subclass, 'update_last_seen_event') and callable(subclass.update_last_seen_event)) and
                (hasattr(subclass, 'fetch_unseen_count_in_event') and callable(subclass.fetch_unseen_count_in_event)) and
                (hasattr(subclass, 'fetch_link_for_event') and callable(subclass.fetch_link_for_event)) and
                (hasattr(subclass, 'create_message_task') and callable(subclass.create_message_task)) and
                (hasattr(subclass, 'fetch_user_all_events') and callable(subclass.fetch_user_all_events)) or
                NotImplemented)

    @abc.abstractmethod
    def fetch_conversation(self, top_navigate=False, excluded_conversation_states: list = None) -> list:
        """
        fetches the conversation from the database
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_conversation(self, req_body: dict, is_ios: bool,
                            is_user_guest: bool, **kwargs) -> dict:
        """
        create conversation
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_conversation_v1(self, req_body: dict) -> dict:
        """
        create conversation revamp
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_message_task(self, req_body: dict) -> dict:
        """
        perform async tasks after create message in pandemonium
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_reaction(self, req_body: dict) -> dict:
        """
        add reaction to a conversation or chatroom
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_reaction(self) -> dict:
        """
        remove reaction in a conversation or chatroom of a user
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_poll(self, request_body):
        """add options to existing poll conversation"""

        raise NotImplementedError

    @abc.abstractmethod
    def submit_poll(self, request_body):
        """add votes on poll conversation"""

        raise NotImplementedError

    @abc.abstractmethod
    def poll_users(self, poll_id, page_no, page_size):
        """returns the  users who voted on a poll"""

        raise NotImplementedError

    @abc.abstractmethod
    def set_chatroom_topic(self) -> dict:
        """sets a conversation as chatroom topic"""

        raise NotImplementedError

    @abc.abstractmethod
    def attend_event(self, req_body):
        """set member as event attendee"""

        raise NotImplementedError

    @abc.abstractmethod
    def set_event_attended(self, req_body):

        """set the micro event attended by user"""

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
    def fetch_user_all_events(self, page, attending_status, past_events) -> dict:
        """
        fetch attending events of user
        """
        raise NotImplementedError
