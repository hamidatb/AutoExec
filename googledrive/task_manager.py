import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from .sheets_manager import ClubSheetsManager
from .minutes_parser import MinutesParser

class TaskManager:
    """
    Manages tasks for the Club Exec Task Manager Bot.
    Handles task creation, updates, tracking, and deadline management.
    """
    
    def __init__(self):
        """Initialize the task manager."""
        self.sheets_manager = ClubSheetsManager()
        self.minutes_parser = MinutesParser()
        
    async def add_task(self, task_data: Dict[str, Any], tasks_spreadsheet_id: str, 
                      club_name: str = None, folder_id: str = None) -> bool:
        """
        Adds a new task to the system.
        
        Args:
            task_data: Dictionary containing task information
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            club_name: Name of the club (for automatic sheet creation)
            folder_id: Folder ID for automatic sheet creation
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate required fields
            if not task_data.get('title') or not task_data.get('owner_discord_id'):
                print("Task must have title and owner_discord_id")
                return False
            
            # Set default values
            if not task_data.get('status'):
                task_data['status'] = 'open'
            if not task_data.get('priority'):
                task_data['priority'] = 'medium'
            
            # Determine the month for the task
            current_month = datetime.now().strftime("%B %Y")
            
            # Ensure monthly sheets exist for this month
            if club_name and folder_id:
                monthly_sheets = self.sheets_manager.get_or_create_monthly_sheets(
                    club_name, current_month, folder_id
                )
                if monthly_sheets and 'tasks' in monthly_sheets:
                    tasks_spreadsheet_id = monthly_sheets['tasks']
            
            # Add task to spreadsheet
            success = self.sheets_manager.add_task(tasks_spreadsheet_id, task_data)
            
            if success:
                print(f"Task '{task_data['title']}' added successfully")
                
                # Schedule reminders for the task
                await self._schedule_task_reminders(task_data, tasks_spreadsheet_id)
            
            return success
            
        except Exception as e:
            print(f"Error adding task: {e}")
            return False
    
    async def update_task_status(self, task_id: str, new_status: str, 
                                tasks_spreadsheet_id: str, config_spreadsheet_id: str = None) -> bool:
        """
        Updates the status of a task in the Tasks sheet (single source of truth).
        
        Args:
            task_id: ID of the task to update
            new_status: New status for the task
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            config_spreadsheet_id: ID of the config spreadsheet (for timer management)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate status
            valid_statuses = ['open', 'in_progress', 'done', 'blocked']
            if new_status not in valid_statuses:
                print(f"Invalid status: {new_status}. Must be one of {valid_statuses}")
                return False
            
            # Update task in spreadsheet (single source of truth)
            success = self.sheets_manager.update_task_status(tasks_spreadsheet_id, task_id, new_status)
            
            if success:
                print(f"Task {task_id} status updated to {new_status} in Tasks sheet")
                
                # If task is done, cancel any pending reminders
                if new_status == 'done' and config_spreadsheet_id:
                    await self._cancel_task_reminders(task_id, config_spreadsheet_id)
                
                # If task is blocked, update reminders to reflect blocked status
                elif new_status == 'blocked' and config_spreadsheet_id:
                    await self._update_task_reminders_for_blocked(task_id, config_spreadsheet_id)
            
            return success
            
        except Exception as e:
            print(f"Error updating task status: {e}")
            return False
    
    async def reschedule_task(self, task_id: str, new_deadline: str, 
                             tasks_spreadsheet_id: str, config_spreadsheet_id: str = None) -> bool:
        """
        Reschedules a task to a new deadline in the Tasks sheet (single source of truth).
        
        Args:
            task_id: ID of the task to reschedule
            new_deadline: New deadline in ISO format
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            config_spreadsheet_id: ID of the config spreadsheet (for timer management)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate deadline format
            try:
                datetime.fromisoformat(new_deadline)
            except ValueError:
                print(f"Invalid deadline format: {new_deadline}. Use ISO format (YYYY-MM-DD)")
                return False
            
            # Update task deadline in spreadsheet (single source of truth)
            success = self.sheets_manager.update_task_deadline(tasks_spreadsheet_id, task_id, new_deadline)
            
            if success:
                print(f"Task {task_id} rescheduled to {new_deadline} in Tasks sheet")
                
                # Reschedule reminders for the new deadline
                if config_spreadsheet_id:
                    await self._reschedule_task_reminders(task_id, new_deadline, config_spreadsheet_id)
            
            return success
            
        except Exception as e:
            print(f"Error rescheduling task: {e}")
            return False
    
    def get_user_tasks(self, discord_id: str, tasks_spreadsheet_id: str, 
                       status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Gets all tasks for a specific user.
        
        Args:
            discord_id: Discord ID of the user
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            status_filter: Optional status filter
            
        Returns:
            List of task dictionaries
        """
        try:
            tasks = self.sheets_manager.get_tasks_by_user(tasks_spreadsheet_id, discord_id)
            
            # Apply status filter if provided
            if status_filter:
                tasks = [task for task in tasks if task.get('status') == status_filter]
            
            return tasks
            
        except Exception as e:
            print(f"Error getting user tasks: {e}")
            return []
    
    def search_tasks_by_title(self, title_query: str, tasks_spreadsheet_id: str, 
                             status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for tasks by title (case-insensitive partial match).
        
        Args:
            title_query: Title or partial title to search for
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            status_filter: Optional status filter ('open', 'in_progress', 'done', 'blocked')
            
        Returns:
            List of matching task dictionaries
        """
        try:
            return self.sheets_manager.search_tasks_by_title(tasks_spreadsheet_id, title_query, status_filter)
            
        except Exception as e:
            print(f"Error searching tasks by title: {e}")
            return []
    
    def get_overdue_tasks(self, tasks_spreadsheet_id: str) -> List[Dict[str, Any]]:
        """
        Gets all overdue tasks.
        
        Args:
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            
        Returns:
            List of overdue task dictionaries
        """
        try:
            # Get all open tasks
            all_tasks = self.sheets_manager.get_all_tasks(tasks_spreadsheet_id)
            overdue_tasks = []
            
            now = datetime.now(timezone.utc)
            
            for task in all_tasks:
                if task.get('status') == 'open' and task.get('due_at'):
                    try:
                        # Parse deadline
                        if task['due_at'] in ['next_meeting', 'this_week', 'next_week', 'end_of_month']:
                            # Handle relative deadlines
                            continue
                        
                        deadline = datetime.fromisoformat(task['due_at'])
                        if deadline < now:
                            overdue_tasks.append(task)
                    except ValueError:
                        # Skip tasks with unparseable deadlines
                        continue
            
            return overdue_tasks
            
        except Exception as e:
            print(f"Error getting overdue tasks: {e}")
            return []
    
    async def create_tasks_from_minutes(self, doc_url: str, tasks_spreadsheet_id: str,
                                       people_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Creates tasks from meeting minutes document.
        
        Args:
            doc_url: URL of the minutes document
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            people_mapping: Dictionary mapping names to Discord IDs
            
        Returns:
            List of created task dictionaries
        """
        try:
            # Parse minutes and create tasks
            created_tasks = self.minutes_parser.create_tasks_from_minutes(
                doc_url, tasks_spreadsheet_id, people_mapping
            )
            
            # Schedule reminders for all created tasks
            for task in created_tasks:
                await self._schedule_task_reminders(task, tasks_spreadsheet_id)
            
            return created_tasks
            
        except Exception as e:
            print(f"Error creating tasks from minutes: {e}")
            return []
    
    async def _schedule_task_reminders(self, task_data: Dict[str, Any], 
                                      tasks_spreadsheet_id: str, config_spreadsheet_id: str = None):
        """
        Schedules reminders for a task using the Timers tab.
        
        Args:
            task_data: Task data dictionary
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            config_spreadsheet_id: ID of the config spreadsheet (for timers)
        """
        try:
            if not config_spreadsheet_id:
                print("No config spreadsheet ID provided for timer scheduling")
                return
                
            task_id = task_data.get('task_id', '')
            due_at = task_data.get('due_at', '')
            
            if not due_at or due_at in ['next_meeting', 'this_week', 'next_week', 'end_of_month']:
                print(f"No specific deadline for task {task_id}, skipping reminder scheduling")
                return
            
            # Parse deadline
            try:
                deadline = datetime.fromisoformat(due_at)
            except ValueError:
                print(f"Invalid deadline format for task {task_id}: {due_at}")
                return
            
            # Schedule reminders at T-24h, T-2h, T+0h (overdue), T+48h (escalation)
            reminders = [
                {'type': 'task_reminder_24h', 'fire_at': deadline - timedelta(hours=24)},
                {'type': 'task_reminder_2h', 'fire_at': deadline - timedelta(hours=2)},
                {'type': 'task_overdue', 'fire_at': deadline},
                {'type': 'task_escalate', 'fire_at': deadline + timedelta(hours=48)}
            ]
            
            for reminder in reminders:
                timer_data = {
                    'id': f"{task_id}_{reminder['type']}",
                    'guild_id': '',  # Will be set by caller
                    'type': reminder['type'],
                    'ref_type': 'task',
                    'ref_id': task_id,
                    'fire_at_utc': reminder['fire_at'].isoformat(),
                    'channel_id': '',  # Will be set by caller
                    'state': 'active'
                }
                
                self.sheets_manager.add_timer(config_spreadsheet_id, timer_data)
                print(f"Scheduled {reminder['type']} reminder for task {task_id}")
            
        except Exception as e:
            print(f"Error scheduling task reminders: {e}")
    
    async def _cancel_task_reminders(self, task_id: str, config_spreadsheet_id: str):
        """
        Cancels reminders for a completed task.
        
        Args:
            task_id: ID of the task
            config_spreadsheet_id: ID of the config spreadsheet
        """
        try:
            # Get all timers for this task
            timers = self.sheets_manager.get_timers(config_spreadsheet_id)
            task_timers = [t for t in timers if t.get('ref_id') == task_id and t.get('ref_type') == 'task']
            
            # Cancel all active timers for this task
            for timer in task_timers:
                if timer.get('state') == 'active':
                    self.sheets_manager.update_timer_state(config_spreadsheet_id, timer['id'], 'cancelled')
                    print(f"Cancelled timer {timer['id']} for task {task_id}")
            
        except Exception as e:
            print(f"Error cancelling task reminders: {e}")
    
    async def _reschedule_task_reminders(self, task_id: str, new_deadline: str,
                                        config_spreadsheet_id: str):
        """
        Reschedules reminders for a task with a new deadline.
        
        Args:
            task_id: ID of the task
            new_deadline: New deadline
            config_spreadsheet_id: ID of the config spreadsheet
        """
        try:
            # Cancel existing reminders
            await self._cancel_task_reminders(task_id, config_spreadsheet_id)
            
            # Schedule new reminders for the new deadline
            deadline = datetime.fromisoformat(new_deadline)
            reminders = [
                {'type': 'task_reminder_24h', 'fire_at': deadline - timedelta(hours=24)},
                {'type': 'task_reminder_2h', 'fire_at': deadline - timedelta(hours=2)},
                {'type': 'task_overdue', 'fire_at': deadline},
                {'type': 'task_escalate', 'fire_at': deadline + timedelta(hours=48)}
            ]
            
            for reminder in reminders:
                timer_data = {
                    'id': f"{task_id}_{reminder['type']}",
                    'guild_id': '',  # Will be set by caller
                    'type': reminder['type'],
                    'ref_type': 'task',
                    'ref_id': task_id,
                    'fire_at_utc': reminder['fire_at'].isoformat(),
                    'channel_id': '',  # Will be set by caller
                    'state': 'active'
                }
                
                self.sheets_manager.add_timer(config_spreadsheet_id, timer_data)
                print(f"Rescheduled {reminder['type']} reminder for task {task_id}")
            
        except Exception as e:
            print(f"Error rescheduling task reminders: {e}")
    
    async def _update_task_reminders_for_blocked(self, task_id: str, config_spreadsheet_id: str):
        """
        Updates reminders for a blocked task.
        
        Args:
            task_id: ID of the task
            config_spreadsheet_id: ID of the config spreadsheet
        """
        try:
            # Get all timers for this task
            timers = self.sheets_manager.get_timers(config_spreadsheet_id)
            task_timers = [t for t in timers if t.get('ref_id') == task_id and t.get('ref_type') == 'task']
            
            # Update all active timers to reflect blocked status
            for timer in task_timers:
                if timer.get('state') == 'active':
                    self.sheets_manager.update_timer_state(config_spreadsheet_id, timer['id'], 'blocked')
                    print(f"Updated timer {timer['id']} to blocked status for task {task_id}")
            
        except Exception as e:
            print(f"Error updating task reminders for blocked status: {e}")
    
    async def send_task_reminders(self, tasks_spreadsheet_id: str, 
                                 reminder_channel_id: int, bot_instance):
        """
        Sends reminders for tasks that are due soon or overdue.
        
        Args:
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            reminder_channel_id: Discord channel ID for reminders
            bot_instance: Discord bot instance
        """
        try:
            # Get overdue tasks
            overdue_tasks = self.get_overdue_tasks(tasks_spreadsheet_id)
            
            if overdue_tasks:
                # Send overdue reminders
                for task in overdue_tasks:
                    message = f"⚠️ **OVERDUE TASK** ⚠️\n"
                    message += f"**{task.get('title')}**\n"
                    message += f"Owner: <@{task.get('owner_discord_id')}>\n"
                    message += f"Due: {task.get('due_at')}\n"
                    message += f"Status: {task.get('status')}"
                    
                    await bot_instance.send_any_message(message, reminder_channel_id)
            
            # Get tasks due in next 24 hours
            # This would check for upcoming deadlines and send reminders
            
        except Exception as e:
            print(f"Error sending task reminders: {e}")
    
    async def handle_task_reply(self, message_content: str, user_id: str,
                               tasks_spreadsheet_id: str) -> str:
        """
        Handles user replies to task reminders.
        
        Args:
            message_content: Content of the user's reply
            user_id: Discord ID of the user
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            
        Returns:
            Response message to send back
        """
        try:
            content_lower = message_content.lower().strip()
            
            if content_lower == "done":
                # Find the most recent task for this user and mark it as done
                user_tasks = self.get_user_tasks(user_id, tasks_spreadsheet_id, 'open')
                if user_tasks:
                    # Mark the most recent task as done
                    task = user_tasks[0]  # Assuming most recent is first
                    if await self.update_task_status(task['task_id'], 'done', tasks_spreadsheet_id):
                        return f"✅ Task '{task['title']}' marked as done!"
                    else:
                        return "❌ Failed to update task status."
                else:
                    return "❌ No open tasks found for you."
            
            elif content_lower == "not yet":
                # Find the most recent task for this user and mark it as in progress
                user_tasks = self.get_user_tasks(user_id, tasks_spreadsheet_id, 'open')
                if user_tasks:
                    task = user_tasks[0]
                    if await self.update_task_status(task['task_id'], 'in_progress', tasks_spreadsheet_id):
                        return f"🔄 Task '{task['title']}' marked as in progress."
                    else:
                        return "❌ Failed to update task status."
                else:
                    return "❌ No open tasks found for you."
            
            elif content_lower.startswith("reschedule to "):
                # Extract new date from message
                new_date = message_content[15:].strip()  # Remove "reschedule to "
                
                # Find the most recent task for this user
                user_tasks = self.get_user_tasks(user_id, tasks_spreadsheet_id, 'open')
                if user_tasks:
                    task = user_tasks[0]
                    if await self.reschedule_task(task['task_id'], new_date, tasks_spreadsheet_id):
                        return f"📅 Task '{task['title']}' rescheduled to {new_date}."
                    else:
                        return "❌ Failed to reschedule task."
                else:
                    return "❌ No open tasks found for you."
            
            else:
                return "❓ I didn't understand that. Please reply with:\n• 'done' - to mark a task complete\n• 'not yet' - to mark a task in progress\n• 'reschedule to [date]' - to change the deadline"
                
        except Exception as e:
            print(f"Error handling task reply: {e}")
            return "❌ An error occurred while processing your reply."
