"""
Context management module for Discord context and agent executor management.
Handles Discord context, agent executors with isolated memory, and conversation management.
"""

# Global variable for Discord context
_discord_context = {}

# Server-specific agent executors with isolated memory
_server_agent_executors = {}

# DM-specific agent executors for users who are admin of multiple servers
_dm_agent_executors = {}


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


def get_meetings_sheet_id(guild_config: dict) -> str:
    """
    Get the meetings sheet ID from guild configuration.
    This is the standard way to get the meetings sheet ID across all tools.
    
    Args:
        guild_config: The guild configuration dictionary
        
    Returns:
        str: The meetings sheet ID, or None if not found
    """
    if not guild_config:
        return None
    
    # Check in order of preference
    if 'monthly_sheets' in guild_config and 'meetings' in guild_config['monthly_sheets']:
        return guild_config['monthly_sheets']['meetings']
    elif 'meetings_sheet_id' in guild_config:
        return guild_config['meetings_sheet_id']
    elif 'meetings_spreadsheet_id' in guild_config:
        return guild_config['meetings_spreadsheet_id']
    
    return None


def get_agent_executor_with_memory(guild_id: str = None, user_id: str = None):
    """Get or create a server-specific agent executor with isolated conversation memory."""
    global _server_agent_executors, _dm_agent_executors
    
    # Determine the context key for this conversation
    if guild_id:
        # Server context - use guild_id as the key
        context_key = f"guild_{guild_id}"
        executor_dict = _server_agent_executors
    elif user_id:
        # DM context - use user_id as the key
        context_key = f"user_{user_id}"
        executor_dict = _dm_agent_executors
    else:
        # Fallback to a default context (shouldn't happen in normal usage)
        context_key = "default"
        executor_dict = _server_agent_executors
    
    # Check if we already have an executor for this context
    if context_key not in executor_dict:
        print(f"🔧 Creating new agent executor for context: {context_key}")
        from langchain.memory import ConversationBufferMemory
        from langchain.agents import AgentExecutor
        
        # Create memory for this specific context
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
        
        # Create the agent executor with this memory
        agent_executor = create_agent_executor_with_tools(memory)
        executor_dict[context_key] = agent_executor
        
        print(f"✅ Created agent executor for {context_key}")
    
    return executor_dict[context_key]


def create_agent_executor_with_tools(memory=None):
    """Create an agent executor with safe tools only (no Discord sending)."""
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from datetime import datetime
    
    # Import safe tools only (no Discord sending)
    from .meeting_tools import (
        create_meeting_mins, send_meeting_schedule, get_meeting_reminder_info,
        schedule_meeting, search_meetings_by_title, cancel_meeting, update_meeting,
        start_meeting_scheduling, create_meeting_with_timer
    )
    from .task_tools import (
        create_task_with_timer, list_active_timers, clear_all_timers,
        parse_meeting_minutes_action_items, send_tasks_by_person, search_tasks_by_title,
        complete_task, create_tasks_from_meeting_minutes, summarize_last_meeting
    )
    from .setup_tools import (
        get_setup_info, get_meeting_sheet_info, get_task_sheet_info, get_channel_info,
        get_user_setup_status, get_club_setup_info, check_guild_setup_status,
        ask_for_discord_mention, get_exec_info
    )
    from .discord_tools import (
        send_reminder_to_person, send_announcement
    )
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    # Safe tools (no Discord sending)
    safe_tools = [
        create_meeting_mins,
        send_meeting_schedule,
        get_meeting_reminder_info,
        get_club_setup_info,
        check_guild_setup_status,
        schedule_meeting,
        search_meetings_by_title,
        cancel_meeting,
        update_meeting,
        send_reminder_to_person,
        send_announcement,
        get_setup_info,
        get_meeting_sheet_info,
        get_task_sheet_info,
        start_meeting_scheduling,
        get_channel_info,
        create_task_with_timer,
        create_meeting_with_timer,
        list_active_timers,
        clear_all_timers,
        ask_for_discord_mention,
        get_exec_info,
        parse_meeting_minutes_action_items,
        create_tasks_from_meeting_minutes,
        send_tasks_by_person,
        search_tasks_by_title,
        complete_task,
        summarize_last_meeting
    ]
    
    # Get current year for date context
    current_year = datetime.now().year
    
    # Create the same system prompt as orig_main_agent.py
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are AutoExec, an AI-powered club executive task manager designed to help student organizations and clubs manage their meetings, tasks, and administrative work efficiently.

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

CRITICAL DATE HANDLING:
- The current year is {current_year} - ALWAYS use {current_year} when generating dates
- NEVER use 2023 or any year before {current_year} when creating dates
- When users say "tomorrow", "next week", "next Friday", etc., calculate dates relative to {current_year}
- For meeting scheduling, use natural language like "tomorrow at 3pm" or "{current_year}-09-08 15:00" format
- The date parsing system will automatically handle relative dates and convert them to the correct {current_year} dates

