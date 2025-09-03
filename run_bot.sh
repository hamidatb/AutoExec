#!/bin/bash

# AutoExec Bot Launch Script
# This script ensures the bot runs with the correct environment variables

echo "🤖 Launching AutoExec Bot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Running setup first..."
    source ./setup_env.sh
fi

# Activate virtual environment
source venv/bin/activate

# Load environment variables using the improved setup script
if [ -f ".env" ]; then
    echo "🔑 Loading environment variables..."
    
    # Read .env file and export variables properly
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
            # Remove quotes and handle spaces around equals sign
            if [[ "$line" =~ ^[[:space:]]*([^[:space:]]+)[[:space:]]*=[[:space:]]*\"?([^\"]*)\"?[[:space:]]*$ ]]; then
                var_name="${BASH_REMATCH[1]}"
                var_value="${BASH_REMATCH[2]}"
                export "$var_name"="$var_value"
            fi
        fi
    done < .env
else
    echo "❌ .env file not found!"
    exit 1
fi

# Verify OpenAI API key is loaded correctly
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not found in environment!"
    exit 1
fi

# Check if it's the correct key (should start with sk-proj-)
if [[ ! "$OPENAI_API_KEY" =~ ^sk-proj- ]]; then
    echo "❌ Wrong OpenAI API key format detected!"
    echo "Expected: sk-proj-... (your project key)"
    echo "Found: ${OPENAI_API_KEY:0:20}..."
    exit 1
fi

echo "✅ Environment verified!"
echo "🔑 Using OpenAI API key: ${OPENAI_API_KEY:0:20}..."
echo "🚀 Starting bot..."

# Run the bot
python -m discordbot.discord_client
