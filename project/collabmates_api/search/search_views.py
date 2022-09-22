from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes
from utility.request_utilities import RequestUtilities
from utility.exception_utilities import InvalidHeaderException, CustomException
from .constants import CHATROOM_SEARCHABLE_FIELDS, CHATROOM_FIELD_HEADER
from .constants import MEMBER_DIRECTORY_SEARCHABLE_FIELDS, MEMBER_DIRECTORY_FIELD_NAME

# ------------  do not remove these imports --------------
# from .chatroom_index import ChatroomDocument
# from .conversation_index import ConversationDocument
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

        if not member_id:
            raise InvalidHeaderException()

        if single_community_view_version_check(platform_code, version_code):
            if not community_id:
                return JsonResponse({
                    'status': status_codes.HTTP_400_BAD_REQUEST,
                    'success': False,
                    'error_message': 'missing required parameter: community_id'
                })

        search_term = request.GET.get('search')
        search_field = request.GET.get('search_type', CHATROOM_FIELD_HEADER)

        if search_field.lower() not in CHATROOM_SEARCHABLE_FIELDS:
            response = {
                "success": False,
                "error_message": "Invalid search type"
            }

            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=300)

        follow_status = request.GET.get('follow_status', True)

        if isinstance(follow_status, str):
            follow_status = follow_status.lower() == 'true'

        search_manager = SearchImpl(member_id=member_id, search_term=search_term,
                                    search_field=search_field, follow_status=follow_status,
                                    page=page, page_size=page_size)

        chatrooms_data = search_manager.search_chatroom(community_id)

        return JsonResponse(chatrooms_data)


class ConversationSearchView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id = request.GET.get('community_id', None)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        if single_community_view_version_check(platform_code, version_code):
            if not community_id:
                return JsonResponse({
                    'status': status_codes.HTTP_400_BAD_REQUEST,
                    'success': False,
                    'error_message': 'missing required parameter: community_id'
                })

        search_term = request.GET.get('search')
        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=300)

        follow_status = request.GET.get('follow_status', True)

        if isinstance(follow_status, str):
            follow_status = follow_status.lower() == 'true'

        search_manager = SearchImpl(member_id=member_id, search_term=search_term,
                                    follow_status=follow_status,
                                    page=page, page_size=page_size)

        conversations_data = search_manager.search_conversation(community_id)

        return JsonResponse(conversations_data)


class ThirdPartySearchView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id = request.GET.get('community_id', None)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        if single_community_view_version_check(platform_code, version_code):
            if not community_id:
                return JsonResponse({
                    'status': status_codes.HTTP_400_BAD_REQUEST,
                    'success': False,
                    'error_message': 'missing required parameter: community_id'
                })

        if not member_id:
            raise InvalidHeaderException()

        device_id = RequestUtilities.get_device_id_from_headers(request)

        search_term = request.GET.get('search')

        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=300)

        search_manager = SearchImpl(member_id=member_id, search_term=search_term,
                                    search_field=CHATROOM_FIELD_HEADER, follow_status=True,
                                    page=page, page_size=page_size, device_id=device_id)

        chatrooms_data = search_manager.search_third_party(community_id)

        return JsonResponse(chatrooms_data)


class MemberDirectorySearchView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        search_term = request.GET.get('search')
        search_field = request.GET.get('search_type', MEMBER_DIRECTORY_FIELD_NAME)

        if search_field.lower() not in MEMBER_DIRECTORY_SEARCHABLE_FIELDS:
            response = {
                "success": False,
                "error_message": "Invalid search type"
            }

            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=300)

        community_id = request.GET.get('community_id', None)

        if community_id is None:
            response = {
                "success": False,
                "error_message": "Community ID is required"
            }

            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        search_manager = SearchImpl(member_id=member_id, search_term=search_term,
                                    search_field=search_field, follow_status=True,
                                    page=page, page_size=page_size, community_id=community_id)

        members_data = search_manager.search_member_directory()

        return JsonResponse(members_data)
