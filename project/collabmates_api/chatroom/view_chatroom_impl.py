from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.string_utilities import StringUtilities
from utility.request_utilities import RequestUtilities
from utility.exception_utilities import InvalidHeaderException, CustomException
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from ..rest_api import GetChatroomInstanceSerializer
from ..chatroom.chatroom_impl import ChatroomImpl
from ..mixins import TransactionMixin
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()


class FetchChatroomView(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)

        chatroom_id = request.GET.get('chatroom_id')
        source_id = request.GET.get('source_id')
        aj = request.GET.get('aj')

        chatroom_manager = ChatroomImpl(member_id, chatroom_id, source_id, aj, device_id=device_id)
        chatroom_data = chatroom_manager.fetch_chatroom()

        return JsonResponse(chatroom_data)


class CreateChatroomView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(CreateChatroomView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.fetch_request_body(request)

        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)

        chatroom_manager = ChatroomImpl(member_id, device_id=device_id,
                                        request_platform=request_platform)
        context = chatroom_manager.create_chatroom(req_body)

        return JsonResponse(context)


class SetChatroomActiveView(TransactionMixin, APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SetChatroomActiveView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.fetch_request_body(request)

        chatroom_manager = ChatroomImpl(member_id)
        context = chatroom_manager.set_chatroom_active_or_inactive(req_body)

        return JsonResponse(context)


class PinUnpinChatroomView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(PinUnpinChatroomView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = PinUnpinChatroomViewHelper.validate_request_for_pin_unpin_chatroom(request)

        if req_body.get('error_message'):
            return JsonResponse(req_body, status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id, req_body['chatroom_id'])

        context = chatroom_manager.pin_or_unpin_chatroom(req_body)

        if context.get('error_message'):
            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(context)


class PinUnpinChatroomViewHelper:

    @staticmethod
    def validate_request_for_pin_unpin_chatroom(request) -> {}:

        request_body = RequestUtilities.load_request_body(request)

        if not request_body:
            return {'error_message': "Invalid request body", 'status': status_codes.HTTP_400_BAD_REQUEST}

        if 'chatroom_id' not in request_body or not request_body['chatroom_id']:
            return {'error_message': "send chatroom id", 'status': status_codes.HTTP_400_BAD_REQUEST}

        if 'value' not in request_body:
            return {'error_message': "send value in request body", 'status': status_codes.HTTP_400_BAD_REQUEST}

        if 'notify' not in request_body:
            return {'error_message': "send notify status", 'status': status_codes.HTTP_400_BAD_REQUEST}

        return request_body


class LeaveSecretChatroomView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(LeaveSecretChatroomView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        header_member_id = RequestUtilities.get_member_id_from_headers(request)

        if not header_member_id:
            raise InvalidHeaderException()

        chatroom_id = request.data.get('chatroom_id', None)
        member_id = request.data.get('member_id', None)

        chatroom_manager = ChatroomImpl(header_member_id, chatroom_id=chatroom_id)

        chatroom_manager.leave_secret_chatroom(member_id)

        context = {
            "success": True
        }

        return JsonResponse(context)


class AddSecretChatroomParticipantView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(AddSecretChatroomParticipantView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.fetch_request_body(request)

        chatroom_id = req_body.get('chatroom_id', None)

        if chatroom_id is None:
            response = {
                'success': False,
                'error_message': 'send chatroom id in body'
            }
            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id, chatroom_id=chatroom_id)

        chatroom_manager.add_secret_chatroom_participant(req_body)

        context = {
            "success": True
        }

        return JsonResponse(context)


class GetTaggingList(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        chatroom_id = request.GET.get('chatroom_id')

        chatroom_manager = ChatroomImpl(member_id, chatroom_id)

        try:
            chatroom_data = chatroom_manager.get_tagging_list()

        except Exception as e:

            error_logger.error(e.args)

            return JsonResponse({'error_message': "Internal server error"},
                                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)

        if chatroom_data.get('error_message'):
            return JsonResponse(chatroom_data, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(chatroom_data)


class AutoFollowChatroomForAllMembersView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(AutoFollowChatroomForAllMembersView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        header_member_id = RequestUtilities.get_member_id_from_headers(request)

        if not header_member_id:
            raise InvalidHeaderException()

        request_body = RequestUtilities.fetch_request_body(request)

        chatroom_id = request_body.get('chatroom_id', None)

        chatroom_manager = ChatroomImpl(header_member_id, chatroom_id=chatroom_id)

        response = chatroom_manager.follow_chatroom_automatically_for_all_members_of_community(header_member_id,
                                                                                               chatroom_id)

        if response.get('error_message'):
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response)


class EditChatroomView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(EditChatroomView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid request"})

        chatroom_manager = ChatroomImpl(member_id)

        response = chatroom_manager.edit_chatroom(req_body)

        if response.get('error_message'):
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response)


class FetchParticipantsOfSecretChatroom(APIView):

    def get(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        chatroom_id = request.GET.get('chatroom_id')

        chatroom_manager = ChatroomImpl(member_id, chatroom_id)

        try:
            chatroom_data = chatroom_manager.fetch_participants_of_secret_chatroom()

        except Exception as e:

            error_logger.error(e.args)

            return JsonResponse({'error_message': "Internal server error"},
                                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)

        if chatroom_data.get('error_message'):
            return JsonResponse(chatroom_data, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(chatroom_data)


class CreateEventView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(CreateEventView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid-request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=member_id)
        context = chatroom_manager.create_event(req_body)

        if context.get('error_message'):
            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(context)


class UpdateEventView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UpdateEventView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid-request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=member_id)

        context = chatroom_manager.update_event(req_body)

        if context.get('error_message'):
            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(context)


class EventAddInstructor(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'error_message': "Invalid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.add_instructor(req_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class EventAddHighlight(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'error_message': "Invalid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.add_highlights(req_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class EventAddMemberTestimonial(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'error_message': "Invalid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.add_member_testimonials(req_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class EventAddFAQ(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'error_message': "Invalid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.add_event_faq(req_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class UpdateLastSeenEventChatroom(APIView):

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.update_last_seen_event()

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class FetchUnseenCountInEvent(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.fetch_unseen_count_in_event()

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class FetchLinkForEvent(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        chatroom_id = request.GET.get('chatroom_id')
        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=chatroom_id)
        response_context = chatroom_manager.fetch_link_for_event()

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class FetchUserAllEvents(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        page = RequestUtilities.get_page_number(request)
        attending_status = StringUtilities.get_boolean_from_string(request.GET.get('attending_status', False))

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.fetch_user_all_events(page, attending_status)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class AttendEventView(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'status': False, 'error_message': "Invalid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.attend_event(req_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)
