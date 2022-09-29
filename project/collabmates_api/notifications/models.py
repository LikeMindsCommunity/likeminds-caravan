from django.db import models
from django.contrib.auth.models import User
from utility.time_utilities import TimeUtilities


class WhatsappSubscription(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscribed = models.BooleanField(default=True)
    event_registration_whatsapp = models.IntegerField(default=0)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(WhatsappSubscription, self).save(*args, **kwargs)
