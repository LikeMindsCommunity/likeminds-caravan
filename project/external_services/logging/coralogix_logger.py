import logging

from coralogix.handlers import CoralogixLogger
from django.conf import settings


class CoralogixLoggerImpl:

    __instance = None

    def __init__(self) -> None:
        logger = logging.getLogger("Python Logger")
        logger.setLevel(logging.INFO)
        coralogix_handler = CoralogixLogger(
                settings.CORALOGIX_LOGGER.get('PRIVATE_API_KEY'),
                settings.CORALOGIX_LOGGER.get('APPLICATION_NAME'),
                settings.CORALOGIX_LOGGER.get('SUBSYSTEM_NAME_APP')
            )
        logger.addHandler(coralogix_handler)
        CoralogixLoggerImpl.__instance = logger

    @staticmethod
    def get_instance() -> object:
        if CoralogixLoggerImpl.__instance is None:
            CoralogixLoggerImpl()

        return CoralogixLoggerImpl.__instance
