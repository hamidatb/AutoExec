"""
Setup tools module for AutoExec agent.
Contains all setup and configuration-related functions.
"""

from langchain.tools import tool
from .context_manager import get_discord_context


@tool
def get_setup_info() -> str:
    """
    Get information about the current bot setup and configuration.
    Use this to answer questions about what's configured, what channels are set up,
    what Google Sheets are being used, etc.
    
    Returns:
        str: Detailed information about the current setup
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ **No club configuration found.**\n\nPlease run `/setup` to configure the bot for your server."
        
        setup_info = "📋 **Current Bot Setup Information:**\n\n"
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                setup_info += f"🏠 **Server:** {guild_config.get('guild_name', 'Unknown')}\n"
                setup_info += f"👥 **Club:** {guild_config.get('club_name', 'Unknown')}\n"
                setup_info += f"👤 **Admin:** <@{guild_config.get('admin_user_id', 'Unknown')}>\n"
                setup_info += f"✅ **Setup Status:** Complete\n"
                setup_info += f"📅 **Setup Date:** {guild_config.get('completed_at', 'Unknown')}\n\n"
                
                # Channel information
                setup_info += "📢 **Channels:**\n"
                task_channel = guild_config.get('task_reminders_channel_id')
                meeting_channel = guild_config.get('meeting_reminders_channel_id')
                escalation_channel = guild_config.get('escalation_channel_id')
                
                if task_channel:
                    setup_info += f"  • Task Reminders: <#{task_channel}>\n"
                if meeting_channel:
                    setup_info += f"  • Meeting Reminders: <#{meeting_channel}>\n"
                if escalation_channel:
                    setup_info += f"  • Escalation: <#{escalation_channel}>\n"
                setup_info += "\n"
                
                # Google Sheets information
                setup_info += "📊 **Google Sheets:**\n"
                config_sheet = guild_config.get('config_spreadsheet_id')
                if config_sheet:
                    setup_info += f"  • Config Sheet: https://docs.google.com/spreadsheets/d/{config_sheet}\n"
                
                # Monthly sheets
                monthly_sheets = guild_config.get('monthly_sheets', {})
                if monthly_sheets:
                    setup_info += "  • Monthly Sheets:\n"
                    if 'tasks' in monthly_sheets:
                        setup_info += f"    - Tasks: https://docs.google.com/spreadsheets/d/{monthly_sheets['tasks']}\n"
                    if 'meetings' in monthly_sheets:
                        setup_info += f"    - Meetings: https://docs.google.com/spreadsheets/d/{monthly_sheets['meetings']}\n"
                
                # Folder information
                config_folder = guild_config.get('config_folder_id')
                monthly_folder = guild_config.get('monthly_folder_id')
                if config_folder:
                    setup_info += f"  • Config Folder: https://drive.google.com/drive/folders/{config_folder}\n"
                if monthly_folder:
                    setup_info += f"  • Monthly Folder: https://drive.google.com/drive/folders/{monthly_folder}\n"
                
                break
        else:
            setup_info += "❌ No complete guild configuration found."
            
        return setup_info
        
    except Exception as e:
        print(f"Error getting setup info: {e}")
        return f"❌ Error getting setup information: {str(e)}"


@tool
def get_meeting_sheet_info() -> str:
    """
    Get information about the meetings Google Sheet, including the link and current status.
    Use this to answer questions like "What's our Google Sheets link for meetings?"
    
    Returns:
        str: Information about the meetings sheet including the link
    """
    from discordbot.discord_client import BOT_INSTANCE
    from .context_manager import get_meetings_sheet_id
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ **No club configuration found.**\n\nPlease run `/setup` to configure the bot for your server."
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                # Get the meetings sheet ID using the standard function
                meetings_sheet_id = get_meetings_sheet_id(guild_config)
                
                if not meetings_sheet_id:
                    return "❌ **No meetings spreadsheet configured.**\n\nPlease run `/setup` to configure the meeting spreadsheet."
                
                # Get some basic info about the sheet
                try:
                    meetings = BOT_INSTANCE.meeting_manager.get_upcoming_meetings(meetings_sheet_id, limit=10)
                    meeting_count = len(meetings)
                except:
                    meeting_count = "Unknown"
                
                sheet_info = "📅 **Meetings Google Sheet Information:**\n\n"
                sheet_info += f"🔗 **Sheet Link:** https://docs.google.com/spreadsheets/d/{meetings_sheet_id}\n"
                sheet_info += f"📊 **Sheet ID:** `{meetings_sheet_id}`\n"
                sheet_info += f"📋 **Upcoming Meetings:** {meeting_count}\n"
                sheet_info += f"🏠 **Server:** {guild_config.get('guild_name', 'Unknown')}\n"
                sheet_info += f"👥 **Club:** {guild_config.get('club_name', 'Unknown')}\n\n"
                sheet_info += "💡 **Tip:** You can use this link to view and edit meetings directly in Google Sheets!"
                
                return sheet_info
                
        return "❌ No complete guild configuration found."
        
    except Exception as e:
        print(f"Error getting meeting sheet info: {e}")
        return f"❌ Error getting meeting sheet information: {str(e)}"


@tool
def get_task_sheet_info() -> str:
    """
    Get information about the tasks Google Sheet, including the link and current status.
    Use this to answer questions like "What's our Google Sheets link for tasks?"
    
    Returns:
        str: Information about the tasks sheet including the link
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ **No club configuration found.**\n\nPlease run `/setup` to configure the bot for your server."
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                # Get the tasks sheet ID
                tasks_sheet_id = None
                if 'monthly_sheets' in guild_config and 'tasks' in guild_config['monthly_sheets']:
                    tasks_sheet_id = guild_config['monthly_sheets']['tasks']
                elif 'tasks_sheet_id' in guild_config:
                    tasks_sheet_id = guild_config['tasks_sheet_id']
                
                if not tasks_sheet_id:
                    return "❌ **No tasks spreadsheet configured.**\n\nPlease run `/setup` to configure the tasks spreadsheet."
                
                # Get some basic info about the sheet
                try:
                    all_tasks = BOT_INSTANCE.meeting_manager.sheets_manager.get_all_tasks(tasks_sheet_id)
                    task_count = len(all_tasks)
                except:
                    task_count = "Unknown"
                
                sheet_info = "📋 **Tasks Google Sheet Information:**\n\n"
                sheet_info += f"🔗 **Sheet Link:** https://docs.google.com/spreadsheets/d/{tasks_sheet_id}\n"
                sheet_info += f"📊 **Sheet ID:** `{tasks_sheet_id}`\n"
                sheet_info += f"📝 **Total Tasks:** {task_count}\n"
                sheet_info += f"🏠 **Server:** {guild_config.get('guild_name', 'Unknown')}\n"
                sheet_info += f"👥 **Club:** {guild_config.get('club_name', 'Unknown')}\n\n"
                sheet_info += "💡 **Tip:** You can use this link to view and edit tasks directly in Google Sheets!"
                
                return sheet_info
                
        return "❌ No complete guild configuration found."
        
    except Exception as e:
        print(f"Error getting task sheet info: {e}")
        return f"❌ Error getting task sheet information: {str(e)}"


