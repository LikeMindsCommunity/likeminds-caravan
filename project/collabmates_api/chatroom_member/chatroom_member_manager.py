import abc


class ChatroomMemberManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'process_chatroom_list') and callable(subclass.process_chatroom_list)) and
                (hasattr(subclass, 'process_event_chatroom_list') and callable(subclass.process_event_chatroom_list)
                or NotImplemented))

    @abc.abstractmethod
    def process_chatroom_list(self, chatroom_list, community_instance) -> []:
        """
        processes the list of chatroom
        """
        raise NotImplementedError

    @abc.abstractmethod
    def process_event_chatroom_list(self, chatroom_list) -> []:
        """
        processes the list of event chatroom
        """
        raise NotImplementedError
