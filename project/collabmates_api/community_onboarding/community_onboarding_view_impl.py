from django.http import JsonResponse
from rest_framework.views import APIView
from utility.request_utilities import RequestUtilities
from utility.number_utilities import NumberUtilities
from .community_onboarding_impl import OnboardingImpl
from rest_framework import status as status_codes


class OnboardingFetchPinnedChatrooms(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        page = request.GET.get('page', 1)
        page = NumberUtilities.get_integer_from_string(page)

        paginate_by = request.GET.get('paginate_by', 20)
        paginate_by = NumberUtilities.get_integer_from_string(paginate_by)

        community_id = request.GET.get('community_id')

        onboarding_manager = OnboardingImpl(community_id,
                                            device_id=RequestUtilities.get_device_id_from_headers(request))

        context = onboarding_manager.fetch_pinned_chatrooms(member_id, page, paginate_by)

        if 'error_message' in context:
            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(context)


class OnboardingFetchPollChatrooms(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        page = request.GET.get('page', 1)
        page = NumberUtilities.get_integer_from_string(page)

        paginate_by = request.GET.get('paginate_by', 20)
        paginate_by = NumberUtilities.get_integer_from_string(paginate_by)

        community_id = request.GET.get('community_id')

        onboarding_manager = OnboardingImpl(community_id,
                                            device_id=RequestUtilities.get_device_id_from_headers(request))

        context = onboarding_manager.fetch_poll_chatrooms(member_id, page, paginate_by)

        if 'error_message' in context:

            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(context)


class OnboardingFetchEventChatrooms(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        page = request.GET.get('page', 1)
        page = NumberUtilities.get_integer_from_string(page)

        paginate_by = request.GET.get('paginate_by', 20)
        paginate_by = NumberUtilities.get_integer_from_string(paginate_by)

        community_id = request.GET.get('community_id')

        onboarding_manager = OnboardingImpl(community_id,
                                            device_id=RequestUtilities.get_device_id_from_headers(request))

        context = onboarding_manager.fetch_event_chatrooms(member_id, page, paginate_by)

        if 'error_message' in context:

            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(context)


class RecentNDaysConversationChatrooms(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        page = request.GET.get('page', 1)
        page = NumberUtilities.get_integer_from_string(page)

        paginate_by = request.GET.get('paginate_by', 20)
        paginate_by = NumberUtilities.get_integer_from_string(paginate_by)

        community_id = request.GET.get('community_id')

        onboarding_manager = OnboardingImpl(community_id,
                                            device_id=RequestUtilities.get_device_id_from_headers(request))

        context = onboarding_manager.recent_n_days_conversation_chatrooms(member_id, page, paginate_by)

        if 'error_message' in context:

            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(context)


class RecentNPercentageConversationChatrooms(APIView):

    def get(self, request, *args, **kwargs):
        member_id = RequestUtilities.get_member_id_from_headers(request)

        page = request.GET.get('page', 1)
        page = NumberUtilities.get_integer_from_string(page)

        paginate_by = request.GET.get('paginate_by', 20)
        paginate_by = NumberUtilities.get_integer_from_string(paginate_by)

        community_id = request.GET.get('community_id')

        onboarding_manager = OnboardingImpl(community_id,
                                            device_id=RequestUtilities.get_device_id_from_headers(request))

        context = onboarding_manager.n_percentage_member_conversation_chatrooms(member_id, page, paginate_by)

        if 'error_message' in context:

            return JsonResponse(context, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(context)
