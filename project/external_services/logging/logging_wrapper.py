import logging

from django.conf import settings

from external_services.logging.file_logger import FileLoggerImpl
from external_services.logging.stream_logger import StreamLoggerImpl
from external_services.logging.logger_manager import LoggerManager


class LoggingWrapper(LoggerManager):

    __instance__ = None

    def __init__(self) -> None:

        if getattr(settings, 'USE_INTERNAL_FILE_LOGGER', False):
            logger = FileLoggerImpl.get_instance()

        else:
            logger = StreamLoggerImpl.get_instance()

        logger.setLevel(logging.INFO)
        LoggingWrapper.__instance__ = logger

    """
        method: get_instance
        returns: logger instance
    """
    @staticmethod
    def get_instance() -> logging.Logger:
        if LoggingWrapper.__instance__ is None:
            LoggingWrapper()

        return LoggingWrapper.__instance__
