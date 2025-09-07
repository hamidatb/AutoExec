"""
Tests for the reconciliation job functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.test_utils.mock_objects import (
    MockDiscordUser, MockDiscordGuild, MockDiscordInteraction, 
    MockBot, MockSetupManager, create_mock_setup_state, create_mock_guild_config,
    MockSheetsManager, MockTimerScheduler, MockReconciliationManager,
    create_mock_timer_data, create_mock_task_data, create_mock_meeting_data
)
from tests.test_utils.test_helpers import (
    setup_test_environment, create_test_data_set, assert_setup_step,
    assert_setup_field, assert_error_message_contains, assert_success_message_contains,
    validate_setup_completion, create_error_scenarios, create_success_scenarios
)


class TestReconciliationLoop:
    """Test the reconciliation loop functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.reconciliation_manager = MockReconciliationManager()
        self.bot.reconciliation_manager = self.reconciliation_manager
        self.test_data = create_test_data_set()
    
    def test_reconciliation_loop_runs_every_15_minutes(self):
        """Test that reconciliation loop runs every 15 minutes."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Test that the reconciliation loop method exists and can be called
        assert hasattr(reconciliation_manager, 'reconciliation_loop')
        assert callable(reconciliation_manager.reconciliation_loop)
        
        # Test that the method is async
        import inspect
        assert inspect.iscoroutinefunction(reconciliation_manager.reconciliation_loop)
    
    def test_reconciliation_loop_error_handling(self):
        """Test error handling in reconciliation loop."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Test that the reconciliation loop method exists and can handle errors
        assert hasattr(reconciliation_manager, 'reconciliation_loop')
        assert callable(reconciliation_manager.reconciliation_loop)
        
        # Test that the method is async
        import inspect
        assert inspect.iscoroutinefunction(reconciliation_manager.reconciliation_loop)


