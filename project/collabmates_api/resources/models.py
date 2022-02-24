import uuid
from django.db import models

from togther.models import Community


class ResourceSettings(models.Model):
    """ Class for saving Resource Settings for a Community"""

    DAY_OF_WEEKLY_EMAIL_CHOICES = [0, 1, 2, 3, 4, 5, 6]
    TIME_OF_WEEKLY_EMAIL_CHOICES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]

    id = models.CharField(
        max_length=100,
        default=uuid.uuid4(),
        primary_key=True
    )
    community_id = models.ForeignKey(
        Community,
        on_delete=models.PROTECT
    )
    day_of_weekly_email = models.IntegerChoices(
        null=True,
        blank=True,
        choices=DAY_OF_WEEKLY_EMAIL_CHOICES
    )
    time_of_weekly_email = models.IntegerChoices(
        null=True,
        blank=True,
        choices=TIME_OF_WEEKLY_EMAIL_CHOICES
    )

    class Meta:
        verbose_name = 'Resouce Setting'
        verbose_name_plural = 'Resouce Settings'
        db_name = 'resource_settings'

