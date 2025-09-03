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
                'config_spreadsheet_id': None,
                'monthly_sheets': None,
                'channels_configured': False
            }
            
            message = "🎉 **Welcome to the Club Exec Task Manager Bot!** 🎉\n\n"
            message += "I'll help you set up task management for your club. Let's get started!\n\n"
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
            self.setup_states[user_id]['step'] = 'sheets_initialization'
            
            message = f"✅ **Admin Set: <@{admin_discord_id}>**\n\n"
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
            print(f"Error handling admin selection: {e}")
            return "❌ Error setting admin. Please try again."
    
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
            config_spreadsheet_id = await self.sheets_manager.create_master_config_sheet(
                club_name, admin_discord_id
            )
            
            if not config_spreadsheet_id:
                return "❌ Failed to create configuration sheet. Please check your Google Drive permissions."
            
            # Store config sheet ID
            current_state['config_spreadsheet_id'] = config_spreadsheet_id
            
            # Create monthly sheets
            current_month = datetime.now().strftime("%B %Y")
            monthly_sheets = await self.sheets_manager.create_monthly_sheets(club_name, current_month)
            
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
            message += "Now I need to know which Discord channels to use:\n\n"
            message += "Please provide the channel IDs for:\n"
            message += "• Task reminders\n"
            message += "• Meeting reminders\n"
            message += "• Escalations (for overdue tasks)\n\n"
            message += "You can get channel IDs by right-clicking a channel and selecting 'Copy ID'"
            
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
            message += "**What happens next:**\n"
            message += "• I'll listen for commands in your DM and public channels\n"
            message += "• Use `/meeting set` to schedule meetings\n"
            message += "• Use `/assign` to create tasks\n"
            message += "• I'll automatically parse meeting minutes and create tasks\n"
            message += "• Task reminders and escalations will be sent automatically\n\n"
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
