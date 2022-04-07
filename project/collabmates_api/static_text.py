from django.conf import settings

from utility.states import member_states

SERVER_URL = settings.URL

if SERVER_URL is None:
    SERVER_URL = 'https://beta.likeminds.community'

# variables
HOURS_24 = 86400


chatroom_actions_creator_mute = [

    {
        'id': 1,
        'title': 'Rename chatroom'
    },

    {
        'id': 2,
        'title': 'View participants'
    },

    {
        'id': 3,
        'title': 'Invite'
    },

    {
        'id': 5,
        'title': 'View community'
    },

    {
        'id': 7,
        'title': 'Delete chatroom'
    },

    {
        'id': 8,
        'title': 'Unmute notifications'
    },

]

chatroom_actions_creator_unmute = [

    {
        'id': 1,
        'title': 'Rename chatroom'
    },

    {
        'id': 2,
        'title': 'View participants'
    },

    {
        'id': 3,
        'title': 'Invite'
    },

    {
        'id': 5,
        'title': 'View community'
    },

    {
        'id': 6,
        'title': 'Mute notifications'
    },

    {
        'id': 7,
        'title': 'Delete chatroom'
    },

]

collabcard_action_user_follow_unmute = [

    {
        'id': 2,
        'title': 'View participants'
    },

    {
        'id': 3,
        'title': 'Invite'
    },

    {
        'id': 5,
        'title': 'View community'
    },

    {
        'id': 6,
        'title': 'Mute notifications'
    },

    {
        'id': 9,
        'title': 'Leave chatroom'
    },

    {
        'id': 10,
        'title': 'Report Spam/Abuse'
    }

]

collabcard_action_user_follow_mute = [

    {
        'id': 2,
        'title': 'View participants'
    },

    {
        'id': 3,
        'title': 'Invite'
    },

    {
        'id': 5,
        'title': 'View community'
    },

    {
        'id': 8,
        'title': 'UnMute notifications'
    },

    {
        'id': 9,
        'title': 'Leave chatroom'
    },

    {
        'id': 10,
        'title': 'Report Spam/Abuse'
    }

]

collabcard_action_user_unfollow = [

    {
        'id': 2,
        'title': 'View participants'
    },

    {
        'id': 3,
        'title': 'Invite'
    },

    {
        'id': 5,
        'title': 'View community'
    },

    {
        'id': 4,
        'title': 'Join chatroom'
    },

    {
        'id': 10,
        'title': 'Report Spam/Abuse'
    }
]

collabcard_action_dm_user_unmute = [
    {
        'id': 21,
        'title': 'View profile'
    },
    {
        'id': 5,
        'title': 'View community'
    },
    {
        'id': 6,
        'title': 'Mute notifications'
    }
]

collabcard_action_dm_user_mute = [
    {
        'id': 21,
        'title': 'View profile'
    },
    {
        'id': 5,
        'title': 'View community'
    },
    {
        'id': 8,
        'title': 'UnMute notifications'
    }
]

rename_chatroom = {'id': 1, 'title': 'Rename chatroom'}

view_participants = {'id': 2, 'title': 'View participants'}

invite = {'id': 3, 'title': 'Invite'}

join_chatroom = {'id': 4, 'title': 'Join chatroom'}

view_community = {'id': 5, 'title': 'View community'}

mute_notifications = {'id': 6, 'title': 'Mute notifications'}

delete_chatroom = {'id': 7, 'title': 'Delete chatroom'}

unMute_notifications = {'id': 8, 'title': 'UnMute notifications'}

unfollow_chatroom = {'id': 9, 'title': 'Leave chatroom'}

report = {'id': 10, 'title': 'Report Spam/Abuse'}

pin_chatroom = {'id': 13, 'title': "Pin chat room"}

unpin_chatroom = {'id': 14, 'title': "Unpin chat room"}

leave_chatroom = {'id': 15, 'title': "Leave chatroom"}

add_all_members = {'id': 16, 'title': "Add all members"}

chatroom_settings = {'id': 17, 'title': "Settings"}

member_can_message = {'id': 18, 'title': "Participants can send message"}

accessible_without_subscription = {'id': 19, 'title': "Accessible without subscription"}

view_profile = {'id': 21, 'title': "View profile"}

edit_chatroom_pic = {'id': 22, 'title': "Edit chatroom pic"}

edit_info = {'id': 23, 'title': "Edit info"}

make_it_secret = {'id': 24, 'title': "Make it secret"}

