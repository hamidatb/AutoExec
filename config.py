import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    Configuration class for the Club Exec Task Manager Bot.
    Loads environment variables and provides validation.
    """
    
    # Discord Bot Configuration
    DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
    
    # OpenAI Configuration (if needed for future features)
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
    
    # Channel Configuration (can be set during setup)
    TASK_REMINDER_CHANNEL_ID = int(os.getenv("TASK_REMINDER_CHANNEL_ID", 0))
    MEETING_REMINDER_CHANNEL_ID = int(os.getenv("MEETING_REMINDER_CHANNEL_ID", 0))
    ESCALATION_CHANNEL_ID = int(os.getenv("ESCALATION_CHANNEL_ID", 0))
    
    # Bot Behavior Configuration
    REMINDER_CHECK_INTERVAL = int(os.getenv("REMINDER_CHECK_INTERVAL", 3600))  # 1 hour in seconds
    MEETING_REMINDER_INTERVAL = int(os.getenv("MEETING_REMINDER_INTERVAL", 300))  # 5 minutes in seconds
    TASK_ESCALATION_DELAY = int(os.getenv("TASK_ESCALATION_DELAY", 172800))  # 48 hours in seconds
    
    # Meeting Reminder Times (in hours before meeting)
    MEETING_REMINDER_2H = int(os.getenv("MEETING_REMINDER_2H", 2))
    MEETING_REMINDER_1H = int(os.getenv("MEETING_REMINDER_1H", 1))
    MEETING_REMINDER_30M = int(os.getenv("MEETING_REMINDER_30M", 0.5))
    
    # Task Reminder Times (in hours before deadline)
    TASK_REMINDER_24H = int(os.getenv("TASK_REMINDER_24H", 24))
    TASK_REMINDER_2H = int(os.getenv("TASK_REMINDER_2H", 2))
    
    @staticmethod
    def validate():
        """Validate that all required configuration is present."""
        missing_configs = []
        
        if not Config.DISCORD_TOKEN:
            missing_configs.append("DISCORD_BOT_TOKEN")
            
        if not Config.OPENAI_API_KEY:
            # OpenAI API key is optional for basic functionality
            pass
            
        if missing_configs:
            raise ValueError(f"Missing required configuration: {', '.join(missing_configs)}")
            
        print("✅ Configuration validation passed!")
        
    @staticmethod
    def get_timezone():
        """Get the configured timezone."""
        import pytz
        try:
            return pytz.timezone(Config.TIMEZONE)
        except pytz.exceptions.UnknownTimeZoneError:
            print(f"⚠️ Unknown timezone '{Config.TIMEZONE}', using UTC")
            return pytz.UTC
            
    @staticmethod
    def print_config():
        """Print current configuration (without sensitive data)."""
        print("🔧 **Bot Configuration**")
        print(f"Club Name: {Config.CLUB_NAME}")
        print(f"Timezone: {Config.TIMEZONE}")
        print(f"Task Reminder Channel: {Config.TASK_REMINDER_CHANNEL_ID}")
        print(f"Meeting Reminder Channel: {Config.MEETING_REMINDER_CHANNEL_ID}")
        print(f"Escalation Channel: {Config.ESCALATION_CHANNEL_ID}")
        print(f"Reminder Check Interval: {Config.REMINDER_CHECK_INTERVAL}s")
        print(f"Meeting Reminder Interval: {Config.MEETING_REMINDER_INTERVAL}s")
        print(f"Task Escalation Delay: {Config.TASK_ESCALATION_DELAY}s")
        print(f"Meeting Reminders: {Config.MEETING_REMINDER_2H}h, {Config.MEETING_REMINDER_1H}h, {Config.MEETING_REMINDER_30M}h before")
        print(f"Task Reminders: {Config.TASK_REMINDER_24H}h, {Config.TASK_REMINDER_2H}h before deadline")
