"""Run the scraper's in-page JavaScript against saved HTML in a real browser.

The unit tests stub out the browser, so they can't tell when Woolworths changes
its markup. These tests load snapshots into headless Chrome from disk (no
network, no bot detection) and call the real scraper methods on them.

- `*_current.html` are real captures; refresh them with
  `python Scripts/capture_dom_fixtures.py` and review the diff.
- Inline snippets and `*_legacy*` markup are hand-written to pin down older
  markup the scraper must keep supporting.
"""

from pathlib import Path

import pytest

from Code import woolworths_category_source
from Code.web_driver import WebDriver
from Tests.test_helpers import DummyLogger, make_woolworths_category_source

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "dom"
STABLE_CATEGORIES = ["fruit-veg", "dairy-eggs-fridge", "pantry", "bakery"]


@pytest.fixture(scope="session")
def selenium_driver():
    """Headless Chrome shared by these tests; skipped when Chrome isn't available."""
    try:
        browser = WebDriver(logger=DummyLogger(), headless=True)
    except Exception as exc:
        pytest.skip(f"Chrome is not available: {type(exc).__name__}: {exc}")
    yield browser.driver
    browser.quit()


class SavedPageBrowser:
    """The slice of IWebDriver the scraper uses, backed by a page on disk."""

    def __init__(self, selenium_driver, page_path: Path):
        self.selenium_driver = selenium_driver
        self.page_path = page_path

    def get_page(self, _url: str) -> None:
        self.selenium_driver.get(self.page_path.as_uri())

    def execute_script(self, script: str, *args):
        return self.selenium_driver.execute_script(script, *args)


@pytest.fixture
def saved_page(selenium_driver, tmp_path):
    """Returns open_page(html_or_path) -> browser showing that markup."""

    def open_page(content: str | Path) -> SavedPageBrowser:
        if isinstance(content, Path):
            page_path = content
        else:
            page_path = tmp_path / "page.html"
            page_path.write_text(
                f'<!doctype html><meta charset="utf-8">{content}', encoding="utf-8"
            )
        browser = SavedPageBrowser(selenium_driver, page_path)
        browser.get_page("")
        return browser

    return open_page


@pytest.fixture(autouse=True)
def no_retry_sleeps(monkeypatch):
    monkeypatch.setattr(woolworths_category_source.time, "sleep", lambda _: None)


def discover_categories(browser, tmp_path):
    source = make_woolworths_category_source(
        cache_path=str(tmp_path / "cache.json"), web_driver=browser
    )
    return source._get_supermarket_categories()


def read_total(browser):
    return WebDriver.get_category_total_items(browser)


# ============================================================
# Browse menu discovery
# ============================================================


def test_menu_discovery_reads_current_markup(saved_page, tmp_path):
    # GIVEN: a capture of the current Woolworths browse menu
    browser = saved_page(FIXTURE_DIR / "menu_current.html")

    # WHEN: categories are discovered
    categories = discover_categories(browser, tmp_path)

    # THEN: the usual categories are found once each, with absolute links
    names = [item["name"] for item in categories]
    assert len(names) >= 15
    assert len(names) == len(set(names))
    assert not [name for name in STABLE_CATEGORIES if name not in names]
    for item in categories:
        assert (
            item["href"] == f"https://www.woolworths.com.au/shop/browse/{item['name']}"
        )


@pytest.mark.parametrize(
    "link_attributes",
    [
        'class="item ng-star-inserted"',
        'class="item"',
    ],
    ids=["item-and-ng-star-inserted-classes", "item-class"],
)
def test_menu_discovery_still_reads_legacy_markup(
    saved_page, tmp_path, link_attributes
):
    # GIVEN: the older menu markup, where links carried an "item" class
    browser = saved_page(
        f'<a {link_attributes} href="/shop/browse/fruit-veg">Fruit & Veg</a>'
        f'<a {link_attributes} href="/shop/browse/pantry">Pantry</a>'
    )

    # WHEN: categories are discovered
    categories = discover_categories(browser, tmp_path)

    # THEN: the categories are still found
    assert [item["name"] for item in categories] == ["fruit-veg", "pantry"]


def test_menu_discovery_normalises_links(saved_page, tmp_path):
    # GIVEN: links with a query string, a trailing slash, a fragment and a repeat
    browser = saved_page(
        '<a href="/shop/browse/pantry?filter=x">Pantry</a>'
        '<a href="/shop/browse/bakery/">Bakery</a>'
        '<a href="/shop/browse/deli#top">Deli</a>'
        '<a href="/shop/browse/pantry">Pantry again</a>'
        '<a href="/shop/other/page">Not a category</a>'
    )

    # WHEN: categories are discovered
    categories = discover_categories(browser, tmp_path)

    # THEN: names are clean, repeats are dropped and other links are ignored
    assert [item["name"] for item in categories] == ["pantry", "bakery", "deli"]


def test_menu_discovery_opens_the_browse_menu_first(saved_page, tmp_path):
    # GIVEN: a page whose category links only appear once "Browse Products" is clicked
    browser = saved_page(
        '<button aria-label="Browse Products" onclick="'
        "document.body.insertAdjacentHTML('beforeend',"
        "'<a href=\\'/shop/browse/fruit-veg\\'>Fruit</a>')\">Browse products</button>"
    )

    # WHEN: categories are discovered
    categories = discover_categories(browser, tmp_path)

    # THEN: the menu was opened and the category found
    assert [item["name"] for item in categories] == ["fruit-veg"]


def test_menu_discovery_returns_nothing_when_markup_is_unrecognised(
    saved_page, tmp_path
):
    # GIVEN: a menu whose links no longer point at /shop/browse/
    browser = saved_page('<a href="/browse/fruit-veg">Fruit</a>')

    # WHEN: categories are discovered
    categories = discover_categories(browser, tmp_path)

    # THEN: nothing is found, which callers treat as a discovery failure
    assert categories == []


# ============================================================
# Category product total
# ============================================================


def test_category_total_reads_current_markup(saved_page):
    # GIVEN: a capture of the current category page product count
    browser = saved_page(FIXTURE_DIR / "category_total_current.html")

    # WHEN/THEN: the total is read from "1 – to 36 of 676 Products"
    assert read_total(browser) == 676


@pytest.mark.parametrize(
    ("markup", "expected_total"),
    [
        ('<div class="ais-Stats-text">1-36 of 1,234 results</div>', 1234),
        ('<span class="search-result-count">88 results</span>', 88),
        ("<p>Displaying 1 - 36 of 5,000 products</p>", 5000),
        ("<p>1 - 36 of 2,048 products</p>", 2048),
        ("<wc-product-tile></wc-product-tile>" * 3, 3),
    ],
    ids=[
        "ais-stats",
        "result-count-class",
        "displaying-text",
        "range-text",
        "tile-count-fallback",
    ],
)
def test_category_total_still_reads_older_markup(saved_page, markup, expected_total):
    # GIVEN: older markup, or no count element at all
    browser = saved_page(markup)

    # WHEN/THEN: the total is still read, falling back to the page text and tiles
    assert read_total(browser) == expected_total


def test_category_total_reads_zero_from_a_page_that_has_not_loaded(saved_page):
    # GIVEN: a page with no count and no product tiles, as while still loading
    browser = saved_page("<main></main>")

    # WHEN/THEN: zero is returned, not None (known issue 3: callers can't tell
    # "not loaded yet" from "empty category")
    assert read_total(browser) == 0
