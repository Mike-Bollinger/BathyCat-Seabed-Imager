#!/bin/bash
#
# BathyImager Startup Script
# =========================
# 
# Automatically detects and uses virtual environment or system Python
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
CONFIG_FILE="$SCRIPT_DIR/config/bathyimager_config.json"

# Change to source directory
cd "$SRC_DIR"

# Choose Python interpreter
PYTHON_CMD=""

# Check for virtual environment first
if [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    echo "Using virtual environment Python"
    PYTHON_CMD="$SCRIPT_DIR/venv/bin/python"
elif [ -f "$SCRIPT_DIR/venv/bin/python3" ]; then
    echo "Using virtual environment Python3"
    PYTHON_CMD="$SCRIPT_DIR/venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    echo "Using system Python3"
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    echo "Using system Python"
    PYTHON_CMD="python"
else
    echo "ERROR: No Python interpreter found"
    exit 1
fi

# Verify config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Run the application
echo "Starting BathyImager with config: $CONFIG_FILE"
exec "$PYTHON_CMD" main.py --config "$CONFIG_FILE" "$@"