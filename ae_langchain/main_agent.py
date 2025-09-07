"""
This is the file to run the agent from.
It will intialize the discord bot on startup, and any messages to the bot are routed through this agent.
"""
import os
import asyncio
from asyncio import create_task
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent, tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI 

from googledrive.file_handler import create_meeting_mins_for_today

from config import Config
import datetime

# Load environment variables
Config().validate()

# if the api key is outdated, run unset OPENAI_API_KEY in terminal
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("API Key not found. Check your .env file!")

# Global variable for pending announcements
_pending_announcements = []

@tool 
def start_discord_bot():
    """
    Starts the Discord bot asynchronously, allowing the LangChain agent to remain active.

    Args:
        None
    Returns:
        str: Confirmation message that the bot was started.
    """
    from discordbot.discord_client import run_bot

    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(run_bot())  # Run bot as async task in existing event loop
    else:
        asyncio.run(run_bot())  # Run bot in a new event loop if none is running

    return "✅ Discord bot has been started and is now running!"

@tool
def send_meeting_mins_summary():
    """
    Must return the FULL formatted string from this as your response if the users question asked for the meeting minutes or said $AEmm. 

    Args:
        None
    Returns:
        str: Confirmation message that the bot was started.
    """
    from discordbot.discord_client import BOT_INSTANCE

    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."

    # Run the message-sending function inside the bot event loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        #print("The loop is already running")
        loop.create_task(BOT_INSTANCE.send_meeting_minutes())  # Use existing bot instance
    else:
        asyncio.run(BOT_INSTANCE.send_meeting_minutes())  # Create new loop if needed

    return "✅ Meeting minutes have been sent via Discord."

@tool
def create_meeting_mins() -> str:
    """
    Creates the meeting minute document for today 
    and returns the link the minutes, which should be sent to Discord afterwards using send_output_to_discord()

    Args:
        None
    Returns:
        The meeting minute link (str)
    """
    meetingMinsLink = create_meeting_mins_for_today()
    if not meetingMinsLink:
        print("There was an error in creating the meeting minutes")
        return "There was an error in creating the meeting minutes"
    else:
        return meetingMinsLink

@tool
def send_output_to_discord(messageToSend:str) -> str:
    """
    Sends a message directly to the Discord chat on behalf of the bot.

    **MANDATORY USAGE**: 
    - If a user asks the AI a direct question that doesn't trigger another tool, this function MUST be used.
    - Always call this function when responding to general questions in Discord.
    - NEVER answer in plain text without using this function when interacting in Discord.

    Args:
        messageToSend (str): The response message to send.

    Returns:
        str: A confirmation that the message was sent.
    """
    from discordbot.discord_client import BOT_INSTANCE

    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."

    # Since we're running in a thread pool, we can't directly send Discord messages
    # Instead, we'll use a thread-safe approach by storing the message to be sent
    # and returning a response that indicates the message should be sent
    
    # Store the message in a global variable that works across threads
    global _pending_announcements
    
    _pending_announcements.append({
        'message': str(messageToSend),
        'channel_id': None,  # Will use last_channel_id
        'channel_name': 'current channel'
    })
    
    return "✅ Message has been queued for Discord."

@tool
def send_meeting_schedule(amount_of_meetings_to_return: int):
    """
    Retrieves a formatted string representation of the upcoming few meetings from Google Sheets.

    **This function REQUIRES an argument. It will raise an error if none is provided.**

    Args:
        amount_of_meetings_to_return (int): The number of meetings to return (REQUIRED).
        
    Returns:
        str: Formatted meeting schedule information to be sent to Discord.
    """
    # Ensure an argument is provided
    if amount_of_meetings_to_return is None:
        raise ValueError("❌ ERROR: 'amount_of_meetings_to_return' is REQUIRED but was not provided. Please try again")

    # Get meetings from Google Sheets using the bot's meeting manager
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    # Get the current guild's club configuration
    # We need to get the guild ID from the current context
    # For now, we'll try to get meetings from the first available guild config
    meetings_info = "📅 **Upcoming Meetings:**\n\n"
    
    try:
        # Get guild configurations from the setup manager instead of bot.club_configs
        print(f"🔍 [DEBUG] Getting guild configurations from setup manager")
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        print(f"🔍 [DEBUG] Found {len(all_guilds) if all_guilds else 0} guild configurations")
        
        if not all_guilds:
            meetings_info += "❌ **No club configuration found.**\n\n"
            meetings_info += "**Possible causes:**\n"
            meetings_info += "• The guild_setup_status.json file was deleted or corrupted\n"
            meetings_info += "• The setup process was never completed\n"
            meetings_info += "• Permission issues accessing the configuration file\n\n"
            meetings_info += "**Solution:** Please run `/setup` to configure the bot for your server."
            return meetings_info
        
        # Get meetings from the first available guild (in a real scenario, we'd get the current guild)
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                # Get the meetings sheet ID from the monthly_sheets structure
                meetings_sheet_id = None
                if 'monthly_sheets' in guild_config and 'meetings' in guild_config['monthly_sheets']:
                    meetings_sheet_id = guild_config['monthly_sheets']['meetings']
                elif 'meetings_sheet_id' in guild_config:
                    meetings_sheet_id = guild_config['meetings_sheet_id']
                
                if meetings_sheet_id:
                    print(f"🔍 [DEBUG] Getting meetings from sheet ID: {meetings_sheet_id}")
                    
                    try:
                        # Get upcoming meetings using the meeting manager
                        upcoming_meetings = BOT_INSTANCE.meeting_manager.get_upcoming_meetings(
                            meetings_sheet_id, 
                            limit=amount_of_meetings_to_return
                        )
                        
                        print(f"🔍 [DEBUG] Found {len(upcoming_meetings) if upcoming_meetings else 0} upcoming meetings")
                        
                        if not upcoming_meetings:
                            meetings_info += "📅 **No upcoming meetings scheduled.**\n\n"
                            meetings_info += "Use `/meeting set` to schedule a new meeting."
                        else:
                            for meeting in upcoming_meetings:
                                title = meeting.get('title', 'Untitled Meeting')
                                start_time = meeting.get('start_at_local', meeting.get('start_at_utc', 'Time TBD'))
                                location = meeting.get('location', 'Location TBD')
                                meeting_link = meeting.get('meeting_link', '')
                                
                                meetings_info += f"**{title}**\n"
                                meetings_info += f"🕐 {start_time}\n"
                                meetings_info += f"📍 {location}\n"
                                if meeting_link:
                                    meetings_info += f"🔗 {meeting_link}\n"
                                meetings_info += "\n"
                    except Exception as sheet_error:
                        print(f"❌ [ERROR] Failed to get meetings from Google Sheets: {sheet_error}")
                        meetings_info += f"❌ **Error retrieving meetings from Google Sheets:**\n"
                        meetings_info += f"Error: {str(sheet_error)}\n\n"
                        meetings_info += "**Possible causes:**\n"
                        meetings_info += "• Google Sheets file was deleted or moved\n"
                        meetings_info += "• Permission issues with the spreadsheet\n"
                        meetings_info += "• Network connectivity issues\n\n"
                        meetings_info += "**Solution:** Please run `/setup` again to reconfigure the meeting spreadsheet."
                    break
        else:
            meetings_info += "❌ No meetings spreadsheet configured. Please run `/setup` first."
            
    except Exception as e:
        print(f"Error getting upcoming meetings: {e}")
        meetings_info += f"❌ Error retrieving meetings: {str(e)}"
    
    return meetings_info
    
