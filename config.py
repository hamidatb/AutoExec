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

    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")  
    EVENTS_SHEET_FILENAME = os.getenv("EVENTS_SHEET_FILENAME") 
    MEETING_MINS_FILENMAME = os.getenv("MEETING_MINS_FILENMAME") 
    MEETING_MINS_TEMPLATE_FILENMAME = os.getenv("MEETING_MINS_TEMPLATE_FILENMAME")
    
    @staticmethod
    def validate():
        if not Config.DISCORD_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN is missing in .env")
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is missing in .env")