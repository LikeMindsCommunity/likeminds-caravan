import abc


class InAppReviewManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (((hasattr(subclass, 'enable_review_popup') and callable(subclass.enable_review_popup)) and
                 (hasattr(subclass, 'shown_review_popup') and callable(subclass.shown_review_popup)) or
                 NotImplemented))

    @abc.abstractmethod
    def enable_review_popup(self, user_ids) -> dict:
        """
        To create Review Popup from a given user id list.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def shown_review_popup(self, member_id) -> dict:
        """
        To Mark Review Popup for an user as shown
        """
        raise NotImplementedError
