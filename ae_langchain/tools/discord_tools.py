"""
Discord tools module for AutoExec agent.
Contains all Discord-specific functions including bot management, announcements, and output.
"""

from langchain.tools import tool
from .context_manager import get_discord_context
from .utility_tools import find_user_by_name

# Import global variables
from ..globals import _pending_announcements


@tool 
def start_discord_bot():
    """
    Starts the Discord bot asynchronously, allowing the LangChain agent to remain active.

    Args:
        None
    Returns:
        str: Confirmation message that the bot was started.
    """
    import asyncio
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
    import asyncio
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
def send_output_to_discord(messageToSend: str) -> str:
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
    
    _pending_announcements.append({
        'message': str(messageToSend),
        'channel_id': None,  # Will use last_channel_id
        'channel_name': 'current channel'
    })
    
    return "✅ Message has been queued for Discord."


@tool
def send_reminder_to_person(person_name: str, reminder_message: str, delay_minutes: int = 0, send_at_time: str = "") -> str:
    """
    Send a reminder message to a specific person in the Discord server.
    This tool finds the person by name and sends them a direct reminder.
    
    **USE THIS TOOL FOR:**
    - Sending reminders to specific individuals (e.g., "remind John about his task")
    - Personal notifications that don't need @everyone
    - Individual task reminders or follow-ups
    - Scheduling reminders for later (e.g., "remind me in 5 minutes")
    - Scheduling reminders for specific times (e.g., "remind me at 2pm")
    
    **DO NOT USE THIS FOR:**
    - General announcements to everyone (use send_announcement instead)
    - Meeting reminders (use meeting tools instead)
    - Creating new tasks (use create_task_with_timer instead)
    
    Args:
        person_name (str): Name of the person to send the reminder to (can be Discord username or real name)
        reminder_message (str): The reminder message to send
        delay_minutes (int): How many minutes to wait before sending (0 = send immediately)
        send_at_time (str): Specific time to send the reminder (e.g., "2pm", "14:00", "2:00 PM")
        
    Returns:
        str: Confirmation that the reminder was sent or scheduled
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime, timezone, timedelta
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get the Discord context from the current message
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
                return f"""❓ **Multiple Servers Detected**

You are an admin of **{len(user_guilds)}** servers. Please specify which server you're referring to:

{guild_list}

**How to specify:**
• Mention the club name: "For [Club Name], send reminder to [person]"
• Mention the server name: "In [Server Name], remind [person] about [message]"

**Example:** "For Computer Science Club, send reminder to Sanika about her task"

Which server would you like me to help you with?"""
        
        # Get the guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        # Clean the person name (remove @ symbol if present)
        clean_person_name = person_name.lstrip('@').strip()
        
        # Find the person by name
        print(f"🔍 [DEBUG] Looking for person: '{clean_person_name}' in guild {guild_id}")
        person_discord_id = find_user_by_name(clean_person_name, guild_config)
        print(f"🔍 [DEBUG] Found person_discord_id: {person_discord_id}")
        
        if not person_discord_id:
            return f"❌ Could not find user '{clean_person_name}'. Please use a Discord username or mention."
        
        # Check if we need to ask for a Discord mention
        if person_discord_id.startswith("NEED_MENTION_FOR_"):
            print(f"🔍 [DEBUG] Need mention for: {clean_person_name}")
            # Get the list of available exec members for context
            exec_members = guild_config.get('exec_members', [])
            exec_list = "\n".join([f"• {member['name']} ({member['role']})" for member in exec_members])
            
            return f"""❓ **Person Not Found**

I couldn't find **{clean_person_name}** in the executive members list.

**Available executives:**
{exec_list if exec_list else "No executives configured"}

**Options:**
• Use one of the executives listed above
• Say "send to @everyone" for a general reminder
• Say "send without mentioning anyone" for a general message
• Provide the Discord mention: `{clean_person_name}'s Discord is @username`

