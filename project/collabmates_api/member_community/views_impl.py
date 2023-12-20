from sys import platform, version
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.request_utilities import RequestUtilities
from utility.number_utilities import NumberUtilities
from utility.string_utilities import StringUtilities
from utility.exception_utilities import InvalidHeaderException, CustomException
from utility.response_utilities import ResponseUtilities
from utility.version_utilities import VersionUtilities

from collabmates_api.views import get_error_context
from collabmates_api.member_community.member_community_impl import MemberCommunityImpl
from collabmates_api.member_community.member_community_view_helper import MemberCommunityViewHelper
from collabmates_api.member_community.views_manager import ViewsManager


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
        version_code = RequestUtilities.get_version_code_from_headers(request)
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        sdk_source = RequestUtilities.get_sdk_source_from_headers(request)
        api_version = RequestUtilities.get_accept_version_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not member_id:
            context = get_error_context(False, "member id missing in request")

            return JsonResponse(context, status=400)

        community_id = request.GET.get('community_id')

        pin_status = request.GET.get('pinned', False)
        pin_status = StringUtilities.get_boolean_from_string(pin_status)

        community_manager = MemberCommunityImpl(member_id, community_id, device_id=device_id, version_code=version_code,
                                                platform_code=platform_code, api_key=api_key)
        chatroom_id = request.GET.get('chatroom_id')
        scroll_direction = request.GET.get('scroll_direction')
        order_type = request.GET.get('order_type', 0)
        page = RequestUtilities.get_page_number(request)

        if (chatroom_id and not scroll_direction) or (scroll_direction and not chatroom_id):
            return JsonResponse({'error_message': "Invalid request parameters", 'status': 400})

        if scroll_direction is not None:
            scroll_direction = NumberUtilities.get_integer_from_string(scroll_direction)

        if order_type:
            order_type = NumberUtilities.get_integer_from_string(order_type)

        # version check for created_at epoch format change
        community_feed_date_uniform_check = VersionUtilities.check_version(platform_code=platform_code, 
                                                                           version_code=version_code, 
                                                                           feature_version_dict=VersionUtilities.community_feed_date_uniform,
                                                                           sdk_source=sdk_source)

        if RequestUtilities.is_request_any(request, [VersionUtilities.PlatformCode.ANDROID,
                                                     VersionUtilities.PlatformCode.IOS,
                                                     VersionUtilities.PlatformCode.FLUTTER,
                                                     VersionUtilities.PlatformCode.REACT_NATIVE]):
            chatroom_context = community_manager.fetch_feed(pin_status, chatroom_id=chatroom_id,
                                                            scroll_direction=scroll_direction,
                                                            api_version=api_version, order_type=order_type,
                                                            page=page, 
                                                            community_feed_date_uniform_check=community_feed_date_uniform_check)

        elif RequestUtilities.is_request_any(request, [VersionUtilities.PlatformCode.WEB,
                                                     VersionUtilities.PlatformCode.REACT]):
            chatroom_context = community_manager.fetch_feed_web(pin_status, order_type,
                                                                chatroom_id, scroll_direction, api_version=api_version,
                                                                page=page, 
                                                                community_feed_date_uniform_check=community_feed_date_uniform_check)

        else:
            chatroom_context = ResponseUtilities.get_impl_error_context("Invalid platform",
                                                                        status_code=status_codes.HTTP_400_BAD_REQUEST)

        if 'error_message' in chatroom_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatroom_context.get('error_message'),
                                                                                chatroom_context.get('status')))

        return JsonResponse(chatroom_context)


