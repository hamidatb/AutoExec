"""
Test helper functions and utilities.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch


def setup_test_environment():
    """Set up the test environment by adding the project root to Python path."""
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def create_test_guild_id() -> str:
    """Create a test guild ID."""
    return "987654321"


def create_test_user_id() -> str:
    """Create a test user ID."""
    return "123456789"


def create_test_channel_id() -> str:
    """Create a test channel ID."""
    return "111222333"


def create_test_spreadsheet_id() -> str:
    """Create a test spreadsheet ID."""
    return "test_spreadsheet_123456789"


def create_test_folder_id() -> str:
    """Create a test folder ID."""
    return "test_folder_123456789"


def assert_setup_step(expected_step: str, actual_state: Dict[str, Any], test_name: str = ""):
    """Assert that the setup state has the expected step."""
    assert actual_state.get('step') == expected_step, \
        f"{test_name}: Expected step '{expected_step}', got '{actual_state.get('step')}'"


def assert_setup_field(expected_value: Any, actual_state: Dict[str, Any], field_name: str, test_name: str = ""):
    """Assert that a setup state field has the expected value."""
    assert actual_state.get(field_name) == expected_value, \
        f"{test_name}: Expected {field_name} '{expected_value}', got '{actual_state.get(field_name)}'"


def assert_error_message_contains(expected_text: str, actual_message: str, test_name: str = ""):
    """Assert that an error message contains expected text."""
    assert expected_text.lower() in actual_message.lower(), \
        f"{test_name}: Expected error message to contain '{expected_text}', got '{actual_message}'"


def assert_success_message_contains(expected_text: str, actual_message: str, test_name: str = ""):
    """Assert that a success message contains expected text."""
    assert expected_text.lower() in actual_message.lower(), \
        f"{test_name}: Expected success message to contain '{expected_text}', got '{actual_message}'"


def assert_channel_id_valid(channel_id: str, test_name: str = ""):
    """Assert that a channel ID is valid (numeric)."""
    assert channel_id.isdigit(), \
        f"{test_name}: Expected numeric channel ID, got '{channel_id}'"


def assert_discord_id_valid(discord_id: str, test_name: str = ""):
    """Assert that a Discord ID is valid (numeric)."""
    assert discord_id.isdigit(), \
        f"{test_name}: Expected numeric Discord ID, got '{discord_id}'"


def assert_guild_id_valid(guild_id: str, test_name: str = ""):
    """Assert that a guild ID is valid (numeric)."""
    assert guild_id.isdigit(), \
        f"{test_name}: Expected numeric guild ID, got '{guild_id}'"


def assert_timezone_valid(timezone_str: str, test_name: str = ""):
    """Assert that a timezone string is valid."""
    valid_timezones = [
        'America/Edmonton', 'America/New_York', 'America/Los_Angeles', 
        'America/Chicago', 'America/Denver', 'Europe/London', 'Europe/Paris',
        'Asia/Tokyo', 'Asia/Shanghai', 'Australia/Sydney', 'UTC'
    ]
    assert timezone_str in valid_timezones, \
        f"{test_name}: Expected valid timezone, got '{timezone_str}'"


def assert_exec_member_valid(member: Dict[str, Any], test_name: str = ""):
    """Assert that an exec member has valid data."""
    assert 'name' in member, f"{test_name}: Exec member missing 'name' field"
    assert 'role' in member, f"{test_name}: Exec member missing 'role' field"
    assert 'discord_id' in member, f"{test_name}: Exec member missing 'discord_id' field"
    assert member['name'], f"{test_name}: Exec member name cannot be empty"
    assert member['discord_id'], f"{test_name}: Exec member discord_id cannot be empty"
    assert_discord_id_valid(member['discord_id'], test_name)


def assert_timer_data_valid(timer: Dict[str, Any], test_name: str = ""):
    """Assert that timer data is valid."""
    required_fields = ['id', 'type', 'fire_at_utc', 'channel_id']
    for field in required_fields:
        assert field in timer, f"{test_name}: Timer missing required field '{field}'"
        assert timer[field], f"{test_name}: Timer field '{field}' cannot be empty"


def assert_task_data_valid(task: Dict[str, Any], test_name: str = ""):
    """Assert that task data is valid."""
    required_fields = ['id', 'title', 'assigned_to', 'deadline', 'status']
    for field in required_fields:
        assert field in task, f"{test_name}: Task missing required field '{field}'"
        assert task[field], f"{test_name}: Task field '{field}' cannot be empty"


def assert_meeting_data_valid(meeting: Dict[str, Any], test_name: str = ""):
    """Assert that meeting data is valid."""
    required_fields = ['id', 'title', 'start_time']
    for field in required_fields:
        assert field in meeting, f"{test_name}: Meeting missing required field '{field}'"
        assert meeting[field], f"{test_name}: Meeting field '{field}' cannot be empty"


def mock_google_drive_access():
    """Create a mock for Google Drive access."""
    return patch('googledrive.sheets_manager.ClubSheetsManager')


def mock_discord_interaction():
    """Create a mock for Discord interaction."""
    return patch('discord.Interaction')


def mock_asyncio_sleep():
    """Create a mock for asyncio.sleep."""
    return patch('asyncio.sleep')


def run_async_test(coro):
    """Run an async test function."""
    return asyncio.run(coro)


def create_test_data_set():
    """Create a comprehensive test data set."""
    return {
        'guild_id': create_test_guild_id(),
        'user_id': create_test_user_id(),
        'channel_id': create_test_channel_id(),
        'spreadsheet_id': create_test_spreadsheet_id(),
        'folder_id': create_test_folder_id(),
        'club_name': 'Test Club',
        'timezone': 'America/Edmonton',
        'admin_mention': '<@123456789>',
        'exec_count': 2,
        'exec_members': [
            {
                'name': 'John Doe',
                'role': 'President',
                'discord_id': '123456789'
            },
            {
                'name': 'Jane Smith',
                'role': 'Vice President',
                'discord_id': '987654321'
            }
        ],
        'folder_links': [
            'https://drive.google.com/drive/folders/test_config_folder_id',
            'https://drive.google.com/drive/folders/test_monthly_folder_id',
            'https://drive.google.com/drive/folders/test_meeting_minutes_folder_id'
        ]
    }


def validate_setup_completion(config: Dict[str, Any], test_name: str = ""):
    """Validate that a setup configuration is complete."""
    required_fields = [
        'club_name', 'admin_user_id', 'timezone', 'config_spreadsheet_id',
        'task_reminders_channel_id', 'meeting_reminders_channel_id',
        'escalation_channel_id', 'general_announcements_channel_id'
    ]
    
    for field in required_fields:
        assert field in config, f"{test_name}: Setup missing required field '{field}'"
        assert config[field], f"{test_name}: Setup field '{field}' cannot be empty"
    
    # Validate specific field types
    assert_channel_id_valid(config['task_reminders_channel_id'], f"{test_name} - task_reminders_channel_id")
    assert_channel_id_valid(config['meeting_reminders_channel_id'], f"{test_name} - meeting_reminders_channel_id")
    assert_channel_id_valid(config['escalation_channel_id'], f"{test_name} - escalation_channel_id")
    assert_channel_id_valid(config['general_announcements_channel_id'], f"{test_name} - general_announcements_channel_id")
    assert_discord_id_valid(config['admin_user_id'], f"{test_name} - admin_user_id")
    assert_timezone_valid(config['timezone'], f"{test_name} - timezone")


def create_error_scenarios():
    """Create common error scenarios for testing."""
    return {
        'invalid_guild_id': 'not_a_number',
        'invalid_channel_id': 'not_a_number',
        'invalid_discord_id': 'not_a_number',
        'invalid_timezone': 'Invalid/Timezone',
        'empty_club_name': '',
        'invalid_exec_format': 'John Doe, @invalid_mention',
        'invalid_folder_link': 'https://invalid-link.com',
        'missing_required_field': None
    }


def create_success_scenarios():
    """Create common success scenarios for testing."""
    return {
        'valid_guild_id': '987654321',
        'valid_channel_id': '111222333',
        'valid_discord_id': '123456789',
        'valid_timezone': 'America/Edmonton',
        'valid_club_name': 'Test Club',
        'valid_exec_format': 'John Doe, President, @johnsmith',
        'valid_folder_link': 'https://drive.google.com/drive/folders/test_folder_id',
        'valid_admin_mention': '<@123456789>'
    }
