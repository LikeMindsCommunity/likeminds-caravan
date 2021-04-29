import math
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

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return time.strftime('%H:%M', time.localtime(epoch_time))

    @staticmethod
    def convert_epoch_time_in_date(epoch_time) -> str:

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return time.strftime('%d %b %Y', time.localtime(epoch_time))

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

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return epoch_time + TimeUtilities.get_epoch_time(minutes=minutes)

    @staticmethod
    def add_hours_to_epoch_time(epoch_time, hours):

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return epoch_time + TimeUtilities.get_epoch_time(hours=hours)

    @staticmethod
    def subtract_minutes_from_epoch_time(epoch_time, minutes):

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return epoch_time - TimeUtilities.get_epoch_time(minutes=minutes)

    @staticmethod
    def subtract_hours_from_epoch_time(epoch_time, hours):

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return epoch_time - TimeUtilities.get_epoch_time(hours=hours)

    @staticmethod
    def get_indian_time_zone():
        return tz.gettz('IST')

    @staticmethod
    def convert_epoch_to_datetime_in_IST(epoch_time):

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

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

    @staticmethod
    def is_epoch_in_milliseconds(epoch_time) -> bool:

        if math.floor(math.log10(epoch_time)+1) == 13:

            return True

        return False

    @staticmethod
    def convert_epoch_time_to_date_and_time_with_month_day_hh_mm(epoch_time) -> str:

        """format -- March 09 at 10:13"""

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return time.strftime('%B %d at %H:%M', time.localtime(epoch_time))

    @staticmethod
    def convert_epoch_time_to_date_with_mon_day_year(epoch_time) -> str:

        """format -- Mar 09 21"""

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return time.strftime('%b %d %y', time.localtime(epoch_time))

    @staticmethod
    def convert_epoch_time_in_hh_mm_am_pm(epoch_time):

        """format -- hh:mm am/pm"""

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return time.strftime('%I:%M %p', time.localtime(epoch_time))

    @staticmethod
    def convert_epoch_time_to_date_month_year(epoch_time) -> str:

        """format -- 09 March 2021"""

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return time.strftime('%d %B %Y', time.localtime(epoch_time))

    @staticmethod
    def convert_epoch_time_to_ddmmyyyy(epoch_time):

        """format -- 18-06-2021"""
        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return time.strftime('%d-%m-%Y', time.localtime(epoch_time))
