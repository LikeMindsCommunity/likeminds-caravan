from django.conf import settings
web_url = settings.WEB_URL

MENU = {
    'member': [
        'Invite members',
        'View all chat rooms',
        'Member directory',
        'Leave community',
        'Report'
    ],
    'promoter': [
        'Invite members',
        'View all chat rooms',
        'Member directory',
        'Edit community',
        'Report'
    ],
    'promoter2': [
        'Invite members',
        'View all chat rooms',
        'Member directory',
        'Customise join form',
        'Edit community',
        'Report'
    ],
    'pending_member': [
        'Cancel joining request'
    ],
    'pending_member_in_paid_community': [
        'Cancel membership request'
    ],
    "Subscription": [
        "Subscription status"
    ]
}

COMMUNITY_REJECT_TOAST = "Your request for joining this community was rejected. You can apply again to join this " \
                         "community "

LEVEL_1_TITLE = 'Create onboarding room'
LEVEL_1_SUB_TITLE = 'Break the ice for new members. Tell what this community stands for.'

LEVEL_2_TITLE = 'Invite your inner circle'
LEVEL_2_SUB_TITLE = 'Bring 2 trusted people you want to build this community with.'

LEVEL_3_TITLE = "Set up community directory"
LEVEL_3_SUB_TITLE = "Help members know each other. Give 10 members a community-specific identity."

LEVEL_4_TITLE = "Invite members with payment link"
LEVEL_4_SUB_TITLE = "Monetize your community. Start social sharing and onboard 10 new members."

COMMUNITY_PENDING_MEMBER_TOAST = "Your request for joining this community is pending"
PAID_COMMUNITY_PENDING_MEMBER_TOAST = "Your request for joining this community is pending. Usually it takes upto 48 hours to get approved. In case you are not approved, your payment would be refunded."

INSTAGRAM = "Instagram"
TWITTER = "Twitter"

INSTAGRAM_URL = "https://www.instagram.com/"
TWITTER_URL = "https://twitter.com/"

DOWNLOAD_SETTING_TYPE_TITLE_MAPPING = {
    "image": "Images",
    "video": "Videos",
    "audio": "Audio",
    "voice_note": "Voice Messages",
    "pdf": "Documents",
    "screen_record": "Allow screenshots & screen recording"
}

COMMUNITY_SETTING_TYPE_TITLE_MAPPING = {
    "intro_room": "Introductions Room",
    "members_auto_join": "Members auto-join",
    "direct_messages": "Enable direct messages",
    "members_can_dm": "Members can DM other members",
    "direct_messages_setting": "Direct message"
}

COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING = {
    "intro_room": "Introduction rooms are used to welcome new members in your communities. If the feature is "
                  "turned off, Introduction rooms and intro rooms would be hidden.",
    "members_auto_join": "If disabled, members will need approval from the community manager to join the community.",
    "direct_messages": "If enabled, community managers will be able to message all  members and vice-versa.",
    "members_can_dm": "Members would have option to accept or reject another member’s DM request.",
    "direct_messages_setting": ""
}

DM_COMMUNITY_SETTING_SUB_TITLE_WHEN_ENABLED = "Community managers will be able to message all members and vice-versa."

INTRO_ROOM_SETTING_DISABLED_TOAST = "Introduction Room has been turned off by the community manager."

FETCH_GET_STARTED_HEADING = u"\U0001f44b" + " Welcome to {}! " + u"\U0001f389"
FETCH_GET_STARTED_TITLE = "What’s next?"
FETCH_GET_STARTED_SUB_TITLE = 'Check the "get started" list here ' + u'\U0001f449'
FETCH_GET_STARTED_IMAGE = "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/Humaaans+-+Space+(1).png"
FETCH_GET_STARTED_BOTTOM_TEXT = "Need help in setting community, reach out to us " \
                                "<<here|route://browser?link=https://rebrand.ly/lmcontactus>>"

EMAIL_VALIDATION_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

WHATSAPP_INVITE_TEMPLATE_WITH_CODE_NAME = "join_community_with_code_v1"
WHATSAPP_INVITE_TEMPLATE_WITHOUT_CODE_NAME = "join_community_without_code_v2"

INVITE_MEMBERS_SUBJECT = "Hi there! You have been invited to join {}"
INVITE_MEMBER_REPLY_EMAIL = "LikeMinds<hi@likeminds.community>"
INVITE_MEMBERS_BUTTON_TEXT = "JOIN NOW"

WHATSAPP_COMMUNITY_CREATED_TEMPLATE_FOR_CM_NAME = 'community_created_v1'
SEGMENT_COMMUNITY_CREATION_EVENT_NAME = "Community creation completed (Core Service)"
DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR = "#00897B"

GETTING_STARTED_CM_MAIL_SUBJECT = "Hi {}! Here is what to do next at LikeMinds"
GETTING_STARTED_CM_BUTTON_TEXT = "GET STARTED"