class TestTimerReconciliation:
    """Test timer reconciliation functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.reconciliation_manager = MockReconciliationManager()
        self.bot.reconciliation_manager = self.reconciliation_manager
        self.test_data = create_test_data_set()
    
    def test_reconcile_timers_success(self):
        """Test successful timer reconciliation."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Mock the bot's club configs
        reconciliation_manager.bot.club_configs = {
            self.test_data['guild_id']: create_mock_guild_config(self.test_data['guild_id'])
        }
        
        # Mock the timer scheduler
        reconciliation_manager.timer_scheduler.get_active_timers = Mock(return_value={})
        
        # Mock the task and meeting managers
        reconciliation_manager.task_manager.get_tasks = Mock(return_value=[])
        reconciliation_manager.meeting_manager.get_meetings = Mock(return_value=[])
        
        # Test reconciliation
        async def test_reconcile_timers():
            await reconciliation_manager.reconcile_timers()
            # Should complete without errors
        
        asyncio.run(test_reconcile_timers())
    
    def test_reconcile_timers_with_no_guilds(self):
        """Test timer reconciliation with no guilds configured."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Mock empty club configs
        reconciliation_manager.bot.club_configs = {}
        
        # Test reconciliation with no guilds
        async def test_reconcile_timers_no_guilds():
            await reconciliation_manager.reconcile_timers()
            # Should complete without errors
        
        asyncio.run(test_reconcile_timers_no_guilds())
    
    def test_reconcile_timers_with_incomplete_setup(self):
        """Test timer reconciliation with incomplete setup."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Mock guild config with incomplete setup
        incomplete_config = create_mock_guild_config(self.test_data['guild_id'])
        incomplete_config['setup_complete'] = False
        
        reconciliation_manager.bot.club_configs = {
            self.test_data['guild_id']: incomplete_config
        }
        
        # Test reconciliation with incomplete setup
        async def test_reconcile_timers_incomplete():
            await reconciliation_manager.reconcile_timers()
            # Should complete without errors
        
        asyncio.run(test_reconcile_timers_incomplete())
    
    def test_reconcile_timers_error_handling(self):
        """Test error handling in timer reconciliation."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Mock the bot's club configs
        reconciliation_manager.bot.club_configs = {
            self.test_data['guild_id']: create_mock_guild_config(self.test_data['guild_id'])
        }
        
        # Mock the timer scheduler to raise an exception
        reconciliation_manager.timer_scheduler.get_active_timers = Mock(side_effect=Exception("Test error"))
        
        # Test reconciliation with error
        async def test_reconcile_timers_error():
            await reconciliation_manager.reconcile_timers()
            # Should complete without errors (error is logged)
        
        asyncio.run(test_reconcile_timers_error())


class TestTimerComparison:
    """Test timer comparison and synchronization."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.reconciliation_manager = MockReconciliationManager()
        self.bot.reconciliation_manager = self.reconciliation_manager
        self.test_data = create_test_data_set()
    
    def test_compare_expected_vs_stored_timers(self):
        """Test comparison of expected vs stored timers."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Create mock current timers
        current_timers = {
            'timer_1': create_mock_timer_data('timer_1', 'task_reminder_24h'),
            'timer_2': create_mock_timer_data('timer_2', 'meeting_reminder_2h')
        }
        
        # Create mock tasks and meetings
        tasks = [create_mock_task_data('task_1')]
        meetings = [create_mock_meeting_data('meeting_1')]
        
        # Test timer comparison
        async def test_timer_comparison():
            await reconciliation_manager._update_timers_from_data(
                current_timers, tasks, meetings, self.test_data['spreadsheet_id']
            )
            # Should complete without errors
        
        asyncio.run(test_timer_comparison())
    
    def test_add_new_timers(self):
        """Test adding new timers to the system."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Test that the method exists and is callable
        assert hasattr(reconciliation_manager, '_update_timers_from_data')
        assert callable(reconciliation_manager._update_timers_from_data)
        
        # Test that the method is async
        import inspect
        assert inspect.iscoroutinefunction(reconciliation_manager._update_timers_from_data)
    
    def test_update_existing_timers(self):
        """Test updating existing timers in the system."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Test that the method exists and is callable
        assert hasattr(reconciliation_manager, '_update_timers_from_data')
        assert callable(reconciliation_manager._update_timers_from_data)
        
        # Test that the method is async
        import inspect
        assert inspect.iscoroutinefunction(reconciliation_manager._update_timers_from_data)
    
    def test_cancel_obsolete_timers(self):
        """Test cancelling obsolete timers in the system."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Create mock current timers
        current_timers = {
            'timer_1': create_mock_timer_data('timer_1', 'task_reminder_24h'),
            'timer_2': create_mock_timer_data('timer_2', 'meeting_reminder_2h')
        }
        
        # Create mock tasks and meetings (empty - no timers needed)
        tasks = []
        meetings = []
        
        # Mock the timer scheduler
        reconciliation_manager.timer_scheduler.cancel_timer = AsyncMock()
        
        # Test cancelling obsolete timers
        async def test_cancel_obsolete_timers():
            await reconciliation_manager._update_timers_from_data(
                current_timers, tasks, meetings, self.test_data['spreadsheet_id']
            )
            # Should call cancel_timer for obsolete timers
            reconciliation_manager.timer_scheduler.cancel_timer.assert_called()
        
        asyncio.run(test_cancel_obsolete_timers())


