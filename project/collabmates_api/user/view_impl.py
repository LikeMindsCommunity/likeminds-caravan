from django.http import JsonResponse
from rest_framework.views import APIView
from utility.request_utilities import RequestUtilities
from django.conf import settings
from collabmates_api.user.user_impl import UserImpl
from rest_framework import status as status_codes


class DeleteUserView(APIView):
    '''inheriting API view class for using class based views in django'''

    def post(self, request):

        if settings.IS_BETA:

            request_body = RequestUtilities.fetch_request_body(request)
            request_values = self.process_request_body(request_body)
            user_manager = UserImpl(user_id=request_values[0], mobile_no=request_values[1])
            user_deleted = user_manager.delete_user()

            if user_deleted:
                return JsonResponse({'success': True})

            return JsonResponse({
                'success': False,
                'error_message': "credentials not found"
            }, status=400)

        else:
            api_response = {
                'success': False,
                'error_message': "resource not found"
            }
            return JsonResponse(api_response, status=404)

    def process_request_body(self, request_body):

        user_id = None
        mobile_no = None

        if 'user_id' in request_body and request_body['user_id']:
            user_id = request_body['user_id']

        elif 'mobile_no' in request_body and request_body['mobile_no']:
            mobile_no = request_body['mobile_no']

        return user_id, mobile_no


class UserSeenSurvey(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        user_manager = UserImpl(user_id=member_id, mobile_no="")
        user_context = user_manager.survey_seen()

        if user_context.get('error_message'):
            return JsonResponse(user_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(user_context)


class UserLogout(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        user_manager = UserImpl(user_id=member_id, mobile_no="")
        device_id = RequestUtilities.get_device_id_from_headers(request)

        user_context = user_manager.logout(device_id)

        if user_context.get('error_message'):
            return JsonResponse(user_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(user_context)


class UserRemoveProfile(APIView):
    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        user_manager = UserImpl(user_id=member_id, mobile_no="")
        user_context = user_manager.remove_profile()

        if user_context.get('error_message'):
            return JsonResponse(user_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(user_context)
