from celery import shared_task
from django.conf import settings

from togther.models import (ModelUtilities, Userinfo)
from collabmates_api.sdk.models import (SdkClient)

from utility.constants import (SWARM_DELETE_CACHE_ENDPOINT, KETTLE_DELETE_CACHE_ENDPOINT, PLATFORM_TYPE_CARAVAN_SERVICE,
                               SWARM_USER_FEED_DATA_REMOVAL_ENDPOINT, SWARM_PENDING_POST_UPDATE_ENDPOINT,
                               SWARM_WIDGET_ENDPOINT, SWARM_LM_WIDGET_ENDPOINT)
from utility.api_client import ApiClient
from utility.response_utilities import ResponseUtilities

from external_services.logging.logging_wrapper import LoggingWrapper

info_logger = LoggingWrapper.get_instance()
error_logger = LoggingWrapper.get_instance()


class InternalServiceUtilities:

    @staticmethod
    @shared_task
    def delete_cache_from_swarm_service(community_id: int, user_id: int, cache_key: str = None, key_pattern: str = None):

        if not (cache_key or key_pattern):
            return
        
        try:    
            user_info_filter = ModelUtilities.get_model_filter(Userinfo, {'user_id': user_id}).first()
            sdk_client_instance = ModelUtilities.get_model_filter(SdkClient, {'community_id': community_id}).first()

            if not (user_info_filter and sdk_client_instance):
                return

            cache_removal_endpoint = settings.SWARM_BASE_URL + SWARM_DELETE_CACHE_ENDPOINT

            client = ApiClient()
            client.update_request_url(cache_removal_endpoint)

            # Add headers
            client.update_headers({
                'x-member-id': user_info_filter.user_unique_id,
                'x-api-key': sdk_client_instance.api_key
            })

            # Add Delete request body
            req_body = {}

            if cache_key:
                req_body["cache_key"] = cache_key

            if key_pattern:
                req_body["key_pattern"] = key_pattern

            if req_body:
                client.update_body(req_body)

            # Send delete request
            response = client.delete().response

            if response.status_code == 200:
                info_logger.info(f"Successfully deleted cache for community: {community_id} for key: {cache_key}")

            else:
                error_logger.error(f"Error deleting cache for community: {community_id} for key: {cache_key} - \
                                   status code: {response.status_code} | response: {response.json()}")

            return 
        
        except Exception as e:
            error_logger.error(f"Exception occurred while deleting cache from swarm - {e.args}")
            return
        
    @staticmethod
    @shared_task
    def delete_cache_from_kettle_service(community_id: int, user_id: int, key_patterns: list = None):

        if not key_patterns:
            return
        
        try:    
            user_info_filter = ModelUtilities.get_model_filter(Userinfo, {'user_id': user_id}).first()
            sdk_client_instance = ModelUtilities.get_model_filter(SdkClient, {'community_id': community_id}).first()

            if not (user_info_filter and sdk_client_instance):
                return

            cache_removal_endpoint = settings.KETTLE_BASE_URL + KETTLE_DELETE_CACHE_ENDPOINT

            client = ApiClient()
            client.update_request_url(cache_removal_endpoint)

            # Add headers
            client.update_headers({
                'x-member-id': user_info_filter.user_unique_id,
                'x-api-key': sdk_client_instance.api_key,
                'x-platform-type': PLATFORM_TYPE_CARAVAN_SERVICE
            })

            # Add Delete request body
            client.update_body({
                "key_patterns": key_patterns
            })

            # Send delete request
            response = client.delete().response

            if response.status_code == 200:
                info_logger.info(f"Successfully sent Kettle cache deletion for community: {community_id} for keys: {key_patterns}")

            else:
                error_logger.error(f"Error deleting Kettle cache for community: {community_id} for keys: {key_patterns} - \
                                   status code: {response.status_code} | response: {response.json()}")

            return 
        
        except Exception as e:
            error_logger.error(f"Exception occurred while deleting cache from kettle service - {e.args}")
            return
    
    @staticmethod
    @shared_task
    def remove_users_feed_data(community_id: int, user_id: int, lm_uuids: list, is_cm: bool):

        if not lm_uuids:
            return
        
        try:    
            user_info_filter = ModelUtilities.get_model_filter(Userinfo, {'user_id': user_id}).first()
            sdk_client_instance = ModelUtilities.get_model_filter(SdkClient, {'community_id': community_id}).first()

            if not (user_info_filter and sdk_client_instance):
                return

            user_feed_removal_endpoint = settings.SWARM_BASE_URL + SWARM_USER_FEED_DATA_REMOVAL_ENDPOINT

            client = ApiClient()
            client.update_request_url(user_feed_removal_endpoint)

            # Add headers
            client.update_headers({
                'x-member-id': user_info_filter.user_unique_id,
                'x-api-key': sdk_client_instance.api_key
            })

            # Add Delete request body
            client.update_body({
                "user_ids": lm_uuids,
                "user_is_cm": is_cm
            })

            # Send delete request
            response = client.delete().response

            if response.status_code == 200:
                info_logger.info(f"Successfully removed users feed data (if exists) for community: {community_id} for users: {lm_uuids}")

            else:
                error_logger.error(f"Failed to remove users feed data for community {community_id} for users: {lm_uuids} - status code: {response.status_code} | response: {response.json()}")

            return 
        
        except Exception as e:
            error_logger.error(f"Exception occurred while removing users feed data - {e.args}")
            return

    @staticmethod
    def approve_or_reject_pending_post_in_swarm_service(api_key: str, user_id: str, pending_post_id: str, 
                                                        status: str) -> dict:
        
        try:

            if not (api_key and user_id and pending_post_id and status):
                return {'error_message': "Please provide all required parameters"}

            pending_post_update_endpoint = settings.SWARM_BASE_URL + SWARM_PENDING_POST_UPDATE_ENDPOINT.format(pending_post_id)

            client = ApiClient()
            client.update_request_url(pending_post_update_endpoint)

            # Add headers
            client.update_headers({
                'x-member-id': user_id,
                'x-api-key': api_key
            })

            # Add request body
            client.update_body({
                "status": status
            })

            # Send patch request
            response = client.patch().response

            if response.status_code != 200:
                error_response = response.json()
                return {'error_message': error_response}

            return {'success': True}
        
        except Exception as e:
            return {'error_message': f"Exception occurred while approving/rejecting pending post in swarm - {e.args}"}

    @staticmethod
    def create_widget_in_swarm(user_unique_id: str, community_id: int, entity_id: str, entity_type: str,
                               metadata: dict, is_lm_widget: bool = False):

        if not (user_unique_id or community_id):
            return ResponseUtilities.get_inner_error_context("Invalid user or API key!")

        try:
            sdk_client_instance = ModelUtilities.get_model_filter(SdkClient, {'community_id': community_id,
                                                                              'is_deleted': False}).first()

            if not sdk_client_instance:
                return ResponseUtilities.get_inner_error_context("Invalid community ID!")

            api_key = sdk_client_instance.api_key

            swarm_create_widget_url = settings.SWARM_BASE_URL + SWARM_WIDGET_ENDPOINT

            if is_lm_widget:
                swarm_create_widget_url = settings.SWARM_BASE_URL + SWARM_LM_WIDGET_ENDPOINT

            client = ApiClient()
            client.update_request_url(swarm_create_widget_url)

            # Add headers
            client.update_headers({
                'x-member-id': user_unique_id,
                'x-api-key': api_key,
                'x-platform-type': PLATFORM_TYPE_CARAVAN_SERVICE
            })

            # Add Delete request body
            client.update_body({
                "parent_entity_id": entity_id,
                "parent_entity_type": entity_type,
                "metadata": metadata
            })

            # Send delete request
            response = client.post().response
            response_data = response.json()

            if response.status_code == 200:
                info_logger.info(f"Successfully created widget for community: {community_id} & "
                                 f"entity_id: {entity_id}, entity_type: {entity_type}")

                if response_data.get('widget'):
                    return response_data.get('widget')

                return ResponseUtilities.get_inner_error_context("No widget data created!")

            else:
                error_logger.error(f"API failed while creating widget for community: {community_id}, "
                                   f"entity_id: {entity_id}, entity_type: {entity_type}, metadata: {metadata}")

                return response_data

        except Exception as e:
            error_logger.error(f"Exception occurred while creating widget for community: {community_id}, "
                               f"entity_id: {entity_id}, entity_type: {entity_type}, metadata: {metadata}")
            return ResponseUtilities.get_inner_error_context("Some error occurred!")

    @staticmethod
    def get_widget_data_from_swarm(user_unique_id: str, community_id: int, entity_id: str, entity_type: str):

        if not (user_unique_id or community_id):
            return ResponseUtilities.get_inner_error_context("Invalid user or API key!")

        try:
            sdk_client_instance = ModelUtilities.get_model_filter(SdkClient, {'community_id': community_id,
                                                                              'is_deleted': False}).first()

            if not sdk_client_instance:
                return ResponseUtilities.get_inner_error_context("Invalid community ID!")

            api_key = sdk_client_instance.api_key

            swarm_get_widget_url = settings.SWARM_BASE_URL + SWARM_WIDGET_ENDPOINT

            client = ApiClient()

            # Add headers
            client.update_headers({
                'x-member-id': user_unique_id,
                'x-api-key': api_key,
                'x-platform-type': PLATFORM_TYPE_CARAVAN_SERVICE
            })

            # Add request params
            client.update_url_params({
                "parent_entity_id": entity_id,
                "parent_entity_type": entity_type
            })

            client.update_request_url(swarm_get_widget_url + client.get_url_params())

            # Send delete request
            response = client.get().response
            response_data = response.json()

            if response.status_code == 200:
                info_logger.info(f"Successfully fetched widget for community: {community_id} & "
                                 f"entity_id: {entity_id}, entity_type: {entity_type}")

                if response_data.get('widgets') and len(response_data.get('widgets')):
                    return response_data

                return ResponseUtilities.get_inner_error_context("No widgets data!")

            else:
                error_logger.error(f"API failed while fetching widget for community: {community_id}: "
                                   f"entity_id: {entity_id}, entity_type: {entity_type}")

                return response_data

        except Exception as e:
            error_logger.error(f"Exception occurred while fetching widget for community: {community_id},"
                               f"entity_id: {entity_id}, entity_type: {entity_type}")
            return ResponseUtilities.get_inner_error_context("Some error occurred!")

    @staticmethod
    def update_widget_in_swarm(user_unique_id: str, community_id: int, widget_id: str, metadata: dict,
                               is_lm_widget: bool = False):

        if not (user_unique_id or community_id):
            return ResponseUtilities.get_inner_error_context("Invalid user or API key!")

        try:
            sdk_client_instance = ModelUtilities.get_model_filter(SdkClient, {'community_id': community_id,
                                                                              'is_deleted': False}).first()

            if not sdk_client_instance:
                return ResponseUtilities.get_inner_error_context("Invalid community ID!")

            api_key = sdk_client_instance.api_key

            swarm_update_widget_url = settings.SWARM_BASE_URL + SWARM_WIDGET_ENDPOINT + f"/{widget_id}"

            if is_lm_widget:
                swarm_update_widget_url = settings.SWARM_BASE_URL + SWARM_LM_WIDGET_ENDPOINT + f"/{widget_id}"

            client = ApiClient()
            client.update_request_url(swarm_update_widget_url)

            # Add headers
            client.update_headers({
                'x-member-id': user_unique_id,
                'x-api-key': api_key,
                'x-platform-type': PLATFORM_TYPE_CARAVAN_SERVICE
            })

            # Add Delete request body
            client.update_body({
                "metadata": metadata
            })

            # Send delete request
            if is_lm_widget:
                response = client.patch().response

            else:
                response = client.put().response

            response_data = response.json()

            if response.status_code == 200:
                info_logger.info(f"Successfully updated widget for community: {community_id} & "
                                 f"widget_id: {widget_id}")

                if response_data.get('widget'):
                    return response_data.get('widget')

                return ResponseUtilities.get_inner_error_context("No widget data created!")

            else:
                error_logger.error(f"API failed while creating widget for community: {community_id}, widget_id: "
                                   f"{widget_id}, metadata: {metadata}")

                return response_data

        except Exception as e:
            error_logger.error(f"Exception occurred while creating widget for community: {community_id}, widget_id: "
                               f"{widget_id}, metadata: {metadata}")
            return ResponseUtilities.get_inner_error_context("Some error occurred!")