IMPORTANT GUIDELINES:
- You can respond directly to simple questions about AutoExec, creator info, and general capabilities
- Use tools when you need to access specific data (meetings, tasks, setup status) or perform actions
- **ALWAYS use tools for meeting queries** - Don't say "I don't have access" when you have meeting tools available
- For questions like "when is our next meeting", "what meetings do we have", "show me upcoming meetings" → Use send_meeting_schedule with appropriate number
- For meeting reminder information (like "what reminders are set up") → Use get_meeting_reminder_info
- For task creation, use create_task_with_timer to automatically set up reminders
- For sending reminders to specific people, use send_reminder_to_person (not send_announcement)
- If the person isn't found in exec members, offer alternatives like @everyone or general announcements
- When users say "in X minutes", use delay_minutes parameter to schedule the reminder, don't send immediately
- For general announcements to everyone, use send_announcement with natural headers like "🎉 **Team Recognition**" or "📢 **Club Information**"
- For meeting scheduling, use start_meeting_scheduling to begin interactive conversation
- When scheduling meetings, have a back-and-forth conversation to gather all details:
  1. Start with start_meeting_scheduling when user wants to schedule a meeting
  2. Continue the conversation by asking follow-up questions based on what's missing:
     - If user provides start time, ask for end time
     - If user provides both times, ask for location/meeting link
     - If user provides location, ask about meeting minutes
     - If all details collected, use create_meeting_with_timer
  3. Always maintain context of what information you've already collected
  4. Use conversation history to track the meeting scheduling progress
- When users provide Discord mentions for unknown people, use that information to complete task creation
- Be conversational and maintain context across multiple messages in the same conversation
- If a user provides additional information (like Discord mentions), use it to complete previous requests
- Pay attention to conversation history - if a user says "I meant [name]" or "actually [name]", they're correcting a previous request
- When users make corrections, use the corrected information to complete the original task/meeting creation
- Look at the chat_history to understand what the user was trying to do originally
- IMPORTANT: If a user corrects an assignee name (e.g., "Oh I meant hamidat"), call create_task_with_timer again with the corrected name, NOT ask_for_discord_mention
- If a user asks "what did I ask you last" or similar questions, refer to the conversation history
- Always consider the full conversation context when responding to any message
- IMPORTANT: When asked about previous messages, ONLY refer to messages that are actually in the chat_history. Do not make up or hallucinate previous messages.
- If the chat_history is empty or doesn't contain the information being asked about, say so clearly
- MEETING SCHEDULING FLOW: When a user wants to schedule a meeting:
  1. Use start_meeting_scheduling to begin the process
  2. In subsequent messages, continue the conversation by asking for missing information:
     - If you see a start time mentioned, ask "What time should the meeting end?"
     - If you see both start and end times, ask "Where will the meeting be held? (location, online link, or Discord channel)"
     - If you see location info, ask "Do you need meeting minutes? (provide existing link, create new, or not needed)"
     - If all info is collected, use create_meeting_with_timer with the details
  3. Always check the conversation history to see what information has already been provided
  4. Don't just echo back what the user said - continue the conversation flow

EXAMPLES OF DIRECT RESPONSES (no tools needed):
- "Who made you?" → Answer directly with creator information
- "What can you do?" → Answer directly about capabilities
- "Hello" → Greet directly

EXAMPLES OF WHEN TO USE TOOLS:
- "What meetings do I have?" → Use send_meeting_schedule with amount_of_meetings_to_return=5
- "When is our next meeting?" → Use send_meeting_schedule with amount_of_meetings_to_return=1
- "Show me upcoming meetings" → Use send_meeting_schedule with amount_of_meetings_to_return=3
- "What's our meeting schedule?" → Use send_meeting_schedule with amount_of_meetings_to_return=5
- "Create a task for John due tomorrow" → Use create_task_with_timer
- "Send a reminder to Hamidat that she hasn't done her task" → Use send_reminder_to_person
- "Send a reminder in 5 minutes to Hamidat about her task" → Use send_reminder_to_person with delay_minutes=5
- "Send a reminder to Sanika about her task" (if Sanika not in exec list) → Show available execs and offer alternatives
- "Send out an announcement about Victoria's Instagram milestone" → Use send_announcement with "🎉 **Team Recognition**\n\nCongratulations to Victoria for reaching 403 followers on our Instagram! 🎉 Let's keep the momentum going! 🚀"
- "Schedule a meeting called Team Sync" → Use start_meeting_scheduling to begin interactive flow
- "Oh I meant hamidat" (after trying to create task for John) → Use create_task_with_timer with corrected name
- "What timers are active?" → Use list_active_timers
- "Is she an exec?" → Use get_exec_info
- "Who are the execs?" → Use get_exec_info
- "What are my upcoming tasks?" → Use send_tasks_by_person
- "Show me my tasks" → Use send_tasks_by_person
- "What tasks do I have?" → Use send_tasks_by_person

