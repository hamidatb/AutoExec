#!/bin/bash

# AutoExec Environment Setup Script
# This script ensures a clean environment for running the bot

echo "🔧 Setting up AutoExec environment..."

# Deactivate conda base if active
if [[ "$CONDA_DEFAULT_ENV" == "base" ]]; then
    echo "📦 Deactivating conda base environment..."
    conda deactivate
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

# Load environment variables from .env
if [ -f ".env" ]; then
    echo "🔑 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found!"
    exit 1
fi

echo "✅ Environment setup complete!"
echo "🚀 You can now run: python -m discordbot.discord_client"
echo ""
echo "💡 To activate this environment in the future, run:"
echo "   source setup_env.sh"