@tool
def send_reminder_for_next_meeting():
    """
    Send a message in Discord reminding everyone about the upcoming meeting.
    """

    # Get meetings from Google Sheets instead of Calendar
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    # This would need to be implemented to get meetings from Google Sheets
    formatted_meeting_reminder = """
        Hi @everyone! Meeting reminders are now managed through Google Sheets.
        
        Use `/meeting upcoming` to see scheduled meetings.
        Meeting reminders are sent automatically based on the schedule in Google Sheets.
    """

    send_output_to_discord(formatted_meeting_reminder)

    return "The reminder for our nearest meeting has now been sent to Discord"

@tool
def cleanup_past_meetings():
    """
    Clean up meetings that were scheduled for past dates (likely due to parsing errors).
    This helps fix issues where meetings were scheduled for wrong years.
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime, timezone
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ No club configuration found. Please run `/setup` first."
        
        cleaned_count = 0
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                # Get the meetings sheet ID
                meetings_sheet_id = None
                if 'monthly_sheets' in guild_config and 'meetings' in guild_config['monthly_sheets']:
                    meetings_sheet_id = guild_config['monthly_sheets']['meetings']
                elif 'meetings_sheet_id' in guild_config:
                    meetings_sheet_id = guild_config['meetings_sheet_id']
                
                if meetings_sheet_id:
                    # Get all meetings
                    all_meetings = BOT_INSTANCE.meeting_manager.sheets_manager.get_all_meetings(meetings_sheet_id)
                    now = datetime.now(timezone.utc)
                    
                    for meeting in all_meetings:
                        if meeting.get('start_at_utc'):
                            try:
                                start_time = datetime.fromisoformat(meeting['start_at_utc'])
                                # If meeting is more than 1 year old, mark as cancelled
                                if start_time.year < now.year - 1:
                                    meeting_id = meeting.get('meeting_id')
                                    if meeting_id:
                                        success = BOT_INSTANCE.meeting_manager.cancel_meeting(meeting_id, meetings_sheet_id)
                                        if success:
                                            cleaned_count += 1
                            except ValueError:
                                continue
        
        if cleaned_count > 0:
            return f"✅ **Cleanup Complete**\n\nCleaned up {cleaned_count} meetings that were scheduled for past dates.\n\n**Note:** These were likely scheduling errors where meetings were scheduled for wrong years."
        else:
            return "✅ **No cleanup needed**\n\nAll meetings are scheduled for appropriate dates."
            
    except Exception as e:
        return f"❌ Error during cleanup: {str(e)}"

@tool
def get_meeting_reminder_info():
    """
    Get information about the next upcoming meeting for display purposes.
    Use this when users ask about meeting reminders or upcoming meetings.
    """

    try:
        # Get meetings from Google Sheets instead of Calendar
        from discordbot.discord_client import BOT_INSTANCE
        
        if BOT_INSTANCE is None:
            return "❌ ERROR: The bot instance is not running."
        
        # Get actual meeting reminder information from Google Sheets
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ No club configuration found. Please run `/setup` first."
        
        # Get the next upcoming meeting for reminder info
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                # Get the meetings sheet ID from the monthly_sheets structure
                meetings_sheet_id = None
                if 'monthly_sheets' in guild_config and 'meetings' in guild_config['monthly_sheets']:
                    meetings_sheet_id = guild_config['monthly_sheets']['meetings']
                elif 'meetings_sheet_id' in guild_config:
                    meetings_sheet_id = guild_config['meetings_sheet_id']
                
                if meetings_sheet_id:
                    # Get the next upcoming meeting
                    upcoming_meetings = BOT_INSTANCE.meeting_manager.get_upcoming_meetings(
                        meetings_sheet_id, 
                        limit=1
                    )
                    
                    if upcoming_meetings:
                        meeting = upcoming_meetings[0]
                        title = meeting.get('title', 'Untitled Meeting')
                        start_time = meeting.get('start_at_local', meeting.get('start_at_utc', 'Time TBD'))
                        location = meeting.get('location', 'Location TBD')
                        meeting_link = meeting.get('meeting_link', '')
                        
                        reminder_info = f"""📅 **Next Meeting Reminder:**

