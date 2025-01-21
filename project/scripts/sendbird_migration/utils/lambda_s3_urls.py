# Lambda File - To be deployed in AWS Lambda to migrate files to Likmeinds S3

import json, os, time, boto3, requests
from urllib.parse import quote, urlparse

VALID_PLATFORM_TYPES = ["caravan-service"]
DOWNLOAD_PATH = "/tmp/"

# Update the following accordingly
S3_BUCKET_PROD = ""
S3_BUCKET_BETA = ""
S3_REGION = ""


def lambda_handler(event, context):
    print("event: ", event)

    file_url, file_path, is_prod, err, sendbird_api_token = validate_request_and_fetch_params(event)
    if err != "":
        print("Error in validation: ", err)
        return get_json_response(file_url, "", err)

    file_name, err = download_file_from_url(file_url, sendbird_api_token)
    if err != "":
        print("error download from s3: ", err)
        return get_json_response(file_url, "", err)

    s3_url, err = upload_file_to_s3(file_path, file_name, is_prod)
    if err != "":
        print("error uploading to s3: ", err)
        return get_json_response(file_url, s3_url, err)

    return get_json_response(file_url, s3_url, err)


def validate_request_and_fetch_params(event):
    headers, body = fetch_headers_body_from_event(event)

    file_url = body.get("file_url", "")
    file_path = body.get("file_path", "")
    sendbird_api_token = body.get("sendbird_api_token", "")

    is_prod = True if body.get("is_prod", False) is True else False

    if not (file_url and file_path):
        return "", "", "", "both file_url & file_path is required", sendbird_api_token

    if headers["x-platform-type"] not in VALID_PLATFORM_TYPES:
        return "", "", "", "Not Authorised", sendbird_api_token

    return file_url, file_path, is_prod, "", sendbird_api_token


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
        parsed_url = urlparse(file_url)
        file_name = os.path.basename(parsed_url.path)
        file_name = append_timestamp_before_extension(file_name)

        temp_path = DOWNLOAD_PATH + file_name

        headers = None

        if sendbird_api_token:
            headers = {}
            headers["Api-Token"] = sendbird_api_token

        response = requests.request("GET", file_url, headers=headers, stream=True)

        response.raise_for_status()

        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return file_name, ""

    except Exception as e:
        return "", str(e)


# To downlaod file from s3 bucket
def download_file_from_s3(file_url):
    try:
        s3 = boto3.client("s3")
        parsed_url = urlparse(file_url)
        bucket_name = parsed_url.netloc.split(".")[0]
        object_key = parsed_url.path.lstrip("/")

        file_name = os.path.basename(object_key)
        file_name = append_timestamp_before_extension(file_name)

        temp_path = DOWNLOAD_PATH + file_name

        s3.download_file(bucket_name, object_key, temp_path)

        return file_name, ""

    except Exception as e:
        return "", str(e)


def upload_file_to_s3(file_path, file_name, is_prod):
    temp_path = ""

    try:
        s3 = boto3.client("s3")
        bucket_name = S3_BUCKET_PROD if is_prod else S3_BUCKET_BETA
        object_key = f"{file_path}{quote(file_name, safe='')}" #TODO Confirm if this is correct and update in Lambda
        temp_path = DOWNLOAD_PATH + file_name

        s3.upload_file(
            temp_path, bucket_name, object_key, ExtraArgs={"ACL": "public-read"}
        )

        public_url = f"https://{bucket_name}.s3.{S3_REGION}.amazonaws.com/{object_key}"

        return public_url, ""

    except Exception as e:
        return "", str(e)

    finally:
        os.remove(temp_path)


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


def append_timestamp_before_extension(file_name):
    name, extension = os.path.splitext(file_name)
    current_time_ms = int(time.time() * 1000)
    new_file_name = f"{name}-{current_time_ms}{extension}"

    return new_file_name
