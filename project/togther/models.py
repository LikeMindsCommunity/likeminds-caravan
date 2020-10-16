from django.db import models
from django.contrib.auth.models import User
import time
from django.db.models.query import QuerySet

response_choices = (
    ('text', 'Text'),
    ('textarea', 'Textarea'),
    ('pdf', 'PDF'),
)

card_action = (
    ('like', 'Like'),
    ('share', 'Share'),
)


class Community(models.Model):
    name = models.CharField(max_length=200)
    about = models.TextField(null=True)
    purpose = models.CharField(max_length=2048)
    location = models.CharField(max_length=200, null=True)
    image_url = models.ImageField(upload_to="media/community", null=True)
    members_count = models.IntegerField(default=0)
    active_since = models.DateField(auto_now_add=True)
    whatsapp_group_link = models.CharField(max_length=400, null=True)
    created_at = models.BigIntegerField(default=-9223372036854775808)
    updated_at = models.BigIntegerField(default=-9223372036854775808)
    purpose_collabcard = models.IntegerField(null=True)
    hide_community = models.CharField(default=0, max_length=1)
    introduction_text = models.CharField(max_length=2048, null=True)
    image_link = models.CharField(max_length=500, null=True)
    thumbnail = models.CharField(max_length=500, null=True)
    introduction_text_state = models.IntegerField(default=0)
    attribute_type = models.IntegerField(default=0)
    # for  purpose collabcard image
    image_link_round = models.TextField(null=True)

    # for whats app community
    type = models.IntegerField(null=True)
    sub_type = models.IntegerField(null=True)

    def __str__(self):
        return self.name


class communityToast(models.Model):
    '''table to save the toast messages of community'''

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    created_at = models.BigIntegerField(default=0)
    toast_message = models.TextField(null=True)


class Members(models.Model):
    member_id = models.ForeignKey(User, on_delete=models.CASCADE)
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    state = models.IntegerField(null=True)
    created_at = models.BigIntegerField(default=-9223372036854775808)
    tool_state = models.IntegerField(default=0)

    updated_at = models.BigIntegerField(default=0)

    # columns for referal in LG communities
    ask_member_id = models.IntegerField(null=True)
    approved_member_id = models.IntegerField(null=True)

    # columns for edit member profile required
    edit_required = models.BooleanField(default=False)

    # column to edit actions required
    actions_required = models.BooleanField(null=True)

    image_url = models.TextField(null=True)

    is_owner = models.BooleanField(default=False)
    custom_title = models.TextField(null=True)
    joined_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="joined_by_user")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="approved_by_user")
    parent_cm = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="parent_cm_user")
    parent_cm_list = models.TextField(null=True)  # it has the user id's of parent's hierarchy

    def __str__(self):
        return self.member_id.userinfo.name + "__" + self.community_id.name

    # def save(self, *args, **kwargs):
    #     if self.created_at <= 0:
    #         self.created_at = time.time()
    #     super(Members, self).save(*args, **kwargs)


class removedMembers(models.Model):
    '''model for saving removed or members who left the community details'''

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    removed_state = models.IntegerField(default=0)
    created_at = models.BigIntegerField(default=0, null=True)


