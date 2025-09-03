import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    This class loads up the environment variables for AutoExec
    """
    DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Google Drive and Sheets Configuration
    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")  
    EVENTS_SHEET_FILENAME = os.getenv("EVENTS_SHEET_FILENAME") 
    MEETING_MINS_FILENMAME = os.getenv("MEETING_MINS_FILENMAME") 
    MEETING_MINS_TEMPLATE_FILENMAME = os.getenv("MEETING_MINS_TEMPLATE_FILENMAME")
    MEETING_SCHEDULE_FILENAME = os.getenv("MEETING_SCHEDULE_FILENAME")
    MEETING_SCHEDULE_SPREADSHEET_ID = os.getenv("MEETING_SCHEDULE_SPREADSHEET_ID")
    MEETING_MINS_SCHEDULE_RANGE = os.getenv("MEETING_MINS_SCHEDULE_RANGE")

    # Google Calendar Configuration
    SHARED_CALENDAR_ID = os.getenv("SHARED_CALENDAR_ID")
    
    # Club Exec Task Manager Bot Configuration
    CLUB_NAME = os.getenv("CLUB_NAME", "Club")
    TIMEZONE = os.getenv("TIMEZONE", "America/Edmonton")
    TASK_REMINDER_CHANNEL_ID = int(os.getenv("TASK_REMINDER_CHANNEL_ID", 0))
    MEETING_REMINDER_CHANNEL_ID = int(os.getenv("MEETING_REMINDER_CHANNEL_ID", 0))
    ESCALATION_CHANNEL_ID = int(os.getenv("ESCALATION_CHANNEL_ID", 0))
    
    @staticmethod
    def validate():
        if not Config.DISCORD_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN is missing in .env")
        if not Config.OPENAI_API_KEY:
            # if the api key is outdated, run unset OPENAI_API_KEY in terminal
            raise EnvironmentError("OPENAI_API_KEY is missing in .env")
