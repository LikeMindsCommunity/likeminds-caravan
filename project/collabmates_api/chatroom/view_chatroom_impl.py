from django.http import JsonResponse
from collabmates_api.chatroom.chatroom_impl import ChatroomImpl
from utility.request_utilities import RequestUtilities
from rest_framework.views import APIView

class FetchChatroomView(APIView):

        '''inheriting API view class for using class based views in django'''

        def get(self, request):

            member_id = RequestUtilities.get_member_id_from_headers(request)

            chatroom_id = request.GET.get('chatroom_id')
            source_id = request.GET.get('source_id')
            aj = request.GET.get('aj')

            chatroom_manager = ChatroomImpl(member_id, chatroom_id, source_id, aj)
            chatroom_data = chatroom_manager.fetch_chatroom()
            return JsonResponse(chatroom_data)

