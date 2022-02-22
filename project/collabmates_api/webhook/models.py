from django.db import models
from utility.time_utilities import TimeUtilities


class CommunityWebhook(models.Model):

    community_id = models.IntegerField()
    url = models.TextField()
    webhook_type = models.IntegerField()
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(CommunityWebhook, self).save(*args, **kwargs)