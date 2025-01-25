# Lambda File - To be deployed in AWS Lambda to migrate files to Likmeinds S3

import json, os, boto3, requests

VALID_PLATFORM_TYPES = ["caravan-service"]
DOWNLOAD_PATH = "/tmp/temp-file"

# Update the following accordingly
S3_BUCKET_PROD = ""
S3_BUCKET_BETA = ""
S3_REGION = ""


def lambda_handler(event, context):
    print("event: ", event)

    file_url, object_key, is_prod, sendbird_api_token, err = validate_request_and_fetch_params(event)
    if err != "":
        print("Error in validation: ", err)
        return get_json_response(file_url, "", err)

    err = download_file_from_url(file_url, sendbird_api_token)
    if err != "":
        print("error download from s3: ", err)
        return get_json_response(file_url, "", err)

    s3_url, err = upload_file_to_s3(object_key, is_prod)
    if err != "":
        print("error uploading to s3: ", err)
        return get_json_response(file_url, s3_url, err)

    return get_json_response(file_url, s3_url, err)


def validate_request_and_fetch_params(event):
    headers, body = fetch_headers_body_from_event(event)

    file_url = body.get("file_url", "")
    object_key = body.get("object_key", "")
    sendbird_api_token = body.get("sendbird_api_token", "")

    is_prod = True if body.get("is_prod", False) is True else False

    if not (file_url and object_key):
        return "", "", "", sendbird_api_token, "both file_url & object_key is required"

    if headers["x-platform-type"] not in VALID_PLATFORM_TYPES:
        return "", "", "", sendbird_api_token, "Not Authorised"

    return file_url, object_key, is_prod, sendbird_api_token, "" 


def fetch_headers_body_from_event(event):
    try:
        event_body = event.get("body", "")
        body = json.loads(event_body)

    except Exception as e:
        body = {}

    headers = event.get("headers", {})
    return headers, body


def download_file_from_url(file_url, sendbird_api_token: str):
    try:
        headers = None

        if sendbird_api_token:
            headers = {}
            headers["Api-Token"] = sendbird_api_token

        response = requests.request("GET", file_url, headers=headers, stream=True)

        response.raise_for_status()

        with open(DOWNLOAD_PATH, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return ""

    except Exception as e:
        return str(e)


def upload_file_to_s3(object_key, is_prod):

    try:

        s3 = boto3.client("s3")
        bucket_name = S3_BUCKET_PROD if is_prod else S3_BUCKET_BETA

        s3.upload_file(
            DOWNLOAD_PATH, bucket_name, object_key, ExtraArgs={"ACL": "public-read"}
        )

        public_url = f"https://{bucket_name}.s3.{S3_REGION}.amazonaws.com/{object_key}"

        return public_url, ""

    except Exception as e:
        return "", str(e)

    finally:
        os.remove(DOWNLOAD_PATH)


def get_json_response(file_url, s3_url, err):
    json_response = {
        "statusCode": 200 if err == "" else 400,
        "body": {
            "file_url": file_url,
            "s3_url": s3_url,
            "error": err,
        },
    }

    print("json_response: ", json_response)

    return json_response
