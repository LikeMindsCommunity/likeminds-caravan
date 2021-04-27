from togther.models import userMobiles,ModelUtilities, userSurvey
from django.contrib.auth.models import User
from collabmates_api.user.user_manager import UserManager
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.exception_utilities import InvalidUserException
from rest_framework import status as status_codes

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
