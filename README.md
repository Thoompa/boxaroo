# Boxaroo

## Setup

1. Create a virtual environment (recommended):
   - `python -m venv .venv`
   - `source .venv/bin/activate`
2. Install requirements:
   - `pip install -r requirements.txt`

## Run

- DEBUG test run:
  - `python __main__.py --list_size TESTING --logging_level DEBUG`
- Full run:
  - `python __main__.py --list_size FULL --logging_level INFO`

## Output

- Data files are saved into `Data/<YYYY-MM-DD>/woolworths-<YYYY-MM-DD>-<size>.csv`
- Logs are saved into `Logs/Log-<YYYY-MM-DD>.txt`

## Features

- `get_category_total_items` reads displayed product count from the website then falls back to tile count.
- `get_products` now tracks per-page `tiles/scraped/incomplete` statistics.
- `get_category_data` logs category totals and incomplete item details.
- partial product rows are retained with missing fields recorded.

## Testing

### Quick Start
```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate

# Run tests
python -m pytest -q

# Or use the provided script
./scripts/run_tests.sh
```

### Setup Requirements
Before running tests, ensure the virtual environment and dependencies are installed:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Test Files
- `tests/test_woolworths.py` - Woolworths scraper unit tests
- `tests/test_web_driver.py` - Web driver tests

### Verbose Output
```bash
python -m pytest -v  # Show individual test results
python -m pytest -vv # Extra verbose with full output
```


## Clean

- `Data` and `__pycache__` are ignored by `.gitignore` and not tracked.

## Pre-commit Hooks

This repository uses [pre-commit](https://pre-commit.com/) to enforce code quality and formatting standards automatically before each commit.

### What pre-commit does

- Formats Python code with **Black**
- Lints and auto-fixes with **Ruff**
- Removes trailing whitespace
- Ensures files end with a newline
- Checks YAML file syntax

### How to use

1. Ensure your virtual environment is activated:
  ```bash
  source .venv/bin/activate
  ```
2. Install pre-commit (if not already):
  ```bash
  pip install pre-commit
  pre-commit install
  ```
3. Hooks run automatically on `git commit`. To run all hooks manually on all files:
  ```bash
  pre-commit run --all-files
  ```
4. If any hook fails, fix the reported issues and re-add the files before committing again.
