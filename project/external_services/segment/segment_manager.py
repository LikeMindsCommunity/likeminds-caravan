import abc


class SegmentManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'track_event') and
                callable(subclass.track_event) or
                NotImplemented)

    @staticmethod
    def track_event(user_id, event_name, event_data):
        """
        sends the event to segment
        """
        raise NotImplementedError
