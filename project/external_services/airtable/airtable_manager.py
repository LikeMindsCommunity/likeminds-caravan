import abc


class AirtableManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'send_data') and callable(subclass.send_data)) or
                NotImplemented)

    def send_data(self, data):
        """
        sends data to airtable endpoint
        """
        raise NotImplementedError
