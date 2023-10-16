from sys import platform
import json
from django.http import JsonResponse
from collabmates_api.community.community_impl import CommunityImpl
from utility.request_utilities import RequestUtilities
from rest_framework.views import APIView
from external_services.logging.logging_wrapper import LoggingWrapper

from utility.exception_utilities import InvalidHeaderException, CustomException
from utility.number_utilities import NumberUtilities
from utility.response_utilities import ResponseUtilities
from utility.version_utilities import VersionUtilities
from cms.cms_auth_utilities import CMSAuthUtilities
from rest_framework import status as status_codes

from ..rest_api import get_error_context

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class CreateCommunityView(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid request body"})

        community_manager = CommunityImpl(member_id, request_platform=request_platform, version_code=version_code)
        community_context = community_manager.create_community(req_body)

        if 'error_message' in community_context:
            return JsonResponse(community_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context)


class FetchCommunity(APIView):
    '''inheriting API view class for using class based views in django'''

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        community_id = request.GET.get('community_id')
        request_status = CommunityViewsHelper.request_validator(request, community_id, member_id)

        if not request_status['status']:

            return JsonResponse({
                'error_message': request_status['error_message']
            }, status=404)

        else:
            request_type = RequestUtilities.get_request_type(request)
            platform_code = RequestUtilities.get_platform_code(request)
            version_code = RequestUtilities.get_version_code_from_headers(request)

            community_manager = CommunityImpl(member_id, community_id, api_key=api_key)
            community_data = community_manager.fetch_community(client_type=request_type,
                                                               platform_code=platform_code,
                                                               version_code=version_code)

            if 'error_message' in community_data:
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_data.get('error_message'),
                                                                                    community_data.get('status')))
            return JsonResponse(community_data)


class FetchAllCommunities(APIView):
    '''inheriting API view class for using class based views in django'''

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        page = RequestUtilities.get_page_number(request, default=1)

        try:
            community_ids = json.loads(request.GET.get('community_ids'))

        except:
            community_ids = None

        community_manager = CommunityImpl(member_id)
        community_response = community_manager.fetch_all_communities(page=page, community_ids=community_ids)

        if 'error_message' in community_response:
            return JsonResponse({
                'success': False,
                'error_message': community_response['error_message']
            })

        return JsonResponse(community_response)


class FetchChatroomFeed(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        platform_code = RequestUtilities.get_platform_code(request)

        if not member_id:
            raise InvalidHeaderException()

        community_id = request.GET.get('community_id')
        size = request.GET.get('size', 2)

        size = NumberUtilities.get_integer_from_string(size)

        try:
            community_manager = CommunityImpl(member_id, community_id, version_code=version_code,
                                              request_platform=platform_code)
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
        version_code = RequestUtilities.get_version_code_from_headers(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid community"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id, req_body.get('community_id'), device_id=device_id,
                                          request_platform=request_platform, version_code=version_code)
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


class FetchCommunityFeedCM_OnboardingUrlView(APIView):

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
        response_context = community_manager.fetch_feed_url_for_cm_onboarding()

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


class FetchPaymentPageUrl(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        community_id = request.GET.get('community_id')

        payment_page_id = request.GET.get('payment_page_id')

        if not community_id:
            response = {
                "success": False,
                "error_message": "Send community_id in query params"
            }

            return JsonResponse(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        if not payment_page_id:
            response = {
                "success": False,
                "error_message": "Send payment_page_id in query params"
            }

            return JsonResponse(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id, community_id)
        response_context = community_manager.fetch_payment_page_url(payment_page_id)

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
        version_code = RequestUtilities.get_version_code_from_headers(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid Json Body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id, req_body.get('community_id'), device_id=device_id,
                                          request_platform=request_platform, version_code=version_code)
        community_context = community_manager.join_community(req_body)

        if 'error_message' in community_context:
            return JsonResponse(community_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context)


class FetchMembersMeta(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        sdk_source = RequestUtilities.get_sdk_source_from_headers(request)

        community_id = request.GET.get('community_id')
        member_ids = request.GET.get('member_ids')
        search_name = request.GET.get('search_name', "")
        page = RequestUtilities.get_page_number(request, default=1)
        page_size = RequestUtilities.get_page_size(request, default=50)

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id, api_key=api_key)

        try:
            # Pagination & search support for newer versions
            if VersionUtilities.check_version(platform_code, version_code,
                                              VersionUtilities.members_meta_pagination_and_search, sdk_source):
                community_data = community_manager.fetch_members_meta_v2(member_ids, page, page_size, search_name)

            else:
                community_data = community_manager.fetch_members_meta(member_ids)

        except Exception as e:
            error_logger.error(e.args)
            return JsonResponse({'error_message': "Internal server error"},status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)
       
        if 'error_message' in community_data:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_data.get('error_message'),
                                                                                community_data.get('status')))
        return JsonResponse(community_data)


class FetchContentDownloadSettings(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        community_id = request.GET.get('community_id')
        chatroom_id = request.GET.get('chatroom_id')

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id, api_key=api_key)

        content_settings_data = community_manager.fetch_content_download_settings(chatroom_id)

        if 'error_message' in content_settings_data:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                content_settings_data.get('error_message'), content_settings_data.get('status')))

        return JsonResponse(content_settings_data)


