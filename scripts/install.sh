#!/bin/bash
# ==============================================================================
# Install Script — Installs dependencies and configures project
# ==============================================================================
# This script sets up required dependencies (CLI and Python), configuration,
# and .env file using professional TUI notifications and prompts.
# ==============================================================================

set -e
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
SERVER_VENV_PATH="$PROJECT_ROOT/server/.venv"
TELEGRAM_VENV_PATH="$PROJECT_ROOT/telegram-app/.venv"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE_FILE="$SCRIPT_DIR/example.env"

source "$SCRIPT_DIR/lib.sh"

command_exists() { command -v "$1" &> /dev/null; }

setup_environment_file() {
    if [ -f "$ENV_FILE" ]; then
        notify info ".env file already exists at '$ENV_FILE'."
    else
        if [ -f "$ENV_EXAMPLE_FILE" ]; then
            cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
            notify success "Created .env file from template."
        else
            notify error "'example.env' not found. Cannot create .env file."
        fi
    fi
}

install_dependencies() {
    local required_cmds=("gum" "glow" "bat" "psql")
    local missing_cmds=()
    for cmd in "${required_cmds[@]}"; do
        if ! command_exists "$cmd"; then
            missing_cmds+=("$cmd")
        fi
    done
    if [ ${#missing_cmds[@]} -eq 0 ]; then
        notify success "All required tools are already installed."
        return
    fi
    notify warn "Missing tools: ${missing_cmds[*]}"
    if command_exists brew; then
        notify info "Installing via Homebrew (macOS)..."
        # Install PostgreSQL if missing
        if [[ " ${missing_cmds[*]} " =~ " psql " ]]; then
            with_spinner "Installing PostgreSQL" brew install postgresql
        fi
        # Install other tools
        local other_cmds=()
        for cmd in "${missing_cmds[@]}"; do
            if [ "$cmd" != "psql" ]; then
                other_cmds+=("$cmd")
            fi
        done
        if [ ${#other_cmds[@]} -gt 0 ]; then
            brew install "${other_cmds[@]}"
        fi
    elif command_exists apt-get; then
        notify info "Installing via apt-get (Debian/Ubuntu)..."
        sudo apt-get update
        if [[ " ${missing_cmds[*]} " =~ " psql " ]]; then
            with_spinner "Installing PostgreSQL" sudo apt-get install -y postgresql postgresql-contrib
        fi
        local other_cmds=()
        for cmd in "${missing_cmds[@]}"; do
            if [ "$cmd" != "psql" ]; then
                other_cmds+=("$cmd")
            fi
        done
        if [ ${#other_cmds[@]} -gt 0 ]; then
            sudo apt-get install -y "${other_cmds[@]}"
        fi
    else
        notify warn "Unsupported package manager. Please install: ${missing_cmds[*]}"
        return
    fi
    notify success "System dependencies installation complete."
}

setup_python_environment() {
    # Setup server environment
    notify info "Setting up server environment..."
    if [ ! -d "$SERVER_VENV_PATH" ]; then
        with_spinner "Creating server virtual environment" python3 -m venv "$SERVER_VENV_PATH"
    fi
    cd "$PROJECT_ROOT/server"
    with_spinner "Installing API server packages" "$SERVER_VENV_PATH/bin/pip" install -r requirements_api.txt
    
    # Setup telegram-app environment
    notify info "Setting up telegram-app environment..."
    if [ ! -d "$TELEGRAM_VENV_PATH" ]; then
        with_spinner "Creating telegram-app virtual environment" python3 -m venv "$TELEGRAM_VENV_PATH"
    fi
    cd "$PROJECT_ROOT/telegram-app"
    with_spinner "Installing Telegram bot packages" "$TELEGRAM_VENV_PATH/bin/pip" install -r requirements.txt
    
    notify success "Python environments created and dependencies installed."
}

main() {
    install_dependencies
    setup_python_environment
    setup_environment_file
    notify success "Installation and setup complete!"
}

main