class Userinfo(models.Model):
    user_id = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    city = models.CharField(max_length=100, null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    address = models.CharField(max_length=1024, null=True)
    headline = models.CharField(max_length=200, null=True)
    contact_number = models.BigIntegerField(null=True, default=0)
    gender = models.IntegerField(null=True)
    image_url = models.CharField(max_length=500, null=True)
    image_file = models.ImageField(upload_to='media/profile_pics/', null=True)
    interests = models.CharField(max_length=400, null=True)
    about = models.CharField(max_length=400, null=True)
    fb_link = models.CharField(max_length=400, null=True)
    linkedin_link = models.CharField(max_length=400, null=True)
    fcm_token = models.CharField(max_length=1024, null=True)
    login_type = models.CharField(max_length=50, null=True)
    login_json = models.TextField(null=True)
    secondary_email = models.CharField(max_length=200, null=True)
    mobile_os = models.CharField(max_length=200, null=True)
    created_at = models.BigIntegerField(default=-9223372036854775808)
    version_code = models.IntegerField(null=True, default=21)
    image_link = models.CharField(max_length=500, null=True)
    apple_id = models.CharField(max_length=100, null=True)
    has_tags = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# Collabcard Report Module
class Report_Tags(models.Model):
    ''' Table containing the report tags '''

    tag_name = models.CharField(max_length=512)
    tag_id = models.IntegerField(null=True)
    type = models.IntegerField(default=0)



class Collabcard(models.Model):
    title = models.TextField()
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    likes_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    answers_count = models.IntegerField(default=0)
    date_epoch = models.BigIntegerField(default=-9223372036854775808)
    answer_text = models.CharField(max_length=100, default='')
    share_link = models.CharField(max_length=2048, default='')
    og_tags = models.CharField(max_length=2048, default='')
    image_count = models.IntegerField(default=0, null=True)
    pdf_count = models.IntegerField(default=0, null=True)
    type = models.IntegerField(default=0)  # state=0 (Normal Collabcard);state=1(Introduction Collabcard)
    date_time = models.BigIntegerField(default=0)  # for saving date of event and due date for polling
    duration = models.BigIntegerField(default=0)  # for saving duration of event

    # for polls count
    polls_count = models.IntegerField(default=0)
    attending_count = models.IntegerField(default=0)

    # for event cards
    location = models.TextField(null=True)
    location_lat = models.FloatField(null=True)
    location_long = models.FloatField(null=True)
    start_date = models.BigIntegerField(default=0, null=True)
    end_date = models.BigIntegerField(default=0, null=True)
    about = models.TextField(null=True)
    co_hosts = models.TextField(null=True)
    online_link = models.TextField(null=True)

    # for purpose card edit
    updated_member = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='purpose_card_updater')
    updated_time = models.BigIntegerField(default=0)

    # for poll functionality
    multiple_select = models.BooleanField(default=False)
    multiple_select_no = models.IntegerField(null=True)
    multiple_select_state = models.IntegerField(null=True)

    poll_type = models.IntegerField(default=0, null=True)
    is_poll_anonymous = models.BooleanField(default=False, null=True)
    allow_add_option = models.BooleanField(default=False, null=True)

    # for saving chatroom name
    header = models.TextField(null=True)
    has_been_named = models.BooleanField(default=True)  # for notification access
    internal_link = models.TextField(null=True)
    preview_type = models.TextField(null=True)
    preview_community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True,
                                          related_name='chatroom_preview_community')
    preview_chatroom = models.ForeignKey('self', on_delete=models.PROTECT, null=True,
                                         related_name='chatroom_preview_chatroom')
    is_pending = models.BooleanField(default=False)  # for pending chat rooms which has to be approved
    is_deleted = models.BooleanField(default=False)
    deleted_by_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True,
                                        related_name='chatroom_deleted_by_user')
    deleted_by_user_state = models.IntegerField(null=True)  # state in community member or manager
    deleted_by_text = models.CharField(max_length=512, null=True)
    reason = models.CharField(max_length=512, null=True)
    tag = models.ForeignKey(Report_Tags, on_delete=models.CASCADE, null=True)

class draftChatroom(models.Model):
    title = models.TextField()
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    answer_text = models.CharField(max_length=100, default='')
    share_link = models.CharField(max_length=2048, default='')
    og_tags = models.CharField(max_length=2048, default='')
    image_count = models.IntegerField(default=0, null=True)
    pdf_count = models.IntegerField(default=0, null=True)
    type = models.IntegerField(default=0)  # state=0 (Normal Collabcard);state=1(Introduction Collabcard)
    date_time = models.BigIntegerField(default=0)  # for saving date of event and due date for polling
    duration = models.BigIntegerField(default=0)  # for saving duration of event
    date_epoch = models.BigIntegerField(default=0)
    # for polls count
    polls_count = models.IntegerField(default=0)
    attending_count = models.IntegerField(default=0)

    # for event cards
    location = models.TextField(null=True)
    location_lat = models.FloatField(null=True)
    location_long = models.FloatField(null=True)
    start_date = models.BigIntegerField(default=0, null=True)
    end_date = models.BigIntegerField(default=0, null=True)
    about = models.TextField(null=True)
    co_hosts = models.TextField(null=True)
    online_link = models.TextField(null=True)

    # for poll functionality
    multiple_select = models.BooleanField(default=False)
    multiple_select_no = models.IntegerField(null=True)
    multiple_select_state = models.IntegerField(null=True)

    poll_type = models.IntegerField(default=0, null=True)
    is_poll_anonymous = models.BooleanField(default=False, null=True)
    allow_add_option = models.BooleanField(default=False, null=True)

    # for saving chatroom name
    header = models.TextField(null=True)

    internal_link = models.TextField(null=True)
    preview_type = models.TextField(null=True)
    preview_community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True,
                                          related_name='draft_chatroom_preview_community')
    preview_chatroom = models.ForeignKey(Collabcard, on_delete=models.PROTECT, null=True,
                                         related_name='draft_chatroom_preview_chatroom')


