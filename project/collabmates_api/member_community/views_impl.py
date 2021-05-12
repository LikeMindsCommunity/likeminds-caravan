from django.http import JsonResponse
from rest_framework.views import APIView

from collabmates_api.member_community.member_community_impl import MemberCommunityImpl
from collabmates_api.member_community.views_manager import ViewsManager
from utility.request_utilities import RequestUtilities
from utility.number_utilities import NumberUtilities
from collabmates_api.views import get_error_context
from utility.string_utilities import StringUtilities


class ViewsImpl(ViewsManager):

    def get_member_communities(self, user_id: int) -> JsonResponse:

        request = self

        page = request.GET.get('page', 1)
        page = NumberUtilities.get_integer_from_string(page, 1)

        member_id = RequestUtilities.get_member_id_from_headers(request)
        if not member_id:
            context = get_error_context(False, "member id missing in request")
            return JsonResponse(context, status=400)

        member_community_manager = MemberCommunityImpl(member_id, None)
        communities = member_community_manager.extract_member_communities(page)

        return JsonResponse({"your_communities": communities})


class FetchCommunityFeed(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)

        if not member_id:
            context = get_error_context(False, "member id missing in request")

            return JsonResponse(context, status=400)

        community_id = request.GET.get('community_id')

        pin_status = request.GET.get('pinned', False)
        pin_status = StringUtilities.get_boolean_from_string(pin_status)

        community_manager = MemberCommunityImpl(member_id, community_id, device_id=device_id)
        chatroom_id = request.GET.get('chatroom_id')
        scroll_direction = request.GET.get('scroll_direction')

        if (chatroom_id and not scroll_direction) or (scroll_direction and not chatroom_id):
            return JsonResponse({'error_message': "Invalid request parameters", 'status': 400})

        if scroll_direction is not None:
            scroll_direction = NumberUtilities.get_integer_from_string(scroll_direction)

        if RequestUtilities.is_request_android(request) or RequestUtilities.is_request_ios(request):

            chatroom_context = community_manager.fetch_feed(pin_status, chatroom_id=chatroom_id,
                                                            scroll_direction=scroll_direction)
        elif RequestUtilities.is_request_web(request):

            chatroom_context = community_manager.fetch_feed_web(pin_status, chatroom_id, scroll_direction)

        else:

            return JsonResponse({'error_message': "Invalid platform", 'status': 400})

        if 'error_message' in chatroom_context:
            response_context = {'error_message': chatroom_context['error_message']}
            status = chatroom_context['status']

            return JsonResponse(response_context, status=status)

        return JsonResponse(chatroom_context)


class FetchFeedMeta(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id = request.GET.get('community_id', "")

        if not member_id or not community_id:
            return JsonResponse({'error_message': 'Invalid parameters'}, status=400)

        member_community_manager = MemberCommunityImpl(member_id, community_id)

        feed_context = member_community_manager.fetch_feed_meta()

        if 'error_message' in feed_context:
            response_context = {'error_message': feed_context['error_message']}
            status = feed_context['status']

            return JsonResponse(response_context, status=status)

        return JsonResponse(feed_context)


class FetchHomeCommunities(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        page = request.GET.get('page', 1)

        if not member_id:
            return JsonResponse({'error_message': 'Invalid header member id'}, status=400)

        member_community_manager = MemberCommunityImpl(member_id, "")
        community_context = member_community_manager.fetch_home_communities(page)

        if 'error_message' in community_context:
            response_context = {'error_message': community_context['error_message']}
            status = community_context['status']

            return JsonResponse(response_context, status=status)

        return JsonResponse(community_context)


class FetchChatroomHome(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        chatroom_id = request.GET.get('chatroom_id')

        if not member_id:
            return JsonResponse({'error_message': 'Invalid header member id'}, status=400)

        member_community_manager = MemberCommunityImpl(member_id, "")
        chatroom_context = member_community_manager.fetch_chatroom_home(chatroom_id)

        if 'error_message' in chatroom_context:
            response_context = {'error_message': chatroom_context['error_message']}
            status = chatroom_context['status']

            return JsonResponse(response_context, status=status)

        return JsonResponse(chatroom_context)
