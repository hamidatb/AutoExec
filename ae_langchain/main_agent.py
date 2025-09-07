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

# Global variable for Discord context
_discord_context = {}

# Global agent executor with memory for conversation continuity
_agent_executor_with_memory = None

def set_discord_context(guild_id: str, channel_id: str, user_id: str):
    """Set the Discord context for LangChain tools."""
    global _discord_context
    _discord_context = {
        'guild_id': guild_id,
        'channel_id': channel_id,
        'user_id': user_id
    }

def get_discord_context():
    """Get the current Discord context."""
    return _discord_context

def get_agent_executor_with_memory():
    """Get or create the agent executor with conversation memory."""
    global _agent_executor_with_memory
    
    if _agent_executor_with_memory is None:
        from langchain.memory import ConversationBufferMemory
        from langchain.agents import AgentExecutor
        
        # Create memory
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create LLM
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )
        
        # Create prompt with memory
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are AutoExec, an AI-powered club executive task manager designed to help student organizations and clubs manage their meetings, tasks, and administrative work efficiently.

ABOUT AUTOEXEC:
- You are a specialized AI assistant for club executives and student organizations
- You help with meeting management, task tracking, scheduling, and organizational communication
- You integrate with Google Sheets for data management and Discord for communication
- You can create meeting minutes, schedule meetings, send reminders, and manage club activities

CREATOR INFORMATION:
- Created by Hamidat Bello 👋
- 4th Year Computing Science Specialization student at the University of Alberta
- Passionate about building impactful software and harnessing technology to spark positive social change
- Portfolio: https://hamidatb.github.io
- GitHub: https://github.com/hamidatb

PERSONALITY & COMMUNICATION:
- Be professional yet friendly and approachable
- Use clear, concise language appropriate for student leaders
- Show enthusiasm for helping with club management tasks
- Be proactive in suggesting improvements and best practices
- Use emojis sparingly but effectively to add warmth

CORE CAPABILITIES:
1. **Meeting Management**: Create meeting minutes, schedule meetings, send meeting reminders
2. **Task Management**: Create tasks with automatic reminders, track deadlines, manage assignments
3. **Communication**: Send announcements, reminders, and notifications via Discord
4. **Organization**: Help with club setup, member management, and administrative tasks

IMPORTANT GUIDELINES:
- You can respond directly to simple questions about AutoExec, creator info, and general capabilities
- Use tools when you need to access specific data (meetings, tasks, setup status) or perform actions
- For task creation, use create_task_with_timer to automatically set up reminders
- For meeting scheduling, use create_meeting_with_timer to set up meeting reminders
- When users provide Discord mentions for unknown people, use that information to complete task creation
- Be conversational and maintain context across multiple messages in the same conversation
- If a user provides additional information (like Discord mentions), use it to complete previous requests
- Pay attention to conversation history - if a user says "I meant [name]" or "actually [name]", they're correcting a previous request
- When users make corrections, use the corrected information to complete the original task/meeting creation
- Look at the chat_history to understand what the user was trying to do originally
- If a user asks "what did I ask you last" or similar questions, refer to the conversation history
- Always consider the full conversation context when responding to any message

EXAMPLES OF DIRECT RESPONSES (no tools needed):
- "Who made you?" → Answer directly with creator information
- "What can you do?" → Answer directly about capabilities
- "Hello" → Greet directly

EXAMPLES OF WHEN TO USE TOOLS:
- "What meetings do I have?" → Use send_meeting_schedule
- "Create a task for John due tomorrow" → Use create_task_with_timer
- "What timers are active?" → Use list_active_timers
- "Is she an exec?" → Use get_exec_info
- "Who are the execs?" → Use get_exec_info"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Get safe tools (no Discord sending)
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
            get_channel_info,
            create_task_with_timer,
            create_meeting_with_timer,
            list_active_timers,
            clear_all_timers,
            ask_for_discord_mention,
            get_exec_info
        ]
        
        # Create agent with memory
        from langchain.agents import create_openai_functions_agent
        agent = create_openai_functions_agent(llm, safe_tools, prompt)
        
        _agent_executor_with_memory = AgentExecutor(
            agent=agent,
            tools=safe_tools,
            memory=memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )
    
    return _agent_executor_with_memory

