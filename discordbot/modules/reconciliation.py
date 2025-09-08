"""
Timer reconciliation logic for the Club Exec Task Manager Bot.
Handles synchronization between Google Sheets data and active timers.
"""

import asyncio
from typing import Optional, Dict, Any, List


class ReconciliationManager:
    """Handles timer reconciliation and synchronization."""
    
    def __init__(self, bot):
        self.bot = bot
        self.sheets_manager = bot.sheets_manager
        self.meeting_manager = bot.meeting_manager
        self.task_manager = bot.task_manager
        self.timer_scheduler = bot.timer_scheduler
    
    async def reconciliation_loop(self):
        """Reconciliation job that runs every 15 minutes to ensure timers match current data."""
        while True:
            try:
                await asyncio.sleep(900)  # 15 minutes
                await self.reconcile_timers()
            except Exception as e:
                print(f"❌ Error in reconciliation loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def reconcile_timers(self):
        """Reconciles timers with current Tasks and Meetings sheets."""
        try:
            print("🔄 Starting timer reconciliation...")
            
            # Get all guild configurations
            all_guilds = self.bot.setup_manager.status_manager.get_all_guilds()
            
            for guild_id, guild_config in all_guilds.items():
                try:
                    if not guild_config.get('setup_complete', False):
                        continue
                    
                    config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
                    if not config_spreadsheet_id:
                        continue
                    
                    # Get current timers from Google Sheets (like original implementation)
                    current_timers = self.sheets_manager.get_timers(config_spreadsheet_id)
                    
                    # Get current tasks and meetings from monthly sheets
                    tasks = []
                    meetings = []
                    monthly_sheets = guild_config.get('monthly_sheets', {})
                    
                    if 'tasks' in monthly_sheets:
                        tasks = self.sheets_manager.get_all_tasks(monthly_sheets['tasks'])
                    if 'meetings' in monthly_sheets:
                        meetings = self.sheets_manager.get_all_meetings(monthly_sheets['meetings'])
                    
                    # Update timers based on current data
                    await self._update_timers_from_data(current_timers, tasks, meetings, config_spreadsheet_id)
                    
                    # Clean up old timers (run once per reconciliation cycle)
                    self.sheets_manager.cleanup_old_timers(config_spreadsheet_id)
                    
                except Exception as e:
                    print(f"❌ Error reconciling timers for guild {guild_id}: {e}")
                    continue
            
            print("✅ Timer reconciliation completed")
            
        except Exception as e:
            print(f"❌ Error in timer reconciliation: {e}")
    
    async def _update_timers_from_data(self, current_timers: List[Dict[str, Any]], 
                                     tasks: List[Dict[str, Any]], 
                                     meetings: List[Dict[str, Any]], 
                                     config_spreadsheet_id: str):
        """Update timers based on current data from sheets."""
        try:
            # Build expected timers from current data
            expected_timers = {}
            
            # Process tasks
            for task in tasks:
                if task.get('status') in ['open', 'in_progress'] and task.get('due_at'):
                    task_timers = self._build_expected_task_timers(task)
                    expected_timers.update(task_timers)
            
            # Process meetings
            for meeting in meetings:
                if meeting.get('status') == 'scheduled' and meeting.get('start_at_utc'):
                    meeting_timers = self._build_expected_meeting_timers(meeting)
                    expected_timers.update(meeting_timers)
            
            # Compare with current timers (convert list to map like original)
            current_timer_map = {t['id']: t for t in current_timers if t.get('state') == 'active'}
            
            # Find timers to add/update
            timers_added = 0
            timers_updated = 0
            timers_cancelled = 0
            
            for timer_id, expected_timer in expected_timers.items():
                if timer_id not in current_timer_map:
                    # New timer - add it
                    await self._add_timer_to_system(expected_timer, config_spreadsheet_id)
                    timers_added += 1
                else:
                    # Check if timer needs updating
                    current_timer = current_timer_map[timer_id]
                    if self._timer_needs_update(current_timer, expected_timer):
                        await self._update_timer_in_system(expected_timer, config_spreadsheet_id)
                        timers_updated += 1
            
            # Find timers to cancel
            for timer_id, current_timer in current_timer_map.items():
                if timer_id not in expected_timers:
                    # Timer no longer needed - cancel it
                    await self._cancel_timer_in_system(timer_id, config_spreadsheet_id)
                    timers_cancelled += 1
            
            print(f"✅ Reconciled timers: {timers_added} added, {timers_updated} updated, {timers_cancelled} cancelled")
                
        except Exception as e:
            print(f"❌ Error updating timers from data: {e}")
    
    def _build_expected_task_timers(self, task: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Build expected timers for a task"""
        timers = {}
        task_id = task.get('id')
        deadline = task.get('deadline')
        
        if not task_id or not deadline:
            return timers
        
        try:
            from datetime import datetime, timedelta
            from dateutil import parser
            
            # Parse deadline
            if isinstance(deadline, str):
                deadline_dt = parser.parse(deadline)
            else:
                deadline_dt = deadline
            
            # 24-hour reminder
            reminder_24h = deadline_dt - timedelta(hours=24)
            if reminder_24h > datetime.now():
                timers[f"task_reminder_24h_{task_id}"] = {
                    'type': 'task_reminder',
                    'task_id': task_id,
                    'reminder_type': '24h',
                    'scheduled_time': reminder_24h.isoformat(),
                    'guild_id': task.get('guild_id'),
                    'user_id': task.get('assigned_to')
                }
            
            # 2-hour reminder
            reminder_2h = deadline_dt - timedelta(hours=2)
            if reminder_2h > datetime.now():
                timers[f"task_reminder_2h_{task_id}"] = {
                    'type': 'task_reminder',
                    'task_id': task_id,
                    'reminder_type': '2h',
                    'scheduled_time': reminder_2h.isoformat(),
                    'guild_id': task.get('guild_id'),
                    'user_id': task.get('assigned_to')
                }
            
            # Overdue notification
            overdue_time = deadline_dt + timedelta(hours=1)
            if overdue_time > datetime.now():
                timers[f"task_overdue_{task_id}"] = {
                    'type': 'task_overdue',
                    'task_id': task_id,
                    'scheduled_time': overdue_time.isoformat(),
                    'guild_id': task.get('guild_id'),
                    'user_id': task.get('assigned_to')
                }
            
            # Escalation (48 hours after deadline)
            escalation_time = deadline_dt + timedelta(hours=48)
            if escalation_time > datetime.now():
                timers[f"task_escalation_{task_id}"] = {
                    'type': 'task_escalation',
                    'task_id': task_id,
                    'scheduled_time': escalation_time.isoformat(),
                    'guild_id': task.get('guild_id'),
                    'user_id': task.get('assigned_to')
                }
                
        except Exception as e:
            print(f"❌ Error building task timers for task {task_id}: {e}")
        
        return timers
    
    def _build_expected_meeting_timers(self, meeting: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Build expected timers for a meeting"""
        timers = {}
        meeting_id = meeting.get('id')
        start_time = meeting.get('start_time')
        
        if not meeting_id or not start_time:
            return timers
        
        try:
            from datetime import datetime, timedelta
            from dateutil import parser
            
            # Parse start time
            if isinstance(start_time, str):
                start_dt = parser.parse(start_time)
            else:
                start_dt = start_time
            
            # 2-hour reminder
            reminder_2h = start_dt - timedelta(hours=2)
            if reminder_2h > datetime.now():
                timers[f"meeting_reminder_2h_{meeting_id}"] = {
                    'type': 'meeting_reminder',
                    'meeting_id': meeting_id,
                    'reminder_type': '2h',
                    'scheduled_time': reminder_2h.isoformat(),
                    'guild_id': meeting.get('guild_id')
                }
            
            # Start notification
            if start_dt > datetime.now():
                timers[f"meeting_start_{meeting_id}"] = {
                    'type': 'meeting_start',
                    'meeting_id': meeting_id,
                    'scheduled_time': start_dt.isoformat(),
                    'guild_id': meeting.get('guild_id')
                }
            
            # Minutes processing (30 minutes after start)
            minutes_time = start_dt + timedelta(minutes=30)
            if minutes_time > datetime.now():
                timers[f"meeting_minutes_{meeting_id}"] = {
                    'type': 'meeting_minutes',
                    'meeting_id': meeting_id,
                    'scheduled_time': minutes_time.isoformat(),
                    'guild_id': meeting.get('guild_id')
                }
                
        except Exception as e:
            print(f"❌ Error building meeting timers for meeting {meeting_id}: {e}")
        
        return timers
    
    def _timer_needs_update(self, current_timer: Dict[str, Any], expected_timer: Dict[str, Any]) -> bool:
        """Check if a timer needs updating"""
        try:
            # Compare key fields that might change
            key_fields = ['scheduled_time', 'reminder_type', 'user_id']
            
            for field in key_fields:
                if current_timer.get(field) != expected_timer.get(field):
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking if timer needs update: {e}")
            return False
    
    async def _add_timer_to_system(self, timer_data: Dict[str, Any], config_spreadsheet_id: str):
        """Add a new timer to the system"""
        try:
            timer_id = timer_data.get('id')
            if not timer_id:
                return
            
            # Add timer to the scheduler
            await self.timer_scheduler.add_timer(timer_id, timer_data)
            print(f"✅ Added timer: {timer_id}")
            
        except Exception as e:
            print(f"❌ Error adding timer to system: {e}")
    
    async def _update_timer_in_system(self, timer_data: Dict[str, Any], config_spreadsheet_id: str):
        """Update an existing timer in the system"""
        try:
            timer_id = timer_data.get('id')
            if not timer_id:
                return
            
            # Update timer in the scheduler
            await self.timer_scheduler.update_timer(timer_id, timer_data)
            print(f"✅ Updated timer: {timer_id}")
            
        except Exception as e:
            print(f"❌ Error updating timer in system: {e}")
    
    async def _cancel_timer_in_system(self, timer_id: str, config_spreadsheet_id: str):
        """Cancel a timer in the system"""
        try:
            # Cancel timer in the scheduler
            await self.timer_scheduler.cancel_timer(timer_id)
            print(f"✅ Cancelled timer: {timer_id}")
            
        except Exception as e:
            print(f"❌ Error cancelling timer in system: {e}")