@tool
def get_channel_info() -> str:
    """
    Get information about the configured Discord channels.
    Use this to answer questions about which channels are set up for reminders, announcements, etc.
    
    Returns:
        str: Information about the configured channels
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get guild configurations from the setup manager
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        if not all_guilds:
            return "❌ **No club configuration found.**\n\nPlease run `/setup` to configure the bot for your server."
        
        channel_info = "📢 **Configured Discord Channels:**\n\n"
        
        # Get the first available guild configuration
        for guild_id, guild_config in all_guilds.items():
            if guild_config.get('setup_complete', False):
                channel_info += f"🏠 **Server:** {guild_config.get('guild_name', 'Unknown')}\n"
                channel_info += f"👥 **Club:** {guild_config.get('club_name', 'Unknown')}\n\n"
                
                # Channel information
                task_channel = guild_config.get('task_reminders_channel_id')
                meeting_channel = guild_config.get('meeting_reminders_channel_id')
                escalation_channel = guild_config.get('escalation_channel_id')
                
                if task_channel:
                    channel_info += f"📋 **Task Reminders:** <#{task_channel}>\n"
                    channel_info += "   • Task assignments and due date reminders\n"
                    channel_info += "   • Overdue notifications\n"
                    channel_info += "   • Task completion confirmations\n\n"
                else:
                    channel_info += "📋 **Task Reminders:** ❌ Not configured\n\n"
                
                if meeting_channel:
                    channel_info += f"📅 **Meeting Reminders:** <#{meeting_channel}>\n"
                    channel_info += "   • Meeting start reminders\n"
                    channel_info += "   • Meeting schedule updates\n"
                    channel_info += "   • Meeting minutes notifications\n\n"
                else:
                    channel_info += "📅 **Meeting Reminders:** ❌ Not configured\n\n"
                
                if escalation_channel:
                    channel_info += f"🚨 **Escalation:** <#{escalation_channel}>\n"
                    channel_info += "   • Overdue task escalations\n"
                    channel_info += "   • Critical notifications\n"
                    channel_info += "   • Admin alerts\n\n"
                else:
                    channel_info += "🚨 **Escalation:** ❌ Not configured\n\n"
                
                break
        else:
            channel_info += "❌ No complete guild configuration found."
            
        return channel_info
        
    except Exception as e:
        print(f"Error getting channel info: {e}")
        return f"❌ Error getting channel information: {str(e)}"


@tool
def get_user_setup_status(user_id: str) -> str:
    """
    Check if a specific user is admin of any configured guild.
    
    Args:
        user_id: Discord user ID to check
        
    Returns:
        string: Setup status for the user
    """
    try:
        from discordbot.discord_client import BOT_INSTANCE
        
        if BOT_INSTANCE is None:
            return "❌ **Setup Status: ERROR**\n\nI cannot check setup status because the Discord bot is not running."
        
        if not hasattr(BOT_INSTANCE, 'setup_manager') or not BOT_INSTANCE.setup_manager:
            return "❌ **Setup Status: ERROR**\n\nI cannot check setup status because the setup manager is not available."
        
        # Check if user is admin of any guild
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
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


@tool
def get_club_setup_info() -> str:
    """
    Get information about the bot's actual setup status and configuration.
    Use this when users ask about setup, configuration, or "what club are you set up for".

    Args:
        None

    Returns:
        string: Information about the bot's actual setup status
    """
    try:
        # Import the Discord client to check actual setup status
        from discordbot.discord_client import BOT_INSTANCE
        from ae_langchain.tools.context_manager import get_discord_context
        
        if BOT_INSTANCE is None:
            return "❌ **Setup Status: ERROR**\n\nI cannot check my setup status because the Discord bot is not running."
        
        # Check if there are any guild configurations using the new guild-based system
        if not hasattr(BOT_INSTANCE, 'setup_manager') or not BOT_INSTANCE.setup_manager:
            return """❌ **Setup Status: ERROR**\n\nI cannot check my setup status because the setup manager is not available."""
        
        # Get the current user's context
        context = get_discord_context()
        user_id = context.get('user_id')
        
        if not user_id:
            return "❌ **Setup Status: ERROR**\n\nI cannot determine your user context. Please use this command in a Discord server or DM."
        
        # Get all guild configurations
        try:
            all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
            # Filter for configured guilds where the current user is an admin
            configured_guilds = {
                guild_id: guild for guild_id, guild in all_guilds.items() 
                if guild.get('setup_complete', False) and guild.get('admin_user_id') == user_id
            }
        except Exception as e:
            return f"""❌ **Setup Status: ERROR**\n\nI encountered an error accessing guild configurations: {str(e)}