auto_joined_by_all_members = {'id': 25, 'title': "Auto joined by all members"}

manage_permissions = {'id': 26, 'title': "Manage Permissions"}

block_member_chatroom = {'id': 27, 'title': "Block"}

unblock_member = {'id': 28, 'title': "Unblock"}

settings_for_purpose_chatroom = [rename_chatroom, member_can_message, accessible_without_subscription]

settings_for_chatroom = [rename_chatroom, member_can_message, pin_chatroom, accessible_without_subscription]

settings_for_chatroom_with_revamp = [edit_chatroom_pic, edit_info, member_can_message, make_it_secret]

# get onboarding examples
INTRODUCTION_EXAMPLES = [

    {
        "header": "Sample member introductions",
        "sub_header": "Here are a few examples",
        "title": "IITD Entrepreneurs in Gurgaon",
        "sub_title": """Hello everyone, I am a 2012 graduate from electrical engineering. I am running a social media venture based out of Gurgaon. Looking forward to connecting with you all and contribute to this community however I can."""

    },

    {
        "header": "Sample member introductions",
        "sub_header": "Here are a few examples",
        "title": "Musicians in Gurgaon",
        "sub_title": "A musician from the Himalayas! Looking for paid opportunities to play percussion (Djembe & Cajon)! I bet your feet won’t stay on the ground for long!  "

    },

    {
        "header": "Sample member introductions",
        "sub_header": "Here are a few examples",
        "title": "COVID Hackers",
        "sub_title": """Hey all, I am a tech entrepreneur from Gurgaon. Looking forward to hacking the COVID times with this tribe and discover fun new "At Home" hobbies 🤟"""

    }

]

ONBOARDING_EXAMPLES = [

    {
        "header": "Sample community purposes",
        "sub_header": "Here are few examples of other communities’ purpose.",
        "title": "IITD Alums in Gurgaon",
        "sub_title": """This community is for IITD alumni currently living in Gurgaon and nearby areas. 
Anytime if you are looking to exchange referrals or maybe want to have a small get together just create a chatroom in the community with relevant content and interested community members will participate in it."""

    },

    {
        "header": "Sample community purposes",
        "sub_header": "Here are few examples of other communities’ purpose.",
        "title": "Python Developers in Mumbai",
        "sub_title": "Welcome tech lovers far and wide! We’re an online and in-person python-enthusiast group hosting live speaking events on a range of tech topics. You can join us in person if possible or on one of our live streams. Look out for our virtual happy hours and other networking events."

    },

    {
        "header": "Sample community purpose",
        "sub_header": "Here are few examples of other communities’ purpose.",
        "title": "Adventure Sports Enthusiasts",
        "sub_title": "This is a group for anyone interested in adventure sports like hiking, rock climbing, camping, kayaking, bouldering, etc. All skill levels are welcome. We started this group to meet other outdoor enthusiasts. Looking forward to exploring the outdoors with everybody."

    }

]

MENU = {
    'member': ['Invite members', 'View all chat rooms', 'Member directory', 'Leave community', 'Report'],
    'promoter': ['Invite members', 'View all chat rooms', 'Member directory', 'Edit community', 'Report'],
    'pending_member': ['Cancel joining request']
}

delete_room_manager_right = {'id': 1, 'title': 'Moderate chatrooms', 'sub_title': None, "state": 0, "rank": 5}

approve_manager_right = {'id': 2, 'title': 'Moderate members', 'sub_title': None, "state": 1, "rank": 3}

edit_community_manager_right = {'id': 3, 'title': "Edit community details", 'sub_title': None, "state": 2, "rank": 2}

view_contact_manager_right = {'id': 4, 'title': 'View member contact info', 'sub_title': None, "state": 3, "rank": 1}

add_manager_manager_right = {'id': 5, 'title': "Add community managers", 'sub_title': None, "state": 4, "rank": 0}

moderate_dm_settings = {'id': 6, 'title': "Moderate DM settings", 'sub_title': None, "state": 5, "rank": 4}

manager_rights_list = [delete_room_manager_right, edit_community_manager_right, approve_manager_right,
                       view_contact_manager_right, add_manager_manager_right]

create_room_member_right = {'id': 1, 'title': "Create chat rooms", 'sub_title': None, "state": 0}

create_poll_member_right = {'id': 2, 'title': "Create polls", 'sub_title': None, "state": 1}

create_event_member_right = {'id': 3, 'title': "Create events", 'sub_title': None, "state": 2}

