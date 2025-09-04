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
    
    async def link_minutes(self, meeting_id: str, minutes_doc_url: str,
                          meetings_spreadsheet_id: str, tasks_spreadsheet_id: str,
                          people_mapping: Dict[str, str]) -> bool:
        """
        Links minutes document to a meeting and processes action items.
        
        Args:
            meeting_id: ID of the meeting
            minutes_doc_url: URL of the minutes document
            meetings_spreadsheet_id: ID of the meetings spreadsheet
            tasks_spreadsheet_id: ID of the tasks spreadsheet
            people_mapping: Dictionary mapping names to Discord IDs
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update meeting with minutes URL
            success = self.sheets_manager.update_meeting_minutes(
                meetings_spreadsheet_id, meeting_id, minutes_doc_url
            )
            
            if not success:
                print(f"Failed to update meeting {meeting_id} with minutes URL")
                return False
            
            # Process minutes and create tasks
            created_tasks = await self.minutes_parser.create_tasks_from_minutes(
                minutes_doc_url, tasks_spreadsheet_id, people_mapping
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
            # Cancel scheduled reminders
            
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
                        message = f"📅 **Meeting Reminder** 📅\n"
                        message += f"**{meeting['title']}** starts in 2 hours\n"
                        message += f"Time: {meeting.get('start_at_local', meeting['start_at_utc'])}\n"
                        message += f"Channel: <#{meeting.get('channel_id', '')}>"
                        
                        await bot_instance.send_any_message(message, reminder_channel_id)
                    
                    elif timedelta(minutes=-5) <= time_until <= timedelta(minutes=5):
                        # T0 reminder
                        message = f"🚀 **Meeting Starting Now** 🚀\n"
                        message += f"**{meeting['title']}**\n"
                        if meeting.get('minutes_doc_url'):
                            message += f"Minutes: {meeting['minutes_doc_url']}"
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
            if meeting.get('minutes_doc_url'):
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
