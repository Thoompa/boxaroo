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

path = pathlib.Path(os.environ["CATEGORY_LISTS_PATH"])
data = json.loads(path.read_text(encoding="utf-8"))
categories = data.get("long")
if not isinstance(categories, list):
    raise SystemExit("Expected JSON key 'long' to be a list of category names")
for name in categories:
    if isinstance(name, str) and name.strip():
        print(name.strip())
PY
)

 if [[ ${#categories[@]} -eq 0 ]]; then
     echo "[boxaroo] No categories found in 'long' list in: $CATEGORY_LISTS" >&2
     exit 1
 fi
for category in "${categories[@]}"; do
    echo "[boxaroo] Running category: ${category}"
    "$PYTHON_BIN" "$REPO_ROOT/__main__.py" --category "$category" --headless
done
