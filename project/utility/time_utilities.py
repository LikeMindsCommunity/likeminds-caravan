import time


class TimeUtilities:

    @staticmethod
    def current_time_in_millis() -> float:
        return float((time.time() * 1000))

    @staticmethod
    def convert_epoch_time_in_hh_mm(epoch_time) -> str:
        return time.strftime('%H:%M', time.localtime(epoch_time))

    @staticmethod
    def current_time_in_sec() -> int:
        return int(time.time())

    @staticmethod
    def current_time_in_milliseconds() -> int:
        return int((time.time() * 1000))

