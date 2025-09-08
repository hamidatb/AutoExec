"""
Task tools module for AutoExec agent.
Contains all task-related functions including creation, management, timers, and completion.
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


@tool
def parse_meeting_minutes_action_items(minutes_doc_url: str) -> str:
    """
    Parse meeting minutes document and create tasks from action items.
    This tool extracts action items from meeting minutes and creates tasks with appropriate deadlines.
    
    Args:
        minutes_doc_url (str): URL to the meeting minutes document
        
    Returns:
        str: Summary of tasks created from the meeting minutes
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime, timezone, timedelta
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get Discord context
        context = get_discord_context()
        guild_id = context.get('guild_id')
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        # Get tasks sheet ID
        monthly_sheets = guild_config.get('monthly_sheets', {})
        tasks_sheet_id = monthly_sheets.get('tasks')
        
        if not tasks_sheet_id:
            return "❌ No tasks spreadsheet configured. Please run `/setup` first."
        
        # Parse the meeting minutes document
        from googledrive.minutes_parser import parse_meeting_minutes
        
        try:
            action_items = parse_meeting_minutes(minutes_doc_url)
        except Exception as parse_error:
            return f"❌ **Error parsing meeting minutes:** {str(parse_error)}\n\nPlease ensure the document URL is correct and accessible."
        
        if not action_items:
            return "📄 **Meeting Minutes Parsed**\n\nNo action items found in the meeting minutes document."
        
        # Set default deadline (2 weeks from now)
        default_deadline = datetime.now(timezone.utc) + timedelta(days=14)
        
        created_tasks = []
        failed_tasks = []
        
        for item in action_items:
            try:
                # Extract task details
                task_title = item.get('task', '').strip()
                assignee = item.get('assignee', '').strip()
                due_date_str = item.get('due_date', '').strip()
                
                if not task_title:
                    continue
                
                # Parse due date or use default
                if due_date_str:
                    due_datetime = parse_due_date(due_date_str)
                    if not due_datetime:
                        due_datetime = default_deadline
                else:
                    due_datetime = default_deadline
                
                # Find assignee Discord ID
                if assignee:
                    assignee_discord_id = find_user_by_name(assignee, guild_config)
                    if not assignee_discord_id or assignee_discord_id.startswith("NEED_MENTION_FOR_"):
                        # Skip tasks with unknown assignees
                        failed_tasks.append(f"❌ {task_title} (assignee '{assignee}' not found)")
                        continue
                else:
                    # No assignee specified - skip
                    failed_tasks.append(f"❌ {task_title} (no assignee specified)")
                    continue
                
                # Create task data
                task_data = {
                    'title': task_title,
                    'owner_discord_id': assignee_discord_id,
                    'owner_name': assignee,
                    'due_at': due_datetime.isoformat(),
                    'status': 'open',
                    'priority': 'medium',
                    'source_doc': minutes_doc_url,
                    'channel_id': guild_config.get('task_reminders_channel_id', ''),
                    'notes': f"Created from meeting minutes: {minutes_doc_url}",
                    'created_by': context.get('user_id', ''),
                    'guild_id': guild_id
                }
                
                # Add task to Google Sheets
                success, task_id = BOT_INSTANCE.sheets_manager.add_task(tasks_sheet_id, task_data)
                
                if success:
                    task_data['task_id'] = task_id
                    # Create timers for the task
                    create_task_timers(task_data, guild_config)
                    created_tasks.append(f"✅ {task_title} → {assignee}")
                else:
                    failed_tasks.append(f"❌ {task_title} (failed to create)")
                    
            except Exception as task_error:
                failed_tasks.append(f"❌ {task_title} (error: {str(task_error)})")
        
        # Format response
        response = f"📄 **Meeting Minutes Processed**\n\n"
        response += f"**Action Items Found:** {len(action_items)}\n"
        response += f"**Tasks Created:** {len(created_tasks)}\n"
        response += f"**Failed:** {len(failed_tasks)}\n\n"
        
        if created_tasks:
            response += "**✅ Successfully Created:**\n"
            for task in created_tasks:
                response += f"• {task}\n"
        
        if failed_tasks:
            response += "\n**❌ Failed to Create:**\n"
            for task in failed_tasks:
                response += f"• {task}\n"
        
        if not created_tasks and not failed_tasks:
            response += f"💡 **All tasks were already completed - no new tasks created.**\n"
        
        # Count tasks with reminders scheduled
        config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
        if config_spreadsheet_id and created_tasks:
            response += f"\n⏰ **Reminders scheduled for {len(created_tasks)} tasks** (24h, 2h, overdue, escalation)\n"
        
        response += f"\n📅 **Note:** Tasks without specified deadlines have been set to {default_deadline} (2 weeks from now)."
        
        return response
        
    except Exception as e:
        return f"❌ **Error parsing meeting minutes:** {str(e)}\n\nPlease ensure the document URL is correct and accessible."