respond_in_rooms_member_right = {'id': 4, 'title': "Respond in chat rooms", 'sub_title': None, "state": 3}

invite_private_member_right = {'id': 5, 'title': "Invite members via private link",
                               'sub_title': "Private links remain valid for 24 hours and. the user joining via them a re auto verified",
                               "state": 4
                               }
auto_approve_member_right = {'id': 6, 'title': "Auto-approve created chat rooms", 'sub_title': None, "state": 5}

create_secret_chatroom_right = {'id': 7, 'title': "create secret room rights", 'sub_title': None, "state": 6}

show_direct_messages_right = {'id': 8, 'title': "Direct messages",
                              'sub_title': 'Direct messaging can happen only between a community manager and a community member (not among 2 members).',
                              "state": 7}

members_can_dm_right = {'id': 9, 'title': "Members who can initiate DMs", 'sub_title': None, "state": 8}

member_rights_list = [create_room_member_right, create_poll_member_right,
                      create_event_member_right, respond_in_rooms_member_right,
                      invite_private_member_right, auto_approve_member_right]


tool_member_requests = {"title": "Member Requests",
                        "image_url": "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Ficons%2Fmember_requests.png?alt=media&token=eed6056e-8553-4c6a-ac99-e049fef4c75e",
                        "count": 0}

tool_pending_chat_rooms = {"title": "Pending Chat Rooms",
                           "image_url": "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Ficons%2Fpending_chat_rooms.png?alt=media&token=4fd6c701-f433-4ad7-b799-7b879a8bc309",
                           "count": 0}

tool_review_reports = {"title": "Review Reports",
                       "image_url": "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Ficons%2Freview_reports.png?alt=media&token=f9a75d81-9c6a-41dd-8a7d-133b47f29512",
                       "count": 0}

tool_edit_directory_questions = {"title": "Edit directory questions",
                                 "image_url": "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Ficons%2Fedit_directory_questions.png?alt=media&token=6132427f-3b08-4da8-8a25-02ee55cec480",
                                 "route": "route://edit_community_directory?community_id={}&community_name={}"}

tool_edit_community_details = {"title": "Edit community details",
                               "image_url": "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Ficons%2Fedit_community_details.png?alt=media&token=0dbb625b-da94-4cbe-b550-5688a6ad5944",
                               "route": "route://edit_community?community_id={}&community_name={}"}

tool_community_settings = {"title": "Community Settings",
                           "image_url": "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Ficons%2Fcommunity_settings.png?alt=media&token=0e105674-9bde-4336-850b-118671fcdec8",
                           "route": "route://community_settings?community_id={}&community_name={}"}

months_semi = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
               9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}


months_full = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July", 8: "August",
               9: "September", 10: "October", 11: "November", 12: "December"}


MENU = {
    'member': ['Invite members', 'View all chat rooms', 'Member directory', 'Leave community', 'Report'],
    'promoter': ['Invite members', 'View all chat rooms', 'Member directory', 'Edit community', 'Report'],
    'pending_member': ['Cancel joining request'],
    'pending_member_in_paid_community': ['Cancel membership request']
}

BRANCH_LINK_PREFIX_ANDROID = 'likeminds://' + SERVER_URL[8:]
BRANCH_LINK_PREFIX_IOS = 'collabmates://' + SERVER_URL[8:]

NOTIFICATION_SUB_TITLE_FOR_CM_REMOVED = "You no longer have any community management rights. Consider highlighting this to your Community Manager if you think this was accidental or if you want to know why."
ENABLE_MANAGER_RIGHT_VIEW_CONTACT_INFO = "Congratulations! The Community Manager has conferred you privilege to “View Members Contact Information”"
ENABLE_MANAGER_RIGHT_EDIT_COMMUNITY = "Congratulations! The Community Manager has conferred you privilege to “Edit Community Details”"
ENABLE_MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS = "Congratulations! The Community Manager has conferred you privilege to “Approve or Remove Members”"
ENABLE_MANAGER_RIGHT_DELETE_ROOMS = "Congratulations! The Community Manager has conferred you privilege to “Delete Chat room or Responses”"
ENABLE_MANAGER_ADD_MANAGER_RIGHT = "Congratulations! The Community Manager has conferred you privilege to “Add Community Managers”."

