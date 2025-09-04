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

    # Simple approach: try to run the coroutine directly
    # This will work if we're in the right context, or fail gracefully if not
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule the task in the current loop
            loop.create_task(BOT_INSTANCE.send_any_message(str(messageToSend)))
        else:
            # Run in a new event loop
            asyncio.run(BOT_INSTANCE.send_any_message(str(messageToSend)))
    except RuntimeError as e:
        # No event loop available - this is expected in some contexts
        # Just log the error and return a message indicating the issue
        print(f"⚠️ Could not send message to Discord (no event loop): {e}")
        return "⚠️ Message could not be sent to Discord (no active event loop)"
    except Exception as e:
        # Any other error
        print(f"❌ Error sending message to Discord: {e}")
        return f"❌ Error sending message to Discord: {e}"

    return "✅ Message has been sent to Discord."

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
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            meetings_info += "❌ No club configuration found. Please run `/setup` first."
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
                    # Get upcoming meetings using the meeting manager
                    upcoming_meetings = BOT_INSTANCE.meeting_manager.get_upcoming_meetings(
                        meetings_sheet_id, 
                        limit=amount_of_meetings_to_return
                    )
                    
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
        
        # This would need to be implemented to get meetings from Google Sheets
        reminder_info = """
**Meeting Reminders:**

Meetings are now managed through Google Sheets instead of Google Calendar.

**To see upcoming meetings:**
• Use `/meeting upcoming` command
• Check the Google Sheets for your club

**Automatic reminders:**
• Meeting reminders are sent automatically based on the schedule in Google Sheets
• Reminders are sent at T-2h and T-0 (meeting start time)

**To schedule a meeting:**
• Use `/meeting set` with title, start time, location, and meeting link
        """
        
        return reminder_info
        
    except Exception as e:
        return f"I encountered an error getting meeting information: {str(e)}"
@tool
def handle_misc_questions() -> str:
    """
    Handle miscellaneous questions that don't perfectly match other available tools.
    Use this for general questions about the bot, setup status, or general assistance.

    Args:
        None

    Returns:
        string: A helpful response to the user's question
    """

    return "I'm AutoExec, your AI-powered club executive task manager! I'm here to help with meetings, tasks, scheduling, and organization. I can help you with specific questions about meetings, create meeting minutes, manage tasks, and more. What would you like to know?"

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

    tools = [send_meeting_mins_summary, start_discord_bot, send_output_to_discord, create_meeting_mins, send_meeting_schedule,handle_misc_questions, send_reminder_for_next_meeting]
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
            ("system", "You are a helpful assistant. ALWAYS use the `send_output_to_discord` tool to send responses to Discord unless another tool already sends the message."),
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
        ("system", """You are AutoExec, an AI-powered club executive task manager. You have access to tools that can help with meetings, tasks, and scheduling.

CRITICAL INSTRUCTION: You MUST use tools for EVERY query. You are NOT allowed to give generic responses.

AVAILABLE TOOLS (you MUST use one of these):
- create_meeting_mins: Use when users ask about creating meeting minutes, want to create minutes, or mention "meeting minutes"
- send_meeting_schedule: Use when users ask about upcoming meetings, meeting schedules, "what meetings do I have", or "show me meetings"
- get_meeting_reminder_info: Use when users ask about meeting reminders, "send a reminder", or "remind me about meetings"
- get_club_setup_info: Use when users ask about setup status, "what club are you set up for", or "are you configured"
- check_guild_setup_status: Use when users ask about setup status in a specific server or "are you set up for this group"
- handle_misc_questions: Use for general questions that don't fit other categories

MANDATORY EXAMPLES:
- "What club are you set up for?" → MUST use get_club_setup_info
- "Are you set up yet?" → MUST use get_club_setup_info
- "Are you set up for this group?" → MUST use check_guild_setup_status
- "Can you send a reminder for a meeting in 2 mins" → MUST use get_meeting_reminder_info
- "What meetings do I have today?" → MUST use send_meeting_schedule  
- "Create meeting minutes" → MUST use create_meeting_mins

YOU MUST USE A TOOL FOR EVERY RESPONSE. DO NOT GIVE GENERIC ANSWERS.

IMPORTANT: If you don't use a tool, you will fail. Always choose the most appropriate tool."""),
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
        handle_misc_questions, 
        get_meeting_reminder_info,
        get_club_setup_info,
        check_guild_setup_status
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