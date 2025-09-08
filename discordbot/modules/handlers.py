"""
Message and interaction handlers for the Club Exec Task Manager Bot.
Handles natural language processing, DM setup, and various message types.
"""

import discord
import asyncio
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from googledrive.sheets_manager import ClubSheetsManager
from googledrive.meeting_manager import MeetingManager
from googledrive.task_manager import TaskManager
from googledrive.setup_manager import SetupManager
from googledrive.minutes_parser import MinutesParser
from googledrive.timer_scheduler import TimerScheduler
from ae_langchain.main_agent import run_agent
from config.config import Config


class MessageHandlers:
    """Handles various types of messages and interactions."""
    
    def __init__(self, bot):
        self.bot = bot
        self.sheets_manager = bot.sheets_manager
        self.meeting_manager = bot.meeting_manager
        self.task_manager = bot.task_manager
        self.setup_manager = bot.setup_manager
        self.minutes_parser = bot.minutes_parser
        self.timer_scheduler = bot.timer_scheduler
    
    async def handle_natural_language(self, message: discord.Message):
        """Handle natural language messages using LangChain agent."""
        try:
            # Set Discord context for the agent
            from ae_langchain.tools.context_manager import set_discord_context
            set_discord_context(
                guild_id=str(message.guild.id) if message.guild else None,
                channel_id=str(message.channel.id),
                user_id=str(message.author.id)
            )
            
            # Process with LangChain agent using the sync wrapper
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
            
            response = await loop.run_in_executor(None, run_agent_sync, message.content)
            
            if response and response.strip():
                # Send response back to the channel
                await message.channel.send(response)
            else:
                await message.channel.send("I'm not sure how to help with that. Try asking me about meetings, tasks, or use `/help` for more information.")
                
        except Exception as e:
            print(f"❌ Error in natural language processing: {e}")
            await message.channel.send("Sorry, I encountered an error processing your request. Please try again.")
    
    async def handle_autoexec_command(self, message: discord.Message):
        """Handle $AE commands using LangChain agent."""
        try:
            # Extract the command after $AE
            command = message.content[3:].strip()  # Remove "$AE" prefix
            
            if not command:
                await message.channel.send("Please provide a command after `$AE`. For example: `$AE create a task for John due tomorrow`")
                return
            
            # Set Discord context for the agent
            from ae_langchain.tools.context_manager import set_discord_context
            set_discord_context(
                guild_id=str(message.guild.id) if message.guild else None,
                channel_id=str(message.channel.id),
                user_id=str(message.author.id)
            )
            
            # Process with LangChain agent using the sync wrapper
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
            
            response = await loop.run_in_executor(None, run_agent_sync, command)
            
            if response and response.strip():
                await message.channel.send(response)
            else:
                await message.channel.send("I'm not sure how to help with that command. Try asking me about meetings, tasks, or use `/help` for more information.")
                
        except Exception as e:
            print(f"❌ Error in $AE command processing: {e}")
            await message.channel.send("Sorry, I encountered an error processing your command. Please try again.")
    
    async def handle_meeting_minutes_request(self, message: discord.Message):
        """Handle $AEmm meeting minutes requests."""
        try:
            # Extract the meeting ID or title from the message
            content = message.content[5:].strip()  # Remove "$AEmm" prefix
            
            if not content:
                await message.channel.send("Please provide a meeting ID or title after `$AEmm`. For example: `$AEmm 123` or `$AEmm Weekly Meeting`")
                return
            
            # Set Discord context for the agent
            from ae_langchain.tools.context_manager import set_discord_context
            set_discord_context(
                guild_id=str(message.guild.id) if message.guild else None,
                channel_id=str(message.channel.id),
                user_id=str(message.author.id)
            )
            
            # Process with LangChain agent using the sync wrapper
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
            
            response = await loop.run_in_executor(None, run_agent_sync, f"get meeting minutes for: {content}")
            
            if response and response.strip():
                await message.channel.send(response)
            else:
                await message.channel.send("I couldn't find meeting minutes for that meeting. Please check the meeting ID or title and try again.")
                
        except Exception as e:
            print(f"❌ Error in meeting minutes request: {e}")
            await message.channel.send("Sorry, I encountered an error processing your request. Please try again.")
    
    async def handle_config_command_usage(self, message: discord.Message):
        """Handle when users try to use /config as a regular message instead of slash command."""
        await message.channel.send(
            "❌ **Configuration commands are slash commands only!**\n\n"
            "Please use one of these slash commands:\n"
            "• `/setup` - Start bot setup (DM only)\n"
            "• `/serverconfig` - Manage server settings (DM only)\n"
            "• `/reset` - Reset configuration (DM only, admin only)\n"
            "• `/help` - Get help information (DM only)\n\n"
            "**Note:** All configuration commands must be used in DMs (private messages) with the bot."
        )
    
    async def handle_langchain_query(self, message: discord.Message):
        """Handle general natural language queries using LangChain."""
        try:
            # Set Discord context for the agent
            from ae_langchain.tools.context_manager import set_discord_context
            set_discord_context(
                guild_id=str(message.guild.id) if message.guild else None,
                channel_id=str(message.channel.id),
                user_id=str(message.author.id)
            )
            
            # Process with LangChain agent using the sync wrapper
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
            
            response = await loop.run_in_executor(None, run_agent_sync, message.content)
            
            if response and response.strip():
                await message.channel.send(response)
            else:
                await message.channel.send("I'm not sure how to help with that. Try asking me about meetings, tasks, or use `/help` for more information.")
                
        except Exception as e:
            print(f"❌ Error in LangChain query processing: {e}")
            await message.channel.send("Sorry, I encountered an error processing your request. Please try again.")
    
    async def handle_dm_general_query(self, message: discord.Message):
        """Handle general queries in DMs that don't match other patterns."""
        try:
            # Set Discord context for the agent
            from ae_langchain.tools.context_manager import set_discord_context
            set_discord_context(
                guild_id=None,  # DM context
                channel_id=str(message.channel.id),
                user_id=str(message.author.id)
            )
            
            # Process with LangChain agent using the sync wrapper
            loop = asyncio.get_event_loop()
            
            def run_agent_sync(query):
                from ae_langchain.main_agent import run_agent_text_only
                try:
                    # For DMs, pass user_id to handle multiple server scenario
                    user_id = str(message.author.id)
                    return run_agent_text_only(query, guild_id=None, user_id=user_id)
                except Exception as e:
                    return f"I'm sorry, I encountered an error: {str(e)}"
            
            response = await loop.run_in_executor(None, run_agent_sync, message.content)
            
            if response and response.strip():
                await message.channel.send(response)
            else:
                await message.channel.send("I'm not sure how to help with that. Try asking me about meetings, tasks, or use `/help` for more information.")
                
        except Exception as e:
            print(f"❌ Error in DM general query processing: {e}")
            await message.channel.send("Sorry, I encountered an error processing your request. Please try again.")
    
    def should_use_langchain(self, content: str) -> bool:
        """Determine if a message should be processed by LangChain."""
        # Skip if it's a command or very short
        if len(content.strip()) < 3:
            return False
            
        # Skip if it's a bot command
        if content.startswith(('!', '/', '$')):
            return False
            
        # Skip if it's just mentions or emojis
        if re.match(r'^[<@!]*[0-9]+>?\s*$', content.strip()):
            return False
            
        return True
    
    async def handle_dm_setup(self, message: discord.Message) -> bool:
        """Handle setup process in DMs.
        
        Returns:
            bool: True if the message was handled by setup, False otherwise
        """
        try:
            # Check if user is in setup process
            if self.setup_manager.is_in_setup(str(message.author.id)):
                # Handle setup step
                response = await self.setup_manager.handle_setup_response(
                    str(message.author.id), 
                    message.content
                )
                
                if response:
                    await message.channel.send(response)
                    return True
            
            # Check if message contains setup-related keywords
            setup_keywords = ['setup', 'configure', 'config', 'start', 'begin']
            if any(keyword in message.content.lower() for keyword in setup_keywords):
                # Only start setup if user is not already fully set up
                if not self.bot.setup_manager_bot.is_fully_setup(user_id=str(message.author.id)):
                    # Start setup process
                    guild_id = None  # DM context
                    guild_name = None
                    response = await self.setup_manager.start_setup(
                        str(message.author.id), 
                        message.author.name, 
                        guild_id, 
                        guild_name
                    )
                    await message.channel.send(response)
                    return True
                else:
                    # User is already set up, don't start setup again
                    await message.channel.send(
                        "✅ **Already Set Up!**\n\n"
                        "You're already fully set up and ready to use all bot features!\n\n"
                        "**Available commands:**\n"
                        "• Ask me about meetings, tasks, or announcements\n"
                        "• Use `/help` to see all available commands\n"
                        "• I can help with club management and organization"
                    )
                    return True
                
        except Exception as e:
            print(f"❌ Error in DM setup handling: {e}")
            await message.channel.send("Sorry, I encountered an error. Please try again.")
            
        return False
    
    async def handle_task_reply(self, message: discord.Message):
        """Handle user replies to task reminders."""
        try:
            # Check if this is a reply to a task reminder
            if message.reference and message.reference.message_id:
                # Get the original message
                try:
                    original_message = await message.channel.fetch_message(message.reference.message_id)
                    
                    # Check if it's a task reminder message
                    if "task reminder" in original_message.content.lower() or "due" in original_message.content.lower():
                        # Process the reply with LangChain
                        from ae_langchain.tools.context_manager import set_discord_context
                        set_discord_context(
                            guild_id=str(message.guild.id) if message.guild else None,
                            channel_id=str(message.channel.id),
                            user_id=str(message.author.id)
                        )
                        
                        # Process with LangChain agent using the sync wrapper
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
                        
                        response = await loop.run_in_executor(None, run_agent_sync, f"User replied to task reminder: {message.content}")
                        
                        if response and response.strip():
                            await message.channel.send(response)
                            
                except discord.NotFound:
                    pass  # Original message not found, ignore
                    
        except Exception as e:
            print(f"❌ Error in task reply handling: {e}")
            # Don't send error message for task replies to avoid spam
