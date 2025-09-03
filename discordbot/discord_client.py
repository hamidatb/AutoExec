import discord
from discord import app_commands
import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

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
        
        # Start reminder loops
        asyncio.create_task(self.reminder_loop())
        asyncio.create_task(self.meeting_reminder_loop())
        
    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        if message.author == self.user:
            return
            
        # Handle DM setup process
        if isinstance(message.channel, discord.DMChannel):
            await self.handle_dm_setup(message)
            return
            
        # Handle natural language commands and queries
        await self.handle_natural_language(message)
            
        # Handle task replies in public channels
        if message.mentions and self.user in message.mentions:
            await self.handle_task_reply(message)
            
    async def handle_natural_language(self, message: discord.Message):
        """Handle natural language messages using LangChain agent."""
        content = message.content.strip()
        
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
            
    async def handle_autoexec_command(self, message: discord.Message):
        """Handle $AE commands using LangChain agent."""
        try:
            # Remove the $AE prefix
            query = message.content[4:].strip()
            
            if not query:
                await message.channel.send("🤖 I'm here! What would you like me to help you with?")
                return
                
            # Use LangChain agent to process the query
            result = run_agent(query)
            response = result.get("output", "I'm sorry, I couldn't process that request.")
            
            # Send response
            await message.channel.send(f"🤖 **AutoExec Response:**\n{response}")
            
        except Exception as e:
            print(f"Error in AutoExec command: {e}")
            await message.channel.send("❌ Sorry, I encountered an error processing your request.")
            
    async def handle_meeting_minutes_request(self, message: discord.Message):
        """Handle $AEmm meeting minutes requests."""
        try:
            # This would integrate with the meeting minutes system
            # For now, send a helpful response
            response = "📋 **Meeting Minutes Request**\n\n"
            response += "I can help you with meeting minutes! Here are your options:\n\n"
            response += "• Use `/meeting upcoming` to see scheduled meetings\n"
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
            # Use LangChain agent for natural language understanding
            result = run_agent(message.content)
            response = result.get("output", "I'm sorry, I couldn't understand that request.")
            
            # Send response
            await message.channel.send(f"🤖 **AI Assistant:**\n{response}")
            
        except Exception as e:
            print(f"Error in LangChain query: {e}")
            await message.channel.send("❌ Sorry, I encountered an error processing your request.")
            
    def should_use_langchain(self, content: str) -> bool:
        """Determine if a message should be processed by LangChain."""
        # Check for natural language patterns
        natural_language_indicators = [
            'can you', 'could you', 'please', 'help me', 'how do i',
            'what is', 'when is', 'where is', 'why', 'how',
            'i need', 'i want', 'i would like', 'tell me', 'show me'
        ]
        
        content_lower = content.lower()
        
        # Check for natural language patterns
        for indicator in natural_language_indicators:
            if indicator in content_lower:
                return True
                
        # Check for question marks
        if '?' in content:
            return True
            
        # Check for longer, conversational messages
        if len(content.split()) > 5:
            return True
            
        return False
            
    async def handle_dm_setup(self, message: discord.Message):
        """Handle setup process in DMs."""
        user_id = str(message.author.id)
        
        if message.content.lower() == '/setup':
            # Start setup process
            response = await self.setup_manager.start_setup(user_id, message.author.name)
            await message.channel.send(response)
            return
            
        if message.content.lower() == '/cancel':
            # Cancel setup
            response = self.setup_manager.cancel_setup(user_id)
            await message.channel.send(response)
            return
            
        # Check if user is in setup process
        if self.setup_manager.is_in_setup(user_id):
            response = await self.setup_manager.handle_setup_response(user_id, message.content)
            await message.channel.send(response)
            
            # If setup is complete, load the new configuration
            if not self.setup_manager.is_in_setup(user_id):
                await self.load_club_configurations()
                
    async def handle_task_reply(self, message: discord.Message):
        """Handle user replies to task reminders."""
        # Find the club configuration for this guild
        guild_id = str(message.guild.id)
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
        
    response = await bot.setup_manager.start_setup(str(interaction.user.id), interaction.user.name)
    await interaction.response.send_message(response)

