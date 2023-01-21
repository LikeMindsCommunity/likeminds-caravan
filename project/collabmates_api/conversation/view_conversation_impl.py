from sys import platform
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.number_utilities import NumberUtilities
from utility.string_utilities import StringUtilities
from .conversation_impl import ConversationImpl
from ..mixins import TransactionMixin

from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from utility.exception_utilities import InvalidHeaderException, CustomException
from utility.version_utilities import VersionUtilities

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()


class FetchConversation(APIView):
    """inheriting API view class for using class based views in django"""

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        platform_code = RequestUtilities.get_platform_code(request)

        query_params = request.query_params

        chatroom_id = query_params.get('chatroom_id')
        scroll_direction = query_params.get('scroll_direction')
        conversation_id = query_params.get('conversation_id')
        page = RequestUtilities.get_page_number(request)
        paginate_by = RequestUtilities.get_page_size(request, key='paginate_by', default=20)
        top_navigate = StringUtilities.get_boolean_from_string(query_params.get('top_navigate', False))
        include_conversation_id = StringUtilities.get_boolean_from_string(query_params.get('include', False))

        conversation_manager = ConversationImpl(member_id, chatroom_id, scroll_direction, conversation_id, page,
                                                paginate_by, device_id=device_id,
                                                include_conversation_id=include_conversation_id,
                                                version_code=version_code, platform_code=platform_code)

        conversation_response = conversation_manager.fetch_conversation(top_navigate)

        if conversation_response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                conversation_response.get('error_message'), conversation_response.get('status')))

        return JsonResponse(conversation_response)


class CreateConversation(APIView):
    """ inheriting API view class for using class based views in django"""

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.fetch_request_body(request)
        is_ios = RequestUtilities.is_request_ios(request)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)

        conversation_manager = ConversationImpl(member_id, platform_code=platform_code, device_id=device_id)

        if VersionUtilities.check_version(platform_code, version_code, VersionUtilities.create_conversation_revamp):
            conversation_response = conversation_manager.create_conversation_v1(req_body)

        else:
            conversation_response = conversation_manager.create_conversation(req_body, is_ios=is_ios)

        if conversation_response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                conversation_response.get('error_message'), conversation_response.get('status')))

        return JsonResponse(conversation_response)


class AddConversationPollOptions(APIView):

    def post(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid request body',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        conversation_manager = ConversationImpl(member_id=member_id)
        conversation_response = conversation_manager.add_poll(req_body)

        if conversation_response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                conversation_response.get('error_message'), conversation_response.get('status')))

        return JsonResponse(conversation_response)


class SubmitConversationPoll(APIView):

    def post(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid request body',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        conversation_manager = ConversationImpl(member_id=member_id)
        conversation_response = conversation_manager.submit_poll(req_body)

        if conversation_response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                conversation_response.get('error_message'), conversation_response.get('status')))

        return JsonResponse(conversation_response)


class FetchConversationPollUsers(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        poll_id = request.GET.get('poll_id')
        conversation_id = request.GET.get('conversation_id')
        page = RequestUtilities.get_page_number(request, default=1)
        page_size = RequestUtilities.get_page_size(request, default=20)

        if not request:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid request body',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        conversation_manager = ConversationImpl(member_id=member_id, conversation_id=conversation_id)
        poll_conversation_response = conversation_manager.poll_users(poll_id, page, page_size)

        if poll_conversation_response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                poll_conversation_response.get('error_message'), poll_conversation_response.get('status')))

        return JsonResponse(poll_conversation_response)


class AddReaction(TransactionMixin, APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(AddReaction, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        post_data = RequestUtilities.fetch_request_post_data(request)

        chatroom_id = post_data.get('chatroom_id', None)
        conversation_id = post_data.get('conversation_id', None)
        reaction = post_data.get('reaction', None)

        chatroom_manager = ConversationImpl(member_id=member_id,
                                            chatroom_id=chatroom_id,
                                            conversation_id=conversation_id)

        response = chatroom_manager.add_reaction(reaction)

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class RemoveReaction(TransactionMixin, APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(RemoveReaction, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        post_data = RequestUtilities.fetch_request_post_data(request)

        chatroom_id = post_data.get('chatroom_id', None)
        conversation_id = post_data.get('conversation_id', None)

        chatroom_manager = ConversationImpl(member_id=member_id,
                                            chatroom_id=chatroom_id,
                                            conversation_id=conversation_id)

        response = chatroom_manager.remove_reaction()

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class SetChatroomTopic(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        chatroom_id = req_body.get('chatroom_id')
        conversation_id = req_body.get('conversation_id')

        conversation_manager = ConversationImpl(member_id=member_id, chatroom_id=chatroom_id,
                                                conversation_id=conversation_id)
        response = conversation_manager.set_chatroom_topic()

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class ConversationEventAttendView(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid request body',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        conversation_manager = ConversationImpl(member_id=member_id)
        response = conversation_manager.attend_event(req_body)

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class SetConversationEventAttendedView(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid request body',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        conversation_manager = ConversationImpl(member_id=member_id)
        response = conversation_manager.set_event_attended(req_body)

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class FetchUnseenCountInEvent(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        conversation_manager = ConversationImpl(member_id=member_id)
        response_context = conversation_manager.fetch_unseen_count_in_event()

        if response_context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))

        return JsonResponse(response_context)


class UpdateLastSeenEventChatroom(APIView):

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        conversation_manager = ConversationImpl(member_id=member_id)
        response_context = conversation_manager.update_last_seen_event()

        if response_context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))

        return JsonResponse(response_context)


class FetchLinkForEvent(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        conversation_id = request.GET.get('conversation_id')

        conversation_manager = ConversationImpl(member_id=member_id, conversation_id=conversation_id)
        response_context = conversation_manager.fetch_link_for_event()

        if response_context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))

        return JsonResponse(response_context)


class FetchUserAllEvents(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        page = RequestUtilities.get_page_number(request)
        attending_status = StringUtilities.get_boolean_from_string(request.GET.get('attending_status', False))
        past_events = StringUtilities.get_boolean_from_string(request.GET.get('past_events', False))
        conversation_manager = ConversationImpl(member_id=member_id)
        response_context = conversation_manager.fetch_user_all_events(page, attending_status, past_events=past_events)

        if response_context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))

        return JsonResponse(response_context)


class FetchUnreadPreview(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        page = RequestUtilities.get_page_number(request)
        chatroom_id = request.GET.get('chatroom_id', None)
        paginate_by = RequestUtilities.get_page_size(request, key='paginate_by', default=20)
        conversation_manager = ConversationImpl(member_id=member_id, chatroom_id=chatroom_id, page=page,
                                                paginate_by=paginate_by)
        response = conversation_manager.fetch_unread_previews()

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class FetchPreviewUnreadMessageCount(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        chatroom_id = request.GET.get('chatroom_id', None)

        conversation_manager = ConversationImpl(member_id=member_id, chatroom_id=chatroom_id)
        response = conversation_manager.fetch_preview_unread_message_count()

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)
