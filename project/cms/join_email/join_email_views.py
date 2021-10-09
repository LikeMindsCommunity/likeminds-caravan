from django.http import JsonResponse
from rest_framework.views import APIView

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.request_utilities import RequestUtilities

from .join_email_impl import JoinEmailImpl
from rest_framework import status as status_codes
from ..cms_auth_utilities import CMSAuthUtilities
from collabmates_api.mixins import TransactionMixin

error_logger = LoggingWrapper.get_instance()


class AddJoinEmailView(TransactionMixin, APIView):
    """ inheriting API view class for using class based views in django """

    @staticmethod
    def post(request, *args, **kwargs):

        user_name, password = CMSAuthUtilities.get_username_and_password_from_headers(request)

        if not CMSAuthUtilities.validate_user(user_name, password):
            return JsonResponse({
                'success': False,
                'error_message': 'user name and password does not match'
            }, status=status_codes.HTTP_401_UNAUTHORIZED)

        req_body = RequestUtilities.fetch_body_or_raise_exception(request)

        join_email_manager = JoinEmailImpl()
        response = join_email_manager.add_join_email(req_body)

        return JsonResponse(response['response'], status=response['status_code'])
