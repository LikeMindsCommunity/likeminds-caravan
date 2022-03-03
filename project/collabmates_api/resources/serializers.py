from rest_framework import serializers

from .models import ResourceSettings

class ResourceSettingsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceSettings
        fields = '__all__'
