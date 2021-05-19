from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes
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


class LeaveSecretChatroomView(TransactionMixin, APIView):

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


class AddSecretChatroomParticipantView(TransactionMixin, APIView):

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
