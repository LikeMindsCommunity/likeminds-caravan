import json

from togther.models import (ModelUtilities, Community, Members, Userinfo, Report)
from utility.response_utilities import ResponseUtilities
from utility.states import ReportClosingStatus, report_action_types
from cms.cms_auth_utilities import CMSAuthUtilities
from collabmates_api.sdk.models import (SdkClient)
from collabmates_api.community.constants import (SWARM_DELETE_CACHE_ENDPOINT, INFERDO_NSFW_FILTER_ENDPOINT, 
                                                 INFERDO_HEADER_API_HOST, INFERDO_SAMPLE_NSFW_IMAGE_URL,
                                                 SWARM_PENDING_POST_UPDATE_ENDPOINT)
from celery import shared_task
from django.conf import settings

from utility.api_client import ApiClient

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()

class CommunityViewHelper:

    @staticmethod
    def validate_fetch_members_meta_request(user_id, community_id, member_ids, api_key=None):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key/community ID")

        member_ids_list = []
        if isinstance(member_ids, str):
            try:
                member_ids_list = json.loads(member_ids)
            except:
                return ResponseUtilities.get_inner_error_context("Invalid member_ids object")

        return {'user_instance': user_instance, 'community_instance': community_instance,
                'member_ids': member_ids_list}

    @staticmethod
    def validate_edit_community_request(req_body, community_id, member_id, username, password):

        if not req_body:
            return ResponseUtilities.get_inner_error_context('In-valid request body')

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("In-valid community id")

        if member_id:

            user_instance = ModelUtilities.get_user_instance_or_none(member_id)

            if not user_instance:
                return ResponseUtilities.get_inner_error_context("In-valid member id")

        else:

            if not CMSAuthUtilities.validate_user(username, password):
                return ResponseUtilities.get_inner_error_context("In-valid username and password")

            members_filter = ModelUtilities.get_model_filter(Members,
                                                             {"community_id": community_instance,
                                                              "is_owner": True})

            if not members_filter:
                return ResponseUtilities.get_inner_error_context("Unable to find owner")

            user_instance = members_filter[0].member_id

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_add_community_member_request(user_id, api_key, req_body):

        if not req_body:
            return ResponseUtilities.get_inner_error_context("Invalid request body")

        if not req_body.get('user_name'):
            return ResponseUtilities.get_inner_error_context("Empty user name!")

        user_body = {
            "name": req_body.get('user_name')
        }

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        is_admin = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_admin:
            return ResponseUtilities.get_inner_error_context("Invalid credentials")

        if req_body.get('user_unique_id'):
            user_body['user_unique_id'] = req_body.get('user_unique_id')

        if req_body.get('uuid'):
            user_body['user_unique_id'] = req_body.get('uuid')

        if req_body.get('image_url'):
            user_body['image_url'] = req_body.get('image_url')

        return {'user_instance': user_instance, 'community_instance': community_instance,
                'user_body': user_body}

    @staticmethod
    def validate_update_community_member_request(user_id, api_key, req_body):

        if not req_body:
            return ResponseUtilities.get_inner_error_context("Invalid request body")

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user id")

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        is_admin = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_admin:
            return ResponseUtilities.get_inner_error_context("Invalid credentials")
        
        user_unique_id = req_body.get('user_unique_id')
        uuid = req_body.get('uuid')

        if uuid:
            valid_id = ModelUtilities.get_valid_user_ids_from_uuids([uuid], community_instance.id)

            if not valid_id:
                return ResponseUtilities.get_inner_error_context("Invalid uuid")
            
            user_unique_id = valid_id[0]

        member_instance = ModelUtilities.get_user_instance_or_none(user_unique_id)

        if not member_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user_unique_id")

        is_community_member = Members.is_community_member(community_instance, member_instance)

        if not is_community_member:
            return ResponseUtilities.get_inner_error_context("User not part of community")

        return {'user_instance': user_instance, 'community_instance': community_instance,
                'member_instance': member_instance}
    
    @staticmethod
    @shared_task
    def delete_cache_from_swarm_service(community_id: int, user_id: int, cache_key: str):
        if not cache_key:
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
            client.update_body({
                "cache_key": cache_key
            })

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
    def validate_inferdo_api_key_for_nsfw_filtering(api_key:str, community_instance, user_instance) -> dict:
        
        if not (api_key and community_instance and user_instance):
            return ResponseUtilities.get_inner_error_context("Invalid request body")
        
        try:    

            client = ApiClient()
            client.update_request_url(INFERDO_NSFW_FILTER_ENDPOINT)

            # Add headers
            client.update_headers({
                'X-RapidAPI-Key': api_key,
                'x-RapidAPI-Host': INFERDO_HEADER_API_HOST
            })

            # Add request body
            client.update_body({
                "url": INFERDO_SAMPLE_NSFW_IMAGE_URL
            })

            # Send POST request
            response = client.post().response

            if response.status_code != 200:
                error_logger.error(f"Error occured setting up Inferdo's API Key for community - {community_instance.id} \
                                   -  {community_instance.name} | StatusCode: {response.status_code} , Response: {response.json()}")
                return ResponseUtilities.get_inner_error_context(f"Error occured setting up Inferdo's API Key: {response.json()}")

            return {'success': True}
        
        except Exception as e:
            error_logger.error(f"Exception occurred while setting up Inferdo's API Key for community - {community_instance.id} -  {community_instance.name} | Error: {e.args}")
            return ResponseUtilities.get_inner_error_context(f"Some error occured setting up Inferdo's API Key, please contact support")

    @shared_task    
    @staticmethod
    def close_under_review_pending_post_reports(community_id: int, user_id: int, report_ids: list, status: str):

        if not ReportClosingStatus.is_valid_status(status):
            return
        
        action_taken = report_action_types.PENDING_POST_APPROVED if status == ReportClosingStatus.APPROVED else report_action_types.PENDING_POST_REJECTED
        community_instance = ModelUtilities.get_model_instance_or_none(SdkClient, community_id)
        user_instance = ModelUtilities.get_model_instance_or_none(Userinfo, user_id)
        report_instances = ModelUtilities.get_model_filter(Report, {'id__in': report_ids})

        if not (community_instance and user_instance and report_instances):
            return
        
        # For each report, approve or reject the pending post in swarm service and close the report
        for report in report_instances:

            pending_post_id = report.entity_id
            response = CommunityViewHelper.approve_or_reject_pending_post_in_swarm_service(community_instance.api_key, 
                                                                                           user_instance.user_unique_id,
                                                                                           pending_post_id, 
                                                                                           status)
            
            # If there was an error from swarm service log the error and continue
            if response.get('error_message'):
                error_logger.error(f"Error occurred while approving/rejecting pending post: {pending_post_id} for report: {report.id} - {response.get('error_message')}")
                continue
            
            # Close the report if the pending post was approved or rejected successfully
            report.is_closed = True
            report.closed_by = user_instance.user_id
            report.action_taken = action_taken
            report.save()

            info_logger.info(f"Successfully approved {pending_post_id} pending post for report: {report.id}")

        return
        
    @staticmethod
    def approve_or_reject_pending_post_in_swarm_service(api_key: str, user_id: str, pending_post_id: str, 
                                                        status: str) -> dict:
        
        try:

            if not (api_key and user_id and pending_post_id and status):
                return ResponseUtilities.get_inner_error_context("Invalid request body")

            pending_post_update_endpoint = settings.SWARM_BASE_URL + SWARM_PENDING_POST_UPDATE_ENDPOINT.format(pending_post_id)

            client = ApiClient()
            client.update_request_url(pending_post_update_endpoint)

            # Add headers
            client.update_headers({
                'x-member-id': user_id,
                'x-api-key': api_key
            })

            # Add Delete request body
            client.update_body({
                "status": status
            })

            # Send delete request
            response = client.patch().response

            if response.status_code != 200:
                error_response = response.json()
                return {'error_message': error_response}

            return {'success': True}
        
        except Exception as e:
            return {'error_message': f"Exception occurred while approving/rejecting pending post in swarm - {e.args}"}
