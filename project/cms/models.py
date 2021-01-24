from django.db import models
import time
from datetime import datetime
from togther.models import *
from django.contrib.auth.models import User

class NewCommunities(models.Model):
    community_id = models.IntegerField(default=0)

    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        else:
            self.updated_at = time.time()

        if self.updated_at == 0 :
            self.updated_at = self.created_at

        super(NewCommunities, self).save(*args, **kwargs)




class PerDayRecordOverview(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE,null=True)
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
            return ("%.2f" %((self.new_chatrooms - self.new_intro_rooms) / self.cumulative_communities))


    def messages_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return ("%.2f" %(self.new_messages / self.cumulative_communities))



    def non_intro_messages_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return ("%.2f" %((self.new_messages - self.new_intro_room_messages) / self.cumulative_communities))


    def non_intro_room_message_ratio(self):
        if self.new_messages !=0:
            return ("%.2f" %((self.new_messages - self.new_intro_room_messages) / self.new_messages))
        else:
            return "-"


    def non_intro_room_message_per_user(self):
        if self.new_messages !=0:
            return ("%.2f" %((self.new_messages - self.new_intro_room_messages) / self.new_messages))
        else:
            return "-"

    def active_user_percent(self):
        if self.new_users_cumulative == 0:
            return '-'
        else:
            return ("%.2f" %(self.active_users / self.new_users_cumulative))


    def non_intro_message_per_unique_user(self):
        if self.active_users == 0:
            return '-'
        else:
            return ("%.2f" %((self.new_chatrooms - self.new_intro_rooms) / self.active_users))


    def non_intro_room_per_unique_user(self):
        if self.active_users == 0:
            return '-'
        else:
            return ("%.2f" %((self.new_chatrooms - self.new_intro_rooms) / self.active_users))

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
    community = models.ForeignKey(Community, on_delete=models.CASCADE,null=True)
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
            return ("%.2f" %((self.new_chatrooms - self.new_intro_rooms) / self.cumulative_communities))


    def messages_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return ("%.2f" %(self.new_messages / self.cumulative_communities))



    def non_intro_messages_per_community(self):
        if self.cumulative_communities == 0:
            return "-"
        else:
            return ("%.2f" %((self.new_messages - self.new_intro_room_messages) / self.cumulative_communities))


    def non_intro_room_message_ratio(self):
        if self.new_messages !=0:
            return ("%.2f" %((self.new_messages - self.new_intro_room_messages) / self.new_messages))
        else:
            return "-"


    def non_intro_room_message_per_user(self):
        if self.new_messages !=0:
            return ("%.2f" %((self.new_messages - self.new_intro_room_messages) / self.new_messages))
        else:
            return "-"

    def active_user_percent(self):
        if self.new_users_cumulative == 0:
            return '-'
        else:
            return ("%.2f" %(self.active_users / self.new_users_cumulative))


    def non_intro_message_per_unique_user(self):
        if self.active_users == 0:
            return '-'
        else:
            return ("%.2f" %((self.new_chatrooms - self.new_intro_rooms) / self.active_users))


    def non_intro_room_per_unique_user(self):
        if self.active_users == 0:
            return '-'
        else:
            return ("%.2f" %((self.new_chatrooms - self.new_intro_rooms) / self.active_users))

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
    community = models.ForeignKey(Community, on_delete=models.CASCADE,null=True)
    utm_source = models.TextField(null=True)
    utm_campaign = models.TextField(null=True)
    utm_medium = models.TextField(null=True)
    shared = models.ForeignKey(User, on_delete=models.CASCADE,null=True,related_name="shared_by")
    device_id = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)
    platform = models.TextField(null=True)

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
        current_time = time.time()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(MessageTemplate, self).save(*args, **kwargs)
