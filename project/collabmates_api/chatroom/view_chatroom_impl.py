import json
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from utility.string_utilities import StringUtilities
from utility.request_utilities import RequestUtilities
from utility.exception_utilities import InvalidHeaderException, CustomException
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from utility.version_utilities import VersionUtilities
from ..rest_api import get_error_context
from ..chatroom.chatroom_impl import ChatroomImpl
from .chatroom_view_helper import ChatroomViewHelper
from ..mixins import TransactionMixin
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.response_utilities import ResponseUtilities
from utility.states import (api_types)
from utility.number_utilities import NumberUtilities

error_logger = LoggingWrapper.get_instance()


class FetchChatroomView(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)

        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        is_internal = StringUtilities.get_boolean_from_string(request.GET.get('is_internal'))

        chatroom_id = request.GET.get('chatroom_id')
        api_key = RequestUtilities.get_api_key_from_headers(request)

        chatroom_manager = ChatroomImpl(member_id, chatroom_id, device_id=device_id,
                                        request_platform=request_platform, version_code=version_code,
                                        api_key=api_key)
        chatroom_data = chatroom_manager.fetch_chatroom(is_internal=is_internal)

        if 'error_message' in chatroom_data:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatroom_data.get('error_message'),
                                                                                chatroom_data.get('status')))
        return JsonResponse(chatroom_data)


class FetchAllChatroomView(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        page = RequestUtilities.get_page_number(request)
        chatroom_filter_type = request.GET.get('filter_type')
        chatroom_excluded_type = request.GET.get('excluded_type')

        chatroom_manager = ChatroomImpl(member_id, device_id=device_id, request_platform=request_platform,
                                        version_code=version_code, api_key=api_key)

        if VersionUtilities.check_version(request_platform, version_code, VersionUtilities.fetch_all_chatrooms):
            chatroom_data = chatroom_manager.fetch_all_chatroom(chatroom_filter_type=chatroom_filter_type,
                                                                chatroom_excluded_type=chatroom_excluded_type,
                                                                page=page)

        else:
            chatroom_data = chatroom_manager.fetch_all_chatroom_old(chatroom_filter_type=chatroom_filter_type,
                                                                    chatroom_excluded_type=chatroom_excluded_type,
                                                                    page=page)

        if chatroom_data.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatroom_data.get('error_message'),
                                                                                chatroom_data.get('status')))
        return JsonResponse(chatroom_data)


class CreateChatroomView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(CreateChatroomView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.fetch_request_body(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        chatroom_manager = ChatroomImpl(member_id, device_id=device_id, request_platform=request_platform,
                                        api_key=api_key)
        chatroom_data = chatroom_manager.create_chatroom(req_body)

        if chatroom_data.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatroom_data.get('error_message'),
                                                                                chatroom_data.get('status')))
        return JsonResponse(chatroom_data)


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
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                                context.get('status')))
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


class LeaveSecretChatroomView(APIView):

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


class AddSecretChatroomParticipantView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(AddSecretChatroomParticipantView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.fetch_request_body(request)
        chatroom_id = req_body.get('chatroom_id', None)

        chatroom_manager = ChatroomImpl(member_id, chatroom_id=chatroom_id)
        chatroom_data = chatroom_manager.add_secret_chatroom_participant(req_body, is_internal=False)

        if 'error_message' in chatroom_data:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatroom_data.get('error_message'),
                                                                                chatroom_data.get('status')))

        return JsonResponse(chatroom_data)


