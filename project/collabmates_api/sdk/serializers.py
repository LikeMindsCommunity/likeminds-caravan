from rest_framework import serializers
from .models import SdkClient, SdkOnboardingScreen
from ..rest_api import CommunitySerializerV1


class SdkProjectSerializer(serializers.ModelSerializer):

    community = CommunitySerializerV1(read_only=True)

    class Meta:
        model = SdkClient
        fields = ('api_key', 'community', 'firebase_server_key', 'is_join_form_enabled', 
                  'gcp_service_account_file')


class OnboardingScreenSerializer(serializers.ModelSerializer):

    class Meta:
        model = SdkOnboardingScreen
        fields = ('id', 'index', 'image', 'heading', 'text', 'cta_colour', 'cta_text')
