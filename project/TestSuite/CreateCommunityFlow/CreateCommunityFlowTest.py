import json

from django.core import management

from project.celery import app
from django.test import TransactionTestCase, SimpleTestCase
from togther.models import Community, Members, Member_Engage, communityLevels, \
    userAdminRights, userMemberRights, memberRights, moderationHistory, communityRightsSettings, adminRights, \
    communityQuestions, Collabcard, card_answers
from rest_framework import status

from .constants import COMMUNITY_CREATOR, CREATE_COMMUNITY_PAGE_1, MANAGER_RIGHTS_LIST, \
    MEMBER_RIGHTS_LIST, CREATE_COMMUNITY_PAGE_2
from ..api_constants import CREATE_COMMUNITY_V1_API_ENDPOINT
from ..utilities.test_utilites import TestUtilities
from ..utilities.api_utilites import APIUtilities


class CreateCommunityFlowTestCase(TransactionTestCase):
    response = None
    response_context = {}

    @classmethod
    def setUpClass(cls):
        app.conf.task_always_eager = True
        CreateCommunityFlowTestCaseHelper.create_member_rights_records()
        CreateCommunityFlowTestCaseHelper.create_manager_rights_records()

    @classmethod
    def tearDownClass(cls):
        print("Tear Down called..")
        management.call_command('flush', verbosity=0, interactive=False)

    def perform_testing_on_page_1(self, response, response_context):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Community.objects.count(), 1)
        self.assertEqual(Members.objects.count(), 1)
        self.assertEqual(Member_Engage.objects.count(), 1)
        self.assertEqual(communityLevels.objects.count(), 4)
        self.assertEqual(moderationHistory.objects.count(), 1)
        self.assertEqual(userAdminRights.objects.count(), 5)
        self.assertEqual(userMemberRights.objects.count(), 6)
        self.assertEqual(communityRightsSettings.objects.count(), 6)
        self.perform_testing_on_community_response(response_context)

    def perform_testing_on_page_2(self, response, response_context):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(communityQuestions.objects.count(), 2)
        self.assertEqual(Collabcard.objects.count(), 2)
        self.assertEqual(card_answers.objects.count(), 3)
        self.perform_testing_on_community_response(response_context)

    def perform_testing_on_community_response(self, response_context):
        self.assertEqual(type(response_context.get('success')), bool)
        self.assertEqual(type(response_context.get('community')), dict)

    def test_api_for_community_creation(self):
        community_creator_user_id = TestUtilities.create_user(COMMUNITY_CREATOR)

        community_context = CREATE_COMMUNITY_PAGE_1
        response = CreateCommunityFlowTestCaseHelper.create_community_for_testing(community_creator_user_id,
                                                                                  community_context)
        response_context = APIUtilities.get_api_request(response)
        self.perform_testing_on_page_1(response, response_context)

        community_context = CREATE_COMMUNITY_PAGE_2.copy()
        community_id = response_context.get('community').get('id')
        community_context['community_id'] = community_id
        response = CreateCommunityFlowTestCaseHelper.create_community_for_testing(community_creator_user_id,
                                                                                  community_context)
        response_context = APIUtilities.get_api_request(response)
        self.perform_testing_on_page_2(response, response_context)


class CreateCommunityFlowTestCaseHelper:

    @staticmethod
    def create_manager_rights_records():

        for right in MANAGER_RIGHTS_LIST:
            adminRights(title=right["title"], sub_title=right["sub_title"], state=right["state"]).save()

    @staticmethod
    def create_member_rights_records():

        for right in MEMBER_RIGHTS_LIST:
            memberRights(title=right["title"], sub_title=right["sub_title"], state=right["state"]).save()

    @staticmethod
    def create_community_for_testing(community_creator_user_id, community_context):
        response = APIUtilities.post_api_request(CREATE_COMMUNITY_V1_API_ENDPOINT, community_context,
                                                 {'HTTP_X_MEMBER_ID': community_creator_user_id})
        return response
