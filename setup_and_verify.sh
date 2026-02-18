#!/bin/bash
echo "🚀 Setting up Archon environment..."

# Check if pip is available
if ! command -v pip &> /dev/null; then
    echo "❌ pip not found. Please install Python and pip."
    exit 1
fi

echo "📦 Installing dependencies from requirements.txt..."
# Use pip install --upgrade to ensure we get latest packages
pip install --upgrade -r requirements.txt

echo "✅ Dependencies installed."

echo "🔍 Running Phase 3 Verification (Intelligence Layer)..."
PYTHONPATH=src python verify_phase3.py

echo "🧠 Running Phase 4 Verification (Learning Engine & Memory)..."
PYTHONPATH=src python verify_phase4.py

echo "🎉 All verifications complete! You can now start Archon CLI:"
echo "   python -m archon start <project_path>"
