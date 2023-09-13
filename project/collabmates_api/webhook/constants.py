WEBHOOK_LIMIT = 5
MAX_WEBHOOK_RETRY_LIMIT = 3

WEBHOOK_FAILURE_MAIL_SUBJECT = "Notification for webhook failure"
WEBHOOK_FAILURE_MAIL_BODY = """
Hey Team,
{} for URLS: {} has failed on {}.
Hence the webhook has been set as inactive
Please check logs for more info.

Webhook details: 
{}

Please inform the concerned team.
"""
