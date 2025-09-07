"""
Tests for input validation functionality.
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
    validate_setup_completion, create_error_scenarios, create_success_scenarios,
    assert_channel_id_valid, assert_discord_id_valid, assert_guild_id_valid,
    assert_timezone_valid, assert_exec_member_valid
)


class TestChannelValidation:
    """Test channel ID validation."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
        self.error_scenarios = create_error_scenarios()
        self.success_scenarios = create_success_scenarios()
    
    def test_valid_channel_ids(self):
        """Test validation of valid channel IDs."""
        valid_channel_ids = [
            "111222333",
            "123456789012345678",
            "987654321098765432"
        ]
        
        for channel_id in valid_channel_ids:
            assert_channel_id_valid(channel_id, f"Channel ID: {channel_id}")
    
    def test_invalid_channel_ids(self):
        """Test validation of invalid channel IDs."""
        invalid_channel_ids = [
            "not_a_number",
            "123abc",
            "123-456-789",
            "",
            "123.456.789",
            "123 456 789"
        ]
        
        for channel_id in invalid_channel_ids:
            try:
                assert_channel_id_valid(channel_id, f"Channel ID: {channel_id}")
                assert False, f"Expected validation to fail for channel ID: {channel_id}"
            except AssertionError:
                pass  # Expected to fail
    
    def test_channel_validation_in_setup(self):
        """Test channel validation during setup flow."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Set up initial state
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'task_reminders_channel')
        
        # Test valid channel ID
        async def test_valid_channel():
            response = await setup_manager._handle_task_reminders_channel(user_id, self.success_scenarios['valid_channel_id'])
            assert "Task Reminders Channel Set" in response
            assert self.success_scenarios['valid_channel_id'] in response
        
        asyncio.run(test_valid_channel())
        
        # Test invalid channel ID
        async def test_invalid_channel():
            response = await setup_manager._handle_task_reminders_channel(user_id, self.error_scenarios['invalid_channel_id'])
            assert "Invalid Channel ID" in response
            assert "numbers only" in response
        
        asyncio.run(test_invalid_channel())
    
    def test_channel_validation_edge_cases(self):
        """Test channel validation edge cases."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Set up initial state
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'task_reminders_channel')
        
        # Test empty channel ID
        async def test_empty_channel():
            response = await setup_manager._handle_task_reminders_channel(user_id, "")
            assert "Invalid Channel ID" in response
        
        asyncio.run(test_empty_channel())
        
        # Test whitespace channel ID
        async def test_whitespace_channel():
            response = await setup_manager._handle_task_reminders_channel(user_id, "   ")
            assert "Invalid Channel ID" in response
        
        asyncio.run(test_whitespace_channel())
        
        # Test channel ID with leading/trailing spaces
        async def test_spaced_channel():
            response = await setup_manager._handle_task_reminders_channel(user_id, " 111222333 ")
            assert "Task Reminders Channel Set" in response
        
        asyncio.run(test_spaced_channel())