class FetchFeedMeta(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        platform_code = RequestUtilities.get_platform_code(request)

        community_id = request.GET.get('community_id', "")

        if not member_id or not community_id:
            return JsonResponse({'error_message': 'Invalid parameters'}, status=400)

        member_community_manager = MemberCommunityImpl(member_id, community_id,
                                                       version_code=version_code,
                                                       platform_code=platform_code)

        feed_context = member_community_manager.fetch_feed_meta()

        if 'error_message' in feed_context:
            response_context = {'error_message': feed_context['error_message']}
            status = feed_context['status']

            return JsonResponse(response_context, status=status)

        return JsonResponse(feed_context)


class FetchHomeCommunities(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        page = request.GET.get('page', 1)
        show_dm = request.GET.get('show_dm', False)
        is_cm = request.GET.get('is_cm', False)
        is_paid = request.GET.get('is_paid', False)
        community_id = request.GET.get('community_id', "")

        if not member_id:
            return JsonResponse({'error_message': 'Invalid header member id'}, status=400)

        member_community_manager = MemberCommunityImpl(member_id, community_id,
                                                       platform_code=platform_code,
                                                       version_code=version_code)
        community_context = member_community_manager.fetch_home_communities(page, show_dm=show_dm, is_cm=is_cm,
                                                                            is_paid=is_paid)

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
            error_message = 'Invalid header member id'
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(error_message,
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        member_community_manager = MemberCommunityImpl(member_id, "")
        chatroom_context = member_community_manager.fetch_chatroom_home(chatroom_id)

        if 'error_message' in chatroom_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatroom_context.get('error_message'),
                                                                                chatroom_context.get('status')))

        return JsonResponse(chatroom_context)


class FetchOnboardingCommunities(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            return JsonResponse({'error_message': 'Invalid header member id'}, status=400)

        page = request.GET.get('page', 1)
        paginate_by = request.GET.get('paginate_by', 10)

        page = NumberUtilities.get_integer_from_string(page)
        paginate_by = NumberUtilities.get_integer_from_string(paginate_by)
        member_community_manager = MemberCommunityImpl(member_id, "")
        community_context = member_community_manager.pending_onboarding_communities(page, paginate_by)

        if 'error_message' in community_context:
            response_context = {'error_message': community_context['error_message']}

            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context)


class CompleteCommunityOnboarding(APIView):

    def post(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'error_message': "Invalid request body"}, status=status_codes.HTTP_400_BAD_REQUEST)

        community_id = req_body.get('community_id')

        member_community_manager = MemberCommunityImpl(member_id, community_id)
        community_context = member_community_manager.completed_onboarding_communites()

        if 'error_message' in community_context:
            response_context = {'error_message': community_context['error_message']}

            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context)


class FetchUserDeletedCommunities(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        member_community_manager = MemberCommunityImpl(member_id, "")
        community_context = member_community_manager.fetch_deleted_communities()

        if 'error_message' in community_context:
            response_context = {'error_message': community_context['error_message']}

            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context)


