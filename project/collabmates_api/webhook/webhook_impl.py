from rest_framework import status as status_codes

from .webhook_manager import WebhookManager
from .constants import WEBHOOK_LIMIT
from .serializers import WebhookSerializer
from utility.response_utilities import ResponseUtilities
from utility.auth_utilities import AuthUtilities
from togther.models import ModelUtilities
from .models import CommunityWebhook

import json


class WebhookImpl(WebhookManager):

    member_id = None
    community_id = None
    webhook_type = None
    url = None
    webhook_id = None

    def __init__(self, member_id: str = None, community_id: str = None, webhook_type: int = None, url: str = None,
                 webhook_id: str = None):
        self.member_id = member_id
        self.community_id = community_id
        self.webhook_type = webhook_type
        self.url = url
        self.webhook_id = webhook_id

    def get_member_id(self) -> str:
        return self.member_id

    def get_community_id(self) -> str:
        return self.community_id

    def get_webhook_type(self) -> int:
        return self.webhook_type

    def get_url(self) -> str:
        return self.url

    def get_webhook_id(self) -> str:
        return self.webhook_id

    def fetch_webhooks(self) -> dict:

        authentication_response = AuthUtilities.is_cm(self.get_community_id(), self.get_member_id())

        if 'error_message' in authentication_response:
            return ResponseUtilities.get_impl_error_context(authentication_response['error_message'],
                                                            authentication_response['status'])

        webhook_instances = ModelUtilities.get_model_filter(CommunityWebhook, {'community_id': self.get_community_id()})

        webhook_data = WebhookSerializer(webhook_instances, many=True)

        return {'success': True, 'webhooks': webhook_data.data}

    @staticmethod
    def _create_webhook_instance(community_id, url, webhook_type) -> dict:

        webhook_data = {
            'community': community_id,
            'url': url,
            'webhook_type': webhook_type,
        }

        webhook_instance = WebhookSerializer(data=webhook_data)

        if webhook_instance.is_valid():
            webhook_instance.save()

            return {'webhook_instance': webhook_instance.data}

        return ResponseUtilities.get_impl_error_context(json.dumps(webhook_instance.errors),
                                                        status_codes.HTTP_400_BAD_REQUEST)

    def add_webhook(self) -> dict:

        authentication_response = AuthUtilities.is_cm(self.get_community_id(), self.get_member_id())

        if 'error_message' in authentication_response:
            return ResponseUtilities.get_impl_error_context(authentication_response['error_message'],
                                                            authentication_response['status'])

        webhook_instances = ModelUtilities.get_model_filter(
            CommunityWebhook, {'community_id': self.get_community_id(), 'webhook_type': self.get_webhook_type()})

        if len(webhook_instances) >= WEBHOOK_LIMIT:
            return ResponseUtilities.get_impl_error_context('You can only create 5 webhooks of same type',
                                                            status_codes.HTTP_403_FORBIDDEN)

        same_webhook_instances = webhook_instances.filter(url=self.get_url())

        if len(same_webhook_instances) > 0:
            return ResponseUtilities.get_impl_error_context('Webhook exist with given details',
                                                            status_codes.HTTP_403_FORBIDDEN)

        create_webhook = self._create_webhook_instance(self.get_community_id(),
                                                       self.get_url(),
                                                       self.get_webhook_type())

        if 'error_message' in create_webhook:
            return ResponseUtilities.get_impl_error_context(create_webhook['error_message'],
                                                            create_webhook['status'])

        webhook_instance_data = create_webhook['webhook_instance']

        return {'success': True, 'webhook': webhook_instance_data}

    def fetch_webhook(self) -> dict:

        webhook_instance = ModelUtilities.get_model_instance_or_none(CommunityWebhook, self.get_webhook_id())

        if not webhook_instance:
            return ResponseUtilities.get_impl_error_context('Invalid webhook_id', status_codes.HTTP_404_NOT_FOUND)

        authentication_response = AuthUtilities.is_cm(webhook_instance.community_id, self.get_member_id())

        if 'error_message' in authentication_response:
            return ResponseUtilities.get_impl_error_context(authentication_response['error_message'],
                                                            authentication_response['status'])

        webhook_data = WebhookSerializer(webhook_instance)

        return {'success': True, 'webhooks': webhook_data.data}

    def update_webhook(self) -> dict:

        webhook_instance = ModelUtilities.get_model_instance_or_none(CommunityWebhook, self.get_webhook_id())

        if not webhook_instance:
            return ResponseUtilities.get_impl_error_context("Invalid webhook details",
                                                            status_codes.HTTP_403_FORBIDDEN)

        authentication_response = AuthUtilities.is_cm(webhook_instance.community_id, self.get_member_id())

        if 'error_message' in authentication_response:
            return ResponseUtilities.get_impl_error_context(authentication_response['error_message'],
                                                            authentication_response['status'])

        webhook_instance.url = self.get_url()
        webhook_instance.save()

        webhook_instance_data = WebhookSerializer(webhook_instance).data

        return {'success': True, 'webhook': webhook_instance_data}

    def delete_webhook(self) -> dict:

        webhook_instance = ModelUtilities.get_model_instance_or_none(CommunityWebhook, self.get_webhook_id())

        if not webhook_instance:
            return ResponseUtilities.get_impl_error_context('Invalid webhook details', status_codes.HTTP_403_FORBIDDEN)

        authentication_response = AuthUtilities.is_cm(webhook_instance.community_id, self.get_member_id())

        if 'error_message' in authentication_response:
            return ResponseUtilities.get_impl_error_context(authentication_response['error_message'],
                                                            authentication_response['status'])

        webhook_instance.delete()

        return {'success': True}