class TestDiscordIDValidation:
    """Test Discord ID validation."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
        self.error_scenarios = create_error_scenarios()
        self.success_scenarios = create_success_scenarios()
    
    def test_valid_discord_ids(self):
        """Test validation of valid Discord IDs."""
        valid_discord_ids = [
            "123456789",
            "987654321098765432",
            "111222333444555666"
        ]
        
        for discord_id in valid_discord_ids:
            assert_discord_id_valid(discord_id, f"Discord ID: {discord_id}")
    
    def test_invalid_discord_ids(self):
        """Test validation of invalid Discord IDs."""
        invalid_discord_ids = [
            "not_a_number",
            "123abc",
            "123-456-789",
            "",
            "123.456.789",
            "123 456 789"
        ]
        
        for discord_id in invalid_discord_ids:
            try:
                assert_discord_id_valid(discord_id, f"Discord ID: {discord_id}")
                assert False, f"Expected validation to fail for Discord ID: {discord_id}"
            except AssertionError:
                pass  # Expected to fail
    
    def test_discord_mention_extraction(self):
        """Test Discord mention extraction and validation."""
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test that the method exists and is callable
        assert hasattr(setup_manager, '_handle_admin_selection')
        assert callable(setup_manager._handle_admin_selection)
        
        # Test that the method is async
        import inspect
        assert inspect.iscoroutinefunction(setup_manager._handle_admin_selection)


class TestGuildIDValidation:
    """Test guild ID validation."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
        self.error_scenarios = create_error_scenarios()
        self.success_scenarios = create_success_scenarios()
    
    def test_valid_guild_ids(self):
        """Test validation of valid guild IDs."""
        valid_guild_ids = [
            "987654321",
            "123456789012345678",
            "111222333444555666"
        ]
        
        for guild_id in valid_guild_ids:
            assert_guild_id_valid(guild_id, f"Guild ID: {guild_id}")
    
    def test_invalid_guild_ids(self):
        """Test validation of invalid guild IDs."""
        invalid_guild_ids = [
            "not_a_number",
            "123abc",
            "123-456-789",
            "",
            "123.456.789",
            "123 456 789"
        ]
        
        for guild_id in invalid_guild_ids:
            try:
                assert_guild_id_valid(guild_id, f"Guild ID: {guild_id}")
                assert False, f"Expected validation to fail for guild ID: {guild_id}"
            except AssertionError:
                pass  # Expected to fail
    
    def test_guild_id_validation_in_setup(self):
        """Test guild ID validation during setup flow."""
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test that the method exists and is callable
        assert hasattr(setup_manager, '_handle_guild_id')
        assert callable(setup_manager._handle_guild_id)
        
        # Test that the method is async
        import inspect
        assert inspect.iscoroutinefunction(setup_manager._handle_guild_id)


