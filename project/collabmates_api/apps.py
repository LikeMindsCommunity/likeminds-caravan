
from django.apps import AppConfig
import os

class CollabmatesApiConfig(AppConfig):
    name = 'collabmates_api'
    _connection_checks_run = False  # Class-level flag

    def ready(self):
        from django.conf import settings

        # In dev, run only in main process
        if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
            return

        # Prevent re-running even if ready() is called again (rare edge)
        if CollabmatesApiConfig._connection_checks_run:
            return

        CollabmatesApiConfig._connection_checks_run = True

        print("\n==> Running connection checks...\n")
        from .health_checks import check_postgres, check_redis, check_elasticsearch
        import threading
        threading.Thread(target=check_postgres).start()
        threading.Thread(target=check_redis).start()
        threading.Thread(target=check_elasticsearch).start()
