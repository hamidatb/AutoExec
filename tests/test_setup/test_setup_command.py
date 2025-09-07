"""
Tests for the /setup command and setup blocking functionality.
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


class TestSetupCommand:
    """Test the /setup command functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
        self.error_scenarios = create_error_scenarios()
        self.success_scenarios = create_success_scenarios()
    
    def test_setup_command_dm_only(self):
        """Test that /setup command only works in DMs."""
        # Create a non-DM interaction
        user = MockDiscordUser()
        guild = MockDiscordGuild()
        interaction = MockDiscordInteraction(user, guild, is_dm=False)
        
        # Mock the command handler
        from discordbot.modules.commands import SlashCommands
        commands = SlashCommands(self.bot)
        
        # Test that non-DM interaction is rejected
        async def test_non_dm_setup():
            await commands.setup_command(interaction)
            interaction.response.send_message.assert_called_once()
            call_args = interaction.response.send_message.call_args[0][0]
            assert "DM" in call_args
            assert "private message" in call_args
        
        asyncio.run(test_non_dm_setup())
    
    def test_setup_command_dm_success(self):
        """Test that /setup command works in DMs."""
        # Create a DM interaction
        user = MockDiscordUser()
        interaction = MockDiscordInteraction(user, is_dm=True)
        
        # Mock the setup manager response
        expected_response = "🎉 **Welcome to the Club Exec Task Manager Bot!** 🎉"
        self.setup_manager.start_setup.return_value = expected_response
        
        # Mock the command handler
        from discordbot.modules.commands import SlashCommands
        commands = SlashCommands(self.bot)
        
        # Test that DM interaction is accepted
        async def test_dm_setup():
            await commands.setup_command(interaction)
            interaction.response.send_message.assert_called_once_with(expected_response)
            self.setup_manager.start_setup.assert_called_once()
        
        asyncio.run(test_dm_setup())
    
    def test_setup_command_with_guild_context(self):
        """Test /setup command with guild context."""
        # Create a DM interaction with guild context
        user = MockDiscordUser()
        guild = MockDiscordGuild()
        interaction = MockDiscordInteraction(user, guild, is_dm=True)
        
        # Mock the setup manager response
        expected_response = "🎉 **Welcome to the Club Exec Task Manager Bot!** 🎉"
        self.setup_manager.start_setup.return_value = expected_response
        
        # Mock the command handler
        from discordbot.modules.commands import SlashCommands
        commands = SlashCommands(self.bot)
        
        # Test that setup is called with guild context
        async def test_setup_with_guild():
            await commands.setup_command(interaction)
            self.setup_manager.start_setup.assert_called_once_with(
                str(user.id), user.name, str(guild.id), guild.name
            )
        
        asyncio.run(test_setup_with_guild())
    
    def test_setup_command_without_guild_context(self):
        """Test /setup command without guild context."""
        # Create a DM interaction without guild context
        user = MockDiscordUser()
        interaction = MockDiscordInteraction(user, is_dm=True)
        interaction.guild = None
        
        # Mock the setup manager response
        expected_response = "🎉 **Welcome to the Club Exec Task Manager Bot!** 🎉"
        self.setup_manager.start_setup.return_value = expected_response
        
        # Mock the command handler
        from discordbot.modules.commands import SlashCommands
        commands = SlashCommands(self.bot)
        
        # Test that setup is called without guild context
        async def test_setup_without_guild():
            await commands.setup_command(interaction)
            self.setup_manager.start_setup.assert_called_once_with(
                str(user.id), user.name, None, None
            )
        
        asyncio.run(test_setup_without_guild())


