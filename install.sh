#!/bin/bash

# ARCHON.AI Installation Script

set -e

echo "🚀 Installing ARCHON.AI..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.11+ is required"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l) )); then
    echo "❌ Python 3.11+ is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION found"

# Install Poetry if not present
if ! command -v poetry &> /dev/null; then
    echo "📦 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✅ Poetry found"

# Install dependencies
echo "📦 Installing dependencies..."
poetry install

# Setup complete
echo ""
echo "✅ ARCHON.AI installed successfully!"
echo ""
echo "Quick start:"
echo "  poetry run archon start"
echo ""
echo "Or activate the virtual environment:"
echo "  poetry shell"
echo "  archon start"
echo ""