class FetchMemberDetails(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        community_id = request.GET.get('community_id')

        if not community_id:
            response = {
                "success": False,
                "error_message": f"Send community_id in url params"
            }
            raise CustomException(response)

        page = RequestUtilities.get_page_number(request, default=1)
        page_size = RequestUtilities.get_page_size(request, default=10)

        member_community_manager = MemberCommunityImpl(member_id=member_id, community_id=community_id)
        community_context = member_community_manager.fetch_members_detail(page, page_size)

        return JsonResponse(community_context)


class ShowDmMessageIcon(APIView):

    def post(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_id = req_body.get('community_id')

        member_community_manager = MemberCommunityImpl(member_id, community_id)
        community_context = member_community_manager.show_dm(req_body)

        if 'error_message' in community_context:
            response_context = community_context

            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context, status=status_codes.HTTP_200_OK)


class FetchMemberProfileView(APIView):

    @staticmethod
    def _validate_request(member_id, req_body, api_key):

        if not member_id:
            return {'error_message': 'Send member_id'}

        if not req_body.get('community_id') and not api_key:
            return {'error_message': 'Send community_id or x-api-key'}

        if not (req_body.get('user_id') or req_body.get('uuid')):
            return {'error_message': 'Send user_id or uuid'}

        return {'success': True, 
                'community_id': req_body.get('community_id'), 
                'user_id': req_body.get('user_id'),
                'uuid': req_body.get('uuid')}

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)
        validated_req_body = self._validate_request(member_id, req_body, api_key)

        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        sdk_source = RequestUtilities.get_sdk_source_from_headers(request)

        community_hood_check = VersionUtilities.check_version(platform_code=platform_code, version_code=version_code, 
                                                              feature_version_dict=VersionUtilities.community_hood,
                                                              sdk_source=sdk_source)

        if not validated_req_body.get('success', False):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(validated_req_body.get('error_message'),
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        member_community_manager = MemberCommunityImpl(member_id, validated_req_body.get('community_id'),
                                                       api_key=api_key)
        community_context = member_community_manager.fetch_member_profile(validated_req_body.get('user_id'), 
                                                                          uuid=validated_req_body.get('uuid'),
                                                                          community_hood_check=community_hood_check)

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status')))

        return JsonResponse(community_context)


class EditMemberProfileView(APIView):

    @staticmethod
    def _validate_request(member_id, req_body, api_key):

        if not member_id:
            return {'error_message': 'Send member_id'}

        if not req_body.get('community_id') and not api_key:
            return {'error_message': 'Send community_id or x-api-key'}

        return {'success': True}

    def post(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)
        validated_req_body = self._validate_request(member_id, req_body, api_key)

        if not validated_req_body.get('success', False):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(validated_req_body.get('error_message'),
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        member_community_manager = MemberCommunityImpl(member_id, req_body.get('community_id'), api_key=api_key)
        community_context = member_community_manager.edit_member_profile(req_body)

        if 'error_message' in community_context:
            return JsonResponse(community_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(community_context, status=status_codes.HTTP_200_OK)


class RequestDMLimitView(APIView):

    @staticmethod
    def _validate_request(member_id, req_body):

        if not member_id:
            return {'error_message': 'Send member_id'}

        if not (req_body.get('member_id') or req_body.get('uuid')):
            return {'error_message': 'Send member_id or uuid'}

        return {'success': True, 
                'community_id': req_body.get('community_id'), 
                'user_id': req_body.get('member_id'),
                'uuid': req_body.get('uuid')}

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        validated_req_body = self._validate_request(member_id, req_body)

        if not validated_req_body.get('success', False):
            return JsonResponse({'success': False, 'error_message': "Invalid request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        member_community_manager = MemberCommunityImpl(member_id, validated_req_body.get('community_id'),
                                                       api_key=api_key)
        community_context = member_community_manager.request_dm_limit(validated_req_body.get('user_id'), 
                                                                      validated_req_body.get('uuid'))

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status')))

        return JsonResponse(community_context)


class FetchDMChatroomsView(APIView):

    @staticmethod
    def _validate_request(member_id, req_body):

        if not member_id:
            return {'error_message': 'Send member_id'}

        return {'success': True, 'community_id': req_body.get('community_id')}

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)
        validated_req_body = self._validate_request(member_id, req_body)
        device_id = RequestUtilities.get_device_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        page = RequestUtilities.get_page_number(request)

        if not validated_req_body.get('success', False):
            return JsonResponse({'success': False, 'error_message': "Invalid request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        member_community_manager = MemberCommunityImpl(member_id, validated_req_body.get('community_id'),
                                                       device_id=device_id, api_key=api_key)
        community_context = member_community_manager.fetch_dm_chatrooms(page=page,
                                                                        custom_tag=req_body.get('tag', ''))

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status')))

        return JsonResponse(community_context)


class MemberCanDMView(APIView):

    @staticmethod
    def _validate_request(member_id, req_body):

        if not member_id:
            return {'error_message': 'Send member_id'}

        return {'success': True, 'community_id': req_body.get('community_id')}

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        validated_req_body = self._validate_request(member_id, req_body)

        if not validated_req_body.get('success', False):
            return JsonResponse(validated_req_body, status=status_codes.HTTP_400_BAD_REQUEST)

        member_community_manager = MemberCommunityImpl(member_id, validated_req_body.get('community_id'),
                                                       api_key=api_key)
        community_context = member_community_manager.member_can_dm(req_body)

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status')))

        return JsonResponse(community_context)


class JoinCommunitySDKView(APIView):

    def post(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)
        validated_req_body = MemberCommunityViewHelper.validate_join_community_request(member_id)
        device_id = RequestUtilities.get_device_id_from_headers(request)
        platform_code = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        api_version = RequestUtilities.get_api_version_from_headers(request)

        if validated_req_body.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(validated_req_body.get('error_message'),
                                                                                validated_req_body.get('status')))

        member_community_manager = MemberCommunityImpl(member_id, community_id=req_body.get('community_id'),
                                                       device_id=device_id, platform_code=platform_code,
                                                       api_key=api_key, version_code=version_code,
                                                       api_version_code=api_version)
        community_context = member_community_manager.join_community_sdk(req_body=req_body)

        if 'error_message' not in community_context:
            return JsonResponse(community_context, status=status_codes.HTTP_200_OK)

        return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                            community_context.get('status_code')))

    def put(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)
        validated_req_body = MemberCommunityViewHelper.validate_join_community_request(member_id)
        device_id = RequestUtilities.get_device_id_from_headers(request)
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        api_version = RequestUtilities.get_api_version_from_headers(request)

        if validated_req_body.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(validated_req_body.get('error_message'),
                                                                                validated_req_body.get('status')))

        member_community_manager = MemberCommunityImpl(member_id, community_id=req_body.get('community_id'),
                                                       device_id=device_id, platform_code=platform_code,
                                                       api_key=api_key, version_code=version_code,
                                                       api_version_code=api_version)
        community_context = member_community_manager.approve_decline_join_community_request(
            req_body.get('uuid'), req_body.get('is_accepted', False))

        if 'error_message' not in community_context:
            return JsonResponse(community_context, status=status_codes.HTTP_200_OK)

        return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                            community_context.get('status_code')))


