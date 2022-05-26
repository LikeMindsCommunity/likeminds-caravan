import json
import uuid

import requests as rqst

from urllib import parse
from typing import Union
from rest_framework import status as status_codes
from django.template.loader import get_template
from celery import shared_task

from django.db.models import Q, Sum
from django.contrib.auth.models import User
from django.conf import settings

from cms.models import userAcquition
from togther.models import (userMobiles, ModelUtilities, userSurvey, userDevices, Community,
                            Members, userEmails, Userinfo, emailTokens, Collabcard, removedMembers,
                            DirectMessageTutorial, communityRightsSettings, card_answers, collabcardState,
                            conversationEngage, CommunitySettings, SDKClientUsersInfo)
from collabmates_api.user.user_manager import UserManager
from collabmates_api.sdk.models import (SdkClient)

from utility.exception_utilities import InvalidUserException
from utility.mail_category_constants import EmailCategories, EmailSubCategories
from utility.time_utilities import TimeUtilities
from utility.states import email_states, mobile_states, member_states, login_types, deleted_members, \
    conversation_states, member_rights, community_setting_types, chat_request_states, api_types
from utility.utils import generate_random
from utility.firebase import upload_image_to_firebase
from utility.api_client import ApiClient
from utility.constants import ONE_DAY_HOURS
from utility.response_utilities import ResponseUtilities

from utility.url_utilities import UrlUtilities

from .constants import *
from .user_view_helper import UserViewHelper
from ..raw_queries import get_community_id_list, get_conversations_after_last_seen_messages_in_chatrooms, \
    get_dm_chatrooms_of_user
from ..views import remove_members, remove_all_member_rights, remove_all_manager_rights
from ..tasks import send_verification_mail_for_email_sync, cm_onboarding_version_check
from ..utility import m2cm_v1_version_check, m2cm_v2_version_check
from ..rest_api import CommunitySerializerV1
from ..serializers import get_logged_in_user
from ..static_text import DM_CHATROOMS_VERSION_CODE_ANDROID, DM_CHATROOMS_VERSION_CODE_IOS, \
    CM_ONBOARDING_CREATE_COMMUNITY_BRANCH_LINK

from external_services.logging.logging_wrapper import LoggingWrapper
from external_services.email.email_wrapper import MailWrapper, MailHelper

