import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleRequest
import requests

# URL for FCM endpoint
fcm_url = "https://fcm.googleapis.com/v1/projects/likeminds-sdk-app/messages:send"


class FCM_HTTP_V1_Notification():
    
    def __init__(self, service_account_file_dict):
        self.service_account_file_dict = service_account_file_dict
        self.access_token = self.generate_access_token()

    def generate_access_token(self):
        # Load the service account credentials from the JSON key file
        credentials = service_account.Credentials.from_service_account_info(self.service_account_file_dict, scopes=['https://www.googleapis.com/auth/cloud-platform'])
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
