from django.conf import settings

# MSG91 API urls
MSG91_SENDOTP_URI = 'https://api.msg91.com/api/v5/otp?authkey=%s&template_id=%s&mobile=%s&invisible=0&otp_expiry=10'
MSG91_VERIFYOTP_URI = 'https://api.msg91.com/api/v5/otp/verify?authkey=%s&mobile=%s&otp=%s'

# SMS Gupshup api
SMSGUPSHUP_SMS_URI = 'http://enterprise.smsgupshup.com/GatewayAPI/rest?method=SendMessage&send_to={0}&msg={1}&msg_type=TEXT&userid={2}&auth_scheme=plain&password={3}&v=1.1&format=text'

# branch
BRANCH_QUICKLINK_URI = 'https://api2.branch.io/v1/url/bulk/%s'
BRANCH_DECODE_URI = 'https://api2.branch.io/v1/url?url=%s&branch_key=%s'

# community sereialiser links
PRIVATE_LINK_TEXT_ADMIN_1 = 'I have started %s community on LikeMinds and I am inviting you to build this community together with me. Join now with this exclusive link: %s or this invite code: %s.\nAuto-verification is enabled for 24 hours.'
PRIVATE_LINK_TEXT_ADMIN_2 = 'Join %s community on LikeMinds with my exclusive link: %s or this invite code: %s.\nAuto-verification is enabled for 24 hours.'
PRIVATE_LINK_TEXT_ADMIN_1_V2 = 'I have started %s community on LikeMinds and I am inviting you to build this community together with me. Join now with this exclusive link: %s or this invite code: %s.'
PRIVATE_LINK_TEXT_ADMIN_2_V2 = 'Join %s community on LikeMinds with my exclusive link: %s or this invite code: %s.'
PRIVATE_LINK_TEXT_MEMBERS_DIRECTORY_1 = 'I have created a community directory for %s on LikeMinds. Signup and complete your profile to see detailed profiles of other members in the community using this exclusive link: %s or this invite code: %s.\nAuto-verification is enabled for 24 hours'
PRIVATE_LINK_TEXT_MEMBERS_DIRECTORY_2 = 'Directory for our community %s has been setup on LikeMinds. Signup and complete your profile to see detailed profiles of other members in the community using this exclusive link. Auto-verification is enabled for 24 hours: %s'
PRIVATE_LINK_FOR_PERMITTED_USER = 'Join %s on LikeMinds with my exclusive link. For security, this is valid only for next 24 hours: %s'
MEMBER_DIRECTORY_LINK_FOR_PERMITTED_USER = 'Here’s the link to the Directory of our community on LikeMinds: %s'
SHARE_TEXT_ADMIN = 'I am building %s community on LikeMinds.\nApply to join our community using this link: %s or this invite code: %s'
SHARE_TEXT_ADMIN_PUBLIC_PAID_COMMUNITY = "I am building %s community on LikeMinds.\n Know more about the community and apply to join using this link: %s"
SHARE_TEXT_ADMIN_PRIVATE_PAID_COMMUNITY = "I am building %s community on LikeMinds and I am inviting you to build this community together with me. Join now with this exclusive link: %s or this invite code: %s.\nAuto-verification is enabled for 24 hours"
SHARE_TEXT_ADMIN_PRIVATE_PAID_COMMUNITY_V2 = "I am building %s community on LikeMinds and I am inviting you to build this community together with me. Join now with this exclusive link: %s or this invite code: %s."
SHARE_TEXT_MEMBER = 'I am part of %s community on LikeMinds and I think you will find it interesting too.\n Know more about the community and apply to join using this link %s or the invite code: %s'
SHARE_TEXT_MEMBER_PUBLIC = 'I am part of %s community on LikeMinds and I think you will find it interesting too.\n ' \
                           'Know more about the community and apply to join using this link %s'
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
INTRO_ROOM_NOTIFICATION_ROUTE_PLURAL = "route://collabcard?collabcard_id=%s"


