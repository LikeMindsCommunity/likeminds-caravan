import json

from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from collabmates_api.cohort.cohort_impl import CohortImpl
from collabmates_api.views import get_error_context
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.request_utilities import RequestUtilities
from utility.response_utilities import ResponseUtilities
from utility.version_utilities import VersionUtilities

error_logger = LoggingWrapper.get_instance()


class CreateCohortView(APIView):

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        header_member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not request_body:
            response = {'success': False, 'error_message': "Invalid request body"}

            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        cohort_manager = CohortImpl(member_id=header_member_id, api_key=api_key)
        response = cohort_manager.create_cohort(request_body=request_body)

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class DeleteCohortView(APIView):

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        header_member_id = RequestUtilities.get_member_id_from_headers(request)
        cohort_id = request_body.get('cohort_id')

        if not request_body:
            response = {'success': False, 'error_message': "Invalid cohort"}

            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        cohort_manager = CohortImpl(member_id=header_member_id)
        response = cohort_manager.delete_cohort(cohort_id=cohort_id)

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class FetchCohortWithMemberCountView(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        community_id = request.GET.get('community_id', "")

        accept_version = RequestUtilities.get_accept_version_from_headers(request)
        api_revamp_v1_check = VersionUtilities.api_revamp_v1_check(accept_version)

        if not member_id:
            response = ResponseUtilities.get_view_impl_error_context('Invalid header member id',
                                                                     status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(**response)

        if not (community_id or api_key):
            response = ResponseUtilities.get_view_impl_error_context('Invalid community ID/API key!',
                                                                     status_codes.HTTP_400_BAD_REQUEST)
            return JsonResponse(**response)

        cohort_manager = CohortImpl(member_id=member_id, api_key=api_key)
        response = cohort_manager.fetch_cohorts_with_community_id(community_id, api_revamp_v1_check=api_revamp_v1_check)

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class FetchCohortView(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)
        community_id = request.GET.get('community_id', "")
        cohort_id = request.GET.get('cohort_id', "")

        accept_version = RequestUtilities.get_accept_version_from_headers(request)
        api_revamp_v1_check = VersionUtilities.api_revamp_v1_check(accept_version)

        cohort_manager = CohortImpl(member_id=member_id, api_key=api_key)
        response = cohort_manager.fetch_cohorts_with_community_and_cohort_id(cohort_id=cohort_id,
                                                                             community_id=community_id,
                                                                             api_revamp_v1_check=api_revamp_v1_check)

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class RemoveMemberFromCohortView(APIView):

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        header_member_id = RequestUtilities.get_member_id_from_headers(request)

        if not request_body:
            response = {'success': False, 'error_message': "Invalid request body"}

            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        cohort_manager = CohortImpl(member_id=header_member_id)
        response = cohort_manager.remove_member_from_cohort(request_body=request_body)

        if response.get('error_message'):
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response, status=status_codes.HTTP_200_OK)


class UpdateCohortView(APIView):

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        header_member_id = RequestUtilities.get_member_id_from_headers(request)
        api_key = RequestUtilities.get_api_key_from_headers(request)

        if not request_body:
            response = {'success': False, 'error_message': "Invalid request body"}

            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        cohort_manager = CohortImpl(member_id=header_member_id, api_key=api_key)
        response = cohort_manager.update_cohort(request_body=request_body)

        if response.get('error_message'):
            return JsonResponse(**ResponseUtilities.get_view_impl_error_context(response.get('error_message'),
                                                                                response.get('status')))

        return JsonResponse(response)


class FetchMemberCohortsView(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        community_id = request.GET.get('community_id', None)

        try:
            member_ids = json.loads(request.GET.get('member_ids'))

        except Exception as e:
            member_ids = []
            error_logger.exception(f"Exception {str(e)} while loading member_ids: {request.GET.get('member_ids')}")

        if not member_id:
            response = get_error_context(success=False, error_message="Invalid member_id passed in header")
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        cohort_manager = CohortImpl(member_id=member_id)
        response = cohort_manager.fetch_member_cohorts(community_id=community_id, member_ids=member_ids)

        if response.get('error_message'):
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response, status=status_codes.HTTP_200_OK)


class FetchCohortAccessForChatroomView(APIView):

    def get(self, request):
        member_id = RequestUtilities.get_member_id_from_headers(request)
        chatroom_id = request.GET.get('chatroom_id', None)

        cohort_manager = CohortImpl(member_id=member_id)
        response = cohort_manager.fetch_all_cohort_access_for_chatroom(chatroom_id=chatroom_id)

        if response.get('error_message'):
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response, status=status_codes.HTTP_200_OK)


class UpdateCohortAccessForChatroomView(APIView):

    def post(self, request):
        request_body = RequestUtilities.load_request_body(request)
        header_member_id = RequestUtilities.get_member_id_from_headers(request)

        if not request_body:
            response = {'success': False, 'error_message': "Invalid request body"}

            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        cohort_manager = CohortImpl(member_id=header_member_id)
        response = cohort_manager.update_cohort_access_for_chatroom(request_body=request_body)

        if response.get('error_message'):
            return JsonResponse(response, status=status_codes.HTTP_400_BAD_REQUEST)

        return JsonResponse(response, status=status_codes.HTTP_200_OK)
