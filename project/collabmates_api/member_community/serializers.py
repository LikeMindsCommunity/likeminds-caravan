from rest_framework import serializers
from .models import Connection, ConnectionRequest


class ConnectionRequestSerializer(serializers.ModelSerializer):
    user1_uuid = serializers.CharField(source='request_by.userinfo.user_unique_id')
    user2_uuid = serializers.CharField(source='request_to.userinfo.user_unique_id')

    class Meta:
        model = ConnectionRequest
        fields = ('user1_uuid', 'user2_uuid', 'created_at', 'updated_at')


class ConnectionSerializer(serializers.ModelSerializer):
    user1_uuid = serializers.CharField(source='connection_by.userinfo.user_unique_id')
    user2_uuid = serializers.CharField(source='connection_with.userinfo.user_unique_id')

    class Meta:
        model = Connection
        fields = ('user1_uuid', 'user2_uuid', 'created_at', 'updated_at')
