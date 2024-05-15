import json
import os
from django.conf import settings
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleRequest
import requests

# URL for FCM endpoint
fcm_url = "https://fcm.googleapis.com/v1/projects/likeminds-sdk-app/messages:send"


class FCM_HTTP_V1_Notification():
    
    def __init__(self):
        self.firebase_service_account_json_path =  os.path.join(os.path.dirname(os.path.dirname(__file__)), settings.FIREBASE_SERVICE_ACCOUNT_JSON)
        self.access_token = self.generate_access_token()

    def generate_access_token(self):
        # Load the service account credentials from the JSON key file
        credentials = service_account.Credentials.from_service_account_file(self.firebase_service_account_json_path, scopes=['https://www.googleapis.com/auth/cloud-platform'])
        request = GoogleRequest()
        credentials.refresh(request)

        # print("Access token: ", credentials.token)
        return credentials.token

    def send_notification(self, data):
        # Set up headers
        fcm_headers = {
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json"
        }

        # Send the request
        response = requests.post(fcm_url, headers=fcm_headers, data=json.dumps(data))

        return response.json()
