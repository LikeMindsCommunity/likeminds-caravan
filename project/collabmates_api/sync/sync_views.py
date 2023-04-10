from django.http import JsonResponse
from rest_framework.views import APIView

from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from utility.string_utilities import StringUtilities
from .sync_impl import SyncImpl


class SyncChatrooms(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        params = RequestUtilities.fetch_request_query_params(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request)
        min_timestamp = params.get('min_timestamp')
        max_timestamp = params.get('max_timestamp')
        chatroom_type = StringUtilities.get_list_from_string(params.get('chatroom_types', []), default=[])

        sync_manager = SyncImpl(member_id=member_id, community_id=params.get('community_id'),
                                api_key=api_key, request_platform=platform, version_code=version_code)
        response_data = sync_manager.sync_chatrooms(page, page_size, min_timestamp, max_timestamp, chatroom_type)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data.get('error_message'),
                                                                    response_data.get('status'))
            return JsonResponse(**context)

        return JsonResponse(response_data)


class SyncConversations(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        params = RequestUtilities.fetch_request_query_params(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request)
        min_timestamp = params.get('min_timestamp')
        max_timestamp = params.get('max_timestamp')
        chatroom_id = params.get('chatroom_id')
        is_local_db = False if params.get('is_local_db') == 'false' else True

        sync_manager = SyncImpl(member_id=member_id, community_id=params.get('community_id'),
                                api_key=api_key, request_platform=platform, version_code=version_code)
        response_data = sync_manager.sync_conversations(chatroom_id, page, page_size, min_timestamp, max_timestamp, is_local_db)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data.get('error_message'),
                                                                    response_data.get('status'))
            return JsonResponse(**context)

        return JsonResponse(response_data)
