"""
Utility tools module for AutoExec agent.
Contains helper functions for date parsing, user finding, and timer creation.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import re


def parse_due_date(date_str: str) -> Optional[datetime]:
    """Parse natural language due dates into datetime objects."""
    date_str = date_str.strip().lower()
    now = datetime.now(timezone.utc)
    
    # Handle specific date formats
    try:
        # Try ISO format first
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            if ' ' in date_str and len(date_str.split()) >= 2:
                # Has time
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            else:
                # Just date, assume end of day
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=23, minute=59, tzinfo=timezone.utc)
            
            # Fix obvious year mistakes (e.g., 2023 when we're in 2025)
            if parsed_date.year < now.year - 1:
                parsed_date = parsed_date.replace(year=now.year)
            
            return parsed_date
    except:
        pass
    
    # Handle relative dates
    if 'tomorrow' in date_str:
        return (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
    elif 'next week' in date_str:
        return (now + timedelta(weeks=1)).replace(hour=17, minute=0, second=0, microsecond=0)
    elif 'next friday' in date_str:
        days_ahead = 4 - now.weekday()  # Friday is 4
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return (now + timedelta(days=days_ahead)).replace(hour=17, minute=0, second=0, microsecond=0)
    
    # Handle month day formats (with ordinal suffixes like "6th", "3rd", "1st", "2nd")
    month_patterns = [
        (r'september (\d{1,2})(?:st|nd|rd|th)?', 9),
        (r'october (\d{1,2})(?:st|nd|rd|th)?', 10),
        (r'november (\d{1,2})(?:st|nd|rd|th)?', 11),
        (r'december (\d{1,2})(?:st|nd|rd|th)?', 12),
        (r'january (\d{1,2})(?:st|nd|rd|th)?', 1),
        (r'february (\d{1,2})(?:st|nd|rd|th)?', 2),
        (r'march (\d{1,2})(?:st|nd|rd|th)?', 3),
        (r'april (\d{1,2})(?:st|nd|rd|th)?', 4),
        (r'may (\d{1,2})(?:st|nd|rd|th)?', 5),
        (r'june (\d{1,2})(?:st|nd|rd|th)?', 6),
        (r'july (\d{1,2})(?:st|nd|rd|th)?', 7),
        (r'august (\d{1,2})(?:st|nd|rd|th)?', 8),
    ]
    
    for pattern, month in month_patterns:
        match = re.search(pattern, date_str)
        if match:
            day = int(match.group(1))
            year = now.year
            # If the month/day has already passed this year, use next year
            if month < now.month or (month == now.month and day <= now.day):
                year += 1
            
            print(f"🔍 [DEBUG] Month/day parsing: month={month}, day={day}, year={year}")
            result = datetime(year, month, day, 17, 0, 0, tzinfo=timezone.utc)
            print(f"🔍 [DEBUG] Month/day result: {result}")
            return result
    
    return None


def parse_duration(duration_str: str) -> Optional[int]:
    """
    Parse duration string and return minutes.
    
    Args:
        duration_str: Duration in natural language (e.g., "1 hour", "2 hours", "30 minutes", "1.5 hours")
        
    Returns:
        int: Duration in minutes, or None if parsing failed
    """
    duration_str = duration_str.lower().strip()
    
    # Handle various duration formats
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*hours?', lambda m: float(m.group(1)) * 60),
        (r'(\d+(?:\.\d+)?)\s*hrs?', lambda m: float(m.group(1)) * 60),
        (r'(\d+(?:\.\d+)?)\s*minutes?', lambda m: float(m.group(1))),
        (r'(\d+(?:\.\d+)?)\s*mins?', lambda m: float(m.group(1))),
        (r'(\d+(?:\.\d+)?)\s*h', lambda m: float(m.group(1)) * 60),
        (r'(\d+(?:\.\d+)?)\s*m', lambda m: float(m.group(1))),
    ]
    
    for pattern, converter in patterns:
        match = re.search(pattern, duration_str)
        if match:
            try:
                minutes = int(converter(match))
                return max(1, minutes)  # Ensure at least 1 minute
            except (ValueError, TypeError):
                continue
    
    return None


def parse_meeting_time(time_str: str) -> datetime:
    """Parse natural language meeting times into datetime objects."""
    time_str = time_str.strip().lower()
    now = datetime.now(timezone.utc)
    
    print(f"🔍 [DEBUG] parse_meeting_time called with: '{time_str}'")
    print(f"🔍 [DEBUG] Current time: {now} (year: {now.year})")
    
    # Handle ISO format
    try:
        if re.match(r'\d{4}-\d{2}-\d{2}', time_str):
            if ' ' in time_str and len(time_str.split()) >= 2:
                parsed_date = datetime.strptime(time_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                # Safety check: if the year is before current year, assume it should be current year
                if parsed_date.year < now.year:
                    print(f"🔍 [DEBUG] Correcting year from {parsed_date.year} to {now.year}")
                    parsed_date = parsed_date.replace(year=now.year)
                return parsed_date
    except:
        pass
    
    # Handle relative times
    if 'tomorrow' in time_str:
        base_date = now + timedelta(days=1)
        print(f"🔍 [DEBUG] Tomorrow parsing: base_date={base_date}")
    elif 'next week' in time_str:
        base_date = now + timedelta(weeks=1)
        print(f"🔍 [DEBUG] Next week parsing: base_date={base_date}")
    elif 'next friday' in time_str:
        days_ahead = 4 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        base_date = now + timedelta(days=days_ahead)
        print(f"🔍 [DEBUG] Next friday parsing: base_date={base_date}")
    else:
        base_date = now
        print(f"🔍 [DEBUG] Using current date: base_date={base_date}")
    
    # Extract time
    time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?', time_str)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        period = time_match.group(3)
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        result = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        print(f"🔍 [DEBUG] Final result with time: {result}")
        return result
    
    # Default to 2 PM if no time specified
    result = base_date.replace(hour=14, minute=0, second=0, microsecond=0)
    print(f"🔍 [DEBUG] Final result (default time): {result}")
    return result


def find_user_by_name(name: str, guild_config: dict) -> str:
    """Find a user's Discord mention by their name."""
    exec_members = guild_config.get('exec_members', [])
    name_lower = name.lower().strip()
    
    print(f"🔍 [DEBUG] find_user_by_name called with: '{name}' -> '{name_lower}'")
    print(f"🔍 [DEBUG] Exec members: {exec_members}")
    
    # Remove any Discord mention formatting if present
    name_lower = name_lower.replace('<@', '').replace('>', '').replace('@', '')
    
    for member in exec_members:
        member_name = member.get('name', '').lower()
        print(f"🔍 [DEBUG] Checking member: '{member_name}'")
        
        # Check if the provided name matches the first name, last name, or full name
        if (name_lower == member_name or  # Exact match
            name_lower in member_name or  # Partial match (e.g., "hamidat" in "hamidat bello")
            any(name_lower == part.strip() for part in member_name.split())):  # First/last name match
            discord_id = member.get('discord_id', '')
            if discord_id:
                result = f"<@{discord_id}>"
                print(f"🔍 [DEBUG] Found match! Returning: {result}")
                return result
    
    # If not found in exec members, return a placeholder that indicates we need the mention
    result = f"NEED_MENTION_FOR_{name}"
    print(f"🔍 [DEBUG] No match found. Returning: {result}")
    return result


