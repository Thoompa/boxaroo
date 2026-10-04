"""Refresh the real-markup fixtures used by Tests/test_dom_contract.py.

Loads the live Woolworths site and saves the browse menu and a category page's
product count as small HTML fragments in Tests/fixtures/dom/. Run it when the
site's markup changes, then look at the diff: that diff is the markup change.

    python Scripts/capture_dom_fixtures.py [--headed]
"""

import argparse
import sys
import time
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Code.logger import ILogger  # noqa: E402
from Code.web_driver import WebDriver  # noqa: E402

FIXTURE_DIR = PROJECT_ROOT / "Tests" / "fixtures" / "dom"
BASE_URL = "https://www.woolworths.com.au"
SAMPLE_CATEGORY = "deli"

CAPTURE_MENU_SCRIPT = """
var link = document.querySelector('a[href^="/shop/browse/"]');
var menu = link && link.closest('[class*="browse-flyout"]');
return menu ? menu.outerHTML : '';
"""

CAPTURE_TOTAL_SCRIPT = """
var el = document.querySelector('[class*="pagination-info_component_pagination-info"]');
return el ? el.outerHTML : '';
"""


class QuietLogger(ILogger):
    def __init__(self, logging_level=None):
        self.logging_level = logging_level

    def debug(self, message): ...
    def log(self, message): ...
    def warning(self, message):
        print(f"WARNING: {message}")

    def error(self, message):
        print(f"ERROR: {message}")


def write_fixture(name: str, source_url: str, fragment: str) -> None:
    if not fragment:
        raise SystemExit(f"Nothing captured for {name}; the markup has changed again")
    FIXTURE_DIR.joinpath(name).write_text(
        f'<!doctype html>\n<meta charset="utf-8">\n'
        f"<!-- Captured {date.today()} from {source_url} by "
        f"Scripts/capture_dom_fixtures.py -->\n{fragment}\n",
        encoding="utf-8",
    )
    print(f"Wrote {name} ({len(fragment)} characters)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    driver = WebDriver(logger=QuietLogger(), headless=not args.headed)
    try:
        driver.get_page(BASE_URL)
        driver.execute_script(
            "var b = document.querySelector('button[aria-label=\"Browse Products\"]');"
            "if (b) { b.click(); }"
        )
        time.sleep(3)
        write_fixture(
            "menu_current.html", BASE_URL, driver.execute_script(CAPTURE_MENU_SCRIPT)
        )

        category_url = f"{BASE_URL}/shop/browse/{SAMPLE_CATEGORY}"
        driver.get_page(category_url)
        write_fixture(
            "category_total_current.html",
            category_url,
            driver.execute_script(CAPTURE_TOTAL_SCRIPT),
        )
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
