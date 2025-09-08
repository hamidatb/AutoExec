"""
Meeting tools module for AutoExec agent.
Contains all meeting-related functions including scheduling, searching, canceling, and updating meetings.
"""

from langchain.tools import tool
from .context_manager import get_discord_context, get_meetings_sheet_id


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
    from googledrive.file_handler import create_meeting_mins_for_today
    
    meetingMinsLink = create_meeting_mins_for_today()
    if not meetingMinsLink:
        print("There was an error in creating the meeting minutes")
        return "There was an error in creating the meeting minutes"
    else:
        return meetingMinsLink


@tool
def send_meeting_schedule(amount_of_meetings_to_return: int):
    """
    Retrieves a formatted string representation of the upcoming few meetings from Google Sheets.
    Use this when users ask "what meetings do we have", "show me upcoming meetings", or "what's our schedule".

    **This function REQUIRES an argument. It will raise an error if none is provided.**

    Args:
        amount_of_meetings_to_return (int): The number of meetings to return (REQUIRED). Use 3-5 for general queries.
        
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
        # print(f"🔍 [DEBUG] Getting guild configurations from setup manager")
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        # print(f"🔍 [DEBUG] Found {len(all_guilds) if all_guilds else 0} guild configurations")
        
        if not all_guilds:
            meetings_info += "❌ **No club configuration found.**\n\n"
            meetings_info += "**Possible causes:**\n"
            meetings_info += "• The config/guild_setup_status.json file was deleted or corrupted\n"
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
                    # print(f"🔍 [DEBUG] Getting meetings from sheet ID: {meetings_sheet_id}")
                    
                    try:
                        # Get upcoming meetings using the meeting manager
                        upcoming_meetings = BOT_INSTANCE.meeting_manager.get_upcoming_meetings(
                            meetings_sheet_id, 
                            limit=amount_of_meetings_to_return
                        )
                        
                        # print(f"🔍 [DEBUG] Found {len(upcoming_meetings) if upcoming_meetings else 0} upcoming meetings")
                        
                        if not upcoming_meetings:
                            meetings_info += "📅 **No upcoming meetings scheduled.**\n\n"
                            meetings_info += "Use `/meeting set` to schedule a new meeting."
                        else:
                            for meeting in upcoming_meetings:
                                title = meeting.get('title', 'Untitled Meeting')
                                start_time = meeting.get('start_at_local', meeting.get('start_at_utc', 'Time TBD'))
                                location = meeting.get('location', 'Location TBD')
                                meeting_link = meeting.get('meeting_link', '')
                                minutes_link = meeting.get('minutes_link', '')
                                
                                meetings_info += f"**{title}**\n"
                                meetings_info += f"🕐 {start_time}\n"
                                meetings_info += f"📍 {location}\n"
                                if meeting_link:
                                    meetings_info += f"🔗 {meeting_link}\n"
                                if minutes_link:
                                    meetings_info += f"📄 Minutes: {minutes_link}\n"
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
    from .discord_tools import send_output_to_discord

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
        
        cleanup_results = []
        
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                meetings_sheet_id = get_meetings_sheet_id(guild_config)
                if meetings_sheet_id:
                    try:
                        # Get all meetings from the sheet
                        all_meetings = BOT_INSTANCE.meeting_manager.get_all_meetings(meetings_sheet_id)
                        
                        if all_meetings:
                            now = datetime.now(timezone.utc)
                            past_meetings = []
                            
                            for meeting in all_meetings:
                                if meeting.get('status') == 'scheduled':
                                    try:
                                        # Parse the start time
                                        start_time_str = meeting.get('start_at_utc')
                                        if start_time_str:
                                            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                                            if start_time < now:
                                                past_meetings.append(meeting)
                                    except Exception as parse_error:
                                        print(f"Error parsing meeting time: {parse_error}")
                                        continue
                            
                            if past_meetings:
                                # Cancel past meetings
                                for meeting in past_meetings:
                                    meeting_id = meeting.get('meeting_id')
                                    if meeting_id:
                                        import asyncio
                                        asyncio.run(BOT_INSTANCE.meeting_manager.cancel_meeting(meeting_id, meetings_sheet_id))
                                
                                cleanup_results.append(f"Cleaned up {len(past_meetings)} past meetings from server {guild_id}")
                            else:
                                cleanup_results.append(f"No past meetings found in server {guild_id}")
                        else:
                            cleanup_results.append(f"No meetings found in server {guild_id}")
                            
                    except Exception as sheet_error:
                        cleanup_results.append(f"Error accessing meetings sheet for server {guild_id}: {str(sheet_error)}")
        
        if cleanup_results:
            return "🧹 **Meeting Cleanup Complete:**\n\n" + "\n".join(cleanup_results)
        else:
            return "❌ No guild configurations found for cleanup."
            
    except Exception as e:
        return f"❌ Error during meeting cleanup: {str(e)}"


@tool
def get_meeting_reminder_info():
    """
    Get information about the next meeting for reminder purposes.
    This is used internally by the reminder system.
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
                meetings_sheet_id = get_meetings_sheet_id(guild_config)
                if meetings_sheet_id:
                    try:
                        # Get the next meeting
                        upcoming_meetings = BOT_INSTANCE.meeting_manager.get_upcoming_meetings(
                            meetings_sheet_id, 
                            limit=1
                        )
                        
                        if upcoming_meetings:
                            meeting = upcoming_meetings[0]
                            title = meeting.get('title', 'Untitled Meeting')
                            start_time_str = meeting.get('start_at_utc')
                            
                            if start_time_str:
                                try:
                                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                                    
                                    # Get the guild's timezone for accurate time calculation
                                    import pytz
                                    guild_timezone = guild_config.get('timezone', 'America/Edmonton')
                                    local_tz = pytz.timezone(guild_timezone)
                                    
                                    # Get current time in the guild's timezone
                                    now_utc = datetime.now(timezone.utc)
                                    now_local = now_utc.astimezone(local_tz)
                                    
                                    # Convert start_time to local timezone for comparison
                                    start_time_local = start_time.astimezone(local_tz)
                                    time_until = start_time_local - now_local
                                    
                                    if time_until.total_seconds() > 0:
                                        hours_until = time_until.total_seconds() / 3600
                                        
                                        reminder_info = f"📅 **Next Meeting Reminder**\n\n"
                                        reminder_info += f"**{title}**\n"
                                        reminder_info += f"🕐 {meeting.get('start_at_local', 'Time TBD')}\n"
                                        reminder_info += f"📍 {meeting.get('location', 'Location TBD')}\n"
                                        
                                        if meeting.get('meeting_link'):
                                            reminder_info += f"🔗 {meeting.get('meeting_link')}\n"
                                        
                                        if hours_until < 24:
                                            reminder_info += f"\n⏰ **Meeting starts in {hours_until:.1f} hours!**"
                                        else:
                                            days_until = hours_until / 24
                                            reminder_info += f"\n⏰ **Meeting starts in {days_until:.1f} days**"
                                        
                                        return reminder_info
                                    else:
                                        return f"❌ Next meeting '{title}' is in the past. Please run cleanup_past_meetings() to fix this."
                                        
                                except Exception as parse_error:
                                    return f"❌ Error parsing meeting time: {str(parse_error)}"
                            else:
                                return f"❌ Next meeting '{title}' has no valid start time."
                        else:
                            return "📅 **No upcoming meetings scheduled.**\n\nUse `/meeting set` to schedule a new meeting."
                            
                    except Exception as sheet_error:
                        return f"❌ Error accessing meetings sheet: {str(sheet_error)}"
                else:
                    return "❌ No meetings spreadsheet configured. Please run `/setup` first."
        
        return "❌ No meetings spreadsheet configured. Please run `/setup` first."
        
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
                meetings_sheet_id = get_meetings_sheet_id(guild_config)
                
                if not meetings_sheet_id:
                    return "❌ No meetings spreadsheet configured. Please run `/setup` first."
                
                # Parse start time
                try:
                    start_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
                    
                    # Check if the date is in the past (likely a parsing error)
                    now = datetime.now()
                    if start_datetime.year < now.year or (start_datetime.year == now.year and start_datetime < now):
                        return f"❌ **Invalid Date:** The scheduled date ({start_datetime.strftime('%B %d, %Y')}) is in the past.\n\n**Current date:** {now.strftime('%B %d, %Y')}\n\n**Please use a future date.**\n\n**Examples:**\n• Tomorrow: `{datetime.now().strftime('%Y-%m-%d')} 14:00`\n• Next week: `{(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')} 14:00`"
                    
                    # Convert local time to UTC using guild timezone
                    import pytz
                    guild_timezone = guild_config.get('timezone', 'America/Edmonton')
                    local_tz = pytz.timezone(guild_timezone)
                    start_datetime_local = local_tz.localize(start_datetime)
                    start_datetime = start_datetime_local.astimezone(timezone.utc)
                    
                    # Debug logging with UTC indicators
                    print(f"🔍 [MEETING DEBUG] Meeting: {meeting_title}")
                    print(f"🔍 [MEETING DEBUG]   Input time: {start_time}")
                    print(f"🔍 [MEETING DEBUG]   Guild timezone: {guild_timezone}")
                    print(f"🔍 [MEETING DEBUG]   Local time: {start_datetime_local}")
                    print(f"🔍 [MEETING DEBUG]   UTC time: {start_datetime}")
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
                    'minutes_link': '',  # Will be set when meeting minutes are created
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
def search_meetings_by_title(meeting_title: str) -> str:
    """
    Search for meetings by title to help with cancellation or updates.
    
    **USE THIS TOOL WHEN:**
    - User wants to cancel or update a meeting but there might be multiple matches
    - User says "add meeting minutes to [meeting name]" or "add minutes to [meeting name]"
    - User wants to see details of meetings with a specific title
    - You need to find a meeting before performing an action on it
    
    **IMPORTANT:** Always show the full meeting details from this tool in your response to the user.
    
    Args:
        meeting_title (str): The title or partial title of the meeting to search for
        
    Returns:
        str: Formatted list of matching meetings with their details
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get Discord context to know which guild
        context = get_discord_context()
        guild_id = context.get('guild_id')
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config:
            return "❌ This server is not set up. Please run `/setup` first."
        
        # Get the meetings sheet ID using the standard function
        meetings_sheet_id = get_meetings_sheet_id(guild_config)
        if not meetings_sheet_id:
            return "❌ No meetings spreadsheet configured for this server."
        
        # Search for meetings by title
        matching_meetings = BOT_INSTANCE.meeting_manager.search_meetings_by_title(
            meeting_title, meetings_sheet_id, status_filter='scheduled'
        )
        
        if not matching_meetings:
            return f"❌ No scheduled meetings found matching '{meeting_title}'."
        
        if len(matching_meetings) == 1:
            meeting = matching_meetings[0]
            return f"✅ Found 1 matching meeting:\n\n**{meeting.get('title', 'Untitled')}**\n🆔 ID: `{meeting.get('meeting_id', 'N/A')}`\n🕐 Date: {meeting.get('start_at_local', 'N/A')}\n📍 Location: {meeting.get('location', 'N/A')}\n🔗 Meeting Link: {meeting.get('meeting_link', 'N/A')}\n📄 Minutes Link: {meeting.get('minutes_link', 'N/A')}"
        
        # Multiple matches - show numbered list
        result = f"🔍 Found {len(matching_meetings)} meetings matching '{meeting_title}':\n\n"
        for i, meeting in enumerate(matching_meetings, 1):
            result += f"**{i}. {meeting.get('title', 'Untitled')}**\n"
            result += f"   🆔 ID: `{meeting.get('meeting_id', 'N/A')}`\n"
            result += f"   🕐 Date: {meeting.get('start_at_local', 'N/A')}\n"
            result += f"   📍 Location: {meeting.get('location', 'N/A')}\n"
            result += f"   🔗 Meeting Link: {meeting.get('meeting_link', 'N/A')}\n"
            result += f"   📄 Minutes Link: {meeting.get('minutes_link', 'N/A')}\n\n"
        
        result += "Please specify which meeting you want to cancel or update by saying the number (1, 2, 3, etc.) or the meeting ID."
        return result
        
    except Exception as e:
        print(f"Error searching meetings: {e}")
        return f"❌ Error searching meetings: {str(e)}"


@tool
def cancel_meeting(meeting_identifier: str) -> str:
    """
    Cancel a scheduled meeting by ID or title.
    
    **USE THIS TOOL WHEN:**
    - User says "cancel [meeting name]" or "cancel the [meeting name]"
    - User wants to remove/delete a scheduled meeting
    - User says "remove [meeting name]" or "delete [meeting name]"
    
    **DO NOT USE THIS TOOL FOR:**
    - Creating new meetings (use schedule_meeting instead)
    - Updating meeting details (use update_meeting instead)
    - Rescheduling meetings (use update_meeting with new_start_time instead)
    
    Args:
        meeting_identifier (str): Either the meeting ID or the meeting title
        
    Returns:
        str: Confirmation message about the cancellation
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get Discord context to know which guild
        context = get_discord_context()
        guild_id = context.get('guild_id')
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config:
            return "❌ This server is not set up. Please run `/setup` first."
        
        # Get the meetings sheet ID using the standard function
        meetings_sheet_id = get_meetings_sheet_id(guild_config)
        if not meetings_sheet_id:
            return "❌ No meetings spreadsheet configured for this server."
        
        # Check if identifier looks like a meeting ID (UUID format)
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        
        if re.match(uuid_pattern, meeting_identifier, re.IGNORECASE):
            # It's a meeting ID
            meeting = BOT_INSTANCE.meeting_manager.get_meeting_by_id(meeting_identifier, meetings_sheet_id)
            if not meeting:
                return f"❌ No meeting found with ID: {meeting_identifier}"
            
            if meeting.get('status') == 'canceled':
                return f"❌ Meeting '{meeting.get('title', 'Untitled')}' is already canceled."
            
            # Cancel the meeting
            import asyncio
            success = asyncio.run(BOT_INSTANCE.meeting_manager.cancel_meeting(meeting_identifier, meetings_sheet_id))
            
            if success:
                return f"✅ **Meeting Canceled Successfully!**\n\n**{meeting.get('title', 'Untitled')}**\n🕐 Was scheduled for: {meeting.get('start_at_local', 'N/A')}\n📍 Location: {meeting.get('location', 'N/A')}\n\nAll reminders for this meeting have been canceled."
            else:
                return f"❌ Failed to cancel meeting '{meeting.get('title', 'Untitled')}'. Please try again."
        
        else:
            # It's a title - search for meetings
            matching_meetings = BOT_INSTANCE.meeting_manager.search_meetings_by_title(
                meeting_identifier, meetings_sheet_id, status_filter='scheduled'
            )
            
            if not matching_meetings:
                return f"❌ No scheduled meetings found matching '{meeting_identifier}'."
            
            if len(matching_meetings) == 1:
                meeting = matching_meetings[0]
                meeting_id = meeting.get('meeting_id')
                
                if not meeting_id:
                    return f"❌ Meeting '{meeting.get('title', 'Untitled')}' has no valid ID."
                
                # Cancel the meeting
                import asyncio
                success = asyncio.run(BOT_INSTANCE.meeting_manager.cancel_meeting(meeting_id, meetings_sheet_id))
                
                if success:
                    return f"✅ **Meeting Canceled Successfully!**\n\n**{meeting.get('title', 'Untitled')}**\n🕐 Was scheduled for: {meeting.get('start_at_local', 'N/A')}\n📍 Location: {meeting.get('location', 'N/A')}\n\nAll reminders for this meeting have been canceled."
                else:
                    return f"❌ Failed to cancel meeting '{meeting.get('title', 'Untitled')}'. Please try again."
            
            else:
                # Multiple matches - return search results
                result = f"🔍 Found {len(matching_meetings)} meetings matching '{meeting_identifier}':\n\n"
                for i, meeting in enumerate(matching_meetings, 1):
                    result += f"**{i}. {meeting.get('title', 'Untitled')}**\n"
                    result += f"   🆔 ID: `{meeting.get('meeting_id', 'N/A')}`\n"
                    result += f"   🕐 Date: {meeting.get('start_at_local', 'N/A')}\n"
                    result += f"   📍 Location: {meeting.get('location', 'N/A')}\n\n"
                
                result += "Please specify which meeting you want to cancel by saying the number (1, 2, 3, etc.) or the meeting ID."
                return result
        
    except Exception as e:
        print(f"Error canceling meeting: {e}")
        return f"❌ Error canceling meeting: {str(e)}"


