import json
from celery import shared_task
from django.db.models import Q
from utility.states import member_states

from togther.models import ModelUtilities, Community, User, Members, Cohort
from collabmates_api.cohort.cohort_impl import CohortHelper
from collabmates_api.rest_api import get_error_context

from .models import *
from .constants import *
from .serializers import *
from .resources_manager import ResourceManager
from .raw_queries import fetch_child_url_ids_for_updating_permission, \
                        fetch_child_file_ids_for_updating_permission, \
                        fetch_child_category_ids_for_updating_permission, \
                        get_parent_categories_with_access_type, \
                        get_child_resource_state_for_category

from internal_services.url_tags.uri_tags_impl import UriTagsImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.time_utilities import TimeUtilities
from external_services.segment.segment_impl import SegmentImpl

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class ResourcesImpl(ResourceManager):
    """Business logic for Resources"""
    member_id = None
    community_id = None
    category_id = None

    def __init__(self, member_id=None, community_id=None, category_id=None):
        self.member_id = member_id
        self.community_id = community_id
        self.category_id = category_id

    def get_member_id(self):
        """
        returns the member_id class variable

        Returns:
            member_id (int)
        """
        return self.member_id

    def get_community_id(self):
        """
        returns the community_id class variable

        Returns:
            community_id (int)
        """
        return self.community_id

    def get_category_id(self):
        """
        returns the category_id class variable

        Returns:
            category_id (int)
        """
        return self.category_id

    def set_community_id(self, community_id):
        """
        updates the community_id class variable

        Args:
            community_id (int)
        """
        self.community_id = community_id
        return

    def update_community_id_for_deleting_reference(self, req_body):
        """
        updates the community_id class variable while deleting reference

        Args:
            req_body (dict)
                category_id (nullable)
                url_id (nullable)
                file_id (nullable)
                child_category_id (nullable)
        Returns:
            response (dict)
        """
        res = {}

        if req_body.get('category_id'):
            resource_category_instance = ModelUtilities.get_model_instance_or_none(
                ResourceCategory,
                req_body.get('category_id')
            )

            if not resource_category_instance:
                return get_error_context(False, 'incorrect category_id')

            self.set_community_id(
                resource_category_instance.community_id.id
            )

            res['category_id'] = resource_category_instance

        if req_body.get('url_id'):
            resource_url_instance = ModelUtilities.get_model_instance_or_none(
                ResourceURL,
                req_body.get('url_id')
            )

            if not resource_url_instance:
                return get_error_context(False, 'incorrect url_id')

            self.set_community_id(
                resource_url_instance.category_id.community_id.id
            )

            res['url_id'] = resource_url_instance

        if req_body.get('file_id'):
            resource_file_instance = ModelUtilities.get_model_instance_or_none(
                ResourceFile,
                req_body.get('file_id')
            )

            if not resource_file_instance:
                return get_error_context(False, 'incorrect file_id')

            self.set_community_id(
                resource_file_instance.category_id.community_id.id
            )

            res['file_id'] = resource_file_instance

        if req_body.get('child_category_id'):
            child_category_instance = ModelUtilities.get_model_instance_or_none(
                ResourceCategory,
                req_body.get('child_category_id')
            )

            if not child_category_instance:
                return get_error_context(False, 'incorrect child_category_id')

            self.set_community_id(
                child_category_instance.community_id.id
            )

            res['child_category_id'] = child_category_instance

        return res

    def update_resource_settings(self, req_body):
        """
        updating resource settings

        Args:
            req_body (dict)
                community_id
                day_of_weekly_email (nullable)
                time_of_weekly_email (nullable)
        Returns:
            response (dict)
        """

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
        """
        fetching resource settings

        Returns:
            response (dict)
        """

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

        Args:
            req_body (dict) - request body
                community_id
                title
                icon_url
                parent_category_id (nullable)
                view_type (nullable)
                banner_url (nullable)
                is_deleted (nullable)
                is_downloadable (nullable)
                is_pinned (nullable)
        Returns:
            response (dict)
        """
        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        serializer = ResourceCategorySerializer(data=req_body)

        if serializer.is_valid():

            level = ResourceHelper.fetch_level_for_resource(
                req_body.get('parent_category_id')
            )

            serializer.save(level=level)

            if req_body.get('parent_category_id'):

                reference_dict = {
                    'category_id': serializer.data.get('parent_category_id'),
                    'child_category_id': serializer.data.get('id')
                }

                ResourcesImpl.create_resource_reference_internally.delay(
                    reference_dict,
                    self.get_member_id()
                )

                ResourcesImpl.copy_category_permission_from_parent_category.delay(
                    req_body.get('parent_category_id'),
                    serializer.data.get('id')
                )

                ResourcesImpl.create_parent_category_to_child_category_mapping.delay(
                    req_body.get('parent_category_id'),
                    serializer.data.get('id')
                )

            else:
                ResourcesImpl.create_category_permission_for_cohorts.delay(
                    self.get_community_id(),
                    serializer.data.get('id')
                )

            ResourceHelper.trigger_event_analytics_on_category_creation.delay(
                self.get_member_id(),
                self.get_community_id(),
                level=level
            )

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

    @staticmethod
    @shared_task
    def copy_category_permission_from_parent_category(parent_category_id, category_id):
        """
        bulk update cohorts mapping with category in
        ResourceCategoryPermission Schema based on parent
        category _id
        Args:
            parent_category_id
            category_id
        """
        parent_category_permission_filter = ModelUtilities.get_model_filter(
            ResourceCategoryPermission,
            {
                'category_id__id': parent_category_id
            }
        )

        category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            category_id
        )

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        child_category_permission_objs = [ResourceCategoryPermission(
            category_id=category_instance,
            cohort_id=parent_category_permission_obj.cohort_id,
            access_type=parent_category_permission_obj.access_type,
            created_at=current_time_in_ms,
            updated_at=current_time_in_ms
        ) for parent_category_permission_obj in parent_category_permission_filter]

        ModelUtilities.bulk_create_instances(
            ResourceCategoryPermission,
            child_category_permission_objs
        )

    @staticmethod
    @shared_task
    def create_category_permission_for_cohorts(community_id, category_id):
        """
        bulk create cohorts mapping with category in
        ResourceCategoryPermission Schema
        """
        category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            category_id
        )

        community_cohorts = ModelUtilities.get_model_filter(
            Cohort,
            {
                'community_id__id': community_id
            }
        )

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        category_permission_objs = [
            ResourceCategoryPermission(
                category_id=category_instance,
                cohort_id=cohort,
                created_at=current_time_in_ms,
                updated_at=current_time_in_ms
            ) for cohort in community_cohorts
        ]

        ModelUtilities.bulk_create_instances(
            ResourceCategoryPermission,
            category_permission_objs
        )

    @staticmethod
    @shared_task
    def create_parent_category_to_child_category_mapping(parent_category_id, category_id):
        """
        bulk create all parent category with child category mapping
        in ResourceCategoryParentCategory Schema
        """
        parent_category_list = list(ModelUtilities.get_model_filter(
            ResourceCategoryParentCategory,
            {
                'child_category_id__id': parent_category_id
            }
        ).values_list(
            'category_id',
            flat=True
        ))

        parent_category_list.append(parent_category_id)

        category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            category_id
        )

        parent_category_queryset = ModelUtilities.get_model_filter(
            ResourceCategory,
            {
                'id__in': parent_category_list
            }
        )

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        child_to_parent_category_mapping = [
            ResourceCategoryParentCategory(
                category_id=parent_category,
                child_category_id=category_instance,
                created_at=current_time_in_ms,
                updated_at=current_time_in_ms
            ) for parent_category in parent_category_queryset
        ]

        ModelUtilities.bulk_create_instances(
            ResourceCategoryParentCategory,
            child_to_parent_category_mapping
        )

    def fetch_resource_category(self, page):
        """
        to fetch resource category

        Args:
            page (int) - page number of the paginated response
        Returns:
            response (dict)
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
            many=True,
            context={
                'member_id': self.get_member_id(),
                'community_id': self.get_community_id()
            }
        )

        res = {
            'success': True,
            'categories': category_serializer.data,
            'category_permissions': category_permission_serializer.data
        }

        return res

    def fetch_root_level_resource_category_objects(self):
        """
        to fetch root level ResourceCategory

        Returns:
            resource_objs (queryset) : List of ResourceCategory objs
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

        Args:
            category_objs (queryset) : List of ResourceCategory objs
        Returns:
            resource_objs (queryset) : List of ResourceCategoryPermission objs
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

        Args:
            req_body (dict) - request body
                id
                title (nullable)
                icon_url (nullable)
                view_type (nullable)
                banner_url (nullable)
                is_deleted (nullable)
                is_downloadable (nullable)
                is_pinned (nullable)
                category_permission (nullable) - JSON list that updates permission for cohorts
                    cohort (required) - Cohort ID
                    access_type (required) - access type for that particular cohort.
        Returns:
            response (dict)
        """
        resource_category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            req_body.get('id')
        )

        if not resource_category_instance:
            return get_error_context(False, 'incorrect id')

        if resource_category_instance.is_deleted:
            return get_error_context(
                False,
                'The Resource Category has been deleted'
            )

        self.set_community_id(resource_category_instance.community_id.id)

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
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

            if req_body.get('category_permission'):
                ResourcesImpl.update_category_permission_for_cohorts.delay(
                    req_body.get('id'),
                    req_body.get('category_permission', [])
                )

                ResourceHelper.trigger_event_analytics_on_resource_permission_updation.delay(
                    self.get_member_id(),
                    self.get_community_id(),
                    RESOURCE_TYPE.CATEGORY,
                    req_body.get('category_permission'),
                    resource_category_instance.is_downloadable
                )

            if req_body.get('view_type'):
                ResourceHelper.trigger_event_analytics_on_category_view_updation.delay(
                    self.get_member_id(),
                    self.get_community_id(),
                    req_body.get('view_type')
                )

            ResourceHelper.trigger_event_analytics_on_resource_updation.delay(
                self.get_member_id(),
                self.get_community_id(),
                RESOURCE_TYPE.CATEGORY,
                req_body.get('title'),
                req_body.get('banner_url')
            )

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

    @staticmethod
    @shared_task
    def update_category_permission_for_cohorts(category_id, permission_obj):
        """
        updates access_type in ResourceCategoryPermission against a
        particular category_id and cohort_id
        Args:
            category_id (int)
            permission_dict (JSON):
                cohort_id
                access_type
        """
        for obj in permission_obj:

            if not obj.get('cohort_id') or not obj.get('access_type'):
                continue

            try:
                parent_categories_with_diff_access = ResourcesImpl.check_if_parent_categories_with_access_type_exist(
                    RESOURCE_TYPE.CATEGORY,
                    category_id,
                    obj
                )

                if not parent_categories_with_diff_access.get('success'):
                    continue

                ModelUtilities.update_or_create_model(
                    ResourceCategoryPermission,
                    filter_dict={
                        'category_id': ModelUtilities.get_model_instance_or_none(
                            ResourceCategory,
                            category_id
                        ),
                        'cohort_id': ModelUtilities.get_model_instance_or_none(
                            Cohort,
                            obj.get('cohort_id')
                        )
                    },
                    update_dict={
                        'access_type': obj.get('access_type')
                    }
                )

                ResourcesImpl.update_permissions_for_child_resources(obj, category_id)

            except Exception as e:
                error_logger.error("Exception occurred while updation/creation of ResourceCategoryPermission - %s" % e.args)
                pass

    @staticmethod
    def update_permissions_for_child_resources(req_obj, category_id):
        """
        Updates child resources' permissions based on the change
        in parent category permission changes

        Args:
            obj (dict)
                cohort_id
                access_type
            category_id
        """
        cohort_id = req_obj.get('cohort_id')
        access_type_list = ()

        if req_obj.get('access_type') == RESOURCE_ACCESS_TYPE.NO_ACCESS:

            access_type_list = [RESOURCE_ACCESS_TYPE.FULL_ACCESS,
                                RESOURCE_ACCESS_TYPE.RESTRICTED_ACCESS]

        elif req_obj.get('access_type') == RESOURCE_ACCESS_TYPE.RESTRICTED_ACCESS:

            access_type_list = [RESOURCE_ACCESS_TYPE.FULL_ACCESS]

        if access_type_list:
            url_ids_to_be_updated = fetch_child_url_ids_for_updating_permission(
                category_id,
                cohort_id,
                access_type_list
            )

            file_ids_to_be_updated = fetch_child_file_ids_for_updating_permission(
                category_id,
                cohort_id,
                access_type_list
            )

            category_ids_to_be_updated = fetch_child_category_ids_for_updating_permission(
                category_id,
                cohort_id,
                access_type_list
            )

            ModelUtilities.get_model_filter(
                ResourceURLPermission,
                {
                    'url_id__in': url_ids_to_be_updated,
                    'cohort_id': cohort_id
                }
            ).update(
                access_type=req_obj.get('access_type')
            )

            ModelUtilities.get_model_filter(
                ResourceFilePermission,
                {
                    'file_id__in': file_ids_to_be_updated,
                    'cohort_id': cohort_id
                }
            ).update(
                access_type=req_obj.get('access_type')
            )

            ModelUtilities.get_model_filter(
                ResourceCategoryPermission,
                {
                    'category_id__in': category_ids_to_be_updated,
                    'cohort_id': cohort_id
                }
            ).update(
                access_type=req_obj.get('access_type')
            )

    def delete_resource_category(self, req_body):
        """
        to delete resource category

        Args:
            req_body (dict) - request body
                id
        Returns:
            response (dict)
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
            return get_error_context(
                False,
                'The Resource Category has already been deleted'
            )

        resource_category_instance.is_deleted = True
        resource_category_instance.save()

        ResourcesImpl.recursively_delete_child_resources.delay(
            category_id=resource_category_instance.id
        )

        if resource_category_instance.parent_category_id:

            reference_dict = {
                'category_id': resource_category_instance.parent_category_id.id,
                'child_category_id': resource_category_instance.id
            }

        else:
            reference_dict = {
                'category_id': resource_category_instance.id
            }

        ResourcesImpl.delete_resource_reference_internally.delay(
            reference_dict,
            self.get_member_id()
        )

        serializer = ResourceCategorySerializer(resource_category_instance)

        res = {
            'success': True,
            'resource_category': serializer.data
        }

        return res

    @staticmethod
    @shared_task
    def recursively_delete_child_resources(category_id):
        """
        celery task that calls method to delete child resources
        Args:
            category_id: Category being deleted
        Returns:
            None
        """
        ResourcesImpl.recursive_method_to_delete_all_child_resources(
            [category_id]
        )

    @staticmethod
    def recursive_method_to_delete_all_child_resources(category_ids):
        """"
        deletes all child resources of the category being category
        Args:
            category_id (List) : Categories being deleted
        Returns:
            None
        """
        url_instances = ModelUtilities.get_model_filter(
            ResourceURL,
            {
                'category_id__id__in': category_ids
            }
        )

        file_instances = ModelUtilities.get_model_filter(
            ResourceFile,
            {
                'category_id__id__in': category_ids
            }
        )

        sub_category_instances = ModelUtilities.get_model_filter(
            ResourceCategory,
            {
                'parent_category_id__id__in': category_ids
            }
        )

        url_instances.update(is_deleted=True)
        file_instances.update(is_deleted=True)
        sub_category_instances.update(is_deleted=True)

        if not sub_category_instances:
            return

        sub_category_ids = list(sub_category_instances.values_list(
            'id',
            flat=True
        ))

        ResourcesImpl.recursive_method_to_delete_all_child_resources(
            sub_category_ids
        )

        return

    def create_resource_url(self, req_body):
        """
        to create resource url

        Args:
            req_body (dict) - request body
                category_id
                url
                title (nullable) - customised title of resource url ( to be updated in og_tags )
                banner_url - customised banner for resource url ( to be updated in image key of og_tags )
                og_tags (nullable) - JSON of og tags
                is_deleted (nullable)
                is_downloadable (nullable)
                is_pinned (nullable)
        Returns:
            response (dict)
        """
        resource_category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            req_body.get('category_id')
        )

        if not resource_category_instance:
            return get_error_context(False, 'incorrect category_id')

        self.set_community_id(resource_category_instance.community_id.id)

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        validated_data = self.populate_req_body_with_og_tags_for_fetching_resource_url(
            req_body
        )

        serializer = ResourceURLSerializer(data=validated_data)

        if serializer.is_valid():

            level = ResourceHelper.fetch_level_for_resource(
                req_body.get('category_id')
            )

            serializer.save(level=level)

            ResourcesImpl.create_url_permission_for_cohorts.delay(
                req_body.get('category_id'),
                serializer.data.get('id')
            )

            ResourcesImpl.create_url_state_for_all_members.delay(
                self.get_community_id(),
                serializer.data.get('id')
            )

            reference_dict = {
                'category_id': serializer.data.get('category_id'),
                'url_id': serializer.data.get('id')
            }

            ResourcesImpl.create_resource_reference_internally.delay(
                reference_dict,
                self.get_member_id()
            )

            ResourcesImpl.create_parent_category_to_child_url_mapping.delay(
                req_body.get('category_id'),
                serializer.data.get('id')
            )

            ResourceHelper.trigger_event_analytics_on_adding_resource.delay(
                self.get_member_id(),
                self.get_community_id(),
                RESOURCE_TYPE.URL,
                level=level
            )

            res = {
                'success': True,
                'resource_url': serializer.data
            }

            return res

        res = {
            'success': False,
            'error_message': serializer.errors
        }

        return res

    def populate_req_body_with_og_tags_for_fetching_resource_url(self,
                                                                 req_body):
        """
        returns a validated JSON that can be ingested in
        ResourceURLSerializer to create ResourceURL instance

        Args:
            req_body (dict) - request body
        Returns:
            validated_data (dict)
        """
        validated_data = {}

        url = req_body.get('url')
        og_tags = req_body.get('og_tags')

        if not url:
            return get_error_context(False, 'url is a non-nullable field')

        if not og_tags:
            og_tags = UriTagsImpl(url).get_tags_from_uri()

        if req_body.get('title'):
            og_tags['title'] = req_body.get('title')

        if req_body.get('banner_url'):
            og_tags['image'] = req_body.get('banner_url')

        validated_data = req_body.copy()

        validated_data['og_tags'] = json.dumps(og_tags)

        return validated_data

    @staticmethod
    @shared_task
    def create_url_permission_for_cohorts(category_id, url_id):
        """
        bulk create cohorts mapping with url in
        ResourceURLPermission Schema
        Args:
            category_id
            url_id
        """
        category_permission_filter = ModelUtilities.get_model_filter(
            ResourceCategoryPermission,
            {
                'category_id__id': category_id
            }
        )

        url_instance = ModelUtilities.get_model_instance_or_none(
            ResourceURL,
            url_id
        )

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        url_permission_objs = [ResourceURLPermission(
            url_id=url_instance,
            cohort_id=category_permission_obj.cohort_id,
            access_type=category_permission_obj.access_type,
            created_at=current_time_in_ms,
            updated_at=current_time_in_ms
        ) for category_permission_obj in category_permission_filter]

        ModelUtilities.bulk_create_instances(
            ResourceURLPermission,
            url_permission_objs
        )

    @staticmethod
    @shared_task
    def create_url_state_for_all_members(community_id, url_id):
        """
        bulk create all members mapping with url in
        ResourceURLState Schema
        Args:
            community_id
            url_id
        """
        community_member_filter = ModelUtilities.get_model_filter(
            Members,
            {
                'community_id__id': community_id,
                'state__in': [member_states.ADMIN, member_states.MEMBER]
            }
        )

        url_instance = ModelUtilities.get_model_instance_or_none(
            ResourceURL,
            url_id
        )

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        url_state_objs = [ResourceURLState(
            url_id=url_instance,
            user_id=member.member_id,
            created_at=current_time_in_ms,
            updated_at=current_time_in_ms
        ) for member in community_member_filter]

        ModelUtilities.bulk_create_instances(
            ResourceURLState,
            url_state_objs
        )

    @staticmethod
    @shared_task
    def create_parent_category_to_child_url_mapping(category_id, url_id):
        """
        bulk create all parent category with child url mapping
        in ResourceURLParentCategory Schema
        """
        parent_category_list = list(ModelUtilities.get_model_filter(
            ResourceCategoryParentCategory,
            {
                'child_category_id__id': category_id
            }
        ).values_list(
            'category_id',
            flat=True
        ))

        parent_category_list.append(category_id)

        url_instance = ModelUtilities.get_model_instance_or_none(
            ResourceURL,
            url_id
        )

        parent_category_queryset = ModelUtilities.get_model_filter(
            ResourceCategory,
            {
                'id__in': parent_category_list
            }
        )

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        child_to_parent_category_mapping = [
            ResourceURLParentCategory(
                category_id=parent_category,
                url_id=url_instance,
                created_at=current_time_in_ms,
                updated_at=current_time_in_ms
            ) for parent_category in parent_category_queryset
        ]

        ModelUtilities.bulk_create_instances(
            ResourceURLParentCategory,
            child_to_parent_category_mapping
        )

    def update_resource_url(self, req_body):
        """
        to update resource url

        Args:
            req_body (dict) - request body
                id
                url (nullable)
                og_tags (nullable) - JSON of og tags
                title (nullable) - customised title of resource url ( to be updated in og_tags )
                banner_url - customised banner for resource url ( to be updated in image key of og_tags)
                is_deleted (nullable)
                is_downloadable (nullable)
                is_pinned (nullable)
                url_permission (nullable): JSON List that updates permission for cohorts
                    cohort (required) - Cohort ID
                    access_type (required) - access type for that particular cohort. Options:-
        Returns:
            response (dict)
        """
        resource_url_instance = ModelUtilities.get_model_instance_or_none(
            ResourceURL,
            req_body.get('id')
        )

        if not resource_url_instance:
            return get_error_context(False, 'incorrect id')

        self.set_community_id(
            resource_url_instance.category_id.community_id.id
        )

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        if resource_url_instance.is_deleted:
            return get_error_context(
                False,
                'The Resource URL has been deleted'
            )

        validated_data = self.populate_req_body_with_og_tags_for_updating_resource_url(
            req_body,
            resource_url_instance
        )

        serializer = ResourceURLSerializer(
            resource_url_instance,
            data=validated_data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            if req_body.get('url_permission'):
                ResourcesImpl.update_url_permission_for_cohorts.delay(
                    req_body.get('id'),
                    req_body.get('url_permission', [])
                )

                ResourceHelper.trigger_event_analytics_on_resource_permission_updation.delay(
                    self.get_member_id(),
                    self.get_community_id(),
                    RESOURCE_TYPE.URL,
                    req_body.get('url_permission'),
                    resource_url_instance.is_downloadable
                )

            ResourceHelper.trigger_event_analytics_on_resource_updation.delay(
                self.get_member_id(),
                self.get_community_id(),
                RESOURCE_TYPE.URL,
                req_body.get('title'),
                req_body.get('banner_url')
            )

            res = {
                'success': True,
                'resource_url': serializer.data
            }

            return res

        res = {
            'success': False,
            'error_message': serializer.errors
        }

        return res

    def populate_req_body_with_og_tags_for_updating_resource_url(self,
                                                                 req_body,
                                                                 instance):
        """
        returns a validated JSON that can be ingested in
        ResourceURLSerializer to update ResourceURL instance

        Args:
            req_body (dict) - request body
            instance (ResourceCategory obj) - parent ResourceCategory
        Returns:
            validated_data (dict)
        """
        validated_data = req_body.copy()

        url = req_body.get('url')
        og_tags = req_body.get('og_tags')

        if url and not og_tags:
            og_tags = UriTagsImpl(url).get_tags_from_uri()

        if req_body.get('title'):

            if not og_tags:
                og_tags = json.loads(instance.og_tags)

            og_tags['title'] = req_body.get('title')

        if req_body.get('banner_url'):

            if not og_tags:
                og_tags = json.loads(instance.og_tags)

            og_tags['image'] = req_body.get('banner_url')

        if og_tags:
            validated_data['og_tags'] = json.dumps(og_tags)

        return validated_data

    @staticmethod
    @shared_task
    def update_url_permission_for_cohorts(url_id, permission_obj):
        """
        updates access_type in ResourceURLPermission against a
        particular url_id and cohort_id
        Args:
            url_id (int)
            permission_dict (JSON):
                cohort_id
                access_type
        """
        for obj in permission_obj:

            if not obj.get('cohort_id') or not obj.get('access_type'):
                continue

            try:
                parent_categories_with_diff_access = ResourcesImpl.check_if_parent_categories_with_access_type_exist(
                    RESOURCE_TYPE.URL,
                    url_id,
                    obj
                )

                if not parent_categories_with_diff_access.get('success'):
                    continue

                ModelUtilities.update_or_create_model(
                    ResourceURLPermission,
                    filter_dict={
                        'url_id': ModelUtilities.get_model_instance_or_none(
                            ResourceURL,
                            url_id
                        ),
                        'cohort_id': ModelUtilities.get_model_instance_or_none(
                            Cohort,
                            obj.get('cohort_id')
                        )
                    },
                    update_dict={
                        'access_type': obj.get('access_type')
                    }
                )
            except Exception as e:
                error_logger.error("Exception occurred while updation/creation of ResourceURLPermission - %s" % e.args)
                pass

    @staticmethod
    def check_if_parent_categories_with_access_type_exist(resource_type,
                                                          resource_id,
                                                          obj):
        """
        checks if any parent category has a "restricted" access set

        Args:
            resource_type (str)
            resource_id (str)
            obj (dict)
                cohort_id
                access_type
        Returns:
            success (boolean)
            error_message (str)
        """
        if obj.get('access_type') == RESOURCE_ACCESS_TYPE.FULL_ACCESS:

            access_type_list = [RESOURCE_ACCESS_TYPE.RESTRICTED_ACCESS,
                                RESOURCE_ACCESS_TYPE.NO_ACCESS]

            parent_categories_with_diff_access = get_parent_categories_with_access_type(
                resource_type,
                resource_id,
                obj.get('cohort_id'),
                access_type_list
            )

            if parent_categories_with_diff_access:
                res = get_error_context(
                    False,
                    "You cannot update access_type for this resource as its \
                        parent categories have RESTRICTED/NO ACCESS set for %s" \
                        % str(obj.get('cohort_id'))
                )

                return res

        elif obj.get('access_type') == RESOURCE_ACCESS_TYPE.RESTRICTED_ACCESS:

            access_type_list = [RESOURCE_ACCESS_TYPE.NO_ACCESS]

            parent_categories_with_diff_access = get_parent_categories_with_access_type(
                resource_type,
                resource_id,
                obj.get('cohort_id'),
                access_type_list
            )

            if parent_categories_with_diff_access:
                res = get_error_context(
                    False,
                    "You cannot update access_type for this resource as its \
                        parent categories have NO ACCESS set for %s" % \
                        str(obj.get('cohort_id'))
                )

                return res

        return {'success': True}

    def delete_resource_url(self, req_body):
        """
        to delete resource url

        Args:
            req_body (dict) - request body
                id
        Returns:
            response (dict)
        """
        resource_url_instance = ModelUtilities.get_model_instance_or_none(
            ResourceURL,
            req_body.get('id')
        )

        if not resource_url_instance:
            return get_error_context(False, 'incorrect id')

        self.set_community_id(
            resource_url_instance.category_id.community_id.id
        )

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        if resource_url_instance.is_deleted:
            return get_error_context(
                False,
                'The Resource URL has already been deleted'
            )

        resource_url_instance.is_deleted = True
        resource_url_instance.save()

        ResourceHelper.trigger_event_analytics_on_deleting_resource.delay(
            self.get_member_id(),
            self.get_community_id()
        )

        reference_dict = {
            'category_id': resource_url_instance.category_id.id,
            'url_id': resource_url_instance.id
        }

        ResourcesImpl.delete_resource_reference_internally.delay(
            reference_dict,
            self.get_member_id()
        )

        serializer = ResourceURLSerializer(resource_url_instance)

        res = {
            'success': True,
            'resource_url': serializer.data
        }

        return res

    def create_resource_file(self, req_body):
        """
        to create resource file

        Args:
            req_body (dict) - request body
                category_id
                url
                name
                type
                meta (nullable)
                is_deleted (nullable)
                is_downloadable (nullable)
                is_pinned (nullable)
        Returns:
            response (dict)
        """
        resource_category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            req_body.get('category_id')
        )

        if not resource_category_instance:
            return get_error_context(False, 'incorrect category_id')

        self.set_community_id(resource_category_instance.community_id.id)

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        serializer = ResourceFileSerializer(data=req_body)

        if serializer.is_valid():

            level = ResourceHelper.fetch_level_for_resource(
                req_body.get('category_id')
            )

            serializer.save(level=level)

            ResourcesImpl.create_file_permission_for_cohorts.delay(
                req_body.get('category_id'),
                serializer.data.get('id')
            )

            ResourcesImpl.create_file_state_for_all_members.delay(
                self.get_community_id(),
                serializer.data.get('id')
            )

            reference_dict = {
                'category_id': serializer.data.get('category_id'),
                'file_id': serializer.data.get('id')
            }

            ResourcesImpl.create_resource_reference_internally.delay(
                reference_dict,
                self.get_member_id()
            )

            ResourcesImpl.create_parent_category_to_child_file_mapping.delay(
                req_body.get('category_id'),
                serializer.data.get('id')
            )

            ResourceHelper.trigger_event_analytics_on_adding_resource.delay(
                self.get_member_id(),
                self.get_community_id(),
                RESOURCE_TYPE.FILE,
                level=level
            )

            res = {
                'success': True,
                'resource_file': serializer.data
            }

            return res

        res = {
            'success': False,
            'error_message': serializer.errors
        }

        return res

    @staticmethod
    @shared_task
    def create_file_permission_for_cohorts(category_id, file_id):
        """
        bulk create cohorts mapping with file in
        ResourceFilePermission Schema
        Args:
            category_id
            file_id
        """
        category_permission_filter = ModelUtilities.get_model_filter(
            ResourceCategoryPermission,
            {
                'category_id__id': category_id
            }
        )

        file_instance = ModelUtilities.get_model_instance_or_none(
            ResourceFile,
            file_id
        )

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        file_permission_objs = [ResourceFilePermission(
            file_id=file_instance,
            cohort_id=category_permission_obj.cohort_id,
            access_type=category_permission_obj.access_type,
            created_at=current_time_in_ms,
            updated_at=current_time_in_ms
        ) for category_permission_obj in category_permission_filter]

        ModelUtilities.bulk_create_instances(
            ResourceFilePermission,
            file_permission_objs
        )

    @staticmethod
    @shared_task
    def create_file_state_for_all_members(community_id, file_id):
        """
        bulk create all members mapping with file in
        ResourceFileState Schema
        Args:
            community_id
            file_id
        """
        community_member_filter = ModelUtilities.get_model_filter(
            Members,
            {
                'community_id__id': community_id,
                'state__in': [member_states.ADMIN, member_states.MEMBER]
            }
        )

        file_instance = ModelUtilities.get_model_instance_or_none(
            ResourceFile,
            file_id
        )

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        file_state_objs = [ResourceFileState(
            file_id=file_instance,
            user_id=member.member_id,
            created_at=current_time_in_ms,
            updated_at=current_time_in_ms
        ) for member in community_member_filter]

        ModelUtilities.bulk_create_instances(
            ResourceFileState,
            file_state_objs
        )

    @staticmethod
    @shared_task
    def create_parent_category_to_child_file_mapping(category_id, file_id):
        """
        bulk create all parent category with child url mapping
        in ResourceURLParentCategory Schema
        """
        parent_category_list = list(ModelUtilities.get_model_filter(
            ResourceCategoryParentCategory,
            {
                'child_category_id__id': category_id
            }
        ).values_list(
            'category_id',
            flat=True
        ))

        parent_category_list.append(category_id)

        file_instance = ModelUtilities.get_model_instance_or_none(
            ResourceFile,
            file_id
        )

        parent_category_queryset = ModelUtilities.get_model_filter(
            ResourceCategory,
            {
                'id__in': parent_category_list
            }
        )

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        child_to_parent_category_mapping = [
            ResourceFileParentCategory(
                category_id=parent_category,
                file_id=file_instance,
                created_at=current_time_in_ms,
                updated_at=current_time_in_ms
            ) for parent_category in parent_category_queryset
        ]

        ModelUtilities.bulk_create_instances(
            ResourceFileParentCategory,
            child_to_parent_category_mapping
        )

    def update_resource_file(self, req_body):
        """
        to update resource file

        Args:
            req_body (dict) - request body
            id
            url (nullable)
            name (nullable)
            type (nullable)
            meta (nullable)
            banner - banner_url of resource_file
            is_deleted (nullable)
            is_downloadable (nullable)
            is_pinned (nullable)
            file_permission (nullable): JSON List that updates permission for cohorts
                cohort (required) - Cohort ID
                access_type (required) - access type for that particular cohort. 
        Returns:
            response (dict)
        """
        resource_file_instance = ModelUtilities.get_model_instance_or_none(
            ResourceFile,
            req_body.get('id')
        )

        if not resource_file_instance:
            return get_error_context(False, 'incorrect id')

        self.set_community_id(
            resource_file_instance.category_id.community_id.id
        )

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        if resource_file_instance.is_deleted:
            return get_error_context(
                False,
                'The Resource File has been deleted'
            )

        serializer = ResourceFileSerializer(
            resource_file_instance,
            data=req_body,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            if req_body.get('file_permission'):
                ResourcesImpl.update_file_permission_for_cohorts.delay(
                    req_body.get('id'),
                    req_body.get('file_permission', [])
                )

                ResourceHelper.trigger_event_analytics_on_resource_permission_updation.delay(
                    self.get_member_id(),
                    self.get_community_id(),
                    RESOURCE_TYPE.FILE,
                    req_body.get('file_permission'),
                    resource_file_instance.is_downloadable
                )

            ResourceHelper.trigger_event_analytics_on_resource_updation.delay(
                self.get_member_id(),
                self.get_community_id(),
                RESOURCE_TYPE.FILE,
                req_body.get('name'),
                req_body.get('meta')
            )

            res = {
                'success': True,
                'resource_file': serializer.data
            }

            return res

        res = {
            'success': False,
            'error_message': serializer.errors
        }

        return res

    @staticmethod
    @shared_task
    def update_file_permission_for_cohorts(file_id, permission_obj):
        """
        updates access_type in ResourceFilePermission against a
        particular file_id and cohort_id
        Args:
            file_id (int)
            permission_dict (JSON):
                cohort_id
                access_type
        """
        for obj in permission_obj:

            if not obj.get('cohort_id') or not obj.get('access_type'):
                continue

            try:
                parent_categories_with_diff_access = ResourcesImpl.check_if_parent_categories_with_access_type_exist(
                    RESOURCE_TYPE.FILE,
                    file_id,
                    obj
                )

                if not parent_categories_with_diff_access.get('success'):
                    continue

                ModelUtilities.update_or_create_model(
                    ResourceFilePermission,
                    filter_dict={
                        'file_id': ModelUtilities.get_model_instance_or_none(
                            ResourceFile,
                            file_id
                        ),
                        'cohort_id': ModelUtilities.get_model_instance_or_none(
                            Cohort,
                            obj.get('cohort_id')
                        )
                    },
                    update_dict={
                        'access_type': obj.get('access_type')
                    }
                )
            except Exception as e:
                error_logger.error("Exception occurred while updation/creation of ResourceFilePermission - %s" % e.args)
                pass

    def delete_resource_file(self, req_body):
        """
        to delete resource file

        Args:
            req_body (dict) - request body
                id
        Returns:
            response (dict)
        """
        resource_file_instance = ModelUtilities.get_model_instance_or_none(
            ResourceFile,
            req_body.get('id')
        )

        if not resource_file_instance:
            return get_error_context(False, 'incorrect id')

        self.set_community_id(
            resource_file_instance.category_id.community_id.id
        )

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        if resource_file_instance.is_deleted:
            return get_error_context(
                False,
                'The Resource File has already been deleted'
            )

        resource_file_instance.is_deleted = True
        resource_file_instance.save()

        ResourceHelper.trigger_event_analytics_on_deleting_resource.delay(
            self.get_member_id(),
            self.get_community_id()
        )

        reference_dict = {
            'category_id': resource_file_instance.category_id.id,
            'file_id': resource_file_instance.id
        }

        ResourcesImpl.delete_resource_reference_internally.delay(
            reference_dict,
            self.get_member_id()
        )

        serializer = ResourceFileSerializer(resource_file_instance)

        res = {
            'success': True,
            'resource_file': serializer.data
        }

        return res

    def create_resource_reference(self, req_body):
        """
        to create resource reference

        Args:
            req_body (dict) - request body
                category_id
                url_id (nullable)
                file_id (nullable)
                child_category_id (nullable)
        Returns:
            response (dict)
        """
        resource_category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            req_body.get('category_id')
        )

        if not resource_category_instance:
            return get_error_context(False, 'incorrect category_id')

        self.set_community_id(resource_category_instance.community_id.id)

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        if not any([
            req_body.get('url_id'),
            req_body.get('file_id'),
            req_body.get('child_category_id')
        ]):
            return get_error_context(
                False,
                "atleast one among url_id, file_id, child_category_id is required"
            )

        serializer = ResourceReferenceSerializer(data=req_body)

        if serializer.is_valid():
            serializer.save()

            res = {
                'success': True,
                'resource_reference': serializer.data
            }

            return res

        res = {
            'success': False,
            'error_message': serializer.errors
        }

        return res

    @staticmethod
    @shared_task
    def create_resource_reference_internally(reference_dict, member_id):
        """
        to create resource reference instance internally
        Args:
            req_dict: Dict of input variables
        Returns:
            None
        """
        res_instance = ResourcesImpl(
            member_id=member_id,
            category_id=reference_dict.get('category_id')
        )

        res = res_instance.create_resource_reference(reference_dict)

        return

    def delete_resource_reference(self, req_body):
        """
        to delete resource reference

        Args:
            req_body (dict) - request body
                category_id (nullable)
                url_id (nullable)
                file_id (nullable)
                child_category_id (nullable)
        Returns:
            response (dict)
        """
        req_objs_check = self.update_community_id_for_deleting_reference(
            req_body
        )

        if not req_objs_check:
            return get_error_context(False, "invalid data")

        validation_check = ResourceHelper.is_user_cm_or_not(
            self.get_community_id(),
            self.get_member_id()
        )

        if not validation_check.get('success'):
            return validation_check

        if not any([
            req_body.get('category_id'),
            req_body.get('url_id'),
            req_body.get('file_id'),
            req_body.get('child_category_id')
        ]):
            return get_error_context(
                False,
                'atleast one among category_id, url_id, file_id, child_category_id is required'
            )

        resource_reference_instances = ModelUtilities.get_model_filter(
            ResourceReference,
            req_objs_check
        )

        if not resource_reference_instances:
            return get_error_context(
                False,
                'incorrect data'
            )

        if req_objs_check.get('url_id') or \
           req_objs_check.get('file_id'):
            instances = resource_reference_instances

        else:
            instances = ResourcesImpl.get_resource_references_to_delete_recursively(
                resource_reference_instances
            )

        instances.delete()

        res = {
            'success': True,
        }

        return res

    @staticmethod
    @shared_task
    def delete_resource_reference_internally(reference_dict, member_id):
        """
        to delete resource reference instance internally
        Args:
            req_dict: Dict of input variables
        Returns:
            None
        """
        res_instance = ResourcesImpl(
            member_id=member_id,
            category_id=reference_dict.get('category_id')
        )

        res = res_instance.delete_resource_reference(reference_dict)

        return

    @staticmethod
    def get_resource_references_to_delete_recursively(instances):
        """
        to fetch all the resource reference instances that are
        child to the current resource being deleted
        Args:
            instances : Resource Reference Queryset

        Returns:
            final_instances : Resource Reference Queryset
        """
        sub_categories_ids = instances.filter(
            child_category_id__isnull=False
        ).values_list(
            'child_category_id',
            flat=True
        )

        if not sub_categories_ids:
            return instances

        sub_reference_intances = ModelUtilities.get_model_filter(
            ResourceReference,
            {
                'category_id__in': sub_categories_ids
            }
        )

        final_instances = instance, ResourcesImpl.get_resource_references_to_delete_recursively(sub_reference_intances)

        info_logger.info('deleted resource reference instances - %s' % final_instances)

        return final_instances

    def fetch_resource_reference(self, page):
        """
        to fetch resource references

        Args:
            req_body (dict) - request body
        Returns:
            response (dict)
        """
        resource_category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            self.get_category_id()
        )

        if not resource_category_instance:
            return get_error_context(False, 'incorrect category_id')

        self.set_community_id(
            resource_category_instance.community_id.id
        )

        member_check = Members.is_community_member(
            self.get_community_id(),
            self.get_member_id()
        )

        if not member_check:
            return get_error_context(
                False,
                "To view resources, you need to be a member of the community."
            )

        reference_instances = ModelUtilities.get_model_filter(
            ResourceReference,
            {
                'category_id': resource_category_instance
            }
        ).select_related(
            'url_id',
            'file_id',
            'category_id'
        )

        reference_queryset = ModelUtilities.paginate_queryset(reference_instances,
                                                              page,
                                                              paginate_by=FETCH_RESOURCE_CATEGORY_PAGE_SIZE)

        url_dict = self.fetch_child_url_data_for_category(
            reference_queryset
        )

        file_dict = self.fetch_child_file_data_for_category(
            reference_queryset
        )

        category_dict = self.fetch_child_category_data_for_category(
            reference_queryset
        )

        res = {'success':True}

        res.update(url_dict)
        res.update(file_dict)
        res.update(category_dict)

        return res

    def fetch_child_url_data_for_category(self, reference_queryset):
        """
        Returns
            ResourceURL instances
            ResourceURLPermission instances
            REsourceURLState instances
        for a particular category
        """
        url_ids = []

        for ref in reference_queryset:
            if ref.url_id:
                url_ids.append(ref.url_id.id)

        url_instances = ModelUtilities.get_model_filter(
            ResourceURL,
            {
                'id__in': url_ids
            }
        )

        url_permission_instances = ModelUtilities.get_model_filter(
            ResourceURLPermission,
            {
                'url_id__in': url_instances
            }
        )

        url_state_instances = ModelUtilities.get_model_filter(
            ResourceURLState,
            {
                'url_id__in': url_instances,
                'user_id__id': self.get_member_id()
            }
        )

        url_serializer = ResourceURLSerializer(
            url_instances,
            many=True
        )

        url_permission_serializer = ResourceURLPermissionSerializer(
            url_permission_instances,
            many=True,
            context={
                'member_id': self.get_member_id(),
                'community_id': self.get_community_id()
            }
        )

        url_state_serializer = ResourceURLStateSerializer(
            url_state_instances,
            many=True
        )

        res = {
            'urls': url_serializer.data,
            'url_permissions': url_permission_serializer.data,
            'url_states': url_state_serializer.data
        }

        return res

    def fetch_child_file_data_for_category(self, reference_queryset):
        """
        Returns
            ResourceFile instances
            ResourceFilePermission instances
            ResourceFileState instances
        for a particular category
        """
        file_ids = []

        for ref in reference_queryset:
            if ref.file_id:
                file_ids.append(ref.file_id.id)

        file_instances = ModelUtilities.get_model_filter(
            ResourceFile,
            {
                'id__in': file_ids
            }
        )

        file_permission_instances = ModelUtilities.get_model_filter(
            ResourceFilePermission,
            {
                'file_id__in': file_instances
            }
        )

        file_state_instances = ModelUtilities.get_model_filter(
            ResourceFileState,
            {
                'file_id__in': file_instances,
                'user_id__id': self.get_member_id()
            }
        )

        file_serializer = ResourceFileSerializer(
            file_instances,
            many=True
        )

        file_permission_serializer = ResourceFilePermissionSerializer(
            file_permission_instances,
            many=True,
            context={
                'member_id': self.get_member_id(),
                'community_id': self.get_community_id()
            }
        )

        file_state_serializer = ResourceFileStateSerializer(
            file_state_instances,
            many=True
        )

        res = {
            'files': file_serializer.data,
            'file_permissions': file_permission_serializer.data,
            'file_states': file_state_serializer.data
        }

        return res

    def fetch_child_category_data_for_category(self, reference_queryset):
        """
        Returns
            ResourceCategory instances
            ResourceCategoryPermission instances
            Child ResourceURLState instances
            Child ResourceFileState instances
        for a particular category
        """
        category_ids = []

        for ref in reference_queryset:
            if ref.category_id:
                category_ids.append(ref.category_id.id)

        category_instances = ModelUtilities.get_model_filter(
            ResourceCategory,
            {
                'id__in': category_ids
            }
        )

        category_permission_instances = ModelUtilities.get_model_filter(
            ResourceCategoryPermission,
            {
                'category_id__in': category_instances
            }
        )

        category_serializer = ResourceCategorySerializer(
            category_instances,
            many=True
        )

        category_permission_serializer = ResourceCategoryPermissionSerializer(
            category_permission_instances,
            many=True,
            context={
                'member_id': self.get_member_id(),
                'community_id': self.get_community_id()
            }
        )

        child_category_list = list(category_instances.values_list('id', flat=True))

        child_category_url_state_ids = get_child_resource_state_for_category(
            RESOURCE_TYPE.URL,
            RESOURCE_STATE.UNSEEN,
            self.get_member_id(),
            child_category_list
        )

        child_category_file_state_ids = get_child_resource_state_for_category(
            RESOURCE_TYPE.FILE,
            RESOURCE_STATE.UNSEEN,
            self.get_member_id(),
            child_category_list
        )

        child_category_url_state_instances = ModelUtilities.get_model_filter(
            ResourceURLState,
            {
                'url_id__id__in': child_category_url_state_ids,
                'user_id__id': self.get_member_id()
            }
        )

        child_category_file_state_instances = ModelUtilities.get_model_filter(
            ResourceFileState,
            {
                'file_id__id__in': child_category_file_state_ids,
                'user_id__id': self.get_member_id()
            }
        )

        child_category_url_state_serializer = ChildCategoryURLStateSerializer(
            child_category_url_state_instances,
            many=True
        )

        child_category_file_state_serializer = ChildCategoryFileStateSerializer(
            child_category_file_state_instances,
            many=True
        )

        res = {
            'child_categories': category_serializer.data,
            'child_category_permissions': category_permission_serializer.data,
            'child_category_url_states': child_category_url_state_serializer.data,
            'child_category_file_states': child_category_file_state_serializer.data
        }

        return res

    def update_resource_state(self, req_body):
        """
        to update resource's state

        Args:
            req_body (dict) - request body
                state
                file_id (nullable) - Resource File ID
                url_id (nullable) - Resource URL ID
        Returns:
            response (dict)
        """
        if req_body.get('url_id'):

            state_filter = ModelUtilities.get_model_filter(
                ResourceURLState,
                {
                    'url_id__id': req_body.get('url_id'),
                    'user_id__id': self.get_member_id()
                }
            )

        elif req_body.get('file_id'):

            state_filter = ModelUtilities.get_model_filter(
                ResourceFileState,
                {
                    'file_id__id': req_body.get('file_id'),
                    'user_id__id': self.get_member_id()
                }
            )

        if not state_filter:
            return get_error_context(False, "invalid url_id/file_id")

        state_filter.update(state=req_body.get('state'))

        if req_body.get('state') == RESOURCE_STATE.CONTINUE_READING:

            if req_body.get('url_id'):
                ResourcesImpl.update_other_resources_state_for_user.delay(
                    self.get_member_id(),
                    url_id=req_body.get('url_id')
                )

            else:
                ResourcesImpl.update_other_resources_state_for_user.delay(
                    self.get_member_id(),
                    file_id=req_body.get('file_id')
                )

        return {'success': True}

    @staticmethod
    @shared_task
    def update_other_resources_state_for_user(member_id, url_id=None, file_id=None):
        """
        updates state for rest of the resources (url and file)
        if any resource is updated with the state = 3
        """
        if url_id:
            ModelUtilities.get_model_filter(
                ResourceURLState,
                {
                    'user_id__id': member_id,
                    'state': RESOURCE_STATE.CONTINUE_READING
                }
            ).exclude(
                url_id=url_id
            ).update(
                state=RESOURCE_STATE.SEEN
            )

            ModelUtilities.get_model_filter(
                ResourceFileState,
                {
                    'user_id__id': member_id,
                    'state': RESOURCE_STATE.CONTINUE_READING
                }
            ).update(
                state=RESOURCE_STATE.SEEN
            )

        elif file_id:
            ModelUtilities.get_model_filter(
                ResourceFileState,
                {
                    'user_id__id': member_id,
                    'state': RESOURCE_STATE.CONTINUE_READING
                }
            ).exclude(
                file_id=file_id
            ).update(
                state=RESOURCE_STATE.SEEN
            )

            ModelUtilities.get_model_filter(
                ResourceURLState,
                {
                    'user_id__id': member_id,
                    'state': RESOURCE_STATE.CONTINUE_READING
                }
            ).update(
                state=RESOURCE_STATE.SEEN
            )

    def fetch_resource_state(self, req_body):
        """
        to fetch resource's state

        Args:
            req_body (dict) - request body
                community_id
                state
        Returns:
            response (dict)
        """
        url_filter = list(ModelUtilities.get_model_filter(
            ResourceURLState,
            {
                'state': req_body.get('state'),
                'user_id__id': self.get_member_id(),
                'url_id__category_id__community_id__id': self.get_community_id()
            }
        ).values_list(
            'url_id',
            flat=True
        ))

        file_filter = list(ModelUtilities.get_model_filter(
            ResourceFileState,
            {
                'state': req_body.get('state'),
                'user_id__id': self.get_member_id(),
                'file_id__category_id__community_id__id': self.get_community_id()
            }
        ).values_list(
            'file_id',
            flat=True
        ))

        url_instances = ModelUtilities.get_model_filter(
            ResourceURL,
            {
                'id__in': url_filter
            }
        )

        file_instances = ModelUtilities.get_model_filter(
            ResourceFile,
            {
                'id__in': file_filter
            }
        )

        url_category_ids = list(
            url_instances.values_list(
                'category_id',
                flat=True
            ).distinct()
        )

        file_category_ids = list(
            file_instances.values_list(
                'category_id',
                flat=True
            ).distinct()
        )

        final_category_ids = set(url_category_ids + file_category_ids)

        category_instances = ModelUtilities.get_model_filter(
            ResourceCategory,
            {
                'id__in': final_category_ids
            }
        )

        url_serializer = ResourceURLSerializer(url_instances, many=True)
        file_serializer = ResourceFileSerializer(file_instances, many=True)
        category_serializer = ResourceCategorySerializer(category_instances, many=True)

        return {
            'success': True,
            'url': url_serializer.data,
            'file': file_serializer.data,
            'category': category_serializer.data,
        }


class ResourceHelper:
    """
    Helper class for Resources
    """

    @staticmethod
    def is_user_cm_or_not(community_id, member_id):
        """
        Tells if the requesting user is a CM or not

        Args:
            community_id (int)
            member_id (int)
        Returns:
            success: Boolean
            error_message (string): If success is False
        """
        community_instance = ModelUtilities.get_model_instance_or_none(
            Community,
            community_id
        )

        if not community_instance:
            return get_error_context(False, "Invalid community_id")

        user_instance = ModelUtilities.get_model_instance_or_none(
            User,
            member_id
        )

        if not user_instance:
            return get_error_context(False, "Invalid member_id")

        is_cm = Members.is_member_community_promoter(community_instance, user_instance)

        if not is_cm:
            return get_error_context(False, "You are not CM/Owner of this community")

        return {
            'success': True
        }

    @staticmethod
    def fetch_level_for_resource(parent_category_id):
        """
        returns level for any resource (URL, File or Category)
        via the parent ResourceCategory

        Args:
            parent_category_id (string)
        Returns:
            level (int): distance from the root category
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

    @staticmethod
    def fetch_access_type_for_resource(resource_type, resource_id,
                                       community_id, member_id):
        """
        returns the access type for a particular resource by comparing
        it's cohorts, all member cohorts and the access_type specified
        in the Permission schema

        Args:
            resource_type : category, url, file
            resource_id : respective resource ID
        Returns:
            access_type (int)
        """
        access_type_to_cohort_mapper = ResourceHelper.create_access_type_to_cohort_mapper(
            resource_type,
            resource_id
        )

        member_cohorts_excluding_all_member_cohort, all_member_cohort = ResourceHelper.get_member_cohorts(
            community_id,
            member_id
        )

        access_type = ResourceHelper.compute_access_type_for_resource(
            access_type_to_cohort_mapper,
            member_cohorts_excluding_all_member_cohort,
            all_member_cohort
        )

        if not access_type:
            access_type = RESOURCE_ACCESS_TYPE.NO_ACCESS

        return access_type

    @staticmethod
    def create_access_type_to_cohort_mapper(resource_type, resource_id):
        """
        creates a dict for cohorts against their respective access_type
        """
        access_type_to_cohort_mapper = {
            RESOURCE_ACCESS_TYPE.FULL_ACCESS: [],
            RESOURCE_ACCESS_TYPE.RESTRICTED_ACCESS: [],
            RESOURCE_ACCESS_TYPE.NO_ACCESS: []
        }

        resource_filter = ModelUtilities.get_model_filter(
            RESOURCE_TYPE_TO_MODEL_MAPPER[resource_type]['model'],
            {
                RESOURCE_TYPE_TO_MODEL_MAPPER[resource_type]['field']: resource_id
            }
        ).select_related('cohort_id')

        for resource in resource_filter:
            if resource.access_type == RESOURCE_ACCESS_TYPE.FULL_ACCESS:
                access_type_to_cohort_mapper[RESOURCE_ACCESS_TYPE.FULL_ACCESS].append(resource.cohort_id.id)

            elif resource.access_type == RESOURCE_ACCESS_TYPE.RESTRICTED_ACCESS:
                access_type_to_cohort_mapper[RESOURCE_ACCESS_TYPE.RESTRICTED_ACCESS].append(resource.cohort_id.id)

            else:
                access_type_to_cohort_mapper[RESOURCE_ACCESS_TYPE.NO_ACCESS].append(resource.cohort_id.id)

        return access_type_to_cohort_mapper

    @staticmethod
    def get_member_cohorts(community_id, member_id):
        """
        returns member's cohorts list

        Args:
            community_id (int)
            member_id (int)
        Returns:
            member_cohorts (List)
            all_member_cohort (int)
        """
        member_cohorts = []
        all_member_cohort = None

        member_cohort_dict = CohortHelper.precompute_cohorts_of_members(community_id=community_id,
                                                                        member_ids=[member_id])

        for obj in member_cohort_dict:

            if obj.get('cohort').get('type') == 3:
                all_member_cohort = obj.get('cohort').get('id')
                continue

            member_cohorts.append(obj.get('cohort').get('id'))

        return member_cohorts, all_member_cohort

    @staticmethod
    def compute_access_type_for_resource(access_type_to_cohort_mapper,
                                         member_cohorts_excluding_all_member_cohort,
                                         all_member_cohort):
        """
        returns access_type for resource after applying logic

        Args:
            access_type_to_cohort_mapper (dict)
            member_cohorts (list)
            all_member_cohort (int)
        Returns:
            access_type (int)
        """
        if not member_cohorts_excluding_all_member_cohort:

            for access_type in sorted(access_type_to_cohort_mapper):

                if all_member_cohort in access_type_to_cohort_mapper[access_type]:

                    return access_type

        return ResourceHelper.find_access_type_for_resource_when_member_cohort_is_null(
            access_type_to_cohort_mapper,
            member_cohorts_excluding_all_member_cohort
        )

    @staticmethod
    def find_access_type_for_resource_when_member_cohort_is_null(access_type_to_cohort_mapper,
                                                                 member_cohorts_excluding_all_member_cohort):
        """
        returns accesss_type for any resource
        """
        for access_type in sorted(access_type_to_cohort_mapper):

            if any(cohort in access_type_to_cohort_mapper[access_type]
                    for cohort in member_cohorts_excluding_all_member_cohort):

                return access_type

    @staticmethod
    def fetch_distinct_community_ids_having_resources():
        """
        returns community ids list for which resources have been
        added
        """
        community_ids = list(ModelUtilities.get_model_filter(
            ResourceCategory,
            {}
        ).values_list(
            'community_id',
            flat=True
        ).distinct())

        return community_ids

    @staticmethod
    def fetch_resource_references_created_in_last_n_day(community_id,
                                                        time):
        """
        returns referencs created from yesterday 8pm till now
        """
        references = ResourceReference.objects.filter(
            category_id__community_id__id=community_id,
            created_at__gte=time,
            child_category_id__isnull=True
        )

        return references

    @staticmethod
    def fetch_community_settings_for_scheduling_weekly_email():
        """
        returns list of community ids for which email is
        supposed to be scheduled the next day this
        function is being called
        """
        day_of_week_next_day = (TimeUtilities.get_current_day_of_the_week() + 1) % 7

        community_settings = ModelUtilities.get_model_filter(
            ResourceSettings,
            {
                'day_of_weekly_email': day_of_week_next_day
            }
        ).values(
            'community_id',
            'time_of_weekly_email'
        )

        return community_settings

    @staticmethod
    def fetch_url_and_file_instances_from_references(references):
        """
        pass
        """
        url_ids = references.filter(
            url_id__isnull=False
        ).values_list(
            'url_id',
            flat=True
        )

        url_instances = ModelUtilities.get_model_filter(
            ResourceURL,
            {
                'id__in': url_ids
            }
        ).select_related('category_id')

        file_ids = references.filter(
            file_id__isnull=False
        ).values_list(
            'file_id',
            flat=True
        )

        file_instances = ModelUtilities.get_model_filter(
            ResourceFile,
            {
                'id__in': file_ids
            }
        ).select_related('category_id')

        return url_instances, file_instances

    @staticmethod
    @shared_task
    def trigger_event_analytics_on_category_creation(user_id, community_id, level=0):
        """
        Category creation event analytics
        """
        event_name = RESOURCE_CATEGORY_CREATION_EVENT

        community = ModelUtilities.get_model_instance_or_none(
            Community,
            community_id
        )

        community_name = community.name if community else ""

        event_dict = {
            'community_id': community_id,
            'community_name': community_name,
            'level': level
        }

        SegmentImpl.track_event(
            user_id,
            event_name,
            event_dict
        )

    @staticmethod
    @shared_task
    def trigger_event_analytics_on_category_view_updation(user_id, community_id, view_type):
        """
        Category's view_type updation event analytics
        """
        event_name = RESOURCE_CATEGORY_VIEW_TYPE_UPDATION_EVENT

        community = ModelUtilities.get_model_instance_or_none(
            Community,
            community_id
        )

        community_name = community.name if community else ""

        event_dict = {
            'community_id': community_id,
            'community_name': community_name,
        }

        event_dict['view_type'] = 'grid_view' if view_type == 1 else 'list_view'

        SegmentImpl.track_event(
            user_id,
            event_name,
            event_dict
        )

    @staticmethod
    @shared_task
    def trigger_event_analytics_on_resource_permission_updation(user_id,
                                                                community_id,
                                                                resource_type,
                                                                permission_obj,
                                                                is_downloadable):
        """
        Resource's permissions updation event analytics
        """
        event_name = RESOURCE_PERMISSION_UPDATION_EVENT

        community = ModelUtilities.get_model_instance_or_none(
            Community,
            community_id
        )

        community_name = community.name if community else ""

        element_type = RESOURCE_CATEGORY_ELEMENT if resource_type == RESOURCE_TYPE.CATEGORY \
            else RESOURCE_ELEMENT

        access_type_list = []

        for obj in permission_obj:
            if obj.get('access_type') == RESOURCE_ACCESS_TYPE.FULL_ACCESS:
                access_type_list.append('full_access')

            elif obj.get('access_type') == RESOURCE_ACCESS_TYPE.RESTRICTED_ACCESS:
                access_type_list.append('restricted_access')

            elif obj.get('access_type') == RESOURCE_ACCESS_TYPE.NO_ACCESS:
                access_type_list.append('no_access')

        event_dict = {
            'community_id': community_id,
            'community_name': community_name,
            'element_type': element_type,
            'is_downloadable': is_downloadable,
            'access_type': access_type_list
        }

        SegmentImpl.track_event(
            user_id,
            event_name,
            event_dict
        )

    @staticmethod
    @shared_task
    def trigger_event_analytics_on_resource_updation(user_id,
                                                    community_id,
                                                    resource_type,
                                                    title,
                                                    banner):
        """
        Resource's permissions updation event analytics
        """
        event_name = RESOURCE_CATEGORY_EDITED_EVENT \
            if resource_type == RESOURCE_TYPE.CATEGORY \
            else RESOURCE_EDITED_EVENT

        community = ModelUtilities.get_model_instance_or_none(
            Community,
            community_id
        )

        community_name = community.name if community else ""

        has_title = True if title else False

        if resource_type == RESOURCE_TYPE.FILE:

            try:
                meta = json.loads(banner)
                has_banner = True if meta.get('banner') else False

            except:
                has_banner = False

        else:
            has_banner = True if banner else False

        event_dict = {
            'community_id': community_id,
            'community_name': community_name,
            'has_title': has_title,
            'has_banner': has_banner,
        }

        SegmentImpl.track_event(
            user_id,
            event_name,
            event_dict
        )

    @staticmethod
    @shared_task
    def trigger_event_analytics_on_adding_resource(user_id, community_id,
                                                resource_type, level=None):
        """
        Resource addition event analytics
        """
        event_name = RESOURCE_ADDED_EVENT

        community = ModelUtilities.get_model_instance_or_none(
            Community,
            community_id
        )

        community_name = community.name if community else ""

        event_dict = {
            'community_id': community_id,
            'community_name': community_name,
            'resource_type': resource_type,
            'level': level,
        }

        SegmentImpl.track_event(
            user_id,
            event_name,
            event_dict
        )

    @staticmethod
    @shared_task
    def trigger_event_analytics_on_deleting_resource(user_id, community_id):
        """
        Resource deletion event analytics
        """
        event_name = RESOURCE_DELETED_EVENT

        community = ModelUtilities.get_model_instance_or_none(
            Community,
            community_id
        )

        community_name = community.name if community else ""

        event_dict = {
            'community_id': community_id,
            'community_name': community_name,
        }

        SegmentImpl.track_event(
            user_id,
            event_name,
            event_dict
        )