**{title}**
🕐 {start_time}
📍 {location}
{f"🔗 {meeting_link}" if meeting_link else ""}

**Automatic reminders are sent at:**
• T-2 hours before the meeting
• T-0 (meeting start time)

**To schedule a new meeting:**
• Use `/meeting set` with title, start time, location, and meeting link
• Or ask me: "Schedule a meeting for tomorrow at 2pm about project updates"
"""
                    else:
                        reminder_info = """📅 **Meeting Reminders:**

**No upcoming meetings scheduled.**

**To schedule a meeting:**
• Use `/meeting set` with title, start time, location, and meeting link
• Or ask me: "Schedule a meeting for tomorrow at 2pm about project updates"

**Automatic reminders:**
• Meeting reminders are sent automatically at T-2h and T-0 (meeting start time)
"""
                    break
        else:
            reminder_info = "❌ No meetings spreadsheet configured. Please run `/setup` first."
        
        return reminder_info
        
    except Exception as e:
        return f"I encountered an error getting meeting information: {str(e)}"

@tool
def schedule_meeting(meeting_title: str, start_time: str, location: str = "", meeting_link: str = "") -> str:
    """
    Schedule a new meeting and add it to the Google Sheets.
    
    Args:
        meeting_title (str): The title of the meeting (REQUIRED)
        start_time (str): The start time in format "YYYY-MM-DD HH:MM" (REQUIRED)
        location (str): The meeting location or description (optional)
        meeting_link (str): The meeting link (Zoom, Teams, etc.) (optional)
        
    Returns:
        str: Confirmation message about the scheduled meeting
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime, timezone, timedelta
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ No club configuration found. Please run `/setup` first."
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                # Get the meetings sheet ID from the monthly_sheets structure
                meetings_sheet_id = None
                if 'monthly_sheets' in guild_config and 'meetings' in guild_config['monthly_sheets']:
                    meetings_sheet_id = guild_config['monthly_sheets']['meetings']
                elif 'meetings_sheet_id' in guild_config:
                    meetings_sheet_id = guild_config['meetings_sheet_id']
                
                if not meetings_sheet_id:
                    return "❌ No meetings spreadsheet configured. Please run `/setup` first."
                
                # Parse start time
                try:
                    start_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
                    
                    # Check if the date is in the past (likely a parsing error)
                    now = datetime.now()
                    if start_datetime.year < now.year or (start_datetime.year == now.year and start_datetime < now):
                        return f"❌ **Invalid Date:** The scheduled date ({start_datetime.strftime('%B %d, %Y')}) is in the past.\n\n**Current date:** {now.strftime('%B %d, %Y')}\n\n**Please use a future date.**\n\n**Examples:**\n• Tomorrow: `{datetime.now().strftime('%Y-%m-%d')} 14:00`\n• Next week: `{(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')} 14:00`"
                    
                    start_datetime = start_datetime.replace(tzinfo=timezone.utc)
                except ValueError:
                    return "❌ Invalid start time format. Please use YYYY-MM-DD HH:MM format."
                
                # Create meeting data
                meeting_data = {
                    'title': meeting_title,
                    'start_at_utc': start_datetime.isoformat(),
                    'end_at_utc': None,
                    'start_at_local': start_datetime.strftime("%B %d, %Y at %I:%M %p"),
                    'end_at_local': None,
                    'location': location or '',
                    'meeting_link': meeting_link or '',
                    'channel_id': '',  # Will be set by the meeting manager
                    'created_by': 'langchain_agent'
                }
                
                # Schedule meeting
                print(f"🔍 [DEBUG] Scheduling meeting '{meeting_title}' to sheet ID: {meetings_sheet_id}")
                print(f"🔍 [DEBUG] Meeting data: {meeting_data}")
                
                try:
                    import asyncio
                    success = asyncio.run(BOT_INSTANCE.meeting_manager.schedule_meeting(
                        meeting_data, 
                        meetings_sheet_id
                    ))
                    
                    print(f"🔍 [DEBUG] Meeting scheduling result: {success}")
                    
                    if success:
                        return f"✅ Meeting '{meeting_title}' scheduled successfully!\n\n**Details:**\n🕐 {meeting_data['start_at_local']}\n📍 {location if location else 'Location TBD'}\n{f'🔗 {meeting_link}' if meeting_link else ''}\n\nMeeting has been added to your Google Sheets and automatic reminders will be sent."
                    else:
                        return "❌ Failed to schedule meeting. The meeting manager returned False. Please try again or use `/meeting set` command."
                        
                except Exception as schedule_error:
                    print(f"❌ [ERROR] Exception during meeting scheduling: {schedule_error}")
                    return f"❌ **Error scheduling meeting:**\n\nError: {str(schedule_error)}\n\n**Possible causes:**\n• Google Sheets file was deleted or moved\n• Permission issues with the spreadsheet\n• Network connectivity issues\n• Invalid meeting data format\n\n**Solution:** Please run `/setup` again to reconfigure the meeting spreadsheet, or use `/meeting set` command."
                
                break
        else:
            return "❌ No meetings spreadsheet configured. Please run `/setup` first."
            
    except Exception as e:
        print(f"Error scheduling meeting: {e}")
        return f"❌ Error scheduling meeting: {str(e)}"

