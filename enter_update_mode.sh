#!/bin/bash
set -euo pipefail

echo "⏸️ Entering update mode..."
echo "⏹️  Stopping bot and disabling autostart..."
sudo systemctl disable --now discord-bot || true

echo "✅ Bot is now stopped and disabled."
echo "   Check with:"
echo "     systemctl is-active discord-bot"
echo "     systemctl is-enabled discord-bot"
