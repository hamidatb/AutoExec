#!/usr/bin/env python3
"""
Startup script for the Club Exec Task Manager Bot.
This script provides a user-friendly way to start the bot with proper setup guidance.
"""

import sys
import os
from pathlib import Path

def check_environment():
    """Check if the environment is properly configured."""
    print("🔍 Checking environment setup...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("   Please copy env.example to .env and configure it:")
        print("   cp env.example .env")
        print("   nano .env")
        return False
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Virtual environment not detected")
        print("   It's recommended to use a virtual environment:")
        print("   python -m venv venv")
        print("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        print("   pip install -r requirements.txt")
        print()
    
    # Check if Google service key exists
    service_key = Path("googledrive/servicekey.json")
    if not service_key.exists():
        print("⚠️  Google service key not found")
        print("   Please place your service account key at:")
        print("   googledrive/servicekey.json")
        print()
    
    return True

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("📦 Checking dependencies...")
    
    try:
        import discord
        print(f"✅ discord.py {discord.__version__}")
    except ImportError:
        print("❌ discord.py not installed")
        print("   Run: pip install -r requirements.txt")
        return False
    
    try:
        import googleapiclient
        print("✅ google-api-python-client")
    except ImportError:
        print("❌ google-api-python-client not installed")
        print("   Run: pip install -r requirements.txt")
        return False
    
    try:
        import dotenv
        print("✅ python-dotenv")
    except ImportError:
        print("❌ python-dotenv not installed")
        print("   Run: pip install -r requirements.txt")
        return False
    
    return True

def start_bot():
    """Start the bot."""
    print("🚀 Starting Club Exec Task Manager Bot...")
    
    try:
        # Import and start the bot
        from discordbot.discord_client import run_bot
        run_bot()
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your .env file configuration")
        print("2. Verify your Discord bot token is correct")
        print("3. Ensure the bot has proper permissions in your server")
        print("4. Check that Google service account is properly configured")
        return 1
    
    return 0

def main():
    """Main startup function."""
    print("🤖 Club Exec Task Manager Bot")
    print("=" * 40)
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed. Please fix the issues above.")
        return 1
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Dependency check failed. Please install missing packages.")
        return 1
    
    print("✅ Environment check passed!")
    print()
    
    # Start the bot
    return start_bot()

if __name__ == "__main__":
    sys.exit(main())
