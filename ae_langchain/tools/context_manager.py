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
    """Create an agent executor with all available tools."""
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    from .discord_tools import (
        send_meeting_mins_summary, start_discord_bot, send_output_to_discord, 
        send_announcement
    )
    from .meeting_tools import (
        create_meeting_mins, send_meeting_schedule, send_reminder_for_next_meeting,
        schedule_meeting, search_meetings_by_title, cancel_meeting, update_meeting,
        create_meeting_with_timer, start_meeting_scheduling
    )
    from .task_tools import (
        create_task_with_timer, list_active_timers, clear_all_timers
    )
    from .setup_tools import (
        ask_for_discord_mention, get_exec_info
    )
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    tools = [
        send_meeting_mins_summary, start_discord_bot, send_output_to_discord, 
        create_meeting_mins, send_meeting_schedule, send_reminder_for_next_meeting, 
        schedule_meeting, search_meetings_by_title, cancel_meeting, update_meeting, 
        send_announcement, create_task_with_timer, create_meeting_with_timer, 
        start_meeting_scheduling, list_active_timers, clear_all_timers, 
        ask_for_discord_mention, get_exec_info
    ]
    
    prompt = create_langchain_prompt()

    # give the llm access to the tool functions 
    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, memory=memory)

    return agent_executor


def create_langchain_prompt():
    """Creates a langchain prompt for the chat model."""
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are AutoExec, an AI assistant for managing club operations, meetings, tasks, and announcements. 

**Your Role:**
- Help manage club meetings, schedules, and minutes
- Create and track tasks with deadlines and reminders
- Send announcements and reminders to Discord channels
- Provide information about club setup and configuration
- Assist with meeting scheduling and management

**Key Guidelines:**
- Always be helpful and professional
- Use appropriate tools for each task (meetings, tasks, announcements, etc.)
- Provide clear, actionable responses
- Remember conversation context within each server/DM
- Use Discord mentions when appropriate for task assignments

**Available Tools:**
- Meeting tools: schedule, search, cancel, update meetings
- Task tools: create tasks with timers and reminders
- Announcement tools: send messages to appropriate channels
- Setup tools: check configuration and user information

Remember to use the right tool for each request and provide helpful, clear responses."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    return prompt


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
