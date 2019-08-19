from django.db import models
from django.contrib.auth.models import User
from django.core.files import File
from urllib.request import urlopen
from io import BytesIO


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
    created_at=models.BigIntegerField(default=-9223372036854775808)
    updated_at=models.BigIntegerField(default=-9223372036854775808)
    purpose_collabcard=models.IntegerField(null=True)
    hide_community=models.CharField(default=0,max_length=1)

    def __str__(self):
        return self.name

class Members (models.Model):
    member_id = models.ForeignKey(User, on_delete=models.CASCADE)
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)
    state=models.IntegerField(null=True)
    def __str__(self):
        return self.community_id.name

class Admins (models.Model):
    admin_id = models.ForeignKey(User, on_delete=models.CASCADE)
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)

    def __str__(self):
        return self.community_id.name

class Community_tags (models.Model):
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)
    category = models.CharField(max_length = 200,null=True)
    tags_id=models.IntegerField(default=0,null=True)
    state=models.CharField(max_length=40,null=True)

    def __str__(self):
        return self.category

class Form_data (models.Model):
    community_id = models.ForeignKey(Community, on_delete = models.CASCADE)
    data = models.CharField(max_length = 400)
    data_type = models.CharField(max_length = 20, choices = response_choices, default = 'text')

    def __str__(self):
        return self.community_id.name

class Userinfo (models.Model):
    
    user_id = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length = 200)
    email = models.CharField(max_length = 200)
    city = models.CharField(max_length = 100, null = True)
    latitude = models.FloatField(null = True)
    longitude = models.FloatField(null=True)
    headline = models.CharField(max_length = 200, null= True)
    contact_number = models.CharField(max_length = 200,null = True)
    gender = models.IntegerField(null = True)
    image_url = models.CharField(max_length = 500, null = True)
    image_file = models.ImageField(upload_to='media/profile_pics/',null =True)
    interests = models.CharField(max_length = 400,null = True)
    about = models.CharField(max_length = 400, null = True)
    fb_link = models.CharField(max_length = 400, null = True)
    linkedin_link = models.CharField(max_length = 400, null = True)
    fcm_token=models.CharField(max_length=1024,null=True)
    login_type=models.CharField(max_length=50,null=True)
    login_json=models.TextField(null=True)
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.image_url and not self.image_file:

            response = urlopen(self.image_url)
            img = BytesIO(response.read())
            self.image_file.save("profile_pic_"+self.name+".jpeg", File(img))

        super(Userinfo, self).save(*args, **kwargs)


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
    date_epoch=models.BigIntegerField(default=-9223372036854775808)
    answer_text = models.CharField(max_length = 100, default = '')
    share_link=models.CharField(max_length=2048,default='')
    og_tags=models.CharField(max_length=2048,default='')



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
    date_epoch=models.BigIntegerField(default=-9223372036854775808)


class temp_admin (models.Model):
    name = models.CharField(max_length = 200)
    contact_number = models.CharField(max_length = 200, null=True)
    email = models.CharField(max_length = 200, null = True)
    community = models.ForeignKey(Community, on_delete = models.CASCADE) 
    member_id = models.IntegerField(default=0)
    #member_id = models.ForeignKey(User, on_delete = models.CASCADE)

class Card_Attachment (models.Model):

    '''model to save files of collabcard'''

    collabcard = models.ForeignKey(Collabcard, on_delete = models.CASCADE)
    attachment = models.FileField(upload_to="media/collabcard_files")
    type=models.CharField(max_length=50,default='')

class collabcard_seen(models.Model):
    card = models.ForeignKey(Collabcard, on_delete= models.CASCADE)
    community = models.ForeignKey(Community, on_delete= models.CASCADE)
    user = models.ForeignKey(User, on_delete = models.CASCADE)


class follow_collabcard(models.Model):
    '''Model to store the follow requests of members'''
    collabcard_id=models.ForeignKey(Collabcard,on_delete=models.CASCADE)
    member_id = models.ForeignKey(User, on_delete=models.CASCADE)

class get_notified(models.Model):
    email = models.EmailField()



class Tags(models.Model):

    '''Model to show tags from database'''

    category_id=models.CharField(max_length=10,null=True)
    category_name=models.CharField(max_length=50,unique=True)
    state=models.IntegerField(null=True)
    type=models.CharField(null=True,max_length=100)

class userinfo_tags(models.Model):
    ''' Model to give user hidden tags '''

    tag_id = models.IntegerField(null=True)
    user_id = models.IntegerField(null=True)



class User_LPIG(models.Model):
    ''' Model to store user LPIG tags '''
    member_id = models.OneToOneField(User, on_delete=models.CASCADE)
    legacy = models.CharField(max_length=1024,null=True)
    profession = models.CharField(max_length=1024,null=True)
    interests = models.CharField(max_length=1024,null=True)
    geography = models.CharField(max_length=1024,null=True)

    def __str__(self):
        return self.member_id.name

class Community_LPIG(models.Model):

    ''' Model to store community LPIG tags '''
    community_id = models.OneToOneField(Community, on_delete=models.CASCADE)
    legacy = models.CharField(max_length=1024,null=True)
    profession = models.CharField(max_length=1024,null=True)
    interests = models.CharField(max_length=1024,null=True)
    geography = models.CharField(max_length=1024,null=True)

    def __str__(self):
        return self.community_id.name

class Community_Rank(models.Model):
    ''' Model for giving community rank acrroding to user relevance '''
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    member_id = models.ForeignKey(User, on_delete=models.CASCADE)
    weight = models.IntegerField(null=True)


class Category(models.Model):

    '''Model to store the categories '''
    name=models.CharField(max_length=512,null=True,unique=True)

    def __str__(self):
        return self.name


class Attributes(models.Model):

    '''function to store the attributes of category'''

    attribute_name=models.CharField(max_length=512,null=True,unique=True)
    category_id=models.ForeignKey(Category,on_delete=models.CASCADE)

    def __str__(self):
        return self.attribute_name


class Tags_lpig(models.Model):

    '''function to store the lpig tags in attributes'''

    name = models.CharField(max_length=512, null=True,unique=True)
    attribute_id=models.ForeignKey(Attributes,on_delete=models.CASCADE)
    category_id=models.ForeignKey(Category,on_delete=models.CASCADE)

    def __str__(self):
        return self.name

