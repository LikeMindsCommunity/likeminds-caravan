from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes
from utility.exception_utilities import (InvalidUserException, InvalidCommunityException,
                                         InvalidHeaderException, CustomException)
from utility.request_utilities import RequestUtilities
from utility.exception_utilities import InvalidHeaderException

from .banner_impl import BannerImpl
from .constants import *


class FetchBannerView(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException

        platform_code = RequestUtilities.get_request_type(request).lower()
        app_version = RequestUtilities.get_version_code_from_headers(request)

        banner_manager = BannerImpl(member_id, platform_code, app_version)

        response = banner_manager.fetch_banner()

        return JsonResponse(response)


class FetchBannerForCMSView(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        user_name, password = BannerUtilities.get_username_and_password_from_headers(request)

        if not BannerUtilities.validate_user(user_name, password):
            BannerUtilities.raise_authentication_error()

        banner_manager = BannerImpl(member_id)
        response = banner_manager.fetch_banner_for_cms()

        return JsonResponse(response, safe=False)



class CheckBannerView(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        start_epoch_time = request.GET.get('start_epoch_time', None)
        end_epoch_time = request.GET.get('end_epoch_time', None)

        user_name, password = BannerUtilities.get_username_and_password_from_headers(request)

        if not BannerUtilities.validate_user(user_name, password):
            BannerUtilities.raise_authentication_error()

        banner_manager = BannerImpl(member_id)
        response = banner_manager.check_banner(start_epoch_time, end_epoch_time)

        return JsonResponse(response, safe=False)


class CreateOrUpdateBannerView(APIView):
    def post(self, request, *args, **kwargs):

        req_body = RequestUtilities.fetch_request_body(request)

        user_name, password = BannerUtilities.get_username_and_password_from_headers(request)

        if not BannerUtilities.validate_user(user_name, password):
            BannerUtilities.raise_authentication_error()

        banner_manager = BannerImpl()
        response = banner_manager.create_or_update_banner(req_body)

        return JsonResponse(response)


class RemoveBannerView(APIView):
    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        banner_id = request.GET.get('banner_id')

        user_name, password = BannerUtilities.get_username_and_password_from_headers(request)

        if not BannerUtilities.validate_user(user_name, password):
            BannerUtilities.raise_authentication_error()

        banner_manager = BannerImpl(member_id)
        response = banner_manager.remove_banner(banner_id)

        return JsonResponse(response)


class BannerUtilities:

    @staticmethod
    def get_username_and_password_from_headers(request):
        user_name = RequestUtilities.get_user_name_from_headers(request)
        password = RequestUtilities.get_password_from_headers(request)

        if user_name is None and password is None:
            BannerUtilities.raise_credentials_missing_exception()
        else:
            return user_name, password

    @staticmethod
    def validate_user(user_name, password):
        return user_name == CMS_USER_NAME and password == CMS_PASSWORD

    @staticmethod
    def raise_credentials_missing_exception():
        response = {
            'success': False,
            'error_message': 'send user name and password in headers'
        }

        raise CustomException(response, status_code=status_codes.HTTP_401_UNAUTHORIZED)

    @staticmethod
    def raise_authentication_error():
        response = {
            'success': False,
            'error_message': 'user name and password does not match'
        }

        raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)
