from rest_framework import status as status_codes

from ..external_service_apis.external_service_apis_manager import ExternalServiceApisManager
from external_services.email.email_wrapper import MailWrapper
from external_services.wa_notification.wa_notification_impl import NotificationImpl
from collabmates_api.member_community.member_community_impl import MemberCommunityImpl

from ..notification import notification_meta, get_token_for_fcm
from ..notifications.tasks_impl import TasksHelper
from utility.response_utilities import ResponseUtilities
from collabmates_api.sdk.models import (SdkClient)


class ExternalServiceApisImpl(ExternalServiceApisManager):

    def __init__(self, user_id, device_id: str = None, request_platform: str = None, version_code: int = 0,
                 api_key: str = None):
        self.user_id = user_id
        self.device_id = device_id
        self.request_platform = request_platform
        self.version_code = version_code
        self.api_key = api_key

    def get_member_id(self) -> str:
        return self.user_id

    def get_device_id(self) -> (str, None):
        return self.device_id

    def get_request_platform(self) -> (str, None):
        return self.request_platform

    def get_version_code(self) -> (int, None):
        return self.version_code

    def get_api_key(self) -> (str, None):
        return self.api_key

    def set_member_id(self, user_id) -> None:
        self.user_id = user_id

    def set_device_id(self, device_id) -> None:
        self.device_id = device_id

    def set_request_platform(self, request_platform) -> None:
        self.request_platform = request_platform

    def set_version_code(self, version_code) -> None:
        self.version_code = version_code

    def set_api_key(self, api_key) -> None:
        self.api_key = api_key

    def _validate_email_body_params(self, req_body):

        if not req_body.get('subject'):
            return {'error_message': 'send subject'}

        if not req_body.get('mail_body'):
            return {'error_message': 'send mail_body'}

        if not req_body.get('mail_recipient_list'):
            return {'error_message': 'send mail_recipient_list'}

        return req_body

    def _validate_wa_body_params(self, req_body):

        if not req_body.get('receivers_list'):
            return {'error_message': 'send receivers_list'}

        if not req_body.get('template_name'):
            return {'error_message': 'send template_name'}

        if not req_body.get('broadcast_name'):
            return {'error_message': 'send broadcast_name'}

        return req_body

    def _validate_notifications_body_params(self, req_body, api_key):

        if not req_body.get('member_ids'):
            return {'error_message': 'send member_ids'}

        if not isinstance(req_body.get('member_ids'), list):
            return {'error_message': 'send member_ids in list'}

        if not req_body.get('message_payload'):
            return {'error_message': 'send payload'}

        if not req_body.get('community_id') and not api_key:
            return {'error_message': 'send community_id/x-api-key'}

        return req_body

    def send_email(self, req_body) -> dict:

        validated_mail_req = self._validate_email_body_params(req_body)

        if validated_mail_req.get('error_message'):
            return {'success': False, 'error_message': validated_mail_req.get('error_message')}

        is_mail_sent = MailWrapper.send_email.delay(subject=req_body.get('subject'), template=req_body.get('mail_body'),
                                                    to_mails_list=req_body.get('mail_recipient_list'),
                                                    from_email=req_body.get('from_email'),
                                                    categories=req_body.get('categories'),
                                                    reply_to=req_body.get('reply_to'))

        if not is_mail_sent:
            return {'success': False, 'error_message': 'Error in sending mail.'}

        return {'success': True}

    def send_wa_message(self, req_body) -> dict:

        validated_wa_req_body = self._validate_wa_body_params(req_body)

        if validated_wa_req_body.get('error_message'):
            return {'success': False, 'error_message': validated_wa_req_body.get('error_message')}

        updated_user_data = TasksHelper.update_wa_subscription_user_data(req_body.get('receivers_list'),
                                                                         req_body.get('template_name'),
                                                                         req_body.get('broadcast_name'))

        for user_data in updated_user_data:
            NotificationImpl.send_bulk_wa_notification.delay(receivers_list=user_data["user_data_list"],
                                                             template_name=user_data["template_name"],
                                                             broadcast_name=user_data["broadcast_name"])

        return {'success': True}

    def send_notifications(self, req_body) -> dict:

        validated_notification_req_body = self._validate_notifications_body_params(req_body, self.get_api_key())

        if validated_notification_req_body.get('error_message'):
            return {'success': False, 'error_message': validated_notification_req_body.get('error_message')}

        member_ids_list = req_body.get('member_ids')
        message_payload = req_body.get('message_payload')
        notification_category = req_body.get('category', {})
        community_id = req_body.get('community_id', None)

        if self.get_api_key():
            community_instance = SdkClient.get_community_instance_or_none(community_id=community_id,
                                                                          api_key=self.get_api_key())

            if not community_instance:
                return ResponseUtilities.get_impl_error_context("Invalid API key/community ID",
                                                                status_code=status_codes.HTTP_400_BAD_REQUEST)

            community_id = community_instance.id

        notification_details_list = []
        member_ids_list = MemberCommunityImpl.get_valid_member_ids(member_ids_list)

        for member_id in member_ids_list:
            notification_details = get_token_for_fcm(member_id, True)

            notification_details_list.append({
                'id': member_id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1]
            })

        message = {
            'payload': message_payload,
        }

        if notification_category:
            message['category'] = notification_category

        if community_id:
            message = TasksHelper.add_community_info_to_notification_payload(message, community_id)

        notification_meta(notification_details_list, message)

        return {'success': True}
