import logging

from external_services.logging.logger_manager import LoggerManager


class FileLoggerImpl(LoggerManager):

    __instance__ = None

    def __init__(self) -> None:
        logger = self._get_file_logger_instance()
        FileLoggerImpl.__instance__ = logger

    @staticmethod
    def _get_file_logger_instance() -> logging.Logger:
        return logging.getLogger('file_logger')

    @staticmethod
    def get_instance() -> logging.Logger:
        if FileLoggerImpl.__instance__ is None:
            FileLoggerImpl()

        return FileLoggerImpl.__instance__
