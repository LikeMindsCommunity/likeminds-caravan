import logging

from django.conf import settings

from external_services.logging.coralogix_logger import CoralogixLoggerImpl
from external_services.logging.file_logger import FileLoggerImpl
from external_services.logging.logger_manager import LoggerManager


class LoggingWrapper(LoggerManager):

    __instance__ = None

    def __init__(self) -> None:

        if getattr(settings, 'USE_INTERNAL_FILE_LOGGER', False):
            logger = FileLoggerImpl.get_instance()
        else:
            logger = CoralogixLoggerImpl.get_instance()
            CoralogixLoggerImpl().add_coralogix_handler(logging.getLogger(), logging.ERROR)

        LoggingWrapper.__instance__ = logger

    """
        method: get_instance
        returns: logger instance
        case:
            (a)local development
            USE_INTERNAL_FILE_LOGGER should be set
            returns local file logger
            (b)beta/prod server
            USE_INTERNAL_FILE_LOGGER should be reset
            returns coralogix logger
    """
    @staticmethod
    def get_instance() -> logging.Logger:
        if LoggingWrapper.__instance__ is None:
            LoggingWrapper()

        return LoggingWrapper.__instance__
