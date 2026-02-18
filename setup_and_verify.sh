#!/bin/bash
echo "🚀 Setting up Archon environment..."

# Check if Python/pip is available
if ! command -v python &> /dev/null; then
    echo "❌ python not found."
    exit 1
fi

echo "📦 Installing dependencies from requirements.txt..."
pip install --upgrade -r requirements.txt

echo "✅ Python dependencies installed."

# Check npm for tools
if command -v npm &> /dev/null; then
    echo "📦 Checking external tools (eraser-cli)..."
    if ! command -v eraser &> /dev/null; then
        echo "⚠️  eraser-cli not found. Installing global package..."
        # Use sudo if needed or just warn?
        # Typically prompt user
        echo "   (Skipping auto-install. Run 'npm install -g eraser-cli' manually if desired)"
    else
        echo "✅ eraser-cli found."
    fi
else
    echo "⚠️  npm not found. External tool integrations may be limited."
fi

echo "🔍 Running Phase 3 Verification (Intelligence Layer)..."
PYTHONPATH=src python verify_phase3.py

echo "🧠 Running Phase 4 Verification (Learning Engine)..."
PYTHONPATH=src python verify_phase4.py

echo "🛠️  Running Phase 5 Verification (Tool Sandbox)..."
PYTHONPATH=src python verify_phase5.py

echo "🎉 All systems GO! Start Archon CLI:"
echo "   python -m archon start ."
