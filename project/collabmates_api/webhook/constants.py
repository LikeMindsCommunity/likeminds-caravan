WEBHOOK_LIMIT = 5
MAX_WEBHOOK_RETRY_LIMIT = 3
MAX_WEBHOOK_USERS_META_LIMIT = 50

WEBHOOK_SOURCE_CHAT = "LM_CHAT"
WEBHOOK_SOURCE_FEED = "LM_FEED"

WEBHOOK_CHATROOM_JOIN_SELF = "self_join"
WEBHOOK_CHATROOM_JOIN_ADDED_BY_CM = "added_by_cm"
WEBHOOK_CHATROOM_JOIN_AUTO_FOLLOW_CHATROOM = "auto_follow_chatroom"
WEBHOOK_CHATROOM_JOIN_CHANNEL_INVITE = "invite_join"
WEBHOOK_CHATROOM_COHORT_ADDED = "cohort_chatroom_added"
WEBHOOK_CHATROOM_TAGGED_JOIN = "tagged_join"

WEBHOOK_CHATROOM_LEAVE_SELF = "self_leave"
WEBHOOK_CHATROOM_LEAVE_REMOVED_BY_CM = "removed_by_cm"
WEBHOOK_CHATROOM_COHORT_CHATROOM_REMOVED = "cohort_chatroom_removed"

WEBHOOK_COMMUNITY_JOIN = "community_join"


WEBHOOK_FAILURE_MAIL_SUBJECT = "Notification for webhook failure"
WEBHOOK_FAILURE_MAIL_BODY = """
<h2>Hey Team</h2>
<br>
<h2>
Webhook Event type: '{}' for URL: <i>{}</i> has failed more than the maximum retry limit.
<br>
Hence the webhook has been set as Inactive.
<br>
Please check logs for more info.
</h2>
<br>
<h2>Webhook details:</h2> 
<br>
<code>
{}
</code>
<br>
<h3>Please inform the concerned team.<h3>
"""
