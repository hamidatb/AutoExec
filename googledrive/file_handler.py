import io
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
from datetime import datetime

from .drive_auth import get_credentials

from config import Config

FOLDER_ID = Config.DRIVE_FOLDER_ID 
EVENTS_SHEET_FILENAME = Config.EVENTS_SHEET_FILENAME
MEETING_MINS_FILENMAME = Config.MEETING_MINS_FILENMAME
MEETING_MIN_TEMPLATE_FILENAME = Config.MEETING_MINS_TEMPLATE_FILENMAME
MEETING_SCHEDULE_FILENAME = Config.MEETING_SCHEDULE_FILENAME

class GoogleDriveHelper:
    """
    A helper class to interact with Google Drive and Google Sheets APIs.
    Provides methods to authenticate, find, and download files.
    """
    def __init__(self):
        """
        Initializes the Google Drive service using provided credentials.
        
        Args:
            None
        """
        creds = get_credentials()

        # Uses the scopes from googledrive.drive_auth
        services = self.get_drive_service(creds)
        self.drive_service = services[0]
        self.sheets_service = services[1]

        self.helperConfig = Config()

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
        Returns an authenticated Google Drive, and Google Sheets service instance.
        """
        drive_service = build("drive", "v3", credentials=creds)
        sheets_service = build("sheets", "v4", credentials=creds)

        return [drive_service, sheets_service]

    def get_latest_matching_file(self):
        """
        Finds the most recent file matching the name filter in the given folder.

        Args:
            folder_id (str): Google Drive folder ID.
            filename_filter (str): Partial file name to match.
        
        Returns:
            dict or None: File metadata if found, otherwise None.
        """
        folder_id = self.helperConfig.DRIVE_FOLDER_ID
        filename_filter = self.helperConfig.MEETING_MINS_FILENMAME

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
            results = self.drive_service.files().list(
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
            request_media = self.drive_service.files().export_media(fileId=file_id, mimeType="text/plain")
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            request_media = self.drive_service.files().export_media(fileId=file_id, mimeType="text/csv")
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
    
    def make_meeting_mins(self):
        """
        Makes a meeting minute document for the current date, through copying the template document, and updating the name of the file.

        Args:
            folder_id (str): Google Drive folder ID.
            template_filename (str): Partial file name to match.

        Returns:
            dict | None: Copied file metadata if successful, else None.
        """
        folder_id = self.helperConfig.DRIVE_FOLDER_ID
        template_filename = self.helperConfig.MEETING_MINS_TEMPLATE_FILENMAME

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
            results = self.drive_service.files().list(
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
            copied_file = self.drive_service.files().copy(
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

    def get_meeting_schedule_list(self, amount_to_return:int):
        """
        Gets the file content of the meeting schedule file, and returns the string

        Args:
            None
        Returns
            meetingScheduleContent (str): The string representation of the meeting schedule.
        """
        MEETING_MINS_SCHEDULE_RANGE = self.helperConfig. MEETING_MINS_SCHEDULE_RANGE
        
        try:
            # Call the Sheets API
            sheet = self.sheets_service.spreadsheets()
            result = (
                sheet.values()
                .get(spreadsheetId=self.helperConfig.MEETING_SCHEDULE_SPREADSHEET_ID, range=self.helperConfig.MEETING_MINS_SCHEDULE_RANGE)
                .execute()
            )
            values = result.get("values", [])

            if not values:
                print("No data found.")
                return

            all_meetings_list = []

            for row in values:
                try:
                    # convert date to a standard format (assuming the format is "Month Day")
                    meeting_date = datetime.strptime(row[0], "%B %d")  # Example: "March 20"
                    meeting_date = meeting_date.replace(year=datetime.today().year)  # Add current year

                    meeting_details = {
                        "date": meeting_date,  # storing as datetime for sorting l8r
                        "time": row[1],
                        "title": row[2],
                        "location": row[3],
                        "minutes": row[4]
                    }
                    all_meetings_list.append(meeting_details)

                except ValueError as val_err:
                    print(f"⚠️ Skipping invalid date format: {row[0]}. Error: {val_err}")

        

            # Sort meetings by date ( the nearest date comes first)
            all_meetings_list.sort(key=lambda x: x["date"])

            all_meetings_list = all_meetings_list[:amount_to_return]


        except Exception as e:
            print(f"❌ ERROR: Failed to fetch files from Drive. {e}")
            return None

        return all_meetings_list  

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
    # make a drive helper instance to use the credentials
    driveHelperInstance = GoogleDriveHelper()
    file = driveHelperInstance.get_latest_matching_file()
    
    if not file:
        print("No matching files found.")
        return

    #print(f"\nFound latest file: {file['name']} ({file['id']})")
    file_content = driveHelperInstance.download_file(file)

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
    # make a drive helper instance to use the credentials
    driveHelperInstance = GoogleDriveHelper()
    meetingMinsForTodayLink = driveHelperInstance.make_meeting_mins()
    
    if not meetingMinsForTodayLink:
        print("No matching files found.")
        return

    return meetingMinsForTodayLink

