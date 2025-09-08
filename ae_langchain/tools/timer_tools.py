"""
Timer tools module for AutoExec agent.
Contains all timer-related functions including creation, listing, and management.
"""

from langchain.tools import tool
from .context_manager import get_discord_context, get_user_admin_servers
from .utility_tools import parse_due_date, find_user_by_name, create_task_timers


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
        print(f"🔍 [DEBUG] Looking for assignee: '{clean_assignee_name}' in guild {guild_id}")
        print(f"🔍 [DEBUG] Guild config exec members: {guild_config.get('exec_members', [])}")
        
        assignee_discord_id = find_user_by_name(clean_assignee_name, guild_config)
        print(f"🔍 [DEBUG] Found assignee_discord_id: {assignee_discord_id}")
        
        if not assignee_discord_id:
            return f"❌ Could not find user '{clean_assignee_name}'. Please use a Discord username or mention."
        
        # Check if we need to ask for a Discord mention
        if assignee_discord_id.startswith("NEED_MENTION_FOR_"):
            print(f"🔍 [DEBUG] Need mention for: {clean_assignee_name}")
            from .setup_tools import ask_for_discord_mention
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
            'channel_id': guild_config.get('task_reminders_channel_id', ''),
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
def list_active_timers() -> str:
    """
    List all active timers from the Timers tab in Google Sheets.
    Use this when users ask about upcoming reminders, timers, or scheduled notifications.
    
    Returns:
        str: Formatted list of active timers
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime
    
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
            
            # Parse fire time and calculate time until
            try:
                fire_datetime = datetime.fromisoformat(fire_at.replace('Z', '+00:00'))
                
                # Get the guild's timezone for accurate time calculation
                import pytz
                from datetime import timezone
                guild_config = configured_guilds.get(guild_id, {})
                guild_timezone = guild_config.get('timezone', 'America/Edmonton')
                local_tz = pytz.timezone(guild_timezone)
                
                # Convert to local time for display
                fire_local = fire_datetime.astimezone(local_tz)
                fire_str = fire_local.strftime('%B %d, %Y at %I:%M %p')
                
                # Calculate time until reminder
                now_utc = datetime.now(timezone.utc)
                now_local = now_utc.astimezone(local_tz)
                time_until = fire_local - now_local
                
                if time_until.total_seconds() > 0:
                    hours_until = time_until.total_seconds() / 3600
                    if hours_until < 1:
                        minutes_until = int(time_until.total_seconds() / 60)
                        time_until_str = f"in {minutes_until} minutes"
                    elif hours_until < 24:
                        time_until_str = f"in {hours_until:.1f} hours"
                    else:
                        days_until = hours_until / 24
                        time_until_str = f"in {days_until:.1f} days"
                else:
                    time_until_str = "OVERDUE"
                    
            except Exception as e:
                fire_str = fire_at
                time_until_str = "Unknown"
            
            # Get the title and mention from the timer data
            title = timer.get('title', 'Unknown')
            mention = timer.get('mention', '')
            
            # Format timer type for display
            type_display = timer_type.replace('_', ' ').title()
            
            response += f"**{type_display}**\n"
            response += f"• {ref_type.title()}: {title}\n"
            response += f"• Fire at: {fire_str}\n"
            response += f"• Time until: {time_until_str}\n"
            if mention:
                response += f"• Mention: {mention}\n"
            response += "\n"
        
        if len(all_timers) > 10:
            response += f"... and {len(all_timers) - 10} more timers"
        
        return response
        
    except Exception as e:
        return f"❌ Error listing timers: {str(e)}"


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
            return "❌ No config spreadsheet configured. Please run `/setup` first."
        
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
