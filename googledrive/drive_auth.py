import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# if modyfying these scopes, delete the old token.json
SCOPES = ["https://www.googleapis.com/auth/drive"]

# these are in my .env 
# these must be recreated if someone wants to run this project on their own environment
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"

def get_credentials():
    """ 
        Handles authentication and returns a Google Drive API service instance.

        Args:
            None
        Returns:
            The credentials for AutoExec linked to the current user
    """

    creds = None
    # check if old tokens exist (authentication has already been previously granetd)
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # if the credentials aren't valid or don't exist, update or create
    if not creds or not creds.valid:
        # just refresh if they're expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # if the user needs new creds, use the AutoExec credntials file to create some
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            # open up their browser and ask them to authenticate AutoExec
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    # return the valid creds
    return creds
def main():
    get_credentials()
    
if __name__ == "__main__":
    main()