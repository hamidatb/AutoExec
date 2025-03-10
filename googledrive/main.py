import os
import time
import io
from dotenv import load_dotenv
from auth import get_credentials
from drive_service import get_drive_service, get_latest_matching_file
from file_handler import download_file

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# get the environment vars
load_dotenv()

FOLDER_ID = os.getenv("DRIVE_FOLDER_ID") # the folder the meeting mins are stored in
FILE_NAME_FILTER = os.getenv("DRIVE_FILE_NAME_FILTER") # the name format to look for 

def main():
    """
    Main function to retrieve and print file content.
    """
    creds = get_credentials()
    service = get_drive_service(creds)

    print("Searching for the most recent file matching filter...")

    files = get_latest_matching_file(service, FOLDER_ID, FILE_NAME_FILTER)
    file = files[0]
    
    if not file:
        print("No matching files found.")
        return

    print(f"\nFound latest file: {file['name']} ({file['id']})")
    file_content = download_file(service, file)

    print("\nFile content:\n")
    print(f"{file_content}")
    print("\nProgram completed successfully. Exiting.")

if __name__ == "__main__":
    main()
