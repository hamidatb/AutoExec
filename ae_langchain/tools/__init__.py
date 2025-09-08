"""
Tools package for AutoExec agent.
Contains modularized tool functions organized by functionality.
"""

from .context_manager import (
    set_discord_context,
    get_discord_context,
    get_meetings_sheet_id,
    get_agent_executor_with_memory,
    clear_conversation_memory,
    clear_all_conversation_memories,
    get_memory_stats,
    get_user_admin_servers,
    handle_dm_server_selection,
    parse_server_context_from_query,
    get_server_context_info
)

from .meeting_tools import (
    create_meeting_mins,
    send_meeting_schedule,
    send_reminder_for_next_meeting,
    cleanup_past_meetings,
    get_meeting_reminder_info,
    get_all_upcoming_reminders,
    schedule_meeting,
    search_meetings_by_title,
    cancel_meeting,
    update_meeting,
    start_meeting_scheduling,
    create_meeting_with_timer
)

from .task_tools import (
    parse_meeting_minutes_action_items,
    send_tasks_by_person,
    search_tasks_by_title,
    complete_task,
    create_tasks_from_meeting_minutes,
    summarize_last_meeting
)

from .timer_tools import (
    create_task_with_timer,
    list_active_timers,
    clear_all_timers
)

from .setup_tools import (
    get_setup_info,
    get_meeting_sheet_info,
    get_task_sheet_info,
    get_channel_info,
    get_user_setup_status,
    get_club_setup_info,
    check_guild_setup_status,
    ask_for_discord_mention,
    get_exec_info
)

from .discord_tools import (
    start_discord_bot,
    send_meeting_mins_summary,
    send_output_to_discord,
    send_reminder_to_person,
    send_announcement,
    get_pending_announcements,
    clear_pending_announcements
)

from .utility_tools import (
    parse_due_date,
    parse_duration,
    parse_meeting_time,
    find_user_by_name,
    create_task_timers,
    create_meeting_timers
)

__all__ = [
    # Context manager
    'set_discord_context',
    'get_discord_context', 
    'get_meetings_sheet_id',
    'get_agent_executor_with_memory',
    'clear_conversation_memory',
    'clear_all_conversation_memories',
    'get_memory_stats',
    'get_user_admin_servers',
    'handle_dm_server_selection',
    'parse_server_context_from_query',
    'get_server_context_info',
    
    # Meeting tools
    'create_meeting_mins',
    'send_meeting_schedule',
    'send_reminder_for_next_meeting',
    'cleanup_past_meetings',
    'get_meeting_reminder_info',
    'get_all_upcoming_reminders',
    'schedule_meeting',
    'search_meetings_by_title',
    'cancel_meeting',
    'update_meeting',
    'start_meeting_scheduling',
    'create_meeting_with_timer',
    
    # Task tools
    'create_task_with_timer',
    'list_active_timers',
    'clear_all_timers',
    'parse_meeting_minutes_action_items',
    'send_tasks_by_person',
    'search_tasks_by_title',
    'complete_task',
    'create_tasks_from_meeting_minutes',
    'summarize_last_meeting',
    
    # Setup tools
    'get_setup_info',
    'get_meeting_sheet_info',
    'get_task_sheet_info',
    'get_channel_info',
    'get_user_setup_status',
    'get_club_setup_info',
    'check_guild_setup_status',
    'ask_for_discord_mention',
    'get_exec_info',
    
    # Discord tools
    'start_discord_bot',
    'send_meeting_mins_summary',
    'send_output_to_discord',
    'send_reminder_to_person',
    'send_announcement',
    'get_pending_announcements',
    'clear_pending_announcements',
    
    # Utility tools
    'parse_due_date',
    'parse_duration',
    'parse_meeting_time',
    'find_user_by_name',
    'create_task_timers',
    'create_meeting_timers'
]
