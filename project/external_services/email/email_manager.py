import abc


class MailManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'send_email') and callable(subclass.create_user)) or
                NotImplemented)

    @staticmethod
    def send_email(subject, template, to_mails_list, categories=None, reply_to=None):
        """
        sends email
        """
        raise NotImplementedError
