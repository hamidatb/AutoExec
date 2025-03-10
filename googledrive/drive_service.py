from googleapiclient.discovery import build

def get_drive_service(creds):
    """
    Returns an authenticated Google Drive service instance.
    """
    return build("drive", "v3", credentials=creds)

def get_latest_matching_file(service, folder_id, filename_filter):
    """
    Finds the most recent file matching the name filter in the given folder.
    """
    query = f"'{folder_id}' in parents and name contains '{filename_filter}'"

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
    print(files)
    return files