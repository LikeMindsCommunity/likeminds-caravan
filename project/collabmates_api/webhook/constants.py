WEBHOOK_LIMIT = 5
MAX_WEBHOOK_RETRY_LIMIT = 3
MAX_WEBHOOK_USERS_META_LIMIT = 50

WEBHOOK_SOURCE_CHAT = "LM_CHAT"
WEBHOOK_SOURCE_FEED = "LM_FEED"

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