class GetTaggingList(APIView):
    """ inheriting API view class for using class based views in django """

    def get(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        chatroom_id = request.GET.get('chatroom_id')
        search_name = request.GET.get('search_name', None)
        page = RequestUtilities.get_page_number(request, default=1)
        page_size = RequestUtilities.get_page_size(request, default=50)
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        sdk_source = RequestUtilities.get_sdk_source_from_headers(request)

        chatroom_manager = ChatroomImpl(member_id, chatroom_id)

        try:
            if VersionUtilities.check_version(platform_code, version_code, VersionUtilities.group_tags, sdk_source):
                chatroom_data = chatroom_manager.get_tagging_list(search_name, page=page, page_size=page_size)

            else:
                """
                version check and old method call plus method definition
                can be removed safely when version dict has valid values for all platforms
                """
                chatroom_data = chatroom_manager.get_tagging_list_old()

        except Exception as e:

            error_logger.error(e.args)

            return JsonResponse({'error_message': "Internal server error"},
                                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)

        if 'error_message' in chatroom_data:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatroom_data.get('error_message'),
                                                                                chatroom_data.get('status')))

        return JsonResponse(chatroom_data)


class AutoFollowChatroomForAllMembersView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(AutoFollowChatroomForAllMembersView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        header_member_id = RequestUtilities.get_member_id_from_headers(request)

        if not header_member_id:
            raise InvalidHeaderException()

        request_body = RequestUtilities.load_request_body(request)
        chatroom_manager = ChatroomImpl(header_member_id, chatroom_id=request_body.get('chatroom_id', None))
        response = chatroom_manager.follow_chatroom_automatically_for_all_members_of_community(header_member_id,
                                                                                               request_body)

        if 'error_message' in response:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class EditChatroomView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(EditChatroomView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        validated_req = ChatroomViewHelper.validate_req_body(req_body)

        if validated_req.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(validated_req.get('error_message'),
                                                                                validated_req.get('status')))

        chatroom_manager = ChatroomImpl(member_id, chatroom_id=req_body.get('chatroom_id'), api_key=api_key)
        chatroom_data = chatroom_manager.edit_chatroom(req_body)

        if chatroom_data.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatroom_data.get('error_message'),
                                                                                chatroom_data.get('status')))

        return JsonResponse(chatroom_data)


class FetchParticipantsOfSecretChatroom(APIView):

    def get(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        chatroom_id = request.GET.get('chatroom_id')
        page = RequestUtilities.get_page_number(request, default=1)
        page_size = RequestUtilities.get_page_size(request, default=10)
        participant_name = request.GET.get('participant_name')
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        sdk_source = RequestUtilities.get_sdk_source_from_headers(request)

        chatroom_manager = ChatroomImpl(member_id, chatroom_id, request_platform=platform_code,
                                        version_code=version_code, sdk_source=sdk_source)

        pagination_version_check = VersionUtilities.check_version(platform_code, version_code,
                                                                  VersionUtilities.participants_meta_pagination,
                                                                  sdk_source)

        if not pagination_version_check:
            page, page_size = None, None

        try:
            chatroom_data = chatroom_manager.fetch_participants_of_secret_chatroom(participant_name, page, page_size)

            if chatroom_data.get('error_message'):
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatroom_data.get('error_message'),
                                                                                    chatroom_data.get('status')))

            return JsonResponse(chatroom_data)

        except Exception as e:

            error_logger.error(e.args)

            return JsonResponse({'success': False, 'error_message': "Internal server error"},
                                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateEventView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(CreateEventView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)
        request_platform = RequestUtilities.get_platform_code(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid-request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=member_id, request_platform=request_platform,
                                        version_code=version_code)
        context = chatroom_manager.create_event(req_body)

        if context.get('error_message'):
            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(context)


class UpdateEventView(APIView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UpdateEventView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False, 'error_message': "Invalid-request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))

        context = chatroom_manager.update_event(req_body)

        if 'error_message' in context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                                context.get('status')))

        return JsonResponse(context)


