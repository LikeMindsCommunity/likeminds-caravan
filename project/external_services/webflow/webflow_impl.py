from utility.api_client import ApiClient
from .constants import WEBFLOW_HOST, WEBFLOW_CREATE_EVENT_PATH, WEBFLOW_UPDATE_EVENT_PATH
from .webflow_manager import WebflowManager
from external_services.logging.logging_wrapper import LoggingWrapper
from django.conf import settings

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class WebflowImpl(WebflowManager):

    @staticmethod
    def create_event_in_webflow(event_meta) -> dict:
        client = ApiClient(host=WEBFLOW_HOST,
                           method='post',
                           path=WEBFLOW_CREATE_EVENT_PATH % settings.WEBFLOW_KEYS.get('collection_id'))

        client.add_header('Authorization', 'Bearer %s' % settings.WEBFLOW_KEYS.get('api_key'))
        client.add_header('accept-version', '1.0.0')
        client.update_body(event_meta)
        client.post()

        return client.fetch_response()

    @staticmethod
    def update_event_in_webflow(event_meta, item_id):
        if not item_id:
            return

        client = ApiClient(host=WEBFLOW_HOST,
                           method='patch',
                           path=WEBFLOW_UPDATE_EVENT_PATH % (settings.WEBFLOW_KEYS.get('collection_id'), item_id))

        client.add_header('Authorization', 'Bearer %s' % settings.WEBFLOW_KEYS.get('api_key'))
        client.add_header('accept-version', '1.0.0')
        client.update_body(event_meta)
        client.patch()

        return client.fetch_response()

