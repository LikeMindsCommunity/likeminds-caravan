from django.db import models
from django.contrib.auth.models import User

response_choices = (
    ('text','Text'),
    ('text_area','Text_area'),
    ('pdf','PDF'),
)

class Community (models.Model):
    name = models.CharField(max_length = 200)
    about = models.TextField()
    location = models.CharField(max_length = 200)
    image_url = models.ImageField(upload_to="media/")
    members_count = models.IntegerField(default = 0)
    active_since = models.DateField(auto_now_add = True)
    whatsapp_group_link = models.CharField(max_length = 400, null=True)

    def __str__(self):
        return self.name

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

class Form_data (models.Model):
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)
    data = models.CharField(max_length = 400)
    data_type = models.CharField(max_length = 20, choices = response_choices, default = 'text') 

class Form_response (models.Model):
    data_id = models.ForeignKey(Form_data,on_delete=models.CASCADE)
    response = models.TextField()

class Userinfo (models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length = 200)
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
    from_year = models.DateField(null = True)
    to_year = models.DateField(null = True)
    description = models.TextField(null = True)
    

class Education (models.Model):
    user_id = models.ForeignKey(Userinfo, default= 6, on_delete= models.CASCADE)
    instituion = models.CharField(max_length = 200, null= True)
    degree = models.CharField(max_length = 200, null= True)
    field_of_study = models.CharField(max_length = 200, null= True)
    from_year = models.DateField(null = True)
    to_year = models.DateField(null = True)
    description = models.TextField(null = True)
    

