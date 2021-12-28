from ..airtable.airtable_manager import AirtableManager
from .constants import JOIN_DATA_WEBHOOK
import requests
from ..logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class AirtableWrapper(AirtableManager):

    endpoint = JOIN_DATA_WEBHOOK

    def send_data(self, data: dict):

        response = requests.post(url=self.endpoint, json=data)

        if response.status_code == 200:
            info_logger.info(response.json())

        else:
            error_logger.error('error while making request on airtable')