@tool
def send_announcement(announcement_message: str, announcement_type: str = "general") -> str:
    """
    Send an announcement message to Discord to the appropriate channel based on the type.
    Use this for meeting reminders, general announcements, or any other messages.
    
    Args:
        announcement_message (str): The announcement message to send (REQUIRED)
        announcement_type (str): Type of announcement - "meeting", "task", "general", or "escalation" (optional, defaults to "general")
        
    Returns:
        str: Confirmation that the announcement was sent
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ No club configuration found. Please run `/setup` first."
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                # Determine which channel to send to based on announcement type
                channel_id = None
                channel_name = ""
                
                if announcement_type.lower() == "meeting":
                    channel_id = guild_config.get('meeting_reminders_channel_id')
                    channel_name = "meeting reminders"
                elif announcement_type.lower() == "task":
                    channel_id = guild_config.get('task_reminders_channel_id')
                    channel_name = "task reminders"
                elif announcement_type.lower() == "escalation":
                    channel_id = guild_config.get('escalation_channel_id')
                    channel_name = "escalation"
                else:  # general or default
                    # For general announcements, use meeting reminders channel as default
                    channel_id = guild_config.get('meeting_reminders_channel_id')
                    channel_name = "general announcements"
                
                if not channel_id:
                    return f"❌ No {channel_name} channel configured. Please run `/setup` first."
                
                # Send the announcement to the specific channel with @everyone tag
                formatted_message = f"@everyone 📢 **{announcement_type.upper()} ANNOUNCEMENT**\n\n{announcement_message}"
                
                # Since we're running in a thread pool, we can't directly send Discord messages
                # Instead, we'll use a thread-safe approach by storing the message to be sent
                # and returning a response that indicates the message should be sent
                
                # Store the message in a global variable that works across threads
                global _pending_announcements
                print(f"🔍 [send_announcement] Using global pending_announcements list")
                
                announcement_data = {
                    'message': formatted_message,
                    'channel_id': int(channel_id),
                    'channel_name': channel_name
                }
                _pending_announcements.append(announcement_data)
                print(f"🔍 [send_announcement] Added announcement to global queue. Total pending: {len(_pending_announcements)}")
                print(f"🔍 [send_announcement] Announcement data: {announcement_data}")
                
                return f"✅ Announcement queued for {channel_name} channel!\n\n**Message to be sent:**\n{formatted_message}"
                
                break
        else:
            return "❌ No club configuration found. Please run `/setup` first."
            
    except Exception as e:
        print(f"Error sending announcement: {e}")
        return f"❌ Error sending announcement: {str(e)}"

@tool
def get_setup_info() -> str:
    """
    Get information about the current bot setup and configuration.
    Use this to answer questions about what's configured, what channels are set up,
    what Google Sheets are being used, etc.
    
    Returns:
        str: Detailed information about the current setup
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ **No club configuration found.**\n\nPlease run `/setup` to configure the bot for your server."
        
        setup_info = "📋 **Current Bot Setup Information:**\n\n"
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                setup_info += f"🏠 **Server:** {guild_config.get('guild_name', 'Unknown')}\n"
                setup_info += f"👥 **Club:** {guild_config.get('club_name', 'Unknown')}\n"
                setup_info += f"👤 **Admin:** <@{guild_config.get('admin_user_id', 'Unknown')}>\n"
                setup_info += f"✅ **Setup Status:** Complete\n"
                setup_info += f"📅 **Setup Date:** {guild_config.get('completed_at', 'Unknown')}\n\n"
                
                # Channel information
                setup_info += "📢 **Channels:**\n"
                task_channel = guild_config.get('task_reminders_channel_id')
                meeting_channel = guild_config.get('meeting_reminders_channel_id')
                escalation_channel = guild_config.get('escalation_channel_id')
                
                if task_channel:
                    setup_info += f"  • Task Reminders: <#{task_channel}>\n"
                if meeting_channel:
                    setup_info += f"  • Meeting Reminders: <#{meeting_channel}>\n"
                if escalation_channel:
                    setup_info += f"  • Escalation: <#{escalation_channel}>\n"
                setup_info += "\n"
                
                # Google Sheets information
                setup_info += "📊 **Google Sheets:**\n"
                config_sheet = guild_config.get('config_spreadsheet_id')
                if config_sheet:
                    setup_info += f"  • Config Sheet: https://docs.google.com/spreadsheets/d/{config_sheet}\n"
                
                # Monthly sheets
                monthly_sheets = guild_config.get('monthly_sheets', {})
                if monthly_sheets:
                    setup_info += "  • Monthly Sheets:\n"
                    if 'tasks' in monthly_sheets:
                        setup_info += f"    - Tasks: https://docs.google.com/spreadsheets/d/{monthly_sheets['tasks']}\n"
                    if 'meetings' in monthly_sheets:
                        setup_info += f"    - Meetings: https://docs.google.com/spreadsheets/d/{monthly_sheets['meetings']}\n"
                
                # Folder information
                config_folder = guild_config.get('config_folder_id')
                monthly_folder = guild_config.get('monthly_folder_id')
                if config_folder:
                    setup_info += f"  • Config Folder: https://drive.google.com/drive/folders/{config_folder}\n"
                if monthly_folder:
                    setup_info += f"  • Monthly Folder: https://drive.google.com/drive/folders/{monthly_folder}\n"
                
                break
        else:
            setup_info += "❌ No complete guild configuration found."
            
        return setup_info
        
    except Exception as e:
        print(f"Error getting setup info: {e}")
        return f"❌ Error getting setup information: {str(e)}"

