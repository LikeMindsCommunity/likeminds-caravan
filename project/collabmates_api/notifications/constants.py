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

    ATTENDANCE_15_MIN = 'event attendance 15 min'
    REGISTRATION = 'event registration'

class EVENT_COMM_FREQUENCY:
    LAST_CALL_WHATSAPP = timedelta(hours=24)
    ATTENDANCE_5_HRS_WHATSAPP = timedelta(hours=5)
    ATTENDANCE_10_MIN_WHATSAPP = timedelta(minutes=10)

    LAST_CALL_APP_NOTI = timedelta(hours=48)
    ATTENDANCE_15_MIN_APP_NOTI = timedelta(minutes=15)

EVENT_COMM_SHOULD_HAPPEN_BEFORE = datetime.strptime("22:0", "%H:%M") # 1O:00 PM
EVENT_COMM_SHOULD_HAPPEN_AFTER = datetime.strptime("08:0", "%H:%M") # 8:00 AM

TIME_10_AM = datetime.strptime("10:0", "%H:%M") # 10:00 AM

WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION = 'event_created_v1'
WHATSAPP_TEMPLATE_NAME_FOR_EVENT_LAST_CALL = 'event_registration_last_cal_v1'
WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_5_HRS = 'attend_5_hrs_before_v1'
WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_10_MIN = 'attend_10_mins_before_v1'

TITLE_EVENT_CREATION_APP_NOTIFICATION = "%s event happening in your community"
SUB_TITLE_EVENT_CREATION_APP_NOTIFICATION = "Register for the event now!"
ROUTE_FREE_EVENT_CREATION_APP_NOTIFICATION = "route://event_chatroom?chatroom_id=%s&is_paid=false&type=register"
ROUTE_PAID_EVENT_CREATION_APP_NOTIFICATION = "route://event_chatroom?chatroom_id=%s&is_paid=true&type=register"

TITLE_EVENT_LAST_CALL_APP_NOTIFICATION = "Registration Reminder"
SUB_TITLE_EVENT_LAST_CALL_APP_NOTIFICATION = "%s event happening in your community"
ROUTE_FREE_EVENT_LAST_CALL_APP_NOTIFICATION = "route://event_chatroom?chatroom_id=%s&is_paid=false&type=register_last_call"
ROUTE_PAID_EVENT_LAST_CALL_APP_NOTIFICATION = "route://event_chatroom?chatroom_id=%s&is_paid=true&type=register_last_call"

TITLE_EVENT_ATTENDANCE_APP_NOTIFICATION = "Event starting in %s mins!"
SUB_TITLE_EVENT_ATTENDANCE_APP_NOTIFICATION = "%s event starting in your community"
ROUTE_EVENT_ATTENDANCE_APP_NOTIFICATION = "route://event_chatroom?chatroom_id=%s&type=attendance"

TITLE_EVENT_REGISTRATION_APP_NOTIFICATION = "New event registration"
SUB_TITLE_EVENT_REGISTRATION_APP_NOTIFICATION = "%s has registered for %s event happening in your community"
ROUTE_FREE_EVENT_REGISTRATION_APP_NOTIFICATION = "route://event_chatroom?chatroom_id=%s&is_paid=false&type=registered"
ROUTE_PAID_EVENT_REGISTRATION_APP_NOTIFICATION = "route://event_chatroom?chatroom_id=%s&is_paid=truetype=registered"