class inActiveChatroomsCount(models.Model):
    '''models to save the count of in-active chatrooms for user'''
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # last_inactive_card = models.ForeignKey(Collabcard, on_delete=models.CASCADE,null=True)
    inactive_count = models.IntegerField(default=0)
    created_at = models.BigIntegerField(null=True)
    updated_at = models.BigIntegerField(null=True)


class deletedChatrooms(models.Model):
    title = models.TextField()
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    answer_text = models.CharField(max_length=100, default='')
    share_link = models.CharField(max_length=2048, default='')
    og_tags = models.CharField(max_length=2048, default='')
    image_count = models.IntegerField(default=0, null=True)
    pdf_count = models.IntegerField(default=0, null=True)
    type = models.IntegerField(default=0)  # state=0 (Normal Collabcard);state=1(Introduction Collabcard)
    date_time = models.BigIntegerField(default=0)  # for saving date of event and due date for polling
    duration = models.BigIntegerField(default=0)  # for saving duration of event
    date_epoch = models.BigIntegerField(default=0)
    # for polls count
    polls_count = models.IntegerField(default=0)
    attending_count = models.IntegerField(default=0)

    # for event cards
    location = models.TextField(null=True)
    location_lat = models.FloatField(null=True)
    location_long = models.FloatField(null=True)
    start_date = models.BigIntegerField(default=0)
    end_date = models.BigIntegerField(default=0)
    about = models.TextField(null=True)
    co_hosts = models.TextField(null=True)
    online_link = models.TextField(null=True)

    # for poll functionality
    multiple_select = models.BooleanField(default=False)
    multiple_select_no = models.IntegerField(null=True)
    multiple_select_state = models.IntegerField(null=True)

    poll_type = models.IntegerField(default=0, null=True)
    is_poll_anonymous = models.BooleanField(default=False, null=True)
    allow_add_option = models.BooleanField(default=False, null=True)
    # saving deleted user details
    deleted_by_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='deleted_by_user')
    deleted_by_text = models.CharField(max_length=512, null=True)
    deleted_by_creator = models.BooleanField(default=False, null=True)
    deleted_by_promoter = models.BooleanField(default=False, null=True)
    reason = models.CharField(max_length=512, null=True)
    tag = models.ForeignKey(Report_Tags, on_delete=models.CASCADE, null=True)

    header = models.TextField(null=True)
    card_id = models.IntegerField(null=True)


class card_answers(models.Model):
    answer = models.TextField()
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=-9223372036854775808)
    state = models.IntegerField(default=0)
    remove = models.ForeignKey(removedMembers, on_delete=models.CASCADE, null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    is_guest = models.BooleanField(default=False)
    og_tags = models.TextField(null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_by_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True,
                                        related_name='conversation_deleted_by_user')
    deleted_by_user_state = models.IntegerField(default=0)  # state in community member or manager
    is_edited = models.BooleanField(default=False)
    reply = models.ForeignKey('self', on_delete=models.PROTECT, null=True, related_name='replied_conversation')
    internal_link = models.TextField(null=True)
    preview_type = models.TextField(null=True)
    preview_community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True,
                                          related_name='conversation_preview_community')
    preview_chatroom = models.ForeignKey(Collabcard, on_delete=models.PROTECT, null=True,
                                         related_name='conversation_preview_chatroom')

    has_files = models.BooleanField(default=False)



class collabcardState(models.Model):
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.IntegerField(null=True)
    created_at = models.BigIntegerField(default=-9223372036854775808, null=True)
    updated_at = models.BigIntegerField(default=-9223372036854775808, null=True)

    # if got removed saving the previous state
    remove = models.ForeignKey(removedMembers, on_delete=models.CASCADE, null=True)


    mute_status = models.BooleanField(default=False)
    follow_status = models.BooleanField(default=False)
    is_guest = models.BooleanField(default=False)
    is_tagged = models.BooleanField(default=False)
    source = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='referrer')

    expiry_time = models.BigIntegerField(null=True)

    external_seen = models.BooleanField(default=True)
    external_follow = models.BooleanField(default=False)

    class Meta:
        unique_together = (('card', 'user'),)





