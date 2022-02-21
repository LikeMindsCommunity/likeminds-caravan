import json

from django.db import models
from django.contrib.auth.models import User
import time
from django.db.models import Q
from utility.states import member_states, member_rights
from django.db.models.query import QuerySet
from rest_framework import status as status_codes
from utility.exception_utilities import (InvalidCommunityException, InvalidChatroomException,
                                         InvalidUserException, CustomException, InvalidConversationException)
from utility.time_utilities import TimeUtilities
from typing import Union
from external_services.logging.logging_wrapper import LoggingWrapper
from django.core import serializers as core_serializer
from django.utils.translation import gettext_lazy as _

error_logger = LoggingWrapper.get_instance()

response_choices = (
    ('text', 'Text'),
    ('textarea', 'Textarea'),
    ('pdf', 'PDF'),
)

card_action = (
    ('like', 'Like'),
    ('share', 'Share'),
)


def get_user_or_raise_exception(user_id):
    try:
        return User.objects.get(pk=user_id)
    except:
        response = {
            'success': False,
            'error_message': f'User with id {user_id} does not exist :('
        }
        raise InvalidUserException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)


def get_user_or_none(user_id):
    try:
        return User.objects.get(pk=user_id)
    except:
        return None


User.add_to_class("get_user_or_raise_exception", get_user_or_raise_exception)
User.add_to_class("get_user_or_none", get_user_or_none)


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

    is_paid = models.BooleanField(default=False)
    website_url = models.TextField(null=True)
    auto_approval = models.BooleanField(default=True)
    grace_period = models.BigIntegerField(default=0)
    is_discoverable = models.BooleanField(default=False)

    community_category = models.TextField(null=True)
    referral_enabled = models.BooleanField(default=False)

    dashboard_link = models.TextField(null=True)
    brand_color = models.TextField(null=True)
    likeminds_plan = models.TextField(null=True)

    fee_membership = models.IntegerField(default=5)
    fee_event = models.IntegerField(default=5)
    fee_payment_pages = models.IntegerField(default=5)

    def __str__(self):
        return self.name

    # saving the last updated in milliseconds
    def save(self, *args, **kwargs):

        current_time = TimeUtilities.current_time_in_sec()

        if self.created_at < 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(Community, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(community_object):
        community_instance = Community()
        community_instance.name = community_object['name']
        community_instance.members_count = community_object['members_count']
        community_instance.purpose = community_object['purpose']
        community_instance.brand_color = community_object['brand_color']
        community_instance.image_link = community_object['image_link']
        community_instance.thumbnail = community_object['thumbnail']
        community_instance.type = community_object['type']
        community_instance.sub_type = community_object['sub_type']
        community_instance.hide_community = community_object['hide_community']
        community_instance.save()

        return community_instance

    @staticmethod
    def get_community_or_raise_exception(community_id):

        try:
            return Community.objects.get(id=community_id)
        except:
            response = {
                'success': False,
                'error_message': f"community with id {community_id} doesn't exists"
            }
            raise InvalidCommunityException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

    @staticmethod
    def get_community_or_None(community_id):
        try:
            return Community.objects.get(id=community_id)
        except:
            return None


class communityToast(models.Model):
    """table to save the toast messages of community"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    created_at = models.BigIntegerField(default=0)
    toast_message = models.TextField(null=True)

    @staticmethod
    def update_or_create_toast_message(create_info):
        if not create_info.get('message'):
            return

        update_dict = {
            'toast_message': create_info.get('message'),
            "created_at": TimeUtilities.current_time_in_sec()
        }

        instance, created = communityToast.objects.update_or_create(user=create_info.get('user_instance'),
                                                                    community=create_info.get('community_instance'),
                                                                    defaults=update_dict)


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
    became_member_at = models.BigIntegerField(default=0)

    has_onboarded = models.BooleanField(default=False)

    @staticmethod
    def create_instance(create_info):
        member_instance = Members()
        member_instance.member_id = create_info.get('user_instance')
        member_instance.community_id = create_info.get('community_instance')
        member_instance.state = create_info.get('state')
        member_instance.created_at = TimeUtilities.current_time_in_sec()
        member_instance.updated_at = TimeUtilities.current_time_in_sec()
        member_instance.joined_by = create_info.get('joined_by', None)
        member_instance.actions_required = create_info.get('actions_required', None)
        member_instance.is_owner = create_info.get('is_owner', False)
        member_instance.custom_title = create_info.get('custom_title', None)
        member_instance.became_member_at = create_info.get('became_member_at', 0)
        member_instance.save()

        return member_instance

    @staticmethod
    def is_community_member(community: Union[Community, str, int], member: Union[User, str, int]) -> bool:
        return Members.objects.filter(community_id=community,
                                      member_id=member
                                      ).filter(Q(state=member_states.ADMIN) |
                                               Q(state=member_states.MEMBER) |
                                               Q(state=member_states.PROFILE_UNAVAILABLE)).exists()

    @staticmethod
    def is_user_community_member_in_community_list(community_id_list: list, member: Union[User, str, int]) -> bool:
        return Members.objects \
            .filter(community_id__in=community_id_list,
                    member_id=member) \
            .filter(Q(state=member_states.ADMIN) |
                    Q(state=member_states.MEMBER) |
                    Q(state=member_states.PROFILE_UNAVAILABLE)) \
            .exists()

    @staticmethod
    def get_community_member_state(community: Community, member: User) -> int:
        member = Members.objects.filter(community_id=community, member_id=member)

        if member:
            return member[0].state

        return member_states.GUEST

    @staticmethod
    def is_member_community_promoter(community: Community, member: User) -> int:
        member_state = Members.get_community_member_state(community, member)
        return member_state == member_states.ADMIN

    @staticmethod
    def is_member_community_owner(community: Community, member: User) -> int:
        member = Members.objects.filter(community_id=community, member_id=member, is_owner=True)

        return member.exists()

    @staticmethod
    def get_community_owner_user_instance_or_none(community: Community) -> object:
        member = Members.objects.filter(community_id=community, is_owner=True)
        if member:
            return member[0].member_id
        return None

    @staticmethod
    def get_member_instance_or_none(community: Community, member: User) -> object:

        member = Members.objects.filter(community_id=community, member_id=member).prefetch_related('member_id',
                                                                                                   'approved_by')

        if member:
            return member[0]

        return None

    @staticmethod
    def get_managers_list(community: Community) -> list:
        return list(Members.objects.filter(community_id=community, state=member_states.ADMIN)
                    .values_list("member_id__id", flat=True))

    @staticmethod
    def get_pending_members(community: Community) -> list:

        return Members.objects.filter(community_id=community, state=member_states.PENDING_MEMBER)

    @staticmethod
    def get_members_count_in_community(community_instance):

        return Members.objects.filter(community_id=community_instance).filter(
            Q(state=member_states.MEMBER)
            | Q(state=member_states.ADMIN)
            | Q(state=member_states.PROFILE_UNAVAILABLE)
        ).count()

    @staticmethod
    def get_members_of_community(community_instance):

        return Members.objects.filter(community_id=community_instance).filter(
            Q(state=member_states.MEMBER)
            | Q(state=member_states.ADMIN)
            | Q(state=member_states.PROFILE_UNAVAILABLE)
        )

    @staticmethod
    def get_community_managers(community_id_list: list) -> list:
        return Members.objects \
            .filter(community_id__in=community_id_list, state=member_states.ADMIN) \
            .order_by('community_id__id', 'id')

    @staticmethod
    def user_has_app_access(user_id):
        '''function to tell whether the user is a part of any community or nor'''
        states_list = [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]
        members_filter = Members.objects.filter(member_id=user_id, state__in=states_list)

        return members_filter.exists()

    @staticmethod
    def fetch_all_user_communties(user: Union[str, int, User]):
        return Members.objects.filter(member_id=user).select_related('community_id')

    @staticmethod
    def fetch_community_members(community_id_list):
        member_state_list = [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]
        members = Members.objects \
            .filter(community_id__in=community_id_list, state__in=member_state_list) \
            .order_by('community_id', 'id')

        return members

    @staticmethod
    def create_instance_from_expired_member_instace(expired_instance):
        member_instance = Members()
        member_instance.member_id = expired_instance.member
        member_instance.community_id = expired_instance.community
        member_instance.state = expired_instance.state
        member_instance.created_at = expired_instance.created_at
        member_instance.updated_at = expired_instance.updated_at
        member_instance.tool_state = expired_instance.tool_state
        member_instance.ask_member_id = expired_instance.ask_member_id
        member_instance.approved_member_id = expired_instance.approved_member_id
        member_instance.edit_required = expired_instance.edit_required
        member_instance.actions_required = expired_instance.actions_required
        member_instance.image_url = expired_instance.image_url
        member_instance.is_owner = expired_instance.is_owner
        member_instance.custom_title = expired_instance.custom_title
        member_instance.joined_by = expired_instance.joined_by
        member_instance.approved_by = expired_instance.approved_by
        member_instance.parent_cm = expired_instance.parent_cm
        member_instance.parent_cm_list = expired_instance.parent_cm_list
        member_instance.became_member_at = expired_instance.became_member_at
        member_instance.has_onboarded = expired_instance.has_onboarded
        member_instance.save()


class removedMembers(models.Model):
    '''model for saving removed or members who left the community details'''

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    removed_state = models.IntegerField(default=0)
    created_at = models.BigIntegerField(default=0, null=True)

    @staticmethod
    def create_instance(create_info):
        instance = removedMembers()
        instance.community = create_info.get('community_instance')
        instance.member = create_info.get('user_instance')
        instance.removed_state = create_info.get('removed_state')
        instance.created_at = TimeUtilities.current_time_in_sec()
        instance.save()

        return instance


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
    updated_at = models.BigIntegerField(default=0)

    def __str__(self):
        return self.name

    @staticmethod
    def get_userinfo_or_raise_exception(user_id):
        try:
            return Userinfo.objects.get(user_id_id=user_id)
        except:
            response = {
                'success': False,
                'error_message': f'Userinfo for user with id {user_id} does not exist'
            }
            raise CustomException(response)

    @staticmethod
    def get_userinfo_or_None(user_id):
        try:
            return Userinfo.objects.get(user_id_id=user_id)
        except:
            return None

    @staticmethod
    def get_username(user_id):
        try:
            instance = Userinfo.objects.get(user_id_id=user_id)
            return instance.name
        except:
            return None

    def save(self, *args, **kwargs):

        current_time = TimeUtilities.current_time_in_sec()

        if self.created_at < 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(Userinfo, self).save(*args, **kwargs)


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
    og_tags = models.TextField(default='')

    image_count = models.IntegerField(default=0, null=True)
    pdf_count = models.IntegerField(default=0, null=True)
    video_count = models.IntegerField(default=0, null=True)
    audio_count = models.IntegerField(default=0, null=True)
    attachment_count = models.IntegerField(default=0)
    attachments_uploaded = models.BooleanField(default=False, null=True)

    type = models.IntegerField(default=0)  # state=0 (Normal Collabcard);state=1(Introduction Collabcard)
    duration = models.BigIntegerField(default=0)  # for saving duration of event

    # for polls count
    polls_count = models.IntegerField(default=0)
    attending_count = models.IntegerField(default=0)

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
    preview_community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True,
                                          related_name='chatroom_preview_community')
    preview_chatroom = models.ForeignKey('self', on_delete=models.SET_NULL, null=True,
                                         related_name='chatroom_preview_chatroom')
    is_pending = models.BooleanField(default=False)  # for pending chat rooms which has to be approved
    is_deleted = models.BooleanField(default=False)  # for internal check, not to be sent in API's
    deleted_by_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True,
                                        related_name='chatroom_deleted_by_user')
    reason = models.CharField(max_length=512, null=True)
    tag = models.ForeignKey(Report_Tags, on_delete=models.CASCADE, null=True)

    member_state = models.IntegerField(null=True)
    disable_poll_announcement_mail = models.BooleanField(default=False)
    has_files = models.BooleanField(default=False)

    is_pinned = models.BooleanField(default=False)
    pinning_time = models.BigIntegerField(default=0)

    is_secret = models.BooleanField(default=False)
    secret_chatroom_participants = models.TextField(null=True)

    has_reactions = models.BooleanField(default=False)

    device_id = models.TextField(null=True)
    platform = models.TextField(null=True)

    auto_follow_done = models.BooleanField(default=False)
    member_can_message = models.BooleanField(default=True)
    topic = models.ForeignKey('card_answers', on_delete=models.SET_NULL, null=True)
    is_edited = models.BooleanField(default=False)
    access_without_subscription = models.BooleanField(default=False)

    # fields for event
    online_link = models.TextField(null=True)
    online_link_type = models.IntegerField(null=True)
    online_link_enable_before = models.BigIntegerField(
        default=TimeUtilities.get_minutes_in_milliseconds(15))  # 15 minutes in milliseconds
    online_link_id = models.TextField(null=True)
    online_link_password = models.TextField(null=True)
    event_payment_link = models.TextField(null=True)
    event_web_page = models.TextField(null=True)

    co_hosts = models.TextField(null=True)
    location = models.TextField(null=True)
    location_lat = models.FloatField(null=True)
    location_long = models.FloatField(null=True)
    start_date = models.BigIntegerField(default=0, null=True)
    about = models.TextField(null=True)
    date_time = models.BigIntegerField(default=0)  # for saving event and poll creation epoch
    end_date = models.BigIntegerField(default=0, null=True)  # for saving end epoch for event and poll
    is_paid = models.BooleanField(default=False)
    access = models.IntegerField(default=1, null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)
    webflow_item_id = models.TextField(null=True)
    is_private = models.BooleanField(default=False)
    chatroom_with_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                           related_name='chatroom_with_user')
    include_members_later = models.BooleanField(default=True)

    about_recording = models.TextField(null=True)
    recording_url_og_tags = models.TextField(null=True)
    has_event_recording = models.BooleanField(default=False)

    @staticmethod
    def update_time_for_community_members(community: Community) -> None:
        current_time_msec = TimeUtilities.current_time_in_milliseconds()
        Member_Engage.objects.filter(community_id=community
                                     ).update(order_time=current_time_msec)

    @staticmethod
    def get_chatroom_or_raise_exception(chatroom_id):
        try:
            return Collabcard.objects.get(pk=chatroom_id)
        except:
            response = {
                'success': False,
                'error_message': f'chatroom with id {chatroom_id} does not exist'
            }
            raise InvalidChatroomException(response)

    @staticmethod
    def get_chatroom_with_joins_or_raise_exception(chatroom_id):

        chatroom = Collabcard.objects.filter(pk=chatroom_id).select_related('community', 'user')
        if chatroom.exists():
            return chatroom[0]
        else:
            response = {
                'success': False,
                'error_message': f'chatroom with id {chatroom_id} does not exist'
            }
            raise InvalidChatroomException(response)

    @staticmethod
    def get_chatroom_or_None(chatroom_id):
        try:
            return Collabcard.objects.get(pk=chatroom_id)
        except:
            return None

    @staticmethod
    def get_community_of_chatroom_or_none(chatroom_id):
        card_instance = Collabcard.get_chatroom_or_None(chatroom_id)
        community_instance = None

        if card_instance:
            community_instance = card_instance.community

        return community_instance

    @staticmethod
    def is_chatroom_deleted(is_deleted: bool):
        return is_deleted

    def save(self, *args, **kwargs):

        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_ms

        self.updated_at = current_time_ms

        super(Collabcard, self).save(*args, **kwargs)


class draftChatroom(models.Model):
    title = models.TextField()
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    answer_text = models.CharField(max_length=100, default='')
    share_link = models.CharField(max_length=2048, default='')
    og_tags = models.TextField(default='')
    image_count = models.IntegerField(default=0, null=True)
    pdf_count = models.IntegerField(default=0, null=True)
    video_count = models.IntegerField(default=0, null=True)
    audio_count = models.IntegerField(default=0, null=True)
    type = models.IntegerField(default=0)  # state=0 (Normal Collabcard);state=1(Introduction Collabcard)
    date_time = models.BigIntegerField(default=0)  # for saving date of event and due date for polling
    duration = models.BigIntegerField(default=0)  # for saving duration of event
    date_epoch = models.BigIntegerField(default=0)
    # for polls count
    polls_count = models.IntegerField(default=0)
    attending_count = models.IntegerField(default=0)
    attachment_count = models.IntegerField(default=0)
    attachments_uploaded = models.BooleanField(default=False, null=True)

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
    preview_community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True,
                                          related_name='draft_chatroom_preview_community')
    preview_chatroom = models.ForeignKey(Collabcard, on_delete=models.SET_NULL, null=True,
                                         related_name='draft_chatroom_preview_chatroom')

    is_secret = models.BooleanField(default=False)
    secret_chatroom_participants = models.TextField(null=True)


class inActiveChatroomsCount(models.Model):
    '''models to save the count of in-active chatrooms for user'''
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # last_inactive_card = models.ForeignKey(Collabcard, on_delete=models.CASCADE,null=True)
    inactive_count = models.IntegerField(default=0)
    created_at = models.BigIntegerField(null=True)
    updated_at = models.BigIntegerField(null=True)

    @staticmethod
    def create_instance(user_instance, inactive_count):
        instance = inActiveChatroomsCount()
        instance.user = user_instance
        instance.inactive_count = inactive_count
        instance.created_at = TimeUtilities.current_time_in_sec()
        instance.updated_at = TimeUtilities.current_time_in_sec()
        instance.save()


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
    remove = models.ForeignKey(removedMembers, on_delete=models.SET_NULL, null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    is_guest = models.BooleanField(default=False)
    og_tags = models.TextField(null=True)
    is_deleted = models.BooleanField(default=False)  # for internal check, not to be sent in API's
    deleted_by_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True,
                                        related_name='conversation_deleted_by_user')
    is_edited = models.BooleanField(default=False)
    reply = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='replied_conversation')
    internal_link = models.TextField(null=True)
    preview_type = models.TextField(null=True)
    preview_community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True,
                                          related_name='conversation_preview_community')
    preview_chatroom = models.ForeignKey(Collabcard, on_delete=models.SET_NULL, null=True,
                                         related_name='conversation_preview_chatroom')

    has_files = models.BooleanField(default=False)

    last_updated = models.BigIntegerField(default=0)

    attachment_count = models.IntegerField(default=0)
    attachments_uploaded = models.BooleanField(default=False, null=True)

    api_version = models.IntegerField(default=0)
    device_id = models.TextField(null=True)
    platform = models.TextField(null=True)
    temporary_id = models.TextField(null=True)

    expiry_time = models.BigIntegerField(null=True)
    poll_type = models.IntegerField(null=True)
    multiple_select_state = models.IntegerField(null=True)
    multiple_select_no = models.IntegerField(null=True)
    is_anonymous = models.BooleanField(default=False)
    allow_add_option = models.BooleanField(default=False)

    has_reactions = models.BooleanField(default=False)
    poll_answer_text = models.TextField(default='')
    reply_chatroom = models.ForeignKey(Collabcard, on_delete=models.CASCADE, null=True,
                                       related_name="reply_chatroom_action")

    header = models.TextField(null=True)
    online_link = models.TextField(null=True)
    location = models.TextField(null=True)
    location_lat = models.TextField(null=True)
    location_long = models.TextField(null=True)
    start_time = models.BigIntegerField(default=0)
    end_time = models.BigIntegerField(default=0)
    online_link_enable_before = models.BigIntegerField(
        default=TimeUtilities.get_minutes_in_milliseconds(15))
    co_hosts = models.TextField(null=True)
    online_link_id = models.TextField(null=True)
    online_link_password = models.TextField(null=True)

    about_recording = models.TextField(null=True)
    recording_url_og_tags = models.TextField(null=True)
    has_event_recording = models.BooleanField(default=False)

    # saving the last updated in milliseconds
    def save(self, *args, **kwargs):

        current_time_milli = TimeUtilities.current_time_in_milliseconds()

        if self.last_updated == 0:
            self.last_updated = current_time_milli

        if self.created_at < 0:
            self.created_at = current_time_milli

        super(card_answers, self).save(*args, **kwargs)

    @staticmethod
    def get_conversation_or_raise_exception(conversation_id):
        try:
            return card_answers.objects.get(pk=conversation_id)
        except:
            response = {
                'success': False,
                'error_message': f'conversation with id {conversation_id} does not exist'
            }
            raise InvalidConversationException(response)

    @staticmethod
    def get_conversation_with_joins_or_raise_exception(conversation_id):

        chatroom = card_answers.objects.filter(pk=conversation_id).select_related('community', 'user', 'card')
        if chatroom.exists():
            return chatroom[0]
        else:
            response = {
                'success': False,
                'error_message': f'conversation with id {conversation_id} does not exist'
            }
            raise InvalidConversationException(response)

    @staticmethod
    def get_conversation_or_None(conversation_id):
        try:
            return card_answers.objects.get(pk=conversation_id)
        except:
            return None


class conversationPolls(models.Model):
    """class to store poll options of conversations"""

    conversation = models.ForeignKey(card_answers, on_delete=models.CASCADE)
    text = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.BigIntegerField()
    updated_at = models.BigIntegerField()

    @staticmethod
    def create_instance(create_info):
        instance = conversationPolls()
        instance.user = create_info['user_instance']
        instance.conversation = create_info['conversation_instance']
        instance.text = create_info['text']
        instance.created_at = TimeUtilities.current_time_in_milliseconds()
        instance.updated_at = TimeUtilities.current_time_in_milliseconds()
        instance.save()

        return instance


class conversationPollMembers(models.Model):
    """class to store the votes of member who voted on a poll"""
    conversation = models.ForeignKey(card_answers, on_delete=models.CASCADE)
    poll = models.ForeignKey(conversationPolls, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = conversationPollMembers()
        instance.user = create_info['user_instance']
        instance.conversation = create_info['conversation_instance']
        instance.poll = create_info['poll_instance']
        instance.created_at = TimeUtilities.current_time_in_milliseconds()
        instance.save()

        return instance


class conversationEventMembers(models.Model):
    """class to store conversation event members data"""

    conversation = models.ForeignKey(card_answers, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    attending_status = models.BooleanField(default=False)
    attended = models.BooleanField(default=False)

    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = conversationEventMembers()
        instance.user = create_info['user_instance']
        instance.conversation = create_info['conversation_instance']
        instance.attending_status = create_info.get('attending_status', False)
        instance.save()

        return instance

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(conversationEventMembers, self).save(*args, **kwargs)


class conversationEventNudge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_id_seen = models.ForeignKey(card_answers, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = conversationEventNudge()
        instance.event_id_seen = create_info.get('conversation_instance')
        instance.user = create_info.get('user_instance')
        instance.save()

    def save(self, *args, **kwargs):
        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_ms

        self.updated_at = current_time_ms

        super(conversationEventNudge, self).save(*args, **kwargs)


class collabcardState(models.Model):
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.IntegerField(null=True)
    created_at = models.BigIntegerField(default=-9223372036854775808, null=True)
    updated_at = models.BigIntegerField(default=-9223372036854775808, null=True)

    # if got removed saving the previous state
    remove = models.ForeignKey(removedMembers, on_delete=models.SET_NULL, null=True)

    mute_status = models.BooleanField(default=False)
    follow_status = models.BooleanField(default=False)
    attending_status = models.BooleanField(default=False, null=True)
    is_guest = models.BooleanField(default=False, db_index=True)
    is_tagged = models.BooleanField(default=False)
    source = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='referrer')

    expiry_time = models.BigIntegerField(null=True)

    external_seen = models.BooleanField(default=True)
    external_follow = models.BooleanField(default=False)

    manual_set_active = models.BigIntegerField(null=True)
    last_seen_conversation = models.ForeignKey(card_answers, null=True, on_delete=models.SET_NULL)

    secret_chatroom_left = models.BooleanField(default=False)
    attended = models.BooleanField(default=False)

    class Meta:
        unique_together = (('card', 'user'),)

    @staticmethod
    def get_chatroom_state_instance(card_id, user_id):

        state_filter = collabcardState.objects.filter(card=card_id, user=user_id)

        chatroom_state_instance = None

        if state_filter:
            chatroom_state_instance = state_filter[0]

        return chatroom_state_instance

    @staticmethod
    def create_chatroom_state_instance(card_instance, user_instance, state=1,
                                       expire_at=None, external_seen=True, is_guest=False, source=None,
                                       follow_status=False,
                                       mute_status=False, is_tagged=False, external_follow=False,
                                       attending_status=False, **kwargs):
        """function to create chatroom state instance"""

        try:
            collabcard_state_instance = collabcardState()
            collabcard_state_instance.card = card_instance
            collabcard_state_instance.community = card_instance.community
            collabcard_state_instance.user = user_instance
            collabcard_state_instance.state = state
            collabcard_state_instance.created_at = TimeUtilities.current_time_in_sec()
            collabcard_state_instance.updated_at = TimeUtilities.current_time_in_sec()
            collabcard_state_instance.external_seen = external_seen
            collabcard_state_instance.attending_status = attending_status
            collabcard_state_instance.follow_status = follow_status
            collabcard_state_instance.mute_status = mute_status
            collabcard_state_instance.is_tagged = is_tagged
            collabcard_state_instance.is_guest = is_guest
            collabcard_state_instance.source = source
            collabcard_state_instance.external_follow = external_follow

            collabcard_state_instance.save()

            return collabcard_state_instance

        except Exception as e:

            error_logger.error(e)

    @staticmethod
    def create_chatroom_state_instances_for_bulk_create(card_instance, user_instance, state=1,
                                                        expire_at=None, external_seen=True, is_guest=False, source=None,
                                                        follow_status=False,
                                                        mute_status=False, is_tagged=False, external_follow=False,
                                                        attending_status=False, **kwargs):
        """function to create chatroom state instance for bulk create"""

        if kwargs.get('community_instance'):
            community_instance = kwargs.get('community_instance')

        else:
            community_instance = card_instance.community

        try:
            collabcard_state_instance = collabcardState()
            collabcard_state_instance.card = card_instance
            collabcard_state_instance.community = community_instance
            collabcard_state_instance.user = user_instance
            collabcard_state_instance.state = state
            collabcard_state_instance.created_at = TimeUtilities.current_time_in_sec()
            collabcard_state_instance.updated_at = TimeUtilities.current_time_in_sec()
            collabcard_state_instance.external_seen = external_seen
            collabcard_state_instance.attending_status = attending_status
            collabcard_state_instance.follow_status = follow_status
            collabcard_state_instance.mute_status = mute_status
            collabcard_state_instance.is_tagged = is_tagged
            collabcard_state_instance.is_guest = is_guest
            collabcard_state_instance.source = source
            collabcard_state_instance.external_follow = external_follow

            return collabcard_state_instance

        except Exception as e:
            error_logger.error(e)

            return None


class conversationMemberState(models.Model):
    '''function to save member state of conversation'''
    conversation = models.ForeignKey(card_answers, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = TimeUtilities.current_time_in_sec()

        self.updated_at = TimeUtilities.current_time_in_sec()

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
    last_conversation_member = models.ForeignKey(Members, on_delete=models.SET_NULL, null=True,
                                                 related_name='last_conversation_member')
    second_last_conversation_member = models.ForeignKey(Members, on_delete=models.SET_NULL, null=True,
                                                        related_name='second_last_conversation_member')

    last_conversation_user = models.ForeignKey(collabcardState, on_delete=models.SET_NULL, null=True,
                                               related_name='last_conversation_user')
    second_last_conversation_user = models.ForeignKey(collabcardState, on_delete=models.SET_NULL, null=True,
                                                      related_name='second_last_conversation_user')

    rights_list = models.TextField(null=True)

    @staticmethod
    def create_instance(create_info):
        instance = conversationEngage()
        instance.card = create_info.get('card_instance')
        instance.user = create_info.get('user_instance')
        instance.community = create_info.get('community_instance')
        instance.last_conversation = None
        instance.unseen_count = 0
        instance.rights_list = create_info.get('rights_list')
        instance.created_at = TimeUtilities.current_time_in_sec()
        instance.updated_at = TimeUtilities.current_time_in_sec()
        instance.save()

    @staticmethod
    def create_instance_for_bulk_create(community_instance, chatroom_instance, user_instance,
                                        unseen_count=0, rights_list=None, last_conversation=None,
                                        created_at=None, updated_at=None):
        current_time_in_sec = TimeUtilities.current_time_in_sec()

        created_at = created_at if created_at else current_time_in_sec
        updated_at = updated_at if updated_at else current_time_in_sec

        instance = conversationEngage()
        instance.card = chatroom_instance
        instance.user = user_instance
        instance.community = community_instance
        instance.last_conversation = last_conversation
        instance.unseen_count = unseen_count
        instance.rights_list = rights_list
        instance.created_at = created_at
        instance.updated_at = updated_at

        return instance


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
    name = models.CharField(max_length=200, null=True)
    meta = models.TextField(null=True)
    attachment = models.FileField(upload_to="media/collabcard_files", default='')
    file_url = models.CharField(max_length=500, null=True)
    thumbnail_url = models.TextField(null=True)
    type = models.CharField(max_length=50, default='')
    index = models.IntegerField(default=1, null=True)
    dimensions = models.TextField(null=True)
    height = models.IntegerField(null=True)
    width = models.IntegerField(null=True)


class draftChatroomFiles(models.Model):
    '''model to save files of collabcard'''

    draft = models.ForeignKey(draftChatroom, on_delete=models.CASCADE)

    file_url = models.TextField(null=True)
    thumbnail_url = models.TextField(null=True)
    type = models.CharField(max_length=50, default='')

    created_at = models.BigIntegerField(default=0)
    index = models.IntegerField(default=1, null=True)
    dimensions = models.TextField(null=True)
    height = models.IntegerField(null=True)
    width = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = TimeUtilities.current_time_in_sec()
        super(draftChatroomFiles, self).save(*args, **kwargs)


class answerAttachment(models.Model):
    '''model to save files of collabcard'''

    answer = models.ForeignKey(card_answers, on_delete=models.CASCADE)

    name = models.CharField(max_length=200, null=True)
    meta = models.TextField(null=True)

    file_url = models.TextField(null=True)
    thumbnail_url = models.TextField(null=True)
    type = models.CharField(max_length=50, default='')

    location_name = models.TextField(null=True)
    location_lat = models.FloatField(null=True)
    location_long = models.FloatField(null=True)

    created_at = models.BigIntegerField(default=0)

    index = models.IntegerField(default=1, null=True)
    dimensions = models.TextField(null=True)
    height = models.IntegerField(null=True)
    width = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = TimeUtilities.current_time_in_sec()
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
    pending_chatrooms = models.IntegerField(default=0, null=True)
    open_reports = models.IntegerField(default=0, null=True)
    updated_at = models.BigIntegerField(default=0, null=True)
    member_referral = models.CharField(default='', max_length=1024)
    member_state = models.IntegerField(null=True)
    click_state = models.IntegerField(default=0)
    new_chatroom_users = models.TextField(null=True)
    rights_list = models.TextField(null=True)
    order_time = models.BigIntegerField(null=True)

    @staticmethod
    def create_instance(create_info):
        engage = Member_Engage()
        engage.member_id = create_info.get('user_instance')
        engage.community_id = create_info.get('community_instance')
        engage.updated_at = TimeUtilities.current_time_in_sec()
        engage.member_state = create_info.get('state')
        engage.click_state = create_info.get('click_state', 0)
        engage.member_referral = create_info.get('member_referral', '')
        engage.rights_list = create_info.get('rights_list', None)
        engage.save()

        return engage

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if not self.order_time:
            self.order_time = current_time

        self.order_time = current_time
        super(Member_Engage, self).save(*args, **kwargs)


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

    # tag = models.ForeignKey(Tags_lpig, on_delete=models.CASCADE)
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
    action_taken_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='action_taken_by_promoter',
                                        null=True)
    action_taken_reason = models.CharField(max_length=2048, null=True)
    action_taken_tag = models.ForeignKey(Report_Tags, on_delete=models.CASCADE, related_name='action_taken_tag',
                                         null=True)
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
    attending_status = models.BooleanField(default=False)
    is_guest = models.BooleanField(default=False)
    source = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='referrer_backup')

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = TimeUtilities.current_time_in_sec()
        self.updated_at = TimeUtilities.current_time_in_sec()
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
            self.created_at = TimeUtilities.current_time_in_sec()

        self.updated_at = TimeUtilities.current_time_in_sec()
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
            self.created_at = TimeUtilities.current_time_in_sec()

        self.updated_at = TimeUtilities.current_time_in_sec()
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
    help_text = models.TextField(null=True, blank=True)

    # when the promoter deletes a question from v1/edit_questions api
    remove_state = models.BooleanField(default=False)

    is_hidden = models.BooleanField(default=False)
    is_compulsory = models.BooleanField(default=False)

    field = models.BooleanField(default=False)

    rank = models.IntegerField(default=0)
    can_add_options = models.BooleanField(default=False)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = TimeUtilities.current_time_in_sec()

        self.updated_at = TimeUtilities.current_time_in_sec()
        super(communityQuestions, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.question_title)


class communityAnswers(models.Model):
    '''model to save answers of a user in community'''

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    question_title = models.TextField(null=True)
    question_answer = models.TextField()
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(communityQuestions, on_delete=models.CASCADE)

    @staticmethod
    def create_instance(create_dict):
        answer_instance = communityAnswers()
        answer_instance.question = create_dict.get('question_instance')
        answer_instance.member = create_dict.get('user_instance')
        answer_instance.community = create_dict.get('community_instance')
        answer_instance.question_answer = create_dict.get('question_answer')
        answer_instance.question_title = create_dict.get('question_title')
        answer_instance.save()

        return answer_instance


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

    @staticmethod
    def create_instance(create_info):
        instance = questionFilters()
        instance.question = create_info.get('question_instance')
        instance.filter = create_info.get('option')
        instance.member = create_info.get('user_instance')
        instance.community = create_info.get('community_instance')
        instance.save()

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = TimeUtilities.current_time_in_sec()

        super(questionFilters, self).save(*args, **kwargs)


class communityExpiryCodes(models.Model):
    '''model to generate private links of community'''

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    promoter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promoter')
    created_at = models.BigIntegerField(default=0, null=True)
    unique_code = models.IntegerField(default=0)
    private_link = models.CharField(max_length=2048, null=True)
    expire_duration = models.BigIntegerField(default=0, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_id', null=True)


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

    @staticmethod
    def create_instance(create_info):
        instance = communityLevels()
        instance.community = create_info['community']
        instance.level = create_info['level']
        instance.title = create_info['title']
        instance.sub_title = create_info['sub_title']
        instance.state = create_info['level_state']
        instance.image = create_info['image']
        instance.joined_members = create_info['joined_members']
        instance.max_members = create_info['max_members']
        instance.save()


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
            self.created_at = TimeUtilities.current_time_in_sec()

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
            self.created_at = TimeUtilities.current_time_in_sec()

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

    @staticmethod
    def create_instance(backup_info):
        instance = mobileBackup()
        instance.mobile_no = backup_info.get('mobile_no')
        instance.country_code = backup_info.get('country_code')
        instance.created_at = time.time()
        instance.save()


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
            self.created_at = TimeUtilities.current_time_in_sec()

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
            self.created_at = TimeUtilities.current_time_in_sec()

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
            self.created_at = TimeUtilities.current_time_in_sec()

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
            self.created_at = TimeUtilities.current_time_in_sec()

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

    @staticmethod
    def fetch_user_admin_rights(user, community):
        user_rights = userAdminRights.objects \
            .filter(user=user, community=community) \
            .values_list('right__state', flat=True)

        return list(user_rights)


class userMemberRights(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    right = models.ForeignKey(memberRights, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('user', 'community', 'right'),)

    @staticmethod
    def check_member_invite_private_right(user, community):

        user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                      right__state=member_rights.MEMBER_RIGHT_INVITE_PRIVATE_LINK)

        if user_rights.exists():
            return True
        return False

    @staticmethod
    def check_member_respond_right(user, community):

        user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                      right__state=member_rights.MEMBER_RIGHT_RESPOND_IN_ROOM)

        if user_rights.exists():
            return True
        return False

    @staticmethod
    def check_member_create_room_right(user, community):

        user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                      right__state=member_rights.MEMBER_RIGHT_CREATE_ROOMS)

        if user_rights.exists():
            return True
        return False

    @staticmethod
    def check_member_auto_approve_right(user, community):

        user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                      right__state=member_rights.MEMBER_RIGHT_AUTO_APPROVE)

        if user_rights.exists():
            return True
        return False

    @staticmethod
    def fetch_user_member_rights(user, community):
        user_rights = userMemberRights.objects \
            .filter(user=user, community=community) \
            .values_list('right__state', flat=True)

        return list(user_rights)


class moderationHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    type = models.IntegerField(null=True)
    moderation_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moderation_by_user',
                                      null=True)
    moderation_time = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_dict):
        instance = moderationHistory()
        instance.user = create_dict.get('user_instance')
        instance.community = create_dict.get('community_instance')
        instance.moderation_by = create_dict.get('moderation_by')
        instance.type = create_dict.get('type')
        instance.save()

    def save(self, *args, **kwargs):
        if self.moderation_time <= 0:
            self.moderation_time = TimeUtilities.current_time_in_sec()

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

    device_id = models.TextField(null=True)

    @staticmethod
    def create_instance(create_info):
        instance = userDevices()
        instance.user = create_info.get('user_instance')
        instance.mobile_os = create_info.get('platform_code')
        instance.fcm_token = create_info.get('token')
        instance.device_id = create_info.get('device_id')
        instance.save()

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_sec()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(userDevices, self).save(*args, **kwargs)


class userMemberRightsHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    right = models.ForeignKey(memberRights, on_delete=models.CASCADE)
    enabled_by_CM = models.BooleanField(default=False, null=True)
    updated_CM = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='manager_who_updated')
    updated_time = models.BigIntegerField(default=0, null=True)

    class Meta:
        unique_together = (('user', 'community', 'right'),)

    def save(self, *args, **kwargs):
        self.updated_time = TimeUtilities.current_time_in_sec()
        super(userMemberRightsHistory, self).save(*args, **kwargs)


class homeSnackbar(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(null=True)
    cta = models.TextField(null=True)
    cta_route = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.created_at == 0:
            self.created_at = TimeUtilities.current_time_in_sec()

        super(homeSnackbar, self).save(*args, **kwargs)


class userSurvey(models.Model):
    """table to save the survey details of user for NPS"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    survey_seen = models.BooleanField(default=False)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = userSurvey()
        instance.user = create_info.get('user_instance')
        instance.survey_seen = create_info.get('survey_seen')
        instance.save()

    def save(self, *args, **kwargs):
        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_ms

        self.updated_at = current_time_ms

        super(userSurvey, self).save(*args, **kwargs)


class ModelUtilities:
    """class contains utility functions for models"""

    @staticmethod
    def model_update(model, filter_dict, update_dict):
        update_status = model.objects.filter(**filter_dict).update(**update_dict)

        return update_status

    @staticmethod
    def get_model_filter(model, filter_dict):
        return model.objects.filter(**filter_dict)

    @staticmethod
    def is_model_filter_exists(model, filter_dict):
        return model.objects.filter(**filter_dict).exists()

    @staticmethod
    def update_or_create_model(model, filter_dict, update_dict):
        model_instance, created = model.objects.update_or_create(
            **filter_dict,
            defaults=update_dict
        )

        return model_instance, created

    @staticmethod
    def get_model_instance_or_none(model, pk):

        instance = None
        try:
            instance = model.objects.get(id=pk)

        except Exception as e:

            pass

        return instance

    @staticmethod
    def paginate_queryset(queryset, page, paginate_by):

        offset = (page - 1) * paginate_by

        return queryset[offset: offset + paginate_by]

    @staticmethod
    def delete_record_in_model(model, filter_dict):
        return model.objects.filter(**filter_dict).delete()

    @staticmethod
    def divide_chunks(model_list, chunk_size=1000):

        for i in range(0, len(model_list), chunk_size):
            yield model_list[i:i + chunk_size]

    @staticmethod
    def bulk_create_instances(model, model_list, chunk_size=1000):

        bulk_create_list = list(ModelUtilities.divide_chunks(model_list, chunk_size))

        for instance_list in bulk_create_list:
            model.objects.bulk_create(instance_list)

    @staticmethod
    def bulk_update_instances(model, model_list, fields, chunk_size=1000):

        if not fields:
            return

        bulk_create_list = list(ModelUtilities.divide_chunks(model_list, chunk_size))

        for instance_list in bulk_create_list:
            model.objects.bulk_update(instance_list, fields, chunk_size)

    @staticmethod
    def serialize_instance(instance):

        return core_serializer.serialize('python', [instance], )[0].get('fields')


class MessageReactions(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chatroom = models.ForeignKey(Collabcard, on_delete=models.CASCADE, null=True)
    conversation = models.ForeignKey(card_answers, on_delete=models.CASCADE, null=True)
    reaction = models.CharField(max_length=100, null=False)

    updated_at = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ['user', 'chatroom', 'conversation']

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()
        self.updated_at = current_time

        super(MessageReactions, self).save(*args, **kwargs)


class CommunityUserDelete(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    deleted_community_id = models.IntegerField(default=0)
    created_at = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ['user', 'deleted_community_id']

    @staticmethod
    def create_instance(create_info):

        try:
            instance = CommunityUserDelete()
            instance.user = create_info.get('user_instance')
            instance.deleted_community_id = create_info.get('community_id')
            instance.save()

        except Exception as e:
            error_logger.error(e)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()
        self.created_at = current_time

        super(CommunityUserDelete, self).save(*args, **kwargs)


class SubscriptionExpiredMembers(models.Model):
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    state = models.IntegerField(null=True)
    created_at = models.BigIntegerField(default=0)
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
    joined_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="expired_joined_by_user")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="expired_approved_by_user")
    parent_cm = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="expired_parent_cm_user")
    parent_cm_list = models.TextField(null=True)  # it has the user id's of parent's hierarchy
    became_member_at = models.BigIntegerField(default=0)

    has_onboarded = models.BooleanField(default=False)

    @staticmethod
    def create_instance_from_member(member_instance: Members):
        expired_instance = SubscriptionExpiredMembers()
        expired_instance.member = member_instance.member_id
        expired_instance.community = member_instance.community_id
        expired_instance.state = member_instance.state
        expired_instance.created_at = member_instance.created_at
        expired_instance.updated_at = member_instance.updated_at
        expired_instance.tool_state = member_instance.tool_state
        expired_instance.ask_member_id = member_instance.ask_member_id
        expired_instance.approved_member_id = member_instance.approved_member_id
        expired_instance.edit_required = member_instance.edit_required
        expired_instance.actions_required = member_instance.actions_required
        expired_instance.image_url = member_instance.image_url
        expired_instance.is_owner = member_instance.is_owner
        expired_instance.custom_title = member_instance.custom_title
        expired_instance.joined_by = member_instance.joined_by
        expired_instance.approved_by = member_instance.approved_by
        expired_instance.parent_cm = member_instance.parent_cm
        expired_instance.parent_cm_list = member_instance.parent_cm_list
        expired_instance.became_member_at = member_instance.became_member_at
        expired_instance.has_onboarded = member_instance.has_onboarded
        expired_instance.save()


