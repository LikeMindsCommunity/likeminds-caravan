from rest_framework import serializers
from togther.models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class UserinfoSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Userinfo
        fields = '__all__'

class CommunitySerializer(serializers.ModelSerializer):
    class Meta: 
        model = Community
        fields = '__all__'     

class CategorySerializer(serializers.ModelSerializer):
    class Meta: 
        model = Category
        fields = '__all__'

class MembersSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Members
        field = '__all__'     

class AdminsSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Admins
        field = '__all__' 

class RequestsSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Requests
        field = '__all__'        