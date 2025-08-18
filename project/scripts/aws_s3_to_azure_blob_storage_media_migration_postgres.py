import os
import psycopg2
import boto3
import requests
from azure.storage.blob import BlobServiceClient
from urllib.parse import urlparse
from io import BytesIO

# --- CONFIG ---

CONFIG = {
    "user_account_profile_image": {
        "table": "togther_userinfo",
        "column": "image_url"
    },
    "user_community_profile_image": {
        "table": "togther_members",
        "column": "image_url"
    },
    "community_header_image": {
        "table": "togther_community",
        "column": "image_url"
    },
    "chatroom_media": {
        "table": "togther_card_attachment",
        "column": "file_url"
    },
    "chatroom_media_preview": {
        "table": "togther_card_attachment",
        "column": "thumbnail_url"
    },
    "poll_chatroom_images": {
        "table": "togther_collabcardpolls",
        "column": "image_url"
    },
    "conversation_media": {
        "table": "togther_answerattachment",
        "column": "file_url"
    },
    "conversation_media_preview": {
        "table": "togther_answerattachment",
        "column": "thumbnail_url"
    },
    "community_logo": {
        "table": "togther_community",
        "column": "image_link"
    },
    "community_logo_round": {
        "table": "togther_community",
        "column": "image_link_round"
    },
    "user_account_profile_image": {
        "table": "togther_userinfo",
        "column": "image_url"
    },
    "chatroom_images": {
        "table": "togther_collabcard",
        "column": "chatroom_image_url"
    },

}

AWS_REGION = "ap-south-1"
AZURE_CONNECTION_STRING = os.environ.get("AZURE_CONNECTION_STRING")
AZURE_CONTAINER = os.environ.get("AZURE_CONTAINER")

DB_CONFIG = {
    "host": os.environ.get("PG_HOST"),
    "port": os.environ.get("PG_PORT", 5432),
    "dbname": os.environ.get("PG_DATABASE"),
    "user": os.environ.get("PG_USER"),
    "password": os.environ.get("PG_PASSWORD")
}

# --- SETUP CLIENTS ---
s3 = boto3.client('s3', region_name=AWS_REGION)
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

# --- FUNCTIONS ---

def download_from_s3(s3_url):
    try : 
        parsed = urlparse(s3_url)
        # bucket = parsed.netloc.split('.')[0]
        # key = parsed.path.lstrip('/')
        filename = s3_url.split('/')[-1]

        response = requests.get(s3_url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch S3 object via public URL: {s3_url}")
        obj = {'Body': BytesIO(response.content)}
        return obj['Body'].read(), filename  # return data and original filename
    except Exception as e:
        raise Exception(f"Failed to download from S3: {e}")


def upload_to_azure_blob(blob_name, data_bytes):
    try : 
        blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER, blob=blob_name)
        blob_client.upload_blob(data_bytes, overwrite=True)
        return f"https://{blob_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER}/{blob_name}"
    except Exception as e:
        raise Exception(f"Failed to upload to Azure Blob Storage: {e}")


def process_table(cursor, conn, table, column):
    print(f"Processing table: {table}, column: {column}")
    
    # Fetch all rows with S3 URLs
    cursor.execute(f"SELECT id, {column} FROM {table} WHERE {column} LIKE 'https://%s3.amazonaws.com%' OR {column} LIKE 'https://%.s3.%amazonaws.com%';")
    rows = cursor.fetchall()

    for row in rows:
        row_id, s3_url = row
        try:
            print(f"  Syncing: {s3_url}")
            data, filename = download_from_s3(s3_url)
            azure_url = upload_to_azure_blob(filename, data)

            # Update row in DB
            cursor.execute(f"UPDATE {table} SET {column} = %s WHERE id = %s;", (azure_url, row_id))
            conn.commit()
            print(f"  Uploaded to Azure Blob Storage: {azure_url} at row_id {row_id}")
        except Exception as e:
            print(f"  Failed for {s3_url}: {e}")


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for key, value in CONFIG.items():
        process_table(cursor, conn, value['table'], value['column'])

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
