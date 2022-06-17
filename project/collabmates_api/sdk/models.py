from django.db import models
from utility.time_utilities import TimeUtilities
from togther.models import (Community, Userinfo, ModelUtilities)
from django.contrib.auth.models import User


class SdkClient(models.Model):

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    api_key = models.CharField(max_length=64, unique=True, null=True)
    project_creator = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(SdkClient, self).save(*args, **kwargs)


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