**What this means:**
• There was a problem accessing the setup data
• The setup manager may not be properly initialized
• Contact an administrator for assistance

**Current Status:** Unable to determine setup status."""
        
        if not configured_guilds:
            return f"""❌ **Setup Status: NOT CONFIGURED**\n\nI am **NOT** set up for any student groups where you are an admin.

**What this means:**
• You are not an admin of any configured clubs
• No Google Sheets are linked to your account
• You cannot manage meetings or tasks for any clubs

**To get started:**
• Run `/setup` to configure me for your group
• This will set up Google Sheets integration
• Configure admin permissions and channels
• Link your group's meeting and task systems

**Current Status:** Waiting for you to run `/setup` to configure your club."""
        
        # Show actual configured guilds
        num_guilds = len(configured_guilds)
        setup_info = f"""✅ **Setup Status: CONFIGURED**\n\nI am set up for **{num_guilds}** student group(s) where you are an admin!\n\n"""
        
        for guild_id, config in configured_guilds.items():
            guild_name = config.get('guild_name', 'Unknown Server')
            club_name = config.get('club_name', 'Unknown Club')
            admin_id = config.get('admin_user_id', 'Unknown')
            has_meetings = 'monthly_sheets' in config and 'meetings' in config.get('monthly_sheets', {})
            has_tasks = 'monthly_sheets' in config and 'tasks' in config.get('monthly_sheets', {})
            
            setup_info += f"**Group: {club_name}** (Server: {guild_name})\n"
            setup_info += f"• Admin: <@{admin_id}>\n"
            setup_info += f"• Meetings: {'✅ Configured' if has_meetings else '❌ Not configured'}\n"
            setup_info += f"• Tasks: {'✅ Configured' if has_tasks else '❌ Not configured'}\n\n"
        
        setup_info += """**What I can do for configured groups:**
