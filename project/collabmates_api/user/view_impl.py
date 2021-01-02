from django.http import JsonResponse
from rest_framework.views import APIView
from utility.request_utilities import RequestUtilities
from django.conf import settings
from collabmates_api.user.user_impl import UserImpl

class DeleteUserView(APIView):

        '''inheriting API view class for using class based views in django'''

        def post(self, request):

            if settings.IS_BETA:

                request_body = RequestUtilities.fetch_request_body(request)
                request_values = self.process_request_body(request_body)
                user_manager = UserImpl(user_id = request_values[0], mobile_no = request_values[1])
                user_deleted = user_manager.delete_user()

                if user_deleted:
                    return JsonResponse({'success':True})

                return JsonResponse({
                    'success': False,
                    'error_message': "credentials not found"
                }, status=400)

            else:
                api_response = {
                    'success': False,
                    'error_message': "resource not found"
                }
                return JsonResponse(api_response,status=404)

        def process_request_body(self, request_body):

            user_id = None
            mobile_no = None

            if 'user_id' in request_body and request_body['user_id']:
                user_id = request_body['user_id']

            elif 'mobile_no' in request_body and request_body['mobile_no']:
                mobile_no = request_body['mobile_no']

            return (user_id,mobile_no)


