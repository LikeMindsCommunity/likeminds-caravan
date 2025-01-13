import json
import os
import time
import boto3
from urllib.parse import quote, urlparse

# from constants import (
#     DOWNLOAD_PATH,
#     S3_BUCKET_PROD,
#     S3_BUCKET_BETA,
#     FILE_SIZE_LIMIT,
#     S3_REGION,
#     VALID_PLATFORM_TYPES,
# )


VALID_PLATFORM_TYPES = ["caravan", ]
DOWNLOAD_PATH = "/tmp/"
S3_BUCKET_PROD = "prod-media-bucket"
S3_BUCKET_BETA = "beta-media-bucket"
S3_REGION = "ap-south-1"

def lambda_handler(event, context):
    print("event: ", event)

    file_url, file_path, is_prod, err = validate_request_and_fetch_params(event)
    if err != "":
        print("Error in validation: ", err)
        return get_json_response(file_url, "", err)

    file_name, err = download_file_from_s3(file_url)
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

    is_prod = True if body.get("is_prod", False) is True else False

    if not (file_url or file_path):
        return "", "", "both file_url & file_path is required"

    if headers["x-platform-type"] not in VALID_PLATFORM_TYPES:
        return "", "", "Not Authorised"

    return file_url, file_path, is_prod, ""


def fetch_headers_body_from_event(event):
    try:
        event_body = event.get("body", "")
        body = json.loads(event_body)
    except Exception as e:
        body = {}

    headers = event.get("headers", {})
    return headers, body


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
    try:
        s3 = boto3.client("s3")
        bucket_name = S3_BUCKET_PROD if is_prod else S3_BUCKET_BETA
        object_key = f"{file_path}/{quote(file_name, safe='')}"
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
