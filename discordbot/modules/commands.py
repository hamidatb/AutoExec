"""
Slash command definitions for the Club Exec Task Manager Bot.
Contains all Discord slash commands and their handlers.
"""

import discord
from discord import app_commands
from typing import Optional


class SlashCommands:
    """Handles all slash command definitions and their logic."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def register_commands(self):
        """Register all slash commands with the bot's command tree."""
        
        @self.bot.tree.command(name="setup", description="Start the bot setup process")
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
            response = await self.bot.setup_manager.start_setup(str(interaction.user.id), interaction.user.name, guild_id, guild_name)
            await interaction.response.send_message(response)

        @self.bot.tree.command(name="cancel", description="Cancel the current setup process")
        async def cancel_setup_command(interaction: discord.Interaction):
            """Cancel the current setup process."""
            if not isinstance(interaction.channel, discord.DMChannel):
                await interaction.response.send_message(
                    "❌ This command can only be used in DMs. Please send me a private message and use `/cancel` there.",
                    ephemeral=True
                )
                return
                
            response = self.bot.setup_manager.cancel_setup(str(interaction.user.id))
            await interaction.response.send_message(response)

        @self.bot.tree.command(name="reset", description="Reset the club configuration (DM only, admin only)")
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
            if not await self.bot.verify_dm_admin_access(interaction, server_id):
                return
            
            user_id = str(interaction.user.id)
            guild_id = server_id
            
            # Get club config from setup manager (persistent storage)
            all_guilds = self.bot.setup_manager.status_manager.get_all_guilds()
            club_config = all_guilds.get(guild_id)
            
            # Confirm the reset action
            response = self.bot.setup_manager.reset_club_configuration(guild_id, user_id, all_guilds)
            await interaction.response.send_message(response, ephemeral=True)

        @self.bot.tree.command(name="serverconfig", description="Update server configuration (DM only, admin only)")
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
            if not await self.bot.verify_dm_admin_access(interaction, server_id):
                return
            
            user_id = str(interaction.user.id)
            guild_id = server_id
            
            # Get club config from setup manager (persistent storage)
            all_guilds = self.bot.setup_manager.status_manager.get_all_guilds()
            club_config = all_guilds.get(guild_id)
            
            if not club_config:
                await interaction.response.send_message(
                    f"❌ **No configuration found for server {guild_id}**\n\nPlease run `/setup` first to configure this server.",
                    ephemeral=True
                )
                return
            
            # Handle the configuration action
            if action.lower() == "view":
                response = self.bot.setup_manager.format_configuration_summary(guild_id, club_config)
            elif action.lower() == "update":
                if not setting or not value:
                    await interaction.response.send_message(
                        "❌ **Missing parameters for update**\n\nUsage: `/serverconfig server_id:123456789 update setting:club_name value:My Club`\n\nAvailable settings:\n• `club_name` - Club name\n• `timezone` - Timezone (e.g., 'America/New_York')\n• `task_reminder_channel` - Channel ID for task reminders\n• `meeting_reminder_channel` - Channel ID for meeting reminders\n• `escalation_channel` - Channel ID for escalations\n• `general_announcements_channel` - Channel ID for announcements\n• `free_speak_channel` - Channel ID for free-speak (optional)",
                        ephemeral=True
                    )
                    return
                
                response = self.bot.setup_manager.update_configuration_setting(
                    guild_id, user_id, setting, value, club_config
                )
            else:
                await interaction.response.send_message(
                    "❌ **Invalid action**\n\nValid actions: `view`, `update`\n\nUsage:\n• `/serverconfig server_id:123456789 view` - View current configuration\n• `/serverconfig server_id:123456789 update setting:club_name value:My Club` - Update a setting",
                    ephemeral=True
                )
                return
            
            await interaction.response.send_message(response, ephemeral=True)

        @self.bot.tree.command(name="sync", description="Sync slash commands (DM only)")
        async def sync_command(interaction: discord.Interaction):
            """Sync slash commands."""
            if not isinstance(interaction.channel, discord.DMChannel):
                await interaction.response.send_message(
                    "❌ This command can only be used in DMs. Please send me a private message and use `/sync` there.",
                    ephemeral=True
                )
                return
            
            try:
                synced = await self.bot.tree.sync()
                await interaction.response.send_message(
                    f"✅ **Slash commands synced!** {len(synced)} commands registered:\n" +
                    "\n".join([f"• `/{cmd.name}`: {cmd.description}" for cmd in synced]),
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ **Error syncing commands:** {str(e)}",
                    ephemeral=True
                )

        @self.bot.tree.command(name="help", description="Get help information (DM only)")
        @app_commands.describe(
            topic="Help topic (general, setup, serverconfig, meetings, tasks)"
        )
        async def help_command(interaction: discord.Interaction, topic: str = "general"):
            """Get help information."""
            if not isinstance(interaction.channel, discord.DMChannel):
                await interaction.response.send_message(
                    "❌ This command can only be used in DMs. Please send me a private message and use `/help` there.",
                    ephemeral=True
                )
                return
            
            # Get help text based on topic
            help_text = self._get_help_text(topic)
            await interaction.response.send_message(help_text, ephemeral=True)
    
    def _get_help_text(self, topic: str) -> str:
        """Get help text for a specific topic."""
        if topic.lower() == "setup":
            return """**AutoExec Bot Setup Guide**

**Step 1: Invite Bot**
• Use the invite link to add AutoExec to your server
• Grant necessary permissions (Send Messages, Use Slash Commands, etc.)

**Step 2: Start Setup (DM Only)**
• Send a private message to AutoExec
• Use `/setup` command
• Follow the guided setup process

**Step 3: Configuration**
• Club name and timezone
• Admin selection
• Channel configuration:
  • Task reminder channel
  • Meeting reminder channel
  • Escalation channel
  • General announcements channel
  • Free-speak channel (optional)

**Step 4: Google Sheets Setup**
• Bot creates master configuration sheet
• Bot creates monthly task/meeting sheets
• Bot configures channels and permissions

**Step 5: Ready to Use**
• Bot listens for commands
• Automatic reminders start working
• Full task management available

**Need Help?**
• Use `/help <topic>` for specific help
• Use `/cancel` during setup to restart
• Use `/reset server_id:123456789` (admin only) to reset completed setup"""
        
        elif topic.lower() == "serverconfig":
            return """**Server Configuration Commands**

**View Configuration:**
• `/serverconfig server_id:123456789 view`
• Shows current server settings

**Update Configuration:**
• `/serverconfig server_id:123456789 update setting:club_name value:My Club`
• Updates a specific setting

**Available Settings:**
• `club_name` - Club name
• `timezone` - Timezone (e.g., 'America/New_York')
• `task_reminder_channel` - Channel ID for task reminders
• `meeting_reminder_channel` - Channel ID for meeting reminders
• `escalation_channel` - Channel ID for escalations
• `general_announcements_channel` - Channel ID for announcements
• `free_speak_channel` - Channel ID for free-speak (optional)

**Important Notes:**
• All commands are DM-only
• Requires server_id parameter
• Admin-only commands
• Use `/help setup` for setup process"""
        
        elif topic.lower() == "meetings":
            return """**Meeting Management (Natural Language)**

**Schedule Meetings:**
• "Schedule a meeting for tomorrow at 3pm"
• "Create a meeting called Weekly Standup for next Monday"
• "Set up a meeting with the team for Friday afternoon"

**Manage Meetings:**
• "When is our next meeting?"
• "What meetings do we have this week?"
• "Cancel the meeting on Friday"
• "Update the meeting time to 2pm"

**Meeting Minutes:**
• "Get minutes from last meeting"
• "Show me the action items from the Weekly Standup"
• "What was discussed in the budget meeting?"

**Examples:**
• "Schedule a board meeting for next Tuesday at 2pm"
• "What meetings are coming up?"
• "Cancel the team meeting on Friday"
• "Update the budget meeting to 3pm"

**Note:** All meeting commands work through natural language in servers or free-speak channels."""
        
        elif topic.lower() == "tasks":
            return """**Task Management (Natural Language)**

**Create Tasks:**
• "Create a task for John to finish the report due tomorrow"
• "Assign Sarah the presentation task due next Friday"
• "Give me a task to review the budget due Monday"

**Manage Tasks:**
• "What tasks do I have?"
• "Show me all open tasks"
• "What tasks are due this week?"
• "Mark my presentation task as done"
• "Complete task 123"

**Task Updates:**
• "Reschedule my report task to next Monday"
• "Change the deadline for task 456 to Friday"
• "Update task 789 to high priority"

**Examples:**
• "Create a task for John to finish the report due tomorrow"
• "What tasks do I have due this week?"
• "Mark my presentation task as complete"
• "Reschedule the budget review to next Monday"

**Note:** All task commands work through natural language in servers or free-speak channels."""
        
        else:  # general
            return """**AutoExec Bot Help**

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
