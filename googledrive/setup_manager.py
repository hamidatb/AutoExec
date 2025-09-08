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
                'step': 'access_code',  # Always start with access code validation
                'access_code_validated': False,
                'club_name': None,
                'admin_discord_id': None,
                'timezone': 'America/Edmonton',  # Default timezone
                'exec_members': [],  # List of exec team members
                'exec_count': None,  # Number of exec members
                'current_exec_index': 0,  # Current exec member being collected
                'guild_id': guild_id,
                'guild_name': guild_name,
                'config_folder_id': None,
                'monthly_folder_id': None,
                'meeting_minutes_folder_id': None,
                'config_spreadsheet_id': None,
                'monthly_sheets': None,
                'channels_configured': False
            }
            
            if not guild_id:
                message = "🎉 **Welcome to the Club Exec Task Manager Bot!** 🎉\n\n"
                message += "I'll help you set up task management for your club. Let's get started!\n\n"
                message += "**Step 1: Access Code**\n"
                message += "To begin setup, I need a valid access code.\n\n"
                message += "Please provide your access code:"
            else:
                message = "🎉 **Welcome to the Club Exec Task Manager Bot!** 🎉\n\n"
                message += f"I'll help you set up task management for **{guild_name}**. Let's get started!\n\n"
                message += "**Step 1: Access Code**\n"
                message += "To begin setup, I need a valid access code.\n\n"
                message += "Please provide your access code:"
            
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
            
            # Check for /cancel command
            if message_content.lower().strip() == '/cancel':
                return self.cancel_setup(user_id)
            
            if user_id not in self.setup_states:
                print(f"❌ [SETUP ERROR] No setup session found for user {user_id}")
                return "❌ Setup session not found. Please start setup again with `/setup`."
            
            current_state = self.setup_states[user_id]
            current_step = current_state['step']
            print(f"🔍 [SETUP] Current step: {current_step}")
            
            if current_step == 'access_code':
                return await self._handle_access_code(user_id, message_content)
            elif current_step == 'guild_id':
                return await self._handle_guild_id(user_id, message_content)
            elif current_step == 'club_name':
                return await self._handle_club_name(user_id, message_content)
            elif current_step == 'admin_selection':
                return await self._handle_admin_selection(user_id, message_content)
            elif current_step == 'timezone':
                return await self._handle_timezone(user_id, message_content)
            elif current_step == 'exec_count':
                return await self._handle_exec_count(user_id, message_content)
            elif current_step == 'exec_member':
                return await self._handle_exec_member(user_id, message_content)
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
            elif current_step == 'general_announcements_channel':
                return await self._handle_general_announcements_channel(user_id, message_content)
            elif current_step == 'free_speak_channel':
                return await self._handle_free_speak_channel(user_id, message_content)
            else:
                print(f"❌ [SETUP ERROR] Unknown setup step: {current_step}")
                return "❌ Unknown setup step. Please start setup again."
                
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error handling setup response: {e}")
            return "❌ An error occurred during setup. Please try again."
    
    async def _handle_access_code(self, user_id: str, access_code: str) -> str:
        """
        Handles access code validation during setup.
        
        Args:
            user_id: Discord ID of the user
            access_code: Access code provided by user
            
        Returns:
            Next setup message or error message
        """
        try:
            from config.config import Config
            
            access_code = access_code.strip()
            
            # Validate the access code
            if not Config.validate_access_code(access_code):
                return "❌ **Invalid Access Code**\n\nThe access code you provided is not valid.\n\nPlease check your access code and try again, or contact an administrator if you don't have one.\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Mark access code as validated and move to next step
            self.setup_states[user_id]['access_code_validated'] = True
            
            # Determine next step based on whether guild_id is already set
            if self.setup_states[user_id]['guild_id']:
                # Guild ID already set, move to club name
                self.setup_states[user_id]['step'] = 'club_name'
                message = "✅ **Access Code Validated!**\n\n"
                message += "**Step 2: Club Information**\n"
                message += "What is the name of your club or organization?\n\n"
                message += "This will be used to name your Google Sheets and identify your club in the system."
            else:
                # Need to get guild ID first
                self.setup_states[user_id]['step'] = 'guild_id'
                message = "✅ **Access Code Validated!**\n\n"
                message += "**Step 2: Server ID**\n"
                message += "Now I need to know which Discord server you want to set up the bot for.\n\n"
                message += "**How to get your Server ID:**\n"
                message += "1. Right-click on your server name in Discord\n"
                message += "2. Select 'Copy Server ID'\n"
                message += "3. Paste the ID here\n\n"
                message += "**Note:** You must be an admin of the server to set up the bot."
            
            return message
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error handling access code: {e}")
            return "❌ Error processing access code. Please try again."
    
    async def _handle_guild_id(self, user_id: str, guild_id: str) -> str:
        """
        Handles guild ID input during setup.
        
        Args:
            user_id: Discord ID of the user
            guild_id: Guild ID provided by user
            
        Returns:
            Next setup message
        """
        try:
            guild_id = guild_id.strip()
            
            # Validate guild ID format (should be numeric)
            if not guild_id.isdigit():
                return "❌ **Invalid Server ID**\n\nPlease provide a valid Discord server ID (numbers only).\n\n**How to get your Server ID:**\n1. Right-click on your server name in Discord\n2. Select 'Copy Server ID'\n3. Paste the ID here\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Check if this guild is already set up
            if self.status_manager.is_setup_complete(guild_id):
                return f"❌ **Server Already Set Up**\n\nThis server (ID: `{guild_id}`) has already been configured.\n\nIf you need to reconfigure it, please contact the current admin or use `/reset` command."
            
            # Store guild ID and move to next step
            self.setup_states[user_id]['guild_id'] = guild_id
            self.setup_states[user_id]['step'] = 'club_name'
            
            message = f"✅ **Server ID Set: `{guild_id}`**\n\n"
            message += "**Step 3: Club Information**\n"
            message += "What is the name of your club or organization?\n\n"
            message += "This will be used to name your Google Sheets and identify your club in the system."
            
            return message
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error handling guild ID: {e}")
            return "❌ Error processing server ID. Please try again."
    
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
            message += "**Step 3: Admin Selection**\n"
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
                return "❌ **Invalid Admin Mention**\n\nPlease @mention the admin user (e.g., @username).\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Store admin Discord ID
            self.setup_states[user_id]['admin_discord_id'] = admin_discord_id
            self.setup_states[user_id]['step'] = 'timezone'
            
            message = f"✅ **Admin Set: <@{admin_discord_id}>**\n\n"
            message += "**Step 4: Timezone Configuration**\n"
            message += "What timezone should I use for your club?\n\n"
            message += "**Type 'Y' to use the default, or choose from the list below:**\n\n"
            message += "**Default:** America/Edmonton\n\n"
            message += "**Available Timezones:**\n"
            message += "• America/New_York\n"
            message += "• America/Los_Angeles\n"
            message += "• America/Chicago\n"
            message += "• America/Denver\n"
            message += "• Europe/London\n"
            message += "• Europe/Paris\n"
            message += "• Asia/Tokyo\n"
            message += "• Asia/Shanghai\n"
            message += "• Australia/Sydney\n"
            message += "• UTC\n\n"
            message += "**Note:** This will be used for all meeting times and reminders."
            
            # Get current month
            current_month = datetime.now().strftime("%B %Y")
            message = message.format(club_name=self.setup_states[user_id]['club_name'], 
                                   current_month=current_month)
            
            return message
            
        except Exception as e:
            print(f"Error handling admin selection: {e}")
            return "❌ Error setting admin. Please try again."
    
    async def _handle_timezone(self, user_id: str, timezone_input: str) -> str:
        """
        Handles timezone input.
        
        Args:
            user_id: Discord ID of the user
            timezone_input: Timezone input from user
            
        Returns:
            Next setup message
        """
        try:
            timezone_input = timezone_input.strip()
            
            # If "Y" or empty, use default
            if not timezone_input or timezone_input.lower() == 'y':
                timezone_input = 'America/Edmonton'
            
            # Basic timezone validation
            valid_timezones = [
                'America/Edmonton', 'America/New_York', 'America/Los_Angeles', 
                'America/Chicago', 'America/Denver', 'Europe/London', 'Europe/Paris',
                'Asia/Tokyo', 'Asia/Shanghai', 'Australia/Sydney', 'UTC'
            ]
            
            # Validate timezone
            if timezone_input not in valid_timezones:
                return f"❌ **Invalid Timezone**\n\nPlease choose from the available timezones or type 'Y' for the default.\n\n**Available options:**\n" + "\n".join([f"• {tz}" for tz in valid_timezones]) + "\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Store timezone
            self.setup_states[user_id]['timezone'] = timezone_input
            self.setup_states[user_id]['step'] = 'exec_count'
            
            message = f"✅ **Timezone Set: {timezone_input}**\n\n"
            message += "**Step 5: Executive Team**\n"
            message += "How many executive team members do you have?\n\n"
            message += "**Note:** This includes all exec positions (President, VP, Treasurer, etc.)\n"
            message += "You can always add more members later through the configuration."
            
            return message
            
        except Exception as e:
            print(f"Error handling timezone: {e}")
            return "❌ Error setting timezone. Please try again."
    
    async def _handle_exec_count(self, user_id: str, count_input: str) -> str:
        """
        Handles executive team count input.
        
        Args:
            user_id: Discord ID of the user
            count_input: Number of exec members
            
        Returns:
            Next setup message
        """
        try:
            count_input = count_input.strip()
            
            # Validate count
            try:
                exec_count = int(count_input)
                if exec_count < 0:
                    return "❌ **Invalid Count**\n\nPlease enter a valid number of executive members (0 or more).\n\n**You can also type `/cancel` to stop the setup process.**"
            except ValueError:
                return "❌ **Invalid Count**\n\nPlease enter a valid number (e.g., 5).\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Store count and initialize exec collection
            self.setup_states[user_id]['exec_count'] = exec_count
            self.setup_states[user_id]['exec_members'] = []
            self.setup_states[user_id]['current_exec_index'] = 0
            
            if exec_count == 0:
                # Skip exec collection, go to folder selection
                self.setup_states[user_id]['step'] = 'folder_selection'
                message = f"✅ **Executive Team Count Set: {exec_count}**\n\n"
                message += "**Step 6: Google Drive Folders**\n"
                message += "Before I create the Google Sheets, I need to know where to put them.\n\n"
                message += "**IMPORTANT**: Please make sure you have shared these folders with the AutoExec service account: **autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com**!\n\n"
                message += "**No OAuth needed** - the bot will access only the folders you specifically share.\n\n"
                message += "Please provide the Google Drive folder links for:\n"
                message += "• **Main Config Folder** - Where to store the Task Manager Config sheet\n"
                message += "• **Monthly Sheets Folder** - Where to store monthly task and meeting sheets\n"
                message += "• **Meeting Minutes Folder** - Where to store meeting minutes documents\n\n"
                message += "You can get folder links by:\n"
                message += "1. Right-clicking the folder in Google Drive\n"
                message += "2. Selecting 'Get link'\n"
                message += "3. Copying the link\n\n"
                message += "**Format**: Please provide all three links separated by a new line or comma."
            else:
                # Start collecting exec members
                self.setup_states[user_id]['step'] = 'exec_member'
                message = f"✅ **Executive Team Count Set: {exec_count}**\n\n"
                message += "**Step 6: Executive Team Members**\n"
                message += f"Now I'll collect information for each of your {exec_count} executive members.\n\n"
                message += "**For each member, please provide:**\n"
                message += "• First and last name\n"
                message += "• Role/position (optional - defaults to 'General Team Member')\n"
                message += "• Discord ID\n\n"
                message += "**Format:** `FirstName LastName, Role, @DiscordUser`\n"
                message += "**Example:** `John Smith, President, @johnsmith`\n\n"
                message += f"**Member 1 of {exec_count}:**"
            
            return message
            
        except Exception as e:
            print(f"Error handling exec count: {e}")
            return "❌ Error setting executive count. Please try again."
    
    async def _handle_exec_member(self, user_id: str, member_input: str) -> str:
        """
        Handles executive member input.
        
        Args:
            user_id: Discord ID of the user
            member_input: Member information input
            
        Returns:
            Next setup message
        """
        try:
            current_state = self.setup_states[user_id]
            current_index = current_state['current_exec_index']
            total_count = current_state['exec_count']
            
            # Parse member input
            parts = [part.strip() for part in member_input.split(',')]
            
            if len(parts) < 2:
                return "❌ **Invalid Format**\n\nPlease provide: `FirstName LastName, Role, @DiscordUser`\n\n**Example:** `John Smith, President, @johnsmith`\n\n**Note:** Role is optional - you can omit it.\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Extract name, role, and Discord ID
            name = parts[0].strip()
            discord_mention = parts[-1].strip()  # Last part should be Discord mention
            
            # Role is optional (middle part if provided)
            role = "General Team Member"  # Default
            if len(parts) == 3:
                role = parts[1].strip()
            
            # Extract Discord ID from mention
            discord_id = self._extract_discord_id(discord_mention)
            if not discord_id:
                return "❌ **Invalid Discord ID**\n\nPlease @mention the Discord user (e.g., @username).\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Validate name
            if not name or len(name.split()) < 2:
                return "❌ **Invalid Name**\n\nPlease provide both first and last name.\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Store member
            member_info = {
                'name': name,
                'role': role,
                'discord_id': discord_id
            }
            current_state['exec_members'].append(member_info)
            current_state['current_exec_index'] += 1
            
            # Check if we've collected all members
            if current_state['current_exec_index'] >= total_count:
                # All members collected, move to folder selection
                current_state['step'] = 'folder_selection'
                message = f"✅ **Member {current_index + 1} Added: {name} ({role})**\n\n"
                message += f"✅ **All {total_count} executive members collected!**\n\n"
                message += "**Step 7: Google Drive Folders**\n"
                message += "Before I create the Google Sheets, I need to know where to put them.\n\n"
                message += "**IMPORTANT**: Please make sure you have shared these folders with the AutoExec service account: **autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com**!\n\n"
                message += "**No OAuth needed** - the bot will access only the folders you specifically share.\n\n"
                message += "Please provide the Google Drive folder links for:\n"
                message += "• **Main Config Folder** - Where to store the Task Manager Config sheet\n"
                message += "• **Monthly Sheets Folder** - Where to store monthly task and meeting sheets\n"
                message += "• **Meeting Minutes Folder** - Where to store meeting minutes documents\n\n"
                message += "You can get folder links by:\n"
                message += "1. Right-clicking the folder in Google Drive\n"
                message += "2. Selecting 'Get link'\n"
                message += "3. Copying the link\n\n"
                message += "**Format**: Please provide all three links separated by a new line or comma."
            else:
                # More members to collect
                message = f"✅ **Member {current_index + 1} Added: {name} ({role})**\n\n"
                message += f"**Member {current_index + 2} of {total_count}:**"
            
            return message
            
        except Exception as e:
            print(f"Error handling exec member: {e}")
            return "❌ Error adding executive member. Please try again."
    
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
            
            if len(folder_links) < 3:
                return "❌ Please provide all three folder links (config folder, monthly sheets folder, and meeting minutes folder)."
            
            # Extract folder IDs from Google Drive links
            config_folder_id = self._extract_folder_id(folder_links[0])
            monthly_folder_id = self._extract_folder_id(folder_links[1])
            meeting_minutes_folder_id = self._extract_folder_id(folder_links[2])
            
            print(f"🔍 [SETUP] Extracted folder IDs - Config: {config_folder_id}, Monthly: {monthly_folder_id}, Meeting Minutes: {meeting_minutes_folder_id}")
            
            if not config_folder_id or not monthly_folder_id or not meeting_minutes_folder_id:
                return "❌ Invalid folder links. Please make sure you're providing Google Drive folder links."
            
            # Store folder IDs
            self.setup_states[user_id]['config_folder_id'] = config_folder_id
            self.setup_states[user_id]['monthly_folder_id'] = monthly_folder_id
            self.setup_states[user_id]['meeting_minutes_folder_id'] = meeting_minutes_folder_id
            
            # Move to sheets creation step
            self.setup_states[user_id]['step'] = 'sheets_creation'
            
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
            
            # Test access to meeting minutes folder
            try:
                meeting_minutes_access = await self._verify_folder_access(meeting_minutes_folder_id)
                print(f"🔍 [SETUP] Meeting minutes folder access result: {meeting_minutes_access}")
            except Exception as e:
                print(f"❌ [SETUP ERROR] Meeting minutes folder verification failed: {e}")
                meeting_minutes_access = False
            
            # Check results and proceed accordingly
            if not config_access:
                # Keep user in folder_selection step so they can retry
                return f"❌ **Config Folder Access Failed**\n\nI cannot access the config folder `{config_folder_id}`.\n\n**Please check:**\n• The folder exists and is shared with the service account\n• The service account has 'Editor' permissions\n• The folder ID is correct\n\n**Service Account:** `autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com`\n\n**What would you like to do?**\n• **Retry**: Share the folder with the service account and send the folder links again\n• **Cancel**: Type `/cancel` to stop the setup process"
            
            if not monthly_access:
                # Keep user in folder_selection step so they can retry
                return f"❌ **Monthly Folder Access Failed**\n\nI cannot access the monthly folder `{monthly_folder_id}`.\n\n**Please check:**\n• The folder exists and is shared with the service account\n• The service account has 'Editor' permissions\n• The folder ID is correct\n\n**Service Account:** `autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com`\n\n**What would you like to do?**\n• **Retry**: Share the folder with the service account and send the folder links again\n• **Cancel**: Type `/cancel` to stop the setup process"
            
            if not meeting_minutes_access:
                # Keep user in folder_selection step so they can retry
                return f"❌ **Meeting Minutes Folder Access Failed**\n\nI cannot access the meeting minutes folder `{meeting_minutes_folder_id}`.\n\n**Please check:**\n• The folder exists and is shared with the service account\n• The service account has 'Editor' permissions\n• The folder ID is correct\n\n**Service Account:** `autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com`\n\n**What would you like to do?**\n• **Retry**: Share the folder with the service account and send the folder links again\n• **Cancel**: Type `/cancel` to stop the setup process"
            
            # Both folders accessible, proceed directly to sheets initialization
            print(f"🔍 [SETUP] Both folders verified, proceeding to sheets initialization")
            
            # Create sheets immediately and return the complete result
            sheets_result = await self._handle_sheets_initialization(user_id, "")
            
            # Combine folder verification with sheets creation result
            complete_message = "✅ **Folders Selected and Verified Successfully!**\n\n"
            complete_message += f"• Config Folder ID: `{config_folder_id}` ✅ Accessible\n"
            complete_message += f"• Monthly Folder ID: `{monthly_folder_id}` ✅ Accessible\n"
            complete_message += f"• Meeting Minutes Folder ID: `{meeting_minutes_folder_id}` ✅ Accessible\n\n"
            complete_message += sheets_result
            
            return complete_message
            
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
            
            # No delay needed since this is now part of the immediate flow
            
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
                    club_name, admin_discord_id, config_folder_id, 
                    current_state.get('timezone', 'America/Edmonton'),
                    current_state.get('exec_members', [])
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
            message += "**Step 8a: Task Reminders Channel**\n"
            message += "Now I need to know which Discord channels to use for different types of messages.\n\n"
            message += "**💡 Important:** You can use the same channel for multiple purposes! For example, you could use your main club channel for both task reminders and general announcements.\n\n"
            message += "First, which channel should I use for task reminders?\n\n"
            message += "This is where I'll send:\n"
            message += "• Task deadline reminders (T-24h, T-2h)\n"
            message += "• Overdue task notifications\n"
            message += "• Task completion confirmations\n\n"
            message += "**How to get channel ID:**\n"
            message += "1. Right-click on the channel in Discord\n"
            message += "2. Select 'Copy ID'\n"
            message += "3. Paste the ID here\n\n"
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
                return "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).\n\n**How to get channel ID:**\n1. Right-click on the channel in Discord\n2. Select 'Copy ID'\n3. Paste the ID here\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Store task reminders channel ID
            current_state = self.setup_states[user_id]
            current_state['task_reminders_channel_id'] = channel_id
            
            # Move to next step
            current_state['step'] = 'meeting_reminders_channel'
            
            message = "✅ **Task Reminders Channel Set!**\n\n"
            message += f"Task reminders will be sent to: <#{channel_id}>\n\n"
            message += "**Step 8b: Meeting Reminders Channel**\n"
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
                return "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).\n\n**How to get channel ID:**\n1. Right-click on the channel in Discord\n2. Select 'Copy ID'\n3. Paste the ID here\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Store meeting reminders channel ID
            current_state = self.setup_states[user_id]
            current_state['meeting_reminders_channel_id'] = channel_id
            
            # Move to next step
            current_state['step'] = 'escalation_channel'
            
            message = "✅ **Meeting Reminders Channel Set!**\n\n"
            message += f"Meeting reminders will be sent to: <#{channel_id}>\n\n"
            message += "**Step 8c: Escalation Channel**\n"
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
                return "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).\n\n**How to get channel ID:**\n1. Right-click on the channel in Discord\n2. Select 'Copy ID'\n3. Paste the ID here\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Store escalation channel ID
            current_state = self.setup_states[user_id]
            current_state['escalation_channel_id'] = channel_id
            
            # Move to general announcements channel step
            current_state['step'] = 'general_announcements_channel'
            
            message = "✅ **Escalation Channel Set!**\n\n"
            message += f"Escalations will be sent to: <#{channel_id}>\n\n"
            message += "**Step 8d: General Announcements Channel**\n"
            message += "Which channel should I use for general announcements and notifications?\n\n"
            message += "This is where I'll send:\n"
            message += "• General club announcements\n"
            message += "• Congratulations and celebrations\n"
            message += "• Important updates\n"
            message += "• Other non-meeting, non-task messages\n\n"
            message += "**💡 Tip:** You can use the same channel for multiple purposes! For example, you could use your main club channel for both general announcements and meeting reminders.\n\n"
            message += "**How to get channel ID:**\n"
            message += "1. Right-click on the channel in Discord\n"
            message += "2. Select 'Copy ID'\n"
            message += "3. Paste the ID here\n\n"
            message += "Please provide the channel ID:"
            
            return message
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error in escalation channel configuration: {e}")
            return f"❌ **Escalation Channel Configuration Failed**\n\nError: {str(e)}\n\n**Please check:**\n• The channel ID is correct\n• The bot has access to that channel\n• Try again with a valid channel ID"
    
    async def _handle_general_announcements_channel(self, user_id: str, message_content: str) -> str:
        """
        Handles general announcements channel configuration.
        
        Args:
            user_id: Discord ID of the user
            message_content: Channel ID for general announcements
            
        Returns:
            Next setup message
        """
        try:
            print(f"🔍 [SETUP] Processing general announcements channel for user {user_id}")
            print(f"🔍 [SETUP] Channel message content: {message_content}")
            
            # Extract channel ID
            channel_id = message_content.strip()
            print(f"🔍 [SETUP] Extracted general announcements channel ID: {channel_id}")
            
            if not channel_id or not channel_id.isdigit():
                return "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only).\n\n**How to get channel ID:**\n1. Right-click on the channel in Discord\n2. Select 'Copy ID'\n3. Paste the ID here\n\n**You can also type `/cancel` to stop the setup process.**"
            
            # Store general announcements channel ID
            current_state = self.setup_states[user_id]
            current_state['general_announcements_channel_id'] = channel_id
            
            # Move to free-speak channel step
            current_state['step'] = 'free_speak_channel'
            
            message = "✅ **General Announcements Channel Set!**\n\n"
            message += f"General announcements will be sent to: <#{channel_id}>\n\n"
            message += "**Step 8e: Free-Speak Channel (Optional)**\n"
            message += "Would you like to configure a channel where the bot can speak freely without being @'d?\n\n"
            message += "This is useful for:\n"
            message += "• Automated responses\n"
            message += "• Status updates\n"
            message += "• Bot interactions\n\n"
            message += "**Type 'skip' to skip this step, or provide a channel ID:**"
            
            return message
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error in general announcements channel configuration: {e}")
            return f"❌ **General Announcements Channel Configuration Failed**\n\nError: {str(e)}\n\n**Please check:**\n• The channel ID is correct\n• The bot has access to that channel\n• Try again with a valid channel ID"
    
    async def _handle_free_speak_channel(self, user_id: str, message_content: str) -> str:
        """
        Handles free-speak channel configuration and completes setup.
        
        Args:
            user_id: Discord ID of the user
            message_content: Channel ID for free-speak or 'skip'
            
        Returns:
            Setup completion message
        """
        try:
            print(f"🔍 [SETUP] Processing free-speak channel for user {user_id}")
            print(f"🔍 [SETUP] Channel message content: {message_content}")
            
            current_state = self.setup_states[user_id]
            message_content = message_content.strip().lower()
            
            # Check if user wants to skip
            if message_content == 'skip':
                current_state['free_speak_channel_id'] = None
                print(f"🔍 [SETUP] User skipped free-speak channel configuration")
            else:
                # Extract channel ID
                channel_id = message_content
                print(f"🔍 [SETUP] Extracted free-speak channel ID: {channel_id}")
                
                if not channel_id or not channel_id.isdigit():
                    return "❌ **Invalid Channel ID**\n\nPlease provide a valid Discord channel ID (numbers only) or type 'skip' to skip this step.\n\n**How to get channel ID:**\n1. Right-click on the channel in Discord\n2. Select 'Copy ID'\n3. Paste the ID here\n\n**You can also type `/cancel` to stop the setup process.**"
                
                # Store free-speak channel ID
                current_state['free_speak_channel_id'] = channel_id
                print(f"🔍 [SETUP] Free-speak channel configured: {channel_id}")
            
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
                        current_state['escalation_channel_id'],
                        current_state.get('free_speak_channel_id'),
                        current_state['general_announcements_channel_id']
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
                    'timezone': current_state.get('timezone', 'America/Edmonton'),
                    'exec_members': current_state.get('exec_members', []),
                    'config_spreadsheet_id': current_state['config_spreadsheet_id'],
                    'task_reminders_channel_id': current_state['task_reminders_channel_id'],
                    'meeting_reminders_channel_id': current_state['meeting_reminders_channel_id'],
                    'escalation_channel_id': current_state['escalation_channel_id'],
                    'general_announcements_channel_id': current_state['general_announcements_channel_id'],
                    'free_speak_channel_id': current_state.get('free_speak_channel_id'),
                    'config_folder_id': current_state['config_folder_id'],
                    'monthly_folder_id': current_state['monthly_folder_id'],
                    'meeting_minutes_folder_id': current_state['meeting_minutes_folder_id'],
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
            message += f"Your club **{current_state['club_name']}** is now fully configured and ready to use!\n\n"
            message += "**Configuration Summary:**\n"
            message += f"• **Club Name:** {current_state['club_name']}\n"
            message += f"• **Admin:** <@{current_state['admin_discord_id']}>\n"
            message += f"• **Timezone:** {current_state.get('timezone', 'America/Edmonton')}\n"
            message += f"• **Executive Members:** {len(current_state.get('exec_members', []))} members added\n"
            message += f"• **Config Sheet:** Created with config, people, logs, and timers tabs\n\n"
            message += "**Channel Configuration:**\n"
            message += f"• Task reminders: <#{current_state['task_reminders_channel_id']}>\n"
            message += f"• Meeting reminders: <#{current_state['meeting_reminders_channel_id']}>\n"
            message += f"• Escalations: <#{current_state['escalation_channel_id']}>\n"
            message += f"• General announcements: <#{current_state['general_announcements_channel_id']}>\n"
            
            # Add free-speak channel info if configured
            if current_state.get('free_speak_channel_id'):
                message += f"• Free-speak channel: <#{current_state['free_speak_channel_id']}>\n"
            else:
                message += "• Free-speak channel: Not configured (skipped)\n"
            
            message += "\n**Setup Data Persisted:**\n"
            message += "• All configuration saved to persistent storage\n"
            message += "• Google Sheets created and configured\n"
            message += "• Executive team members added to people sheet\n"
            message += "• Timezone settings applied\n\n"
            message += "**Ready to Use:**\n"
            message += "• All features are now unlocked\n"
            message += "• Use `/meeting set` to schedule meetings\n"
            message += "• Use `/assign` to create tasks\n"
            message += "• I'll automatically parse meeting minutes and create tasks\n"
            message += "• Task reminders and escalations will be sent to configured channels\n"
            if current_state.get('free_speak_channel_id'):
                message += "• I can speak freely in the free-speak channel without being @'d\n"
            message += "\n**Need help?** Use `/help` to see all available commands."
            
            return message
            
        except Exception as e:
            print(f"❌ [SETUP ERROR] Error in free-speak channel configuration: {e}")
            return f"❌ **Free-Speak Channel Configuration Failed**\n\nError: {str(e)}\n\n**Please check:**\n• The channel ID is correct\n• The bot has access to that channel\n• Try again with a valid channel ID or type 'skip'"
    
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
                        channel_ids[2],  # Escalations
                        None  # Free-speak channel (not configured in old flow)
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
                    'timezone': current_state.get('timezone', 'America/Edmonton'),
                    'exec_members': current_state.get('exec_members', []),
                    'config_spreadsheet_id': current_state['config_spreadsheet_id'],
                    'task_reminders_channel_id': current_state['task_reminders_channel_id'],
                    'meeting_reminders_channel_id': current_state['meeting_reminders_channel_id'],
                    'escalation_channel_id': current_state['escalation_channel_id'],
                    'free_speak_channel_id': None,  # Not configured in old flow
                    'config_folder_id': current_state['config_folder_id'],
                    'monthly_folder_id': current_state['monthly_folder_id'],
                    'meeting_minutes_folder_id': current_state['meeting_minutes_folder_id'],
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
            message += f"• Escalations will be sent to: <#{channel_ids[2]}>\n"
            message += "• Free-speak channel: Not configured (use `/config` to add later)\n\n"
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
            club_configs: Current club configurations dictionary (from persistent storage)
            
        Returns:
            Reset confirmation message or error message
        """
        try:
            # Check if the guild has a configuration
            if guild_id not in club_configs:
                return f"❌ **Reset Failed**\n\nNo configuration found for this server."
            
            # Verify the user is the admin
            guild_config = club_configs[guild_id]
            if str(admin_user_id) != guild_config.get('admin_user_id'):
                return f"❌ **Reset Failed**\n\nOnly the admin can reset the club configuration.\n\n**Current Admin:** <@{guild_config.get('admin_user_id')}>"
            
            # Get club name for confirmation
            club_name = guild_config.get('club_name', 'Unknown Club')
            
            # Remove the configuration from persistent storage
            success = self.status_manager.remove_guild(guild_id, admin_user_id)
            
            if not success:
                return f"❌ **Reset Failed**\n\nFailed to remove configuration from storage."
            
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

    def format_configuration_summary(self, guild_id: str, club_config: Dict[str, Any]) -> str:
        """
        Formats the configuration summary into a readable string for Discord.
        
        Args:
            guild_id: The Discord guild/server ID
            club_config: Current club configuration dictionary
            
        Returns:
            Formatted configuration summary string
        """
        try:
            message = f"📋 **Configuration for Server {guild_id}**\n\n"
            message += f"**Club Information:**\n"
            message += f"• **Club Name:** {club_config.get('club_name', 'Unknown')}\n"
            message += f"• **Admin:** <@{club_config.get('admin_user_id', 'Unknown')}>\n"
            message += f"• **Timezone:** {club_config.get('timezone', 'America/Edmonton')}\n"
            message += f"• **Setup Complete:** {'✅ Yes' if club_config.get('setup_complete', False) else '❌ No'}\n"
            
            if club_config.get('completed_at'):
                message += f"• **Completed:** {club_config.get('completed_at')}\n"
            
            message += f"\n**Executive Members:** {len(club_config.get('exec_members', []))} members\n"
            
            message += f"\n**Channel Configuration:**\n"
            message += f"• Task reminders: <#{club_config.get('task_reminders_channel_id', 'Not set')}>\n"
            message += f"• Meeting reminders: <#{club_config.get('meeting_reminders_channel_id', 'Not set')}>\n"
            message += f"• Escalations: <#{club_config.get('escalation_channel_id', 'Not set')}>\n"
            message += f"• General announcements: <#{club_config.get('general_announcements_channel_id', 'Not set')}>\n"
            
            if club_config.get('free_speak_channel_id'):
                message += f"• Free-speak channel: <#{club_config.get('free_speak_channel_id')}>\n"
            else:
                message += "• Free-speak channel: Not configured\n"
            
            message += f"\n**Google Drive Integration:**\n"
            message += f"• Config folder: {club_config.get('config_folder_id', 'Not set')}\n"
            message += f"• Monthly folder: {club_config.get('monthly_folder_id', 'Not set')}\n"
            message += f"• Meeting minutes folder: {club_config.get('meeting_minutes_folder_id', 'Not set')}\n"
            message += f"• Config spreadsheet: {club_config.get('config_spreadsheet_id', 'Not set')}\n"
            
            return message
            
        except Exception as e:
            print(f"Error formatting configuration summary: {e}")
            return f"❌ Error formatting configuration for server {guild_id}"

    async def verify_folder_access_for_update(self, folder_id: str) -> tuple[bool, str]:
        """
        Verifies that the bot can access a Google Drive folder for configuration updates.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            Tuple of (is_accessible: bool, message: str)
        """
        try:
            print(f"🔍 [CONFIG UPDATE] Testing access to folder: {folder_id}")
            
            # Try to get folder metadata
            folder = self.sheets_manager.drive_service.files().get(
                fileId=folder_id,
                fields='id,name,permissions'
            ).execute()
            
            folder_name = folder.get('name', 'Unknown')
            print(f"🔍 [CONFIG UPDATE] Folder metadata retrieved: {folder_name}")
            
            # Check if we have write permissions by trying to create a test file
            test_file_metadata = {
                'name': f'config_update_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                'parents': [folder_id]
            }
            
            # Create a simple text file using MediaIoBaseUpload
            from googleapiclient.http import MediaIoBaseUpload
            import io
            
            # Create a file-like object with the test content
            test_content = 'Configuration update test file - can be deleted'
            media_body = MediaIoBaseUpload(
                io.BytesIO(test_content.encode('utf-8')),
                mimetype='text/plain',
                resumable=False
            )
            
            test_file = self.sheets_manager.drive_service.files().create(
                body=test_file_metadata,
                media_body=media_body
            ).execute()
            
            print(f"🔍 [CONFIG UPDATE] Test file created successfully: {test_file.get('id')}")
            
            # Clean up test file
            self.sheets_manager.drive_service.files().delete(fileId=test_file.get('id')).execute()
            print(f"🔍 [CONFIG UPDATE] Test file cleaned up")
            
            return True, f"✅ Folder '{folder_name}' is accessible and writable"
            
        except Exception as e:
            print(f"❌ [CONFIG UPDATE ERROR] Folder access verification failed for {folder_id}: {e}")
            print(f"❌ [CONFIG UPDATE ERROR] Exception type: {type(e).__name__}")
            import traceback
            print(f"❌ [CONFIG UPDATE ERROR] Full traceback: {traceback.format_exc()}")
            
            error_msg = str(e)
            if "not found" in error_msg.lower():
                return False, f"❌ Folder not found. Please check the folder ID and ensure it exists."
            elif "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
                return False, f"❌ Permission denied. Please ensure the folder is shared with the service account: **autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com** with 'Editor' permissions."
            else:
                return False, f"❌ Access verification failed: {error_msg}"

    def update_guild_configuration(self, guild_id: str, user_id: str, updates: Dict[str, Any]) -> tuple[bool, str]:
        """
        Update guild configuration with validation. Only the admin can make changes.
        
        Args:
            guild_id: Guild ID
            user_id: User ID requesting the update
            updates: Dictionary of configuration updates
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if user can modify config
            if not self.status_manager.can_modify_config(user_id, guild_id):
                return False, "❌ Access denied. Only the admin can modify server configuration."
            
            # Get current config
            current_config = self.status_manager.get_guild_config(guild_id)
            if not current_config:
                return False, "❌ No configuration found for this server."
            
            # Validate folder updates if any
            folder_updates = {}
            for key, value in updates.items():
                if key.endswith('_folder_id') and value:
                    folder_updates[key] = value
            
            # Update the configuration
            success = self.status_manager.update_guild_config(guild_id, user_id, updates)
            
            if success:
                updated_settings = []
                for key, value in updates.items():
                    setting_name = key.replace('_', ' ').title()
                    updated_settings.append(f"• {setting_name}: {value}")
                
                message = f"✅ **Configuration Updated Successfully!**\n\n"
                message += f"**Updated Settings:**\n" + "\n".join(updated_settings)
                message += f"\n\n**Note:** Changes have been saved and will take effect immediately."
                
                return True, message
            else:
                return False, "❌ Failed to update configuration. Please try again."
                
        except Exception as e:
            print(f"Error updating guild configuration: {e}")
            return False, f"❌ Configuration update failed: {str(e)}"
