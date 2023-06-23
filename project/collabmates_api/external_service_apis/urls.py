from django.urls import path
from .external_service_apis_view_impl import *

urlpatterns = [
    path('send_email', SendEmailView.as_view(), name="send_email"),
    path('send_wa_bulk_messages', SendWhatsAppMessageView.as_view(), name="send_wa_bulk_message"),
    path('send_notifications', SendNotificationsView.as_view(), name="send_notifications"),
    path('crontab/<str:task_name>', RunCronJobView.as_view(), name="run_cron_jobs"),
    path('cache/warmup/<str:key_name>', WarmUpCacheView.as_view(), name="warm_up_cache"),
]
