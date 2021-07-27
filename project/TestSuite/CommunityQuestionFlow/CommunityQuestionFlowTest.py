import json
from rest_framework import status

from TestSuite.CommunityQuestionFlow.constants import COMMUNITY_MEMBER, CREATE_COMMUNITY_PAGE_3
from TestSuite.CreateCommunityFlow.CreateCommunityFlowTest import CreateCommunityFlowTestCaseHelper
from TestSuite.CreateCommunityFlow.constants import COMMUNITY_CREATOR, CREATE_COMMUNITY_PAGE_1, CREATE_COMMUNITY_PAGE_2
from TestSuite.api_constants import QUESTIONS_API_ENDPOINT
from TestSuite.utilities.api_utilites import APIUtilities
from TestSuite.utilities.test_utilites import TestUtilities
from project.celery import app

from django.test import TransactionTestCase

from togther.models import communityQuestions


class CommunityQuestionFlow(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        app.conf.task_always_eager = True

    @classmethod
    def tearDownClass(cls):
        pass

    def perform_testing_on_question(self, response, response_context):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        questions = response_context.get('questions')

        for question in questions:

            if question.get('value'):
                question_value = json.loads(question.get('value'))
                self.assertEqual(type(question_value), list)

                for value in question_value:
                    self.assertEqual(type(value), dict)

            self.assertEqual(type(question.get('id')), int)
            self.assertEqual(type(question.get('question_title')), str)
            self.assertEqual(type(question.get('optional')), bool)
            self.assertEqual(type(question.get('community_id')), int)
            self.assertEqual(type(question.get('state')), int)
            self.assertEqual(type(question.get('help_text')), str)
            self.assertEqual(type(question.get('is_hidden')), bool)
            self.assertEqual(type(question.get('field')), bool)
            self.assertEqual(type(question.get('rank')), int)
            print('Question {0}-{1} has been tested successfully.'.format(question.get('id'),
                                                                          question.get('question_title')))
            self.perform_testing_on_community_question_response(response_context)

    def perform_testing_on_community_question_count(self, response, response_context):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(communityQuestions.objects.count(), 8)
        self.perform_testing_on_community_question_response(response_context)

    def perform_testing_on_community_response(self, response_context):
        self.assertEqual(type(response_context.get('success')), bool)
        self.assertEqual(type(response_context.get('community')), dict)

    def perform_testing_on_community_question_response(self, response_context):
        self.assertEqual(type(response_context.get('community')), dict)

    def test_api_for_question_community(self):
        community_creator_user_id = TestUtilities.create_user(COMMUNITY_CREATOR)
        community_member_user_id = TestUtilities.create_user(COMMUNITY_MEMBER)

        community_context = CREATE_COMMUNITY_PAGE_1
        response = CreateCommunityFlowTestCaseHelper.create_community_for_testing(community_creator_user_id,
                                                                                  community_context)
        response_context = APIUtilities.get_api_request(response)
        self.perform_testing_on_community_response(response_context)

        community_context = CREATE_COMMUNITY_PAGE_2.copy()
        community_id = response_context.get('community').get('id')
        community_context['community_id'] = community_id
        response = CreateCommunityFlowTestCaseHelper.create_community_for_testing(community_creator_user_id,
                                                                                  community_context)
        response_context = APIUtilities.get_api_request(response)
        self.perform_testing_on_community_response(response_context)

        community_context = CREATE_COMMUNITY_PAGE_3.copy()
        community_context['community_id'] = community_id
        response = CreateCommunityFlowTestCaseHelper.create_community_for_testing(community_creator_user_id,
                                                                                  community_context)
        response_context = APIUtilities.get_api_request(response)

        self.perform_testing_on_community_response(response_context)

        # Calling the GET method for questions endpoint.
        response_get_community_question = CommunityQuestionFlowTestCaseHelper.get_community_questions(
            community_creator_user_id, community_member_user_id,
            response_context.get('community').get('id'))
        response_context_get_community_question = APIUtilities.get_api_request(
            response_get_community_question)
        self.perform_testing_on_question(response_get_community_question, response_context_get_community_question)
        self.perform_testing_on_community_question_count(response_get_community_question,
                                                         response_context_get_community_question)


class CommunityQuestionFlowTestCaseHelper:

    @staticmethod
    def get_community_questions(community_creator_user_id, member_id, community_id):
        community_questions_context = {
            "community_id": community_id,
            "shared_by": community_creator_user_id,
        }
        headers = {'HTTP_X_MEMBER_ID': member_id}

        response = APIUtilities.hit_get_api_with_body(QUESTIONS_API_ENDPOINT, community_questions_context, headers)
        return response
