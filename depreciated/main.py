from dotenv import load_dotenv

from googledrive.drive_auth import get_credentials
from googledrive.file_handler import GoogleDriveHelper

from config import Config

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# get the environment vars from the configuration
Config()

FOLDER_ID = Config.DRIVE_FOLDER_ID # the folder the meeting mins are stored in
EVENTS_SHEET_FILENAME = Config.EVENTS_SHEET_FILENAME
MEETING_MINS_FILENMAME = Config.MEETING_MINS_FILENMAME

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

    # make a drive helper instance to use the credentials
    driverHelperInstance = GoogleDriveHelper(creds)
    service = driverHelperInstance.get_drive_service()

    print("Searching for the most recent file matching filter...")

    files = driverHelperInstance.get_latest_matching_file(service, FOLDER_ID, MEETING_MINS_FILENMAME)
    file = files[0]
    
    if not file:
        print("No matching files found.")
        return

    print(f"\nFound latest file: {file['name']} ({file['id']})")
    file_content = driverHelperInstance.download_file(file)

    print("\nFile content:\n")
    print(f"{file_content}")

    return file_content

def main():
    """
    Main function to retrieve and print file content.
    """
    creds = get_credentials()

    # make a drive helper instance to use the credentials
    driverHelperInstance = GoogleDriveHelper(creds)
    service = driverHelperInstance.get_drive_service()

    print("Searching for the most recent file matching filter...")

    files = driverHelperInstance.get_latest_matching_file(service, FOLDER_ID, MEETING_MINS_FILENMAME)
    file = files[0]
    
    if not file:
        print("No matching files found.")
        return

    print(f"\nFound latest file: {file['name']} ({file['id']})")
    file_content = driverHelperInstance.download_file(file)

    print("\nFile content:\n")
    print(f"{file_content}")

if __name__ == "__main__":
    main()