class EventAddOrUpdateInstructor(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'error_message': "Invalid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.add_or_update_instructor(req_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class EventAddOrUpdateHighlight(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'error_message': "Invalid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.add_or_update_highlights(req_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class EventAddOrUpdateMemberTestimonial(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'error_message': "Invalid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.add_or_update_member_testimonials(req_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class EventAddOrUpdateFAQ(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'error_message': "Invalid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.add_or_update_event_faq(req_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class UpdateLastSeenEventChatroom(APIView):

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id: str = request.POST.get('community_id')

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.update_last_seen_event(community_id)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class FetchUnseenCountInEvent(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id: str = request.GET.get('community_id')

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.fetch_unseen_count_in_event(community_id)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class FetchLinkForEvent(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        chatroom_ids = self.get_chatroom_ids_from_query_params(request)
        chatroom_id = request.GET.get('chatroom_id')
        if request.GET.get('is_edit_mode'):
            is_edit_mode = StringUtilities.get_boolean_from_string(request.GET.get('is_edit_mode'))
        else:
            is_edit_mode = None

        if chatroom_id:
            chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=chatroom_id)
            response_context = chatroom_manager.fetch_link_for_event(is_edit_mode)

        else:
            response_context = ChatroomImpl.fetch_link_for_events_list(is_edit_mode, member_id=member_id,
                                                                    chatroom_ids=chatroom_ids)

        if response_context.get('error_message'):
            response_context['success'] = False
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        response_context['success'] = True
        return JsonResponse(response_context)

    def get_chatroom_ids_from_query_params(self, request):

        chatroom_ids = []

        try:
            chatroom_ids = json.loads(request.GET.get('chatroom_ids'))
        except:
            pass

        return chatroom_ids


class FetchUserAllEvents(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        page = RequestUtilities.get_page_number(request)
        past_events = StringUtilities.get_boolean_from_string(request.GET.get('past_events', False))
        community_id = request.GET.get('community_id')

        if request.GET.get('attending_status'):
            attending_status = StringUtilities.get_boolean_from_string(request.GET.get('attending_status'))
        else:
            attending_status = None

        if request.GET.get('has_content'):
            has_content = StringUtilities.get_boolean_from_string(request.GET.get('has_content'))
        else:
            has_content = None

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.fetch_user_all_events(page, attending_status, has_content,
                                                                  past_events=past_events, community_id=community_id)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class FetchUserAllEventsMeta(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        past_events = StringUtilities.get_boolean_from_string(request.GET.get('past_events', False))
        community_id = request.GET.get('community_id')

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.fetch_user_all_events_meta(past_events=past_events, community_id=community_id)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class AttendEventView(APIView):

    def post(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'status': False, 'error_message': "Invalid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id)
        response_context = chatroom_manager.attend_event(req_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class SetEventAttendedView(APIView):

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False,
                                 'error_message': "In-valid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
        response_context = chatroom_manager.set_event_attended()

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class EnableMemberMessageInChatroomView(APIView):
    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False,
                                 'error_message': "In-valid request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        value = req_body.get('value')
        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
        response_context = chatroom_manager.toggle_member_message_post(value)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class FetchChatroomSettingsView(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        request_platform = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)

        chatroom_id = request.GET.get('chatroom_id')
        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=chatroom_id,
                                        request_platform=request_platform, version_code=version_code)
        response_context = chatroom_manager.fetch_chatroom_settings()

        if response_context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))

        return JsonResponse(response_context)


class AddMembersToChatroomView(APIView):
  
    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False,
                                 'error_message': "In-valid request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_participants = req_body.get('chatroom_participants')
        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
        response_context = chatroom_manager.add_members_to_chatroom(chatroom_participants)

        if response_context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))

        return JsonResponse(response_context)


class ChatroomUpdateFilesView(APIView):

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False,
                                 'error_message': "In-valid request body"})

        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
        response_context = chatroom_manager.update_files(req_body)

        if response_context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))

        return JsonResponse(response_context)


