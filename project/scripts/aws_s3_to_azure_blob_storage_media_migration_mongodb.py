

import os
from pymongo import MongoClient
from azure.storage.blob import BlobServiceClient
from urllib.parse import urlparse
import boto3
import requests
from io import BytesIO
from urllib.parse import urlparse, quote


# -------------------- CONFIG --------------------

# mongodb beta
MONGO_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("MONGODB_DATABASE")

COLLECTIONS_TO_PROCESS = [
    "post",
    # "comment",
]

AWS_REGION = "ap-south-1"

AZURE_CONNECTION_STRING = os.environ.get("AZURE_CONNECTION_STRING")
AZURE_CONTAINER = os.environ.get("AZURE_CONTAINER")

# -------------------- CLIENTS --------------------

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[DB_NAME]

s3 = boto3.client("s3", region_name=AWS_REGION)
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

# -------------------- FUNCTIONS --------------------


def encode_s3_url_path(url):
    parsed = urlparse(url)
    encoded_path = "/" + "/".join(quote(part) for part in parsed.path.lstrip("/").split("/"))
    return f"{parsed.scheme}://{parsed.netloc}{encoded_path}"

def download_from_s3(s3_url):

    try : 
        print(f"Downloading from S3: {s3_url}")
        filename = s3_url.split('/')[-1]
        response = requests.get(s3_url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch S3 object via public URL: {s3_url}")
        obj = {'Body': BytesIO(response.content)}
        return obj['Body'].read(), filename  # return data and original filename
    
    except Exception as e:
        raise Exception(f"Failed to download from S3: {e}")

def upload_to_azure(blob_name, data):
    try : 
        blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER, blob=blob_name)
        blob_client.upload_blob(data, overwrite=True)
        return f"https://{blob_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER}/{blob_name}"
    except Exception as e:
        raise Exception(f"Failed to upload to Azure Blob Storage: {e}")

def is_s3_url(url):
    return url and "amazonaws.com" in url

def process_collection(collection_name):
    print(f"\n--- Processing collection: {collection_name} ---")
    collection = mongo_db[collection_name]
    
    # Fetch only _ids first to avoid long-lived cursors
    id_cursor = collection.find({"attachments.attachment_meta.url": {"$regex": "s3.ap-south-1.amazonaws.com"}, "is_deleted": False}, {"_id": 1})
    ids = [doc["_id"] for doc in id_cursor]

    print(f"  Found {len(ids)} documents to process in {collection_name}")

    for doc_id in ids:
        doc = collection.find_one({"_id": doc_id})
        if not doc:
            continue
        updated = False
        new_attachments = []

        for att in doc.get("attachments", []):
            meta = att.get("attachment_meta", {})
            url = meta.get("url")
            thumbanil_url = meta.get("thumbnail_url")

            if url and is_s3_url(url):
                try:
                    url = encode_s3_url_path(url)  # Encode the S3 URL path
                    print(f"  Migrating: {url}")
                    data, filename = download_from_s3(url)
                    blob_name = f"{collection_name}/attachments.attachment_meta.url/{doc_id}/{filename}"
                    print(f"Structured blob name: {blob_name}")
                    azure_url = upload_to_azure(blob_name, data)
                    # azure_url = upload_to_azure(filename, data)
                    meta["url"] = azure_url
                    updated = True
                except Exception as e:
                    print(f"    ⚠️ Failed: {url} → {e}")

            # Handle thumbnail URL if it exists
            if thumbanil_url and is_s3_url(thumbanil_url):
                try : 
                    thumbanil_url = encode_s3_url_path(thumbanil_url)  # Encode the thumbnail URL path
                    print(f"  Migrating thumbnail: {thumbanil_url}")
                    thumb_data, thumb_filename = download_from_s3(thumbanil_url)
                    thumb_blob_name = f"{collection_name}/attachments.attachment_meta.thumbnail_url/{doc_id}/{thumb_filename}"
                    print(f"Structured thumbnail blob name: {thumb_blob_name}")
                    thumb_azure_url = upload_to_azure(thumb_blob_name, thumb_data)
                    meta["thumbnail_url"] = thumb_azure_url
                except Exception as e:
                    print(f"    ⚠️ Failed thumbnail: {thumbanil_url} → {e}")

            new_attachments.append(att)

        if updated:
            collection.update_one({"_id": doc["_id"]}, {"$set": {"attachments": new_attachments}})
            print(f"  ✅ Updated document {doc['_id']} in {collection_name}")

# -------------------- MAIN --------------------

if __name__ == "__main__":
    for coll in COLLECTIONS_TO_PROCESS:
        process_collection(coll)
