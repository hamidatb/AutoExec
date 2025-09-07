"""
Club Exec Task Manager Bot - Discord client implementation.
Refactored version with modular structure.
"""

import discord
from discord import app_commands
import asyncio
from datetime import datetime

from googledrive.sheets_manager import ClubSheetsManager
from googledrive.meeting_manager import MeetingManager
from googledrive.task_manager import TaskManager
from googledrive.setup_manager import SetupManager
from googledrive.minutes_parser import MinutesParser
from googledrive.timer_scheduler import TimerScheduler
from config.config import Config

# Import modular components
from .modules import MessageHandlers, SlashCommands, SetupManager as BotSetupManager, ReconciliationManager, BotUtils

Config()


class ClubExecBot(discord.Client):
    """
    Club Exec Task Manager Bot - Discord client implementation.
    Handles slash commands, setup process, user interactions, and natural language processing.
    """
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.messages = True
        
        super().__init__(intents=intents)
        
        # Initialize command tree for slash commands
        self.tree = app_commands.CommandTree(self)
        
        # Initialize managers
        self.sheets_manager = ClubSheetsManager()
        self.meeting_manager = MeetingManager()
        self.task_manager = TaskManager()
        self.setup_manager = SetupManager()
        self.minutes_parser = MinutesParser()
        self.timer_scheduler = TimerScheduler(self)
        
        # Store active reminders and timers
        self.active_reminders = {}
        self.setup_sessions = {}
        
        # Bot configuration
        self.club_configs = {}  # Store club configurations in memory
        
        # LangChain agent for natural language processing
        self.langchain_agent = None
        
        # Store last channel context for LangChain responses
        self.last_channel_id = None
        
        # Initialize modular components
        self.message_handlers = MessageHandlers(self)
        self.slash_commands = SlashCommands(self)
        self.setup_manager_bot = BotSetupManager(self)
        self.reconciliation_manager = ReconciliationManager(self)
        self.utils = BotUtils(self)
        
        # Bot uptime tracking
        self.start_time = datetime.now()
    
    async def setup_hook(self):
        """Set up slash commands when the bot starts."""
        try:
            # Register slash commands
            self.slash_commands.register_commands()
            
            synced = await self.tree.sync()
            print(f"✅ Slash commands synced! {len(synced)} commands registered:")
            for cmd in synced:
                print(f"  - /{cmd.name}: {cmd.description}")
        except Exception as e:
            print(f"❌ Error syncing slash commands: {e}")
    
    async def on_ready(self):
        """Called when the bot successfully logs in."""
        print(f'✅ Logged in as {self.user}')
        print(f'🆔 Bot ID: {self.user.id}')
        print(f'🏠 Connected to {len(self.guilds)} guild(s)')
        
        # Load existing club configurations
        await self.setup_manager_bot.load_club_configurations()
        
        # Start the timer scheduler (replaces old reminder system)
        await self.timer_scheduler.start()
        
        # Start reconciliation loop
        asyncio.create_task(self.reconciliation_manager.reconciliation_loop())
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        if message.author == self.user:
            return
            
        # Handle DM setup process FIRST - this takes priority
        if isinstance(message.channel, discord.DMChannel):
            # Always handle setup-related commands and questions first
            handled = await self.message_handlers.handle_dm_setup(message)
            
            # Only process natural language if setup manager didn't handle it AND dm_setup didn't handle it
            if not handled and not self.setup_manager.is_in_setup(str(message.author.id)):
                await self.message_handlers.handle_dm_general_query(message)
            return
            
        # For public channels, respond when the bot is mentioned OR in free-speak channel
        if self.user in message.mentions or self._is_free_speak_channel(message.channel):
            # Handle different types of commands
            if message.content.startswith('$AEmm'):
                await self.message_handlers.handle_meeting_minutes_request(message)
            elif message.content.startswith('$AE'):
                await self.message_handlers.handle_autoexec_command(message)
            elif message.content.startswith('/config'):
                await self.message_handlers.handle_config_command_usage(message)
            elif self.message_handlers.should_use_langchain(message.content):
                await self.message_handlers.handle_langchain_query(message)
        
        # Handle task replies (replies to task reminder messages)
        if message.reference:
            await self.message_handlers.handle_task_reply(message)
    
    def _is_free_speak_channel(self, channel: discord.TextChannel) -> bool:
        """Check if the channel is configured as a free-speak channel."""
        try:
            guild_id = str(channel.guild.id)
            config = self.club_configs.get(guild_id)
            
            if not config:
                return False
            
            free_speak_channel_id = config.get('free_speak_channel')
            if not free_speak_channel_id:
                return False
            
            return str(channel.id) == str(free_speak_channel_id)
        except Exception as e:
            print(f"❌ Error checking free-speak channel: {e}")
            return False
    
    # Delegate methods to modular components
    async def handle_natural_language(self, message: discord.Message):
        """Delegate to message handlers."""
        await self.message_handlers.handle_natural_language(message)
    
    async def handle_autoexec_command(self, message: discord.Message):
        """Delegate to message handlers."""
        await self.message_handlers.handle_autoexec_command(message)
    
    async def handle_meeting_minutes_request(self, message: discord.Message):
        """Delegate to message handlers."""
        await self.message_handlers.handle_meeting_minutes_request(message)
    
    async def handle_config_command_usage(self, message: discord.Message):
        """Delegate to message handlers."""
        await self.message_handlers.handle_config_command_usage(message)
    
    async def handle_langchain_query(self, message: discord.Message):
        """Delegate to message handlers."""
        await self.message_handlers.handle_langchain_query(message)
    
    async def handle_dm_general_query(self, message: discord.Message):
        """Delegate to message handlers."""
        await self.message_handlers.handle_dm_general_query(message)
    
    def should_use_langchain(self, content: str) -> bool:
        """Delegate to message handlers."""
        return self.message_handlers.should_use_langchain(content)
    
    async def handle_dm_setup(self, message: discord.Message) -> bool:
        """Delegate to message handlers."""
        return await self.message_handlers.handle_dm_setup(message)
    
    async def handle_task_reply(self, message: discord.Message):
        """Delegate to message handlers."""
        await self.message_handlers.handle_task_reply(message)
    
    async def load_club_configurations(self):
        """Delegate to setup manager."""
        await self.setup_manager_bot.load_club_configurations()
    
    def _is_user_admin_of_any_guild(self, user_id: str) -> bool:
        """Delegate to setup manager."""
        return self.setup_manager_bot._is_user_admin_of_any_guild(user_id)
    
    def _get_user_setup_status_direct(self, user_id: str) -> str:
        """Delegate to setup manager."""
        return self.setup_manager_bot._get_user_setup_status_direct(user_id)
    
    def is_fully_setup(self, guild_id: str = None, user_id: str = None) -> bool:
        """Delegate to setup manager."""
        return self.setup_manager_bot.is_fully_setup(guild_id, user_id)
    
    async def check_setup_gate(self, interaction: discord.Interaction) -> bool:
        """Delegate to setup manager."""
        return await self.setup_manager_bot.check_setup_gate(interaction)
    
    async def verify_dm_admin_access(self, interaction: discord.Interaction, server_id: str) -> bool:
        """Delegate to setup manager."""
        return await self.setup_manager_bot.verify_dm_admin_access(interaction, server_id)
    
    async def reconciliation_loop(self):
        """Delegate to reconciliation manager."""
        await self.reconciliation_manager.reconciliation_loop()
    
    async def reconcile_timers(self):
        """Delegate to reconciliation manager."""
        await self.reconciliation_manager.reconcile_timers()
    
    async def send_any_message(self, message: str, channel_id: int = None):
        """Delegate to utils."""
        await self.utils.send_any_message(message, channel_id)
    
    @property
    def uptime(self) -> str:
        """Get bot uptime."""
        try:
            uptime_delta = datetime.now() - self.start_time
            return self.utils.format_duration(int(uptime_delta.total_seconds()))
        except Exception as e:
            print(f"❌ Error getting uptime: {e}")
            return "Unknown"


# Create the bot instance
bot = ClubExecBot()

# Make bot instance globally accessible for LangChain agent
BOT_INSTANCE = bot


def run_bot():
    """Run the Club Exec Task Manager Bot."""
    bot_token = Config.DISCORD_TOKEN
    
    if not bot_token:
        print("❌ DISCORD_BOT_TOKEN not found in environment variables")
        return
        
    try:
        print("🚀 Starting Club Exec Task Manager Bot...")
        print("🤖 Bot now supports natural language and LangChain integration!")
        bot.run(bot_token)
    except Exception as e:
        print(f"❌ Error starting bot: {e}")


if __name__ == "__main__":
    run_bot()