class FetchEventLinkForDashboard(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        chatroom_id = request.GET.get('chatroom_id')
        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=chatroom_id)
        response_context = chatroom_manager.fetch_event_link_for_dashboard()

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class UpdateAccessWithOutSubscriptionView(APIView):

    def post(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        req_body = RequestUtilities.load_request_body(request)

        if not req_body:
            return JsonResponse({'success': False,
                                 'error_message': "Invalid request body"},
                                status=status_codes.HTTP_400_BAD_REQUEST)

        value = req_body.get('value')
        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
        context = chatroom_manager.update_access_without_subscription(value=value)

        if context.get('error_message'):
            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(context)


class FetchAccessChatroomView(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        chatroom_id = request.GET.get('chatroom_id')

        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=chatroom_id)
        response_context = chatroom_manager.fetch_access_for_chatroom()

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context)


class ChangeChatroomTypeView(APIView):

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid member-id',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        req_body = RequestUtilities.load_request_body(request)

        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)

        chatroom_manager = ChatroomImpl(member_id, device_id=device_id,
                                        request_platform=request_platform)
        context = chatroom_manager.change_chatroom_type(req_body)

        if context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                                context.get('status')))

        return JsonResponse(context)

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context('Invalid member-id',
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        chatroom_id = request.GET.get('chatroom_id')

        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)

        chatroom_manager = ChatroomImpl(member_id, chatroom_id=chatroom_id, device_id=device_id,
                                        request_platform=request_platform)
        context = chatroom_manager.get_change_chatroom_type_status()

        if context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(context.get('error_message'),
                                                                                context.get('status')))

        return JsonResponse(context)


class AddEventRecordingAttachmentMeta(APIView):

    def _validate_request(self, member_id, req_body):
        res = {}

        if not member_id:
            res = get_error_context(False, "Invalid member_id")

        elif not req_body:
            res = get_error_context(False, "Invalid request body")

        elif not req_body.get('about_recording') and not req_body.get('recording_url'):
            res = get_error_context(False, "Both about_recording and recording_url cannot be empty")

        elif not req_body.get('chatroom_id') and not req_body.get('conversation_id'):
            res = get_error_context(False, "Both chatroom_id and conversation_id cannot be empty")

        return res

    def post(self, request):
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_request(member_id, req_body)

            if request_validation_errors:
                return JsonResponse(request_validation_errors, status=status_codes.HTTP_400_BAD_REQUEST)

            res = ChatroomImpl.update_chatroom_or_conversation_instance_with_event_attachments_metadata(req_body, member_id)

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


class AddEventRecordingAttachment(APIView):

    def _validate_request(self, member_id, req_body):
        res = {}

        if not member_id:
            res = get_error_context(False, "Invalid member_id")

        elif not req_body:
            res = get_error_context(False, "Invalid request body")

        elif not req_body.get('chatroom_id') and not req_body.get('conversation_id'):
            res = get_error_context(False, "Both chatroom_id and conversation_id cannot be empty")

        return res

    def post(self, request):
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_request(member_id, req_body)

            if request_validation_errors:
                return JsonResponse(request_validation_errors, status=status_codes.HTTP_400_BAD_REQUEST)

            res, is_attachment_instance_created = ChatroomImpl.add_event_attachments(req_body, member_id)

            if is_attachment_instance_created:
                return JsonResponse(res, status=status_codes.HTTP_201_CREATED)

            return JsonResponse(res, status=status_codes.HTTP_400_BAD_REQUEST)

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(res, status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteEventRecordingAttachmentMeta(APIView):

    def _validate_request(self, member_id, req_body):
        res = {}

        if not member_id:
            res = get_error_context(False, "Invalid member_id")

        elif not req_body:
            res = get_error_context(False, "Invalid request body")

        elif not req_body.get('id'):
            res = get_error_context(False, "id cannot be empty")

        elif not req_body.get('chatroom_id') and not req_body.get('conversation_id'):
            res = get_error_context(False, "Both chatroom_id and conversation_id cannot be empty")

        return res

    def post(self, request):
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_request(member_id, req_body)

            if request_validation_errors:
                return JsonResponse(request_validation_errors, status=status_codes.HTTP_400_BAD_REQUEST)

            res = ChatroomImpl.delete_event_attachment_metadata_from_chatroom_or_conversation_instance(req_body, member_id)

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


class DeleteEventRecordingAttachment(APIView):

    def _validate_request(self, member_id, req_body):

        res = {}

        if not member_id:
            res = get_error_context(False, "Invalid member_id")

        elif not req_body:
            res = get_error_context(False, "Invalid request body")

        elif not req_body.get('id'):
            res = get_error_context(False, "id cannot be empty")

        return res

    def post(self, request):
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_request(member_id, req_body)

            if request_validation_errors:
                return JsonResponse(request_validation_errors, status=status_codes.HTTP_400_BAD_REQUEST)

            res = ChatroomImpl.delete_event_attachments(req_body.get('id'), member_id)

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


class RemoveCohortFromChatroomView(APIView):

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        header_member_id = RequestUtilities.get_member_id_from_headers(request)

        if not request_body:
            response = {'success': False, 'error_message': "Invalid request body"}

            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=header_member_id)
        response_context = chatroom_manager.remove_cohort_from_chatroom(request_body=request_body)

        if response_context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))

        return JsonResponse(response_context)