@tool
def update_meeting(meeting_identifier: str, new_title: str = "", new_start_time: str = "", 
                  new_location: str = "", new_meeting_link: str = "", new_minutes_link: str = "") -> str:
    """
    Update a scheduled meeting with new information.
    
    **USE THIS TOOL WHEN:**
    - User says "update [meeting name]" or "change [meeting name]"
    - User says "reschedule [meeting name]" (use new_start_time parameter)
    - User wants to modify meeting details (time, location, title, link, minutes)
    - User says "move [meeting name] to [new time]"
    - User says "add meeting minutes to [meeting name]" (use new_minutes_link parameter)
    - User wants to add or update meeting minutes link
    - After using search_meetings_by_title and user specifies which meeting to update
    
    **DO NOT USE THIS TOOL FOR:**
    - Creating new meetings (use schedule_meeting instead)
    - Canceling meetings (use cancel_meeting instead)
    
    Args:
        meeting_identifier (str): Either the meeting ID or the meeting title (REQUIRED)
        new_title (str): New title for the meeting (optional)
        new_start_time (str): New start time in "YYYY-MM-DD HH:MM" format (optional)
        new_location (str): New location for the meeting (optional)
        new_meeting_link (str): New meeting link (optional)
        new_minutes_link (str): New minutes link (optional)
        
    Returns:
        str: Confirmation message about the update
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime, timezone
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get Discord context to know which guild
        context = get_discord_context()
        guild_id = context.get('guild_id')
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config:
            return "❌ This server is not set up. Please run `/setup` first."
        
        # Get the meetings sheet ID using the standard function
        meetings_sheet_id = get_meetings_sheet_id(guild_config)
        if not meetings_sheet_id:
            return "❌ No meetings spreadsheet configured for this server."
        
        # Check if identifier looks like a meeting ID (UUID format)
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        
        if re.match(uuid_pattern, meeting_identifier, re.IGNORECASE):
            # It's a meeting ID
            meeting = BOT_INSTANCE.meeting_manager.get_meeting_by_id(meeting_identifier, meetings_sheet_id)
            if not meeting:
                return f"❌ No meeting found with ID: {meeting_identifier}"
            
            meeting_id = meeting_identifier
            original_title = meeting.get('title', 'Untitled')
            
        else:
            # It's a title - search for meetings
            matching_meetings = BOT_INSTANCE.meeting_manager.search_meetings_by_title(
                meeting_identifier, meetings_sheet_id, status_filter='scheduled'
            )
            
            if not matching_meetings:
                return f"❌ No scheduled meetings found matching '{meeting_identifier}'."
            
            if len(matching_meetings) == 1:
                meeting = matching_meetings[0]
                meeting_id = meeting.get('meeting_id')
                original_title = meeting.get('title', 'Untitled')
                
                if not meeting_id:
                    return f"❌ Meeting '{original_title}' has no valid ID."
            else:
                # Multiple matches - return search results
                result = f"🔍 Found {len(matching_meetings)} meetings matching '{meeting_identifier}':\n\n"
                for i, meeting in enumerate(matching_meetings, 1):
                    result += f"**{i}. {meeting.get('title', 'Untitled')}**\n"
                    result += f"   🆔 ID: `{meeting.get('meeting_id', 'N/A')}`\n"
                    result += f"   🕐 Date: {meeting.get('start_at_local', 'N/A')}\n"
                    result += f"   📍 Location: {meeting.get('location', 'N/A')}\n\n"
                
                result += "Please specify which meeting you want to update by saying the number (1, 2, 3, etc.) or the meeting ID."
                return result
        
        # Prepare update data
        update_data = {}
        
        if new_title:
            update_data['title'] = new_title
        
        if new_start_time:
            try:
                start_datetime = datetime.strptime(new_start_time, "%Y-%m-%d %H:%M")
                # Convert local time to UTC using guild timezone
                import pytz
                guild_timezone = guild_config.get('timezone', 'America/Edmonton')
                local_tz = pytz.timezone(guild_timezone)
                start_datetime_local = local_tz.localize(start_datetime)
                start_datetime = start_datetime_local.astimezone(timezone.utc)
                
                # Debug logging with UTC indicators
                print(f"🔍 [UPDATE DEBUG] Meeting update:")
                print(f"🔍 [UPDATE DEBUG]   Input time: {new_start_time}")
                print(f"🔍 [UPDATE DEBUG]   Guild timezone: {guild_timezone}")
                print(f"🔍 [UPDATE DEBUG]   Local time: {start_datetime_local}")
                print(f"🔍 [UPDATE DEBUG]   UTC time: {start_datetime}")
                update_data['start_at_utc'] = start_datetime.isoformat()
                update_data['start_at_local'] = start_datetime.strftime("%B %d, %Y at %I:%M %p")
            except ValueError:
                return "❌ Invalid new_start_time format. Please use YYYY-MM-DD HH:MM format."
        
        if new_location:
            update_data['location'] = new_location
        
        if new_meeting_link:
            update_data['meeting_link'] = new_meeting_link
        
        if new_minutes_link:
            update_data['minutes_link'] = new_minutes_link
        
        if not update_data:
            return "❌ No update data provided. Please specify at least one field to update."
        
        # Update the meeting
        import asyncio
        success = asyncio.run(BOT_INSTANCE.meeting_manager.update_meeting(meeting_id, update_data, meetings_sheet_id))
        
        if success:
            result = f"✅ **Meeting Updated Successfully!**\n\n"
            result += f"**{original_title}** → **{update_data.get('title', original_title)}**\n\n"
            
            if 'start_at_local' in update_data:
                result += f"🕐 **New Time:** {update_data['start_at_local']}\n"
            else:
                result += f"🕐 **Time:** {meeting.get('start_at_local', 'N/A')}\n"
            
            if 'location' in update_data:
                result += f"📍 **New Location:** {update_data['location']}\n"
            else:
                result += f"📍 **Location:** {meeting.get('location', 'N/A')}\n"
            
            if 'meeting_link' in update_data:
                result += f"🔗 **New Meeting Link:** {update_data['meeting_link']}\n"
            elif meeting.get('meeting_link'):
                result += f"🔗 **Meeting Link:** {meeting.get('meeting_link')}\n"
            
            if 'minutes_link' in update_data:
                result += f"📄 **New Minutes Link:** {update_data['minutes_link']}\n"
            elif meeting.get('minutes_link'):
                result += f"📄 **Minutes Link:** {meeting.get('minutes_link')}\n"
            
            return result
        else:
            return f"❌ Failed to update meeting '{original_title}'. Please try again."
        
    except Exception as e:
        print(f"Error updating meeting: {e}")
        return f"❌ Error updating meeting: {str(e)}"


@tool
def start_meeting_scheduling(meeting_title: str) -> str:
    """
    Start the meeting scheduling process by creating a meeting with a timer.
    This is a convenience function that combines meeting creation with timer setup.
    
    Args:
        meeting_title (str): The title of the meeting to schedule
        
    Returns:
        str: Confirmation message about the meeting scheduling process
    """
    # This function starts the meeting scheduling conversation
    # The actual meeting creation will be handled by create_meeting_with_timer
    # when the user provides all the required details
    
    return f"""🎯 **Meeting Scheduling Started**