LINKED_IN_ACCESS_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKED_IN_USER_URL = 'https://api.linkedin.com/v2/me?projection=(id,firstName,emailAddress,lastName,vanityName,headline,interests,location,picture-url,name,profilePicture(displayImage~:playableStreams))&oauth2_access_token='
LINKED_IN_EMAIL_URL = 'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))&oauth2_access_token='

VIDEO_ATTACHMENT_FILL_TEXT = "\n * This is a video message. Please update your app *"

VIDEO_SYNC_TRIGGER_VERSION_CODE_AN = 85
VIDEO_SYNC_TRIGGER_VERSION_CODE_iOS = 85
SECRET_CHATROOM_SYNC_TRIGGER_VERSION_CODE_AN = 110
REACTIONS_SYNC_TRIGGER_VERSION_CODE_AN = 112
TOPIC_SYNC_TRIGGER_VERSION_CODE_AN = 133
CHATROOM_FIRST_MESSAGE_ACTION_VERSION_CODE_ANDROID = 131
MICRO_POLLS_ANDROID_VERSION_CODE = 139
EVENT_ATTACHMENT_VERSION_CODE_AN = 151

DM_CHATROOMS_VERSION_CODE_IOS = 213
DM_CHATROOMS_VERSION_CODE_ANDROID = 156
DM_CHATROOMS_VERSION_CODE_WEB = 1

EVENT_CO_HOST_NOTIFICATION_TITLE = 'You are a co-host!'
EVENT_CO_HOST_NOTIFICATION_SUB_TITLE = "%s added you as a host for %s in %s"
EVENT_CO_HOST_NOTIFICATION_ROUTE = 'route://chatroom_detail?chatroom_id=%s'
CREATE_CONVERSATION_API_END_POINT = f"{settings.URL}/api/conversation/create"
UPLOAD_FILES_V1_API_END_POINT = f"{settings.URL}/api/v1/upload_files"
POLL_EXPIRY_NOTIFICATION_SUB_TITLE = 'Your poll ended. Tap to see results'
POLL_EXPIRY_NOTIFICATION_ROUTE = 'route://poll_chatroom?chatroom_id=%s&poll_end=true'

MEMBER_LEFT_COMMUNITY_NOTIFICATION_SUB_TITLE = "%s has left your community."
COMMUNITY_DETAIL_ROUTE = f"route://community?community_id=%s&community_name=%s"

MASTER_INTRO_TITLE_TEXT = "This chat room has introductions of all members of the community. Greet members in their respective intro rooms to make them feel welcomed."
MASTER_INTRO_HEADER = "Introductions "+u"\U0001F590"

GENERAL_CHAT_TITLE_TEXT = "This chatroom is to have off-topic conversations with the community members."
GENERAL_CHAT_HEADER = "General Chat Room"

CHATROOM_PREVIW_CACHE_KEY = "chatroom_preview_%s_%s"

PIN_CHATROOM_TITLE = "Chat room pinned!"
PIN_SUBTITLE = "Your community manager %s has just pinned %s on everyone’s feed."
PIN_ROUTE = "route://chatroom_detail?chatroom_id=%s"

SECRET_CHATROOM_ADD_SUBTITLE = "You have been added to %s"
SECRET_CHATROOM_ADD_ROUTE = "route://chatroom_detail?chatroom_id=%s"

SECRET_CHATROOM_REMOVED_SUBTITLE = "You have been removed from %s"
SECRET_CHATROOM_REMOVED_ROUTE = "route://main"

POLL_CONVERSATION_TITLE = "Time to vote!"
POLL_CONVERSATION_SUBTITLE = "%s started a poll in %s in %s"
POLL_CONVERSATION_ROUTE = "route://poll_chatroom?community_id=%s&chatroom_id=%s&conversation_id=%s"

MESSAGE_REACTIONS_NOTIFICATION_SUB_TITLE = "%s reacted to your message with %s"
MESSAGE_REACTIONS_CHATROOM_NOTIFICATION_ROUTE = "route://chatroom_detail?chatroom_id=%s"
MESSAGE_REACTIONS_CONVERSATION_NOTIFICATION_ROUTE = f"{MESSAGE_REACTIONS_CHATROOM_NOTIFICATION_ROUTE}&conversation_id=%s"

COMMUNITY_MEMBER_STATES = [
        member_states.ADMIN,
        member_states.PENDING_MEMBER,
        member_states.MEMBER,
        member_states.PROFILE_UNAVAILABLE
    ]

CURRENT_IOS_VERSION = 91

GIF_ATTACHMENT_FILL_TEXT = "\n * This is a gif message. Please update your app *"

