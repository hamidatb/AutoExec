# Club Exec Task Manager Bot - Test Suite

This directory contains comprehensive tests for the Club Exec Task Manager Bot, organized into modular test categories.

## Test Structure

```
tests/
├── __init__.py
├── README.md
├── test_bot.py                    # Legacy test file
├── test_setup/                    # Setup command and DM flow tests
│   ├── __init__.py
│   ├── test_setup_command.py      # /setup command blocking tests
│   └── test_interactive_dm_flow.py # Interactive DM flow tests
├── test_validation/               # Input validation tests
│   ├── __init__.py
│   └── test_input_validation.py   # Channel, timezone, admin, exec validation
├── test_sheets/                   # Google Sheets creation tests
│   ├── __init__.py
│   └── test_sheets_creation.py    # Sheet creation and management tests
├── test_reconciliation/           # Reconciliation job tests
│   ├── __init__.py
│   └── test_reconciliation_job.py # 15-minute timer comparison tests
└── test_utils/                    # Test utilities and helpers
    ├── __init__.py
    ├── mock_objects.py            # Mock objects and fixtures
    └── test_helpers.py            # Helper functions and assertions
```

## Running Tests

### Quick Start

```bash
# Run all tests
python tests/run_tests.py

# Run with verbose output
python tests/run_tests.py -v

# Run with coverage reporting
python tests/run_tests.py -c

# Run specific test category
python tests/run_tests.py -k "setup"

# Run tests matching a pattern
python tests/run_tests.py -k "validation"
```

### Using pytest directly

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_setup/test_setup_command.py

# Run specific test class
pytest tests/test_setup/test_setup_command.py::TestSetupCommand

# Run specific test method
pytest tests/test_setup/test_setup_command.py::TestSetupCommand::test_setup_command_dm_only

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=googledrive --cov=discordbot --cov-report=term-missing
```

## Test Categories

### 1. Setup Tests (`test_setup/`)

Tests for the `/setup` command and interactive DM flow:

- **Setup Command Blocking**: Ensures features are blocked until setup is complete
- **Interactive DM Flow**: Tests the complete setup process through DMs
- **Guild ID Validation**: Tests server ID input validation
- **Club Name Validation**: Tests club name input validation
- **Admin Selection**: Tests admin @mention validation
- **Timezone Configuration**: Tests timezone selection with default handling
- **Executive Team Setup**: Tests exec member collection and validation
- **Channel Configuration**: Tests Discord channel ID validation
- **Setup Completion**: Tests the complete setup flow end-to-end

### 2. Validation Tests (`test_validation/`)

Tests for input validation functionality:

- **Channel ID Validation**: Tests Discord channel ID format validation
- **Discord ID Validation**: Tests Discord user ID format validation
- **Guild ID Validation**: Tests Discord server ID format validation
- **Timezone Validation**: Tests timezone string validation
- **Executive Member Validation**: Tests exec member data validation
- **Input Sanitization**: Tests input cleaning and whitespace handling
- **Case Insensitive Handling**: Tests case-insensitive input processing

### 3. Sheets Tests (`test_sheets/`)

Tests for Google Sheets creation and management:

- **Master Config Sheet Creation**: Tests creation of the main configuration sheet
- **Monthly Sheets Creation**: Tests creation of monthly task and meeting sheets
- **Config Channels Update**: Tests updating configuration with channel IDs
- **Folder Access Verification**: Tests Google Drive folder access validation
- **Sheet Structure Validation**: Tests that sheets have required tabs and structure
- **Data Persistence**: Tests that configuration data is properly saved

### 4. Reconciliation Tests (`test_reconciliation/`)

Tests for the reconciliation job functionality:

- **Reconciliation Loop**: Tests the 15-minute reconciliation loop
- **Timer Comparison**: Tests comparison of expected vs stored timers
- **Timer Synchronization**: Tests adding, updating, and cancelling timers
- **Expected Timer Building**: Tests building expected timers from current data
- **Timer Update Detection**: Tests detection of when timers need updating
- **Reconciliation Logging**: Tests logging and summary generation

## Test Features

### Key Features Tested

1. **Setup Command Blocking**: All features are blocked until `/setup` is complete
2. **Interactive DM Flow**: Complete setup process through private messages
3. **Input Validation**: Comprehensive validation of all user inputs
4. **Google Sheets Integration**: Creation and management of configuration sheets
5. **Reconciliation Job**: 15-minute timer synchronization with Google Sheets
6. **Error Handling**: Robust error handling and user feedback
7. **Data Persistence**: Configuration data is properly saved and retrieved

### Test Coverage

The test suite covers:

- ✅ `/setup` command functionality and blocking
- ✅ Interactive DM flow for setup
- ✅ Input validation (channels, timezone, admin, execs)
- ✅ Google Sheets creation with proper tabs (config, people, logs, timers)
- ✅ Configuration data persistence
- ✅ Reconciliation job (15-minute timer comparison)
- ✅ Timer synchronization (insert/update/cancel)
- ✅ Error handling and user feedback
- ✅ Case-insensitive input processing
- ✅ Channel ID validation
- ✅ Admin verification and access control

## Mock Objects and Fixtures

The test suite includes comprehensive mock objects:

- **MockDiscordUser**: Mock Discord user objects
- **MockDiscordGuild**: Mock Discord guild objects
- **MockDiscordInteraction**: Mock Discord interaction objects
- **MockBot**: Mock bot instance for testing
- **MockSetupManager**: Mock setup manager for testing
- **MockSheetsManager**: Mock Google Sheets manager for testing
- **MockTimerScheduler**: Mock timer scheduler for testing
- **MockReconciliationManager**: Mock reconciliation manager for testing

## Test Helpers

Utility functions for testing:

- **Input Validation Helpers**: Functions to validate various input types
- **Assertion Helpers**: Custom assertions for test validation
- **Mock Data Creators**: Functions to create test data sets
- **Error Scenario Creators**: Functions to create error test scenarios
- **Success Scenario Creators**: Functions to create success test scenarios

## Configuration

Test configuration is managed through `pytest.ini`:

- Test discovery patterns
- Output formatting
- Markers for test categorization
- Timeout settings
- Warning filters
- Coverage options

## Continuous Integration

The test suite is designed to work with CI/CD pipelines:

- Comprehensive test coverage
- Clear pass/fail indicators
- Detailed error reporting
- JSON result export
- Exit codes for automation

## Contributing

When adding new tests:

1. Follow the existing test structure
2. Use appropriate test categories
3. Include comprehensive mock objects
4. Add proper error handling tests
5. Update this README if adding new test categories
6. Ensure tests are deterministic and don't depend on external services

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the project root is in the Python path
2. **Mock Failures**: Check that mock objects are properly configured
3. **Async Test Issues**: Use `asyncio.run()` for async test functions
4. **Google API Errors**: Tests use mocks, so real API calls shouldn't occur

### Debug Mode

Run tests with verbose output for debugging:

```bash
python tests/run_tests.py -v
```

### Test Specific Features

Run tests for specific features:

```bash
# Test setup functionality
python tests/run_tests.py -k "setup"

# Test validation
python tests/run_tests.py -k "validation"

# Test sheets creation
python tests/run_tests.py -k "sheets"

# Test reconciliation
python tests/run_tests.py -k "reconciliation"
```