class conversationMemberState(models.Model):
    '''function to save member state of conversation'''
    conversation = models.ForeignKey(card_answers, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()

        if self.updated_at == 0:
            self.updated_at = self.created_at

        super(conversationMemberState, self).save(*args, **kwargs)


class conversationEngage(models.Model):
    '''model to map to conversation engage screen'''

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE, null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    last_conversation = models.ForeignKey(card_answers, on_delete=models.CASCADE, null=True)
    second_last_conversation = models.ForeignKey(card_answers, on_delete=models.CASCADE, null=True,
                                                 related_name='second_last_conversation')
    unseen_count = models.IntegerField(default=0)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    draft = models.ForeignKey(draftChatroom, on_delete=models.CASCADE, null=True)
    last_conversation_member = models.ForeignKey(Members, on_delete=models.SET_NULL, null=True,related_name='last_conversation_member')
    second_last_conversation_member = models.ForeignKey(Members, on_delete=models.SET_NULL, null=True,related_name='second_last_conversation_member')

    last_conversation_user = models.ForeignKey(collabcardState, on_delete=models.SET_NULL, null=True,
                                               related_name='last_conversation_user')
    second_last_conversation_user = models.ForeignKey(collabcardState, on_delete=models.SET_NULL, null=True,
                                                      related_name='second_last_conversation_user')

    rights_list = models.TextField(null=True)

class temp_admin(models.Model):
    name = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=200, null=True)
    email = models.CharField(max_length=200, null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    member_id = models.IntegerField(default=0)
    # member_id = models.ForeignKey(User, on_delete = models.CASCADE)


class Card_Attachment(models.Model):
    '''model to save files of collabcard'''

    collabcard = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    attachment = models.FileField(upload_to="media/collabcard_files", default='')
    file_url = models.CharField(max_length=500, null=True)
    type = models.CharField(max_length=50, default='')


class draftChatroomFiles(models.Model):
    '''model to save files of collabcard'''

    draft = models.ForeignKey(draftChatroom, on_delete=models.CASCADE)

    file_url = models.TextField(null=True)
    type = models.CharField(max_length=50, default='')

    created_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        super(draftChatroomFiles, self).save(*args, **kwargs)


class answerAttachment(models.Model):
    '''model to save files of collabcard'''

    answer = models.ForeignKey(card_answers, on_delete=models.CASCADE)

    file_url = models.TextField(null=True)
    type = models.CharField(max_length=50, default='')

    location_name = models.TextField(null=True)
    location_lat = models.FloatField(null=True)
    location_long = models.FloatField(null=True)

    created_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        super(answerAttachment, self).save(*args, **kwargs)


class get_notified(models.Model):
    email = models.EmailField()


class User_LPIG(models.Model):
    ''' Model to store user LPIG tags '''
    member_id = models.OneToOneField(User, on_delete=models.CASCADE)
    legacy = models.CharField(max_length=1024, null=True)
    profession = models.CharField(max_length=1024, null=True)
    interests = models.CharField(max_length=1024, null=True)
    geography = models.CharField(max_length=1024, null=True)

    def __str__(self):
        return str(self.member_id.id)


class Community_LPIG(models.Model):
    ''' Model to store community LPIG tags '''
    community_id = models.OneToOneField(Community, on_delete=models.CASCADE)
    legacy = models.CharField(max_length=1024, null=True)
    profession = models.CharField(max_length=1024, null=True)
    interests = models.CharField(max_length=1024, null=True)
    geography = models.CharField(max_length=1024, null=True)

    def __str__(self):
        return self.community_id.name


class Community_Rank(models.Model):
    ''' Model for giving community rank acrroding to user relevance '''
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    member_id = models.ForeignKey(User, on_delete=models.CASCADE)
    weight = models.IntegerField(null=True)


class Category(models.Model):
    '''Model to store the categories '''
    name = models.CharField(max_length=512, null=True, unique=True)

    def __str__(self):
        return self.name


class Attributes(models.Model):
    '''Model to store the attributes of category'''

    attribute_name = models.CharField(max_length=512, null=True, unique=True)
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE)

    def __str__(self):
        return self.attribute_name


class Tags_lpig(models.Model):
    '''Model to store the lpig tags in attributes'''

    name = models.CharField(max_length=512, null=True)
    attribute_id = models.ForeignKey(Attributes, on_delete=models.CASCADE)
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE)
    tag_id = models.IntegerField(null=True)
    tag_characterstics = models.CharField(max_length=1024, null=True)
    tag_image = models.ImageField(upload_to="media/tags_images", default='')
    is_cluster = models.IntegerField(default=0)
    cluster_tag_id = models.IntegerField(null=True)
    image_link = models.CharField(max_length=500, null=True)
    tag_rank = models.IntegerField(default=0)
    thumbnail = models.CharField(max_length=500, null=True)
    created_at = models.BigIntegerField(default=-9223372036854775808, null=True)
    updated_at = models.BigIntegerField(default=-9223372036854775808, null=True)

    def __str__(self):
        return self.name
    #
    # def save(self, *args, **kwargs):
    #     if self.created_at <= 0:
    #         self.created_at = time.time()
    #     self.updated_at = time.time()
    #     super(Tags_lpig, self).save(*args, **kwargs)


