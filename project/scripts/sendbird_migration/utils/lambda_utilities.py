import requests
from django.conf import settings

from ..constants import LAMBDA_URL

class LambdaUtilities:

    @staticmethod
    def migrate_to_s3(file_url, file_path) -> str:
        """
            file_url: str - URL of the file to be migrated
            file_path: str - Path where the file should be stored in S3

            Migrates the file to S3 and returns the public URL 
        """

        if not file_url:
            return ""

        headers = {
            "x-platform-type": "caravan-service"
        }

        payload = {
            "file_url": file_url,
            "file_path": file_path,
            "is_prod": False
        }
        
        if not settings.IS_BETA:
            payload["is_prod"] = True

        response = requests.put(LAMBDA_URL, json=payload, headers=headers)
        if response.status_code != 200:
            print(f"Error when migrating file to s3 for file_url: {file_url} & file_path: {file_path} | response: {response.json()}")
            return ""

        public_url = response.json().get("s3_url")

        return public_url