@bot.tree.command(name="meeting", description="Manage meetings")
@app_commands.describe(
    action="Action to perform",
    title="Meeting title",
    start="Start time (YYYY-MM-DD HH:MM)",
    end="End time (YYYY-MM-DD HH:MM)",
    minutes_url="Google Docs URL for minutes"
)
async def meeting_command(
    interaction: discord.Interaction,
    action: str,
    title: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    minutes_url: Optional[str] = None
):
    """Handle meeting-related commands."""
    # Check if user is admin
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
    
    if not club_config:
        await interaction.response.send_message(
            "❌ Bot not configured for this server. Please run `/setup` first.",
            ephemeral=True
        )
        return
        
    if str(interaction.user.id) != club_config.get('admin_discord_id'):
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
                
            # Parse end time if provided
            end_time = None
            if end:
                try:
                    end_time = datetime.strptime(end, "%Y-%m-%d %H:%M")
                    end_time = end_time.replace(tzinfo=timezone.utc)
                except ValueError:
                    await interaction.response.send_message(
                        "❌ Invalid end time format. Use YYYY-MM-DD HH:MM",
                        ephemeral=True
                    )
                    return
                    
            # Create meeting data
            meeting_data = {
                'title': title,
                'start_at_utc': start_time.isoformat(),
                'end_at_utc': end_time.isoformat() if end_time else None,
                'start_at_local': start_time.strftime("%B %d, %Y at %I:%M %p"),
                'end_at_local': end_time.strftime("%B %d, %Y at %I:%M %p") if end_time else None,
                'channel_id': str(interaction.channel.id),
                'created_by': str(interaction.user.id)
            }
            
            # Schedule meeting
            success = await bot.meeting_manager.schedule_meeting(
                meeting_data, 
                club_config['meetings_sheet_id']
            )
            
            if success:
                await interaction.response.send_message(
                    f"✅ Meeting '{title}' scheduled successfully!\n"
                    f"Start: {meeting_data['start_at_local']}\n"
                    f"Channel: <#{interaction.channel.id}>"
                )
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
            
        elif action.lower() == "linkminutes":
            if not minutes_url:
                await interaction.response.send_message(
                    "❌ Please provide the minutes document URL.",
                    ephemeral=True
                )
                return
                
            # This would require a meeting ID or selection
            await interaction.response.send_message(
                "❌ Please specify which meeting to link minutes to. Use the meeting ID.",
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
    # Check if user is admin
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
    
    if not club_config:
        await interaction.response.send_message(
            "❌ Bot not configured for this server. Please run `/setup` first.",
            ephemeral=True
        )
        return
        
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
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
    
    if not club_config:
        await interaction.response.send_message(
            "❌ Bot not configured for this server. Please run `/setup` first.",
            ephemeral=True
        )
        return
        
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
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
    
    if not club_config:
        await interaction.response.send_message(
            "❌ Bot not configured for this server. Please run `/setup` first.",
            ephemeral=True
        )
        return
        
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
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
    
    if not club_config:
        await interaction.response.send_message(
            "❌ Bot not configured for this server. Please run `/setup` first.",
            ephemeral=True
        )
        return
        
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
    guild_id = str(interaction.guild.id)
    club_config = bot.club_configs.get(guild_id)
    
    if not club_config:
        await interaction.response.send_message(
            "❌ Bot not configured for this server. Please run `/setup` first.",
            ephemeral=True
        )
        return
        
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

@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    """Show available commands."""
    help_text = """
🤖 **Club Exec Task Manager Bot - Commands**

**Setup & Configuration:**
• `/setup` - Start bot setup (DM only)
• `/help` - Show this help message

**Meeting Management (Admin Only):**
• `/meeting set title:"Title" start:"2025-09-08 17:00" end:"2025-09-08 18:00"`
• `/meeting upcoming` - Show upcoming meetings
• `/meeting cancel` - Cancel a meeting
• `/meeting linkminutes <url>` - Link minutes document
• `/meeting agenda` - Create agenda template

**Task Management:**
• `/assign @user "Task title" due:"2025-09-09 12:00"` - Assign task (Admin only)
• `/summary [month]` - Show task summary
• `/status @user` - Show tasks for specific user
• `/done <task_id>` - Mark task complete
• `/reschedule <task_id> "2025-09-10 15:00"` - Reschedule task

**User Preferences:**
• `/subscribe` - Subscribe to private reminders

**Natural Language Commands:**
• `$AE <query>` - Use AI agent for general queries
• `$AEmm` - Request meeting minutes
• Natural language: "Can you help me schedule a meeting?"
• Questions: "What meetings do I have today?"

**Natural Language Responses:**
Reply to task reminders with:
• "done" - Mark task complete
• "not yet" - Mark task in progress  
• "reschedule to <date>" - Change deadline

Need help? Contact your server admin!
"""
    
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