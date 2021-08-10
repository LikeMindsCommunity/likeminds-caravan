from django.conf import settings
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from .calendar_manager import CalendarManager
import os


class CalendarImpl(CalendarManager):
    calendar_instance = None

    def get_calendar_instance(self):

        if self.calendar_instance is None:
            self.calendar_instance = self._create_calendar_instance()

        return self.calendar_instance

    def _create_calendar_instance(self):

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            settings.CALENDAR_CREDENTIALS.get('key_dict'), settings.CALENDAR_CREDENTIALS.get('scopes'))

        credentials = credentials.create_delegated(settings.CALENDAR_CREDENTIALS.get('delegated_email'))

        return build('calendar', 'v3', credentials=credentials)

    def call_calender_api(self, event_payload):

        event_link = self.get_calendar_instance().events(). \
            insert(calendarId='primary', body=event_payload, sendUpdates='all').execute()
