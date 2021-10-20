from external_services.logging.logging_wrapper import LoggingWrapper
from external_services.wa_notification.wa_notification_manager import NotificationManager
from external_services.wa_notification.wati_api_client import WAApiClient

from celery import shared_task

error_logger = LoggingWrapper.get_instance()


class NotificationImpl(NotificationManager):

    def _send_single_wa_notification(self, user_data, template_name, broadcast_name) -> None:
        WAApiClient.call_wa_broadcast_api(user_data, template_name, broadcast_name)

    @staticmethod
    @shared_task
    def send_bulk_wa_notification(receivers_list, template_name, broadcast_name) -> None:
        WAApiClient.call_wa_bulk_broadcast_api(receivers_list, template_name, broadcast_name)

    @classmethod
    def send_wa_notifications(self, user_data_for_wa_notification, template_name, broadcast_name) -> None:
        for user_data in user_data_for_wa_notification:
            self._send_single_wa_notification(self, user_data, template_name, broadcast_name)

    @classmethod
    def send_wa_bulk_notitfications(self, user_data_for_wa_notification, template_name, broadcast_name) -> None:
        NotificationImpl.send_bulk_wa_notification(user_data_for_wa_notification, template_name, broadcast_name)
