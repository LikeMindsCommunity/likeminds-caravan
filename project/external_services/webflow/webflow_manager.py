import abc


class WebflowManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'create_event_in_webflow') and
                callable(subclass.create_event_in_webflow) and
                (hasattr(subclass, 'update_event_in_webflow') and
                 callable(subclass.update_event_in_webflow)) and
                (hasattr(subclass, 'publish_event_in_webflow') and
                 callable(subclass.publish_event_in_webflow)) or
                NotImplemented)

    @staticmethod
    def create_event_in_webflow(req_body) -> dict:
        """
        create an event in webflow
        """
        raise NotImplementedError

    @staticmethod
    def update_event_in_webflow(req_body, item_id) -> dict:
        """
        update an event in webflow
        """
        raise NotImplementedError

    @staticmethod
    def publish_event_in_webflow(req_body, site_id) -> dict:
        """
        publish an event in webflow
        """
        raise NotImplementedError
