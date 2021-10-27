ACTIVE_USER_LIMIT = 3

FEED_UPWARD_SCROLL = 0
FEED_DOWNWARD_SCROLL = 1

CHATROOM_COUNT_LIMIT = 4

INVITE_MEMBERS = {
    'id': 1,
    'title': "Invite members",
}

NEW_CHATROOM = {
    'id': 2,
    'title': "Create new chat room",
}

DIRECTORY = {
    'id': 3,
    'title': "Member directory",
}

PINNED = {
    'id': 4,
    'title': "Pinned chat rooms",
}

COMMUNITY_DETAILS = {
    'id': 5,
    'title': "Community details",
}

PINNED_TOP_BAR_TITLE = "Pinned chat rooms"
PINNED_TOP_BAR_IMAGE = "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Fmain_website%2Fpaper_pin.png?alt=media&token=8b249d08-fd67-45f8-9acd-d8c05ce5e8af"

INVITE_MEMBERS_ROUTE = "route://chatroom_new_feed?community_id=%s&share=true"
NEW_CHATROOM_ROUTE = "route://create_chatroom?community_id=%s&community_name=%s"
DIRECTORY_ROUTE = "route://members_directory?community_id=%s&community_name=%s"
PINNED_ROUTE = "route://chatroom_pinned_feed?community_id=%s"
COMMUNITY_DETAILS_ROUTE = "route://community?community_id=%s"

CUSTOM_INTRO_TEXT_LEFT = "Left the community on %s"
CUSTOM_CLICK_TEXT_LEFT = "The profile you are trying to access does not exist. %s left the community on %s"
CUSTOM_INTRO_TEXT_DELETED = "Removed from the community on  %s"
CUSTOM_CLICK_TEXT_DELETED = "The profile you are trying to access does not exist. %s was removed from the community on %s"

CUSTOM_INTRO_TEXT_MEMBERSHIP_EXPIRED = "Profile does not exist"
CUSTOM_CLICK_TEXT_MEMBERSHIP_EXPIRED = "The profile you are trying to access does not exist. %s's membership expired on %s"

MEMBER_COMMUNITY_PROFILE_ROUTE = "route://member_community_profile?community_id=%s&member_id=%s"
MEMBER_SINCE_TEXT = "Member of %s since %s"

PENDING_MEMBER_TEXT = "Verification pending for %s"

CTA_ROUTE_DIRECT_MESSAGES = "route://direct_messages"
CTA_ROUTE_DIRECT_MESSAGES_COMMUNITY_DETAIL_SINGLE_CM = "route://direct_messages?chatroom_id={}"
CTA_ROUTE_DIRECT_MESSAGES_MEMBER_PROFILE = "route://direct_messages?chatroom_id={}&community_id={}"

COMMUNITY_FEED_ACTIONS = {
    "create_room": True,
    "create_poll": True,
    "create_event": True,
    "respond_in_rooms": True,
    "auto_approve": True,
    "create_secret_chatroom": True,
    "show_dm": True
}
