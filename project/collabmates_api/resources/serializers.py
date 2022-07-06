import json

from rest_framework import serializers

from togther.models import ModelUtilities
from .models import *
from .constants import *

class ResourceSettingsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceSettings
        fields = '__all__'


class ResourceCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceCategory
        fields = '__all__'

    def validate_parent_category_id(self, parent_category_instance):
        """
        Check that parent_category_id instance is not deleted
        """
        if parent_category_instance.is_deleted:
            raise serializers.ValidationError("Parent Category does not exist. Please enter a valid parent_category_id")

        return parent_category_instance


class ResourceCategoryPermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceCategoryPermission
        fields = '__all__'

    def fetch_access_type(self, instance):
        from .resources_impl import ResourceHelper

        access_type = ResourceHelper.fetch_access_type_for_resource(
            resource_type=RESOURCE_TYPE.CATEGORY,
            resource_id=instance.category_id.id,
            community_id=self.context.get("community_id"),
            member_id=self.context.get("member_id"),
        )

        return access_type

    def to_representation(self, instance):
        data = super(ResourceCategoryPermissionSerializer, self).to_representation(instance)

        data['access_type'] = self.fetch_access_type(instance)

        return data


class ResourceURLSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceURL
        fields = '__all__'

    def validate_category_id(self, category_instance):
        """
        Check that category_id instance is not deleted
        """
        if category_instance.is_deleted:
            raise serializers.ValidationError("Category does not exist. Please enter a valid category_id")

        return category_instance

    def to_representation(self, instance):
        data = super(ResourceURLSerializer, self).to_representation(instance)

        data['og_tags'] = json.loads(instance.og_tags)
        return data


class ResourceURLPermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceURLPermission
        fields = '__all__'

    def fetch_access_type(self, instance):
        from .resources_impl import ResourceHelper

        access_type = ResourceHelper.fetch_access_type_for_resource(
            resource_type=RESOURCE_TYPE.URL,
            resource_id=instance.url_id.id,
            community_id=self.context.get("community_id"),
            member_id=self.context.get("member_id"),
        )

        return access_type

    def to_representation(self, instance):
        data = super(ResourceURLPermissionSerializer, self).to_representation(instance)

        data['access_type'] = self.fetch_access_type(instance)

        return data


class ResourceURLStateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceURLState
        fields = '__all__'


class ResourceFileSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceFile
        fields = '__all__'

    def validate_category_id(self, category_instance):
        """
        Check that category_id instance is not deleted
        """
        if category_instance.is_deleted:
            raise serializers.ValidationError("Category does not exist. Please enter a valid category_id")

        return category_instance


class ResourceFilePermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceFilePermission
        fields = '__all__'

    def fetch_access_type(self, instance):
        from .resources_impl import ResourceHelper

        access_type = ResourceHelper.fetch_access_type_for_resource(
            resource_type=RESOURCE_TYPE.FILE,
            resource_id=instance.file_id.id,
            community_id=self.context.get("community_id"),
            member_id=self.context.get("member_id"),
        )

        return access_type

    def to_representation(self, instance):
        data = super(ResourceFilePermissionSerializer, self).to_representation(instance)

        data['access_type'] = self.fetch_access_type(instance)

        return data


class ResourceFileStateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceFileState
        fields = '__all__'


class ResourceReferenceSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceReference
        fields = '__all__'

    def validate_category_id(self, category_instance):
        """
        Check that category_id instance is not deleted
        """
        if category_instance.is_deleted:
            raise serializers.ValidationError("Category does not exist. Please enter a valid category_id")

        return category_instance

    def validate_file_id(self, file_instance):
        """
        Check that file_id instance is not deleted
        """
        if file_instance.is_deleted:
            raise serializers.ValidationError("File does not exist. Please enter a valid file_id")

        return file_instance

    def validate_url_id(self, url_instance):
        """
        Check that url_id instance is not deleted
        """
        if url_instance.is_deleted:
            raise serializers.ValidationError("URL does not exist. Please enter a valid url_id")

        return url_instance

    def validate_child_category_id(self, category_instance):
        """
        Check that child_category_id instance is not deleted
        """
        if category_instance.is_deleted:
            raise serializers.ValidationError("Child Category does not exist. Please enter a valid child_category_id")

        return category_instance


class ChildCategoryURLStateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceURLState
        fields = '__all__'

    def fetch_category_id(self, instance):
        return instance.url_id.category_id.id

    def to_representation(self, instance):
        data = super(ChildCategoryURLStateSerializer, self).to_representation(instance)

        data['category_id'] = self.fetch_category_id(instance)

        return data


class ChildCategoryFileStateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceFileState
        fields = '__all__'

    def fetch_category_id(self, instance):
        return instance.file_id.category_id.id

    def to_representation(self, instance):
        data = super(ChildCategoryFileStateSerializer, self).to_representation(instance)

        data['category_id'] = self.fetch_category_id(instance)

        return data
