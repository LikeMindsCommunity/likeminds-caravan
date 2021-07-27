import json

from rest_framework.test import APIClient


class APIUtilities:

    @staticmethod
    def post_api_request(url, request_body, headers=None):
        if headers is None:
            headers = {}

        client = APIClient()
        response = client.post(url, data=request_body, format='json', **headers)

        return response

    @staticmethod
    def get_api_request(response):

        try:
            response_context = json.loads(response.content)
        except Exception as e:
            response_context = {}

        return response_context

    @staticmethod
    def hit_get_api_with_body(url, request_body, headers=None):
        if headers is None:
            headers = {}

        client = APIClient()
        response = client.get(url, data=request_body, **headers)

        return response
