import io
from googleapiclient.http import MediaIoBaseDownload

def download_file(service, file) -> str:
    """
    Downloads the file that was found.
    Handles either google sheets or Google docs files.

    Args:   
        service: The Google drive instance
        file: The file that matched a query, that we want to download
    Returns:
        file_content: A string of the text content of the aformentioned file
    """
   # Process the latest file
    file_id = file["id"]
    file_name = file["name"]
    mime_type = file["mimeType"]
    
    # If the file is a Google Docs file, export it
    if mime_type == "application/vnd.google-apps.document":
        #print("Google Docs file detected. Exporting as plain text...")
        request_media = service.files().export_media(fileId=file_id, mimeType="text/plain")
    elif mime_type == "application/vnd.google-apps.spreadsheet":
        #print("Google Sheets file detected")
        request_media = service.files().export_media(fileId=file_id, mimeType="text/csv")
    else:
        print("AutoExec is intended to work with Google Sheets and Google Docs.\nPlease try again with the appropriate file format.")
        return -1

    # Read the file content
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_media)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        # if status:
            # print(f"Download {int(status.progress() * 100)}% complete.")

    # Decode file content as UTF-8
    file_content = fh.getvalue().decode("utf-8")
    return file_content