• Schedule and manage meetings
• Create and track meeting minutes
• Assign and monitor tasks
• Send automated reminders
• Process natural language requests

**Example Questions:**
• "What meetings do I have today?"
• "Can you create meeting minutes?"
• "Send a reminder for the next meeting"
• "Show me the upcoming schedule"

**Current Status:** Fully operational for configured groups! 🎉"""
        
        return setup_info
        
    except Exception as e:
        return f"""❌ **Setup Status: ERROR**\n\nI encountered an error checking my setup status: {str(e)}

**What this means:**
• There was a problem accessing my configuration
• I may not be properly set up
• Contact an administrator for assistance

**Current Status:** Unable to determine setup status."""


@tool
def check_guild_setup_status(guild_id: str) -> str:
    """
    Check if the bot is set up for a specific Discord guild/server.
    Use this when users ask about setup status in a specific server.

    Args:
        guild_id: The Discord guild/server ID to check

    Returns:
        string: Setup status for the specific guild
    """
    try:
        # Import the Discord client to check actual setup status
        from discordbot.discord_client import BOT_INSTANCE
        
        if BOT_INSTANCE is None:
            return "❌ **Setup Status: ERROR**\n\nI cannot check setup status because the Discord bot is not running."
        
        if not hasattr(BOT_INSTANCE, 'setup_manager') or not BOT_INSTANCE.setup_manager:
            return "❌ **Setup Status: ERROR**\n\nI cannot check setup status because the setup manager is not available."
        
        # Get guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config:
            return f"""❌ **Setup Status: NOT CONFIGURED**\n\nThis server (ID: {guild_id}) is **NOT** configured.

**What this means:**
• No setup has been completed for this server
• No Google Sheets are linked
• No admin users are set up
• I cannot manage meetings or tasks for this server

**To get started:**
• An admin needs to run `/setup` in this server
• This will configure the bot for this specific server
• Set up Google Sheets integration
• Configure admin permissions and channels

**Current Status:** Waiting for setup by an administrator."""
        
        if not guild_config.get('setup_complete', False):
            return f"""⚠️ **Setup Status: INCOMPLETE**\n\nThis server (ID: {guild_id}) setup is **INCOMPLETE**.

**What this means:**
• Setup process was started but not finished
• Some components may be configured, others may be missing
• I may have limited functionality

**To complete setup:**
• Run `/setup` again to complete the configuration
• Ensure all required steps are completed
• Verify Google Sheets integration is working

**Current Status:** Setup incomplete - please run `/setup` to finish configuration."""
        
        # Server is fully configured
        guild_name = guild_config.get('guild_name', 'Unknown Server')
        club_name = guild_config.get('club_name', 'Unknown Club')
        admin_id = guild_config.get('admin_user_id', 'Unknown')
        has_meetings = 'monthly_sheets' in guild_config and 'meetings' in guild_config.get('monthly_sheets', {})
        has_tasks = 'monthly_sheets' in guild_config and 'tasks' in guild_config.get('monthly_sheets', {})
        
        return f"""✅ **Setup Status: CONFIGURED**\n\nThis server is **FULLY CONFIGURED**!

**Server Information:**
• Server: {guild_name} (ID: {guild_id})
• Club: {club_name}
• Admin: <@{admin_id}>
• Setup Complete: ✅ Yes

**Configured Components:**
• Meetings: {'✅ Configured' if has_meetings else '❌ Not configured'}
• Tasks: {'✅ Configured' if has_tasks else '❌ Not configured'}

**What I can do:**
• Schedule and manage meetings
• Create and track meeting minutes
• Assign and monitor tasks
• Send automated reminders
• Process natural language requests

**Current Status:** Fully operational! 🎉"""
        
    except Exception as e:
        return f"""❌ **Setup Status: ERROR**\n\nI encountered an error checking setup status for server {guild_id}: {str(e)}

