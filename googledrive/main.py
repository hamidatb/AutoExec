import os
import time
import io
from dotenv import load_dotenv

# since I'm using absolute imports, this script needs to be run from the autoexec root
from googledrive.auth import get_credentials
from googledrive.drive_service import get_drive_service, get_latest_matching_file
from googledrive.file_handler import download_file

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# get the environment vars
load_dotenv()

FOLDER_ID = os.getenv("DRIVE_FOLDER_ID") # the folder the meeting mins are stored in
EVENTS_SHEET_FILENAME = os.getenv("EVENTS_SHEET_FILENAME")
MEETING_MINS_FILENMAME = os.getenv("MEETING_MINS_FILENMAME") # the name format to look for 

def get_file(filetype:int) -> str:
    """
    Function to get the file content from the meeting minutes
    
    Args:
        Filetype flag to know what type of file to find.
        0 -> Looking for a google sheets file
        1 -> Looking got a meeting minutes file
    Returns:
        A string of the file content
    """
    creds = get_credentials()
    service = get_drive_service(creds)

    if filetype == 1:
        files = get_latest_matching_file(service, FOLDER_ID, MEETING_MINS_FILENMAME)
        file = files[0]
    
        if not file:
            print("No matching files found.")
            return

        file_content = download_file(service, file)

        # return the string of the file content here
        return file_content
    else:
        return None

def main():
    """
    Main function to retrieve and print file content.
    """
    creds = get_credentials()
    service = get_drive_service(creds)

    print("Searching for the most recent file matching filter...")

    files = get_latest_matching_file(service, FOLDER_ID, MEETING_MINS_FILENMAME)
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
