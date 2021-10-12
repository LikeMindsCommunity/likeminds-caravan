from django.http import JsonResponse
from collabmates_api.community.community_impl import CommunityImpl
from utility.request_utilities import RequestUtilities
from rest_framework.views import APIView
from external_services.logging.logging_wrapper import LoggingWrapper

from utility.exception_utilities import InvalidHeaderException, CustomException
from utility.number_utilities import NumberUtilities
from rest_framework import status as status_codes

from ..rest_api import get_error_context

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


class FetchAllCommunities(APIView):
    '''inheriting API view class for using class based views in django'''

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        page = RequestUtilities.get_page_number(request, default=1)

        community_manager = CommunityImpl(member_id)
        community_response = community_manager.fetch_all_communities(page=page)

        if 'error_message' in community_response:
            return JsonResponse({
                'success': False,
                'error_message': community_response['error_message']
            })

        return JsonResponse(community_response)


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

        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid community"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id, req_body.get('community_id'), device_id=device_id,
                                          request_platform=request_platform)
        community_context = community_manager.approve_or_decline_community(req_body)

        if 'error_message' in community_context:
            return JsonResponse(community_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context)


class FetchCommunityFeedUrl(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        community_id = request.GET.get('community_id')

        if not community_id:
            response = {
                "success": False,
                "error_message": "Send community_id in query params"
            }

            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id, community_id)
        response_context = community_manager.fetch_feed_url()

        return JsonResponse(response_context)


class FetchCommunityOTLUrl(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        community_id = request.GET.get('community_id')

        payment_id = request.GET.get('payment_id')
        shared_by = request.GET.get('shared_by')

        if not community_id:
            response = {
                "success": False,
                "error_message": "Send community_id in query params"
            }

            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        if not payment_id:
            response = {
                "success": False,
                "error_message": "Send payment_id in query params"
            }

            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id, community_id)
        response_context = community_manager.fetch_otl_url(payment_id, shared_by)

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


class CommunityJoinView(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid Json Body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id, req_body.get('community_id'), device_id=device_id,
                                          request_platform=request_platform)
        community_context = community_manager.join_community(req_body)

        if 'error_message' in community_context:
            return JsonResponse(community_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context)


class FetchMembersMeta(APIView):

    def get(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        community_id = request.GET.get('community_id')

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id)

        try:
            chatroom_data = community_manager.fetch_members_meta(community_id)

        except Exception as e:

            error_logger.error(e.args)

            return JsonResponse({'error_message': "Internal server error"},
                                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)

        if chatroom_data.get('error_message'):
            return JsonResponse(chatroom_data, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(chatroom_data)


class FetchContentDownloadSettings(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        community_id = request.GET.get('community_id')
        chatroom_id = request.GET.get('chatroom_id')

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id)

        content_settings_data = community_manager.fetch_content_download_settings(chatroom_id)

        if 'error_message' in content_settings_data:
            return JsonResponse(content_settings_data, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(content_settings_data)


class UpdateContentDownloadSettings(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        content_download_settings = req_body.get('content_download_settings', [])

        community_manager = CommunityImpl(member_id=member_id)

        content_setting_status = community_manager.update_content_download_settings(content_download_settings)

        if 'error_message' in content_setting_status:
            return JsonResponse(content_setting_status, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(content_setting_status)


class FetchCommunitySettings(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        community_id = request.GET.get('community_id', None)

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id)

        response = community_manager.fetch_community_settings()

        if 'error_message' in response:
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response)


class UpdateCommunitySettings(APIView):
    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.load_request_body(request)

        community_settings = req_body.get('community_settings', [])
        community_id = req_body.get('community_id', None)

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id)

        response = community_manager.update_community_settings(community_settings)

        if 'error_message' in response:
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response)


class FetchCommunityToastsV1View(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        community_id = request.GET.get('community_id', None)

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id)

        response = community_manager.fetch_community_toasts_v1()

        if 'error_message' in response:
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response)


class UpdateCommunityToastV1View(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        req_body = RequestUtilities.load_request_body(request)

        toast_id = req_body.get('toast_id', None)

        community_manager = CommunityImpl(member_id=member_id)

        response = community_manager.update_community_toast_v1(toast_id)

        if 'error_message' in response:
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response)


class JoinEmailAddView(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid body sent"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id, req_body.get('community_id'))
        community_context = community_manager.add_join_email(req_body)

        if 'error_message' in community_context:
            return JsonResponse(community_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context)


class JoinEmailFetchView(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            return JsonResponse({'success': False, 'error_message': "Member Id not sent in headers"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_id = request.GET.get('community_id', None)

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id)
        response = community_manager.fetch_join_email()

        if 'error_message' in response:
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response)


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


class FetchCommunityMeta(APIView):

    def _validate_request(self, member_id, aj):
        res = {}

        if not member_id:
            res = get_error_context(False, "Invalid member_id")

        elif not aj:
            res = get_error_context(False, "Invalid aj")

        return res

    def post(self, request):
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            aj = request.query_params.get('aj')

            request_validation_errors = self._validate_request(member_id, aj)

            if request_validation_errors:
                return JsonResponse(request_validation_errors, status=status_codes.HTTP_400_BAD_REQUEST)

            from .community_impl import CommunityHelper

            res = CommunityHelper.fetch_community_for_aj(aj)

            if res.get('success'):
                return JsonResponse(res, status=status_codes.HTTP_200_OK)
            
            else:
                return JsonResponse(res, status=status_codes.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            res = { 
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            
            return JsonResponse(res, status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)
