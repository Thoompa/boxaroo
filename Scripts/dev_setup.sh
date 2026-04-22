#!/usr/bin/env bash
# Quick development setup script for Boxaroo
# Usage: ./scripts/dev_setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔧 Boxaroo Development Setup"
echo "================================"

cd "$REPO_ROOT"

# Check Python is available
echo "✓ Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found. Please install Python 3.x"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "  Found: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv .venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate venv
echo "✓ Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "✓ Upgrading pip, setuptools, wheel..."
python -m pip install --upgrade pip setuptools wheel -q

# Install requirements
echo "✓ Installing project dependencies..."
python -m pip install -r requirements.txt -q

# Verify pytest is installed
echo "✓ Verifying test framework..."
python -m pytest --version

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate environment: source .venv/bin/activate"
echo "  2. Run tests: python -m pytest -q"
echo "  3. Run app: python __main__.py --list_size TESTING --logging_level DEBUG"
echo ""
