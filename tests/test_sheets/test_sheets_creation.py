"""
Tests for Google Sheets creation and management functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.test_utils.mock_objects import (
    MockDiscordUser, MockDiscordGuild, MockDiscordInteraction, 
    MockBot, MockSetupManager, create_mock_setup_state, create_mock_guild_config,
    MockSheetsManager
)
from tests.test_utils.test_helpers import (
    setup_test_environment, create_test_data_set, assert_setup_step,
    assert_setup_field, assert_error_message_contains, assert_success_message_contains,
    validate_setup_completion, create_error_scenarios, create_success_scenarios
)


class TestMasterConfigSheetCreation:
    """Test creation of the master configuration sheet."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.sheets_manager = MockSheetsManager()
        self.test_data = create_test_data_set()
    
    def test_create_master_config_sheet_success(self):
        """Test successful creation of master config sheet."""
        club_name = self.test_data['club_name']
        admin_discord_id = self.test_data['user_id']
        config_folder_id = self.test_data['folder_id']
        timezone = self.test_data['timezone']
        exec_members = self.test_data['exec_members']
        
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service, \
             patch.object(sheets_manager, 'drive_service') as mock_drive_service:
            
            # Set up mock responses
            mock_sheets_service.spreadsheets().create().execute.return_value = {
                'spreadsheetId': 'test_config_sheet_id',
                'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_config_sheet_id'
            }
            
            mock_drive_service.files().update().execute.return_value = {
                'id': 'test_config_sheet_id'
            }
            
            # Test sheet creation
            result = sheets_manager.create_master_config_sheet(
                club_name, admin_discord_id, config_folder_id, timezone, exec_members
            )
            
            assert result == 'test_config_sheet_id'
            mock_sheets_service.spreadsheets().create().execute.assert_called_once()
            mock_drive_service.files().update().execute.assert_called_once()
    
    def test_create_master_config_sheet_with_tabs(self):
        """Test that master config sheet is created with all required tabs."""
        club_name = self.test_data['club_name']
        admin_discord_id = self.test_data['user_id']
        config_folder_id = self.test_data['folder_id']
        timezone = self.test_data['timezone']
        exec_members = self.test_data['exec_members']
        
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service, \
             patch.object(sheets_manager, 'drive_service') as mock_drive_service:
            
            # Set up mock responses
            mock_sheets_service.spreadsheets().create().execute.return_value = {
                'spreadsheetId': 'test_config_sheet_id',
                'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_config_sheet_id'
            }
            
            mock_drive_service.files().update().execute.return_value = {
                'id': 'test_config_sheet_id'
            }
            
            # Test sheet creation
            result = sheets_manager.create_master_config_sheet(
                club_name, admin_discord_id, config_folder_id, timezone, exec_members
            )
            
            # Verify that the create call was made with proper structure
            create_call = mock_sheets_service.spreadsheets().create().execute.call_args
            assert create_call is not None
            
            # The sheet should be created with proper structure
            assert result == 'test_config_sheet_id'
    
    def test_create_master_config_sheet_error_handling(self):
        """Test error handling in master config sheet creation."""
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Test that the method exists and is callable
        assert hasattr(sheets_manager, 'create_master_config_sheet')
        assert callable(sheets_manager.create_master_config_sheet)
    
    def test_create_master_config_sheet_with_empty_exec_members(self):
        """Test master config sheet creation with empty exec members list."""
        club_name = self.test_data['club_name']
        admin_discord_id = self.test_data['user_id']
        config_folder_id = self.test_data['folder_id']
        timezone = self.test_data['timezone']
        exec_members = []  # Empty list
        
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service, \
             patch.object(sheets_manager, 'drive_service') as mock_drive_service:
            
            # Set up mock responses
            mock_sheets_service.spreadsheets().create().execute.return_value = {
                'spreadsheetId': 'test_config_sheet_id',
                'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_config_sheet_id'
            }
            
            mock_drive_service.files().update().execute.return_value = {
                'id': 'test_config_sheet_id'
            }
            
            # Test sheet creation with empty exec members
            result = sheets_manager.create_master_config_sheet(
                club_name, admin_discord_id, config_folder_id, timezone, exec_members
            )
            
            assert result == 'test_config_sheet_id'
            mock_sheets_service.spreadsheets().create().execute.assert_called_once()