class AddCohortToChatroomView(APIView):

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        header_member_id = RequestUtilities.get_member_id_from_headers(request)

        if not request_body:
            response = {'success': False, 'error_message': "Invalid request body"}

            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=header_member_id)
        response_context = chatroom_manager.add_cohort_to_chatroom(request_body=request_body)

        if response_context.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))

        return JsonResponse(response_context)


class FetchChatroomParticipantsView(APIView):

    def get(self, request, *args, **kwargs):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        chatroom_id = request.GET.get('chatroom_id')
        page = RequestUtilities.get_page_number(request, default=1)
        page_size = RequestUtilities.get_page_size(request, default=10)
        participant_name = request.GET.get('participant_name')
        platform_code = RequestUtilities.get_platform_code_with_sdk(request)
        version_code = RequestUtilities.get_version_code_from_headers(request)
        sdk_source = RequestUtilities.get_sdk_source_from_headers(request)


        chatroom_manager = ChatroomImpl(member_id, chatroom_id, request_platform=platform_code,
                                        version_code=version_code, sdk_source=sdk_source)

        pagination_version_check = VersionUtilities.check_version(platform_code, version_code,
                                                                  VersionUtilities.participants_meta_pagination,
                                                                  sdk_source)

        if not pagination_version_check:
            page, page_size = None, None

        try:
            chatroom_data = chatroom_manager.fetch_chatroom_participants(participant_name, page, page_size)

            if chatroom_data.get('error_message'):
                return JsonResponse(**ResponseUtilities.get_view_impl_error_context(chatroom_data.get('error_message'),
                                                                                    chatroom_data.get('status')))

            return JsonResponse(chatroom_data)

        except Exception as e:

            error_logger.error(e.args)

            response = {
                'success': False,
                'error_message': "Internal Server Error"
            }

            return JsonResponse(response, status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)


class PublishEventWebflowView(APIView):

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        header_member_id = RequestUtilities.get_member_id_from_headers(request)

        if not request_body:
            response = {'success': False, 'error_message': "Invalid request body"}

            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        if not header_member_id:
            response = {'success': False, 'error_message': "Send member-id in headers"}

            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=header_member_id)
        response_context = chatroom_manager.publish_event_webflow(req_body=request_body)

        if response_context.get('error_message'):
            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response_context, status=status_codes.HTTP_200_OK)


