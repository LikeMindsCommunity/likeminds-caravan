import logging

import requests

from external_services.pandemonium import constants
from django.conf import settings


class PandemoniumAPIClient:
    domain_url = settings.PANDEMONIUM_BASE_URL

    def get_domain_url(self):
        return self.domain_url

    def publish_chatroom_conversation_to_pandemonium(self, chatroom_id: int, data: dict):
        url = f"{self.get_domain_url()}/{constants.ROUTE_PUBLISH}/{constants.CHATROOM_TOPIC_PARAM}:{chatroom_id}?{constants.TOPIC_MESSAGE_TYPE_PARAM}={constants.TOPIC_MESSAGE_TYPE_CONVERSATION}"
        data = data

        response = requests.post(url, json=data)
        if response.status_code == 200:
            logging.info(f"published conversation data in pandemonium for chatroom_id={chatroom_id}, response={response.content}")
        else:
            logging.error(f"failed to publish conversation data in pandemonium. status_code={response.status_code}")
