from django.http import JsonResponse

from collabmates_api.multimedia_operations.mm_operations_impl import MultimediaOperationsImpl
from collabmates_api.multimedia_operations.views_manager import ViewsManager
from collabmates_api.utilities.request_utilities import RequestUtilities
from collabmates_api.views import get_error_context
from external_services.amazon_s3.buckets import S3_BUCKETS


class ViewsImpl(ViewsManager):

    def generate_presigned_post(self) -> JsonResponse:
        try:
            request = self
            conversation_id, file_name = ViewsHelper.validate_request(request)

        except Exception as e:
            context = get_error_context(False, str(e))

            return JsonResponse(context, status=400)

        else:
            bucket = S3_BUCKETS.get('media_bucket')
            multimedia_operations_manager = MultimediaOperationsImpl(bucket)
            object_name = ViewsHelper.create_s3_media_object_path(conversation_id, file_name)
            api_response = multimedia_operations_manager.generate_presigned_post(object_name)

            return JsonResponse({"api_response": api_response})


class ViewsHelper:

    @staticmethod
    def validate_request(request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        conversation_id = request.GET.get('conversation_id')
        file_name = request.GET.get('file_name')

        if not member_id:
            raise TypeError('member id is missing from request')

        elif not conversation_id:
            raise TypeError('conversation id is missing from request')

        elif not file_name:
            raise TypeError("file name is missing from request")

        return conversation_id, file_name

    @staticmethod
    def create_s3_media_object_path(*args) -> str:
        prefix = 'conversation'
        forward_slash = '/'
        object_name = prefix

        for arg in args:
            object_name += (forward_slash + arg)

        return object_name
