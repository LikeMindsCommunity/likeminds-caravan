from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.request_utilities import RequestUtilities
from utility.exception_utilities import CustomException

from .options_impl import OptionsImpl
from ..cms_auth_utilities import CMSAuthUtilities
from collabmates_api.mixins import TransactionMixin

error_logger = LoggingWrapper.get_instance()


class FetchOptionView(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):

        slug = request.GET.get('slug', None)

        if not slug:
            response = {
                "success": False,
                "error_message": "send slug in url params"
            }

            raise CustomException(response)

        option_manager = OptionsImpl()
        response = option_manager.fetch_option(slug)

        return JsonResponse(response, safe=False)


class CreateOrUpdateOptionView(TransactionMixin, APIView):

    def post(self, request, *args, **kwargs):

        user_name, password = CMSAuthUtilities.get_username_and_password_from_headers(request)

        if not CMSAuthUtilities.validate_user(user_name, password):
            CMSAuthUtilities.raise_authentication_error()

        req_body = RequestUtilities.fetch_body_or_raise_exception(request)

        option_manager = OptionsImpl()
        response = option_manager.create_option(req_body)

        return JsonResponse(response)
