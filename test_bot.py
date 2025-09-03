#!/usr/bin/env python3
"""
Test script for the Club Exec Task Manager Bot.
This script tests basic functionality without actually running the bot.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing module imports...")
    
    try:
        from config import Config
        print("✅ Config module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Config: {e}")
        return False
    
    try:
        from googledrive.sheets_manager import ClubSheetsManager
        print("✅ ClubSheetsManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ClubSheetsManager: {e}")
        return False
    
    try:
        from googledrive.meeting_manager import MeetingManager
        print("✅ MeetingManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import MeetingManager: {e}")
        return False
    
    try:
        from googledrive.task_manager import TaskManager
        print("✅ TaskManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import TaskManager: {e}")
        return False
    
    try:
        from googledrive.setup_manager import SetupManager
        print("✅ SetupManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import SetupManager: {e}")
        return False
    
    try:
        from googledrive.minutes_parser import MinutesParser
        print("✅ MinutesParser imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import MinutesParser: {e}")
        return False
    
    try:
        from discordbot.discord_client import ClubExecBot
        print("✅ ClubExecBot imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ClubExecBot: {e}")
        return False
    
    return True

def test_config():
    """Test configuration loading."""
    print("\n🔧 Testing configuration...")
    
    try:
        from config import Config
        Config()
        
        # Test required fields
        if not Config.DISCORD_TOKEN:
            print("⚠️ DISCORD_BOT_TOKEN not set (will be required for bot to run)")
        else:
            print("✅ DISCORD_BOT_TOKEN is set")
        
        print(f"✅ Club Name: {Config.CLUB_NAME}")
        print(f"✅ Timezone: {Config.TIMEZONE}")
        print(f"✅ Task Reminder Channel: {Config.TASK_REMINDER_CHANNEL_ID}")
        print(f"✅ Meeting Reminder Channel: {Config.MEETING_REMINDER_CHANNEL_ID}")
        print(f"✅ Escalation Channel: {Config.ESCALATION_CHANNEL_ID}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_google_drive_setup():
    """Test Google Drive integration setup."""
    print("\n📁 Testing Google Drive setup...")
    
    service_key_path = Path("googledrive/servicekey.json")
    
    if not service_key_path.exists():
        print("⚠️ Google service key not found at googledrive/servicekey.json")
        print("   This is required for Google Drive integration")
        return False
    else:
        print("✅ Google service key found")
        
        # Check if it's a valid JSON file
        try:
            import json
            with open(service_key_path, 'r') as f:
                key_data = json.load(f)
            
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in key_data]
            
            if missing_fields:
                print(f"❌ Service key missing required fields: {missing_fields}")
                return False
            else:
                print("✅ Service key appears valid")
                return True
                
        except Exception as e:
            print(f"❌ Error reading service key: {e}")
            return False

def test_dependencies():
    """Test that all required dependencies are installed."""
    print("\n📦 Testing dependencies...")
    
    required_packages = [
        ('discord', 'discord'),
        ('googleapiclient', 'googleapiclient'),
        ('google.auth', 'google.auth'),
        ('python-dotenv', 'dotenv'),
        ('python-dateutil', 'dateutil'),
        ('pytz', 'pytz')
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name} is installed")
        except ImportError:
            print(f"❌ {package_name} is missing")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("   Install them with: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Run all tests."""
    print("🚀 Club Exec Task Manager Bot - Test Suite")
    print("=" * 50)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("Google Drive Setup", test_google_drive_setup)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The bot should be ready to run.")
        print("\nTo start the bot:")
        print("1. Ensure your .env file is configured")
        print("2. Run: python discordbot/discord_client.py")
    else:
        print("⚠️ Some tests failed. Please fix the issues before running the bot.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
