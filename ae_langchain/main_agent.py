"""
This is the refactored main agent file.
It imports from the modularized tools and maintains the same functionality.
"""
import os
import asyncio
from asyncio import create_task
from typing import Optional
from dotenv import load_dotenv

from config.config import Config

# Load environment variables
Config().validate()

# if the api key is outdated, run unset OPENAI_API_KEY in terminal
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("API Key not found. Check your .env file!")

# Import global variables
from .globals import _pending_announcements, _discord_context, _server_agent_executors, _dm_agent_executors

# Import all tools from the modularized structure
from .tools import (
    # Context management
    set_discord_context,
    get_discord_context,
    get_meetings_sheet_id,
    get_agent_executor_with_memory,
    clear_conversation_memory,
    clear_all_conversation_memories,
    get_memory_stats,
    get_user_admin_servers,
    handle_dm_server_selection,
    parse_server_context_from_query,
    get_server_context_info,
    
    # Meeting tools
    create_meeting_mins,
    send_meeting_schedule,
    send_reminder_for_next_meeting,
    cleanup_past_meetings,
    get_meeting_reminder_info,
    schedule_meeting,
    search_meetings_by_title,
    cancel_meeting,
    update_meeting,
    start_meeting_scheduling,
    create_meeting_with_timer,
    
    # Task tools
    create_task_with_timer,
    list_active_timers,
    clear_all_timers,
    parse_meeting_minutes_action_items,
    send_tasks_by_person,
    search_tasks_by_title,
    complete_task,
    create_tasks_from_meeting_minutes,
    summarize_last_meeting,
    
    # Setup tools
    get_setup_info,
    get_meeting_sheet_info,
    get_task_sheet_info,
    get_channel_info,
    get_user_setup_status,
    get_club_setup_info,
    check_guild_setup_status,
    ask_for_discord_mention,
    get_exec_info,
    
    # Discord tools
    start_discord_bot,
    send_meeting_mins_summary,
    send_output_to_discord,
    send_reminder_to_person,
    send_announcement,
    get_pending_announcements,
    clear_pending_announcements
)


async def run_agent(query: str):
    """
    Run the agent with the given query.
    This is the main entry point for the agent.
    """
    # Get Discord context from the query or use default
    context = get_discord_context()
    guild_id = context.get('guild_id')
    user_id = context.get('user_id')
    
    # Handle DM context if no guild_id
    if not guild_id and user_id:
        # Check if user is admin of multiple servers
        user_guilds = get_user_admin_servers(user_id)
        if len(user_guilds) > 1:
            # Multiple servers - try to parse context from query
            server_context = parse_server_context_from_query(user_id, query)
            if server_context:
                # Found server context, use it
                pass
            else:
                # No server context found, handle multiple server scenario
                return handle_dm_server_selection(user_id, query)
    
    # Get the appropriate agent executor with server-specific memory
    agent_executor = get_agent_executor_with_memory(guild_id=guild_id, user_id=user_id)
    
    try:
        response = agent_executor.invoke({"input": f"{query}"})
        
        # Manually save the conversation to memory
        agent_executor.memory.save_context(
            {"input": query},
            {"output": response.get("output", "I'm sorry, I couldn't process that request.")}
        )
        
        return response.get("output", "I'm sorry, I couldn't process that request.")
    except Exception as e:
        print(f"❌ Error in agent execution: {e}")
        import traceback
        traceback.print_exc()
        return f"I'm sorry, I encountered an error: {str(e)}"


def run_agent_text_only(query: str, guild_id: str = None, user_id: str = None):
    """
    Runs the LangChain agent in text-only mode (no Discord sending).
    Use this when calling from the Discord bot to avoid event loop issues.

    Args:
        query (str): The input query.
        guild_id (str): The Discord guild/server ID for server-specific context.
        user_id (str): The Discord user ID for DM-specific context.

    Returns:
        str: The text response from the agent.
    """
    # If we have a guild_id, set the Discord context for tools to use
    if guild_id:
        # Set a minimal Discord context for tools that need it
        set_discord_context(
            guild_id=guild_id,
            channel_id="",  # We don't have a specific channel in DM context
            user_id=user_id or ""
        )
        print(f"🔍 [run_agent_text_only] Set Discord context for guild_id: {guild_id}")
    
    # Handle DM context with multiple servers
    if user_id and not guild_id:
        # Check if this is a general DM question that doesn't require server context
        query_lower = query.lower()
        general_dm_questions = [
            'what was my last message',
            'what did i ask you',
            'what did i say',
            'what was my previous message',
            'what did i tell you',
            'what was my last question',
            'what did i ask',
            'what did we talk about',
            'what was our conversation',
            'what did we discuss',
            'hello',
            'hi',
            'hey',
            'what can you do',
            'who made you',
            'who created you',
            'help',
            'what are you',
            'how are you',
            'thanks',
            'thank you',
            'goodbye',
            'bye'
        ]
        
        is_general_question = any(phrase in query_lower for phrase in general_dm_questions)
        
        if is_general_question:
            # Use DM context directly for general questions
            print(f"🔍 Using DM context for general question: {query}")
        else:
            # Try to parse server context from the query for server-specific actions
            parsed_guild_id, cleaned_query = parse_server_context_from_query(user_id, query)
            if parsed_guild_id:
                # Use the parsed server context
                guild_id = parsed_guild_id
                query = cleaned_query
                print(f"🔍 Parsed server context: guild_id={guild_id}, cleaned_query='{query}'")
            else:
                # No server context found, handle multiple server scenario
                return handle_dm_server_selection(user_id, query)
    
    # Get the appropriate agent executor with server-specific memory
    agent_executor = get_agent_executor_with_memory(guild_id=guild_id, user_id=user_id)
    
    try:
        response = agent_executor.invoke({"input": f"{query}"})
        
        # Manually save the conversation to memory
        agent_executor.memory.save_context(
            {"input": query},
            {"output": response.get("output", "I'm sorry, I couldn't process that request.")}
        )
        
        return response.get("output", "I'm sorry, I couldn't process that request.")
    except Exception as e:
        print(f"❌ Error in agent execution: {e}")
        import traceback
        traceback.print_exc()
        return f"I'm sorry, I encountered an error: {str(e)}"


async def run_tasks():
    """Start the Discord bot by running the agent with the start command."""
    query = "Start the discord bot"
    result = run_agent_text_only(query)
    print(result)


async def send_hourly_message():
    """Send a message to Discord every hour."""
    while True:
        query = "Send a message saying 'hi'"
        result = run_agent_text_only(query)
        print(result)
        await asyncio.sleep(3600)  # Wait for 1 hour (3600 seconds)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    print(f"This is the main async agent")

    try:
        loop.run_until_complete(run_tasks())
    except KeyboardInterrupt:
        print("Shutting down...")
