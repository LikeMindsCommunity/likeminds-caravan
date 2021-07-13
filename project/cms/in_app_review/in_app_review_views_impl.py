from django.contrib.auth.models import User
from django.http import JsonResponse

from rest_framework.views import APIView
from rest_framework import status as status_codes

from cms.in_app_review.in_app_review_impl import InAppReviewImpl
from cms.models import InAppReview
from cms.utils import get_error_context
from togther.models import ModelUtilities
from utility.exception_utilities import InvalidHeaderException
from utility.request_utilities import RequestUtilities
from utility.time_utilities import TimeUtilities


class ShownReviewPopUpView(APIView):

    def post(self, request):
        header_member_id = RequestUtilities.get_member_id_from_headers(request)

        if not header_member_id:
            raise InvalidHeaderException()

        in_app_review_manager = InAppReviewImpl()
        response = in_app_review_manager.shown_review_popup(header_member_id)

        if response.get('error_message'):
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response, status=status_codes.HTTP_200_OK)


class EnableReviewPopUpView(APIView):

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)

        if not request_body:
            return JsonResponse({'success': False, 'error_message': "Invalid request body"})

        user_ids = request_body.get('user_ids')

        in_app_review_manager = InAppReviewImpl()
        response = in_app_review_manager.enable_review_popup(user_ids)

        if response.get('error_message'):
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response, status=status_codes.HTTP_200_OK)