JOIN_LMCM_COMMUNITY_LINK = "https://collabmates.app.link/DnKPs8Ld1mb"
CM_ONBOARDING_CREATE_COMMUNITY_DASHBOARD_LINK = ""
CREATE_EVENT_DASHBOARD_LINK = web_url + "/dashboard/{}/events"

MAX_NUMBER_OF_TIMES_GETTING_STARTED_EMAIL_SHOULD_FIRE = 7
FREQUENCY_OF_GETTING_STARTED_EMAIL_IN_MINS = 1440

DEFAULT_COMMUNITY_FIELD_TYPE_NAME = 'default'
DEFAULT_COMMUNITY_FIELD_TYPE_RANK = 999

COMMUNITY_HOOD_COMMUNITY_ID = 49751

CREATE_COMMUNITY_QUESTION_NAME_TITLE = "Name"
CREATE_COMMUNITY_QUESTION_NAME_HELP_TEXT = "Your name"

CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_TITLE = "Phone Number"
CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_HELP_TEXT = "Your mobile number"
CREATE_COMMUNITY_QUESTION_PHONE_NUMBER_VALUE = [{"answer_privacy": "Private"}]

CREATE_COMMUNITY_QUESTION_EMAIL_TITLE = "Email"
CREATE_COMMUNITY_QUESTION_EMAIL_HELP_TEXT = "Your email id"
CREATE_COMMUNITY_QUESTION_EMAIL_VALUE = [{"answer_privacy": "Private"}]

CREATE_COMMUNITY_QUESTION_INTRODUCTION_TITLE = "Introduce yourself"
CREATE_COMMUNITY_QUESTION_INTRODUCTION_VALUE = [{"min_chars": "50", "max_chars": "No limit"}]

FETCH_QUESTIONS_SHARED_BY_USER_TITLE = "{} invited you to join {}"
COMMUNITY_QUESTIONS_DEFAULT_TITLE = "You are joining {}"
TIME_IN_HRS_TO_SEND_JOIN_DROP_OFF_NOTIFICATION = 2
COMMUNITY_QUESTIONS_MORE_MANAGER_NAME_VALUE = "{}..{}"
FETCH_COMMUNITY_QUESTIONS_JOIN_TITLE = "Join community"

CHARACTER_LIMIT_ON_COMMUNITY_NAME = 30

FREE_COMMUNITY_NOT_AJ_NOT_SHARED_BY_MESSAGE = 'Please send valid invite code to join this community'
INVALID_INVITE_CODE_MESSAGE = 'Invalid invite code!'
FREE_INVITE_CODE_ALREADY_USED_MESSAGE = 'Free invite code already used!'

TYPE_ID_WITH_NO_DIRECTORY_QUESTIONS = 1111
SUB_TYPE_ID_WITH_NO_DIRECTORY_QUESTIONS = 1111

CM_ONBOARDING_COMMUNITY_MODERATION_MAIL_SUBJECT = "It's time to set some rules!"
CM_ONBOARDING_COMMUNITY_MODERATION_BUTTON_TEXT = "Moderation Guide"
CM_ONBOARDING_COMMUNITY_MODERATION_BUTTON_LINK = "https://flicker-map-472.notion.site/Community-Settings-a022b2fe2f5f41dfa98f45c44d1dfcdd"
MEMBER_REPLY_EMAIL = "LikeMinds<hi@likeminds.community>"
CM_ONBOARDING_COMMUNITY_MODERATION_MIN_MEMBERS_COUNT = 5

EDIT_COMMUNITY_RIGHT_MENU_OPTION_NUMBER = 3
EDIT_COMMUNITY_RIGHT_MENU_OPTION_NUMBER_FOR_DIRECTORY_QUESTIONS = 4

ANSWER_PRIVACY_KEY = "answer_privacy"
ANSWER_PRIVACY_PRIVATE_VALUE = "Private"
ANSWER_PRIVACY_PUBLIC_VALUE = "Public"
DIRECTORY_QUESTIONS_CREATE_EVENT_NAME = "Questions added"
DIRECTORY_QUESTIONS_EDIT_EVENT_NAME = "Question edited"
DIRECTORY_QUESTIONS_DELETE_EVENT_NAME = "Questions deleted"

DEFAULT_QUESTION_ID_KEY = "id"
DEFAULT_ANSWER_KEY = "value"
DEFAULT_QUESTIONS_LIST_KEY = "questions"
DIRECTORY_QUESTIONS_V2_QUESTION_ID_KEY = "question_id"
DIRECTORY_QUESTIONS_V2_ANSWER_KEY = "answer"
DIRECTORY_QUESTIONS_V2_QUESTIONS_LIST_KEY = "question_answers"

PAID_PLAN = "paid"
FREE_PLAN = "free"

LEAST_MEMBER_RIGHT_STATE_VALUE = 0
