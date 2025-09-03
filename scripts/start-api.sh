#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib.sh"

notify info "Starting NSP Server (API + Database)..."

# Check if PostgreSQL is installed
if ! command -v psql > /dev/null; then
    notify error "PostgreSQL is not installed. Please install PostgreSQL first."
    exit 1
fi

# Start PostgreSQL if not running
if ! pgrep -x "postgres" > /dev/null; then
    notify info "Starting PostgreSQL database..."
    if command -v brew > /dev/null && brew services list | grep postgresql > /dev/null; then
        with_spinner "Starting PostgreSQL via Homebrew" brew services start postgresql
    elif command -v systemctl > /dev/null; then
        with_spinner "Starting PostgreSQL via systemctl" sudo systemctl start postgresql
    elif command -v pg_ctl > /dev/null; then
        with_spinner "Starting PostgreSQL via pg_ctl" pg_ctl -D /usr/local/var/postgres start
    else
        notify error "Cannot start PostgreSQL automatically. Please start it manually."
        exit 1
    fi
    sleep 2  # Wait for PostgreSQL to start
else
    notify success "PostgreSQL is already running"
fi

# Create database and user if they don't exist
notify info "Setting up database..."
if ! psql -lqt | cut -d \| -f 1 | grep -qw nsp_qr_db; then
    with_spinner "Creating database and user" bash -c '
        psql -c "CREATE USER nsp_user WITH PASSWORD '"'"'nsp_password'"'"';" postgres || true
        psql -c "CREATE DATABASE nsp_qr_db OWNER nsp_user;" postgres || true
        psql -c "GRANT ALL PRIVILEGES ON DATABASE nsp_qr_db TO nsp_user;" postgres || true
    '
else
    notify success "Database already exists"
fi

# Initialize database schema
notify info "Initializing database schema..."
cd "$PROJECT_ROOT/server"
if [ -f "database_schema.sql" ]; then
    with_spinner "Creating database tables" psql -d nsp_qr_db -U nsp_user -h localhost -f database_schema.sql
fi

# Start API server
notify info "Starting API server..."
with_spinner "Initializing server components" .venv/bin/python api_server.py