class UnsubscribeEmailNotificationsView(APIView):

    @staticmethod
    def _validate_request(member_id, req_body):

        if not member_id:
            return {'error_message': 'Query params missing'}

        if not req_body.get('community_id'):
            return {'error_message': 'Query params missing'}

        return {'success': True}

    def post(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)
        validated_req_body = self._validate_request(member_id, req_body)

        if not validated_req_body.get('success', False):
            return JsonResponse({'success': False, 'error_message': "Invalid request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        code_flags = req_body.get('code_flag', {})

        member_community_manager = MemberCommunityImpl(member_id, community_id=req_body.get('community_id'))
        community_context = member_community_manager.unsubscribe_email_notifications(code_flags=code_flags)

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status_code')))

        return JsonResponse(community_context, status=status_codes.HTTP_200_OK)

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_params = RequestUtilities.fetch_request_query_params(request)

        validated_req_body = self._validate_request(member_id, req_params)

        if not validated_req_body.get('success', False):
            return JsonResponse({'success': False, 'error_message': "Invalid request params"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        community_id = req_params.get("community_id")
        chatroom_id = req_params.get("chatroom_id")
        notification_codes = req_params.get("codes")

        member_community_manager = MemberCommunityImpl(member_id, community_id=community_id)
        community_context = member_community_manager.fetch_unsubscribe_email_notifications(chatroom_id=chatroom_id,
                                                                                           codes=notification_codes)

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status_code')))

        return JsonResponse(community_context, status=status_codes.HTTP_200_OK)


class FetchAccessView(APIView):

    @staticmethod
    def _validate_request(member_id, api_key, req_params):

        if not member_id:
            return ResponseUtilities.get_inner_error_context("Send x-member-id in headers")

        if not api_key:
            return ResponseUtilities.get_inner_error_context("Send x-api-key in headers")

        if not req_params:
            return ResponseUtilities.get_inner_error_context("Invalid request params")

        if not req_params.get('access_type'):
            return ResponseUtilities.get_inner_error_context("send access_type in request params")

        return {'success': True}

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_params = RequestUtilities.fetch_request_query_params(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        validated_req_params = self._validate_request(member_id, api_key, req_params)

        if not validated_req_params.get('success', False):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                validated_req_params.get('error_message'), status_codes.HTTP_400_BAD_REQUEST))

        member_community_manager = MemberCommunityImpl(member_id, None, api_key=api_key)
        community_context = member_community_manager.fetch_member_access(req_params.get('access_type'))

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status')))

        return JsonResponse(community_context)


class FetchPostFeedView(APIView):

    @staticmethod
    def _validate_request(member_id, api_key, req_params):

        if not member_id:
            return ResponseUtilities.get_inner_error_context("Send x-member-id in headers")

        if not api_key:
            return ResponseUtilities.get_inner_error_context("Send x-api-key in headers")

        if not req_params:
            return ResponseUtilities.get_inner_error_context("Invalid request params")

        if not req_params.get('order_type'):
            return ResponseUtilities.get_inner_error_context("send order_type in request params")

        return {'success': True}

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_params = RequestUtilities.fetch_request_query_params(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        validated_req_params = self._validate_request(member_id, api_key, req_params)

        if not validated_req_params.get('success', False):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                validated_req_params.get('error_message'), status_codes.HTTP_400_BAD_REQUEST))

        order_type = NumberUtilities.get_integer_from_string(req_params.get('order_type'), 0)
        pinned = req_params.get('pinned', '') == 'true'
        page = NumberUtilities.get_integer_from_string(req_params.get('page'), 1)
        page_size = NumberUtilities.get_integer_from_string(req_params.get('page_size'), 10)
        chatroom_ids = req_params.get('chatroom_ids')

        member_community_manager = MemberCommunityImpl(member_id, None, api_key=api_key)
        community_context = member_community_manager.fetch_post_feed(order_type, pinned, page, page_size, chatroom_ids)

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status')))

        return JsonResponse(community_context)


class FetchExcludedChatroomsView(APIView):

    @staticmethod
    def _validate_request(member_id, api_key):

        if not member_id:
            return ResponseUtilities.get_inner_error_context("Send x-member-id in headers")

        if not api_key:
            return ResponseUtilities.get_inner_error_context("Send x-api-key in headers")

        return {'success': True}

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        validated_req_params = self._validate_request(member_id, api_key)

        if not validated_req_params.get('success', False):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                validated_req_params.get('error_message'), status_codes.HTTP_400_BAD_REQUEST))

        member_community_manager = MemberCommunityImpl(member_id, None, api_key=api_key)
        community_context = member_community_manager.fetch_excluded_chatrooms_for_user()

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status')))

        return JsonResponse(community_context)


