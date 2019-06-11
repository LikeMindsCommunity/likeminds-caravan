from django.db import models
from django.contrib.auth.models import User
import datetime

response_choices = (
    ('text','Text'),
    ('textarea','Textarea'),
    ('pdf','PDF'),
)

card_action = (
    ('like','Like'),
    ('share','Share'),
)

class Community (models.Model):
    name = models.CharField(max_length = 200)
    about = models.TextField()
    purpose = models.CharField(max_length= 300)
    location = models.CharField(max_length = 200)
    image_url = models.ImageField(upload_to="media/", default = 'https://upload.wikimedia.org/wikipedia/en/0/09/Community_title.jpg')
    members_count = models.IntegerField(default = 0)
    active_since = models.DateField(auto_now_add = True)
    whatsapp_group_link = models.CharField(max_length = 400, null=True)

    def __str__(self):
        return self.name

class Members (models.Model):
    member_id = models.ForeignKey(User, on_delete=models.CASCADE)
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)

    def __str__(self):
        return self.community_id.name

class Admins (models.Model):
    admin_id = models.ForeignKey(User, on_delete=models.CASCADE)
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)

    def __str__(self):
        return self.community_id.name

class Category (models.Model):
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)
    category = models.CharField(max_length = 200)

    def __str__(self):
        return self.category

class Form_data (models.Model):
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)
    data = models.CharField(max_length = 400)
    data_type = models.CharField(max_length = 20, choices = response_choices, default = 'text')

    def __str__(self):
        return self.community_id.name

class Userinfo (models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length = 200)
    email = models.CharField(max_length = 200)
    city = models.CharField(max_length = 100, null = True)
    headline = models.CharField(max_length = 200, null= True)
    contact_number = models.CharField(max_length = 200,null = True)
    gender = models.IntegerField(null = True)
    image_url = models.CharField(max_length = 500, null = True)
    interests = models.CharField(max_length = 400,null = True)
    about = models.CharField(max_length = 400, null = True)
    fb_link = models.CharField(max_length = 400, null = True)
    linkedin_link = models.CharField(max_length = 400, null = True)
    headline = models.CharField(max_length = 100, null = True) 
    
    def __str__(self):
        return self.name

class Experience (models.Model):
    user_id = models.ForeignKey(Userinfo,default =6 ,on_delete= models.CASCADE)
    title = models.CharField(max_length = 200, null= True)
    company = models.CharField(max_length = 200, null = True)
    location = models.CharField(max_length = 200, null=True)
    from_year = models.CharField(max_length = 4,null = True)
    to_year = models.CharField(max_length = 4,null = True)
    description = models.TextField(null = True)
    

class Education (models.Model):
    user_id = models.ForeignKey(Userinfo, default= 6, on_delete= models.CASCADE)
    instituion = models.CharField(max_length = 200, null= True)
    degree = models.CharField(max_length = 200, null= True)
    field_of_study = models.CharField(max_length = 200, null= True)
    from_year = models.CharField(max_length = 4,null = True)
    to_year = models.CharField(max_length = 4,null = True)
    description = models.TextField(null = True)

class Requests (models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    user_info = models.ForeignKey(Userinfo, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    status = models.IntegerField(default = 0)

class Form_response (models.Model):
    data = models.TextField()
    user = models.IntegerField()
    community = models.IntegerField()
    response = models.TextField()
    
class Collabcard (models.Model):
    title = models.TextField()
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    likes_count =  models.IntegerField(default = 0)
    share_count =  models.IntegerField(default = 0)
    answers_count = models.IntegerField(default=0)
    date_created = models.DateTimeField(default=now,editable=False)

class Comments (models.Model):
    comment =  models.CharField(max_length = 1000)
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class Cardaction (models.Model):
    action =  models.CharField(max_length=100 ,choices = response_choices)
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    #date = models.DateField(auto_now_add = True)

class card_answers (models.Model):
    answer = models.TextField()
    card = models.ForeignKey(Collabcard, on_delete = models.CASCADE)
    user = models.ForeignKey(User,on_delete = models.CASCADE)

class temp_admin (models.Model):
    name = models.CharField(max_length = 200)
    contact_number = models.CharField(max_length = 200, null=True)
    email = models.CharField(max_length = 200, null = True)
    community = models.ForeignKey(Community, on_delete = models.CASCADE)

class card_images (models.Model):
    collabcard = models.ForeignKey(Collabcard, on_delete = models.CASCADE)
    image_url = models.ImageField(upload_to="media/collabcardImages")

class collabcard_seen(models.Model):
    card = models.ForeignKey(Collabcard, on_delete= models.CASCADE)
    community = models.ForeignKey(Community, on_delete= models.CASCADE)
    user = models.ForeignKey(User, on_delete = models.CASCADE)