@tool
def get_meeting_sheet_info() -> str:
    """
    Get information about the meetings Google Sheet, including the link and current status.
    Use this to answer questions like "What's our Google Sheets link for meetings?"
    
    Returns:
        str: Information about the meetings sheet including the link
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ **No club configuration found.**\n\nPlease run `/setup` to configure the bot for your server."
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                # Get the meetings sheet ID
                meetings_sheet_id = None
                if 'monthly_sheets' in guild_config and 'meetings' in guild_config['monthly_sheets']:
                    meetings_sheet_id = guild_config['monthly_sheets']['meetings']
                elif 'meetings_sheet_id' in guild_config:
                    meetings_sheet_id = guild_config['meetings_sheet_id']
                
                if not meetings_sheet_id:
                    return "❌ **No meetings spreadsheet configured.**\n\nPlease run `/setup` to configure the meeting spreadsheet."
                
                # Get some basic info about the sheet
                try:
                    meetings = BOT_INSTANCE.meeting_manager.get_upcoming_meetings(meetings_sheet_id, limit=10)
                    meeting_count = len(meetings)
                except:
                    meeting_count = "Unknown"
                
                sheet_info = "📅 **Meetings Google Sheet Information:**\n\n"
                sheet_info += f"🔗 **Sheet Link:** https://docs.google.com/spreadsheets/d/{meetings_sheet_id}\n"
                sheet_info += f"📊 **Sheet ID:** `{meetings_sheet_id}`\n"
                sheet_info += f"📋 **Upcoming Meetings:** {meeting_count}\n"
                sheet_info += f"🏠 **Server:** {guild_config.get('guild_name', 'Unknown')}\n"
                sheet_info += f"👥 **Club:** {guild_config.get('club_name', 'Unknown')}\n\n"
                sheet_info += "💡 **Tip:** You can use this link to view and edit meetings directly in Google Sheets!"
                
                return sheet_info
                
        return "❌ No complete guild configuration found."
        
    except Exception as e:
        print(f"Error getting meeting sheet info: {e}")
        return f"❌ Error getting meeting sheet information: {str(e)}"

@tool
def get_task_sheet_info() -> str:
    """
    Get information about the tasks Google Sheet, including the link and current status.
    Use this to answer questions like "What's our Google Sheets link for tasks?"
    
    Returns:
        str: Information about the tasks sheet including the link
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ **No club configuration found.**\n\nPlease run `/setup` to configure the bot for your server."
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                # Get the tasks sheet ID
                tasks_sheet_id = None
                if 'monthly_sheets' in guild_config and 'tasks' in guild_config['monthly_sheets']:
                    tasks_sheet_id = guild_config['monthly_sheets']['tasks']
                elif 'tasks_sheet_id' in guild_config:
                    tasks_sheet_id = guild_config['tasks_sheet_id']
                
                if not tasks_sheet_id:
                    return "❌ **No tasks spreadsheet configured.**\n\nPlease run `/setup` to configure the tasks spreadsheet."
                
                # Get some basic info about the sheet
                try:
                    all_tasks = BOT_INSTANCE.meeting_manager.sheets_manager.get_all_tasks(tasks_sheet_id)
                    task_count = len(all_tasks)
                except:
                    task_count = "Unknown"
                
                sheet_info = "📋 **Tasks Google Sheet Information:**\n\n"
                sheet_info += f"🔗 **Sheet Link:** https://docs.google.com/spreadsheets/d/{tasks_sheet_id}\n"
                sheet_info += f"📊 **Sheet ID:** `{tasks_sheet_id}`\n"
                sheet_info += f"📝 **Total Tasks:** {task_count}\n"
                sheet_info += f"🏠 **Server:** {guild_config.get('guild_name', 'Unknown')}\n"
                sheet_info += f"👥 **Club:** {guild_config.get('club_name', 'Unknown')}\n\n"
                sheet_info += "💡 **Tip:** You can use this link to view and edit tasks directly in Google Sheets!"
                
                return sheet_info
                
        return "❌ No complete guild configuration found."
        
    except Exception as e:
        print(f"Error getting task sheet info: {e}")
        return f"❌ Error getting task sheet information: {str(e)}"

@tool
def get_channel_info() -> str:
    """
    Get information about the configured Discord channels.
    Use this to answer questions about which channels are set up for reminders, announcements, etc.
    
    Returns:
        str: Information about the configured channels
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ **No club configuration found.**\n\nPlease run `/setup` to configure the bot for your server."
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                channel_info = "📢 **Configured Discord Channels:**\n\n"
                
                task_channel = guild_config.get('task_reminders_channel_id')
                meeting_channel = guild_config.get('meeting_reminders_channel_id')
                escalation_channel = guild_config.get('escalation_channel_id')
                
                if task_channel:
                    channel_info += f"📋 **Task Reminders:** <#{task_channel}>\n"
                    channel_info += f"   - Used for: Task reminders, task-related announcements\n"
                else:
                    channel_info += f"📋 **Task Reminders:** Not configured\n"
                
                if meeting_channel:
                    channel_info += f"📅 **Meeting Reminders:** <#{meeting_channel}>\n"
                    channel_info += f"   - Used for: Meeting reminders, meeting announcements\n"
                else:
                    channel_info += f"📅 **Meeting Reminders:** Not configured\n"
                
                if escalation_channel:
                    channel_info += f"⚠️ **Escalation:** <#{escalation_channel}>\n"
                    channel_info += f"   - Used for: Important alerts, escalation notifications\n"
                else:
                    channel_info += f"⚠️ **Escalation:** Not configured\n"
                
                channel_info += f"\n🏠 **Server:** {guild_config.get('guild_name', 'Unknown')}\n"
                channel_info += f"👥 **Club:** {guild_config.get('club_name', 'Unknown')}\n"
                
                return channel_info
                
        return "❌ No complete guild configuration found."
        
    except Exception as e:
        print(f"Error getting channel info: {e}")
        return f"❌ Error getting channel information: {str(e)}"


@tool
def get_user_setup_status(user_id: str) -> str:
    """
    Check if a specific user is admin of any configured guild.
    
    Args:
        user_id: Discord user ID to check
        
    Returns:
        string: Setup status for the user
    """
    try:
        from discordbot.discord_client import BOT_INSTANCE
        
        if BOT_INSTANCE is None:
            return "❌ **Setup Status: ERROR**\n\nI cannot check setup status because the Discord bot is not running."
        
        if not hasattr(BOT_INSTANCE, 'setup_manager') or not BOT_INSTANCE.setup_manager:
            return "❌ **Setup Status: ERROR**\n\nI cannot check setup status because the setup manager is not available."
        
        # Check if user is admin of any guild
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        user_guilds = []
        
        for guild_id, config in all_guilds.items():
            if config.get('admin_user_id') == user_id and config.get('setup_complete', False):
                user_guilds.append((guild_id, config))
        
        if not user_guilds:
            return """❌ **Setup Status: NOT CONFIGURED**\n\nYou are not an admin of any configured student groups.