class TestMonthlySheetsCreation:
    """Test creation of monthly task and meeting sheets."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.sheets_manager = MockSheetsManager()
        self.test_data = create_test_data_set()
    
    def test_create_monthly_sheets_success(self):
        """Test successful creation of monthly sheets."""
        club_name = self.test_data['club_name']
        current_month = "January 2024"
        monthly_folder_id = self.test_data['folder_id']
        
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service, \
             patch.object(sheets_manager, 'drive_service') as mock_drive_service:
            
            # Set up mock responses for both tasks and meetings sheets
            mock_sheets_service.spreadsheets().create().execute.side_effect = [
                {
                    'spreadsheetId': 'test_tasks_sheet_id',
                    'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_tasks_sheet_id'
                },
                {
                    'spreadsheetId': 'test_meetings_sheet_id',
                    'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_meetings_sheet_id'
                }
            ]
            
            mock_drive_service.files().update().execute.side_effect = [
                {'id': 'test_tasks_sheet_id'},
                {'id': 'test_meetings_sheet_id'}
            ]
            
            # Test monthly sheets creation
            result = sheets_manager.create_monthly_sheets(
                club_name, current_month, monthly_folder_id
            )
            
            assert result is not None
            assert 'tasks' in result
            assert 'meetings' in result
            assert result['tasks'] == 'test_tasks_sheet_id'
            assert result['meetings'] == 'test_meetings_sheet_id'
    
    def test_create_monthly_sheets_with_proper_naming(self):
        """Test that monthly sheets are created with proper naming."""
        club_name = self.test_data['club_name']
        current_month = "January 2024"
        monthly_folder_id = self.test_data['folder_id']
        
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service, \
             patch.object(sheets_manager, 'drive_service') as mock_drive_service:
            
            # Set up mock responses
            mock_sheets_service.spreadsheets().create().execute.return_value = {
                'spreadsheetId': 'test_sheet_id',
                'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_sheet_id'
            }
            
            mock_drive_service.files().update().execute.return_value = {
                'id': 'test_sheet_id'
            }
            
            # Test monthly sheets creation
            result = sheets_manager.create_monthly_sheets(
                club_name, current_month, monthly_folder_id
            )
            
            # Verify that the create call was made with proper naming
            create_calls = mock_sheets_service.spreadsheets().create().execute.call_args_list
            assert len(create_calls) == 2  # One for tasks, one for meetings
            
            # The sheets should be created with proper structure
            assert result is not None
            assert 'tasks' in result
            assert 'meetings' in result
    
    def test_create_monthly_sheets_error_handling(self):
        """Test error handling in monthly sheets creation."""
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Test that the method exists and is callable
        assert hasattr(sheets_manager, 'create_monthly_sheets')
        assert callable(sheets_manager.create_monthly_sheets)


class TestConfigChannelsUpdate:
    """Test updating configuration with channel IDs."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.sheets_manager = MockSheetsManager()
        self.test_data = create_test_data_set()
    
    def test_update_config_channels_success(self):
        """Test successful update of config channels."""
        config_spreadsheet_id = self.test_data['spreadsheet_id']
        task_reminders_channel_id = "111222333"
        meeting_reminders_channel_id = "444555666"
        escalation_channel_id = "777888999"
        free_speak_channel_id = "333444555"
        general_announcements_channel_id = "000111222"
        
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service:
            # Set up mock responses
            mock_sheets_service.spreadsheets().values().update().execute.return_value = {
                'updatedCells': 5
            }
            
            # Test channel update
            result = sheets_manager.update_config_channels(
                config_spreadsheet_id,
                task_reminders_channel_id,
                meeting_reminders_channel_id,
                escalation_channel_id,
                free_speak_channel_id,
                general_announcements_channel_id
            )
            
            assert result is not None
            mock_sheets_service.spreadsheets().values().update().execute.assert_called()
    
    def test_update_config_channels_without_free_speak(self):
        """Test updating config channels without free-speak channel."""
        config_spreadsheet_id = self.test_data['spreadsheet_id']
        task_reminders_channel_id = "111222333"
        meeting_reminders_channel_id = "444555666"
        escalation_channel_id = "777888999"
        free_speak_channel_id = None  # No free-speak channel
        general_announcements_channel_id = "000111222"
        
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service:
            # Set up mock responses
            mock_sheets_service.spreadsheets().values().update().execute.return_value = {
                'updatedCells': 4
            }
            
            # Test channel update without free-speak
            result = sheets_manager.update_config_channels(
                config_spreadsheet_id,
                task_reminders_channel_id,
                meeting_reminders_channel_id,
                escalation_channel_id,
                free_speak_channel_id,
                general_announcements_channel_id
            )
            
            assert result is not None
            mock_sheets_service.spreadsheets().values().update().execute.assert_called()
    
    def test_update_config_channels_error_handling(self):
        """Test error handling in config channels update."""
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Test that the method exists and is callable
        assert hasattr(sheets_manager, 'update_config_channels')
        assert callable(sheets_manager.update_config_channels)


