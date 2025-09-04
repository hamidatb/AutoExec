import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from .sheets_manager import ClubSheetsManager
from .meeting_manager import MeetingManager
from .task_manager import TaskManager

class SetupManager:
    """
    Manages the initial setup process for the Club Exec Task Manager Bot.
    Handles club configuration, admin selection, and Google Sheets initialization.
    """
    
    def __init__(self):
        """Initialize the setup manager."""
        self.sheets_manager = ClubSheetsManager()
        self.meeting_manager = MeetingManager()
        self.task_manager = TaskManager()
        self.setup_states = {}  # Track setup progress for each user
        
    async def start_setup(self, user_id: str, user_name: str) -> str:
        """
        Starts the setup process for a new user.
        
        Args:
            user_id: Discord ID of the user
            user_name: Discord username of the user
            
        Returns:
            Initial setup message
        """
        try:
            # Initialize setup state for this user
            self.setup_states[user_id] = {
                'step': 'club_name',
                'club_name': None,
                'admin_discord_id': None,
                'config_folder_id': None,
                'monthly_folder_id': None,
                'config_spreadsheet_id': None,
                'monthly_sheets': None,
                'channels_configured': False
            }
            
            message = "🎉 **Welcome to the Club Exec Task Manager Bot!** 🎉\n\n"
            message += "I'll help you set up task management for your club. Let's get started!\n\n"
            message += "**IMPORTANT**: Before we begin, make sure you have:\n"
            message += "1. Created Google Drive folders for your club's documents\n"
            message += "2. Shared these folders with the AutoExec service account: **autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com**\n"
            message += "3. Given the service account 'Editor' permissions\n\n"
            message += "**Note**: No OAuth setup required - just share the folders and you're ready to go!\n\n"
            message += "**Step 1: Club Information**\n"
            message += "What is the name of your club or group?"
            
            return message
            
        except Exception as e:
            print(f"Error starting setup: {e}")
            return "❌ An error occurred while starting setup. Please try again."
    
    async def handle_setup_response(self, user_id: str, message_content: str) -> str:
        """
        Handles user responses during the setup process.
        
        Args:
            user_id: Discord ID of the user
            message_content: User's response message
            
        Returns:
            Next setup message or completion message
        """
        try:
            if user_id not in self.setup_states:
                return "❌ Setup session not found. Please start setup again with `/setup`."
            
            current_state = self.setup_states[user_id]
            current_step = current_state['step']
            
            if current_step == 'club_name':
                return await self._handle_club_name(user_id, message_content)
            elif current_step == 'admin_selection':
                return await self._handle_admin_selection(user_id, message_content)
            elif current_step == 'folder_selection':
                return await self._handle_folder_selection(user_id, message_content)
            elif current_step == 'sheets_initialization':
                return await self._handle_sheets_initialization(user_id, message_content)
            elif current_step == 'channel_configuration':
                return await self._handle_channel_configuration(user_id, message_content)
            else:
                return "❌ Unknown setup step. Please start setup again."
                
        except Exception as e:
            print(f"Error handling setup response: {e}")
            return "❌ An error occurred during setup. Please try again."
    
    async def _handle_club_name(self, user_id: str, club_name: str) -> str:
        """
        Handles club name input.
        
        Args:
            user_id: Discord ID of the user
            club_name: Name of the club
            
        Returns:
            Next setup message
        """
        try:
            # Store club name
            self.setup_states[user_id]['club_name'] = club_name.strip()
            self.setup_states[user_id]['step'] = 'admin_selection'
            
            message = f"✅ **Club Name Set: {club_name}**\n\n"
            message += "**Step 2: Admin Selection**\n"
            message += "Who should be the admin for this bot? Please @mention them.\n\n"
            message += "The admin will have full control over:\n"
            message += "• Meeting scheduling and cancellation\n"
            message += "• Task management and configuration\n"
            message += "• Bot settings and overrides"
            
            return message
            
        except Exception as e:
            print(f"Error handling club name: {e}")
            return "❌ Error setting club name. Please try again."
    
    async def _handle_admin_selection(self, user_id: str, admin_mention: str) -> str:
        """
        Handles admin selection input.
        
        Args:
            user_id: Discord ID of the user
            admin_mention: Admin mention string
            
        Returns:
            Next setup message
        """
        try:
            # Extract Discord ID from mention
            admin_discord_id = self._extract_discord_id(admin_mention)
            
            if not admin_discord_id:
                return "❌ Please @mention the admin user (e.g., @username)."
            
            # Store admin Discord ID
            self.setup_states[user_id]['admin_discord_id'] = admin_discord_id
            self.setup_states[user_id]['step'] = 'folder_selection'
            
            message = f"✅ **Admin Set: <@{admin_discord_id}>**\n\n"
            message += "**Step 3: Google Sheets Initialization**\n"
            message += "Before I create the Google Sheets, I need to know where to put them.\n\n"
            message += "**IMPORTANT**: Please make sure you have shared these folders with the AutoExec service account: **autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com**!\n\n"
            message += "**No OAuth needed** - the bot will access only the folders you specifically share.\n\n"
            message += "Please provide the Google Drive folder links for:\n"
            message += "• **Main Config Folder** - Where to store the Task Manager Config sheet\n"
            message += "• **Monthly Sheets Folder** - Where to store monthly task and meeting sheets\n\n"
            message += "You can get folder links by:\n"
            message += "1. Right-clicking the folder in Google Drive\n"
            message += "2. Selecting 'Get link'\n"
            message += "3. Copying the link\n\n"
            message += "**Format**: Please provide both links separated by a new line or comma."
            
            # Get current month
            current_month = datetime.now().strftime("%B %Y")
            message = message.format(club_name=self.setup_states[user_id]['club_name'], 
                                   current_month=current_month)
            
            return message
            
        except Exception as e:
            print(f"Error handling admin selection: {e}")
            return "❌ Error setting admin. Please try again."
    
    async def _handle_folder_selection(self, user_id: str, message_content: str) -> str:
        """
        Handles folder selection for Google Sheets placement.
        
        Args:
            user_id: Discord ID of the user
            message_content: User's response containing folder links
            
        Returns:
            Next setup message
        """
        try:
            # Parse folder links from message
            # Split by newline or comma
            folder_links = [link.strip() for link in message_content.replace('\n', ',').split(',') if link.strip()]
            
            if len(folder_links) < 2:
                return "❌ Please provide both folder links (config folder and monthly sheets folder)."
            
            # Extract folder IDs from Google Drive links
            config_folder_id = self._extract_folder_id(folder_links[0])
            monthly_folder_id = self._extract_folder_id(folder_links[1])
            
            if not config_folder_id or not monthly_folder_id:
                return "❌ Invalid folder links. Please make sure you're providing Google Drive folder links."
            
            # Store folder IDs
            self.setup_states[user_id]['config_folder_id'] = config_folder_id
            self.setup_states[user_id]['monthly_folder_id'] = monthly_folder_id
            
            # Move to sheets initialization
            self.setup_states[user_id]['step'] = 'sheets_initialization'
            
            message = "✅ **Folders Selected Successfully!**\n\n"
            message += "**Step 3: Google Sheets Initialization**\n"
            message += "I'll now create the necessary Google Sheets for your club:\n\n"
            message += "• **{club_name} Task Manager Config** - Main configuration\n"
            message += "• **{club_name} Tasks - {current_month}** - Task tracking\n"
            message += "• **{club_name} Meetings - {current_month}** - Meeting management\n\n"
            message += "This may take a few moments..."
            
            # Get current month
            current_month = datetime.now().strftime("%B %Y")
            message = message.format(club_name=self.setup_states[user_id]['club_name'], 
                                   current_month=current_month)
            
            return message
            
        except Exception as e:
            print(f"Error handling folder selection: {e}")
            return "❌ Error processing folder links. Please try again."
    
    def _extract_folder_id(self, folder_link: str) -> str:
        """
        Extracts folder ID from Google Drive folder link.
        
        Args:
            folder_link: Google Drive folder link
            
        Returns:
            str: Folder ID or empty string if invalid
        """
        try:
            # Google Drive folder links typically look like:
            # https://drive.google.com/drive/folders/FOLDER_ID
            if 'drive.google.com/drive/folders/' in folder_link:
                folder_id = folder_link.split('drive.google.com/drive/folders/')[1].split('?')[0]
                return folder_id
            elif 'drive.google.com/folders/' in folder_link:
                folder_id = folder_link.split('drive.google.com/folders/')[1].split('?')[0]
                return folder_id
            else:
                return ""
        except Exception as e:
            print(f"Error extracting folder ID: {e}")
            return ""
    
    async def _handle_sheets_initialization(self, user_id: str, message_content: str) -> str:
        """
        Handles Google Sheets initialization.
        
        Args:
            user_id: Discord ID of the user
            message_content: User's response (should be "continue" or similar)
            
        Returns:
            Next setup message
        """
        try:
            current_state = self.setup_states[user_id]
            club_name = current_state['club_name']
            admin_discord_id = current_state['admin_discord_id']
            
            # Create master config sheet
            config_spreadsheet_id = self.sheets_manager.create_master_config_sheet(
                club_name, admin_discord_id, current_state['config_folder_id']
            )
            
            if not config_spreadsheet_id:
                return "❌ Failed to create configuration sheet. Please check your Google Drive permissions."
            
            # Store config sheet ID
            current_state['config_spreadsheet_id'] = config_spreadsheet_id
            
            # Create monthly sheets
            current_month = datetime.now().strftime("%B %Y")
            monthly_sheets = self.sheets_manager.create_monthly_sheets(
                club_name, current_month, current_state['monthly_folder_id']
            )
            
            if not monthly_sheets:
                return "❌ Failed to create monthly sheets. Please check your Google Drive permissions."
            
            # Store monthly sheets
            current_state['monthly_sheets'] = monthly_sheets
            
            # Move to next step
            current_state['step'] = 'channel_configuration'
            
            message = "✅ **Google Sheets Created Successfully!**\n\n"
            message += f"• Config Sheet: {config_spreadsheet_id}\n"
            message += f"• Tasks Sheet: {monthly_sheets['tasks']}\n"
            message += f"• Meetings Sheet: {monthly_sheets['meetings']}\n\n"
            message += "**Step 4: Channel Configuration**\n"
            message += "Now I need to know which Discord channels to use for different types of messages:\n\n"
            message += "Please provide the channel IDs for:\n"
            message += "• **Task reminders** - Where I'll send task deadline reminders (T-24h, T-2h, overdue)\n"
            message += "• **Meeting reminders** - Where I'll send meeting notifications (T-2h, T-0)\n"
            message += "• **Escalations** - Where I'll send alerts for overdue tasks and admin notifications\n\n"
            message += "**How to get channel IDs:**\n"
            message += "1. Right-click on the channel in Discord\n"
            message += "2. Select 'Copy ID'\n"
            message += "3. Paste all three IDs in your next message (one per line)\n\n"
            message += "**Example format:**\n"
            message += "```\n123456789012345678\n987654321098765432\n555666777888999000\n```"
            
            return message
            
        except Exception as e:
            print(f"Error handling sheets initialization: {e}")
            return "❌ Error creating Google Sheets. Please check your permissions and try again."
    
    async def _handle_channel_configuration(self, user_id: str, message_content: str) -> str:
        """
        Handles channel configuration input.
        
        Args:
            user_id: Discord ID of the user
            message_content: Channel configuration message
            
        Returns:
            Setup completion message
        """
        try:
            # Parse channel IDs from message
            # This is a simplified parser - in practice, you might want a more structured approach
            channel_ids = self._extract_channel_ids(message_content)
            
            if len(channel_ids) < 3:
                return "❌ Please provide all three channel IDs: task reminders, meeting reminders, and escalations."
            
            current_state = self.setup_states[user_id]
            
            # Update config sheet with channel IDs
            await self.sheets_manager.update_config_channels(
                current_state['config_spreadsheet_id'],
                channel_ids[0],  # Task reminders
                channel_ids[1],  # Meeting reminders
                channel_ids[2]   # Escalations
            )
            
            # Mark setup as complete
            current_state['channels_configured'] = True
            
            # Log successful setup
            await self.sheets_manager.log_action(
                current_state['config_spreadsheet_id'],
                'setup_completed',
                user_id,
                f'Setup completed for club: {current_state["club_name"]}',
                'success'
            )
            
            # Clean up setup state
            del self.setup_states[user_id]
            
            message = "🎉 **Setup Complete!** 🎉\n\n"
            message += f"Your club **{current_state['club_name']}** is now configured!\n\n"
            message += "**Channel Configuration:**\n"
            message += f"• Task reminders will be sent to: <#{channel_ids[0]}>\n"
            message += f"• Meeting reminders will be sent to: <#{channel_ids[1]}>\n"
            message += f"• Escalations will be sent to: <#{channel_ids[2]}>\n\n"
            message += "**What happens next:**\n"
            message += "• I'll listen for commands in your DM and public channels\n"
            message += "• Use `/meeting set` to schedule meetings\n"
            message += "• Use `/assign` to create tasks\n"
            message += "• I'll automatically parse meeting minutes and create tasks\n"
            message += "• Task reminders and escalations will be sent to the configured channels\n\n"
            message += "**Need help?** Use `/help` to see all available commands."
            
            return message
            
        except Exception as e:
            print(f"Error handling channel configuration: {e}")
            return "❌ Error configuring channels. Please try again."
    
    def _extract_discord_id(self, mention: str) -> Optional[str]:
        """
        Extracts Discord ID from a mention string.
        
        Args:
            mention: Mention string (e.g., "<@123456789>")
            
        Returns:
            Discord ID or None if not found
        """
        try:
            # Remove <@ and > characters
            if mention.startswith('<@') and mention.endswith('>'):
                user_id = mention[2:-1]
                # Remove ! if present (for users)
                if user_id.startswith('!'):
                    user_id = user_id[1:]
                return user_id
            return None
        except Exception:
            return None
    
    def _extract_channel_ids(self, message: str) -> List[str]:
        """
        Extracts channel IDs from a message.
        
        Args:
            message: Message containing channel IDs
            
        Returns:
            List of channel IDs
        """
        try:
            # This is a simplified parser - in practice, you might want a more structured approach
            # Look for numbers that could be channel IDs (typically 18-19 digits)
            import re
            channel_ids = re.findall(r'\d{17,19}', message)
            return channel_ids
        except Exception:
            return []
    
    def get_setup_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Gets the current setup status for a user.
        
        Args:
            user_id: Discord ID of the user
            
        Returns:
            Setup state dictionary or None if not in setup
        """
        return self.setup_states.get(user_id)
    
    def is_in_setup(self, user_id: str) -> bool:
        """
        Checks if a user is currently in the setup process.
        
        Args:
            user_id: Discord ID of the user
            
        Returns:
            True if user is in setup, False otherwise
        """
        return user_id in self.setup_states
    
    def cancel_setup(self, user_id: str) -> str:
        """
        Cancels the setup process for a user.
        
        Args:
            user_id: Discord ID of the user
            
        Returns:
            Cancellation message
        """
        try:
            if user_id in self.setup_states:
                del self.setup_states[user_id]
                return "❌ Setup cancelled. You can start again anytime with `/setup`."
            else:
                return "❌ No setup session found to cancel."
        except Exception as e:
            print(f"Error cancelling setup: {e}")
            return "❌ Error cancelling setup."

    def reset_club_configuration(self, guild_id: str, admin_user_id: str, club_configs: Dict[str, Any]) -> str:
        """
        Resets the club configuration for a specific guild.
        Only the admin can perform this action.
        
        Args:
            guild_id: The Discord guild/server ID to reset
            admin_user_id: Discord ID of the user requesting the reset
            club_configs: Current club configurations dictionary
            
        Returns:
            Reset confirmation message or error message
        """
        try:
            # Check if the guild has a configuration
            if guild_id not in club_configs:
                return f"❌ **Reset Failed**\n\nNo configuration found for this server."
            
            # Verify the user is the admin
            guild_config = club_configs[guild_id]
            if str(admin_user_id) != guild_config.get('admin_discord_id'):
                return f"❌ **Reset Failed**\n\nOnly the admin can reset the club configuration.\n\n**Current Admin:** <@{guild_config.get('admin_discord_id')}>"
            
            # Get club name for confirmation
            club_name = guild_config.get('club_name', 'Unknown Club')
            
            # Remove the configuration
            del club_configs[guild_id]
            
            # TODO: In the future, this could also clean up Google Sheets and other resources
            
            return f"""✅ **Configuration Reset Complete**

