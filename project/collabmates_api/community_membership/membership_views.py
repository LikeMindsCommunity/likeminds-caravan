from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from .membership_impl import MembershipImpl

from utility.request_utilities import RequestUtilities

from utility.exception_utilities import InvalidHeaderException, CustomException

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class FetchCommunityBenefits(APIView):
    """inheriting API view class for using class based views in django"""

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        request_body = RequestUtilities.load_request_body(request)
        community_ids = request_body.get('community_ids', None)

        if community_ids is None:
            response = {
                'success': False,
                'error_message': "community id's missing in body or invalid or format error"
            }
            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        membership_manager = MembershipImpl(member_id)
        response = membership_manager.fetch_community_benefits(community_ids)

        return JsonResponse(response)