host_url = settings.URL
subscription_url = settings.SUBSCRIPTION_SERVER_URL

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class UserImpl(UserManager):
    user_id = None
    community_id = None
    mobile_no = None

    def __init__(self,
                 user_id: str,
                 community_id: str = None,
                 mobile_no: str = None,
                 platform_code: str = None,
                 version_code: int = 0):
        self.user_id = user_id
        self.community_id = community_id
        self.mobile_no = mobile_no
        self.platform_code = platform_code
        self.version_code = version_code

    def get_user_id(self):
        return self.user_id

    def set_user_id(self, user_id):
        self.user_id = user_id

    def get_community_id(self):
        return self.community_id

    def set_community_id(self, community_id):
        self.community_id = community_id

    def get_mobile_no(self):
        return self.mobile_no

    def get_platform_code(self):
        return self.platform_code

    def get_version_code(self):
        return self.version_code

    def set_mobile_no(self, mobile_no):
        self.mobile_no = mobile_no

    def _fetch_user_instance(self, user_id):
        user_instance = None
        try:
            user_instance = User.objects.get(id=user_id)
            return user_instance
        except Exception as e:
            error_logger.error(e.args)

        return user_instance

    def _fetch_user_instance_from_mobile_no(self, mobile_no):
        user_instance = None
        try:
            user_mobiles = userMobiles.objects.get(mobile_no=mobile_no)
            user_instance = user_mobiles.user
        except Exception as e:
            error_logger.error(e.args)

        return user_instance

    def delete_user_query(self, user_instance):
        return User.objects.filter(id=user_instance.id).delete()

    def delete_user(self):

        if self.get_user_id():
            user_instance = self._fetch_user_instance(self.get_user_id())

            if user_instance:
                self.delete_user_query(user_instance)
                return True

            else:
                return False

        elif self.get_mobile_no():
            user_instance = self._fetch_user_instance_from_mobile_no(self.get_mobile_no())

            if user_instance:
                self.delete_user_query(user_instance)
                return True

            else:
                return False

    def survey_seen(self) -> dict:

        user_instance = User.get_user_or_none(self.get_user_id())

        if not user_instance:
            return {'error_message': "In-valid user id", 'success': False}

        survey_filter = ModelUtilities.get_model_filter(userSurvey, {'user': user_instance})

        if not survey_filter:
            userSurvey.create_instance({
                'user_instance': user_instance,
                'survey_seen': True
            })

        return {'success': True}

    @staticmethod
    def delete_notification_sending_details(user_instance, device_id) -> Union[int, dict]:

        delete_count = userDevices.objects.filter(user=user_instance, device_id=device_id).delete()

        return delete_count

    def logout(self, device_id) -> dict:

        user_instance = User.get_user_or_none(self.get_user_id())

        if not user_instance:
            return {'error_message': "In-valid user id", 'success': False}

        device_count = self.delete_notification_sending_details(user_instance, device_id)

        if device_count[0]:
            return {'success': True}

        return {'error_message': "In-valid device id", 'success': False}

    def _get_community_instances_for_user(self):
        community_id_list = get_community_id_list(self.get_user_id())
        community_instances = Community.objects.filter(id__in=community_id_list)

        return community_instances

    @staticmethod
    def _pre_compute_community_owners(community_instances_list):

        owner_dict = {}

        owner_instances = Members.objects.filter(community_id__in=community_instances_list, is_owner=True)

        for data in owner_instances:

            if data.community_id_id not in owner_dict:
                owner_dict[data.community_id_id] = data.member_id

        return owner_dict

    @staticmethod
    def _remove_all_community_profile(community_instances_list, user_instance):

        owner_dict = UserImpl._pre_compute_community_owners(community_instances_list)

        for community_instance in community_instances_list:

            current_user_instance = owner_dict.get(community_instance.id)

            if not current_user_instance:
                continue

            remove_members(community_instance, user_instance,
                           removed_state=1,
                           current_user_instance=current_user_instance)
            remove_all_member_rights(community_instance, user_instance)
            remove_all_manager_rights(community_instance, user_instance)

    @staticmethod
    def _update_user_information_for_remove_profile(user_instance):

        user_instance.username = REMOVED_PROFILE_NAME + "_" + str(TimeUtilities.current_time_in_milliseconds())
        user_instance.save()

        userinfo_instance = user_instance.userinfo
        userinfo_instance.name = REMOVED_PROFILE_NAME
        userinfo_instance.image_link = REMOVED_PROFILE_URL
        userinfo_instance.updated_at = TimeUtilities.current_time_in_sec()
        userinfo_instance.save()

    @staticmethod
    def _delete_profile_information(user_instance):

        userMobiles.objects.filter(user=user_instance).delete()
        userEmails.objects.filter(user=user_instance).delete()
        userDevices.objects.filter(user=user_instance).delete()

    def remove_profile(self):

        user_instance = User.get_user_or_none(self.get_user_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        community_instances_list = self._get_community_instances_for_user()
        self._update_user_information_for_remove_profile(user_instance)
        self._delete_profile_information(user_instance)
        self._remove_all_community_profile(community_instances_list, user_instance)

        return {'success': True}

    @staticmethod
    def _create_user_and_userinfo(user_context, phone_no):

        user_exists = ModelUtilities.is_model_filter_exists(User, {'username': phone_no})
        user_instance = None

        if not user_exists:
            user_instance = User()
            user_instance.username = phone_no
            user_instance.save()

            userinfo_instance = Userinfo()
            userinfo_instance.name = user_context['name']
            userinfo_instance.created_at = TimeUtilities.current_time_in_sec()
            userinfo_instance.user_id = user_instance
            userinfo_instance.image_link = UserHelper.process_image_url_for_processing(user_context,
                                                                                       user_instance)
            userinfo_instance.save()

        return user_instance

    def create_user_context_for_sdk(self, user_instance):

        user_object = {
            'success': True,
            'user': self.compute_logged_in_user(user_instance.userinfo),
            'email_exists': False,
            'access': UserHelper.is_user_belong_to_any_community(user_instance)
        }

        return user_object

    @staticmethod
    def _get_or_create_sdk_user_and_userinfo(user_context, api_key=None):

        user_unique_id = user_context.get('user_unique_id')
        user_instance = None
        unique_id = str(uuid.uuid4())
        sdk_client_user_info_instance = None
        community_instance = None

        if not user_unique_id:
            should_create_user = True

        else:

            if not api_key:
                return ResponseUtilities.get_error_context(False, "Invalid API key!")

            sdk_client_filter = ModelUtilities.get_model_filter(SdkClient, {'api_key': api_key})

            if not sdk_client_filter:
                return ResponseUtilities.get_error_context(False, "Invalid API key!")

            community_instance = sdk_client_filter[0].community

            sdk_client_users_info_filter = ModelUtilities.get_model_filter(SDKClientUsersInfo,
                                                                           {'community': community_instance,
                                                                            'user_unique_id': user_unique_id})

            if sdk_client_users_info_filter:
                sdk_client_user_info_instance = sdk_client_users_info_filter[0]
                return {'success': True,
                        'user_instance': sdk_client_user_info_instance.user,
                        'sdk_client_user_info_instance': sdk_client_user_info_instance}

            user_info_filter = ModelUtilities.get_model_filter(Userinfo, {'user_unique_id': user_unique_id})

            if user_info_filter:
                user_instance = user_info_filter[0].user_id
                return {'success': True,
                        'user_instance': user_instance,
                        'sdk_client_user_info_instance': sdk_client_user_info_instance}

            should_create_user = True

        if should_create_user:
            user_instance = User()
            user_instance.username = unique_id
            user_instance.save()

            userinfo_instance = Userinfo()
            userinfo_instance.name = user_context.get('user_name')
            userinfo_instance.created_at = TimeUtilities.current_time_in_sec()
            userinfo_instance.user_id = user_instance
            userinfo_instance.user_unique_id = unique_id
            userinfo_instance.is_bot = user_context.get('is_bot', False)
            userinfo_instance.save()

            if user_unique_id and community_instance:
                sdk_client_user_info_instance = SDKClientUsersInfo()
                sdk_client_user_info_instance.community = community_instance
                sdk_client_user_info_instance.user = user_instance
                sdk_client_user_info_instance.user_unique_id = user_unique_id
                sdk_client_user_info_instance.save()

        return {'success': True,
                'user_instance': user_instance,
                'sdk_client_user_info_instance': sdk_client_user_info_instance}

    @staticmethod
    def create_user_primary_email(user_instance, user_context, email_state=email_states.PRIMARY):

        email = user_context.get('email')

        if not email:
            return

        login_type = user_context.get('login_type')
        verified = False

        if login_type != "custom":
            verified = True

        user_exists = ModelUtilities.is_model_filter_exists(userEmails, {'verified': verified,
                                                                         'user': user_instance})

        if not user_exists:
            user_email_instance = userEmails()
            user_email_instance.user = user_instance
            user_email_instance.email_state = email_state
            user_email_instance.email = email
            user_email_instance.verified = verified
            user_email_instance.save()

    @staticmethod
    def create_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY):

        if not mobile_no:
            return

        mobile_exists = ModelUtilities.is_model_filter_exists(userMobiles, {'country_code': country_code,
                                                                            'mobile_no': mobile_no})

        if not mobile_exists:
            instance = userMobiles()
            instance.country_code = country_code
            instance.mobile_no = mobile_no
            instance.state = state
            instance.user = user_instance
            instance.created_at = TimeUtilities.current_time_in_sec()
            instance.save()

    @staticmethod
    def userinfo_serializer(userinfo_instance):

        return {'id': userinfo_instance.user_id_id,
                'name': userinfo_instance.name,
                'image_url': userinfo_instance.image_link,
                'user_unique_id': userinfo_instance.user_unique_id}

    def compute_logged_in_user(self, userinfo_instance):

        userinfo_context = self.userinfo_serializer(userinfo_instance)

        email_list = self.create_user_email_list(userinfo_instance)
        mobile_list = self.create_user_mobile_list(userinfo_instance)

        if email_list:
            userinfo_context['emails'] = email_list

        if mobile_list:
            userinfo_context['mobiles'] = mobile_list

        return userinfo_context

    def create_user_email_list(self, userinfo_instance):
        email_filter = userEmails.objects.filter(user=userinfo_instance.user_id_id)

        email_list = []

        for email_instance in email_filter:
            email_list.append(UserHelper.emailSerializer(email_instance))

        return email_list

    def create_user_mobile_list(self, userinfo_instance):
        mobile_filter = userMobiles.objects.filter(user=userinfo_instance.user_id_id)
        mobile_list = []

        for mobile_instance in mobile_filter:
            mobile_list.append(UserHelper.mobilesSerializer(mobile_instance))

        return mobile_list

    @staticmethod
    def send_email_verification_mails_for_custom_user(user_context, user_instance, userinfo_instance):

        if user_context.get('login_type') == "custom":

            email = user_context.get('email')

            if not email:
                return

            verification_details = UserHelper.generate_email_verification_token_for_custom_login(user_instance, email)

            if not verification_details.get('verify_url'):
                return

            send_verification_mail_for_email_sync.delay(user_name=userinfo_instance.name,
                                                        verification_link=verification_details['verify_url'],
                                                        email=email)

    @staticmethod
    def save_user_analytics_for_user_login(req_body, user_instance, platform_code, device_id, version_code):

        if req_body.get('user_acquisition_url'):
            user_acquired = UserHelper.decode_user_acquisition_url_for_login(user_instance,
                                                                             req_body['user_acquisition_url'],
                                                                             platform_code, device_id)
            UserHelper.create_userAcquition_analytics(user_instance, user_acquired, platform_code, version_code)

    def create_user_context_for_email_exists(self, email):

        if not email:
            return {}

        email_filter = ModelUtilities.get_model_filter(userEmails, {'email': email, 'verified': True})

        user_email_exists_object = {}

        if email_filter:
            user_instance = email_filter[0].user
            user_email_exists_object['success'] = True
            user_email_exists_object['user'] = self.compute_logged_in_user(user_instance.userinfo)
            user_email_exists_object['email_exists'] = True
            user_email_exists_object['access'] = UserHelper.is_user_belong_to_any_community(user_instance)

        return user_email_exists_object

    def login(self, req_body, platform_code, device_id, version_code, api_key: str = None) -> {}:

        login_type = req_body.get('type')

        try:
            user_context = UserHelper.validate_login_types(req_body)

        except Exception as e:
            error_logger.error(e)

            user_context = {}

        if not user_context:
            return {'success': False, 'error_message': "Invalid Login"}

        if login_type == str(api_types.SDK):
            sdk_user_context = self._get_or_create_sdk_user_and_userinfo(user_context, api_key=api_key)

            if not sdk_user_context.get('success'):
                return sdk_user_context

            return self.create_user_context_for_sdk(sdk_user_context.get('user_instance'))

        if (not login_type == str(api_types.SDK)) and not user_context.get('has_profile_image'):
            return {'success': False, 'user': user_context,
                    'error_message': "profile picture not available"}

        user_email_exists_object = self.create_user_context_for_email_exists(user_context.get('email'))

        if user_email_exists_object:

            return user_email_exists_object

        mobile_context = UserHelper.compute_mobile_no(req_body)

        if not mobile_context:
            return {'success': False, "error_message": "send mobile number in request body"}

        mobile_filter = ModelUtilities.get_model_filter(userMobiles,
                                                        {'mobile_no': mobile_context['mobile_no'],
                                                         'country_code': mobile_context['country_code']})

        if not mobile_filter:
            user_instance = self._create_user_and_userinfo(user_context, {'phone_no': mobile_context['phone_no']})
            self.create_user_mobile_number(user_instance,
                                           mobile_context['country_code'],
                                           mobile_context['mobile_no'])
            self.create_user_primary_email(user_instance, user_context)
            email_exists = False

        else:
            user_instance = mobile_filter[0].user
            email_exists = True

        userinfo_instance = user_instance.userinfo
        self.send_email_verification_mails_for_custom_user(user_context, user_instance, userinfo_instance)
        self.save_user_analytics_for_user_login(req_body, user_instance, platform_code, device_id, version_code)
        user_context = self.compute_logged_in_user(userinfo_instance)
        access = UserHelper.is_user_belong_to_any_community(user_instance)

        return {'success': True, 'user': user_context, 'access': access, 'email_exists': email_exists}

    def _process_user_communties_for_access(self, user_communities):
        """
        user_communties is a list of Members instances
        """
        context = {
            'pending_communities': [],
            'has_access': False,
            'community_id_list': []
        }

        for community in user_communities:
            if community.state == member_states.PENDING_MEMBER:
                context['pending_communities'].append(community.community_id)
                context['community_id_list'].append(community.community_id_id)

            else:
                context['has_access'] = True
                break

        return context

    def _fetch_expired_subscriptions_of_user(self, subscriptions):

        removed_community_ids = list(removedMembers.objects
                                     .filter(member__id=self.get_user_id(),
                                             removed_state=deleted_members.MEMBERSHIP_EXPIRED)
                                     .values_list("community_id", flat=True))

        current_time = TimeUtilities.current_time_in_milliseconds()

        community_ids = [subscription['community_id'] for subscription in subscriptions
                         if (current_time > subscription['valid_till_grace_period'] and
                             subscription['community_id'] in removed_community_ids)]

        return community_ids

    def _fetch_access_context_for_user(self, pending_communities, expired_communities):

        pending_count, subscription_count = len(pending_communities), len(expired_communities)

        if pending_count == 0 and subscription_count == 0:
            return CONTEXT_ACCESS_NOT_PART_OF_COMMUNITIES

        if pending_count == 1 and subscription_count == 0:

            context = CONTEXT_ACCESS_ONE_PENDING_COMMUNITY.copy()
            context['pending_communities'] = pending_communities

        elif pending_count == 0 and subscription_count == 1:

            community_id = expired_communities[0]['id']
            community_name = expired_communities[0]['name']

            context = CONTEXT_ACCESS_ONE_EXPIRED_COMMUNITY.copy()
            context['sub_title_1'] = SUB_TITLE_ACCESS_ONE_EXPIRED_COMMUNITY % (community_name, community_id, community_id)
            context['cta'] = CTA_ACCESS_ONE_EXPIRED_COMMUNITY % (community_id, self.get_user_id())
            context['membership_expired_communities'] = expired_communities

        elif pending_count > 1 and subscription_count == 0:
            context = CONTEXT_ACCESS_MORE_PENDING_COMMUNITIES.copy()
            context['pending_communities'] = pending_communities

        elif pending_count == 0 and subscription_count > 1:
            context = CONTEXT_ACCESS_MORE_EXPIRED_COMMUNITIES.copy()
            context['membership_expired_communities'] = expired_communities

        elif pending_count >= 1 and subscription_count == 1:

            community_id = expired_communities[0]['id']
            community_name = expired_communities[0]['name']

            context = CONTEXT_ACCESS_MORE_PENDING_ONE_EXPIRED_COMMUNITIES.copy()
            context['sub_title_1'] = SUB_TITLE_ACCESS_MORE_PENDING_ONE_EXPIRED_COMMUNITY % (community_name, community_id)
            context['pending_communities'] = pending_communities
            context['membership_expired_communities'] = expired_communities

        elif pending_count >= 1 and subscription_count > 1:
            context = CONTEXT_ACCESS_MORE_PENDING_MORE_EXPIRED_COMMUNITIES.copy()
            context['pending_communities'] = pending_communities
            context['membership_expired_communities'] = expired_communities

        else:
            context = CONTEXT_ACCESS_NOT_PART_OF_COMMUNITIES

        return context

    @staticmethod
    def fetch_user_verified_mobile_numbers(user_id_list):
        hash_map = {}

        user_mobiles = userMobiles.objects.filter(user__id__in=user_id_list)

        for num_instance in user_mobiles:
            serialized_instance = UserHelper.mobilesSerializer(num_instance)

            if num_instance.user_id in hash_map:
                hash_map[num_instance.user_id].append(serialized_instance)
            else:
                hash_map[num_instance.user_id] = [serialized_instance]

        return hash_map

    @staticmethod
    def fetch_user_verified_emails(user_id_list):
        hash_map = {}

        user_emails = userEmails.objects.filter(user__id__in=user_id_list)

        for email_instance in user_emails:
            serialized_instance = UserHelper.emailSerializer(email_instance)

            if email_instance.user_id in hash_map:
                hash_map[email_instance.user_id].append(serialized_instance)
            else:
                hash_map[email_instance.user_id] = [serialized_instance]

        return hash_map

    def fetch_app_access(self) -> dict:

        if not self.get_user_id():
            return CONTEXT_ACCESS_NOT_PART_OF_COMMUNITIES
        
        user_communities = Members.fetch_all_user_communties(self.get_user_id())

        user_community_data = self._process_user_communties_for_access(user_communities)

        if user_community_data['has_access']:
            return {'success': True, 'access': True}

        expired_subscriptions = UserHelper.fetch_user_subscriptions(self.get_user_id())

        expired_community_ids = self._fetch_expired_subscriptions_of_user(expired_subscriptions)

        total_community_ids = list(set(user_community_data['community_id_list']) | set(expired_community_ids))

        member_data = UserHelper.fetch_community_members_data(total_community_ids)

        pending_communities = UserHelper.serialize_community_for_access(user_community_data['pending_communities'], member_data)

        expired_community_instances = Community.objects.filter(pk__in=expired_community_ids)
        expired_communities = UserHelper.serialize_community_for_access(expired_community_instances, member_data)

        data = self._fetch_access_context_for_user(pending_communities=pending_communities,
                                                   expired_communities=expired_communities)

        return data

    def fetch_dm_home(self) -> dict:

        is_m2cm_v1 = m2cm_v1_version_check(self.get_platform_code(), self.get_version_code())
        is_m2cm_v2 = m2cm_v2_version_check(self.get_platform_code(), self.get_version_code())

        if not is_m2cm_v1:
            return {'success': True}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_user_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        admin = ModelUtilities.get_model_filter(Members, {"member_id": user_instance, "state": member_states.ADMIN})

        # Check whether member_id present in DirectMessageTutorial Table
        direct_message_tutorial = ModelUtilities.get_model_filter(DirectMessageTutorial, {"user_id": user_instance})

        if direct_message_tutorial.exists():
            direct_message_tutorial = direct_message_tutorial[0]

        else:
            direct_message_tutorial = None

        is_cm = False

        if self.get_community_id():
            admin = ModelUtilities.get_model_filter(Members, {
                "member_id": user_instance,
                "community_id_id": self.get_community_id(),
                "state": member_states.ADMIN})
            communities_list = [self.get_community_id()]

        else:
            communities_list = list(ModelUtilities.get_model_filter(Members, {
                "member_id": user_instance
            }).values_list(
                "community_id_id", flat=True))

        communities = ModelUtilities.get_model_filter(CommunitySettings,
                                                      {"community_id__in": communities_list,
                                                       "setting_type": community_setting_types.DIRECT_MESSAGES})

        dm_disabled_time = UserHelper.get_dm_disabled_time_for_members(communities)
        communities = communities.filter(enabled=True)
        community_ids_list = list(communities.values_list("community_id", flat=True))
        hide_dm_tab = False

        if admin.exists():

            is_cm = True

            if (not is_m2cm_v2) and direct_message_tutorial:

                if all([direct_message_tutorial.clicked, not direct_message_tutorial.messaged, not communities,
                        TimeUtilities.current_time_in_sec() >= TimeUtilities.add_hours_to_epoch_time(
                            direct_message_tutorial.updated_at, 168)]):

                    return {
                        "success": True,
                        "is_cm": is_cm
                    }

                unseen_count = UserHelper.get_unread_dm_messages_count(user_instance.id, community_ids_list)

                return {
                    "success": True,
                    "clicked": direct_message_tutorial.clicked,
                    "messaged": direct_message_tutorial.messaged,
                    "unread_dm_count": unseen_count,
                    "is_cm": is_cm
                }

            elif is_m2cm_v2:
                get_dm_chatrooms_state_list = get_dm_chatrooms_of_user(user_id=user_instance.id,
                                                                       community_id=community_ids_list)
                unseen_count = 0

                if get_dm_chatrooms_state_list:
                    get_dm_chatrooms_list = [card_id[1] for card_id in get_dm_chatrooms_state_list]
                    unseen_count = get_conversations_after_last_seen_messages_in_chatrooms(get_dm_chatrooms_list)

                if self.get_community_id():
                    hide_dm_tab = ModelUtilities.get_model_instance_or_none(Community, self.get_community_id()).hide_dm_tab

                return {
                    "success": True,
                    "unread_dm_count": unseen_count,
                    "is_cm": is_cm,
                    "hide_dm_tab": hide_dm_tab
                }

            else:
                return {"success": True, "clicked": False, "messaged": False, "is_cm": is_cm}

        else:

            if communities:

                if (not is_m2cm_v2) and direct_message_tutorial:

                    unseen_count = UserHelper.get_unread_dm_messages_count(user_instance.id, community_ids_list)

                    return {
                        "success": True,
                        "clicked": direct_message_tutorial.clicked,
                        "messaged": direct_message_tutorial.messaged,
                        "unread_dm_count": unseen_count,
                        "is_cm": is_cm
                    }

                elif is_m2cm_v2:
                    get_dm_chatrooms_state_list = get_dm_chatrooms_of_user(user_id=user_instance.id,
                                                                           community_id=community_ids_list)
                    get_dm_chatrooms_list = [card_id[1] for card_id in get_dm_chatrooms_state_list]
                    unseen_count = get_conversations_after_last_seen_messages_in_chatrooms(get_dm_chatrooms_list)
                    connection_requests_count = ModelUtilities.get_model_filter(
                        collabcardState, {'id__in': get_dm_chatrooms_list,
                                          'chat_request_state': chat_request_states.INITIATED}).exclude(
                        chat_requested_by=user_instance).count()

                    return {
                        "success": True,
                        "unread_dm_count": unseen_count + connection_requests_count,
                        "is_cm": is_cm
                    }

                else:
                    return {"success": True, "clicked": False, "messaged": False, "is_cm": is_cm}

            else:

                if TimeUtilities.current_time_in_sec() > dm_disabled_time:
                    return {"success": True, "is_cm": is_cm, "hide_dm_tab": True}

                else:
                    return {"success": True, "is_cm": is_cm, "hide_dm_tab": False, "hide_dm_text": HIDE_DM_TEXT}

    def update_dm_tutorial(self, req_body) -> {}:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_user_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        clicked = req_body.get("clicked")
        messaged = req_body.get("messaged")

        if (clicked is None) and (messaged is None):
            return {'success': False, 'error_message': "Please send either clicked or messaged."}

        # Get DirectMessageTutorial Instance
        dm_tutorial_instance = ModelUtilities.get_model_filter(DirectMessageTutorial, {"user_id": user_instance})

        if not dm_tutorial_instance:
            clicked = clicked if clicked is not None else False
            messaged = messaged if messaged is not None else False

            dm_tutorial_instance = DirectMessageTutorial.create_instance({"user_instance": user_instance,
                                                                          "clicked": clicked,
                                                                          "messaged": messaged})
            dm_tutorial_instance.save()

        else:
            dm_tutorial_instance = dm_tutorial_instance[0]
            dm_tutorial_instance.clicked = clicked if clicked is not None else dm_tutorial_instance.clicked
            dm_tutorial_instance.messaged = messaged if messaged is not None else dm_tutorial_instance.messaged
            dm_tutorial_instance.save()

        return {'success': True}

    def fetch_dm_feed(self, community_id: str) -> dict:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_user_id())
        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        filter_dict: dict = self._get_member_filter_for_dm_feed(self.get_user_id(), community_id)
        member_filter = ModelUtilities.get_model_filter(Members, filter_dict)

        if not member_filter.exists():
            error_message: str = 'User not a part of any community'
            if community_id:
                error_message: str = f'User not a part of community, id={str(community_id)}'

            return {"success": False, "error_message": error_message}

        cm_instances = member_filter.filter(state=member_states.ADMIN)
        member_instances = member_filter.filter(state=member_states.MEMBER)

        if cm_instances.exists():
            cm_instances_count = len(cm_instances)

            cta = "route://community_settings_select"

            if cm_instances_count == 1:
                community_instance = cm_instances[0].community_id

                query_params = {
                    "community_id": community_instance.id,
                    "community_name": community_instance.name
                }

                cta += f"?" + UrlUtilities.encode_query_url(query_params)

            response_context = UserHelper.get_dm_feed_response(member_filter, cta=cta, is_cm=True)

        else:
            response_context = UserHelper.get_dm_feed_response(member_filter)

        response_context["total_cm_communities_count"] = len(cm_instances)
        response_context["total_member_communities_count"] = len(member_instances)

        return response_context

    @staticmethod
    def _get_member_filter_for_dm_feed(member_id: str, community_id: str) -> dict:
        filter_dict: dict = dict({
            "member_id_id": member_id
        })
        if community_id:
            filter_dict['community_id_id'] = community_id

        return filter_dict


    @staticmethod
    def fetch_all_users(page, user_ids):

        user_filter = {}

        if user_ids is not None:
            user_filter['pk__in'] = user_ids

        user_instances = ModelUtilities.get_model_filter(User, user_filter)
        user_instances = ModelUtilities.paginate_queryset(user_instances, page, paginate_by=USER_LIST_PAGE_SIZE)

        user_serialized_instances = []
        for user_instance in user_instances:
            user_serialized_instances.append(get_logged_in_user(user_instance))

        response_context = {
            'users': user_serialized_instances,
            'success': True
        }

        return response_context

    def create_user_bot(self, req_body) -> dict:
        validated_request = UserViewHelper.validate_create_user_bot_request(req_body)

        if not validated_request.get('success'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_name = validated_request.get('community_name')

        user_context = {
            'user_name': CREATE_USER_BOT_NAME.format(community_name),
            'is_bot': True
        }

        sdk_user_context = self._get_or_create_sdk_user_and_userinfo(user_context)

        if not sdk_user_context.get('success'):
            return ResponseUtilities.get_impl_error_context(sdk_user_context.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        return self.create_user_context_for_sdk(sdk_user_context.get('user_instance'))

    def update_user_bot(self, req_body) -> dict:
        validated_request = UserViewHelper.validate_update_user_bot_request(self.get_user_id(), req_body)

        if not validated_request.get('success'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_name = validated_request.get('community_name')

        filter_dict = {
            'user_id': validated_request.get('user_instance')
        }

        update_dict = {
            'name': CREATE_USER_BOT_NAME.format(community_name)
        }

        ModelUtilities.update_or_create_model(Userinfo, filter_dict, update_dict)

        return self.create_user_context_for_sdk(validated_request.get('user_instance'))

    def fetch_user_bot(self, api_key: str = None) -> dict:
        validated_request = UserViewHelper.validate_fetch_user_bot_request(api_key)

        if not validated_request.get('success'):
            return ResponseUtilities.get_impl_error_context(validated_request.get('error_message'),
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_instance = validated_request.get('community_instance')

        user_instance = Members.get_community_owner_user_instance_or_none(community_instance)

        if not user_instance:
            return ResponseUtilities.get_impl_error_context('No owner in community',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        if user_instance.userinfo.is_bot:
            return self.create_user_context_for_sdk(user_instance)

        return ResponseUtilities.get_impl_error_context('Community bot not found',
                                                        status_code=status_codes.HTTP_400_BAD_REQUEST)

    def fetch_user_info(self) -> dict:
        user_instance = ModelUtilities.get_user_instance_or_none(self.get_user_id())

        if not user_instance:
            return ResponseUtilities.get_impl_error_context('Invalid user ID',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        return {'success': True, 'user': get_logged_in_user(user_instance)}


class UserHelper:

    @staticmethod
    def get_user_or_raise_exception(user_id):
        try:
            return User.objects.get(pk=user_id)
        except:
            response = {
                'success': False,
                'error_message': f'User with id {user_id} does not exist'
            }
            raise InvalidUserException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

    @staticmethod
    def compute_mobile_no(body):
        country_code = body.get('country_code', "")
        mobile_no = body.get('mobile_no', "")

        if not mobile_no or not country_code:
            return {}

        mobile_context = {'country_code': country_code,
                          'mobile_no': mobile_no,
                          'phone_no': str(country_code) + str(mobile_no)}

        return mobile_context

    @staticmethod
    def is_user_belong_to_any_community(user_instance):

        return Members.objects.filter(member_id=user_instance).filter(Q(state=member_states.ADMIN)
                                                                      | Q(state=member_states.MEMBER)
                                                                      | Q(
            state=member_states.PROFILE_UNAVAILABLE)).exists()

    @staticmethod
    def validate_login_types(req_body):
        login_type = req_body.get('type')

        if login_type == login_types.GOOGLE:

            return UserHelper.validate_google_login_object(req_body)

        elif login_type == login_types.FACEBOOK:

            return UserHelper.validate_facebook_login_object(req_body)

        elif login_type == login_types.LINKEDIN:

            return UserHelper.validate_linkedIn_login_object(req_body)

        elif login_type == login_types.LINKEDIN_WEB:

            return UserHelper.validate_linkedIn_web_login_object(req_body)

        elif login_type == login_types.APPLE:

            return UserHelper.validate_apple_login_object(req_body)

        elif login_type == login_types.CUSTOM:

            return UserHelper.validate_custom_login_object(req_body)

        elif login_type == str(api_types.SDK):
            return UserHelper.validate_sdk_login_object(req_body)

        else:
            return {}

    @staticmethod
    def validate_facebook_login_object(req_body):

        user_context = {}
        facebook_meta = req_body.get('login_json')
        user_context['name'] = facebook_meta['name']
        user_context['email'] = facebook_meta.get('email', '')

        if facebook_meta.get('picture'):

            facebook_pic_data = facebook_meta['picture']['data']

            if facebook_pic_data.get('is_silhouette'):
                user_context['has_profile_image'] = False

            else:
                user_context['has_profile_image'] = True
                user_context['image_url'] = facebook_pic_data['url']
        else:
            user_context['has_profile_image'] = False

        user_context['login_type'] = "facebook"

        return user_context

    @staticmethod
    def validate_linkedIn_login_object(req_body):

        user_context = {}
        linkedin_meta = req_body.get('login_json')

        user_name = linkedin_meta['firstName']['localized']['en_US'] + " " + linkedin_meta['lastName']['localized'][
            'en_US']

        if linkedin_meta.get('email'):
            email = linkedin_meta['email']['elements'][0]['handle~']['emailAddress']

        else:
            email = ''

        if linkedin_meta.get('profilePicture'):
            image_url = linkedin_meta['profilePicture']['displayImage~']['elements'][2]['identifiers'][0][
                'identifier']
            user_context['has_profile_image'] = True
            user_context['image_url'] = image_url

        else:
            user_context['has_profile_image'] = False

        user_context['name'] = user_name
        user_context['email'] = email

        user_context['login_type'] = "linkedIn"

        return user_context

    @staticmethod
    def validate_apple_login_object(req_body):

        user_context = {}
        apple_meta = req_body.get('login_json')
        user_context['name'] = apple_meta['name']
        user_context['email'] = apple_meta.get('email', '')

        if apple_meta.get('picture'):
            user_context['has_profile_image'] = True
            user_context['image_url'] = apple_meta['picture']['data']['url']
        else:
            user_context['has_profile_image'] = False

        user_context['login_type'] = "apple"

        return user_context

    @staticmethod
    def validate_custom_login_object(req_body):

        user_context = {}
        custom_meta = req_body.get('user', {})
        user_context['name'] = custom_meta.get('name')
        user_context['email'] = custom_meta.get('email', '')

        if custom_meta.get('image_url'):
            user_context['image_url'] = custom_meta.get('image_url')
            user_context['has_profile_image'] = True

        else:
            user_context['has_profile_image'] = False

        user_context['login_type'] = "custom"

        return user_context

    @staticmethod
    def validate_sdk_login_object(req_body):

        user_context = {}

        if not req_body.get('user_name'):
            return user_context

        user_context['user_name'] = req_body.get('user_name')

        if req_body.get('user_unique_id'):
            user_context['user_unique_id'] = req_body.get('user_unique_id')

        if req_body.get('api_key'):
            user_context['api_key'] = req_body.get('api_key')

        return user_context

    @staticmethod
    def generate_email_verification_token_for_custom_login(user_instance, email):

        if not email:
            return

        token_list = list(emailTokens.objects.filter(user=user_instance).values_list('token', flat=True))

        verification_details = UserHelper.generating_verification_link_for_custom_login_user(token_list,
                                                                                             user_instance.id)

        instance = emailTokens()
        instance.user = user_instance
        instance.token = verification_details['token']
        instance.expire_time = VERIFICATION_EMAIL_EXPIRE_TIME  # 24 hours
        instance.email = email
        instance.email_state = 0
        instance.save()

        return verification_details

    @staticmethod
    def generating_verification_link_for_custom_login_user(token_list, user_id):
        """function to generate verification link for email and saving the email"""

        url = settings.URL
        token = generate_random(token_list)

        verify_url = url + "/api/email_verify?token=" + str(token) + "&user=" + str(user_id)

        temp = {'verify_url': verify_url, 'token': token}

        return temp

    @staticmethod
    def process_image_url_for_processing(user_context, user_instance):

        image_url = user_context.get('image_url')

        if not image_url:
            return ''

        if user_context.get('login_type') == "custom":

            return image_url

        return upload_image_to_firebase(image_url, user_instance.id)

    @staticmethod
    def fetch_auth_data_for_google_login(google_id_token):

        params = {'id_token': google_id_token}
        google_json = {}

        try:
            response = rqst.get("https://oauth2.googleapis.com/tokeninfo", params=params)
            response = response.text
            google_json = json.loads(response)

        except Exception as e:
            error_logger.error(e)

        return google_json

    @staticmethod
    def validate_google_login_object(req_body):

        google_id_token = req_body.get('google_id_token')

        google_json = UserHelper.fetch_auth_data_for_google_login(google_id_token)
        user_context = {'name': google_json['name'],
                        'email': google_json.get('email', '')}

        image_url = google_json.get('picture', '')

        if image_url:

            index = image_url.find(GOOGLE_REGEX)

            if index == -1:
                user_context['image_url'] = image_url
                user_context['has_profile_image'] = True
            else:
                user_context['has_profile_image'] = False

        else:
            user_context['has_profile_image'] = False

        user_context['login_type'] = "google"

        return user_context

    @staticmethod
    def fetch_auth_data_for_linkedIn_web_login(req_body):
        code = req_body.get('code', None)

        if not code:
            return {}

        response = UserHelper.generate_access_toke_for_linkedIn_web(req_body)

        if 'access_token' not in response:
            return {}

        return UserHelper.fetch_user_details_from_access_token(response['access_token'])

    @staticmethod
    def fetch_user_details_from_access_token(access_token):

        user_url = LINKED_IN_WEB_USER_URL + access_token
        email_url = LINKED_IN_WEB_EMAIL_URL + access_token

        # getting public details of user from Linked In
        try:
            resp = rqst.get(user_url)
            data_main = json.loads(resp.text)
            resp = rqst.get(email_url)
            email_data = json.loads(resp.text)
            data_main['email'] = email_data
        except Exception as e:
            error_logger.error(e)

            return {}

        return data_main

    @staticmethod
    def generate_access_toke_for_linkedIn_web(req_body):
        code = req_body.get('code', None)
        grant_type = req_body.get('grant_type', None)
        redirect_uri = req_body.get('redirect_uri', None)
        client_id = req_body.get('client_id', None)
        client_secret = req_body.get('client_secret', None)

        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': grant_type,
            'redirect_uri': redirect_uri,
            'code': code
        }

        ans = rqst.post(LINKED_IN_WEB_ACCESS_TOKEN_URL, params=params)
        response = ans.json()

        return response

    @staticmethod
    def validate_linkedIn_web_login_object(req_body):

        linkedIn_web_meta = UserHelper.fetch_auth_data_for_linkedIn_web_login(req_body)
        user_context = {}

        user_name = linkedIn_web_meta['firstName']['localized']['en_US'] + " " + \
                    linkedIn_web_meta['lastName']['localized'][
                        'en_US']

        if linkedIn_web_meta.get('email'):
            email = linkedIn_web_meta['email']['elements'][0]['handle~']['emailAddress']

        else:
            email = ''

        if linkedIn_web_meta.get('profilePicture'):
            image_url = linkedIn_web_meta['profilePicture']['displayImage~']['elements'][2]['identifiers'][0][
                'identifier']
            user_context['has_profile_image'] = True
            user_context['image_url'] = image_url

        else:
            user_context['has_profile_image'] = False

        user_context['name'] = user_name
        user_context['email'] = email

        user_context['login_type'] = "linkedIn_web"

        return user_context

    @staticmethod
    def decode_landing_type_from_login_url(user_acquisition_url):

        url_path_dict = {}

        try:
            url_path = parse.urlparse(user_acquisition_url).path

            path_list = url_path.split("/")

            if path_list[1] == "community":
                url_path_dict['landing_type'] = "community_join"
                url_path_dict['community_id'] = path_list[2]

            elif path_list[1] == "collabcard":
                url_path_dict['landing_type'] = "chatroom_join"
                url_path_dict['chatroom_id'] = path_list[2]

            elif path_list[1] == "create_community":
                url_path_dict['landing_type'] = CM_ONBOARDING_LANDING_TYPE

        except Exception as e:
            error_logger.error(e)

        return url_path_dict

    @staticmethod
    def decode_user_acquisition_url_for_login(user_instance, user_acquisition_url, platform_code, device_id):

        user_acquired = {}
        url_path_dict = UserHelper.decode_landing_type_from_login_url(user_acquisition_url)

        try:
            query_def = parse.parse_qs(parse.urlparse(user_acquisition_url).query)

            if query_def.get('aj'):
                user_acquired['link_type'] = "private"
            else:
                user_acquired['link_type'] = "public"

            user_acquired['user_id'] = user_instance.id

            user_acquired.update(url_path_dict)

            if query_def.get('utm_source'):
                user_acquired['utm_source'] = query_def['utm_source'][0]

            if query_def.get('utm_medium'):
                user_acquired['utm_medium'] = query_def['utm_medium'][0]

            if query_def.get('utm_campaign'):
                user_acquired['utm_campaign'] = query_def['utm_campaign'][0]

            if query_def.get('shared_by'):
                user_acquired['shared_by'] = query_def['shared_by'][0]

            if query_def.get('source'):

                if query_def['source'][0] == "members_directory":
                    user_acquired['landing_type'] = "directory_link"

            if platform_code:
                user_acquired['platform'] = platform_code

            if device_id:
                user_acquired['device_id'] = device_id

        except Exception as e:
            error_logger.error(e)

        return user_acquired

    @staticmethod
    def create_userAcquition_analytics(user_instance, user_acquired, platform_code, version_code):
        '''saving the analytics of acquired user'''

        user_filter = userAcquition.objects.filter(user=user_instance)

        if not user_filter.exists():

            instance = userAcquition()
            instance.user = user_instance
            instance.landing_type = user_acquired['landing_type'] if 'landing_type' in user_acquired else ''
            instance.link_type = user_acquired['link_type'] if 'link_type' in user_acquired else ''

            instance.utm_source = user_acquired['utm_source'] if 'utm_source' in user_acquired else ''
            instance.utm_campaign = user_acquired['utm_campaign'] if 'utm_campaign' in user_acquired else ''
            instance.utm_medium = user_acquired['utm_medium'] if 'utm_medium' in user_acquired else ''
            instance.platform = user_acquired['platform'] if 'platform' in user_acquired else ''

            instance.device_id = user_acquired['device_id'] if 'device_id' in user_acquired else ''

            if 'community_id' in user_acquired and user_acquired['community_id']:
                community_instance = Community.get_community_or_None(user_acquired['community_id'])

                if not community_instance:
                    log = "incorrect community id : %s" % (user_acquired['community_id'])
                    error_logger.error(log)

                    return

                instance.community = community_instance

            if user_acquired.get('shared_by'):
                shared_user_instance = ModelUtilities.get_model_instance_or_none(User,
                                                                                 user_acquired.get('shared_by'))
                instance.shared = shared_user_instance

            if user_acquired.get('chatroom_id'):

                card_instance = Collabcard.get_chatroom_or_None(user_acquired['chatroom_id'])

                if not card_instance:
                    log = "incorrect chatroom id : %s" % (user_acquired['chatroom_id'])
                    error_logger.error(log)

                    return
                instance.chatroom = card_instance

            instance.save()

            if cm_onboarding_version_check(platform_code, version_code) and \
                    (instance.landing_type == CM_ONBOARDING_LANDING_TYPE):
                task_begin_time = TimeUtilities.add_hours_to_epoch_time(TimeUtilities.current_time_in_sec(), hours=1)
                task_expiry_time = TimeUtilities.add_hours_to_epoch_time(TimeUtilities.current_time_in_sec(), hours=2)

                UserHelper.cm_send_email_for_creating_community.apply_async(args=[instance.user_id], kwargs={},
                                                                            eta=TimeUtilities.convert_epoch_to_datetime_in_IST(task_begin_time),
                                                                            expires=TimeUtilities.convert_epoch_to_datetime_in_IST(task_expiry_time))

    @staticmethod
    @shared_task
    def cm_send_email_for_creating_community(user_id):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        print(user_instance)

        if not user_instance:
            return

        members_filter = ModelUtilities.get_model_filter(Members, {'member_id': user_id,
                                                                   'state': member_states.ADMIN,
                                                                   'is_owner': True})

        if members_filter:
            mail_subject = FIRST_LOGIN_NON_FORM_CM_MAIL_SUBJECT

            mail_template = get_template('mails/cm_onboarding/cm_dropoff_mail_cm_onboarding.html').render({
                "community_logo": LIKEMINDS_LOGO,
                "community_name": 'LikeMinds',
                "cm_name": user_instance.userinfo.name,
                "community_brand_color": DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR,
                "button_text": FIRST_LOGIN_NON_FORM_CM_MAIL_BUTTON_TEXT,
                "button_link": CM_ONBOARDING_CREATE_COMMUNITY_BRANCH_LINK
            })
            mail_categories = MailHelper.get_email_category_list_using_category_subcategory(
                EmailCategories.CREATE_COMMUNITY, EmailSubCategories.DROPOFF)

            send_email_response = MailWrapper.send_email(mail_subject, mail_template, [user_instance.userinfo.email],
                                                         categories=mail_categories,
                                                         reply_to=[FIRST_LOGIN_NON_FORM_CM_REPLY_EMAIL])

            return

    @staticmethod
    def emailSerializer(email_instance):

        return {
                'id': email_instance.id,
                'user_id': email_instance.user_id,
                'email': email_instance.email,
                'state': email_instance.email_state,
                'verified': email_instance.verified
            }

    @staticmethod
    def mobilesSerializer(mobile_instance):

        return {

            'id': mobile_instance.id,
            'user_id': mobile_instance.user_id,
            'mobile_no': mobile_instance.mobile_no,
            'country_code': mobile_instance.country_code,
            'state': mobile_instance.state
        }

    @staticmethod
    def fetch_user_subscriptions(user_id, community_id=None):
        client = ApiClient(host=subscription_url,
                           method='get',
                           path=SUBSCRIPTION_FETCH_API_PATH)

        if community_id:
            client.add_url_param('community_id', community_id)

        client.add_header('x-member-id', user_id).request()

        response = client.fetch_response()

        if response.get('success'):
            return response['subscriptions']

        return []

    @staticmethod
    def fetch_community_members_data(community_id_list):
        communities = Members.fetch_community_members(community_id_list)

        community_dict = {}

        creator = None
        manager_count = 0
        members_count = 0
        current_community_id = None

        for community in communities:

            if current_community_id != community.community_id_id:

                creator = None
                manager_count = 0
                members_count = 0
                current_community_id = community.community_id_id

            if creator is None:
                creator = community.member_id

            if community.state == member_states.ADMIN:
                manager_count += 1

            members_count += 1

            creator_name = creator.userinfo.name if creator else None

            context = {
                'promoters_count': manager_count,
                'members_count': members_count
            }

            if creator_name:
                context['created_by'] = creator_name

            community_dict[community.community_id_id] = context

        return community_dict

    @staticmethod
    def serialize_community_for_access(communities, community_member_data):
        data = CommunitySerializerV1(communities, many=True).data

        for community in data:
            if community_member_data.get(community['id']):
                community.update(community_member_data.get(community['id']))

        return data

    @staticmethod
    def get_unread_dm_messages_count(user_id, community_ids):
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not user_instance:
            return 0

        conversation_engage_filter = ModelUtilities.get_model_filter(conversationEngage,
                                                                     {"user": user_instance,
                                                                      "community_id__in": community_ids,
                                                                      "card__is_private": True}).exclude(
            card__chatroom_with_user=None)

        unseen_count = conversation_engage_filter.aggregate(total_unseen_count=Sum('unseen_count'))

        return unseen_count["total_unseen_count"] if unseen_count["total_unseen_count"] else 0

    @staticmethod
    def get_dm_feed_response(member_instances, cta=None, is_cm=False):
        community_ids_list = list(member_instances.values_list("community_id_id", flat=True))

        community_rights = ModelUtilities.get_model_filter(CommunitySettings,
                                                           {"community__in": community_ids_list,
                                                            "setting_type": community_setting_types.DIRECT_MESSAGES,
                                                            "enabled": True})

        if is_cm:

            if community_rights.exists():
                return {"success": True}

            else:

                disclaimer = {
                    "title": "Feature not enabled yet.",
                    "subtitle": "To enable direct message with your community members, go to <<community "
                                f"settings|{cta}>> and enable direct messages in your community.",
                    "cta": cta
                }

                return {"success": True, "disclaimer": disclaimer}

        else:

            if community_rights.exists():
                return {"success": True}

            else:
                return {"success": False, "error_message": "Direct messages are disabled for this community."}

    @staticmethod
    def get_dm_disabled_time_for_members(community_settings_filter):
        dm_disabled_time = max([i if i else 0 for i in list(community_settings_filter.values_list("updated_at",
                                                                                                  flat=True))])

        if not dm_disabled_time:
            dm_disabled_time = max([i if i else 0 for i in list(community_settings_filter.values_list("created_at",
                                                                                                      flat=True))])

        return TimeUtilities.add_hours_to_epoch_time(dm_disabled_time, ONE_DAY_HOURS)
