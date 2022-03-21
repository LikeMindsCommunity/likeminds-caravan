import json
from celery import shared_task
from utility.states import member_states

from togther.models import ModelUtilities, Community, User, Members, Cohort
from collabmates_api.rest_api import get_error_context

from .models import *
from .constants import *
from .serializers import *
from .resources_manager import ResourceManager

from internal_services.url_tags.uri_tags_impl import UriTagsImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.time_utilities import TimeUtilities

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

    def update_community_id(self, community_id):
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
            community_id (int)
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

            self.update_community_id(
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

            self.update_community_id(
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

            self.update_community_id(
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

            self.update_community_id(
                child_category_instance.community_id.id
            )

            res['child_category_id'] = child_category_instance

        return res

    def update_resource_settings(self, req_body):
        """
        updating resource settings

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
        Returns:
            response (dict)
        TODO:
            1. To add analytics
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

            ResourcesImpl.create_category_permission_for_cohorts.delay(
                self.get_community_id(),
                serializer.data.get('id')
            )

            if req_body.get('parent_category_id'):

                reference_dict = {
                    'category_id': serializer.data.get('parent_category_id'),
                    'child_category_id': serializer.data.get('id')
                }

                ResourcesImpl.create_resource_reference_internally.delay(
                    reference_dict,
                    self.get_member_id()
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

    def fetch_resource_category(self, page):
        """
        to fetch resource category

        Args:
            page (int) - page number of the paginated response
        Returns:
            response (dict)
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
        Returns:
            response (dict)
        TODO:
            1. To add analytics
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

            if req_body.get('category_permission'):
                ResourcesImpl.update_category_permission_for_cohorts.delay(
                    req_body.get('id'),
                    req_body.get('category_permission', [])
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
                pass

            try:
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
            except Exception as e:
                error_logger.error("Exception occurred while updation/creation of ResourceCategoryPermission - %s" % e.args)
                pass

    def delete_resource_category(self, req_body):
        """
        to delete resource category

        Args:
            req_body (dict) - request body
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
        Returns:
            response (dict)
        TODO:
            1. To add analytics
        """
        resource_category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            req_body.get('category_id')
        )

        if not resource_category_instance:
            return get_error_context(False, 'incorrect category_id')

        self.update_community_id(resource_category_instance.community_id.id)

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

    def update_resource_url(self, req_body):
        """
        to update resource url

        Args:
            req_body (dict) - request body
        Returns:
            response (dict)
        TODO:
            1. To add analytics
        """
        resource_url_instance = ModelUtilities.get_model_instance_or_none(
            ResourceURL,
            req_body.get('id')
        )

        if not resource_url_instance:
            return get_error_context(False, 'incorrect id')

        self.update_community_id(
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
                pass

            try:
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

    def delete_resource_url(self, req_body):
        """
        to delete resource url

        Args:
            req_body (dict) - request body
        Returns:
            response (dict)
        TODO:
            1. To trigger analytics
        """
        resource_url_instance = ModelUtilities.get_model_instance_or_none(
            ResourceURL,
            req_body.get('id')
        )

        if not resource_url_instance:
            return get_error_context(False, 'incorrect id')

        self.update_community_id(
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
        Returns:
            response (dict)
        TODO:
            1. To add analytics
        """
        resource_category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            req_body.get('category_id')
        )

        if not resource_category_instance:
            return get_error_context(False, 'incorrect category_id')

        self.update_community_id(resource_category_instance.community_id.id)

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

    def update_resource_file(self, req_body):
        """
        to update resource file

        Args:
            req_body (dict) - request body
        Returns:
            response (dict)
        TODO:
            1. To add analytics
        """
        resource_file_instance = ModelUtilities.get_model_instance_or_none(
            ResourceFile,
            req_body.get('id')
        )

        if not resource_file_instance:
            return get_error_context(False, 'incorrect id')

        self.update_community_id(
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
                pass

            try:
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
        Returns:
            response (dict)
        TODO:
            1. To trigger analytics
            2. To delete references
        """
        resource_file_instance = ModelUtilities.get_model_instance_or_none(
            ResourceFile,
            req_body.get('id')
        )

        if not resource_file_instance:
            return get_error_context(False, 'incorrect id')

        self.update_community_id(
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
        Returns:
            response (dict)
        """
        resource_category_instance = ModelUtilities.get_model_instance_or_none(
            ResourceCategory,
            req_body.get('category_id')
        )

        if not resource_category_instance:
            return get_error_context(False, 'incorrect category_id')

        self.update_community_id(resource_category_instance.community_id.id)

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

        final_instances = instances | ResourcesImpl.get_resource_references_to_delete_recursively(sub_reference_intances)

        info_logger.info('deleted resource reference instances - %s' % final_instances)

        return final_instances

    def fetch_resource_reference(self, page):
        """
        to fetch resource references

        Args:
            req_body (dict) - request body
        Returns:
            response (dict)
        TODO:
            To complete
        """
        pass


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