Please clarify who you'd like to send the reminder to."""
        
        # Get the task reminders channel
        task_reminders_channel_id = guild_config.get('task_reminders_channel_id')
        if not task_reminders_channel_id:
            return "❌ No task reminders channel configured. Please run `/setup` first."
        
        # Create the reminder message (no @everyone, just mention the person)
        formatted_message = f"📝 **Reminder**\n\nHey {person_discord_id}, {reminder_message}"
        
        if delay_minutes > 0 or send_at_time:
            # Schedule the reminder for later using a timer
            import pytz
            guild_timezone = guild_config.get('timezone', 'America/Edmonton')
            local_tz = pytz.timezone(guild_timezone)
            
            # Get current time in guild timezone
            now_utc = datetime.now(timezone.utc)
            now_local = now_utc.astimezone(local_tz)
            
            if send_at_time:
                # Parse absolute time (e.g., "2pm", "14:00", "2:00 PM")
                try:
                    # Parse the time string
                    time_str = send_at_time.strip().lower()
                    
                    # Handle different time formats
                    if 'pm' in time_str or 'am' in time_str:
                        # 12-hour format
                        fire_at_local = datetime.strptime(time_str, "%I:%M %p").time()
                    elif ':' in time_str:
                        # 24-hour format
                        fire_at_local = datetime.strptime(time_str, "%H:%M").time()
                    else:
                        # Just hour (e.g., "2pm", "14")
                        if 'pm' in time_str:
                            hour = int(time_str.replace('pm', '').strip())
                            if hour != 12:
                                hour += 12
                        elif 'am' in time_str:
                            hour = int(time_str.replace('am', '').strip())
                            if hour == 12:
                                hour = 0
                        else:
                            hour = int(time_str)
                        fire_at_local = datetime.strptime(f"{hour:02d}:00", "%H:%M").time()
                    
                    # Create datetime for today with the specified time
                    fire_at_local = now_local.replace(
                        hour=fire_at_local.hour,
                        minute=fire_at_local.minute,
                        second=0,
                        microsecond=0
                    )
                    
                    # If the time has already passed today, schedule for tomorrow
                    if fire_at_local <= now_local:
                        fire_at_local += timedelta(days=1)
                        
                except ValueError as e:
                    return f"❌ Could not parse time '{send_at_time}'. Please use formats like '2pm', '14:00', or '2:00 PM'"
            else:
                # Use relative delay
                fire_at_local = now_local + timedelta(minutes=delay_minutes)
            
            # Convert to UTC for storage
            fire_at = fire_at_local.astimezone(timezone.utc)
            
            # Debug logging
            print(f"🔍 [REMINDER DEBUG] Person: {clean_person_name}")
            print(f"🔍 [REMINDER DEBUG]   Guild timezone: {guild_timezone}")
            print(f"🔍 [REMINDER DEBUG]   Current local time: {now_local}")
            print(f"🔍 [REMINDER DEBUG]   Fire local time: {fire_at_local}")
            print(f"🔍 [REMINDER DEBUG]   Fire UTC time: {fire_at}")
            
            timer_id = f"reminder_{clean_person_name}_{int(datetime.now().timestamp())}"
            
            timer_data = {
                'id': timer_id,
                'guild_id': guild_id,
                'type': 'scheduled_reminder',
                'ref_type': 'reminder',
                'ref_id': timer_id,
                'fire_at_utc': fire_at.isoformat(),
                'channel_id': task_reminders_channel_id,
                'state': 'active',
                'title': f"Reminder for {clean_person_name}",
                'mention': person_discord_id
            }
            
            # Store the message content in a way that the timer can access it
            # We'll use the mention field to store the full message
            timer_data['mention'] = formatted_message
            
            config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
            if config_spreadsheet_id:
                success = BOT_INSTANCE.sheets_manager.add_timer(config_spreadsheet_id, timer_data)
                if success:
                    if send_at_time:
                        # Format the local time for display
                        fire_time_str = fire_at_local.strftime("%I:%M %p")
                        return f"✅ Reminder scheduled for {clean_person_name} at {fire_time_str}."
                    else:
                        return f"✅ Reminder scheduled for {clean_person_name} in {delay_minutes} minutes."
                else:
                    return f"❌ Failed to schedule reminder. Please try again."
            else:
                return f"❌ No config spreadsheet found. Please run `/setup` first."
        else:
            # Send immediately
            announcement_data = {
                'message': formatted_message,
                'channel_id': int(task_reminders_channel_id),
                'channel_name': 'task reminders'
            }
            _pending_announcements.append(announcement_data)
            print(f"🔍 [send_reminder_to_person] Added reminder to global queue. Total pending: {len(_pending_announcements)}")
            
            return f"✅ Reminder sent to {clean_person_name} in the task reminders channel."
        
    except Exception as e:
        return f"❌ Error sending reminder: {str(e)}"


@tool
def send_announcement(announcement_message: str, announcement_type: str = "general") -> str:
    """
    Send an announcement message to Discord to the appropriate channel based on the type.
    
    **USE THIS TOOL FOR:**
    - General announcements and notifications
    - Meeting reminders and updates
    - Urgent messages that need immediate attention
    - Informational messages
    
    **DO NOT USE THIS FOR TASK CREATION** - Use create_task_with_timer instead!
    **DO NOT USE THIS FOR MEETING SCHEDULING** - Use create_meeting_with_timer instead!
    
    **IMPORTANT:** You can (but do not always have to) add natural headers to your announcement_message like:
    - "🎉 **Team Recognition**\n\nCongratulations to Victoria for reaching 403 followers..."
    - "📢 **Club Information**\n\nOur next meeting has been rescheduled..."
    - "📅 **Meeting Update**\n\nOur weekly meeting has been moved to Friday at 3pm..."
    - "🚨 **Urgent Update**\n\nPlease note the following changes..."
    - "📋 **Task Reminder**\n\nDon't forget to complete your assigned tasks..."
    - "🎊 **Club Event**\n\nJoin us for our upcoming social event..."
    
    Args:
        announcement_message (str): The announcement message to send (REQUIRED) - you can include natural headers like "🎉 **Team Recognition**\n\n[message]"
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
                    # For general announcements, use dedicated general announcements channel
                    channel_id = guild_config.get('general_announcements_channel_id')
                    channel_name = "general announcements"
                
                if not channel_id:
                    return f"❌ No {channel_name} channel configured. Please run `/setup` first."
                
                # Send the announcement to the specific channel with @everyone tag
                formatted_message = f"@everyone {announcement_message}"
                
                # Since we're running in a thread pool, we can't directly send Discord messages
                # Instead, we'll use a thread-safe approach by storing the message to be sent
                # and returning a response that indicates the message should be sent
                
                # Store the message in a global variable that works across threads
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


def get_pending_announcements():
    """Get the list of pending announcements."""
    return _pending_announcements


def clear_pending_announcements():
    """Clear the list of pending announcements."""
    _pending_announcements.clear()
