"""
Task tools module for AutoExec agent.
Contains all task-related functions including parsing, management, and completion.
Timer-related functions have been moved to timer_tools.py.
"""

from langchain.tools import tool
from .context_manager import get_discord_context, get_user_admin_servers, get_meetings_sheet_id
from .utility_tools import create_task_timers


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
        
        # Parse the meeting minutes document using MinutesParser (like original)
        from googledrive.minutes_parser import MinutesParser
        
        try:
            minutes_parser = MinutesParser()
            action_items = minutes_parser.parse_minutes_doc(minutes_doc_url)
        except Exception as parse_error:
            return f"❌ **Error parsing meeting minutes:** {str(parse_error)}\n\nPlease ensure the document URL is correct and accessible."
        
        if not action_items:
            return "📄 **Meeting Minutes Parsed**\n\nNo action items found in the meeting minutes document."
        
        # Set default deadline (2 weeks from now)
        default_deadline = datetime.now(timezone.utc) + timedelta(days=14)
        
        created_tasks = []
        failed_tasks = []
        
        # Get exec members for Discord ID mapping (like original)
        exec_members = guild_config.get('exec_members', [])
        people_mapping = {}
        for member in exec_members:
            if 'discord_id' in member and 'name' in member:
                people_mapping[member['name']] = member['discord_id']
        
        # Calculate default deadline (2 weeks from now, like original)
        default_deadline = (datetime.now(timezone.utc) + timedelta(weeks=2)).replace(hour=23, minute=59, second=0, microsecond=0).isoformat()
        
        for item in action_items:
            try:
                # Extract task details (using original field names)
                person = item.get('person', 'Unknown')
                task = item.get('task', 'No task specified')
                deadline = item.get('deadline', default_deadline)
                completed = item.get('completed', False)
                role = item.get('role', '')
                
                if not task or task.strip() == '':
                    continue
                
                # Skip if already completed (like original)
                if completed:
                    continue
                
                # Map person name to Discord ID (like original)
                discord_id = people_mapping.get(person, '')
                
                # Use the deadline from parsed action items, or default if not set
                task_deadline = deadline if deadline else default_deadline
                
                # Format Discord ID for proper mention format (like original)
                formatted_discord_id = f"<@{discord_id}>" if discord_id else ""
                
                # Use task reminders channel from guild config (fallback to context channel)
                task_channel_id = guild_config.get('task_reminders_channel_id') or context.get('channel_id', '')
                
                # Create task data (like original)
                task_data = {
                    'title': task,
                    'owner_discord_id': formatted_discord_id,
                    'owner_name': person,
                    'due_at': task_deadline,
                    'status': 'open',
                    'priority': 'medium',
                    'source_doc': minutes_doc_url,
                    'channel_id': task_channel_id,
                    'notes': f"Role: {role} | From meeting minutes",
                    'created_by': context.get('user_id', ''),
                    'guild_id': guild_id
                }
                
                # Add task to Google Sheets
                success, task_id = BOT_INSTANCE.sheets_manager.add_task(tasks_sheet_id, task_data)
                
                if success:
                    task_data['task_id'] = task_id
                    created_tasks.append(f"✅ {person}: {task}")
                    
                    # Schedule reminders for the task if it has a specific deadline (like original)
                    config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
                    if config_spreadsheet_id and task_data.get('due_at'):
                        timer_count = create_task_timers(task_data, guild_config)
                else:
                    failed_tasks.append(f"❌ {person}: {task}")
                    
            except Exception as task_error:
                failed_tasks.append(f"❌ {person}: {task} (error: {str(task_error)})")
        
        # Format response (like original)
        response = "📋 **Action Items from Meeting Minutes**\n\n"
        
        # Add summary (like original)
        if created_tasks:
            response += f"🎉 **Successfully created {len(created_tasks)} tasks in Google Sheets!**\n\n"
            for task in created_tasks:
                response += f"• {task}\n"
        
        if failed_tasks:
            response += f"\n⚠️ **Failed to create {len(failed_tasks)} tasks:**\n"
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
            
            # Only include tasks with 'open' status
            if status == 'open':
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
            elif status == 'completed':
                completed_tasks.append(task)
        
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
        
        # Handle DM context - check if user is admin of any configured servers (like original)
        if not guild_id:
            if not user_id:
                return "❌ No Discord context found. Please use this command in a Discord server or DM."
            
            # Check if user is admin of any servers
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
• Mention the club name: "For [Club Name], complete task [ID]"
• Mention the server name: "In [Server Name], mark task [ID] as done"

**Example:** "For Computer Science Club, complete task abc123"

