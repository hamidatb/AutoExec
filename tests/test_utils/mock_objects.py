"""
Mock objects and test fixtures for the Club Exec Task Manager Bot tests.
"""

import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, Optional
import discord
from datetime import datetime, timezone


class MockDiscordUser:
    """Mock Discord user object."""
    
    def __init__(self, user_id: str = "123456789", username: str = "testuser"):
        self.id = int(user_id)
        self.name = username
        self.display_name = username
        self.mention = f"<@{user_id}>"


class MockDiscordGuild:
    """Mock Discord guild object."""
    
    def __init__(self, guild_id: str = "987654321", name: str = "Test Guild"):
        self.id = int(guild_id)
        self.name = name


class MockDiscordChannel:
    """Mock Discord channel object."""
    
    def __init__(self, channel_id: str = "111222333", name: str = "test-channel"):
        self.id = int(channel_id)
        self.name = name


class MockDiscordDMChannel:
    """Mock Discord DM channel object."""
    
    def __init__(self, recipient: MockDiscordUser):
        self.recipient = recipient
        self.type = discord.ChannelType.private


class MockDiscordInteraction:
    """Mock Discord interaction object."""
    
    def __init__(self, user: MockDiscordUser, guild: Optional[MockDiscordGuild] = None, 
                 channel: Optional[MockDiscordChannel] = None, is_dm: bool = False):
        self.user = user
        self.guild = guild
        self.channel = channel if not is_dm else MockDiscordDMChannel(user)
        self.response = AsyncMock()
        self.followup = AsyncMock()
        self.is_dm = is_dm


class MockBot:
    """Mock bot instance for testing."""
    
    def __init__(self):
        self.club_configs = {}
        self.setup_manager = Mock()
        self.sheets_manager = Mock()
        self.meeting_manager = Mock()
        self.task_manager = Mock()
        self.timer_scheduler = Mock()
        self.tree = Mock()
        
        # Mock methods
        self.send_any_message = AsyncMock()
        self.verify_dm_admin_access = AsyncMock(return_value=True)


class MockSetupManager:
    """Mock setup manager for testing."""
    
    def __init__(self):
        self.setup_states = {}
        self.status_manager = MockGuildSetupStatusManager()
        
        # Mock methods
        self.start_setup = AsyncMock()
        self.handle_setup_response = AsyncMock()
        self.cancel_setup = Mock()
        self.is_in_setup = Mock(return_value=False)
        self.is_setup_complete = Mock(return_value=False)
        self.is_fully_setup = Mock(return_value=False)  # Added missing method
        self.get_guild_config = Mock(return_value=None)
        self.can_modify_config = Mock(return_value=True)
        self.mark_setup_complete = Mock()
        self.reset_club_configuration = Mock()
        self.get_configuration_summary = Mock()
        self.update_configuration_setting = Mock()


class MockGuildSetupStatusManager:
    """Mock guild setup status manager for testing."""
    
    def __init__(self):
        self.guilds = {}
        
        # Mock methods
        self.is_setup_complete = Mock(return_value=False)
        self.get_guild_config = Mock(return_value=None)
        self.can_modify_config = Mock(return_value=True)
        self.mark_setup_complete = Mock()
        self.update_guild_config = Mock(return_value=True)
        self.get_all_guilds = Mock(return_value={})
        self.remove_guild = Mock(return_value=True)
        self.get_setup_stats = Mock(return_value={
            "total_guilds": 0,
            "completed_setups": 0,
            "incomplete_setups": 0,
            "last_updated": datetime.now().isoformat()
        })


class MockSheetsManager:
    """Mock Google Sheets manager for testing."""
    
    def __init__(self):
        self.drive_service = Mock()
        self.sheets_service = Mock()
        
        # Mock methods
        self.create_master_config_sheet = Mock(return_value="test_config_sheet_id")
        self.create_monthly_sheets = Mock(return_value={
            "tasks": "test_tasks_sheet_id",
            "meetings": "test_meetings_sheet_id"
        })
        self.update_config_channels = Mock()
        self.log_action = AsyncMock()
        self.get_timers = Mock(return_value=[])
        self.update_timer_state = Mock(return_value=True)
        self.get_all_tasks = Mock(return_value=[])
        self.get_all_meetings = Mock(return_value=[])
        
        # Mock the Google API service chain
        self.sheets_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            'spreadsheetId': 'test_config_sheet_id',
            'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_config_sheet_id'
        }
        self.drive_service.files.return_value.update.return_value.execute.return_value = {
            'id': 'test_config_sheet_id'
        }


class MockTimerScheduler:
    """Mock timer scheduler for testing."""
    
    def __init__(self):
        self.running = False
        self.active_timers = {}
        
        # Mock methods
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.add_timer = AsyncMock()
        self.update_timer = AsyncMock()
        self.cancel_timer = AsyncMock()
        self.get_active_timers = Mock(return_value={})
        
        # Make cancel_timer return a coroutine to avoid "object Mock can't be used in 'await' expression" error
        self.cancel_timer = AsyncMock()


