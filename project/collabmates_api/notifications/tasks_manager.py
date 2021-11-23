import abc

class TaskManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'get_response_dict_for_whatsapp_comms') and 
                callable(subclass.get_response_dict_for_whatsapp_comms)) and
                (hasattr(subclass, 'calculate_time_for_sending_notification') and 
                callable(subclass.calculate_time_for_sending_notification))
                or NotImplemented)

    @abc.abstractmethod
    def get_response_dict_for_whatsapp_comms(self, payload):
        """
        getting response_dict for whatsapp notifications
        """
        raise NotImplementedError

    @abc.abstractmethod
    def calculate_time_for_sending_notification(self, event_instance):
        """
        calculate time for sending notification
        """
        raise NotImplementedError
