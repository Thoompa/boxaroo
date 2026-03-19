#!/usr/bin/env bash
set -euo pipefail

echo "Running unit tests..."
python -m pytest -q

echo "Running TESTING list..."
python __main__.py --list_size TESTING --logging_level INFO
