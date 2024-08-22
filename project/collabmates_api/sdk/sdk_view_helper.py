from django.db.models import Q
from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, communityQuestions, SDKClientUsersInfo, removedMembers)
from utility.states import (login_types)
from utility.validation_utilities import ValidationUtilities
from .models import SdkClient, SdkOnboardingScreen


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

        if not request_params:
            return ResponseUtilities.get_inner_error_context('invalid request params')

        no_of_months = request_params.get('no_of_months')

        if 'no_of_months' not in request_params and not no_of_months:
            return ResponseUtilities.get_inner_error_context('send no_of_months in params')

        if not no_of_months.isdigit():
            return ResponseUtilities.get_inner_error_context('no_of_months should be a number')

        if int(no_of_months) == 0:
            return ResponseUtilities.get_inner_error_context('no_of_months should be non-zero')
        
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
            'request_params': request_params,
            'user_instance': validated_dict.get('user_id'),
            'community_instance': validated_dict.get('community_id')
        }