def clear_conversation_memory():
    """Clear the conversation memory to start fresh."""
    global _agent_executor_with_memory
    _agent_executor_with_memory = None
    print("🧹 Conversation memory cleared")

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
    
    **USE THIS TOOL FOR:**
    - General announcements and notifications
    - Meeting reminders and updates
    - Urgent messages that need immediate attention
    - Informational messages
    
    **DO NOT USE THIS FOR TASK CREATION** - Use create_task_with_timer instead!
    **DO NOT USE THIS FOR MEETING SCHEDULING** - Use create_meeting_with_timer instead!
    
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

@tool
def create_task_with_timer(task_title: str, assignee_name: str, due_date: str, priority: str = "medium", notes: str = "") -> str:
    """
    **TASK CREATION TOOL** - Use ONLY when users explicitly want to CREATE a new task with a deadline.
    
    Create a new task and automatically set up timers for reminders.
    This tool parses natural language and creates both the task and associated timers in Google Sheets.
    
    **USE THIS TOOL ONLY WHEN:**
    - User explicitly says "create a task" or "assign a task"
    - User says someone "has a task due [date]" (indicating task creation)
    - User mentions "assign [person] [task] due [date]"
    - User wants to create a task with a deadline
    
    **DO NOT USE THIS TOOL FOR:**
    - General questions about tasks
    - Questions like "is [person] an exec" or "who is [person]"
    - Simple conversations or greetings
    
    Args:
        task_title (str): The title/description of the task
        assignee_name (str): Name of the person assigned to the task (can be Discord username or real name)
        due_date (str): Due date in natural language (e.g., "September 9th", "next Friday", "2025-01-15 14:30")
        priority (str): Task priority - "low", "medium", "high", or "urgent" (default: "medium")
        notes (str): Additional notes or context for the task
        
    Returns:
        str: Confirmation message with task details and timer information
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime, timezone, timedelta
    import re
    
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get the Discord context from the current message
        context = get_discord_context()
        guild_id = context.get('guild_id')
        channel_id = context.get('channel_id')
        user_id = context.get('user_id')
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get the guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        # Parse the due date
        due_datetime = parse_due_date(due_date)
        if not due_datetime:
            return f"❌ Could not parse due date: '{due_date}'. Please use formats like 'September 9th', 'next Friday', or '2025-01-15 14:30'"
        
        
        # Clean the assignee name (remove @ symbol if present)
        clean_assignee_name = assignee_name.lstrip('@').strip()
        
        # Find the assignee by name (this is a simplified lookup)
        assignee_discord_id = find_user_by_name(clean_assignee_name, guild_config)
        if not assignee_discord_id:
            return f"❌ Could not find user '{clean_assignee_name}'. Please use a Discord username or mention."
        
        # Check if we need to ask for a Discord mention
        if assignee_discord_id.startswith("NEED_MENTION_FOR_"):
            return ask_for_discord_mention(clean_assignee_name)
        
        # Create task data
        task_data = {
            'title': task_title,
            'owner_discord_id': assignee_discord_id,
            'owner_name': clean_assignee_name,
            'due_at': due_datetime.isoformat(),
            'status': 'open',
            'priority': priority,
            'source_doc': '',
            'channel_id': channel_id,
            'notes': notes,
            'created_by': user_id,
            'guild_id': guild_id
        }
        
        # Get the tasks sheet ID
        monthly_sheets = guild_config.get('monthly_sheets', {})
        tasks_sheet_id = monthly_sheets.get('tasks')
        
        if not tasks_sheet_id:
            return "❌ No tasks spreadsheet configured. Please run `/setup` first."
        
        # Add the task and get the generated task_id
        success, task_id = BOT_INSTANCE.sheets_manager.add_task(tasks_sheet_id, task_data)
        
        if success:
            # Update task_data with the generated task_id
            task_data['task_id'] = task_id
            # Create timers for the task
            timer_count = create_task_timers(task_data, guild_config)
            
            response = f"""✅ **Task Created Successfully!**