PENDING_MEMBER_TOAST = "Your request for joining this community is pending"
PAID_COMMUNITY_PENDING_MEMBER_TOAST = "Your request for joining this community is pending. Usually it takes upto 48 hours to get approved. In case you are not approved, your payment would be refunded."

CHATROOM_NOTIFICATION_OWNER_ADD_ALL_MEMBER_TITLE = "%s added you to %s chatroom!"
CHATROOM_NOTIFICATION_OWNER_ADD_ALL_MEMBER_SUBTITLE = "Tap to join in the conversation."

MEMBER_LEFT_COMMUNITY_TOAST = "You left the community."
MEMBER_REMOVED_FROM_COMMUNITY_TOAST = "You are no longer a member of this community."
PENDING_MEMBER_REQUEST_REJECTED_COMMUNITY_TOAST = "Your request for joining this community is cancelled"

CHATROOM_TOPIC_NOTIFICATION_TITLE = "Topic updated!"
CHATROOM_TOPIC_NOTIFICATION_SUB_TITLE = "The topic of your followed chat room %s has just been updated."
CHATROOM_TOPIC_NOTIFICATION_ROUTE = "route://chatroom_detail?chatroom_id=%s"

CHATROOM_DETAIL_NOTIFICATION_ROUTE = "route://chatroom_detail?chatroom_id=%s"
SECRET_CHATROOM_VERSION_CODE_IOS = 157

PAID_COMMUNITY_LEVEL_4_TITLE = "Monetization"
PAID_COMMUNITY_LEVEL_4_SUB_TITLE = "Invite members with payment link"

# These are only for beta, don't send them in upcoming release.
CHATROOM_SETTINGS_VERSION_CODE_AN = 155
CHATROOM_SETTINGS_VERSION_CODE_IOS = 232

INTRO_ROOM_V2_VERSION_CODE_DICT = {
    "an": 159,
    "ios": 235
}


MEMBER_LEFT_DM_CHATROOM_MESSAGE = "{} left {}"
MEMBER_REMOVED_DM_CHATROOM_MESSAGE = "{} was removed from {}"

CM_REMOVED_COMMUNITY_DM_CHATROOM_MESSAGE = "{} is no longer a community manager"
MEMBER_JOINING_COMMUNITY_DM_CHATROOM_MESSAGE = "{} is a member now"

MEMBER_BECOMES_CM_DM_CHATROOM_MESSAGE = "{} is a community manager now"

BLOCK_MEMBER_DM_CHATROOM_MESSAGE = "Direct messaging request rejected."
UNBLOCK_MEMBER_DM_CHATROOM_MESSAGE = "{} and {} are now connected."

ATTENDEES_FILTER_NAME = "attendees"
CO_HOSTS_FILTER_NAME = "co_hosts"

ALL_MEMBER_COHORT_TEXT = "All Member Cohort"
SUBSCRIPTION_COHORT_NAME = "Subscription Plan - {}"
SUBSCRIPTION_EXPIRED_COHORT_NAME = "Subscription Expired"

SUBSCRIPTION_PLAN_NAMES = {
    "days": {
        "unique": False,
        "title": "Day/s",
        "subtitle": "day/s"
    },
    "weekly": {
        "unique": False,
        "title": "Week/s",
        "subtitle": "week/s"
    },
    "monthly": {
        "unique": False,
        "title": "Month/s",
        "subtitle": "month/s"
    },
    "quarterly": {
        "unique": True,
        "title": "Quarterly",
        "subtitle": "month/s"
    },
    "half_yearly": {
        "unique": True,
        "title": "Half Yearly",
        "subtitle": "month/s"
    },
    "yearly": {
        "unique": True,
        "title": "Yearly",
        "subtitle": "month/s"
    },
    "lifetime": {
        "unique": True,
        "title": "Lifetime",
        "subtitle": "lifetime"
    }
}

LM_PLATFORM_CODES = ["an", "ios", "web"]

SINGLE_COMMUNITY_VIEW_VERSION_CODE = {
    "an": 170,
    "ios": 300,
    "web": 1001
}

FREE_LINK_VERSION_CODE = {
    "an": 1001,
    "ios": 1001,
    "web": 1001
}

CREATE_CHATROOM_REVAMP_VERSION_CODE = {
    "an": 1001,
    "ios": 1001,
    "web": 1001
}