class TestSetupBlocking:
    """Test that features are blocked until setup is complete."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
    
    def test_setup_gate_not_started(self):
        """Test setup gate when setup hasn't been started."""
        # Create interaction
        user = MockDiscordUser()
        guild = MockDiscordGuild()
        interaction = MockDiscordInteraction(user, guild)
        
        # Mock setup manager to return not started
        self.setup_manager.is_fully_setup.return_value = False
        
        # Test setup gate
        from discordbot.modules.setup import SetupManager
        setup_gate = SetupManager(self.bot)
        
        async def test_setup_gate():
            result = await setup_gate.check_setup_gate(interaction)
            assert result is False
            interaction.response.send_message.assert_called_once()
            call_args = interaction.response.send_message.call_args[0][0]
            assert "Setup Required" in call_args
            assert "/setup" in call_args
        
        asyncio.run(test_setup_gate())
    
    def test_setup_gate_in_progress(self):
        """Test setup gate when setup is in progress."""
        # Create interaction
        user = MockDiscordUser()
        guild = MockDiscordGuild()
        interaction = MockDiscordInteraction(user, guild)
        
        # Mock setup manager to return in progress
        self.setup_manager.is_fully_setup.return_value = False
        self.setup_manager.is_in_setup.return_value = True
        
        # Test setup gate
        from discordbot.modules.setup import SetupManager
        setup_gate = SetupManager(self.bot)
        
        async def test_setup_gate():
            result = await setup_gate.check_setup_gate(interaction)
            assert result is False
            interaction.response.send_message.assert_called_once()
            call_args = interaction.response.send_message.call_args[0][0]
            assert "Setup Required" in call_args
        
        asyncio.run(test_setup_gate())
    
    def test_setup_gate_completed(self):
        """Test setup gate when setup is completed."""
        # Create interaction
        user = MockDiscordUser()
        guild = MockDiscordGuild()
        interaction = MockDiscordInteraction(user, guild)
        
        # Mock setup manager to return completed
        self.setup_manager.is_fully_setup.return_value = True
        
        # Test setup gate
        from discordbot.modules.setup import SetupManager
        setup_gate = SetupManager(self.bot)
        
        async def test_setup_gate():
            result = await setup_gate.check_setup_gate(interaction)
            assert result is True
            interaction.response.send_message.assert_not_called()
        
        asyncio.run(test_setup_gate())
    
    def test_setup_gate_guild_not_setup(self):
        """Test setup gate when user is setup but guild is not."""
        # Create interaction
        user = MockDiscordUser()
        guild = MockDiscordGuild()
        interaction = MockDiscordInteraction(user, guild)
        
        # Mock setup manager to return user setup but guild not setup
        def mock_is_fully_setup(guild_id=None, user_id=None):
            if user_id:
                return True  # User is setup
            if guild_id:
                return False  # Guild is not setup
            return False
        
        self.setup_manager.is_fully_setup.side_effect = mock_is_fully_setup
        
        # Test setup gate
        from discordbot.modules.setup import SetupManager
        setup_gate = SetupManager(self.bot)
        
        async def test_setup_gate():
            result = await setup_gate.check_setup_gate(interaction)
            assert result is False
            interaction.response.send_message.assert_called_once()
            call_args = interaction.response.send_message.call_args[0][0]
            assert "Guild Setup Required" in call_args
        
        asyncio.run(test_setup_gate())
    
    def test_setup_gate_error_handling(self):
        """Test setup gate error handling."""
        # Create interaction
        user = MockDiscordUser()
        guild = MockDiscordGuild()
        interaction = MockDiscordInteraction(user, guild)
        
        # Mock setup manager to raise an exception
        self.setup_manager.is_fully_setup.side_effect = Exception("Test error")
        
        # Test setup gate
        from discordbot.modules.setup import SetupManager
        setup_gate = SetupManager(self.bot)
        
        async def test_setup_gate():
            result = await setup_gate.check_setup_gate(interaction)
            assert result is False
            interaction.response.send_message.assert_called_once()
            call_args = interaction.response.send_message.call_args[0][0]
            assert "error occurred" in call_args.lower()
        
        asyncio.run(test_setup_gate())


