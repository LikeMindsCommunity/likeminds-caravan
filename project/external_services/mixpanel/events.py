from django.conf import settings
from celery import shared_task

from togther.models import Community
from collabmates_api.static_text import (SEGMENT_EVENT_MEMBER_APPROVED,
                                         SEGMENT_EVENT_LEAVE_COMMUNITY,
                                         SEGMENT_EVENT_MEMBER_REJECTED)
from external_services.segment.segment_impl import SegmentImpl

from collabmates_api.user.constants import SUBSCRIPTION_FETCH_API_PATH

from utility.api_client import ApiClient
from utility.states import SubscriptionStatus

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


subscription_url = settings.SUBSCRIPTION_SERVER_URL


class MixpanelEvents:

    @staticmethod
    @shared_task
    def leave_community(user_id, community_id, reason=""):

        community_instance = Community.get_community_or_None(community_id)

        if community_instance is None:
            return

        community_name = community_instance.name

        subscription_status = MixpanelEventHelper.fetch_user_subscription_status_in_community(user_id, community_id)

        properties = MixpanelEventHelper.prepare_properties(community_id=community_id, community_name=community_name,
                                                            subscription_status=subscription_status, reason=reason)

        SegmentImpl.track_event(str(user_id),
                                event_name=SEGMENT_EVENT_LEAVE_COMMUNITY,
                                event_data=properties)

    @staticmethod
    @shared_task
    def member_approved_by_cm(user_id, approved_by_id, community_id):

        community_instance = Community.get_community_or_None(community_id)

        if community_instance is None:
            return

        community_name = community_instance.name

        properties = MixpanelEventHelper.prepare_properties(community_id=community_id, community_name=community_name,
                                                            approved_by_id=approved_by_id)

        SegmentImpl.track_event(str(user_id),
                                event_name=SEGMENT_EVENT_MEMBER_APPROVED,
                                event_data=properties)

    @staticmethod
    @shared_task
    def member_rejected_by_cm(user_id, rejected_by_id, community_id):

        community_instance = Community.get_community_or_None(community_id)

        if community_instance is None:
            return

        community_name = community_instance.name

        properties = MixpanelEventHelper.prepare_properties(community_id=community_id, community_name=community_name,
                                                            rejected_by_id=rejected_by_id)

        SegmentImpl.track_event(str(user_id),
                                event_name=SEGMENT_EVENT_MEMBER_REJECTED,
                                event_data=properties)


class MixpanelEventHelper:

    @staticmethod
    def prepare_properties(**kwargs):
        return kwargs

    @staticmethod
    def fetch_user_subscription_status_in_community(user_id, community_id):
        client = ApiClient(host=subscription_url,
                           method='get',
                           path=SUBSCRIPTION_FETCH_API_PATH)

        client.add_header('x-member-id', user_id)
        client.add_url_param('community_id', community_id)
        client.request()

        response = client.fetch_response()

        if response.get('success'):
            subscriptions = response.get("subscriptions", None)

            if subscriptions:
                membership_state = subscriptions[0].get('membership_state', 1)

                try:
                    return SubscriptionStatus(membership_state).fetch_name()
                except ValueError as e:
                    error_logger.error(f"enum value does not exist - {e}")

        return SubscriptionStatus.SUBSCRIPTION_NOT_FOUND.fetch_name()
