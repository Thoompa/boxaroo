"""Refresh the real product tile text used by Tests/test_product_parser_real_data.py.

Scrapes the first page of a spread of categories from the live site and saves
each tile's raw text (what ProductParser receives) to Tests/fixtures/tiles/.
Prices and specials change, so a refresh changes most lines of these files;
the tests are written around patterns, not specific products.

    python Scripts/capture_tile_fixtures.py [--headed] [category ...]
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Code.logger import ILogger  # noqa: E402
from Code.web_driver import WebDriver  # noqa: E402

FIXTURE_DIR = PROJECT_ROOT / "Tests" / "fixtures" / "tiles"
BASE_URL = "https://www.woolworths.com.au/shop/browse/"

# A spread of tile styles: per-kg produce, specials, Marketplace sellers, packaged goods.
DEFAULT_CATEGORIES = [
    "fruit-veg",
    "deli",
    "pantry",
    "dairy-eggs-fridge",
    "home-lifestyle",
    "pet",
    "health-wellness",
    "beer-wine-spirits",
]


class QuietLogger(ILogger):
    def __init__(self, logging_level=None):
        self.logging_level = logging_level

    def debug(self, message): ...
    def log(self, message): ...
    def warning(self, message):
        print(f"WARNING: {message}")

    def error(self, message):
        print(f"ERROR: {message}")


def capture_first_page(driver: WebDriver, category: str) -> list[str]:
    tiles: list[str] = []

    def record(payloads, page_number):
        tiles.extend(payloads)
        return []

    driver.get_page(BASE_URL + category)
    # Stop after the first page.
    driver._advance_with_recovery = lambda *args, **kwargs: False
    driver.get_products(record, category_name=category)
    # The page repeats each tile; keep the first of each, in page order.
    return list(dict.fromkeys(tile for tile in tiles if tile.strip()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("categories", nargs="*", default=DEFAULT_CATEGORIES)
    args = parser.parse_args()

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    driver = WebDriver(logger=QuietLogger(), headless=not args.headed)
    try:
        for category in args.categories:
            tiles = capture_first_page(driver, category)
            if not tiles:
                raise SystemExit(f"No tiles captured for {category}")
            path = FIXTURE_DIR / f"{category}.json"
            path.write_text(
                json.dumps(
                    {
                        "captured": str(date.today()),
                        "source": BASE_URL + category,
                        "tiles": tiles,
                    },
                    indent=1,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            print(f"Wrote {path.name}: {len(tiles)} tiles")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
