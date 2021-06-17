from django.http import JsonResponse
from collabmates_api.community.community_impl import CommunityImpl
from utility.request_utilities import RequestUtilities
from rest_framework.views import APIView
from external_services.logging.logging_wrapper import LoggingWrapper

from utility.exception_utilities import InvalidHeaderException
from utility.number_utilities import NumberUtilities
from rest_framework import status as status_codes

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class FetchCommunity(APIView):
    '''inheriting API view class for using class based views in django'''

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id = request.GET.get('community_id')
        request_status = CommunityViewsHelper.request_validator(request, community_id, member_id)

        if not request_status['status']:

            return JsonResponse({
                'error_message': request_status['error_message']
            }, status=404)

        else:
            request_type = RequestUtilities.get_request_type(request)
            community_manager = CommunityImpl(member_id, community_id)
            community_response = community_manager.fetch_community(client_type=request_type)

            if community_response['status']:
                return JsonResponse({
                    'community': community_response['community_context']
                }, status=community_response['response_code'])

            else:
                return JsonResponse({
                    'error_message': community_response['error_message']
                }, status=community_response['response_code'])


class FetchChatroomFeed(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        community_id = request.GET.get('community_id')
        size = request.GET.get('size', 2)

        size = NumberUtilities.get_integer_from_string(size)

        try:
            community_manager = CommunityImpl(member_id, community_id)
            response_context = community_manager.fetch_chatroom_feed(size)

        except Exception as e:

            error_logger.error(e.args)
            return JsonResponse({'error_message': "Internal server error"},
                                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class DeleteCommunityView(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid community"})

        community_manager = CommunityImpl(member_id, req_body.get('community_id'))
        community_context = community_manager.delete_community()

        if 'error_message' in community_context:
            return JsonResponse(community_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context)


class ApproveOrDeclineCommunity(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid community"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id, req_body.get('community_id'))
        community_context = community_manager.approve_or_decline_community(req_body)

        if 'error_message' in community_context:
            return JsonResponse(community_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context)


class FetchCommunityFeedUrl(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        community_id = request.GET.get('community_id')

        community_manager = CommunityImpl(member_id, community_id)
        response_context = community_manager.fetch_feed_url()

        return JsonResponse(response_context)


class FetchDiscoverableCommunities(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        page = RequestUtilities.get_page_number(request, default=1)
        page_size = RequestUtilities.get_page_size(request, default=20)

        community_manager = CommunityImpl(member_id, community_id="")
        response_context = community_manager.fetch_discoverable_communities(page=page, page_size=page_size)

        return JsonResponse(response_context)


class CommunityViewsHelper:

    def request_validator(request, community_id, member_id) -> {}:

        request_status = {
            'status': True
        }

        if not community_id:
            request_status['error_message'] = "invalid community_id"
            request_status['status'] = False

        elif not member_id and (
                RequestUtilities.is_request_ios(request) or RequestUtilities.is_request_android(request)):
            request_status['error_message'] = "invalid user_id"
            request_status['status'] = False

        return request_status