I'm ready to help you schedule **"{meeting_title}"**!

To complete the scheduling, I'll need a few more details:

**Next steps:**
1. **What time should the meeting start?** (e.g., "tomorrow at 2pm" or "2025-09-08 14:00")
2. **What time should it end?** (e.g., "3pm" or "15:00")
3. **Where will it be held?** (location, online link, or Discord channel)
4. **Do you need meeting minutes?** (provide existing link, create new, or not needed)

Just provide the details and I'll create the meeting with automatic reminders! 📅"""


@tool
def create_meeting_with_timer(meeting_title: str, start_time: str, end_time: str, location: str = "", meeting_link: str = "", minutes_link: str = "", create_minutes: bool = False) -> str:
    """
    Create a meeting with automatic timer setup for reminders.
    This combines meeting scheduling with timer management.
    
    Args:
        meeting_title (str): The title of the meeting (REQUIRED)
        start_time (str): The start time in format "YYYY-MM-DD HH:MM" (REQUIRED)
        end_time (str): The end time in format "YYYY-MM-DD HH:MM" (REQUIRED)
        location (str): The meeting location or description (optional)
        meeting_link (str): The meeting link (Zoom, Teams, etc.) (optional)
        minutes_link (str): The minutes link (optional)
        create_minutes (bool): Whether to create meeting minutes document (optional)
        
    Returns:
        str: Confirmation message about the meeting creation and timer setup
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime, timezone, timedelta
    from .utility_tools import create_meeting_timers
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get the Discord context from the current message
        from ae_langchain.tools.context_manager import get_discord_context
        context = get_discord_context()
        guild_id = context.get('guild_id')
        channel_id = context.get('channel_id')
        user_id = context.get('user_id')
        
        if not user_id:
            return "❌ No Discord context found. Please use this command in a Discord server or DM."
        
        # Handle DM context - check if user is admin of any configured servers
        if not guild_id:
            from ae_langchain.tools.context_manager import get_user_admin_servers
            user_guilds = get_user_admin_servers(user_id)
            if len(user_guilds) == 0:
                return "❌ You are not an admin of any configured servers. Please run `/setup` first."
            elif len(user_guilds) == 1:
                guild_id = user_guilds[0]['guild_id']
            else:
                guild_list = "\n".join([f"• **{guild['club_name']}** (Server: {guild['guild_name']})" for guild in user_guilds])
                return f"""❓ **Multiple Servers Detected**\n\nYou are an admin of **{len(user_guilds)}** servers. Please specify which server you're referring to:\n\n{guild_list}\n\n**How to specify:**\n• Mention the club name: "For [Club Name], schedule meeting [title]"\n• Mention the server name: "In [Server Name], create meeting [title]"\n\n**Example:** "For Computer Science Club, schedule meeting budget review"\n\nWhich server would you like me to help you with?"""
        
        # Get the guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        # Parse the start time
        try:
            start_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            # Convert local time to UTC using guild timezone
            import pytz
            guild_timezone = guild_config.get('timezone', 'America/Edmonton')
            local_tz = pytz.timezone(guild_timezone)
            start_datetime_local = local_tz.localize(start_datetime)
            start_datetime = start_datetime_local.astimezone(timezone.utc)
            
            # Debug logging with UTC indicators
            print(f"🔍 [MEETING DEBUG] Meeting: {meeting_title}")
            print(f"🔍 [MEETING DEBUG]   Input start time: {start_time}")
            print(f"🔍 [MEETING DEBUG]   Guild timezone: {guild_timezone}")
            print(f"🔍 [MEETING DEBUG]   Start local time: {start_datetime_local}")
            print(f"🔍 [MEETING DEBUG]   Start UTC time: {start_datetime}")
        except ValueError:
            return f"❌ Could not parse start time: '{start_time}'. Please use format 'YYYY-MM-DD HH:MM'"
        
        # Parse the end time
        try:
            end_datetime = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
            # Convert local time to UTC using guild timezone
            end_datetime_local = local_tz.localize(end_datetime)
            end_datetime = end_datetime_local.astimezone(timezone.utc)
            
            # Debug logging with UTC indicators
            print(f"🔍 [MEETING DEBUG]   Input end time: {end_time}")
            print(f"🔍 [MEETING DEBUG]   End local time: {end_datetime_local}")
            print(f"🔍 [MEETING DEBUG]   End UTC time: {end_datetime}")
        except ValueError:
            return f"❌ Could not parse end time: '{end_time}'. Please use format 'YYYY-MM-DD HH:MM'"
        
        # Validate that end time is after start time
        if end_datetime <= start_datetime:
            return f"❌ End time must be after start time. Start: {start_datetime.strftime('%B %d, %Y at %I:%M %p')}, End: {end_datetime.strftime('%B %d, %Y at %I:%M %p')}"
        
        # Create meeting data
        meeting_data = {
            'title': meeting_title,
            'start_at_utc': start_datetime.isoformat(),
            'end_at_utc': end_datetime.isoformat(),
            'start_at_local': start_datetime.strftime("%B %d, %Y at %I:%M %p"),
            'end_at_local': end_datetime.strftime("%B %d, %Y at %I:%M %p"),
            'location': location,
            'meeting_link': meeting_link,
            'minutes_link': minutes_link,
            'create_minutes': create_minutes,
            'channel_id': guild_config.get('meeting_reminders_channel_id', ''),
            'created_by': user_id,
            'guild_id': guild_id,
            'status': 'scheduled'
        }
        
        # Get the meetings sheet ID
        monthly_sheets = guild_config.get('monthly_sheets', {})
        meetings_sheet_id = monthly_sheets.get('meetings')
        
        if not meetings_sheet_id:
            return "❌ No meetings spreadsheet configured. Please run `/setup` first."
        
        # Add the meeting and get the generated meeting_id
        success, meeting_id = BOT_INSTANCE.sheets_manager.add_meeting(meetings_sheet_id, meeting_data)
        
        if success:
            # Update meeting_data with the generated meeting_id
            meeting_data['meeting_id'] = meeting_id
            # Create timers for the meeting
            timer_count = create_meeting_timers(meeting_data, guild_config)
            
            response = f"""✅ **Meeting Scheduled Successfully!**

**Meeting:** {meeting_title}
**Start:** {start_datetime.strftime('%B %d, %Y at %I:%M %p')}
**End:** {end_datetime.strftime('%B %d, %Y at %I:%M %p')}
**Location:** {location if location else 'TBD'}
**Link:** {meeting_link if meeting_link else 'TBD'}
**Timers Created:** {timer_count} automatic reminders

**What happens next:**
• 2-hour reminder will be sent
• Meeting start notification

The meeting and all timers have been added to your Google Sheets!"""
            
            return response
        else:
            return "❌ Failed to schedule meeting. Please try again."
        
    except Exception as e:
        print(f"Error creating meeting with timer: {e}")
        return f"❌ Error creating meeting with timer: {str(e)}"
