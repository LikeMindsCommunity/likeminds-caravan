from rest_framework import status

from project.celery import app
from django.test import TransactionTestCase

from togther.models import communityAnswers, questionFilters, Members, Member_Engage, communityLevels, Community, \
    collabcardState, card_answers
from utility.states import member_states, click_states, level_click_states
from .constants import JOIN_COMMUNITY_GUEST_TEXT, JOIN_COMMUNITY_PROMOTER_TEXT, JOIN_COMMUNITY_GUEST_TEXT_PRIVATE_LINK
from ..CommunityQuestionFlow.constants import *
from ..CreateCommunityFlow.constants import *
from ..api_constants import JOIN_COMMUNITY_V1_API_ENDPOINT
from ..utilities.api_utilites import APIUtilities
from ..utilities.test_utilites import TestUtilities


class JoinCommunityFlowTestCase(TransactionTestCase):
    response = None
    response_context = {}

    @classmethod
    def setUpClass(cls):
        app.conf.task_always_eager = True

    @classmethod
    def tearDownClass(cls):
        pass

    def perform_testing_for_data_check(self, response, response_context):
        """
        To check data after join community api hit via public link or invalid private link
        """
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(communityAnswers.objects.count(), 8)
        self.assertEqual(questionFilters.objects.count(), 2)
        self.assertEqual(Members.objects.filter(state=member_states.PENDING_MEMBER).count(), 1)
        self.assertEqual(Member_Engage.objects.filter(member_state=member_states.PENDING_MEMBER,
                                                      click_state=click_states.PENDING_APPROVAL).count(), 1)
        self.perform_testing_for_response(response_context)

    def perform_testing_for_data_check_for_joining_as_promoter(self, response, response_context):
        """
        To check data after join community api hit via public link or invalid private link
        """
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(communityAnswers.objects.count(), 16)
        self.assertEqual(Member_Engage.objects.filter(click_state=click_states.DEFAULT).count(), 1)
        self.assertEqual(questionFilters.objects.count(), 4)
        self.assertEqual(communityLevels.objects.filter(level_click_state=level_click_states.COMMUNITY_JOINED).count(),
                         4)
        self.perform_testing_for_response(response_context)

    def perform_testing_for_response(self, response_context):
        self.assertEqual(type(response_context.get('success')), bool)

        if response_context.get('access'):
            self.assertEqual(type(response_context.get('access')), bool)

    def perform_testing_for_valid_private_join_link(self, response, response_context):
        """
        To check data after join community api hit via valid private link
        """
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(communityAnswers.objects.count(), 8)
        self.assertEqual(Members.objects.filter(state=member_states.MEMBER).count(), 1)
        self.assertEqual(questionFilters.objects.count(), 2)
        self.assertEqual(Member_Engage.objects.filter(member_state=member_states.MEMBER).count(), 1)
        self.assertEqual(collabcardState.objects.filter(follow_status=True).count(), 3)
        self.assertEqual(card_answers.objects.filter(remove_id=None, is_guest=False).count(), 3)
        self.perform_testing_for_response(response_context)

    def test_api_for_join_community(self):
        """
        To test join community API via public join link and guest, promoter member states
        """
        community_creator_user_id = TestUtilities.create_user(COMMUNITY_CREATOR)
        community_member_user_id = TestUtilities.create_user(COMMUNITY_MEMBER)
        response = TestUtilities.create_community(CREATE_COMMUNITY_PAGE_1, community_creator_user_id)
        response_context = APIUtilities.get_api_request(response)

        community_context = CREATE_COMMUNITY_PAGE_2.copy()
        community_id = response_context.get('community').get('id')
        community_context['community_id'] = community_id
        response = TestUtilities.create_community(community_context, community_creator_user_id)

        community_context = CREATE_COMMUNITY_PAGE_3.copy()
        community_context['community_id'] = community_id
        response = TestUtilities.create_community(community_context, community_creator_user_id)

        join_community_public_context = JOIN_COMMUNITY_GUEST_TEXT.copy()
        join_community_public_context['community_id'] = community_id
        response = JoinCommunityFlowTestCaseHelper.post_join_community(community_member_user_id,
                                                                       join_community_public_context)
        response_context = APIUtilities.get_api_request(response)

        self.perform_testing_for_data_check(response, response_context)
        print("Tested v1/join_community for Guest")

        join_community_public_context = JOIN_COMMUNITY_PROMOTER_TEXT.copy()
        join_community_public_context['community_id'] = community_id
        response = JoinCommunityFlowTestCaseHelper.post_join_community(community_creator_user_id,
                                                                       join_community_public_context)
        response_context = APIUtilities.get_api_request(response)
        print(response_context)

        self.perform_testing_for_data_check_for_joining_as_promoter(response, response_context)
        print("Tested v1/join_community for Promoter")

    def test_api_for_join_community_for_private_join_link(self):
        """
        To test join community API via valid private join link
        """
        community_creator_user_id = TestUtilities.create_user(COMMUNITY_CREATOR)
        community_member_user_id = TestUtilities.create_user(COMMUNITY_MEMBER)
        response = TestUtilities.create_community(CREATE_COMMUNITY_PAGE_1, community_creator_user_id)
        response_context = APIUtilities.get_api_request(response)

        community_context = CREATE_COMMUNITY_PAGE_2.copy()
        community_id = response_context.get('community').get('id')
        community_context['community_id'] = community_id
        response = TestUtilities.create_community(community_context, community_creator_user_id)

        community = Community.get_community_or_None(community_id)
        community.auto_approval = True
        community.is_paid = True
        community.save()

        community_context = CREATE_COMMUNITY_PAGE_3.copy()
        community_context['community_id'] = community_id
        response = TestUtilities.create_community(community_context, community_creator_user_id)
        response_context = APIUtilities.get_api_request(response)

        auto_approval = response_context.get('community').get('auto_approval')
        is_paid = response_context.get('community').get('is_paid')

        join_community_public_context = JOIN_COMMUNITY_GUEST_TEXT_PRIVATE_LINK.copy()
        join_community_public_context['community_id'] = community_id
        response = JoinCommunityFlowTestCaseHelper.post_join_community(community_member_user_id,
                                                                       join_community_public_context)
        response_context = APIUtilities.get_api_request(response)

        if auto_approval and is_paid:
            self.perform_testing_for_valid_private_join_link(response, response_context)
            print("Tested v1/join_community for Guest via Private Join Link")


class JoinCommunityFlowTestCaseHelper:

    @staticmethod
    def post_join_community(community_member_id, join_community_context):
        response = APIUtilities.post_api_request(JOIN_COMMUNITY_V1_API_ENDPOINT, join_community_context,
                                                 {'HTTP_X_MEMBER_ID': community_member_id})
        return response
