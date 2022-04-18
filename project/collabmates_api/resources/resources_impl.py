from django.conf import settings

from togther.models import ModelUtilities, Community, User, Members
from collabmates_api.rest_api import get_error_context

from .models import *
from .constants import *
from .serializers import *
from .resources_manager import ResourceManager

from external_services.logging.logging_wrapper import LoggingWrapper
error_logger = LoggingWrapper.get_instance()


class ResourcesImpl(ResourceManager):
    """Business logic for Resources"""

    @staticmethod
    def update_resource_settings(req_body, member_id):
        """updating resource settings"""

        community_id = req_body.get('community_id')

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return get_error_context(False, "Invalid community_id")

        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not user_instance:
            return get_error_context(False, "Invalid member_id")

        is_cm = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_cm:
            return get_error_context(False, "You are not CM/Owner of this community")

        resource_settings_instance = ModelUtilities.get_model_filter(
            ResourceSettings,
            {
                'community_id': community_instance
            }
        )

        serializer = ResourceSettingsSerializer(resource_settings_instance[0], req_body, partial=True)

        if serializer.is_valid():
            serializer.save()

            res = {
                'success': True,
                'resource_settings': serializer.data
            }

            return res

        res = {
            'success': False,
            'error_message': serializer.errors,
        }

        return res

    @staticmethod
    def fetch_resource_settings(req_body, member_id):
        """updating resource settings"""

        community_id = req_body.get('community_id')

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return get_error_context(False, "Invalid community_id")

        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not user_instance:
            return get_error_context(False, "Invalid member_id")

        is_cm = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_cm:
            return get_error_context(False, "You are not CM/Owner of this community")

        resource_settings_instance = ModelUtilities.get_model_filter(
            ResourceSettings,
            {
                'community_id': community_instance
            }
        )

        serializer = ResourceSettingsSerializer(resource_settings_instance[0])

        res = {
            'success': True,
            'resource_settings': serializer.data
        }

        return res
