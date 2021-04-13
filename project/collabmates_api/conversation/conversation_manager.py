import abc


class ConversationManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'fetch_conversation') and callable(subclass.fetch_conversation)) and
                (hasattr(subclass, 'create_conversation') and callable(subclass.create_conversation)) and
                (hasattr(subclass, 'add_poll') and callable(subclass.add_poll)) and
                (hasattr(subclass, 'submit_poll') and callable(subclass.submit_poll)) and
                (hasattr(subclass, 'poll_users') and callable(subclass.poll_users)) and
                (hasattr(subclass, 'add_reaction') and callable(subclass.add_reaction)) and
                (hasattr(subclass, 'remove_reaction') and callable(subclass.remove_reaction)) or
                NotImplemented)


    @abc.abstractmethod
    def fetch_conversation(self, top_navigate=False) -> None:
        """
        fetches the conversation from the database
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_conversation(self, req_body: dict, is_ios: bool,
                            is_user_guest: bool, has_files: bool, **kwargs) -> dict:
        """
        create conversation
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
