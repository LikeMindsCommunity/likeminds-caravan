from rest_framework import serializers
from .models import CommunityWebhook


class WebhookSerializer(serializers.ModelSerializer):

    class Meta:
        model = CommunityWebhook
        fields = ('id', 'community', 'url', 'webhook_type', 'is_active', 'created_at')
