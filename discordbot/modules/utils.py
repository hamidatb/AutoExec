"""
Utility functions for the Club Exec Task Manager Bot.
Contains helper functions and utilities used across the bot.
"""

import discord
from typing import Optional, Dict, Any, List


class BotUtils:
    """Utility functions for the bot."""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def send_any_message(self, message: str, channel_id: int = None):
        """Send a message to a specific channel."""
        try:
            if channel_id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(message)
                    print(f"✅ [send_any_message] Sent message to channel {channel_id}")
                else:
                    print(f"❌ [send_any_message] Channel {channel_id} not found")
            else:
                print("❌ [send_any_message] No channel ID provided for message")
        except Exception as e:
            print(f"❌ [send_any_message] Error sending message: {e}")
    
    def get_guild_config(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific guild."""
        try:
            return self.bot.club_configs.get(guild_id)
        except Exception as e:
            print(f"❌ Error getting guild config for {guild_id}: {e}")
            return None
    
    def get_user_guilds(self, user_id: str) -> List[str]:
        """Get all guild IDs where the user is an admin."""
        try:
            user_guilds = []
            for guild_id, config in self.bot.club_configs.items():
                if config.get('admin_user_id') == user_id:
                    user_guilds.append(guild_id)
            return user_guilds
        except Exception as e:
            print(f"❌ Error getting user guilds for {user_id}: {e}")
            return []
    
    def is_user_admin(self, user_id: str, guild_id: str = None) -> bool:
        """Check if a user is an admin of a specific guild or any guild."""
        try:
            if guild_id:
                config = self.bot.club_configs.get(guild_id)
                return config and config.get('admin_user_id') == user_id
            else:
                return any(config.get('admin_user_id') == user_id 
                          for config in self.bot.club_configs.values())
        except Exception as e:
            print(f"❌ Error checking admin status for {user_id}: {e}")
            return False
    
    def get_channel_name(self, channel_id: int) -> Optional[str]:
        """Get the name of a channel by its ID."""
        try:
            channel = self.bot.get_channel(channel_id)
            return channel.name if channel else None
        except Exception as e:
            print(f"❌ Error getting channel name for {channel_id}: {e}")
            return None
    
    def get_guild_name(self, guild_id: int) -> Optional[str]:
        """Get the name of a guild by its ID."""
        try:
            guild = self.bot.get_guild(guild_id)
            return guild.name if guild else None
        except Exception as e:
            print(f"❌ Error getting guild name for {guild_id}: {e}")
            return None
    
    def format_user_mention(self, user_id: str) -> str:
        """Format a user ID as a Discord mention."""
        try:
            return f"<@{user_id}>"
        except Exception as e:
            print(f"❌ Error formatting user mention for {user_id}: {e}")
            return f"User {user_id}"
    
    def format_channel_mention(self, channel_id: int) -> str:
        """Format a channel ID as a Discord mention."""
        try:
            return f"<#{channel_id}>"
        except Exception as e:
            print(f"❌ Error formatting channel mention for {channel_id}: {e}")
            return f"Channel {channel_id}"
    
    def format_guild_mention(self, guild_id: int) -> str:
        """Format a guild ID as a Discord mention."""
        try:
            guild = self.bot.get_guild(guild_id)
            return guild.name if guild else f"Guild {guild_id}"
        except Exception as e:
            print(f"❌ Error formatting guild mention for {guild_id}: {e}")
            return f"Guild {guild_id}"
    
    def sanitize_message_content(self, content: str) -> str:
        """Sanitize message content for safe display."""
        try:
            # Remove potential Discord formatting that could cause issues
            content = content.replace('@everyone', '@\u200beveryone')
            content = content.replace('@here', '@\u200bhere')
            return content
        except Exception as e:
            print(f"❌ Error sanitizing message content: {e}")
            return content
    
    def truncate_message(self, content: str, max_length: int = 2000) -> str:
        """Truncate a message to fit Discord's character limit."""
        try:
            if len(content) <= max_length:
                return content
            
            # Truncate and add ellipsis
            truncated = content[:max_length - 3] + "..."
            return truncated
        except Exception as e:
            print(f"❌ Error truncating message: {e}")
            return content[:max_length] if len(content) > max_length else content
    
    def format_timestamp(self, timestamp: str) -> str:
        """Format a timestamp for display."""
        try:
            from datetime import datetime
            from dateutil import parser
            
            if isinstance(timestamp, str):
                dt = parser.parse(timestamp)
            else:
                dt = timestamp
            
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"❌ Error formatting timestamp {timestamp}: {e}")
            return str(timestamp)
    
    def format_duration(self, seconds: int) -> str:
        """Format a duration in seconds to a human-readable string."""
        try:
            if seconds < 60:
                return f"{seconds} seconds"
            elif seconds < 3600:
                minutes = seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''}"
            elif seconds < 86400:
                hours = seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                days = seconds // 86400
                return f"{days} day{'s' if days != 1 else ''}"
        except Exception as e:
            print(f"❌ Error formatting duration {seconds}: {e}")
            return f"{seconds} seconds"
    
    def get_embed_color(self, status: str) -> int:
        """Get a Discord embed color based on status."""
        try:
            color_map = {
                'success': 0x00ff00,  # Green
                'error': 0xff0000,    # Red
                'warning': 0xffff00,  # Yellow
                'info': 0x0099ff,     # Blue
                'default': 0x7289da   # Discord blurple
            }
            return color_map.get(status.lower(), color_map['default'])
        except Exception as e:
            print(f"❌ Error getting embed color for {status}: {e}")
            return 0x7289da  # Default Discord blurple
    
    def create_embed(self, title: str, description: str = "", color: str = "default") -> discord.Embed:
        """Create a Discord embed with consistent styling."""
        try:
            embed = discord.Embed(
                title=title,
                description=description,
                color=self.get_embed_color(color)
            )
            embed.set_footer(text="AutoExec Bot")
            return embed
        except Exception as e:
            print(f"❌ Error creating embed: {e}")
            # Return a simple embed as fallback
            return discord.Embed(title=title, description=description)
    
    def is_valid_discord_id(self, id_str: str) -> bool:
        """Check if a string is a valid Discord ID."""
        try:
            # Discord IDs are 17-19 digit numbers
            return id_str.isdigit() and 17 <= len(id_str) <= 19
        except Exception as e:
            print(f"❌ Error validating Discord ID {id_str}: {e}")
            return False
    
    def extract_mentions(self, content: str) -> List[str]:
        """Extract user mentions from message content."""
        try:
            import re
            # Pattern for Discord user mentions: <@!123456789012345678>
            mention_pattern = r'<@!?(\d+)>'
            mentions = re.findall(mention_pattern, content)
            return mentions
        except Exception as e:
            print(f"❌ Error extracting mentions from {content}: {e}")
            return []
    
    def extract_channel_mentions(self, content: str) -> List[str]:
        """Extract channel mentions from message content."""
        try:
            import re
            # Pattern for Discord channel mentions: <#123456789012345678>
            mention_pattern = r'<#(\d+)>'
            mentions = re.findall(mention_pattern, content)
            return mentions
        except Exception as e:
            print(f"❌ Error extracting channel mentions from {content}: {e}")
            return []
    
    def log_activity(self, activity: str, user_id: str = None, guild_id: str = None):
        """Log bot activity for debugging and monitoring."""
        try:
            timestamp = self.format_timestamp(datetime.now().isoformat())
            log_entry = f"[{timestamp}] {activity}"
            
            if user_id:
                log_entry += f" | User: {user_id}"
            if guild_id:
                log_entry += f" | Guild: {guild_id}"
            
            print(log_entry)
        except Exception as e:
            print(f"❌ Error logging activity: {e}")
    
    def get_bot_status(self) -> Dict[str, Any]:
        """Get current bot status information."""
        try:
            return {
                'guilds_connected': len(self.bot.guilds),
                'clubs_configured': len(self.bot.club_configs),
                'active_reminders': len(self.bot.active_reminders),
                'setup_sessions': len(self.bot.setup_sessions),
                'uptime': self.bot.uptime if hasattr(self.bot, 'uptime') else 'Unknown'
            }
        except Exception as e:
            print(f"❌ Error getting bot status: {e}")
            return {}
