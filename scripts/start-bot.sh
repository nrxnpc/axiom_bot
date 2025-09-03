#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib.sh"

notify info "Starting NSP Telegram Bot..."

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/telegram-app/.venv" ]; then
    notify error "Virtual environment not found. Please run 'make install' first."
    exit 1
fi

# Check if server is running
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    notify warn "API server is not running. Please start it first with 'make start-server'"
fi

# Start Telegram bot
cd "$PROJECT_ROOT/telegram-app"
notify info "Connecting to Telegram API..."
.venv/bin/python qr_bot.py