class EventInstructor(models.Model):

    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE, null=True)
    about = models.TextField(null=True)
    url = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):

        instance = EventInstructor()
        instance.card = create_info.get('card_instance')
        instance.about = create_info.get('about')
        instance.url = create_info.get('url')
        instance.save()

        return instance

    def save(self, *args, **kwargs):
        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_ms

        self.updated_at = current_time_ms

        super(EventInstructor, self).save(*args, **kwargs)


class EventHighlights(models.Model):
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE, null=True)
    highlight = models.TextField(null=True)
    url = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = EventHighlights()
        instance.card = create_info.get('card_instance')
        instance.highlight = create_info.get('highlight')
        instance.url = create_info.get('url')
        instance.save()

        return instance

    def save(self, *args, **kwargs):
        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_ms

        self.updated_at = current_time_ms

        super(EventHighlights, self).save(*args, **kwargs)


class EventMemberTestimonials(models.Model):
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE, null=True)
    member_name = models.TextField(null=True)
    testimonial = models.TextField(null=True)
    url = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = EventMemberTestimonials()
        instance.card = create_info.get('card_instance')
        instance.member_name = create_info.get('member_name')
        instance.testimonial = create_info.get('testimonial')
        instance.url = create_info.get('url')
        instance.save()

        return instance

    def save(self, *args, **kwargs):
        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_ms

        self.updated_at = current_time_ms

        super(EventMemberTestimonials, self).save(*args, **kwargs)


