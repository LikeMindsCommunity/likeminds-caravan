from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes
from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from utility.exception_utilities import InvalidHeaderException, CustomException
from .constants import CHATROOM_SEARCHABLE_FIELDS, CHATROOM_FIELD_HEADER
from .constants import MEMBER_DIRECTORY_SEARCHABLE_FIELDS, MEMBER_DIRECTORY_FIELD_NAME, MEMBER_DIRECTORY_ORDER_BY_RECENT, MEMBER_DIRECTORY_ORDER_BY_FIELDS

# ------------  do not remove these imports --------------
from .chatroom_index import ChatroomDocument
from .conversation_index import ConversationDocument
from .member_directory_index import MemberDirectoryDocument
# --------------------------------------------------------

from .search_impl import SearchImpl
from ..utility import single_community_view_version_check


class ChatroomSearchView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id = request.GET.get('community_id', None)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        if single_community_view_version_check(platform_code, version_code) and not (community_id or api_key):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid community ID/API key!',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        search_term = request.GET.get('search')
        search_field = request.GET.get('search_type', CHATROOM_FIELD_HEADER)

        if search_field.lower() == 'chatroom_id':
            search_field = 'id'

        if search_field.lower() not in CHATROOM_SEARCHABLE_FIELDS:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid search type!',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=300)

        follow_status = request.GET.get('follow_status', True)

        if isinstance(follow_status, str):
            follow_status = follow_status.lower() == 'true'

        search_manager = SearchImpl(member_id=member_id, search_term=search_term, search_field=search_field,
                                    follow_status=follow_status, page=page, page_size=page_size, api_key=api_key,
                                    community_id=community_id)

        chatrooms_data = search_manager.search_chatroom()

        if 'error_message' in chatrooms_data:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatrooms_data.get('error_message'),
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        return JsonResponse(chatrooms_data)


class ConversationSearchView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id = request.GET.get('community_id', None)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        if single_community_view_version_check(platform_code, version_code) and not (community_id or api_key):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid community ID/API key!',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        search_term = request.GET.get('search')
        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=300)

        follow_status = request.GET.get('follow_status', True)

        if isinstance(follow_status, str):
            follow_status = follow_status.lower() == 'true'

        search_manager = SearchImpl(member_id=member_id, search_term=search_term, follow_status=follow_status,
                                    page=page, page_size=page_size, api_key=api_key, community_id=community_id)

        conversations_data = search_manager.search_conversation()

        if 'error_message' in conversations_data:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(conversations_data.get('error_message'),
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        return JsonResponse(conversations_data)


class ThirdPartySearchView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id = request.GET.get('community_id', None)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if single_community_view_version_check(platform_code, version_code) and not (community_id or api_key):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid community ID/API key!',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        if not member_id:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Send member ID in headers!',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        search_term = request.GET.get('search')

        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=300)

        search_manager = SearchImpl(member_id=member_id, search_term=search_term, search_field=CHATROOM_FIELD_HEADER,
                                    follow_status=True, page=page, page_size=page_size, device_id=device_id,
                                    api_key=api_key, community_id=community_id)

        chatrooms_data = search_manager.search_third_party()

        if 'error_message' in chatrooms_data:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatrooms_data.get('error_message'),
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        return JsonResponse(chatrooms_data)


class MemberDirectorySearchView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not member_id:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context("Send x-member-id!",
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        search_term = request.GET.get('search')
        search_field = request.GET.get('search_type', MEMBER_DIRECTORY_FIELD_NAME)
        order_by = request.GET.get('order_type', "")

        if search_field.lower() not in MEMBER_DIRECTORY_SEARCHABLE_FIELDS:
            response = {
                "success": False,
                "error_message": "Invalid search type"
            }

            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=300)

        community_id = request.GET.get('community_id', None)

        if not (community_id or api_key):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context("Community ID/API Key is required!",
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        search_manager = SearchImpl(member_id=member_id, search_term=search_term, search_field=search_field, order_by=order_by,
                                    follow_status=True, page=page, page_size=page_size, community_id=community_id,
                                    api_key=api_key)

        members_data = search_manager.search_member_directory()

        return JsonResponse(members_data)
