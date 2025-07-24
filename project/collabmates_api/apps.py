import sys
from django.apps import AppConfig


class CollabmatesApiConfig(AppConfig):
    name = 'collabmates_api'


    def ready(self):
        print("Running connection checks...\n")
        from .health_checks import check_postgres, check_redis, check_elasticsearch
        import threading
        threading.Thread(target=check_postgres).start()
        threading.Thread(target=check_redis).start()
        threading.Thread(target=check_elasticsearch).start()