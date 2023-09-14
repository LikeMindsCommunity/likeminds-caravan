WEBHOOK_LIMIT = 5
MAX_WEBHOOK_RETRY_LIMIT = 3
MAX_WEBHOOK_USERS_META_LIMIT = 50

WEBHOOK_SOURCE_CHAT = "LM_CHAT"
WEBHOOK_SOURCE_FEED = "LM_FEED"

WEBHOOK_CHATROOM_JOIN_SELF = "self_join"
WEBHOOK_CHATROOM_JOIN_ADDED_BY_CM = "added_by_cm"
WEBHOOK_CHATROOM_JOIN_AUTO_FOLLOW_CHATROOM = "auto_follow_chatroom"
WEBHOOK_CHATROOM_JOIN_CHANNEL_INVITE = "invite_join"
WEBHOOK_CHATROOM_COHORT_JOIN = "cohort_join"
WEBHOOK_CHATROOM_TAGGED_JOIN = "tagged_join"

WEBHOOK_CHATROOM_LEAVE_SELF = "self_leave"
WEBHOOK_CHATROOM_LEAVE_REMOVED_BY_CM = "removed_by_cm"


WEBHOOK_FAILURE_MAIL_SUBJECT = "Notification for webhook failure"
WEBHOOK_FAILURE_MAIL_BODY = """
Hey Team,
{} for URL: {} has failed on {}.
Hence the webhook has been set as inactive
Please check logs for more info.

Webhook details: 
{}

Please inform the concerned team.
"""