**What this means:**
• You haven't set up the bot for any servers yet
• Or you're not the admin of any configured servers

**To get started:**
• Run `/setup` in a Discord server where you're an admin
• This will configure the bot for that server
• You can be admin of multiple servers

**Current Status:** No configured servers found for your account."""
        
        # User is admin of one or more guilds
        if len(user_guilds) == 1:
            guild_id, config = user_guilds[0]
            guild_name = config.get('guild_name', 'Unknown Server')
            club_name = config.get('club_name', 'Unknown Club')
            
            return f"""✅ **Setup Status: CONFIGURED**\n\nYou are the admin of **{club_name}** in server **{guild_name}**.

**Your Configuration:**
• Server: {guild_name} (ID: {guild_id})
• Club: {club_name}
• Admin: <@{user_id}>

**What you can do:**
• Schedule and manage meetings
• Create and track meeting minutes
• Assign and monitor tasks
• Send automated reminders
• Process natural language requests

**Current Status:** Fully operational! 🎉"""
        else:
            # User is admin of multiple guilds
            response = f"""✅ **Setup Status: CONFIGURED**\n\nYou are the admin of **{len(user_guilds)}** configured student groups!\n\n"""
            
            for guild_id, config in user_guilds:
                guild_name = config.get('guild_name', 'Unknown Server')
                club_name = config.get('club_name', 'Unknown Club')
                response += f"**{club_name}** (Server: {guild_name})\n"
            
            response += "\n**What you can do:**\n• Schedule and manage meetings\n• Create and track meeting minutes\n• Assign and monitor tasks\n• Send automated reminders\n• Process natural language requests\n\n**Current Status:** Fully operational for all your groups! 🎉"
            
            return response
            
    except Exception as e:
        return f"❌ **Setup Status: ERROR**\n\nError checking setup status: {str(e)}"

@tool
def get_club_setup_info() -> str:
    """
    Get information about the bot's actual setup status and configuration.
    Use this when users ask about setup, configuration, or "what club are you set up for".

    Args:
        None

    Returns:
        string: Information about the bot's actual setup status
    """

    try:
        # Import the Discord client to check actual setup status
        from discordbot.discord_client import BOT_INSTANCE
        
        if BOT_INSTANCE is None:
            return "❌ **Setup Status: ERROR**\n\nI cannot check my setup status because the Discord bot is not running."
        
        # Check if there are any guild configurations using the new guild-based system
        if not hasattr(BOT_INSTANCE, 'setup_manager') or not BOT_INSTANCE.setup_manager:
            return """❌ **Setup Status: ERROR**\n\nI cannot check my setup status because the setup manager is not available."""
        
        # Get all guild configurations
        try:
            all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
            configured_guilds = [guild for guild in all_guilds.values() if guild.get('setup_complete', False)]
        except Exception as e:
            return f"""❌ **Setup Status: ERROR**\n\nI encountered an error accessing guild configurations: {str(e)}

**What this means:**
• There was a problem accessing the setup data
• The setup manager may not be properly initialized
• Contact an administrator for assistance

**Current Status:** Unable to determine setup status."""
        
        if not configured_guilds:
            return """❌ **Setup Status: NOT CONFIGURED**\n\nI am **NOT** set up for any student groups yet.

**What this means:**
• No clubs or student groups have been configured
• No Google Sheets are linked
• No admin users are set up
• I cannot manage meetings or tasks

**To get started:**
• An admin needs to run `/setup` to configure me for your group
• This will set up Google Sheets integration
• Configure admin permissions and channels
• Link your group's meeting and task systems

**Current Status:** Waiting for initial setup by an administrator."""
        
        # Show actual configured guilds
        num_guilds = len(configured_guilds)
        setup_info = f"""✅ **Setup Status: CONFIGURED**\n\nI am set up for **{num_guilds}** student group(s)!\n\n"""
        
        for guild_id, config in configured_guilds.items():
            guild_name = config.get('guild_name', 'Unknown Server')
            club_name = config.get('club_name', 'Unknown Club')
            admin_id = config.get('admin_user_id', 'Unknown')
            has_meetings = 'monthly_sheets' in config and 'meetings' in config.get('monthly_sheets', {})
            has_tasks = 'monthly_sheets' in config and 'tasks' in config.get('monthly_sheets', {})
            
            setup_info += f"**Group: {club_name}** (Server: {guild_name})\n"
            setup_info += f"• Admin: <@{admin_id}>\n"
            setup_info += f"• Meetings: {'✅ Configured' if has_meetings else '❌ Not configured'}\n"
            setup_info += f"• Tasks: {'✅ Configured' if has_tasks else '❌ Not configured'}\n\n"
        
        setup_info += """**What I can do for configured groups:**
• Schedule and manage meetings
• Create and track meeting minutes
• Assign and monitor tasks
• Send automated reminders
• Process natural language requests

**Example Questions:**
• "What meetings do I have today?"
• "Can you create meeting minutes?"
• "Send a reminder for the next meeting"
• "Show me the upcoming schedule"

**Current Status:** Fully operational for configured groups! 🎉"""
        
        return setup_info
        
    except Exception as e:
        return f"""❌ **Setup Status: ERROR**\n\nI encountered an error checking my setup status: {str(e)}

**What this means:**
• There was a problem accessing my configuration
• I may not be properly set up
• Contact an administrator for assistance

