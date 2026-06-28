#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
CATEGORY_LISTS="$REPO_ROOT/Data/category_lists/woolworths-category-lists.json"

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "[boxaroo] Python venv not found or not executable at: $PYTHON_BIN" >&2
    echo "[boxaroo] Create it with: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
    exit 1
fi

if [[ ! -f "$CATEGORY_LISTS" ]]; then
    echo "[boxaroo] Category list cache not found at: $CATEGORY_LISTS" >&2
    echo "[boxaroo] Build it with: $PYTHON_BIN \"$REPO_ROOT/__main__.py\" --list_size SHORT --refresh_category_lists" >&2
    exit 1
fi
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
