import abc


class S3ClientManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'generate_presigned_post') and
                callable(subclass.generate_presigned_post) or
                NotImplemented)

    @abc.abstractmethod
    def generate_presigned_post(self, object_path: str, expiration: int) -> dict:
        """
        returns a pre-signed url for multimedia upload
        """
        raise NotImplementedError
