#!/bin/bash

# AutoExec Environment Setup Script
# This script ensures a clean environment for running the bot

echo "🔧 Setting up AutoExec environment..."

# Deactivate conda base if active
if [[ "$CONDA_DEFAULT_ENV" == "base" ]]; then
    echo "📦 Deactivating conda base environment..."
    conda deactivate 2>/dev/null || echo "⚠️  Conda not available or already deactivated"
fi

# Remove any conflicting environment variables
unset OPENAI_API_KEY
unset PINECONE_API_KEY
unset DISCORD_BOT_TOKEN

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📦 Installing requirements..."
pip install -r requirements.txt

# Load environment variables from .env with proper parsing
if [ -f ".env" ]; then
    echo "🔑 Loading environment variables from .env..."
    
    # Read .env file and export variables properly
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
            # Remove quotes and handle spaces around equals sign
            if [[ "$line" =~ ^[[:space:]]*([^[:space:]]+)[[:space:]]*=[[:space:]]*\"?([^\"]*)\"?[[:space:]]*$ ]]; then
                var_name="${BASH_REMATCH[1]}"
                var_value="${BASH_REMATCH[2]}"
                export "$var_name"="$var_value"
                echo "  ✅ Loaded: $var_name"
            fi
        fi
    done < .env
else
    echo "❌ .env file not found!"
    exit 1
fi

echo "✅ Environment setup complete!"
echo "🚀 You can now run: python -m discordbot.discord_client"
echo ""
echo "💡 To activate this environment in the future, run:"
echo "   source setup_env.sh"
