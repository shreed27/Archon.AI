#!/bin/bash

# ARCHON Wrapper Script
# Usage: 
#   ./archon download  - Install/Update dependencies
#   ./archon start     - Start the system

set -e

COMMAND=$1

function show_header() {
    echo ""
    echo -e "\033[1;36m       ARCHON       \033[0m"
    echo -e "\033[0;37m  Autonomous Engineering  \033[0m"
    echo ""
}

if [ "$COMMAND" = "download" ]; then
    show_header
    echo -e "\033[1;33m⬇️  Downloading Neural Engine & Dependencies...\033[0m"
    
    # Check for poetry
    if ! command -v poetry &> /dev/null; then
        echo "📦 Installing package manager..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
    fi

    # Install dependencies quietly but show progress
    poetry install --sync
    
    echo ""
    echo -e "\033[1;32m✅ Download Complete.\033[0m"
    echo -e "Run \033[1;37m./archon start\033[0m to initialize."
    exit 0

elif [ "$COMMAND" = "start" ]; then
    # Ensure dependencies exist
    if [ ! -d ".venv" ] && [ ! -d "$(poetry env info --path 2>/dev/null)" ]; then
        echo "❌ Dependencies not found. Run './archon download' first."
        exit 1
    fi
    
    # Run the python CLI
    poetry run archon start
    exit 0

elif [ "$COMMAND" = "help" ] || [ -z "$COMMAND" ]; then
    show_header
    echo "Usage:"
    echo "  ./archon download   Install/Update system"
    echo "  ./archon start      Initialize neural engine"
    exit 0

else
    # Pass through other commands to the python CLI
    poetry run archon "$@"
fi
