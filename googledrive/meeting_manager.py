import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from .sheets_manager import ClubSheetsManager
from .minutes_parser import MinutesParser

class MeetingManager:
    """
    Manages meetings for the Club Exec Task Manager Bot.
    Handles meeting scheduling, reminders, and minutes processing.
    """
    
    def __init__(self):
        """Initialize the meeting manager."""
        self.sheets_manager = ClubSheetsManager()
        self.minutes_parser = MinutesParser()
        
    async def schedule_meeting(self, meeting_data: Dict[str, Any], 
                              meetings_spreadsheet_id: str, 
                              club_name: str = None, folder_id: str = None) -> bool:
        """
        Schedules a new meeting.
        
        Args:
            meeting_data: Dictionary containing meeting information
            meetings_spreadsheet_id: ID of the meetings spreadsheet
            club_name: Name of the club (for automatic sheet creation)
            folder_id: Folder ID for automatic sheet creation
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate required fields
            if not meeting_data.get('title') or not meeting_data.get('start_at_utc'):
                print("Meeting must have title and start time")
                return False
            
            # Parse and validate times
            try:
                start_time = datetime.fromisoformat(meeting_data['start_at_utc'])
                if meeting_data.get('end_at_utc'):
                    end_time = datetime.fromisoformat(meeting_data['end_at_utc'])
                    if end_time <= start_time:
                        print("End time must be after start time")
                        return False
            except ValueError:
                print("Invalid time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
                return False
            
            # Determine the month for the meeting
            current_month = datetime.now().strftime("%B %Y")
            
            # Ensure monthly sheets exist for this month
            if club_name and folder_id:
                monthly_sheets = self.sheets_manager.get_or_create_monthly_sheets(
                    club_name, current_month, folder_id
                )
                if monthly_sheets and 'meetings' in monthly_sheets:
                    meetings_spreadsheet_id = monthly_sheets['meetings']
            
            # Add meeting to spreadsheet
            success = self.sheets_manager.add_meeting(meetings_spreadsheet_id, meeting_data)
            
            if success:
                print(f"Meeting '{meeting_data['title']}' scheduled successfully")
                
                # Schedule meeting reminders
                await self._schedule_meeting_reminders(meeting_data, meetings_spreadsheet_id)
            
            return success
            
        except Exception as e:
            print(f"Error scheduling meeting: {e}")
            return False
    
    async def cancel_meeting(self, meeting_id: str, meetings_spreadsheet_id: str) -> bool:
        """
        Cancels a scheduled meeting.
        
        Args:
            meeting_id: ID of the meeting to cancel
            meetings_spreadsheet_id: ID of the meetings spreadsheet
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update meeting status to canceled
            success = self.sheets_manager.update_meeting_status(
                meetings_spreadsheet_id, meeting_id, 'canceled'
            )
            
            if success:
                print(f"Meeting {meeting_id} canceled")
                
                # Cancel scheduled reminders
                await self._cancel_meeting_reminders(meeting_id)
            
            return success
            
        except Exception as e:
            print(f"Error canceling meeting: {e}")
            return False
    
    async def update_meeting(self, meeting_id: str, meetings_spreadsheet_id: str, 
                           updates: Dict[str, Any]) -> bool:
        """
        Updates a meeting with new information.
        
        Args:
            meeting_id: ID of the meeting to update
            meetings_spreadsheet_id: ID of the meetings spreadsheet
            updates: Dictionary of fields to update (title, start_at_utc, end_at_utc, location, meeting_link, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update meeting fields
            success = self.sheets_manager.update_meeting_fields(
                meetings_spreadsheet_id, meeting_id, updates
            )
            
            if success:
                print(f"Meeting {meeting_id} updated with: {updates}")
                
                # If time was changed, we might need to reschedule reminders
                if 'start_at_utc' in updates:
                    # Cancel old reminders and schedule new ones
                    await self._cancel_meeting_reminders(meeting_id)
                    # Note: We'd need config_spreadsheet_id to reschedule, but for now just cancel old ones
            
            return success
            
        except Exception as e:
            print(f"Error updating meeting: {e}")
            return False
    
    async def link_minutes(self, meeting_id: str, new_minutes_link: str,
                          meetings_spreadsheet_id: str, tasks_spreadsheet_id: str,
                          people_mapping: Dict[str, str]) -> bool:
        """
        Links minutes document to a meeting and processes action items.
        
        Args:
            meeting_id: ID of the meeting
            new_minutes_link: URL of the minutes document
            meetings_spreadsheet_id: ID of the meetings spreadsheet
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            people_mapping: Dictionary mapping names to Discord IDs
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update meeting with minutes URL
            success = self.sheets_manager.update_meeting_minutes(
                meetings_spreadsheet_id, meeting_id, new_minutes_link
            )
            
            if not success:
                print(f"Failed to update meeting {meeting_id} with minutes URL")
                return False
            
            # Process minutes and create tasks
            created_tasks = await self.minutes_parser.create_tasks_from_minutes(
                new_minutes_link, tasks_spreadsheet_id, people_mapping
            )
            
            if created_tasks:
                print(f"Created {len(created_tasks)} tasks from meeting minutes")
                
                # Update meeting status to completed
                await self.sheets_manager.update_meeting_status(
                    meetings_spreadsheet_id, meeting_id, 'ended'
                )
            
            return True
            
        except Exception as e:
            print(f"Error linking minutes: {e}")
            return False
    
    def get_upcoming_meetings(self, meetings_spreadsheet_id: str, 
                             limit: int = 5) -> List[Dict[str, Any]]:
        """
        Gets upcoming meetings.
        
        Args:
            meetings_spreadsheet_id: ID of the meetings spreadsheet
            limit: Maximum number of meetings to return
            
        Returns:
            List of upcoming meeting dictionaries
        """
        try:
            # Get all scheduled meetings
            all_meetings = self.sheets_manager.get_all_meetings(meetings_spreadsheet_id)
            upcoming_meetings = []
            
            now = datetime.now(timezone.utc)
            
            for meeting in all_meetings:
                if meeting.get('status') == 'scheduled' and meeting.get('start_at_utc'):
                    try:
                        start_time = datetime.fromisoformat(meeting['start_at_utc'])
                        if start_time > now:
                            upcoming_meetings.append(meeting)
                    except ValueError:
                        continue
            
            # Sort by start time and limit results
            upcoming_meetings.sort(key=lambda x: x.get('start_at_utc', ''))
            return upcoming_meetings[:limit]
            
        except Exception as e:
            print(f"Error getting upcoming meetings: {e}")
            return []
    
    def get_meeting_by_id(self, meeting_id: str, meetings_spreadsheet_id: str) -> Optional[Dict[str, Any]]:
        """
        Gets a specific meeting by ID.
        
        Args:
            meeting_id: ID of the meeting
            meetings_spreadsheet_id: ID of the meetings spreadsheet
            
        Returns:
            Meeting dictionary or None if not found
        """
        try:
            all_meetings = self.sheets_manager.get_all_meetings(meetings_spreadsheet_id)
            
            for meeting in all_meetings:
                if meeting.get('meeting_id') == meeting_id:
                    return meeting
            
            return None
            
        except Exception as e:
            print(f"Error getting meeting by ID: {e}")
            return None
    
    def search_meetings_by_title(self, title_query: str, meetings_spreadsheet_id: str, 
                                status_filter: str = None) -> List[Dict[str, Any]]:
        """
        Search for meetings by title (case-insensitive partial match).
        
        Args:
            title_query: Title or partial title to search for
            meetings_spreadsheet_id: ID of the meetings spreadsheet
            status_filter: Optional status filter ('scheduled', 'canceled', etc.)
            
        Returns:
            List of matching meeting dictionaries
        """
        try:
            all_meetings = self.sheets_manager.get_all_meetings(meetings_spreadsheet_id)
            matching_meetings = []
            
            title_query_lower = title_query.lower().strip()
            
            for meeting in all_meetings:
                meeting_title = meeting.get('title', '').lower()
                
                # Check if title matches (partial match)
                if title_query_lower in meeting_title:
                    # Apply status filter if provided
                    if status_filter is None or meeting.get('status') == status_filter:
                        matching_meetings.append(meeting)
            
            # Sort by start time (most recent first)
            matching_meetings.sort(key=lambda x: x.get('start_at_utc', ''), reverse=True)
            
            return matching_meetings
            
        except Exception as e:
            print(f"Error searching meetings by title: {e}")
            return []
    
    async def _schedule_meeting_reminders(self, meeting_data: Dict[str, Any],
                                         meetings_spreadsheet_id: str, config_spreadsheet_id: str = None):
        """
        Schedules reminders for a meeting using the Timers tab.
        
        Args:
            meeting_data: Meeting data dictionary
            meetings_spreadsheet_id: ID of the meetings spreadsheet
            config_spreadsheet_id: ID of the config spreadsheet (for timers)
        """
        try:
            if not config_spreadsheet_id:
                print("No config spreadsheet ID provided for timer scheduling")
                return
                
            meeting_id = meeting_data.get('meeting_id', '')
            start_at = meeting_data.get('start_at_utc', '')
            
            if not start_at:
                print(f"No start time for meeting {meeting_id}, skipping reminder scheduling")
                return
            
            # Parse start time
            try:
                start_time = datetime.fromisoformat(start_at)
            except ValueError:
                print(f"Invalid start time format for meeting {meeting_id}: {start_at}")
                return
            
            # Schedule reminders at T-2h and T-0
            reminders = [
                {'type': 'meeting_reminder_2h', 'fire_at': start_time - timedelta(hours=2)},
                {'type': 'meeting_start', 'fire_at': start_time}
            ]
            
            for reminder in reminders:
                timer_data = {
                    'id': f"{meeting_id}_{reminder['type']}",
                    'guild_id': '',  # Will be set by caller
                    'type': reminder['type'],
                    'ref_type': 'meeting',
                    'ref_id': meeting_id,
                    'fire_at_utc': reminder['fire_at'].isoformat(),
                    'channel_id': meeting_data.get('channel_id', ''),
                    'state': 'active'
                }
                
                self.sheets_manager.add_timer(config_spreadsheet_id, timer_data)
                print(f"Scheduled {reminder['type']} reminder for meeting {meeting_id}")
            
        except Exception as e:
            print(f"Error scheduling meeting reminders: {e}")
    
    async def _cancel_meeting_reminders(self, meeting_id: str):
        """
        Cancels reminders for a canceled meeting.
        
        Args:
            meeting_id: ID of the meeting
        """
        try:
            print(f"Canceling reminders for meeting: {meeting_id}")
            
            # Get Discord context to know which guild
            from ae_langchain.tools.context_manager import get_discord_context
            context = get_discord_context()
            guild_id = context.get('guild_id')
            
            if not guild_id:
                print("No Discord context found for canceling meeting reminders")
                return
            
            # Get guild configuration
            from discordbot.discord_client import BOT_INSTANCE
            all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
            guild_config = all_guilds.get(guild_id)
            
            if not guild_config:
                print(f"No guild config found for guild {guild_id}")
                return
            
            config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
            if not config_spreadsheet_id:
                print("No config spreadsheet ID found")
                return
            
            # Get all timers for this meeting
            timers = BOT_INSTANCE.sheets_manager.get_timers(config_spreadsheet_id)
            meeting_timers = [t for t in timers if t.get('ref_id') == meeting_id and t.get('ref_type') == 'meeting']
            
            # Cancel all active timers for this meeting
            cancelled_count = 0
            for timer in meeting_timers:
                if timer.get('state') == 'active':
                    timer_id = timer.get('id')
                    if timer_id:
                        success = BOT_INSTANCE.sheets_manager.update_timer_state(config_spreadsheet_id, timer_id, 'cancelled')
                        if success:
                            cancelled_count += 1
                            print(f"Cancelled timer {timer_id} for meeting {meeting_id}")
            
            print(f"Cancelled {cancelled_count} reminders for meeting {meeting_id}")
            
        except Exception as e:
            print(f"Error canceling meeting reminders: {e}")
    
    async def send_meeting_reminders(self, meetings_spreadsheet_id: str,
                                    reminder_channel_id: int, bot_instance):
        """
        Sends meeting reminders.
        
        Args:
            meetings_spreadsheet_id: ID of the meetings spreadsheet
            reminder_channel_id: Discord channel ID for reminders
            bot_instance: Discord bot instance
        """
        try:
            # Get upcoming meetings in next 2 hours
            upcoming_meetings = self.get_upcoming_meetings(meetings_spreadsheet_id)
            now = datetime.now(timezone.utc)
            
            for meeting in upcoming_meetings:
                try:
                    start_time = datetime.fromisoformat(meeting['start_at_utc'])
                    time_until = start_time - now
                    
                    if timedelta(hours=1, minutes=55) <= time_until <= timedelta(hours=2, minutes=5):
                        # T-2h reminder
                        message = f"@everyone 📅 **Meeting Reminder** 📅\n"
                        message += f"**{meeting['title']}** starts in 2 hours\n"
                        message += f"Time: {meeting.get('start_at_local', meeting['start_at_utc'])}\n"
                        message += f"Channel: <#{meeting.get('channel_id', '')}>"
                        
                        await bot_instance.send_any_message(message, reminder_channel_id)
                    
                    elif timedelta(minutes=-5) <= time_until <= timedelta(minutes=5):
                        # T0 reminder
                        message = f"@everyone 🚀 **Meeting Starting Now** 🚀\n"
                        message += f"**{meeting['title']}**\n"
                        if meeting.get('new_minutes_link'):
                            message += f"Minutes: {meeting['new_minutes_link']}"
                        else:
                            message += "No minutes document linked yet"
                        
                        await bot_instance.send_any_message(message, reminder_channel_id)
                        
                        # Schedule minutes parsing in 30 minutes
                        asyncio.create_task(self._schedule_minutes_parsing(meeting, 30))
                    
                except ValueError:
                    continue
                    
        except Exception as e:
            print(f"Error sending meeting reminders: {e}")
    
    async def _schedule_minutes_parsing(self, meeting: Dict[str, Any], delay_minutes: int):
        """
        Schedules minutes parsing after a delay.
        
        Args:
            meeting: Meeting data dictionary
            delay_minutes: Delay in minutes before parsing
        """
        try:
            await asyncio.sleep(delay_minutes * 60)  # Convert to seconds
            
            # Parse minutes if available
            if meeting.get('new_minutes_link'):
                print(f"Parsing minutes for meeting: {meeting['title']}")
                # This would trigger minutes parsing and task creation
                
        except Exception as e:
            print(f"Error in scheduled minutes parsing: {e}")
    
    def create_agenda_template(self, meeting_title: str) -> str:
        """
        Creates an agenda template for a meeting.
        
        Args:
            meeting_title: Title of the meeting
            
        Returns:
            Agenda template string
        """
        agenda = f"📋 **Meeting Agenda: {meeting_title}** 📋\n\n"
        agenda += "**1. Roll Call & Attendance**\n"
        agenda += "• Present:\n• Absent:\n\n"
        agenda += "**2. Review of Previous Meeting Minutes**\n"
        agenda += "• Action items from last meeting:\n\n"
        agenda += "**3. New Business**\n"
        agenda += "• \n\n"
        agenda += "**4. Action Items & Deadlines**\n"
        agenda += "• \n\n"
        agenda += "**5. Next Meeting**\n"
        agenda += "• Date:\n• Time:\n• Location:\n\n"
        agenda += "**6. Adjournment**\n"
        agenda += "• Meeting ended at:\n• Minutes taken by:"
        
        return agenda
