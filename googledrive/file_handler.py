import io
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build

from googledrive.drive_auth import get_credentials

from config import Config

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# get the environment vars from the configuration
Config()

FOLDER_ID = Config.DRIVE_FOLDER_ID # the folder the meeting mins are stored in
EVENTS_SHEET_FILENAME = Config.EVENTS_SHEET_FILENAME
MEETING_MINS_FILENMAME = Config.MEETING_MINS_FILENMAME

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

        print(f"🔍 Searching for latest matching file: {query}")
        print(f"📂 Searching in Google Drive folder: {folder_id}")

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
        
        print(f"✅ Found file: {files[0]}")
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