class Member_Engage(models.Model):
    '''Model to store the communities of a particular user'''

    member_id = models.ForeignKey(User, on_delete=models.CASCADE)
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    last_unseen_conversation = models.ForeignKey(Collabcard, on_delete=models.SET_NULL, null=True)
    last_unseen_count = models.IntegerField(default=0, null=True)
    pending_members = models.IntegerField(default=0, null=True)
    updated_at = models.BigIntegerField(default=0, null=True)
    member_referral = models.CharField(default='', max_length=1024)
    member_state = models.IntegerField(null=True)
    click_state = models.IntegerField(default=0)
    new_chatroom_users = models.TextField(null=True)
    rights_list = models.TextField(null=True)

# community lpig

class Community_Legacy(models.Model):
    '''Model to store the communities of legacy'''
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    tags_id = models.ForeignKey(Tags_lpig, on_delete=models.CASCADE)
    correct_tag_id = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.tags_id and not self.correct_tag_id:
            correct_id = self.tags_id.tag_id
            self.correct_tag_id = correct_id
            self.save()

        super(Community_Legacy, self).save(*args, **kwargs)


class Community_Profession(models.Model):
    '''Model to store the communities of profession'''
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    tags_id = models.ForeignKey(Tags_lpig, on_delete=models.CASCADE)
    correct_tag_id = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.tags_id and not self.correct_tag_id:
            correct_id = self.tags_id.tag_id
            self.correct_tag_id = correct_id
            self.save()

        super(Community_Profession, self).save(*args, **kwargs)


class Community_Interest(models.Model):
    '''Model to store the communities of interest'''
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    tags_id = models.ForeignKey(Tags_lpig, on_delete=models.CASCADE)
    correct_tag_id = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.tags_id and not self.correct_tag_id:
            correct_id = self.tags_id.tag_id
            self.correct_tag_id = correct_id
            self.save()

        super(Community_Interest, self).save(*args, **kwargs)


class Community_Geography(models.Model):
    '''Model to store the communities of geography'''
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    tags_id = models.ForeignKey(Tags_lpig, on_delete=models.CASCADE)
    correct_tag_id = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.tags_id and not self.correct_tag_id:
            correct_id = self.tags_id.tag_id
            self.correct_tag_id = correct_id
            self.save()

        super(Community_Geography, self).save(*args, **kwargs)


# user lpig

class User_Legacy(models.Model):
    '''Model to store the user of legacy'''
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    tags_id = models.ForeignKey(Tags_lpig, on_delete=models.CASCADE)
    correct_tag_id = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.tags_id and not self.correct_tag_id:
            correct_id = self.tags_id.tag_id
            self.correct_tag_id = correct_id
            self.save()

        super(User_Legacy, self).save(*args, **kwargs)


class User_Profession(models.Model):
    '''Model to store the user of profession'''
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    tags_id = models.ForeignKey(Tags_lpig, on_delete=models.CASCADE)
    correct_tag_id = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.tags_id and not self.correct_tag_id:
            correct_id = self.tags_id.tag_id
            self.correct_tag_id = correct_id
            self.save()

        super(User_Profession, self).save(*args, **kwargs)


class User_Interest(models.Model):
    '''Model to store the user of interest'''
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    tags_id = models.ForeignKey(Tags_lpig, on_delete=models.CASCADE)
    correct_tag_id = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.tags_id and not self.correct_tag_id:
            correct_id = self.tags_id.tag_id
            self.correct_tag_id = correct_id
            self.save()

        super(User_Interest, self).save(*args, **kwargs)


class User_Geography(models.Model):
    '''Model to store the user of geography'''
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    tags_id = models.ForeignKey(Tags_lpig, on_delete=models.CASCADE)
    correct_tag_id = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.tags_id and not self.correct_tag_id:
            correct_id = self.tags_id.tag_id
            self.correct_tag_id = correct_id
            self.save()

        super(User_Geography, self).save(*args, **kwargs)


class Referal(models.Model):
    """ Model for reference module """
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='member')
    invited_member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invited_member')
    community = models.ForeignKey(Community, on_delete=models.CASCADE)


class Location_Info(models.Model):
    """ saving location details of a geography tag """

    # tag = models.ForeignKey(Tags_lpig, on_delete=models.PROTECT)
    tag_name = models.CharField(max_length=512, null=True, unique=True)
    city = models.CharField(max_length=512, null=True, default='')
    district = models.CharField(max_length=512, null=True, default='')
    state = models.CharField(max_length=512, null=True, default='')
    country = models.CharField(max_length=512, null=True, default='')
    pincode = models.CharField(max_length=512, null=True, default='')

    def __str__(self):
        return self.tag_name


