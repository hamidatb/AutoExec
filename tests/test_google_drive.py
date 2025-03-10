import pytest
import os
from unittest.mock import patch, MagicMock
from googledrive.main import main

@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    os.environ["DRIVE_FOLDER_ID"] = "mock_folder_id"
    os.environ["DRIVE_FILE_NAME_FILTER"] = "Meeting Mins"

@patch("main.get_credentials")
@patch("main.get_drive_service")
@patch("main.get_latest_matching_file")
@patch("main.download_file")
def test_main(mock_download_file, mock_get_latest_matching_file, mock_get_drive_service, mock_get_credentials, mock_env_vars, capsys):
    """Test the main function with mocked dependencies."""
    
    # Mock credentials and service
    mock_get_credentials.return_value = "mock_creds"
    mock_get_drive_service.return_value = "mock_service"

    # Mock found file
    mock_file = {"id": "mock_file_id", "name": "Meeting Mins Jan 2025", "mimeType": "application/vnd.google-apps.document"}
    mock_get_latest_matching_file.return_value = [mock_file]  # List with one mock file

    # Mock file download content
    mock_download_file.return_value = "Mock file content"

    # Run the main function
    main()

    # Capture printed output
    captured = capsys.readouterr()
    output = captured.out

    # Assertions
    assert "Searching for the most recent file matching filter..." in output
    assert "Found latest file: Meeting Mins Jan 2025 (mock_file_id)" in output
    assert "Mock file content" in output
    assert "Program completed successfully. Exiting." in output
