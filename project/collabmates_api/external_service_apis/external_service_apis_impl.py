from ..external_service_apis.external_service_apis_manager import ExternalServiceApisManager
from external_services.email.email_wrapper import MailWrapper
from external_services.wa_notification.wa_notification_impl import NotificationImpl


class ExternalServiceApisImpl(ExternalServiceApisManager):

    def __init__(self, user_id, device_id: str = None, request_platform: str = None, version_code: int = 0):
        self.user_id = user_id
        self.device_id = device_id
        self.request_platform = request_platform
        self.version_code = version_code

    def get_member_id(self) -> str:
        return self.user_id

    def get_device_id(self) -> (str, None):
        return self.device_id

    def get_request_platform(self) -> (str, None):
        return self.request_platform

    def get_version_code(self) -> (int, None):
        return self.version_code

    def set_member_id(self, user_id) -> None:
        self.user_id = user_id

    def set_device_id(self, device_id) -> None:
        self.device_id = device_id

    def set_request_platform(self, request_platform) -> None:
        self.request_platform = request_platform

    def set_version_code(self, version_code) -> None:
        self.version_code = version_code

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

        NotificationImpl.send_bulk_wa_notification.delay(receivers_list=req_body.get('receivers_list'),
                                                         template_name=req_body.get('template_name'),
                                                         broadcast_name=req_body.get('broadcast_name'))

        return {'success': True}
