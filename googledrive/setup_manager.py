import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from .sheets_manager import ClubSheetsManager
from .guild_setup_manager import GuildSetupStatusManager
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
        self.status_manager = GuildSetupStatusManager()
        self.setup_states = {}  # Track setup progress for each user
    
    def is_setup_complete(self, guild_id: str) -> bool:
        """
        Check if setup is complete for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if setup is complete, False otherwise
        """
        return self.status_manager.is_setup_complete(guild_id)
    
    def get_guild_config(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """
        Get guild configuration.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Guild configuration dict or None if not found
        """
        return self.status_manager.get_guild_config(guild_id)
    
    def can_modify_config(self, user_id: str, guild_id: str) -> bool:
        """
        Check if a user can modify a guild's configuration.
        
        Args:
            user_id: User ID requesting to modify
            guild_id: Guild ID
            
        Returns:
            True if user can modify, False otherwise
        """
        return self.status_manager.can_modify_config(user_id, guild_id)
        
    async def start_setup(self, user_id: str, user_name: str, guild_id: str = None, guild_name: str = None) -> str:
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
                'guild_id': guild_id,
                'guild_name': guild_name,
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
            print(f"🔍 [SETUP] Handling setup response for user {user_id}")
            print(f"🔍 [SETUP] Message content: {message_content}")
            
            if user_id not in self.setup_states:
                print(f"❌ [SETUP ERROR] No setup session found for user {user_id}")
                return "❌ Setup session not found. Please start setup again with `/setup`."
            
            current_state = self.setup_states[user_id]
            current_step = current_state['step']
            print(f"🔍 [SETUP] Current step: {current_step}")
            
            if current_step == 'club_name':
                return await self._handle_club_name(user_id, message_content)
            elif current_step == 'admin_selection':
                return await self._handle_admin_selection(user_id, message_content)
            elif current_step == 'folder_selection':
                return await self._handle_folder_selection(user_id, message_content)
            elif current_step == 'sheets_initialization':
                return await self._handle_sheets_initialization(user_id, message_content)
            elif current_step == 'task_reminders_channel':
                return await self._handle_task_reminders_channel(user_id, message_content)
            elif current_step == 'meeting_reminders_channel':
                return await self._handle_meeting_reminders_channel(user_id, message_content)
            elif current_step == 'escalation_channel':
                return await self._handle_escalation_channel(user_id, message_content)
            else:
                print(f"❌ [SETUP ERROR] Unknown setup step: {current_step}")
                return "❌ Unknown setup step. Please start setup again."
                
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error handling setup response: {e}")
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
            print(f"🔍 [SETUP] Processing folder selection for user {user_id}")
            print(f"🔍 [SETUP] Message content: {message_content}")
            
            # Parse folder links from message
            # Split by newline or comma
            folder_links = [link.strip() for link in message_content.replace('\n', ',').split(',') if link.strip()]
            print(f"🔍 [SETUP] Extracted {len(folder_links)} folder links")
            
            if len(folder_links) < 2:
                return "❌ Please provide both folder links (config folder and monthly sheets folder)."
            
            # Extract folder IDs from Google Drive links
            config_folder_id = self._extract_folder_id(folder_links[0])
            monthly_folder_id = self._extract_folder_id(folder_links[1])
            
            print(f"🔍 [SETUP] Extracted folder IDs - Config: {config_folder_id}, Monthly: {monthly_folder_id}")
            
            if not config_folder_id or not monthly_folder_id:
                return "❌ Invalid folder links. Please make sure you're providing Google Drive folder links."
            
            # Store folder IDs
            self.setup_states[user_id]['config_folder_id'] = config_folder_id
            self.setup_states[user_id]['monthly_folder_id'] = monthly_folder_id
            
            # Immediately verify folder access instead of waiting for user input
            print(f"🔍 [SETUP] Starting immediate folder verification for user {user_id}")
            
            # Test access to config folder
            try:
                config_access = await self._verify_folder_access(config_folder_id)
                print(f"🔍 [SETUP] Config folder access result: {config_access}")
            except Exception as e:
                print(f"❌ [SETUP ERROR] Config folder verification failed: {e}")
                config_access = False
            
            # Test access to monthly folder
            try:
                monthly_access = await self._verify_folder_access(monthly_folder_id)
                print(f"🔍 [SETUP] Monthly folder access result: {monthly_access}")
            except Exception as e:
                print(f"❌ [SETUP ERROR] Monthly folder verification failed: {e}")
                monthly_access = False
            
            # Check results and proceed accordingly
            if not config_access:
                return f"❌ **Config Folder Access Failed**\n\nI cannot access the config folder `{config_folder_id}`.\n\n**Please check:**\n• The folder exists and is shared with the service account\n• The service account has 'Editor' permissions\n• The folder ID is correct\n\n**Service Account:** `autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com`"
            
            if not monthly_access:
                return f"❌ **Monthly Folder Access Failed**\n\nI cannot access the monthly folder `{monthly_folder_id}`.\n\n**Please check:**\n• The folder exists and is shared with the service account\n• The service account has 'Editor' permissions\n• The folder ID is correct\n\n**Service Account:** `autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com`"
            
            # Both folders accessible, proceed directly to sheets initialization
            print(f"🔍 [SETUP] Both folders verified, proceeding to sheets initialization")
            
            # Send initial message about folder verification
            initial_message = "✅ **Folders Selected and Verified Successfully!**\n\n"
            initial_message += f"• Config Folder ID: `{config_folder_id}` ✅ Accessible\n"
            initial_message += f"• Monthly Folder ID: `{monthly_folder_id}` ✅ Accessible\n\n"
            initial_message += "**Step 3: Google Sheets Initialization**\n"
            initial_message += "I'll now create the necessary Google Sheets for your club:\n\n"
            initial_message += f"• **{self.setup_states[user_id]['club_name']} Task Manager Config** - Main configuration\n"
            initial_message += f"• **{self.setup_states[user_id]['club_name']} Tasks - {datetime.now().strftime('%B %Y')}** - Task tracking\n"
            initial_message += f"• **{self.setup_states[user_id]['club_name']} Meetings - {datetime.now().strftime('%B %Y')}** - Meeting management\n\n"
            initial_message += "This may take a few moments..."
            
            # Now immediately proceed to sheets initialization
            sheets_result = await self._handle_sheets_initialization(user_id, "")
            
            # Combine the initial message with the sheets result
            return initial_message + "\n\n" + sheets_result
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error handling folder selection: {e}")
            return "❌ Error processing folder links. Please try again."
    
    async def _verify_folder_access(self, folder_id: str) -> bool:
        """
        Verifies that the bot can access a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            True if accessible, False otherwise
        """
        try:
            print(f"🔍 [SETUP] Testing access to folder: {folder_id}")
            
            # Try to get folder metadata
            folder = self.sheets_manager.drive_service.files().get(
                fileId=folder_id,
                fields='id,name,permissions'
            ).execute()
            
            print(f"🔍 [SETUP] Folder metadata retrieved: {folder.get('name', 'Unknown')}")
            
            # Check if we have write permissions by trying to create a test file
            test_file_metadata = {
                'name': f'access_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                'parents': [folder_id]
            }
            
            # Create a simple text file using MediaIoBaseUpload
            from googleapiclient.http import MediaIoBaseUpload
            import io
            
            # Create a file-like object with the test content
            test_content = 'Test access file - can be deleted'
            media_body = MediaIoBaseUpload(
                io.BytesIO(test_content.encode('utf-8')),
                mimetype='text/plain',
                resumable=False
            )
            
            test_file = self.sheets_manager.drive_service.files().create(
                body=test_file_metadata,
                media_body=media_body
            ).execute()
            
            print(f"🔍 [SETUP] Test file created successfully: {test_file.get('id')}")
            
            # Clean up test file
            self.sheets_manager.drive_service.files().delete(fileId=test_file.get('id')).execute()
            print(f"🔍 [SETUP] Test file cleaned up")
            
            return True
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Folder access verification failed for {folder_id}: {e}")
            print(f"❌ [SETUP ERROR] Exception type: {type(e).__name__}")
            import traceback
            print(f"❌ [SETUP ERROR] Full traceback: {traceback.format_exc()}")
            return False
    
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
            print(f"🔍 [SETUP] Starting sheets initialization for user {user_id}")
            
            current_state = self.setup_states[user_id]
            club_name = current_state['club_name']
            admin_discord_id = current_state['admin_discord_id']
            config_folder_id = current_state['config_folder_id']
            monthly_folder_id = current_state['monthly_folder_id']
            
            print(f"🔍 [SETUP] Creating config sheet for club: {club_name}")
            print(f"🔍 [SETUP] Admin Discord ID: {admin_discord_id}")
            print(f"🔍 [SETUP] Config folder ID: {config_folder_id}")
            
            # Create master config sheet
            try:
                config_spreadsheet_id = self.sheets_manager.create_master_config_sheet(
                    club_name, admin_discord_id, config_folder_id
                )
                print(f"🔍 [SETUP] Config sheet created with ID: {config_spreadsheet_id}")
            except Exception as e:
                print(f"❌ [SETUP ERROR] Failed to create config sheet: {e}")
                return f"❌ **Config Sheet Creation Failed**\n\nError: {str(e)}\n\n**Please check:**\n• The config folder is shared with the service account\n• The service account has 'Editor' permissions\n• The folder ID is correct"
            
            if not config_spreadsheet_id:
                return "❌ Failed to create configuration sheet. Please check your Google Drive permissions."
            
            # Store config sheet ID
            current_state['config_spreadsheet_id'] = config_spreadsheet_id
            
            # Create monthly sheets
            current_month = datetime.now().strftime("%B %Y")
            print(f"🔍 [SETUP] Creating monthly sheets for: {current_month}")
            print(f"🔍 [SETUP] Monthly folder ID: {monthly_folder_id}")
            
            try:
                monthly_sheets = self.sheets_manager.create_monthly_sheets(
                    club_name, current_month, monthly_folder_id
                )
                print(f"🔍 [SETUP] Monthly sheets created: {monthly_sheets}")
            except Exception as e:
                print(f"❌ [SETUP ERROR] Failed to create monthly sheets: {e}")
                return f"❌ **Monthly Sheets Creation Failed**\n\nError: {str(e)}\n\n**Please check:**\n• The monthly folder is shared with the service account\n• The service account has 'Editor' permissions\n• The folder ID is correct"
            
            if not monthly_sheets:
                return "❌ Failed to create monthly sheets. Please check your Google Drive permissions."
            
            # Store monthly sheets
            current_state['monthly_sheets'] = monthly_sheets
            
            # Move to next step - start with task reminders channel
            current_state['step'] = 'task_reminders_channel'
            
            print(f"🔍 [SETUP] Sheets initialization completed successfully")
            print(f"🔍 [SETUP] Moving to channel configuration step")
            
            message = "✅ **Google Sheets Created Successfully!**\n\n"
            message += f"• Config Sheet: `{config_spreadsheet_id}`\n"
            message += f"• Tasks Sheet: `{monthly_sheets['tasks']}`\n"
            message += f"• Meetings Sheet: `{monthly_sheets['meetings']}`\n\n"
            message += "**Step 5a: Task Reminders Channel**\n"
            message += "Now I need to know which Discord channels to use for different types of messages.\n\n"
            message += "First, which channel should I use for task reminders?\n\n"
            message += "This is where I'll send:\n"
            message += "• Task deadline reminders (T-24h, T-2h)\n"
            message += "• Overdue task notifications\n"
            message += "• Task completion confirmations\n\n"
            message += "Please provide the channel ID:"
            
            return message
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error in sheets initialization: {e}")
            return f"❌ **Sheets Initialization Failed**\n\nError: {str(e)}\n\n**Please check:**\n• Your Google Drive permissions\n• The service account has access to the folders\n• Try running setup again"
    
    async def _handle_task_reminders_channel(self, user_id: str, message_content: str) -> str:
        """
        Handles task reminders channel configuration.
        
        Args:
            user_id: Discord ID of the user
            message_content: Channel ID for task reminders
            
        Returns:
            Next setup message
        """
        try:
            print(f"🔍 [SETUP] Processing task reminders channel for user {user_id}")
            print(f"🔍 [SETUP] Channel message content: {message_content}")
            
            # Extract channel ID
            channel_id = message_content.strip()
            print(f"🔍 [SETUP] Extracted task reminders channel ID: {channel_id}")
            
            if not channel_id or not channel_id.isdigit():
                return "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).\n\n**How to get channel ID:**\n1. Right-click on the channel in Discord\n2. Select 'Copy ID'\n3. Paste the ID here"
            
            # Store task reminders channel ID
            current_state = self.setup_states[user_id]
            current_state['task_reminders_channel_id'] = channel_id
            
            # Move to next step
            current_state['step'] = 'meeting_reminders_channel'
            
            message = "✅ **Task Reminders Channel Set!**\n\n"
            message += f"Task reminders will be sent to: <#{channel_id}>\n\n"
            message += "**Step 5b: Meeting Reminders Channel**\n"
            message += "Now, which channel should I use for meeting reminders?\n\n"
            message += "This is where I'll send:\n"
            message += "• Meeting notifications (T-2h, T-0)\n"
            message += "• Meeting reminders\n\n"
            message += "Please provide the channel ID:"
            
            return message
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error in task reminders channel configuration: {e}")
            return f"❌ **Task Reminders Channel Configuration Failed**\n\nError: {str(e)}\n\n**Please check:**\n• The channel ID is correct\n• The bot has access to that channel\n• Try again with a valid channel ID"
    
    async def _handle_meeting_reminders_channel(self, user_id: str, message_content: str) -> str:
        """
        Handles meeting reminders channel configuration.
        
        Args:
            user_id: Discord ID of the user
            message_content: Channel ID for meeting reminders
            
        Returns:
            Next setup message
        """
        try:
            print(f"🔍 [SETUP] Processing meeting reminders channel for user {user_id}")
            print(f"🔍 [SETUP] Channel message content: {message_content}")
            
            # Extract channel ID
            channel_id = message_content.strip()
            print(f"🔍 [SETUP] Extracted meeting reminders channel ID: {channel_id}")
            
            if not channel_id or not channel_id.isdigit():
                return "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).\n\n**How to get channel ID:**\n1. Right-click on the channel in Discord\n2. Select 'Copy ID'\n3. Paste the ID here"
            
            # Store meeting reminders channel ID
            current_state = self.setup_states[user_id]
            current_state['meeting_reminders_channel_id'] = channel_id
            
            # Move to next step
            current_state['step'] = 'escalation_channel'
            
            message = "✅ **Meeting Reminders Channel Set!**\n\n"
            message += f"Meeting reminders will be sent to: <#{channel_id}>\n\n"
            message += "**Step 5c: Escalation Channel**\n"
            message += "Finally, which channel should I use for escalations?\n\n"
            message += "This is where I'll send:\n"
            message += "• Overdue task alerts\n"
            message += "• Admin notifications\n"
            message += "• Important system messages\n\n"
            message += "Please provide the channel ID:"
            
            return message
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error in meeting reminders channel configuration: {e}")
            return f"❌ **Meeting Reminders Channel Configuration Failed**\n\nError: {str(e)}\n\n**Please check:**\n• The channel ID is correct\n• The bot has access to that channel\n• Try again with a valid channel ID"
    
    async def _handle_escalation_channel(self, user_id: str, message_content: str) -> str:
        """
        Handles escalation channel configuration and completes setup.
        
        Args:
            user_id: Discord ID of the user
            message_content: Channel ID for escalations
            
        Returns:
            Setup completion message
        """
        try:
            print(f"🔍 [SETUP] Processing escalation channel for user {user_id}")
            print(f"🔍 [SETUP] Channel message content: {message_content}")
            
            # Extract channel ID
            channel_id = message_content.strip()
            print(f"🔍 [SETUP] Extracted escalation channel ID: {channel_id}")
            
            if not channel_id or not channel_id.isdigit():
                return "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).\n\n**How to get channel ID:**\n1. Right-click on the channel in Discord\n2. Select 'Copy ID'\n3. Paste the ID here"
            
            # Store escalation channel ID
            current_state = self.setup_states[user_id]
            current_state['escalation_channel_id'] = channel_id
            
            print(f"🔍 [SETUP] All channels configured, updating config sheet")
            print(f"🔍 [SETUP] Config spreadsheet ID: {current_state['config_spreadsheet_id']}")
            
            # Update config sheet with all channel IDs (with retry logic)
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    print(f"🔍 [SETUP] Attempting to update config sheet (attempt {attempt + 1}/{max_retries})")
                    self.sheets_manager.update_config_channels(
                        current_state['config_spreadsheet_id'],
                        current_state['task_reminders_channel_id'],
                        current_state['meeting_reminders_channel_id'],
                        current_state['escalation_channel_id']
                    )
                    print(f"🔍 [SETUP] Config sheet updated successfully")
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    print(f"❌ [SETUP ERROR] Failed to update config sheet (attempt {attempt + 1}/{max_retries}): {e}")
                    
                    if attempt < max_retries - 1:  # Not the last attempt
                        print(f"🔍 [SETUP] Retrying in {retry_delay} seconds...")
                        import asyncio
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        # Last attempt failed
                        error_msg = str(e)
                        if "Broken pipe" in error_msg or "Connection reset" in error_msg:
                            return f"❌ **Network Connection Issue**\n\nThere was a temporary network problem connecting to Google Sheets.\n\n**Please try again in a few moments.**\n\nIf the problem persists, check your internet connection and try restarting the setup process."
                        else:
                            return f"❌ **Channel Configuration Failed**\n\nError: {error_msg}\n\n**Please check:**\n• The channel IDs are correct\n• The bot has access to those channels\n• Try again with valid channel IDs"
            
            # Mark setup as complete
            current_state['channels_configured'] = True
            
            print(f"🔍 [SETUP] Logging successful setup completion")
            
            # Log successful setup
            try:
                await self.sheets_manager.log_action(
                    current_state['config_spreadsheet_id'],
                    'setup_completed',
                    user_id,
                    f'Setup completed for club: {current_state["club_name"]}',
                    'success'
                )
                print(f"🔍 [SETUP] Setup completion logged successfully")
            except Exception as e:
                print(f"⚠️ [SETUP WARNING] Failed to log setup completion: {e}")
                # Don't fail the setup for logging errors
            
            # Save setup completion to persistent storage
            try:
                guild_config = {
                    'guild_name': current_state.get('guild_name', 'Unknown Guild'),
                    'club_name': current_state['club_name'],
                    'admin_user_id': current_state['admin_discord_id'],
                    'config_spreadsheet_id': current_state['config_spreadsheet_id'],
                    'task_reminders_channel_id': current_state['task_reminders_channel_id'],
                    'meeting_reminders_channel_id': current_state['meeting_reminders_channel_id'],
                    'escalation_channel_id': current_state['escalation_channel_id'],
                    'config_folder_id': current_state['config_folder_id'],
                    'monthly_folder_id': current_state['monthly_folder_id'],
                    'monthly_sheets': current_state.get('monthly_sheets', {})
                }
                
                guild_id = current_state.get('guild_id')
                if not guild_id:
                    return f"❌ **Setup Completion Failed**\n\nError: No guild ID found in setup state.\n\n**Please contact support.**"
                
                self.status_manager.mark_setup_complete(guild_id, guild_config)
                print(f"🔍 [SETUP] Setup completion saved to persistent storage")
            except Exception as e:
                print(f"❌ [SETUP ERROR] Failed to save setup completion: {e}")
                return f"❌ **Setup Completion Failed**\n\nError saving setup status: {str(e)}\n\n**Please contact support.**"
            
            # Clean up setup state
            del self.setup_states[user_id]
            
            print(f"🔍 [SETUP] Setup completed successfully for user {user_id}")
            
            message = "🎉 **Setup Complete!** 🎉\n\n"
            message += f"Your club **{current_state['club_name']}** is now configured!\n\n"
            message += "**Channel Configuration:**\n"
            message += f"• Task reminders will be sent to: <#{current_state['task_reminders_channel_id']}>\n"
            message += f"• Meeting reminders will be sent to: <#{current_state['meeting_reminders_channel_id']}>\n"
            message += f"• Escalations will be sent to: <#{current_state['escalation_channel_id']}>\n\n"
            message += "**What happens next:**\n"
            message += "• I'll listen for commands in your DM and public channels\n"
            message += "• Use `/meeting set` to schedule meetings\n"
            message += "• Use `/assign` to create tasks\n"
            message += "• I'll automatically parse meeting minutes and create tasks\n"
            message += "• Task reminders and escalations will be sent to the configured channels\n\n"
            message += "**Need help?** Use `/help` to see all available commands."
            
            return message
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error in escalation channel configuration: {e}")
            return f"❌ **Escalation Channel Configuration Failed**\n\nError: {str(e)}\n\n**Please check:**\n• The channel ID is correct\n• The bot has access to that channel\n• Try again with a valid channel ID"
    
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
            print(f"🔍 [SETUP] Processing channel configuration for user {user_id}")
            print(f"🔍 [SETUP] Channel message content: {message_content}")
            
            # Parse channel IDs from message
            # This is a simplified parser - in practice, you might want a more structured approach
            channel_ids = self._extract_channel_ids(message_content)
            print(f"🔍 [SETUP] Extracted channel IDs: {channel_ids}")
            
            if len(channel_ids) < 3:
                return "❌ Please provide all three channel IDs: task reminders, meeting reminders, and escalations."
            
            current_state = self.setup_states[user_id]
            
            print(f"🔍 [SETUP] Updating config sheet with channel IDs")
            print(f"🔍 [SETUP] Config spreadsheet ID: {current_state['config_spreadsheet_id']}")
            
            # Update config sheet with channel IDs (with retry logic)
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    print(f"🔍 [SETUP] Attempting to update config sheet (attempt {attempt + 1}/{max_retries})")
                    self.sheets_manager.update_config_channels(
                        current_state['config_spreadsheet_id'],
                        channel_ids[0],  # Task reminders
                        channel_ids[1],  # Meeting reminders
                        channel_ids[2]   # Escalations
                    )
                    print(f"🔍 [SETUP] Config sheet updated successfully")
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    print(f"❌ [SETUP ERROR] Failed to update config sheet (attempt {attempt + 1}/{max_retries}): {e}")
                    
                    if attempt < max_retries - 1:  # Not the last attempt
                        print(f"🔍 [SETUP] Retrying in {retry_delay} seconds...")
                        import asyncio
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        # Last attempt failed
                        error_msg = str(e)
                        if "Broken pipe" in error_msg or "Connection reset" in error_msg:
                            return f"❌ **Network Connection Issue**\n\nThere was a temporary network problem connecting to Google Sheets.\n\n**Please try again in a few moments.**\n\nIf the problem persists, check your internet connection and try restarting the setup process."
                        else:
                            return f"❌ **Channel Configuration Failed**\n\nError: {error_msg}\n\n**Please check:**\n• The channel IDs are correct\n• The bot has access to those channels\n• Try again with valid channel IDs"
            
            # Mark setup as complete
            current_state['channels_configured'] = True
            
            print(f"🔍 [SETUP] Logging successful setup completion")
            
            # Log successful setup
            try:
                await self.sheets_manager.log_action(
                    current_state['config_spreadsheet_id'],
                    'setup_completed',
                    user_id,
                    f'Setup completed for club: {current_state["club_name"]}',
                    'success'
                )
                print(f"🔍 [SETUP] Setup completion logged successfully")
            except Exception as e:
                print(f"⚠️ [SETUP WARNING] Failed to log setup completion: {e}")
                # Don't fail the setup for logging errors
            
            # Save setup completion to persistent storage
            try:
                guild_config = {
                    'guild_name': current_state.get('guild_name', 'Unknown Guild'),
                    'club_name': current_state['club_name'],
                    'admin_user_id': current_state['admin_discord_id'],
                    'config_spreadsheet_id': current_state['config_spreadsheet_id'],
                    'task_reminders_channel_id': current_state['task_reminders_channel_id'],
                    'meeting_reminders_channel_id': current_state['meeting_reminders_channel_id'],
                    'escalation_channel_id': current_state['escalation_channel_id'],
                    'config_folder_id': current_state['config_folder_id'],
                    'monthly_folder_id': current_state['monthly_folder_id'],
                    'monthly_sheets': current_state.get('monthly_sheets', {})
                }
                
                guild_id = current_state.get('guild_id')
                if not guild_id:
                    return f"❌ **Setup Completion Failed**\n\nError: No guild ID found in setup state.\n\n**Please contact support.**"
                
                self.status_manager.mark_setup_complete(guild_id, guild_config)
                print(f"🔍 [SETUP] Setup completion saved to persistent storage")
            except Exception as e:
                print(f"❌ [SETUP ERROR] Failed to save setup completion: {e}")
                return f"❌ **Setup Completion Failed**\n\nError saving setup status: {str(e)}\n\n**Please contact support.**"
            
            # Clean up setup state
            del self.setup_states[user_id]
            
            print(f"🔍 [SETUP] Setup completed successfully for user {user_id}")
            
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
            print(f"❌ [SETUP ERROR] Error in channel configuration: {e}")
            return f"❌ **Channel Configuration Failed**\n\nError: {str(e)}\n\n**Please check:**\n• The channel IDs are correct\n• The bot has access to those channels\n• Try again with valid channel IDs"
    
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
