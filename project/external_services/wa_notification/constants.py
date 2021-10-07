"""
Constants for wa_notification based class
"""

WATI_NOTIFICATION_CONST = {
    'WATI_BROADCAST_URL': 'https://live-server-876.wati.io/api/v1/sendTemplateMessage?whatsappNumber=%s',
    'WATI_BROADCAST_SCHEMA': {
        "parameters": [
            {
                "name": "parameter name",
                "value": "parameter value",
            }
        ],
        "broadcast_name": "Broadcast name that you want to set | mandatory",
        "template_name": "Template name that was approved by whatsapp | mandatory"
    },
    'WATI_BROADCAST_METHOD': 'POST',
    'TEMPLATE_NAMES': {
        'EVENT_REMINDER': 'online_event_reminder_v1',
        'PAYMENT_PAGE_SUCCESS': 'payment_page_successfull_v1',
        'PAYMENT_PAGE_FAILED': 'failed_payment_member_v5',
    },
    'BROADCAST_NAMES': {
        'EVENT_REMINDER': 'event_reminder_core',
        'PAYMENT_PAGE_SUCCESS': 'payment_page_success',
        'PAYMENT_PAGE_FAILED': 'payment_page_failed'
    },
    'WATI_BROADCAST_BULK_URL': 'https://live-server-876.wati.io/api/v1/sendTemplateMessages',
    'WATI_BROADCAST_BULK_SCHEMA': {
        "receivers": [
            {
                "whatsappNumber": "Number on which message to be send",
                "customParams": [
                    {
                        "name": "parameter name",
                        "value": "parameter value",
                    }
                ]
            }
        ],
        "broadcast_name": "Broadcast name that you want to set | mandatory",
        "template_name": "Template name that was approved by whatsapp | mandatory"
    },
}
