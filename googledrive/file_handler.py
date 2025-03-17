import io
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
from datetime import datetime

from googledrive.drive_auth import get_credentials

from config import Config

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# get the environment vars from the configuration
Config()

FOLDER_ID = Config.DRIVE_FOLDER_ID # the folder the meeting mins are stored in
EVENTS_SHEET_FILENAME = Config.EVENTS_SHEET_FILENAME
MEETING_MINS_FILENMAME = Config.MEETING_MINS_FILENMAME
MEETING_MIN_TEMPLATE_FILENAME = Config.MEETING_MINS_TEMPLATE_FILENMAME
MEETING_SCHEDULE_FILENAME = Config.MEETING_SCHEDULE_FILENAME

class GoogleDriveHelper:
    """
    A helper class to interact with Google Drive API.
    Provides methods to authenticate, find, and download files.
    """
    def __init__(self, creds):
        """
        Initializes the Google Drive service using provided credentials.
        
        Args:
            creds: Google API credentials object.
        """
        self.service = self.get_drive_service(creds)

    def validate_drive_fields(**options) -> bool:
        """
        Validates the fields passed into it
        """
        for field in options:
            if field == None:
                print(f"ERROR: Missing field in GoogleDrive Handler")
                return False
        return True

    def get_drive_service(self, creds):
        """
        Returns an authenticated Google Drive service instance.
        """
        return build("drive", "v3", credentials=creds)

    def get_latest_matching_file(self, folder_id: str, filename_filter: str):
        """
        Finds the most recent file matching the name filter in the given folder.

        Args:
            folder_id (str): Google Drive folder ID.
            filename_filter (str): Partial file name to match.
        
        Returns:
            dict or None: File metadata if found, otherwise None.
        """
        if not folder_id:
            print("❌ ERROR: folder_id is None. Check environment variables.")
            return None

        if not filename_filter.strip():
            print("❌ ERROR: filename_filter is empty or None.")
            return None

        query = f"'{folder_id}' in parents"
        if filename_filter.strip():
            query += f" and name contains '{filename_filter.strip()}'"

        #print(f"🔍 Searching for latest matching file: {query}")
        #print(f"📂 Searching in Google Drive folder: {folder_id}")

        try:
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, createdTime)",
                orderBy="createdTime desc",  # Sort by creation date, newest first
                pageSize=1,  # Get only the latest file
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()

        except Exception as e:
            print(f"❌ ERROR: Failed to fetch files from Drive. {e}")
            return None

        files = results.get("files", [])
        if not files:
            print("❌ No matching files found.")
            return None  # Return None if no files match
        
        #print(f"✅ Found file: {files[0]}")
        return files[0]  # Return the first (latest) file found

    def download_file(self, file: dict) -> str:
        """
        Downloads the file that was found and returns its content as a string.
        Handles Google Docs and Google Sheets files.

        Args:
            file (dict): The metadata of the file to download.
        
        Returns:
            str: The text content of the file.
        """
        if not file:
            print("❌ ERROR: No file provided for download.")
            return None

        file_id = file["id"]
        mime_type = file["mimeType"]

        if mime_type == "application/vnd.google-apps.document":
            request_media = self.service.files().export_media(fileId=file_id, mimeType="text/plain")
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            request_media = self.service.files().export_media(fileId=file_id, mimeType="text/csv")
        else:
            print("AutoExec is designed to work with Google Sheets and Google Docs only.\nPlease try again with an appropriate file format.")
            return None

        # Read the file content
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_media)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        # Decode file content as UTF-8
        file_content = fh.getvalue().decode("utf-8")
        return file_content
    
    def make_meeting_mins(self, folder_id:str, template_filename:str):
        """
        Makes a meeting minute document for the current date, through copying the template document, and updating the name of the file.

        Args:
            folder_id (str): Google Drive folder ID.
            template_filename (str): Partial file name to match.

        Returns:
            dict | None: Copied file metadata if successful, else None.
        """
        if not folder_id:
            print("❌ ERROR: folder_id is None. Check environment variables.")
            return None

        if not template_filename.strip():
            print("❌ ERROR: The template document is empty or None.")
            return None

        # Query for the latest file that matches the template filename
        query = f"'{folder_id}' in parents"
        if template_filename.strip():
            query += f" and name contains '{template_filename.strip()}'"

        try:
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, createdTime)",
                orderBy="createdTime desc",  # Sort by creation date, newest first
                pageSize=1,  # Get only the latest file
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()

            # get the remplate file
            files = results.get("files", None)
            if not files:
                print("❌ No matching meeting minute templates found.")
                return None  

            template_file = files[0]
            template_id = template_file["id"]

        except Exception as e:
            print(f"❌ ERROR: Failed to fetch the meeting minute template from Drive. {e}")
            return None

        # make a new filename with the curr date
        newFilename = f"Meeting Minutes - {datetime.today().strftime('%Y-%m-%d')}"

        # try copying the file
        try:
            copied_file = self.service.files().copy(
                fileId=template_id,
                body={
                    "name": newFilename,
                    "parents": [folder_id]  # ensuring the copied file remains in the same folder
                },
                supportsAllDrives=True
            ).execute()
            
            copied_file_id = copied_file["id"]
            file_link = f"https://drive.google.com/file/d/{copied_file_id}/view"

            print(f"✅ Successfully copied and renamed file: {copied_file['name']}")
            print(f"🔗 File Link: {file_link}")

            return file_link  # Return the shareable Google Drive link

        except Exception as e:
            print(f"❌ ERROR: Failed to copy the template document. {e}")
            return None

    def getNextMeeting(self, folder_id:str, meeting_schedule_filename:str):
        #TODO
        return None


# ---------------- Functions that use the drive helper class ----------------------
def getFileContentStr(filetype:int) -> str:
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
    file = driverHelperInstance.get_latest_matching_file(FOLDER_ID, MEETING_MINS_FILENMAME)
    
    if not file:
        print("No matching files found.")
        return

    #print(f"\nFound latest file: {file['name']} ({file['id']})")
    file_content = driverHelperInstance.download_file(file)

    #print("\nFile content:\n")
    #print(f"{file_content}")

    return file_content


def create_meeting_mins_for_today():
    """
    A function to create the meeting minutes for today in the Google drive folder, and then send back the link to that file.

    Args:
        None

    Returns:
        meetingMinLink (str): The link to the meeting minutes
    """
    creds = get_credentials()

    # make a drive helper instance to use the credentials
    driverHelperInstance = GoogleDriveHelper(creds)
    meetingMinsForTodayLink = driverHelperInstance.make_meeting_mins(FOLDER_ID, MEETING_MIN_TEMPLATE_FILENAME)
    
    if not meetingMinsForTodayLink:
        print("No matching files found.")
        return

    return meetingMinsForTodayLink


def get_next_meeting():
    """
    Returns the date of the next meeting, and None if there is no next meeting.

    Args:
        None
    Returns:
        nextMeetingDict (dict) -> The dictionary of the meeting minutes.
    """
    creds = get_credentials()

    driveHelperInstance = GoogleDriveHelper(creds)
    nextMeetingDict = driveHelperInstance.getNextMeeting(FOLDER_ID, MEETING_SCHEDULE_FILENAME)

    return nextMeetingDict