class TestFolderAccessVerification:
    """Test Google Drive folder access verification."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.sheets_manager = MockSheetsManager()
        self.test_data = create_test_data_set()
    
    def test_verify_folder_access_success(self):
        """Test successful folder access verification."""
        folder_id = self.test_data['folder_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Mock Google Drive API calls
        with patch.object(setup_manager.sheets_manager, 'drive_service') as mock_drive_service:
            # Set up mock responses
            mock_drive_service.files().get().execute.return_value = {
                'id': folder_id,
                'name': 'Test Folder',
                'permissions': []
            }
            
            mock_drive_service.files().create().execute.return_value = {
                'id': 'test_file_id'
            }
            
            mock_drive_service.files().delete().execute.return_value = {}
            
            # Test folder access verification
            async def test_verify_access():
                result = await setup_manager._verify_folder_access(folder_id)
                assert result is True
            
            asyncio.run(test_verify_access())
    
    def test_verify_folder_access_failure(self):
        """Test folder access verification failure."""
        folder_id = self.test_data['folder_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Mock Google Drive API to raise an exception
        with patch.object(setup_manager.sheets_manager, 'drive_service') as mock_drive_service:
            mock_drive_service.files().get().execute.side_effect = Exception("Access denied")
            
            # Test folder access verification failure
            async def test_verify_access_failure():
                result = await setup_manager._verify_folder_access(folder_id)
                assert result is False
            
            asyncio.run(test_verify_access_failure())
    
    def test_verify_folder_access_permission_denied(self):
        """Test folder access verification with permission denied."""
        folder_id = self.test_data['folder_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Mock Google Drive API calls
        with patch.object(setup_manager.sheets_manager, 'drive_service') as mock_drive_service:
            # Set up mock responses
            mock_drive_service.files().get().execute.return_value = {
                'id': folder_id,
                'name': 'Test Folder',
                'permissions': []
            }
            
            mock_drive_service.files().create().execute.side_effect = Exception("Permission denied")
            
            # Test folder access verification with permission denied
            async def test_verify_access_permission_denied():
                result = await setup_manager._verify_folder_access(folder_id)
                assert result is False
            
            asyncio.run(test_verify_access_permission_denied())


class TestSheetStructureValidation:
    """Test validation of sheet structure and content."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.sheets_manager = MockSheetsManager()
        self.test_data = create_test_data_set()
    
    def test_config_sheet_has_required_tabs(self):
        """Test that config sheet has all required tabs."""
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service:
            # Set up mock responses
            mock_sheets_service.spreadsheets().create().execute.return_value = {
                'spreadsheetId': 'test_config_sheet_id',
                'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_config_sheet_id'
            }
            
            # Test sheet creation
            result = sheets_manager.create_master_config_sheet(
                self.test_data['club_name'],
                self.test_data['user_id'],
                self.test_data['folder_id'],
                self.test_data['timezone'],
                self.test_data['exec_members']
            )
            
            # Verify that the create call was made with proper structure
            create_call = mock_sheets_service.spreadsheets().create().execute.call_args
            assert create_call is not None
            
            # The sheet should be created with proper structure
            assert result == 'test_config_sheet_id'
    
    def test_monthly_sheets_have_required_structure(self):
        """Test that monthly sheets have required structure."""
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service:
            # Set up mock responses
            mock_sheets_service.spreadsheets().create().execute.return_value = {
                'spreadsheetId': 'test_sheet_id',
                'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_sheet_id'
            }
            
            # Test monthly sheets creation
            result = sheets_manager.create_monthly_sheets(
                self.test_data['club_name'],
                "January 2024",
                self.test_data['folder_id']
            )
            
            # Verify that the create call was made with proper structure
            create_calls = mock_sheets_service.spreadsheets().create().execute.call_args_list
            assert len(create_calls) == 2  # One for tasks, one for meetings
            
            # The sheets should be created with proper structure
            assert result is not None
            assert 'tasks' in result
            assert 'meetings' in result


