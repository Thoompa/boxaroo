# Boxaroo

Selenium-based scraper that collects Woolworths (Australia) product and price data, one category at a time, into dated CSV files. A Vue 3 front-end in `BoxarooApp/` is for viewing the data. The goal is a reliable, repeatable record of supermarket prices over time, so completeness and trustworthy run reporting matter more than raw speed.

## Layout

- `Code/` — scraper. `cli.py`/`main.py` entry, `scrape_coordinator.py` orchestrates runs, `web_driver.py` (Selenium + pagination), `woolworths*.py` (category source, normaliser, adapter), `product_parser.py`, `file_handler.py`, `logger.py`.
- `Tests/` — pytest suite; shared test doubles live in `Tests/test_helpers.py`.
- `Scripts/run_long_categories.sh` — runs each category as its own headless process (how scheduled runs work); `Deploy/` has example systemd units.
- `Config/performance.example.json` — per-device ETA tuning (`Config/performance.json` is git-ignored).
- `Data/` (CSV output, category list cache) and `Logs/` are git-ignored. `Logs/odyssey/` holds logs from the scheduled-run host.

## Commands

- Setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt pytest`
- Tests: `python -m pytest -q` (`Tests/test_woolworths_live_integration.py` hits the live site; skip it for routine runs)
- Run one category: `python __main__.py --category <name> --headless`
- Quick check: `python __main__.py --list_size TESTING --logging_level DEBUG`
- Full usage and list sizes: `README.md`

## Conventions

- All imports at the top of the file, never inline (`copilot-instructions.md`).
- Tests use GIVEN/WHEN/THEN comments (WHEN in passive voice), `Dummy*` test doubles, and reuse `Tests/test_helpers.py` (`.github/instructions/python-tests.instructions.md`).
- `Code/web_driver.py` uses CRLF line endings; preserve them when editing.
- Formatting/linting via pre-commit (Black, Ruff).
- Scraping is slow (hours per large category) and the site bot-detects: don't add live scraping to routine verification.

## Known issues

A review of ~5 months of run logs found data-collection problems (lost runs, truncated categories, parsing bugs, unreliable totals). They are tracked, with evidence and priorities, in [.claude/known-issues.md](.claude/known-issues.md). Read it before changing scraping, pagination, storage or run-summary code, and update it when an issue is fixed or a new one is found.
