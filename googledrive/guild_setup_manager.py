import json
import os
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

class GuildSetupStatusManager:
    """
    Manages setup status persistence using JSON file storage.
    Handles multiple guilds with separate configurations.
    """
    
    def __init__(self, status_file_path: str = "guild_setup_status.json"):
        """
        Initialize the guild setup status manager.
        
        Args:
            status_file_path: Path to the JSON file storing setup status
        """
        self.status_file_path = Path(status_file_path)
        self._ensure_status_file_exists()
    
    def _ensure_status_file_exists(self):
        """Ensure the status file exists with proper structure."""
        if not self.status_file_path.exists():
            initial_data = {
                "guilds": {},
                "last_updated": datetime.now().isoformat()
            }
            self._write_status_file(initial_data)
    
    def _read_status_file(self) -> Dict[str, Any]:
        """Read the status file and return its contents."""
        try:
            with open(self.status_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"❌ [GUILD SETUP STATUS] Error reading status file: {e}")
            # Return default structure if file is corrupted
            return {"guilds": {}, "last_updated": datetime.now().isoformat()}
    
    def _write_status_file(self, data: Dict[str, Any]):
        """Write data to the status file."""
        try:
            data["last_updated"] = datetime.now().isoformat()
            with open(self.status_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"🔍 [GUILD SETUP STATUS] Status file updated successfully")
        except Exception as e:
            print(f"❌ [GUILD SETUP STATUS] Error writing status file: {e}")
            raise
    
    def is_setup_complete(self, guild_id: str) -> bool:
        """
        Check if setup is complete for a given guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if setup is complete, False otherwise
        """
        print(f"🔍 [GUILD SETUP STATUS] Checking setup status for guild: {guild_id}")
        
        status_data = self._read_status_file()
        print(f"🔍 [GUILD SETUP STATUS] Status file contents: {status_data}")
        
        guilds = status_data.get("guilds", {})
        print(f"🔍 [GUILD SETUP STATUS] All guilds in file: {list(guilds.keys())}")
        
        guild_data = guilds.get(guild_id)
        print(f"🔍 [GUILD SETUP STATUS] Guild data for guild {guild_id}: {guild_data}")
        
        if not guild_data:
            print(f"❌ [GUILD SETUP STATUS] No setup data found for guild {guild_id}")
            return False
        
        is_complete = guild_data.get("setup_complete", False)
        print(f"🔍 [GUILD SETUP STATUS] Setup status for guild {guild_id}: {is_complete}")
        return is_complete
    
    def get_guild_config(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the complete guild configuration.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Guild configuration dict or None if not found
        """
        status_data = self._read_status_file()
        guild_data = status_data.get("guilds", {}).get(guild_id)
        
        if not guild_data:
            print(f"🔍 [GUILD SETUP STATUS] No guild config found for guild {guild_id}")
            return None
        
        print(f"🔍 [GUILD SETUP STATUS] Retrieved guild config for guild {guild_id}")
        return guild_data
    
    def mark_setup_complete(self, guild_id: str, guild_config: Dict[str, Any]):
        """
        Mark setup as complete and store guild configuration.
        
        Args:
            guild_id: Discord guild ID
            guild_config: Complete guild configuration data
        """
        status_data = self._read_status_file()
        
        # Add completion timestamp
        guild_config["setup_complete"] = True
        guild_config["completed_at"] = datetime.now().isoformat()
        
        # Store the guild configuration
        status_data["guilds"][guild_id] = guild_config
        
        self._write_status_file(status_data)
        print(f"🔍 [GUILD SETUP STATUS] Setup marked complete for guild {guild_id}, club: {guild_config.get('club_name', 'Unknown')}")
    
    def is_admin(self, user_id: str, guild_id: str) -> bool:
        """
        Check if a user is the admin of a specific guild.
        
        Args:
            user_id: User ID to check
            guild_id: Guild ID
            
        Returns:
            True if user is the admin, False otherwise
        """
        guild_data = self.get_guild_config(guild_id)
        if not guild_data:
            return False
        
        admin_id = guild_data.get("admin_user_id")
        is_admin = user_id == admin_id
        print(f"🔍 [GUILD SETUP STATUS] Admin check: user {user_id} is admin of guild {guild_id}: {is_admin}")
        return is_admin
    
    def can_modify_config(self, user_id: str, guild_id: str) -> bool:
        """
        Check if a user can modify a guild's configuration.
        Only the guild admin can modify their guild's config.
        
        Args:
            user_id: User ID requesting to modify
            guild_id: Guild ID
            
        Returns:
            True if user can modify, False otherwise
        """
        can_modify = self.is_admin(user_id, guild_id)
        
        if not can_modify:
            print(f"❌ [GUILD SETUP STATUS] Access denied: user {user_id} is not admin of guild {guild_id}")
        else:
            print(f"✅ [GUILD SETUP STATUS] Access granted: user {user_id} can modify guild {guild_id}")
        
        return can_modify
    
    def update_guild_config(self, guild_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update guild configuration. Only the admin can make changes.
        
        Args:
            guild_id: Guild ID
            user_id: User ID requesting the update
            updates: Dictionary of configuration updates
            
        Returns:
            True if update was successful, False otherwise
        """
        if not self.can_modify_config(user_id, guild_id):
            return False
        
        status_data = self._read_status_file()
        guild_data = status_data.get("guilds", {}).get(guild_id)
        
        if not guild_data:
            print(f"❌ [GUILD SETUP STATUS] No guild found for guild {guild_id}")
            return False
        
        # Update the configuration
        guild_data.update(updates)
        guild_data["last_modified"] = datetime.now().isoformat()
        guild_data["modified_by"] = user_id
        
        status_data["guilds"][guild_id] = guild_data
        self._write_status_file(status_data)
        
        print(f"✅ [GUILD SETUP STATUS] Guild config updated for guild {guild_id}")
        return True
    
    def get_all_guilds(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all guild configurations.
        
        Returns:
            Dictionary of all guild configurations
        """
        status_data = self._read_status_file()
        return status_data.get("guilds", {})
    
    def remove_guild(self, guild_id: str, requesting_user_id: str) -> bool:
        """
        Remove a guild configuration. Only the admin can remove their guild.
        
        Args:
            guild_id: Guild ID to remove
            requesting_user_id: User ID requesting the removal
            
        Returns:
            True if removal was successful, False otherwise
        """
        if not self.can_modify_config(requesting_user_id, guild_id):
            return False
        
        status_data = self._read_status_file()
        
        if guild_id in status_data.get("guilds", {}):
            del status_data["guilds"][guild_id]
            self._write_status_file(status_data)
            print(f"✅ [GUILD SETUP STATUS] Guild removed for guild {guild_id}")
            return True
        
        print(f"❌ [GUILD SETUP STATUS] No guild found to remove for guild {guild_id}")
        return False
    
    def get_setup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about setup status.
        
        Returns:
            Dictionary with setup statistics
        """
        status_data = self._read_status_file()
        guilds = status_data.get("guilds", {})
        
        total_guilds = len(guilds)
        completed_setups = sum(1 for guild in guilds.values() if guild.get("setup_complete", False))
        
        return {
            "total_guilds": total_guilds,
            "completed_setups": completed_setups,
            "incomplete_setups": total_guilds - completed_setups,
            "last_updated": status_data.get("last_updated", "Unknown")
        }
