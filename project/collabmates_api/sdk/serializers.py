from rest_framework import serializers
from .models import SdkClient
from ..rest_api import CommunitySerializerV1


class SdkProjectSerializer(serializers.ModelSerializer):

    community = CommunitySerializerV1(read_only=True)

    class Meta:
        model = SdkClient
        fields = ('api_key', 'community', 'firebase_server_key')
