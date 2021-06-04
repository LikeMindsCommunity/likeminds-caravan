from django.http import JsonResponse
from rest_framework.views import APIView
from utility.request_utilities import RequestUtilities
from utility.exception_utilities import InvalidHeaderException, CustomException

# ------------  do not remove these imports --------------
from .chatroom_index import ChatroomDocument
from .conversation_index import ConversationDocument
# --------------------------------------------------------

from .search_impl import SearchImpl


class ChatroomSearchView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        search_term = request.GET.get('search')
        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=300)

        follow_status = request.GET.get('follow_status', True)

        if isinstance(follow_status, str):
            follow_status = follow_status.lower() == 'true'

        search_manager = SearchImpl(member_id=member_id, search_term=search_term,
                                    follow_status=follow_status,
                                    page=page, page_size=page_size)

        chatrooms_data = search_manager.search_chatroom()

        return JsonResponse(chatrooms_data)


class ConversationSearchView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        search_term = request.GET.get('search')
        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=300)

        follow_status = request.GET.get('follow_status', True)

        if isinstance(follow_status, str):
            follow_status = follow_status.lower() == 'true'

        search_manager = SearchImpl(member_id=member_id, search_term=search_term,
                                    follow_status=follow_status,
                                    page=page, page_size=page_size)

        conversations_data = search_manager.search_conversation()

        return JsonResponse(conversations_data)
