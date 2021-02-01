import logging

from coralogix.handlers import CoralogixLogger
from django.conf import settings

from external_services.logging.logger_manager import LoggerManager


class CoralogixLoggerImpl(LoggerManager):

    __instance__ = None

    def __init__(self) -> None:
        logger = self._get_coralogix_logger_instance()
        CoralogixLoggerImpl.__instance__ = logger

    def _get_coralogix_logger_instance(self) -> object:
        logger = logging.getLogger()
        handler = self._coralogix_handler()
        logger.addHandler(handler)

        return logger

    @staticmethod
    def _coralogix_handler() -> CoralogixLogger:
        return CoralogixLogger(
            settings.CORALOGIX_LOGGER.get('PRIVATE_API_KEY'),
            settings.CORALOGIX_LOGGER.get('APPLICATION_NAME'),
            settings.CORALOGIX_LOGGER.get('SUBSYSTEM_NAME_APP')
        )

    @staticmethod
    def get_instance() -> object:
        if CoralogixLoggerImpl.__instance__ is None:
            CoralogixLoggerImpl()

        return CoralogixLoggerImpl.__instance__
