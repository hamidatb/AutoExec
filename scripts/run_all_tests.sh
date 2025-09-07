#!/bin/bash
# Simple shell script to run all tests for the Club Exec Task Manager Bot
#./scripts/run_all_tests.sh

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment exists and activate it
VENV_PATH="$PROJECT_ROOT/venv"
if [[ -d "$VENV_PATH" ]]; then
    echo "🐍 Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
    echo "✅ Virtual environment activated: $VIRTUAL_ENV"
else
    echo "⚠️ No virtual environment found at $VENV_PATH"
    echo "💡 Consider creating one with: python3 -m venv venv"
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    exit 1
fi

# Run the test suite
echo "🚀 Starting comprehensive test suite..."
echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Run tests with verbose output
python3 scripts/run_tests.py -v

# Capture exit code
EXIT_CODE=$?

# Print final message
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "🎉 All tests completed successfully!"
else
    echo "❌ Some tests failed. Check the output above for details."
fi

exit $EXIT_CODE
