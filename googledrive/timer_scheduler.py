import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from .sheets_manager import ClubSheetsManager

class TimerScheduler:
    """
    Timer scheduler that uses Google Sheets as the single source of truth.
    Checks Google Sheets periodically for timers that should fire and sends Discord messages.
    """
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.sheets_manager = ClubSheetsManager()
        self.running = False
        self.check_interval = 60  # Check every minute
        self.tolerance_minutes = 1  # Fire timers within 1 minute of their scheduled time
    
    async def start(self):
        """Start the timer scheduler"""
        self.running = True
        asyncio.create_task(self._timer_loop())
        print("✅ Timer scheduler started")
    
    async def stop(self):
        """Stop the timer scheduler"""
        self.running = False
        print("⏹️ Timer scheduler stopped")
    
    async def _timer_loop(self):
        """Main timer loop that checks Google Sheets for timers to fire"""
        while self.running:
            try:
                await self._check_and_fire_timers()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"❌ Error in timer loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_and_fire_timers(self):
        """Check all guilds for timers that should fire"""
        try:
            # Get all guild configurations
            all_guilds = self.bot.setup_manager.status_manager.get_all_guilds()
            
            for guild_id, guild_config in all_guilds.items():
                if not guild_config.get('setup_complete', False):
                    continue
                
                config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
                if not config_spreadsheet_id:
                    continue
                
                # Get active timers from Google Sheets
                timers = self.sheets_manager.get_timers(config_spreadsheet_id)
                active_timers = [t for t in timers if t.get('state') == 'active']
                
                # Check each timer
                for timer in active_timers:
                    if await self._should_fire_timer(timer):
                        await self._fire_timer(timer, config_spreadsheet_id)
        
        except Exception as e:
            print(f"❌ Error checking timers: {e}")
    
    async def _should_fire_timer(self, timer: Dict[str, Any]) -> bool:
        """Check if a timer should fire now"""
        try:
            fire_at_str = timer.get('fire_at_utc')
            if not fire_at_str:
                return False
            
            fire_at = datetime.fromisoformat(fire_at_str)
            now = datetime.now(timezone.utc)
            
            # Fire if the time has passed (with tolerance)
            return fire_at <= now + timedelta(minutes=self.tolerance_minutes)
        
        except (ValueError, TypeError) as e:
            print(f"❌ Invalid timer fire time for timer {timer.get('id', 'unknown')}: {e}")
            return False
    
    async def _fire_timer(self, timer: Dict[str, Any], config_spreadsheet_id: str):
        """Fire a specific timer"""
        try:
            timer_id = timer['id']
            timer_type = timer.get('type', 'unknown')
            print(f"🔥 Firing timer: {timer_id} (type: {timer_type})")
            
            # Send Discord message based on timer type
            await self._send_timer_message(timer)
            
            # Update timer state in Google Sheets to 'fired'
            success = self.sheets_manager.update_timer_state(config_spreadsheet_id, timer_id, 'fired')
            
            if success:
                print(f"✅ Timer {timer_id} fired and marked as fired")
            else:
                print(f"⚠️ Timer {timer_id} fired but failed to update state")
            
        except Exception as e:
            print(f"❌ Error firing timer {timer_id}: {e}")
            # Mark as failed
            try:
                self.sheets_manager.update_timer_state(config_spreadsheet_id, timer_id, 'failed')
            except Exception as update_error:
                print(f"❌ Failed to mark timer {timer_id} as failed: {update_error}")
    
    async def _send_timer_message(self, timer_data: Dict[str, Any]):
        """Send Discord message based on timer type"""
        try:
            timer_type = timer_data['type']
            channel_id = int(timer_data['channel_id'])
            
            if timer_type.startswith('task_'):
                await self._send_task_reminder(timer_data, channel_id)
            elif timer_type.startswith('meeting_'):
                await self._send_meeting_reminder(timer_data, channel_id)
            else:
                print(f"⚠️ Unknown timer type: {timer_type}")
        
        except Exception as e:
            print(f"❌ Error sending timer message: {e}")
    
    async def _send_task_reminder(self, timer_data: Dict[str, Any], channel_id: int):
        """Send task-specific reminder message"""
        try:
            timer_type = timer_data['type']
            title = timer_data.get('title', 'Unknown Task')
            mention = timer_data.get('mention', '')
            
            message = ""
            
            if timer_type == 'task_reminder_24h':
                message = f"⏰ **Task Reminder - 24 Hours**\n"
                message += f"**{title}** is due in 24 hours\n"
                if mention:
                    message += f"{mention} - Please check your task status!"
            
            elif timer_type == 'task_reminder_2h':
                message = f"⚠️ **Task Reminder - 2 Hours**\n"
                message += f"**{title}** is due in 2 hours\n"
                if mention:
                    message += f"{mention} - Please check your task status!"
            
            elif timer_type == 'task_overdue':
                message = f"🚨 **OVERDUE TASK** 🚨\n"
                message += f"**{title}** is now overdue\n"
                if mention:
                    message += f"{mention} - Please complete this task immediately!"
            
            elif timer_type == 'task_escalate':
                message = f"📢 **TASK ESCALATION** 📢\n"
                message += f"**{title}** has been overdue for 48 hours\n"
                message += f"@everyone - This task needs immediate attention!"
            
            if message:
                await self.bot.send_any_message(message, channel_id)
                print(f"✅ Sent {timer_type} message for task {title}")
        
        except Exception as e:
            print(f"❌ Error sending task reminder: {e}")
    
    async def _send_meeting_reminder(self, timer_data: Dict[str, Any], channel_id: int):
        """Send meeting-specific reminder message"""
        try:
            timer_type = timer_data['type']
            title = timer_data.get('title', 'Unknown Meeting')
            mention = timer_data.get('mention', '@everyone')
            
            message = ""
            
            if timer_type == 'meeting_reminder_2h':
                message = f"📅 **Meeting Reminder - 2 Hours**\n"
                message += f"**{title}** starts in 2 hours\n"
                message += f"{mention} - Please prepare for the meeting!"
            
            elif timer_type == 'meeting_start':
                message = f"🚀 **Meeting Starting Now** 🚀\n"
                message += f"**{title}**\n"
                message += f"{mention} - The meeting is starting now!"
            
            if message:
                await self.bot.send_any_message(message, channel_id)
                print(f"✅ Sent {timer_type} message for meeting {title}")
        
        except Exception as e:
            print(f"❌ Error sending meeting reminder: {e}")
    
    async def _get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details by ID from all guilds"""
        try:
            all_guilds = self.bot.setup_manager.status_manager.get_all_guilds()
            
            for guild_id, guild_config in all_guilds.items():
                if not guild_config.get('setup_complete', False):
                    continue
                
                # Check monthly sheets for tasks
                monthly_sheets = guild_config.get('monthly_sheets', {})
                tasks_sheet_id = monthly_sheets.get('tasks')
                
                if tasks_sheet_id:
                    tasks = self.sheets_manager.get_all_tasks(tasks_sheet_id)
                    for task in tasks:
                        if task.get('task_id') == task_id:
                            return task
            
            return None
        
        except Exception as e:
            print(f"❌ Error getting task by ID: {e}")
            return None
    
    async def _get_meeting_by_id(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """Get meeting details by ID from all guilds"""
        try:
            all_guilds = self.bot.setup_manager.status_manager.get_all_guilds()
            
            for guild_id, guild_config in all_guilds.items():
                if not guild_config.get('setup_complete', False):
                    continue
                
                # Check monthly sheets for meetings
                monthly_sheets = guild_config.get('monthly_sheets', {})
                meetings_sheet_id = monthly_sheets.get('meetings')
                
                if meetings_sheet_id:
                    meetings = self.sheets_manager.get_all_meetings(meetings_sheet_id)
                    for meeting in meetings:
                        if meeting.get('meeting_id') == meeting_id:
                            return meeting
            
            return None
        
        except Exception as e:
            print(f"❌ Error getting meeting by ID: {e}")
            return None