SYNC_NOTIFICATION_TITLE = "Sync"
SYNC_NOTIFICATION_SUBTITLE = "To sync local DB"
SYNC_NOTIFICATION_ROUTE = "route://sync"


INTRO_ROOM_LOOKBACK_PERIOD = 86400

DIRECTORY_FEATURE = "Community Members Directory"
BRANCH_FEATURE_PUBLIC_LINK = "CommunityPublic"
BRANCH_FEATURE_PRIVATE_LINK = "CommunityPrivate"
BRANCH_FEATURE_DIRECTORY_LINK = "Community Members Directory"
BRANCH_FEATURE_COMMUNITY_OTL_URL = "CommunityOtlUrl"
BRANCH_FEATURE_PAYMENT_PAGE_URL = "PaymentPageUrl"
BRANCH_CM_ONBOARDING_COMMUNITY_FEED_URL = "CommunityFeedUrlCMOnboarding"
BRANCH_SINGLE_EVENT_URL = "SingleEventUrl"

HOURS_24 = 86400
MINUTES_60 = 3600
MINUTES_30 = 1800
MINUTES_10 = 600
MINUTES_5 = 300
MINUTES_2 = 120
ONE_DAY_HOURS = 24

VALID_URLS_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

INVALID_PLATFORM = 'Invalid request'


CONVERSATIONS_COUNT_CACHE_KEY = "conversations_count_%s"
CONVERSATIONS_DISTINCT_CREATORS_KEY = "conversations_distinct_creators_%s"

SUBSCRIPTION_FETCH_EVENT_PLAN = "api/subscription/fetch_event_plan"
COMMUNITY_PUBLIC_URL = "%s/community/%s"

CONVERSATIONS_UNREAD_USER_CHATROOM_KEY = "conversations_unread_%s_%s"

COMMUNITY_HOOD_ID = 49977 if settings.IS_BETA else 49751
LITTLE_JOYS_ID = 50441 if settings.IS_BETA else 50449
COMMUNITY_HOOD_MARKETING_TITLE = "CH onboarding beta" if settings.IS_BETA else "CH onboarding prod"

PLATFORM_CODE_WEB = 'web'

INTERNATIONAL_OTP_LIMIT_MAIL_SUBJECT = 'International OTP limit exceeded'
INTERNATIONAL_OTP_LIMIT_MAIL_TEMPLATE = 'mails/international_otp_limit.html'
INTERNATIONAL_OTP_LIMIT_MAIL_RECEIVERS = ['product@likeminds.community', 'backend@likeminds.community']
INTERNATIONAL_OTP_LIMIT_FILE_NAME = 'international_otp_blocked_requests_%s.csv'
INTERNATIONAL_OTP_LIMIT_API_PATH = 'otp_limit_mail'

COMMUNITY_HOOD_PENDING_MEMBER_MAIL_SUBJECT = "Thank you for your interest in joining CommunityHood!"
COMMUNITY_HOOD_PENDING_MEMBER_MAIL_BODY = """
<p>
Dear {},
</p><p>
Thank you for your interest in being a part of CommunityHood. Your account is under approval process.
</p><p>
We will update you shortly with your account status.
</p><p>
Best regards,
</p><p>
Team CommunityHood
</p>
"""

ANDROID_BRODCAST_NOTIFIFCATION_BLOCK_VERSION_START = 200
ANDROID_BRODCAST_NOTIFIFCATION_BLOCK_VERSION_END = 212

# Community Configurations
COMMUNITY_CONFIGURATIONS = {
    "media_limits":
    {
        "type": "media_limits",
        "description": "Media size upload limit (in Kilobytes) for different file formats",
        "value":
        {
            "max_image_size": 5124, # 5 MB
            "max_video_size": 102400, # 100 MB
        }
    },
    "feed_metadata":
    {
        "type": "feed_metadata",
        "description": "",
        "value":
        {
            "post": "post"
        }
    },
    "profile_metadata":
    {
        "type": "profile_metadata",
        "description": "Community user profiles metadata",
        "value":
        {
            "widgets_enabled": False
        }
    }
}

