# MSG91 API urls
MSG91_SENDOTP_URI = 'https://api.msg91.com/api/v5/otp?authkey=%s&template_id=%s&mobile=%s&invisible=0&otp_expiry=10'
MSG91_VERIFYOTP_URI = 'https://api.msg91.com/api/v5/otp/verify?authkey=%s&mobile=%s&otp=%s'

# SMS Gupshup api
SMSGUPSHUP_SMS_URI = 'http://enterprise.smsgupshup.com/GatewayAPI/rest?method=SendMessage&send_to={0}&msg={1}&msg_type=TEXT&userid={2}&auth_scheme=plain&password={3}&v=1.1&format=text'

# branch
BRANCH_QUICKLINK_URI = 'https://api2.branch.io/v1/url/bulk/%s'
BRANCH_DECODE_URI = 'https://api2.branch.io/v1/url?url=%s&branch_key=%s'

# community sereialiser links
PRIVATE_LINK_TEXT_ADMIN_1 = 'I have started %s community on LikeMinds and I am inviting you to build this community together with me. Join now with this exclusive link. Auto-verification is enabled for 24 hours: %s'
PRIVATE_LINK_TEXT_ADMIN_2 = 'Join %s community on LikeMinds with my exclusive link. Auto-verification is enabled for 24 hours: %s'
PRIVATE_LINK_TEXT_MEMBERS_DIRECTORY_1 = 'I have created a community directory for %s on LikeMinds. Signup and complete your profile to see detailed profiles of other members in the community using this exclusive link. Auto-verification is enabled for 24 hours: %s'
PRIVATE_LINK_TEXT_MEMBERS_DIRECTORY_2 = 'Directory for our community %s has been setup on LikeMinds. Signup and complete your profile to see detailed profiles of other members in the community using this exclusive link. Auto-verification is enabled for 24 hours: %s'
PRIVATE_LINK_FOR_PERMITTED_USER = 'Join %s on LikeMinds with my exclusive link. For security, this is valid only for next 24 hours: %s'
MEMBER_DIRECTORY_LINK_FOR_PERMITTED_USER = 'Directory for our community %s has been setup on LikeMinds. Signup and complete your profile to see detailed profiles of other members in the community using this exclusive link. Auto-verification is enabled for 24 hours: %s'
SHARE_TEXT_ADMIN = 'I am building %s community on LikeMinds.\n %s \nApply to join our community. %s'
SHARE_TEXT_MEMBER = 'I am part of %s community on LikeMinds.\n %s \nApply to join our community. %s'
SHARE_TEXT_ANONYMOUS = 'I recently discovered %s community on LikeMinds. You can join this community using this link.'
CUSTOM_CLICK_TEXT = '%s joined this community via a private community link on %s and hasn’t created their profile for this community yet'
INSTAGRAM_LINK = "https://www.instagram.com/"
TWITTER_LINK = "https://twitter.com/"

COMMUNITY_JOIN_SMS = '''Congratulations, {0}! Your request to join {1} has been approved.

The next step for you is to download the LikeMinds app. The app allows you to get real-time notifications, join other chatrooms, start your own chatroom, attend events, and much more. 

Download app : {2}'''

COMMUNITY_JOIN_SMS_REMINDER = '''Hi {0}! It’s been 3 days since you’ve been approved to join {1}. Download the LikeMinds app to get real-time notifications, join other relevant chatrooms, start your own chatroom, attend events, and much more. 

Download app : {2}'''

CREATE_INTRO_TEXT_ADMIN = """Created this community on %s"""
CREATE_INTRO_TEXT_MEMBER = """Joined via a private community link on %s"""

INTRO_ROOM_NOTIFICATION_TITLE_SINGULAR = "New member joined"
INTRO_ROOM_NOTIFICATION_TITLE_PLURAL = "New members joined"
INTRO_ROOM_NOTIFICATION_SUBTITLE_SINGULAR = "Hey %s, %s just joined %s. A message from you will make them feel welcomed :)"
INTRO_ROOM_NOTIFICATION_SUBTITLE_PLURAL = "Hey %s, %s is %s members stronger. See who all joined and welcome them to the community."
INTRO_ROOM_NOTIFICATION_ROUTE_SINGULAR = "route://chatroom_detail?chatroom_id=%s"
INTRO_ROOM_NOTIFICATION_ROUTE_PLURAL = "route://community_collabcard?community_id=%s&community_name=%s"


SYNC_NOTIFICATION_TITLE = "Sync"
SYNC_NOTIFICATION_SUBTITLE = "To sync local DB"
SYNC_NOTIFICATION_ROUTE = "route://sync"


INTRO_ROOM_LOOKBACK_PERIOD = 86400

DIRECTORY_FEATURE = "Community Members Directory"
BRANCH_FEATURE_PUBLIC_LINK = "CommunityPublic"
BRANCH_FEATURE_PRIVATE_LINK = "CommunityPrivate"
BRANCH_FEATURE_DIRECTORY_LINK = "Community Members Directory"
BRANCH_FEATURE_COMMUNITY_OTL_URL = "CommunityOtlUrl"

HOURS_24 = 86400
MINUTES_30 = 1800
MINUTES_10 = 600
MINUTES_5 = 300
MINUTES_2 = 120

VALID_URLS_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

INVALID_PLATFORM = 'Invalid request'


CONVERSATIONS_COUNT_CACHE_KEY = "conversations_count_%s"
CONVERSATIONS_DISTINCT_CREATORS_KEY = "conversations_distinct_creators_%s"

SUBSCRIPTION_FETCH_EVENT_PLAN = "api/subscription/fetch_event_plan"