@tool
def send_tasks_by_person(limit: int = 10) -> str:
    """
    Retrieves and sends upcoming tasks for the current user.
    Works in both DMs and servers by checking the user's Discord ID.
    
    Args:
        limit (int): Maximum number of tasks to return (default: 10)
        
    Returns:
        str: Formatted list of user's upcoming tasks with source document links
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime, timezone
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get Discord context
        context = get_discord_context()
        user_id = context.get('user_id')
        guild_id = context.get('guild_id')
        channel_id = context.get('channel_id')
        
        if not user_id:
            return "❌ No Discord context found. Please use this command in a Discord server or DM."
        
        # Handle DM context - check if user is admin of any configured servers
        if not guild_id:
            user_guilds = get_user_admin_servers(user_id)
            if len(user_guilds) == 0:
                return "❌ You are not an admin of any configured servers. Please run `/setup` first."
            elif len(user_guilds) == 1:
                guild_id = user_guilds[0]['guild_id']
            else:
                guild_list = "\n".join([f"• **{guild['club_name']}** (Server: {guild['guild_name']})" for guild in user_guilds])
                return f"""❓ **Multiple Servers Detected**\n\nYou are an admin of **{len(user_guilds)}** servers. Please specify which server you're referring to:\n\n{guild_list}\n\n**How to specify:**\n• Mention the club name: "For [Club Name], what are my tasks?"\n• Mention the server name: "In [Server Name], show my upcoming tasks"\n\n**Example:** "For Computer Science Club, what are my upcoming tasks?"\n\nWhich server would you like me to help you with?"""
        
        # Get guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        # Get tasks spreadsheet ID
        monthly_sheets = guild_config.get('monthly_sheets', {})
        tasks_sheet_id = monthly_sheets.get('tasks')
        
        if not tasks_sheet_id:
            return "❌ No tasks spreadsheet configured. Please run `/setup` first."
        
        # Get user's tasks from Google Sheets
        user_tasks = BOT_INSTANCE.sheets_manager.get_tasks_by_user(tasks_sheet_id, user_id)
        
        if not user_tasks:
            return "📋 **Your Tasks**\n\n✅ You have no upcoming tasks! Great job staying on top of things!"
        
        # Filter and sort tasks (upcoming and open tasks first)
        current_time = datetime.now(timezone.utc)
        
        upcoming_tasks = []
        overdue_tasks = []
        completed_tasks = []
        
        for task in user_tasks:
            status = task.get('status', 'open').lower()
            due_at = task.get('due_at', '')
            
            if status == 'completed':
                completed_tasks.append(task)
            else:
                # Check if task is overdue
                try:
                    if due_at:
                        due_datetime = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                        if due_datetime < current_time:
                            overdue_tasks.append(task)
                        else:
                            upcoming_tasks.append(task)
                    else:
                        upcoming_tasks.append(task)
                except:
                    upcoming_tasks.append(task)
        
        # Sort upcoming tasks by due date
        upcoming_tasks.sort(key=lambda x: x.get('due_at', ''))
        
        # Limit results
        upcoming_tasks = upcoming_tasks[:limit]
        overdue_tasks = overdue_tasks[:limit]
        
        # Format response
        response = "📋 **Your Tasks**\n\n"
        
        if overdue_tasks:
            response += "🚨 **Overdue Tasks:**\n"
            for i, task in enumerate(overdue_tasks, 1):
                title = task.get('title', 'Untitled Task')
                due_at = task.get('due_at', '')
                source_doc = task.get('source_doc', '')
                notes = task.get('notes', '')
                
                response += f"{i}. **{title}**\n"
                if due_at:
                    try:
                        due_dt = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                        due_str = due_dt.strftime("%B %d, %Y at %I:%M %p UTC")
                        response += f"   ⏰ Due: {due_str}\n"
                    except:
                        response += f"   ⏰ Due: {due_at}\n"
                if source_doc:
                    response += f"   📄 Source: [View Document]({source_doc})\n"
                if notes:
                    response += f"   📝 Notes: {notes}\n"
                response += "\n"
        
        if upcoming_tasks:
            if overdue_tasks:
                response += "📅 **Upcoming Tasks:**\n"
            for i, task in enumerate(upcoming_tasks, 1):
                title = task.get('title', 'Untitled Task')
                due_at = task.get('due_at', '')
                source_doc = task.get('source_doc', '')
                notes = task.get('notes', '')
                priority = task.get('priority', 'medium')
                
                # Priority emoji
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority.lower(), "🟡")
                
                response += f"{i}. {priority_emoji} **{title}**\n"
                if due_at:
                    try:
                        due_dt = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                        due_str = due_dt.strftime("%B %d, %Y at %I:%M %p UTC")
                        response += f"   ⏰ Due: {due_str}\n"
                    except:
                        response += f"   ⏰ Due: {due_at}\n"
                if source_doc:
                    response += f"   📄 Source: [View Document]({source_doc})\n"
                if notes:
                    response += f"   📝 Notes: {notes}\n"
                response += "\n"
        
        if completed_tasks:
            response += f"✅ **Completed Tasks:** {len(completed_tasks)} tasks completed\n"
        
        # Add summary
        total_tasks = len(upcoming_tasks) + len(overdue_tasks)
        if total_tasks == 0:
            response += "\n🎉 You're all caught up! No pending tasks."
        else:
            response += f"\n📊 **Summary:** {len(overdue_tasks)} overdue, {len(upcoming_tasks)} upcoming"
        
        return response
        
    except Exception as e:
        print(f"Error getting user tasks: {e}")
        return f"❌ Error retrieving your tasks: {str(e)}"


