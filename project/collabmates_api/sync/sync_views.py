from django.http import JsonResponse
from rest_framework.views import APIView

from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from utility.string_utilities import StringUtilities
from utility.version_utilities import VersionUtilities
from .sync_impl import SyncImpl


class SyncChatrooms(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        params = RequestUtilities.fetch_request_query_params(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        platform = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_version = RequestUtilities.get_api_version_from_headers(request)
        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request)
        min_timestamp = params.get('min_timestamp')
        max_timestamp = params.get('max_timestamp')
        chatroom_type = StringUtilities.get_list_from_string(params.get('chatroom_types', []), default=[])
        is_local_db = params.get('is_local_db')
        included_conversation_states = StringUtilities.get_list_from_string(params.get('included_conversation_states'),
                                                                            default=None)
        chatroom_id = params.get('chatroom_id')
        tag = params.get('tag')

        if (is_local_db is None) or (is_local_db == ''):

            if platform in [VersionUtilities.PlatformCode.ANDROID_SDK, VersionUtilities.PlatformCode.REACT_NATIVE_SDK]:
                is_local_db = True

            else:
                is_local_db = False

        else:
            is_local_db = StringUtilities.get_boolean_from_string(is_local_db, True)

        sync_manager = SyncImpl(member_id=member_id, community_id=params.get('community_id'),
                                api_key=api_key, request_platform=platform, version_code=version_code,
                                api_version_code=api_version)
        response_data = sync_manager.sync_chatrooms(page, page_size, min_timestamp, max_timestamp, chatroom_type,
                                                    is_local_db=is_local_db,
                                                    included_conversation_states=included_conversation_states,
                                                    chatroom_id=chatroom_id, tag=tag)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data.get('error_message'),
                                                                    response_data.get('status'))
            return JsonResponse(**context)

        return JsonResponse(response_data)


class SyncChannelDetail(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        params = RequestUtilities.fetch_request_query_params(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        platform = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        channel_id = params.get('channel_id')
        channel_action_types = StringUtilities.convert_string_to_list(params.get('channel_action_types', ''))

        sync_manager = SyncImpl(member_id=member_id, api_key=api_key, request_platform=platform,
                                version_code=version_code)
        response_data = sync_manager.sync_channel_detail(channel_id=channel_id,
                                                         channel_action_types=channel_action_types)

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
        conversation_id = params.get('conversation_id')
        is_local_db = StringUtilities.get_boolean_from_string(params.get('is_local_db'), True)
        excluded_conversation_states = StringUtilities.get_list_from_string(params.get('excluded_conversation_states'),
                                                                            default=None)
        order_by = params.get('order_by')

        sync_manager = SyncImpl(member_id=member_id, community_id=params.get('community_id'),
                                api_key=api_key, request_platform=platform, version_code=version_code)
        response_data = sync_manager.sync_conversations(chatroom_id, page, page_size, min_timestamp, max_timestamp,
                                                        is_local_db, conversation_id=conversation_id,
                                                        excluded_conversation_states=excluded_conversation_states,
                                                        order_by=order_by)

        if 'error_message' in response_data:
            context = ResponseUtilities.get_view_impl_error_context(response_data.get('error_message'),
                                                                    response_data.get('status'))
            return JsonResponse(**context)

        return JsonResponse(response_data)
