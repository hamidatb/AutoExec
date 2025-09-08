"""
Setup and configuration logic for the Club Exec Task Manager Bot.
Handles club setup, configuration management, and admin verification.
"""

import discord
from typing import Optional, Dict, Any, List


class SetupManager:
    """Handles setup and configuration logic for the bot."""
    
    def __init__(self, bot):
        self.bot = bot
        self.sheets_manager = bot.sheets_manager
        self.setup_manager = bot.setup_manager
    
    async def load_club_configurations(self):
        """Load club configurations from Google Sheets."""
        try:
            # Load configurations from setup manager
            all_guilds = self.setup_manager.status_manager.get_all_guilds()
            self.bot.club_configs = all_guilds
            print(f"✅ Loaded {len(all_guilds)} club configurations")
        except Exception as e:
            print(f"❌ Error loading club configurations: {e}")
            self.bot.club_configs = {}
    
    def _is_user_admin_of_any_guild(self, user_id: str) -> bool:
        """
        Check if a user is an admin of any guild that has been set up.
        This is used to determine if they can access admin commands.
        """
        try:
            for guild_id, config in self.bot.club_configs.items():
                if config.get('admin_user_id') == user_id:
                    return True
            return False
        except Exception as e:
            print(f"❌ Error checking admin status: {e}")
            return False
    
    def _get_user_setup_status_direct(self, user_id: str) -> str:
        """
        Get the setup status of a user directly from the setup manager.
        This bypasses the guild-specific check and looks at the user's overall setup status.
        """
        try:
            # Check if user is in any setup process
            if self.setup_manager.is_in_setup(user_id):
                return "in_progress"
            
            # Check if user is admin of any guild
            if self._is_user_admin_of_any_guild(user_id):
                return "completed"
            
            # Check if user has any guild configurations
            for guild_id, config in self.bot.club_configs.items():
                if config.get('admin_user_id') == user_id:
                    return "completed"
            
            return "not_started"
        except Exception as e:
            print(f"❌ Error getting user setup status: {e}")
            return "not_started"
    
    def is_fully_setup(self, guild_id: str = None, user_id: str = None) -> bool:
        """
        Check if a guild or user is fully set up.
        
        Args:
            guild_id: Guild ID to check (optional)
            user_id: User ID to check (optional)
            
        Returns:
            bool: True if fully set up, False otherwise
        """
        print(f"🔍 [SETUP CHECK] is_fully_setup called with guild_id={guild_id}, user_id={user_id}")
        
        try:
            if guild_id:
                # Use the same approach as the original client - check directly from setup manager
                result = self.setup_manager.is_setup_complete(guild_id)
                print(f"🔍 [SETUP CHECK] Guild {guild_id} setup complete: {result}")
                return result
            
            elif user_id:
                # Check if user is admin of any guild
                result = self._is_user_admin_of_any_guild(user_id)
                print(f"🔍 [SETUP CHECK] User {user_id} admin of any guild: {result}")
                return result
            
            # Check if any guild has completed setup
            all_guilds = self.setup_manager.status_manager.get_all_guilds()
            result = any(guild_config.get('setup_complete', False) for guild_config in all_guilds.values())
            print(f"🔍 [SETUP CHECK] Any guild setup complete: {result}")
            return result
            
        except Exception as e:
            print(f"❌ Error checking setup status: {e}")
            return False
    
    async def check_setup_gate(self, interaction: discord.Interaction) -> bool:
        """
        Check if the user has completed setup before allowing access to certain commands.
        
        Args:
            interaction: Discord interaction object
            
        Returns:
            bool: True if setup is complete, False otherwise
        """
        try:
            user_id = str(interaction.user.id)
            guild_id = str(interaction.guild.id) if interaction.guild else None
            
            # Check if user is fully set up
            if not self.is_fully_setup(user_id=user_id):
                await interaction.response.send_message(
                    "❌ **Setup Required**\n\n"
                    "You need to complete the setup process before using this command.\n\n"
                    "**To get started:**\n"
                    "1. Send me a private message\n"
                    "2. Use `/setup` to begin the setup process\n"
                    "3. Follow the guided setup steps\n\n"
                    "**Need help?** Use `/help setup` for detailed instructions.",
                    ephemeral=True
                )
                return False
            
            # Check if guild is fully set up (if applicable)
            if guild_id and not self.is_fully_setup(guild_id=guild_id):
                await interaction.response.send_message(
                    "❌ **Guild Setup Required**\n\n"
                    "This server needs to be set up before using this command.\n\n"
                    "**To set up this server:**\n"
                    "1. Send me a private message\n"
                    "2. Use `/setup` to begin the setup process\n"
                    "3. Follow the guided setup steps\n\n"
                    "**Need help?** Use `/help setup` for detailed instructions.",
                    ephemeral=True
                )
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error in setup gate check: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while checking setup status. Please try again.",
                ephemeral=True
            )
            return False
    
    async def verify_dm_admin_access(self, interaction: discord.Interaction, server_id: str) -> bool:
        """
        Verify that the user has admin access to the specified server.
        This is used for DM-only admin commands.
        
        Args:
            interaction: Discord interaction object
            server_id: Server ID to verify access for
            
        Returns:
            bool: True if user has admin access, False otherwise
        """
        try:
            user_id = str(interaction.user.id)
            
            # Check if user is admin of the specified server
            config = self.bot.club_configs.get(server_id)
            if not config:
                await interaction.response.send_message(
                    f"❌ **Server Not Found**\n\n"
                    f"No configuration found for server ID `{server_id}`.\n\n"
                    f"**Possible reasons:**\n"
                    f"• Server hasn't been set up yet\n"
                    f"• Server ID is incorrect\n"
                    f"• Server configuration was reset\n\n"
                    f"**To fix:**\n"
                    f"• Use `/setup` to set up the server\n"
                    f"• Verify the server ID is correct\n"
                    f"• Use `/help setup` for setup instructions",
                    ephemeral=True
                )
                return False
            
            # Check if user is the admin of this server
            if config.get('admin_user_id') != user_id:
                await interaction.response.send_message(
                    f"❌ **Access Denied**\n\n"
                    f"You don't have admin access to server `{server_id}`.\n\n"
                    f"**Only the server admin can use this command.**\n\n"
                    f"**To check who the admin is:**\n"
                    f"• Use `/serverconfig server_id:{server_id} view`\n"
                    f"• Contact the server admin for access\n\n"
                    f"**Need help?** Use `/help serverconfig` for more information.",
                    ephemeral=True
                )
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error verifying admin access: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while verifying admin access. Please try again.",
                ephemeral=True
            )
            return False
