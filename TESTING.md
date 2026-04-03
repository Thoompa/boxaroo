# Boxaroo Testing & Development Commands

## ONE-LINE SETUP (First Time Only)

```bash
python3 -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt
```

Or use the setup script:
```bash
bash scripts/dev_setup.sh
```

## ACTIVATE ENVIRONMENT (Every Session)

```bash
source .venv/bin/activate
```

## RUN TESTS

```bash
# Quick test run (unit tests only)
python -m pytest -q

# Full test suite (unit tests + integration test)
./scripts/run_tests.sh

# Verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_woolworths.py -v

# Run specific test
python -m pytest tests/test_woolworths.py::test_parse_product_data_full -v
```

## RUN APPLICATION

```bash
# Small dataset, debug logging (fastest)
python __main__.py --list_size TESTING --logging_level DEBUG

# Medium dataset, info logging
python __main__.py --list_size SHORT --logging_level INFO

# Full dataset, info logging (slowest, real web scraping)
python __main__.py --list_size FULL --logging_level INFO
```

## CHECK ENVIRONMENT

```bash
# Verify venv is active
which python

# Check Python version
python --version

# List installed packages
pip list

# Verify pytest is available
python -m pytest --version
```

## OUTPUT LOCATIONS

- **Data files:** `Data/<YYYY-MM-DD>/woolworths-<YYYY-MM-DD>-<size>.csv`
- **Logs:** `Logs/Log-<YYYY-MM-DD>.txt`
- **Test output:** Printed to stdout

## COMMON ISSUES & FIXES

| Issue | Solution |
|-------|----------|
| `No module named pytest` | `source .venv/bin/activate` |
| `externally-managed-environment` | Use `.venv`, not system Python |
| `command not found: python` | Use `python3` or `.venv/bin/python` |
| `Permission denied: ./scripts/run_tests.sh` | `bash scripts/run_tests.sh` or `chmod +x scripts/run_tests.sh` |
| ChromeDriver errors | Selenium 4.x auto-manages; ensure Chrome installed |

## KEY FILES FOR AGENTS

- `.instructions.md` - This guide (AI agent reference)
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project metadata
- `tox.ini` - Test configuration
- `tests/` - Test suite
- `woolworths.py` - Main scraper logic
- `web_driver.py` - Selenium wrapper
