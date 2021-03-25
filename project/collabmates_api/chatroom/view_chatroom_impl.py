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


class FetchChatroomView(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        chatroom_id = request.GET.get('chatroom_id')
        source_id = request.GET.get('source_id')
        aj = request.GET.get('aj')

        chatroom_manager = ChatroomImpl(member_id, chatroom_id, source_id, aj)
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

        chatroom_manager = ChatroomImpl(member_id)
        context = chatroom_manager.create_chatroom(req_body)

        member_data = {'member_id': member_id, 'current_user_id': member_id, 'state_instance': None}
        chatroom_obj = GetChatroomInstanceSerializer(context['room_instance'], context=member_data, many=False)

        return JsonResponse({'success': True,
                             'chatroom': context['chatroom'],
                             'chatroom_local': chatroom_obj.data})


class SetChatroomActiveView(APIView):

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
            return JsonResponse(req_body, status=400)

        chatroom_manager = ChatroomImpl(member_id, req_body['chatroom_id'])

        context = chatroom_manager.pin_or_unpin_chatroom(req_body)

        if context.get('error_message'):
            return JsonResponse(context, status=400)

        return JsonResponse(context)


class PinUnpinChatroomViewHelper:

    @staticmethod
    def validate_request_for_pin_unpin_chatroom(request) -> {}:

        request_body = RequestUtilities.load_request_body(request)

        if not request_body:
            return {'error_message': "Invalid request body", 'status': 400}

        if 'chatroom_id' not in request_body or not request_body['chatroom_id']:
            return {'error_message': "send chatroom id", 'status': 400}

        if 'value' not in request_body:
            return {'error_message': "send value in request body", 'status': 400}

        if 'notify' not in request_body:
            return {'error_message': "send notify status", 'status': 400}

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
