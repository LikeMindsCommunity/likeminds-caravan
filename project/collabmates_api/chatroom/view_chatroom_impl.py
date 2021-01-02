from django.http import JsonResponse
from ..chatroom.chatroom_impl import ChatroomImpl
from rest_framework.views import APIView
from ..rest_api import GetChatroomInstanceSerializer
from utility.request_utilities import RequestUtilities
from utility.exception_utilities import InvalidHeaderException


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
