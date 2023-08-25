from .segment_manager import SegmentManager
from external_services.logging.logging_wrapper import LoggingWrapper
from django.conf import settings
from togther.models import (ModelUtilities)
from collabmates_api.sdk.models import (SdkClient)
from utility.constants import (COMMUNITY_HOOD_ID)

import analytics

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()

analytics.write_key = settings.SEGMENT_KEY


class SegmentImpl(SegmentManager):

    @staticmethod
    def track_event(user_id, event_name, event_data) -> None:

        community_id = event_data.get('community_id')

        community_instance = ModelUtilities.get_model_filter(SdkClient, {'community': community_id}).first()

        if community_instance and community_instance.community_id != COMMUNITY_HOOD_ID:
            return

        try:
            analytics.track(user_id, event_name, event_data)

        except Exception as e:
            error_logger.error(e)
