from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timedelta
from config import Config
import re

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = "googledrive/servicekey.json"

# Calendar API scopes (read-only access)
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

class googleCalendarHelper:
    """
    A helper class to manage all of the google calendar interactions with the gcal API.

    """
    def __init__(self):
        # Authenticate the bot with the service account
        self.calendar_creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )

        # Initialize the Google Calendar API client
        self.calender_service = build("calendar", "v3", credentials=self.calendar_creds)

        self.calendarConfig = Config()
        self.calendar_id = self.calendarConfig.SHARED_CALENDAR_ID


    def get_bot_invited_meeting_list(self, max_results:int):
        """
        Fetches upcoming events from Google Calendar where the bot is invited.
        
        Args:
            calendar_id (str): The calendar ID where the bot has access.
            max_results (int): The number of events to return.
        
        Returns:
            list: A list of upcoming events where the bot is invited.
        """
        now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time

        events_result = (
            self.calender_service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        print("Got to after the result was called")

        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return []

        meeting_list = []
        for event in events:
            attendees = event.get("attendees", [])
            
            # Check if the bot's service account email is an attendee
            bot_invited = any(
                attendee.get("email") == self.calendar_creds.service_account_email for attendee in attendees
            )
            
            if bot_invited:
                start_time = event["start"].get("dateTime", event["start"].get("date"))

                end_time = event["end"].get("dateTime", event["end"].get("date"))
                print(start_time, end_time)


                meeting_details = {
                    "date": start_time[:10],  # YYYY-MM-DD format
                    "start_time": start_time[11:16] if "T" in start_time else "All Day",
                    "end_time": end_time[11:16] if "T" in end_time else "All Day",  
                    "title": event.get("summary", "No Title"),
                    "location": event.get("location", "No Location Provided"),         
                }
                meeting_list.append(meeting_details)

        return meeting_list
    

def get_upcoming_meetings_list(max_meetings_to_return:int=2) -> list:
    """
    Gets a list of the upcoming meetings

    Args:
        None
    Returns:
        list: The list of upcoming meetings, each are a dictionary
    """
    calendar_helper_instance = googleCalendarHelper()
    meeting_list = calendar_helper_instance.get_bot_invited_meeting_list(max_meetings_to_return)

    return meeting_list

def get_formatted_meeting_schedule(meeting_list:list) -> str:
        """
        Formats the list of meetings
        """
        if not meeting_list:
            return "There are no upcoming meetings that AutoExec is invited to"
        
        formatted_meetings = "**📅 Upcoming Meetings:**\n"

        for meeting in meeting_list:
            formatted_meetings += (
                f"\n• **Date:** {meeting['date']} | **Time:** {meeting['start_time']} "
                f"\n    **Reason:** {meeting['title']}"
                f"\n    **Where:** {meeting['location']}"
            )
        return formatted_meetings



if __name__ == "__main__":
    meetings = get_upcoming_meetings_list()

    print("\n📅 Upcoming Meetings (Bot Invited):")
    if not meetings:
        print("🚫 No meetings where the bot is invited.")
    else:
        res = get_formatted_meeting_schedule(meetings)
        print(res)