class App_Update_Info(models.Model):
    """Table containing all app update Informations for android"""

    version_code = models.IntegerField(null=True)
    android_route = models.CharField(max_length=2048, null=True)
    created_at = models.BigIntegerField(default=-9223372036854775808, null=True)

    # def save(self, *args, **kwargs):
    #     if self.created_at <= 0:
    #         self.created_at = time.time()
    #     super(App_Update_Info, self).save(*args, **kwargs)


class Report(models.Model):
    '''Table containing the report data of user'''
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    collabcard = models.ForeignKey(Collabcard, on_delete=models.CASCADE, null=True)
    conversation = models.ForeignKey(card_answers, on_delete=models.CASCADE, null=True)

    reported_member_id = models.IntegerField(null=True)  # can be removed
    member = models.ForeignKey(User, on_delete=models.CASCADE, null=True)  # can be removed

    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_by_user', null=True)
    user_reported = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_who_is_reported', null=True)
    reason = models.CharField(max_length=2048, null=True)
    tag = models.ForeignKey(Report_Tags, on_delete=models.CASCADE, null=True)
    type = models.IntegerField(null=True)
    action_taken_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='action_taken_by_promoter', null=True)
    action_taken_reason = models.CharField(max_length=2048, null=True)
    action_taken_tag = models.ForeignKey(Report_Tags, on_delete=models.CASCADE, related_name='action_taken_tag', null=True)
    rights_added = models.TextField(null=True)
    rights_removed = models.TextField(null=True)
    action_taken = models.IntegerField(null=True)
    is_closed = models.BooleanField(default=False)
    closed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_closed_by_user', null=True)
    closed_time = models.BigIntegerField(default=0, null=True)
    date_epoch = models.BigIntegerField(default=-9223372036854775808, null=True)

    link = models.TextField(null=True)






class CollabcardStateBackup(models.Model):
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE, null=True)
    deleted_card = models.ForeignKey(deletedChatrooms, on_delete=models.CASCADE, null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.IntegerField(null=True)
    created_at = models.BigIntegerField(default=0, null=True)
    updated_at = models.BigIntegerField(default=0, null=True)
    seen_status = models.BooleanField(default=False)
    remove = models.ForeignKey(removedMembers, on_delete=models.CASCADE, null=True)
    mute_status = models.BooleanField(default=False)
    follow_status = models.BooleanField(default=False)
    is_guest = models.BooleanField(default=False)
    source = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='referrer_backup')

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        self.updated_at = time.time()
        super(CollabcardStateBackup, self).save(*args, **kwargs)


class CollabcardPolls(models.Model):
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    text = models.CharField(max_length=2048, null=True)
    created_at = models.BigIntegerField(default=0, null=True)
    updated_at = models.BigIntegerField(default=0, null=True)
    sub_text = models.TextField(null=True)
    image_url = models.TextField(null=True)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        self.updated_at = time.time()
        super(CollabcardPolls, self).save(*args, **kwargs)

    def get_card_polls(self, card_id):
        pass


class draftPolls(models.Model):
    draft = models.ForeignKey(draftChatroom, on_delete=models.CASCADE)
    text = models.CharField(max_length=2048, null=True)
    sub_text = models.TextField(null=True)
    image_url = models.TextField(null=True)


class MemberPollVotes(models.Model):
    poll = models.ForeignKey(CollabcardPolls, on_delete=models.CASCADE)
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0, null=True)
    updated_at = models.BigIntegerField(default=0, null=True)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        self.updated_at = time.time()
        super(MemberPollVotes, self).save(*args, **kwargs)


class collabcardTemp(models.Model):
    '''model to save the data for new collabcard created by user'''

    title = models.TextField()
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collabcardTemp_member')
    created_at = models.BigIntegerField(default=0, null=True)
    show_member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='show_member_id')
    state = models.IntegerField(default=0)


class communityQuestions(models.Model):
    '''model to save community questions'''

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    question_title = models.TextField(null=True)
    question_state = models.IntegerField(default=0)
    value = models.TextField(null=True)
    dropdown_selection_limit = models.IntegerField(null=True)
    optional = models.BooleanField(default=False)
    help_text = models.TextField(null=True)

    # when the promoter deletes a question from v1/edit_questions api
    remove_state = models.BooleanField(default=False)

    is_hidden = models.BooleanField(default=False)

    field = models.BooleanField(default=False)

    rank = models.IntegerField(default=0)

    def __str__(self):
        return str(self.question_title)


class communityAnswers(models.Model):
    '''model to save answers of a user in community'''

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    question_title = models.TextField(null=True)
    question_answer = models.TextField()
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(communityQuestions, on_delete=models.CASCADE)


