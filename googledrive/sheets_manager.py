import uuid
from datetime import datetime, timezone
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
        self.config = Config()
        
    def create_master_config_sheet(self, club_name: str, admin_discord_id: str) -> str:
        """
        Creates the master configuration sheet for the club.
        
        Args:
            club_name: Name of the club
            admin_discord_id: Discord ID of the admin
            
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
                ['timezone', self.config.TIMEZONE],
                ['task_reminder_channel_id', str(self.config.TASK_REMINDER_CHANNEL_ID)],
                ['meeting_reminder_channel_id', str(self.config.MEETING_REMINDER_CHANNEL_ID)],
                ['escalation_channel_id', str(self.config.ESCALATION_CHANNEL_ID)]
            ]
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='config!A1',
                valueInputOption='RAW',
                body={'values': [config_data]}
            ).execute()
            
            # Initialize people sheet headers
            people_headers = [['name', 'discord_id', 'role', 'created_at', 'updated_at']]
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='people!A1',
                valueInputOption='RAW',
                body={'values': people_headers}
            ).execute()
            
            # Initialize logs sheet headers
            logs_headers = [['timestamp', 'action', 'user_id', 'details', 'status', 'error_message', 'created_at']]
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='logs!A1',
                valueInputOption='RAW',
                body={'values': logs_headers}
            ).execute()
            
            return spreadsheet_id
            
        except HttpError as error:
            print(f"Error creating master config sheet: {error}")
            return None
    
    def create_monthly_sheets(self, club_name: str, month_year: str) -> Dict[str, str]:
        """
        Creates monthly task and meeting sheets.
        
        Args:
            club_name: Name of the club
            month_year: Month and year (e.g., "September 2025")
            
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
                 'end_at_local', 'channel_id', 'minutes_doc_url', 'status', 'created_by', 'created_at_utc', 'updated_at']
            ]
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=meetings_id,
                range='meetings!A1',
                valueInputOption='RAW',
                body={'values': meetings_headers}
            ).execute()
            
            return {
                'tasks': tasks_id,
                'meetings': meetings_id
            }
            
        except HttpError as error:
            print(f"Error creating monthly sheets: {error}")
            return {}
    
    def add_task(self, spreadsheet_id: str, task_data: Dict[str, Any]) -> bool:
        """
        Adds a new task to the tasks sheet.
        
        Args:
            spreadsheet_id: ID of the tasks spreadsheet
            task_data: Dictionary containing task information
            
        Returns:
            bool: True if successful, False otherwise
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
            
            return True
            
        except HttpError as error:
            print(f"Error adding task: {error}")
            return False
    
    def add_meeting(self, spreadsheet_id: str, meeting_data: Dict[str, Any]) -> bool:
        """
        Adds a new meeting to the meetings sheet.
        
        Args:
            spreadsheet_id: ID of the meetings spreadsheet
            meeting_data: Dictionary containing meeting information
            
        Returns:
            bool: True if successful, False otherwise
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
                meeting_data.get('channel_id', ''),
                meeting_data.get('minutes_doc_url', ''),
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
            
            return True
            
        except HttpError as error:
            print(f"Error adding meeting: {error}")
            return False
    
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
                if len(row) >= len(headers) and row[2] == discord_id:  # owner_discord_id column
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
                range='meetings!A:L'
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
                range='meetings!A:L'
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
                        range=f'meetings!I{i}:L{i}',
                        valueInputOption='RAW',
                        body={'values': [[new_status, row[9], row[10], now]]}
                    ).execute()
                    return True
            
            return False
            
        except HttpError as error:
            print(f"Error updating meeting status: {error}")
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
                range='meetings!A:L'
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
                        range=f'meetings!H{i}:L{i}',
                        valueInputOption='RAW',
                        body={'values': [[minutes_url, row[8], row[9], row[10], now]]}
                    ).execute()
                    return True
            
            return False
            
        except HttpError as error:
            print(f"Error updating meeting minutes: {error}")
            return False
    
    def update_config_channels(self, config_spreadsheet_id: str, task_channel_id: str, 
                              meeting_channel_id: str, escalation_channel_id: str) -> bool:
        """
        Updates the channel configuration in the config sheet.
        
        Args:
            config_spreadsheet_id: ID of the config spreadsheet
            task_channel_id: Channel ID for task reminders
            meeting_channel_id: Channel ID for meeting reminders
            escalation_channel_id: Channel ID for escalations
            
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
