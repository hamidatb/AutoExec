import json
import os
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

class SetupStatusManager:
    """
    Manages setup status persistence using JSON file storage.
    Handles multiple clubs with separate configurations.
    """
    
    def __init__(self, status_file_path: str = "setup_status.json"):
        """
        Initialize the setup status manager.
        
        Args:
            status_file_path: Path to the JSON file storing setup status
        """
        self.status_file_path = Path(status_file_path)
        self._ensure_status_file_exists()
    
    def _ensure_status_file_exists(self):
        """Ensure the status file exists with proper structure."""
        if not self.status_file_path.exists():
            initial_data = {
                "clubs": {},
                "last_updated": datetime.now().isoformat()
            }
            self._write_status_file(initial_data)
    
    def _read_status_file(self) -> Dict[str, Any]:
        """Read the status file and return its contents."""
        try:
            with open(self.status_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"❌ [SETUP STATUS] Error reading status file: {e}")
            # Return default structure if file is corrupted
            return {"clubs": {}, "last_updated": datetime.now().isoformat()}
    
    def _write_status_file(self, data: Dict[str, Any]):
        """Write data to the status file."""
        try:
            data["last_updated"] = datetime.now().isoformat()
            with open(self.status_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"🔍 [SETUP STATUS] Status file updated successfully")
        except Exception as e:
            print(f"❌ [SETUP STATUS] Error writing status file: {e}")
            raise
    
    def is_setup_complete(self, user_id: str) -> bool:
        """
        Check if setup is complete for a given user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if setup is complete, False otherwise
        """
        status_data = self._read_status_file()
        club_data = status_data.get("clubs", {}).get(user_id)
        
        if not club_data:
            print(f"🔍 [SETUP STATUS] No setup data found for user {user_id}")
            return False
        
        is_complete = club_data.get("setup_complete", False)
        print(f"🔍 [SETUP STATUS] Setup status for user {user_id}: {is_complete}")
        return is_complete
    
    def get_club_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the complete club configuration for a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Club configuration dict or None if not found
        """
        status_data = self._read_status_file()
        club_data = status_data.get("clubs", {}).get(user_id)
        
        if not club_data:
            print(f"🔍 [SETUP STATUS] No club config found for user {user_id}")
            return None
        
        print(f"🔍 [SETUP STATUS] Retrieved club config for user {user_id}")
        return club_data
    
    def mark_setup_complete(self, user_id: str, club_config: Dict[str, Any]):
        """
        Mark setup as complete and store club configuration.
        
        Args:
            user_id: Discord user ID
            club_config: Complete club configuration data
        """
        status_data = self._read_status_file()
        
        # Add completion timestamp
        club_config["setup_complete"] = True
        club_config["completed_at"] = datetime.now().isoformat()
        
        # Store the club configuration
        status_data["clubs"][user_id] = club_config
        
        self._write_status_file(status_data)
        print(f"🔍 [SETUP STATUS] Setup marked complete for user {user_id}, club: {club_config.get('club_name', 'Unknown')}")
    
    def is_admin(self, user_id: str, club_user_id: str) -> bool:
        """
        Check if a user is the admin of a specific club.
        
        Args:
            user_id: User ID to check
            club_user_id: Club's admin user ID
            
        Returns:
            True if user is the admin, False otherwise
        """
        is_admin = user_id == club_user_id
        print(f"🔍 [SETUP STATUS] Admin check: user {user_id} is admin of club {club_user_id}: {is_admin}")
        return is_admin
    
    def can_modify_config(self, user_id: str, target_club_user_id: str) -> bool:
        """
        Check if a user can modify a club's configuration.
        Only the club admin can modify their club's config.
        
        Args:
            user_id: User ID requesting to modify
            target_club_user_id: Club's admin user ID
            
        Returns:
            True if user can modify, False otherwise
        """
        can_modify = self.is_admin(user_id, target_club_user_id)
        
        if not can_modify:
            print(f"❌ [SETUP STATUS] Access denied: user {user_id} is not admin of club {target_club_user_id}")
        else:
            print(f"✅ [SETUP STATUS] Access granted: user {user_id} can modify club {target_club_user_id}")
        
        return can_modify
    
    def update_club_config(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update club configuration. Only the admin can make changes.
        
        Args:
            user_id: User ID requesting the update
            updates: Dictionary of configuration updates
            
        Returns:
            True if update was successful, False otherwise
        """
        status_data = self._read_status_file()
        club_data = status_data.get("clubs", {}).get(user_id)
        
        if not club_data:
            print(f"❌ [SETUP STATUS] No club found for user {user_id}")
            return False
        
        # Check if user is the admin
        if not self.is_admin(user_id, club_data.get("admin_id", "")):
            print(f"❌ [SETUP STATUS] User {user_id} is not authorized to modify this club's config")
            return False
        
        # Update the configuration
        club_data.update(updates)
        club_data["last_modified"] = datetime.now().isoformat()
        club_data["modified_by"] = user_id
        
        status_data["clubs"][user_id] = club_data
        self._write_status_file(status_data)
        
        print(f"✅ [SETUP STATUS] Club config updated for user {user_id}")
        return True
    
    def get_all_clubs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all club configurations.
        
        Returns:
            Dictionary of all club configurations
        """
        status_data = self._read_status_file()
        return status_data.get("clubs", {})
    
    def remove_club(self, user_id: str, requesting_user_id: str) -> bool:
        """
        Remove a club configuration. Only the admin can remove their club.
        
        Args:
            user_id: Club admin user ID to remove
            requesting_user_id: User ID requesting the removal
            
        Returns:
            True if removal was successful, False otherwise
        """
        if not self.can_modify_config(requesting_user_id, user_id):
            return False
        
        status_data = self._read_status_file()
        
        if user_id in status_data.get("clubs", {}):
            del status_data["clubs"][user_id]
            self._write_status_file(status_data)
            print(f"✅ [SETUP STATUS] Club removed for user {user_id}")
            return True
        
        print(f"❌ [SETUP STATUS] No club found to remove for user {user_id}")
        return False
    
    def get_setup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about setup status.
        
        Returns:
            Dictionary with setup statistics
        """
        status_data = self._read_status_file()
        clubs = status_data.get("clubs", {})
        
        total_clubs = len(clubs)
        completed_setups = sum(1 for club in clubs.values() if club.get("setup_complete", False))
        
        return {
            "total_clubs": total_clubs,
            "completed_setups": completed_setups,
            "incomplete_setups": total_clubs - completed_setups,
            "last_updated": status_data.get("last_updated", "Unknown")
        }