# master questions flow

class communityType(models.Model):
    '''model  to save type of community'''

    typ = models.TextField(null=True)
    next_input_title = models.TextField(null=True)

    def __str__(self):
        return self.typ


class communitySubtype(models.Model):
    '''model to save subtype of community'''
    sub_typ = models.TextField(null=True)
    typ = models.ForeignKey(communityType, on_delete=models.CASCADE)

    def __str__(self):
        return self.sub_typ


class masterQuestions(models.Model):
    '''model to save the master questions of community'''

    typ = models.ForeignKey(communityType, on_delete=models.CASCADE)
    sub_type = models.ForeignKey(communitySubtype, on_delete=models.CASCADE)
    question_title = models.TextField(null=True)
    value = models.TextField(null=True)
    help_text = models.TextField(null=True)
    state = models.IntegerField(default=0)


# saving the community duration
class communityExpire(models.Model):
    '''community to save duration of community when it got expired'''

    duration = models.BigIntegerField(default=0)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)


class questionFilters(models.Model):
    '''model to save questions filters'''
    question = models.ForeignKey(communityQuestions, on_delete=models.CASCADE)
    filter = models.TextField(null=True)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0, null=True)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        super(questionFilters, self).save(*args, **kwargs)


class communityExpiryCodes(models.Model):
    '''model to generate private links of community'''

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    promoter = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0, null=True)
    unique_code = models.IntegerField(default=0)
    private_link = models.CharField(max_length=2048, null=True)
    expire_duration = models.BigIntegerField(default=0, null=True)


class chatroomExpiryCodes(models.Model):
    '''api to generate private links for chatrooms'''

    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    source = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    unique_code = models.IntegerField(default=0)
    private_link = models.CharField(max_length=2048, null=True)
    expire_duration = models.BigIntegerField(default=0, null=True)


class createCommunityAction(models.Model):
    '''model to save create community actions'''

    step_no = models.TextField(null=True)
    step_title = models.TextField(null=True)
    max_point = models.IntegerField(null=True)
    current_point = models.IntegerField(null=True)
    step_subtitle = models.TextField(null=True)
    step_action = models.TextField(null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    current_point_value = models.IntegerField(default=0)


class communityLevels(models.Model):
    '''model to save the levels of the community'''

    level = models.TextField(null=True)
    title = models.TextField(null=True)
    sub_title = models.TextField(null=True)
    action = models.TextField(null=True)
    joined_members = models.IntegerField(null=True)
    max_members = models.IntegerField(null=True)
    state = models.IntegerField(default=0)
    image = models.TextField(null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)

    level_click_state = models.IntegerField(default=0)


class communityUpdate(models.Model):
    '''table to set updating details for user and community'''
    updated_member = models.ForeignKey(User, on_delete=models.CASCADE)
    updated_field = models.TextField(null=True)
    updated_time = models.BigIntegerField(default=0)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)


class emailTokens(models.Model):
    '''function to generate email tokens for syncing new email ids'''

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.TextField(null=True)
    token = models.IntegerField(null=True)
    expire_time = models.BigIntegerField(default=0)
    created_at = models.BigIntegerField(default=0, null=True)
    # verification_link = models.TextField(null=True)
    email_state = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        super(emailTokens, self).save(*args, **kwargs)


class userEmails(models.Model):
    '''function to save user emails and mobile number for communication and email sync'''

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.TextField(null=True)
    email_state = models.IntegerField(default=0)
    created_at = models.BigIntegerField(default=0)

    verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        super(userEmails, self).save(*args, **kwargs)


class userMobiles(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    country_code = models.IntegerField(null=True)
    mobile_no = models.BigIntegerField(null=True)
    state = models.IntegerField(default=0)

    created_at = models.BigIntegerField(default=0)


class mobileBackup(models.Model):
    country_code = models.IntegerField(null=True)
    mobile_no = models.BigIntegerField(null=True)
    created_at = models.BigIntegerField(default=0)


class membersEngagePilot(models.Model):
    '''models to save member engage pilot for backuping pilot community users'''

    member = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    last_unseen_conversation = models.ForeignKey(Collabcard, on_delete=models.SET_NULL, null=True)
    last_unseen_count = models.IntegerField(default=0, null=True)
    pending_members = models.IntegerField(default=0, null=True)
    updated_at = models.BigIntegerField(default=0, null=True)
    member_referral = models.CharField(default='', max_length=1024)
    member_state = models.IntegerField(null=True)


class membersPilot(models.Model):
    '''model to create members pilot for backuping pilot community users'''

    member_id = models.ForeignKey(User, on_delete=models.CASCADE)
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    state = models.IntegerField(null=True)
    created_at = models.BigIntegerField(default=0)
    tool_state = models.IntegerField(default=0)

    # columns for referal in LG communities
    ask_member_id = models.IntegerField(null=True)
    approved_member_id = models.IntegerField(null=True)

    # columns for edit member profile required
    edit_required = models.BooleanField(default=False)

    # column to edit actions required
    actions_required = models.BooleanField(null=True)


class communityFieldTypes(models.Model):
    type = models.TextField(null=True)
    sub_type_header = models.TextField(null=True)
    sub_type_placeholder = models.TextField(null=True)

    rank = models.IntegerField(default=0)

    created_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        super(communityFieldTypes, self).save(*args, **kwargs)

    def __str__(self):
        return self.type

    class Meta:
        ordering = ["type"]


class communityFieldSubTypes(models.Model):
    type = models.ForeignKey(communityFieldTypes, on_delete=models.CASCADE)
    sub_type = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)

    rank = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        super(communityFieldSubTypes, self).save(*args, **kwargs)

    def __str__(self):
        return self.sub_type


    class Meta:
        ordering = ["sub_type"]