**Current Status:** Unable to determine setup status."""

@tool
def check_guild_setup_status(guild_id: str) -> str:
    """
    Check if the bot is set up for a specific Discord guild/server.
    Use this when users ask about setup status in a specific server.

    Args:
        guild_id: The Discord guild/server ID to check

    Returns:
        string: Setup status for the specific guild
    """

    try:
        # Import the Discord client to check actual setup status
        from discordbot.discord_client import BOT_INSTANCE
        
        if BOT_INSTANCE is None:
            return "❌ **Guild Setup Status: ERROR**\n\nI cannot check setup status because the Discord bot is not running."
        
        # Check if there are any club configurations
        if not hasattr(BOT_INSTANCE, 'club_configs') or not BOT_INSTANCE.club_configs:
            return f"❌ **Guild Setup Status: NOT CONFIGURED**\n\nI am **NOT** set up for guild {guild_id}.\n\n**Current Status:** No configurations found."
        
        # Check specific guild configuration
        guild_config = BOT_INSTANCE.club_configs.get(guild_id)
        
        if not guild_config:
            return f"❌ **Guild Setup Status: NOT CONFIGURED**\n\nI am **NOT** set up for guild {guild_id}.\n\n**What this means:**\n• This server has not been configured\n• No admin users are set up\n• No Google Sheets are linked\n\n**To get started:**\n• An admin needs to run `/setup` to configure me for this server\n\n**Current Status:** Waiting for setup by an administrator."
        
        # Show guild-specific configuration
        club_name = guild_config.get('club_name', 'Unknown Club')
        admin_id = guild_config.get('admin_discord_id', 'Unknown')
        has_meetings = 'meetings_sheet_id' in guild_config
        has_tasks = 'tasks_sheet_id' in guild_config
        
        setup_info = f"""✅ **Guild Setup Status: CONFIGURED**\n\nI am set up for **{club_name}** in this server!\n\n"""
        
        setup_info += f"**Group: {club_name}**\n"
        setup_info += f"• Admin: <@{admin_id}>\n"
        setup_info += f"• Meetings: {'✅ Configured' if has_meetings else '❌ Not configured'}\n"
        setup_info += f"• Tasks: {'✅ Configured' if has_tasks else '❌ Not configured'}\n\n"
        
        if has_meetings and has_tasks:
            setup_info += """**What I can do in this server:**
                • Schedule and manage meetings
                • Create and track meeting minutes
                • Assign and monitor tasks
                • Send automated reminders
                • Process natural language requests

                **Current Status:** Fully operational! 🎉"""
        else:
            setup_info += """**Partial Setup Detected:**
                • Some features may not be available
                • Contact the admin to complete configuration
                • Missing: Meetings or Tasks setup

                **Current Status:** Partially configured."""
                        
        return setup_info
        
    except Exception as e:
        return f"""❌ **Guild Setup Status: ERROR**\n\nI encountered an error checking setup status for guild {guild_id}: {str(e)}

            **What this means:**
            • There was a problem accessing the guild configuration
            • Contact an administrator for assistance

            **Current Status:** Unable to determine guild setup status."""

# These are agent helper functions for instantiation
def create_llm_with_tools() -> ChatOpenAI:
    """
    Creates the base agentic AI model

    Args:
        None
    Returns:
        The langchain ChatOpenAI model
    """
    # I dont wanna use an expensive model, use the cheapest gpt LOL
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    tools = [send_meeting_mins_summary, start_discord_bot, send_output_to_discord, create_meeting_mins, send_meeting_schedule, send_reminder_for_next_meeting, schedule_meeting, send_announcement]
    prompt = create_langchain_prompt()

    # give the llm access to the tool functions 
    from langchain.agents import create_openai_functions_agent
    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    return agent_executor

def create_langchain_prompt() -> ChatPromptTemplate:
    """
    Creates a langchain prompt for the chat model.
    
    Args:
        None
    Returns:
        The ChatPromptTemplate of the model
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """You are AutoExec, an AI-powered club executive task manager designed to help student organizations and clubs manage their meetings, tasks, and administrative work efficiently.

            ABOUT AUTOEXEC:
            - You are a specialized AI assistant for club executives and student organizations
            - You help with meeting management, task tracking, scheduling, and organizational communication
            - You integrate with Google Sheets for data management and Discord for communication
            - You can create meeting minutes, schedule meetings, send reminders, and manage club activities

            PERSONALITY & COMMUNICATION:
            - Be professional yet friendly and approachable
            - Use clear, concise language appropriate for student leaders
            - Be proactive in suggesting helpful actions
            - Show enthusiasm for helping with club management tasks
            - Use emojis appropriately to make responses engaging but not overwhelming

             RESPONSE GUIDELINES:
             - You can respond directly to questions about AutoExec, club management, meetings, tasks, and scheduling
             - Use tools when you need to access specific data (meetings, setup status, etc.) or perform actions
             - For general questions about capabilities, you can answer directly without tools
             - Always stay within AutoExec's scope: club management, meetings, tasks, scheduling, and organizational communication
             - Be helpful and suggest relevant tools when appropriate, but don't force tool usage for simple questions
             - If asked about topics outside AutoExec's scope, politely redirect to AutoExec's capabilities"""),
                        ("user", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ]
    )
    return prompt


def run_agent(query: str):
    """
    Runs the LangChain agent with the given query.

    Args:
        query (str): The input query.

    Returns:
        dict: The response from the agent.
    """
    agent_executor = create_llm_with_tools()
    response = agent_executor.invoke({"input": f"{query}"})
    return response


def run_agent_text_only(query: str):
    """
    Runs the LangChain agent in text-only mode (no Discord sending).
    Use this when calling from the Discord bot to avoid event loop issues.

    Args:
        query (str): The input query.

    Returns:
        str: The text response from the agent.
    """
    # Create a modified prompt that doesn't require Discord sending
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are AutoExec, an AI-powered club executive task manager designed to help student organizations and clubs manage their meetings, tasks, and administrative work efficiently.

