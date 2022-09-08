from .mixpanel_manager import MixpanelManager
from django.conf import settings
from mixpanel import Mixpanel
from .constants import MIXPANEL_NOTIFICATION_TRACKING_EVENT_NAME
from togther.models import (ModelUtilities)
from collabmates_api.sdk.models import (SdkClient)
from external_services.logging.logging_wrapper import LoggingWrapper
error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class MixpanelImpl(MixpanelManager):
    mixpanel_instance = None

    def __init__(self):
        self._initialize_mixpanel()

    def _initialize_mixpanel(self):
        self.mixpanel_instance = Mixpanel(token=settings.MIXPANEL_TOKEN)

    def track_notification(self, distinct_id, properties) -> None:
        payload = properties.get('payload')

        if payload and isinstance(payload, dict):
            community_id = payload.get('community_id')

            community_instance = ModelUtilities.get_model_filter(SdkClient, {'community': community_id})

            if community_instance:
                return

        try:
            self.mixpanel_instance.track(distinct_id=distinct_id,
                                         event_name=MIXPANEL_NOTIFICATION_TRACKING_EVENT_NAME,
                                         properties=properties)
        except Exception as e:
            error_logger.error(e)

    def track_event(self, event_name, distinct_id, properties) -> None:
        try:
            self.mixpanel_instance.track(distinct_id=distinct_id,
                                         event_name=event_name,
                                         properties=properties)
        except Exception as e:
            error_logger.error(e)
