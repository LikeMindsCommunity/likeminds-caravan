import abc


class FCMNotificationManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'get_access_token_for_auth') and
                callable(subclass.get_access_token_for_auth) and
                hasattr(subclass, 'update_payload') and
                callable(subclass.update_payload)
                or
                NotImplemented)

    @abc.abstractmethod
    def get_access_token_for_auth(self):
        '''
        gets access token for authentication in HTTP v1 FCM API.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def update_payload(self, payload):
        '''
        takes payload as argument and returns the updated payload according to HTTP v1 API
        '''
        raise NotImplementedError
