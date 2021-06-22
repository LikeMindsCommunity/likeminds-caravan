import abc


class WAApiManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'send_broadcast') and
                callable(subclass.send_broadcast)
                or
                NotImplemented)

    @staticmethod
    def call_wa_broadcast_api(phone, template_name, broadcast_name, parameters) -> bool:
        """
        sends a whatsapp message on the phone number
        phone -> phone with country code
        teamplte_name -> teamplte_name from wa dashboard
        broadcast_name -> sets the name identifier of the broadcast sent
        """

        raise NotImplementedError
