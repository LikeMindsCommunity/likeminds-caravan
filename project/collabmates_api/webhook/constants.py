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
