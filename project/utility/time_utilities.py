import time


class TimeUtilities:

    @staticmethod
    def current_time_in_millis() -> float:
        return float((time.time() * 1000))
