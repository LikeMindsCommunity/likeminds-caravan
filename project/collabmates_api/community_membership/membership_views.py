from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from .membership_impl import MembershipImpl
from ..mixins import TransactionMixin

from utility.request_utilities import RequestUtilities

from utility.exception_utilities import InvalidHeaderException, CustomException

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class FetchCommunityBenefits(APIView):
    """inheriting API view class for using class based views in django"""

    def _convert_string_list_to_integer_list(self, string, delimiter=","):
        map_object = map(int, string.split(delimiter))

        return list(map_object)

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        query_params = RequestUtilities.fetch_request_query_params(request)

        community_ids = query_params.get('community_ids', None)

        if community_ids is None:
            response = {
                'success': False,
                'error_message': "community id's missing in query params or invalid or format error"
            }
            raise CustomException(response)

        try:
            community_ids = self._convert_string_list_to_integer_list(community_ids)
        except:
            response = {
                'success': False,
                'error_message': "community id's in query params are invalid or format error"
            }
            raise CustomException(response)

        membership_manager = MembershipImpl(member_id)
        response = membership_manager.fetch_community_benefits(community_ids)

        return JsonResponse(response)


class RemoveCommunityMemberShipView(TransactionMixin, APIView):
    """inheriting API view class for using class based views in django"""

    def post(self, request):
        post_data = RequestUtilities.fetch_request_post_data(request)

        community_id = post_data.get('community_id', None)
        member_id = post_data.get('member_id', None)

        if member_id is None:
            response = {
                'success': False,
                'error_message': "member_id missing in post params"
            }
            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        if community_id is None:
            response = {
                'success': False,
                'error_message': "community id missing in post params"
            }
            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        membership_manager = MembershipImpl(member_id)
        response = membership_manager.remove_community_membership(community_id, member_id)

        return JsonResponse(response)


class RenewCommunityMemberShipView(TransactionMixin, APIView):
    """inheriting API view class for using class based views in django"""

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        post_data = RequestUtilities.fetch_request_post_data(request)
        community_id = post_data.get('community_id', None)

        if community_id is None:
            response = {
                'success': False,
                'error_message': "community id missing in post params"
            }
            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        membership_manager = MembershipImpl(member_id)
        response = membership_manager.renew_community_membership(community_id)

        return JsonResponse(response)
