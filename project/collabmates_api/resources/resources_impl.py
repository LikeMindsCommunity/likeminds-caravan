from django.conf import settings
from uritemplate import partial

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
    member_id = None
    community_id = None

    def __init__(self, member_id=None, community_id=None):
        self.member_id = member_id
        self.community_id = community_id

    def get_member_id(self):
        return self.member_id

    def get_community_id(self):
        return self.community_id

    def update_resource_settings(self, req_body):
        """updating resource settings"""

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        community_instance = ModelUtilities.get_model_instance_or_none(
            Community,
            self.get_community_id()
        )

        resource_settings_instance = ModelUtilities.get_model_filter(
            ResourceSettings,
            {
                'community_id': community_instance
            }
        )

        serializer = ResourceSettingsSerializer(
            resource_settings_instance[0],
            req_body,
            partial=True)

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

    def fetch_resource_settings(self):
        """fetching resource settings"""

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        community_instance = ModelUtilities.get_model_instance_or_none(
            Community,
            self.get_community_id()
        )

        resource_settings_instance = ModelUtilities.get_model_filter(
            ResourceSettings,
            {
                'community_id': community_instance
            }
        )

        serializer = ResourceSettingsSerializer(
            resource_settings_instance[0]
        )

        res = {
            'success': True,
            'resource_settings': serializer.data
        }

        return res

    def create_resource_category(self, req_body):
        """
        to create resource category
        TODO:
            1. To Iterate and add each community cohort in
               ResourceCategoryPermission
            2. To add analytics
            3. To add references
        """
        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        serializer = ResourceCategorySerializer(data=req_body)

        if serializer.is_valid():

            level = ResourceHelper.fetch_level_for_resource_category_instance(
                req_body.get('parent_category_id')
            )

            serializer.save(level=level)

            res = {
                'success': True,
                'resource_category': serializer.data
            }

            return res

        res = {
            'success': False,
            'error_message': serializer.errors
        }

        return res

    def fetch_resource_category(self, page):
        """
        to fetch resource category
        TODO:
            1. To Update access_type in ResourceCategoryPermission
               before fetching
        """
        category_queryset = self.fetch_root_level_resource_category_objects()

        paginated_categories = ModelUtilities.paginate_queryset(
            category_queryset,
            page=page,
            paginate_by=FETCH_RESOURCE_CATEGORY_PAGE_SIZE
        )

        category_permission_queryset = self.fetch_category_permission_for_category_istances(
            paginated_categories
        )

        category_serializer = ResourceCategorySerializer(
            paginated_categories,
            many=True
        )

        category_permission_serializer = ResourceCategoryPermissionSerializer(
            category_permission_queryset,
            many=True
        )

        res = {
            'success': True,
            'categories': category_serializer.data,
            'category_permissions': category_permission_serializer.data
        }

        return res

    def fetch_root_level_resource_category_objects(self):
        """
        to fetch root level resource categories
        """
        resource_objs = ModelUtilities.get_model_filter(
            ResourceCategory,
            {
                'community_id': self.get_community_id(),
                'parent_category_id': None,
                'is_deleted': False
            }
        )

        return resource_objs

    def fetch_category_permission_for_category_istances(self, category_objs):
        """
        to fetch Resource Category Permissions for Categories
        """
        resource_objs = ModelUtilities.get_model_filter(
            ResourceCategoryPermission,
            {
                'category_id__in': category_objs,
            }
        )

        return resource_objs

    def update_resource_category(self, req_body):
        """
        to update resource category
        TODO:
            1. To Update permission access_type in
               ResourceCategoryPermission
            2. To add analytics
            3. To add references
        """
        resource_category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            req_body.get('id')
        )

        if not resource_category_instance:
            return get_error_context(False, 'incorrect id')

        if resource_category_instance.is_deleted:
            return get_error_context(False, 'The Resource Category has been deleted')

        validation_check = ResourceHelper.is_user_cm_or_not(
            resource_category_instance.community_id.id,
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        serializer = ResourceCategorySerializer(
            resource_category_instance,
            data=req_body,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            res = {
                'success': True,
                'resource_category': serializer.data
            }

            return res

        res = {
            'success': False,
            'error_message': serializer.errors
        }

        return res

    def delete_resource_category(self, req_body):
        """
        to delete resource category
        TODO:
            1. To delete all references
            2. To delete All sub-categories, urls and files recursively
        """
        resource_category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            req_body.get('id')
        )

        if not resource_category_instance:
            return get_error_context(False, 'incorrect id')

        validation_check = ResourceHelper.is_user_cm_or_not(
            resource_category_instance.community_id.id,
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        if resource_category_instance.is_deleted:
            return get_error_context(False, 'The Resource Category has already been deleted')

        resource_category_instance.is_deleted = True
        resource_category_instance.save()

        serializer = ResourceCategorySerializer(resource_category_instance)

        res = {
            'success': True,
            'resource_category': serializer.data
        }

        return res

class ResourceHelper:
    """
    Helper class for Resources
    """

    @staticmethod
    def is_user_cm_or_not(community_id, member_id):
        """
        Tells if the requesting user is a CM or not
        Args:
            community_id
            member_id
        Returns:
            success: Boolean
            error_message: If success is False
        """
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return get_error_context(False, "Invalid community_id")

        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not user_instance:
            return get_error_context(False, "Invalid member_id")

        is_cm = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_cm:
            return get_error_context(False, "You are not CM/Owner of this community")

        return {
            'success': True
        }

    @staticmethod
    def fetch_level_for_resource_category_instance(parent_category_id):
        """
        Args:
            parent_category_id
        Returns:
            level: distance from the root category
        """
        if parent_category_id:
            parent_category_instance = ModelUtilities.get_model_instance_or_none(
                ResourceCategory,
                parent_category_id
            )

            level = parent_category_instance.level + 1

        else:
            level = 0

        return level
