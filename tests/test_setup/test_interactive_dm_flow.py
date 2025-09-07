"""
Tests for the interactive DM flow during setup.
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
    MockBot, MockSetupManager, create_mock_setup_state, create_mock_guild_config
)
from tests.test_utils.test_helpers import (
    setup_test_environment, create_test_data_set, assert_setup_step,
    assert_setup_field, assert_error_message_contains, assert_success_message_contains,
    validate_setup_completion, create_error_scenarios, create_success_scenarios
)


class TestInteractiveDMFlow:
    """Test the interactive DM flow during setup."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
        self.error_scenarios = create_error_scenarios()
        self.success_scenarios = create_success_scenarios()
    
    def test_guild_id_validation(self):
        """Test guild ID validation in setup flow."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test valid guild ID
        async def test_valid_guild_id():
            response = await setup_manager._handle_guild_id(user_id, self.success_scenarios['valid_guild_id'])
            assert "Server ID Set" in response
            assert "Step 2: Club Information" in response
            assert self.success_scenarios['valid_guild_id'] in response
        
        asyncio.run(test_valid_guild_id())
        
        # Test invalid guild ID
        async def test_invalid_guild_id():
            response = await setup_manager._handle_guild_id(user_id, self.error_scenarios['invalid_guild_id'])
            assert "Invalid Server ID" in response
            assert "numbers only" in response
        
        asyncio.run(test_invalid_guild_id())
    
    def test_club_name_validation(self):
        """Test club name validation in setup flow."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Set up initial state
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'club_name')
        
        # Test valid club name
        async def test_valid_club_name():
            response = await setup_manager._handle_club_name(user_id, self.success_scenarios['valid_club_name'])
            assert "Club Name Set" in response
            assert "Step 3: Admin Selection" in response
            assert self.success_scenarios['valid_club_name'] in response
        
        asyncio.run(test_valid_club_name())
        
        # Test empty club name
        async def test_empty_club_name():
            response = await setup_manager._handle_club_name(user_id, self.error_scenarios['empty_club_name'])
            # Should still work as it strips whitespace
            assert "Club Name Set" in response
        
        asyncio.run(test_empty_club_name())
    
    def test_admin_selection_validation(self):
        """Test admin selection validation in setup flow."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Set up initial state
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'admin_selection')
        
        # Test valid admin mention
        async def test_valid_admin_mention():
            response = await setup_manager._handle_admin_selection(user_id, self.success_scenarios['valid_admin_mention'])
            assert "Admin Set" in response
            assert "Step 4: Timezone Configuration" in response
            assert self.success_scenarios['valid_admin_mention'] in response
        
        asyncio.run(test_valid_admin_mention())
        
        # Test invalid admin mention
        async def test_invalid_admin_mention():
            response = await setup_manager._handle_admin_selection(user_id, "invalid_mention")
            assert "Invalid Admin Mention" in response
            assert "@mention" in response
        
        asyncio.run(test_invalid_admin_mention())
    
    def test_timezone_validation(self):
        """Test timezone validation in setup flow."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Set up initial state
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'timezone')
        
        # Test valid timezone
        async def test_valid_timezone():
            response = await setup_manager._handle_timezone(user_id, self.success_scenarios['valid_timezone'])
            assert "Timezone Set" in response
            assert "Step 5: Executive Team" in response
            assert self.success_scenarios['valid_timezone'] in response
        
        asyncio.run(test_valid_timezone())
        
        # Test default timezone (empty input)
        async def test_default_timezone():
            response = await setup_manager._handle_timezone(user_id, "")
            assert "Timezone Set" in response
            assert "America/Edmonton" in response
        
        asyncio.run(test_default_timezone())
        
        # Test invalid timezone
        async def test_invalid_timezone():
            response = await setup_manager._handle_timezone(user_id, self.error_scenarios['invalid_timezone'])
            assert "Invalid Timezone" in response
            assert "available timezones" in response
        
        asyncio.run(test_invalid_timezone())
    
    def test_exec_count_validation(self):
        """Test executive count validation in setup flow."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Set up initial state
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'exec_count')
        
        # Test valid exec count
        async def test_valid_exec_count():
            response = await setup_manager._handle_exec_count(user_id, "3")
            assert "Executive Team Count Set" in response
            assert "Step 6: Executive Team Members" in response
            assert "3" in response
        
        asyncio.run(test_valid_exec_count())
        
        # Test zero exec count
        async def test_zero_exec_count():
            response = await setup_manager._handle_exec_count(user_id, "0")
            assert "Executive Team Count Set" in response
            assert "Step 6: Google Drive Folders" in response
        
        asyncio.run(test_zero_exec_count())
        
        # Test invalid exec count
        async def test_invalid_exec_count():
            response = await setup_manager._handle_exec_count(user_id, "not_a_number")
            assert "Invalid Count" in response
            assert "valid number" in response
        
        asyncio.run(test_invalid_exec_count())
        
        # Test negative exec count
        async def test_negative_exec_count():
            response = await setup_manager._handle_exec_count(user_id, "-1")
            assert "Invalid Count" in response
            assert "0 or more" in response
        
        asyncio.run(test_negative_exec_count())
    
    def test_exec_member_validation(self):
        """Test executive member validation in setup flow."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Set up initial state
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'exec_member')
        setup_manager.setup_states[user_id]['exec_count'] = 2
        setup_manager.setup_states[user_id]['current_exec_index'] = 0
        
        # Test valid exec member format
        async def test_valid_exec_member():
            response = await setup_manager._handle_exec_member(user_id, "John Doe, President, @johnsmith")
            assert "Member 1 Added" in response
            assert "John Doe" in response
            assert "President" in response
        
        asyncio.run(test_valid_exec_member())
        
        # Test exec member without role
        async def test_exec_member_no_role():
            response = await setup_manager._handle_exec_member(user_id, "Jane Smith, @janesmith")
            assert "Member 1 Added" in response
            assert "Jane Smith" in response
            assert "General Team Member" in response
        
        asyncio.run(test_exec_member_no_role())
        
        # Test invalid exec member format
        async def test_invalid_exec_member():
            response = await setup_manager._handle_exec_member(user_id, "John Doe")
            assert "Invalid Format" in response
            assert "FirstName LastName, Role, @DiscordUser" in response
        
        asyncio.run(test_invalid_exec_member())
        
        # Test invalid Discord mention
        async def test_invalid_discord_mention():
            response = await setup_manager._handle_exec_member(user_id, "John Doe, President, invalid_mention")
            assert "Invalid Discord ID" in response
            assert "@mention" in response
        
        asyncio.run(test_invalid_discord_mention())
        
        # Test invalid name format
        async def test_invalid_name_format():
            response = await setup_manager._handle_exec_member(user_id, "John, President, @johnsmith")
            assert "Invalid Name" in response
            assert "first and last name" in response
        
        asyncio.run(test_invalid_name_format())
    
    def test_cancel_command_handling(self):
        """Test /cancel command handling during setup."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Set up initial state
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'club_name')
        
        # Test cancel command
        async def test_cancel_command():
            response = await setup_manager.handle_setup_response(user_id, "/cancel")
            assert "Setup cancelled" in response
            assert user_id not in setup_manager.setup_states
        
        asyncio.run(test_cancel_command())
    
    def test_setup_flow_completion(self):
        """Test complete setup flow from start to finish."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Mock Google Sheets operations
        with patch.object(setup_manager.sheets_manager, 'create_master_config_sheet') as mock_create_config, \
             patch.object(setup_manager.sheets_manager, 'create_monthly_sheets') as mock_create_monthly, \
             patch.object(setup_manager.sheets_manager, 'update_config_channels') as mock_update_channels, \
             patch.object(setup_manager.sheets_manager, 'log_action') as mock_log_action, \
             patch.object(setup_manager.status_manager, 'mark_setup_complete') as mock_mark_complete:
            
            # Set up mock returns
            mock_create_config.return_value = "test_config_sheet_id"
            mock_create_monthly.return_value = {
                "tasks": "test_tasks_sheet_id",
                "meetings": "test_meetings_sheet_id"
            }
            mock_update_channels.return_value = None
            mock_log_action.return_value = None
            mock_mark_complete.return_value = None
            
            # Test complete setup flow
            async def test_complete_setup():
                # Start setup
                response = await setup_manager.start_setup(user_id, "testuser", self.test_data['guild_id'], "Test Guild")
                assert "Welcome" in response
                
                # Set up state for testing
                setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'free_speak_channel')
                setup_manager.setup_states[user_id]['config_spreadsheet_id'] = "test_config_sheet_id"
                setup_manager.setup_states[user_id]['task_reminders_channel_id'] = "111222333"
                setup_manager.setup_states[user_id]['meeting_reminders_channel_id'] = "444555666"
                setup_manager.setup_states[user_id]['escalation_channel_id'] = "777888999"
                setup_manager.setup_states[user_id]['general_announcements_channel_id'] = "000111222"
                
                # Complete setup
                response = await setup_manager._handle_free_speak_channel(user_id, "skip")
                assert "Setup Complete" in response
                assert "Test Club" in response
                
                # Verify mocks were called
                mock_create_config.assert_called_once()
                mock_create_monthly.assert_called_once()
                mock_update_channels.assert_called_once()
                mock_log_action.assert_called_once()
                mock_mark_complete.assert_called_once()
            
            asyncio.run(test_complete_setup())
    
    def test_setup_error_handling(self):
        """Test setup error handling."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test error handling when no setup session exists
        async def test_no_setup_session():
            response = await setup_manager.handle_setup_response(user_id, "test message")
            assert "Setup session not found" in response
        
        asyncio.run(test_no_setup_session())
        
        # Test error handling with invalid step
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'invalid_step')
        
        async def test_invalid_step():
            response = await setup_manager.handle_setup_response(user_id, "test message")
            assert "Unknown setup step" in response
        
        asyncio.run(test_invalid_step())
    
    def test_setup_state_persistence(self):
        """Test that setup state is properly maintained during flow."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test state persistence through multiple steps
        async def test_state_persistence():
            # Start setup
            await setup_manager.start_setup(user_id, "testuser", self.test_data['guild_id'], "Test Guild")
            assert user_id in setup_manager.setup_states
            assert setup_manager.setup_states[user_id]['step'] == 'club_name'
            
            # Set club name
            await setup_manager._handle_club_name(user_id, "Test Club")
            assert setup_manager.setup_states[user_id]['club_name'] == "Test Club"
            assert setup_manager.setup_states[user_id]['step'] == 'admin_selection'
            
            # Set admin
            await setup_manager._handle_admin_selection(user_id, "<@123456789>")
            assert setup_manager.setup_states[user_id]['admin_discord_id'] == "123456789"
            assert setup_manager.setup_states[user_id]['step'] == 'timezone'
            
            # Set timezone
            await setup_manager._handle_timezone(user_id, "America/Edmonton")
            assert setup_manager.setup_states[user_id]['timezone'] == "America/Edmonton"
            assert setup_manager.setup_states[user_id]['step'] == 'exec_count'
        
        asyncio.run(test_state_persistence())


if __name__ == "__main__":
    pytest.main([__file__])
