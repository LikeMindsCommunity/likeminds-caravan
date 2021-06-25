import json

from django.db import models
import time
from datetime import datetime
from togther.models import *
from django.contrib.auth.models import User
from utility.time_utilities import TimeUtilities
from django.db.models.query import QuerySet


class NewCommunities(models.Model):
    community_id = models.IntegerField(default=0)

    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        else:
            self.updated_at = time.time()

        if self.updated_at == 0:
            self.updated_at = self.created_at

        super(NewCommunities, self).save(*args, **kwargs)


class PerDayRecordOverview(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    cumulative_communities = models.IntegerField(default=0)
    new_chatrooms = models.IntegerField(default=0)
    new_cm_chatrooms = models.IntegerField(default=0)
    new_intro_rooms = models.IntegerField(default=0)
    new_messages = models.IntegerField(default=0)
    new_intro_room_messages = models.IntegerField(default=0)
    new_intro_poll_messages = models.IntegerField(default=0)
    new_intro_event_messages = models.IntegerField(default=0)
    new_messages_by_cm = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    new_users_cumulative = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    members_added = models.IntegerField(default=0)
    cummulative_members = models.IntegerField(default=0)

    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def get_created_time(self):
        return datetime.fromtimestamp(self.created_at)

    def get_updated_time(self):
        return datetime.fromtimestamp(self.updated_at)

    def chatroom_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return self.new_chatrooms - self.cumulative_communities

    def non_intro_room_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return ("%.2f" % ((self.new_chatrooms - self.new_intro_rooms) / self.cumulative_communities))

    def messages_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return ("%.2f" % (self.new_messages / self.cumulative_communities))

    def non_intro_messages_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return ("%.2f" % ((self.new_messages - self.new_intro_room_messages) / self.cumulative_communities))

    def non_intro_room_message_ratio(self):
        if self.new_messages != 0:
            return ("%.2f" % ((self.new_messages - self.new_intro_room_messages) / self.new_messages))
        else:
            return "-"

    def non_intro_room_message_per_user(self):
        if self.new_messages != 0:
            return ("%.2f" % ((self.new_messages - self.new_intro_room_messages) / self.new_messages))
        else:
            return "-"

    def active_user_percent(self):
        if self.new_users_cumulative == 0:
            return '-'
        else:
            return ("%.2f" % (self.active_users / self.new_users_cumulative))

    def non_intro_message_per_unique_user(self):
        if self.active_users == 0:
            return '-'
        else:
            return ("%.2f" % ((self.new_chatrooms - self.new_intro_rooms) / self.active_users))

    def non_intro_room_per_unique_user(self):
        if self.active_users == 0:
            return '-'
        else:
            return ("%.2f" % ((self.new_chatrooms - self.new_intro_rooms) / self.active_users))

    def chatroom_by_members_only(self):
        return self.new_chatrooms - self.new_intro_rooms - self.new_cm_chatrooms

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()

        # else:
        #     self.updated_at = time.time()
        #
        # if self.updated_at == 0 :
        #     self.updated_at = self.created_at

        super(PerDayRecordOverview, self).save(*args, **kwargs)


class PerWeekRecordOverview(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    cumulative_communities = models.IntegerField(default=0)
    new_chatrooms = models.IntegerField(default=0)
    new_cm_chatrooms = models.IntegerField(default=0)
    new_intro_rooms = models.IntegerField(default=0)
    new_messages = models.IntegerField(default=0)
    new_intro_room_messages = models.IntegerField(default=0)
    new_intro_poll_messages = models.IntegerField(default=0)
    new_intro_event_messages = models.IntegerField(default=0)
    new_messages_by_cm = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    new_users_cumulative = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    members_added = models.IntegerField(default=0)
    cummulative_members = models.IntegerField(default=0)

    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def get_created_time(self):
        return datetime.fromtimestamp(self.created_at)

    def get_updated_time(self):
        return datetime.fromtimestamp(self.updated_at)

    def chatroom_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return self.new_chatrooms - self.cumulative_communities

    def non_intro_room_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return ("%.2f" % ((self.new_chatrooms - self.new_intro_rooms) / self.cumulative_communities))

    def messages_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return ("%.2f" % (self.new_messages / self.cumulative_communities))

    def non_intro_messages_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return ("%.2f" % ((self.new_messages - self.new_intro_room_messages) / self.cumulative_communities))

    def non_intro_room_message_ratio(self):
        if self.new_messages != 0:
            return ("%.2f" % ((self.new_messages - self.new_intro_room_messages) / self.new_messages))
        else:
            return "-"

    def non_intro_room_message_per_user(self):
        if self.new_messages != 0:
            return ("%.2f" % ((self.new_messages - self.new_intro_room_messages) / self.new_messages))
        else:
            return "-"

    def active_user_percent(self):
        if self.new_users_cumulative == 0:
            return '-'
        else:
            return ("%.2f" % (self.active_users / self.new_users_cumulative))

    def non_intro_message_per_unique_user(self):
        if self.active_users == 0:
            return '-'
        else:
            return ("%.2f" % ((self.new_chatrooms - self.new_intro_rooms) / self.active_users))

    def non_intro_room_per_unique_user(self):
        if self.active_users == 0:
            return '-'
        else:
            return ("%.2f" % ((self.new_chatrooms - self.new_intro_rooms) / self.active_users))

    def chatroom_by_members_only(self):
        return self.new_chatrooms - self.new_intro_rooms - self.new_cm_chatrooms

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        # else:
        #     self.updated_at = time.time()
        #
        # if self.updated_at == 0 :
        #     self.updated_at = self.created_at

        super(PerWeekRecordOverview, self).save(*args, **kwargs)


class NewAnswer(models.Model):
    option = models.TextField(null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(communityQuestions, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.option)


class userAcquition(models.Model):
    '''table to save user when it comes to the platform'''

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    landing_type = models.TextField(null=True)
    link_type = models.TextField(null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    utm_source = models.TextField(null=True)
    utm_campaign = models.TextField(null=True)
    utm_medium = models.TextField(null=True)
    shared = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name="shared_by")
    device_id = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)
    platform = models.TextField(null=True)
    chatroom = models.ForeignKey(Collabcard, on_delete=models.CASCADE, null=True)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()

        super(userAcquition, self).save(*args, **kwargs)


class appUninstalls(models.Model):
    """
    to store the number of days for users when the app is uninstalled.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    uninstall_days = models.IntegerField(default=0)


class MessageTemplate(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(MessageTemplate, self).save(*args, **kwargs)


class MarketingBannerQuerySet(QuerySet):

    def update(self, *args, **kwargs):

        updated_at = TimeUtilities.current_time_in_milliseconds()
        kwargs['updated_at'] = updated_at

        return super(MarketingBannerQuerySet, self).update(*args, **kwargs)


class MarketingBanner(models.Model):

    objects = MarketingBannerQuerySet.as_manager()

    icon = models.TextField(null=True)
    heading = models.TextField(null=True)
    description = models.TextField(null=True)
    cta = models.TextField(null=True)
    cta_route = models.TextField(null=True)

    overlap_id = models.IntegerField(null=True)

    platform = models.TextField(null=True)
    user_ids = models.TextField(null=True)
    community_ids = models.TextField(null=True)

    min_app_version_an = models.IntegerField(default=0)
    min_app_version_ios = models.IntegerField(default=0)

    hide_time = models.BigIntegerField(default=0, null=True)
    start_epoch_time = models.BigIntegerField(default=0, null=True)
    end_epoch_time = models.BigIntegerField(default=0, null=True)
    created_at = models.BigIntegerField(default=0, null=True)
    updated_at = models.BigIntegerField(default=0, null=True)

    def save(self, *args, **kwargs):

        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(MarketingBanner, self).save(*args, **kwargs)


class Subscription(models.Model):

    member = models.ForeignKey(Members, on_delete=models.CASCADE)
    start_date = models.BigIntegerField(default=0)
    end_date = models.BigIntegerField(default=0)
    plan = models.TextField(null=True)
    active = models.BooleanField(default=False)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(Subscription, self).save(*args, **kwargs)


class LMOptions(models.Model):
    slug = models.TextField(unique=True)
    value = models.TextField()
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(LMOptions, self).save(*args, **kwargs)

    def get_value(self):
        try:
            return json.loads(self.value)
        except:
            return self.value

    @staticmethod
    def get_object_or_raise_exception(slug):
        try:
            return LMOptions.objects.get(slug=slug)
        except:
            response = {
                "success": False,
                "error_message": f"Option doest not exist with the given slug = {slug}"
            }
            raise CustomException(response)

    @staticmethod
    def update_or_create_option(slug, value):
        if not value:
            return

        slug = slug.strip()
        value = json.dumps(value)

        create_dict = {
            'value': value,
            "created_at": TimeUtilities.current_time_in_sec(),
            "updated_at": TimeUtilities.current_time_in_sec()
        }

        obj, created = LMOptions.objects.get_or_create(slug=slug, defaults=create_dict)

        if not created:
            obj.value = value
            obj.save()

