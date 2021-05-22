import abc


class OnboardingManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'fetch_pinned_chatrooms')
                and callable(subclass.fetch_pinned_chatrooms)) and \
               (hasattr(subclass, 'fetch_poll_chatrooms')
                and callable(subclass.fetch_poll_chatrooms)) and \
               (hasattr(subclass, 'fetch_event_chatrooms')
                and callable(subclass.fetch_event_chatrooms)) and \
               (hasattr(subclass, 'recent_n_days_conversation_chatrooms')
                and callable(subclass.recent_n_days_conversation_chatrooms)) and \
               (hasattr(subclass, 'n_percentage_member_conversation_chatrooms')
                and callable(subclass.n_percentage_member_conversation_chatrooms)) or NotImplemented

    @abc.abstractmethod
    def fetch_pinned_chatrooms(self, user_id, page_no, page_size) -> {}:
        """returns the latest pinned chatrooms for community onboarding"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_poll_chatrooms(self, user_id, page_no, page_size) -> {}:
        """returns the latest poll chatrooms with expiry greater than current time"""

        raise NotImplementedError

    @abc.abstractmethod
    def fetch_event_chatrooms(self, user_id, page_no, page_size) -> {}:
        """returns the latest event chatrooms with expiry greater than current time"""

        raise NotImplementedError

    @abc.abstractmethod
    def recent_n_days_conversation_chatrooms(self, user_id, page_no, page_size) -> {}:
        """send chatrooms in which last conversation created within the duration of n days"""

        raise NotImplementedError

    @abc.abstractmethod
    def n_percentage_member_conversation_chatrooms(self, user_id, page_no, page_size) -> {}:
        """send chatrooms in which n% of members have created conversation"""

        raise NotImplementedError


