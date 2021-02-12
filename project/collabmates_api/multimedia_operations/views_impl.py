from django.conf import settings
from django.http import JsonResponse

from rest_framework import status as status_codes

from collabmates_api.multimedia_operations.mm_operations_impl import MultimediaOperationsImpl
from collabmates_api.multimedia_operations.views_manager import ViewsManager
from utility.request_utilities import RequestUtilities
from collabmates_api.views import get_error_context


class ViewsImpl(ViewsManager):

    def generate_presigned_post(self) -> JsonResponse:
        try:
            request = self
            path = ViewsHelper.validate_request(request)

        except Exception as e:
            context = get_error_context(False, str(e))

            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        else:
            s3_bucket_name = 'media_bucket'
            bucket = settings.S3_BUCKETS.get(s3_bucket_name)
            multimedia_operations_manager = MultimediaOperationsImpl(bucket)
            api_response = multimedia_operations_manager.generate_presigned_post(path)

            return JsonResponse({"api_response": api_response})


class ViewsHelper:

    @staticmethod
    def validate_request(request) -> str:

        member_id = RequestUtilities.get_member_id_from_headers(request)
        path = request.GET.get('path')

        if not member_id:
            raise TypeError('member id is missing from request')

        elif not path:
            raise TypeError('object path is missing from request')

        return path
