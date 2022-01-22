from datetime import datetime, timedelta

class COMM_TYPE:
    APP_NOTI = 'app notification'
    WA = 'whatsapp'
    EMAIL = 'email'
    CALENDAR = 'calendar'

class EVENT_TYPE:
    CREATION = 'event creation'
    LAST_CALL = 'event last call'
    ATTENDANCE_5_HRS = 'event attendance 5 hrs'
    ATTENDANCE_10_MIN = 'event attendance 10 min'

    ATTENDANCE_15_MIN = 'event attendance 15 min'
    REGISTRATION = 'event registration'

    ATTENDANCE_9_AM = 'event attendance 9 AM'
    POST_EVENT_ATTENDEES = 'post event attendees'
    POST_EVENT_ATTACHMENTS = 'post event attachments'

class EVENT_COMM_FREQUENCY:
    LAST_CALL_WHATSAPP = timedelta(hours=24)
    ATTENDANCE_5_HRS_WHATSAPP = timedelta(hours=5)
    ATTENDANCE_10_MIN_WHATSAPP = timedelta(minutes=10)

    LAST_CALL_APP_NOTI = timedelta(hours=48)
    ATTENDANCE_15_MIN_APP_NOTI = timedelta(minutes=15)

    LAST_CALL_EMAIL = timedelta(hours=24)
    POST_EVENT_ATTENDEES_MAIL = timedelta(hours=1)
    POST_EVENT_ATTENDEES_MAIL_EXPIRY_AFTER = timedelta(hours=2)

EVENT_COMM_SHOULD_HAPPEN_BEFORE = datetime.strptime("22:0", "%H:%M") # 1O:00 PM
EVENT_COMM_SHOULD_HAPPEN_AFTER = datetime.strptime("08:0", "%H:%M") # 8:00 AM

TIME_10_AM = datetime.strptime("10:0", "%H:%M") # 10:00 AM
TIME_9_AM = datetime.strptime("9:0", "%H:%M") # 9:00 AM

WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION = 'event_created_v1'
WHATSAPP_TEMPLATE_NAME_FOR_EVENT_LAST_CALL = 'event_registration_last_cal_v1'
WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_5_HRS = 'attend_5_hrs_before_v1'
WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_10_MIN = 'attend_10_mins_before_v1'

TITLE_NEW_EVENT_ATTACHMENT_APP_NOTIICATION = "New attachments & recordings have been added to %s event in your community"
TITLE_UPDATE_EVENT_ATTACHMENT_APP_NOTIICATION = "Attachments & recordings have been updated in %s event."
SUB_TITLE_EVENT_ATTACHMENT_APP_NOTIICATION = "Tap to view details"
ROUTE_EVENT_ATTACHMENT_APP_NOTIICATION = "route://event_attachment?chatroom_id=%s"

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
ROUTE_FREE_EVENT_REGISTRATION_APP_NOTIFICATION = "route://event_chatroom?chatroom_id=%s&community_id=%s&is_paid=false&type=registered"
ROUTE_PAID_EVENT_REGISTRATION_APP_NOTIFICATION = "route://event_chatroom?chatroom_id=%s&community_id=%s&is_paid=true&type=registered"

CHATROOM_URL = "%s/collabcard/%s"
MAIL_EVENT_NOTIFICATION = 30

POST_EVENT_ATTENDEES_LINK = "%s/dashboard/%s"

SUBJECT_EVENT_CREATION_MAIL = "New Event happening in %s community 😃"
SUBJECT_EVENT_LAST_CALL_MAIL = "Registration reminder! Don’t miss out on this."
SUBJECT_EVENT_REGISTRATION_MAIL = "Registration complete ✅"
SUBJECT_EVENT_ATTENDANCE_MAIL = "Event day 🥳"
SUBJECT_POST_EVENT_ATTENDEES_MAIL = "Attendees list for %s 👥"
SUBJECT_POST_EVENT_ATTACHMENT_MAIL = "Event recordings & attachments added 📹 🗃"

SENDER_NAME_FOR_EMAIL_COMMS = "Team LikeMinds"
SENDER_EMAIL_FOR_EMAIL_COMMS = "team@likeminds.chat"

PAID_EVENT_REGISTRATION_SOUND = "ka-ching.mp3"

SUBJECT_CHATROOM_NOT_OPENED_MAIL = "%s is waiting for your response!"
SENDER_FOR_ENGAGEMENT_COMMUNICATION = "hello@likeminds.community"