@tool
def search_tasks_by_title(task_title: str) -> str:
    """
    Search for tasks by title to help users find the exact task they want to complete.
    This tool helps confirm task details before marking them as completed.
    
    Args:
        task_title (str): The title or partial title of the task to search for
        
    Returns:
        str: List of matching tasks with their details and IDs
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get Discord context
        context = get_discord_context()
        user_id = context.get('user_id')
        guild_id = context.get('guild_id')
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        # Get tasks spreadsheet ID
        monthly_sheets = guild_config.get('monthly_sheets', {})
        tasks_sheet_id = monthly_sheets.get('tasks')
        
        if not tasks_sheet_id:
            return "❌ No tasks spreadsheet configured. Please run `/setup` first."
        
        # Search for tasks by title
        all_tasks = BOT_INSTANCE.sheets_manager.get_all_tasks(tasks_sheet_id)
        matching_tasks = []
        
        task_title_lower = task_title.lower()
        for task in all_tasks:
            title = task.get('title', '').lower()
            if task_title_lower in title:
                matching_tasks.append(task)
        
        if not matching_tasks:
            return f"❌ No tasks found matching '{task_title}'."
        
        # Format response
        response = f"🔍 **Found {len(matching_tasks)} task(s) matching '{task_title}':**\n\n"
        
        for i, task in enumerate(matching_tasks, 1):
            title = task.get('title', 'Untitled Task')
            task_id = task.get('task_id', 'N/A')
            status = task.get('status', 'open')
            due_at = task.get('due_at', '')
            owner_name = task.get('owner_name', 'Unknown')
            priority = task.get('priority', 'medium')
            
            # Status emoji
            status_emoji = {"completed": "✅", "open": "📋", "in_progress": "🔄"}.get(status.lower(), "📋")
            
            # Priority emoji
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority.lower(), "🟡")
            
            response += f"**{i}. {status_emoji} {title}**\n"
            response += f"   🆔 ID: `{task_id}`\n"
            response += f"   👤 Owner: {owner_name}\n"
            response += f"   {priority_emoji} Priority: {priority.title()}\n"
            response += f"   📊 Status: {status.title()}\n"
            
            if due_at:
                try:
                    due_dt = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                    due_str = due_dt.strftime("%B %d, %Y at %I:%M %p UTC")
                    response += f"   ⏰ Due: {due_str}\n"
                except:
                    response += f"   ⏰ Due: {due_at}\n"
            
            response += "\n"
        
        response += "💡 **To complete a task, use:** `complete_task(task_id)` with the task ID from above."
        
        return response
        
    except Exception as e:
        print(f"Error searching tasks: {e}")
        return f"❌ Error searching tasks: {str(e)}"


@tool
def complete_task(task_id: str) -> str:
    """
    Mark a task as completed in Google Sheets.
    This tool updates the task status and clears associated timers.
    
    Args:
        task_id (str): The ID of the task to complete
        
    Returns:
        str: Confirmation message about the task completion
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get Discord context
        context = get_discord_context()
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        # Get tasks spreadsheet ID
        monthly_sheets = guild_config.get('monthly_sheets', {})
        tasks_sheet_id = monthly_sheets.get('tasks')
        
        if not tasks_sheet_id:
            return "❌ No tasks spreadsheet configured. Please run `/setup` first."
        
        # Get the task to verify it exists
        task = BOT_INSTANCE.sheets_manager.get_task_by_id(tasks_sheet_id, task_id)
        if not task:
            return f"❌ No task found with ID: {task_id}"
        
        # Check if task is already completed
        if task.get('status', '').lower() == 'completed':
            return f"✅ Task '{task.get('title', 'Untitled')}' is already completed."
        
        # Mark task as completed
        success = BOT_INSTANCE.sheets_manager.complete_task(tasks_sheet_id, task_id, user_id)
        
        if success:
            # Clear associated timers
            config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
            if config_spreadsheet_id:
                # Get all timers for this task
                timers = BOT_INSTANCE.sheets_manager.get_timers(config_spreadsheet_id)
                task_timers = [t for t in timers if t.get('ref_id') == task_id and t.get('state') == 'active']
                
                cleared_count = 0
                for timer in task_timers:
                    timer_id = timer.get('timer_id')
                    if timer_id:
                        if BOT_INSTANCE.sheets_manager.clear_timer(config_spreadsheet_id, timer_id):
                            cleared_count += 1
            
            response = f"✅ **Task Completed Successfully!**\n\n"
            response += f"**Task:** {task.get('title', 'Untitled')}\n"
            response += f"**Completed by:** <@{user_id}>\n"
            response += f"**Completed at:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
            
            if config_spreadsheet_id and 'cleared_count' in locals():
                response += f"**Timers cleared:** {cleared_count} reminder(s)\n"
            
            return response
        else:
            return f"❌ Failed to complete task '{task.get('title', 'Untitled')}'. Please try again."
        
    except Exception as e:
        print(f"Error completing task: {e}")
        return f"❌ Error completing task: {str(e)}"