class communityField(models.Model):
    type = models.ForeignKey(communityFieldTypes, on_delete=models.CASCADE)
    sub_type = models.ForeignKey(communityFieldSubTypes, on_delete=models.CASCADE)

    question_title = models.TextField(null=True)
    state = models.IntegerField(default=0)
    value = models.TextField(null=True)
    optional = models.BooleanField(default=False)
    help_text = models.TextField(null=True)
    field = models.BooleanField(default=False)
    created_at = models.BigIntegerField(default=0)

    is_compulsory = models.BooleanField(default=False)
    rank = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        super(communityField, self).save(*args, **kwargs)


class memberNotificationFlag(models.Model):
    '''
    Model to store the flag state to send emails/push notifications of a particular user
    Code for mails with start with 'mail_'
    Code for notification with start with 'push_'
    '''

    member = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True)
    card = models.ForeignKey(Collabcard, on_delete=models.SET_NULL, null=True)
    code = models.CharField(default='', max_length=100)
    flag = models.BooleanField(default=True)
    updated_at = models.BigIntegerField(default=0, null=True)
    created_at = models.BigIntegerField(default=0, null=True)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = time.time()
        super(memberNotificationFlag, self).save(*args, **kwargs)


class userPopupTime(models.Model):
    '''api to make user pop up time for getting phonebook permissions'''

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    popup_type = models.TextField(null=True)
    trigger_time = models.BigIntegerField(null=True)
    ignore = models.BooleanField(default=False)
    count = models.IntegerField(default=0)

    created_at = models.BigIntegerField(null=True)


class userPhonebook(models.Model):
    '''api to make user phonebook'''

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    phonebook = models.TextField(null=True)
    created_at = models.BigIntegerField(null=True)
    updated_at = models.BigIntegerField(null=True)


class userFeedback(models.Model):
    '''api to make save user feedback'''

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(null=True)
    images = models.TextField(null=True)
    feedback = models.TextField(null=True)



class adminRights(models.Model):
    title = models.TextField(null=True)
    sub_title = models.TextField(null=True)
    state = models.IntegerField(default=0)


class memberRights(models.Model):
    title = models.TextField(null=True)
    sub_title = models.TextField(null=True)
    state = models.IntegerField(default=0)


class userAdminRights(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    right = models.ForeignKey(adminRights, on_delete=models.CASCADE)
    # right_given_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='right_given_by_user')
    class Meta:
        unique_together = (('user', 'community', 'right'),)

class userMemberRights(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    right = models.ForeignKey(memberRights, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('user', 'community', 'right'),)

class moderationHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    type = models.IntegerField(null=True)
    moderation_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moderation_by_user')
    moderation_time = models.BigIntegerField(default=0)

    def __str__(self):
        return self.user.userinfo.name + "__" + self.community_id.name

    def save(self, *args, **kwargs):
        if self.moderation_time <= 0:
            self.moderation_time = time.time()
        super(moderationHistory, self).save(*args, **kwargs)


class communityRightsSettings(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    right = models.ForeignKey(memberRights, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('community', 'right'),)


class blockedMembers(models.Model):
    blocked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by_user')
    blocked_member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_who_is_blocked')
    community = models.ForeignKey(Community, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('blocked_by', 'blocked_member', 'community'),)



class userDevices(models.Model):

    '''class to store the devices of user when the user installs the app'''

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    fcm_token = models.TextField(null=True)
    mobile_os = models.TextField(null=True)

    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.created_at <= 0:
            self.created_at = time.time()
        super(userDevices, self).save(*args, **kwargs)


