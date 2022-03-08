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
