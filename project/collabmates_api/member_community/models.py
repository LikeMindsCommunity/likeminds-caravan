from django.db import models
from django.contrib.auth.models import User
from utility.time_utilities import TimeUtilities
from togther.models import Community


class ConnectionRequest(models.Model):

    request_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="connection_request_by")
    request_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="connection_request_to")
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)
#
    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(ConnectionRequest, self).save(*args, **kwargs)


class Connection(models.Model):

    connection_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="connection_user_1")
    connection_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name="connection_user_2")
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(Connection, self).save(*args, **kwargs)