Which server would you like me to help you with?"""
        
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
        
        # Find the task by ID (like original implementation)
        all_tasks = BOT_INSTANCE.sheets_manager.get_all_tasks(tasks_sheet_id)
        target_task = None
        
        for task in all_tasks:
            if task.get('task_id') == task_id:
                target_task = task
                break
        
        if not target_task:
            return f"❌ **Task Not Found**\n\nNo task found with ID `{task_id}`.\n\n**To find tasks:** Use the search_tasks_by_title tool to search for tasks by name.\n**Example:** \"Search for task budget review\""
        
        # Check if task is already completed
        current_status = target_task.get('status', 'open').lower()
        if current_status == 'done':
            return f"✅ **Task Already Completed**\n\n**Task:** {target_task.get('title', 'Untitled Task')}\n**Status:** Already marked as done\n**Task ID:** `{task_id}`\n\nThis task was already completed!"
        
        # Get task details for confirmation
        task_title = target_task.get('title', 'Untitled Task')
        owner_name = target_task.get('owner_name', 'Unknown')
        due_at = target_task.get('due_at', '')
        priority = target_task.get('priority', 'medium')
        notes = target_task.get('notes', '')
        
        # Update task status to 'done' in Google Sheets (like original)
        success = BOT_INSTANCE.sheets_manager.update_task_status(tasks_sheet_id, task_id, 'done')
        
        # Cancel all pending reminders for this task (like original)
        cancelled_count = 0
        config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
        if success and config_spreadsheet_id:
            try:
                # Get all timers for this task
                task_timers = BOT_INSTANCE.sheets_manager.get_timers_by_ref(config_spreadsheet_id, 'task', task_id)
                
                # Cancel all active timers for this task
                for timer in task_timers:
                    if timer.get('state') == 'active':
                        timer_id = timer.get('id')
                        if timer_id:
                            cancel_success = BOT_INSTANCE.sheets_manager.update_timer_state(config_spreadsheet_id, timer_id, 'cancelled')
                            if cancel_success:
                                cancelled_count += 1
                                print(f"Cancelled timer {timer_id} for task {task_id}")
                
                print(f"Cancelled {cancelled_count} reminders for task {task_id}")
            except Exception as e:
                print(f"Error cancelling task reminders: {e}")
                # Don't fail the whole operation if reminder cancellation fails
        
        if success:
            # Format response (like original)
            response = f"✅ **Task Completed Successfully!**\n\n"
            response += f"**Task:** {task_title}\n"
            response += f"**Owner:** {owner_name}\n"
            response += f"**Priority:** {priority.title()}\n"
            if due_at:
                response += f"**Due Date:** {due_at}\n"
            if notes:
                response += f"**Notes:** {notes}\n"
            response += f"**Completed by:** <@{user_id}>\n"
            response += f"**Completed at:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
            
            if cancelled_count > 0:
                response += f"**Reminders cancelled:** {cancelled_count} reminder(s)\n"
            
            return response
        else:
            return f"❌ **Failed to Complete Task**\n\nCould not update task status in Google Sheets. Please try again."
        
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
        
        # Get the most recent meeting across current and previous months (like original)
        recent_meeting = BOT_INSTANCE.sheets_manager.get_most_recent_meeting_across_months(guild_config)
        
        if not recent_meeting:
            return "❌ **No Meetings Found**\n\nSorry, there are no meetings in your meetings spreadsheet."
        
        meeting_title = recent_meeting.get('title', 'Unknown Meeting')
        minutes_link = recent_meeting.get('minutes_link', '')
        
        if not minutes_link or minutes_link.strip() == '':
            return f"❌ **No Meeting Minutes Attached**\n\nSorry, there are no meeting minutes attached to the last meeting, but the title was: **{meeting_title}**"
        
        # Get the document content (need to import this function)
        from googledrive.file_handler import get_document_content_from_url
        doc_content = get_document_content_from_url(minutes_link)
        
        if doc_content.startswith("❌"):
            return f"❌ **Cannot Access Minutes**\n\nSorry, I can't access the minutes document for the last meeting (title: **{meeting_title}**). The document may not be accessible or the link may be invalid.\n\n**Minutes Link:** {minutes_link}"
        
        # Initialize LLM for summarization
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            max_tokens=1000
        )
        
        # Create appropriate prompt based on summary type
        if summary_type.lower() == "action_items":
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant that extracts action items from meeting minutes. Focus only on action items, tasks, and deliverables mentioned in the meeting."),
                ("user", "Please extract and summarize the action items from this meeting minutes document:\n\n{doc_content}")
            ])
        else:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant that summarizes meeting minutes. Provide a clear, concise summary of the key points, decisions, and action items from the meeting."),
                ("user", "Please summarize this meeting minutes document:\n\n{doc_content}")
            ])
        
        # Generate summary
        chain = prompt | llm
        summary = chain.invoke({"doc_content": doc_content})
        
        # Format the response
        response = f"📋 **Meeting Summary: {meeting_title}**\n\n"
        response += f"🔗 **Full Minutes:** {minutes_link}\n\n"
        response += f"📝 **Summary:**\n{summary.content if hasattr(summary, 'content') else str(summary)}"
        
        return response
        
    except Exception as e:
        return f"❌ **Error summarizing meeting:** {str(e)}\n\nPlease try again or check if the meeting minutes are accessible."