ABOUT AUTOEXEC:
- You are a specialized AI assistant for club executives and student organizations
- You help with meeting management, task tracking, scheduling, and organizational communication
- You integrate with Google Sheets for data management and Discord for communication
- You can create meeting minutes, schedule meetings, send reminders, and manage club activities

PERSONALITY & COMMUNICATION:
- Be professional yet friendly and approachable
- Use clear, concise language appropriate for student leaders
- Be proactive in suggesting helpful actions
- Show enthusiasm for helping with club management tasks
- Use emojis appropriately to make responses engaging but not overwhelming
- Provide personalized responses based on current context

RESPONSE GUIDELINES:
- You can respond directly to questions about AutoExec, club management, meetings, tasks, and scheduling
- Use tools when you need to access specific data (meetings, setup status, etc.) or perform actions
- For general questions about capabilities, you can answer directly without tools
- Always stay within AutoExec's scope: club management, meetings, tasks, scheduling, and organizational communication
- Be helpful and suggest relevant tools when appropriate, but don't force tool usage for simple questions
- If asked about topics outside AutoExec's scope, politely redirect to AutoExec's capabilities

AVAILABLE TOOLS (use when you need to access data or perform actions):
- create_meeting_mins: Use when users ask about creating meeting minutes, want to create minutes, or mention "meeting minutes"
- send_meeting_schedule: Use when users ask about upcoming meetings, meeting schedules, "what meetings do I have", or "show me meetings"
- get_meeting_reminder_info: Use when users ask about meeting reminders, "send a reminder", or "remind me about meetings"
- schedule_meeting: Use when users want to SCHEDULE/CREATE a new meeting, "schedule a meeting", "set up a meeting", or "create a meeting"
- send_announcement: Use when users want to SEND AN ANNOUNCEMENT, "send out an announcement", "announce something", or "send a message to everyone". Supports types: "meeting", "task", "general", "escalation"
- get_club_setup_info: Use when users ask about setup status, "what club are you set up for", or "are you configured"
- check_guild_setup_status: Use when users ask about setup status in a specific server or "are you set up for this group"

EXAMPLES:
- "What club are you set up for?" → Use get_club_setup_info to get current setup status
- "Are you set up yet?" → Use get_club_setup_info to check configuration
- "Are you set up for this group?" → Use check_guild_setup_status for server-specific info
- "Can you send a reminder for a meeting in 2 mins" → Use get_meeting_reminder_info
- "What meetings do I have today?" → Use send_meeting_schedule to get upcoming meetings
- "Create meeting minutes" → Use create_meeting_mins to generate minutes
- "Schedule a meeting for tomorrow at 2pm" → Use schedule_meeting to add to calendar
- "Set up a meeting for next week" → Use schedule_meeting to create new meeting
- "Send out an announcement about the meeting tomorrow" → Use send_announcement
- "Announce that we're having a team meeting" → Use send_announcement
- "Hello", "What can you do?", "Help me" → You can respond directly about AutoExec's capabilities

Remember: Use tools when you need specific data or to perform actions. You can respond directly to general questions about AutoExec's capabilities."""),
        ("user", "{input}"),
        MessagesPlaceholder("agent_scratchpad")
    ])
    
    # Create a simple LLM without the Discord tools
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
    
    # Create a simple agent without Discord tools
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
    
    # Include tools that don't require Discord sending but are useful for queries
    safe_tools = [
        create_meeting_mins, 
        send_meeting_schedule, 
        get_meeting_reminder_info,
        get_club_setup_info,
        check_guild_setup_status,
        schedule_meeting,
        send_announcement,
        get_setup_info,
        get_meeting_sheet_info,
        get_task_sheet_info,
        get_channel_info
    ]
    
    print(f"🔧 Available tools: {[tool.name for tool in safe_tools]}")
    
    # Use OpenAI functions agent which is more reliable for tool calling
    agent = create_openai_functions_agent(llm, safe_tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=safe_tools, 
        verbose=True, 
        handle_parsing_errors=True,
        max_iterations=3,
        early_stopping_method="generate",
        return_intermediate_steps=True
    )
    
    try:
        print(f"🔍 Invoking agent with query: {query}")
        print(f"🔍 Available tools: {[tool.name for tool in safe_tools]}")
        
        response = agent_executor.invoke({"input": f"{query}"})
        print(f"🔍 Agent response: {response}")
        
        # Check if the agent actually used any tools
        if hasattr(response, 'intermediate_steps') and response.intermediate_steps:
            print(f"🔍 Agent used tools: {response.intermediate_steps}")
        else:
            print("⚠️ Agent didn't use any tools - this might be the problem!")
            
        # Check the response structure
        print(f"🔍 Response keys: {response.keys() if hasattr(response, 'keys') else 'No keys'}")
        print(f"🔍 Response type: {type(response)}")
        
        return response.get("output", "I'm sorry, I couldn't process that request.")
    except Exception as e:
        print(f"❌ Error in agent execution: {e}")
        import traceback
        traceback.print_exc()
        return f"I'm sorry, I encountered an error: {str(e)}"

async def run_tasks():
    # Start the Discord bot by running the agent with the "Start the discord bot" query
    query = "Start the discord bot"
    result = await run_agent(query)  # Ensure `run_agent` is async
    print(result["output"])  # Print confirmation that the bot has started

    # Add any other async tasks if needed
    
async def send_hourly_message():
    """
    Sends a message to Discord every hour.
    """
    while True:
        query = "Send a message saying 'hi'"
        result = await run_agent(query)
        print(result["output"])  # Confirm message sent
        await asyncio.sleep(3600)  # Wait for 1 hour (3600 seconds)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    print(f"This is the main async agent")

    try:
        loop.run_until_complete(run_tasks())  # Run the async function without creating a new event loop
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        loop.close()