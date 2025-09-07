import discord
from discord import app_commands
import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from googledrive.sheets_manager import ClubSheetsManager
from googledrive.meeting_manager import MeetingManager
from googledrive.task_manager import TaskManager
from googledrive.setup_manager import SetupManager
from googledrive.minutes_parser import MinutesParser
from googledrive.timer_scheduler import TimerScheduler
from ae_langchain.main_agent import run_agent
from config import Config

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
        
    async def setup_hook(self):
        """Set up slash commands when the bot starts."""
        try:
            synced = await self.tree.sync()
            print(f"✅ Slash commands synced! {len(synced)} commands registered:")
            for cmd in synced:
                print(f"  - /{cmd.name}: {cmd.description}")
        except Exception as e:
            print(f"❌ Error syncing slash commands: {e}")
        
        # Background tasks are now handled by the timer scheduler
        
    async def on_ready(self):
        """Called when the bot successfully logs in."""
        print(f'✅ Logged in as {self.user}')
        print(f'🆔 Bot ID: {self.user.id}')
        print(f'🏠 Connected to {len(self.guilds)} guild(s)')
        
        # Load existing club configurations
        await self.load_club_configurations()
        
        # Start the timer scheduler (replaces old reminder system)
        await self.timer_scheduler.start()
        
        # Start reconciliation loop
        asyncio.create_task(self.reconciliation_loop())
        
    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        if message.author == self.user:
            return
            
        # Handle DM setup process FIRST - this takes priority
        if isinstance(message.channel, discord.DMChannel):
            # Always handle setup-related commands and questions first
            handled = await self.handle_dm_setup(message)
            
            # Only process natural language if setup manager didn't handle it AND dm_setup didn't handle it
            if not handled and not self.setup_manager.is_in_setup(str(message.author.id)):
                await self.handle_natural_language(message)
            return
            
        # For public channels, respond when the bot is mentioned OR in free-speak channel
        should_respond = False
        
        # Check if bot is mentioned
        if message.mentions and self.user in message.mentions:
            should_respond = True
        
        # Check if this is the free-speak channel
        if not should_respond and message.guild:
            guild_id = str(message.guild.id)
            all_guilds = self.setup_manager.status_manager.get_all_guilds()
            club_config = all_guilds.get(guild_id)
            
            if club_config and club_config.get('setup_complete', False):
                free_speak_channel_id = club_config.get('free_speak_channel_id')
                if free_speak_channel_id and str(message.channel.id) == str(free_speak_channel_id):
                    should_respond = True
        
        if should_respond:
            await self.handle_natural_language(message)
            await self.handle_task_reply(message)
            
    async def handle_natural_language(self, message: discord.Message):
        """Handle natural language messages using LangChain agent."""
        # CRITICAL: Skip natural language processing if user is in setup mode
        if isinstance(message.channel, discord.DMChannel) and self.setup_manager.is_in_setup(str(message.author.id)):
            return
        
        # Check setup gating for ALL channels (including DMs for non-setup users)
        guild_id = str(message.guild.id) if message.guild else None
        user_id = str(message.author.id)
        
        print(f"🔍 [SETUP CHECK] Checking setup for user {user_id}, guild {guild_id}")
        # For guild messages, check guild setup. For DMs, we need to find which guild the user is admin of
        if guild_id:
            setup_complete = self.setup_manager.is_setup_complete(guild_id)
        else:
            # For DMs, check if user is admin of any guild
            setup_complete = self._is_user_admin_of_any_guild(user_id)
        print(f"🔍 [SETUP CHECK] Setup complete: {setup_complete}")
        
        # Check if this is a setup-related question (regardless of setup status)
        content_lower = message.content.lower()
        setup_keywords = ['setup', 'set up', 'configured', 'configuration', 'are you set up', 'setup status', 'am i set up']
        
        if any(keyword in content_lower for keyword in setup_keywords):
            # Handle setup status check directly
            if guild_id:
                # Server context - check this specific guild
                if setup_complete:
                    # Guild is set up - show success message
                    guild_config = self.setup_manager.get_guild_config(guild_id)
                    guild_name = guild_config.get('guild_name', 'Unknown Server') if guild_config else 'Unknown Server'
                    club_name = guild_config.get('club_name', 'Unknown Club') if guild_config else 'Unknown Club'
                    
                    await message.channel.send(
                        f"✅ **Setup Status: CONFIGURED**\n\n"
                        f"I am set up for **{club_name}** in server **{guild_name}**.\n\n"
                        f"**Configuration:**\n"
                        f"• Server: {guild_name} (ID: {guild_id})\n"
                        f"• Club: {club_name}\n\n"
                        f"**Current Status:** Fully operational! 🎉"
                    )
                else:
                    # Guild is not set up
                    await message.channel.send(
                        f"❌ **Setup Required**\n\n"
                        f"I am not set up for the guild with ID {guild_id}. If you would like to set up the bot for this guild, please follow the setup instructions."
                    )
            else:
                # DM context - check if user is admin of any guild
                response = self._get_user_setup_status_direct(user_id)
                await message.channel.send(response)
            return
        
        # If not a setup question and setup is not complete, block other processing
        if not setup_complete:
            await message.channel.send(
                "❌ **Setup Required**\n\n"
                "Setup is not complete. Please ask your admin to run `/setup` in DM with me."
            )
            return
            
        # Store channel context for LangChain responses
        self.last_channel_id = message.channel.id
        
        # Set Discord context for LangChain tools (for both @mentions and DMs)
        from ae_langchain.main_agent import set_discord_context
        set_discord_context(
            guild_id=str(message.guild.id) if message.guild else None,
            channel_id=str(message.channel.id),
            user_id=str(message.author.id)
        )
        
        # Clean the content - remove bot mentions for processing
        content = message.content.strip()
        if message.mentions and self.user in message.mentions:
            # Remove the bot mention from the content
            content = re.sub(rf'<@!?{self.user.id}>', '', content).strip()
            
            
        # Check for config command usage as regular message (should be slash command)
        if content.startswith('/config') or content.startswith('/serverconfig'):
            await self.handle_config_command_usage(message)
            return
            
        # Check for general natural language queries
        if self.should_use_langchain(content):
            print(f"🔍 Using LangChain for message: {content}")
            # Set Discord context for LangChain tools
            from ae_langchain.main_agent import set_discord_context
            set_discord_context(
                guild_id=str(message.guild.id) if message.guild else None,
                channel_id=str(message.channel.id),
                user_id=str(message.author.id)
            )
            await self.handle_langchain_query(message)
            return
        else:
            print(f"🔍 NOT using LangChain for message: {content}")
            
        # Special handling for DMs ONLY if no other handler was used
        # This prevents duplicate processing and welcome messages in wrong contexts
        if isinstance(message.channel, discord.DMChannel):
            # Set Discord context for LangChain tools (DM context)
            from ae_langchain.main_agent import set_discord_context
            set_discord_context(
                guild_id=None,  # DMs don't have guild context
                channel_id=str(message.channel.id),
                user_id=str(message.author.id)
            )
            await self.handle_dm_general_query(message)
            return
            
    async def handle_autoexec_command(self, message: discord.Message):
        """Handle $AE commands using LangChain agent."""
        # CRITICAL: Skip if user is in setup mode
        if isinstance(message.channel, discord.DMChannel) and self.setup_manager.is_in_setup(str(message.author.id)):
            return
            
        try:
            # Store channel context for LangChain responses
            self.last_channel_id = message.channel.id
            
            # Remove the $AE prefix
            query = message.content[4:].strip()
            
            if not query:
                await message.channel.send("🤖 I'm here! What would you like me to help you with?")
                return
            
            # Handle specific system questions directly
            query_lower = query.lower()
            if any(keyword in query_lower for keyword in ['system architecture', 'how do you work', 'what are you', 'what can you do']):
                if 'system architecture' in query_lower or 'how do you work' in query_lower:
                    response = """**AutoExec System Architecture**

**Core Components:**
• **Discord Bot Interface** - Handles user commands and natural language queries
• **LangChain AI Agent** - Processes complex requests using GPT-3.5-turbo
• **Google Drive Integration** - Manages meetings, tasks, and documents
• **Task Management System** - Tracks deadlines, reminders, and status updates

**How It Works:**
1. You send a message (like `$AE` commands or natural language)
2. Bot stores channel context and processes your request
3. LangChain agent analyzes the query and generates responses
4. Bot sends responses back to the same Discord channel
5. All data is stored in Google Sheets for persistence

**Available Features:**
• Meeting scheduling and reminders
• Task assignment and tracking
• Natural language processing
• Google Drive document management
• Automated deadline notifications

I'm designed to help manage club executive tasks efficiently! 🎯"""
                elif 'what can you do' in query_lower:
                    response = """**What I Can Do**

**Meeting Management:**
• Schedule meetings with `/meeting set`
• View upcoming meetings with `/meeting_upcoming`
• Create agenda templates
• Link and parse meeting minutes

**Task Management:**
• Assign tasks with `/assign @user "task" due:"date"`
• Track task status and deadlines
• Send automated reminders
• Handle task updates (done, reschedule, etc.)

**Natural Language:**
• Answer questions about meetings and tasks
• Help with scheduling and organization
• Provide information about the system
• Process complex requests using AI

**Automation:**
• Send meeting reminders (T-2h, T-0)
• Track overdue tasks
• Parse action items from minutes
• Manage Google Drive documents

Just ask me anything about meetings, tasks, or how I can help! 🚀"""
                else:
                    response = "🤖 I'm AutoExec, your AI-powered club executive task manager! I help with meetings, tasks, scheduling, and organization. What would you like to know?"
                
                await message.channel.send(response)
                return
                
            # Use LangChain agent to process the query
            # Run in a thread to avoid blocking the event loop
            import concurrent.futures
            loop = asyncio.get_event_loop()
            
            def run_agent_sync(query):
                from ae_langchain.main_agent import run_agent_text_only
                try:
                    # Pass the guild context for server-specific memory
                    guild_id = str(message.guild.id) if message.guild else None
                    user_id = str(message.author.id)
                    return run_agent_text_only(query, guild_id=guild_id, user_id=user_id)
                except Exception as e:
                    return f"I'm sorry, I encountered an error: {str(e)}"
            
            # Run the agent in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(executor, run_agent_sync, query)
            
            print(f"🔍 LangChain response: {response}")
            
            # Send response directly to the channel
            await message.channel.send(response)
            
            # Check for and send any pending announcements
            from ae_langchain.main_agent import _pending_announcements
            if _pending_announcements:
                for announcement in _pending_announcements:
                    try:
                        # If no specific channel_id, use the current channel
                        channel_id = announcement['channel_id'] or message.channel.id
                        await self.send_any_message(
                            announcement['message'], 
                            channel_id
                        )
                        print(f"✅ Sent pending announcement to channel {channel_id}")
                    except Exception as e:
                        print(f"❌ Failed to send pending announcement: {e}")
                
                # Clear the pending announcements
                _pending_announcements.clear()
            
        except Exception as e:
            print(f"Error in AutoExec command: {e}")
            await message.channel.send("❌ Sorry, I encountered an error processing your request.")
            
    async def handle_meeting_minutes_request(self, message: discord.Message):
        """Handle $AEmm meeting minutes requests."""
        # CRITICAL: Skip if user is in setup mode
        if isinstance(message.channel, discord.DMChannel) and self.setup_manager.is_in_setup(str(message.author.id)):
            return
            
        try:
            # Store channel context for LangChain responses
            self.last_channel_id = message.channel.id
            
            # This would integrate with the meeting minutes system
            # For now, send a helpful response
            response = "📋 **Meeting Minutes Request**\n\n"
            response += "I can help you with meeting minutes! Here are your options:\n\n"
            response += "• Use `/meeting_upcoming` to see scheduled meetings\n"
            response += "• Use natural language to create tasks from meeting minutes\n"
            response += "• I'll automatically parse action items from linked minutes\n\n"
            response += "Need help? Use `/help` to see all available commands!"
            
            await message.channel.send(response)
            
        except Exception as e:
            print(f"Error in meeting minutes request: {e}")
            await message.channel.send("❌ Sorry, I encountered an error processing your request.")

    async def handle_config_command_usage(self, message: discord.Message):
        """Handle when users try to use /config as a regular message instead of slash command."""
        try:
            print(f"🔍 [CONFIG COMMAND] User {message.author.id} tried to use /config as regular message")
            
            # All slash commands are now DM-only
            response = """❌ **Use slash commands, not regular messages**

The `/serverconfig` command is a **slash command** that must be used in DMs.

**How to use configuration commands:**

1. **Send me a DM** (not in server channels)
2. **Type `/serverconfig server_id:123456789`** and Discord will show you the available options
3. **Choose your action:**
   - `/serverconfig server_id:123456789 view` - See current server settings
   - `/serverconfig server_id:123456789 update <setting> <value>` - Update a setting

**Examples:**
- `/serverconfig server_id:123456789 view`
- `/serverconfig server_id:123456789 update task_reminders_channel 123456789012345678`
- `/serverconfig server_id:123456789 update config_folder https://drive.google.com/drive/folders/...`

**Note:** 
• All slash commands are DM-only and admin-only
• Always include the server_id parameter
• Only the server admin can use these commands"""
            
            await message.channel.send(response)
            
        except Exception as e:
            print(f"Error handling config command usage: {e}")
            await message.channel.send("❌ An error occurred while processing your request.")
            
    async def handle_langchain_query(self, message: discord.Message):
        """Handle general natural language queries using LangChain."""
        try:
            print(f"🔍 handle_langchain_query called for message: {message.content}")
            
            # Store channel context for LangChain responses
            self.last_channel_id = message.channel.id
            
            # Use LangChain agent for natural language understanding
            # Run in a thread to avoid blocking the event loop
            import concurrent.futures
            loop = asyncio.get_event_loop()
            
            def run_agent_sync(query):
                from ae_langchain.main_agent import run_agent_text_only
                try:
                    # Pass the guild context for server-specific memory
                    guild_id = str(message.guild.id) if message.guild else None
                    user_id = str(message.author.id)
                    return run_agent_text_only(query, guild_id=guild_id, user_id=user_id)
                except Exception as e:
                    return f"I'm sorry, I encountered an error: {str(e)}"
            
            # Run the agent in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(executor, run_agent_sync, message.content)
            
            print(f"🔍 LangChain response: {response}")
            
            # Send response directly to the channel
            await message.channel.send(response)
            print(f"🔍 [handle_langchain_query] Response sent to channel, now checking for pending announcements...")
            
            # Check for and send any pending announcements
            print(f"🔍 [handle_langchain_query] Checking pending announcements...")
            
            # Import the global variable from the main_agent module
            from ae_langchain.main_agent import _pending_announcements
            print(f"🔍 [handle_langchain_query] Global _pending_announcements exists: {'_pending_announcements' in globals()}")
            print(f"🔍 [handle_langchain_query] _pending_announcements: {_pending_announcements}")
            print(f"🔍 [handle_langchain_query] len(_pending_announcements): {len(_pending_announcements) if _pending_announcements else 'None'}")
            
            if _pending_announcements:
                for announcement in _pending_announcements:
                    try:
                        # If no specific channel_id, use the current channel
                        channel_id = announcement['channel_id'] or message.channel.id
                        await self.send_any_message(
                            announcement['message'], 
                            channel_id
                        )
                        print(f"✅ Sent pending announcement to channel {channel_id}")
                    except Exception as e:
                        print(f"❌ Failed to send pending announcement: {e}")
                
                # Clear the pending announcements
                _pending_announcements.clear()
            
        except Exception as e:
            print(f"❌ [handle_langchain_query] Error in LangChain query: {e}")
            import traceback
            traceback.print_exc()
            await message.channel.send("❌ Sorry, I encountered an error processing your request.")
            
    async def handle_dm_general_query(self, message: discord.Message):
        """Handle general queries in DMs that don't match other patterns."""
        # CRITICAL: Skip if user is in setup mode
        if self.setup_manager.is_in_setup(str(message.author.id)):
            return
            
        try:
            # Store channel context for LangChain responses
            self.last_channel_id = message.channel.id
            
            print(f"🔍 handle_dm_general_query called for message: {message.content}")
            print(f"🔍 Channel type: {type(message.channel)}")
            print(f"🔍 Is DM: {isinstance(message.channel, discord.DMChannel)}")
            
            user_id = str(message.author.id)
            print(f"🔍 Processing query for user {user_id}")
            
            # Check for setup-related questions first
            content_lower = message.content.lower()
            setup_keywords = ['setup', 'set up', 'configured', 'configuration', 'are you set up', 'setup status', 'am i set up']
            
            if any(keyword in content_lower for keyword in setup_keywords):
                # Handle setup status check directly
                from ae_langchain.main_agent import get_user_setup_status
                response = get_user_setup_status(user_id)
                await message.channel.send(response)
                return
            
            # Use LangChain agent for natural language understanding
            # Run in a thread to avoid blocking the event loop
            import concurrent.futures
            loop = asyncio.get_event_loop()
            
            def run_agent_sync(query):
                from ae_langchain.main_agent import run_agent_text_only
                try:
                    # For DMs, pass user_id to handle multiple server scenario
                    user_id = str(message.author.id)
                    return run_agent_text_only(query, guild_id=None, user_id=user_id)
                except Exception as e:
                    return f"I'm sorry, I encountered an error: {str(e)}"
            
            # Run the agent in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(executor, run_agent_sync, message.content)
            
            # Send response directly to the DM
            await message.channel.send(response)
            
            # Check for and send any pending announcements
            print(f"🔍 [DM] Checking for pending announcements...")
            from ae_langchain.main_agent import _pending_announcements
            if _pending_announcements:
                print(f"🔍 [DM] Found {len(_pending_announcements)} pending announcements")
                for i, announcement in enumerate(_pending_announcements):
                    try:
                        # If no specific channel_id, use the current channel
                        channel_id = announcement['channel_id'] or message.channel.id
                        print(f"🔍 [DM] Sending announcement {i+1} to channel {channel_id}")
                        print(f"🔍 [DM] Message: {announcement['message'][:100]}...")
                        await self.send_any_message(
                            announcement['message'], 
                            channel_id
                        )
                        print(f"✅ [DM] Sent pending announcement to channel {channel_id}")
                    except Exception as e:
                        print(f"❌ [DM] Failed to send pending announcement: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Clear the pending announcements
                _pending_announcements.clear()
            else:
                print(f"🔍 [DM] No pending announcements found")
            
        except Exception as e:
            print(f"Error in DM general query: {e}")
            await message.channel.send("❌ Sorry, I encountered an error processing your request.")
            
    def should_use_langchain(self, content: str) -> bool:
        """Determine if a message should be processed by LangChain."""
        # Skip very short messages (likely setup responses)
        if len(content.strip()) <= 2:
            return False
            
        # Since we're only called when the bot is mentioned, be more permissive
        # Skip only obvious non-conversational content
        content_lower = content.lower()
        
        # Skip very short responses that are likely setup confirmations
        if len(content.split()) <= 1 and content_lower in ['yes', 'no', 'ok', 'okay', 'y', 'n']:
            return False
            
        # For everything else, use LangChain since the user specifically mentioned the bot
        return True
            
    async def handle_dm_setup(self, message: discord.Message) -> bool:
        """Handle setup process in DMs.
        
        Returns:
            bool: True if message was handled, False if it should be processed by other handlers
        """
        user_id = str(message.author.id)
        
        if message.content.lower() == '/setup':
            # Start setup process
            guild_id = str(message.guild.id) if message.guild else None
            guild_name = message.guild.name if message.guild else None
            response = await self.setup_manager.start_setup(user_id, message.author.name, guild_id, guild_name)
            await message.channel.send(response)
            return True
            
        if message.content.lower() == '/cancel':
            # Cancel setup
            response = self.setup_manager.cancel_setup(user_id)
            await message.channel.send(response)
            return True
        
        # Handle setup-related questions in DMs
        content_lower = message.content.lower()
        setup_keywords = ['setup', 'set up', 'configured', 'configuration', 'are you set up', 'setup status', 'am i set up']
        
        if any(keyword in content_lower for keyword in setup_keywords):
            # Handle setup status check directly
            response = self._get_user_setup_status_direct(user_id)
            await message.channel.send(response)
            return True
            
        # Check if user is in setup process
        if self.setup_manager.is_in_setup(user_id):
            response = await self.setup_manager.handle_setup_response(user_id, message.content)
            await message.channel.send(response)
            
            # If setup is complete, load the new configuration
            if not self.setup_manager.is_in_setup(user_id):
                await self.load_club_configurations()
            return True
            
        # If not in setup process, check if this is a setup-related question
        # that should be handled by the setup manager instead of LangChain
        content_lower = message.content.lower()
        setup_keywords = ['setup', 'configure', 'are you set up', 'what club', 'admin', 'permission', 'set up']
        
        if any(keyword in content_lower for keyword in setup_keywords):
            # This is a setup-related question - provide helpful setup info
            response = """**Setup Status Check**

I am **NOT** set up for any student groups yet.

**What this means:**
• No clubs or student groups have been configured
• No Google Sheets are linked
• No admin users are set up
• I cannot manage meetings or tasks

**To get started:**
• Run `/setup` to begin the configuration process
• This will set up Google Sheets integration
• Configure admin permissions and channels
• Link your group's meeting and task systems

**Current Status:** Waiting for initial setup by an administrator."""
            
            await message.channel.send(response)
            return True
            
        # If not a setup command and not in setup process, and not a setup question,
        # let natural language processing handle it
        return False
                
    async def handle_task_reply(self, message: discord.Message):
        """Handle user replies to task reminders."""
        # Check setup gating first
        guild_id = str(message.guild.id) if message.guild else None
        if not self.is_fully_setup(guild_id):
            return
        
        # Find the club configuration for this guild
        club_config = self.club_configs.get(guild_id)
        
        if not club_config:
            return
            
        # Handle task status updates
        content_lower = message.content.lower().strip()
        
        if any(keyword in content_lower for keyword in ['done', 'not yet', 'reschedule']):
            # Find the most recent task for this user
            user_tasks = self.task_manager.get_user_tasks(
                str(message.author.id), 
                club_config['tasks_sheet_id']
            )
            
            if user_tasks:
                response = await self.task_manager.handle_task_reply(
                    message.content, 
                    str(message.author.id), 
                    club_config['tasks_sheet_id']
                )
                
                # Send response as a reply
                await message.reply(response)
                
    async def load_club_configurations(self):
        """Load club configurations from Google Sheets."""
        # This would load from the config sheets
        # For now, we'll use environment variables
        pass
    
    def _is_user_admin_of_any_guild(self, user_id: str) -> bool:
        """
        Check if a user is admin of any guild.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user is admin of any guild, False otherwise
        """
        all_guilds = self.setup_manager.status_manager.get_all_guilds()
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('admin_user_id') == user_id and guild_config.get('setup_complete', False):
                print(f"🔍 [SETUP CHECK] User {user_id} is admin of guild {guild_id}")
                return True
        print(f"🔍 [SETUP CHECK] User {user_id} is not admin of any guild")
        return False
    
    def _get_user_setup_status_direct(self, user_id: str) -> str:
        """
        Get setup status for a user directly (without LangChain).
        
        Args:
            user_id: Discord user ID to check
            
        Returns:
            Setup status message
        """
        try:
            # Check if user is admin of any guild
            all_guilds = self.setup_manager.status_manager.get_all_guilds()
            user_guilds = []
            
            for guild_id, config in all_guilds.items():
                if config.get('admin_user_id') == user_id and config.get('setup_complete', False):
                    user_guilds.append((guild_id, config))
            
            if not user_guilds:
                return """❌ **Setup Status: NOT CONFIGURED**\n\nYou are not an admin of any configured student groups.

**What this means:**
• You haven't set up the bot for any servers yet
• Or you're not the admin of any configured servers

**To get started:**
• Run `/setup` in a Discord server where you're an admin
• This will configure the bot for that server
• You can be admin of multiple servers

**Current Status:** No configured servers found for your account."""
            
            # User is admin of one or more guilds
            if len(user_guilds) == 1:
                guild_id, config = user_guilds[0]
                guild_name = config.get('guild_name', 'Unknown Server')
                club_name = config.get('club_name', 'Unknown Club')
                
                return f"""✅ **Setup Status: CONFIGURED**\n\nYou are the admin of **{club_name}** in server **{guild_name}**.

**Your Configuration:**
• Server: {guild_name} (ID: {guild_id})
• Club: {club_name}
• Admin: <@{user_id}>

**What you can do:**
• Schedule and manage meetings
• Create and track meeting minutes
• Assign and monitor tasks
• Send automated reminders
• Process natural language requests

**Current Status:** Fully operational! 🎉"""
            else:
                # User is admin of multiple guilds
                response = f"""✅ **Setup Status: CONFIGURED**\n\nYou are the admin of **{len(user_guilds)}** configured student groups!\n\n"""
                
                for guild_id, config in user_guilds:
                    guild_name = config.get('guild_name', 'Unknown Server')
                    club_name = config.get('club_name', 'Unknown Club')
                    response += f"**{club_name}** (Server: {guild_name})\n"
                
                response += "\n**What you can do:**\n• Schedule and manage meetings\n• Create and track meeting minutes\n• Assign and monitor tasks\n• Send automated reminders\n• Process natural language requests\n\n**Current Status:** Fully operational for all your groups! 🎉"
                
                return response
                
        except Exception as e:
            return f"❌ **Setup Status: ERROR**\n\nError checking setup status: {str(e)}"
    
    def is_fully_setup(self, guild_id: str = None, user_id: str = None) -> bool:
        """
        Checks if the bot is fully set up for a guild or user.
        
        Args:
            guild_id: Guild ID to check (if None, checks if any guild is set up)
            user_id: User ID to check (for DM interactions)
            
        Returns:
            True if fully set up, False otherwise
        """
        print(f"🔍 [SETUP CHECK] is_fully_setup called with guild_id={guild_id}, user_id={user_id}")
        
        # For guild interactions, check guild setup
        if guild_id:
            result = self.setup_manager.is_setup_complete(guild_id)
            print(f"🔍 [SETUP CHECK] Guild {guild_id} setup complete: {result}")
            return result
        
        # For DM interactions, check if user is admin of any guild
        if user_id:
            result = self._is_user_admin_of_any_guild(user_id)
            print(f"🔍 [SETUP CHECK] User {user_id} admin of any guild: {result}")
            return result
        
        # Check if any guild has completed setup
        all_guilds = self.setup_manager.status_manager.get_all_guilds()
        result = any(guild_config.get('setup_complete', False) for guild_config in all_guilds.values())
        print(f"🔍 [SETUP CHECK] Any guild setup complete: {result}")
        return result
    
    async def check_setup_gate(self, interaction: discord.Interaction) -> bool:
        """
        Checks if the bot is set up and blocks commands if not.
        
        Args:
            interaction: Discord interaction to respond to
            
        Returns:
            True if setup is complete, False if blocked
        """
        guild_id = str(interaction.guild.id) if interaction.guild else None
        user_id = str(interaction.user.id)
        
        if not self.is_fully_setup(guild_id=guild_id, user_id=user_id):
            await interaction.response.send_message(
                "❌ **Setup Required**\n\n"
                "Setup is not complete. Please ask your admin to run `/setup` in DM with me.",
                ephemeral=True
            )
            return False
        return True
    
    async def verify_dm_admin_access(self, interaction: discord.Interaction, server_id: str) -> bool:
        """
        Verify that a user in DM has admin access to the specified server.
        
        Args:
            interaction: Discord interaction to respond to
            server_id: Server ID to check admin access for
            
        Returns:
            True if user is admin of the server, False otherwise
        """
        user_id = str(interaction.user.id)
        
        # Get club config from setup manager
        all_guilds = self.setup_manager.status_manager.get_all_guilds()
        club_config = all_guilds.get(server_id)
        
        if not club_config or not club_config.get('setup_complete', False):
            await interaction.response.send_message(
                "❌ **Server Not Configured**\n\n"
                f"No configuration found for server ID {server_id}.\n\n"
                "**To get started:**\n• Run `/setup` in DMs to configure the bot for this server",
                ephemeral=True
            )
            return False
        
        # Check if the user is the admin
        if user_id != club_config.get('admin_user_id'):
            admin_id = club_config.get('admin_user_id', 'Unknown')
            await interaction.response.send_message(
                f"❌ **Access Denied**\n\n"
                f"Only the admin can use this command.\n\n"
                f"**Current Admin:** <@{admin_id}>\n\n"
                f"**Need help?** Contact the admin or run `/setup` in DMs to reconfigure.",
                ephemeral=True
            )
            return False
        
        return True
    
    
    async def reconciliation_loop(self):
        """Reconciliation job that runs every 15 minutes to ensure timers match current data."""
        while True:
            try:
                await asyncio.sleep(900)  # Wait 15 minutes
                await self.reconcile_timers()
            except Exception as e:
                print(f"Error in reconciliation loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def reconcile_timers(self):
        """Reconciles timers with current Tasks and Meetings sheets."""
        try:
            # Get all guild configurations
            all_guilds = self.setup_manager.status_manager.get_all_guilds()
            
            for guild_id, guild_config in all_guilds.items():
                if not guild_config.get('setup_complete', False):
                    continue
                
                config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
                if not config_spreadsheet_id:
                    continue
                
                # Get current timers
                current_timers = self.sheets_manager.get_timers(config_spreadsheet_id)
                
                # Get current tasks and meetings from monthly sheets
                tasks = []
                meetings = []
                monthly_sheets = guild_config.get('monthly_sheets', {})
                
                if 'tasks' in monthly_sheets:
                    tasks = self.sheets_manager.get_all_tasks(monthly_sheets['tasks'])
                if 'meetings' in monthly_sheets:
                    meetings = self.sheets_manager.get_all_meetings(monthly_sheets['meetings'])
                
                # Update timers based on current data
                await self._update_timers_from_data(current_timers, tasks, meetings, config_spreadsheet_id)
                
                # Clean up old timers (run once per reconciliation cycle)
                self.sheets_manager.cleanup_old_timers(config_spreadsheet_id)
            
            print("✅ Timer reconciliation completed")
        except Exception as e:
            print(f"Error in timer reconciliation: {e}")
    
    
    async def _update_timers_from_data(self, current_timers: List[Dict[str, Any]], 
                                     tasks: List[Dict[str, Any]], 
                                     meetings: List[Dict[str, Any]], 
                                     config_spreadsheet_id: str):
        """Updates timers based on current tasks and meetings data."""
        try:
            # Build expected timers from current data
            expected_timers = {}
            
            # Process tasks
            for task in tasks:
                if task.get('status') in ['open', 'in_progress'] and task.get('due_at'):
                    task_timers = self._build_expected_task_timers(task)
                    expected_timers.update(task_timers)
            
            # Process meetings
            for meeting in meetings:
                if meeting.get('status') == 'scheduled' and meeting.get('start_at_utc'):
                    meeting_timers = self._build_expected_meeting_timers(meeting)
                    expected_timers.update(meeting_timers)
            
            # Compare with current timers
            current_timer_map = {t['id']: t for t in current_timers if t.get('state') == 'active'}
            
            # Find timers to add/update
            timers_added = 0
            timers_updated = 0
            timers_cancelled = 0
            
            for timer_id, expected_timer in expected_timers.items():
                if timer_id not in current_timer_map:
                    # New timer - add it
                    await self._add_timer_to_system(expected_timer, config_spreadsheet_id)
                    timers_added += 1
                else:
                    # Check if timer needs updating
                    current_timer = current_timer_map[timer_id]
                    if self._timer_needs_update(current_timer, expected_timer):
                        await self._update_timer_in_system(expected_timer, config_spreadsheet_id)
                        timers_updated += 1
            
            # Find timers to cancel
            for timer_id, current_timer in current_timer_map.items():
                if timer_id not in expected_timers:
                    # Timer no longer needed - cancel it
                    await self._cancel_timer_in_system(timer_id, config_spreadsheet_id)
                    timers_cancelled += 1
            
            print(f"✅ Reconciled timers: {timers_added} added, {timers_updated} updated, {timers_cancelled} cancelled")
            
        except Exception as e:
            print(f"Error updating timers from data: {e}")
    
    def _build_expected_task_timers(self, task: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Build expected timers for a task"""
        timers = {}
        task_id = task['task_id']
        due_at = task['due_at']
        
        if due_at and due_at not in ['next_meeting', 'this_week', 'next_week', 'end_of_month']:
            try:
                deadline = datetime.fromisoformat(due_at)
                
                # Build timer types
                timer_types = [
                    ('task_reminder_24h', deadline - timedelta(hours=24)),
                    ('task_reminder_2h', deadline - timedelta(hours=2)),
                    ('task_overdue', deadline),
                    ('task_escalate', deadline + timedelta(hours=48))
                ]
                
                for timer_type, fire_at in timer_types:
                    timer_id = f"{task_id}_{timer_type}"
                    timers[timer_id] = {
                        'id': timer_id,
                        'guild_id': task.get('guild_id', ''),
                        'type': timer_type,
                        'ref_type': 'task',
                        'ref_id': task_id,
                        'fire_at_utc': fire_at.isoformat(),
                        'channel_id': task.get('channel_id', ''),
                        'state': 'active'
                    }
            except ValueError:
                pass
        
        return timers
    
    def _build_expected_meeting_timers(self, meeting: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Build expected timers for a meeting"""
        timers = {}
        meeting_id = meeting['meeting_id']
        start_at = meeting['start_at_utc']
        
        try:
            start_time = datetime.fromisoformat(start_at)
            
            # Build timer types
            timer_types = [
                ('meeting_reminder_2h', start_time - timedelta(hours=2)),
                ('meeting_start', start_time)
            ]
            
            for timer_type, fire_at in timer_types:
                timer_id = f"{meeting_id}_{timer_type}"
                timers[timer_id] = {
                    'id': timer_id,
                    'guild_id': meeting.get('guild_id', ''),
                    'type': timer_type,
                    'ref_type': 'meeting',
                    'ref_id': meeting_id,
                    'fire_at_utc': fire_at.isoformat(),
                    'channel_id': meeting.get('channel_id', ''),
                    'state': 'active'
                }
        except ValueError:
            pass
        
        return timers
    
    def _timer_needs_update(self, current_timer: Dict[str, Any], expected_timer: Dict[str, Any]) -> bool:
        """Check if a timer needs updating"""
        # Compare fire_at_utc times
        current_fire_at = current_timer.get('fire_at_utc')
        expected_fire_at = expected_timer.get('fire_at_utc')
        
        return current_fire_at != expected_fire_at
    
    async def _add_timer_to_system(self, timer_data: Dict[str, Any], config_spreadsheet_id: str):
        """Add a new timer to the system"""
        try:
            success = self.sheets_manager.add_timer(config_spreadsheet_id, timer_data)
            if success:
                print(f"✅ Added timer: {timer_data['id']}")
            else:
                print(f"❌ Failed to add timer: {timer_data['id']}")
        except Exception as e:
            print(f"❌ Error adding timer {timer_data['id']}: {e}")
    
    async def _update_timer_in_system(self, timer_data: Dict[str, Any], config_spreadsheet_id: str):
        """Update an existing timer in the system"""
        try:
            # For now, we'll cancel the old timer and add a new one
            # In a more sophisticated system, you'd update the existing row
            await self._cancel_timer_in_system(timer_data['id'], config_spreadsheet_id)
            await self._add_timer_to_system(timer_data, config_spreadsheet_id)
            print(f"✅ Updated timer: {timer_data['id']}")
        except Exception as e:
            print(f"❌ Error updating timer {timer_data['id']}: {e}")
    
    async def _cancel_timer_in_system(self, timer_id: str, config_spreadsheet_id: str):
        """Cancel a timer in the system"""
        try:
            success = self.sheets_manager.update_timer_state(config_spreadsheet_id, timer_id, 'cancelled')
            if success:
                print(f"✅ Cancelled timer: {timer_id}")
            else:
                print(f"❌ Failed to cancel timer: {timer_id}")
        except Exception as e:
            print(f"❌ Error cancelling timer {timer_id}: {e}")
        
                
    async def send_any_message(self, message: str, channel_id: int = None):
        """Send a message to a specific channel."""
        print(f"🔍 [send_any_message] Called with channel_id: {channel_id}, message: {message[:50]}...")
        
        # Use last_channel_id as default if no channel_id provided
        if not channel_id and self.last_channel_id:
            channel_id = self.last_channel_id
            print(f"🔍 [send_any_message] Using last_channel_id: {channel_id}")
            
        if channel_id:
            channel = self.get_channel(channel_id)
            print(f"🔍 [send_any_message] Got channel: {channel}")
            if channel:
                print(f"🔍 [send_any_message] Sending message to channel {channel_id}")
                await channel.send(message)
                print(f"✅ [send_any_message] Message sent successfully to channel {channel_id}")
            else:
                print(f"❌ [send_any_message] Could not find channel {channel_id}")
        else:
            print("❌ [send_any_message] No channel ID provided for message")

# Create the bot instance
bot = ClubExecBot()

# Make bot instance globally accessible for LangChain agent
BOT_INSTANCE = bot

# Slash command tree
@bot.tree.command(name="setup", description="Start the bot setup process")
async def setup_command(interaction: discord.Interaction):
    """Start the bot setup process."""
    if not isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message(
            "❌ This command can only be used in DMs. Please send me a private message and use `/setup` there.",
            ephemeral=True
        )
        return
        
    guild_id = str(interaction.guild.id) if interaction.guild else None
    guild_name = interaction.guild.name if interaction.guild else None
    response = await bot.setup_manager.start_setup(str(interaction.user.id), interaction.user.name, guild_id, guild_name)
    await interaction.response.send_message(response)

@bot.tree.command(name="cancel", description="Cancel the current setup process")
async def cancel_setup_command(interaction: discord.Interaction):
    """Cancel the current setup process."""
    if not isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message(
            "❌ This command can only be used in DMs. Please send me a private message and use `/cancel` there.",
            ephemeral=True
        )
        return
        
    response = bot.setup_manager.cancel_setup(str(interaction.user.id))
    await interaction.response.send_message(response)

@bot.tree.command(name="reset", description="Reset the club configuration (DM only, admin only)")
@app_commands.describe(
    server_id="Server ID (required)"
)
async def reset_config_command(interaction: discord.Interaction, server_id: str):
    """Reset the club configuration. Only the admin can perform this action."""
    # Check if this is a DM
    if not isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message(
            "❌ This command can only be used in DMs. Please send me a private message and use `/reset` there.",
            ephemeral=True
        )
        return
    
    # Validate server_id format
    if not server_id.isdigit():
        await interaction.response.send_message(
            "❌ **Invalid Server ID**\n\nPlease provide a valid Discord server ID (numbers only).\n\n**How to get Server ID:**\n1. Right-click on your server name in Discord\n2. Select 'Copy Server ID'",
            ephemeral=True
        )
        return
    
    # Verify admin access
    if not await bot.verify_dm_admin_access(interaction, server_id):
        return
    
    user_id = str(interaction.user.id)
    guild_id = server_id
    
    # Get club config from setup manager (persistent storage)
    all_guilds = bot.setup_manager.status_manager.get_all_guilds()
    club_config = all_guilds.get(guild_id)
    
    # Confirm the reset action
    response = bot.setup_manager.reset_club_configuration(guild_id, user_id, all_guilds)
    await interaction.response.send_message(response, ephemeral=True)

@bot.tree.command(name="serverconfig", description="Update server configuration (DM only, admin only)")
@app_commands.describe(
    action="Action to perform (view or update)",
    setting="Configuration setting to update",
    value="New value for the setting",
    server_id="Server ID (required)"
)
async def config_command(
    interaction: discord.Interaction,
    server_id: str,
    action: str = "view",
    setting: Optional[str] = None,
    value: Optional[str] = None
):
    """Handle configuration update commands."""
    # Check if this is a DM
    if not isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message(
            "❌ This command can only be used in DMs. Please send me a private message and use `/serverconfig` there.",
            ephemeral=True
        )
        return
    
    # Validate server_id format
    if not server_id.isdigit():
        await interaction.response.send_message(
            "❌ **Invalid Server ID**\n\nPlease provide a valid Discord server ID (numbers only).\n\n**How to get Server ID:**\n1. Right-click on your server name in Discord\n2. Select 'Copy Server ID'",
            ephemeral=True
        )
        return
    
    # Verify admin access
    if not await bot.verify_dm_admin_access(interaction, server_id):
        return
    
    user_id = str(interaction.user.id)
    guild_id = server_id
    
    # Get club config from setup manager
    all_guilds = bot.setup_manager.status_manager.get_all_guilds()
    club_config = all_guilds.get(guild_id)
    
    try:
        print(f"🔍 [SERVERCONFIG] Command called with action='{action}', setting='{setting}', value='{value}'")
        
        if action.lower() == "view":
            # Show current configuration
            config_text = f"**Current Configuration for {club_config.get('club_name', 'Unknown Club')}**\n\n"
            config_text += f"**Club Name:** {club_config.get('club_name', 'Not set')}\n"
            config_text += f"**Admin:** <@{club_config.get('admin_user_id', 'Unknown')}>\n"
            config_text += f"**Timezone:** {club_config.get('timezone', 'Not set')}\n\n"
            
            # Executive Members
            exec_members = club_config.get('exec_members', [])
            if exec_members:
                config_text += f"**Executive Team ({len(exec_members)} members):**\n"
                for member in exec_members:
                    config_text += f"• {member.get('name', 'Unknown')} - {member.get('role', 'General Team Member')} (<@{member.get('discord_id', 'Unknown')}>)\n"
                config_text += "\n"
            else:
                config_text += "**Executive Team:** No members configured\n\n"
            
            config_text += f"**Google Drive Folders:**\n"
            config_text += f"• Config Folder: `{club_config.get('config_folder_id', 'Not set')}`\n"
            config_text += f"• Monthly Folder: `{club_config.get('monthly_folder_id', 'Not set')}`\n"
            config_text += f"• Meeting Minutes Folder: `{club_config.get('meeting_minutes_folder_id', 'Not set')}`\n\n"
            config_text += f"**Discord Channels:**\n"
            config_text += f"• Task Reminders: <#{club_config.get('task_reminders_channel_id', 'Not set')}>\n"
            config_text += f"• Meeting Reminders: <#{club_config.get('meeting_reminders_channel_id', 'Not set')}>\n"
            config_text += f"• Escalations: <#{club_config.get('escalation_channel_id', 'Not set')}>\n"
            config_text += f"• General Announcements: <#{club_config.get('general_announcements_channel_id', 'Not set')}>\n"
            free_speak_channel = club_config.get('free_speak_channel_id')
            if free_speak_channel:
                config_text += f"• Free-Speak Channel: <#{free_speak_channel}>\n"
            else:
                config_text += f"• Free-Speak Channel: Not configured\n"
            config_text += "\n"
            config_text += f"**Google Sheets:**\n"
            config_text += f"• Config Sheet: `{club_config.get('config_spreadsheet_id', 'Not set')}`\n"
            monthly_sheets = club_config.get('monthly_sheets', {})
            if monthly_sheets:
                config_text += f"• Tasks Sheet: `{monthly_sheets.get('tasks', 'Not set')}`\n"
                config_text += f"• Meetings Sheet: `{monthly_sheets.get('meetings', 'Not set')}`\n"
            else:
                config_text += "• Monthly Sheets: Not set\n"
            
            await interaction.response.send_message(config_text, ephemeral=True)
            
        elif action.lower() == "update":
            if not setting or not value:
                await interaction.response.send_message(
                    "❌ **Invalid Parameters**\n\nUsage: `/config update <setting> <value>`\n\n**Available settings:**\n• `config_folder` - Google Drive config folder link\n• `monthly_folder` - Google Drive monthly folder link\n• `meeting_minutes_folder` - Google Drive meeting minutes folder link\n• `task_reminders_channel` - Discord channel ID for task reminders\n• `meeting_reminders_channel` - Discord channel ID for meeting reminders\n• `escalation_channel` - Discord channel ID for escalations\n• `general_announcements_channel` - Discord channel ID for general announcements\n• `free_speak_channel` - Discord channel ID for free-speak (optional)\n• `timezone` - Club timezone (e.g., America/New_York)\n• `exec_members` - Executive team members (JSON format)",
                    ephemeral=True
                )
                return
            
            # Handle different setting types
            updates = {}
            
            if setting.lower() == "config_folder":
                folder_id = bot.setup_manager._extract_folder_id(value)
                if not folder_id:
                    await interaction.response.send_message(
                        "❌ **Invalid Folder Link**\n\nPlease provide a valid Google Drive folder link.",
                        ephemeral=True
                    )
                    return
                
                # Verify folder access
                await interaction.response.defer(ephemeral=True)
                is_accessible, access_message = await bot.setup_manager.verify_folder_access_for_update(folder_id)
                if not is_accessible:
                    await interaction.followup.send(access_message, ephemeral=True)
                    return
                
                updates['config_folder_id'] = folder_id
                
            elif setting.lower() == "monthly_folder":
                folder_id = bot.setup_manager._extract_folder_id(value)
                if not folder_id:
                    await interaction.response.send_message(
                        "❌ **Invalid Folder Link**\n\nPlease provide a valid Google Drive folder link.",
                        ephemeral=True
                    )
                    return
                
                # Verify folder access
                await interaction.response.defer(ephemeral=True)
                is_accessible, access_message = await bot.setup_manager.verify_folder_access_for_update(folder_id)
                if not is_accessible:
                    await interaction.followup.send(access_message, ephemeral=True)
                    return
                
                updates['monthly_folder_id'] = folder_id
                
            elif setting.lower() == "meeting_minutes_folder":
                folder_id = bot.setup_manager._extract_folder_id(value)
                if not folder_id:
                    await interaction.response.send_message(
                        "❌ **Invalid Folder Link**\n\nPlease provide a valid Google Drive folder link.",
                        ephemeral=True
                    )
                    return
                
                # Verify folder access
                await interaction.response.defer(ephemeral=True)
                is_accessible, access_message = await bot.setup_manager.verify_folder_access_for_update(folder_id)
                if not is_accessible:
                    await interaction.followup.send(access_message, ephemeral=True)
                    return
                
                updates['meeting_minutes_folder_id'] = folder_id
                
            elif setting.lower() == "task_reminders_channel":
                if not value.isdigit():
                    await interaction.response.send_message(
                        "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).",
                        ephemeral=True
                    )
                    return
                updates['task_reminders_channel_id'] = value
                
            elif setting.lower() == "meeting_reminders_channel":
                if not value.isdigit():
                    await interaction.response.send_message(
                        "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).",
                        ephemeral=True
                    )
                    return
                updates['meeting_reminders_channel_id'] = value
                
            elif setting.lower() == "escalation_channel":
                if not value.isdigit():
                    await interaction.response.send_message(
                        "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).",
                        ephemeral=True
                    )
                    return
                updates['escalation_channel_id'] = value
                
            elif setting.lower() == "general_announcements_channel":
                if not value.isdigit():
                    await interaction.response.send_message(
                        "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).",
                        ephemeral=True
                    )
                    return
                updates['general_announcements_channel_id'] = value
                
            elif setting.lower() == "free_speak_channel":
                if value.lower() == "none" or value.lower() == "null" or value.lower() == "":
                    updates['free_speak_channel_id'] = None
                elif not value.isdigit():
                    await interaction.response.send_message(
                        "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only) or 'none' to remove the free-speak channel.",
                        ephemeral=True
                    )
                    return
                else:
                    updates['free_speak_channel_id'] = value
                
            elif setting.lower() == "timezone":
                # Validate timezone
                valid_timezones = [
                    'America/Edmonton', 'America/New_York', 'America/Los_Angeles', 
                    'America/Chicago', 'America/Denver', 'Europe/London', 'Europe/Paris',
                    'Asia/Tokyo', 'Asia/Shanghai', 'Australia/Sydney', 'UTC'
                ]
                
                if value not in valid_timezones:
                    await interaction.response.send_message(
                        f"❌ **Invalid Timezone**\n\nPlease choose from the available timezones:\n" + 
                        "\n".join([f"• {tz}" for tz in valid_timezones]),
                        ephemeral=True
                    )
                    return
                
                updates['timezone'] = value
                
            elif setting.lower() == "exec_members":
                # Parse JSON for exec members
                try:
                    import json
                    exec_members = json.loads(value)
                    
                    # Validate structure
                    if not isinstance(exec_members, list):
                        raise ValueError("exec_members must be a list")
                    
                    for member in exec_members:
                        if not isinstance(member, dict):
                            raise ValueError("Each member must be a dictionary")
                        if not all(key in member for key in ['name', 'discord_id', 'role']):
                            raise ValueError("Each member must have 'name', 'discord_id', and 'role' fields")
                    
                    updates['exec_members'] = exec_members
                    
                except json.JSONDecodeError:
                    example_json = '[{"name": "John Smith", "discord_id": "123456789", "role": "President"}]'
                    await interaction.response.send_message(
                        f"❌ **Invalid JSON Format**\n\nPlease provide valid JSON for executive members.\n\n**Example:**\n```json\n{example_json}\n```",
                        ephemeral=True
                    )
                    return
                except ValueError as e:
                    example_json = '[{"name": "John Smith", "discord_id": "123456789", "role": "President"}]'
                    await interaction.response.send_message(
                        f"❌ **Invalid Executive Members Format**\n\n{str(e)}\n\n**Example:**\n```json\n{example_json}\n```",
                        ephemeral=True
                    )
                    return
                
            else:
                await interaction.response.send_message(
                    "❌ **Unknown Setting**\n\n**Available settings:**\n• `config_folder` - Google Drive config folder link\n• `monthly_folder` - Google Drive monthly folder link\n• `meeting_minutes_folder` - Google Drive meeting minutes folder link\n• `task_reminders_channel` - Discord channel ID for task reminders\n• `meeting_reminders_channel` - Discord channel ID for meeting reminders\n• `escalation_channel` - Discord channel ID for escalations\n• `general_announcements_channel` - Discord channel ID for general announcements\n• `free_speak_channel` - Discord channel ID for free-speak (optional)\n• `timezone` - Club timezone (e.g., America/New_York)\n• `exec_members` - Executive team members (JSON format)",
                    ephemeral=True
                )
                return
            
            # Update the configuration using the new method
            success, message = bot.setup_manager.update_guild_configuration(guild_id, user_id, updates)
            
            if success:
                # If updating channels, also update the Google Sheets config
                if any(key.endswith('_channel_id') for key in updates.keys()):
                    try:
                        bot.sheets_manager.update_config_channels(
                            club_config.get('config_spreadsheet_id'),
                            updates.get('task_reminders_channel_id', club_config.get('task_reminders_channel_id')),
                            updates.get('meeting_reminders_channel_id', club_config.get('meeting_reminders_channel_id')),
                            updates.get('escalation_channel_id', club_config.get('escalation_channel_id')),
                            updates.get('free_speak_channel_id', club_config.get('free_speak_channel_id'))
                        )
                    except Exception as e:
                        print(f"Warning: Failed to update Google Sheets config: {e}")
                
                # Use deferred response if we haven't responded yet
                if not interaction.response.is_done():
                    await interaction.response.send_message(message, ephemeral=True)
                else:
                    await interaction.followup.send(message, ephemeral=True)
            else:
                # Use deferred response if we haven't responded yet
                if not interaction.response.is_done():
                    await interaction.response.send_message(message, ephemeral=True)
                else:
                    await interaction.followup.send(message, ephemeral=True)
                
        else:
            await interaction.response.send_message(
                "❌ **Invalid Action**\n\n**Available actions:**\n• `view` - Show current configuration\n• `update` - Update a configuration setting\n\n**Examples:**\n• `/config view`\n• `/config update config_folder https://drive.google.com/drive/folders/...`\n• `/config update task_reminders_channel 123456789012345678`",
                ephemeral=True
            )
            
    except Exception as e:
        print(f"Error in config command: {e}")
        await interaction.response.send_message(
            f"❌ **Configuration Error**\n\nAn error occurred: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="sync", description="Sync slash commands (DM only)")
async def sync_command(interaction: discord.Interaction):
    """Sync slash commands with Discord."""
    # Check if this is a DM
    if not isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message(
            "❌ This command can only be used in DMs. Please send me a private message and use `/sync` there.",
            ephemeral=True
        )
        return
    
    try:
        # Sync commands
        synced = await bot.tree.sync()
        await interaction.response.send_message(
            f"✅ **Slash Commands Synced!**\n\n**Synced {len(synced)} commands:**\n" + 
            "\n".join([f"• `/{cmd.name}` - {cmd.description}" for cmd in synced]) +
            "\n\n**Note:** It may take a few minutes for commands to appear in Discord.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ **Sync Failed**\n\nError: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="help", description="Show help information and available commands (DM only)")
@app_commands.describe(
    topic="Help topic (serverconfig, meetings, tasks, setup, or general)"
)
async def help_command(interaction: discord.Interaction, topic: str = "general"):
    """Show help information and available commands."""
    # Check if this is a DM
    if not isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message(
            "❌ This command can only be used in DMs. Please send me a private message and use `/help` there.",
            ephemeral=True
        )
        return
    
    if topic.lower() == "serverconfig":
        help_text = """**Server Configuration Help**

**View Configuration:**
• `/serverconfig server_id:123456789 view` - See all current settings

**Update Settings:**
• `/serverconfig server_id:123456789 update config_folder <link>` - Update Google Drive config folder
• `/serverconfig server_id:123456789 update monthly_folder <link>` - Update Google Drive monthly folder
• `/serverconfig server_id:123456789 update meeting_minutes_folder <link>` - Update meeting minutes folder
• `/serverconfig server_id:123456789 update task_reminders_channel <channel_id>` - Update task reminders channel
• `/serverconfig server_id:123456789 update meeting_reminders_channel <channel_id>` - Update meeting reminders channel
• `/serverconfig server_id:123456789 update escalation_channel <channel_id>` - Update escalation channel
• `/serverconfig server_id:123456789 update general_announcements_channel <channel_id>` - Update general announcements channel
• `/serverconfig server_id:123456789 update free_speak_channel <channel_id>` - Update free-speak channel (or 'none' to remove)
• `/serverconfig server_id:123456789 update timezone <timezone>` - Update club timezone
• `/serverconfig server_id:123456789 update exec_members <json>` - Update executive team members

**DM Only:** All serverconfig commands must be used in DMs
**Admin Only:** Only the server admin can use these commands
**Server ID Required:** Always include the server ID parameter"""
        
    elif topic.lower() == "meetings":
        help_text = """**Meeting Management Help**

**Natural Language Examples:**
• @AutoExec "Schedule a meeting tomorrow at 3pm"
• @AutoExec "When is our next meeting?"
• @AutoExec "Show me upcoming meetings"
• @AutoExec "Create meeting minutes for today's meeting"
• @AutoExec "Create an agenda for our weekly team meeting"

**How It Works:**
Just mention @AutoExec and describe what you want to do with meetings. The bot understands natural language and will:
• Schedule meetings with proper details
• Show you upcoming meetings
• Create meeting agendas and minutes
• Help with meeting planning and coordination

**No Slash Commands Needed!**
Everything is done through natural conversation."""
        
    elif topic.lower() == "tasks":
        help_text = """**Task Management Help**

**Natural Language Examples:**
• @AutoExec "Create a task for John due tomorrow"
• @AutoExec "Assign the budget review to Sarah due Friday"
• @AutoExec "What tasks do I have?"
• @AutoExec "Mark my presentation task as done"
• @AutoExec "Show me all my upcoming tasks"
• @AutoExec "Reschedule my meeting prep to next week"

**How It Works:**
Just mention @AutoExec and describe what you want to do with tasks. The bot understands natural language and will:
• Create tasks with proper assignments and deadlines
• Show you your personal task list
• Mark tasks as complete when you say "done"
• Reschedule tasks to new dates
• Provide task summaries and status updates

**No Slash Commands Needed!**
Everything is done through natural conversation."""
        
    elif topic.lower() == "setup":
        help_text = """**Setup Process Help**

**Getting Started:**
1. Send me a DM (not in server channels)
2. Use `/setup` command
3. Follow the prompts

**Setup Steps:**
1. **Server ID** - Your Discord server ID
2. **Club Name** - Your organization name
3. **Admin Selection** - Choose server admin
4. **Executive Team** - Add team members
5. **Google Drive** - Configure folders
6. **Google Sheets** - Create spreadsheets
7. **Discord Channels** - Configure channels

**Channel Configuration:**
• Task reminders channel
• Meeting reminders channel
• Escalation channel
• General announcements channel
• Free-speak channel (optional)

**Need to Restart?**
• Use `/cancel` during setup
• Use `/reset server_id:123456789` (admin only, DM only) to reset completed setup"""
        
    else:  # general
        help_text = """**AutoExec Bot Help**

**Admin Commands (DM Only):**
• `/setup` - Start bot setup
• `/help <topic>` - Get detailed help
• `/serverconfig server_id:123456789 view/update` - Manage settings
• `/reset server_id:123456789` - Reset configuration
• `/sync` - Sync slash commands

**Natural Language (Main Feature):**
• In server: @AutoExec "your question"
• In free-speak channel: Just type your question
• Examples: 
  - "When is our next meeting?"
  - "Create a task for John due tomorrow"
  - "What tasks do I have?"
  - "Mark my presentation task as done"
  - "Schedule a meeting for tomorrow at 3pm"

**Help Topics:**
• `/help serverconfig` - Server configuration commands
• `/help meetings` - Meeting management (natural language)
• `/help tasks` - Task management (natural language)
• `/help setup` - Setup process guide

**Important Notes:**
• All slash commands are DM-only
• Server-specific commands (`/serverconfig`, `/reset`) require server_id parameter and are admin-only
• General commands (`/help`, `/sync`) are DM-only but don't require server_id
• Natural language works in servers and free-speak channels
• The Magic: AutoExec understands natural language! Just talk to it like you would a human assistant."""
    
    await interaction.response.send_message(help_text, ephemeral=True)









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