class UpdateContentDownloadSettings(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        content_download_settings = req_body.get('content_download_settings', [])

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key)

        content_setting_status = community_manager.update_content_download_settings(content_download_settings)

        if 'error_message' in content_setting_status:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                content_setting_status.get('error_message'), content_setting_status.get('status')))

        return JsonResponse(content_setting_status)


class FetchCommunitySettings(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        community_id = request.GET.get('community_id', None)

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id, version_code=version_code,
                                          request_platform=platform_code, api_key=api_key)

        response = community_manager.fetch_community_settings()

        if 'error_message' in response:
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response)


class UpdateCommunitySettings(APIView):
    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        community_settings = req_body.get('community_settings', [])
        community_id = req_body.get('community_id', None)

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id, api_key=api_key)

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

        return request_status


class FetchCommunityMeta(APIView):

    def _validate_request(self, aj):
        res = {}

        if not (aj and str(aj).isdigit()):
            res = get_error_context(False, "Invalid aj")

        return res

    def post(self, request):
        try:
            aj = request.query_params.get('aj')
            platform_code = RequestUtilities.get_platform_code(request)
            version_code = RequestUtilities.get_version_code_from_headers(request)

            request_validation_errors = self._validate_request(aj)

            if request_validation_errors:
                return JsonResponse(request_validation_errors, status=status_codes.HTTP_400_BAD_REQUEST)

            from .community_impl import CommunityHelper

            res = CommunityHelper.fetch_community_for_aj(aj, platform_code, version_code)

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


