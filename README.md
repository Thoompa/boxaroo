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

- `python -m pytest -q`

## Clean

- `Data` and `__pycache__` are ignored by `.gitignore` and not tracked.