MEETING SCHEDULING CONVERSATION EXAMPLES:
- User: "Schedule a meeting tomorrow at 3pm" → Use start_meeting_scheduling, then ask "What time should it end?"
- User: "Tomorrow at 5pm" (after being asked for start time) → Ask "What time should the meeting end?"
- User: "6pm" (after being asked for end time) → Ask "Where will the meeting be held?"
- User: "Discord voice channel" (after being asked for location) → Ask "Do you need meeting minutes?"
- User: "Create new minutes" (after being asked about minutes) → Use create_meeting_with_timer with all details"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # give the llm access to the tool functions 
    agent = create_openai_functions_agent(llm, safe_tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=safe_tools, verbose=True, memory=memory, handle_parsing_errors=True, max_iterations=3)

    return agent_executor




def clear_conversation_memory(guild_id: str = None, user_id: str = None):
    """Clear the conversation memory for a specific context."""
    global _server_agent_executors, _dm_agent_executors
    
    if guild_id:
        context_key = f"guild_{guild_id}"
        if context_key in _server_agent_executors:
            _server_agent_executors[context_key].memory.clear()
            print(f"🧹 Cleared memory for guild {guild_id}")
    elif user_id:
        context_key = f"user_{user_id}"
        if context_key in _dm_agent_executors:
            _dm_agent_executors[context_key].memory.clear()
            print(f"🧹 Cleared memory for user {user_id}")


def clear_all_conversation_memories():
    """Clear all conversation memories."""
    global _server_agent_executors, _dm_agent_executors
    
    for executor in _server_agent_executors.values():
        executor.memory.clear()
    
    for executor in _dm_agent_executors.values():
        executor.memory.clear()
    
    print("🧹 Cleared all conversation memories")


def get_memory_stats():
    """Get statistics about active conversation memories."""
    global _server_agent_executors, _dm_agent_executors
    
    server_count = len(_server_agent_executors)
    dm_count = len(_dm_agent_executors)
    
    return f"Active memories: {server_count} servers, {dm_count} DMs"


def get_user_admin_servers(user_id: str):
    """Get all servers where the user is an admin."""
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return []
    
    try:
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        user_guilds = []
        
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                exec_members = guild_config.get('exec_members', [])
                for member in exec_members:
                    if member.get('discord_id') == user_id:
                        user_guilds.append({
                            'guild_id': guild_id,
                            'guild_name': guild_config.get('guild_name', f'Server {guild_id}'),
                            'config': guild_config
                        })
                        break
        
        return user_guilds
    except Exception as e:
        print(f"Error getting user admin servers: {e}")
        return []


def handle_dm_server_selection(user_id: str, query: str):
    """Handle server selection for DMs when user is admin of multiple servers."""
    user_guilds = get_user_admin_servers(user_id)
    
    if len(user_guilds) == 0:
        return "❌ You are not an admin of any configured servers. Please run `/setup` first."
    elif len(user_guilds) == 1:
        # Single server - use it directly
        guild_config = user_guilds[0]['config']
        guild_id = user_guilds[0]['guild_id']
        
        # Set the Discord context for this single server
        set_discord_context(guild_id, "", user_id)
        
        # Get agent executor and process the query
        agent_executor = get_agent_executor_with_memory(guild_id=guild_id, user_id=user_id)
        
        try:
            response = agent_executor.invoke({"input": f"{query}"})
            agent_executor.memory.save_context(
                {"input": query},
                {"output": response.get("output", "I'm sorry, I couldn't process that request.")}
            )
            return response.get("output", "I'm sorry, I couldn't process that request.")
        except Exception as e:
            return f"I'm sorry, I encountered an error: {str(e)}"
    else:
        # Multiple servers - ask user to specify
        server_list = "\n".join([f"• {guild['guild_name']} (ID: {guild['guild_id']})" for guild in user_guilds])
        return f"""🤔 You're an admin of multiple servers. Please specify which server you want to use:

{server_list}

You can mention the server name or ID in your message, or use a command like "use server [name/id]" to set the context."""


def parse_server_context_from_query(user_id: str, query: str):
    """Parse server context from a user query in DM."""
    user_guilds = get_user_admin_servers(user_id)
    
    if len(user_guilds) <= 1:
        return None, query  # No need to parse if user has 0 or 1 servers
    
    # Look for server mentions in the query
    query_lower = query.lower()
    
    for guild in user_guilds:
        guild_name = guild['guild_name'].lower()
        guild_id = guild['guild_id']
        
        # Check if guild name or ID is mentioned in the query
        if (guild_name in query_lower or 
            guild_id in query or 
            f"server {guild_id}" in query_lower or
            f"guild {guild_id}" in query_lower):
            
            # Set the context and return the guild_id and cleaned query
            set_discord_context(guild_id, "", user_id)
            return guild_id, query
    
    return None, query


def get_server_context_info(guild_id: str):
    """Get information about the current server context."""
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return f"Server {guild_id}"
    
    try:
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id, {})
        guild_name = guild_config.get('guild_name', f'Server {guild_id}')
        return guild_name
    except Exception:
        return f"Server {guild_id}"
