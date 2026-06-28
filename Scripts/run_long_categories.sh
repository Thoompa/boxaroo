#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
CATEGORY_LISTS="$REPO_ROOT/Data/category_lists/woolworths-category-lists.json"

mapfile -t categories < <(
    CATEGORY_LISTS_PATH="$CATEGORY_LISTS" "$PYTHON_BIN" - <<'PY'
import json
import os
import pathlib

data = json.loads(pathlib.Path(os.environ["CATEGORY_LISTS_PATH"]).read_text())
print("\n".join(data["long"]))
PY
)

for category in "${categories[@]}"; do
    echo "[boxaroo] Running category: ${category}"
    "$PYTHON_BIN" "$REPO_ROOT/__main__.py" --category "$category" --headless
done
