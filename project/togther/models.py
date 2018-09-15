from django.db import models

# Create your models here.
class User (models.Model):
    email_id = models.EmailField()
    fb_token = models.TextField()
    linkdin_token = models.TextField()

class Userinfo (models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length = 200)
    city = models.CharField(max_length = 100)
    college = models.CharField(max_length = 200)
    contact_number = models.CharField(max_length = 200)
    experience = models.CharField(max_length = 200)
    gender = models.IntegerField()
    image_url = models.CharField(max_length = 200)
    interests = models.CharField(max_length = 200)

class Community (models.Model):
    name = models.CharField(max_length = 200)
    about = models.TextField()
    location = models.CharField(max_length = 200)
    image_url = models.CharField(max_length = 200)
    members_count = models.IntegerField(default = 0)
    active_since = models.DateField()

class Members (models.Model):
    member_id = models.ForeignKey(User, on_delete=models.CASCADE)
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)

class Admins (models.Model):
    admin_id = models.ForeignKey(User, on_delete=models.CASCADE)
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)

class Requests (models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)
    status = models.IntegerField(default = 0)

class Category (models.Model):
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)
    category = models.CharField(max_length = 200)