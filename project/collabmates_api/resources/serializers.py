import json

from rest_framework import serializers

from .models import *

class ResourceSettingsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceSettings
        fields = '__all__'

class ResourceCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceCategory
        fields = '__all__'

class ResourceCategoryPermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceCategoryPermission
        fields = '__all__'

    def get_access_type(self, instance):
        """
        TODO:
            1. Update logic for fetching access_type
        """
        return instance.access_type

    def to_representation(self, instance):
        data = super(ResourceCategoryPermissionSerializer).to_representation(instance)

        data['access_type'] = self.get_access_type()

        return data

class ResourceURLSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceURL
        fields = '__all__'

    def to_representation(self, instance):
        data = super(ResourceURLSerializer, self).to_representation(instance)

        data['og_tags'] = json.loads(instance.og_tags)
        return data

class ResourceURLPermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceURLPermission
        fields = '__all__'

class ResourceURLStateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceURLState
        fields = '__all__'

class ResourceFileSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceFile
        fields = '__all__'

class ResourceFilePermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceFilePermission
        fields = '__all__'

class ResourceFileStateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceFileState
        fields = '__all__'

class ResourceReferenceSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceReference
        fields = '__all__'
