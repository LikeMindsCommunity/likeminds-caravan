from django.conf import settings

AIRTABLE_WEBHOOK_PROD = 'https://hooks.airtable.com/workflows/v1/genericWebhook/appb6t4SAoDF2gdpN/wfl2nAPWkipseGdJR/wtrtlsxBhIBMvm9zK'
AIRTABLE_WEBHOOK_BETA = 'https://hooks.airtable.com/workflows/v1/genericWebhook/appb6t4SAoDF2gdpN/wfl9ROVu0hA6shTZ9/wtrAPGD9XHMqJXPP2'
JOIN_DATA_WEBHOOK = AIRTABLE_WEBHOOK_BETA if settings.IS_BETA else AIRTABLE_WEBHOOK_PROD
