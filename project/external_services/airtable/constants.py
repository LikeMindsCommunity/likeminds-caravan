from django.conf import settings
from utility.states import airtable_webhook_types

AIRTABLE_WEBHOOK_PROD = 'https://hooks.airtable.com/workflows/v1/genericWebhook/appb6t4SAoDF2gdpN/wfl2nAPWkipseGdJR/wtrtlsxBhIBMvm9zK'
AIRTABLE_WEBHOOK_BETA = 'https://hooks.airtable.com/workflows/v1/genericWebhook/appb6t4SAoDF2gdpN/wfl9ROVu0hA6shTZ9/wtrAPGD9XHMqJXPP2'
JOIN_DATA_WEBHOOK = AIRTABLE_WEBHOOK_BETA if settings.IS_BETA else AIRTABLE_WEBHOOK_PROD

APPROVE_REJECT_WEBHOOK = 'https://hooks.airtable.com/workflows/v1/genericWebhook/appb6t4SAoDF2gdpN/wflalG5aKXPDW0MIL/wtrZJQAmxxjASFdBV'

WEBHOOK_TYPES = {
    airtable_webhook_types.JOIN_COMMUNITY: JOIN_DATA_WEBHOOK,
    airtable_webhook_types.APPROVE_REQUEST: APPROVE_REJECT_WEBHOOK
}
