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
    'TEMPLATE_NAMES':{
        'EVENT_REMINDER': 'online_event_reminder_v1'
    },
    'BROADCAST_NAMES':{
        'EVENT_REMINDER': 'event_reminder_core'
    }
}
