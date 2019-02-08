from django.contrib.auth.models import User, Group
from rest_framework import serializers
from togther.models import *


class CommunitySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Community
        fields = ('id','name', 'purpose', 'image_url' ,'about', 'location', 'members_count')