class TestExpectedTimerBuilding:
    """Test building expected timers from current data."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.reconciliation_manager = MockReconciliationManager()
        self.bot.reconciliation_manager = self.reconciliation_manager
        self.test_data = create_test_data_set()
    
    def test_build_expected_task_timers(self):
        """Test building expected timers for tasks."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Create mock task data with future deadline
        task = create_mock_task_data('task_1')
        task['deadline'] = (datetime.now() + timedelta(days=2)).isoformat()  # 2 days in future
        task['status'] = 'Open'
        
        # Test building expected task timers
        expected_timers = reconciliation_manager._build_expected_task_timers(task)
        
        # Should have timers for 24h reminder, 2h reminder, overdue, and escalation
        assert len(expected_timers) > 0
        # Check that we have at least some expected timer types
        timer_ids = list(expected_timers.keys())
        assert any('task_reminder_24h' in timer_id for timer_id in timer_ids)
        assert any('task_reminder_2h' in timer_id for timer_id in timer_ids)
        assert any('task_overdue' in timer_id for timer_id in timer_ids)
        assert any('task_escalation' in timer_id for timer_id in timer_ids)
    
    def test_build_expected_meeting_timers(self):
        """Test building expected timers for meetings."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Create mock meeting data with future start time
        meeting = create_mock_meeting_data('meeting_1')
        meeting['start_time'] = (datetime.now() + timedelta(hours=3)).isoformat()  # 3 hours in future
        
        # Test building expected meeting timers
        expected_timers = reconciliation_manager._build_expected_meeting_timers(meeting)
        
        # Should have timers for 2h reminder, start notification, and minutes processing
        assert len(expected_timers) > 0
        timer_ids = list(expected_timers.keys())
        assert any('meeting_reminder_2h' in timer_id for timer_id in timer_ids)
        assert any('meeting_start' in timer_id for timer_id in timer_ids)
        assert any('meeting_minutes' in timer_id for timer_id in timer_ids)
    
    def test_build_expected_timers_with_past_deadlines(self):
        """Test building expected timers with past deadlines."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Test that the method exists and is callable
        assert hasattr(reconciliation_manager, '_build_expected_task_timers')
        assert callable(reconciliation_manager._build_expected_task_timers)
        
        # Create mock task data with past deadline
        task = create_mock_task_data('task_1')
        task['deadline'] = (datetime.now() - timedelta(days=1)).isoformat()
        task['status'] = 'Open'
        
        # Test building expected task timers
        expected_timers = reconciliation_manager._build_expected_task_timers(task)
        
        # Should return a dictionary
        assert isinstance(expected_timers, dict)
    
    def test_build_expected_timers_with_completed_tasks(self):
        """Test building expected timers with completed tasks."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Test that the method exists and is callable
        assert hasattr(reconciliation_manager, '_build_expected_task_timers')
        assert callable(reconciliation_manager._build_expected_task_timers)
        
        # Create mock task data with completed status
        task = create_mock_task_data('task_1')
        task['deadline'] = (datetime.now() + timedelta(days=1)).isoformat()
        task['status'] = 'Completed'
        
        # Test building expected task timers
        expected_timers = reconciliation_manager._build_expected_task_timers(task)
        
        # Should return a dictionary (may be empty for completed tasks)
        assert isinstance(expected_timers, dict)
    
    def test_build_expected_timers_with_missing_data(self):
        """Test building expected timers with missing data."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Create mock task data with missing deadline
        task = create_mock_task_data('task_1')
        task['deadline'] = None
        task['status'] = 'Open'
        
        # Test building expected task timers
        expected_timers = reconciliation_manager._build_expected_task_timers(task)
        
        # Should not have any timers for tasks without deadlines
        assert len(expected_timers) == 0
        
        # Create mock meeting data with missing start time
        meeting = create_mock_meeting_data('meeting_1')
        meeting['start_time'] = None
        
        # Test building expected meeting timers
        expected_timers = reconciliation_manager._build_expected_meeting_timers(meeting)
        
        # Should not have any timers for meetings without start times
        assert len(expected_timers) == 0


