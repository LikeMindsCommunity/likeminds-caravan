import abc


class NotificationManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'send_wa_notifications') and
                callable(subclass.send_wa_notifications)
                or
                NotImplemented)

    @staticmethod
    def send_wa_notifications(user_data_for_wa_notification, template_name, broadcast_name) -> None:
        """
        sends a whatsapp message on the phone number
        phone -> phone with country code
        teamplte_name -> teamplte_name from wa dashboard
        broadcast_name -> sets the name identifier of the broadcast sent
        """
        raise NotImplementedError
