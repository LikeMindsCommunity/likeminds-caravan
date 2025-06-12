import logging

from external_services.logging.logger_manager import LoggerManager


class StreamLoggerImpl(LoggerManager):

    __instance__ = None

    def __init__(self) -> None:
        logger = self._get_logger_instance()
        StreamLoggerImpl.__instance__ = logger

    @staticmethod
    def _get_logger_instance() -> logging.Logger:
        logger = logging.getLogger(__class__.__name__)

        stream_info_logger = logging.getLogger('stream_info_logger')
        # Safely get or create a handler
        if not stream_info_logger.handlers:
            # If no handler, add a default StreamHandler
            handler = logging.StreamHandler()
            stream_info_logger.addHandler(handler)
        else:
            handler = stream_info_logger.handlers[0]
        logger.addHandler(handler)

        return logger

    @staticmethod
    def get_instance() -> logging.Logger:
        if StreamLoggerImpl.__instance__ is None:
            StreamLoggerImpl()

        return StreamLoggerImpl.__instance__