**What this means:**
• There was a problem accessing the server configuration
• The setup manager may not be properly initialized
• Contact an administrator for assistance

**Current Status:** Unable to determine guild setup status."""


@tool
def ask_for_discord_mention(person_name: str) -> str:
    """
    Ask the user to provide the Discord mention for a person whose name doesn't match any executive.
    
    **ONLY USE THIS TOOL WHEN:**
    - You are actively creating a task with create_task_with_timer
    - The assignee name cannot be matched to an executive in the config
    - You need the Discord mention to complete the task creation
    
    **DO NOT USE THIS TOOL FOR:**
    - General questions about people
    - Questions like "is [person] an exec"
    - Simple conversations
    
    Args:
        person_name: The name of the person who needs a Discord mention
        
    Returns:
        str: Message asking for the Discord mention
    """
    from discordbot.discord_client import BOT_INSTANCE
    from ae_langchain.tools.context_manager import get_discord_context, get_user_admin_servers
    
    try:
        # Try to get guild context to show available execs
        context = get_discord_context()
        user_id = context.get('user_id')
        guild_id = context.get('guild_id')
        
        # Handle DM context
        if not guild_id and user_id:
            user_guilds = get_user_admin_servers(user_id)
            if len(user_guilds) == 1:
                guild_id = user_guilds[0]['guild_id']
        
        if guild_id and BOT_INSTANCE:
            # Get the guild configuration
            all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
            guild_config = all_guilds.get(guild_id)
            
            if guild_config:
                exec_members = guild_config.get('exec_members', [])
                exec_list = "\n".join([f"• {member['name']} ({member['role']})" for member in exec_members])
                
                return f"""❓ **Discord Mention Needed**

I couldn't find a matching executive for **{person_name}**.

**Available executives:**
{exec_list if exec_list else "No executives configured"}

**Options:**
• Use one of the executives listed above
• Provide the Discord mention: `{person_name}'s Discord is @username`

You can reply with: `{person_name}'s Discord is @username`"""
    
    except Exception as e:
        print(f"🔍 [DEBUG] Error in ask_for_discord_mention: {e}")
    
    # Fallback to simple message if we can't get guild context
    return f"❓ **Discord Mention Needed**\n\nI couldn't find a matching executive for **{person_name}**. Please provide their Discord mention (e.g., @username or <@123456789>) so I can create the task reminder properly.\n\nYou can reply with: `{person_name}'s Discord is @username`"


@tool
def get_exec_info(person_name: str = "") -> str:
    """
    Get information about club executives from the guild configuration.
    
    **USE THIS TOOL WHEN:**
    - User asks "is [person] an exec" or "who are the execs"
    - User wants to know about club leadership
    - User asks about specific executive members
    
    Args:
        person_name: Optional name to check if they're an executive (leave empty to get all execs)
        
    Returns:
        str: Information about executives
    """
    from discordbot.discord_client import BOT_INSTANCE
    
    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."
    
    try:
        # Get the Discord context from the current message
        context = get_discord_context()
        guild_id = context.get('guild_id')
        
        if not guild_id:
            return "❌ No Discord context found. Please use this command in a Discord server."
        
        # Get the guild configuration
        all_guilds = BOT_INSTANCE.setup_manager.status_manager.get_all_guilds()
        guild_config = all_guilds.get(guild_id)
        
        if not guild_config or not guild_config.get('setup_complete', False):
            return f"❌ Guild {guild_id} is not set up. Please run `/setup` first."
        
        exec_members = guild_config.get('exec_members', [])
        
        if not exec_members:
            return "❌ No executive members found in the configuration."
        
        if person_name:
            # Check if specific person is an exec
            person_lower = person_name.lower().strip()
            for member in exec_members:
                member_name = member.get('name', '').lower()
                if (person_lower == member_name or 
                    person_lower in member_name or 
                    any(person_lower == part.strip() for part in member_name.split())):
                    return f"✅ **Yes, {member.get('name')} is an executive member.**"
            
            return f"❌ **No, {person_name} is not listed as an executive member.**"
        else:
            # Return all exec members
            exec_list = []
            for member in exec_members:
                name = member.get('name', 'Unknown')
                role = member.get('role', 'Executive')
                exec_list.append(f"• **{name}** - {role}")
            
            return f"👥 **Executive Members:**\n\n" + "\n".join(exec_list)
            
    except Exception as e:
        return f"❌ Error getting executive information: {str(e)}"
