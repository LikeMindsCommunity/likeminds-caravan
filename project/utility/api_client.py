from typing import Union

import requests
from rest_framework import status as status_codes
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class ApiClient:
    params = dict()
    body = dict()
    headers = dict()
    response = None
    url = None

    def __init__(self, host: str = None, path: str = None, method: str = "GET", schema: str = None):
        self.host = host
        self.path = path
        self.method = method.upper()
        self.schema = schema if schema is not None else "https"

    def get_host(self):
        return self.host

    def get_request_path(self):
        return self.path

    def get_request_method(self):
        return self.method

    def get_url_params(self):
        return "?" + "&".join(f"{key}={value}" for key, value in self.params.items())

    def get_headers(self):
        return self.headers

    def get_body(self):
        return self.body

    def _fetch_schema(self):
        schema = f"{self.schema}" if self.schema not in self.get_host() else ""
        if schema:
            schema = (schema + "://") if "://" not in schema else schema

        return schema

    def get_request_url(self):

        if self.url:
            return self.url

        return f"{self._fetch_schema()}{self.get_host()}/{self.get_request_path()}{self.get_url_params()}"

    def update_request_url(self, url):
        self.url = url

    def add_url_param(self, key, value):
        self.params.update({key: value})
        return self

    def update_url_params(self, params: dict):
        self.params.update(**params)
        return self

    def update_body(self, data: Union[dict, list]):
        self.body = data
        return self

    def add_header(self, key, value):
        self.headers.update({str(key): str(value)})
        return self

    def update_headers(self, headers: dict):
        self.headers.update(**headers)
        return self

    def request(self):
        url = self.get_request_url()

        self.response = requests.request(method=self.get_request_method(),
                                         url=url,
                                         headers=self.get_headers(),
                                         json=self.get_body())
        return self

    def get(self):
        url = self.get_request_url()

        self.response = requests.request(method="GET",
                                         url=url,
                                         headers=self.get_headers(),
                                         json=self.get_body())
        return self

    def post(self):
        url = self.get_request_url()

        self.response = requests.request(method="POST",
                                         url=url,
                                         headers=self.get_headers(),
                                         json=self.get_body())
        return self

    def delete(self):
        url = self.get_request_url()

        self.response = requests.request(method="DELETE",
                                         url=url,
                                         headers=self.get_headers(),
                                         json=self.get_body())
        return self

    def fetch_response_code(self):
        return self.response.status_code

    def fetch_response(self):
        if self.response.status_code == status_codes.HTTP_200_OK:
            try:
                return self.response.json()
            except Exception as e:
                error_logger.error(f"external API hit - exception details = {e.args}, API response contect = {self.response.text}")
                return {}
        else:
            error_logger.error(f"external API hit - method={self.get_request_method()},"
                               f"url={self.get_request_url()},headers={self.get_headers()},"
                               f"data={self.get_body()}, status - {self.response.status_code}\n"
                               f"response-content = {self.response.text}")
            return {}
