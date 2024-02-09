CHATROOM_EXPIRE_DURATION = 86400  # chatroom expire duration in seconds
INTRO_PLACEHOLDER_TEXT = "Welcome to %s , "
INTRO_PLACEHOLDER_USER_ROUTE = "route://member_profile/%s"
INTRO_PLACEHOLDER_USER_PROFILE_ROUTE = "route://user_profile/%s"
SUBSCRIPTION_VALIDATE_EVENT_ONLINE_LINK = "api/subscription/valid_event_transaction"

EVENT_CARD_MAIL_DESCRIPTION = """You have been invited to an event %s happening in the %s community. Here is the link to the event %s

About the event:

%s"""

CHATROOM_URL = "%s/collabcard/%s"
MAIL_EVENT_NOTIFICATION = 30

IMAGE_LINK_FOR_NO_EVENTS_FOUND = "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/Animation.png"
TITLE_FOR_NO_UPCOMING_EVENTS_FOUND = "No Events"
SUB_TITLE_FOR_CM_VIEW_NO_UPCOMING_EVENTS_FOUND = "Create events to engage your members and increase connections in your community.\n\nNot sure? Explore types of <<online community events|route://browser?link=https://likeminds.community/blog/online-community-events/>> you can host on LikeMinds."
SUB_TITLE_FOR_MEMBER_VIEW_NO_UPCOMING_EVENTS_FOUND = "Some exciting events coming really soon 😃"

TITLE_FOR_NO_PAST_EVENTS_FOUND = "No events ended"
SUB_TITLE_FOR_NO_PAST_EVENTS_FOUND = "All ended events would start appearing here for you to explore later. Do check for any new content/recordings added once an event ends"

FIRST_EVENT_CM_MAIL_SUBJECT = "Hi {}! You have successfully created your first event"
FIRST_EVENT_CM_REPLY_EMAIL = "LikeMinds<hi@likeminds.community>"
FIRST_EVENT_CM_MAIL_BUTTON_TEXT = "INVITE MEMBERS"
DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR = "#00897B"

CHATROOM_URL_WITH_COMMUNITY_ID = "%s/collabcard/%s?community_id=%s"

DM_CHATROOM_NAME = "Direct Message"

CHATROOM_NOTIFICATION_PAUSE_EVENT = "Notification paused"
CHATROOM_NOTIFICATION_SETTING_UPDATED_EVENT = "User Notification setting updated"


CHATROOM_USER_SETTINGS_MEMBER_CAN_MESSAGE = "member_can_message"
CHATROOM_USER_SETTINGS = [CHATROOM_USER_SETTINGS_MEMBER_CAN_MESSAGE]

EMAIL_UNSUBSCRIBE_URL = "%s/email_unsubscribe?communityId=%s&memberId=%s"

LIKEMINDS_WEB_URL = "https://likeminds.community/?utm_source=%s&utm_medium=email&utm_campaign=%s&utm_content=%s"

CREATE_CONVERSATION_OG_TAGS_REQUEST_TIMEOUT = 30


class PauseChatroomNotificationTime:
    EIGHT_HR = 8
    TWENTY_FOUR_HR = 24
    
    EIGHT_HOURS = "8 hours"
    TWENTY_FOUR_HOURS = "24 hours"
    ONE_WEEK = "1 week"
