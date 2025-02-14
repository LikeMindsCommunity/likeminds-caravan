import json
from rest_framework import status as status_codes

from .webhook_manager import WebhookManager
from .serializers import WebhookSerializer
from .webhook_impl_helper import WebhookImplHelper
from .models import CommunityWebhook

from togther.models import ModelUtilities, Community
from collabmates_api.sdk.models import SdkClient 
from utility.response_utilities import ResponseUtilities
from utility.internal_service_utilities import InternalServiceUtilities
from utility.cache_keys import SWARM_CACHE_KEY_WEBHOOKS


class WebhookImpl(WebhookManager):

    api_key = None
    member_id = None
    community_id = None
    webhook_type = None
    url = None
    webhook_id = None

    def __init__(self, member_id: str = None, community_id: str = None, webhook_type: int = None, url: str = None,
                 webhook_id: str = None, api_key: str = None):
        self.member_id = member_id
        self.community_id = community_id
        self.webhook_type = webhook_type
        self.url = url
        self.webhook_id = webhook_id
        self.api_key = api_key

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
    
    def get_api_key(self) -> str:
        return self.api_key

    def fetch_webhooks(self) -> dict:

        validated_request = WebhookImplHelper.validate_fetch_webhooks_request(self.get_api_key(),
                                                                              self.get_member_id())

        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request['error_message'],
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        community_instance = validated_request.get('community_instance')

        webhook_instances = ModelUtilities.get_model_filter(CommunityWebhook, {'community_id': community_instance.id})

        webhook_data = WebhookSerializer(webhook_instances, many=True)

        return {'success': True, 'webhooks': webhook_data.data}

    @staticmethod
    def _create_webhook_instance(community_id, url, webhook_type, is_active) -> dict:

        webhook_data = {
            'community': community_id,
            'url': url,
            'webhook_type': webhook_type,
            'is_active': is_active
        }

        webhook_instance = WebhookSerializer(data=webhook_data)

        if webhook_instance.is_valid():
            webhook_instance.save()

            return {'webhook_instance': webhook_instance.data}

        return ResponseUtilities.get_impl_error_context(json.dumps(webhook_instance.errors),
                                                        status_codes.HTTP_400_BAD_REQUEST)

    def add_webhook(self, is_active) -> dict:
        validated_request = WebhookImplHelper.validate_add_webhook_request(self.get_api_key(),
                                                                           self.get_member_id(),
                                                                           self.get_url(),
                                                                           self.get_webhook_type(),
                                                                           is_active)
        
        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        webhook_url = validated_request.get('webhook_url')
        webhook_type = validated_request.get('webhook_type')

        create_webhook = self._create_webhook_instance(community_instance.id,
                                                       webhook_url,
                                                       webhook_type,
                                                       is_active)

        if 'error_message' in create_webhook:
            return ResponseUtilities.get_impl_error_context(create_webhook['error_message'],
                                                            create_webhook['status'])
        
        # Call swarm API to delete cache
        InternalServiceUtilities.delete_cache_from_swarm_service.delay(
            community_id=community_instance.id, user_id=self.get_member_id(), 
            cache_key=(SWARM_CACHE_KEY_WEBHOOKS % str(self.get_api_key())))

        webhook_instance_data = create_webhook['webhook_instance']

        return {'success': True, 'webhook': webhook_instance_data}

    @staticmethod
    def _create_or_update_webhook_instances(community: Community, url: str, webhook_statuses: dict) -> dict:
        webhook_filter = ModelUtilities.get_model_filter(CommunityWebhook,
                                                         {'community_id': community,
                                                          'url': url,
                                                          'webhook_type__in': webhook_statuses.keys()})

        new_webhook_types = list(set(webhook_statuses.keys()) - set(
            list(webhook_filter.values_list('webhook_type', flat=True))))

        # Update webhook instances
        update_webhook_instances_list = []

        for webhook_instance in webhook_filter:
            webhook_status = webhook_statuses.get(webhook_instance.webhook_type, None)

            if webhook_status is not None:
                webhook_instance.is_active = webhook_status
                update_webhook_instances_list.append(webhook_instance)

        ModelUtilities.bulk_update_instances(CommunityWebhook, update_webhook_instances_list, fields=['is_active'])

        # Create webhook instances
        create_webhook_instances_list = []

        for webhook_type in new_webhook_types:
            create_webhook_instances_list.append(CommunityWebhook(community=community,
                                                                  url=url,
                                                                  webhook_type=webhook_type))

        ModelUtilities.bulk_create_instances(CommunityWebhook, create_webhook_instances_list)

        return {'success': True}

    def add_or_update_webhook(self, webhook_statuses: dict):
        validated_request = WebhookImplHelper.validate_add_or_update_webhook_request(self.get_api_key(),
                                                                                     self.get_member_id(),
                                                                                     self.get_url(),
                                                                                     webhook_statuses)

        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')
        webhook_url = validated_request.get('webhook_url')

        response = self._create_or_update_webhook_instances(community_instance, webhook_url, webhook_statuses)

        # Call swarm API to delete cache
        InternalServiceUtilities.delete_cache_from_swarm_service.delay(
            community_id=community_instance.id, user_id=self.get_member_id(),
            cache_key=(SWARM_CACHE_KEY_WEBHOOKS % str(self.get_api_key())))

        return response

    def fetch_webhook(self) -> dict:

        validated_request = WebhookImplHelper.validate_fetch_webhook_request(self.get_api_key(),
                                                                             self.get_member_id(),
                                                                             self.get_webhook_id())
        
        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request['error_message'],
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
    
        webhook_instance = validated_request.get('webhook_instance')

        webhook_data = WebhookSerializer(webhook_instance)

        return {'success': True, 'webhooks': webhook_data.data}

    def update_webhook(self, webhook_url:str = None, is_active:bool = None) -> dict:

        validated_request = WebhookImplHelper.validate_update_webhook_request(self.get_api_key(),
                                                                              self.get_member_id(),
                                                                              self.get_webhook_id())
        
        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request['error_message'],
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        webhook_instance = validated_request.get('webhook_instance')

        if is_active is not None:
            webhook_instance.is_active = is_active

        if webhook_url is not None :
            webhook_instance.url = webhook_url

        webhook_instance.save()

        # Call swarm API to delete cache
        InternalServiceUtilities.delete_cache_from_swarm_service.delay(
            community_id=webhook_instance.community_id, user_id=self.get_member_id(), 
            cache_key=(SWARM_CACHE_KEY_WEBHOOKS % str(self.get_api_key())))

        webhook_instance_data = WebhookSerializer(webhook_instance).data

        return {'success': True, 'webhook': webhook_instance_data}

    def delete_webhook(self) -> dict:

        validated_request = WebhookImplHelper.validate_delete_webhook_request(self.get_api_key(),
                                                                              self.get_member_id(),
                                                                              self.get_webhook_id())
        
        if 'error_message' in validated_request:
            return ResponseUtilities.get_impl_error_context(validated_request['error_message'],
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)
        
        webhook_instance = validated_request.get('webhook_instance')
        
        webhook_instance.delete()

        # Call swarm API to delete cache
        InternalServiceUtilities.delete_cache_from_swarm_service.delay(
            community_id=webhook_instance.community_id, user_id=self.get_member_id(), 
            cache_key=(SWARM_CACHE_KEY_WEBHOOKS % str(self.get_api_key())))

        return {'success': True}
