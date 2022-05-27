from django.db import models
from utility.time_utilities import TimeUtilities
from togther.models import (Community, ModelUtilities)


class SdkClient(models.Model):

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    api_key = models.CharField(max_length=64, unique=True, null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(SdkClient, self).save(*args, **kwargs)

    @staticmethod
    def get_community_instance_or_none(pk):
        instance = None

        if not pk:
            return instance

        if str(pk).isdigit():
            column_name = "id"
            model = Community
        else:
            column_name = "api_key"
            model = SdkClient

        instance_filter = ModelUtilities.get_model_filter(model, {column_name: pk})

        if instance_filter:
            instance = instance_filter[0]

            if column_name == "api_key":
                instance = instance.community

        return instance


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
