import os
import time
import io
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from auth import get_credentials

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# get the environment vars
load_dotenv()

FOLDER_ID = os.getenv("DRIVE_FOLDER_ID") # the folder the meeting mins are stored in
FILE_NAME_FILTER = os.getenv("DRIVE_FILE_NAME_FILTER") # the name format to look for 

def search_for_file(creds:Credentials) -> list :
    # create a goog drive api service instance using the credentials 
    service = build("drive", "v3", credentials=creds)

    print("Searching for the most recent file matching filter...")
    # search for files in the specified folder that match the filter, sorted by creation date (newest first).
    query = f"'{FOLDER_ID}' in parents and name contains '{FILE_NAME_FILTER}'"
    
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, createdTime)",
        orderBy="createdTime desc",  # Sort by creation date, newest first
        pageSize=1,  # Get only the latest file
        includeItemsFromAllDrives=True,
        supportsAllDrives=True
    ).execute()

    # items are what was found
    files = results.get("files", [])

    if not files:
        print("No matching files found.")
        return -1 # -1 if the there were no matching files
    
    return files, service

def get_file_content(items, service):
    # Process the latest file
    file = items[0]
    file_id = file["id"]
    file_name = file["name"]
    mime_type = file["mimeType"]
    
    print(f"\nFound latest file: {file_name} ({file_id})")

    # If the file is a Google Docs file, export it
    if mime_type == "application/vnd.google-apps.document":
        print("Google Docs file detected. Exporting as plain text...")
        request_media = service.files().export_media(fileId=file_id, mimeType="text/plain")
    else:
        print("AutoExec is intented to work with Google Docs specifically.")
        return -1

    # Read the file content
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_media)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"Download {int(status.progress() * 100)}% complete.")

    # Decode file content as UTF-8
    file_content = fh.getvalue().decode("utf-8")
    print("\nFile content:\n")
    print(file_content)

def main():
    """
    Finds the most recent Google Drive file matching the name filter, prints its content, and then exits.
    
    Eventually this will pass on info to the agent

    Args:
        None
    Returns:
        None
    """
    # Load or request credentials.
    creds = get_credentials()

    try:
        items, service = search_for_file(creds)
        if items == -1:
            return # found nothing

        gotContentSuccess = get_file_content(items, service)
        if gotContentSuccess == -1:
            return 

        print("\n Program completed successfully. Exiting.")
        return  # Exit the program

    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    main()
