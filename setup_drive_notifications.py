import os
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import pubsub_v1
import json

# Load service account credentials
SERVICE_ACCOUNT_FILE = "service-account.json"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/pubsub"
]
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# Create Drive API client
drive_service = build("drive", "v3", credentials=credentials)

# Get the Google Drive folder ID from the environment variables
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
print(f"📂 setup_drive_notifications.py: Checking Environment Variable: DRIVE_FOLDER_ID -> setup_drive_notifications.py")
if DRIVE_FOLDER_ID is None:
    print("❌ ERROR: DRIVE_FOLDER_ID is missing in the environment! -> setup_drive_notifications.py")
    exit(1)

# Pub/Sub topic where Drive will send events
PROJECT_ID = "active-alchemy-453323-f0"
PUBSUB_TOPIC_NAME = f"projects/{PROJECT_ID}/topics/autoExecPubSub"

def get_start_page_token():
    """ Get the latest Google Drive change token """
    response = drive_service.changes().getStartPageToken().execute()
    return response.get("startPageToken")

def poll_drive_changes():
    """ Poll for changes in the Google Drive folder and send to Pub/Sub """
    start_page_token = get_start_page_token()
    
    while True:
        # Get the list of changes from Drive
        changes = drive_service.changes().list(
            pageToken=start_page_token,
            fields="newStartPageToken, changes(fileId, file(name))"
        ).execute()

        # If there are changes, send them to Pub/Sub
        if "changes" in changes:
            for change in changes["changes"]:
                file_id = change["fileId"]
                file_name = change["file"]["name"]
                
                print(f"Detected change in Drive: {file_name} (ID: {file_id})")
                
                # Publish to Pub/Sub
                publish_drive_event(file_id, file_name)

        # Update the start page token
        if "newStartPageToken" in changes:
            start_page_token = changes["newStartPageToken"]

        # Wait before polling again
        time.sleep(10)

def publish_drive_event(file_id, file_name):
    """ Publish Google Drive changes to Pub/Sub """
    publisher = pubsub_v1.PublisherClient(credentials=credentials)
    topic_path = PUBSUB_TOPIC_NAME

    message_data = {
        "file_id": file_id,
        "file_name": file_name
    }

    message_json = json.dumps(message_data).encode("utf-8")
    try:
        future = publisher.publish(topic_path, message_json)
        message_id = future.result()
        print(f"✅ Successfully published to Pub/Sub: {message_data}, Message ID: {message_id}")
    except Exception as e:
        print(f"❌ ERROR publishing to Pub/Sub: {e}")

if __name__ == "__main__":
    print("Listening for Google Drive changes...")
    poll_drive_changes()
