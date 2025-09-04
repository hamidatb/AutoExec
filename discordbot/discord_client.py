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
        await self.tree.sync()
        print("✅ Slash commands synced!")
        
        # Start background tasks
        asyncio.create_task(self.reminder_loop())
        asyncio.create_task(self.meeting_reminder_loop())
        
    async def on_ready(self):
        """Called when the bot successfully logs in."""
        print(f'✅ Logged in as {self.user}')
        print(f'🆔 Bot ID: {self.user.id}')
        print(f'🏠 Connected to {len(self.guilds)} guild(s)')
        
        # Load existing club configurations
        await self.load_club_configurations()
        
        # Rehydrate reminders from Timers tab
        await self.rehydrate_reminders()
        
        # Start reminder loops
        asyncio.create_task(self.reminder_loop())
        asyncio.create_task(self.meeting_reminder_loop())
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
            
        # Handle natural language commands and queries in public channels
        await self.handle_natural_language(message)
            
        # Handle task replies in public channels
        if message.mentions and self.user in message.mentions:
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
            
        content = message.content.strip()
        
        # Store channel context for LangChain responses
        self.last_channel_id = message.channel.id
        
        # Check for AutoExec commands
        if content.startswith('$AE'):
            await self.handle_autoexec_command(message)
            return
            
        # Check for meeting minutes request
        if content.startswith('$AEmm'):
            await self.handle_meeting_minutes_request(message)
            return
            
        # Check for general natural language queries
        if self.should_use_langchain(content):
            await self.handle_langchain_query(message)
            return
            
        # Special handling for DMs ONLY if no other handler was used
        # This prevents duplicate processing and welcome messages in wrong contexts
        if isinstance(message.channel, discord.DMChannel):
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
                    return run_agent_text_only(query)
                except Exception as e:
                    return f"I'm sorry, I encountered an error: {str(e)}"
            
            # Run the agent in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(executor, run_agent_sync, query)
            
            print(f"🔍 LangChain response: {response}")
            
            # Send response directly to the channel
            await message.channel.send(response)
            
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
            response += "• Use `/meeting linkminutes <url>` to link minutes documents\n"
            response += "• I'll automatically parse action items from linked minutes\n\n"
            response += "Need help? Use `/help` to see all available commands!"
            
            await message.channel.send(response)
            
        except Exception as e:
            print(f"Error in meeting minutes request: {e}")
            await message.channel.send("❌ Sorry, I encountered an error processing your request.")
            
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
                    return run_agent_text_only(query)
                except Exception as e:
                    return f"I'm sorry, I encountered an error: {str(e)}"
            
            # Run the agent in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(executor, run_agent_sync, message.content)
            
            print(f"🔍 LangChain response: {response}")
            
            # Send response directly to the channel
            await message.channel.send(response)
            
            # Check for and send any pending announcements
            if hasattr(self, 'pending_announcements') and self.pending_announcements:
                for announcement in self.pending_announcements:
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
                self.pending_announcements = []
            
        except Exception as e:
            print(f"Error in LangChain query: {e}")
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
                    return run_agent_text_only(query)
                except Exception as e:
                    return f"I'm sorry, I encountered an error: {str(e)}"
            
            # Run the agent in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(executor, run_agent_sync, message.content)
            
            # Send response directly to the DM
            await message.channel.send(response)
            
        except Exception as e:
            print(f"Error in DM general query: {e}")
            await message.channel.send("❌ Sorry, I encountered an error processing your request.")
            
    def should_use_langchain(self, content: str) -> bool:
        """Determine if a message should be processed by LangChain."""
        # Skip very short messages (likely setup responses)
        if len(content.strip()) <= 3:
            return False
            
        # Skip setup-related questions that are handled by setup manager
        content_lower = content.lower()
        setup_keywords = ['setup', 'configure', 'are you set up', 'what club', 'admin', 'permission', 'set up']
        if any(keyword in content_lower for keyword in setup_keywords):
            return False
            
        # Check for natural language patterns
        natural_language_indicators = [
            'can you', 'could you', 'please', 'help me', 'how do i',
            'what is', 'when is', 'where is', 'why', 'how',
            'i need', 'i want', 'i would like', 'tell me', 'show me',
            'what can you', 'how do you work'
        ]
        
        # Check for natural language patterns
        for indicator in natural_language_indicators:
            if indicator in content_lower:
                return True
                
        # Check for question marks (but not for very short messages)
        if '?' in content and len(content.split()) > 2:
            return True
            
        # Check for longer, conversational messages
        if len(content.split()) > 8:
            return True
            
        return False
            
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
    
    async def rehydrate_reminders(self):
        """Rehydrates reminders from the Timers tab on startup."""
        try:
            for guild_id, club_config in self.club_configs.items():
                if 'config_spreadsheet_id' in club_config:
                    # Load timers from Timers tab
                    timers = self.sheets_manager.get_timers(club_config['config_spreadsheet_id'])
                    for timer in timers:
                        if timer.get('state') == 'active':
                            # Schedule the timer
                            await self._schedule_timer(timer)
            print("✅ Reminders rehydrated from Timers tab")
        except Exception as e:
            print(f"Error rehydrating reminders: {e}")
    
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
            for guild_id, club_config in self.club_configs.items():
                if 'config_spreadsheet_id' in club_config:
                    # Get current timers
                    current_timers = self.sheets_manager.get_timers(club_config['config_spreadsheet_id'])
                    
                    # Get current tasks and meetings
                    tasks = []
                    meetings = []
                    if 'tasks_sheet_id' in club_config:
                        tasks = self.sheets_manager.get_all_tasks(club_config['tasks_sheet_id'])
                    if 'meetings_sheet_id' in club_config:
                        meetings = self.sheets_manager.get_all_meetings(club_config['meetings_sheet_id'])
                    
                    # Update timers based on current data
                    await self._update_timers_from_data(current_timers, tasks, meetings, club_config['config_spreadsheet_id'])
            
            print("✅ Timer reconciliation completed")
        except Exception as e:
            print(f"Error in timer reconciliation: {e}")
    
    async def _schedule_timer(self, timer: Dict[str, Any]):
        """Schedules a timer based on its configuration."""
        try:
            # This would integrate with a proper scheduling system
            # For now, we'll just store it in active_reminders
            timer_id = timer.get('id')
            if timer_id:
                self.active_reminders[timer_id] = timer
                print(f"Scheduled timer: {timer_id}")
        except Exception as e:
            print(f"Error scheduling timer: {e}")
    
    async def _update_timers_from_data(self, current_timers: List[Dict[str, Any]], 
                                     tasks: List[Dict[str, Any]], 
                                     meetings: List[Dict[str, Any]], 
                                     config_spreadsheet_id: str):
        """Updates timers based on current tasks and meetings data."""
        try:
            # This would implement the reconciliation logic
            # For now, we'll just log that reconciliation is happening
            print(f"Reconciling {len(current_timers)} timers with {len(tasks)} tasks and {len(meetings)} meetings")
        except Exception as e:
            print(f"Error updating timers from data: {e}")
        
    async def reminder_loop(self):
        """Background loop for sending task reminders."""
        while True:
            try:
                # Send task reminders every hour
                for guild_id, club_config in self.club_configs.items():
                    if 'tasks_sheet_id' in club_config:
                        await self.task_manager.send_task_reminders(
                            club_config['tasks_sheet_id'],
                            club_config.get('task_reminder_channel_id', 0),
                            self
                        )
                        
                await asyncio.sleep(3600)  # Wait 1 hour
                
            except Exception as e:
                print(f"Error in reminder loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
                
    async def meeting_reminder_loop(self):
        """Background loop for sending meeting reminders."""
        while True:
            try:
                # Send meeting reminders every 5 minutes
                for guild_id, club_config in self.club_configs.items():
                    if 'meetings_sheet_id' in club_config:
                        await self.meeting_manager.send_meeting_reminders(
                            club_config['meetings_sheet_id'],
                            club_config.get('meeting_reminder_channel_id', 0),
                            self
                        )
                        
                await asyncio.sleep(300)  # Wait 5 minutes
                
            except Exception as e:
                print(f"Error in meeting reminder loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
                
    async def send_any_message(self, message: str, channel_id: int = None):
        """Send a message to a specific channel."""
        # Use last_channel_id as default if no channel_id provided
        if not channel_id and self.last_channel_id:
            channel_id = self.last_channel_id
            
        if channel_id:
            channel = self.get_channel(channel_id)
            if channel:
                await channel.send(message)
            else:
                print(f"❌ Could not find channel {channel_id}")
        else:
            print("❌ No channel ID provided for message")

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

@bot.tree.command(name="reset", description="Reset the club configuration (admin only)")
async def reset_config_command(interaction: discord.Interaction):
    """Reset the club configuration. Only the admin can perform this action."""
    # Check if this is a server (guild) interaction
    if not interaction.guild:
        await interaction.response.send_message(
            "❌ This command can only be used in a server, not in DMs.",
            ephemeral=True
        )
        return
        
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    
    # Check if the bot is configured for this server
    if guild_id not in bot.club_configs:
        await interaction.response.send_message(
            "❌ **Reset Failed**\n\nNo configuration found for this server.\n\n**To get started:**\n• Run `/setup` in DMs to configure the bot",
            ephemeral=True
        )
        return
    
    # Check if the user is the admin
    if not bot.setup_manager.is_admin(user_id, guild_id, bot.club_configs):
        club_config = bot.club_configs[guild_id]
        admin_id = club_config.get('admin_discord_id', 'Unknown')
        await interaction.response.send_message(
            f"❌ **Reset Failed**\n\nOnly the admin can reset the club configuration.\n\n**Current Admin:** <@{admin_id}>\n\n**Need help?** Contact the admin or run `/setup` in DMs to reconfigure.",
            ephemeral=True
        )
        return
    
    # Confirm the reset action
    response = bot.setup_manager.reset_club_configuration(guild_id, user_id, bot.club_configs)
    await interaction.response.send_message(response, ephemeral=True)

@bot.tree.command(name="help", description="Show help information and available commands")
async def help_command(interaction: discord.Interaction):
    """Show help information and available commands."""
    help_text = """**AutoExec Bot Help**

**Setup Commands (DM only):**
• `/setup` - Start the bot setup process
• `/cancel` - Cancel the current setup process

**Server Commands:**
• `/reset` - Reset club configuration (admin only)
• `/help` - Show this help message

**Meeting Management:**
• `/meeting set` - Schedule a new meeting
• `/meeting_upcoming` - Show upcoming meetings
• `/meeting linkminutes` - Link meeting minutes

**Task Management:**
• `/assign` - Assign a task to someone
• `/tasks` - Show your assigned tasks

**Natural Language:**
• Use `$AE` followed by your question for AI-powered assistance
• Use `$AEmm` to request meeting minutes

**Setup Process:**
1. Send me a DM and use `/setup`
2. Follow the prompts to configure your club
3. Set up Google Sheets integration
4. Configure admin permissions and channels

**Need to start over?**
• Use `/cancel` during setup to restart
• Use `/reset` (admin only) to reset completed configuration

**Support:**
If you need help, contact your server admin or use the natural language features!"""
    
    await interaction.response.send_message(help_text, ephemeral=True)

@bot.tree.command(name="meeting", description="Manage meetings")
@app_commands.describe(
    action="Action to perform",
    title="Meeting title",
    start="Start time (YYYY-MM-DD HH:MM)",
    location="Meeting location or link",
    meeting_link="Meeting link (Zoom, Teams, etc.)"
)
async def meeting_command(
    interaction: discord.Interaction,
    action: str,
    title: Optional[str] = None,
    start: Optional[str] = None,
    location: Optional[str] = None,
    meeting_link: Optional[str] = None
):
    """Handle meeting-related commands."""
    # Check setup gating first
    if not await bot.check_setup_gate(interaction):
        return
    
    # Check if user is admin
    guild_id = str(interaction.guild.id)
    
    # Get club config from setup manager instead of bot.club_configs
    all_guilds = bot.setup_manager.status_manager.get_all_guilds()
    club_config = all_guilds.get(guild_id)
    
    if not club_config or not club_config.get('setup_complete', False):
        await interaction.response.send_message(
            "❌ No club configuration found for this server. Please run `/setup` first.",
            ephemeral=True
        )
        return
        
    if str(interaction.user.id) != club_config.get('admin_user_id'):
        await interaction.response.send_message(
            "❌ Only the admin can manage meetings.",
            ephemeral=True
        )
        return
        
    try:
        if action.lower() == "set":
            if not title or not start:
                await interaction.response.send_message(
                    "❌ Please provide both title and start time.",
                    ephemeral=True
                )
                return
                
            # Parse start time
            try:
                start_time = datetime.strptime(start, "%Y-%m-%d %H:%M")
                start_time = start_time.replace(tzinfo=timezone.utc)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid start time format. Use YYYY-MM-DD HH:MM",
                    ephemeral=True
                )
                return
                    
            # Create meeting data
            meeting_data = {
                'title': title,
                'start_at_utc': start_time.isoformat(),
                'end_at_utc': None,  # No end time needed
                'start_at_local': start_time.strftime("%B %d, %Y at %I:%M %p"),
                'end_at_local': None,
                'location': location or '',
                'meeting_link': meeting_link or '',
                'channel_id': str(interaction.channel.id),
                'created_by': str(interaction.user.id)
            }
            
            # Get the meetings sheet ID from the monthly_sheets structure
            meetings_sheet_id = None
            if 'monthly_sheets' in club_config and 'meetings' in club_config['monthly_sheets']:
                meetings_sheet_id = club_config['monthly_sheets']['meetings']
            elif 'meetings_sheet_id' in club_config:
                meetings_sheet_id = club_config['meetings_sheet_id']
            
            if not meetings_sheet_id:
                await interaction.response.send_message(
                    "❌ No meetings spreadsheet configured. Please run `/setup` first.",
                    ephemeral=True
                )
                return
            
            # Schedule meeting
            success = await bot.meeting_manager.schedule_meeting(
                meeting_data, 
                meetings_sheet_id
            )
            
            if success:
                message = f"✅ Meeting '{title}' scheduled successfully!\n"
                message += f"Start: {meeting_data['start_at_local']}\n"
                if location:
                    message += f"Location: {location}\n"
                if meeting_link:
                    message += f"Link: {meeting_link}\n"
                message += f"Channel: <#{interaction.channel.id}>"
                await interaction.response.send_message(message)
            else:
                await interaction.response.send_message(
                    "❌ Failed to schedule meeting. Please try again.",
                    ephemeral=True
                )
                
        elif action.lower() == "upcoming":
            # Get upcoming meetings
            upcoming = bot.meeting_manager.get_upcoming_meetings(
                club_config['meetings_sheet_id']
            )
            
            if not upcoming:
                await interaction.response.send_message("📅 No upcoming meetings scheduled.")
                return
                
            message = "📅 **Upcoming Meetings:**\n\n"
            for meeting in upcoming[:5]:  # Show next 5 meetings
                message += f"**{meeting['title']}**\n"
                message += f"🕐 {meeting.get('start_at_local', meeting['start_at_utc'])}\n"
                message += f"📍 <#{meeting.get('channel_id', '')}>\n\n"
                
            await interaction.response.send_message(message)
            
        elif action.lower() == "cancel":
            # This would require a meeting ID or selection
            await interaction.response.send_message(
                "❌ Please specify which meeting to cancel. Use the meeting ID.",
                ephemeral=True
            )
            
        elif action.lower() == "end":
            # For the end command, we need to get the minutes URL from the interaction
            # This would need to be passed as a parameter or handled differently
            await interaction.response.send_message(
                "❌ Please use `/meeting end minutes:<url>` to end a meeting with minutes.",
                ephemeral=True
            )
            
        elif action.lower() == "agenda":
            if not title:
                await interaction.response.send_message(
                    "❌ Please provide a meeting title for the agenda.",
                    ephemeral=True
                )
                return
                
            agenda = bot.meeting_manager.create_agenda_template(title)
            await interaction.response.send_message(agenda)
            
        else:
            await interaction.response.send_message(
                "❌ Unknown action. Use: set, upcoming, cancel, linkminutes, or agenda",
                ephemeral=True
            )
            
    except Exception as e:
        print(f"Error in meeting command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="meeting_upcoming", description="Show upcoming meetings")
async def meeting_upcoming_command(interaction: discord.Interaction):
    """Show upcoming meetings."""
    # Check setup gating first
    if not await bot.check_setup_gate(interaction):
        return
    
    try:
        guild_id = str(interaction.guild.id)
        club_config = bot.club_configs.get(guild_id)
        
        if not club_config or 'config_spreadsheet_id' not in club_config:
            await interaction.response.send_message(
                "❌ No club configuration found.",
                ephemeral=True
            )
            return
            
        # Get upcoming meetings from the meeting manager
        meetings = bot.meeting_manager.get_upcoming_meetings(
            club_config['config_spreadsheet_id']
        )
        
        if not meetings:
            await interaction.response.send_message(
                "📅 **No upcoming meetings found.**\n\n"
                "Use `/meeting set` to schedule a new meeting.",
                ephemeral=True
            )
            return
            
        # Format meetings for display
        response = "📅 **Upcoming Meetings:**\n\n"
        for meeting in meetings[:5]:  # Show next 5 meetings
            title = meeting.get('title', 'Untitled Meeting')
            start_time = meeting.get('start_at_local', 'Time TBD')
            location = meeting.get('location', 'Location TBD')
            meeting_link = meeting.get('meeting_link', '')
            
            response += f"**{title}**\n"
            response += f"🕐 {start_time}\n"
            response += f"📍 {location}\n"
            if meeting_link:
                response += f"🔗 {meeting_link}\n"
            response += "\n"
            
        await interaction.response.send_message(response, ephemeral=True)
        
    except Exception as e:
        print(f"Error in meeting upcoming command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred while fetching meetings. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="assign", description="Assign a task to a user")
@app_commands.describe(
    user="User to assign the task to",
    title="Task title",
    due="Due date (YYYY-MM-DD HH:MM)"
)
async def assign_command(
    interaction: discord.Interaction,
    user: discord.Member,
    title: str,
    due: Optional[str] = None
):
    """Assign a task to a user."""
    # Check setup gating first
    if not await bot.check_setup_gate(interaction):
        return
    
    # Check if user is admin
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
        
    if str(interaction.user.id) != club_config.get('admin_discord_id'):
        await interaction.response.send_message(
            "❌ Only the admin can assign tasks.",
            ephemeral=True
        )
        return
        
    try:
        # Parse due date if provided
        due_at = None
        if due:
            try:
                due_at = datetime.strptime(due, "%Y-%m-%d %H:%M")
                due_at = due_at.replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid due date format. Use YYYY-MM-DD HH:MM",
                    ephemeral=True
                )
                return
                
        # Create task data
        task_data = {
            'title': title,
            'owner_discord_id': str(user.id),
            'owner_name': user.display_name,
            'due_at': due_at,
            'status': 'open',
            'priority': 'medium',
            'source_doc': '',
            'channel_id': str(interaction.channel.id),
            'notes': f"Assigned by {interaction.user.display_name}"
        }
        
        # Add task
        success = await bot.task_manager.add_task(
            task_data, 
            club_config['tasks_sheet_id']
        )
        
        if success:
            await interaction.response.send_message(
                f"✅ Task assigned to {user.mention}!\n"
                f"**{title}**\n"
                f"Due: {due if due else 'No deadline set'}"
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to assign task. Please try again.",
                ephemeral=True
            )
            
    except Exception as e:
        print(f"Error in assign command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="summary", description="Show task summary")
@app_commands.describe(month="Month to show (e.g., 'September 2025')")
async def summary_command(interaction: discord.Interaction, month: Optional[str] = None):
    """Show task summary for a month."""
    # Check setup gating first
    if not await bot.check_setup_gate(interaction):
        return
    
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
        
    try:
        # Get all tasks
        all_tasks = bot.sheets_manager.get_all_tasks(club_config['tasks_sheet_id'])
        
        if not all_tasks:
            await interaction.response.send_message("📋 No tasks found.")
            return
            
        # Filter by month if specified
        if month:
            # Simple month filtering - could be improved
            filtered_tasks = [task for task in all_tasks if month.lower() in task.get('created_at', '').lower()]
            tasks = filtered_tasks
        else:
            tasks = all_tasks
            
        if not tasks:
            await interaction.response.send_message(f"📋 No tasks found for {month}.")
            return
            
        # Group tasks by status
        open_tasks = [t for t in tasks if t.get('status') == 'open']
        in_progress_tasks = [t for t in tasks if t.get('status') == 'in_progress']
        done_tasks = [t for t in tasks if t.get('status') == 'done']
        
        message = f"📋 **Task Summary{f' - {month}' if month else ''}**\n\n"
        
        if open_tasks:
            message += f"🟡 **Open Tasks ({len(open_tasks)})**\n"
            for task in open_tasks[:5]:  # Show first 5
                message += f"• {task.get('title', 'Unknown')} - <@{task.get('owner_discord_id', '')}>\n"
            if len(open_tasks) > 5:
                message += f"... and {len(open_tasks) - 5} more\n"
            message += "\n"
            
        if in_progress_tasks:
            message += f"🟠 **In Progress ({len(in_progress_tasks)})**\n"
            for task in in_progress_tasks[:3]:  # Show first 3
                message += f"• {task.get('title', 'Unknown')} - <@{task.get('owner_discord_id', '')}>\n"
            message += "\n"
            
        if done_tasks:
            message += f"🟢 **Completed ({len(done_tasks)})**\n"
            message += f"• {len(done_tasks)} tasks completed\n\n"
            
        await interaction.response.send_message(message)
        
    except Exception as e:
        print(f"Error in summary command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="status", description="Show tasks for a specific user")
@app_commands.describe(user="User to show tasks for")
async def status_command(interaction: discord.Interaction, user: discord.Member):
    """Show tasks for a specific user."""
    # Check setup gating first
    if not await bot.check_setup_gate(interaction):
        return
    
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
        
    try:
        # Get user tasks
        user_tasks = bot.task_manager.get_user_tasks(
            str(user.id), 
            club_config['tasks_sheet_id']
        )
        
        if not user_tasks:
            await interaction.response.send_message(f"📋 {user.mention} has no tasks assigned.")
            return
            
        # Group by status
        open_tasks = [t for t in user_tasks if t.get('status') == 'open']
        in_progress_tasks = [t for t in user_tasks if t.get('status') == 'in_progress']
        done_tasks = [t for t in user_tasks if t.get('status') == 'done']
        
        message = f"📋 **Tasks for {user.display_name}**\n\n"
        
        if open_tasks:
            message += f"🟡 **Open Tasks ({len(open_tasks)})**\n"
            for task in open_tasks:
                due_info = f" - Due: {task.get('due_at', 'No deadline')}"
                message += f"• {task.get('title', 'Unknown')}{due_info}\n"
            message += "\n"
            
        if in_progress_tasks:
            message += f"🟠 **In Progress ({len(in_progress_tasks)})**\n"
            for task in in_progress_tasks:
                due_info = f" - Due: {task.get('due_at', 'No deadline')}"
                message += f"• {task.get('title', 'Unknown')}{due_info}\n"
            message += "\n"
            
        if done_tasks:
            message += f"🟢 **Completed ({len(done_tasks)})**\n"
            message += f"• {len(done_tasks)} tasks completed\n\n"
            
        await interaction.response.send_message(message)
        
    except Exception as e:
        print(f"Error in status command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="done", description="Mark a task as complete")
@app_commands.describe(task_id="ID of the task to mark as done")
async def done_command(interaction: discord.Interaction, task_id: str):
    """Mark a task as complete."""
    # Check setup gating first
    if not await bot.check_setup_gate(interaction):
        return
    
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
        
    try:
        # Update task status
        success = await bot.task_manager.update_task_status(
            task_id, 
            'done', 
            club_config['tasks_sheet_id']
        )
        
        if success:
            await interaction.response.send_message(f"✅ Task {task_id} marked as complete!")
        else:
            await interaction.response.send_message(
                "❌ Failed to update task. Please check the task ID.",
                ephemeral=True
            )
            
    except Exception as e:
        print(f"Error in done command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="reschedule", description="Reschedule a task")
@app_commands.describe(
    task_id="ID of the task to reschedule",
    new_date="New deadline (YYYY-MM-DD HH:MM)"
)
async def reschedule_command(interaction: discord.Interaction, task_id: str, new_date: str):
    """Reschedule a task to a new deadline."""
    # Check setup gating first
    if not await bot.check_setup_gate(interaction):
        return
    
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
        
    try:
        # Parse new date
        try:
            new_deadline = datetime.strptime(new_date, "%Y-%m-%d %H:%M")
            new_deadline = new_deadline.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format. Use YYYY-MM-DD HH:MM",
                ephemeral=True
            )
            return
            
        # Reschedule task
        success = await bot.task_manager.reschedule_task(
            task_id, 
            new_deadline, 
            club_config['tasks_sheet_id']
        )
        
        if success:
            await interaction.response.send_message(
                f"✅ Task {task_id} rescheduled to {new_date}!"
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to reschedule task. Please check the task ID.",
                ephemeral=True
            )
            
    except Exception as e:
        print(f"Error in reschedule command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="subscribe", description="Subscribe to private task reminders")
async def subscribe_command(interaction: discord.Interaction):
    """Subscribe to private task reminders."""
    # This would store user preference for private DMs
    await interaction.response.send_message(
        "✅ You're now subscribed to private task reminders! "
        "You'll receive DMs for upcoming deadlines and overdue tasks.",
        ephemeral=True
    )

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