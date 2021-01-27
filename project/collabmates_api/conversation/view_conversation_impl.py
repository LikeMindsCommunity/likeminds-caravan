from django.http import JsonResponse
from .conversation_impl import ConversationImpl
from utility.request_utilities import RequestUtilities
from rest_framework.views import APIView
from ..serializers import get_conversation_instance_for_db_synching
from utility.exception_utilities import InvalidHeaderException


class FetchConversation(APIView):
    """inheriting API view class for using class based views in django"""

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        chatroom_id = request.GET.get('chatroom_id')
        scroll_direction = request.GET.get('scroll_direction')
        conversation_id = request.GET.get('conversation_id')
        page = request.GET.get('page', 1)
        paginate_by = request.GET.get('paginate_by', 200)

        conversation_manager = ConversationImpl(member_id, chatroom_id, scroll_direction, conversation_id, page,
                                                paginate_by)

        conversations = conversation_manager.fetch_conversation()

        return JsonResponse({
            'conversations': conversations
        })


class CreateConversation(APIView):
    """ inheriting API view class for using class based views in django"""

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.fetch_request_body(request)
        is_ios = RequestUtilities.is_request_ios(request)

        is_user_guest = ConversationViewsHelper.is_user_guest(req_body)
        has_files = ConversationViewsHelper.has_files(req_body, is_ios)

        conversation_manager = ConversationImpl(member_id)
        conversation_response = conversation_manager.create_conversation(req_body, is_ios,
                                                                         is_user_guest, has_files)

        return JsonResponse(conversation_response)


class ConversationViewsHelper:

    @staticmethod
    def is_user_guest(req_body):
        return req_body.get('aj') and req_body.get('source_id')

    @staticmethod
    def has_files(req_body, is_ios):
        return req_body.get('has_files', False) or is_ios

