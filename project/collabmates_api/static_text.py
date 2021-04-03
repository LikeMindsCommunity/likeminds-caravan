from django.conf import settings
SERVER_URL = settings.URL

if SERVER_URL is None:
    SERVER_URL = 'https://beta.likeminds.community'

# variables
#HOURS_24 = 86400
HOURS_24 = 60

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
        'title': 'Unfollow chatroom'
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
        'title': 'Unfollow chatroom'
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
        'title': 'Follow chatroom'
    },

    {
        'id': 10,
        'title': 'Report Spam/Abuse'
    }
]

rename_chatroom = {'id': 1, 'title': 'Rename chatroom'}

view_participants = {'id': 2, 'title': 'View participants'}

invite = {'id': 3, 'title': 'Invite'}

follow_chatroom = {'id': 4, 'title': 'Follow chatroom'}

view_community = {'id': 5, 'title': 'View community'}

mute_notifications = {'id': 6, 'title': 'Mute notifications'}

delete_chatroom = {'id': 7, 'title': 'Delete chatroom'}

unMute_notifications = {'id': 8, 'title': 'UnMute notifications'}

unfollow_chatroom = {'id': 9, 'title': 'Unfollow chatroom'}

report = {'id': 10, 'title': 'Report Spam/Abuse'}

mark_active = {'id': 11, 'title': 'Mark active'}

mark_inactive = {'id': 12, 'title': 'Mark inactive'}

pin_chatroom = {'id': 13, 'title': "Pin chat room"}

unpin_chatroom = {'id': 14, 'title': "Unpin chat room"}

leave_chatroom = {'id': 15, 'title': "Leave chatroom"}

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

delete_room_manager_right = {'id': 1, 'title': 'Delete chat rooms/messages', 'sub_title': None, "state": 0}


approve_manager_right = {'id': 2, 'title': 'Approve/remove members', 'sub_title': None, "state": 1}

edit_community_manager_right = {'id': 3, 'title': "Edit community details", 'sub_title': None, "state": 2}

view_contact_manager_right = {'id': 4, 'title': 'View member contact info', 'sub_title': None, "state": 3}

add_manager_manager_right = {'id': 5, 'title': "Add community managers", 'sub_title': None, "state": 4}

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
                                 "image_url": "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Ficons%2Fedit_directory_questions.png?alt=media&token=6132427f-3b08-4da8-8a25-02ee55cec480"}

tool_edit_community_details = {"title": "Edit community details",
                               "image_url": "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Ficons%2Fedit_community_details.png?alt=media&token=0dbb625b-da94-4cbe-b550-5688a6ad5944"}

tool_community_settings = {"title": "Community Settings",
                           "image_url": "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Ficons%2Fcommunity_settings.png?alt=media&token=0e105674-9bde-4336-850b-118671fcdec8"}

months_semi = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
               9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}


months_full = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July", 8: "August",
               9: "September", 10: "October", 11: "November", 12: "December"}


MENU = {
    'member': ['Invite members','View all chat rooms','Member directory','Leave community','Report'],
    'promoter': ['Invite members','View all chat rooms','Member directory','Edit community','Report'],
    'pending_member':['Cancel joining request']
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

EVENT_CO_HOST_NOTIFICATION_TITLE = 'You are a co-host!'
EVENT_CO_HOST_NOTIFICATION_SUB_TITLE = "%S added you as a host for %s in %s"
EVENT_CO_HOST_NOTIFICATION_ROUTE = 'route://chatroom_detail?chatroom_id=%s'
EVENT_NOTIFICATIONS_TITLE = "Event Reminder!"
CREATE_CONVERSATION_API_END_POINT = f"{settings.URL}/api/conversation/create"
UPLOAD_FILES_V1_API_END_POINT = f"{settings.URL}/api/v1/upload_files"
ONLINE_EVENT_NOTIFICATION_SUB_TITLE = 'is going to start soon. Please join it online now.'
ONLINE_EVENT_NOTIFICATION_ROUTE = 'route://browser?link=%s'
OFFLINE_EVENT_NOTIFICATION_24_H_SUB_TITLE = 'is taking place tomorrow. Please make arrangements to reach there on time.'
OFFLINE_EVENT_NOTIFICATION_24_H_ROUTE = 'route://chatroom_detail?chatroom_id=%s'
OFFLINE_EVENT_NOTIFICATION_30_M_SUB_TITLE = 'Your event is starting in 30 minutes'
OFFLINE_EVENT_NOTIFICATION_30_M_ROUTE = 'route://chatroom_detail?chatroom_id=%s'
POLL_EXPIRY_NOTIFICATION_SUB_TITLE = 'Your poll ended. Tap to see results'
POLL_EXPIRY_NOTIFICATION_ROUTE = 'route://poll_chatroom?chatroom_id=%s&poll_end=true'

MEMBER_LEFT_COMMUNITY_NOTIFICATION_SUB_TITLE = "%s has left your community."
COMMUNITY_DETAIL_ROUTE = f"route://community?community_id=%s&community_name=%s"

MASTER_INTRO_TITLE_TEXT = "This chat room has introductions of all members of the community. Greet members in their respective intro rooms to make them feel welcomed."
MASTER_INTRO_HEADER = "Introductions "+u"\U0001F590"

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
POLL_CONVERSATION_ROUTE = "'route://poll_chatroom?chatroom_id=%s&conversation_id=%s"

