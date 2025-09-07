"""
Global variables for the AutoExec agent.
This module contains shared global variables used across the application.
"""

# Global variable for pending announcements
_pending_announcements = []

# Global variable for Discord context
_discord_context = {}

# Server-specific agent executors with isolated memory
_server_agent_executors = {}

# DM-specific agent executors for users who are admin of multiple servers
_dm_agent_executors = {}
