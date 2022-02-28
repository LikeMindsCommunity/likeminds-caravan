from rest_framework import serializers
from .models import CommunityWebhook


class WebhookSerializer(serializers.ModelSerializer):

    class Meta:
        model = CommunityWebhook
        fields = '__all__'
