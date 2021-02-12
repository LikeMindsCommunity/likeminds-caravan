import time
from typing import Union
from dateutil import tz
from datetime import datetime, timedelta


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

    @staticmethod
    def convert_milliseconds_to_sec(millisec: Union[int, str]) -> int:
        return millisec // 1000

    @staticmethod
    def get_epoch_time(hours=0, minutes=0):
        epoch_time = hours * 3600 + minutes * 60
        return epoch_time

    @staticmethod
    def add_minutes_to_epoch_time(epoch_time, minutes):
        return epoch_time + TimeUtilities.get_epoch_time(minutes=minutes)

    @staticmethod
    def add_hours_to_epoch_time(epoch_time, hours):
        return epoch_time + TimeUtilities.get_epoch_time(hours=hours)

    @staticmethod
    def subtract_minutes_from_epoch_time(epoch_time, minutes):
        return epoch_time - TimeUtilities.get_epoch_time(minutes=minutes)

    @staticmethod
    def subtract_hours_from_epoch_time(epoch_time, hours):
        return epoch_time - TimeUtilities.get_epoch_time(hours=hours)

    @staticmethod
    def get_indian_time_zone():
        return tz.gettz('IST')

    @staticmethod
    def convert_epoch_to_datetime_in_IST(epoch_time):
        tz_ist = TimeUtilities.get_indian_time_zone()
        return datetime.fromtimestamp(epoch_time).replace(tzinfo=tz_ist)

    @staticmethod
    def add_minutes_to_datetime(date_time, minutes):
        return date_time + timedelta(minutes=minutes)

    @staticmethod
    def add_hours_to_datetime(date_time, hours):
        return date_time + timedelta(hours=hours)

    @staticmethod
    def subtract_minutes_from_datetime(date_time, minutes):
        return date_time - timedelta(minutes=minutes)

    @staticmethod
    def subtract_hours_from_datetime(date_time, hours):
        return date_time - timedelta(hours=hours)
