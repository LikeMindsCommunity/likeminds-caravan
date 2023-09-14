from rest_framework import status as status_codes

from utility.response_utilities import ResponseUtilities
from utility.validation_utilities import ValidationUtilities

from .constants import WEBHOOK_LIMIT

from togther.models import ModelUtilities, Members
from .models import CommunityWebhook



class WebhookImplHelper:

    @staticmethod
    def validate_add_webhook_request(api_key: str, user_id: str, webhook_url: str, webhook_type: str,
                                     is_active) -> dict:
        
        if not isinstance(is_active, bool):
            return ResponseUtilities.get_inner_error_context('send is_active in body as boolean')
        
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instace = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        is_admin = Members.is_member_community_promoter(community_instace, user_instance)

        if not is_admin:
            return ResponseUtilities.get_inner_error_context('You are not the owner/CM of community')

        webhook_instances = ModelUtilities.get_model_filter(
            CommunityWebhook, {'community_id': community_instace.id, 'webhook_type': webhook_type})

        if len(webhook_instances) >= WEBHOOK_LIMIT:
            return ResponseUtilities.get_inner_error_context('You can only create 5 webhooks of same type')

        same_webhook_instances = webhook_instances.filter(url=webhook_url)

        if len(same_webhook_instances) > 0:
            return ResponseUtilities.get_inner_error_context('Webhook exist with given details')
        
        return {
            'community_instance': community_instace,
            'user_instance': user_instance,
            'webhook_type': webhook_type,
            'webhook_url': webhook_url,
        }
    
    @staticmethod
    def validate_fetch_webhooks_request(api_key: str, user_id: str) -> dict:

        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instace = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        is_admin = Members.is_member_community_promoter(community_instace, user_instance)

        if not is_admin:
            return ResponseUtilities.get_inner_error_context('You are not the owner/CM of community')

        return {
            'community_instance': community_instace,
            'user_instance': user_instance,
        }
    
    @staticmethod
    def validate_fetch_webhook_request(api_key: str, user_id: str, webhook_id: str) -> dict:

        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instace = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        is_admin = Members.is_member_community_promoter(community_instace, user_instance)

        if not is_admin:
            return ResponseUtilities.get_inner_error_context('You are not the owner/CM of community')

        webhook_instance = ModelUtilities.get_model_filter(CommunityWebhook, 
                                                           {'id': webhook_id,
                                                            'community_id': community_instace.id}
                                                            ).first()

        if not webhook_instance:
            return ResponseUtilities.get_inner_error_context('Invalid webhook id')

        return {
            'community_instance': community_instace,
            'user_instance': user_instance,
            'webhook_instance': webhook_instance,
        }
    
    @staticmethod
    def validate_update_webhook_request(api_key: str, user_id: str, webhook_id: str) -> dict:
        
        validation_params = {
            'community_id': {
                'api_key': api_key
            },
            'user_id': user_id,
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        community_instace = validated_dict.get('community_id')
        user_instance = validated_dict.get('user_id')

        is_admin = Members.is_member_community_promoter(community_instace, user_instance)

        if not is_admin:
            return ResponseUtilities.get_inner_error_context('You are not the owner/CM of community')
        
        webhook_instance = ModelUtilities.get_model_filter(CommunityWebhook,
                                                           {'id': webhook_id,
                                                            'community_id': community_instace.id}
                                                            ).first()
        
        if not webhook_instance:
            return ResponseUtilities.get_inner_error_context('Invalid webhook id')
        
        return {
            'community_instance': community_instace,
            'user_instance': user_instance,
            'webhook_instance': webhook_instance
        }
    
    @staticmethod
    def validate_delete_webhook_request(api_key: str, user_id: str, webhook_id: str) -> dict:
            
            validation_params = {
                'community_id': {
                    'api_key': api_key
                },
                'user_id': user_id,
            }
    
            validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)
    
            if validated_dict.get('error_message'):
                return validated_dict
            
            community_instace = validated_dict.get('community_id')
            user_instance = validated_dict.get('user_id')
    
            is_admin = Members.is_member_community_promoter(community_instace, user_instance)
    
            if not is_admin:
                return ResponseUtilities.get_inner_error_context('You are not the owner/CM of community')
            
            webhook_instance = ModelUtilities.get_model_filter(CommunityWebhook,
                                                               {'id': webhook_id,
                                                                'community_id': community_instace.id}
                                                                ).first()
            
            if not webhook_instance:
                return ResponseUtilities.get_inner_error_context('Invalid webhook id')
            
            return {
                'community_instance': community_instace,
                'user_instance': user_instance,
                'webhook_instance': webhook_instance
            }