class TestCancelCommand:
    """Test the /cancel command functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
    
    def test_cancel_command_dm_only(self):
        """Test that /cancel command only works in DMs."""
        # Create a non-DM interaction
        user = MockDiscordUser()
        guild = MockDiscordGuild()
        interaction = MockDiscordInteraction(user, guild, is_dm=False)
        
        # Mock the command handler
        from discordbot.modules.commands import SlashCommands
        commands = SlashCommands(self.bot)
        
        # Test that non-DM interaction is rejected
        async def test_non_dm_cancel():
            await commands.cancel_setup_command(interaction)
            interaction.response.send_message.assert_called_once()
            call_args = interaction.response.send_message.call_args[0][0]
            assert "DM" in call_args
            assert "private message" in call_args
        
        asyncio.run(test_non_dm_cancel())
    
    def test_cancel_command_dm_success(self):
        """Test that /cancel command works in DMs."""
        # Create a DM interaction
        user = MockDiscordUser()
        interaction = MockDiscordInteraction(user, is_dm=True)
        
        # Mock the setup manager response
        expected_response = "❌ Setup cancelled. You can start again anytime with `/setup`."
        self.setup_manager.cancel_setup.return_value = expected_response
        
        # Mock the command handler
        from discordbot.modules.commands import SlashCommands
        commands = SlashCommands(self.bot)
        
        # Test that DM interaction is accepted
        async def test_dm_cancel():
            await commands.cancel_setup_command(interaction)
            interaction.response.send_message.assert_called_once_with(expected_response)
            self.setup_manager.cancel_setup.assert_called_once_with(str(user.id))
        
        asyncio.run(test_dm_cancel())
    
    def test_cancel_command_no_setup_session(self):
        """Test /cancel command when no setup session exists."""
        # Create a DM interaction
        user = MockDiscordUser()
        interaction = MockDiscordInteraction(user, is_dm=True)
        
        # Mock the setup manager response for no session
        expected_response = "❌ No setup session found to cancel."
        self.setup_manager.cancel_setup.return_value = expected_response
        
        # Mock the command handler
        from discordbot.modules.commands import SlashCommands
        commands = SlashCommands(self.bot)
        
        # Test that cancel works even with no session
        async def test_cancel_no_session():
            await commands.cancel_setup_command(interaction)
            interaction.response.send_message.assert_called_once_with(expected_response)
            self.setup_manager.cancel_setup.assert_called_once_with(str(user.id))
        
        asyncio.run(test_cancel_no_session())


class TestSetupFlow:
    """Test the complete setup flow."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.setup_manager = MockSetupManager()
        self.bot.setup_manager = self.setup_manager
        self.test_data = create_test_data_set()
    
    def test_setup_flow_start(self):
        """Test starting the setup flow."""
        user_id = self.test_data['user_id']
        user_name = "testuser"
        guild_id = self.test_data['guild_id']
        guild_name = "Test Guild"
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test starting setup
        async def test_start_setup():
            response = await setup_manager.start_setup(user_id, user_name, guild_id, guild_name)
            assert "Welcome to the Club Exec Task Manager Bot" in response
            assert "Step 1: Club Information" in response
            assert guild_name in response
        
        asyncio.run(test_start_setup())
    
    def test_setup_flow_without_guild(self):
        """Test starting the setup flow without guild context."""
        user_id = self.test_data['user_id']
        user_name = "testuser"
        
        # Mock the setup manager
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test starting setup without guild
        async def test_start_setup_no_guild():
            response = await setup_manager.start_setup(user_id, user_name)
            assert "Welcome to the Club Exec Task Manager Bot" in response
            assert "Step 1: Server ID" in response
        
        asyncio.run(test_start_setup_no_guild())
    
    def test_setup_flow_error_handling(self):
        """Test setup flow error handling."""
        user_id = self.test_data['user_id']
        user_name = "testuser"
        
        # Mock the setup manager to raise an exception
        from googledrive.setup_manager import SetupManager
        setup_manager = SetupManager()
        
        # Test error handling
        async def test_setup_error():
            # This should not raise an exception
            response = await setup_manager.start_setup(user_id, user_name)
            assert "error occurred" in response.lower() or "Welcome" in response
        
        asyncio.run(test_setup_error())


if __name__ == "__main__":
    pytest.main([__file__])