class FetchUserChatroomStatus(APIView):

    @staticmethod
    def _validate_request(member_id, api_key):

        if not member_id:
            return ResponseUtilities.get_inner_error_context("Send x-member-id in headers")

        if not api_key:
            return ResponseUtilities.get_inner_error_context("Send x-api-key in headers")

        return {'success': True}

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        validated_req_params = self._validate_request(member_id, api_key)
        req_params = RequestUtilities.fetch_request_query_params(request)
        page = RequestUtilities.get_page_number(request, default=1)
        page_size = RequestUtilities.get_page_size(request, default=10)
        chatroom_types = StringUtilities.get_list_from_string(req_params.get('chatroom_types'), default=[])

        if not validated_req_params.get('success', False):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                validated_req_params.get('error_message'), status_codes.HTTP_400_BAD_REQUEST))

        member_community_manager = MemberCommunityImpl(member_id, None, api_key=api_key)
        community_context = member_community_manager.fetch_user_chatroom_status(
            user_id=req_params.get('user_id'), chatroom_types=chatroom_types, page=page, page_size=page_size, uuid=req_params.get('uuid'))

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status')))

        return JsonResponse(community_context)


class UserHomeMeta(APIView):

    @staticmethod
    def _validate_request(member_id, api_key):

        if not member_id:
            return ResponseUtilities.get_inner_error_context("Send x-member-id in headers")

        if not api_key:
            return ResponseUtilities.get_inner_error_context("Send x-api-key in headers")

        return {'success': True}

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        validated_req_params = self._validate_request(member_id, api_key)

        if not validated_req_params.get('success', False):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(
                validated_req_params.get('error_message'), status_codes.HTTP_400_BAD_REQUEST))

        member_community_manager = MemberCommunityImpl(member_id, None, api_key=api_key)
        community_context = member_community_manager.fetch_user_home_meta()

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status')))

        return JsonResponse(community_context)
    
class PendingMembers(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not member_id:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context("Send x-member-id in headers",
                                                                                status_codes.HTTP_400_BAD_REQUEST))
        
        member_community_manager = MemberCommunityImpl(member_id, None, api_key=api_key)
        community_context = member_community_manager.fetch_pending_members()

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status')))

        return JsonResponse(community_context)
    
class LeaveCommunity(APIView):

    def delete(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not member_id:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context("Send x-member-id in headers",
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        member_community_manager = MemberCommunityImpl(member_id, None, api_key=api_key)
        community_context = member_community_manager.self_leave_community()

        if 'error_message' in community_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(community_context.get('error_message'),
                                                                                community_context.get('status_code')))

        return JsonResponse(community_context)

