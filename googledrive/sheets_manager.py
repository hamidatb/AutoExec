import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .drive_auth import get_credentials
from config import Config

class ClubSheetsManager:
    """
    Manages Google Sheets for the Club Exec Task Manager Bot.
    Handles tasks, meetings, config, and people sheets.
    """
    
    def __init__(self):
        """Initialize the sheets manager with credentials."""
        creds = get_credentials()
        self.sheets_service = build("sheets", "v4", credentials=creds)
        self.drive_service = build("drive", "v3", credentials=creds)
        self.config = Config()
        
    def create_master_config_sheet(self, club_name: str, admin_discord_id: str, folder_id: str = None, timezone: str = 'America/Edmonton', exec_members: List[Dict] = None) -> str:
        """
        Creates the master configuration sheet for the club.
        
        Args:
            club_name: Name of the club
            admin_discord_id: Discord ID of the admin
            folder_id: Optional Google Drive folder ID to place the sheet in
            
        Returns:
            str: Spreadsheet ID of the created sheet
        """
        try:
            # Create the spreadsheet
            spreadsheet = {
                'properties': {
                    'title': f'{club_name} Task Manager Config'
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'config',
                            'gridProperties': {'rowCount': 100, 'columnCount': 10}
                        }
                    },
                    {
                        'properties': {
                            'title': 'people',
                            'gridProperties': {'rowCount': 100, 'columnCount': 5}
                        }
                    },
                    {
                        'properties': {
                            'title': 'logs',
                            'gridProperties': {'rowCount': 100, 'columnCount': 8}
                        }
                    },
                    {
                        'properties': {
                            'title': 'timers',
                            'gridProperties': {'rowCount': 1000, 'columnCount': 8}
                        }
                    }
                ]
            }
            
            result = self.sheets_service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = result['spreadsheetId']
            
            # Initialize config sheet
            config_data = [
                ['club_name', club_name],
                ['admin_discord_id', admin_discord_id],
                ['default_channels', ''],
                ['allowed_role_ids', ''],
                ['timezone', timezone],
                ['task_reminder_channel_id', str(self.config.TASK_REMINDER_CHANNEL_ID)],
                ['meeting_reminder_channel_id', str(self.config.MEETING_REMINDER_CHANNEL_ID)],
                ['escalation_channel_id', str(self.config.ESCALATION_CHANNEL_ID)],
                ['free_speak_channel_id', '']
            ]
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='config!A1',
                valueInputOption='RAW',
                body={'values': config_data}
            ).execute()
            
            # Initialize people sheet headers
            people_headers = [['name', 'discord_id', 'role', 'created_at', 'updated_at']]
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='people!A1',
                valueInputOption='RAW',
                body={'values': people_headers}
            ).execute()
            
            # Add exec members to people sheet if provided
            if exec_members:
                people_data = []
                current_time = datetime.now().isoformat()
                for member in exec_members:
                    people_data.append([
                        member.get('name', ''),
                        member.get('discord_id', ''),
                        member.get('role', 'General Team Member'),
                        current_time,
                        current_time
                    ])
                
                if people_data:
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range='people!A2',
                        valueInputOption='RAW',
                        body={'values': people_data}
                    ).execute()
            
            # Initialize logs sheet headers
            logs_headers = [['timestamp', 'action', 'user_id', 'details', 'status', 'error_message', 'created_at']]
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='logs!A1',
                valueInputOption='RAW',
                body={'values': logs_headers}
            ).execute()
            
            # Initialize timers sheet headers
            timers_headers = [['id', 'guild_id', 'type', 'ref_type', 'ref_id', 'fire_at_utc', 'channel_id', 'state', 'title', 'mention']]
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='timers!A1',
                valueInputOption='RAW',
                body={'values': timers_headers}
            ).execute()
            
            # Move sheet to specified folder if provided
            if folder_id:
                try:
                    # Remove from root and add to specified folder
                    self.drive_service.files().update(
                        fileId=spreadsheet_id,
                        addParents=folder_id,
                        removeParents='root'
                    ).execute()
                except Exception as e:
                    print(f"Warning: Could not move config sheet to folder {folder_id}: {e}")
            
            return spreadsheet_id
            
        except HttpError as error:
            print(f"Error creating master config sheet: {error}")
            return None
    
    def create_monthly_sheets(self, club_name: str, month_year: str, folder_id: str = None) -> Dict[str, str]:
        """
        Creates monthly task and meeting sheets.
        
        Args:
            club_name: Name of the club
            month_year: Month and year (e.g., "September 2025")
            folder_id: Optional Google Drive folder ID to place the sheets in
            
        Returns:
            Dict with spreadsheet IDs for tasks and meetings
        """
        try:
            # Create tasks sheet
            tasks_spreadsheet = {
                'properties': {
                    'title': f'{club_name} Tasks - {month_year}'
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'tasks',
                            'gridProperties': {'rowCount': 1000, 'columnCount': 12}
                        }
                    }
                ]
            }
            
            tasks_result = self.sheets_service.spreadsheets().create(body=tasks_spreadsheet).execute()
            tasks_id = tasks_result['spreadsheetId']
            
            # Initialize tasks sheet headers
            tasks_headers = [
                ['task_id', 'title', 'owner_discord_id', 'owner_name', 'due_at', 
                 'status', 'priority', 'source_doc', 'channel_id', 'notes', 'created_at', 'updated_at']
            ]
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=tasks_id,
                range='tasks!A1',
                valueInputOption='RAW',
                body={'values': tasks_headers}
            ).execute()
            
            # Move tasks sheet to specified folder if provided
            if folder_id:
                try:
                    self.drive_service.files().update(
                        fileId=tasks_id,
                        addParents=folder_id,
                        removeParents='root'
                    ).execute()
                except Exception as e:
                    print(f"Warning: Could not move tasks sheet to folder {folder_id}: {e}")
            
            # Create meetings sheet
            meetings_spreadsheet = {
                'properties': {
                    'title': f'{club_name} Meetings - {month_year}'
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'meetings',
                            'gridProperties': {'rowCount': 100, 'columnCount': 12}
                        }
                    }
                ]
            }
            
            meetings_result = self.sheets_service.spreadsheets().create(body=meetings_spreadsheet).execute()
            meetings_id = meetings_result['spreadsheetId']
            
            # Initialize meetings sheet headers
            meetings_headers = [
                ['meeting_id', 'title', 'start_at_utc', 'end_at_utc', 'start_at_local', 
                 'end_at_local', 'location', 'meeting_link', 'channel_id', 'minutes_link', 'status', 'created_by', 'created_at_utc', 'updated_at']
            ]
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=meetings_id,
                range='meetings!A1',
                valueInputOption='RAW',
                body={'values': meetings_headers}
            ).execute()
            
            # Move meetings sheet to specified folder if provided
            if folder_id:
                try:
                    self.drive_service.files().update(
                        fileId=meetings_id,
                        addParents=folder_id,
                        removeParents='root'
                    ).execute()
                except Exception as e:
                    print(f"Warning: Could not move meetings sheet to folder {folder_id}: {e}")
            
            return {
                'tasks': tasks_id,
                'meetings': meetings_id
            }
            
        except HttpError as error:
            print(f"Error creating monthly sheets: {error}")
            return {}
    
    def add_task(self, spreadsheet_id: str, task_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Adds a new task to the tasks sheet.
        
        Args:
            spreadsheet_id: ID of the tasks spreadsheet
            task_data: Dictionary containing task information
            
        Returns:
            tuple: (success: bool, task_id: str)
        """
        try:
            task_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            
            task_row = [
                task_id,
                task_data.get('title', ''),
                task_data.get('owner_discord_id', ''),
                task_data.get('owner_name', ''),
                task_data.get('due_at', ''),
                task_data.get('status', 'open'),
                task_data.get('priority', 'medium'),
                task_data.get('source_doc', ''),
                task_data.get('channel_id', ''),
                task_data.get('notes', ''),
                now,
                now
            ]
            
            # Find the next empty row
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='tasks!A:A'
            ).execute()
            
            next_row = len(result.get('values', [])) + 1
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'tasks!A{next_row}',
                valueInputOption='RAW',
                body={'values': [task_row]}
            ).execute()
            
            return True, task_id
            
        except HttpError as error:
            print(f"Error adding task: {error}")
            return False, ""
    
    def add_meeting(self, spreadsheet_id: str, meeting_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Adds a new meeting to the meetings sheet.
        
        Args:
            spreadsheet_id: ID of the meetings spreadsheet
            meeting_data: Dictionary containing meeting information
            
        Returns:
            tuple: (success: bool, meeting_id: str)
        """
        try:
            meeting_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            
            meeting_row = [
                meeting_id,
                meeting_data.get('title', ''),
                meeting_data.get('start_at_utc', ''),
                meeting_data.get('end_at_utc', ''),
                meeting_data.get('start_at_local', ''),
                meeting_data.get('end_at_local', ''),
                meeting_data.get('location', ''),
                meeting_data.get('meeting_link', ''),
                meeting_data.get('channel_id', ''),
                meeting_data.get('minutes_link', ''),
                meeting_data.get('status', 'scheduled'),
                meeting_data.get('created_by', ''),
                now,
                now
            ]
            
            # Find the next empty row
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='meetings!A:A'
            ).execute()
            
            next_row = len(result.get('values', [])) + 1
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'meetings!A{next_row}',
                valueInputOption='RAW',
                body={'values': [meeting_row]}
            ).execute()
            
            return True, meeting_id
            
        except HttpError as error:
            print(f"Error adding meeting: {error}")
            return False, ""
    
    def get_tasks_by_user(self, spreadsheet_id: str, discord_id: str) -> List[Dict[str, Any]]:
        """
        Gets all tasks for a specific user.
        
        Args:
            spreadsheet_id: ID of the tasks spreadsheet
            discord_id: Discord ID of the user
            
        Returns:
            List of task dictionaries
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='tasks!A:L'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:  # No data or only headers
                return []
            
            headers = values[0]
            tasks = []
            
            for row in values[1:]:
                if len(row) >= len(headers):
                    # Check if this task belongs to the user
                    # Handle both raw Discord ID and mention format (<@ID>)
                    owner_discord_id = row[2] if len(row) > 2 else ""
                    is_user_task = (
                        owner_discord_id == discord_id or  # Exact match
                        owner_discord_id == f"<@{discord_id}>" or  # Mention format
                        (owner_discord_id.startswith("<@") and owner_discord_id.endswith(">") and 
                         owner_discord_id[2:-1] == discord_id)  # Extract ID from mention format
                    )
                    
                    if is_user_task:
                        task = dict(zip(headers, row))
                        tasks.append(task)
            
            return tasks
            
        except HttpError as error:
            print(f"Error getting tasks by user: {error}")
            return []
    
    def get_all_tasks(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """
        Gets all tasks from the tasks sheet.
        
        Args:
            spreadsheet_id: ID of the tasks spreadsheet
            
        Returns:
            List of all task dictionaries
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='tasks!A:L'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:  # No data or only headers
                return []
            
            headers = values[0]
            tasks = []
            
            for row in values[1:]:
                if len(row) >= len(headers):
                    task = dict(zip(headers, row))
                    tasks.append(task)
            
            return tasks
            
        except HttpError as error:
            print(f"Error getting all tasks: {error}")
            return []
    
    def search_tasks_by_title(self, spreadsheet_id: str, title_query: str, 
                             status_filter: str = None) -> List[Dict[str, Any]]:
        """
        Search for tasks by title (case-insensitive partial match).
        
        Args:
            spreadsheet_id: ID of the tasks spreadsheet
            title_query: Title or partial title to search for
            status_filter: Optional status filter ('open', 'in_progress', 'done', 'blocked')
            
        Returns:
            List of matching task dictionaries
        """
        try:
            all_tasks = self.get_all_tasks(spreadsheet_id)
            matching_tasks = []
            
            title_query_lower = title_query.lower().strip()
            
            for task in all_tasks:
                task_title = task.get('title', '').lower()
                
                # Check if title matches (partial match)
                if title_query_lower in task_title:
                    # Apply status filter if provided
                    if status_filter is None or task.get('status') == status_filter:
                        matching_tasks.append(task)
            
            # Sort by due date (most urgent first)
            matching_tasks.sort(key=lambda x: x.get('due_at', ''), reverse=False)
            
            return matching_tasks
            
        except Exception as e:
            print(f"Error searching tasks by title: {e}")
            return []
    
    def get_all_meetings(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """
        Gets all meetings from the meetings sheet.
        
        Args:
            spreadsheet_id: ID of the meetings spreadsheet
            
        Returns:
            List of all meeting dictionaries
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='meetings!A:N'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:  # No data or only headers
                return []
            
            headers = values[0]
            meetings = []
            
            for row in values[1:]:
                if len(row) >= len(headers):
                    meeting = dict(zip(headers, row))
                    meetings.append(meeting)
            
            return meetings
            
        except HttpError as error:
            print(f"Error getting all meetings: {error}")
            return []
    
    def update_task_status(self, spreadsheet_id: str, task_id: str, new_status: str) -> bool:
        """
        Updates the status of a task.
        
        Args:
            spreadsheet_id: ID of the tasks spreadsheet
            task_id: ID of the task to update
            new_status: New status for the task
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='tasks!A:L'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return False
            
            # Find the row with the task_id
            for i, row in enumerate(values[1:], start=2):
                if row[0] == task_id:  # task_id column
                    # Update status and updated_at
                    now = datetime.now(timezone.utc).isoformat()
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f'tasks!F{i}:L{i}',
                        valueInputOption='RAW',
                        body={'values': [[new_status, row[6], row[7], row[8], row[9], row[10], now]]}
                    ).execute()
                    return True
            
            return False
            
        except HttpError as error:
            print(f"Error updating task status: {error}")
            return False
    
    def update_task_deadline(self, spreadsheet_id: str, task_id: str, new_deadline: str) -> bool:
        """
        Updates the deadline of a task.
        
        Args:
            spreadsheet_id: ID of the tasks spreadsheet
            task_id: ID of the task to update
            new_deadline: New deadline for the task
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='tasks!A:L'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return False
            
            # Find the row with the task_id
            for i, row in enumerate(values[1:], start=2):
                if row[0] == task_id:  # task_id column
                    # Update deadline and updated_at
                    now = datetime.now(timezone.utc).isoformat()
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f'tasks!E{i}:L{i}',
                        valueInputOption='RAW',
                        body={'values': [[new_deadline, row[5], row[6], row[7], row[8], row[9], row[10], now]]}
                    ).execute()
                    return True
            
            return False
            
        except HttpError as error:
            print(f"Error updating task deadline: {error}")
            return False
    
    def update_meeting_status(self, spreadsheet_id: str, meeting_id: str, new_status: str) -> bool:
        """
        Updates the status of a meeting.
        
        Args:
            spreadsheet_id: ID of the meetings spreadsheet
            meeting_id: ID of the meeting to update
            new_status: New status for the meeting
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='meetings!A:N'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return False
            
            # Find the row with the meeting_id
            for i, row in enumerate(values[1:], start=2):
                if row[0] == meeting_id:  # meeting_id column
                    # Update status and updated_at
                    now = datetime.now(timezone.utc).isoformat()
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f'meetings!K{i}:N{i}',
                        valueInputOption='RAW',
                        body={'values': [[new_status, row[11], row[12], now]]}
                    ).execute()
                    return True
            
            return False
            
        except HttpError as error:
            print(f"Error updating meeting status: {error}")
            return False
    
    def update_meeting_fields(self, spreadsheet_id: str, meeting_id: str, updates: Dict[str, Any]) -> bool:
        """
        Updates multiple fields of a meeting.
        
        Args:
            spreadsheet_id: ID of the meetings spreadsheet
            meeting_id: ID of the meeting to update
            updates: Dictionary of field names to new values
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='meetings!A:N'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return False
            
            headers = values[0]
            
            # Find the row with the meeting_id
            for i, row in enumerate(values[1:], start=2):
                if row[0] == meeting_id:  # meeting_id column
                    # Create updated row
                    updated_row = row.copy()
                    
                    # Update fields based on the updates dictionary
                    for field, value in updates.items():
                        if field in headers:
                            field_index = headers.index(field)
                            # Ensure the row is long enough
                            while len(updated_row) <= field_index:
                                updated_row.append('')
                            updated_row[field_index] = str(value)
                    
                    # Update updated_at field
                    if 'updated_at' in headers:
                        updated_at_index = headers.index('updated_at')
                        while len(updated_row) <= updated_at_index:
                            updated_row.append('')
                        updated_row[updated_at_index] = datetime.now(timezone.utc).isoformat()
                    
                    # Update the row in the sheet
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f'meetings!A{i}:N{i}',
                        valueInputOption='RAW',
                        body={'values': [updated_row]}
                    ).execute()
                    return True
            
            return False
            
        except HttpError as error:
            print(f"Error updating meeting fields: {error}")
            return False
    
    def update_meeting_minutes(self, spreadsheet_id: str, meeting_id: str, minutes_url: str) -> bool:
        """
        Updates the minutes document URL for a meeting.
        
        Args:
            spreadsheet_id: ID of the meetings spreadsheet
            meeting_id: ID of the meeting to update
            minutes_url: URL of the minutes document
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='meetings!A:N'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return False
            
            # Find the row with the meeting_id
            for i, row in enumerate(values[1:], start=2):
                if row[0] == meeting_id:  # meeting_id column
                    # Update minutes URL and updated_at
                    now = datetime.now(timezone.utc).isoformat()
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f'meetings!J{i}:N{i}',
                        valueInputOption='RAW',
                        body={'values': [[minutes_url, row[10], row[11], row[12], now]]}
                    ).execute()
                    return True
            
            return False
            
        except HttpError as error:
            print(f"Error updating meeting minutes: {error}")
            return False
    
    def update_config_channels(self, config_spreadsheet_id: str, task_channel_id: str, 
                              meeting_channel_id: str, escalation_channel_id: str, 
                              free_speak_channel_id: str = None, general_announcements_channel_id: str = None) -> bool:
        """
        Updates the channel configuration in the config sheet.
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            task_channel_id: Channel ID for task reminders
            meeting_channel_id: Channel ID for meeting reminders
            escalation_channel_id: Channel ID for escalations
            free_speak_channel_id: Channel ID for free-speak (optional)
            general_announcements_channel_id: Channel ID for general announcements (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update channel IDs in config sheet
            config_data = [
                ['task_reminder_channel_id', task_channel_id],
                ['meeting_reminder_channel_id', meeting_channel_id],
                ['escalation_channel_id', escalation_channel_id]
            ]
            
            # Add general announcements channel if provided
            if general_announcements_channel_id:
                config_data.append(['general_announcements_channel_id', general_announcements_channel_id])
            
            # Add free-speak channel if provided
            if free_speak_channel_id:
                config_data.append(['free_speak_channel_id', free_speak_channel_id])
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=config_spreadsheet_id,
                range='config!F1',
                valueInputOption='RAW',
                body={'values': config_data}
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"Error updating config channels: {error}")
            return False
    
    def log_action(self, config_spreadsheet_id: str, action: str, user_id: str, details: str, status: str = 'success', error_message: str = ''):
        """
        Logs an action to the logs sheet.
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            action: Action performed
            user_id: Discord ID of the user who performed the action
            details: Details about the action
            status: Status of the action (success, error, etc.)
            error_message: Error message if applicable
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            log_row = [
                now,
                action,
                user_id,
                details,
                status,
                error_message,
                now
            ]
            
            # Find the next empty row
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=config_spreadsheet_id,
                range='logs!A:A'
            ).execute()
            
            next_row = len(result.get('values', [])) + 1
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=config_spreadsheet_id,
                range=f'logs!A{next_row}',
                valueInputOption='RAW',
                body={'values': [log_row]}
            ).execute()
            
        except HttpError as error:
            print(f"Error logging action: {error}")
    
    def add_timer(self, config_spreadsheet_id: str, timer_data: Dict[str, Any]) -> bool:
        """
        Adds a new timer to the timers sheet.
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            timer_data: Dictionary containing timer information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            timer_row = [
                timer_data.get('id', ''),
                timer_data.get('guild_id', ''),
                timer_data.get('type', ''),
                timer_data.get('ref_type', ''),
                timer_data.get('ref_id', ''),
                timer_data.get('fire_at_utc', ''),
                timer_data.get('channel_id', ''),
                timer_data.get('state', 'active'),
                timer_data.get('title', 'Unknown'),
                timer_data.get('mention', '')
            ]
            
            # Find the next empty row
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=config_spreadsheet_id,
                range='timers!A:A'
            ).execute()
            
            next_row = len(result.get('values', [])) + 1
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=config_spreadsheet_id,
                range=f'timers!A{next_row}',
                valueInputOption='RAW',
                body={'values': [timer_row]}
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"Error adding timer: {error}")
            return False
    
    def get_timers(self, config_spreadsheet_id: str) -> List[Dict[str, Any]]:
        """
        Gets all timers from the timers sheet.
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            
        Returns:
            List of timer dictionaries
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=config_spreadsheet_id,
                range='timers!A:J'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:  # No data or only headers
                return []
            
            headers = values[0]
            timers = []
            
            for row in values[1:]:
                if len(row) >= len(headers):
                    timer = dict(zip(headers, row))
                    timers.append(timer)
            
            return timers
            
        except HttpError as error:
            print(f"Error getting timers: {error}")
            return []
    
    def update_timer_state(self, config_spreadsheet_id: str, timer_id: str, new_state: str) -> bool:
        """
        Updates the state of a timer.
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            timer_id: ID of the timer to update
            new_state: New state for the timer
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=config_spreadsheet_id,
                range='timers!A:J'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return False
            
            # Find the row with the timer_id
            for i, row in enumerate(values[1:], start=2):
                if len(row) > 0 and row[0] == timer_id:  # id column
                    # Update state
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=config_spreadsheet_id,
                        range=f'timers!H{i}',
                        valueInputOption='RAW',
                        body={'values': [[new_state]]}
                    ).execute()
                    return True
            
            return False
            
        except HttpError as error:
            print(f"Error updating timer state: {error}")
            return False
    
    def delete_timer(self, config_spreadsheet_id: str, timer_id: str) -> bool:
        """
        Deletes a timer from the timers sheet.
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            timer_id: ID of the timer to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=config_spreadsheet_id,
                range='timers!A:H'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return False
            
            # Find the row with the timer_id
            for i, row in enumerate(values[1:], start=2):
                if row[0] == timer_id:  # id column
                    # Clear the row
                    self.sheets_service.spreadsheets().values().clear(
                        spreadsheetId=config_spreadsheet_id,
                        range=f'timers!A{i}:H{i}'
                    ).execute()
                    return True
            
            return False
            
        except HttpError as error:
            print(f"Error deleting timer: {error}")
            return False
    
    def ensure_monthly_sheets_exist(self, club_name: str, month_year: str, folder_id: str = None) -> Dict[str, str]:
        """
        Ensures that monthly sheets exist for the given month and year.
        Creates them if they don't exist.
        
        Args:
            club_name: Name of the club
            month_year: Month and year (e.g., "September 2025")
            folder_id: Optional Google Drive folder ID to place the sheets in
            
        Returns:
            Dict with spreadsheet IDs for tasks and meetings
        """
        try:
            # Check if sheets already exist by trying to find them
            # This is a simplified check - in practice, you might want to maintain
            # a registry of created sheets in the config sheet
            
            # For now, we'll always create new sheets for the month
            # In a production system, you'd check if they already exist
            return self.create_monthly_sheets(club_name, month_year, folder_id)
            
        except Exception as e:
            print(f"Error ensuring monthly sheets exist: {e}")
            return {}
    
    def get_or_create_monthly_sheets(self, club_name: str, month_year: str, folder_id: str = None) -> Dict[str, str]:
        """
        Gets existing monthly sheets or creates new ones if they don't exist.
        
        Args:
            club_name: Name of the club
            month_year: Month and year (e.g., "September 2025")
            folder_id: Optional Google Drive folder ID to place the sheets in
            
        Returns:
            Dict with spreadsheet IDs for tasks and meetings
        """
        try:
            # Try to find existing sheets first
            # This would involve searching through the config sheet or Drive
            # For now, we'll create new sheets each time
            # In production, you'd implement proper sheet discovery
            
            return self.create_monthly_sheets(club_name, month_year, folder_id)
            
        except Exception as e:
            print(f"Error getting or creating monthly sheets: {e}")
            return {}
    
    def get_active_timers(self, config_spreadsheet_id: str) -> List[Dict[str, Any]]:
        """
        Get all active timers from the timers sheet.
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            
        Returns:
            List of active timer dictionaries
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=config_spreadsheet_id,
                range='timers!A:H'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return []
            
            headers = values[0]
            active_timers = []
            
            for row in values[1:]:
                if len(row) >= len(headers):
                    timer = dict(zip(headers, row))
                    if timer.get('state') == 'active':
                        active_timers.append(timer)
            
            return active_timers
            
        except HttpError as error:
            print(f"Error getting active timers: {error}")
            return []
    
    def cleanup_old_timers(self, config_spreadsheet_id: str, days_old: int = 7):
        """
        Clean up old fired/failed timers to keep the sheet manageable.
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            days_old: Number of days old timers to clean up (default: 7)
        """
        try:
            # Get all timers
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=config_spreadsheet_id,
                range='timers!A:H'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return
            
            headers = values[0]
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            # Find rows to delete (old fired/failed timers)
            rows_to_delete = []
            for i, row in enumerate(values[1:], start=2):  # Start from row 2 (after header)
                if len(row) >= len(headers):
                    timer = dict(zip(headers, row))
                    if timer.get('state') in ['fired', 'failed']:
                        try:
                            fire_at = datetime.fromisoformat(timer.get('fire_at_utc', ''))
                            if fire_at < cutoff_date:
                                rows_to_delete.append(i)
                        except ValueError:
                            continue
            
            # Delete rows (in reverse order to maintain row numbers)
            for row_num in reversed(rows_to_delete):
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=config_spreadsheet_id,
                    body={
                        'requests': [{
                            'deleteDimension': {
                                'range': {
                                    'sheetId': 0,  # Assuming timers is the first sheet
                                    'dimension': 'ROWS',
                                    'startIndex': row_num - 1,
                                    'endIndex': row_num
                                }
                            }
                        }]
                    }
                ).execute()
            
            print(f"Cleaned up {len(rows_to_delete)} old timers")
            
        except HttpError as error:
            print(f"Error cleaning up old timers: {error}")
    
    def get_timer_by_id(self, config_spreadsheet_id: str, timer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific timer by ID.
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            timer_id: ID of the timer to find
            
        Returns:
            Timer dictionary or None if not found
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=config_spreadsheet_id,
                range='timers!A:H'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return None
            
            headers = values[0]
            
            for row in values[1:]:
                if len(row) >= len(headers):
                    timer = dict(zip(headers, row))
                    if timer.get('id') == timer_id:
                        return timer
            
            return None
            
        except HttpError as error:
            print(f"Error getting timer by ID: {error}")
            return None
    
    def get_timers_by_ref(self, config_spreadsheet_id: str, ref_type: str, ref_id: str) -> List[Dict[str, Any]]:
        """
        Get all timers for a specific reference (task or meeting).
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            ref_type: Type of reference ('task' or 'meeting')
            ref_id: ID of the reference
            
        Returns:
            List of timer dictionaries
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=config_spreadsheet_id,
                range='timers!A:H'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return []
            
            headers = values[0]
            matching_timers = []
            
            for row in values[1:]:
                if len(row) >= len(headers):
                    timer = dict(zip(headers, row))
                    if timer.get('ref_type') == ref_type and timer.get('ref_id') == ref_id:
                        matching_timers.append(timer)
            
            return matching_timers
            
        except HttpError as error:
            print(f"Error getting timers by reference: {error}")
            return []