from django.db import models
from utility.time_utilities import TimeUtilities
from togther.models import (Community, Userinfo, ModelUtilities)
from django.contrib.auth.models import User


class SdkClient(models.Model):

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    api_key = models.CharField(max_length=64, unique=True, null=True)
    project_creator = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    is_deleted = models.BooleanField(default=False)
    firebase_server_key = models.TextField(null=True)
    is_join_form_enabled = models.BooleanField(default=False)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(SdkClient, self).save(*args, **kwargs)

    @staticmethod
    def get_community_instance_or_none(community_id=None, api_key=None):
        instance = None

        if not (community_id or api_key):
            return instance

        if all([community_id, str(community_id).isdigit()]):
            column_name = "id"
            model = Community
            model_filter = {
                "id": community_id
            }

        elif api_key:
            column_name = "api_key"
            model = SdkClient
            model_filter = {
                "api_key": api_key,
                "is_deleted": False
            }

        else:
            return instance

        instance_filter = ModelUtilities.get_model_filter(model, model_filter)

        if instance_filter:
            instance = instance_filter[0]

            if column_name == "api_key":
                instance = instance.community

        return instance

    @staticmethod
    def is_sdk_community(community_id=None, api_key=None):
        filter_dict = {
            'is_deleted': False
        }

        if community_id:
            filter_dict['community'] = community_id

        if api_key:
            filter_dict['api_key'] = api_key

        return True if ModelUtilities.get_model_filter(SdkClient, filter_dict) else False


class SdkPlatform(models.Model):

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    type = models.IntegerField()
    package = models.CharField(max_length=128, null=True)
    certificate = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(SdkPlatform, self).save(*args, **kwargs)


class SdkOnboardingScreen(models.Model):

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    index = models.PositiveIntegerField()
    image = models.TextField()
    heading = models.TextField(null=True)
    text = models.TextField(null=True)
    cta_colour = models.CharField(max_length=7, null=True)
    cta_text = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(SdkOnboardingScreen, self).save(*args, **kwargs)


class OnboardedVerifiedIUsers(models.Model):
    sdk_client = models.ForeignKey(SdkClient, on_delete=models.CASCADE)
    mobile_no = models.BigIntegerField(null=True)
    country_code = models.IntegerField(null=True)
    email = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_sec()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(OnboardedVerifiedIUsers, self).save(*args, **kwargs)

