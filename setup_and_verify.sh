#!/bin/bash
echo "🚀 Setting up Archon environment..."

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ python not found."
    exit 1
fi

echo "📦 Installing dependencies..."
# Install requirements
pip install -r requirements.txt
# Install package in editable mode (makes 'archon' command available)
pip install -e .

echo "✅ Dependencies installed & Archon linked."

# Check npm for tools
if command -v npm &> /dev/null; then
    echo "📦 Checking external tools (eraser-cli)..."
    if ! command -v eraser &> /dev/null; then
        echo "⚠️  eraser-cli not found. Run 'npm install -g eraser-cli' manually if desired."
    else
        echo "✅ eraser-cli found."
    fi
else
    echo "⚠️  npm not found. External tool integrations may be limited."
fi

echo "🔍 Running Verification Suites..."
# No PYTHONPATH needed now if pip install -e . worked
python verify_phase3.py
python verify_phase4.py
python verify_phase5.py

echo "🎉 All systems GO! Start Archon CLI:"
echo "   archon start ."
# Or python -m archon start .