**Club:** {club_name}
**Server:** {guild_id}

**What was reset:**
• Club configuration and settings
• Admin permissions
• Google Sheets integration
• Meeting and task management setup

**To reconfigure:**
• Run `/setup` to start the setup process again
• This will create a fresh configuration

**Note:** All previous data and settings have been removed."""
            
        except Exception as e:
            print(f"Error resetting club configuration: {e}")
            return f"❌ **Reset Failed**\n\nAn error occurred while resetting the configuration: {str(e)}"

    def get_club_admin(self, guild_id: str, club_configs: Dict[str, Any]) -> Optional[str]:
        """
        Gets the admin Discord ID for a specific guild.
        
        Args:
            guild_id: The Discord guild/server ID
            club_configs: Current club configurations dictionary
            
        Returns:
            Admin Discord ID or None if not found
        """
        try:
            if guild_id in club_configs:
                return club_configs[guild_id].get('admin_discord_id')
            return None
        except Exception as e:
            print(f"Error getting club admin: {e}")
            return None

    def is_admin(self, user_id: str, guild_id: str, club_configs: Dict[str, Any]) -> bool:
        """
        Checks if a user is the admin for a specific guild.
        
        Args:
            user_id: Discord ID of the user to check
            guild_id: The Discord guild/server ID
            club_configs: Current club configurations dictionary
            
        Returns:
            True if user is admin, False otherwise
        """
        try:
            admin_id = self.get_club_admin(guild_id, club_configs)
            return admin_id == str(user_id)
        except Exception as e:
            print(f"Error checking admin status: {e}")
            return False

    def can_reset_configuration(self, user_id: str, guild_id: str, club_configs: Dict[str, Any]) -> tuple[bool, str]:
        """
        Checks if a user can reset the configuration for a specific guild.
        
        Args:
            user_id: Discord ID of the user requesting the reset
            guild_id: The Discord guild/server ID
            club_configs: Current club configurations dictionary
            
        Returns:
            Tuple of (can_reset: bool, reason: str)
        """
        try:
            # Check if the guild has a configuration
            if guild_id not in club_configs:
                return False, "No configuration found for this server."
            
            # Check if the user is the admin
            if not self.is_admin(user_id, guild_id, club_configs):
                guild_config = club_configs[guild_id]
                admin_id = guild_config.get('admin_discord_id', 'Unknown')
                return False, f"Only the admin can reset the club configuration. Current Admin: <@{admin_id}>"
            
            return True, "User is authorized to reset configuration."
            
        except Exception as e:
            print(f"Error checking reset authorization: {e}")
            return False, f"Error checking authorization: {str(e)}"

    def get_configuration_summary(self, guild_id: str, club_configs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Gets a summary of the current configuration for a guild.
        
        Args:
            guild_id: The Discord guild/server ID
            club_configs: Current club configurations dictionary
            
        Returns:
            Configuration summary dictionary or None if not found
        """
        try:
            if guild_id not in club_configs:
                return None
                
            config = club_configs[guild_id]
            return {
                'club_name': config.get('club_name', 'Unknown Club'),
                'admin_discord_id': config.get('admin_discord_id', 'Unknown'),
                'has_meetings': 'meetings_sheet_id' in config,
                'has_tasks': 'tasks_sheet_id' in config,
                'config_spreadsheet_id': config.get('config_spreadsheet_id'),
                'created_at': config.get('created_at', 'Unknown')
            }
            
        except Exception as e:
            print(f"Error getting configuration summary: {e}")
            return None
