from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timedelta

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = "googledrive/servicekey.json"

# Calendar API scopes (read-only access)
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Authenticate the bot with the service account
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# Initialize the Google Calendar API client
service = build("calendar", "v3", credentials=creds)

def get_bot_invited_events(calendar_id="primary", max_results=5):
    """
    Fetches upcoming events from Google Calendar where the bot is invited.
    
    Args:
        calendar_id (str): The calendar ID where the bot has access.
        max_results (int): The number of events to return.
    
    Returns:
        list: A list of upcoming events where the bot is invited.
    """
    now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    print(f"Calendar ID: {calendar_id}")

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])

    if not events:
        print("No upcoming events found.")
        return []

    meeting_list = []
    for event in events:
        attendees = event.get("attendees", [])
        
        # Check if the bot's service account email is an attendee
        bot_invited = any(
            attendee.get("email") == creds.service_account_email for attendee in attendees
        )
        
        if bot_invited:
            start_time = event["start"].get("dateTime", event["start"].get("date"))
            meeting_details = {
                "date": start_time[:10],  # YYYY-MM-DD format
                "time": start_time[11:16] if "T" in start_time else "All Day",
                "title": event.get("summary", "No Title"),
                "location": event.get("location", "No Location Provided"),  # ✅ Fetch Location
                "description": event.get("description", "No Description"),  # ✅ Fetch Description
    
            }
            meeting_list.append(meeting_details)

    return meeting_list

if __name__ == "__main__":
    calendar_id = "92d67297c1e478b124a00ce743806fc2e7358949955a8da08a4a5a747e1aceb9@group.calendar.google.com"  # Replace with your bot's shared calendar ID
    meetings = get_bot_invited_events(calendar_id)

    print("\n📅 Upcoming Meetings (Bot Invited):\n")
    if meetings:
        for meeting in meetings:
            print(f"• **{meeting['date']}** at {meeting['time']} - **{meeting['title']}**")
            print(f"  📍 Location: {meeting['location']}")
            print(f"  📝 Description: {meeting['description']}\n")
    else:
        print("🚫 No meetings where the bot is invited.")