MEMBERSHIP_PLANS_MANAGEMENT_TOOLS = {
    "title": "Membership plans",
    "image_url": "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/mambership_plans_icon.png",
    "route": "route://membership_plans?community_id={}"
}

SEGMENT_COMMUNITY_LOGO_UPLOADED_EVENT_NAME = "Community logo uploaded (Core Service)"

CUSTOMISE_JOIN_FORM_MAIL_SUBJECT = "Hi {}! Your community join form is all set"

CM_ONBOARDING_ANDROID_VERSION_CODE = 175
CM_ONBOARDING_IOS_VERSION_CODE = 297
CM_ONBOARDING_WEB_VERSION_CODE = 1

CM_ONBOARDING_COMMUNITY_FEED_URL = "{}/community_feed?community_id={}&community_name={}"

PRIVATE_LINK_APP_INVITE_DEFAULT_TOAST = "The private invite link has expired. Continue to join the community and " \
                                        "wait for admin’s approval. Or, ask {} to resend a private invite link."

if settings.IS_BETA:
    CM_ONBOARDING_CREATE_COMMUNITY_BRANCH_LINK = "https://collabmates.app.link/4FSTFGHWQkb"

else:
    CM_ONBOARDING_CREATE_COMMUNITY_BRANCH_LINK = "https://collabmates.app.link/jufb9hPRGkb"

COMMUNITY_MEMBER_PROFILE_MEMBER_SINCE_TEXT = "Member since {}"

CM_ONBOARDING_JOIN_FORM_NOT_SETUP_MAIL_SUBJECT = "Setup join form for {}"
DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR = "#00897B"
CM_ONBOARDING_JOIN_FORM_NOT_SETUP_BUTTON_LINK = "https://flicker-map-472.notion.site/Community-join-form-586af3b4e6a04d16970a374410d0bf6e"
CM_ONBOARDING_JOIN_FORM_NOT_SETUP_BUTTON_TEXT = "Join form guide"
MEMBER_REPLY_EMAIL = "LikeMinds<hi@likeminds.community>"

FIVE_DAYS_IN_HOURS = 24 * 5

DIRECTORY_QUESTIONS_ANDROID_VERSION_CODE = 185
DIRECTORY_QUESTIONS_IOS_VERSION_CODE = 335
DIRECTORY_QUESTIONS_WEB_VERSION_CODE = 1101

M2CM_V2_ANDROID_VERSION_CODE = 1209
M2CM_V2_IOS_VERSION_CODE = 1209
M2CM_V2_WEB_VERSION_CODE = 1209

DIRECTORY_QUESTIONS_MANAGEMENT_TOOLS_TITLE = "Customise join form"
MEMBER_REQUEST_TOOL_ROUTE = "route://member_approve?community_id={}&community_name={}"
PENDING_CHATROOM_TOOL_ROUTE = "route://pending_chatrooms?community_id={}&community_name={}"
REPORTS_TOOL_ROUTE = "route://review_reports?community_id={}&community_name={}"
MANAGEMENT_TOOLS_HEADER = "Management tools for {}"

MEMBER_PROFILE_MENU_ITEMS = {
    "EDIT_TITLE": {
        "title": "Edit title",
        "route": "route://edit_custom_title?community_id={}&member_id={}"
    },
    "EDIT_PERMISSIONS": {
        "title": "Edit permissions",
        "route": "route://edit_member_rights?community_id={}&member_id={}"
    },
    "GIVE_CM_RIGHTS": {
        "title": "Give community management rights",
        "route": "route://give_manager_rights?community_id={}&member_id={}"
    },
    "EDIT_CM_RIGHTS": {
        "title": "Edit management rights",
        "route": "route://edit_manager_rights?community_id={}&member_id={}"
    },
    "REPORT_MEMBER": {
        "title": "Report member",
        "route": "route://report_member?community_id={}&member_id={}"
    },
    "REMOVE_FROM_COMMUNITY": {
        "title": "Remove from community",
        "route": "route://remove_from_community?community_id={}&member_id={}"
    },
    "BLOCK_MEMBER": {
        "title": "Block member",
        "route": "route://block_member?community_id={}&member_id={}"
    }
}

COMMUNITY_LEVEL_3_TEXT = "Level 3"

IMAGE_URLS_FOR_QUESTION_TITLES = ["Email", "Phone Number", "Phone No."]

CREATE_COMMUNITY_QUESTION_NAME_TITLE = "Name"

SIX_HOURS_IN_SECONDS = 6 * 60 * 60