**Task:** {task_title}
**Assigned to:** {assignee_name}
**Due:** {due_datetime.strftime('%B %d, %Y at %I:%M %p')}
**Priority:** {priority.title()}
**Timers Created:** {timer_count} automatic reminders

**What happens next:**
• 24-hour reminder will be sent
• 2-hour reminder will be sent  
• Overdue notification if not completed
• Escalation after 48 hours overdue

The task and all timers have been added to your Google Sheets!"""
            
            return response
        else:
            return "❌ Failed to create task. Please try again."
            
    except Exception as e:
        return f"❌ Error creating task: {str(e)}"

@tool
def create_meeting_with_timer(meeting_title: str, start_time: str, location: str = "", meeting_link: str = "") -> str:
    """
    Create a new meeting and automatically set up timers for reminders.
    This tool parses natural language and creates both the meeting and associated timers.
    
    Args:
        meeting_title (str): The title of the meeting
        start_time (str): Start time in natural language (e.g., "September 9th at 2pm", "next Friday 3:30pm", "2025-01-15 14:30")
        location (str): Meeting location or venue (optional)
        meeting_link (str): Meeting link for virtual meetings (optional)
        
    Returns:
        str: Confirmation message with meeting details and timer information
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
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get the guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        # Parse the start time
        start_datetime = parse_meeting_time(start_time)
        if not start_datetime:
            return f"❌ Could not parse start time: '{start_time}'. Please use formats like 'September 9th at 2pm', 'next Friday 3:30pm', or '2025-01-15 14:30'"
        
        # Create meeting data
        meeting_data = {
            'title': meeting_title,
            'start_at_utc': start_datetime.isoformat(),
            'end_at_utc': None,
            'start_at_local': start_datetime.strftime("%B %d, %Y at %I:%M %p"),
            'end_at_local': None,
            'location': location,
            'meeting_link': meeting_link,
            'channel_id': channel_id,
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
        return f"❌ Error scheduling meeting: {str(e)}"

@tool
def list_active_timers() -> str:
    """
    List all active timers from the Timers tab in Google Sheets.
    Use this when users ask about upcoming reminders, timers, or scheduled notifications.
    
    Returns:
        str: Formatted list of active timers
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get all configured guilds
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        configured_guilds = {gid: config for gid, config in all_guilds.items() if config.get('setup_complete', False)}
        
        if not configured_guilds:
            return "❌ No configured guilds found. Please run `/setup` first."
        
        all_timers = []
        
        for guild_id, guild_config in configured_guilds.items():
            config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
            if config_spreadsheet_id:
                timers = BOT_INSTANCE.sheets_manager.get_timers(config_spreadsheet_id)
                active_timers = [t for t in timers if t.get('state') == 'active']
                all_timers.extend(active_timers)
        
        if not all_timers:
            return "📅 **No Active Timers**\n\nThere are currently no active reminders or timers scheduled."
        
        # Sort by fire time
        all_timers.sort(key=lambda x: x.get('fire_at_utc', ''))
        
        response = f"⏰ **Active Timers ({len(all_timers)})**\n\n"
        
        for timer in all_timers[:10]:  # Show next 10 timers
            timer_type = timer.get('type', 'unknown')
            fire_at = timer.get('fire_at_utc', '')
            ref_type = timer.get('ref_type', 'unknown')
            ref_id = timer.get('ref_id', 'unknown')
            guild_id = timer.get('guild_id', '')
            
            # Parse fire time
            try:
                fire_datetime = datetime.fromisoformat(fire_at.replace('Z', '+00:00'))
                fire_str = fire_datetime.strftime('%B %d, %Y at %I:%M %p')
            except:
                fire_str = fire_at
            
            # Get the title and mention from the timer data
            title = timer.get('title', 'Unknown')
            mention = timer.get('mention', '')
            
            # Format timer type for display
            type_display = timer_type.replace('_', ' ').title()
            
            response += f"**{type_display}**\n"
            response += f"• {ref_type.title()}: {title}\n"
            response += f"• Fire at: {fire_str}\n"
            if mention:
                response += f"• Mention: {mention}\n"
            response += "\n"
        
        if len(all_timers) > 10:
            response += f"... and {len(all_timers) - 10} more timers"
        
        return response
        
    except Exception as e:
        return f"❌ Error listing timers: {str(e)}"

@tool
def get_exec_info(person_name: str = "") -> str:
    """
    Get information about club executives from the guild configuration.
    
    **USE THIS TOOL WHEN:**
    - User asks "is [person] an exec" or "who are the execs"
    - User wants to know about club leadership
    - User asks about specific executive members
    
    Args:
        person_name: Optional name to check if they're an executive (leave empty to get all execs)
        
    Returns:
        str: Information about executives
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get the Discord context from the current message
        context = get_discord_context()
        guild_id = context.get('guild_id')
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get the guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        exec_members = guild_config.get('exec_members', [])
        
        if not exec_members:
            return "❌ No executive members found in the configuration."
        
        if person_name:
            # Check if specific person is an exec
            person_lower = person_name.lower().strip()
            for member in exec_members:
                member_name = member.get('name', '').lower()
                if (person_lower == member_name or 
                    person_lower in member_name or 
                    any(person_lower == part.strip() for part in member_name.split())):
                    return f"✅ **Yes, {member.get('name')} is an executive member.**"
            
            return f"❌ **No, {person_name} is not listed as an executive member.**"
        else:
            # Return all exec members
            exec_list = []
            for member in exec_members:
                name = member.get('name', 'Unknown')
                role = member.get('role', 'Executive')
                exec_list.append(f"• **{name}** - {role}")
            
            return f"👥 **Executive Members:**\n\n" + "\n".join(exec_list)
            
    except Exception as e:
        return f"❌ Error getting executive information: {str(e)}"

@tool
def ask_for_discord_mention(person_name: str) -> str:
    """
    Ask the user to provide the Discord mention for a person whose name doesn't match any executive.
    
    **ONLY USE THIS TOOL WHEN:**
    - You are actively creating a task with create_task_with_timer
    - The assignee name cannot be matched to an executive in the config
    - You need the Discord mention to complete the task creation
    
    **DO NOT USE THIS TOOL FOR:**
    - General questions about people
    - Questions like "is [person] an exec"
    - Simple conversations
    
    Args:
        person_name: The name of the person who needs a Discord mention
        
    Returns:
        str: Message asking for the Discord mention
    """
    return f"❓ **Discord Mention Needed**\n\nI couldn't find a matching executive for **{person_name}**. Please provide their Discord mention (e.g., @username or <@123456789>) so I can create the task reminder properly.\n\nYou can reply with: `{person_name}'s Discord is @username`"

@tool
def clear_all_timers() -> str:
    """
    Clear all active timers from the Timers tab in Google Sheets.
    Use this when users ask to clear, delete, or remove all timers.
    
    **USE THIS TOOL WHEN:**
    - User says "clear all timers"
    - User says "delete all timers"
    - User says "remove all timers"
    - User wants to reset the timer system
    
    Returns:
        str: Confirmation message with number of timers cleared
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
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
        if not config_spreadsheet_id:
            return "❌ No config spreadsheet configured."
        
        # Get all active timers
        timers = BOT_INSTANCE.sheets_manager.get_timers(config_spreadsheet_id)
        active_timers = [t for t in timers if t.get('state') == 'active']
        
        if not active_timers:
            return "📅 **No Active Timers**\n\nThere are no active timers to clear."
        
        # Clear all active timers by setting their state to 'cancelled'
        cleared_count = 0
        for timer in active_timers:
            timer_id = timer.get('id')
            if timer_id:
                success = BOT_INSTANCE.sheets_manager.update_timer_state(config_spreadsheet_id, timer_id, 'cancelled')
                if success:
                    cleared_count += 1
        
        return f"✅ **Timers Cleared Successfully!**\n\n**Cleared:** {cleared_count} active timers\n\nAll timers have been cancelled and will no longer fire."
        
    except Exception as e:
        return f"❌ Error clearing timers: {str(e)}"

# Helper functions for the new tools
def parse_due_date(date_str: str) -> datetime:
    """Parse natural language due dates into datetime objects."""
    from datetime import datetime, timezone, timedelta
    import re
    
    date_str = date_str.strip().lower()
    now = datetime.now(timezone.utc)
    
    # Handle specific date formats
    try:
        # Try ISO format first
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            if ' ' in date_str and len(date_str.split()) >= 2:
                # Has time
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            else:
                # Just date, assume end of day
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=23, minute=59, tzinfo=timezone.utc)
            
            # Fix obvious year mistakes (e.g., 2023 when we're in 2025)
            if parsed_date.year < now.year - 1:
                parsed_date = parsed_date.replace(year=now.year)
            
            return parsed_date
    except:
        pass
    
    # Handle relative dates
    if 'tomorrow' in date_str:
        return (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
    elif 'next week' in date_str:
        return (now + timedelta(weeks=1)).replace(hour=17, minute=0, second=0, microsecond=0)
    elif 'next friday' in date_str:
        days_ahead = 4 - now.weekday()  # Friday is 4
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return (now + timedelta(days=days_ahead)).replace(hour=17, minute=0, second=0, microsecond=0)
    
    # Handle month day formats
    month_patterns = [
        (r'september (\d{1,2})', 9),
        (r'october (\d{1,2})', 10),
        (r'november (\d{1,2})', 11),
        (r'december (\d{1,2})', 12),
        (r'january (\d{1,2})', 1),
        (r'february (\d{1,2})', 2),
        (r'march (\d{1,2})', 3),
        (r'april (\d{1,2})', 4),
        (r'may (\d{1,2})', 5),
        (r'june (\d{1,2})', 6),
        (r'july (\d{1,2})', 7),
        (r'august (\d{1,2})', 8),
    ]
    
    for pattern, month in month_patterns:
        match = re.search(pattern, date_str)
        if match:
            day = int(match.group(1))
            year = now.year
            # If the month/day has already passed this year, use next year
            if month < now.month or (month == now.month and day <= now.day):
                year += 1
            return datetime(year, month, day, 17, 0, 0, tzinfo=timezone.utc)
    
    return None

def parse_meeting_time(time_str: str) -> datetime:
    """Parse natural language meeting times into datetime objects."""
    from datetime import datetime, timezone, timedelta
    import re
    
    time_str = time_str.strip().lower()
    now = datetime.now(timezone.utc)
    
    # Handle ISO format
    try:
        if re.match(r'\d{4}-\d{2}-\d{2}', time_str):
            if ' ' in time_str and len(time_str.split()) >= 2:
                return datetime.strptime(time_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except:
        pass
    
    # Handle relative times
    if 'tomorrow' in time_str:
        base_date = now + timedelta(days=1)
    elif 'next week' in time_str:
        base_date = now + timedelta(weeks=1)
    elif 'next friday' in time_str:
        days_ahead = 4 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        base_date = now + timedelta(days=days_ahead)
    else:
        base_date = now
    
    # Extract time
    time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?', time_str)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        period = time_match.group(3)
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Default to 2 PM if no time specified
    return base_date.replace(hour=14, minute=0, second=0, microsecond=0)

def find_user_by_name(name: str, guild_config: dict) -> str:
    """Find a user's Discord mention by their name."""
    exec_members = guild_config.get('exec_members', [])
    name_lower = name.lower().strip()
    
    # Remove any Discord mention formatting if present
    name_lower = name_lower.replace('<@', '').replace('>', '').replace('@', '')
    
    for member in exec_members:
        member_name = member.get('name', '').lower()
        # Check if the provided name matches the first name, last name, or full name
        if (name_lower == member_name or  # Exact match
            name_lower in member_name or  # Partial match (e.g., "hamidat" in "hamidat bello")
            any(name_lower == part.strip() for part in member_name.split())):  # First/last name match
            discord_id = member.get('discord_id', '')
            if discord_id:
                return f"<@{discord_id}>"
    # If not found in exec members, return a placeholder that indicates we need the mention
    return f"NEED_MENTION_FOR_{name}"

def create_task_timers(task_data: dict, guild_config: dict) -> int:
    """Create timers for a task and return the count."""
    from datetime import datetime, timezone, timedelta
    from discordbot.discord_client import BOT_INSTANCE
    
    try:
        due_at = datetime.fromisoformat(task_data['due_at'])
        task_id = task_data.get('task_id', 'unknown')
        guild_id = task_data.get('guild_id', '')
        
        # Create timer types
        timer_types = [
            ('task_reminder_24h', due_at - timedelta(hours=24)),
            ('task_reminder_2h', due_at - timedelta(hours=2)),
            ('task_overdue', due_at),
            ('task_escalate', due_at + timedelta(hours=48))
        ]
        
        
        config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
        if not config_spreadsheet_id:
            return 0
        
        # Get the assignee mention
        assignee_name = task_data.get('owner_name', '')
        assignee_mention = find_user_by_name(assignee_name, guild_config)
        
        timer_count = 0
        for timer_type, fire_at in timer_types:
            timer_id = f"{task_id}_{timer_type}"
            timer_data = {
                'id': timer_id,
                'guild_id': guild_id,
                'type': timer_type,
                'ref_type': 'task',
                'ref_id': task_id,
                'fire_at_utc': fire_at.isoformat(),
                'channel_id': task_data.get('channel_id', ''),
                'state': 'active',
                'title': task_data.get('title', 'Unknown Task'),
                'mention': assignee_mention
            }
            
            success = BOT_INSTANCE.sheets_manager.add_timer(config_spreadsheet_id, timer_data)
            if success:
                timer_count += 1
        
        return timer_count
        
    except Exception as e:
        print(f"Error creating task timers: {e}")
        return 0

def create_meeting_timers(meeting_data: dict, guild_config: dict) -> int:
    """Create timers for a meeting and return the count."""
    from datetime import datetime, timezone, timedelta
    from discordbot.discord_client import BOT_INSTANCE
    
    try:
        start_at = datetime.fromisoformat(meeting_data['start_at_utc'])
        meeting_id = meeting_data.get('meeting_id', 'unknown')
        guild_id = meeting_data.get('guild_id', '')
        
        # Create timer types
        timer_types = [
            ('meeting_reminder_2h', start_at - timedelta(hours=2)),
            ('meeting_start', start_at)
        ]
        
        config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
        if not config_spreadsheet_id:
            return 0
        
        timer_count = 0
        for timer_type, fire_at in timer_types:
            timer_id = f"{meeting_id}_{timer_type}"
            timer_data = {
                'id': timer_id,
                'guild_id': guild_id,
                'type': timer_type,
                'ref_type': 'meeting',
                'ref_id': meeting_id,
                'fire_at_utc': fire_at.isoformat(),
                'channel_id': meeting_data.get('channel_id', ''),
                'state': 'active',
                'title': meeting_data.get('title', 'Unknown Meeting'),
                'mention': '@everyone'  # Meeting reminders go to everyone
            }
            
            success = BOT_INSTANCE.sheets_manager.add_timer(config_spreadsheet_id, timer_data)
            if success:
                timer_count += 1
        
        return timer_count
        
    except Exception as e:
        print(f"Error creating meeting timers: {e}")
        return 0

def get_task_title_by_id(task_id: str, guild_id: str, bot_instance) -> str:
    """Get task title by task ID."""
    try:
        if not bot_instance:
            return "Unknown Task"
        
        # Get guild configuration
        all_guilds = bot_instance.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config:
            return "Unknown Task"
        
        # Get tasks sheet ID
        monthly_sheets = guild_config.get('monthly_sheets', {})
        tasks_sheet_id = monthly_sheets.get('tasks')
        
        if not tasks_sheet_id:
            return "Unknown Task"
        
        # Get all tasks and find the one with matching ID
        tasks = bot_instance.sheets_manager.get_all_tasks(tasks_sheet_id)
        
        for task in tasks:
            if task.get('task_id') == task_id:
                return task.get('title', 'Unknown Task')
        
        return "Unknown Task"
        
    except Exception as e:
        print(f"Error getting task title: {e}")
        return "Unknown Task"

def get_meeting_title_by_id(meeting_id: str, guild_id: str, bot_instance) -> str:
    """Get meeting title by meeting ID."""
    try:
        if not bot_instance:
            return "Unknown Meeting"
        
        # Get guild configuration
        all_guilds = bot_instance.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config:
            return "Unknown Meeting"
        
        # Get meetings sheet ID
        monthly_sheets = guild_config.get('monthly_sheets', {})
        meetings_sheet_id = monthly_sheets.get('meetings')
        
        if not meetings_sheet_id:
            return "Unknown Meeting"
        
        # Get all meetings and find the one with matching ID
        meetings = bot_instance.sheets_manager.get_all_meetings(meetings_sheet_id)
        for meeting in meetings:
            if meeting.get('meeting_id') == meeting_id:
                return meeting.get('title', 'Unknown Meeting')
        
        return "Unknown Meeting"
        
    except Exception as e:
        print(f"Error getting meeting title: {e}")
        return "Unknown Meeting"

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

    tools = [send_meeting_mins_summary, start_discord_bot, send_output_to_discord, create_meeting_mins, send_meeting_schedule, send_reminder_for_next_meeting, schedule_meeting, send_announcement, create_task_with_timer, create_meeting_with_timer, list_active_timers, clear_all_timers, ask_for_discord_mention, get_exec_info]
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
            
            CREATOR INFORMATION:
            - Created by Hamidat Bello 👋
            - 4th Year Computing Science Specialization student at the University of Alberta
            - Passionate about building impactful software and harnessing technology to spark positive social change
            - GitHub: https://github.com/hamidatb

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

CREATOR INFORMATION:
- Created by Hamidat Bello 👋
- 4th Year Computing Science Specialization student at the University of Alberta
- Passionate about building impactful software and harnessing technology to spark positive social change
- Portfolio: https://hamidatb.github.io
- GitHub: https://github.com/hamidatb

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
- "Who made you?", "Who created AutoExec?" → You can respond directly with creator information

Remember: Use tools when you need specific data or to perform actions. You can respond directly to general questions about AutoExec's capabilities and creator information."""),
        ("user", "{input}"),
        MessagesPlaceholder("agent_scratchpad")
    ])
    
    # Get the agent executor with memory for conversation continuity
    agent_executor = get_agent_executor_with_memory()
    
    try:
        print(f"🔍 Invoking agent with query: {query}")
        print(f"🔧 Available tools: {[tool.name for tool in agent_executor.tools]}")
        
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