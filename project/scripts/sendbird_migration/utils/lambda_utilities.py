import requests
from django.conf import settings

from ..constants import LAMBDA_URL

class LambdaUtilities:

    @staticmethod
    def migrate_to_s3(file_url, file_path) -> str:

        payload = {
            "file_url": file_url,
            "file_path": file_path,
            "is_prod": False
        }
        
        if not settings.IS_BETA:
            payload["is_prod"] = True

        response = requests.post(LAMBDA_URL, json=payload)
        if response.status_code != 200:
            print(f"Error: {response.json()}")
            return ""

        public_url = response.json().get("s3_url")

        return public_url
