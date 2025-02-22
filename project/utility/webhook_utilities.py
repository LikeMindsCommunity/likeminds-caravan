import uuid, hmac, hashlib, json

from django.conf import settings

from celery import shared_task
from celery.exceptions import Retry
from utility.api_client import ApiClient

from togther.models import (ModelUtilities)
from utility.time_utilities import (TimeUtilities)
from collabmates_api.sdk.models import (SdkClient)
from collabmates_api.webhook.models import (CommunityWebhook)
from collabmates_api.webhook.constants import (MAX_WEBHOOK_RETRY_LIMIT, WEBHOOK_FAILURE_MAIL_SUBJECT, 
                                               WEBHOOK_FAILURE_MAIL_BODY)

from external_services.logging.logging_wrapper import LoggingWrapper
from external_services.email.email_wrapper import MailWrapper


logger = LoggingWrapper.get_instance()

class WebhookUtilties:

    def create_hexdigest_from_payload(payload, secret:str) -> str:

        if not secret or not payload:
            return None
        
        message = json.dumps(payload)

        digest = hmac.new(
            key=bytes(secret, 'utf-8'),
            msg=bytes(message, 'utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        return digest
    
    @staticmethod
    def fetch_active_webhook_instance(url: str, webhook_type: str) -> CommunityWebhook:
        """
        Fetch webhook instance
        """

        webhook_instance = ModelUtilities.get_model_filter(CommunityWebhook, {
            'url': url,
            'webhook_type': webhook_type,
            'is_active': True
        }).first()

        return webhook_instance
    
    @staticmethod
    def create_api_client_with_payload_and_secret(url: str, payload: dict, secret: str = None) -> ApiClient:
        """
        Create api client instance with payload and secret
        """

        # If id is not present in payload, add a random UUID to it
        if not payload.get('id'):
            payload['id'] = str(uuid.uuid4())

        api_client = ApiClient()
        api_client.update_request_url(url)
        api_client.update_body(payload)

        if secret:
            signature = WebhookUtilties.create_hexdigest_from_payload(payload, secret)
            api_client.add_header('x-signature', signature)

        return api_client
    
    @staticmethod
    def set_webhook_as_inactive_and_send_mail(webhook_instance: CommunityWebhook, payload: dict,
                                              response_code: int, response_text: str):
        """
        Set webhook as inactive and send mail
        """

        # Set webhook as inactive
        webhook_instance.is_active = False
        webhook_instance.save()

        subject = WEBHOOK_FAILURE_MAIL_SUBJECT

        current_date_time = TimeUtilities.get_current_datetime_in_IST().strftime("%d-%m-%Y %H:%M")
        body = WEBHOOK_FAILURE_MAIL_BODY.format(webhook_instance.webhook_type, current_date_time,
                                                webhook_instance.url, current_date_time, response_code, response_text,
                                                json.dumps(payload, indent=4))
        
        # Fetch team emails from settings
        team_emails = settings.WEBHOOK_FAILURE_NOTIFICATION_TEAM_EMAILS

        # Send Mail to admin
        MailWrapper.send_email_with_custom_from_email(subject=subject, 
                                                      template=body, 
                                                      to_mails_list=team_emails)
        
    @shared_task(bind=True, retry_kwargs={'max_retries': MAX_WEBHOOK_RETRY_LIMIT + 1})
    def send_webhook_request_with_payload(self, url: str, payload: dict, webhook_type: str, secret: str = None):
        """
        Celery task to send webhook request with payload
        """

        try:

            # Check if webhook is active or not
            webhook_instance = WebhookUtilties.fetch_active_webhook_instance(url, webhook_type)

            if not webhook_instance:
                return
            
            # Create api client instance with payload and secret
            api_client = WebhookUtilties.create_api_client_with_payload_and_secret(url, payload, secret)

            # Send request
            api_client.post()

            response_code = api_client.response.status_code
            response_text = api_client.response.text

            if response_code == 200:
                logger.info(f"{payload['id']} | Webhook request successfully made for url: {url} | payload: {payload}")
            
            # If not successful
            else:
                logger.error(f"{payload['id']} | Webhook request failed for url: {url}, with status code: {response_code} and response: {api_client.response.text} | payload: {payload}")

                current_retries = self.request.retries

                # If current retries are less than max retries, retry the task with exponential countdown
                if current_retries < MAX_WEBHOOK_RETRY_LIMIT:

                    # Retry wity countdown 1 -> 60 -> 3600 seconds
                    countdown_secs = 60 ** current_retries

                    raise self.retry(countdown=countdown_secs)
                
                # If current retries are equal to max retries, set webhook as inactive and send mail
                else:

                    WebhookUtilties.set_webhook_as_inactive_and_send_mail(webhook_instance, payload, response_code, response_text)

                    logger.error(f"{payload['id']} | Webhook request failed and maximum retry limit reached - Webhook set as inactive and mail sent to admin | url: {url}, payload: {payload} and response: {response_text}")

        except Exception as e:

            # If RETRY exception, raise and retry, else log the error and exit
            if isinstance(e, Retry):
                raise e
        
            logger.error(f"{payload['id']} | Webhook request failed with unhandled exception: {e.args}, url: {url}, payload: {payload}")

    @staticmethod
    def validate_and_fetch_all_webhook_url_and_secret(community_id: int, webhook_type: str) -> list:

        if not (community_id and webhook_type):
            return {}

        webhook_instances = ModelUtilities.get_model_filter(CommunityWebhook, {
            'community_id': community_id,
            'webhook_type': webhook_type,
            'is_active': True
        })

        webhooks = []

        secret = ""

        # Use API Key as secret for SDK Communities
        sdk_client_instance = ModelUtilities.get_model_filter(SdkClient, {
            'community_id': community_id}).first()

        if sdk_client_instance:
            secret = sdk_client_instance.api_key

        for webhook_instance in webhook_instances:
            webhooks.append({
                'url': webhook_instance.url,
                'secret': secret
            })

        return webhooks