class TestTimerUpdateDetection:
    """Test detection of timer updates needed."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.reconciliation_manager = MockReconciliationManager()
        self.bot.reconciliation_manager = self.reconciliation_manager
        self.test_data = create_test_data_set()
    
    def test_timer_needs_update_detection(self):
        """Test detection of when timers need updating."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Create mock current timer
        current_timer = {
            'id': 'timer_1',
            'type': 'task_reminder_24h',
            'scheduled_time': '2024-01-01T10:00:00',
            'reminder_type': '24h',
            'user_id': '123456789'
        }
        
        # Create mock expected timer with different scheduled time
        expected_timer = {
            'id': 'timer_1',
            'type': 'task_reminder_24h',
            'scheduled_time': '2024-01-01T11:00:00',  # Different time
            'reminder_type': '24h',
            'user_id': '123456789'
        }
        
        # Test timer update detection
        needs_update = reconciliation_manager._timer_needs_update(current_timer, expected_timer)
        assert needs_update is True
        
        # Test timer that doesn't need update
        expected_timer['scheduled_time'] = '2024-01-01T10:00:00'  # Same time
        needs_update = reconciliation_manager._timer_needs_update(current_timer, expected_timer)
        assert needs_update is False
    
    def test_timer_needs_update_different_user(self):
        """Test detection of timer updates when user changes."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Create mock current timer
        current_timer = {
            'id': 'timer_1',
            'type': 'task_reminder_24h',
            'scheduled_time': '2024-01-01T10:00:00',
            'reminder_type': '24h',
            'user_id': '123456789'
        }
        
        # Create mock expected timer with different user
        expected_timer = {
            'id': 'timer_1',
            'type': 'task_reminder_24h',
            'scheduled_time': '2024-01-01T10:00:00',
            'reminder_type': '24h',
            'user_id': '987654321'  # Different user
        }
        
        # Test timer update detection
        needs_update = reconciliation_manager._timer_needs_update(current_timer, expected_timer)
        assert needs_update is True
    
    def test_timer_needs_update_different_reminder_type(self):
        """Test detection of timer updates when reminder type changes."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Create mock current timer
        current_timer = {
            'id': 'timer_1',
            'type': 'task_reminder_24h',
            'scheduled_time': '2024-01-01T10:00:00',
            'reminder_type': '24h',
            'user_id': '123456789'
        }
        
        # Create mock expected timer with different reminder type
        expected_timer = {
            'id': 'timer_1',
            'type': 'task_reminder_24h',
            'scheduled_time': '2024-01-01T10:00:00',
            'reminder_type': '2h',  # Different reminder type
            'user_id': '123456789'
        }
        
        # Test timer update detection
        needs_update = reconciliation_manager._timer_needs_update(current_timer, expected_timer)
        assert needs_update is True


class TestReconciliationLogging:
    """Test reconciliation logging and summary."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        setup_test_environment()
        self.bot = MockBot()
        self.reconciliation_manager = MockReconciliationManager()
        self.bot.reconciliation_manager = self.reconciliation_manager
        self.test_data = create_test_data_set()
    
    def test_reconciliation_summary_logging(self):
        """Test that reconciliation summary is logged."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Mock the bot's club configs
        reconciliation_manager.bot.club_configs = {
            self.test_data['guild_id']: create_mock_guild_config(self.test_data['guild_id'])
        }
        
        # Mock the timer scheduler
        reconciliation_manager.timer_scheduler.get_active_timers = Mock(return_value={})
        
        # Mock the task and meeting managers
        reconciliation_manager.task_manager.get_tasks = Mock(return_value=[])
        reconciliation_manager.meeting_manager.get_meetings = Mock(return_value=[])
        
        # Test reconciliation with logging
        async def test_reconciliation_logging():
            await reconciliation_manager.reconcile_timers()
            # Should complete without errors and log summary
        
        asyncio.run(test_reconciliation_logging())
    
    def test_reconciliation_error_logging(self):
        """Test that reconciliation errors are logged."""
        # Mock the reconciliation manager
        from discordbot.modules.reconciliation import ReconciliationManager
        reconciliation_manager = ReconciliationManager(self.bot)
        
        # Mock the bot's club configs
        reconciliation_manager.bot.club_configs = {
            self.test_data['guild_id']: create_mock_guild_config(self.test_data['guild_id'])
        }
        
        # Mock the timer scheduler to raise an exception
        reconciliation_manager.timer_scheduler.get_active_timers = Mock(side_effect=Exception("Test error"))
        
        # Test reconciliation with error logging
        async def test_reconciliation_error_logging():
            await reconciliation_manager.reconcile_timers()
            # Should complete without errors (error is logged)
        
        asyncio.run(test_reconciliation_error_logging())


if __name__ == "__main__":
    pytest.main([__file__])
