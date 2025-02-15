from utility.states import WebhookTypes

WEBHOOK_LIMIT = 5
MAX_WEBHOOK_RETRY_LIMIT = 3
MAX_WEBHOOK_USERS_META_LIMIT = 50

WEBHOOK_SOURCE_CHAT = "LM_CHAT"
WEBHOOK_SOURCE_FEED = "LM_FEED"

WEBHOOK_FAILURE_MAIL_SUBJECT = "Notification for webhook failure"
WEBHOOK_FAILURE_MAIL_BODY = """

Hey Team,<br>
{} webhook has failed on {}. <br>
Please inform the customer about the same.<br>

<h2>Here are the details:</h2>
<br>
Webhook URL: {}<br>
Webhook Failure Time: {}<br>
Webhook Status Code: {}<br>
Webhook Response: {}<br>
Webhook Payload:<br>
<code>
{}
</code>\
"""

WEBHOOK_TYPES_TITLE_MAP = {
    WebhookTypes.COMMUNITY_JOINED.value: {
        "name": "Community Joined",
        "category": "Community"
    },
    WebhookTypes.CHATROOM_JOINED.value: {
        "name": "Chatroom Joined",
        "category": "Chatroom"
    },
    WebhookTypes.CHATROOM_LEFT.value: {
        "name": "Community Left",
        "category": "Chatroom"
    },
    WebhookTypes.CHATROOM_USER_TAGGED.value: {
        "name": "User Tagged",
        "category": "Chatroom"
    },
    WebhookTypes.CHATROOM_CONVERSATION_REPLIED.value: {
        "name": "Conversation Replied",
        "category": "Chatroom"
    },
    WebhookTypes.PROFILE_CREATED.value: {
        "name": "Profile Created",
        "category": "Chatroom"
    },
    WebhookTypes.POST_CREATED.value: {
        "name": "Post Created",
        "category": "Feed"
    },
    WebhookTypes.POST_PINNED.value: {
        "name": "Post Pinned",
        "category": "Feed"
    },
    WebhookTypes.POST_LIKED.value: {
        "name": "Post Liked",
        "category": "Feed"
    },
    WebhookTypes.POST_TAGGED.value: {
        "name": "Post Tagged",
        "category": "Feed"
    },
    WebhookTypes.COMMENT_ADDED.value: {
        "name": "Comment Added",
        "category": "Feed"
    },
    WebhookTypes.COMMENT_TAGGED.value: {
        "name": "Comment Tagged",
        "category": "Feed"
    },
    WebhookTypes.COMMENT_REACT.value: {
        "name": "Comment Reacted",
        "category": "Feed"
    },
    WebhookTypes.NOTIFICATIONS_CHAT.value: {
        "name": "Chat Notifications",
        "category": "Chatroom"
    },
    WebhookTypes.NOTIFICATIONS_FEED.value: {
        "name": "Feed Notifications",
        "category": "Feed"
    },
    WebhookTypes.CHATROOM_MESSAGE_SENT.value: {
        "name": "Conversation Sent",
        "category": "Chatroom"
    },
    WebhookTypes.CHATROOM_MESSAGE_REACTED.value: {
        "name": "Conversation Reacted",
        "category": "Chatroom"
    },
    WebhookTypes.CHATROOM_MESSAGE_DELETED.value: {
        "name": "Conversation Deleted",
        "category": "Chatroom"
    },
    WebhookTypes.CHATROOM_POLL_CREATED.value: {
        "name": "Poll Created",
        "category": "Chatroom"
    },
}
