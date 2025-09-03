# ==============================================================================
# Makefile for NSP QR Bot Project
# ==============================================================================
# Main usage:
#   - make install      # Install dependencies
#   - make start-server # Start server (API + Database)
#   - make start-bot    # Start Telegram bot
# ==============================================================================

SHELL := /bin/bash
SCRIPT_DIR := ./scripts

.PHONY: help install start-server start-bot clipboard

all: help

# ------------------------------------------------------------------------------
# Show usage and available commands
# ------------------------------------------------------------------------------
help:
	@echo ""
	@echo "NSP QR Bot Project"
	@echo "=================="
	@echo "Usage:"
	@echo "  make install       Install dependencies"
	@echo "  make start-server  Start server (API + Database)"
	@echo "  make start-bot     Start Telegram bot"
	@echo "  make clipboard     Copy source files to clipboard"
	@echo ""
	@echo "Example workflow:"
	@echo "  1. make install"
	@echo "  2. make start-server   (in one terminal)"
	@echo "  3. make start-bot      (in another terminal)"
	@echo ""

# ------------------------------------------------------------------------------
# Installation: Set up dependencies
# ------------------------------------------------------------------------------
install:
	@chmod +x $(SCRIPT_DIR)/install.sh
	@$(SCRIPT_DIR)/install.sh

# ------------------------------------------------------------------------------
# Start services
# ------------------------------------------------------------------------------
start-server:
	@chmod +x $(SCRIPT_DIR)/start-api.sh
	@$(SCRIPT_DIR)/start-api.sh

start-bot:
	@chmod +x $(SCRIPT_DIR)/start-bot.sh
	@$(SCRIPT_DIR)/start-bot.sh

# ------------------------------------------------------------------------------
# Copy Project Context: All source files to clipboard
# ------------------------------------------------------------------------------
clipboard:
	@chmod +x $(SCRIPT_DIR)/clipboard.sh
	@$(SCRIPT_DIR)/clipboard.sh