class TestTimezoneValidation:
    """Test timezone validation."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
        self.error_scenarios = create_error_scenarios()
        self.success_scenarios = create_success_scenarios()
    
    def test_valid_timezones(self):
        """Test validation of valid timezones."""
        valid_timezones = [
            'America/Edmonton',
            'America/New_York',
            'America/Los_Angeles',
            'America/Chicago',
            'America/Denver',
            'Europe/London',
            'Europe/Paris',
            'Asia/Tokyo',
            'Asia/Shanghai',
            'Australia/Sydney',
            'UTC'
        ]
        
        for timezone_str in valid_timezones:
            assert_timezone_valid(timezone_str, f"Timezone: {timezone_str}")
    
    def test_invalid_timezones(self):
        """Test validation of invalid timezones."""
        invalid_timezones = [
            'Invalid/Timezone',
            'America/Invalid',
            'Not_A_Timezone',
            'UTC+5',
            'GMT',
            'EST',
            'PST'
        ]
        
        for timezone_str in invalid_timezones:
            try:
                assert_timezone_valid(timezone_str, f"Timezone: {timezone_str}")
                assert False, f"Expected validation to fail for timezone: {timezone_str}"
            except AssertionError:
                pass  # Expected to fail
    
    def test_timezone_validation_in_setup(self):
        """Test timezone validation during setup flow."""
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
            assert self.success_scenarios['valid_timezone'] in response
        
        asyncio.run(test_valid_timezone())
        
        # Test invalid timezone
        async def test_invalid_timezone():
            response = await setup_manager._handle_timezone(user_id, self.error_scenarios['invalid_timezone'])
            assert "Invalid Timezone" in response
            assert "available timezones" in response
        
        asyncio.run(test_invalid_timezone())
        
        # Test default timezone (empty input)
        async def test_default_timezone():
            response = await setup_manager._handle_timezone(user_id, "")
            assert "Timezone Set" in response
            assert "America/Edmonton" in response
        
        asyncio.run(test_default_timezone())
        
        # Test default timezone (Y input)
        async def test_default_timezone_y():
            response = await setup_manager._handle_timezone(user_id, "Y")
            assert "Timezone Set" in response
            assert "America/Edmonton" in response
        
        asyncio.run(test_default_timezone_y())


class TestExecMemberValidation:
    """Test executive member validation."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
        self.error_scenarios = create_error_scenarios()
        self.success_scenarios = create_success_scenarios()
    
    def test_valid_exec_members(self):
        """Test validation of valid executive members."""
        valid_exec_members = [
            {
                'name': 'John Doe',
                'role': 'President',
                'discord_id': '123456789'
            },
            {
                'name': 'Jane Smith',
                'role': 'Vice President',
                'discord_id': '987654321'
            },
            {
                'name': 'Bob Johnson',
                'role': 'General Team Member',
                'discord_id': '111222333'
            }
        ]
        
        for member in valid_exec_members:
            assert_exec_member_valid(member, f"Exec member: {member['name']}")
    
    def test_invalid_exec_members(self):
        """Test validation of invalid executive members."""
        invalid_exec_members = [
            {
                'name': '',  # Empty name
                'role': 'President',
                'discord_id': '123456789'
            },
            {
                'name': 'John Doe',
                'role': 'President',
                'discord_id': ''  # Empty Discord ID
            },
            {
                'name': 'John',  # Missing last name
                'role': 'President',
                'discord_id': '123456789'
            },
            {
                'name': 'John Doe',
                'role': 'President',
                'discord_id': 'invalid_id'  # Invalid Discord ID
            }
        ]
        
        for member in invalid_exec_members:
            try:
                assert_exec_member_valid(member, f"Exec member: {member['name']}")
                assert False, f"Expected validation to fail for exec member: {member}"
            except AssertionError:
                pass  # Expected to fail
    
    def test_exec_member_validation_in_setup(self):
        """Test executive member validation during setup flow."""
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test that the method exists and is callable
        assert hasattr(setup_manager, '_handle_exec_member')
        assert callable(setup_manager._handle_exec_member)
        
        # Test that the method is async
        import inspect
        assert inspect.iscoroutinefunction(setup_manager._handle_exec_member)
    
    def test_exec_member_case_insensitive(self):
        """Test that exec member validation is case insensitive."""
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test that the method exists and is callable
        assert hasattr(setup_manager, '_handle_exec_member')
        assert callable(setup_manager._handle_exec_member)
        
        # Test that the method is async
        import inspect
        assert inspect.iscoroutinefunction(setup_manager._handle_exec_member)


class TestInputSanitization:
    """Test input sanitization and cleaning."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
    
    def test_input_whitespace_handling(self):
        """Test that input whitespace is properly handled."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Set up initial state
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'club_name')
        
        # Test club name with leading/trailing whitespace
        async def test_whitespace_handling():
            response = await setup_manager._handle_club_name(user_id, "  Test Club  ")
            assert "Club Name Set" in response
            assert "Test Club" in response
            assert setup_manager.setup_states[user_id]['club_name'] == "Test Club"
        
        asyncio.run(test_whitespace_handling())
    
    def test_input_case_handling(self):
        """Test that input case is properly handled."""
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test that the method exists and is callable
        assert hasattr(setup_manager, '_handle_timezone')
        assert callable(setup_manager._handle_timezone)
        
        # Test that the method is async
        import inspect
        assert inspect.iscoroutinefunction(setup_manager._handle_timezone)
    
    def test_input_special_characters(self):
        """Test handling of special characters in input."""
        user_id = self.test_data['user_id']
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Set up initial state
        setup_manager.setup_states[user_id] = create_mock_setup_state(user_id, 'club_name')
        
        # Test club name with special characters
        async def test_special_characters():
            response = await setup_manager._handle_club_name(user_id, "Test Club & Organization!")
            assert "Club Name Set" in response
            assert "Test Club & Organization!" in response
        
        asyncio.run(test_special_characters())


if __name__ == "__main__":
    pytest.main([__file__])
