from django.db import models
from utility.time_utilities import TimeUtilities
from utility.states import WebhookTypes
from togther.models import Community


class CommunityWebhook(models.Model):

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    url = models.TextField()
    webhook_type = models.CharField(max_length=30, choices=[(webhook_type.value, webhook_type) for webhook_type in WebhookTypes])
    is_active = models.BooleanField(default=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(CommunityWebhook, self).save(*args, **kwargs)
