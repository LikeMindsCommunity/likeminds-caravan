from django.db.models import Q
from collabmates_api.rest_api import SDKClientUsersInfoSerializer
from collabmates_api.serializers import UserinfoSerializer
from utility.firebase import upload_image_to_firebase
from utility.time_utilities import TimeUtilities
from utility.response_utilities import ResponseUtilities
from togther.models import (Community, CommunitySettings, Members, ModelUtilities, Userinfo, communityQuestions, SDKClientUsersInfo, removedMembers, userEmails, userMobiles)
from utility.states import (login_types)
from utility.validation_utilities import ValidationUtilities
from .models import SdkClient, SdkOnboardingScreen
from django.contrib.auth.models import User
from django.db import IntegrityError
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.states import email_states, mobile_states, member_states, login_types, community_setting_types, GuestFlowUserTypes, CommunityConfigurationTypes
import uuid
import re

error_logger = LoggingWrapper.get_instance()

class SdkViewHelper:

    @staticmethod
    def _member_id_validator(member_id):

        if not member_id:
            return ResponseUtilities.get_inner_error_context('send member_id in headers')

        member = ModelUtilities.get_user_instance_or_none(member_id)

        if not member:
            return ResponseUtilities.get_inner_error_context('Invalid x-member-id')

        return {'user_instance': member}

    @staticmethod
    def fetch_sdk_project_validator(request_params, member_id):

        if not request_params:
            return ResponseUtilities.get_inner_error_context('invalid request params')

        if 'project_creator' not in request_params and not request_params.get('project_creator'):
            return ResponseUtilities.get_inner_error_context('send project_creator in params')

        project_creator = ModelUtilities.get_user_instance_or_none(request_params.get('project_creator'))

        if not project_creator:
            return ResponseUtilities.get_inner_error_context('Invalid project_creator')

        member_validator = SdkViewHelper._member_id_validator(member_id)

        if 'error_message' in member_validator:
            return member_validator

        return {'project_creator': project_creator}

    @staticmethod
    def create_sdk_project_body_validator(request_body, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        member_validator = SdkViewHelper._member_id_validator(member_id)

        if 'error_message' in member_validator:
            return member_validator

        if 'project_creator' not in request_body or not request_body.get('project_creator'):
            return ResponseUtilities.get_inner_error_context('send project_creator in body')

        project_creator = ModelUtilities.get_user_instance_or_none(request_body.get('project_creator'))

        if not project_creator:
            return ResponseUtilities.get_inner_error_context('Invalid project_creator')

        if 'name' not in request_body or not request_body.get('name'):
            return ResponseUtilities.get_inner_error_context('send name in body')

        if 'platform' in request_body and request_body['platform'] and not isinstance(request_body['platform'], list):
            return ResponseUtilities.get_inner_error_context('platform object should be a list')

        return {'project_creator': project_creator}

    @staticmethod
    def edit_sdk_project_body_validator(request_body, member_id, api_key):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('Invalid request body')

        req_body = request_body.copy()

        if 'name' in req_body and req_body['name']:
            req_body['community_name'] = req_body['name']
            del req_body['name']

        if 'headline' in req_body and req_body['headline']:
            req_body['purpose'] = req_body['headline']
            del req_body['headline']

        if not member_id:
            return ResponseUtilities.get_inner_error_context('Send member_id in headers')

        member = ModelUtilities.get_user_instance_or_none(member_id)

        if not member:
            return ResponseUtilities.get_inner_error_context('Invalid x-member-id')

        if not api_key:
            return ResponseUtilities.get_inner_error_context('Send api_key in headers')

        if 'platform' in request_body and request_body['platform'] and not isinstance(request_body['platform'], list):
            return ResponseUtilities.get_inner_error_context('platform object should be a list')

        return {'req_body': req_body}

    @staticmethod
    def delete_sdk_project_validator(member_id):

        member_validator = SdkViewHelper._member_id_validator(member_id)

        if 'error_message' in member_validator:
            return member_validator

        return {'user_instance': member_validator.get('user_instance')}

    @staticmethod
    def initiate_sdk_body_validator(community_id, request_body):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('invalid request body')

        user_name = request_body.get('user_name')
        user_object = request_body.get('user')

        if (not user_name) and user_object:
            user_name = user_object.get('name')

        if request_body.get('is_guest'):

            if not user_name:
                user_name = "Guest User"

        if not (user_name or request_body.get('user_unique_id')):
            return ResponseUtilities.get_inner_error_context('send user_name in body')

        login_req_body = {
            'type': login_types.SDK,
            'user': {
                'name': user_name,
                'is_guest': request_body.get('is_guest', False)
            }
        }

        if user_object:
            login_req_body['user'] = user_object

        join_req_body = {}

        if ('user_unique_id' in request_body) and request_body.get('user_unique_id'):
            login_req_body['user']['user_unique_id'] = request_body.get('user_unique_id')

        if ('image_url' in request_body) and request_body.get('image_url'):
            login_req_body['user']['image_url'] = request_body.get('image_url')
            join_req_body['image_url'] = request_body.get('image_url')

        elif user_object and 'image_url' in user_object:
            join_req_body['image_url'] = user_object.get('image_url')

        if request_body.get('question_answers'):
            questions_filter = ModelUtilities.get_model_filter(communityQuestions, {'community': community_id})
            question_ids_list = list(questions_filter.values_list('id', flat=True))
            req_question_ids_list = [question.get('question_id') for question in request_body.get('question_answers')]

            if set(req_question_ids_list) - set(question_ids_list):
                return ResponseUtilities.get_inner_error_context('Invalid community questions list!')

            join_req_body['question_answers'] = request_body.get('question_answers')

        if request_body.get('shared_by'):
            join_req_body['shared_by'] = request_body.get('shared_by')

        return {'login_req_body': login_req_body, 'join_req_body': join_req_body}

    @staticmethod
    def fetch_onboarding_screens_validator(request_params, api_key):

        if not api_key:
            return ResponseUtilities.get_inner_error_context('Send api_key in headers')

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        filters = {
            'community': community_instance
        }

        if request_params.get('screen_id', None):
            filters['id'] = request_params['screen_id']

        onboarding_screens = ModelUtilities.get_model_filter(SdkOnboardingScreen, filters).order_by('index',
                                                                                                    '-updated_at')

        return {'onboarding_screens': onboarding_screens}

    @staticmethod
    def create_onboarding_screen_validator(request_body, api_key, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('Invalid request body')

        if request_body.get('index', -1) < 0:
            return ResponseUtilities.get_inner_error_context('Send valid screen index')

        if not request_body.get('image'):
            return ResponseUtilities.get_inner_error_context('Send valid image url')

        member_validator = SdkViewHelper._member_id_validator(member_id)

        if 'error_message' in member_validator:
            return member_validator

        if not api_key:
            return ResponseUtilities.get_inner_error_context('Send api_key in headers')

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        screen = ModelUtilities.get_model_filter(SdkOnboardingScreen, {'community': community_instance,
                                                                       'index': request_body.get('index')})

        if screen:
            return ResponseUtilities.get_inner_error_context("Screen already exists with given index")

        return {'user_instance': member_validator.get('user_instance'), 'community_instance': community_instance}

    @staticmethod
    def edit_onboarding_screen_validator(request_body, api_key, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('Invalid request body')

        if not request_body.get('id'):
            return ResponseUtilities.get_inner_error_context('Send valid id')

        if 'index' in request_body and not request_body.get('index'):
            return ResponseUtilities.get_inner_error_context('Send valid screen index')

        if 'image' in request_body and not request_body.get('image'):
            return ResponseUtilities.get_inner_error_context('Send valid image url')

        member_validator = SdkViewHelper._member_id_validator(member_id)

        if 'error_message' in member_validator:
            return member_validator

        if not api_key:
            return ResponseUtilities.get_inner_error_context('Send api_key in headers')

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        screen = ModelUtilities.get_model_instance_or_none(SdkOnboardingScreen, request_body.get('id'))

        if not screen:
            return ResponseUtilities.get_inner_error_context("Invalid screen id sent")

        return {'user_instance': member_validator.get('user_instance'), 'community_instance': community_instance,
                'screen_instance': screen}

    @staticmethod
    def delete_onboarding_screen_validator(request_body, api_key, member_id):

        if not request_body:
            return ResponseUtilities.get_inner_error_context('Invalid request body')

        if not request_body.get('id'):
            return ResponseUtilities.get_inner_error_context('Send valid id')

        member_validator = SdkViewHelper._member_id_validator(member_id)

        if 'error_message' in member_validator:
            return member_validator

        if not api_key:
            return ResponseUtilities.get_inner_error_context('Send api_key in headers')

        community_instance = SdkClient.get_community_instance_or_none(api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid API key!")

        screen = ModelUtilities.get_model_instance_or_none(SdkOnboardingScreen, request_body.get('id'))

        if not screen:
            return ResponseUtilities.get_inner_error_context("Invalid screen id sent")

        return {'user_instance': member_validator.get('user_instance'), 'community_instance': community_instance,
                'screen_instance': screen}

    @staticmethod
    def validate_fetch_sdk_user_info_request(user_id: str, api_key: str, member_uuid: str):
        validation_params = {
            'user_id': user_id,
            'community_id': {
                'api_key': api_key
            }
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict

        community_instance = validated_dict.get('community_id')

        sdk_client_users_info_filter = ModelUtilities.get_model_filter(
            SDKClientUsersInfo, {'community': community_instance}).filter(
            Q(user_unique_id=member_uuid) | Q(user__userinfo__user_unique_id=member_uuid))

        if not sdk_client_users_info_filter:
            return ResponseUtilities.get_inner_error_context('Invalid uuid!')

        app_access = True

        sdk_client_users_info_filter = sdk_client_users_info_filter.first()

        removed_member = ModelUtilities.get_model_filter(removedMembers,
                                                         {'community': community_instance,
                                                          'member': sdk_client_users_info_filter.user})

        if len(removed_member):
            app_access = False

        return {
            'user_instance': validated_dict.get('user_id'),
            'community_instance': community_instance,
            'uuid_sdk_client_instance': sdk_client_users_info_filter,
            'app_access': app_access
        }

    @staticmethod
    def get_mau_overview_validator(request_params, member_id, api_key):

        no_of_months = request_params.get('no_of_months')

        if 'no_of_months' not in request_params or not no_of_months:
            validated_request_params = request_params.copy()
            
            validated_request_params['no_of_months'] = '6'
            no_of_months = '6'
        else:
            validated_request_params = request_params

        if not no_of_months.isdigit() or (int(no_of_months) <= 0):
            return ResponseUtilities.get_inner_error_context('no_of_months should be a positive integer')

        # member_id and api_key validation
        validation_params = {
            'user_id': member_id,
            'community_id': {
                'api_key': api_key
            }
        }

        validated_dict = ValidationUtilities.is_valid(validation_params=validation_params)

        if validated_dict.get('error_message'):
            return validated_dict
        
        return {
            'request_params': validated_request_params,
            'user_instance': validated_dict.get('user_id'),
            'community_instance': validated_dict.get('community_id')
        }

    @staticmethod
    def sdk_login_user_validator(req_body):

        # user_meta = req_body.get('user', {})

        # if not user_meta.get('name'):
        #     return {}

        user_context = {
            'name': req_body.get('name'),
            'email': req_body.get('email', ''),
            'organisation_name': req_body.get('organisation_name'),
            'mobile_no': int(req_body.get('mobile_no')),
            'country_code': int(req_body.get('country_code')),
        }

        if req_body.get('image_url'):
            user_context['image_url'] = req_body.get('image_url')
            user_context['has_profile_image'] = True

        else:
            user_context['has_profile_image'] = False

        return user_context

    @staticmethod
    def _get_or_create_sdk_user_and_userinfo(user_context):

        user_email = user_context.get('email')
        user_mobile_no = user_context.get('mobile_no')
        user_country_code = user_context.get('country_code')
        user_instance = None
        unique_id = str(uuid.uuid4())
        existing_user = False
        app_access = True
        
        if not user_email:
            return ResponseUtilities.get_inner_error_context("User email not found")
        
        validated_email = SdkViewHelper.is_valid_email(user_email)

        if not validated_email:
            return ResponseUtilities.get_inner_error_context("User email is not valid")

        should_create_user = True
        user_info_filter = None

        existing_user_ids_with_email = list(ModelUtilities.get_model_filter(userEmails,
                                                                            {'email': validated_email}).values_list(
            'user_id', flat=True))

        if existing_user_ids_with_email:
            user_info_filter = ModelUtilities.get_model_filter(Userinfo, {'user_id_id__in': existing_user_ids_with_email})

        if user_info_filter:
            existing_user = True
            user_info_instance = user_info_filter[0]

            removed_member = ModelUtilities.get_model_filter(removedMembers,
                                                    {'member': user_info_instance.user_id_id})

            if len(removed_member):
                app_access = False
        
            return {'user_info_instance': user_info_instance,
                    'is_existing_user': existing_user,
                    'app_access': app_access}

        if should_create_user:

            if not user_context.get('name'):
                return ResponseUtilities.get_inner_error_context("Invalid user name!")

            user_instance = User()
            user_instance.username = unique_id
            user_instance.save()

            userinfo_instance = Userinfo()
            userinfo_instance.name = user_context.get('name')
            userinfo_instance.created_at = TimeUtilities.current_time_in_sec()
            userinfo_instance.user_id = user_instance
            userinfo_instance.user_unique_id = unique_id
            userinfo_instance.image_link = SdkViewHelper.process_image_url_for_processing(user_context, user_instance)
            userinfo_instance.organisation_name = user_context.get('organisation_name')
            userinfo_instance.save()

            if user_mobile_no and user_country_code:
                SdkViewHelper.create_user_mobile_number(user_instance,
                                                   user_country_code,
                                                   user_mobile_no,
                                                   force_create_instance=True)

            if user_context.get('email'):
                SdkViewHelper.create_user_primary_email(user_instance, user_context)

        return {'user_info_instance': userinfo_instance,
                'is_existing_user': existing_user,
                'app_access': app_access}
    
    @staticmethod
    def create_user_primary_email(user_instance, user_context, email_state=email_states.PRIMARY):

        email = user_context.get('email')

        if not email:
            return

        login_type = user_context.get('login_type')
        verified = False

        if login_type not in [login_types.CUSTOM]:
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
    def create_user_mobile_number(user_instance, country_code, mobile_no, state=mobile_states.PRIMARY,
                                  force_create_instance: bool = False):

        if not mobile_no:
            return

        mobile_exists = True

        if not force_create_instance:
            mobile_exists = ModelUtilities.is_model_filter_exists(userMobiles, {'country_code': country_code,
                                                                                'mobile_no': mobile_no})

        if force_create_instance or not mobile_exists:
            instance = userMobiles()
            instance.country_code = country_code
            instance.mobile_no = mobile_no
            instance.state = state
            instance.user = user_instance
            instance.created_at = TimeUtilities.current_time_in_sec()
            instance.save()

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
    def process_image_url_for_processing(user_context, user_instance):

        image_url = user_context.get('image_url')

        if not image_url:
            return ''

        if user_context.get('login_type') in [login_types.CUSTOM, login_types.SDK]:
            return image_url

        return upload_image_to_firebase(image_url, user_instance.id)

    @staticmethod
    def is_user_belong_to_any_community(user_instance):

        return Members.objects.filter(member_id=user_instance.user_id_id).filter(Q(state=member_states.ADMIN)
                                                                      | Q(state=member_states.MEMBER)
                                                                      | Q(
            state=member_states.PROFILE_UNAVAILABLE)).exists()

    def create_user_context_for_sdk(user_info_instance, is_exisiting_user=False, app_access=True):

        logged_in_user = SdkViewHelper.compute_logged_in_user(user_info_instance)
        
        user_object = {
            'success': True,
            'user': logged_in_user,
            'email_exists': True if len(logged_in_user['emails']) else False,
            'access': SdkViewHelper.is_user_belong_to_any_community(user_info_instance),
            'is_existing_user': is_exisiting_user,
            'app_access': app_access
        }

        return user_object
    
    def is_valid_email(email):
        
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        
        return re.match(email_regex, email) is not None

    def compute_logged_in_user(userinfo_instance):

        userinfo_context = {
            'id': userinfo_instance.id,
            'name': userinfo_instance.name,
            'updated_at': userinfo_instance.updated_at,
            'is_guest': userinfo_instance.is_guest,
            'user_unique_id': userinfo_instance.user_unique_id,
            'uuid': userinfo_instance.user_unique_id,
            'organisation_name': userinfo_instance.organisation_name,
            'image_url': userinfo_instance.image_link
        }

        email_list = SdkViewHelper.create_user_email_list(userinfo_instance)
        mobile_list = SdkViewHelper.create_user_mobile_list(userinfo_instance)

        if email_list:
            userinfo_context['emails'] = email_list

        if mobile_list:
            userinfo_context['mobiles'] = mobile_list

        return userinfo_context
    
    def create_user_email_list(userinfo_instance):
        email_filter = userEmails.objects.filter(user=userinfo_instance.user_id_id)

        email_list = []

        for email_instance in email_filter:
            email_list.append(SdkViewHelper.emailSerializer(email_instance))

        return email_list

    def create_user_mobile_list(userinfo_instance):
        mobile_filter = userMobiles.objects.filter(user=userinfo_instance.user_id_id)
        mobile_list = []

        for mobile_instance in mobile_filter:
            mobile_list.append(SdkViewHelper.mobilesSerializer(mobile_instance))

        return mobile_list
