from datetime import datetime, timedelta

class COMM_TYPE:
    APP_NOTI = 'app notification'
    WA = 'whatsapp'
    EMAIL = 'email'

class EVENT_TYPE:
    CREATION = 'event creation'
    LAST_CALL = 'event last call'
    ATTENDANCE_5_HRS = 'event attendance 5 hrs'
    ATTENDANCE_10_MIN = 'event attendance 10 min'

class EVENT_COMM_FREQUENCY:
    LAST_CALL_WHATSAPP = timedelta(hours=24)
    ATTENDANCE_5_HRS_WHATSAPP = timedelta(hours=5)
    ATTENDANCE_10_MIN_WHATSAPP = timedelta(minutes=10)

EVENT_COMM_SHOULD_HAPPEN_BEFORE = datetime.strptime("22:0", "%H:%M") # 1O:00 PM
EVENT_COMM_SHOULD_HAPPEN_AFTER = datetime.strptime("08:0", "%H:%M") # 8:00 AM

EVENT_LAST_CALL_TIME = datetime.strptime("10:0", "%H:%M") # 10:00 AM

WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION = 'event_created'
WHATSAPP_TEMPLATE_NAME_FOR_EVENT_LAST_CALL = 'event_registration_last_cal'
WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_5_HRS = 'attend_5_hrs_before'
WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_10_MIN = 'attend_10_mins_before'
