from django.http import JsonResponse

from utility.constants import INVALID_PLATFORM
from utility.number_utilities import NumberUtilities
from utility.string_utilities import StringUtilities
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
        paginate_by = request.GET.get('paginate_by', 20)
        top_navigate = request.GET.get('top_navigate', False)
        top_navigate = StringUtilities.get_boolean_from_string(top_navigate)

        conversation_manager = ConversationImpl(member_id, chatroom_id, scroll_direction, conversation_id, page,
                                                paginate_by)
        conversations = conversation_manager.fetch_conversation(top_navigate)

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
        platform_code = RequestUtilities.get_platform_code(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)

        is_user_guest = ConversationViewsHelper.is_user_guest(req_body)
        has_files = ConversationViewsHelper.has_files(req_body, is_ios)

        conversation_manager = ConversationImpl(member_id, platform_code=platform_code, device_id=device_id)

        try:
            conversation_response = conversation_manager.create_conversation(req_body, is_ios,
                                                                         is_user_guest, has_files)
        except Exception as e:
            return JsonResponse({'error_message': e.args}, status=400)

        if conversation_response.get('error_message'):
            return JsonResponse(conversation_response, status=400)

        return JsonResponse(conversation_response)


class AddConversationPollOptions(APIView):

    def post(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.load_request_body(request)

        if not request:
            return JsonResponse({'success': False, 'error_message': "Invalid request body"}, status=400)

        conversation_manager = ConversationImpl(member_id=member_id)
        conversation_response = conversation_manager.add_poll(req_body)

        if conversation_response.get('error_message'):
            return JsonResponse(conversation_response, status=400)

        return JsonResponse(conversation_response)


class SubmitConversationPoll(APIView):

    def post(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid request body"}, status=400)

        conversation_manager = ConversationImpl(member_id=member_id)
        conversation_response = conversation_manager.submit_poll(req_body)

        if conversation_response.get('error_message'):
            return JsonResponse(conversation_response, status=400)

        return JsonResponse(conversation_response)


class FetchConversationPollUsers(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        poll_id = request.GET.get('poll_id')
        conversation_id = request.GET.get('conversation_id')
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 20)

        page = NumberUtilities.get_integer_from_string(page)
        page_size = NumberUtilities.get_integer_from_string(page_size)

        if not request:
            return JsonResponse({'success': False, 'error_message': "Invalid request body"}, status=400)

        conversation_manager = ConversationImpl(member_id=member_id, conversation_id=conversation_id)
        poll_conversation_response = conversation_manager.poll_users(poll_id, page, page_size)

        if poll_conversation_response.get('error_message'):
            return JsonResponse(poll_conversation_response, status=400)

        return JsonResponse(poll_conversation_response)


class ConversationViewsHelper:

    @staticmethod
    def is_user_guest(req_body):
        return req_body.get('aj') and req_body.get('source_id')

    @staticmethod
    def has_files(req_body, is_ios):
        return req_body.get('has_files', False) or is_ios