@tool
def create_tasks_from_meeting_minutes(minutes_doc_url: str) -> str:
    """
    Create tasks from meeting minutes action items.
    This is a convenience function that combines parsing and task creation.
    
    Args:
        minutes_doc_url (str): URL to the meeting minutes document
        
    Returns:
        str: Summary of tasks created from the meeting minutes
    """
    # This function is a wrapper around parse_meeting_minutes_action_items
    return parse_meeting_minutes_action_items(minutes_doc_url)


@tool
def summarize_last_meeting(summary_type: str = "full") -> str:
    """
    Get a summary of the last meeting from the meeting minutes.
    This tool retrieves and summarizes the most recent meeting.
    
    Args:
        summary_type (str): Type of summary - "full", "brief", or "action_items" (default: "full")
        
    Returns:
        str: Summary of the last meeting
    """
    from discordbot.discord_client import BOT_INSTANCE
    from datetime import datetime, timezone
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get Discord context
        context = get_discord_context()
        guild_id = context.get('guild_id')
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        # Get meetings sheet ID
        meetings_sheet_id = get_meetings_sheet_id(guild_config)
        if not meetings_sheet_id:
            return "❌ No meetings spreadsheet configured. Please run `/setup` first."
        
        # Get the most recent meeting
        all_meetings = BOT_INSTANCE.meeting_manager.get_all_meetings(meetings_sheet_id)
        
        if not all_meetings:
            return "📅 **No Meetings Found**\n\nNo meetings have been scheduled yet."
        
        # Sort by start time and get the most recent
        recent_meetings = sorted(all_meetings, key=lambda x: x.get('start_at_utc', ''), reverse=True)
        last_meeting = recent_meetings[0]
        
        title = last_meeting.get('title', 'Untitled Meeting')
        start_time = last_meeting.get('start_at_local', 'Time TBD')
        location = last_meeting.get('location', 'Location TBD')
        meeting_link = last_meeting.get('meeting_link', '')
        minutes_link = last_meeting.get('minutes_link', '')
        
        response = f"📅 **Last Meeting Summary**\n\n"
        response += f"**Meeting:** {title}\n"
        response += f"**Date:** {start_time}\n"
        response += f"**Location:** {location}\n"
        
        if meeting_link:
            response += f"**Meeting Link:** {meeting_link}\n"
        
        if minutes_link:
            response += f"**Minutes Link:** {minutes_link}\n"
            
            # If user wants action items and minutes are available, parse them
            if summary_type == "action_items" and minutes_link:
                try:
                    from googledrive.minutes_parser import parse_meeting_minutes
                    action_items = parse_meeting_minutes(minutes_link)
                    
                    if action_items:
                        response += f"\n📋 **Action Items ({len(action_items)}):**\n"
                        for i, item in enumerate(action_items, 1):
                            task = item.get('task', '').strip()
                            assignee = item.get('assignee', '').strip()
                            due_date = item.get('due_date', '').strip()
                            
                            response += f"{i}. **{task}**\n"
                            if assignee:
                                response += f"   👤 Assigned to: {assignee}\n"
                            if due_date:
                                response += f"   ⏰ Due: {due_date}\n"
                            response += "\n"
                    else:
                        response += "\n📋 **No action items found in the minutes.**\n"
                        
                except Exception as parse_error:
                    response += f"\n❌ **Error parsing action items:** {str(parse_error)}\n"
        else:
            response += "\n📄 **No meeting minutes available.**\n"
        
        return response
        
    except Exception as e:
        print(f"Error summarizing last meeting: {e}")
        return f"❌ Error summarizing last meeting: {str(e)}"