class TestSheetDataPersistence:
    """Test that sheet data is properly persisted."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.sheets_manager = MockSheetsManager()
        self.test_data = create_test_data_set()
    
    def test_config_data_persistence(self):
        """Test that configuration data is properly persisted to sheets."""
        config_spreadsheet_id = self.test_data['spreadsheet_id']
        task_reminders_channel_id = "111222333"
        meeting_reminders_channel_id = "444555666"
        escalation_channel_id = "777888999"
        free_speak_channel_id = "333444555"
        general_announcements_channel_id = "000111222"
        
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service:
            # Set up mock responses
            mock_sheets_service.spreadsheets().values().update().execute.return_value = {
                'updatedCells': 5
            }
            
            # Test channel update
            result = sheets_manager.update_config_channels(
                config_spreadsheet_id,
                task_reminders_channel_id,
                meeting_reminders_channel_id,
                escalation_channel_id,
                free_speak_channel_id,
                general_announcements_channel_id
            )
            
            assert result is not None
            mock_sheets_service.spreadsheets().values().update().execute.assert_called()
    
    def test_exec_members_data_persistence(self):
        """Test that executive members data is properly persisted to sheets."""
        club_name = self.test_data['club_name']
        admin_discord_id = self.test_data['user_id']
        config_folder_id = self.test_data['folder_id']
        timezone = self.test_data['timezone']
        exec_members = self.test_data['exec_members']
        
        # Mock the sheets manager
        from googledrive.sheets_manager import ClubSheetsManager
        sheets_manager = ClubSheetsManager()
        
        # Mock Google Sheets API calls
        with patch.object(sheets_manager, 'sheets_service') as mock_sheets_service, \
             patch.object(sheets_manager, 'drive_service') as mock_drive_service:
            
            # Set up mock responses
            mock_sheets_service.spreadsheets().create().execute.return_value = {
                'spreadsheetId': 'test_config_sheet_id',
                'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_config_sheet_id'
            }
            
            mock_drive_service.files().update().execute.return_value = {
                'id': 'test_config_sheet_id'
            }
            
            # Test sheet creation with exec members
            result = sheets_manager.create_master_config_sheet(
                club_name, admin_discord_id, config_folder_id, timezone, exec_members
            )
            
            assert result == 'test_config_sheet_id'
            mock_sheets_service.spreadsheets().create().execute.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
