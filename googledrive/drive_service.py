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
    if folder_id is None:
        print("❌ ERROR: folder_id is None. Check environment variables.")
        return -1

    if not filename_filter:
        print("❌ ERROR: filename_filter is empty or None.")
        return -1

    query = f"'{folder_id}' in parents"
    
    # Only add name filter if filename_filter is provided
    if filename_filter.strip():
        query += f" and name contains '{filename_filter.strip()}'"

    print(f"🔍 Get latest matching id query: {query}")
    print(f"📂 Searching in Google Drive folder: {folder_id}")

    try:
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, createdTime)",
            orderBy="createdTime desc",  # Sort by creation date, newest first
            pageSize=1,  # Get only the latest file
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
    except Exception as e:
        print(f"❌ ERROR: Failed to fetch files from Drive. {e}")
        return -1

    # Extract found files
    files = results.get("files", [])

    if not files:
        print("❌ No matching files found.")
        return -1  # Return -1 if there were no matching files
    
    print(f"✅ Found files: {files}")
    return files