def convert_names_to_mentions(mention_string: str, guild_config: dict) -> str:
    """
    Convert a string of names to Discord mentions.
    
    Args:
        mention_string: String containing names (e.g., "Andrew, Sanika" or "@everyone")
        guild_config: Guild configuration containing exec members
        
    Returns:
        String with Discord mentions (e.g., "<@123456789> <@987654321>" or "@everyone")
    """
    if not mention_string or mention_string.lower() == '@everyone':
        return '@everyone'
    
    # Split by comma and process each name
    names = [name.strip() for name in mention_string.split(',')]
    mentions = []
    
    for name in names:
        if name.lower() == '@everyone':
            mentions.append('@everyone')
        elif name.startswith('<@') and name.endswith('>'):
            # Already a Discord mention, keep as is
            mentions.append(name)
        else:
            # Convert name to mention
            mention = find_user_by_name(name, guild_config)
            if mention.startswith('NEED_MENTION_FOR_'):
                # If we can't find the user, keep the original name
                mentions.append(name)
            else:
                mentions.append(mention)
    
    return ' '.join(mentions)


def create_task_timers(task_data: dict, guild_config: dict) -> int:
    """Create timers for a task and return the count."""
    from discordbot.discord_client import BOT_INSTANCE
    
    try:
        due_at = datetime.fromisoformat(task_data['due_at'])
        task_id = task_data.get('task_id', 'unknown')
        guild_id = task_data.get('guild_id', '')
        
        # Create timer types
        timer_types = [
            ('task_reminder_24h', due_at - timedelta(hours=24)),
            ('task_reminder_2h', due_at - timedelta(hours=2)),
            ('task_overdue', due_at),
            ('task_escalate', due_at + timedelta(hours=48))
        ]
        
        config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
        if not config_spreadsheet_id:
            return 0
        
        # Get the assignee mention
        assignee_name = task_data.get('owner_name', '')
        assignee_mention = find_user_by_name(assignee_name, guild_config)
        
        timer_count = 0
        for timer_type, fire_at in timer_types:
            timer_id = f"{task_id}_{timer_type}"
            timer_data = {
                'id': timer_id,
                'guild_id': guild_id,
                'type': timer_type,
                'ref_type': 'task',
                'ref_id': task_id,
                'fire_at_utc': fire_at.isoformat(),
                'channel_id': task_data.get('channel_id', ''),
                'state': 'active',
                'title': task_data.get('title', 'Unknown Task'),
                'mention': assignee_mention
            }
            
            success = BOT_INSTANCE.sheets_manager.add_timer(config_spreadsheet_id, timer_data)
            if success:
                timer_count += 1
        
        return timer_count
        
    except Exception as e:
        print(f"Error creating task timers: {e}")
        return 0


