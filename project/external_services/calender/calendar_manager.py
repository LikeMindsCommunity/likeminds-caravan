import abc


class CalendarManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'call_calender_api') and
                callable(subclass.call_calender_api) or
                NotImplemented)

    @abc.abstractmethod
    def call_calender_api(self, payload: dict) -> None:
        """
        Make a call to calendar api to create and send invites
        """
        raise NotImplementedError