class EventFAQ(models.Model):
    card = models.ForeignKey(Collabcard, on_delete=models.CASCADE, null=True)
    question = models.TextField(null=True)
    answer = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = EventFAQ()
        instance.card = create_info.get('card_instance')
        instance.question = create_info.get('question')
        instance.answer = create_info.get('answer')
        instance.save()

        return instance

    def save(self, *args, **kwargs):
        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_ms

        self.updated_at = current_time_ms

        super(EventFAQ, self).save(*args, **kwargs)


class EventNudge(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seen_event_chatroom = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = EventNudge()
        instance.seen_event_chatroom = create_info.get('card_instance')
        instance.user = create_info.get('user_instance')
        instance.save()

    def save(self, *args, **kwargs):
        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_ms

        self.updated_at = current_time_ms

        super(EventNudge, self).save(*args, **kwargs)


class ContentDownloadSettings(models.Model):
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    download_setting_type = models.CharField(max_length=100, null=False)
    download_setting_title = models.CharField(max_length=100, null=False)
    enabled = models.BooleanField(default=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = ContentDownloadSettings()
        instance.community_id = create_info.get('community_instance')
        instance.download_setting_type = create_info.get('download_setting_type')
        instance.download_setting_title = create_info.get('download_setting_title')
        instance.enabled = create_info.get('enabled')
        instance.created_at = TimeUtilities.current_time_in_milliseconds()

        return instance

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()
        self.updated_at = current_time

        super(ContentDownloadSettings, self).save(*args, **kwargs)


class Cohort(models.Model):

    name = models.CharField(max_length=200)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)
    type = models.IntegerField(default=0)
    type_id = models.CharField(max_length=64, null=True)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(Cohort, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(cohort_info):
        instance = Cohort()
        instance.name = cohort_info.get('name')
        instance.community = cohort_info.get('community_instance')
        instance.type = cohort_info.get('type')
        instance.type_id = cohort_info.get('type_id')
        instance.save()
        return instance


class CohortMember(models.Model):

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(CohortMember, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(cohort_member_info):
        instance = CohortMember()
        instance.cohort = cohort_member_info.get('cohort_instance')
        instance.user = cohort_member_info.get('user_instance')
        instance.save()
        return instance

    @staticmethod
    def create_instance_for_bulk_create(cohort_member_info):
        instance = CohortMember()
        instance.cohort = cohort_member_info.get('cohort_instance')
        instance.user = cohort_member_info.get('user_instance')
        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        if instance.created_at == 0:
            instance.created_at = current_time_ms

        instance.updated_at = current_time_ms

        return instance


class CohortRights(models.Model):

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    member_rights = models.ForeignKey(memberRights, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(CohortRights, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(cohort_member_info):
        instance = CohortRights()
        instance.cohort = cohort_member_info.get('cohort_instance')
        instance.member_rights = cohort_member_info.get('right_instance')
        instance.save()
        return instance

    @staticmethod
    def create_instance_for_bulk_create(cohort_member_info):
        instance = CohortRights()
        instance.cohort = cohort_member_info.get('cohort_instance')
        instance.member_rights = cohort_member_info.get('right_instance')
        current_time_ms = TimeUtilities.current_time_in_milliseconds()

        if instance.created_at == 0:
            instance.created_at = current_time_ms

        instance.updated_at = current_time_ms

        return instance


class CohortFilter(models.Model):

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    question = models.ForeignKey(communityQuestions, on_delete=models.CASCADE)
    value = models.CharField(max_length=200)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(CohortFilter, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(cohort_filter_data):
        cohort_filter = CohortFilter()
        cohort_filter.cohort = cohort_filter_data.get('cohort')
        cohort_filter.question = cohort_filter_data.get('question')
        cohort_filter.value = cohort_filter_data.get('value')
        cohort_filter.save()


class DirectMessageTutorial(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    clicked = models.BooleanField(default=False)
    messaged = models.BooleanField(default=False)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = DirectMessageTutorial()
        instance.user_id = create_info.get('user_instance')
        instance.clicked = create_info.get('clicked')
        instance.messaged = create_info.get('messaged')
        instance.created_at = TimeUtilities.current_time_in_milliseconds()

        return instance

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()
        self.updated_at = current_time

        super(DirectMessageTutorial, self).save(*args, **kwargs)


class CommunitySettings(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    setting_type = models.CharField(max_length=100, null=False)
    setting_title = models.CharField(max_length=100, null=False)
    setting_sub_title = models.CharField(max_length=255, null=False)
    enabled = models.BooleanField(default=False)
    enabled_by = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = CommunitySettings()
        instance.community = create_info.get('community_instance')
        instance.setting_type = create_info.get('setting_type')
        instance.setting_title = create_info.get('setting_title')
        instance.setting_sub_title = create_info.get('setting_sub_title')
        instance.enabled = create_info.get('enabled')
        instance.enabled_by = create_info.get('enabled_by', None)
        instance.created_at = TimeUtilities.current_time_in_milliseconds()

        return instance

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()
        self.updated_at = current_time

        super(CommunitySettings, self).save(*args, **kwargs)


class CommunityToastV1(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    text = models.TextField(null=True)
    is_shown = models.BooleanField(default=False)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    @staticmethod
    def create_instance(create_info):
        instance = CommunityToastV1()
        instance.user = create_info.get('user_instance')
        instance.community = create_info.get('community_instance')
        instance.text = create_info.get('text')
        instance.is_shown = create_info.get('is_shown')
        instance.created_at = TimeUtilities.current_time_in_milliseconds()

        return instance

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()
        self.updated_at = current_time

        super(CommunityToastV1, self).save(*args, **kwargs)


class EventRecordingsAttachments(models.Model):
    """ table to store recording and attachment of event """

    TYPE_CHOICES = (
        ('image','image'),
        ('video','video'),
        ('pdf','pdf'),
        ('gif','gif'),
        ('audio','audio'),
        ('voice_note','voice_note'),
    )

    url = models.TextField(
        help_text=_(
            'download url of multimedia'
        )
    )
    chatroom_id = models.ForeignKey(
        Collabcard,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
            help_text=_(
                'id of chatroom'
            )
    )
    conversation_id = models.ForeignKey(
        card_answers,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=_(
            'id of conversation'
        )
    )
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        help_text=_(
            'type of attachment'
        )
    )
    index = models.IntegerField(
        help_text=_(
            'multimedia position'
        )
    )
    width = models.IntegerField(
        null=True,
        help_text=_(
            'width of multimedia'
        )
    )
    height = models.IntegerField(
        null=True,
        blank=True,
        help_text=_(
            'height of multimedia'
        )
    )
    thumbnail_url = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            'thumbnail in case of video'
        )
    )
    name = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text=_(
            'file name'
        )
    )
    meta = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            'meta data of multimedia'
        )
    )
    created_at = models.BigIntegerField(
        default=0,
        help_text=_(
            'instance created time'
        )
    )
    updated_at = models.BigIntegerField(
        default=0,
        help_text=_(
            'instance updated time'
        )
    )
    is_recording = models.BooleanField(
        default=False,
        null=True,
        help_text=(
            'whether its a recording or not'
        )
    )
    about = models.TextField(
        null=True,
        help_text=(
            'description for the attachment'
        )
    )

    class Meta:
            verbose_name = 'event recording attachment'
            verbose_name_plural = 'event recording attachments'
            db_table = 'togther_event_recording_attachment'

    def save(self, *args, **kwargs):
        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()
        self.updated_at = current_time_in_ms

        if self.created_at <= 0:
            self.created_at = current_time_in_ms

        super(EventRecordingsAttachments, self).save(*args, **kwargs)


class EventRecordingsURL(models.Model):
    """ table to store URL details of event """

    chatroom_id = models.ForeignKey(
        Collabcard,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=_(
            'id of chatroom'
        )
    )
    conversation_id = models.ForeignKey(
        card_answers,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=_(
            'id of conversation'
        )
    )
    recording_url_og_tags = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            'og tags'
        )
    )
    is_recording = models.BooleanField(
        default=False,
        help_text=(
            'whether its a recording or not'
        )
    )
    about_recording = models.TextField(
        null=True,
        blank=True,
        help_text=(
            'description for the attachment'
        )
    )
    created_at = models.BigIntegerField(
        default=0,
        help_text=_(
            'instance created time'
        )
    )
    updated_at = models.BigIntegerField(
        default=0,
        help_text=_(
            'instance updated time'
        )
    )

    class Meta:
        verbose_name = 'event recording url'
        verbose_name_plural = 'event recording urls'
        db_table = 'togther_event_recording_url'

    def save(self, *args, **kwargs):
        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()
        self.updated_at = current_time_in_ms

        if self.created_at <= 0:
            self.created_at = current_time_in_ms

        super(EventRecordingsURL, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(event_url_info):
        instance = EventRecordingsURL()
        instance.chatroom_id = event_url_info.get('chatroom_id')
        instance.conversation_id = event_url_info.get('conversation_id')
        instance.is_recording = event_url_info.get('is_recording', False)
        instance.about_recording = event_url_info.get('about_recording')
        instance.recording_url_og_tags = event_url_info.get('recording_url_og_tags')
        instance.save()
        return instance

     
class ChatroomCohort(models.Model):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    chatroom = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ChatroomCohort, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(chatroom_cohort_info):
        instance = ChatroomCohort()
        instance.cohort = chatroom_cohort_info.get('cohort_instance')
        instance.chatroom = chatroom_cohort_info.get('chatroom_instance')
        instance.save()
        return instance


class CommunityJoinDefaultEmail(models.Model):
    body = models.TextField(null=True)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()
        self.updated_at = current_time_in_ms

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        super(CommunityJoinDefaultEmail, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(community_join_default_email_body):
        instance = CommunityJoinDefaultEmail()
        instance.body = community_join_default_email_body.get('body')
        instance.save()
        return instance


class CommunityJoinEmail(models.Model):
    reply_to = models.TextField(null=True)
    subject = models.TextField(null=True)
    body = models.TextField(null=True)
    community_id = models.ForeignKey(Community, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        self.updated_at = current_time_in_ms

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        super(CommunityJoinEmail, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(community_join_email_info):
        instance = CommunityJoinEmail()
        instance.reply_to = community_join_email_info.get('reply_to')
        instance.subject = community_join_email_info.get('subject')
        instance.body = community_join_email_info.get('body')
        instance.community_id = community_join_email_info.get('community_instance')
        instance.save()
        return instance


class GetStarted(models.Model):
    type = models.IntegerField(null=False)
    title = models.CharField(max_length=255, null=False)
    tool_tip_text = models.TextField(default="", null=False)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(GetStarted, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(get_started_info):
        instance = GetStarted()
        instance.type = get_started_info.get('type')
        instance.title = get_started_info.get('title')
        instance.tool_tip_text = get_started_info.get('tool_tip_text')
        instance.created_at = TimeUtilities.current_time_in_milliseconds()
        instance.updated_at = TimeUtilities.current_time_in_milliseconds()

        return instance


class CommunityGetStarted(models.Model):
    get_started = models.ForeignKey(GetStarted, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(CommunityGetStarted, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(community_get_started_info):
        instance = CommunityGetStarted()
        instance.get_started = community_get_started_info.get('get_started')
        instance.completed = community_get_started_info.get('completed')
        instance.community = community_get_started_info.get('community')
        instance.created_at = TimeUtilities.current_time_in_milliseconds()
        instance.updated_at = TimeUtilities.current_time_in_milliseconds()

        return instance


class UserEmailsSendStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True)
    chatroom_id = models.IntegerField(default=None, null=True)
    status_type = models.IntegerField(default=0)
    frequency_in_minutes = models.IntegerField(null=True)
    count = models.IntegerField(null=True)
    max_count = models.IntegerField(null=True)
    mail_data = models.TextField(null=True)
    is_completed = models.BooleanField(default=False)
    expires_at = models.BigIntegerField(default=0)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(UserEmailsSendStatus, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(user_emails_info):
        instance = UserEmailsSendStatus()
        instance.user = user_emails_info.get('user')
        instance.community = user_emails_info.get('community')
        instance.chatroom_id = user_emails_info.get('chatroom_id')
        instance.status_type = user_emails_info.get('status_type')
        instance.frequency_in_minutes = user_emails_info.get('frequency_in_minutes')
        instance.count = user_emails_info.get('count')
        instance.max_count = user_emails_info.get('max_count')
        instance.mail_data = user_emails_info.get('mail_data')
        instance.is_completed = user_emails_info.get('is_completed', False)
        instance.expires_at = user_emails_info.get('expires_at', 0)
        instance.created_at = TimeUtilities.current_time_in_milliseconds()
        instance.updated_at = TimeUtilities.current_time_in_milliseconds()
        instance.save()

        return instance


class EventCommsCeleryTasks(models.Model):
    task_id = models.CharField(max_length=100)
    event = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    comm_type = models.CharField(max_length=30)
    event_type = models.CharField(max_length=30)
    is_deleted = models.BooleanField(default=False)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(EventCommsCeleryTasks, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(task_info):
        instance = EventCommsCeleryTasks()
        instance.task_id = task_info.get('task_id')
        instance.event = task_info.get('event')
        instance.comm_type = task_info.get('comm_type')
        instance.event_type = task_info.get('event_type')
        instance.is_deleted = task_info.get('is_deleted')
        instance.created_at = TimeUtilities.current_time_in_milliseconds()
        instance.updated_at = TimeUtilities.current_time_in_milliseconds()
        instance.save()

        return instance


class EventGoogleCalendarLogs(models.Model):
    calendar_id = models.CharField(max_length=100)
    event = models.ForeignKey(Collabcard, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'event google calendar log'
        verbose_name_plural = 'event google calendar logs'
        db_table = 'togther_event_google_calendar_logs'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(EventGoogleCalendarLogs, self).save(*args, **kwargs)

    @staticmethod
    def create_instance(task_info):
        instance = EventGoogleCalendarLogs()
        instance.calendar_id = task_info.get('calendar_id')
        instance.event = task_info.get('event')
        instance.is_deleted = task_info.get('is_deleted')
        instance.created_at = TimeUtilities.current_time_in_milliseconds()
        instance.updated_at = TimeUtilities.current_time_in_milliseconds()
        instance.save()

        return instance


class MessageTemplate(models.Model):

    community_id = models.IntegerField(null=True, default=None)
    message = models.TextField()
    chatroom_type = models.IntegerField()
    cm_id = models.IntegerField(null=True, default=None)
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        current_time = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time

        self.updated_at = current_time

        super(MessageTemplate, self).save(*args, **kwargs)
