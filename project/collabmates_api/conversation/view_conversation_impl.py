from django.http import JsonResponse
from collabmates_api.conversation.conversation_impl import ConversationImpl
from collabmates_api.utilities.request_utilities import RequestUtilities
from rest_framework.views import APIView

class FethcConversation(APIView):

        '''inheriting API view class for using class based views in django'''

        def get(self, request):

            member_id = RequestUtilities.get_member_id_from_headers(request)

            chatroom_id = request.GET.get('chatroom_id')
            scroll_direction = request.GET.get('scroll_direction')
            conversation_id = request.GET.get('conversation_id')
            page = request.GET.get('page',1)
            paginate_by = request.GET.get('paginate_by',200)

            conversation_manager = ConversationImpl(member_id, chatroom_id, scroll_direction, conversation_id, page, paginate_by)
            conversations = conversation_manager.fetch_conversation()

            return JsonResponse({
                'conversations':conversations
            })

