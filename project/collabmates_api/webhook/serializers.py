from rest_framework import serializers
from .models import CommunityWebhook


class WebhookSerializer(serializers.ModelSerializer):

    class Meta:
        model = CommunityWebhook
        fields = ('id', 'community_id', 'url', 'webhook_type', 'created_at', 'updated_at')
