import os
from google.oauth2 import service_account

# Scopes for Google Drive and Sheets access
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",  # Full access to Google Sheets
    "https://www.googleapis.com/auth/drive"         # Full access to Google Drive (all files)
]

# Path to service account key file
SERVICE_ACCOUNT_KEY_PATH = "googledrive/servicekey.json"

def get_credentials():
    """ 
        Handles authentication using service account and returns Google API credentials.
        Users only need to share specific folders with the service account.

        Args:
            None
        Returns:
            The service account credentials for AutoExec
    """
    
    try:
        # Use service account credentials
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_KEY_PATH, 
            scopes=SCOPES
        )
        return creds
        
    except FileNotFoundError:
        print(f"❌ Service account key file not found at: {SERVICE_ACCOUNT_KEY_PATH}")
        print("Please download the service account key for autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com")
        print("and save it as 'googledrive/servicekey.json'")
        raise
    except Exception as e:
        print(f"❌ Error loading service account credentials: {e}")
        raise

def main():
    get_credentials()
    
if __name__ == "__main__":
    main()