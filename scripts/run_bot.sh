#!/bin/bash
set -euo pipefail

# AutoExec Bot Launch Script (local dev)
# Goal: run the bot with the right venv + env vars, keep secrets quiet, and save readable logs.

echo "🤖 Launching AutoExec Bot (local)..."

# --- tiny helpers ---
log_dir="logs"
log_file="${log_dir}/local_run.log"
venv_dir="venv"

mkdir -p "$log_dir"

# Make sure we clean up nicely on exit (even if Ctrl+C)
deactivate_if_needed() {
  # shellcheck disable=SC1090
  command -v deactivate >/dev/null 2>&1 && deactivate || true
}
trap deactivate_if_needed EXIT

# 1) Virtual environment: create if needed, then activate
if [[ ! -d "$venv_dir" ]]; then
  echo "🧪 No virtual environment found. Creating one..."
  python3 -m venv "$venv_dir"
  # shellcheck disable=SC1090
  source "${venv_dir}/bin/activate"
  pip install --upgrade pip
  pip install -r requirements.txt
else
  # shellcheck disable=SC1090
  source "${venv_dir}/bin/activate"
fi

# 2) Load environment variables from .env — without ever printing values
if [[ ! -f ".env" ]]; then
  echo "❌ .env file not found. Create one first (see README)!"
  exit 1
fi

echo "🔑 Loading environment variables from .env (keeping secrets quiet)..."
# Minimal .env parser: KEY=VALUE lines, ignore comments/empties; strips surrounding quotes.
while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  if [[ "$line" =~ ^[[:space:]]*([^[:space:]=]+)[[:space:]]*=[[:space:]]*\"?([^\"]*)\"?[[:space:]]*$ ]]; then
    var_name="${BASH_REMATCH[1]}"
    var_value="${BASH_REMATCH[2]}"
    export "${var_name}=${var_value}"
  fi
done < .env

# 3) Sanity checks for required env vars (do NOT print values)
required_vars=( "DISCORD_BOT_TOKEN" )
missing=0
for v in "${required_vars[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "❌ Required env var ${v} is missing."
    missing=1
  fi
done
if [[ $missing -eq 1 ]]; then
  echo "Fix your .env and try again."
  exit 1
fi

# Optional: OpenAI key check if your local run needs it
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  # Just pattern check; don't print the key.
  if [[ ! "$OPENAI_API_KEY" =~ ^sk-[a-z]+- ]]; then
    echo "⚠️  OPENAI_API_KEY is set but format looks unusual. Continuing anyway."
  fi
fi

# 4) Basic permission warnings (no secrets printed)
if [[ -f ".env" ]]; then
  perms=$(stat -c "%a" .env 2>/dev/null || stat -f "%OLp" .env 2>/dev/null || echo "")
  if [[ -n "$perms" ]]; then
    # If .env is group/other-readable, gently warn
    if [[ "$perms" =~ ^[0-9]([6-7])[0-9]$ || "$perms" =~ ^[0-9][0-9]([6-7])$ ]]; then
      echo "⚠️  .env permissions look a bit open (${perms}). Consider: chmod 600 .env"
    fi
  fi
fi

echo "✅ Environment ready. Starting bot and tee-ing logs to ${log_file}"
echo "📝 Tip: Ctrl+C to stop. Logs persist in ${log_file}"

# 5) Run the bot: show output live AND write to log with timestamps
#   - Use Python's -u flag for unbuffered output
#   - Capture all output and add timestamps to log file
python -u scripts/start_bot.py 2>&1 | while IFS= read -r line; do
  echo "$line"
  echo "$(date '+%Y-%m-%d %H:%M:%S') $line" >> "${log_file}"
done
