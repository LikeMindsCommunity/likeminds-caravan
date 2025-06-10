import sys
import logging

from external_services.logging.logger_manager import LoggerManager


class StreamLoggerImpl(LoggerManager):

    __instance__ = None

    def __init__(self) -> None:
        logger = self._get_logger_instance()
        StreamLoggerImpl.__instance__ = logger

    def _get_logger_instance(self) -> logging.Logger:
        logger = logging.getLogger(__class__.__name__)

        stream_logger = self.stream_info_logger()
        handler = stream_logger.handlers[0]
        logger.addHandler(handler)

        return logger

    @staticmethod
    def get_instance() -> logging.Logger:
        if StreamLoggerImpl.__instance__ is None:
            StreamLoggerImpl()

        return StreamLoggerImpl.__instance__

    @staticmethod
    def stream_info_logger() -> logging.Logger:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(logging.Formatter('%(asctime)s  %(levelname)s %(message)s'))
        stream_logger = logging.getLogger('stream_logger')
        stream_logger.addHandler(stream_handler)

        return stream_logger
