from togther.models import userMobiles, ModelUtilities, userSurvey, userDevices, Community, Members, userEmails
from django.contrib.auth.models import User
from collabmates_api.user.user_manager import UserManager
from external_services.logging.logging_wrapper import LoggingWrapper
from typing import Tuple
from utility.exception_utilities import InvalidUserException
from rest_framework import status as status_codes

from utility.time_utilities import TimeUtilities
from .constants import REMOVED_PROFILE_NAME, REMOVED_PROFILE_URL
from ..raw_queries import get_community_id_list
from ..views import remove_members, remove_all_member_rights, remove_all_manager_rights

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class UserImpl(UserManager):
    user_id = None
    mobile_no = None

    def __init__(self, user_id: str, mobile_no: str):
        self.user_id = user_id
        self.mobile_no = mobile_no

    def get_user_id(self):
        return self.user_id

    def set_user_id(self, user_id):
        self.user_id = user_id

    def get_mobile_no(self):
        return self.mobile_no

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
    def delete_notification_sending_details(user_instance, device_id) -> Tuple[int, dict]:

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

            remove_members(community_instance.id, user_instance.id,
                           removed_state=1,
                           current_user_instance=current_user_instance)
            remove_all_member_rights(community_instance, user_instance)
            remove_all_manager_rights(community_instance, user_instance)

    @staticmethod
    def _update_user_information_for_remove_profile(user_instance):

        user_instance.username = REMOVED_PROFILE_NAME + "_"+str(TimeUtilities.current_time_in_milliseconds())
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