def create_meeting_timers(meeting_data: dict, guild_config: dict, mention: str = '') -> int:
    """Create timers for a meeting and return the count."""
    from discordbot.discord_client import BOT_INSTANCE
    
    try:
        start_at = datetime.fromisoformat(meeting_data['start_at_utc'])
        meeting_id = meeting_data.get('meeting_id', 'unknown')
        guild_id = meeting_data.get('guild_id', '')
        
        # Convert names to Discord mentions
        converted_mention = convert_names_to_mentions(mention, guild_config)
        
        # Create timer types
        timer_types = [
            ('meeting_reminder_2h', start_at - timedelta(hours=2)),
            ('meeting_start', start_at)
        ]
        
        config_spreadsheet_id = guild_config.get('config_spreadsheet_id')
        if not config_spreadsheet_id:
            return 0
        
        timer_count = 0
        for timer_type, fire_at in timer_types:
            timer_id = f"{meeting_id}_{timer_type}"
            timer_data = {
                'id': timer_id,
                'guild_id': guild_id,
                'type': timer_type,
                'ref_type': 'meeting',
                'ref_id': meeting_id,
                'fire_at_utc': fire_at.isoformat(),
                'channel_id': meeting_data.get('channel_id', ''),
                'state': 'active',
                'title': meeting_data.get('title', 'Unknown Meeting'),
                'mention': converted_mention  # Use the converted mention
            }
            
            success = BOT_INSTANCE.sheets_manager.add_timer(config_spreadsheet_id, timer_data)
            if success:
                timer_count += 1
        
        return timer_count
        
    except Exception as e:
        print(f"Error creating meeting timers: {e}")
        return 0