class FetchGetStartedView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        community_id = request.GET.get('community_id')

        if not community_id:
            return JsonResponse({'success': False, 'error_message': 'send community_id'},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id=member_id, community_id=community_id)

        content_settings_data = community_manager.fetch_get_started()

        if 'error_message' in content_settings_data:
            return JsonResponse(content_settings_data, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(content_settings_data)


class SendInviteView(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not member_id:
            return JsonResponse({'success': False, 'error_message': 'Send member_id'},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id=member_id, request_platform=platform_code,
                                          version_code=version_code, api_key=api_key)

        res = community_manager.send_invite(req_body)

        if 'error_message' in res:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        return JsonResponse(res)


class EditCommunityQuestionsView(APIView):

    def _validate_request(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        if not member_id:
            return {'success': False, 'error_message': 'Send member_id'}

        req_body['success'] = True
        req_body['member_id'] = member_id
        return req_body

    def post(self, request):
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        validated_body = self._validate_request(request)

        if not validated_body.get('success'):
            return JsonResponse(validated_body, status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id=validated_body.get('member_id'),
                                          community_id=validated_body.get('community_id'),
                                          version_code=version_code,
                                          request_platform=platform_code,
                                          api_key=api_key)

        res = community_manager.edit_questions(validated_body)

        if not res.get('success'):
            return JsonResponse(res, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(res, status=status_codes.HTTP_200_OK)


class FetchCommunityQuestionsView(APIView):

    def _validate_request(self, member_id, req_body):

        validated_req = {
            'success': True,
            'member_id': member_id,
            'community_id': req_body.get('community_id'),
            'aj': req_body.get('aj', None),
            'shared_by': req_body.get('shared_by', None)
        }

        return validated_req

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        validated_body = self._validate_request(member_id, req_body)
        sdk_source = RequestUtilities.get_sdk_source_from_headers(request)

        if not validated_body.get('success'):
            return JsonResponse(validated_body, status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id=validated_body.get('member_id'),
                                          community_id=validated_body.get('community_id'),
                                          version_code=version_code,
                                          request_platform=platform_code,
                                          api_key=api_key,
                                          sdk_source=sdk_source)

        res = community_manager.fetch_community_questions(validated_body)

        if 'error_message' in res:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        return JsonResponse(res)


class FetchCommunityBrandingView(APIView):

    def _validate_request(self, member_id, community_id, req_body):

        validated_req = {}

        if not member_id:
            return {'success': False, 'error_message': 'Send member_id'}

        if not community_id:
            return {'success': False, 'error_message': 'Send community_id'}

        validated_req['success'] = True
        validated_req['member_id'] = member_id
        validated_req['community_id'] = community_id
        validated_req['aj'] = req_body.get('aj', None)
        validated_req['shared_by'] = req_body.get('shared_by', None)

        return validated_req

    def get(self, request, community_id):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)
        validated_body = self._validate_request(member_id, community_id, req_body)

        if not validated_body.get('success'):
            return JsonResponse(validated_body, status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id=validated_body.get('member_id'),
                                          community_id=community_id,
                                          version_code=version_code,
                                          request_platform=platform_code)

        res = community_manager.fetch_community_branding_info(validated_body)

        if not res.get('success'):
            return JsonResponse(res, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(res, status=status_codes.HTTP_200_OK)


class FetchCommunityFromDomainView(APIView):

    def _validate_request(self, req_body, member_id):

        validated_req = {}

        if 'domain' not in req_body:
            return {'success': False, 'error_message': 'send domain'}

        validated_req['success'] = True
        validated_req['member_id'] = member_id
        validated_req['domain'] = req_body.get('domain')

        return validated_req

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)
        validated_body = self._validate_request(req_body, member_id)

        if not validated_body.get('success'):
            return JsonResponse(validated_body, status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id=validated_body.get('member_id'))

        res = community_manager.fetch_community_id_from_domain(validated_body)

        if not res.get('success'):
            return JsonResponse(res, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(res, status=status_codes.HTTP_200_OK)


class UpdateCommunityDMSettingsView(APIView):

    def _validate_request(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        if not member_id:
            return {'success': False, 'error_message': 'Send member_id'}

        req_body['success'] = True
        req_body['member_id'] = member_id
        return req_body

    def post(self, request):
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        validated_body = self._validate_request(request)

        if not validated_body.get('success'):
            return JsonResponse(validated_body, status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id=validated_body.get('member_id'),
                                          community_id=validated_body.get('community_id'),
                                          version_code=version_code,
                                          request_platform=platform_code,
                                          api_key=api_key)

        res = community_manager.update_community_dm_settings(validated_body)

        if res.get('success'):
            return JsonResponse(res, status=status_codes.HTTP_200_OK)

        return JsonResponse(res, status=status_codes.HTTP_400_BAD_REQUEST)


class FetchCommunityDMSettingsView(APIView):

    def _validate_request(self, member_id, req_body):

        validated_req = {}

        if not member_id:
            return {'success': False, 'error_message': 'Send member_id'}

        validated_req['success'] = True
        validated_req['member_id'] = member_id
        validated_req['community_id'] = req_body.get('community_id')

        return validated_req

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)
        validated_body = self._validate_request(member_id, req_body)

        if not validated_body.get('success'):
            return JsonResponse(validated_body, status=status_codes.HTTP_400_BAD_REQUEST)

        community_manager = CommunityImpl(member_id=validated_body.get('member_id'),
                                          community_id=validated_body.get('community_id'),
                                          version_code=version_code,
                                          request_platform=platform_code,
                                          api_key=api_key)

        res = community_manager.fetch_community_dm_settings()

        if res.get('success'):
            return JsonResponse(res, status=status_codes.HTTP_200_OK)

        return JsonResponse(res, status=status_codes.HTTP_400_BAD_REQUEST)


class FetchCommunityDMRightView(APIView):

    def _validate_request(self, member_id, req_body):

        validated_req = {}

        if not member_id:
            return {'success': False, 'error_message': 'Send member_id'}

        if not req_body.get('community_id'):
            return {'success': False, 'error_message': 'Send community_id'}

        validated_req['success'] = True
        validated_req['member_id'] = member_id
        validated_req['community_id'] = req_body.get('community_id')

        return validated_req

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)
        validated_body = self._validate_request(member_id, req_body)

        if not validated_body.get('success'):
            return JsonResponse(validated_body, status=status_codes.HTTP_200_OK)

        community_manager = CommunityImpl(member_id=validated_body.get('member_id'),
                                          community_id=validated_body.get('community_id'),
                                          version_code=version_code,
                                          request_platform=platform_code)

        res = community_manager.fetch_community_dm_right(req_body)

        if res.get('success'):
            return JsonResponse(res, status=status_codes.HTTP_200_OK)

        return JsonResponse(res, status=status_codes.HTTP_400_BAD_REQUEST)


class EditCommunityView(APIView):

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)
        username = RequestUtilities.get_user_name_from_headers(request)
        password = RequestUtilities.get_password_from_headers(request)

        community_manager = CommunityImpl(member_id=member_id, community_id=request_body.get('community_id'))
        community_data = community_manager.edit_community(request_body, username, password)

        if 'error_message' in community_data:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_data.get('error_message'),
                                                                                community_data.get('status')))
        return JsonResponse(community_data)