class CreateDMChatroomView(APIView):

    def _validate_request(self, member_id, req_body):

        if not member_id:
            return {'success': False, 'error_message': "Send member-id in headers"}

        if not req_body:
            return {'success': False, 'error_message': "Invalid request body"}

        if not req_body.get('member_id'):
            return {'success': False, 'error_message': "Empty Member ID!"}

        return {'success': True}

    def post(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.load_request_body(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        validated_request = self._validate_request(member_id, req_body)

        if not validated_request.get('success'):
            return JsonResponse(validated_request, status=status_codes.HTTP_400_BAD_REQUEST)

        device_id = RequestUtilities.get_device_id_from_headers(request)
        request_platform = RequestUtilities.get_platform_code(request)

        chatroom_manager = ChatroomImpl(member_id, device_id=device_id, request_platform=request_platform,
                                        api_key=api_key)
        response_context = chatroom_manager.create_dm_chatroom(req_body)

        if 'error_message' in response_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))
        return JsonResponse(response_context)


class BlockMemberView(APIView):

    def _validate_request(self, member_id, req_body):

        if not member_id:
            return {'success': False, 'error_message': "Send member-id in headers"}

        if not req_body:
            return {'success': False, 'error_message': "Invalid request body"}

        if not req_body.get('chatroom_id'):
            return {'success': False, 'error_message': "Empty Chatroom ID!"}

        return {'success': True}

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        header_member_id = RequestUtilities.get_member_id_from_headers(request)

        validated_request = self._validate_request(header_member_id, request_body)

        if not validated_request.get('success'):
            return JsonResponse(validated_request, status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=header_member_id, chatroom_id=request_body.get('chatroom_id'))
        response_context = chatroom_manager.block_member(req_body=request_body)

        if response_context.get('success'):
            return JsonResponse(response_context, status=status_codes.HTTP_200_OK)

        return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)


class RequestDMView(APIView):

    def _validate_request(self, member_id, req_body):

        if not member_id:
            return {'success': False, 'error_message': "Send member-id in headers"}

        if not req_body:
            return {'success': False, 'error_message': "Invalid request body"}

        if not req_body.get('chatroom_id'):
            return {'success': False, 'error_message': "Empty Chatroom ID!"}

        return {'success': True}

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        header_member_id = RequestUtilities.get_member_id_from_headers(request)
        platform_code = RequestUtilities.get_platform_code(request)
        device_id = RequestUtilities.get_device_id_from_headers(request)

        validated_request = self._validate_request(header_member_id, request_body)

        if not validated_request.get('success'):
            return JsonResponse(validated_request, status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=header_member_id, chatroom_id=request_body.get('chatroom_id'),
                                        device_id=device_id, request_platform=platform_code)
        response_context = chatroom_manager.request_dm(req_body=request_body)

        if response_context.get('success'):
            return JsonResponse(response_context, status=status_codes.HTTP_200_OK)

        return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)


class ScheduledChatroomFollow(APIView):

    def _validate_request(self, member_id, req_body):

        if not member_id:
            return {'success': False, 'error_message': "Send member-id in headers"}

        if not req_body:
            return {'success': False, 'error_message': "Invalid request body"}

        if not req_body.get('chatroom_id'):
            return {'success': False, 'error_message': "Invalid Chatroom ID!"}

        return {'success': True}

    def post(self, request):
        try:
            req_body = RequestUtilities.load_request_body(request)
            member_id = RequestUtilities.get_member_id_from_headers(request)

            validated_request = self._validate_request(member_id, req_body)

            if not validated_request.get('success'):
                return JsonResponse(validated_request, status=status_codes.HTTP_400_BAD_REQUEST)

            chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
            response_context = chatroom_manager.scheduled_chatroom_follow()

            if response_context.get('success'):
                return JsonResponse(response_context, status=status_codes.HTTP_200_OK)

            return JsonResponse(response_context, status=status_codes.HTTP_400_BAD_REQUEST)

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatroomNotificationSettings(APIView):

    def _validate_request(self, member_id, req_body):

        if not member_id:
            return {'success': False, 'error_message': "Send x-member-id in headers"}

        if not req_body:
            return {'success': False, 'error_message': "Invalid request body"}

        if not req_body.get('chatroom_id'):
            return {'success': False, 'error_message': "Invalid Chatroom ID!"}

        return {'success': True}

    def put(self, request):
        req_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)

        validated_request = self._validate_request(member_id, req_body)

        if not validated_request.get('success'):
            return JsonResponse(validated_request, status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
        response_context = chatroom_manager.update_chatroom_noti_settings(req_body.get('noti_state'),
                                                                          req_body.get('is_noti_paused'),
                                                                          req_body.get('pause_noti_for'))

        if 'error_message' in response_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))
        return JsonResponse(response_context)

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)

        community_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
        res = community_manager.fetch_chatroom_noti_settings()

        if res.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        return JsonResponse(res)


