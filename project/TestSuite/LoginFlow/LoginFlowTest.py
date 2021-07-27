import json
from project.celery import app
from django.test import TransactionTestCase, SimpleTestCase
from togther.models import User, Userinfo, userMobiles, userEmails
from rest_framework import status
from rest_framework.test import APIClient

from .constants import LOGIN_REQUEST_JSON
from ..api_constants import LOGIN_V1_API_ENDPOINT


class LoginFlowTestCase(TransactionTestCase):
    response = None
    response_context = {}

    @classmethod
    def setUpClass(cls):
        app.conf.task_always_eager = True

    def get_response(self):
        return self.response

    def set_response(self, response):
        self.response = response

    def get_response_context(self):
        return self.response_context

    def set_response_context(self, response):
        self.response_context = json.loads(response.content)

    def match_response_keys_with_data_types(self):
        response_context = self.get_response_context()

        user = response_context.get('user')

        has_tags = response_context.get('has_tags')
        access = response_context.get('access')
        email_exists = response_context.get('email_exists')

        self.assertEqual(type(user), dict)
        self.assertEqual(type(has_tags), bool)
        self.assertEqual(type(access), bool)
        self.assertEqual(type(email_exists), bool)

        self.assertEqual(type(user.get('id')), int)
        self.assertEqual(type(user.get('name')), str)
        self.assertEqual(type(user.get('image_url')), str)
        self.assertEqual(type(user.get('mobiles')), list)

    def test_api_for_user_creation(self):
        client = APIClient()
        response = client.post(LOGIN_V1_API_ENDPOINT, data=LOGIN_REQUEST_JSON, format='json')
        self.set_response(response)
        self.set_response_context(self.get_response())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Userinfo.objects.count(), 1)
        self.assertEqual(userMobiles.objects.count(), 1)
