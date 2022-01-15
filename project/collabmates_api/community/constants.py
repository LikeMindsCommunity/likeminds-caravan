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
    "members_auto_join": "Members auto-join"
}

COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING = {
    "intro_room": "Introduction rooms are used to welcome new members in your communities. If the feature is "
                  "turned off, Introduction rooms and intro rooms would be hidden.",
    "members_auto_join": "If disabled, members will need approval from the community manager to join the community."
}

INTRO_ROOM_SETTING_DISABLED_TOAST = "Introduction Room has been turned off by the community manager."

FETCH_GET_STARTED_HEADING = u"\U0001f44b" + " Welcome to {}! " + u"\U0001f389"
FETCH_GET_STARTED_TITLE = "What’s next?"
FETCH_GET_STARTED_SUB_TITLE = 'Check the "get started" list here ' + u'\U0001f449'
FETCH_GET_STARTED_IMAGE = "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/Humaaans+-+Space+(1).png"
FETCH_GET_STARTED_BOTTOM_TEXT = "Need help in setting community, reach out to us " \
                                "<<here|route://browser?link=https://rebrand.ly/lmcontactus>>"

EMAIL_VALIDATION_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

WHATSAPP_INVITE_TEMPLATE_WITH_CODE_NAME = "join_community_with_code"
WHATSAPP_INVITE_TEMPLATE_WITHOUT_CODE_NAME = "join_community_without_code_v2"

INVITE_MEMBERS_SUBJECT = "Hi there! You have been invited to join {}"
INVITE_MEMBER_REPLY_EMAIL = "LikeMinds<hi@likeminds.community>"
INVITE_MEMBERS_BUTTON_TEXT = "JOIN NOW"

WHATSAPP_COMMUNITY_CREATED_TEMPLATE_FOR_CM_NAME = 'community_created_v1'
SEGMENT_COMMUNITY_CREATION_EVENT_NAME = "Community creation completed (Core Service)"
DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR = "#00897B"

GETTING_STARTED_CM_MAIL_SUBJECT = "Hi {}! Here is what to do next at LikeMinds"
GETTING_STARTED_CM_BUTTON_TEXT = "GET STARTED"

JOIN_LMCM_COMMUNITY_LINK = "https://collabmates.app.link/bQ7qwsrOzlb"
CM_ONBOARDING_CREATE_COMMUNITY_DASHBOARD_LINK = ""
CREATE_EVENT_DASHBOARD_LINK = web_url + "/dashboard/{}/events"

MAX_NUMBER_OF_TIMES_GETTING_STARTED_EMAIL_SHOULD_FIRE = 7
FREQUENCY_OF_GETTING_STARTED_EMAIL_IN_MINS = 1440

DEFAULT_COMMUNITY_FIELD_TYPE_NAME = 'default'
DEFAULT_COMMUNITY_FIELD_TYPE_RANK = 999

COMMUNITY_HOOD_COMMUNITY_ID = 49751

CHARACTER_LIMIT_ON_COMMUNITY_NAME = 30

FREE_COMMUNITY_NOT_AJ_NOT_SHARED_BY_MESSAGE = 'Please send valid invite code to join this community'
INVALID_INVITE_CODE_MESSAGE = 'Invalid invite code!'
FREE_INVITE_CODE_ALREADY_USED_MESSAGE = 'Free invite code already used!'
