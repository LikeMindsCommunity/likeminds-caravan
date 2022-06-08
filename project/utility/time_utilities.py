import math
import time
from typing import Union
from dateutil import tz
from datetime import datetime, timedelta


class TimeUtilities:
    MILLI_SEC_IN_A_DAY = 86400000

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
    def convert_milliseconds_to_min(millisec):
        return millisec // 60000

    @staticmethod
    def convert_sec_to_milliseconds(sec):
        return int(sec * 1000)

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

        if math.floor(math.log10(epoch_time) + 1) == 13:
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

        """format -- Mar 09 2021"""

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return time.strftime('%b %d %Y', time.localtime(epoch_time))

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

    @staticmethod
    def get_minutes_in_milliseconds(minutes):

        return minutes * 60 * 1000

    @staticmethod
    def convert_epoch_time_to_RFC3339(epoch_time):

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        dt = datetime.utcfromtimestamp(epoch_time).isoformat() + 'Z'

        return dt

    @staticmethod
    def get_epoch_from_datetime(epoch_time, hour, minute):

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return datetime.fromtimestamp(epoch_time).replace(hour=hour, minute=minute).timestamp()

    @staticmethod
    def convert_epoch_time_to_webflow_time(epoch_time):

        """webflow time --> dd/mm/yyyyTHH:MM"""

        if TimeUtilities.is_epoch_in_milliseconds(epoch_time):
            epoch_time = TimeUtilities.convert_milliseconds_to_sec(epoch_time)

        return time.strftime('%d/%m/%Y', time.localtime(epoch_time)) + "T" + TimeUtilities.convert_epoch_time_in_hh_mm(
            epoch_time)

    @staticmethod
    def add_IST_offset_to_date_time(date_time):

        """2020-10-11 01:56:24 --> 2020-10-11 01:56:24+05:30"""

        tz_ist = TimeUtilities.get_indian_time_zone()
        return date_time.replace(tzinfo=tz_ist)

    @staticmethod
    def get_current_datetime_in_IST():

        """format --> 2020-10-11 01:56:24+05:30"""

        current_time_in_epoch = TimeUtilities.current_time_in_sec()

        return TimeUtilities.convert_epoch_to_datetime_in_IST(current_time_in_epoch)

    @staticmethod
    def get_current_datetime():
        return datetime.now()

    @staticmethod
    def get_week_first_day_in_datetime():
        current_datetime = TimeUtilities.get_current_datetime()
        return current_datetime - timedelta(days=current_datetime.weekday())

    @staticmethod
    def get_week_end_day_in_datetime():
        return TimeUtilities.get_week_first_day_in_datetime() + timedelta(days=6)

    @staticmethod
    def get_month_first_day_in_datetime():
        current_datetime = TimeUtilities.get_current_datetime()
        return current_datetime.replace(day=1)

    @staticmethod
    def get_month_last_day_in_datetime():
        next_month_datetime = TimeUtilities.get_current_datetime().replace(day=28) + timedelta(days=4)
        return next_month_datetime - timedelta(days=next_month_datetime.day)

    @staticmethod
    def get_epoch_time_for_start_of_day_in_millisec(date_time):

        """2020-10-11 01:56:24+05:30 --> 2020-10-11 00:00:00"""
        return int(date_time.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()) * 1000

    @staticmethod
    def get_epoch_time_for_end_of_day_in_millisec(date_time):

        """2020-10-11 01:56:24+05:30 --> 2020-10-11 00:00:00"""
        return int(date_time.replace(hour=23, minute=59, second=59, microsecond=999).timestamp()) * 1000

