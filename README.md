# Boxaroo

## Setup

1. Create a virtual environment (recommended):
   - `python -m venv .venv`
   - `source .venv/bin/activate`
2. Install requirements:
   - `pip install -r requirements.txt`

## Run

- DEBUG test run (tiny category sample):
  - `python __main__.py --list_size TESTING --logging_level DEBUG`
- Short run (~10 min):
  - `python __main__.py --list_size SHORT --logging_level INFO`
- Medium run (~35 min):
  - `python __main__.py --list_size MEDIUM --logging_level INFO`
- Long run (~2.5 hrs):
  - `python __main__.py --list_size LONG --logging_level INFO`
- Full run (~8 hrs):
  - `python __main__.py --list_size FULL --logging_level INFO`

### List sizes

| Size    | Products per category | Approximate runtime |
|---------|-----------------------|---------------------|
| TESTING | ≤ 3 categories        | ~2 min              |
| SHORT   | < 1 000               | ~12 min             |
| MEDIUM  | < 1 800               | ~35 min             |
| LONG    | < 10 000              | ~2.5 hrs            |
| FULL    | all categories        | ~8 hrs              |

Thresholds are based on the number of products in each Woolworths category.
Run `--help` to see dynamic ETA estimates calculated from cached product totals:

```
python __main__.py --help
```

### Refreshing category lists

Category lists and product totals are cached in `Data/category_lists/woolworths-category-lists.json`.
To rebuild the cache from the live website (required after site structure changes):

```
python __main__.py --list_size SHORT --refresh_category_lists
```

## Output

- Data files are saved into `Data/<YYYY-MM-DD>/woolworths-<YYYY-MM-DD>-<size>.csv`
- Logs are saved into `Logs/Log-<YYYY-MM-DD>.txt`

## Features

- Five list sizes (TESTING / SHORT / MEDIUM / LONG / FULL) let you balance speed vs. coverage.
- `--help` displays dynamic ETA estimates per list size, calculated from cached product totals.
- `--refresh_category_lists` fetches the current category structure from the website and rebuilds the cache, including per-category and per-list product totals.
- `get_category_total_items` reads displayed product count from the website then falls back to tile count.
- `get_products` now tracks per-page `tiles/scraped/incomplete` statistics.
- `get_products` callback contract is plain-data only: callback input is `list[str]` of product text payloads, never Selenium `WebElement` objects.
- `get_category_data` logs category totals and incomplete item details.
- Partial product rows are retained with missing fields recorded.

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

## Agent & Automation Documentation

Agents and automated tools should consult the following files for comprehensive project guidance, test plans, and development automation:

- **Agent/** — Primary folder for relevant AI material (agent definitions, role guides, and workflow notes)
- **.instructions.md** — Full development and environment setup guide for AI agents and automation tools
- **TESTING.md** — Quick reference for all setup, test, and run commands
- **BDD_TEST_PLAN.md** — Complete BDD (Given/When/Then) test plan, including implemented and planned scenarios
- **scripts/dev_setup.sh** — Automated environment setup script

These files provide:
- Environment and dependency setup instructions
- Test and run command reference
- Detailed test coverage and priorities
- Manual review and logging requirements
- Project structure and file responsibilities

Agents should always check these files before making changes, running tests, or performing code analysis.

When agent-specific guidance exists, agents should check the Agent/ folder first, then use this README and the referenced docs for project-wide instructions.
