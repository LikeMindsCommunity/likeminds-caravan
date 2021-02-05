from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes
from utility.request_utilities import RequestUtilities
from utility.exception_utilities import InvalidHeaderException, JsonDecodeException, CustomException

from .banner_impl import BannerImpl
from ..cms_auth_utilities import CMSAuthUtilities


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

        user_name, password = CMSAuthUtilities.get_username_and_password_from_headers(request)

        if not CMSAuthUtilities.validate_user(user_name, password):
            CMSAuthUtilities.raise_authentication_error()

        banner_manager = BannerImpl()
        response = banner_manager.fetch_banner_for_cms()

        return JsonResponse(response, safe=False)


class CheckBannerView(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):

        user_name, password = CMSAuthUtilities.get_username_and_password_from_headers(request)

        if not CMSAuthUtilities.validate_user(user_name, password):
            CMSAuthUtilities.raise_authentication_error()

        start_epoch_time = request.GET.get('start_epoch_time', None)
        end_epoch_time = request.GET.get('end_epoch_time', None)

        banner_manager = BannerImpl()
        response = banner_manager.check_banner(start_epoch_time, end_epoch_time)

        return JsonResponse(response, safe=False)


class CreateOrUpdateBannerView(APIView):

    def post(self, request, *args, **kwargs):

        user_name, password = CMSAuthUtilities.get_username_and_password_from_headers(request)

        if not CMSAuthUtilities.validate_user(user_name, password):
            CMSAuthUtilities.raise_authentication_error()

        req_body = BannerRequestUtilities.fetch_body_or_raise_exception(request)

        banner_manager = BannerImpl()
        response = banner_manager.create_or_update_banner(req_body)

        return JsonResponse(response)


class RemoveBannerView(APIView):

    def post(self, request, *args, **kwargs):

        banner_id = request.data.get('banner_id')

        user_name, password = CMSAuthUtilities.get_username_and_password_from_headers(request)

        if not CMSAuthUtilities.validate_user(user_name, password):
            CMSAuthUtilities.raise_authentication_error()

        if not banner_id:
            response = {
                'success': False,
                'error_message': 'send banner id in post params'
            }
            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        banner_manager = BannerImpl()
        response = banner_manager.remove_banner(banner_id)

        return JsonResponse(response)


class BannerRequestUtilities:
    @staticmethod
    def fetch_body_or_raise_exception(request):
        try:
            return RequestUtilities.fetch_request_body(request)
        except Exception as e:
            response = {
                'success': False,
                'error_message': f'{e.__class__.__name__} - {e.__str__()}'
            }
            raise JsonDecodeException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)