class CommunityMemberView(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key,
                                          request_platform=platform_code, version_code=version_code)
        community_data = community_manager.add_community_member(req_body)

        if community_data.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_data.get('error_message'),
                                                                                community_data.get('status')))
        return JsonResponse(community_data)

    def put(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key)
        community_data = community_manager.update_community_member(req_body)

        if community_data.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_data.get('error_message'),
                                                                                community_data.get('status')))
        return JsonResponse(community_data)
    
    def delete(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key)
        community_data = community_manager.remove_community_members(req_body)

        if community_data.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_data.get('error_message'),
                                                                                community_data.get('status')))
        return JsonResponse(community_data)


class CommunityNotificationSettings(APIView):

    def put(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        community_manager = CommunityImpl(member_id=member_id, community_id=req_body.get('community_id'),
                                          api_key=api_key)
        res = community_manager.update_community_noti_settings(req_body)

        if res.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        return JsonResponse(res)

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)

        community_manager = CommunityImpl(member_id=member_id, community_id=req_body.get('community_id'),
                                          api_key=api_key)
        res = community_manager.fetch_community_noti_settings()

        if res.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        return JsonResponse(res)


class FeedNotificationSettings(APIView):

    def put(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)
        notification_settings = req_body.get('notification_settings')

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key)
        res = community_manager.update_feed_notification_settings(notification_settings)

        if res.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        return JsonResponse(res)

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key)
        res = community_manager.fetch_feed_notification_settings()

        if res.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        return JsonResponse(res)


class UsersView(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_params = RequestUtilities.fetch_request_query_params(request)

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key)
        res = community_manager.fetch_users_meta_info(member_ids=req_params.get('member_ids'))

        if 'error_message' in res:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))

        return JsonResponse(res)
    

class ReportTagsView(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_params = RequestUtilities.fetch_request_query_params(request)

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key)

        res = community_manager.fetch_report_Tags(req_params.get('entity_type'))

        if 'error_message' in res:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        
        return JsonResponse(res)
    

class CommunityReportView(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key)
        res = community_manager.push_community_report(req_body)

        if 'error_message' in res:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        
        return JsonResponse(res)
    
    def delete(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key)
        res = community_manager.delete_community_reports(report_ids=req_body.get('report_ids'))

        if 'error_message' in res:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        
        return JsonResponse(res)


class CommunityConfigurationsView(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_params = RequestUtilities.fetch_request_query_params(request)

        community_manager = CommunityImpl(member_id=member_id,
                                          community_id=req_params.get('community_id'),
                                          api_key=api_key)
        res = community_manager.fetch_community_configurations(req_params.get('configuration_types'))

        if 'error_message' in res:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        
        return JsonResponse(res)


class RemovalReportsView(APIView):

    def get(self, request): 
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        community_manager = CommunityImpl(member_id=member_id, api_key=api_key)
        res = community_manager.fetch_community_removal_reports()

        if 'error_message' in res:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        
        return JsonResponse(res)