class MockReconciliationManager:
    """Mock reconciliation manager for testing."""
    
    def __init__(self):
        # Mock methods
        self.reconciliation_loop = AsyncMock()
        self.reconcile_timers = AsyncMock()
        self.timer_scheduler = MockTimerScheduler()


class MockSlashCommands:
    """Mock slash commands for testing."""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def setup_command(self, interaction):
        """Mock setup command."""
        if not isinstance(interaction.channel, MockDiscordDMChannel):
            await interaction.response.send_message(
                "❌ This command can only be used in DMs. Please send me a private message and use `/setup` there.",
                ephemeral=True
            )
            return
            
        guild_id = str(interaction.guild.id) if interaction.guild else None
        guild_name = interaction.guild.name if interaction.guild else None
        response = await self.bot.setup_manager.start_setup(str(interaction.user.id), interaction.user.name, guild_id, guild_name)
        await interaction.response.send_message(response)
    
    async def cancel_setup_command(self, interaction):
        """Mock cancel setup command."""
        if not isinstance(interaction.channel, MockDiscordDMChannel):
            await interaction.response.send_message(
                "❌ This command can only be used in DMs. Please send me a private message and use `/cancel` there.",
                ephemeral=True
            )
            return
            
        response = self.bot.setup_manager.cancel_setup(str(interaction.user.id))
        await interaction.response.send_message(response)


def create_mock_setup_state(user_id: str = "123456789", step: str = "club_name") -> Dict[str, Any]:
    """Create a mock setup state for testing."""
    return {
        'step': step,
        'club_name': 'Test Club',
        'admin_discord_id': '123456789',
        'timezone': 'America/Edmonton',
        'exec_members': [],
        'exec_count': 0,
        'current_exec_index': 0,
        'guild_id': '987654321',
        'guild_name': 'Test Guild',
        'config_folder_id': 'test_config_folder_id',
        'monthly_folder_id': 'test_monthly_folder_id',
        'meeting_minutes_folder_id': 'test_meeting_minutes_folder_id',
        'config_spreadsheet_id': 'test_config_spreadsheet_id',
        'monthly_sheets': {
            'tasks': 'test_tasks_sheet_id',
            'meetings': 'test_meetings_sheet_id'
        },
        'channels_configured': False
    }


def create_mock_guild_config(guild_id: str = "987654321") -> Dict[str, Any]:
    """Create a mock guild configuration for testing."""
    return {
        'guild_name': 'Test Guild',
        'club_name': 'Test Club',
        'admin_user_id': '123456789',
        'timezone': 'America/Edmonton',
        'exec_members': [
            {
                'name': 'John Doe',
                'role': 'President',
                'discord_id': '123456789'
            }
        ],
        'config_spreadsheet_id': 'test_config_spreadsheet_id',
        'task_reminders_channel_id': '111222333',
        'meeting_reminders_channel_id': '444555666',
        'escalation_channel_id': '777888999',
        'general_announcements_channel_id': '000111222',
        'free_speak_channel_id': '333444555',
        'config_folder_id': 'test_config_folder_id',
        'monthly_folder_id': 'test_monthly_folder_id',
        'meeting_minutes_folder_id': 'test_meeting_minutes_folder_id',
        'monthly_sheets': {
            'tasks': 'test_tasks_sheet_id',
            'meetings': 'test_meetings_sheet_id'
        },
        'setup_complete': True,
        'completed_at': datetime.now().isoformat()
    }


def create_mock_timer_data(timer_id: str = "test_timer_1", timer_type: str = "task_reminder_24h") -> Dict[str, Any]:
    """Create mock timer data for testing."""
    return {
        'id': timer_id,
        'type': timer_type,
        'fire_at_utc': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        'channel_id': '111222333',
        'title': 'Test Task',
        'mention': '<@123456789>',
        'state': 'active'
    }


def create_mock_task_data(task_id: str = "test_task_1") -> Dict[str, Any]:
    """Create mock task data for testing."""
    return {
        'id': task_id,
        'title': 'Test Task',
        'assigned_to': '123456789',
        'deadline': (datetime.now() + timedelta(days=1)).isoformat(),
        'status': 'Open',
        'guild_id': '987654321'
    }


def create_mock_meeting_data(meeting_id: str = "test_meeting_1") -> Dict[str, Any]:
    """Create mock meeting data for testing."""
    return {
        'id': meeting_id,
        'title': 'Test Meeting',
        'start_time': (datetime.now() + timedelta(hours=2)).isoformat(),
        'guild_id': '987654321'
    }


# Import timedelta for the mock functions
from datetime import timedelta