class ChatroomParticipants(APIView):

    def _validate_request(self, member_id, req_body):

        if not member_id:
            return {'success': False, 'error_message': "Send x-member-id in headers"}

        if not req_body:
            return {'success': False, 'error_message': "Invalid request body"}

        if not req_body.get('chatroom_id'):
            return {'success': False, 'error_message': "Invalid Chatroom ID!"}

        return {'success': True}

    def delete(self, request):
        req_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)

        validated_request = self._validate_request(member_id, req_body)

        if validated_request.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(validated_request.get('error_message'),
                                                                                status_codes.HTTP_400_BAD_REQUEST))

        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
        response_context = chatroom_manager.remove_chatroom_participant(
            removed_members_list=req_body.get('removed_members'))

        if 'error_message' in response_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))
        return JsonResponse(response_context)


class ChatroomInvites(APIView):

    def _validate_request(self, member_id, req_body):

        if not member_id:
            return {'success': False, 'error_message': "Send x-member-id in headers"}

        if not req_body:
            return {'success': False, 'error_message': "Invalid request body"}

        if not req_body.get('chatroom_id'):
            return {'success': False, 'error_message': "Invalid Chatroom ID!"}

        return {'success': True}

    def put(self, request):
        req_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)

        validated_request = self._validate_request(member_id, req_body)

        if not validated_request.get('success'):
            return JsonResponse(validated_request, status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
        response_context = chatroom_manager.update_chatroom_invites(invite_status=req_body.get('invite_status'))

        if 'error_message' in response_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))
        return JsonResponse(response_context)

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        req_body = RequestUtilities.fetch_request_query_params(request)
        page = RequestUtilities.get_page_number(request)
        page_size = RequestUtilities.get_page_size(request, default=10)
        chatroom_types = StringUtilities.get_list_from_string(req_body.get('chatroom_types'), default=[])

        community_manager = ChatroomImpl(member_id=member_id, api_key=api_key)
        res = community_manager.get_chatroom_invites(chatroom_types, page, page_size)

        if res.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(res.get('error_message'),
                                                                                res.get('status')))
        return JsonResponse(res)


class ChatroomSettings(APIView):

    def _validate_request(self, member_id, req_body):

        if not member_id:
            return {'success': False, 'error_message': "Send x-member-id in headers"}

        if not req_body:
            return {'success': False, 'error_message': "Invalid request body"}

        if not req_body.get('chatroom_id'):
            return {'success': False, 'error_message': "Invalid Chatroom ID!"}

        return {'success': True}

    def put(self, request):
        req_body = RequestUtilities.load_request_body(request)
        member_id = RequestUtilities.get_member_id_from_headers(request)

        validated_request = self._validate_request(member_id, req_body)

        if not validated_request.get('success'):
            return JsonResponse(validated_request, status=status_codes.HTTP_400_BAD_REQUEST)

        chatroom_manager = ChatroomImpl(member_id=member_id, chatroom_id=req_body.get('chatroom_id'))
        response_context = chatroom_manager.update_chatroom_settings(
            chatroom_settings=req_body.get('chatroom_settings'))

        if 'error_message' in response_context:
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response_context.get('error_message'),
                                                                                response_context.get('status')))
        return JsonResponse(response_context)
